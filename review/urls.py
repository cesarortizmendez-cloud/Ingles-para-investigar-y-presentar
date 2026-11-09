from django.urls import path

from . import views

urlpatterns = [
    path("", views.session, name="review"),
    path("lexico/<int:pk>/", views.lexis_answer, name="review_lexis"),
]
