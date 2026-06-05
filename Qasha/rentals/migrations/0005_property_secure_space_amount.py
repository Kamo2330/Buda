from decimal import Decimal

from django.db import migrations, models


def copy_deposit_to_secure_amount(apps, schema_editor):
    Property = apps.get_model('rentals', 'Property')
    for prop in Property.objects.all():
        if not prop.secure_space_amount and prop.deposit_amount:
            prop.secure_space_amount = prop.deposit_amount
            prop.save(update_fields=['secure_space_amount'])


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0004_booking_payment_on_file'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='secure_space_amount',
            field=models.DecimalField(
                decimal_places=2,
                default=Decimal('0'),
                help_text='Amount a tenant pays on Qasha to secure this space when the host accepts.',
                max_digits=10,
            ),
        ),
        migrations.RunPython(copy_deposit_to_secure_amount, migrations.RunPython.noop),
    ]
