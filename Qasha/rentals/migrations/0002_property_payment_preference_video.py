# Generated manually for Qasha listing UX

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='payment_preference',
            field=models.CharField(
                choices=[('platform', 'Through Qasha (recommended)'), ('direct', 'Pay the host directly')],
                default='platform',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='property',
            name='video',
            field=models.FileField(
                blank=True,
                null=True,
                upload_to='properties/videos/',
                validators=[
                    django.core.validators.FileExtensionValidator(
                        allowed_extensions=['mp4', 'webm', 'mov', 'mpeg', 'mpg']
                    )
                ],
            ),
        ),
    ]
