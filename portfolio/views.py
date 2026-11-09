import json

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import get_profile
from activities.models import Attempt
from assessment.models import DiagnosticResult, RubricScore
from curriculum.models import ChapterProgress
from curriculum.services import course_chapter_index, current_packages, find_activity
from learning_core import progression
from review.models import ReviewItem
from voice.models import Recording
from voice.services import purge_expired
from learning_core import programs
from plan.services import day_titles, progress_for


@login_required
def index(request):
    """Evidencias: tareas integradoras y producciones abiertas, con rúbricas y grabaciones."""
    purged = purge_expired(request.user)
    if purged:
        messages.info(request, f"Se eliminaron {purged} grabaciones según tu plazo de conservación.")
    index = course_chapter_index()
    packages = current_packages()
    titles = day_titles()
    evidence = []
    attempts = (Attempt.objects.filter(user=request.user, activity_type__in=["oral", "open_text"])
                .exclude(source="diagnostico").select_related("package").order_by("chapter_code", "-created_at"))
    for att in attempts:
        _l, act = find_activity(att.package.data, att.activity_id)
        evidence.append({
            "attempt": att, "act": act or {},
            "chapter_title": titles.get(att.chapter_code) or index.get(att.chapter_code, {}).get("title", att.chapter_code),
            "rubric": att.rubric_scores.first(),
            "recordings": list(att.recordings.only("id", "mime", "duration_s", "transcript", "consent_share", "consent_reuse")),
        })
    demonstrated = []
    for prog in ChapterProgress.objects.filter(user=request.user):
        pkg = packages.get(prog.chapter_code)
        if pkg and prog.last_state in (progression.PROVISIONAL, progression.CONSOLIDATED):
            demonstrated.append({"code": prog.chapter_code, "label": progression.LABELS[prog.last_state],
                                 "objectives": pkg.data["objectives"]})
    days_done = []  # por programa: Base 20 primero, luego Plan 40
    for prg in programs.PROGRAMS:
        for n, prog in sorted(progress_for(request.user, packages, prg["slug"]).items()):
            pkg = packages.get(programs.day_code(prg["slug"], n))
            if prog.get("done") and pkg:
                days_done.append({"n": n, "title": pkg.data["title"], "objectives": pkg.data["objectives"],
                                  "program": prg["short"], "main": prg["slug"] == programs.MAIN})
    loose = Recording.objects.filter(user=request.user, attempt__isnull=True) \
        .only("id", "mime", "duration_s", "activity_id", "created_at")
    return render(request, "portfolio/index.html", {
        "evidence": evidence, "demonstrated": demonstrated, "loose_recordings": loose, "days_done": days_done,
    })


@login_required
def export_json(request):
    user = request.user
    profile = get_profile(user)
    data = {
        "exported_at": timezone.now().isoformat(),
        "user": {"username": user.get_username(), "email": user.email},
        "profile": {f.name: getattr(profile, f.name) for f in profile._meta.fields
                    if f.name not in ("id", "user", "created_at", "updated_at")},
        "chapters": list(ChapterProgress.objects.filter(user=user).values(
            "chapter_code", "last_state", "provisional_on", "consolidated_on", "recovery_needed")),
        "attempts": list(Attempt.objects.filter(user=user).values(
            "chapter_code", "activity_id", "package__version", "source", "attempt_number", "status",
            "score", "correct", "response", "helps", "duration_ms", "feedback", "created_at")),
        "rubrics": list(RubricScore.objects.filter(attempt__user=user).values(
            "attempt__activity_id", "rubric_code", "rater_kind", "scores", "total", "passed", "notes", "created_at")),
        "review": list(ReviewItem.objects.filter(user=user).values("key", "kind", "stage", "due", "history")),
        "diagnostics": list(DiagnosticResult.objects.filter(user=user).values("package_version", "estimates",
                                                                               "recommendation", "created_at")),
        "recordings": list(Recording.objects.filter(user=user).values(
            "id", "activity_id", "mime", "duration_s", "transcript", "consent_share", "consent_reuse", "created_at")),
        "note": "El audio de las grabaciones no se incluye en este archivo; puede descargarlo desde el portafolio.",
    }
    body = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    resp = HttpResponse(body, content_type="application/json; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="progreso-{user.get_username()}.json"'
    return resp


@login_required
def privacy(request):
    recs = Recording.objects.filter(user=request.user)
    return render(request, "portfolio/privacy.html", {
        "n_recordings": recs.count(),
        "n_attempts": Attempt.objects.filter(user=request.user).count(),
        "shared": recs.filter(consent_share=True).count(),
    })


@login_required
@require_POST
def delete_recordings(request):
    if request.POST.get("confirm") != "ELIMINAR":
        messages.error(request, "Escribe ELIMINAR para confirmar.")
        return redirect("privacy")
    n, _ = Recording.objects.filter(user=request.user).delete()
    messages.success(request, f"Se eliminaron {n} grabaciones. Los intentos y rúbricas se conservan sin audio.")
    return redirect("privacy")


@login_required
@require_POST
def delete_account(request):
    if request.POST.get("confirm") != "ELIMINAR MI CUENTA":
        messages.error(request, "Escribe ELIMINAR MI CUENTA para confirmar.")
        return redirect("privacy")
    user = request.user
    logout(request)
    user.delete()  # en cascada: perfil, intentos, grabaciones, repaso, rúbricas, diagnósticos
    messages.success(request, "Tu cuenta y todos tus datos fueron eliminados.")
    return redirect("home")
