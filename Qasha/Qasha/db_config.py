"""Database configuration: PostgreSQL (production) or SQLite (local fallback)."""

from __future__ import annotations

import os
import urllib.parse
from pathlib import Path


def load_dotenv(base_dir: Path) -> None:
    """Load KEY=VALUE lines from .env if present (no extra package required)."""
    env_file = base_dir / '.env'
    if not env_file.is_file():
        return
    for line in env_file.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, value = line.partition('=')
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def _postgres_from_url(url: str) -> dict:
    if url.startswith('postgres://'):
        url = 'postgresql://' + url[len('postgres://') :]
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ('postgresql', 'postgres'):
        raise ValueError(f'Unsupported DATABASE_URL scheme: {parsed.scheme}')
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': urllib.parse.unquote(parsed.path.lstrip('/')),
        'USER': urllib.parse.unquote(parsed.username or ''),
        'PASSWORD': urllib.parse.unquote(parsed.password or ''),
        'HOST': parsed.hostname or 'localhost',
        'PORT': str(parsed.port or 5432),
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
        'OPTIONS': {
            'connect_timeout': int(os.environ.get('DB_CONNECT_TIMEOUT', '10')),
        },
    }


def _postgres_from_env() -> dict:
    return {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'qasha'),
        'USER': os.environ.get('POSTGRES_USER', 'qasha'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'qasha'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
        'CONN_MAX_AGE': int(os.environ.get('DB_CONN_MAX_AGE', '60')),
        'OPTIONS': {
            'connect_timeout': int(os.environ.get('DB_CONNECT_TIMEOUT', '10')),
        },
    }


def configure_databases(base_dir: Path) -> dict:
    """
    PostgreSQL when DATABASE_URL or USE_POSTGRES is set; otherwise SQLite for easy local dev.
    """
    load_dotenv(base_dir)

    database_url = os.environ.get('DATABASE_URL', '').strip()
    use_postgres = os.environ.get('USE_POSTGRES', '').lower() in ('1', 'true', 'yes')

    if database_url:
        return {'default': _postgres_from_url(database_url)}
    if use_postgres:
        return {'default': _postgres_from_env()}

    return {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': base_dir / 'db.sqlite3',
        }
    }
