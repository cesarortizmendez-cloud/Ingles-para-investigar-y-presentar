"""Pruebas de la lógica pedagógica pura. Se ejecutan sin Django: `pytest tests/`."""
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from learning_core import contract, diagnostic, grading, progression, rubrics, scheduler  # noqa: E402
from learning_core.normalize import contains_phrase, normalize, parse_number, word_count  # noqa: E402
from learning_core.presenters import cloze_segments, pick_variant  # noqa: E402

CONTENT = ROOT / "content"


def load(rel):
    return json.loads((CONTENT / rel).read_text(encoding="utf-8"))


def activity(pkg, aid):
    for _l, a in contract.iter_activities(pkg):
        if a["id"] == aid:
            return a
    raise KeyError(aid)


C11 = load("chapters/C11.json")
C01 = load("chapters/C01.json")
DX01 = load("diagnostic/DX01.json")


# ------------------------------------------------------------ contrato
@pytest.mark.parametrize("pkg", [C01, C11, DX01], ids=["C01", "C11", "DX01"])
def test_packages_satisfy_contract(pkg):
    assert contract.validate(pkg) == []


def test_contract_detects_errors():
    broken = json.loads(json.dumps(C11))
    broken["objectives"] = broken["objectives"][:2]
    broken["lessons"][0]["activities"][0]["answer"] = "z"
    broken["lessons"][1]["activities"][3]["gaps"].pop("4")
    errs = contract.validate(broken)
    assert any("entre 3 y 5 objetivos" in e for e in errs)
    assert any("'answer' no está" in e for e in errs)
    assert any("marcadores" in e for e in errs)


def test_course_catalog_has_24_chapters():
    course = load("course.json")
    ids = [c[0] for s in course["stages"] for c in s["chapters"]]
    assert ids == [f"C{i:02d}" for i in range(1, 25)]
    assert all(len(s["chapters"]) == 4 for s in course["stages"])


# ------------------------------------------------------------ normalización
def test_normalize_and_numbers():
    assert normalize("  However,  ") == "however"
    assert normalize("It’s") == "it's"
    assert parse_number("0,5") == 0.5
    assert parse_number("15 %") == 15
    assert parse_number("0.5 pp") == 0.5
    assert parse_number("1.234,5") == 1234.5
    assert parse_number("abc") is None
    assert word_count("The findings suggest that 3.5% is lower.") == 7
    assert contains_phrase("It was associated with higher output", "associated with")
    assert not contains_phrase("It was associatedwith", "associated with")
    assert not contains_phrase("unrandomly", "randomly")


# ------------------------------------------------------------ C11 claves de la especificación (§17)
def test_c11_key_values_from_spec():
    a = activity(C11, "C11.1.a2")
    r = grading.grade(a, {"fields": {"weeks": "8", "out_a": "120", "out_b": "138", "def_a": "4,0", "def_b": "3.5"}})
    assert r.correct and r.score == 1.0
    swapped = grading.grade(a, {"fields": {"weeks": "8", "out_a": "120", "out_b": "138", "def_a": "3.5", "def_b": "4.0"}})
    assert not swapped.correct and swapped.score == pytest.approx(0.6)


def test_c11_percent_vs_percentage_points():
    a = activity(C11, "C11.2.a1")
    assert grading.grade(a, {"fields": {"rel": "15", "pp": "0,5"}}).correct
    # 12,5 es la reducción relativa, no los puntos porcentuales
    r = grading.grade(a, {"fields": {"rel": "15", "pp": "12.5"}})
    assert not r.correct and r.score == 0.5
    # el cálculo real coincide con la clave
    assert (138 - 120) / 120 * 100 == pytest.approx(15)
    assert 4.0 - 3.5 == pytest.approx(0.5)


def test_c11_transfer_and_deferred_numbers_are_consistent():
    assert (12 - 9) / 12 * 100 == pytest.approx(activity(C11, "C11.D.a1")["fields"][0]["answer"])
    assert 3.2 - 3.0 == pytest.approx(activity(C11, "C11.D.a1")["fields"][1]["answer"])
    assert (150 - 120) / 120 * 100 == pytest.approx(activity(C11, "C11.4.a6")["fields"][0]["answer"])
    assert (6 - 4) / 6 == pytest.approx(1 / 3)


def test_choice_with_evidence():
    a = activity(C11, "C11.1.a1")
    full = grading.grade(a, {"option": "b", "evidence": ["s1", "s3"]})
    assert full.correct and full.score == 1.0
    no_ev = grading.grade(a, {"option": "b", "evidence": []})
    assert not no_ev.correct and no_ev.score == 0.6
    wrong_ev = grading.grade(a, {"option": "b", "evidence": ["s2"]})
    assert wrong_ev.score == 0.6
    wrong = grading.grade(a, {"option": "a", "evidence": ["s3"]})
    assert wrong.score == 0.4 and "aleatoriamente" in wrong.feedback[0]


def test_choice_requires_justification():
    a = activity(C11, "C11.1.a3")
    assert grading.grade(a, {"option": "b"}).status == grading.INCOMPLETE
    r = grading.grade(a, {"option": "b", "justification": "the lines were not random"})
    assert r.status == grading.GRADED and r.correct


def test_cloze_near_feedback():
    a = activity(C11, "C11.2.a4")
    r = grading.grade(a, {"gaps": {"1": "whereas", "2": "Respectively", "3": "However,", "4": "prove"}})
    assert r.score == 0.75
    assert any("demasiado fuerte" in f for f in r.feedback)


def test_short_text_recall_and_near():
    a = activity(C11, "C11.4.a1")
    assert grading.grade(a, {"text": "Was associated with"}).correct
    r = grading.grade(a, {"text": "caused"})
    assert not r.correct and "causalidad" in r.feedback[0]


def test_ordering():
    a = activity(C01, "C01.2.a3")
    assert grading.grade(a, {"order": ["w1", "w2", "w3", "w4", "w5"]}).correct
    r = grading.grade(a, {"order": ["w1", "w2", "w3", "w5", "w4"]})
    assert r.score == 0.6 and not r.correct
    assert grading.grade(a, {"order": ["w1", "w1", "w3", "w4", "w5"]}).status == grading.INCOMPLETE


def test_listening_mixed_questions():
    a = activity(C01, "C01.3.a1")
    r = grading.grade(a, {"questions": {"q1": {"option": "a"}, "q2": {"option": "b"}, "q3": {"fields": {"n": "14"}}}})
    assert r.correct and r.score == 1.0
    r2 = grading.grade(a, {"questions": {"q1": {"option": "a"}, "q2": {"option": "b"}, "q3": {"fields": {"n": "40"}}}})
    assert not r2.correct and r2.score == pytest.approx(2 / 3, abs=1e-3)
    assert grading.grade(a, {"questions": {}}).status == grading.INCOMPLETE


def test_dictation():
    a = activity(C11, "C11.3.a3")
    assert grading.grade(a, {"text": "However the lines were not randomly assigned to the procedures"}).correct
    r = grading.grade(a, {"text": "However the lines were not random assigned to the procedure"})
    assert not r.correct and r.feedback


def test_open_text_feedback_is_capped_and_labeled():
    a = activity(C11, "C11.4.a2")
    r = grading.grade(a, {"text": "The new procedure caused an increase and this proves everything about the lines."})
    assert r.status == grading.GRADED  # práctica sin rúbrica
    assert len(r.feedback) <= grading.MAX_FEEDBACK
    assert grading.SIMULATED_NOTICE in r.notices
    good = grading.grade(a, {"text": "The revised procedure was associated with 15% higher output, but the lines were not randomly assigned."})
    assert good.feedback == []


def test_oral_without_mic_is_pending_not_passed():
    a = activity(C11, "C11.5.a1")
    r = grading.grade(a, {"no_mic": True})
    assert r.status == grading.PENDING_EVIDENCE and r.score is None
    r2 = grading.grade(a, {"recording_id": 5, "transcript": "Line B produced 138 units. The findings suggest the procedure may help, but teams had different experience."})
    assert r2.status == grading.PENDING_RUBRIC and r2.score is None
    assert grading.TRANSCRIPT_ONLY_NOTICE in r2.notices


# ------------------------------------------------------------ rúbricas
def test_rubric_weights_sum_100():
    for code, spec in rubrics.RUBRICS.items():
        assert sum(w for _c, _n, w in spec["criteria"]) == 100, code


def test_rubric_total_and_essentials():
    all3 = {c: 3 for c, _n, _w in rubrics.criteria("oral")}
    ev = rubrics.evaluate("oral", all3)
    assert ev["total"] == 75 and ev["passed"]
    weak = dict(all3, intelligibility=1, fluency=4, resources=4)
    ev2 = rubrics.evaluate("oral", weak)
    assert ev2["total"] == pytest.approx(25 * .75 + 20 * .75 + 20 * .25 + 20 + 15)
    assert not ev2["passed"] and ev2["essential_below_min"] == ["intelligibility"]
    with pytest.raises(rubrics.RubricError):
        rubrics.total("oral", {"task": 3})


# ------------------------------------------------------------ repaso espaciado
def test_scheduler_intervals():
    t = date(2026, 11, 5)
    assert scheduler.first_due(t) == (0, t + timedelta(days=1))
    assert scheduler.next_review(0, True, False, t) == (1, t + timedelta(days=3))
    assert scheduler.next_review(3, True, False, t) == (4, t + timedelta(days=30))
    assert scheduler.next_review(4, True, False, t) == (4, t + timedelta(days=30))
    assert scheduler.next_review(2, True, True, t) == (2, t + timedelta(days=1))
    assert scheduler.next_review(3, False, False, t) == (0, t + timedelta(days=1))


def test_plan_day_caps_and_redistributes():
    t = date(2026, 11, 5)
    items = [scheduler.Item(f"k{i}", t - timedelta(days=i % 5)) for i in range(45)]
    items.append(scheduler.Item("block", t, blocking=True))
    today, moved = scheduler.plan_day(items, t, cap=20, future_load={t + timedelta(days=1): 15})
    assert len(today) == 20 and today[0].key == "block"
    assert len(moved) == 26
    per_day = {}
    for m in moved:
        per_day[m.due] = per_day.get(m.due, 0) + 1
    assert per_day[t + timedelta(days=1)] == 5  # 15 ya agendados + 5 = tope 20
    assert all(m.due > t for m in moved)


# ------------------------------------------------------------ cierre de capítulo
def test_chapter_states():
    t = date(2026, 11, 5)
    passed = {"passed": True, "total": 80}
    base = dict(opened=True, attempts=5, provisional_on=None, deferred=None, today=t)
    assert progression.chapter_state(opened=False, attempts=0, check=None, task=None,
                                     provisional_on=None, deferred=None, today=t)["state"] == "no_iniciado"
    assert progression.chapter_state(**dict(base, attempts=0), check=None, task=None)["state"] == "abierto"
    assert progression.chapter_state(**base, check=0.7, task=passed)["state"] == "practicado"
    s = progression.chapter_state(**base, check=0.8, task=passed)
    assert s["state"] == "aprobado_provisional" and not s["deferred_available"]
    later = t + timedelta(days=8)
    ok = progression.chapter_state(opened=True, attempts=9, check=0.8, task=passed,
                                   provisional_on=t, deferred=0.75, today=later)
    assert ok["state"] == "consolidado"
    fail = progression.chapter_state(opened=True, attempts=9, check=0.8, task=passed,
                                     provisional_on=t, deferred=0.5, today=later)
    assert fail["state"] == "aprobado_provisional" and fail["recovery_needed"]


def test_check_ratio_uses_all_items():
    assert progression.check_ratio({"a": 1, "b": 0.5}, ["a", "b"]) == 0.75
    assert progression.check_ratio({"a": 1}, ["a", "b"]) is None


def test_c11_check_threshold_reachable():
    checks = [a["id"] for _l, a in contract.iter_activities(C11) if a.get("role") == "check"]
    assert len(checks) == 5  # 4/5 = 80 %: un error aún permite aprobar
    scores = {c: 1.0 for c in checks}
    scores[checks[0]] = 0.0
    assert progression.check_ratio(scores, checks) == pytest.approx(0.8)


# ------------------------------------------------------------ diagnóstico
def test_diagnostic_confidence_and_insufficient_sample():
    ev = [{"skill": "reading", "kind": "auto", "score": s} for s in (1, 1, 0, 1, 1)]
    ev += [{"skill": "writing", "kind": "self", "score": 0.75}]
    ev += [{"skill": "listening", "kind": "auto", "score": 1}]
    est = diagnostic.estimate(ev)
    assert est["reading"]["level"] == "B1+ o superior" and est["reading"]["confidence"] == "media"
    assert est["writing"]["confidence"] == "baja" and est["writing"]["request_more"]
    assert est["listening"]["confidence"] == "insuficiente" and est["listening"]["level"] is None
    assert est["speaking"]["confidence"] == "insuficiente"
    rec = diagnostic.recommend(est)
    assert "speaking" in rec["pending_evidence"]


def test_diagnostic_detects_a2_gap():
    ev = [{"skill": "lexis_grammar", "kind": "auto", "score": s} for s in (0, 0, 1, 0)]
    est = diagnostic.estimate(ev)
    assert est["lexis_grammar"]["level"] == "A2 (posible brecha)"
    rec = diagnostic.recommend(est)
    assert rec["reinforcement"] == ["lexis_grammar"] and rec["start_day"] == 1 and rec["base_first"] is True
    assert diagnostic.base_first(["speaking"]) is False and diagnostic.base_first(["speaking", "writing"]) is True
    assert rec["plan_focus"] == [{"skill": "lexis_grammar", "block": "🔤 Vocabulario y 🧩 Gramática"}]


# ------------------------------------------------------------ presentación
def test_cloze_segments():
    segs = cloze_segments("A [[1]] B [[2]].")
    assert segs == [{"text": "A "}, {"gap": "1"}, {"text": " B "}, {"gap": "2"}, {"text": "."}]


def test_pick_variant_by_specialty():
    acts = C11["lessons"][5]["activities"]
    chosen = pick_variant(acts, "informatica")
    assert [a["id"] for a in chosen] == ["C11.6.a1t", "C11.6.a2"]
    assert pick_variant(acts, "otra")[0]["id"] == "C11.6.a1i"


# ------------------------------------------------------------ plan de 40 días
from learning_core import plan  # noqa: E402

DAYS = [load(f"days/D{i:02d}.json") for i in range(1, 41)]
PLAN = load("plan40.json")


def test_forty_days_satisfy_contract():
    assert len(DAYS) == 40
    for d in DAYS:
        assert contract.validate(d) == [], d["id"]
    assert [d["day"] for d in PLAN["days"]] == list(range(1, 41))
    types = [d["day_type"] for d in DAYS]
    assert types.count("repaso") == 5 and types[-1] == "final"


def test_plan_vocabulary_is_unique_and_sized():
    forms = [lx["form"].lower() for d in DAYS for lx in d["language_focus"]["lexis"]]
    assert len(forms) == 34 * 12
    assert len(set(forms)) == len(forms)


def test_vocab_cloze_answers_come_from_the_day_list():
    for d in DAYS:
        if d["day_type"] != "aprendizaje":
            continue
        forms = {lx["form"].lower() for lx in d["language_focus"]["lexis"]}
        cloze = d["lessons"][0]["activities"][0]
        for gap in cloze["gaps"].values():
            assert gap["accept"][0].lower() in forms


def test_every_vocab_item_is_gradable():
    d = DAYS[0]
    lx = d["language_focus"]["lexis"][0]
    acts = [a for a in d["lessons"][0]["activities"] if a["type"] == "short_text"]
    a = acts[0]
    assert grading.grade(a, {"text": a["accept"][0].upper()}).correct


def test_min_count_check():
    passed, msgs = grading.run_checks([{"id": "v", "min_count": 2, "phrases": ["data", "sample", "average"], "feedback": "x"}],
                                      "The sample average was high.")
    assert passed == ["v"]
    passed, msgs = grading.run_checks([{"id": "v", "min_count": 3, "phrases": ["data", "sample", "average"], "feedback": "x"}],
                                      "The sample was high.")
    assert msgs == ["x"]


def test_day_progress_rules():
    assert plan.day_progress(20, 16, [0.8, 0.7])["done"]
    assert not plan.day_progress(20, 15, [1.0])["done"]
    assert not plan.day_progress(20, 20, [0.5, 0.6])["done"]


def test_calendar_and_streak():
    start = date(2026, 11, 1)
    today = date(2026, 11, 7)
    assert plan.recommended_day(start, today) == 7
    assert plan.recommended_day(start, date(2027, 3, 1)) == 40
    assert plan.recommended_day(None, today) == 1
    cells = plan.calendar(start, today, {1: {"done": True, "started": True}, 2: {"started": True, "done": False}})
    states = [c["state"] for c in cells[:8]]
    assert states == ["completado", "en_curso", "atrasado", "atrasado", "atrasado", "atrasado", "hoy", "pendiente"]
    assert cells[0]["date"] == start and cells[39]["date"] == date(2026, 12, 10)
    dates = {today, today - timedelta(days=1), today - timedelta(days=2), today - timedelta(days=4)}
    assert plan.streak(dates, today) == 3
    assert plan.streak({today - timedelta(days=1)}, today) == 1


# ------------------------------------------------------------ motivación
from learning_core import coach  # noqa: E402


def test_milestones_and_projection():
    ms = coach.milestones(9)
    assert [m["reached"] for m in ms] == [True, True, False, False, False, False, False]
    assert [m["n"] for m in ms if m["next"]] == [14] and ms[2]["missing"] == 5
    start, today = date(2026, 11, 1), date(2026, 11, 7)
    p = coach.projection(start, today, 6)
    assert p["planned_end"] == date(2026, 12, 10) and p["finish"] == date(2026, 12, 10) and p["on_track"]
    late = coach.projection(start, date(2026, 11, 20), 6)
    assert not late["on_track"] and late["delay_days"] == 13
    assert coach.projection(None, today, 0) is None


def test_ring_has_forty_segments():
    segs = coach.ring_segments(["completado"] * 3 + ["pendiente"] * 37)
    assert len(segs) == 40 and segs[0]["state"] == "completado"
    assert segs[0]["d"].startswith("M ") and segs[0]["d"].endswith("Z")


# ------------------------------------------------------------ programas (Base 20 + Plan 40)
def test_programs_codes():
    from learning_core import programs
    assert programs.for_code("B05")["slug"] == "base20"
    assert programs.for_code("D40")["slug"] == "plan40"
    assert programs.for_code("B21") is None and programs.for_code("D41") is None
    assert programs.for_code("C01") is None and programs.for_code("X") is None
    assert programs.day_code("base20", 3) == "B03"


def test_calendar_for_twenty_days():
    from datetime import date
    from learning_core import plan
    cells = plan.calendar(date(2026, 1, 1), date(2026, 1, 25), {}, total=20, prefix="B")
    assert len(cells) == 20 and cells[0]["code"] == "B01"
    assert plan.recommended_day(date(2026, 1, 1), date(2026, 1, 25), 20) == 20
    assert all(c["state"] != "hoy" for c in cells[:19])
