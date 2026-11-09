from django.urls import path

from . import views

urlpatterns = [
    path("<int:package_id>/<str:activity_id>/responder/", views.submit_view, name="activity_submit"),
]
