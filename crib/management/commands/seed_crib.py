from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from crib.models import Checkout, Employee, Tool

FIRST_NAMES = [
    "James", "Maria", "Wei", "Fatima", "Liam", "Priya", "Carlos", "Anna",
    "Kenji", "Grace", "Omar", "Nina", "Tyrell", "Elena", "Sam", "Ivy",
    "Marcus", "Dana", "Raj", "Sofia",
]
LAST_NAMES = [
    "Nguyen", "Garcia", "Kim", "Khan", "Brown", "Patel", "Rossi", "Ivanov",
    "Suzuki", "Lee", "Ali", "Novak", "Jackson", "Petrova", "Chen", "Wright",
    "Diallo", "Silva", "Kumar", "Torres",
]
DEPARTMENTS = ["Machining", "Assembly", "Welding", "QA", "Maintenance"]

TOOL_DESCRIPTIONS = [
    'Torque wrench 1/2"', "Digital caliper", "Cordless drill", "Angle grinder",
    "Impact driver", "Feeler gauge set", "Dial indicator", "Micrometer 0-25mm",
    "Bench vise", "Pipe wrench", "Hex key set", "Multimeter", "Heat gun",
    "Bandsaw blade guide", "Deburring tool", "Rivet gun", "Tap and die set",
    "Combination square", "Height gauge", "Pry bar set", 'Socket set 3/8"',
    "Ratchet strap set", "Come-along winch", "Bolt cutters", "Pipe cutter",
    'Spirit level 24"', "Chain hoist 1-ton", "Air ratchet", "Grease gun",
    "Torque screwdriver",
]

EMPLOYEE_COUNT = 20
TOOL_COUNT = 30
OVERDUE_TOOL_COUNT = 2
OPEN_CHECKOUT_COUNT = 5


class Command(BaseCommand):
    help = (
        f"Wipe and reseed crib data: {EMPLOYEE_COUNT} employees, {TOOL_COUNT} "
        f"tools ({OVERDUE_TOOL_COUNT} calibration-overdue, 1 inactive), "
        f"{OPEN_CHECKOUT_COUNT} already checked out."
    )

    def handle(self, *args, **options):
        with transaction.atomic():
            # Re-runnable: clear prior seed data first, in FK-safe order.
            Checkout.objects.all().delete()
            Tool.objects.all().delete()
            Employee.objects.all().delete()

            employees = self._seed_employees()
            tools = self._seed_tools()
            self._seed_checkouts(employees, tools)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {len(employees)} employees, {len(tools)} tools, "
            f"{OPEN_CHECKOUT_COUNT} open checkouts."
        ))

    def _seed_employees(self):
        employees = [
            Employee(
                badge_id=f"E-{1001 + i}",
                name=f"{FIRST_NAMES[i]} {LAST_NAMES[i]}",
                department=DEPARTMENTS[i % len(DEPARTMENTS)],
            )
            for i in range(EMPLOYEE_COUNT)
        ]
        return Employee.objects.bulk_create(employees)

    def _seed_tools(self):
        today = date.today()
        tools = []
        for i in range(TOOL_COUNT):
            calibration_due = None
            if i < OVERDUE_TOOL_COUNT:
                calibration_due = today - timedelta(days=30 + i)
            elif i < OVERDUE_TOOL_COUNT + 8:
                calibration_due = today + timedelta(days=90 + i)

            tools.append(Tool(
                asset_tag=f"T-{i + 1:04d}",
                description=TOOL_DESCRIPTIONS[i],
                calibration_due=calibration_due,
                is_active=i != TOOL_COUNT - 1,  # last tool is the inactive one
            ))
        return Tool.objects.bulk_create(tools)

    def _seed_checkouts(self, employees, tools):
        # Only hand out tools the service layer would actually allow, so the
        # seeded state looks like something handle_scan() could have produced.
        eligible = [
            tool for tool in tools
            if tool.is_active and (tool.calibration_due is None or tool.calibration_due >= date.today())
        ]
        for employee, tool in zip(employees[:OPEN_CHECKOUT_COUNT], eligible[:OPEN_CHECKOUT_COUNT]):
            Checkout.open(tool, employee)
