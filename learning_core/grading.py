"""Motor de corrección.

- Ítems cerrados: corrección determinista (§15: no se usa IA para esto).
- Respuestas abiertas (escritura, oral): NO se puntúan automáticamente. Se entrega
  una retroalimentación orientativa basada en reglas del contenido (máximo tres
  prioridades, §3) y el intento queda pendiente de rúbrica (autoevaluación o
  evaluador humano). La etiqueta SIMULATED_NOTICE se muestra siempre.

Formato de respuestas (lo arma la vista desde el POST):
  choice      {"option": "b", "justification": "...", "evidence": ["s2"]}
  cloze       {"gaps": {"1": "while", "2": "..."}}
  ordering    {"order": ["m2", "m1", ...], "justification": "..."}
  numeric     {"fields": {"f1": "15", ...}}
  short_text  {"text": "..."}
  listening   {"questions": {"q1": {"option": "a"} | {"fields": {...}}}}
  dictation   {"text": "..."}
  open_text   {"text": "..."}
  oral        {"recording_id": 12 | None, "transcript": "...", "no_mic": bool}
"""
from __future__ import annotations

import difflib
from dataclasses import asdict, dataclass, field

from .normalize import contains_phrase, normalize, parse_number, tokens, word_count

MAX_FEEDBACK = 3
SIMULATED_NOTICE = (
    "Retroalimentación orientativa automática basada en reglas del contenido. "
    "No es IA ni una evaluación final: la nota de esta tarea se asigna con rúbrica."
)
TRANSCRIPT_ONLY_NOTICE = (
    "Comentario basado solo en la transcripción del reconocimiento de voz. "
    "La evaluación fonética (sonidos, entonación) no está disponible."
)

CLOSED_TYPES = {"choice", "cloze", "ordering", "numeric", "short_text", "listening", "dictation"}
OPEN_TYPES = {"open_text", "oral"}
ALL_TYPES = CLOSED_TYPES | OPEN_TYPES

# Estados de un intento
GRADED = "corregido"
PENDING_RUBRIC = "pendiente_rubrica"
PENDING_EVIDENCE = "pendiente_evidencia"
INCOMPLETE = "incompleto"


@dataclass
class GradeResult:
    status: str
    score: float | None = None  # 0..1 para ítems cerrados
    correct: bool | None = None
    feedback: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)
    notices: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["feedback"] = d["feedback"][:MAX_FEEDBACK]
        return d


class ActivityError(ValueError):
    pass


def grade(activity: dict, response: dict) -> GradeResult:
    kind = activity.get("type")
    fn = _GRADERS.get(kind)
    if fn is None:
        raise ActivityError(f"Tipo de actividad desconocido: {kind!r}")
    result = fn(activity, response or {})
    result.feedback = result.feedback[:MAX_FEEDBACK]
    return result


# ---------------------------------------------------------------- cerrados

def _grade_choice(activity: dict, response: dict) -> GradeResult:
    option = response.get("option")
    if not option:
        return GradeResult(INCOMPLETE, feedback=["Elige una opción antes de enviar."])
    justification = (response.get("justification") or "").strip()
    if activity.get("justify") and word_count(justification) < 3:
        return GradeResult(
            INCOMPLETE,
            feedback=["Agrega una justificación breve (al menos tres palabras) antes de ver la respuesta."],
        )
    options = {o["id"]: o for o in activity["options"]}
    if option not in options:
        return GradeResult(INCOMPLETE, feedback=["La opción enviada no existe en esta actividad."])
    correct_option = option == activity["answer"]
    feedback = []
    chosen_fb = options[option].get("feedback")
    if chosen_fb:
        feedback.append(chosen_fb)
    elif not correct_option and activity.get("explanation"):
        feedback.append(activity["explanation"])

    score = 1.0 if correct_option else 0.0
    details = {"option": option, "answer": activity["answer"]}
    evidence = activity.get("evidence")
    if evidence:
        selected = set(response.get("evidence") or [])
        expected = set(evidence["answer"])
        valid_ids = {s["id"] for s in evidence["sentences"]}
        selected &= valid_ids
        hits = selected & expected
        wrong = selected - expected
        evidence_ok = bool(hits) and not wrong
        details.update({"evidence_selected": sorted(selected), "evidence_answer": sorted(expected)})
        # La opción vale 60 %, la evidencia 40 %: elegir bien sin evidencia no es la misma prueba.
        score = (0.6 if correct_option else 0.0) + (0.4 if evidence_ok else 0.0)
        if not selected:
            feedback.append("Marca la oración del texto que respalda tu elección.")
        elif not evidence_ok:
            feedback.append(evidence.get("feedback") or "Revisa la evidencia: alguna oración marcada no respalda la respuesta.")
        correct = correct_option and evidence_ok
    else:
        correct = correct_option
    if correct and activity.get("explanation") and not feedback:
        feedback.append(activity["explanation"])
    return GradeResult(GRADED, score=round(score, 4), correct=correct, feedback=feedback, details=details)


def _accepts(spec: dict, given: str) -> bool:
    g = normalize(given)
    return any(g == normalize(a) for a in spec.get("accept", []))


def _near_feedback(spec: dict, given: str) -> str | None:
    g = normalize(given)
    for variant, fb in (spec.get("near") or {}).items():
        if g == normalize(variant):
            return fb
    return None


def _grade_cloze(activity: dict, response: dict) -> GradeResult:
    gaps = activity["gaps"]
    given = response.get("gaps") or {}
    if not any((given.get(k) or "").strip() for k in gaps):
        return GradeResult(INCOMPLETE, feedback=["Completa al menos un espacio."])
    right, feedback, per_gap = 0, [], {}
    for key, spec in gaps.items():
        value = given.get(key, "")
        ok = _accepts(spec, value)
        per_gap[key] = ok
        if ok:
            right += 1
            continue
        near = _near_feedback(spec, value)
        if near:
            feedback.append(f"Espacio {key}: {near}")
        elif spec.get("hint"):
            feedback.append(f"Espacio {key}: {spec['hint']}")
        else:
            feedback.append(f"Espacio {key}: revisa esta forma en su contexto.")
    score = right / len(gaps)
    return GradeResult(
        GRADED, score=round(score, 4), correct=right == len(gaps), feedback=feedback,
        details={"gaps": per_gap},
    )


def _grade_ordering(activity: dict, response: dict) -> GradeResult:
    answer = list(activity["answer"])
    order = [x for x in (response.get("order") or []) if x]
    if sorted(order) != sorted(answer):
        return GradeResult(INCOMPLETE, feedback=["Asigna una posición distinta a cada elemento."])
    if activity.get("justify") and word_count(response.get("justification") or "") < 3:
        return GradeResult(INCOMPLETE, feedback=["Justifica brevemente el orden elegido."])
    in_place = sum(1 for a, b in zip(order, answer) if a == b)
    score = in_place / len(answer)
    feedback = []
    if order != answer:
        first_wrong = next(i for i, (a, b) in enumerate(zip(order, answer)) if a != b)
        feedback.append(activity.get("explanation") or f"Revisa a partir de la posición {first_wrong + 1}.")
    elif activity.get("explanation"):
        feedback.append(activity["explanation"])
    return GradeResult(
        GRADED, score=round(score, 4), correct=order == answer, feedback=feedback,
        details={"order": order, "answer": answer},
    )


def _grade_numeric_fields(fields: list[dict], given: dict) -> tuple[int, list[str], dict]:
    right, feedback, per_field = 0, [], {}
    for f in fields:
        value = parse_number(given.get(f["id"]))
        tol = float(f.get("tolerance", 0))
        ok = value is not None and abs(value - float(f["answer"])) <= tol + 1e-9
        per_field[f["id"]] = ok
        if ok:
            right += 1
        elif value is None:
            feedback.append(f"{f['label']}: escribe un número (puedes usar coma o punto decimal).")
        else:
            feedback.append(f"{f['label']}: {f.get('hint') or 'revisa el valor en la fuente.'}")
    return right, feedback, per_field


def _grade_numeric(activity: dict, response: dict) -> GradeResult:
    given = response.get("fields") or {}
    if not any(str(given.get(f["id"], "")).strip() for f in activity["fields"]):
        return GradeResult(INCOMPLETE, feedback=["Escribe al menos un valor."])
    right, feedback, per_field = _grade_numeric_fields(activity["fields"], given)
    n = len(activity["fields"])
    if right == n and activity.get("explanation"):
        feedback.append(activity["explanation"])
    return GradeResult(GRADED, score=round(right / n, 4), correct=right == n, feedback=feedback,
                       details={"fields": per_field})


def _grade_short_text(activity: dict, response: dict) -> GradeResult:
    text = response.get("text") or ""
    if not text.strip():
        return GradeResult(INCOMPLETE, feedback=["Escribe tu respuesta: recuperar la expresión es el ejercicio."])
    ok = _accepts(activity, text)
    feedback = []
    if not ok:
        near = _near_feedback(activity, text)
        feedback.append(near or activity.get("hint") or "No coincide con la expresión trabajada.")
        if activity.get("show_answer_on_error", True):
            feedback.append(f"Forma esperada: «{activity['accept'][0]}».")
    elif activity.get("explanation"):
        feedback.append(activity["explanation"])
    return GradeResult(GRADED, score=1.0 if ok else 0.0, correct=ok, feedback=feedback,
                       details={"given": normalize(text)})


def _grade_listening(activity: dict, response: dict) -> GradeResult:
    answers = response.get("questions") or {}
    total, answered, earned, feedback, per_q = 0, 0, 0.0, [], {}
    for q in activity["questions"]:
        total += 1
        sub = dict(q)
        sub.setdefault("type", "choice" if "options" in q else "numeric")
        r = grade(sub, answers.get(q["id"], {}))
        per_q[q["id"]] = r.status == GRADED and bool(r.correct)
        if r.status != GRADED:
            feedback.append(f"{q.get('label', q['id'])}: sin respuesta.")
            continue
        answered += 1
        earned += r.score or 0.0
        if not r.correct and r.feedback:
            feedback.append(f"{q.get('label', q['id'])}: {r.feedback[0]}")
    if answered == 0:
        return GradeResult(INCOMPLETE, feedback=["Responde las preguntas antes de ver la transcripción."])
    score = earned / total if total else 0.0
    return GradeResult(GRADED, score=round(score, 4), correct=all(per_q.values()), feedback=feedback,
                       details={"questions": per_q})


def _grade_dictation(activity: dict, response: dict) -> GradeResult:
    text = response.get("text") or ""
    if not text.strip():
        return GradeResult(INCOMPLETE, feedback=["Escribe lo que escuchaste."])
    best_ratio, best_target = 0.0, None
    for target in [activity["answer"]] + list(activity.get("accept", [])):
        ratio = difflib.SequenceMatcher(None, tokens(target), tokens(text)).ratio()
        if ratio > best_ratio:
            best_ratio, best_target = ratio, target
    target_tokens, given_tokens = tokens(best_target), tokens(text)
    sm = difflib.SequenceMatcher(None, target_tokens, given_tokens)
    feedback = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            continue
        expected = " ".join(target_tokens[i1:i2]) or "—"
        got = " ".join(given_tokens[j1:j2]) or "—"
        feedback.append(f"Se esperaba «{expected}» y escribiste «{got}».")
    correct = best_ratio >= activity.get("threshold", 0.9)
    return GradeResult(GRADED, score=round(best_ratio, 4), correct=correct, feedback=feedback,
                       details={"ratio": round(best_ratio, 4)})


# ---------------------------------------------------------------- abiertos

def run_checks(checks: list[dict], text: str) -> tuple[list[str], list[str]]:
    """Aplica reglas del contenido. Devuelve (ids cumplidos, mensajes de prioridad en orden)."""
    passed, messages = [], []
    for c in checks or []:
        ok = True
        if c.get("any_of"):
            ok = ok and any(contains_phrase(text, p) for p in c["any_of"])
        if c.get("all_of"):
            ok = ok and all(contains_phrase(text, p) for p in c["all_of"])
        if c.get("none_of"):
            ok = ok and not any(contains_phrase(text, p) for p in c["none_of"])
        if c.get("min_count"):
            hits = sum(1 for p in c.get("phrases", []) if contains_phrase(text, p))
            ok = ok and hits >= int(c["min_count"])
        if ok:
            passed.append(c["id"])
        else:
            messages.append(c["feedback"])
    return passed, messages


def _grade_open_text(activity: dict, response: dict) -> GradeResult:
    text = response.get("text") or ""
    n = word_count(text)
    if n == 0:
        return GradeResult(INCOMPLETE, feedback=["Escribe tu texto antes de enviarlo."])
    feedback = []
    lo, hi = activity.get("min_words"), activity.get("max_words")
    if lo and n < lo:
        feedback.append(f"Tu texto tiene {n} palabras; la tarea pide al menos {lo}.")
    if hi and n > hi:
        feedback.append(f"Tu texto tiene {n} palabras; la tarea pide como máximo {hi}. Prioriza lo esencial.")
    passed, messages = run_checks(activity.get("checks"), text)
    feedback.extend(messages)
    status = PENDING_RUBRIC if activity.get("rubric") else GRADED
    return GradeResult(
        status, feedback=feedback, details={"word_count": n, "checks_passed": passed},
        notices=[SIMULATED_NOTICE],
    )


def _grade_oral(activity: dict, response: dict) -> GradeResult:
    transcript = (response.get("transcript") or "").strip()
    if not response.get("recording_id"):
        if response.get("no_mic"):
            return GradeResult(
                PENDING_EVIDENCE,
                feedback=["Modo sin micrófono: puedes seguir estudiando, pero esta habilidad oral queda pendiente de evidencia."],
            )
        return GradeResult(INCOMPLETE, feedback=["Graba tu respuesta antes de enviarla."])
    feedback, notices, details = [], [], {"recording_id": response["recording_id"]}
    if transcript:
        passed, messages = run_checks(activity.get("checks"), transcript)
        feedback.extend(messages)
        details["checks_passed"] = passed
        notices.append(TRANSCRIPT_ONLY_NOTICE)
    else:
        notices.append("Sin transcripción: no hay comentario automático. Escucha tu grabación y aplica la rúbrica.")
    notices.append(SIMULATED_NOTICE)
    status = PENDING_RUBRIC if activity.get("rubric") else GRADED
    return GradeResult(status, feedback=feedback, details=details, notices=notices)


_GRADERS = {
    "choice": _grade_choice,
    "cloze": _grade_cloze,
    "ordering": _grade_ordering,
    "numeric": _grade_numeric,
    "short_text": _grade_short_text,
    "listening": _grade_listening,
    "dictation": _grade_dictation,
    "open_text": _grade_open_text,
    "oral": _grade_oral,
}
