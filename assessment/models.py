from django.conf import settings
from django.db import models

from learning_core import rubrics


class RubricScore(models.Model):
    RATER_KINDS = [
        (rubrics.RATER_SELF, "Autoevaluación"),
        (rubrics.RATER_HUMAN, "Evaluador humano"),
        (rubrics.RATER_AUTO, "Automático orientativo (no calibrado)"),
    ]

    attempt = models.ForeignKey("activities.Attempt", on_delete=models.CASCADE, related_name="rubric_scores")
    rater = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+")
    rater_kind = models.CharField(max_length=24, choices=RATER_KINDS)
    rubric_code = models.CharField(max_length=20)
    scores = models.JSONField()  # {"task": 3, ...}
    total = models.FloatField()
    passed = models.BooleanField()
    essential_below_min = models.JSONField(default=list)
    notes = models.TextField("Prioridades de mejora / comentarios", blank=True)
    conditions = models.CharField("Condiciones (ayudas, notas, intentos)", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "evaluación con rúbrica"
        verbose_name_plural = "evaluaciones con rúbrica"

    def __str__(self):
        return f"{self.attempt} · {self.rubric_code} · {self.total:.0f} ({self.rater_kind})"


class DiagnosticResult(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="diagnostics")
    package_version = models.CharField(max_length=20)
    estimates = models.JSONField()
    recommendation = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "resultado de diagnóstico"
