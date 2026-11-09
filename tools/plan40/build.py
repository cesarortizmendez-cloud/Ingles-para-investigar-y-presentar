"""Genera content/plan40.json y content/days/D01.json … D40.json a partir de los datos
de tools/plan40/week*.py. Uso:  python tools/plan40/build.py

Los datos editoriales (palabras, cápsulas, textos, preguntas) están en week1.py … week6.py.
Este script solo les da la estructura común de actividades, para que los 40 días sean
coherentes y validables con learning_core.contract.
"""
from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from learning_core import contract  # noqa: E402

import importlib  # noqa: E402

import meta  # noqa: E402

WEEKS = []
for _i in range(1, 7):
    try:
        WEEKS.append(importlib.import_module(f"week{_i}").DAYS)
    except ModuleNotFoundError:
        break

# Variantes ortográficas aceptadas (británico/estadounidense)
ALTS = {"analyse": ["analyze"], "analyses": ["analyzes"], "analysed": ["analyzed"], "analysing": ["analyzing"],
        "behaviour": ["behavior"], "centre": ["center"], "modelling": ["modeling"], "programme": ["program"],
        "organise": ["organize"], "organised": ["organized"], "utilisation": ["utilization"], "percent": ["per cent"]}


def accepts(form):
    return [form] + ALTS.get(form.lower(), [])

VERSION = "1.0.0"
PROV = {"author": "Equipo editorial del curso (Claude, revisión pendiente)", "license": "Original del proyecto",
        "year": 2026, "adaptation": "texto didáctico original; personajes y datos ficticios"}
QUALITY = {"authors": ["Claude (redacción inicial)"], "reviewed_by": "", "license": "Original del proyecto",
           "date": "2026-11-07", "changelog": [{"version": VERSION, "date": "2026-11-07", "change": "Plan 40 días, versión inicial."}]}
MINUTES = {"vocabulario": 25, "gramatica": 25, "escucha": 15, "lectura": 20, "habla": 15, "escritura": 10}


def gap_out(sentence: str, form: str) -> str:
    pat = re.compile(r"(?<!\w)" + re.escape(form) + r"(?!\w)", re.IGNORECASE)
    if not pat.search(sentence):
        raise ValueError(f"La forma «{form}» no aparece en el ejemplo: {sentence}")
    return pat.sub("[[{n}]]", sentence, count=1)


def underscores_to_gaps(sentences, start=1):
    """[("I ___ here.", ["am"], "pista"), …] → texto con [[n]] y dict de gaps."""
    parts, gaps = [], {}
    for i, item in enumerate(sentences, start=start):
        text, accept = item[0], item[1]
        hint = item[2] if len(item) > 2 else ""
        if text.count("___") != 1:
            raise ValueError(f"Cada oración de cloze necesita exactamente un ___: {text}")
        parts.append(f"({i}) " + text.replace("___", f"[[{i}]]"))
        gaps[str(i)] = {"accept": list(accept), **({"hint": hint} if hint else {})}
    return "  ".join(parts), gaps


def choice_q(qid, q):
    """q = (pregunta_es, [opciones], índice_correcto, explicación_es)."""
    prompt, opts, ans, expl = q
    return {"id": qid, "prompt": prompt, "label": prompt,
            "options": [{"id": chr(97 + i), "text": o} for i, o in enumerate(opts)],
            "answer": chr(97 + ans), **({"explanation": expl} if expl else {})}


def first_sentences(text: str, n: int = 2) -> list[str]:
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    return sents[:n]


REGISTER = "académico"


def lexis_entries(code, vocab):
    return [{"id": f"{code}-LX{i:02d}", "form": f, "meaning_es": es, "example": ex, "example_es": ex_es,
             "collocations": [], "family": [], "register": REGISTER, "confusions": ""}
            for i, (f, es, ex, ex_es) in enumerate(vocab, start=1)]


# ------------------------------------------------------------------ bloques
def block_vocab(code, vocab, rng):
    words = [{"form": f, "meaning_es": es, "example": ex, "example_es": ex_es} for f, es, ex, ex_es in vocab]
    res = {"id": f"{code}-RV", "type": "wordlist", "title": "Palabras y expresiones del día", "words": words,
           "fictional_data": True, "provenance": PROV}
    order = list(range(len(vocab)))
    rng.shuffle(order)
    cloze_idx, recall_idx = sorted(order[:6]), order[6:]
    acts = []
    text_parts, gaps = [], {}
    for k, i in enumerate(cloze_idx, start=1):
        f, es, ex, _ = vocab[i]
        text_parts.append(f"({k}) " + gap_out(ex, f).replace("{n}", str(k)))
        gaps[str(k)] = {"accept": accepts(f), "hint": f"Significa «{es}»."}
    acts.append({"id": f"{code}.1.a1", "type": "cloze", "role": "practice", "skill": "lexis_grammar",
                 "prompt": "Completa cada oración con la palabra o expresión del día que corresponde (sin mirar la lista).",
                 "text": "  ".join(text_parts), "gaps": gaps})
    for k, i in enumerate(recall_idx, start=2):
        f, es, ex, ex_es = vocab[i]
        acts.append({"id": f"{code}.1.a{k}", "type": "short_text", "role": "practice", "skill": "lexis_grammar",
                     "prompt": f"Escríbelo en inglés: «{es}»",
                     "accept": accepts(f), "hint": f"Empieza con «{f[:2]}…» · Ejemplo: {ex_es}"})
    f, es, ex, ex_es = vocab[recall_idx[0]]
    acts.append({"id": f"{code}.1.a{len(recall_idx) + 2}", "type": "dictation", "role": "practice", "skill": "listening",
                 "prompt": "Dictado: escucha la oración (puedes repetirla) y escríbela completa.",
                 "audio": {"text": ex, "voice": "en-US", "source": "sintetizada"}, "answer": ex})
    return res, {"id": f"{code}.1", "order": 1, "kind": "vocabulario", "minutes": MINUTES["vocabulario"],
                 "title": "Vocabulario: escuchar, repetir y recuperar",
                 "intro": "1) Escucha cada palabra y su ejemplo, y repítelos en voz alta. 2) Cierra la lista. "
                          "3) Responde sin mirar: recordar con esfuerzo es lo que fija la palabra. Mañana volverán en el repaso.",
                 "resources": [res["id"]], "activities": acts}


def block_grammar(code, g):
    res = {"id": f"{code}-RG", "type": "capsule", "title": g["title"], "explain": g["explain"], "form": g["form"],
           "examples": g["examples"], "tip": g.get("tip", ""), "fictional_data": True, "provenance": PROV}
    acts = []
    half = len(g["cloze"]) // 2
    for k, chunk in enumerate((g["cloze"][:half], g["cloze"][half:]), start=1):
        text, gaps = underscores_to_gaps(chunk, start=1)
        acts.append({"id": f"{code}.2.a{k}", "type": "cloze", "role": "practice", "skill": "lexis_grammar",
                     "prompt": "Completa cada espacio con la forma correcta.", "text": text, "gaps": gaps})
    for k, q in enumerate(g["choice"], start=3):
        cq = choice_q("x", q)
        acts.append({"id": f"{code}.2.a{k}", "type": "choice", "role": "practice", "skill": "lexis_grammar",
                     "prompt": cq["prompt"], "options": cq["options"], "answer": cq["answer"],
                     **({"explanation": cq["explanation"]} if cq.get("explanation") else {})})
    prompt, phrases = g["produce"]
    acts.append({"id": f"{code}.2.a{len(acts) + 1}", "type": "open_text", "role": "practice", "skill": "writing",
                 "prompt": prompt, "min_words": 10, "max_words": 80,
                 "checks": [{"id": "estructura", "any_of": phrases,
                             "feedback": "Usa la estructura de hoy (revisa la cápsula y los ejemplos)."}]})
    return res, {"id": f"{code}.2", "order": 2, "kind": "gramatica", "minutes": MINUTES["gramatica"],
                 "title": f"Gramática: {g['title']}",
                 "intro": "Lee la explicación en español, escucha los ejemplos y luego practica. Fíjate primero en el significado y después en la forma.",
                 "resources": [res["id"]], "activities": acts}


def block_listen(code, L, order=3):
    qs = [choice_q(f"q{i}", q) for i, q in enumerate(L["qs"], start=1)]
    acts = [{"id": f"{code}.{order}.a1", "type": "listening", "role": "practice", "skill": "listening",
             "prompt": f"{L['title']}: escucha sin leer y responde.",
             "audio": {"text": L["text"], "voice": L.get("voice", "en-US"), "source": "sintetizada"},
             "transcript": L["text"], "translation_es": L["es"], "questions": qs},
            {"id": f"{code}.{order}.a2", "type": "dictation", "role": "practice", "skill": "listening",
             "prompt": "Dictado breve de una oración del audio.",
             "audio": {"text": L["dictation"], "voice": L.get("voice", "en-US"), "source": "sintetizada"},
             "answer": L["dictation"]}]
    if L["dictation"] not in L["text"]:
        raise ValueError(f"{code}: la oración de dictado debe salir del audio")
    return {"id": f"{code}.{order}", "order": order, "kind": "escucha", "minutes": MINUTES["escucha"],
            "title": f"Escucha: {L['title']}",
            "intro": "Escucha dos veces sin leer. Primero la idea general, después los detalles. Si te cuesta, baja la velocidad a 0,85× (queda registrado como ayuda). La transcripción y la traducción se abren después de responder.",
            "resources": [], "activities": acts}


def block_read(code, R, order=4):
    res = {"id": f"{code}-RR", "type": "text", "title": R["title"], "body": R["text"], "translation_es": R["es"],
           "glossary": R.get("glossary", []), "audio": True, "fictional_data": True, "provenance": PROV}
    acts = []
    for i, q in enumerate(R["qs"], start=1):
        cq = choice_q("x", q)
        acts.append({"id": f"{code}.{order}.a{i}", "type": "choice", "role": "practice", "skill": "reading",
                     "prompt": cq["prompt"], "options": cq["options"], "answer": cq["answer"],
                     **({"explanation": cq["explanation"]} if cq.get("explanation") else {})})
    return res, {"id": f"{code}.{order}", "order": order, "kind": "lectura", "minutes": MINUTES["lectura"],
                 "title": f"Lectura: {R['title']}",
                 "intro": "Lee primero sin traducción y subraya mentalmente las palabras del día. Escucha el texto completo mientras lo sigues con la vista. Usa la traducción solo al final, para comprobar.",
                 "resources": [res["id"]], "activities": acts}


def block_speak(code, S, read_text, vocab_forms, order=5, rubric=None):
    shadow = " ".join(first_sentences(read_text, 2))
    acts = [{"id": f"{code}.{order}.a1", "type": "oral", "role": "practice", "skill": "speaking",
             "prompt": "Shadowing: escucha el modelo frase por frase e imítalo al mismo tiempo (ritmo, pausas, acento). Graba tu mejor versión y compárala.",
             "model": {"text": shadow, "voice": "en-US", "source": "sintetizada",
                       "chunks": first_sentences(read_text, 2)},
             "min_seconds": 5, "max_seconds": 60,
             "self_check": ["Hice las pausas en los mismos lugares que el modelo.",
                            "Pronuncié las terminaciones (-s, -ed) sin agregar vocales.",
                            "Lo repetí al menos tres veces antes de grabar."]}]
    oral = {"id": f"{code}.{order}.a2", "type": "oral", "role": "practice", "skill": "speaking",
            "prompt": S["prompt"], "min_seconds": S.get("min", 30), "max_seconds": S.get("max", 90),
            "checks": [{"id": "vocab", "min_count": 2, "phrases": vocab_forms,
                        "feedback": "Intenta usar al menos dos palabras o expresiones del día."}] if vocab_forms else []}
    if S.get("model"):
        oral["model"] = {"text": S["model"], "voice": "en-US", "source": "sintetizada"}
    if rubric:
        oral["rubric"] = rubric
    acts.append(oral)
    return {"id": f"{code}.{order}", "order": order, "kind": "habla", "minutes": MINUTES["habla"],
            "title": "Habla: imitar y luego producir",
            "intro": "Primero imitas (shadowing) para ganar ritmo; después hablas con tus propias palabras. Puedes tener notas de tres o cuatro palabras, pero no leas un guion.",
            "resources": [], "activities": acts}


def block_write(code, W, vocab_forms, grammar_phrases, order=6, rubric=None):
    checks = []
    if vocab_forms:
        checks.append({"id": "vocab", "min_count": 3, "phrases": vocab_forms,
                       "feedback": "Incluye al menos tres palabras o expresiones del día."})
    if grammar_phrases:
        checks.append({"id": "gram", "any_of": grammar_phrases, "feedback": "Usa la estructura gramatical del día."})
    act = {"id": f"{code}.{order}.a1", "type": "open_text", "role": "practice", "skill": "writing",
           "prompt": W["prompt"], "min_words": W.get("min", 40), "max_words": W.get("max", 100), "checks": checks}
    if rubric:
        act["rubric"] = rubric
    return {"id": f"{code}.{order}", "order": order, "kind": "escritura", "minutes": MINUTES["escritura"],
            "title": "Escritura breve", "intro": "Escribe sin traductor. Es mejor un texto corto y correcto que uno largo copiado.",
            "resources": [], "activities": [act]}


# ------------------------------------------------------------------ días
def build_learning_day(d, prefix="D"):
    n = d["n"]
    code = f"{prefix}{n:02d}"
    rng = random.Random(code)
    vocab = d["vocab"]
    assert len(vocab) == 12, f"{code}: necesita 12 palabras"
    rv, b1 = block_vocab(code, vocab, rng)
    rg, b2 = block_grammar(code, d["grammar"])
    b3 = block_listen(code, d["listen"])
    rr, b4 = block_read(code, d["read"])
    forms = [v[0] for v in vocab]
    b5 = block_speak(code, d["speak"], d["read"]["text"], forms)
    b6 = block_write(code, d["write"], forms, d["grammar"]["produce"][1])
    return {
        "id": code, "kind": "day", "version": VERSION, "status": "borrador",
        "title": d["title"], "day": n, "week": d["week"], "day_type": "aprendizaje", "intro": d["intro"],
        "objectives": [{"id": f"{code}-O{i}", "text": t} for i, t in enumerate(d["goals"], start=1)],
        "language_focus": {"lexis": lexis_entries(code, vocab), "grammar": [{"id": f"{code}-G1", "topic": d["grammar"]["title"]}],
                           "pronunciation": []},
        "resources": [rv, rg, rr], "lessons": [b1, b2, b3, b4, b5, b6], "quality": QUALITY,
    }


def build_review_day(d, week_days, final=False, prefix="D"):
    n = d["n"]
    code = f"{prefix}{n:02d}"
    rng = random.Random(code)
    pool = [v for wd in week_days for v in wd["vocab"]]
    rng.shuffle(pool)
    acts = []
    sample = pool[:12]
    text_parts, gaps = [], {}
    for k, (f, es, ex, _) in enumerate(sample[:6], start=1):
        text_parts.append(f"({k}) " + gap_out(ex, f).replace("{n}", str(k)))
        gaps[str(k)] = {"accept": accepts(f), "hint": f"Significa «{es}»."}
    acts.append({"id": f"{code}.1.a1", "type": "cloze", "role": "check", "skill": "lexis_grammar",
                 "prompt": "Repaso acumulado: completa con palabras de la semana (sin mirar).",
                 "text": "  ".join(text_parts), "gaps": gaps})
    for k, (f, es, _ex, ex_es) in enumerate(sample[6:12], start=2):
        acts.append({"id": f"{code}.1.a{k}", "type": "short_text", "role": "check", "skill": "lexis_grammar",
                     "prompt": f"Escríbelo en inglés: «{es}»", "accept": accepts(f), "hint": f"Ejemplo: {ex_es}"})
    b1 = {"id": f"{code}.1", "order": 1, "kind": "vocabulario", "minutes": MINUTES["vocabulario"],
          "title": "Repaso acumulado de vocabulario", "resources": [],
          "intro": "Sin lista: recupera de memoria. Lo que falles volverá mañana en el repaso espaciado.", "activities": acts}
    g_acts = []
    cl = [wd["grammar"]["cloze"][-1] for wd in week_days]
    for k in range(0, len(cl), 3):
        text, gps = underscores_to_gaps(cl[k:k + 3], start=1)
        g_acts.append({"id": f"{code}.2.a{len(g_acts) + 1}", "type": "cloze", "role": "check", "skill": "lexis_grammar",
                       "prompt": "Repaso mixto de la gramática de la semana.", "text": text, "gaps": gps})
    for wd in week_days:
        cq = choice_q("x", wd["grammar"]["choice"][-1])
        g_acts.append({"id": f"{code}.2.a{len(g_acts) + 1}", "type": "choice", "role": "check", "skill": "lexis_grammar",
                       "prompt": cq["prompt"], "options": cq["options"], "answer": cq["answer"],
                       **({"explanation": cq["explanation"]} if cq.get("explanation") else {})})
    b2 = {"id": f"{code}.2", "order": 2, "kind": "gramatica", "minutes": MINUTES["gramatica"], "title": "Repaso mixto de gramática",
          "intro": "Mezcla de todo lo de la semana: así se aprende a elegir la forma correcta, no solo a repetirla.",
          "resources": [], "activities": g_acts}
    b3 = block_listen(code, d["listen"])
    rr, b4 = block_read(code, d["read"])
    forms = [v[0] for v in pool[:24]]
    b5 = block_speak(code, d["speak"], d["read"]["text"], forms, rubric="oral")
    b6 = block_write(code, d["write"], forms, [], rubric="writing")
    lessons = [b1, b2, b3, b4, b5, b6]
    if final:
        inter = {"id": f"{code}.5.a3", "type": "oral", "role": "practice", "skill": "interaction", "rubric": "interaction",
                 "prompt": "Preguntas del público: responde cada una en 30–60 segundos. Si no entiendes, pide aclaración (Could you repeat the question, please?).",
                 "model": {"text": d["qa"][0], "voice": "en-GB", "source": "sintetizada"},
                 "follow_ups": d["qa"][1:], "min_seconds": 30, "max_seconds": 120,
                 "checks": []}
        b5["activities"].append(inter)
    return {
        "id": code, "kind": "day", "version": VERSION, "status": "borrador",
        "title": d["title"], "day": n, "week": d["week"], "day_type": "final" if final else "repaso", "intro": d["intro"],
        "objectives": [{"id": f"{code}-O{i}", "text": t} for i, t in enumerate(d["goals"], start=1)],
        "language_focus": {"lexis": [], "grammar": [], "pronunciation": []},
        "resources": [rr], "lessons": lessons, "quality": QUALITY,
    }


def main():
    out = ROOT / "content" / "days"
    out.mkdir(parents=True, exist_ok=True)
    weeks = WEEKS
    all_days, errors = [], []
    learning_so_far = []
    for wdays in weeks:
        learning = [d for d in wdays if not d.get("review") and not d.get("final")]
        for d in wdays:
            if d.get("final"):
                pkg = build_review_day(d, (learning_so_far + learning)[-10:], final=True)
            elif d.get("review"):
                pkg = build_review_day(d, learning)
            else:
                pkg = build_learning_day(d)
            errs = contract.validate(pkg)
            errors += errs
            (out / f"{pkg['id']}.json").write_text(json.dumps(pkg, ensure_ascii=False, indent=1), encoding="utf-8")
            all_days.append({"day": d["n"], "code": pkg["id"], "week": d["week"], "title": d["title"], "type": pkg["day_type"]})
        learning_so_far += learning
    plan = dict(meta.PLAN)
    plan["days"] = sorted(all_days, key=lambda x: x["day"])
    (ROOT / "content" / "plan40.json").write_text(json.dumps(plan, ensure_ascii=False, indent=1), encoding="utf-8")
    words = sum(len(d["vocab"]) for w in weeks for d in w if "vocab" in d)
    print(f"{len(all_days)} días generados · {words} unidades léxicas")
    if errors:
        print("\n".join(errors))
        sys.exit(1)


if __name__ == "__main__":
    main()
