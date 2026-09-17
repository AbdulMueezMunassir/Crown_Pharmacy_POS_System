from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'full_name', 'email', 'role', 'is_active_staff', 'last_login')
    list_filter = ('role', 'is_active_staff', 'is_staff', 'is_superuser')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'employee_id', 'slmc_license')
    ordering = ('first_name',)

    fieldsets = BaseUserAdmin.fieldsets + (
        ('Pharmacy Profile', {
            'fields': ('role', 'phone', 'slmc_license', 'employee_id', 'is_active_staff')
        }),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Pharmacy Profile', {
            'fields': ('role', 'phone', 'slmc_license', 'employee_id', 'is_active_staff')
        }),
    )