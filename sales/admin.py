from django.contrib import admin
from .models import Sale, SaleItem, Return, ReturnItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    fields = (
        'product', 'batch_number', 'expiry_date', 'quantity',
        'unit_price', 'discount_percent', 'line_total'
    )
    readonly_fields = ('line_total',)


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number', 'customer_name', 'salesperson',
        'grand_total', 'payment_method', 'status', 'created_at'
    )
    list_filter = ('status', 'payment_method', 'created_at', 'salesperson')
    search_fields = ('invoice_number', 'customer_name', 'customer_mobile')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [SaleItemInline]
    date_hierarchy = 'created_at'


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = (
        'return_number', 'sale', 'reason_code',
        'refund_method', 'refund_amount', 'status', 'created_at'
    )
    list_filter = ('status', 'reason_code', 'refund_method')
    search_fields = ('return_number', 'sale__invoice_number')
    inlines = [ReturnItemInline]