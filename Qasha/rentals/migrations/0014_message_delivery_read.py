from django.db import migrations, models
from django.utils import timezone


def backfill_message_timestamps(apps, schema_editor):
    Message = apps.get_model('rentals', 'Message')
    now = timezone.now()
    for msg in Message.objects.filter(delivered_at__isnull=True):
        msg.delivered_at = msg.created_at
        msg.save(update_fields=['delivered_at'])
    for msg in Message.objects.filter(is_read=True, read_at__isnull=True):
        msg.read_at = msg.created_at
        msg.save(update_fields=['read_at'])


class Migration(migrations.Migration):

    dependencies = [
        ('rentals', '0013_property_type_custom'),
    ]

    operations = [
        migrations.AddField(
            model_name='message',
            name='delivered_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='read_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_message_timestamps, migrations.RunPython.noop),
    ]
