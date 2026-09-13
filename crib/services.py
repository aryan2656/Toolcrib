from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Checkout, Employee, Tool

IDEMPOTENCY_WINDOW = timedelta(seconds=2)


def _tool_payload(tool):
    return {"asset_tag": tool.asset_tag, "description": tool.description}


def _employee_payload(employee):
    return {"badge_id": employee.badge_id, "name": employee.name}


def _checkout_result(checkout, tool, employee):
    if checkout.returned_at is None:
        return {
            "status": 200,
            "action": "checked_out",
            "tool": _tool_payload(tool),
            "employee": _employee_payload(employee),
            "due_back_at": checkout.due_back_at,
        }
    duration = checkout.returned_at - checkout.checked_out_at
    return {
        "status": 200,
        "action": "returned",
        "tool": _tool_payload(tool),
        "duration_minutes": int(duration.total_seconds() // 60),
    }


def _recent_checkout(tool, employee, now):
    # Scanners double-fire; a checkout opened or closed for this exact
    # tool+employee pair in the last 2 seconds replays instead of acting
    # again, so an accidental repeat scan can't toggle state twice.
    cutoff = now - IDEMPOTENCY_WINDOW
    return (
        Checkout.objects.filter(tool=tool, employee=employee)
        .filter(Q(checked_out_at__gte=cutoff) | Q(returned_at__gte=cutoff))
        .order_by("-checked_out_at")
        .first()
    )


def handle_scan(badge, asset_tag):
    now = timezone.now()

    try:
        employee = Employee.objects.get(badge_id=badge)
    except Employee.DoesNotExist:
        return {
            "status": 404,
            "error": "unknown_badge",
            "value": badge,
            "message": f"Badge {badge} is not recognized.",
        }

    try:
        tool = Tool.objects.get(asset_tag=asset_tag)
    except Tool.DoesNotExist:
        return {
            "status": 404,
            "error": "unknown_tool",
            "value": asset_tag,
            "message": f"Tool {asset_tag} is not recognized.",
        }

    if not tool.is_active:
        return {
            "status": 409,
            "error": "tool_inactive",
            "message": f"{tool.asset_tag} is retired and cannot be checked out.",
        }

    if tool.calibration_due is not None and tool.calibration_due < now.date():
        return {
            "status": 409,
            "error": "calibration_overdue",
            "calibration_due": tool.calibration_due,
            "message": f"{tool.asset_tag} is overdue for calibration and cannot be checked out.",
        }

    recent = _recent_checkout(tool, employee, now)
    if recent is not None:
        return _checkout_result(recent, tool, employee)

    current = tool.current_checkout

    if current is None:
        checkout = Checkout.open(tool, employee, checked_out_at=now)
        return _checkout_result(checkout, tool, employee)

    if current.employee_id == employee.id:
        current.returned_at = now
        current.save(update_fields=["returned_at"])
        return _checkout_result(current, tool, employee)

    return {
        "status": 409,
        "error": "held_by_other",
        "holder_name": current.employee.name,
        "since": current.checked_out_at,
        "message": f"{tool.asset_tag} is already checked out to {current.employee.name}.",
    }
