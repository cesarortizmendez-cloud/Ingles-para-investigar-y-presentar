"""Punto de extensión para asistencia con IA (§15).

En el incremento 1 NO hay ningún servicio de IA conectado. `SimulatedTutor`
devuelve preguntas de seguimiento guionizadas en el contenido y la
retroalimentación por reglas de learning_core.grading. La interfaz se identifica
siempre como «simulada» (`is_simulated = True`) para no presentarla como real.

Para conectar un proveedor real: implementar `TutorProvider`, registrar en
`PROVIDERS` y definir TUTOR_PROVIDER. Reglas que el proveedor debe respetar:
- contexto acotado (objetivo, fragmento del material, turnos relevantes, errores
  prioritarios); nunca el portafolio completo;
- no inventar resultados de un paper: si la fuente no contiene la respuesta, decirlo;
- sus comentarios no cambian el estado académico (lo decide learning_core).
"""
from __future__ import annotations

from typing import Protocol

from django.conf import settings


class TutorProvider(Protocol):
    name: str
    is_simulated: bool

    def follow_up_questions(self, activity: dict, transcript: str = "") -> list[str]: ...


class SimulatedTutor:
    name = "Tutor simulado (preguntas guionizadas, sin IA)"
    is_simulated = True

    def follow_up_questions(self, activity: dict, transcript: str = "") -> list[str]:
        return list(activity.get("follow_ups", []))


PROVIDERS = {"simulated": SimulatedTutor}


def get_tutor() -> TutorProvider:
    return PROVIDERS.get(getattr(settings, "TUTOR_PROVIDER", "simulated"), SimulatedTutor)()
