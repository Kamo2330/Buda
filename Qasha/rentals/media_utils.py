"""Media storage helpers and upload constraints."""

ALLOWED_VIDEO_EXTENSIONS = (
    'mp4',
    'm4v',
    'webm',
    'mov',
    '3gp',
    'mpeg',
    'mpg',
    'avi',
    'mkv',
    'ogv',
    'ogg',
)

# Formats that usually play in mobile/desktop browsers (H.264/AAC in MP4 is best).
VIDEO_PLAYBACK_PREFERRED = ('mp4', 'm4v', 'webm', 'mov')

VIDEO_MIME_BY_EXT = {
    'mp4': 'video/mp4',
    'm4v': 'video/mp4',
    'webm': 'video/webm',
    'mov': 'video/quicktime',
    '3gp': 'video/3gpp',
    'mpeg': 'video/mpeg',
    'mpg': 'video/mpeg',
    'avi': 'video/x-msvideo',
    'mkv': 'video/x-matroska',
    'ogv': 'video/ogg',
    'ogg': 'video/ogg',
}

VIDEO_ACCEPT_INPUT = ','.join(
    [f'video/{ext}' for ext in ('mp4', 'webm', 'quicktime', '3gpp')]
    + [f'.{ext}' for ext in ALLOWED_VIDEO_EXTENSIONS]
)


def stored_media_exists(file_field) -> bool:
    if not file_field or not getattr(file_field, 'name', None):
        return False
    try:
        return file_field.storage.exists(file_field.name)
    except Exception:
        return False


def video_extension_allowed(filename: str) -> bool:
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[-1].lower() in ALLOWED_VIDEO_EXTENSIONS


def mime_type_for_video(filename: str) -> str:
    ext = (str(filename or '').rsplit('.', 1)[-1]).lower()
    return VIDEO_MIME_BY_EXT.get(ext, 'video/mp4')
