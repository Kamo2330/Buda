"""Safe redirects for POST `next` parameters."""

from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme


def safe_redirect(request, next_url, default_view_name, **default_kwargs):
    default = reverse(default_view_name, **default_kwargs)
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect(default)
