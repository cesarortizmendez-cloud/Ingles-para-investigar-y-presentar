from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST

from config.http import safe_next
from curriculum.models import ContentPackage
from curriculum.services import chapter_status, find_activity
from learning_core import grading

from .forms import parse_duration, parse_helps, parse_response
from .services import submit


@login_required
@require_POST
def submit_view(request, package_id: int, activity_id: str):
    pkg = get_object_or_404(ContentPackage, pk=package_id)
    lesson_id, activity = find_activity(pkg.data, activity_id)
    if activity is None:
        raise Http404("Actividad inexistente en esta versión.")

    if pkg.kind == "diagnostic":
        source = "diagnostico"
        fallback = reverse("lesson", args=[pkg.code, lesson_id])
    elif lesson_id == "deferred":
        source = "diferido"
        fallback = reverse("deferred", args=[pkg.code])
        state = chapter_status(request.user, pkg)
        if not state["deferred_available"]:
            messages.warning(request, "La confirmación diferida todavía no está disponible.")
            return redirect(fallback)
    else:
        source = "repaso" if request.POST.get("source") == "repaso" else "leccion"
        fallback = reverse("lesson", args=[pkg.code, lesson_id])

    attempt, result = submit(
        user=request.user, package=pkg, activity=activity, lesson_id=lesson_id,
        response=parse_response(activity, request.POST), helps=parse_helps(request.POST),
        duration_ms=parse_duration(request.POST), source=source,
    )
    nxt = safe_next(request, fallback)
    if attempt is None:
        messages.warning(request, " ".join(result.feedback) or "Respuesta incompleta.")
    elif attempt.status == grading.PENDING_RUBRIC:
        messages.info(request, "Respuesta guardada. Evalúala con la rúbrica para registrar tu desempeño.")
    elif attempt.status == grading.PENDING_EVIDENCE:
        messages.info(request, "Guardado en modo sin micrófono: la habilidad oral queda pendiente de evidencia.")
    return redirect(f"{nxt.split('#')[0]}#act-{activity_id}")
