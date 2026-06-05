from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from rentals.forms import BookingPaymentForm
from rentals.payment_idempotency import (
    abort_payment_idempotency,
    begin_payment_idempotency,
    complete_payment_idempotency,
    payment_token,
)
from rentals.promotion_payment import charge_host_verification
from rentals.promotions import FREE_ACCOUNT_PLAN, VERIFICATION_TIERS

from .forms import QashaAuthenticationForm, UserRegistrationForm, ManageProfileForm
from .tiers import (
    FREE_MAX_PHOTOS,
    PREMIUM_MAX_PHOTOS,
    PREMIUM_MAX_VIDEO_SECONDS,
    get_max_active_listings,
    user_active_listing_count,
)


@require_POST
def logout_view(request):
    """Log out via POST only (CSRF-protected in nav)."""
    logout(request)
    return redirect("rentals:property_list")


@login_required
def edit_profile(request):
    """Account and profile settings from Manage."""
    form = ManageProfileForm(request.user, request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Your profile was updated.")
        return redirect("users:profile")

    return render(
        request,
        "users/profile_edit.html",
        {
            "form": form,
            "profile_user": request.user,
        },
    )


@login_required
def upgrade_account(request):
    """Legacy URL — listing perks are now included with host verification."""
    messages.info(
        request,
        "More photos and video are included when you become a verified host. "
        "Apply under Promote & verify.",
    )
    return redirect("rentals:promotions")


@login_required
def request_host_verification(request):
    """Landlord or agency verification — pay on Qasha; badge activates immediately."""
    user = request.user
    payment_form = BookingPaymentForm()
    selected_tier = request.GET.get("tier", "") or request.POST.get("tier", "")

    if request.method == "POST" and request.POST.get("action") == "pay_verification":
        tier = request.POST.get("tier", "")
        if tier not in VERIFICATION_TIERS:
            messages.error(request, "Please choose a verification type.")
        elif user.has_host_verification_badge() and not (
            tier == "agency" and user.host_verification_tier == "landlord"
        ):
            messages.info(request, "Your host verification is already active.")
        else:
            payment_form = BookingPaymentForm(request.POST)
            if payment_form.is_valid():
                idem = payment_token('verification', user.pk, tier)
                if not begin_payment_idempotency(request, idem):
                    if user.has_host_verification_badge():
                        messages.info(request, 'Your host verification is already active.')
                    else:
                        messages.info(
                            request,
                            'This payment was already submitted. Refresh the page in a moment.',
                        )
                    return redirect('rentals:promotions')
                try:
                    charge_host_verification(
                        user,
                        tier,
                        card_last4=payment_form.cleaned_data["card_last4"],
                        cardholder_name=payment_form.cleaned_data["cardholder_name"],
                    )
                    complete_payment_idempotency(request, idem)
                    tier_info = VERIFICATION_TIERS[tier]
                    messages.success(
                        request,
                        f"You are now {tier_info['badge']}. Your verified badge and listing perks are active.",
                    )
                    return redirect("rentals:promotions")
                except ValueError as exc:
                    abort_payment_idempotency(idem)
                    messages.error(request, str(exc))
            selected_tier = tier

    elif request.method == "POST":
        tier = request.POST.get("tier", "")
        if tier in VERIFICATION_TIERS and not user.has_host_verification_badge():
            selected_tier = tier

    tier_info = VERIFICATION_TIERS.get(selected_tier) if selected_tier in VERIFICATION_TIERS else None

    return render(
        request,
        "users/request_verification.html",
        {
            "verification_tiers": VERIFICATION_TIERS,
            "free_plan": FREE_ACCOUNT_PLAN,
            "selected_tier": selected_tier,
            "tier_info": tier_info,
            "payment_form": payment_form,
            "free_max_photos": FREE_MAX_PHOTOS,
            "premium_max_photos": PREMIUM_MAX_PHOTOS,
            "premium_max_video_minutes": PREMIUM_MAX_VIDEO_SECONDS // 60,
            "listing_count": user_active_listing_count(user),
            "listing_cap": get_max_active_listings(user),
        },
    )


class UserLoginView(LoginView):
    template_name = "users/login.html"
    authentication_form = QashaAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        redirect_to = self.get_redirect_url()
        if redirect_to:
            return redirect_to
        return reverse_lazy("rentals:property_list")


class SignUpView(CreateView):
    form_class = UserRegistrationForm
    template_name = "users/signup.html"
    success_url = reverse_lazy("rentals:property_list")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("rentals:property_list")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, "Welcome to Qasha. Your account has been created.")
        return response
