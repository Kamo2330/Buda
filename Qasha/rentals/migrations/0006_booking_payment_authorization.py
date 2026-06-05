from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0005_property_secure_space_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='authorization_ref',
            field=models.CharField(blank=True, max_length=40),
        ),
        migrations.AddField(
            model_name='booking',
            name='authorized_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='payment_auth_status',
            field=models.CharField(
                choices=[
                    ('none', 'No authorization'),
                    ('authorized', 'Authorized (hold — not charged yet)'),
                    ('captured', 'Captured (paid)'),
                    ('released', 'Authorization released'),
                ],
                default='none',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='released_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(
            code=lambda apps, schema_editor: _backfill_auth(apps),
            reverse_code=migrations.RunPython.noop,
        ),
    ]


def _backfill_auth(apps):
    Booking = apps.get_model('rentals', 'Booking')
    for b in Booking.objects.filter(payment_on_file=True, status='pending'):
        b.payment_auth_status = 'authorized'
        if not b.authorization_ref:
            b.authorization_ref = f'AUTH-{b.pk}-LEGACY'
        b.save(update_fields=['payment_auth_status', 'authorization_ref'])
    for b in Booking.objects.filter(status='secured', paid_at__isnull=False):
        b.payment_auth_status = 'captured'
        b.save(update_fields=['payment_auth_status'])
    for b in Booking.objects.filter(status__in=('declined', 'cancelled'), payment_on_file=True):
        if b.payment_auth_status == 'authorized':
            b.payment_auth_status = 'released'
            b.save(update_fields=['payment_auth_status'])
