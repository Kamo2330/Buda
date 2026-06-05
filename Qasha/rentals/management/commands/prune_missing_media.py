"""Remove listing photo/video DB rows when files are missing from media/ (safe cleanup)."""

from django.core.management.base import BaseCommand

from rentals.media_utils import stored_media_exists
from rentals.models import Property, PropertyImage


class Command(BaseCommand):
    help = 'Delete property images and videos whose files are missing from storage.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be removed without deleting.',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        removed_images = 0
        removed_videos = 0

        for img in PropertyImage.objects.select_related('property').iterator():
            if stored_media_exists(img.image):
                continue
            self.stdout.write(
                f'Image {img.pk} ({img.image.name}) on listing {img.property_id} — file missing'
            )
            if not dry_run:
                if img.image:
                    img.image.delete(save=False)
                img.delete()
            removed_images += 1

        for prop in Property.objects.exclude(video='').iterator():
            if stored_media_exists(prop.video):
                continue
            self.stdout.write(f'Video on listing {prop.pk} ({prop.video.name}) — file missing')
            if not dry_run:
                prop.video.delete(save=False)
                prop.video = None
                prop.save(update_fields=['video', 'updated_at'])
            removed_videos += 1

        action = 'Would remove' if dry_run else 'Removed'
        self.stdout.write(
            self.style.SUCCESS(
                f'{action} {removed_images} image(s) and {removed_videos} video(s).'
            )
        )
