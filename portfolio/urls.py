from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="portfolio"),
    path("exportar.json", views.export_json, name="portfolio_export"),
    path("privacidad/", views.privacy, name="privacy"),
    path("privacidad/eliminar-grabaciones/", views.delete_recordings, name="delete_recordings"),
    path("privacidad/eliminar-cuenta/", views.delete_account, name="delete_account"),
]
