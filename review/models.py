from django.conf import settings
from django.db import models


class ReviewItem(models.Model):
    KINDS = [("activity", "Actividad o error"), ("lexis", "Unidad léxica")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="review_items")
    key = models.CharField(max_length=60)  # id de actividad o "lexis:C11-LX01"
    kind = models.CharField(max_length=10, choices=KINDS)
    chapter_code = models.CharField(max_length=10)
    stage = models.PositiveSmallIntegerField(default=0)
    due = models.DateField(db_index=True)
    blocking = models.BooleanField("Brecha que impide la siguiente tarea", default=False)
    last_correct = models.BooleanField(null=True)
    last_helped = models.BooleanField(default=False)
    history = models.JSONField(default=list)  # [{"date": "...", "correct": bool, "helped": bool, "stage": n}]
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "key")]
        ordering = ["due", "stage"]
        verbose_name = "ítem de repaso"
        verbose_name_plural = "ítems de repaso"

    def __str__(self):
        return f"{self.user} · {self.key} · {self.due}"
