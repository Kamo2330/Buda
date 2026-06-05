from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0003_user_host_verification_requested_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='terms_accepted_at',
            field=models.DateTimeField(
                blank=True,
                help_text='When the user accepted Terms and Privacy at registration.',
                null=True,
            ),
        ),
    ]
