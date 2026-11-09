"""Programas por días (sin Django): Base 20 → Plan 40 → (Avanzado 20, próximamente).

Cada programa usa el mismo motor (calendario, anillo, bloques diarios, repaso espaciado) y se
distingue por la letra de sus códigos de día: B01…B20, D01…D40, A01…A20. Así los intentos,
el repaso y el portafolio de cada programa nunca se mezclan.
"""
from __future__ import annotations

PROGRAMS: tuple[dict, ...] = (
    {"slug": "base20", "prefix": "B", "total": 20, "file": "base20.json", "start_field": "base_start",
     "short": "Base 20", "name": "Plan base de 20 días", "order": 1,
     "role": "Preparatorio: lo básico y las situaciones de todos los días, para llegar listo al plan de 40 días."},
    {"slug": "plan40", "prefix": "D", "total": 40, "file": "plan40.json", "start_field": "plan_start",
     "short": "Plan 40", "name": "Plan intensivo de 40 días", "order": 2,
     "role": "Principal: inglés para investigar y presentar, en seis semanas."},
)
BY_SLUG = {p["slug"]: p for p in PROGRAMS}
BY_PREFIX = {p["prefix"]: p for p in PROGRAMS}
MAIN = "plan40"


def get(slug: str) -> dict:
    return BY_SLUG[slug]


def for_code(code: str) -> dict | None:
    """Programa al que pertenece un código de día (B05, D12…); None si no es un día válido."""
    if len(code or "") != 3 or not code[1:].isdigit():
        return None
    prog = BY_PREFIX.get(code[0])
    if prog and 1 <= int(code[1:]) <= prog["total"]:
        return prog
    return None


def day_code(slug: str, n: int) -> str:
    return f"{BY_SLUG[slug]['prefix']}{n:02d}"
