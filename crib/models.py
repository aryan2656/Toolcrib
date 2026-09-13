from datetime import timedelta

from django.db import models
from django.db.models import Exists, OuterRef
from django.utils import timezone

DEFAULT_LOAN_HOURS = 8


class Employee(models.Model):
    badge_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    department = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.badge_id})"


class ToolQuerySet(models.QuerySet):
    def currently_out(self):
        # Checkout is a reverse FK from Tool, so a plain select_related()
        # can't join it. Prefetch the open checkout (with its employee)
        # instead, so `tool.current_checkout` is free for every row here.
        open_checkouts = Checkout.objects.filter(
            returned_at__isnull=True
        ).select_related("employee")
        # filter(checkouts__returned_at__isnull=True) would also match tools
        # with NO checkouts at all (LEFT JOIN produces NULL either way), so
        # existence is checked with Exists() instead of a plain filter.
        has_open_checkout = Checkout.objects.filter(
            tool=OuterRef("pk"), returned_at__isnull=True
        )
        return self.filter(Exists(has_open_checkout)).prefetch_related(
            models.Prefetch("checkouts", queryset=open_checkouts, to_attr="_open_checkouts")
        )


class Tool(models.Model):
    asset_tag = models.CharField(max_length=20, unique=True)
    description = models.CharField(max_length=255)
    calibration_due = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    objects = ToolQuerySet.as_manager()

    def __str__(self):
        return self.asset_tag

    @property
    def current_checkout(self):
        if hasattr(self, "_open_checkouts"):
            return self._open_checkouts[0] if self._open_checkouts else None
        return self.checkouts.filter(returned_at__isnull=True).select_related("employee").first()


class Checkout(models.Model):
    tool = models.ForeignKey(Tool, on_delete=models.PROTECT, related_name="checkouts")
    employee = models.ForeignKey(Employee, on_delete=models.PROTECT, related_name="checkouts")
    checked_out_at = models.DateTimeField(default=timezone.now)
    due_back_at = models.DateTimeField()
    returned_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["tool", "returned_at"]),
        ]

    def __str__(self):
        return f"{self.tool.asset_tag} -> {self.employee.badge_id}"

    @classmethod
    def open(cls, tool, employee, *, checked_out_at=None):
        checked_out_at = checked_out_at or timezone.now()
        return cls.objects.create(
            tool=tool,
            employee=employee,
            checked_out_at=checked_out_at,
            due_back_at=checked_out_at + timedelta(hours=DEFAULT_LOAN_HOURS),
        )
