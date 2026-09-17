from django.contrib import admin
from .models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'patient_id', 'name', 'mobile', 'loyalty_tier',
        'loyalty_points', 'total_spent', 'total_invoices', 'last_purchase_date'
    )
    list_filter = ('loyalty_tier', 'is_active')
    search_fields = ('patient_id', 'name', 'mobile', 'email', 'nic')
    readonly_fields = ('patient_id', 'created_at', 'updated_at')
    fieldsets = (
        ('Identity', {
            'fields': ('patient_id', 'name', 'nic', 'date_of_birth')
        }),
        ('Contact', {
            'fields': ('mobile', 'email', 'address')
        }),
        ('Medical', {
            'fields': ('allergies', 'chronic_conditions')
        }),
        ('Loyalty', {
            'fields': ('loyalty_tier', 'loyalty_points', 'total_spent', 'total_invoices', 'last_purchase_date')
        }),
        ('Meta', {
            'fields': ('is_active', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )