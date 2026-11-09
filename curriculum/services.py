"""Acceso al contenido versionado y cálculo de estado de capítulo."""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from learning_core import contract, progression, rubrics

from .models import ChapterProgress, ContentPackage


class ContentError(Exception):
    pass


# ------------------------------------------------------------------ catálogo

@lru_cache(maxsize=8)
def load_program(slug: str = "plan40") -> dict:
    """Metadatos y lista de días de un programa (content/plan40.json, content/base20.json…)."""
    from learning_core import programs
    path = Path(settings.CONTENT_DIR) / programs.get(slug)["file"]
    return json.loads(path.read_text(encoding="utf-8"))


def load_plan() -> dict:
    return load_program("plan40")


load_plan.cache_clear = load_program.cache_clear


@lru_cache(maxsize=1)
def load_course() -> dict:
    path = Path(settings.CONTENT_DIR) / "course.json"
    return json.loads(path.read_text(encoding="utf-8"))


def course_chapter_index() -> dict[str, dict]:
    out = {}
    for stage in load_course()["stages"]:
        for code, title in stage["chapters"]:
            out[code] = {"code": code, "title": title, "stage": stage["id"], "stage_title": stage["title"]}
    return out


def current_package(code: str) -> ContentPackage | None:
    return ContentPackage.objects.filter(code=code, is_current=True).first()


def current_packages() -> dict[str, ContentPackage]:
    return {p.code: p for p in ContentPackage.objects.filter(is_current=True)}


# ------------------------------------------------------------------ importación

def bump_patch(version: str) -> str:
    major, minor, patch = (int(x) for x in version.split("."))
    return f"{major}.{minor}.{patch + 1}"


@transaction.atomic
def publish_version(data: dict, change_note: str = "") -> tuple[ContentPackage, bool]:
    """Valida y guarda `data` como versión vigente. Devuelve (paquete, creado)."""
    errors = contract.validate(data)
    if errors:
        raise ContentError("\n".join(errors))
    code, version = data["id"], data["version"]
    checksum = ContentPackage.compute_checksum(data)
    existing = ContentPackage.objects.filter(code=code, version=version).first()
    if existing:
        if existing.checksum != checksum:
            raise ContentError(
                f"{code} v{version} ya existe con otro contenido. Suba la versión (p. ej. {bump_patch(version)}) "
                "para no alterar los intentos registrados con la versión anterior."
            )
        if not existing.is_current:
            ContentPackage.objects.filter(code=code).update(is_current=False)
            existing.is_current = True
            existing.save(update_fields=["is_current"])
        return existing, False
    ContentPackage.objects.filter(code=code).update(is_current=False)
    pkg = ContentPackage.objects.create(
        code=code, kind=data["kind"], version=version, status=data["status"], title=data["title"],
        data=data, is_current=True, change_note=change_note,
    )
    return pkg, True


def import_directory(root: Path | None = None) -> list[tuple[str, str, bool]]:
    root = Path(root or settings.CONTENT_DIR)
    results = []
    paths = list(root.glob("chapters/*.json")) + list(root.glob("diagnostic/*.json")) + list(root.glob("days/*.json"))
    for path in sorted(paths):
        data = json.loads(path.read_text(encoding="utf-8"))
        pkg, created = publish_version(data, change_note=f"Importado de {path.name}")
        results.append((pkg.code, pkg.version, created))
    return results


# ------------------------------------------------------------------ navegación del paquete

def lesson(data: dict, lesson_id: str) -> dict | None:
    return next((lsn for lsn in data.get("lessons", []) if lsn["id"] == lesson_id), None)


def find_activity(data: dict, activity_id: str) -> tuple[str, dict] | tuple[None, None]:
    for lesson_id, act in contract.iter_activities(data):
        if act["id"] == activity_id:
            return lesson_id, act
    return None, None


def resources_by_id(data: dict) -> dict[str, dict]:
    return {r["id"]: r for r in data.get("resources", [])}


def activities_with_role(data: dict, role: str) -> list[dict]:
    return [a for _l, a in contract.iter_activities(data) if a.get("role") == role]


# ------------------------------------------------------------------ estado de capítulo

def mark_opened(user, chapter_code: str) -> ChapterProgress:
    prog, _ = ChapterProgress.objects.get_or_create(user=user, chapter_code=chapter_code)
    if not prog.opened_at:
        prog.opened_at = timezone.now()
        prog.save(update_fields=["opened_at", "updated_at"])
        from review.services import seed_lexis
        pkg = current_package(chapter_code)
        if pkg:
            seed_lexis(user, pkg.data)
    return prog


def _first_scores(attempts, ids: set[str], since=None) -> dict[str, float | None]:
    out: dict[str, float | None] = {}
    for att in attempts.order_by("created_at"):
        if att.activity_id not in ids or att.activity_id in out:
            continue
        if since and att.created_at.date() < since:
            continue
        if att.status != "corregido":
            continue
        out[att.activity_id] = att.score
    return out


def task_evaluation(user, data: dict) -> dict | None:
    """Mejor evaluación con rúbrica de la tarea integradora (humana prevalece sobre autoevaluación)."""
    from assessment.models import RubricScore

    final_ids = [a["id"] for a in activities_with_role(data, "final")]
    if not final_ids:
        return None
    essential = data.get("assessment", {}).get("essential_criteria")
    scores = RubricScore.objects.filter(attempt__user=user, attempt__activity_id__in=final_ids).order_by("-created_at")
    human = [s for s in scores if s.rater_kind == rubrics.RATER_HUMAN]
    pool = human or [s for s in scores if s.rater_kind == rubrics.RATER_SELF]
    if not pool:
        return None
    evaluations = [rubrics.evaluate(s.rubric_code, s.scores, essential) | {"rater_kind": s.rater_kind} for s in pool]
    return max(evaluations, key=lambda e: (e["passed"], e["total"]))


def chapter_status(user, pkg: ContentPackage, save: bool = True) -> dict:
    from activities.models import Attempt

    data = pkg.data
    code = pkg.code
    today = timezone.localdate()
    prog = ChapterProgress.objects.filter(user=user, chapter_code=code).first()
    attempts = Attempt.objects.filter(user=user, chapter_code=code)
    n_attempts = attempts.exclude(source="diferido").count()

    check_ids = [a["id"] for a in activities_with_role(data, "check")]
    first = _first_scores(attempts.exclude(source="diferido"), set(check_ids))
    check = progression.check_ratio(first, check_ids)
    task = task_evaluation(user, data)

    provisional_on = prog.provisional_on if prog else None
    deferred = None
    deferred_ids = [a["id"] for a in data.get("assessment", {}).get("deferred_check", {}).get("activities", [])]
    if provisional_on and deferred_ids:
        start, _end = progression.deferred_window(provisional_on)
        dfirst = _first_scores(attempts.filter(source="diferido"), set(deferred_ids), since=start)
        deferred = progression.check_ratio(dfirst, deferred_ids)

    state = progression.chapter_state(
        opened=bool(prog and prog.opened_at), attempts=n_attempts, check=check, task=task,
        provisional_on=provisional_on, deferred=deferred, today=today,
    )
    if save:
        prog = prog or ChapterProgress(user=user, chapter_code=code)
        if state["state"] in (progression.PROVISIONAL, progression.CONSOLIDATED) and not prog.provisional_on:
            prog.provisional_on = today
            # recalcular la ventana con la fecha recién fijada
            state = progression.chapter_state(
                opened=True, attempts=n_attempts, check=check, task=task,
                provisional_on=today, deferred=None, today=today,
            )
        if state["state"] == progression.CONSOLIDATED and not prog.consolidated_on:
            prog.consolidated_on = today
        prog.recovery_needed = state["recovery_needed"]
        prog.last_state = state["state"]
        prog.save()
    state.update({"check": check, "task": task, "deferred": deferred, "label": progression.LABELS[state["state"]]})
    return state


def recovery_activities(data: dict, user) -> list[dict]:
    """Actividades de práctica ligadas a los objetivos de los ítems diferidos fallados."""
    from activities.models import Attempt

    deferred = data.get("assessment", {}).get("deferred_check", {}).get("activities", [])
    failed_obj = set()
    for act in deferred:
        last = Attempt.objects.filter(user=user, activity_id=act["id"], source="diferido").order_by("-created_at").first()
        if last and not last.correct:
            failed_obj.update(act.get("objectives", []))
    out = []
    for lesson_id, act in contract.iter_activities(data):
        if lesson_id == "deferred" or act.get("role") not in ("practice", "check"):
            continue
        if set(act.get("objectives", [])) & failed_obj and act["type"] not in ("oral", "open_text"):
            out.append({"lesson_id": lesson_id, "activity": act})
    return out
