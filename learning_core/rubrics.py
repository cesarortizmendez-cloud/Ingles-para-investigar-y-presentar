"""Rúbricas iniciales (§12). Son reglas de producto a pilotear, no puntuaciones MCER."""
from __future__ import annotations

ANCHORS = {
    0: "No hay evidencia evaluable",
    1: "No permite cumplir el objetivo",
    2: "Logro parcial con dificultades",
    3: "Logro claro con fallas menores",
    4: "Logro sólido y autónomo",
}

TASK_PASS_TOTAL = 70.0
ESSENTIAL_MIN = 2

# (código, nombre, peso). Los pesos de cada rúbrica suman 100.
RUBRICS: dict[str, dict] = {
    "oral": {
        "title": "Exposición oral",
        "criteria": [
            ("task", "Cumplimiento de la tarea y fidelidad al contenido", 25),
            ("organization", "Organización y coherencia", 20),
            ("intelligibility", "Inteligibilidad", 20),
            ("resources", "Recursos lingüísticos y precisión", 20),
            ("fluency", "Fluidez", 15),
        ],
        "default_essential": ["task", "intelligibility"],
    },
    "interaction": {
        "title": "Interacción",
        "criteria": [
            ("relevance", "Pertinencia y comprensión de la pregunta", 25),
            ("turns", "Manejo de turnos y aclaraciones", 20),
            ("intelligibility", "Inteligibilidad", 20),
            ("resources", "Recursos lingüísticos", 20),
            ("fluency", "Fluidez", 15),
        ],
        "default_essential": ["relevance", "intelligibility"],
    },
    "reading": {
        "title": "Lectura",
        "criteria": [
            ("ideas", "Identificación de ideas", 40),
            ("evidence", "Evidencia y relaciones", 30),
            ("inference", "Inferencias y límites", 20),
            ("vocabulary", "Vocabulario contextual", 10),
        ],
        "default_essential": ["ideas"],
    },
    "writing": {
        "title": "Escritura",
        "criteria": [
            ("fidelity", "Fidelidad y tarea", 35),
            ("organization", "Organización", 25),
            ("resources", "Recursos lingüísticos", 25),
            ("conventions", "Convenciones y atribución", 15),
        ],
        "default_essential": ["fidelity"],
    },
}

RATER_SELF = "autoevaluacion"
RATER_HUMAN = "humano"
RATER_AUTO = "automatico_orientativo"
RATERS = (RATER_SELF, RATER_HUMAN, RATER_AUTO)


class RubricError(ValueError):
    pass


def criteria(code: str) -> list[tuple[str, str, int]]:
    try:
        return RUBRICS[code]["criteria"]
    except KeyError as exc:
        raise RubricError(f"Rúbrica desconocida: {code!r}") from exc


def total(code: str, scores: dict[str, int]) -> float:
    """Suma de peso × puntuación/4 (0–100)."""
    result = 0.0
    for cid, _name, weight in criteria(code):
        if cid not in scores:
            raise RubricError(f"Falta la puntuación del criterio {cid!r}.")
        s = int(scores[cid])
        if s not in ANCHORS:
            raise RubricError(f"Puntuación fuera de rango en {cid!r}: {s}")
        result += weight * s / 4
    return round(result, 2)


def evaluate(code: str, scores: dict[str, int], essential: list[str] | None = None) -> dict:
    essential = list(essential if essential is not None else RUBRICS[code]["default_essential"])
    t = total(code, scores)
    weak = [c for c in essential if int(scores[c]) < ESSENTIAL_MIN]
    return {
        "rubric": code,
        "total": t,
        "essential": essential,
        "essential_below_min": weak,
        "passed": t >= TASK_PASS_TOTAL and not weak,
    }
