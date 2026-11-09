"""Estimación del diagnóstico por habilidad (§4).

Reglas:
- Cada habilidad se estima por separado; nunca se asume que todo es B1.
- Las evidencias tienen tipo: "auto" (ítem cerrado corregido), "self" (autoevaluación
  con rúbrica) o "human" (evaluador humano).
- Con muestra insuficiente se pide más evidencia en vez de emitir una etiqueta precisa.
- La autoevaluación sola nunca da confianza mayor que «baja».
- Las bandas son internas del itinerario, no certificaciones MCER.
"""
from __future__ import annotations

SKILLS = {
    "reading": "Lectura",
    "listening": "Escucha",
    "writing": "Escritura",
    "speaking": "Habla",
    "interaction": "Interacción",
    "lexis_grammar": "Léxico y estructuras",
}

KIND_WEIGHT = {"human": 1.0, "auto": 1.0, "self": 0.5}

BANDS = (
    (0.35, "A2 (posible brecha)"),
    (0.55, "B1 inicial"),
    (0.75, "B1"),
    (1.01, "B1+ o superior"),
)


def band(score: float) -> str:
    for limit, label in BANDS:
        if score < limit:
            return label
    return BANDS[-1][1]


def estimate_skill(evidence: list[dict]) -> dict:
    n_auto = sum(1 for e in evidence if e["kind"] == "auto")
    n_self = sum(1 for e in evidence if e["kind"] == "self")
    n_human = sum(1 for e in evidence if e["kind"] == "human")
    if not evidence:
        return {"level": None, "score": None, "confidence": "insuficiente", "n": 0, "request_more": True,
                "note": "Sin evidencia todavía."}
    wsum = sum(KIND_WEIGHT[e["kind"]] for e in evidence)
    score = sum(KIND_WEIGHT[e["kind"]] * float(e["score"]) for e in evidence) / wsum

    if n_auto + n_human == 0:
        confidence, note = "baja", "Solo autoevaluación: estimación provisional que requiere revisión humana o más evidencia."
    elif n_human >= 1 and n_auto >= 3:
        confidence, note = "alta", ""
    elif n_auto >= 6 or n_human >= 1:
        confidence, note = "media", ""
    elif n_auto >= 3:
        confidence, note = "media", "Muestra breve; se confirmará con el desempeño en los capítulos."
    else:
        return {"level": None, "score": round(score, 3), "confidence": "insuficiente", "n": len(evidence),
                "request_more": True, "note": "Muestra insuficiente: se solicitará evidencia adicional."}
    return {"level": band(score), "score": round(score, 3), "confidence": confidence,
            "n": len(evidence), "request_more": confidence == "baja", "note": note}


def estimate(evidence: list[dict]) -> dict[str, dict]:
    by_skill: dict[str, list[dict]] = {s: [] for s in SKILLS}
    for e in evidence:
        if e["skill"] in by_skill:
            by_skill[e["skill"]].append(e)
    return {s: estimate_skill(ev) for s, ev in by_skill.items()}


# Bloque diario del plan de 40 días donde se trabaja cada habilidad.
SKILL_BLOCKS = {
    "reading": "📄 Lectura",
    "listening": "🎧 Escucha",
    "writing": "✍️ Escritura",
    "speaking": "🎙️ Habla",
    "interaction": "🎙️ Habla (preguntas y respuestas; semana 6)",
    "lexis_grammar": "🔤 Vocabulario y 🧩 Gramática",
}


def base_first(reinforcement: list[str]) -> bool:
    """¿Conviene hacer primero (o en paralelo) el plan base de 20 días? Sí, si hay brecha en léxico/estructuras
    o en lectura, o en dos o más habilidades."""
    return bool({"lexis_grammar", "reading"} & set(reinforcement)) or len(reinforcement) >= 2


def recommend(estimates: dict[str, dict]) -> dict:
    """Recomendación para el plan de 40 días: dónde poner más atención y qué falta medir.

    El plan siempre empieza en el día 1 (cada día usa lo anterior); el diagnóstico no salta días,
    sino que indica qué bloques diarios reforzar. ``start_chapter`` se conserva por compatibilidad
    con los capítulos complementarios.
    """
    reinforcement = [s for s, e in estimates.items() if e["level"] == "A2 (posible brecha)"]
    pending = [s for s, e in estimates.items() if e["request_more"]]
    strong = [s for s, e in estimates.items() if e["level"] == "B1+ o superior" and e["confidence"] != "baja"]
    notes = []
    if {"reading", "lexis_grammar"} <= set(strong):
        notes.append("Lectura y léxico fuertes: las semanas 1 y 2 del plan te servirán de repaso; puedes avanzarlas más rápido.")
    if reinforcement:
        notes.append("No necesitas reiniciar el plan: basta con unos minutos extra en los bloques indicados.")
    if pending:
        notes.append("Algunas habilidades necesitan más evidencia: completa esas partes del diagnóstico y recalcula.")
    return {"start_chapter": "C01", "start_day": 1, "base_first": base_first(reinforcement), "reinforcement": reinforcement, "pending_evidence": pending,
            "strong": strong, "notes": notes,
            "plan_focus": [{"skill": s, "block": SKILL_BLOCKS[s]} for s in reinforcement if s in SKILL_BLOCKS]}
