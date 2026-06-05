from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0003_booking_flow_occupancy_private_feedback'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='payment_card_last4',
            field=models.CharField(blank=True, max_length=4),
        ),
        migrations.AddField(
            model_name='booking',
            name='payment_cardholder_name',
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name='booking',
            name='payment_on_file',
            field=models.BooleanField(
                default=False,
                help_text='Tenant submitted card details at application; charged when host accepts.',
            ),
        ),
    ]
