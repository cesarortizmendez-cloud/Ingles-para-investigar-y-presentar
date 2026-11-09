from django.conf import settings
from django.db import models


class Recording(models.Model):
    """Grabación del alumno.

    Se guarda en la base de datos (BinaryField) para que funcione en Vercel, cuyo
    disco es efímero. Para volúmenes mayores conviene un almacenamiento de objetos
    (Vercel Blob, S3): ver docs/ARQUITECTURA.md.
    """

    TRANSCRIPT_SOURCES = [
        ("", "Sin transcripción"),
        ("asr_navegador", "Reconocimiento del navegador"),
        ("manual", "Escrita o corregida por el alumno"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="recordings")
    attempt = models.ForeignKey("activities.Attempt", null=True, blank=True, on_delete=models.SET_NULL,
                                related_name="recordings")
    package = models.ForeignKey("curriculum.ContentPackage", null=True, on_delete=models.SET_NULL)
    activity_id = models.CharField(max_length=40, db_index=True)
    audio = models.BinaryField()
    mime = models.CharField(max_length=60, default="audio/webm")
    size_bytes = models.PositiveIntegerField(default=0)
    duration_s = models.FloatField(null=True, blank=True)
    transcript = models.TextField(blank=True)
    transcript_source = models.CharField(max_length=20, choices=TRANSCRIPT_SOURCES, blank=True)
    asr_errors_flagged = models.TextField("Errores del reconocimiento señalados por el alumno", blank=True)
    consent_share = models.BooleanField("Autoriza compartir con evaluador externo", default=False)
    consent_reuse = models.BooleanField("Autoriza reutilizar para otros fines", default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "grabación"
        verbose_name_plural = "grabaciones"

    def __str__(self):
        return f"{self.user} · {self.activity_id} · {self.created_at:%Y-%m-%d %H:%M}"
