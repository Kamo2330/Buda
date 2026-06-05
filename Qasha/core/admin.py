from django.contrib import admin, messages
from django.utils.html import format_html

from .models import ContactMessage, NewsletterSubscription, SiteConfiguration

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    """Help → Ask us submissions land here."""

    list_display = ('priority_display', 'name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_urgent', 'is_read', 'created_at', 'subject')
    search_fields = ('name', 'email', 'subject', 'message')
    list_editable = ('is_read',)
    readonly_fields = ('name', 'email', 'subject', 'message', 'is_urgent', 'created_at')
    list_per_page = 30
    actions = ['mark_read', 'mark_unread']

    fieldsets = (
        (None, {
            'fields': ('is_urgent', 'is_read', 'name', 'email', 'subject', 'message', 'created_at'),
        }),
    )

    @admin.display(description='Priority', ordering='is_urgent')
    def priority_display(self, obj):
        if obj.is_urgent:
            return format_html(
                '<span style="background:#dc3545;color:#fff;padding:2px 8px;'
                'border-radius:4px;font-weight:600;font-size:11px;">URGENT</span>'
            )
        return format_html('<span class="text-muted">Normal</span>')

    @admin.action(description='Mark selected as read')
    def mark_read(self, request, queryset):
        queryset.update(is_read=True)

    @admin.action(description='Mark selected as unread')
    def mark_unread(self, request, queryset):
        queryset.update(is_read=False)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        unread_urgent = ContactMessage.objects.filter(is_urgent=True, is_read=False).count()
        if unread_urgent:
            messages.warning(
                request,
                f'{unread_urgent} urgent Help message(s) need attention '
                '(Report a problem / Emergency).',
            )
        extra_context['qasha_help_stats'] = {
            'unread_urgent': unread_urgent,
            'unread_normal': ContactMessage.objects.filter(is_urgent=False, is_read=False).count(),
        }
        return super().changelist_view(request, extra_context=extra_context)


@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('email', 'is_active', 'subscribed_at')
    list_filter = ('is_active', 'subscribed_at')
    search_fields = ('email',)
    list_editable = ('is_active',)
    readonly_fields = ('subscribed_at',)


@admin.register(SiteConfiguration)
class SiteConfigurationAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Basic Information', {
            'fields': ('site_name', 'site_tagline')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone', 'whatsapp_number', 'office_address')
        }),
        ('Social Media', {
            'fields': ('facebook_url', 'twitter_url', 'instagram_url', 'linkedin_url')
        }),
    )

    def has_add_permission(self, request):
        return not SiteConfiguration.objects.exists()
