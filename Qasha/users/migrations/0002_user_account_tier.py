from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='account_tier',
            field=models.CharField(
                choices=[('free', 'Free'), ('premium', 'Premium (validated)')],
                default='free',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='user',
            name='premium_since',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='user',
            name='premium_requested_at',
            field=models.DateTimeField(
                blank=True,
                help_text='User asked to validate a paid Premium account.',
                null=True,
            ),
        ),
    ]
