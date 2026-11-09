from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from config.http import redirect_next
from curriculum.models import ContentPackage

from .models import Recording
from .services import purge_expired


def _can_listen(user, rec: Recording) -> bool:
    # El dueño siempre; el personal solo si el alumno autorizó compartir con evaluadores.
    return rec.user_id == user.id or (user.is_staff and rec.consent_share)


@login_required
@require_POST
def upload(request):
    purge_expired(request.user)
    blob = request.FILES.get("audio")
    if blob is None:
        return JsonResponse({"error": "No llegó audio."}, status=400)
    if blob.size > settings.RECORDING_MAX_BYTES:
        return JsonResponse({"error": "La grabación es demasiado grande. Graba un fragmento más corto."}, status=413)
    mime = (blob.content_type or "").split(";")[0]
    if not mime.startswith("audio/"):
        return JsonResponse({"error": "Formato no reconocido como audio."}, status=400)
    try:
        duration = float(request.POST.get("duration_s") or 0) or None
    except ValueError:
        duration = None
    if duration and duration > settings.RECORDING_MAX_SECONDS:
        return JsonResponse({"error": "La grabación supera la duración máxima."}, status=413)
    pkg = ContentPackage.objects.filter(pk=request.POST.get("package_id") or 0).first()
    transcript = (request.POST.get("transcript") or "")[:5000]
    rec = Recording.objects.create(
        user=request.user, package=pkg, activity_id=(request.POST.get("activity_id") or "")[:40],
        audio=blob.read(), mime=mime, size_bytes=blob.size, duration_s=duration,
        transcript=transcript, transcript_source="asr_navegador" if transcript else "",
    )
    return JsonResponse({"id": rec.pk, "url": f"/voz/{rec.pk}/audio/"})


@login_required
def stream(request, pk: int):
    rec = get_object_or_404(Recording, pk=pk)
    if not _can_listen(request.user, rec):
        return HttpResponseForbidden("No autorizado.")
    resp = HttpResponse(bytes(rec.audio), content_type=rec.mime)
    resp["Cache-Control"] = "private, max-age=3600"
    resp["Content-Length"] = str(len(rec.audio))
    return resp


@login_required
@require_POST
def update_transcript(request, pk: int):
    rec = get_object_or_404(Recording, pk=pk, user=request.user)
    rec.transcript = (request.POST.get("transcript") or "")[:5000]
    rec.transcript_source = "manual"
    rec.asr_errors_flagged = (request.POST.get("asr_errors") or "")[:2000]
    rec.save(update_fields=["transcript", "transcript_source", "asr_errors_flagged"])
    if request.headers.get("x-requested-with") == "fetch":
        return JsonResponse({"ok": True})
    messages.success(request, "Transcripción actualizada.")
    return redirect_next(request, "portfolio")


@login_required
@require_POST
def update_consent(request, pk: int):
    rec = get_object_or_404(Recording, pk=pk, user=request.user)
    rec.consent_share = request.POST.get("consent_share") == "1"
    rec.consent_reuse = request.POST.get("consent_reuse") == "1"
    rec.save(update_fields=["consent_share", "consent_reuse"])
    messages.success(request, "Autorizaciones actualizadas.")
    return redirect("portfolio")


@login_required
@require_POST
def delete(request, pk: int):
    rec = get_object_or_404(Recording, pk=pk, user=request.user)
    rec.delete()
    messages.success(request, "Grabación eliminada.")
    return redirect_next(request, "portfolio")
