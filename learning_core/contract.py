"""Contrato editorial mínimo de un paquete de contenido (§14).

`validate(package)` devuelve una lista de errores legibles (vacía = válido). Se usa
en `manage.py validate_content`, al importar y en las pruebas.
"""
from __future__ import annotations

import re

from .grading import ALL_TYPES
from .rubrics import RUBRICS

EDITORIAL_STATES = ("borrador", "revisado", "publicado")
LESSON_KINDS = ("comprender", "descubrir", "escuchar", "recuperar", "producir", "tarea")
DAY_BLOCKS = ("vocabulario", "gramatica", "escucha", "lectura", "habla", "escritura")
DAY_TYPES = ("aprendizaje", "repaso", "final")
DAY_ID = re.compile(r"^[A-Z]\d{2}$")
RESOURCE_TYPES = ("text", "chart", "wordlist", "capsule")
ROLES = ("practice", "check", "final", "deferred", "diagnostic")
SPECIALTIES = ("comun", "comercial", "industrial", "informatica")
CHAPTER_ID = re.compile(r"^C\d{2}$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
CLOZE_GAP = re.compile(r"\[\[(\w+)\]\]")

REQUIRED_CHAPTER = ("id", "kind", "version", "status", "title", "stage", "order", "objectives",
                    "dependencies", "language_level", "language_focus", "resources", "lessons",
                    "adaptation", "assessment", "quality")


def iter_activities(package: dict):
    """Todas las actividades del paquete: (lesson_id | 'deferred', actividad)."""
    for lesson in package.get("lessons", []):
        for act in lesson.get("activities", []):
            yield lesson["id"], act
    for act in (package.get("assessment") or {}).get("deferred_check", {}).get("activities", []):
        yield "deferred", act


def _check_activity(act: dict, resource_ids: set[str], errors: list[str]) -> None:
    aid = act.get("id", "?")
    kind = act.get("type")
    if kind not in ALL_TYPES:
        errors.append(f"{aid}: tipo desconocido {kind!r}")
        return
    if not act.get("prompt"):
        errors.append(f"{aid}: falta 'prompt'")
    if act.get("role", "practice") not in ROLES:
        errors.append(f"{aid}: rol inválido {act.get('role')!r}")
    if act.get("specialty", "comun") not in SPECIALTIES:
        errors.append(f"{aid}: especialidad inválida {act.get('specialty')!r}")
    for rid in act.get("resources", []):
        if rid not in resource_ids:
            errors.append(f"{aid}: recurso inexistente {rid}")
    if act.get("rubric") and act["rubric"] not in RUBRICS:
        errors.append(f"{aid}: rúbrica desconocida {act['rubric']!r}")

    if kind == "choice":
        _check_choice(aid, act, errors)
    elif kind == "cloze":
        markers = set(CLOZE_GAP.findall(act.get("text", "")))
        if markers != set(act.get("gaps", {})):
            errors.append(f"{aid}: los marcadores [[n]] no coinciden con 'gaps'")
        for k, g in act.get("gaps", {}).items():
            if not g.get("accept"):
                errors.append(f"{aid}: el espacio {k} no tiene respuestas aceptadas")
    elif kind == "ordering":
        ids = [i["id"] for i in act.get("items", [])]
        if sorted(ids) != sorted(act.get("answer", [])) or len(set(ids)) != len(ids):
            errors.append(f"{aid}: 'answer' debe ser una permutación de los ids de 'items'")
    elif kind == "numeric":
        _check_numeric(aid, act.get("fields", []), errors)
    elif kind == "short_text":
        if not act.get("accept"):
            errors.append(f"{aid}: falta 'accept'")
    elif kind == "listening":
        if not (act.get("audio") or {}).get("text") and not (act.get("audio") or {}).get("file"):
            errors.append(f"{aid}: falta audio (texto para voz sintetizada o archivo)")
        if not act.get("transcript"):
            errors.append(f"{aid}: falta 'transcript' para la revisión posterior")
        for q in act.get("questions", []):
            if "options" in q:
                _check_choice(f"{aid}/{q.get('id')}", q, errors)
            else:
                _check_numeric(f"{aid}/{q.get('id')}", q.get("fields", []), errors)
    elif kind == "dictation":
        if not act.get("answer") or not (act.get("audio") or {}).get("text"):
            errors.append(f"{aid}: dictado requiere 'answer' y 'audio.text'")
    elif kind == "oral":
        if not act.get("min_seconds") or not act.get("max_seconds"):
            errors.append(f"{aid}: oral requiere 'min_seconds' y 'max_seconds'")


def _check_choice(aid: str, act: dict, errors: list[str]) -> None:
    ids = [o["id"] for o in act.get("options", [])]
    if len(ids) < 2 or len(set(ids)) != len(ids):
        errors.append(f"{aid}: se necesitan al menos dos opciones con id único")
    if act.get("answer") not in ids:
        errors.append(f"{aid}: 'answer' no está entre las opciones")
    ev = act.get("evidence")
    if ev:
        sids = {s["id"] for s in ev.get("sentences", [])}
        if not ev.get("answer") or not set(ev["answer"]) <= sids:
            errors.append(f"{aid}: la evidencia correcta debe estar entre las oraciones")


def _check_numeric(aid: str, fields: list[dict], errors: list[str]) -> None:
    if not fields:
        errors.append(f"{aid}: faltan campos numéricos")
    for f in fields:
        if not {"id", "label", "answer"} <= set(f):
            errors.append(f"{aid}: campo numérico incompleto {f}")


def validate(package: dict) -> list[str]:
    errors: list[str] = []
    kind = package.get("kind")
    if kind not in ("chapter", "diagnostic", "day"):
        return [f"'kind' debe ser 'chapter', 'diagnostic' o 'day' (recibido {kind!r})"]
    pid = package.get("id", "?")
    if not VERSION.match(str(package.get("version", ""))):
        errors.append(f"{pid}: versión debe tener formato X.Y.Z")
    if package.get("status") not in EDITORIAL_STATES:
        errors.append(f"{pid}: estado editorial inválido {package.get('status')!r}")

    if kind == "chapter":
        for key in REQUIRED_CHAPTER:
            if key not in package:
                errors.append(f"{pid}: falta el campo '{key}' del contrato editorial")
        if not CHAPTER_ID.match(pid):
            errors.append(f"{pid}: id de capítulo debe ser C01…C24")
        n_obj = len(package.get("objectives", []))
        if not 3 <= n_obj <= 5:
            errors.append(f"{pid}: debe tener entre 3 y 5 objetivos (tiene {n_obj})")
        kinds = [lsn.get("kind") for lsn in package.get("lessons", [])]
        if kinds != list(LESSON_KINDS):
            errors.append(f"{pid}: las seis lecciones núcleo deben seguir el orden {LESSON_KINDS}")
        lex = package.get("language_focus", {}).get("lexis", [])
        if not 8 <= len(lex) <= 12:
            errors.append(f"{pid}: se esperan 8–12 unidades léxicas prioritarias (tiene {len(lex)})")
        quality = package.get("quality", {})
        for key in ("authors", "license", "date", "changelog"):
            if key not in quality:
                errors.append(f"{pid}: calidad sin '{key}'")

    if kind == "day":
        for key in ("id", "version", "status", "title", "day", "week", "day_type", "objectives", "lessons", "resources", "quality"):
            if key not in package:
                errors.append(f"{pid}: falta el campo '{key}'")
        from . import programs
        prog = programs.for_code(pid) if DAY_ID.match(pid or "") else None
        if prog is None:
            errors.append(f"{pid}: id de día debe ser B01…B20 (base) o D01…D40 (plan 40)")
        elif package.get("day") != int(pid[1:]):
            errors.append(f"{pid}: el campo 'day' no coincide con el código")
        if package.get("day_type") not in DAY_TYPES:
            errors.append(f"{pid}: day_type inválido")
        if not 2 <= len(package.get("objectives", [])) <= 5:
            errors.append(f"{pid}: un día necesita entre 2 y 5 metas")
        kinds = [lsn.get("kind") for lsn in package.get("lessons", [])]
        if [k for k in kinds if k not in DAY_BLOCKS] or len(set(kinds)) != len(kinds):
            errors.append(f"{pid}: bloques del día inválidos o repetidos: {kinds}")
        lex = package.get("language_focus", {}).get("lexis", [])
        if package.get("day_type") == "aprendizaje" and len(lex) != 12:
            errors.append(f"{pid}: un día de aprendizaje introduce 12 unidades léxicas (tiene {len(lex)})")
        for lsn in package.get("lessons", []):
            if not lsn.get("activities"):
                errors.append(f"{lsn.get('id')}: bloque sin actividades")

    resources = package.get("resources", [])
    resource_ids = {r["id"] for r in resources}
    for r in resources:
        if r.get("type", "text") not in RESOURCE_TYPES:
            errors.append(f"{r['id']}: tipo de recurso desconocido {r.get('type')!r}")
        prov = r.get("provenance") or {}
        if not prov.get("license") or not prov.get("author"):
            errors.append(f"{r['id']}: recurso sin autoría o licencia")
        if r.get("fictional_data") is None:
            errors.append(f"{r['id']}: indique 'fictional_data' (true si los datos son didácticos)")

    seen: set[str] = set()
    obj_ids = {o["id"] for o in package.get("objectives", [])}
    for _lesson_id, act in iter_activities(package):
        aid = act.get("id", "?")
        if aid in seen:
            errors.append(f"{aid}: id de actividad duplicado")
        seen.add(aid)
        if not aid.startswith(pid):
            errors.append(f"{aid}: el id debe empezar por {pid}")
        for o in act.get("objectives", []):
            if obj_ids and o not in obj_ids:
                errors.append(f"{aid}: objetivo inexistente {o}")
        _check_activity(act, resource_ids, errors)

    if kind == "chapter":
        assess = package.get("assessment", {})
        finals = [a for _l, a in iter_activities(package) if a.get("role") == "final"]
        if not finals:
            errors.append(f"{pid}: falta la tarea integradora (rol 'final')")
        for f in finals:
            if not f.get("rubric"):
                errors.append(f"{f['id']}: la tarea integradora necesita rúbrica")
        if not [a for _l, a in iter_activities(package) if a.get("role") == "check"]:
            errors.append(f"{pid}: faltan ítems de comprobación (rol 'check')")
        deferred = assess.get("deferred_check", {}).get("activities", [])
        if not deferred:
            errors.append(f"{pid}: falta la confirmación diferida")
        for a in deferred:
            if a.get("type") in ("open_text", "oral"):
                errors.append(f"{a['id']}: la confirmación diferida usa ítems de corrección determinista")
    return errors
