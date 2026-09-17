from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'sku', 'name', 'generic_name', 'category',
        'drug_schedule', 'selling_price', 'total_stock',
        'stock_status', 'is_active'
    )
    list_filter = (
        'category', 'drug_schedule', 'is_active',
        'is_cold_chain', 'is_controlled'
    )
    search_fields = ('sku', 'barcode', 'name', 'generic_name', 'brand')
    readonly_fields = ('created_at', 'updated_at')
    list_per_page = 25

    fieldsets = (
        ('Identity', {
            'fields': ('sku', 'barcode', 'name', 'generic_name', 'brand', 'category')
        }),
        ('Classification', {
            'fields': ('drug_schedule', 'dosage_form', 'strength', 'description')
        }),
        ('Pricing (LKR)', {
            'fields': ('cost_price', 'selling_price', 'mrp', 'tax_rate', 'discount_percent')
        }),
        ('Inventory', {
            'fields': ('unit_type', 'min_stock_level', 'max_stock_level', 'storage_location')
        }),
        ('Handling', {
            'fields': ('is_cold_chain', 'is_controlled', 'is_active')
        }),
        ('Media', {
            'fields': ('image',)
        }),
        ('Meta', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )