from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0002_property_payment_preference_video'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='is_occupied',
            field=models.BooleanField(
                default=False,
                help_text='Tenant is in the place; listing stays off browse until marked vacant.',
            ),
        ),
        migrations.AddField(
            model_name='booking',
            name='host_note',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='booking',
            name='paid_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='booking',
            name='check_out_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='booking',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending host review'),
                    ('accepted', 'Accepted — pay on Qasha to secure'),
                    ('secured', 'Secured (paid on Qasha)'),
                    ('declined', 'Declined'),
                    ('cancelled', 'Cancelled'),
                    ('completed', 'Completed'),
                ],
                default='pending',
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name='message',
            name='subject',
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name='review',
            name='is_public',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterModelOptions(
            name='review',
            options={
                'verbose_name': 'Private feedback',
                'verbose_name_plural': 'Private feedback',
            },
        ),
    ]
