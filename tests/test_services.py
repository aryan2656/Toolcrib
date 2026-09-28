# handle_scan(badge, asset_tag) returns a plain dict: a "status" key holding
# the HTTP status code the view should respond with, plus the response body
# fields from PLAN.md's table (nested "tool"/"employee" dicts, and native
# date/datetime values — JsonResponse's default encoder serializes those).
from datetime import timedelta

import pytest
from django.utils import timezone

from crib.models import Checkout
from crib.services import handle_scan


@pytest.mark.django_db
def test_free_tool_checks_out(employee, tool):
    result = handle_scan(employee.badge_id, tool.asset_tag)

    assert result["status"] == 200
    assert result["action"] == "checked_out"
    assert result["tool"]["asset_tag"] == tool.asset_tag
    assert result["employee"]["badge_id"] == employee.badge_id

    checkout = Checkout.objects.get(tool=tool, employee=employee)
    assert checkout.returned_at is None
    assert result["due_back_at"] == checkout.due_back_at


@pytest.mark.django_db
def test_tool_held_by_same_employee_returns_it(employee, tool):
    checked_out_at = timezone.now() - timedelta(hours=1)
    Checkout.open(tool, employee, checked_out_at=checked_out_at)

    result = handle_scan(employee.badge_id, tool.asset_tag)

    assert result["status"] == 200
    assert result["action"] == "returned"
    assert result["tool"]["asset_tag"] == tool.asset_tag
    assert 59 <= result["duration_minutes"] <= 61

    checkout = Checkout.objects.get(tool=tool, employee=employee)
    assert checkout.returned_at is not None


@pytest.mark.django_db
def test_tool_held_by_other_employee_is_blocked(employee, other_employee, tool):
    checked_out_at = timezone.now() - timedelta(hours=1)
    Checkout.open(tool, other_employee, checked_out_at=checked_out_at)

    result = handle_scan(employee.badge_id, tool.asset_tag)

    assert result["status"] == 409
    assert result["error"] == "held_by_other"
    assert result["holder_name"] == other_employee.name
    assert result["since"] == checked_out_at
    assert "message" in result

    checkout = Checkout.objects.get(tool=tool)
    assert checkout.employee == other_employee
    assert checkout.returned_at is None


@pytest.mark.django_db
def test_unknown_badge_is_rejected(tool):
    result = handle_scan("E-9999", tool.asset_tag)

    assert result["status"] == 404
    assert result["error"] == "unknown_badge"
    assert result["value"] == "E-9999"
    assert "message" in result
    assert Checkout.objects.count() == 0


@pytest.mark.django_db
def test_unknown_asset_tag_is_rejected(employee):
    result = handle_scan(employee.badge_id, "T-9999")

    assert result["status"] == 404
    assert result["error"] == "unknown_tool"
    assert result["value"] == "T-9999"
    assert "message" in result
    assert Checkout.objects.count() == 0


@pytest.mark.django_db
def test_inactive_tool_is_blocked(employee, inactive_tool):
    result = handle_scan(employee.badge_id, inactive_tool.asset_tag)

    assert result["status"] == 409
    assert result["error"] == "tool_inactive"
    assert "message" in result
    assert Checkout.objects.count() == 0


@pytest.mark.django_db
def test_calibration_overdue_tool_is_blocked(employee, overdue_tool):
    result = handle_scan(employee.badge_id, overdue_tool.asset_tag)

    assert result["status"] == 409
    assert result["error"] == "calibration_overdue"
    assert result["calibration_due"] == overdue_tool.calibration_due
    assert "message" in result
    assert Checkout.objects.count() == 0


@pytest.mark.django_db
def test_repeat_scan_within_two_seconds_replays_without_changing_state(employee, tool):
    first = handle_scan(employee.badge_id, tool.asset_tag)
    second = handle_scan(employee.badge_id, tool.asset_tag)

    assert second == first
    # Scanners double-fire; a repeat within the window must not toggle state.
    assert Checkout.objects.count() == 1
    assert Checkout.objects.get(tool=tool, employee=employee).returned_at is None
