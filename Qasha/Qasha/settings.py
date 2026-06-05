"""
Django settings for Qasha project.
"""

import os
from pathlib import Path

from .db_config import configure_databases, load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.lower() in ('1', 'true', 'yes')


def _env_list(name: str, default: str = '') -> list[str]:
    raw = os.environ.get(name, default)
    return [part.strip() for part in raw.split(',') if part.strip()]


from django.core.exceptions import ImproperlyConfigured

_INSECURE_SECRET_PREFIX = 'django-insecure-'

SECRET_KEY = os.environ.get(
    'SECRET_KEY',
    'django-insecure-sawjl97y&o-a&nqqjbndzp76t4+-z9egy1b#-n)i8$#j_)%lqo',
)

DEBUG = _env_bool('DEBUG', True)

ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS')
CSRF_TRUSTED_ORIGINS = _env_list('CSRF_TRUSTED_ORIGINS')

if not DEBUG:
    if not os.environ.get('SECRET_KEY') or SECRET_KEY.startswith(_INSECURE_SECRET_PREFIX):
        raise ImproperlyConfigured(
            'Set a strong SECRET_KEY environment variable when DEBUG is false.'
        )
    if not ALLOWED_HOSTS:
        raise ImproperlyConfigured(
            'Set ALLOWED_HOSTS when DEBUG is false (comma-separated hostnames).'
        )

def _append_dev_hosts_and_csrf_origins():
    for host in ('127.0.0.1', 'localhost', '[::1]'):
        if host not in ALLOWED_HOSTS:
            ALLOWED_HOSTS.append(host)
    if DEBUG:
        try:
            import socket

            _, _, lan_ips = socket.gethostbyname_ex(socket.gethostname())
            for ip in lan_ips:
                if ip not in ALLOWED_HOSTS:
                    ALLOWED_HOSTS.append(ip)
        except OSError:
            pass
    for host in ALLOWED_HOSTS:
        if host in ('localhost', '[::1]'):
            continue
        schemes = ('https',) if not DEBUG else ('http', 'https')
        for scheme in schemes:
            port_suffix = ':8000' if DEBUG and scheme == 'http' else ''
            for origin in (f'{scheme}://{host}{port_suffix}', f'{scheme}://{host}'):
                if origin not in CSRF_TRUSTED_ORIGINS:
                    CSRF_TRUSTED_ORIGINS.append(origin)


_append_dev_hosts_and_csrf_origins()

CURRENCY_CODE = 'ZAR'
CURRENCY_SYMBOL = 'R'

# Google Maps Platform — Places Autocomplete (set in .env for address search)
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
HELP_ALERT_EMAIL = os.environ.get('HELP_ALERT_EMAIL', '')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'users.apps.UsersConfig',
    'rentals',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Qasha.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'rentals.context_processors.nav_alerts',
                'core.context_processors.google_maps',
                'users.context_processors.profile_location',
            ],
        },
    },
]

WSGI_APPLICATION = 'Qasha.wsgi.application'

DATABASES = configure_databases(BASE_DIR)

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en-us'

TIME_ZONE = os.environ.get('TIME_ZONE', 'Africa/Johannesburg')

USE_I18N = True

USE_TZ = True

STATIC_URL = 'static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Large listing uploads (photos + video on mobile)
DATA_UPLOAD_MAX_MEMORY_SIZE = 262144000  # 250 MB
FILE_UPLOAD_MAX_MEMORY_SIZE = 262144000

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'qasha-default',
    }
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'users.User'

LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/rentals/'

if not DEBUG:
    SECURE_SSL_REDIRECT = _env_bool('SECURE_SSL_REDIRECT', False)
    SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE', True)
    CSRF_COOKIE_SECURE = _env_bool('CSRF_COOKIE_SECURE', True)
    _hsts = os.environ.get('SECURE_HSTS_SECONDS', '')
    if _hsts.isdigit() and int(_hsts) > 0:
        SECURE_HSTS_SECONDS = int(_hsts)
