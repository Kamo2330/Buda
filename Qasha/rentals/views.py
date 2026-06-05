from datetime import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Case, When, Value, IntegerField
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.decorators.http import require_POST

from .forms import (
    PropertyForm,
    PropertyImageForm,
    BookingForm,
    BookingPaymentForm,
    MessageForm,
    ReviewForm,
)
from .payment_utils import (
    authorize_booking_payment,
    capture_booking_payment,
    release_booking_authorization,
)
from .notifications import (
    notify_guest_booking_accepted,
    notify_guest_booking_declined,
    notify_guest_booking_cancelled_by_host,
)
from .booking_utils import (
    default_check_out,
    dates_overlap,
    get_securing_amount,
    uses_qasha_payment,
    validate_booking_dates,
    property_has_confirmed_tenant,
    property_has_active_booking,
    mark_property_occupied,
    clear_property_occupancy_if_no_tenant,
    decline_other_pending_bookings,
    OPEN_BOOKING_STATUSES,
)
from .redirect_utils import safe_redirect
from .amenity_utils import MAX_AMENITIES, amenity_filter_error, parse_custom_amenity_lines
from .payment_idempotency import (
    abort_payment_idempotency,
    begin_payment_idempotency,
    complete_payment_idempotency,
    payment_token,
)
from .cache_utils import get_browse_cities, get_host_amenities, get_standard_amenities, invalidate_browse_cache
from .query_utils import annotate_listing_price, property_listing_queryset
from .geo_utils import apply_geo_browse, apply_browse_ordering, RADIUS_FORM_CHOICES
from .listing_form_utils import listing_form_error_context, listing_video_upload_context
from .media_utils import stored_media_exists
from .promotions import FEATURED_PLANS, VERIFICATION_TIERS, FREE_ACCOUNT_PLAN, FEATURED_LISTING_HELP
from .promotion_payment import charge_featured_listing, charge_host_verification
from users.tiers import get_photo_limit, user_can_upload_video, user_has_full_listing_access, user_can_create_listing, get_max_active_listings
from .models import (
    Property,
    PropertyImage,
    Amenity,
    PropertyAmenity,
    PropertyRule,
    Booking,
    Message,
    Review,
    Wishlist,
)
import json

User = get_user_model()


def _thread_messages(user, other):
    return (
        Message.objects.filter(
            (Q(sender=user) & Q(recipient=other)) | (Q(sender=other) & Q(recipient=user))
        )
        .select_related("sender", "recipient", "property")
        .order_by("created_at")
    )


def _users_may_message(user, other):
    if _thread_messages(user, other).exists():
        return True
    return Booking.objects.filter(
        Q(guest=user, property__host=other) | Q(guest=other, property__host=user),
        status__in=OPEN_BOOKING_STATUSES,
    ).exists()


def _may_contact_host_about_listing(user, property_obj):
    """Message a listing host only after applying or an existing thread."""
    if _users_may_message(user, property_obj.host):
        return True
    return Booking.objects.filter(
        property=property_obj,
        guest=user,
        status__in=OPEN_BOOKING_STATUSES,
    ).exists()


def _duplicate_pending_booking(guest, property_obj, check_in, check_out=None):
    end = check_out or default_check_out(property_obj, check_in)
    for booking in Booking.objects.filter(
        guest=guest,
        property=property_obj,
        status='pending',
    ):
        other_end = booking.check_out_date or default_check_out(
            property_obj, booking.check_in_date
        )
        if dates_overlap(booking.check_in_date, other_end, check_in, end):
            return True
    return False


def _inbox_threads(user):
    """One row per other user: latest message and unread count."""
    seen = {}
    qs = (
        Message.objects.filter(Q(recipient=user) | Q(sender=user))
        .select_related("sender", "recipient", "property")
        .order_by("-created_at")[:300]
    )
    unread_map = {
        row["sender_id"]: row["c"]
        for row in Message.objects.filter(recipient=user, is_read=False)
        .values("sender_id")
        .annotate(c=Count("id"))
    }
    for m in qs:
        other = m.recipient if m.sender_id == user.id else m.sender
        oid = other.pk
        if oid == user.pk:
            continue
        if oid in seen:
            continue
        seen[oid] = {"other": other, "last": m, "unread": unread_map.get(oid, 0)}
    return sorted(seen.values(), key=lambda x: x["last"].created_at, reverse=True)


class PropertyListView(ListView):
    """Property search and browse view"""
    model = Property
    template_name = 'rentals/property_list.html'
    context_object_name = 'properties'
    paginate_by = 12
    
    def get_queryset(self):
        queryset = property_listing_queryset(
            Property.objects.filter(
                is_published=True,
                is_available=True,
                is_occupied=False,
            )
        )

        if self.request.user.is_authenticated:
            queryset = queryset.exclude(host=self.request.user)

        # Search functionality
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(title__icontains=search) |
                Q(description__icontains=search) |
                Q(city__icontains=search) |
                Q(suburb__icontains=search) |
                Q(address__icontains=search)
            )
        
        # Filters
        property_type = self.request.GET.get('property_type')
        if property_type:
            standard_types = {choice[0] for choice in Property.PROPERTY_TYPES}
            if property_type in standard_types:
                queryset = queryset.filter(property_type=property_type)
            else:
                queryset = queryset.filter(
                    property_type='other',
                    property_type_custom__icontains=property_type,
                )
        
        furnishing = self.request.GET.get('furnishing')
        if furnishing:
            queryset = queryset.filter(furnishing=furnishing)
        
        lease_type = self.request.GET.get('lease_type')
        if lease_type:
            queryset = queryset.filter(lease_type__in=[lease_type, 'both'])
        
        city = self.request.GET.get('city', '').strip()
        if city:
            queryset = queryset.filter(city__iexact=city)

        suburb = self.request.GET.get('suburb', '').strip()
        if suburb:
            queryset = queryset.filter(suburb__icontains=suburb)

        min_price = self.request.GET.get('min_price')
        max_price = self.request.GET.get('max_price')
        if min_price or max_price:
            queryset = annotate_listing_price(queryset)
        if min_price:
            try:
                min_p = float(min_price)
                queryset = queryset.filter(listing_price__gte=min_p)
            except ValueError:
                pass

        if max_price:
            try:
                max_p = float(max_price)
                queryset = queryset.filter(listing_price__lte=max_p)
            except ValueError:
                pass

        bedrooms = self.request.GET.get('bedrooms')
        if bedrooms:
            try:
                queryset = queryset.filter(bedrooms__gte=int(bedrooms))
            except ValueError:
                pass

        bathrooms = self.request.GET.get('bathrooms')
        if bathrooms:
            try:
                queryset = queryset.filter(bathrooms__gte=int(bathrooms))
            except ValueError:
                pass

        max_occupants = self.request.GET.get('max_occupants')
        if max_occupants:
            try:
                queryset = queryset.filter(max_occupants__gte=int(max_occupants))
            except ValueError:
                pass

        if self.request.GET.get('utilities_included'):
            queryset = queryset.filter(utilities_included=True)

        payment_preference = self.request.GET.get('payment_preference')
        if payment_preference in ('platform', 'direct'):
            queryset = queryset.filter(payment_preference=payment_preference)

        pet_friendly = self.request.GET.get('pet_friendly')
        if pet_friendly:
            queryset = queryset.filter(
                property_amenities__amenity__name__iexact='Pet friendly',
            )
            distinct_pks = queryset.values_list('pk', flat=True).distinct()
            queryset = property_listing_queryset(
                Property.objects.filter(
                    pk__in=distinct_pks,
                    is_published=True,
                    is_available=True,
                    is_occupied=False,
                )
            )

        amenity_ids = []
        for raw in self.request.GET.getlist('amenities'):
            try:
                amenity_ids.append(int(raw))
            except (TypeError, ValueError):
                pass
        custom_filter_names = parse_custom_amenity_lines(
            self.request.GET.get('custom_amenities', '')
        )
        self.amenity_filter_error = amenity_filter_error(amenity_ids, custom_filter_names)
        if not self.amenity_filter_error:
            for amenity_id in amenity_ids:
                queryset = queryset.filter(property_amenities__amenity_id=amenity_id)
            for name in custom_filter_names:
                queryset = queryset.filter(property_amenities__amenity__name__iexact=name)
            distinct_pks = queryset.values_list('pk', flat=True).distinct()
            queryset = property_listing_queryset(
                Property.objects.filter(
                    pk__in=distinct_pks,
                    is_published=True,
                    is_available=True,
                    is_occupied=False,
                )
            )

        geo_result = apply_geo_browse(queryset, self.request)
        self.geo_browse = geo_result['info']
        queryset = geo_result['queryset']

        return apply_browse_ordering(
            queryset,
            self.request,
            geo_active=self.geo_browse.get('active'),
            nationwide=self.geo_browse.get('nationwide', False),
        ).distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all amenities for filter
        context['amenities'] = get_standard_amenities()
        context['host_amenities'] = get_host_amenities()
        context['max_amenities'] = MAX_AMENITIES
        context['cities'] = get_browse_cities()
        context['property_types'] = Property.PROPERTY_TYPES

        user = self.request.user
        if user.is_authenticated:
            context['saved_property_ids'] = set(
                Wishlist.objects.filter(user=user).values_list('property_id', flat=True)
            )
        else:
            context['saved_property_ids'] = set()

        context['current_filters'] = {
            'search': self.request.GET.get('search', ''),
            'city': self.request.GET.get('city', ''),
            'suburb': self.request.GET.get('suburb', ''),
            'property_type': self.request.GET.get('property_type', ''),
            'furnishing': self.request.GET.get('furnishing', ''),
            'lease_type': self.request.GET.get('lease_type', ''),
            'min_price': self.request.GET.get('min_price', ''),
            'max_price': self.request.GET.get('max_price', ''),
            'bedrooms': self.request.GET.get('bedrooms', ''),
            'bathrooms': self.request.GET.get('bathrooms', ''),
            'max_occupants': self.request.GET.get('max_occupants', ''),
            'utilities_included': self.request.GET.get('utilities_included', ''),
            'payment_preference': self.request.GET.get('payment_preference', ''),
            'pet_friendly': self.request.GET.get('pet_friendly', ''),
            'amenities': self.request.GET.getlist('amenities'),
            'custom_amenities': self.request.GET.get('custom_amenities', ''),
            'sort': self.request.GET.get('sort', 'newest'),
            'radius_km': self.request.GET.get('radius_km', ''),
            'widen_search': self.request.GET.get('widen_search', ''),
        }
        cf = context['current_filters']
        context['geo_browse'] = getattr(self, 'geo_browse', {})
        context['radius_choices'] = RADIUS_FORM_CHOICES
        if user.is_authenticated:
            try:
                profile = user.profile
                if 'radius_km' not in self.request.GET:
                    cf['radius_km'] = str(
                        profile.search_radius_km
                        if profile.search_radius_km is not None
                        else 5
                    )
                if 'widen_search' not in self.request.GET:
                    cf['widen_search'] = '1' if profile.widen_search_if_empty else ''
            except Exception:
                pass
        context['selected_amenity_ids'] = {str(a) for a in cf['amenities']}
        custom_filter_parsed = parse_custom_amenity_lines(cf['custom_amenities'])
        context['custom_amenities_filter_count'] = len(custom_filter_parsed)
        # Badge counts only filters the user applied (GET), not profile defaults for radius/widen.
        context['active_filter_count'] = sum(
            1
            for key in (
                'search', 'city', 'suburb', 'property_type', 'furnishing', 'lease_type',
                'min_price', 'max_price', 'bedrooms', 'bathrooms', 'max_occupants',
                'payment_preference',
            )
            if cf.get(key)
        ) + len(cf['amenities']) + len(custom_filter_parsed) + (1 if cf.get('utilities_included') else 0) + (1 if cf.get('pet_friendly') else 0)
        if 'radius_km' in self.request.GET and cf.get('radius_km', '') != '':
            context['active_filter_count'] += 1
        if 'widen_search' in self.request.GET and cf.get('widen_search') in ('1', 'true', 'on'):
            context['active_filter_count'] += 1
        pag_qs = self.request.GET.copy()
        pag_qs.pop('page', None)
        context['pagination_query'] = pag_qs.urlencode()
        context['amenity_filter_error'] = getattr(self, 'amenity_filter_error', None)
        if context['amenity_filter_error']:
            messages.error(self.request, context['amenity_filter_error'])
        return context


class PropertyDetailView(DetailView):
    """Property detail view"""
    model = Property
    template_name = 'rentals/property_detail.html'
    context_object_name = 'property'
    
    def get_queryset(self):
        return property_listing_queryset(
            Property.objects.filter(is_published=True)
        ).prefetch_related('rules')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        property_obj = self.get_object()
        user = self.request.user

        context['is_occupied'] = property_obj.is_occupied
        context['is_own_listing'] = user.is_authenticated and user.pk == property_obj.host_id
        context['can_apply'] = (
            property_obj.is_available
            and not property_obj.is_occupied
            and not context['is_own_listing']
            and not property_has_confirmed_tenant(property_obj)
        )

        if user.is_authenticated:
            context['in_wishlist'] = Wishlist.objects.filter(
                user=user,
                property=property_obj,
            ).exists()
            context['user_booking'] = (
                Booking.objects.filter(property=property_obj, guest=user)
                .exclude(status__in=['declined', 'cancelled'])
                .order_by('-created_at')
                .first()
            )
        else:
            context['user_booking'] = None

        related_properties = (
            Property.objects.filter(
                city=property_obj.city,
                is_published=True,
                is_available=True,
                is_occupied=False,
            )
            .exclude(id=property_obj.id)
            .select_related('host')
            .prefetch_related('images')[:4]
        )

        context['related_properties'] = related_properties
        context['gallery_images'] = property_obj.get_available_images()
        context['gallery_image_urls'] = [
            img.image.url for img in context['gallery_images']
        ]
        context['missing_gallery_count'] = (
            property_obj.images.count() - len(context['gallery_images'])
        )

        return context


class PropertyCreateView(LoginRequiredMixin, CreateView):
    """Create new property listing"""
    model = Property
    form_class = PropertyForm
    template_name = 'rentals/property_form.html'

    def dispatch(self, request, *args, **kwargs):
        if not user_can_create_listing(request.user):
            cap = get_max_active_listings(request.user)
            messages.error(
                request,
                f'You have reached your limit of {cap} active listings. '
                'Remove or unpublish a listing, or upgrade your account, to add more.',
            )
            return redirect('rentals:my_listings')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['photo_limit'] = get_photo_limit(user)
        context['can_upload_video'] = user_can_upload_video(user)
        context['has_full_listing_access'] = user_has_full_listing_access(user)
        context['is_premium'] = user_has_full_listing_access(user)
        context.update(_listing_form_nav_context(user))
        context.update(listing_video_upload_context())
        context['current_photo_count'] = 0
        context['existing_images'] = []
        context.update(_listing_amenity_context(context['form'], None))
        if context.get('form') and context['form'].errors:
            context.update(listing_form_error_context(context['form']))
        return context

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Some required details are missing or incorrect — see the alert below and jump to each section.',
        )
        if self.request.FILES:
            messages.warning(
                self.request,
                'Photos or video you selected were not kept — please add them again after fixing the errors.',
            )
        return super().form_invalid(form)

    def get_initial(self):
        initial = super().get_initial()
        initial.setdefault('lease_type', 'monthly')
        initial.setdefault('payment_preference', 'platform')
        initial.setdefault('bedrooms', 0)
        initial.setdefault('max_occupants', 1)
        initial.setdefault('bathrooms', 1)
        return initial

    def get_success_url(self):
        return reverse('rentals:my_listings')

    def _save_uploaded_images(self, prop):
        files = self.request.FILES.getlist('property_images')
        if not files:
            return
        limit = get_photo_limit(self.request.user)
        primary_raw = self.request.POST.get('primary_image_index', '')
        try:
            primary_index = int(primary_raw) if primary_raw != '' else 0
        except ValueError:
            primary_index = 0
        with transaction.atomic():
            prop = Property.objects.select_for_update().get(pk=prop.pk)
            room = limit - prop.images.count()
            if room <= 0:
                messages.warning(
                    self.request,
                    f'Photo limit reached ({limit} for your plan). Extra photos were not added.',
                )
                return
            files = files[:room]
            if primary_index < 0 or primary_index >= len(files):
                primary_index = 0
            prop.images.update(is_primary=False)
            for i, f in enumerate(files):
                PropertyImage.objects.create(
                    property=prop,
                    image=f,
                    is_primary=(i == primary_index),
                )

    def form_valid(self, form):
        form.instance.host = self.request.user
        form.instance.is_published = True
        form.instance.listing_terms_accepted_at = timezone.now()
        if not form.instance.deposit_amount:
            form.instance.deposit_amount = form.instance.secure_space_amount or Decimal('0')
        response = super().form_valid(form)
        self._save_uploaded_images(self.object)
        invalidate_browse_cache()
        user = self.request.user
        if not user.is_host:
            user.is_host = True
            user.save(update_fields=['is_host', 'updated_at'])
        if self.request.FILES.getlist('property_images'):
            messages.success(self.request, 'Your listing is live. Renters can message you on Qasha.')
        else:
            messages.success(
                self.request,
                'Your listing is live without photos. Open Your listings → Edit to add photos anytime.',
            )
        return response


class PropertyUpdateView(LoginRequiredMixin, UpdateView):
    """Update property listing"""
    model = Property
    form_class = PropertyForm
    template_name = 'rentals/property_form.html'

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_queryset(self):
        return Property.objects.filter(host=self.request.user).prefetch_related('images')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['photo_limit'] = get_photo_limit(user)
        context['can_upload_video'] = user_can_upload_video(user)
        context['has_full_listing_access'] = user_has_full_listing_access(user)
        context['is_premium'] = user_has_full_listing_access(user)
        context.update(_listing_form_nav_context(user))
        context.update(listing_video_upload_context())
        if self.object:
            context['current_photo_count'] = self.object.images.count()
            existing = list(self.object.images.all().order_by('-is_primary', 'created_at'))
            context['existing_images'] = existing
            context['missing_image_count'] = sum(1 for img in existing if not img.has_file())
            context['video_file_missing'] = bool(
                self.object.video and not self.object.has_video_file()
            )
        else:
            context['current_photo_count'] = 0
            context['existing_images'] = []
            context['missing_image_count'] = 0
            context['video_file_missing'] = False
        context.update(_listing_amenity_context(context['form'], self.object))
        if context.get('form') and context['form'].errors:
            context.update(listing_form_error_context(context['form']))
        return context

    def form_invalid(self, form):
        messages.error(
            self.request,
            'Some required details are missing or incorrect — see the alert below and jump to each section.',
        )
        if self.request.FILES:
            messages.warning(
                self.request,
                'Photos or video you selected were not kept — please add them again after fixing the errors.',
            )
        if self.request.POST.getlist('remove_image_ids') or self.request.POST.get('remove_video') == '1':
            messages.info(
                self.request,
                'Photo/video removals are only saved when the form passes validation. '
                'Fix the errors below, or use “Remove all missing media” for broken files only.',
            )
        return super().form_invalid(form)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        if request.POST.get('action') == 'purge_missing_media':
            removed = self._purge_missing_media(self.object)
            if removed:
                messages.success(
                    request,
                    f'Removed {removed} broken media record(s). Upload new photos or video below.',
                )
            else:
                messages.info(request, 'No broken media records were found on this listing.')
            return redirect(self.get_success_url())
        return super().post(request, *args, **kwargs)

    def _purge_missing_media(self, prop):
        """Delete DB rows (and disk files) for photos/video whose files are gone."""
        removed = 0
        for img in list(prop.images.all()):
            if not img.has_file():
                if img.image:
                    img.image.delete(save=False)
                img.delete()
                removed += 1
        if prop.video and not stored_media_exists(prop.video):
            prop.video.delete(save=False)
            prop.video = None
            prop.save(update_fields=['video', 'updated_at'])
            removed += 1
        return removed

    def _apply_primary_image_choice(self, prop):
        primary_id = self.request.POST.get('primary_image_id')
        if not primary_id:
            return
        try:
            img = prop.images.get(pk=int(primary_id))
        except (PropertyImage.DoesNotExist, ValueError):
            return
        prop.images.update(is_primary=False)
        img.is_primary = True
        img.save(update_fields=['is_primary'])

    def _save_uploaded_images(self, prop):
        files = self.request.FILES.getlist('property_images')
        if not files:
            self._apply_primary_image_choice(prop)
            return
        limit = get_photo_limit(self.request.user)
        primary_raw = self.request.POST.get('primary_image_index', '0')
        try:
            primary_index = int(primary_raw)
        except ValueError:
            primary_index = 0
        with transaction.atomic():
            prop = Property.objects.select_for_update().get(pk=prop.pk)
            room = limit - prop.images.count()
            if room <= 0:
                messages.warning(
                    self.request,
                    f'Photo limit reached ({limit} for your plan). Extra photos were not added.',
                )
                self._apply_primary_image_choice(prop)
                return
            files = files[:room]
            primary_index = max(0, min(primary_index, len(files) - 1))
            chosen_pk = None
            for i, f in enumerate(files):
                img = PropertyImage.objects.create(property=prop, image=f, is_primary=False)
                if i == primary_index:
                    chosen_pk = img.pk
            if chosen_pk:
                prop.images.update(is_primary=False)
                PropertyImage.objects.filter(pk=chosen_pk).update(is_primary=True)
            if self.request.POST.get('primary_image_id'):
                self._apply_primary_image_choice(prop)
            elif not chosen_pk:
                self._apply_primary_image_choice(prop)

    def _remove_marked_images(self, prop):
        raw_ids = self.request.POST.getlist('remove_image_ids')
        if not raw_ids:
            return
        ids = []
        for raw in raw_ids:
            try:
                ids.append(int(raw))
            except ValueError:
                continue
        if not ids:
            return
        for img in prop.images.filter(pk__in=ids):
            if img.image:
                img.image.delete(save=False)
            img.delete()

    def _remove_video_if_requested(self, prop):
        if self.request.POST.get('remove_video') != '1':
            return
        if self.request.FILES.get('video'):
            return
        if prop.video:
            prop.video.delete(save=False)
        prop.video = None
        prop.save(update_fields=['video', 'updated_at'])

    def form_valid(self, form):
        if not form.instance.deposit_amount:
            form.instance.deposit_amount = form.instance.secure_space_amount or Decimal('0')
        prop = self.object
        self._remove_marked_images(prop)
        self._remove_video_if_requested(prop)
        response = super().form_valid(form)
        self._save_uploaded_images(self.object)
        invalidate_browse_cache()
        messages.success(self.request, 'Your listing was updated.')
        return response

    def get_success_url(self):
        return reverse('rentals:property_update', kwargs={'pk': self.object.pk})


@login_required
def my_listings(request):
    properties = (
        Property.objects.filter(host=request.user)
        .prefetch_related('images')
        .order_by('-created_at')
    )
    return render(request, 'rentals/my_listings.html', {'properties': properties})


@login_required
@require_POST
def property_delete(request, pk):
    prop = get_object_or_404(Property, pk=pk, host=request.user)
    prop.delete()
    messages.success(request, 'Your listing was removed.')
    return redirect('rentals:my_listings')


@login_required
@require_POST
def property_toggle_available(request, pk):
    prop = get_object_or_404(Property, pk=pk, host=request.user)
    prop.is_available = not prop.is_available
    prop.save(update_fields=['is_available', 'updated_at'])
    if prop.is_available:
        messages.success(request, 'Your place is now shown as available.')
    else:
        messages.success(request, 'Your place is now hidden from search (not available).')
    return safe_redirect(request, request.POST.get('next'), 'rentals:my_listings')


@login_required
@require_POST
def set_primary_image(request, property_id, image_id):
    prop = get_object_or_404(Property, pk=property_id, host=request.user)
    img = get_object_or_404(PropertyImage, pk=image_id, property=prop)
    prop.images.update(is_primary=False)
    img.is_primary = True
    img.save(update_fields=['is_primary'])
    messages.success(request, 'This photo will show on the timeline.')
    return safe_redirect(
        request,
        request.POST.get('next'),
        'rentals:property_update',
        kwargs={'pk': property_id},
    )


def _message_subject(property_obj=None):
    if property_obj:
        return f"About: {property_obj.title}"[:200]
    return "Message on Qasha"


def _listing_amenity_context(form, property_obj=None):
    """Selected amenity IDs and custom lines for the listing form."""
    from .amenity_utils import MAX_AMENITIES

    selected = set()
    custom_text = ''
    if form.is_bound:
        for raw in form.data.getlist('amenities'):
            try:
                selected.add(int(raw))
            except (TypeError, ValueError):
                pass
        custom_text = form.data.get('custom_amenities', '')
    elif property_obj and property_obj.pk:
        linked = property_obj.property_amenities.select_related('amenity')
        selected = {pa.amenity_id for pa in linked if not pa.amenity.is_custom}
        custom_text = '\n'.join(pa.amenity.name for pa in linked if pa.amenity.is_custom)
    return {
        'selected_amenity_ids': selected,
        'custom_amenities_initial': custom_text,
        'max_amenities_total': MAX_AMENITIES,
        'max_custom_amenities': MAX_AMENITIES,
    }


def _listing_form_nav_context(user):
    """Counts for quick links on the list-property form."""
    return {
        'listing_count': Property.objects.filter(host=user).count(),
        'wishlist_count': Wishlist.objects.filter(user=user).count(),
        'my_applications_count': Booking.objects.filter(guest=user)
        .exclude(status__in=['declined', 'cancelled'])
        .count(),
        'pending_host_count': Booking.objects.filter(
            property__host=user,
            status='pending',
        ).count(),
    }


@login_required
def my_hub(request):
    """Hub for listings, saved places, applications, and account tools."""
    pending_host = Booking.objects.filter(
        property__host=request.user,
        status='pending',
    ).count()
    return render(
        request,
        'rentals/my_hub.html',
        {
            'listing_count': Property.objects.filter(host=request.user).count(),
            'wishlist_count': Wishlist.objects.filter(user=request.user).count(),
            'my_applications_count': Booking.objects.filter(guest=request.user).exclude(
                status__in=['declined', 'cancelled']
            ).count(),
            'pending_host_count': pending_host,
        },
    )


@login_required
def promotions_hub(request):
    """Featured listings and host verification."""
    from users.tiers import FREE_MAX_PHOTOS, PREMIUM_MAX_PHOTOS, PREMIUM_MAX_VIDEO_SECONDS

    properties = (
        Property.objects.filter(host=request.user)
        .prefetch_related('images')
        .order_by('-created_at')
    )
    return render(
        request,
        'rentals/promotions.html',
        {
            'properties': properties,
            'featured_plans': FEATURED_PLANS,
            'verification_tiers': VERIFICATION_TIERS,
            'free_plan': FREE_ACCOUNT_PLAN,
            'featured_listing_help': FEATURED_LISTING_HELP,
            'free_max_photos': FREE_MAX_PHOTOS,
            'premium_max_photos': PREMIUM_MAX_PHOTOS,
            'premium_max_video_minutes': PREMIUM_MAX_VIDEO_SECONDS // 60,
        },
    )


@login_required
def promote_listing(request, pk):
    """Pay on Qasha to feature one listing."""
    prop = get_object_or_404(Property, pk=pk, host=request.user)
    payment_form = BookingPaymentForm()
    selected_plan = request.GET.get('plan', '') or request.POST.get('plan', '')

    if request.method == 'POST' and request.POST.get('action') == 'pay_featured':
        plan = request.POST.get('plan', '')
        if plan not in FEATURED_PLANS:
            messages.error(request, 'Please choose a featured plan.')
        else:
            payment_form = BookingPaymentForm(request.POST)
            if payment_form.is_valid():
                idem = payment_token('featured', request.user.pk, prop.pk, plan)
                if not begin_payment_idempotency(request, idem):
                    if prop.is_featured_active():
                        messages.info(request, 'This listing is already featured.')
                    else:
                        messages.info(
                            request,
                            'This payment was already submitted. Refresh the page in a moment.',
                        )
                    return redirect('rentals:promotions')
                try:
                    was_featured = prop.is_featured_active()
                    ref = charge_featured_listing(
                        prop,
                        plan,
                        card_last4=payment_form.cleaned_data['card_last4'],
                        cardholder_name=payment_form.cleaned_data['cardholder_name'],
                    )
                    complete_payment_idempotency(request, idem)
                    plan_info = FEATURED_PLANS[plan]
                    action = 'extended' if was_featured else 'featured'
                    messages.success(
                        request,
                        f'Payment received (ref {ref}). "{prop.title}" is {action} for {plan_info["label"]}.',
                    )
                    return redirect('rentals:promotions')
                except ValueError as exc:
                    abort_payment_idempotency(idem)
                    messages.error(request, str(exc))
            else:
                messages.error(request, 'Please fix the card details below.')
            selected_plan = plan

    elif request.method == 'POST':
        plan = request.POST.get('plan', '')
        if plan in FEATURED_PLANS:
            selected_plan = plan

    plan_info = FEATURED_PLANS.get(selected_plan) if selected_plan in FEATURED_PLANS else None

    return render(
        request,
        'rentals/promote_listing.html',
        {
            'property': prop,
            'featured_plans': FEATURED_PLANS,
            'selected_plan': selected_plan,
            'plan_info': plan_info,
            'payment_form': payment_form,
        },
    )


@login_required
def wishlist_view(request):
    """View and manage saved places."""
    items = (
        Wishlist.objects.filter(user=request.user)
        .select_related('property', 'property__host')
        .prefetch_related('property__images')
        .order_by('-created_at')
    )
    return render(request, 'rentals/wishlist.html', {'wishlist_items': items})


@login_required
@require_POST
def add_to_wishlist(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id, is_published=True)
    if property_obj.host_id == request.user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in (
            request.headers.get('Accept', '')
        ):
            return JsonResponse({'success': False, 'message': 'You cannot save your own listing.'}, status=400)
        messages.error(request, 'You cannot save your own listing.')
        return redirect('rentals:property_detail', pk=property_id)

    _, created = Wishlist.objects.get_or_create(user=request.user, property=property_obj)
    message = 'Saved to your wishlist.' if created else 'Already in your wishlist.'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in (
        request.headers.get('Accept', '')
    ):
        return JsonResponse({'success': True, 'message': message, 'in_wishlist': True})

    messages.success(request, message)
    return safe_redirect(request, request.POST.get('next'), 'rentals:wishlist')


@login_required
@require_POST
def remove_from_wishlist(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id)
    deleted, _ = Wishlist.objects.filter(user=request.user, property=property_obj).delete()
    message = 'Removed from your wishlist.' if deleted else 'That place was not in your wishlist.'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in (
        request.headers.get('Accept', '')
    ):
        return JsonResponse({'success': True, 'message': message, 'in_wishlist': False})

    messages.success(request, message)
    return safe_redirect(request, request.POST.get('next'), 'rentals:wishlist')


def _booking_draft_session_key(property_id):
    return f'booking_draft_{property_id}'


def _save_booking_draft(request, property_id, check_in, check_out, special_requests):
    request.session[_booking_draft_session_key(property_id)] = {
        'check_in': check_in.isoformat(),
        'check_out': check_out.isoformat() if check_out else '',
        'special_requests': special_requests or '',
    }
    request.session.modified = True
    try:
        request.session.save()
    except AttributeError:
        pass


def _get_booking_draft(request, property_id):
    return request.session.get(_booking_draft_session_key(property_id))


def _clear_booking_draft(request, property_id):
    request.session.pop(_booking_draft_session_key(property_id), None)
    request.session.modified = True


@login_required
def create_booking(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id, is_published=True)

    if property_obj.host_id == request.user.id:
        messages.error(request, 'You cannot apply to your own listing.')
        return redirect('rentals:property_detail', pk=property_id)

    if property_obj.is_occupied or not property_obj.is_available:
        messages.error(request, 'This place is not open for new applications right now.')
        return redirect('rentals:property_detail', pk=property_id)

    if property_has_confirmed_tenant(property_obj):
        messages.error(request, 'This place is not open for new applications right now.')
        return redirect('rentals:property_detail', pk=property_id)

    uses_platform_payment = uses_qasha_payment(property_obj)
    securing_amount = get_securing_amount(property_obj)

    if uses_platform_payment and securing_amount <= 0:
        messages.error(
            request,
            'This listing does not have a securing amount set. Ask the owner to update their listing.',
        )
        return redirect('rentals:property_detail', pk=property_id)

    book_url = reverse('rentals:create_booking', kwargs={'property_id': property_id})
    step = int(request.GET.get('step', 1)) if uses_platform_payment else 1

    # —— Direct payment: one step (dates only) ——
    if not uses_platform_payment:
        if request.method == 'POST':
            form = BookingForm(request.POST, property_obj=property_obj)
            if form.is_valid():
                check_in = form.cleaned_data['check_in_date']
                check_out = form.cleaned_data.get('check_out_date') or default_check_out(
                    property_obj, check_in
                )
                with transaction.atomic():
                    property_obj = Property.objects.select_for_update().get(pk=property_id)
                    if (
                        not property_obj.is_available
                        or property_obj.is_occupied
                        or property_has_confirmed_tenant(property_obj)
                    ):
                        messages.error(
                            request,
                            'This place is not open for new applications right now.',
                        )
                        return redirect('rentals:property_detail', pk=property_id)
                    if _duplicate_pending_booking(
                        request.user, property_obj, check_in, check_out
                    ):
                        messages.info(
                            request,
                            'You already have a pending application that overlaps these dates.',
                        )
                        return redirect('rentals:my_applications')
                    booking = form.save(commit=False)
                    booking.property = property_obj
                    booking.guest = request.user
                    booking.check_out_date = check_out
                    booking.total_amount = Decimal('0')
                    booking.status = 'pending'
                    booking.save()
                messages.success(
                    request,
                    'Booking request sent. The owner will accept or decline on Qasha.',
                )
                return redirect('rentals:my_applications')
        else:
            form = BookingForm(property_obj=property_obj)
        return render(
            request,
            'rentals/booking_form.html',
            {
                'form': form,
                'property': property_obj,
                'uses_platform_payment': False,
                'booking_step': 1,
            },
        )

    # —— Platform payment: step 1 dates → step 2 authorize payment ——
    draft = _get_booking_draft(request, property_id)

    if request.method == 'GET' and step == 2 and not draft:
        messages.warning(request, 'Choose your dates first, then authorize payment.')
        return redirect(book_url)

    if request.method == 'POST' and request.POST.get('booking_step') == '1':
        form = BookingForm(request.POST, property_obj=property_obj)
        if form.is_valid():
            check_in = form.cleaned_data['check_in_date']
            check_out = form.cleaned_data.get('check_out_date') or default_check_out(
                property_obj, check_in
            )
            _save_booking_draft(
                request,
                property_id,
                check_in,
                check_out,
                form.cleaned_data.get('special_requests', ''),
            )
            return redirect(f'{book_url}?step=2')
        return render(
            request,
            'rentals/booking_form.html',
            {
                'form': form,
                'property': property_obj,
                'uses_platform_payment': True,
                'securing_amount': securing_amount,
                'booking_step': 1,
            },
        )

    if request.method == 'POST' and request.POST.get('booking_step') == '2':
        payment_form = BookingPaymentForm(request.POST)
        draft = _get_booking_draft(request, property_id)
        if not draft or not draft.get('check_in'):
            messages.error(
                request,
                'Your booking session expired. Please choose your dates again.',
            )
            return redirect(book_url)
        if payment_form.is_valid():
            try:
                check_in = datetime.strptime(draft['check_in'], '%Y-%m-%d').date()
            except ValueError:
                messages.error(request, 'Invalid dates. Please start again from step 1.')
                return redirect(book_url)
            check_out = (
                datetime.strptime(draft['check_out'], '%Y-%m-%d').date()
                if draft.get('check_out')
                else default_check_out(property_obj, check_in)
            )
            try:
                validate_booking_dates(property_obj, check_in, check_out)
            except ValidationError as exc:
                messages.error(request, exc.messages[0])
                return redirect(book_url)
            idem = payment_token(
                'booking', request.user.pk, property_id, check_in.isoformat(), check_out.isoformat()
            )
            if not begin_payment_idempotency(request, idem):
                messages.info(request, 'This booking was already submitted.')
                return redirect('rentals:my_applications')
            try:
                with transaction.atomic():
                    property_obj = Property.objects.select_for_update().get(pk=property_id)
                    if (
                        not property_obj.is_available
                        or property_obj.is_occupied
                        or property_has_confirmed_tenant(property_obj)
                    ):
                        abort_payment_idempotency(idem)
                        messages.error(
                            request,
                            'This place is not open for new applications right now.',
                        )
                        return redirect('rentals:property_detail', pk=property_id)
                    if _duplicate_pending_booking(
                        request.user, property_obj, check_in, check_out
                    ):
                        abort_payment_idempotency(idem)
                        messages.info(
                            request,
                            'You already have a pending application that overlaps these dates.',
                        )
                        return redirect('rentals:my_applications')
                    booking = Booking(
                        property=property_obj,
                        guest=request.user,
                        check_in_date=check_in,
                        check_out_date=check_out,
                        special_requests=draft.get('special_requests', ''),
                        total_amount=securing_amount,
                        status='pending',
                        payment_on_file=True,
                        payment_cardholder_name=payment_form.cleaned_data['cardholder_name'],
                        payment_card_last4=payment_form.cleaned_data['card_last4'],
                    )
                    booking.save()
                    authorize_booking_payment(booking)
                complete_payment_idempotency(request, idem)
                _clear_booking_draft(request, property_id)
                messages.success(
                    request,
                    f'Booking request sent. {securing_amount} is authorized on your card (hold only — not charged). '
                    'If the owner accepts, payment is captured automatically. If they decline, the hold is released.',
                )
                return redirect('rentals:my_applications')
            except ValueError:
                abort_payment_idempotency(idem)
                messages.error(
                    request,
                    'Payment authorization failed. Please check your card details and try again.',
                )
                return redirect(book_url)
        messages.error(request, 'Please fix the payment details below.')
        return render(
            request,
            'rentals/booking_form.html',
            {
                'payment_form': payment_form,
                'property': property_obj,
                'uses_platform_payment': True,
                'securing_amount': securing_amount,
                'booking_step': 2,
                'draft': draft,
            },
        )

    if step == 2:
        return render(
            request,
            'rentals/booking_form.html',
            {
                'payment_form': BookingPaymentForm(),
                'property': property_obj,
                'uses_platform_payment': True,
                'securing_amount': securing_amount,
                'booking_step': 2,
                'draft': draft,
            },
        )

    form = BookingForm(property_obj=property_obj)
    if draft:
        try:
            form.initial['check_in_date'] = datetime.strptime(draft['check_in'], '%Y-%m-%d').date()
            if draft.get('check_out'):
                form.initial['check_out_date'] = datetime.strptime(
                    draft['check_out'], '%Y-%m-%d'
                ).date()
            form.initial['special_requests'] = draft.get('special_requests', '')
        except ValueError:
            pass

    return render(
        request,
        'rentals/booking_form.html',
        {
            'form': form,
            'property': property_obj,
            'uses_platform_payment': True,
            'securing_amount': securing_amount,
            'booking_step': 1,
        },
    )


@login_required
def my_applications(request):
    applications = (
        Booking.objects.filter(guest=request.user)
        .select_related('property', 'property__host')
        .order_by('-created_at')
    )
    return render(request, 'rentals/my_applications.html', {'applications': applications})


@login_required
def host_applications(request):
    applications = (
        Booking.objects.filter(property__host=request.user)
        .select_related('property', 'guest')
        .order_by('-created_at')
    )
    return render(request, 'rentals/host_applications.html', {'applications': applications})


@login_required
@require_POST
def booking_accept(request, booking_id):
    host_note = request.POST.get('host_note', '')[:500]
    accepted_booking = None

    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id,
            property__host=request.user,
        )
        if booking.status != 'pending':
            messages.error(request, 'This application is no longer pending.')
        else:
            prop = Property.objects.select_for_update().get(pk=booking.property_id)
            other_holds = Booking.objects.filter(
                property=prop,
                status__in=('accepted', 'secured'),
            ).exclude(pk=booking.pk)
            if prop.is_occupied or other_holds.exists():
                messages.error(
                    request,
                    'This place already has a confirmed tenant. Decline this application instead.',
                )
            else:
                booking.host_note = host_note
                if uses_qasha_payment(prop):
                    if not booking.payment_on_file:
                        messages.error(
                            request,
                            'This tenant has no payment on file. '
                            'They must complete the card step before you can accept on Qasha.',
                        )
                    else:
                        try:
                            if booking.payment_auth_status != 'authorized':
                                authorize_booking_payment(booking)
                            capture_booking_payment(booking)
                            booking.save(update_fields=['host_note', 'updated_at'])
                            decline_other_pending_bookings(prop, booking.pk)
                            accepted_booking = booking
                            messages.success(
                                request,
                                f'Booking confirmed. Payment of {booking.total_amount} captured from '
                                f'{booking.guest.get_full_name() or booking.guest.username}\'s card '
                                f'(•••• {booking.payment_card_last4}). '
                                'The tenant was notified in Messages.',
                            )
                        except ValueError:
                            release_booking_authorization(booking)
                            booking.status = 'pending'
                            booking.save(update_fields=['status', 'host_note', 'updated_at'])
                            messages.error(
                                request,
                                'Payment could not be captured. The tenant was not confirmed — '
                                'ask them to check their card and apply again.',
                            )
                else:
                    booking.status = 'accepted'
                    booking.save(update_fields=['status', 'host_note', 'updated_at'])
                    mark_property_occupied(prop)
                    decline_other_pending_bookings(prop, booking.pk)
                    accepted_booking = booking
                    messages.success(
                        request,
                        'Application accepted. The tenant was notified in Messages.',
                    )

    if accepted_booking:
        notify_guest_booking_accepted(accepted_booking)
    return redirect('rentals:host_applications')


@login_required
@require_POST
def booking_decline(request, booking_id):
    host_note = request.POST.get('host_note', '')[:500]
    declined = False
    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id,
            property__host=request.user,
        )
        if booking.status != 'pending':
            messages.error(request, 'This application is no longer pending.')
        else:
            release_booking_authorization(booking)
            booking.status = 'declined'
            booking.host_note = host_note
            booking.save(update_fields=['status', 'host_note', 'updated_at'])
            declined = True
    if declined:
        notify_guest_booking_declined(booking)
        messages.info(
            request,
            'Booking request declined. The tenant was notified in Messages.',
        )
    return redirect('rentals:host_applications')


@login_required
def booking_pay(request, booking_id):
    """Legacy URL — payment is collected at application and charged when the host accepts."""
    booking = get_object_or_404(Booking, pk=booking_id, guest=request.user)
    if booking.status == 'secured':
        messages.info(request, 'This booking is already paid and secured on Qasha.')
    elif booking.is_payment_authorized():
        messages.info(
            request,
            'Your payment is on file. The owner will accept or decline your application — '
            'you are charged only if they accept.',
        )
    elif booking.status == 'pending':
        messages.info(
            request,
            'Add your payment details on the application form. You are charged automatically when the owner accepts.',
        )
        return redirect('rentals:create_booking', property_id=booking.property_id)
    else:
        messages.info(request, 'No payment is required for this application.')
    return redirect('rentals:my_applications')


@login_required
@require_POST
def booking_cancel(request, booking_id):
    cancelled = False
    cancelled_by_host = False
    was_captured = False
    with transaction.atomic():
        booking = get_object_or_404(Booking.objects.select_for_update(), pk=booking_id)
        if booking.guest_id != request.user.id and booking.property.host_id != request.user.id:
            messages.error(request, 'You cannot cancel this application.')
        elif booking.status not in ('pending', 'accepted', 'secured'):
            messages.error(request, 'This application can no longer be cancelled.')
        elif booking.status == 'secured' and booking.payment_auth_status == 'captured':
            messages.error(
                request,
                'Paid bookings cannot be cancelled here. Use Help to request a refund.',
            )
        else:
            release_booking_authorization(booking)
            was_captured = booking.payment_auth_status == 'captured'
            booking.status = 'cancelled'
            booking.save(update_fields=['status', 'updated_at'])
            clear_property_occupancy_if_no_tenant(booking.property, except_booking_id=booking.pk)
            cancelled_by_host = booking.property.host_id == request.user.id
            cancelled = True
    if not cancelled:
        return redirect('rentals:my_hub')
    invalidate_browse_cache()
    if cancelled_by_host:
        notify_guest_booking_cancelled_by_host(booking)
    if was_captured:
        messages.info(
            request,
            'Booking cancelled and the listing is open again.'
            + (' The tenant was notified in Messages.' if cancelled_by_host else '')
            + ' Contact support if a refund is needed.',
        )
    elif booking.payment_auth_status == 'released':
        messages.info(
            request,
            'Booking request cancelled. Card authorization released — no charge was made.'
            + (' The tenant was notified in Messages.' if cancelled_by_host else ''),
        )
    else:
        messages.info(
            request,
            'Booking request cancelled.'
            + (' The tenant was notified in Messages.' if cancelled_by_host else ''),
        )
    if cancelled_by_host:
        return redirect('rentals:host_applications')
    return redirect('rentals:my_applications')


@login_required
@require_POST
def property_toggle_occupied(request, pk):
    prop = get_object_or_404(Property, pk=pk, host=request.user)
    if prop.is_occupied:
        if property_has_active_booking(prop):
            messages.error(
                request,
                'You still have an accepted or confirmed tenant on this listing. '
                'Decline or cancel that booking before marking the place vacant.',
            )
            return safe_redirect(request, request.POST.get('next'), 'rentals:my_listings')
        prop.is_occupied = False
        prop.is_available = True
        messages.success(request, 'Marked as vacant and open for new applications.')
    else:
        prop.is_occupied = True
        prop.is_available = False
        messages.success(request, 'Marked as occupied. It is hidden from browse until you mark it vacant.')
    prop.save(update_fields=['is_occupied', 'is_available', 'updated_at'])
    invalidate_browse_cache()
    return safe_redirect(request, request.POST.get('next'), 'rentals:my_listings')


@login_required
def send_message(request, property_id):
    property_obj = get_object_or_404(Property, id=property_id, is_published=True)

    if property_obj.host_id == request.user.id:
        messages.error(request, 'You cannot message yourself on your own listing.')
        return redirect('rentals:property_detail', pk=property_id)

    if not _may_contact_host_about_listing(request.user, property_obj):
        messages.error(
            request,
            'Send a booking request first, or continue an existing conversation from Messages.',
        )
        return redirect('rentals:property_detail', pk=property_id)

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.recipient = property_obj.host
            msg.property = property_obj
            msg.subject = _message_subject(property_obj)
            msg.save()
            messages.success(request, 'Your message was sent.')
            return redirect(
                f'{reverse("rentals:message_thread", kwargs={"other_user_id": property_obj.host_id})}'
                f'?property={property_obj.pk}',
            )
    else:
        form = MessageForm()

    return render(
        request,
        'rentals/message_form.html',
        {'form': form, 'property': property_obj},
    )


@login_required
def message_inbox(request):
    threads = _inbox_threads(request.user)
    return render(
        request,
        'rentals/message_inbox.html',
        {'threads': threads},
    )


@login_required
def message_thread(request, other_user_id):
    other = get_object_or_404(User, pk=other_user_id)
    if other.pk == request.user.pk:
        messages.error(request, 'You cannot message yourself.')
        return redirect('rentals:message_inbox')

    thread_qs = _thread_messages(request.user, other)
    if not _users_may_message(request.user, other):
        messages.error(request, 'You can only message people you have a booking or conversation with.')
        return redirect('rentals:message_inbox')

    if request.method == 'POST':
        form = MessageForm(request.POST)
        if form.is_valid():
            msg = form.save(commit=False)
            msg.sender = request.user
            msg.recipient = other
            last_with_prop = thread_qs.exclude(property__isnull=True).last()
            msg.property = last_with_prop.property if last_with_prop else None
            msg.subject = _message_subject(msg.property)
            msg.save()
            messages.success(request, 'Message sent.')
            prop_q = request.GET.get('property', '')
            url = reverse('rentals:message_thread', kwargs={'other_user_id': other.pk})
            if prop_q:
                url = f'{url}?property={prop_q}'
            return redirect(url)
    else:
        form = MessageForm()

    thread_messages = list(thread_qs)
    now = timezone.now()
    Message.objects.filter(
        pk__in=thread_qs.filter(recipient=request.user, is_read=False).values_list('pk', flat=True)
    ).update(is_read=True, read_at=now)
    thread_messages = list(thread_qs)

    return render(
        request,
        'rentals/message_thread.html',
        {
            'other_user': other,
            'thread_messages': thread_messages,
            'form': form,
            'thread_property_id': request.GET.get('property', ''),
        },
    )


@login_required
def add_review(request, property_id):
    """Private feedback — host and moderation only."""
    property_obj = get_object_or_404(Property, id=property_id, is_published=True)

    if property_obj.host_id == request.user.id:
        messages.error(request, 'You cannot send feedback on your own listing.')
        return redirect('rentals:property_detail', pk=property_id)

    has_stay = Booking.objects.filter(
        property=property_obj,
        guest=request.user,
        status__in=['accepted', 'secured', 'completed'],
    ).exists()
    if not has_stay:
        messages.error(
            request,
            'Private feedback is only available after you have an accepted or confirmed booking for this place.',
        )
        return redirect('rentals:property_detail', pk=property_id)

    existing = Review.objects.filter(property=property_obj, reviewer=request.user).first()

    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=existing)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.property = property_obj
            feedback.reviewer = request.user
            feedback.is_public = False
            feedback.save()
            messages.success(
                request,
                'Thank you. Your feedback was sent privately to the owner and Qasha.',
            )
            return redirect('rentals:property_detail', pk=property_id)
    else:
        form = ReviewForm(instance=existing)

    return render(
        request,
        'rentals/feedback_form.html',
        {'form': form, 'property': property_obj, 'existing_feedback': existing},
    )


@login_required
def host_feedback(request):
    """Private feedback from tenants on the host's listings."""
    feedback_list = (
        Review.objects.filter(property__host=request.user)
        .select_related('property', 'reviewer')
        .order_by('-created_at')
    )
    return render(request, 'rentals/host_feedback.html', {'feedback_list': feedback_list})