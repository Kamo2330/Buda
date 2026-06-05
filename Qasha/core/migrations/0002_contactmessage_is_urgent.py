from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contactmessage',
            name='is_urgent',
            field=models.BooleanField(
                default=False,
                help_text='Report a problem / emergency topics — shown first in admin.',
            ),
        ),
        migrations.AlterModelOptions(
            name='contactmessage',
            options={
                'ordering': ['-is_urgent', '-created_at'],
                'verbose_name': 'Help message',
                'verbose_name_plural': 'Help messages',
            },
        ),
    ]
