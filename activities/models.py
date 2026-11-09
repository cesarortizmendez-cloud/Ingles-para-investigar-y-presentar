from django.conf import settings
from django.db import models


class Attempt(models.Model):
    """Un intento sobre una actividad. Conserva la versión de contenido usada."""

    SOURCES = [
        ("leccion", "Lección"),
        ("repaso", "Repaso"),
        ("diferido", "Confirmación diferida"),
        ("diagnostico", "Diagnóstico"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="attempts")
    package = models.ForeignKey("curriculum.ContentPackage", on_delete=models.PROTECT, related_name="attempts")
    chapter_code = models.CharField(max_length=20, db_index=True)
    lesson_id = models.CharField(max_length=30, blank=True)
    activity_id = models.CharField(max_length=40, db_index=True)
    activity_type = models.CharField(max_length=20)
    role = models.CharField(max_length=12, default="practice")
    skill = models.CharField(max_length=20, blank=True)
    source = models.CharField(max_length=12, choices=SOURCES, default="leccion")
    attempt_number = models.PositiveSmallIntegerField(default=1)

    response = models.JSONField(default=dict)
    helps = models.JSONField("Ayudas usadas", default=list)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)

    status = models.CharField(max_length=24)
    score = models.FloatField(null=True, blank=True)
    correct = models.BooleanField(null=True)
    feedback = models.JSONField(default=list)
    details = models.JSONField(default=dict)
    notices = models.JSONField(default=list)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "activity_id"])]
        verbose_name = "intento"

    def __str__(self):
        return f"{self.user} · {self.activity_id} #{self.attempt_number} · {self.status}"

    @property
    def helped(self) -> bool:
        return bool(self.helps)
