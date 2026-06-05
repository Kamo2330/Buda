from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0012_property_listing_terms_accepted_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='property_type_custom',
            field=models.CharField(
                blank=True,
                help_text='When property type is Other, the label shown on the listing.',
                max_length=80,
            ),
        ),
    ]
