"""Repaso espaciado (§3, §11).

Intervalos provisionales 1, 3, 7, 14 y 30 días. Reglas:
- Acierto sin ayuda: avanza una etapa.
- Acierto con ayuda (traducción, transcripción, pista): no avanza; vuelve en 1 día.
  Acertar con traducción no es la misma evidencia que responder sin ella.
- Error: vuelve a la etapa 0 (mañana).
- Una agenda incumplida no se convierte en deuda: se atiende un máximo diario y el
  resto se redistribuye en los días siguientes respetando el mismo tope.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta

DEFAULT_INTERVALS = (1, 3, 7, 14, 30)
DEFAULT_DAILY_CAP = 20


@dataclass(frozen=True)
class Item:
    key: str
    due: date
    stage: int = 0
    blocking: bool = False  # brecha que impide la siguiente tarea → prioridad


def first_due(today: date, intervals=DEFAULT_INTERVALS) -> tuple[int, date]:
    return 0, today + timedelta(days=intervals[0])


def next_review(stage: int, correct: bool, helped: bool, today: date,
                intervals=DEFAULT_INTERVALS) -> tuple[int, date]:
    last = len(intervals) - 1
    if not correct:
        new_stage = 0
    elif helped:
        return stage, today + timedelta(days=intervals[0])
    else:
        new_stage = min(stage + 1, last)
    return new_stage, today + timedelta(days=intervals[new_stage])


def is_consolidated(stage: int, intervals=DEFAULT_INTERVALS) -> bool:
    return stage >= len(intervals) - 1


def plan_day(items: list[Item], today: date, cap: int = DEFAULT_DAILY_CAP,
             future_load: dict[date, int] | None = None) -> tuple[list[Item], list[Item]]:
    """Devuelve (para_hoy, reprogramados). Los reprogramados traen su nueva fecha."""
    due = [i for i in items if i.due <= today]
    due.sort(key=lambda i: (not i.blocking, i.due, i.stage, i.key))
    today_list, rest = due[:cap], due[cap:]
    load = dict(future_load or {})
    moved, day = [], today + timedelta(days=1)
    for item in rest:
        while load.get(day, 0) >= cap:
            day += timedelta(days=1)
        load[day] = load.get(day, 0) + 1
        moved.append(replace(item, due=day))
    return today_list, moved
