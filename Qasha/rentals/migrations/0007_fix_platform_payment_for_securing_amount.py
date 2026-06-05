from django.db import migrations


def platform_when_securing_amount_set(apps, schema_editor):
    Property = apps.get_model('rentals', 'Property')
    Property.objects.filter(
        secure_space_amount__gt=0,
        payment_preference='direct',
    ).update(payment_preference='platform')


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0006_booking_payment_authorization'),
    ]

    operations = [
        migrations.RunPython(platform_when_securing_amount_set, migrations.RunPython.noop),
    ]
