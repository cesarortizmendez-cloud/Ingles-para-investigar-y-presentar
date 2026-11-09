from django.urls import path

from . import views

urlpatterns = [
    path("ruta/", views.catalog, name="catalog"),
    path("capitulo/<str:code>/", views.chapter_detail, name="chapter"),
    path("capitulo/<str:code>/leccion/<str:lesson_id>/", views.lesson_view, name="lesson"),
    path("capitulo/<str:code>/diferido/", views.deferred_view, name="deferred"),
    path("diagnostico/", views.diagnostic_index, name="diagnostic"),
]
