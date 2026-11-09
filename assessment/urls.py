from django.urls import path

from . import views

urlpatterns = [
    path("intento/<int:attempt_id>/rubrica/", views.rubric_form, name="rubric_form"),
    path("diagnostico/resultado/", views.diagnostic_result, name="diagnostic_result"),
    path("diagnostico/calcular/", views.diagnostic_compute, name="diagnostic_compute"),
]
