"""Motivación de los planes por días: metas intermedias, fecha estimada de término y anillo de avance."""
from __future__ import annotations

import math
from datetime import date, timedelta

TOTAL = 40

MILESTONES = [
    (1, "Primer paso", "🏁"),
    (7, "Semana 1", "⭐"),
    (14, "Dos semanas", "🔥"),
    (21, "Voz pasiva", "🧩"),
    (28, "Resultados", "📈"),
    (35, "Discusión", "💬"),
    (40, "Presentación final", "🇺🇸"),
]


def milestones(done: int, items=None) -> list[dict]:
    """Metas intermedias; ``items`` = [(día, etiqueta, ícono), …] (por omisión, las del plan de 40 días)."""
    out, next_set = [], False
    for n, label, icon in (items or MILESTONES):
        reached = done >= n
        is_next = not reached and not next_set
        next_set = next_set or is_next
        out.append({"n": n, "label": label, "icon": icon, "reached": reached, "next": is_next,
                    "missing": max(0, n - done)})
    return out


def projection(start: date | None, today: date, done: int, total: int = TOTAL) -> dict | None:
    """Fecha estimada de término si se completa un día por día desde hoy."""
    if start is None:
        return None
    planned_end = start + timedelta(days=total - 1)
    left = total - done
    finish = today + timedelta(days=max(0, left - 1)) if left else today
    return {"planned_end": planned_end, "finish": finish, "left": left,
            "on_track": finish <= planned_end, "delay_days": max(0, (finish - planned_end).days)}


def ring_segments(states: list[str], cx: float = 110, cy: float = 110, r_out: float = 100, r_in: float = 76,
                  gap_deg: float = 1.6) -> list[dict]:
    """Arcos SVG para un anillo con un segmento por día (40, 20…), empezando arriba."""
    n = len(states)
    step = 360 / n
    segs = []
    for i, state in enumerate(states):
        a0 = math.radians(-90 + i * step + gap_deg / 2)
        a1 = math.radians(-90 + (i + 1) * step - gap_deg / 2)

        def pt(r, a):
            return f"{cx + r * math.cos(a):.2f} {cy + r * math.sin(a):.2f}"
        d = (f"M {pt(r_out, a0)} A {r_out} {r_out} 0 0 1 {pt(r_out, a1)} "
             f"L {pt(r_in, a1)} A {r_in} {r_in} 0 0 0 {pt(r_in, a0)} Z")
        segs.append({"n": i + 1, "d": d, "state": state})
    return segs
