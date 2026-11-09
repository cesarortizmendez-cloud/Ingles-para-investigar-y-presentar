from django.shortcuts import redirect
from django.utils.http import url_has_allowed_host_and_scheme


def safe_next(request, default: str) -> str:
    """Devuelve `next` del POST/GET solo si apunta a este mismo sitio."""
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()},
                                               require_https=request.is_secure()):
        return nxt
    return default


def redirect_next(request, default_name: str, *args):
    from django.urls import reverse
    return redirect(safe_next(request, reverse(default_name, args=args)))
