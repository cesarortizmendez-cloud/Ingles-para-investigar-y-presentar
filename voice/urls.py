from django.urls import path

from . import views

urlpatterns = [
    path("subir/", views.upload, name="recording_upload"),
    path("<int:pk>/audio/", views.stream, name="recording_stream"),
    path("<int:pk>/transcripcion/", views.update_transcript, name="recording_transcript"),
    path("<int:pk>/autorizaciones/", views.update_consent, name="recording_consent"),
    path("<int:pk>/eliminar/", views.delete, name="recording_delete"),
]
