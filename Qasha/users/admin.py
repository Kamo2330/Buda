from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404, redirect
from django.urls import path, reverse
from django.utils.html import format_html
from django.views.decorators.http import require_POST

from rentals.models import Property
from rentals.promotions import (
    approve_host_verification,
    gift_featured_for_host,
    grant_host_verification,
    reject_host_verification,
    revoke_host_verification,
)

from .models import User, UserProfile


@admin.action(description='✓ Approve verification after payment / query')
def approve_pending_verification(modeladmin, request, queryset):
    count = 0
    for user in queryset:
        if user.host_verification_status != 'pending':
            continue
        tier = user.host_verification_requested_tier or user.host_verification_tier or 'landlord'
        if tier not in ('landlord', 'agency'):
            tier = 'landlord'
        approve_host_verification(user, tier)
        count += 1
    if count:
        modeladmin.message_user(request, f'Verified {count} user(s).', messages.SUCCESS)


@admin.action(description='🎁 FREE verify as Landlord (query / promotion)')
def gift_landlord_verification(modeladmin, request, queryset):
    for user in queryset:
        grant_host_verification(user, 'landlord')
    modeladmin.message_user(
        request,
        f'Free landlord verification granted to {queryset.count()} user(s).',
        messages.SUCCESS,
    )


@admin.action(description='🎁 FREE verify as Agency (query / promotion)')
def gift_agency_verification(modeladmin, request, queryset):
    for user in queryset:
        grant_host_verification(user, 'agency')
    modeladmin.message_user(
        request,
        f'Free agency verification granted to {queryset.count()} user(s).',
        messages.SUCCESS,
    )


@admin.action(description='🎁 FREE featured 7 days — all their listings')
def gift_featured_7d_all_listings(modeladmin, request, queryset):
    total = 0
    for user in queryset:
        total += gift_featured_for_host(user, '7d')
    modeladmin.message_user(
        request,
        f'Featured {total} listing(s) for 7 days (free).',
        messages.SUCCESS,
    )


@admin.action(description='🎁 FREE featured 30 days — all their listings')
def gift_featured_30d_all_listings(modeladmin, request, queryset):
    total = 0
    for user in queryset:
        total += gift_featured_for_host(user, '30d')
    modeladmin.message_user(
        request,
        f'Featured {total} listing(s) for 30 days (free).',
        messages.SUCCESS,
    )


@admin.action(description='Reject pending verification')
def reject_verification_request(modeladmin, request, queryset):
    for user in queryset:
        reject_host_verification(user)
    modeladmin.message_user(request, f'Rejected verification for {queryset.count()} user(s).', messages.WARNING)


@admin.action(description='Revoke verification')
def revoke_verification(modeladmin, request, queryset):
    for user in queryset:
        revoke_host_verification(user)
    modeladmin.message_user(request, f'Revoked verification for {queryset.count()} user(s).', messages.WARNING)


class HostPropertyInline(admin.TabularInline):
    model = Property
    fk_name = 'host'
    extra = 0
    can_delete = False
    show_change_link = True
    fields = ('title', 'city', 'is_published', 'featured_until', 'featured_plan')
    readonly_fields = ('title', 'city', 'is_published', 'featured_until', 'featured_plan')
    verbose_name = 'Listing'
    verbose_name_plural = 'Client listings — feature individual ones under Rentals → Properties'

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Verify hosts and gift featured listings when handling queries."""

    list_display = (
        'username',
        'email',
        'host_verification_status',
        'host_verification_tier',
        'host_verification_requested_at',
        'listing_count',
        'is_host',
    )
    list_filter = (
        'host_verification_status',
        'host_verification_tier',
        'is_host',
        'is_staff',
        'is_active',
    )
    search_fields = ('username', 'first_name', 'last_name', 'email')
    ordering = ('-date_joined',)
    inlines = [HostPropertyInline]
    actions = [
        approve_pending_verification,
        gift_landlord_verification,
        gift_agency_verification,
        gift_featured_7d_all_listings,
        gift_featured_30d_all_listings,
        reject_verification_request,
        revoke_verification,
    ]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Queries — verify & feature for free',
            {
                'fields': ('admin_query_tools',),
            },
        ),
        (
            'Verification details',
            {
                'fields': (
                    'host_verification_status',
                    'host_verification_tier',
                    'host_verification_since',
                    'host_verification_requested_at',
                    'host_verification_requested_tier',
                ),
            },
        ),
        (
            'Qasha account',
            {
                'fields': (
                    'phone_number',
                    'profile_picture',
                    'is_host',
                    'is_verified',
                    'account_tier',
                    'premium_since',
                    'premium_requested_at',
                )
            },
        ),
    )

    def change_view(self, request, object_id, form_url='', extra_context=None):
        self._change_request = request
        return super().change_view(request, object_id, form_url, extra_context)

    def get_readonly_fields(self, request, obj=None):
        fields = list(super().get_readonly_fields(request, obj))
        if obj:
            fields.append('admin_query_tools')
        return fields

    @admin.display(description='Listings')
    def listing_count(self, obj):
        return obj.properties.count()

    @admin.display(description='Quick actions (queries / promotions)')
    def admin_query_tools(self, obj):
        if not obj.pk:
            return 'Save the user first, then use these buttons.'
        request = getattr(self, '_change_request', None)
        csrf = get_token(request) if request else ''
        base = f'/admin/users/user/{obj.pk}/'
        btn = (
            '<form method="post" action="{url}" style="display:inline;margin:0;">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{csrf}">'
            '<button type="submit" class="button"{style}>{label}</button></form>'
        )
        return format_html(
            '<div style="display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:.75rem;">'
            + btn.format(url=base + 'verify-landlord/', csrf=csrf, style='', label='Verify Landlord (free)')
            + btn.format(url=base + 'verify-agency/', csrf=csrf, style='', label='Verify Agency (free)')
            + btn.format(url=base + 'approve-pending/', csrf=csrf, style='', label='Approve pending verification')
            + btn.format(url=base + 'feature-7d/', csrf=csrf, style='', label='Feature all listings 7 days (free)')
            + btn.format(url=base + 'feature-30d/', csrf=csrf, style='', label='Feature all listings 30 days (free)')
            + btn.format(
                url=base + 'revoke-verify/',
                csrf=csrf,
                style=' style="background:#ba2121;"',
                label='Revoke verification',
            )
            + '</div>'
            '<p class="help">Verified tick is shown to all users. Featured badge on browse is owner-only; featured boost still applies in search.</p>'
            '<p class="help">To feature one listing only: '
            '<a href="/admin/rentals/property/?host__id__exact={}">open their properties</a>.</p>',
            obj.pk,
        )

    def get_urls(self):
        urls = super().get_urls()
        opts = self.model._meta
        custom = [
            path(
                '<path:object_id>/verify-landlord/',
                self.admin_site.admin_view(require_POST(self._verify_landlord)),
                name=f'{opts.app_label}_{opts.model_name}_verify_landlord',
            ),
            path(
                '<path:object_id>/verify-agency/',
                self.admin_site.admin_view(require_POST(self._verify_agency)),
                name=f'{opts.app_label}_{opts.model_name}_verify_agency',
            ),
            path(
                '<path:object_id>/approve-pending/',
                self.admin_site.admin_view(require_POST(self._approve_pending)),
                name=f'{opts.app_label}_{opts.model_name}_approve_pending',
            ),
            path(
                '<path:object_id>/feature-7d/',
                self.admin_site.admin_view(require_POST(self._feature_7d)),
                name=f'{opts.app_label}_{opts.model_name}_feature_7d',
            ),
            path(
                '<path:object_id>/feature-30d/',
                self.admin_site.admin_view(require_POST(self._feature_30d)),
                name=f'{opts.app_label}_{opts.model_name}_feature_30d',
            ),
            path(
                '<path:object_id>/revoke-verify/',
                self.admin_site.admin_view(require_POST(self._revoke_verify)),
                name=f'{opts.app_label}_{opts.model_name}_revoke_verify',
            ),
        ]
        return custom + urls

    def _redirect_back(self, user_id):
        return redirect(reverse('admin:users_user_change', args=[user_id]))

    def _verify_landlord(self, request, object_id):
        user = get_object_or_404(User, pk=object_id)
        grant_host_verification(user, 'landlord')
        messages.success(request, f'{user.username} verified as Landlord (free).')
        return self._redirect_back(object_id)

    def _verify_agency(self, request, object_id):
        user = get_object_or_404(User, pk=object_id)
        grant_host_verification(user, 'agency')
        messages.success(request, f'{user.username} verified as Agency (free).')
        return self._redirect_back(object_id)

    def _approve_pending(self, request, object_id):
        user = get_object_or_404(User, pk=object_id)
        if user.host_verification_status != 'pending':
            messages.warning(request, f'{user.username} has no pending verification request.')
            return self._redirect_back(object_id)
        tier = user.host_verification_requested_tier or 'landlord'
        if tier not in ('landlord', 'agency'):
            tier = 'landlord'
        approve_host_verification(user, tier)
        messages.success(request, f'{user.username} verification approved.')
        return self._redirect_back(object_id)

    def _feature_7d(self, request, object_id):
        user = get_object_or_404(User, pk=object_id)
        n = gift_featured_for_host(user, '7d')
        messages.success(request, f'Featured {n} listing(s) for 7 days (free).')
        return self._redirect_back(object_id)

    def _feature_30d(self, request, object_id):
        user = get_object_or_404(User, pk=object_id)
        n = gift_featured_for_host(user, '30d')
        messages.success(request, f'Featured {n} listing(s) for 30 days (free).')
        return self._redirect_back(object_id)

    def _revoke_verify(self, request, object_id):
        user = get_object_or_404(User, pk=object_id)
        revoke_host_verification(user)
        messages.warning(request, f'Verification revoked for {user.username}.')
        return self._redirect_back(object_id)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'verification_summary', 'user_admin_link')
    search_fields = ('user__username', 'user__email', 'location')
    readonly_fields = ('user', 'promote_verify_panel')

    fieldsets = (
        (None, {'fields': ('user', 'promote_verify_panel', 'bio', 'location', 'date_of_birth')}),
    )

    @admin.display(description='Verification')
    def verification_summary(self, obj):
        user = obj.user
        if user.host_verification_status == 'pending':
            return f'Pending ({user.host_verification_requested_tier or "?"})'
        if user.has_host_verification_badge():
            return user.host_verification_badge_label()
        return user.get_host_verification_status_display()

    @admin.display(description='Manage')
    def user_admin_link(self, obj):
        return format_html(
            '<a href="/admin/users/user/{}/change/">Verify &amp; feature for free →</a>',
            obj.user_id,
        )

    @admin.display(description='Queries — verify & feature')
    def promote_verify_panel(self, obj):
        user = obj.user
        return format_html(
            '<p>Status: <strong>{}</strong> · Listings: <strong>{}</strong></p>'
            '<p><a class="button" href="/admin/users/user/{}/change/">Open user admin '
            '(one-click verify &amp; featured gifts)</a></p>',
            user.get_host_verification_status_display(),
            user.properties.count(),
            user.pk,
        )

    def has_add_permission(self, request):
        return False
