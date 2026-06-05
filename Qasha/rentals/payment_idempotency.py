"""Prevent duplicate simulated charges on double POST."""

import time

from django.core.cache import cache

_IDEM_WINDOW_SECONDS = 120


def payment_token(action: str, user_id: int, *parts: str) -> str:
    return ':'.join([action, str(user_id), *[str(p) for p in parts]])


def _cache_key(token: str) -> str:
    return f'qasha:pay:{token}'


def _inflight_key(token: str) -> str:
    return f'{_cache_key(token)}:inflight'


def payment_already_processed(request, token: str) -> bool:
    if cache.get(_cache_key(token)):
        return True
    entry = request.session.get('qasha_payment_idem')
    if not entry or entry.get('token') != token:
        return False
    return (time.time() - entry.get('ts', 0)) < _IDEM_WINDOW_SECONDS


def begin_payment_idempotency(request, token: str) -> bool:
    """
    Atomically claim a payment attempt.
    Returns False if already completed or another identical request is in flight.
    """
    if cache.get(_cache_key(token)):
        return False
    if not cache.add(_inflight_key(token), 1, timeout=_IDEM_WINDOW_SECONDS):
        return False
    return True


def complete_payment_idempotency(request, token: str) -> None:
    cache.set(_cache_key(token), True, timeout=_IDEM_WINDOW_SECONDS)
    cache.delete(_inflight_key(token))
    request.session['qasha_payment_idem'] = {'token': token, 'ts': time.time()}
    request.session.modified = True


def abort_payment_idempotency(token: str) -> None:
    cache.delete(_inflight_key(token))


def mark_payment_processed(request, token: str) -> None:
    complete_payment_idempotency(request, token)
