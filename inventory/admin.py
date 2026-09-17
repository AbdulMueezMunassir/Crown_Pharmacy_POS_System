from django.contrib import admin
from .models import Batch, GRN, GRNItem


class GRNItemInline(admin.TabularInline):
    model = GRNItem
    extra = 1
    fields = (
        'product', 'batch_number', 'quantity', 'free_quantity',
        'cost_price', 'discount_percent', 'selling_price',
        'manufacturing_date', 'expiry_date', 'line_total'
    )
    readonly_fields = ('line_total',)


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = (
        'product', 'batch_number', 'quantity_available', 'expiry_date',
        'days_until_expiry', 'expiry_status', 'supplier', 'quality_status'
    )
    list_filter = ('quality_status', 'is_active', 'cold_chain_verified')
    search_fields = ('batch_number', 'product__name', 'product__sku', 'grn_number')
    readonly_fields = ('created_at', 'updated_at', 'days_until_expiry', 'expiry_status')
    date_hierarchy = 'expiry_date'
    ordering = ('expiry_date',)
    list_per_page = 25

    fieldsets = (
        ('Product', {
            'fields': ('product', 'batch_number', 'supplier')
        }),
        ('Quantities', {
            'fields': ('quantity_received', 'quantity_available', 'quantity_reserved')
        }),
        ('Pricing (LKR)', {
            'fields': ('cost_price', 'selling_price')
        }),
        ('Dates', {
            'fields': ('manufacturing_date', 'expiry_date', 'received_date')
        }),
        ('Handling', {
            'fields': ('grn_number', 'storage_location', 'cold_chain_verified', 'quality_status', 'is_active')
        }),
        ('Meta', {
            'fields': ('created_by', 'created_at', 'updated_at', 'days_until_expiry', 'expiry_status'),
            'classes': ('collapse',)
        }),
    )


@admin.register(GRN)
class GRNAdmin(admin.ModelAdmin):
    list_display = (
        'grn_number', 'supplier', 'inward_date',
        'net_payable', 'status', 'received_by', 'created_at'
    )
    list_filter = ('status', 'supplier', 'inward_date')
    search_fields = ('grn_number', 'supplier_invoice', 'do_number', 'po_number')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [GRNItemInline]
    date_hierarchy = 'inward_date'