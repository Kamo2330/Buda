from django.db import models


class ContactMessage(models.Model):
    """Help panel “Ask us” messages — reviewed in Django admin."""

    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_urgent = models.BooleanField(
        default=False,
        help_text='Report a problem / emergency topics — shown first in admin.',
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-is_urgent', '-created_at']
        verbose_name = 'Help message'
        verbose_name_plural = 'Help messages'
    
    def __str__(self):
        return f"{self.name} - {self.subject}"


class NewsletterSubscription(models.Model):
    """Newsletter subscriptions"""
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.email


class SiteConfiguration(models.Model):
    """Site-wide configuration settings"""
    site_name = models.CharField(max_length=100, default="Qasha")
    site_tagline = models.CharField(max_length=200, default="Find the perfect room or home with Qasha")
    contact_email = models.EmailField(default="contact@qasha.com")
    contact_phone = models.CharField(max_length=20, default="")
    whatsapp_number = models.CharField(max_length=20, default="")
    office_address = models.TextField(blank=True)
    facebook_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    
    class Meta:
        verbose_name = "Site Configuration"
        verbose_name_plural = "Site Configuration"
    
    def __str__(self):
        return self.site_name
    
    def save(self, *args, **kwargs):
        if not self.pk and SiteConfiguration.objects.exists():
            raise ValueError("Only one SiteConfiguration instance is allowed")
        super().save(*args, **kwargs)