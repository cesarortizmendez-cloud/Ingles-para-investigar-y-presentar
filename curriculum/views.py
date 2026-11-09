from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from activities.models import Attempt
from accounts.models import get_profile
from activities.viewmodels import build
from django.utils import timezone

from learning_core import plan, programs, progression
from plan.services import CHAPTER_WEEK, program_overview
from learning_core.presenters import pick_variant

from .models import ChapterProgress
from .services import (chapter_status, current_package, current_packages, lesson, load_course, load_plan, mark_opened,
                       recovery_activities, resources_by_id)


@login_required
def catalog(request):
    packages = current_packages()
    progress = {p.chapter_code: p for p in ChapterProgress.objects.filter(user=request.user)}
    stages = []
    for stage in load_course()["stages"]:
        chapters = []
        for code, title in stage["chapters"]:
            pkg = packages.get(code)
            prog = progress.get(code)
            chapters.append({
                "code": code, "title": title, "available": pkg is not None,
                "objectives": pkg.data["objectives"] if pkg else [],
                "product": pkg.data.get("product") if pkg else "",
                "suggested": pkg.data["dependencies"]["suggested_chapters"] if pkg else [],
                "status": pkg.status if pkg else "",
                "state_label": progression.LABELS.get(prog.last_state if prog else "no_iniciado"),
                "recovery": bool(prog and prog.recovery_needed),
                "week": CHAPTER_WEEK.get(code),
            })
        stages.append({**stage, "chapter_list": chapters})
    profile = get_profile(request.user)
    overview = program_overview(request.user, profile)
    for prog in overview:
        days = prog["meta"]["days"]
        cur_unit = next((d["week"] for d in days if d["day"] == prog["today_n"]), None) if prog["started"] else None
        units = []
        for w in prog["meta"]["weeks"]:
            nums = [d["day"] for d in days if d["week"] == w["n"]]
            units.append({**w, "first": min(nums), "last": max(nums), "current": w["n"] == cur_unit})
        prog["units"] = units
    return render(request, "curriculum/catalog.html", {
        "stages": stages, "note": load_course()["note"], "overview": overview,
    })


@login_required
def chapter_detail(request, code: str):
    pkg = current_package(code)
    if pkg is None or pkg.kind != "chapter":
        raise Http404("Capítulo no disponible todavía.")
    state = chapter_status(request.user, pkg)
    lesson_rows = []
    for lsn in pkg.data["lessons"]:
        ids = [a["id"] for a in lsn["activities"]]
        done = Attempt.objects.filter(user=request.user, activity_id__in=ids).values("activity_id").distinct().count()
        lesson_rows.append({"lesson": lsn, "done": done, "total": len(ids)})
    return render(request, "curriculum/chapter.html", {
        "pkg": pkg, "data": pkg.data, "state": state, "lessons": lesson_rows,
        "recovery": recovery_activities(pkg.data, request.user) if state["recovery_needed"] else [],
    })


@login_required
def lesson_view(request, code: str, lesson_id: str):
    pkg = current_package(code)
    if pkg is None:
        raise Http404("Contenido no disponible.")
    lsn = lesson(pkg.data, lesson_id)
    if lsn is None:
        raise Http404("Lección inexistente.")
    if pkg.kind in ("chapter", "day"):
        mark_opened(request.user, code)
    profile = get_profile(request.user)
    resources = resources_by_id(pkg.data)
    show_all = request.GET.get("variantes") == "todas"
    acts = lsn["activities"] if show_all else pick_variant(lsn["activities"], profile.specialty)
    here = reverse("lesson", args=[code, lesson_id])
    source = "diagnostico" if pkg.kind == "diagnostic" else "leccion"
    vms = [build(activity=a, package=pkg, user=request.user, lesson_id=lesson_id, resources=resources,
                 profile=profile, next_url=here, source=source) for a in acts]
    lessons = pkg.data["lessons"]
    idx = next(i for i, x in enumerate(lessons) if x["id"] == lesson_id)
    has_variants = any(a.get("variant_group") for a in lsn["activities"])
    return render(request, "curriculum/lesson.html", {
        "pkg": pkg, "data": pkg.data, "lesson": lsn, "activities": vms,
        "lesson_resources": [resources[r] for r in lsn.get("resources", []) if r in resources],
        "prev": lessons[idx - 1] if idx > 0 else None,
        "next": lessons[idx + 1] if idx + 1 < len(lessons) else None,
        "has_variants": has_variants, "show_all": show_all, "is_diagnostic": pkg.kind == "diagnostic",
        "is_day": pkg.kind == "day", "day_program": programs.for_code(code) if pkg.kind == "day" else None,
        "voice": profile.tts_voice,
    })


@login_required
def deferred_view(request, code: str):
    pkg = current_package(code)
    if pkg is None or pkg.kind != "chapter":
        raise Http404("Capítulo no disponible.")
    state = chapter_status(request.user, pkg)
    if not state["deferred_available"]:
        if state["deferred_window"]:
            messages.info(request, f"La confirmación diferida se abre el {state['deferred_window'][0]:%d-%m-%Y}.")
        else:
            messages.info(request, "Primero aprueba provisionalmente el capítulo.")
        return redirect("chapter", code=code)
    profile = get_profile(request.user)
    resources = resources_by_id(pkg.data)
    here = reverse("deferred", args=[code])
    deferred = pkg.data["assessment"]["deferred_check"]
    vms = [build(activity=a, package=pkg, user=request.user, lesson_id="deferred", resources=resources,
                 profile=profile, next_url=here, source="diferido") for a in deferred["activities"]]
    return render(request, "curriculum/deferred.html", {
        "pkg": pkg, "data": pkg.data, "activities": vms, "state": state,
        "deferred_resources": [resources[r] for r in deferred.get("resources", []) if r in resources],
    })


@login_required
def diagnostic_index(request):
    pkg = current_package("DX01")
    if pkg is None:
        raise Http404("El diagnóstico no está importado (python manage.py import_content).")
    rows = []
    for lsn in pkg.data["lessons"]:
        ids = [a["id"] for a in lsn["activities"]]
        done = Attempt.objects.filter(user=request.user, source="diagnostico", activity_id__in=ids) \
            .values("activity_id").distinct().count()
        rows.append({"lesson": lsn, "done": done, "total": len(ids)})
    return render(request, "curriculum/diagnostic_index.html", {"pkg": pkg, "rows": rows})
