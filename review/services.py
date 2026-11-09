from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from learning_core import scheduler

from .models import ReviewItem


def _intervals():
    return tuple(getattr(settings, "REVIEW_INTERVALS_DAYS", scheduler.DEFAULT_INTERVALS))


def seed_lexis(user, chapter_data: dict) -> int:
    """Agenda las unidades léxicas prioritarias del capítulo para el día siguiente."""
    today = timezone.localdate()
    _stage, due = scheduler.first_due(today, _intervals())
    created = 0
    for lx in chapter_data.get("language_focus", {}).get("lexis", []):
        _obj, was_created = ReviewItem.objects.get_or_create(
            user=user, key=f"lexis:{lx['id']}",
            defaults={"kind": "lexis", "chapter_code": chapter_data["id"], "due": due},
        )
        created += int(was_created)
    return created


def apply_outcome(item: ReviewItem, correct: bool, helped: bool) -> ReviewItem:
    today = timezone.localdate()
    stage, due = scheduler.next_review(item.stage, correct, helped, today, _intervals())
    item.stage, item.due = stage, due
    item.last_correct, item.last_helped = correct, helped
    item.history = (item.history or []) + [
        {"date": today.isoformat(), "correct": correct, "helped": helped, "stage": stage}]
    if correct and not helped:
        item.blocking = False
    item.save()
    return item


def record_outcome(user, attempt, activity: dict) -> ReviewItem:
    """Toda actividad cerrada corregida entra (o avanza) en el repaso espaciado."""
    item, created = ReviewItem.objects.get_or_create(
        user=user, key=activity["id"],
        defaults={"kind": "activity", "chapter_code": attempt.chapter_code, "due": timezone.localdate()},
    )
    correct = bool(attempt.correct)
    if not correct and activity.get("role") in ("check", "deferred"):
        item.blocking = True
    if created:
        # Primera vez: siempre vuelve en otro día (intervalo 1) antes de empezar a espaciar.
        _stage, item.due = scheduler.first_due(timezone.localdate(), _intervals())
        item.last_correct, item.last_helped = correct, attempt.helped
        item.history = [{"date": timezone.localdate().isoformat(), "correct": correct,
                         "helped": attempt.helped, "stage": 0}]
        item.save()
        return item
    return apply_outcome(item, correct, attempt.helped)


def today_plan(user):
    """Ítems de hoy (máx. REVIEW_DAILY_CAP) y redistribución del exceso sin acumular deuda."""
    today = timezone.localdate()
    cap = getattr(settings, "REVIEW_DAILY_CAP", scheduler.DEFAULT_DAILY_CAP)
    rows = {i.key: i for i in ReviewItem.objects.filter(user=user, due__lte=today)}
    future = (ReviewItem.objects.filter(user=user, due__gt=today, due__lte=today + timedelta(days=60))
              .values("due").annotate(n=Count("id")))
    load = {r["due"]: r["n"] for r in future}
    items = [scheduler.Item(k, r.due, r.stage, r.blocking) for k, r in rows.items()]
    todays, moved = scheduler.plan_day(items, today, cap, load)
    for m in moved:
        ReviewItem.objects.filter(pk=rows[m.key].pk).update(due=m.due)
    return [rows[i.key] for i in todays], len(moved)


def due_count(user) -> int:
    return ReviewItem.objects.filter(user=user, due__lte=timezone.localdate()).count()


def next_due(user) -> dict | None:
    """Próxima fecha con repasos (después de hoy) y cuántos ítems vencen ese día."""
    first = ReviewItem.objects.filter(user=user, due__gt=timezone.localdate()).order_by("due").first()
    if not first:
        return None
    return {"date": first.due, "n": ReviewItem.objects.filter(user=user, due=first.due).count()}
