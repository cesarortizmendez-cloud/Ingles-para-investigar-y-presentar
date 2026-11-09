from django.contrib import admin
from django.urls import include, path

from accounts import views as account_views

from . import pwa

urlpatterns = [
    path("", account_views.home, name="home"),
    path("manifest.webmanifest", pwa.manifest, name="manifest"),
    path("sw.js", pwa.service_worker, name="service_worker"),
    path("sin-conexion/", pwa.offline, name="offline"),
    path("admin/", admin.site.urls),
    path("cuenta/login/", account_views.RememberLoginView.as_view(), name="login"),
    path("cuenta/", include("django.contrib.auth.urls")),
    path("cuenta/", include("accounts.urls")),
    path("", include("curriculum.urls")),
    path("actividad/", include("activities.urls")),
    path("voz/", include("voice.urls")),
    path("repaso/", include("review.urls")),
    path("evaluacion/", include("assessment.urls")),
    path("portafolio/", include("portfolio.urls")),
    path("plan/", include("plan.urls")),
]
