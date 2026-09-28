from django.urls import path

from . import views

urlpatterns = [
    path("", views.terminal, name="terminal"),
    path("api/scan/", views.scan, name="scan"),
    path("api/board/", views.board, name="board"),
]
