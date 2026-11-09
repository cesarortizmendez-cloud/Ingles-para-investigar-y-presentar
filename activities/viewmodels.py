"""Prepara cada actividad para la plantilla `activities/_activity.html`."""
import random

from learning_core import rubrics
from learning_core.presenters import cloze_segments
from tutor.providers import get_tutor

from .models import Attempt


def _shuffled(items: list[dict], seed: str, answer: list[str] | None = None) -> list[dict]:
    out = list(items)
    random.Random(seed).shuffle(out)
    if answer and [i["id"] for i in out] == list(answer) and len(out) > 1:
        out = out[1:] + out[:1]  # nunca mostrar la solución como orden inicial
    return out


def build(*, activity: dict, package, user, lesson_id: str, resources: dict, profile, next_url: str,
          source: str = "leccion") -> dict:
    attempts = Attempt.objects.filter(user=user, activity_id=activity["id"]).order_by("-created_at")
    latest = attempts.first()
    vm = {
        "act": activity,
        "package": package,
        "lesson_id": lesson_id,
        "latest": latest,
        "n_attempts": attempts.count(),
        "next_url": next_url,
        "source": source,
        "voice": (activity.get("audio") or activity.get("model") or {}).get("voice") or profile.tts_voice,
        "act_resources": [resources[r] for r in activity.get("resources", []) if r in resources],
        "no_mic": profile.no_mic_mode,
    }
    kind = activity["type"]
    if kind == "cloze":
        vm["segments"] = cloze_segments(activity["text"])
    elif kind == "ordering":
        vm["items"] = _shuffled(activity["items"], activity["id"], activity["answer"])
        vm["positions"] = list(range(1, len(activity["items"]) + 1))
    elif kind == "listening":
        # AUD04: la transcripción solo se habilita después de responder.
        vm["show_transcript"] = latest is not None
    elif kind == "oral":
        from voice.models import Recording
        vm["recordings"] = list(Recording.objects.filter(user=user, activity_id=activity["id"])
                                .only("id", "created_at", "duration_s", "transcript", "mime").order_by("-created_at")[:3])
        vm["show_follow_ups"] = latest is not None
        tutor = get_tutor()
        vm["follow_ups"] = tutor.follow_up_questions(activity, (latest.response or {}).get("transcript", "") if latest else "")
        vm["tutor_name"] = tutor.name
    if activity.get("rubric"):
        vm["rubric_title"] = rubrics.RUBRICS[activity["rubric"]]["title"]
        if latest:
            vm["latest_rubric"] = latest.rubric_scores.order_by("-created_at").first()
    return vm
