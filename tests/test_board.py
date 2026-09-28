from datetime import timedelta

import pytest
from django.utils import timezone

from crib.models import Checkout, Tool
from crib.services import board_state


@pytest.mark.django_db
def test_board_is_empty_when_nothing_is_out():
    result = board_state()

    assert result["tools"] == []
    assert "generated_at" in result


@pytest.mark.django_db
def test_checked_out_tool_appears_on_board(employee, tool):
    checkout = Checkout.open(tool, employee, checked_out_at=timezone.now())

    result = board_state()

    assert len(result["tools"]) == 1
    row = result["tools"][0]
    assert row["asset_tag"] == tool.asset_tag
    assert row["description"] == tool.description
    assert row["holder_name"] == employee.name
    assert row["checked_out_at"] == checkout.checked_out_at
    assert row["due_back_at"] == checkout.due_back_at
    assert row["overdue"] is False


@pytest.mark.django_db
def test_returned_tool_does_not_appear_on_board(employee, tool):
    checkout = Checkout.open(tool, employee, checked_out_at=timezone.now() - timedelta(hours=1))
    checkout.returned_at = timezone.now()
    checkout.save()

    result = board_state()

    assert result["tools"] == []


@pytest.mark.django_db
def test_overdue_tool_is_flagged(employee, tool):
    # Checkout.open()'s default loan period is 8h, so backdating
    # checked_out_at by 9h puts due_back_at 1h in the past.
    Checkout.open(tool, employee, checked_out_at=timezone.now() - timedelta(hours=9))

    result = board_state()

    assert result["tools"][0]["overdue"] is True


@pytest.mark.django_db
def test_board_orders_soonest_due_first(employee, other_employee):
    tool_a = Tool.objects.create(asset_tag="T-0010", description="Bench vise")
    tool_b = Tool.objects.create(asset_tag="T-0011", description="Multimeter")

    now = timezone.now()
    Checkout.open(tool_a, employee, checked_out_at=now)  # due in 8h
    Checkout.open(tool_b, other_employee, checked_out_at=now - timedelta(hours=7))  # due in 1h

    result = board_state()

    assert [row["asset_tag"] for row in result["tools"]] == [tool_b.asset_tag, tool_a.asset_tag]
