from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum
from datetime import timedelta

from products.models import Product
from inventory.models import Batch
from sales.models import Sale


@login_required
def home(request):
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)
    ninety_days_from_now = today + timedelta(days=90)

    today_sales = Sale.objects.filter(
        created_at__date=today, status='completed'
    ).aggregate(total=Sum('grand_total'))['total'] or 0

    monthly_sales = Sale.objects.filter(
        created_at__date__gte=thirty_days_ago, status='completed'
    ).aggregate(total=Sum('grand_total'))['total'] or 0

    total_products = Product.objects.filter(is_active=True).count()

    inventory_value = Batch.objects.filter(
        is_active=True, quantity_available__gt=0
    ).aggregate(value=Sum('cost_price'))['value'] or 0

    low_stock_count = 0
    for p in Product.objects.filter(is_active=True):
        if 0 < p.total_stock <= p.min_stock_level:
            low_stock_count += 1

    expiring_soon = Batch.objects.filter(
        is_active=True,
        quantity_available__gt=0,
        expiry_date__gt=today,
        expiry_date__lte=ninety_days_from_now,
    ).count()

    recent_sales = Sale.objects.select_related('salesperson').order_by('-created_at')[:5]

    fefo_batches = Batch.objects.filter(
        is_active=True,
        quantity_available__gt=0,
        expiry_date__gt=today,
        expiry_date__lte=today + timedelta(days=30),
    ).select_related('product').order_by('expiry_date')[:5]

    context = {
        'today_sales': today_sales,
        'monthly_sales': monthly_sales,
        'total_products': total_products,
        'inventory_value': inventory_value,
        'low_stock_count': low_stock_count,
        'expiring_soon': expiring_soon,
        'recent_sales': recent_sales,
        'fefo_batches': fefo_batches,
        'today': today,
    }
    return render(request, 'dashboard/home.html', context)