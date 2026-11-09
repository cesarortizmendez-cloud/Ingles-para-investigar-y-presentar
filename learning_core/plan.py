"""Planes por días (Base 20, Plan 40…): progreso diario, calendario y racha (sin Django).

Reglas (propuestas de producto, a pilotear):
- Un día se considera COMPLETADO cuando se intentó al menos el 80 % de sus actividades
  y el promedio de primeros intentos en ítems cerrados es ≥ 70 %.
- EN CURSO: hay intentos, pero aún no cumple lo anterior.
- El día recomendado es (hoy − fecha de inicio) + 1, entre 1 y 40. Se puede adelantar:
  ningún día se bloquea. Un día anterior al recomendado sin completar figura ATRASADO,
  pero no se acumula como deuda: el repaso espaciado limita la carga diaria.
"""
from __future__ import annotations

from datetime import date, timedelta

TOTAL_DAYS = 40
DONE_ATTEMPTED_MIN = 0.80
DONE_SCORE_MIN = 0.70

COMPLETED = "completado"
IN_PROGRESS = "en_curso"
TODAY = "hoy"
PENDING = "pendiente"
LATE = "atrasado"
LABELS = {COMPLETED: "Completado", IN_PROGRESS: "En curso", TODAY: "Hoy", PENDING: "Pendiente", LATE: "Atrasado"}


def day_progress(total_activities: int, attempted: int, closed_first_scores: list[float]) -> dict:
    ratio = attempted / total_activities if total_activities else 0.0
    mean = sum(closed_first_scores) / len(closed_first_scores) if closed_first_scores else None
    done = ratio >= DONE_ATTEMPTED_MIN and (mean is None or mean >= DONE_SCORE_MIN)
    return {"attempted": attempted, "total": total_activities, "ratio": round(ratio, 3),
            "score": None if mean is None else round(mean, 3), "done": done, "started": attempted > 0}


def recommended_day(start: date | None, today: date, total: int = TOTAL_DAYS) -> int:
    if start is None:
        return 1
    return max(1, min(total, (today - start).days + 1))


def calendar(start: date | None, today: date, progress: dict[int, dict], total: int = TOTAL_DAYS,
             prefix: str = "D") -> list[dict]:
    """Una celda por día del programa (40 días con prefijo D por omisión; Base 20 usa total=20, prefijo B)."""
    rec = recommended_day(start, today, total)
    cells = []
    for n in range(1, total + 1):
        p = progress.get(n) or {}
        if p.get("done"):
            state = COMPLETED
        elif n == rec and start is not None:
            state = TODAY
        elif p.get("started"):
            state = IN_PROGRESS
        elif start is not None and n < rec:
            state = LATE
        else:
            state = PENDING
        cells.append({
            "n": n, "code": f"{prefix}{n:02d}", "date": (start + timedelta(days=n - 1)) if start else None,
            "state": state, "label": LABELS[state], "progress": p,
        })
    return cells


def streak(activity_dates: set[date], today: date) -> int:
    """Días consecutivos con práctica, terminando hoy (o ayer si hoy aún no practica)."""
    day = today if today in activity_dates else today - timedelta(days=1)
    n = 0
    while day in activity_dates:
        n += 1
        day -= timedelta(days=1)
    return n
