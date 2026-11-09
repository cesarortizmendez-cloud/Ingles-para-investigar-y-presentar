import hashlib
import json

from django.conf import settings
from django.db import models


class ContentPackage(models.Model):
    """Una versión inmutable de un paquete de contenido (capítulo o diagnóstico).

    Editar un capítulo crea una nueva fila (nueva versión) y la marca como vigente;
    las versiones anteriores se conservan porque los intentos apuntan a ellas. Así,
    cambiar una lección no destruye intentos anteriores ni obliga a tocar el motor.
    """

    KINDS = [("chapter", "Capítulo"), ("diagnostic", "Diagnóstico"), ("day", "Día del plan 40")]
    STATES = [("borrador", "Borrador"), ("revisado", "Revisado"), ("publicado", "Publicado")]

    code = models.CharField("ID estable", max_length=20, db_index=True)
    kind = models.CharField(max_length=12, choices=KINDS)
    version = models.CharField(max_length=20)
    status = models.CharField("Estado editorial", max_length=12, choices=STATES, default="borrador")
    title = models.CharField(max_length=200)
    data = models.JSONField("Contenido (JSON del contrato editorial)")
    checksum = models.CharField(max_length=64, editable=False)
    is_current = models.BooleanField("Vigente", default=False)
    change_note = models.CharField("Nota de cambio", max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("code", "version")]
        ordering = ["code", "-created_at"]
        verbose_name = "paquete de contenido"
        verbose_name_plural = "paquetes de contenido"

    def __str__(self):
        flag = " (vigente)" if self.is_current else ""
        return f"{self.code} v{self.version}{flag}"

    @staticmethod
    def compute_checksum(data) -> str:
        raw = json.dumps(data, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def save(self, *args, **kwargs):
        self.checksum = self.compute_checksum(self.data)
        super().save(*args, **kwargs)


class ChapterProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chapter_progress")
    chapter_code = models.CharField(max_length=10)
    opened_at = models.DateTimeField(null=True, blank=True)
    provisional_on = models.DateField("Aprobado provisionalmente el", null=True, blank=True)
    consolidated_on = models.DateField("Consolidado el", null=True, blank=True)
    recovery_needed = models.BooleanField(default=False)
    last_state = models.CharField(max_length=24, default="no_iniciado")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("user", "chapter_code")]
        verbose_name = "progreso de capítulo"
        verbose_name_plural = "progreso de capítulos"

    def __str__(self):
        return f"{self.user} · {self.chapter_code} · {self.last_state}"
