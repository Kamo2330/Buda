from django.conf import settings
from django.shortcuts import render
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import TemplateView, RedirectView
from django.core.mail import send_mail
from .models import ContactMessage, NewsletterSubscription, SiteConfiguration
from django.utils import timezone
from rentals.models import Property
from rentals.query_utils import property_listing_queryset
import json


URGENT_HELP_TOPICS = frozenset({'Report a problem', 'Emergency / urgent'})


def _notify_staff_urgent_help(name, email, topic, message):
    """Email site contact when configured (demo builds may use console backend)."""
    alert_to = getattr(settings, 'HELP_ALERT_EMAIL', '') or ''
    if not alert_to:
        try:
            config = SiteConfiguration.objects.first()
            if config and config.contact_email:
                alert_to = config.contact_email
        except Exception:
            pass
    if not alert_to:
        return
    body = (
        f'Urgent Help message on Qasha\n\n'
        f'Topic: {topic}\n'
        f'From: {name} <{email}>\n\n'
        f'{message}\n\n'
        f'Open admin → Core → Help messages to reply.'
    )
    send_mail(
        subject=f'[Qasha URGENT] Help: {topic}',
        message=body,
        from_email=alert_to,
        recipient_list=[alert_to],
        fail_silently=True,
    )


class HomeView(TemplateView):
    """Home page view"""
    template_name = 'core/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Paid featured listings on homepage
        now = timezone.now()
        featured_properties = property_listing_queryset(
            Property.objects.filter(
                featured_until__gt=now,
                is_published=True,
                is_available=True,
                is_occupied=False,
            )
        ).order_by('-featured_until')[:6]
        
        # Get site configuration
        try:
            site_config = SiteConfiguration.objects.first()
        except SiteConfiguration.DoesNotExist:
            site_config = None
        
        context.update({
            'featured_properties': featured_properties,
            'site_config': site_config,
        })
        
        return context


class AboutView(TemplateView):
    """About us page view"""
    template_name = 'core/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            site_config = SiteConfiguration.objects.first()
        except SiteConfiguration.DoesNotExist:
            site_config = None
        
        context['site_config'] = site_config
        return context


class ContactView(RedirectView):
    """Legacy URL — opens in-app help panel."""
    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse('rentals:property_list') + '?help=1'


class PrivacyPolicyView(TemplateView):
    template_name = 'core/privacy.html'


class TermsOfServiceView(TemplateView):
    template_name = 'core/terms.html'


class LaunchComplianceView(LoginRequiredMixin, UserPassesTestMixin, TemplateView):
    """Internal pre-launch checklist — staff only, not linked publicly."""

    template_name = 'core/launch_compliance.html'

    def test_func(self):
        return self.request.user.is_staff


class HowItWorksView(TemplateView):
    """How it works page view"""
    template_name = 'core/how_it_works.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            site_config = SiteConfiguration.objects.first()
        except SiteConfiguration.DoesNotExist:
            site_config = None
        
        context['site_config'] = site_config
        return context


@require_POST
def contact_form_submit(request):
    """Handle in-app help contact form."""
    try:
        data = json.loads(request.body)

        message = data.get('message', '').strip()
        topic = (data.get('topic') or 'General question').strip()[:200]

        if request.user.is_authenticated:
            name = request.user.get_full_name() or request.user.username
            email = request.user.email
        else:
            name = data.get('name', '').strip() or 'Guest'
            email = data.get('email', '').strip()

        if not message:
            return JsonResponse({'success': False, 'message': 'Please write a message.'})
        if not email:
            return JsonResponse({'success': False, 'message': 'Please add your email.'})

        urgent_topics = {'Report a problem', 'Emergency / urgent'}
        is_urgent = topic in urgent_topics

        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=topic,
            message=message,
            is_urgent=is_urgent,
        )

        if is_urgent:
            _notify_staff_urgent_help(name, email, topic, message)

        return JsonResponse({
            'success': True,
            'message': (
                'Got it — we have flagged this as urgent and will respond as soon as we can.'
                if is_urgent
                else 'Got it — we will reply by email soon.'
            ),
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid data format.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        })


@require_POST
def newsletter_subscribe(request):
    """Handle newsletter subscription"""
    try:
        data = json.loads(request.body)
        email = data.get('email', '').strip()
        
        if not email:
            return JsonResponse({
                'success': False,
                'message': 'Email is required.'
            })
        
        subscription, created = NewsletterSubscription.objects.get_or_create(
            email=email,
            defaults={'is_active': True}
        )
        
        if not created:
            if not subscription.is_active:
                subscription.is_active = True
                subscription.save()
                message = 'You have been resubscribed to our newsletter!'
            else:
                message = 'You are already subscribed to our newsletter.'
        else:
            message = 'Thank you for subscribing to our newsletter!'
        
        return JsonResponse({
            'success': True,
            'message': message
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid data format.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred. Please try again.'
        })