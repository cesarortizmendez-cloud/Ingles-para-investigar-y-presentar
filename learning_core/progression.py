"""Estado de un capítulo (§12, «Cierre de capítulo»).

Estados: no_iniciado → abierto → practicado → aprobado_provisional → consolidado.
- aprobado_provisional: ≥ 80 % en comprobación con ítems no vistos (primer intento
  de cada ítem «check») Y tarea integradora ≥ 70/100 sin criterio esencial < 2/4.
- consolidado: además, confirmación diferida ≥ 75 % realizada desde 7 días después
  de la aprobación provisional (se recomienda antes del día 14).
- Si la confirmación diferida falla: sigue aprobado_provisional con recuperación
  específica activada. Nunca se borra historial ni se obliga a repetir el nivel.
El capítulo siguiente puede abrirse en cualquier momento (los prerrequisitos son
sugerencias), por eso no existe un estado «bloqueado».
"""
from __future__ import annotations

from datetime import date, timedelta

NOT_STARTED = "no_iniciado"
OPEN = "abierto"
PRACTICED = "practicado"
PROVISIONAL = "aprobado_provisional"
CONSOLIDATED = "consolidado"
STATES = (NOT_STARTED, OPEN, PRACTICED, PROVISIONAL, CONSOLIDATED)
LABELS = {
    NOT_STARTED: "No iniciado",
    OPEN: "Abierto",
    PRACTICED: "Practicado",
    PROVISIONAL: "Aprobado provisionalmente",
    CONSOLIDATED: "Consolidado",
}

CHECK_MIN = 0.80
DEFERRED_MIN = 0.75
DEFERRED_START_DAYS = 7
DEFERRED_RECOMMENDED_END_DAYS = 14


def check_ratio(first_attempt_scores: dict[str, float | None], check_ids: list[str]) -> float | None:
    """Promedio de primeros intentos en ítems de comprobación; None si falta alguno."""
    if not check_ids:
        return None
    values = [first_attempt_scores.get(i) for i in check_ids]
    if any(v is None for v in values):
        return None
    return sum(values) / len(values)


def deferred_window(provisional_on: date) -> tuple[date, date]:
    return (provisional_on + timedelta(days=DEFERRED_START_DAYS),
            provisional_on + timedelta(days=DEFERRED_RECOMMENDED_END_DAYS))


def chapter_state(*, opened: bool, attempts: int, check: float | None, task: dict | None,
                  provisional_on: date | None, deferred: float | None, today: date) -> dict:
    reasons: list[str] = []
    out = {"state": NOT_STARTED, "recovery_needed": False, "deferred_window": None,
           "deferred_available": False, "reasons": reasons}
    if not opened and attempts == 0:
        return out
    out["state"] = OPEN
    if attempts == 0:
        return out
    out["state"] = PRACTICED

    if check is None:
        reasons.append("Falta completar la comprobación con ítems nuevos.")
    elif check < CHECK_MIN:
        reasons.append(f"Comprobación: {check:.0%} (se requiere {CHECK_MIN:.0%}).")
    if task is None:
        reasons.append("Falta la evaluación con rúbrica de la tarea integradora.")
    elif not task.get("passed"):
        if task.get("total", 0) < 70:
            reasons.append(f"Tarea integradora: {task.get('total', 0):.0f}/100 (se requiere 70).")
        if task.get("essential_below_min"):
            reasons.append("Algún criterio esencial quedó bajo 2/4.")
    passed_now = check is not None and check >= CHECK_MIN and bool(task and task.get("passed"))
    if not passed_now and provisional_on is None:
        return out

    out["state"] = PROVISIONAL
    since = provisional_on or today
    start, end = deferred_window(since)
    out["deferred_window"] = (start, end)
    out["deferred_available"] = today >= start
    if deferred is None:
        if today < start:
            reasons.append(f"Confirmación diferida disponible desde el {start.isoformat()}.")
        else:
            reasons.append("Confirmación diferida disponible ahora.")
        return out
    if deferred >= DEFERRED_MIN:
        out["state"] = CONSOLIDATED
        reasons.clear()
        return out
    out["recovery_needed"] = True
    reasons.append(f"Confirmación diferida: {deferred:.0%} (se requiere {DEFERRED_MIN:.0%}). Se activó recuperación específica.")
    return out
