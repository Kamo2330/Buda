import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0009_seed_amenities'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='amenity',
            name='is_custom',
            field=models.BooleanField(
                default=False,
                help_text='Added by a host on the listing form (not in the standard filter list).',
            ),
        ),
        migrations.AddField(
            model_name='amenity',
            name='created_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='amenities_created',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
