from django.urls import path

from . import views

urlpatterns = [
    # Plan de 40 días (programa principal): rutas históricas /plan/ y /plan/dia/<n>/
    path("", views.calendar_view, name="plan_calendar"),
    path("comenzar/", views.start_plan, name="plan_start"),
    path("dia/<int:n>/", views.day_view, name="plan_day"),
    # Otros programas: /plan/base20/, /plan/base20/dia/<n>/ (y más adelante el avanzado)
    path("<slug:program>/", views.calendar_view, name="program_calendar"),
    path("<slug:program>/comenzar/", views.start_plan, name="program_start"),
    path("<slug:program>/dia/<int:n>/", views.day_view, name="program_day"),
]
