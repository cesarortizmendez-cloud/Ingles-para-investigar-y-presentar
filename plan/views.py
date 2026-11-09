from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import get_profile
from curriculum.services import current_packages, load_program
from learning_core import coach, plan, programs

from .services import BLOCK_LABELS, calendar_url, day_code, day_url, phrase_of_day, progress_for, stats

MAIN = programs.MAIN


def _program(slug: str) -> dict:
    if slug not in programs.BY_SLUG:
        raise Http404("Programa desconocido.")
    try:
        meta = load_program(slug)
    except FileNotFoundError:
        raise Http404("Este programa todavía no tiene contenido.")
    return {**programs.get(slug), "meta": meta, "calendar_url": calendar_url(slug)}


def _cells(user, profile, packages, slug: str = MAIN):
    prog = programs.get(slug)
    today = timezone.localdate()
    cells = plan.calendar(profile.program_start(slug), today, progress_for(user, packages, slug),
                          total=prog["total"], prefix=prog["prefix"])
    meta = {d["day"]: d for d in load_program(slug)["days"]}
    for c in cells:
        c["meta"] = meta.get(c["n"], {})
        c["available"] = c["code"] in packages
        c["url"] = day_url(slug, c["n"]) if c["available"] else "#"
    return cells


def coach_context(user, profile, cells=None, slug: str = MAIN) -> dict:
    """Contexto del gráfico de avance de un programa (lo usan el calendario y el inicio)."""
    prog = _program(slug)
    packages = current_packages()
    cells = cells or _cells(user, profile, packages, slug)
    today = timezone.localdate()
    start = profile.program_start(slug)
    total = prog["total"]
    today_n = plan.recommended_day(start, today, total)
    done = sum(1 for c in cells if c["state"] == plan.COMPLETED)
    items = [tuple(m) for m in prog["meta"].get("milestones", [])] or None
    return {
        "prog": prog,
        "ring": coach.ring_segments([c["state"] for c in cells]),
        "milestones": coach.milestones(done, items),
        "projection": coach.projection(start, today, done, total),
        "done": done, "total": total, "pct": round(done * 100 / total),
        "today_n": today_n, "today_title": cells[today_n - 1]["meta"].get("title", ""),
        "today_url": day_url(slug, today_n), "stats": stats(user, slug),
        "ring_title": prog["meta"].get("ring_title", "Tu camino a la presentación final"),
    }


@login_required
def calendar_view(request, program: str = MAIN):
    prog = _program(program)
    profile = get_profile(request.user)
    packages = current_packages()
    cells = _cells(request.user, profile, packages, program)
    weeks = []
    for wk in prog["meta"]["weeks"]:
        days = [c for c in cells if c["meta"].get("week") == wk["n"]]
        done = sum(1 for c in days if c["state"] == plan.COMPLETED)
        weeks.append({**wk, "days": days, "done": done, "count": len(days)})
    ctx = coach_context(request.user, profile, cells, program)
    others = [{**p, "url": calendar_url(p["slug"])} for p in programs.PROGRAMS if p["slug"] != program]
    ctx.update({"plan": prog["meta"], "weeks": weeks, "profile": profile, "start": profile.program_start(program),
                "start_action": reverse("plan_start") if program == MAIN else reverse("program_start", args=[program]),
                "others": others})
    return render(request, "plan/calendar.html", ctx)


@login_required
@require_POST
def start_plan(request, program: str = MAIN):
    prog = _program(program)
    profile = get_profile(request.user)
    raw = request.POST.get("start") or ""
    try:
        start = date.fromisoformat(raw) if raw else timezone.localdate()
    except ValueError:
        messages.error(request, "Fecha no válida.")
        return redirect(prog["calendar_url"])
    setattr(profile, prog["start_field"], start)
    profile.save(update_fields=[prog["start_field"], "updated_at"])
    messages.success(request, f"{prog['name']} iniciado: el día 1 es el {start:%d-%m-%Y}. ¡Vamos!")
    return redirect(day_url(program, plan.recommended_day(start, timezone.localdate(), prog["total"])))


@login_required
def day_view(request, n: int, program: str = MAIN):
    prog = _program(program)
    if not 1 <= n <= prog["total"]:
        raise Http404(f"El programa tiene {prog['total']} días.")
    packages = current_packages()
    pkg = packages.get(day_code(n, program))
    meta = next((d for d in prog["meta"]["days"] if d["day"] == n), None)
    if pkg is None or meta is None:
        raise Http404("Este día todavía no está cargado (python manage.py import_content).")
    profile = get_profile(request.user)
    start = profile.program_start(program)
    cells = _cells(request.user, profile, packages, program)
    cell = cells[n - 1]
    prog_day = cell["progress"] or {}
    blocks = []
    for b in prog_day.get("blocks", []):
        lsn = next(x for x in pkg.data["lessons"] if x["id"] == b["lesson_id"])
        blocks.append({**b, "lesson": lsn})
    if not blocks:
        for lsn in pkg.data["lessons"]:
            label, icon = BLOCK_LABELS.get(lsn["kind"], (lsn["kind"], "•"))
            blocks.append({"lesson": lsn, "label": label, "icon": icon, "minutes": lsn.get("minutes", 0),
                           "done": 0, "total": len(lsn["activities"]), "lesson_id": lsn["id"]})
    next_block = next((b for b in blocks if b["done"] < b["total"]), blocks[0])
    phrase_en, phrase_es = phrase_of_day(pkg.data)
    review_minutes = prog["meta"].get("review_minutes", 15)
    total_minutes = sum(lsn.get("minutes", 0) for lsn in pkg.data["lessons"]) + review_minutes
    return render(request, "plan/day.html", {
        "prog": prog, "pkg": pkg, "data": pkg.data, "meta": meta, "n": n, "blocks": blocks, "progress": prog_day,
        "cells": cells, "next_block": next_block, "phrase_en": phrase_en, "phrase_es": phrase_es,
        "prev_n": n - 1 if n > 1 else None, "next_n": n + 1 if n < prog["total"] else None,
        "prev_url": day_url(program, n - 1) if n > 1 else None,
        "next_url": day_url(program, n + 1) if n < prog["total"] else None,
        "date": start + timedelta(days=n - 1) if start else None,
        "today_n": plan.recommended_day(start, timezone.localdate(), prog["total"]),
        "total_minutes": total_minutes, "review_minutes": review_minutes,
        "daily_minutes": profile.daily_minutes,
    })
