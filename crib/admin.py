from django.contrib import admin

from .models import Checkout, Employee, Tool


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("badge_id", "name", "department", "is_active")
    list_filter = ("department", "is_active")
    search_fields = ("badge_id", "name")


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ("asset_tag", "description", "calibration_due", "is_active")
    list_filter = ("is_active",)
    search_fields = ("asset_tag", "description")


@admin.register(Checkout)
class CheckoutAdmin(admin.ModelAdmin):
    list_display = ("tool", "employee", "checked_out_at", "due_back_at", "returned_at")
    list_filter = ("returned_at",)
    search_fields = ("tool__asset_tag", "employee__badge_id", "employee__name")
    autocomplete_fields = ("tool", "employee")
