from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.forms import UserCreationForm

from .models import Profile


class SignupForm(UserCreationForm):
    email = forms.EmailField(label="Correo", required=False)
    remember = forms.BooleanField(label="Mantener la sesión abierta en este equipo", required=False,
                                  help_text="Recomendado solo en tu propio teléfono o computador (o en la app instalada).")

    class Meta(UserCreationForm.Meta):
        fields = ("username", "email")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            "display_name", "position", "institution", "specialty", "interests",
            "base_start", "plan_start", "daily_minutes", "conference_dates", "paper_familiarity", "reference_voice",
            "no_mic_mode", "keep_recordings_days",
        ]
        widgets = {
            "interests": forms.Textarea(attrs={"rows": 3}),
            "conference_dates": forms.Textarea(attrs={"rows": 2}),
            "plan_start": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
            "base_start": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        }
        labels = {"reference_voice": "Acento de los audios"}
        help_texts = {
            "daily_minutes": "Cada día del plan toma unas 2 horas (incluye 15 min de repaso). Con menos tiempo, "
                             "divide el día en dos sesiones; el calendario no se rompe por ir más lento.",
            "specialty": "Elige los ejemplos y textos de tu área cuando una actividad tiene variantes.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Sin migración: solo cambian los textos visibles de las opciones.
        self.fields["reference_voice"].choices = [
            ("en-US", "Estadounidense (recomendado)"),
            ("en-GB", "Británico"),
            ("intl", "Variado: el acento propio de cada audio"),
        ]


REMEMBER_LABEL = "Mantener la sesión abierta en este equipo"
REMEMBER_HELP = ("Recomendado solo en tu propio teléfono o computador (o en la app instalada). "
                 "Si no lo marcas, la sesión se cierra al cerrar el navegador o la app.")


class RememberLoginForm(AuthenticationForm):
    remember = forms.BooleanField(label=REMEMBER_LABEL, required=False, help_text=REMEMBER_HELP)


def apply_remember(request, remember: bool) -> None:
    """Con «mantener», la sesión dura SESSION_COOKIE_AGE (90 días, renovable); sin él, hasta cerrar el navegador."""
    request.session.set_expiry(None if remember else 0)
