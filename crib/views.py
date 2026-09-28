import json

from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from .services import board_state, handle_scan


def terminal(request):
    return render(request, "crib/terminal.html", {"debug": settings.DEBUG})


@require_POST
def scan(request):
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {"error": "invalid_json", "message": "Request body must be valid JSON."},
            status=400,
        )

    badge = payload.get("badge")
    asset_tag = payload.get("asset_tag")
    if not badge or not asset_tag:
        return JsonResponse(
            {"error": "missing_fields", "message": "Both badge and asset_tag are required."},
            status=400,
        )

    result = handle_scan(badge, asset_tag)
    status = result.pop("status")
    return JsonResponse(result, status=status)


@require_GET
def board(request):
    return JsonResponse(board_state())
