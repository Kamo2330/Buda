from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0011_performance_indexes'),
    ]

    operations = [
        migrations.AddField(
            model_name='property',
            name='listing_terms_accepted_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Host accepted listing declarations and Terms when publishing.',
                null=True,
            ),
        ),
    ]
