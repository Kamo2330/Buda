from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0005_userprofile_home_location'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='search_radius_km',
            field=models.PositiveSmallIntegerField(
                default=5,
                help_text='Default GPS search radius on browse (2–15 km).',
            ),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='widen_search_if_empty',
            field=models.BooleanField(
                default=True,
                help_text='If no listings in radius, expand search up to 15 km.',
            ),
        ),
    ]
