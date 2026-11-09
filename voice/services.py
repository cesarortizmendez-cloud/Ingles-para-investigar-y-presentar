from datetime import timedelta

from django.utils import timezone

from .models import Recording


def purge_expired(user) -> int:
    """Elimina las grabaciones más antiguas que el plazo elegido por el alumno (0 = conservar)."""
    from accounts.models import get_profile

    days = get_profile(user).keep_recordings_days
    if not days:
        return 0
    cutoff = timezone.now() - timedelta(days=days)
    deleted, _ = Recording.objects.filter(user=user, created_at__lt=cutoff).delete()
    return deleted
