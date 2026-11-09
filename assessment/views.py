from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from activities.models import Attempt
from curriculum.services import current_package, find_activity
from django.utils import timezone

from accounts.models import get_profile
from plan.services import program_overview
from learning_core import diagnostic, plan, rubrics

from .models import DiagnosticResult
from .services import compute_diagnostic, save_rubric


def _back_url(attempt: Attempt) -> str:
    if attempt.lesson_id == "deferred":
        return reverse("deferred", args=[attempt.chapter_code])
    return reverse("lesson", args=[attempt.chapter_code, attempt.lesson_id]) + f"#act-{attempt.activity_id}"


@login_required
def rubric_form(request, attempt_id: int):
    attempt = get_object_or_404(Attempt, pk=attempt_id)
    is_owner = attempt.user_id == request.user.id
    if not (is_owner or request.user.is_staff):
        return HttpResponseForbidden("No autorizado.")
    _lesson, act = find_activity(attempt.package.data, attempt.activity_id)
    if not act or not act.get("rubric"):
        raise Http404("Esta actividad no se evalúa con rúbrica.")
    code = act["rubric"]
    essential = attempt.package.data.get("assessment", {}).get("essential_criteria") if act.get("role") == "final" else None
    essential = essential or rubrics.RUBRICS[code]["default_essential"]
    criteria = [{"id": cid, "name": name, "weight": w, "essential": cid in essential}
                for cid, name, w in rubrics.criteria(code)]

    if request.method == "POST":
        try:
            scores = {c["id"]: int(request.POST.get(f"c_{c['id']}", "")) for c in criteria}
            rs = save_rubric(attempt=attempt, rater=request.user, scores=scores,
                             notes=request.POST.get("notes", "")[:2000], essential=essential)
        except (ValueError, rubrics.RubricError):
            messages.error(request, "Asigna una puntuación de 0 a 4 a cada criterio.")
        else:
            lowest = sorted(criteria, key=lambda c: (scores[c["id"]], -c["weight"]))[:2]
            names = " y ".join(c["name"].lower() for c in lowest)
            verdict = "cumple la regla de tarea (≥ 70 y esenciales ≥ 2)" if rs.passed else "aún no cumple la regla de tarea"
            messages.success(request, f"Total {rs.total:.0f}/100: {verdict}. Prioriza {names} y vuelve a producir.")
            return redirect(_back_url(attempt))

    recordings = list(attempt.recordings.only("id", "mime", "duration_s", "transcript").all())
    if not recordings and attempt.response.get("recording_id"):
        from voice.models import Recording
        recordings = list(Recording.objects.filter(pk=attempt.response["recording_id"], user=attempt.user)
                          .only("id", "mime", "duration_s", "transcript"))
    return render(request, "assessment/rubric_form.html", {
        "attempt": attempt, "act": act, "criteria": criteria, "anchors": sorted(rubrics.ANCHORS.items()),
        "rubric_title": rubrics.RUBRICS[code]["title"], "is_owner": is_owner, "recordings": recordings,
        "previous": attempt.rubric_scores.all(), "back_url": _back_url(attempt),
    })


@login_required
def diagnostic_result(request):
    pkg = current_package("DX01")
    if pkg is None:
        raise Http404("El diagnóstico no está importado.")
    result = DiagnosticResult.objects.filter(user=request.user).first()
    rec = result.recommendation if result else {}
    profile = get_profile(request.user)
    return render(request, "assessment/diagnostic_result.html", {
        "result": result, "skills": diagnostic.SKILLS, "package": pkg,
        # se recalcula aquí para que también sirva con resultados guardados antes de este cambio
        "plan_focus": [{"skill": diagnostic.SKILLS[s], "block": diagnostic.SKILL_BLOCKS[s]}
                       for s in rec.get("reinforcement", []) if s in diagnostic.SKILL_BLOCKS],
        "profile": profile,
        "overview": program_overview(request.user, profile),
        "base_first": diagnostic.base_first(rec.get("reinforcement", [])) if result else False,
    })


@login_required
@require_POST
def diagnostic_compute(request):
    pkg = current_package("DX01")
    if pkg is None:
        raise Http404("El diagnóstico no está importado.")
    compute_diagnostic(request.user, pkg)
    return redirect("diagnostic_result")
