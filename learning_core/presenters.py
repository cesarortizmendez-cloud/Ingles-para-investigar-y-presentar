"""Preparación de actividades para las plantillas (sin Django)."""
from __future__ import annotations

from .contract import CLOZE_GAP


def cloze_segments(text: str) -> list[dict]:
    """'A [[1]] B' → [{'text': 'A '}, {'gap': '1'}, {'text': ' B'}]."""
    out, pos = [], 0
    for m in CLOZE_GAP.finditer(text):
        if m.start() > pos:
            out.append({"text": text[pos:m.start()]})
        out.append({"gap": m.group(1)})
        pos = m.end()
    if pos < len(text):
        out.append({"text": text[pos:]})
    return out


def pick_variant(activities: list[dict], specialty: str) -> list[dict]:
    """De las actividades con variante por especialidad, deja la del alumno (o la común).

    Las actividades sin 'variant_group' se devuelven siempre. Dentro de un grupo se
    prefiere la especialidad del alumno; si no existe, la primera del grupo.
    """
    out, groups = [], {}
    for act in activities:
        g = act.get("variant_group")
        if not g:
            out.append(act)
            continue
        groups.setdefault(g, []).append(act)
        if len(groups[g]) == 1:
            out.append({"__group__": g})
    result = []
    for item in out:
        if "__group__" in item:
            group = groups[item["__group__"]]
            chosen = next((a for a in group if a.get("specialty") == specialty), group[0])
            result.append(chosen)
        else:
            result.append(item)
    return result
