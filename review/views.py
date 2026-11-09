import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from curriculum.services import current_packages, find_activity, resources_by_id
from accounts.models import get_profile
from activities.viewmodels import build
from learning_core.normalize import normalize

from .models import ReviewItem
from django.utils import timezone

from learning_core import plan
from plan.services import day_titles, focus_program, program_overview

from .services import apply_outcome, next_due, today_plan


def _lexis_entry(pkg_data: dict, lexis_id: str) -> dict | None:
    return next((lx for lx in pkg_data.get("language_focus", {}).get("lexis", []) if lx["id"] == lexis_id), None)


def _gapped_example(entry: dict) -> str:
    pattern = re.compile(re.escape(entry["form"]), re.IGNORECASE)
    return pattern.sub("_____", entry.get("example", ""), count=1)


@login_required
def session(request):
    items, moved = today_plan(request.user)
    packages = current_packages()
    profile = get_profile(request.user)
    titles = day_titles()
    cards = []
    for item in items:
        pkg = packages.get(item.chapter_code)
        if not pkg:
            continue
        if item.kind == "lexis":
            entry = _lexis_entry(pkg.data, item.key.split(":", 1)[1])
            if entry:
                cards.append({"kind": "lexis", "item": item, "entry": entry, "gapped": _gapped_example(entry),
                              "origin": titles.get(item.chapter_code, item.chapter_code)})
            continue
        lesson_id, act = find_activity(pkg.data, item.key)
        if act is None or act["type"] in ("oral", "open_text"):
            continue
        cards.append({"kind": "activity", "item": item, "vm": build(
            activity=act, package=pkg, user=request.user, lesson_id=lesson_id,
            resources=resources_by_id(pkg.data), profile=profile,
            next_url=reverse("review"), source="repaso")})
    return render(request, "review/session.html", {
        "cards": cards, "moved": moved, "next_due": next_due(request.user),
        "focus": focus_program(program_overview(request.user, profile)),
    })


@login_required
@require_POST
def lexis_answer(request, pk: int):
    item = get_object_or_404(ReviewItem, pk=pk, user=request.user, kind="lexis")
    pkg = current_packages().get(item.chapter_code)
    entry = _lexis_entry(pkg.data, item.key.split(":", 1)[1]) if pkg else None
    if not entry:
        messages.warning(request, "Esta unidad ya no existe en la versión vigente del capítulo.")
        return redirect("review")
    answer = request.POST.get("text", "")
    if not answer.strip():
        messages.warning(request, "Escribe la expresión antes de comprobar.")
        return redirect(f"{reverse('review')}#rev-{item.pk}")
    correct = normalize(answer) == normalize(entry["form"])
    helped = request.POST.get("helped") == "1"
    apply_outcome(item, correct, helped)
    if correct:
        messages.success(request, f"Correcto: «{entry['form']}».{' (con pista: volverá mañana)' if helped else ''}")
    else:
        messages.warning(request, f"Se esperaba «{entry['form']}». {entry.get('confusions') or ''} Volverá mañana.")
    return redirect("review")
