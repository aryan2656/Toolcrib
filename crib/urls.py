from django.urls import path

from . import views

urlpatterns = [
    path("", views.terminal, name="terminal"),
    path("board/", views.board_page, name="board_page"),
    path("api/scan/", views.scan, name="scan"),
    path("api/board/", views.board, name="board"),
]
