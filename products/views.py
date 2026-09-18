from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db.models import Q, Sum, Min
from django.core.paginator import Paginator

from .models import Product, Category


@login_required
def product_list(request):
    qs = Product.objects.filter(is_active=True).select_related('category').prefetch_related('batches')

    # Search
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(generic_name__icontains=search) |
            Q(sku__icontains=search) |
            Q(barcode__icontains=search)
        )

    # Filters
    category_id = request.GET.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)

    drug_schedule = request.GET.get('schedule')
    if drug_schedule:
        qs = qs.filter(drug_schedule=drug_schedule)

    # Pagination
    paginator = Paginator(qs, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search': search,
        'categories': Category.objects.filter(is_active=True),
        'total_count': qs.count(),
        'schedule_choices': Product.DRUG_SCHEDULE_CHOICES,
    }
    return render(request, 'products/list.html', context)