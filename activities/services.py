from django.db import transaction

from curriculum.services import mark_opened
from learning_core import grading

from .models import Attempt


@transaction.atomic
def submit(*, user, package, activity: dict, lesson_id: str, response: dict, helps: list[str],
           duration_ms: int | None, source: str):
    """Corrige y registra. Devuelve (intento | None, resultado).

    Un envío incompleto no se guarda: no es evidencia y no debe contar como primer intento.
    """
    result = grading.grade(activity, response)
    if result.status == grading.INCOMPLETE:
        return None, result
    previous = Attempt.objects.filter(user=user, activity_id=activity["id"]).count()
    attempt = Attempt.objects.create(
        user=user, package=package, chapter_code=package.code, lesson_id=lesson_id,
        activity_id=activity["id"], activity_type=activity["type"], role=activity.get("role", "practice"),
        skill=activity.get("skill", ""), source=source, attempt_number=previous + 1,
        response=response, helps=helps, duration_ms=duration_ms,
        status=result.status, score=result.score, correct=result.correct,
        feedback=result.feedback, details=result.details, notices=result.notices,
    )
    if package.kind == "chapter":
        mark_opened(user, package.code)
    if activity["type"] == "oral" and response.get("recording_id"):
        from voice.models import Recording
        Recording.objects.filter(pk=response["recording_id"], user=user).update(attempt=attempt)
    if result.status == grading.GRADED and activity["type"] in grading.CLOSED_TYPES and package.kind == "chapter":
        from review.services import record_outcome
        record_outcome(user, attempt, activity)
    return attempt, result
