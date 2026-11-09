from django.urls import path

from . import views

urlpatterns = [
    path("registro/", views.signup, name="signup"),
    path("perfil/", views.profile_edit, name="profile"),
]
