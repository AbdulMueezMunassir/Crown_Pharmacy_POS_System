from django.contrib import admin
from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'contact_person', 'phone', 'status', 'payment_terms_days', 'outstanding_balance')
    list_filter = ('status', 'payment_terms_days')
    search_fields = ('code', 'name', 'contact_person', 'phone', 'email', 'nmra_license')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Identity', {
            'fields': ('code', 'name', 'status')
        }),
        ('Contact', {
            'fields': ('contact_person', 'phone', 'email', 'address')
        }),
        ('Regulatory', {
            'fields': ('nmra_license', 'license_expiry')
        }),
        ('Commercial', {
            'fields': ('credit_terms', 'payment_terms_days', 'outstanding_balance', 'reliability_score')
        }),
        ('Meta', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )