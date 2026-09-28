from datetime import timedelta

import pytest
from django.utils import timezone

from crib.models import Employee, Tool


@pytest.fixture
def employee():
    return Employee.objects.create(badge_id="E-1001", name="Alex Kim", department="Machining")


@pytest.fixture
def other_employee():
    return Employee.objects.create(badge_id="E-1002", name="Sam Lowe", department="Assembly")


@pytest.fixture
def tool():
    return Tool.objects.create(asset_tag="T-0001", description="Torque wrench")


@pytest.fixture
def inactive_tool():
    return Tool.objects.create(asset_tag="T-0002", description="Retired caliper", is_active=False)


@pytest.fixture
def overdue_tool():
    return Tool.objects.create(
        asset_tag="T-0003",
        description="Dial indicator",
        calibration_due=timezone.now().date() - timedelta(days=1),
    )
