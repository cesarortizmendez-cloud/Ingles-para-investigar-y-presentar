from django.conf import settings
from django.db import models


class Profile(models.Model):
    SPECIALTIES = [
        ("industrial", "Industrial"),
        ("comercial", "Comercial y gestión"),
        ("informatica", "Informática"),
    ]
    PAPER_FAMILIARITY = [
        ("nunca", "Casi nunca leo artículos en inglés"),
        ("con_traductor", "Leo con traductor"),
        ("parcial", "Leo partes (abstract, resultados)"),
        ("habitual", "Leo artículos completos con frecuencia"),
    ]
    VOICES = [
        ("en-US", "Inglés estadounidense"),
        ("en-GB", "Inglés británico"),
        ("intl", "Voces internacionales (alternar)"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField("Nombre para mostrar", max_length=80, blank=True)
    position = models.CharField("Cargo", max_length=120, blank=True)
    institution = models.CharField("Institución", max_length=160, blank=True)
    specialty = models.CharField("Especialidad principal", max_length=20, choices=SPECIALTIES, default="industrial")
    interests = models.TextField("Intereses y línea de investigación", blank=True)
    weekly_minutes = models.PositiveIntegerField("Disponibilidad semanal (minutos)", default=360)
    conference_dates = models.TextField("Congresos o presentaciones próximas (fecha y nombre)", blank=True)
    paper_familiarity = models.CharField("Familiaridad con artículos", max_length=20, choices=PAPER_FAMILIARITY, default="con_traductor")
    reference_voice = models.CharField("Voz de referencia", max_length=8, choices=VOICES, default="en-US")
    no_mic_mode = models.BooleanField("Estudiar sin micrófono", default=False,
                                      help_text="Puede estudiar, pero las habilidades orales quedarán pendientes de evidencia.")
    plan_start = models.DateField("Inicio del plan intensivo de 40 días", null=True, blank=True,
                                  help_text="Día 1 del plan. Puede cambiarla si quiere reiniciar el calendario.")
    base_start = models.DateField("Inicio del plan base de 20 días", null=True, blank=True,
                                  help_text="Día 1 del plan base (preparatorio). Puede hacerse antes o en paralelo al de 40 días.")
    daily_minutes = models.PositiveIntegerField("Minutos diarios para el plan", default=120)
    keep_recordings_days = models.PositiveIntegerField("Conservar grabaciones (días; 0 = hasta que las elimine)", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.display_name or self.user.get_username()

    def program_start(self, slug: str):
        """Fecha del día 1 de un programa (Base 20, Plan 40…), o None si no lo ha iniciado."""
        from learning_core import programs
        return getattr(self, programs.get(slug)["start_field"])

    @property
    def tts_voice(self) -> str:
        return "en-US" if self.reference_voice == "intl" else self.reference_voice


def get_profile(user) -> Profile:
    """Perfil del usuario, creándolo si falta (p. ej. usuarios anteriores a la app)."""
    profile, _ = Profile.objects.get_or_create(user=user)
    return profile
