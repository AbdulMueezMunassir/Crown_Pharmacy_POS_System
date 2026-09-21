from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum, Min, Count
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models.deletion import ProtectedError

from .models import Product, Category
from .forms import ProductForm, CategoryForm


# ══════════════════════════════════════════════════════════
# PRODUCT VIEWS
# ══════════════════════════════════════════════════════════

@login_required
def product_list(request):
    qs = Product.objects.filter(is_active=True).select_related('category')

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(name__icontains=search) |
            Q(generic_name__icontains=search) |
            Q(sku__icontains=search) |
            Q(barcode__icontains=search)
        )

    category_id = request.GET.get('category')
    if category_id:
        qs = qs.filter(category_id=category_id)

    drug_schedule = request.GET.get('schedule')
    if drug_schedule:
        qs = qs.filter(drug_schedule=drug_schedule)

    stock_filter = request.GET.get('stock')
    if stock_filter == 'low':
        qs = qs.annotate(stock=Sum('batches__quantity_available')).filter(stock__lte=100, stock__gt=0)
    elif stock_filter == 'out':
        qs = qs.annotate(stock=Sum('batches__quantity_available')).filter(Q(stock=0) | Q(stock__isnull=True))

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


@login_required
def product_detail(request, pk):
    from datetime import date, timedelta

    product = get_object_or_404(Product, pk=pk)
    batches = product.batches.filter(is_active=True).select_related('supplier').order_by('expiry_date')

    today = date.today()
    in_30_days = today + timedelta(days=30)

    total_available = batches.filter(quantity_available__gt=0).aggregate(
        total=Sum('quantity_available')
    )['total'] or 0

    batch_count = batches.filter(quantity_available__gt=0).count()

    expiring_30 = batches.filter(
        expiry_date__gt=today,
        expiry_date__lte=in_30_days,
        quantity_available__gt=0,
    ).count()

    expired = batches.filter(
        expiry_date__lt=today,
        quantity_available__gt=0,
    ).count()

    context = {
        'product': product,
        'batches': batches,
        'total_available': total_available,
        'batch_count': batch_count,
        'expiring_30': expiring_30,
        'expired': expired,
    }
    return render(request, 'products/detail.html', context)

@login_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, f'Product "{product.name}" created successfully.')
            return redirect('products:detail', pk=product.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ProductForm()

    return render(request, 'products/form.html', {
        'form': form,
        'mode': 'create',
        'product': None,
    })


@login_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated successfully.')
            return redirect('products:detail', pk=product.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = ProductForm(instance=product)

    return render(request, 'products/form.html', {
        'form': form,
        'mode': 'edit',
        'product': product,
    })


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if request.method == 'POST':
        name = product.name
        product.is_active = False
        product.save()
        messages.success(request, f'Product "{name}" has been deactivated.')
        return redirect('products:list')

    return render(request, 'products/confirm_delete.html', {'product': product})


# ══════════════════════════════════════════════════════════
# CATEGORY VIEWS
# ══════════════════════════════════════════════════════════

@login_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count('products')).order_by('name')
    return render(request, 'products/category_list.html', {'categories': categories})


@login_required
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            cat = form.save()
            messages.success(request, f'Category "{cat.name}" created.')
            return redirect('products:category_list')
    else:
        form = CategoryForm()
    return render(request, 'products/category_form.html', {
        'form': form,
        'mode': 'create',
    })


@login_required
def category_edit(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f'Category "{category.name}" updated.')
            return redirect('products:category_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'products/category_form.html', {
        'form': form,
        'mode': 'edit',
        'category': category,
    })


@login_required
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = category.name
        # Unlink products instead of deleting them
        Product.objects.filter(category=category).update(category=None)
        category.delete()
        messages.success(request, f'Category "{name}" deleted. Products unlinked.')
        return redirect('products:category_list')
    return render(request, 'products/confirm_category_delete.html', {'category': category})