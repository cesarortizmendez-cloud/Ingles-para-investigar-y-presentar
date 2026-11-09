from activities.models import Attempt
from learning_core import diagnostic, rubrics

from .models import DiagnosticResult, RubricScore


def save_rubric(*, attempt: Attempt, rater, scores: dict[str, int], notes: str, essential=None) -> RubricScore:
    kind = rubrics.RATER_SELF if rater.pk == attempt.user_id else rubrics.RATER_HUMAN
    ev = rubrics.evaluate(attempt_rubric_code(attempt), scores, essential)
    helps = ", ".join(attempt.helps) if attempt.helps else "sin ayudas registradas"
    return RubricScore.objects.create(
        attempt=attempt, rater=rater, rater_kind=kind, rubric_code=ev["rubric"], scores=scores,
        total=ev["total"], passed=ev["passed"], essential_below_min=ev["essential_below_min"], notes=notes,
        conditions=f"Intento n.º {attempt.attempt_number}; {helps}",
    )


def attempt_rubric_code(attempt: Attempt) -> str:
    from curriculum.services import find_activity
    _l, act = find_activity(attempt.package.data, attempt.activity_id)
    if not act or not act.get("rubric"):
        raise rubrics.RubricError("Esta actividad no tiene rúbrica.")
    return act["rubric"]


def diagnostic_evidence(user, package) -> list[dict]:
    evidence = []
    seen = set()
    for att in Attempt.objects.filter(user=user, source="diagnostico", package__code=package.code).order_by("created_at"):
        if att.activity_id in seen:
            continue  # solo el primer intento es evidencia diagnóstica
        if att.status == "corregido" and att.score is not None:
            evidence.append({"skill": att.skill, "kind": "auto", "score": att.score, "activity": att.activity_id})
            seen.add(att.activity_id)
            continue
        rs = att.rubric_scores.order_by("-created_at")
        human = rs.filter(rater_kind=rubrics.RATER_HUMAN).first()
        chosen = human or rs.filter(rater_kind=rubrics.RATER_SELF).first()
        if chosen:
            evidence.append({"skill": att.skill, "kind": "human" if human else "self",
                             "score": chosen.total / 100, "activity": att.activity_id})
            seen.add(att.activity_id)
    return evidence


def compute_diagnostic(user, package) -> DiagnosticResult:
    estimates = diagnostic.estimate(diagnostic_evidence(user, package))
    rec = diagnostic.recommend(estimates)
    return DiagnosticResult.objects.create(user=user, package_version=package.version,
                                           estimates=estimates, recommendation=rec)
