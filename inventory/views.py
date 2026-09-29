from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum, Count, Min, F
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from datetime import date, timedelta

from .models import Batch, GRN, GRNItem
from .forms import GRNForm, GRNItemFormSet
from products.models import Product
from suppliers.models import Supplier


# ══════════════════════════════════════════════════════════
# INVENTORY OVERVIEW
# ══════════════════════════════════════════════════════════

@login_required
def overview(request):
    today = date.today()
    in_30 = today + timedelta(days=30)
    in_90 = today + timedelta(days=90)

    active_batches = Batch.objects.filter(is_active=True, quantity_available__gt=0)

    # KPIs
    total_value = active_batches.aggregate(
        v=Sum(F('cost_price') * F('quantity_available'))
    )['v'] or 0

    total_units = active_batches.aggregate(t=Sum('quantity_available'))['t'] or 0
    total_batches = active_batches.count()

    low_stock_products = 0
    for p in Product.objects.filter(is_active=True):
        if 0 < p.total_stock <= p.min_stock_level:
            low_stock_products += 1

    out_of_stock = Product.objects.filter(is_active=True).annotate(
        stk=Sum('batches__quantity_available')
    ).filter(Q(stk=0) | Q(stk__isnull=True)).count()

    expiring_30 = active_batches.filter(
        expiry_date__gt=today, expiry_date__lte=in_30
    ).count()
    expiring_90 = active_batches.filter(
        expiry_date__gt=in_30, expiry_date__lte=in_90
    ).count()
    expired = active_batches.filter(expiry_date__lte=today).count()

    context = {
        'total_value': total_value,
        'total_units': total_units,
        'total_batches': total_batches,
        'low_stock_products': low_stock_products,
        'out_of_stock': out_of_stock,
        'expiring_30': expiring_30,
        'expiring_90': expiring_90,
        'expired': expired,
    }
    return render(request, 'inventory/overview.html', context)


# ══════════════════════════════════════════════════════════
# BATCH LIST & DETAIL
# ══════════════════════════════════════════════════════════

@login_required
def batch_list(request):
    today = date.today()
    qs = Batch.objects.filter(is_active=True).select_related('product', 'supplier')

    # Filters
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(batch_number__icontains=search) |
            Q(product__name__icontains=search) |
            Q(product__sku__icontains=search) |
            Q(grn_number__icontains=search)
        )

    expiry_filter = request.GET.get('expiry', '')
    if expiry_filter == 'expired':
        qs = qs.filter(expiry_date__lte=today, quantity_available__gt=0)
    elif expiry_filter == 'critical':
        qs = qs.filter(expiry_date__gt=today, expiry_date__lte=today + timedelta(days=30), quantity_available__gt=0)
    elif expiry_filter == 'warning':
        qs = qs.filter(expiry_date__gt=today + timedelta(days=30), expiry_date__lte=today + timedelta(days=90), quantity_available__gt=0)
    elif expiry_filter == 'safe':
        qs = qs.filter(expiry_date__gt=today + timedelta(days=90))

    status_filter = request.GET.get('status', '')
    if status_filter == 'available':
        qs = qs.filter(quantity_available__gt=0)
    elif status_filter == 'empty':
        qs = qs.filter(quantity_available=0)

    # FEFO ordering (earliest expiry first)
    qs = qs.order_by('expiry_date', 'created_at')

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'search': search,
        'expiry_filter': expiry_filter,
        'status_filter': status_filter,
        'total_count': qs.count(),
        'today': today,
    }
    return render(request, 'inventory/batch_list.html', context)


@login_required
def batch_detail(request, pk):
    batch = get_object_or_404(Batch, pk=pk)
    return render(request, 'inventory/batch_detail.html', {'batch': batch})


# ══════════════════════════════════════════════════════════
# STOCK RECEIVING (GRN)
# ══════════════════════════════════════════════════════════

@login_required
def grn_list(request):
    qs = GRN.objects.select_related('supplier', 'received_by').order_by('-created_at')

    # Filters
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(grn_number__icontains=search) |
            Q(supplier_invoice__icontains=search) |
            Q(do_number__icontains=search) |
            Q(supplier__name__icontains=search)
        )

    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'status_filter': status_filter,
        'search': search,
        'total_count': qs.count(),
    }
    return render(request, 'inventory/grn_list.html', context)


@login_required
def grn_create(request):
    if request.method == 'POST':
        form = GRNForm(request.POST)
        formset = GRNItemFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                grn = form.save(commit=False)
                grn.received_by = request.user
                grn.grn_number = _generate_grn_number()
                grn.status = 'draft'
                grn.save()

                formset.instance = grn
                items = formset.save(commit=False)

                subtotal = 0
                trade_discount = 0
                for item in items:
                    if not item.product:
                        continue
                    item.save()
                    line_gross = (item.quantity + (item.free_quantity or 0)) * item.cost_price
                    line_discount = line_gross * (item.discount_percent / 100)
                    item.line_total = line_gross - line_discount
                    item.save(update_fields=['line_total'])
                    subtotal += line_gross
                    trade_discount += line_discount

                grn.subtotal = subtotal
                grn.trade_discount = trade_discount
                grn.vat_amount = 0
                grn.net_payable = subtotal - trade_discount
                grn.save()

            messages.success(
                request,
                f'GRN {grn.grn_number} created as draft. Review and Post to Inventory.'
            )
            return redirect('inventory:grn_detail', pk=grn.pk)
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = GRNForm()
        formset = GRNItemFormSet()

    return render(request, 'inventory/grn_form.html', {
        'form': form,
        'formset': formset,
    })


@login_required
def grn_detail(request, pk):
    grn = get_object_or_404(GRN, pk=pk)
    return render(request, 'inventory/grn_detail.html', {'grn': grn})


@login_required
@transaction.atomic
def grn_post(request, pk):
    """Convert a draft GRN to posted — creates batches and updates inventory."""
    grn = get_object_or_404(GRN, pk=pk)

    if grn.status != 'draft':
        messages.error(request, 'Only draft GRNs can be posted.')
        return redirect('inventory:grn_detail', pk=grn.pk)

    if grn.items.count() == 0:
        messages.error(request, 'Cannot post a GRN with no items.')
        return redirect('inventory:grn_detail', pk=grn.pk)

    created_batches = 0
    for item in grn.items.all():
        # Check for duplicate batch
        existing = Batch.objects.filter(
            product=item.product,
            batch_number=item.batch_number
        ).first()

        if existing:
            # Add to existing batch
            existing.quantity_received += item.quantity + (item.free_quantity or 0)
            existing.quantity_available += item.quantity + (item.free_quantity or 0)
            existing.cost_price = item.cost_price
            existing.selling_price = item.selling_price
            existing.save()
            item.batch = existing
        else:
            # Create new batch
            batch = Batch.objects.create(
                product=item.product,
                batch_number=item.batch_number,
                supplier=grn.supplier,
                quantity_received=item.quantity + (item.free_quantity or 0),
                quantity_available=item.quantity + (item.free_quantity or 0),
                cost_price=item.cost_price,
                selling_price=item.selling_price,
                manufacturing_date=item.manufacturing_date,
                expiry_date=item.expiry_date,
                received_date=grn.inward_date,
                grn_number=grn.grn_number,
                created_by=request.user,
            )
            item.batch = batch
            created_batches += 1

        item.save()

    grn.status = 'posted'
    grn.save()

    messages.success(
        request,
        f'GRN {grn.grn_number} posted! {created_batches} new batches created and stock updated.'
    )
    return redirect('inventory:grn_detail', pk=grn.pk)


@login_required
def grn_cancel(request, pk):
    grn = get_object_or_404(GRN, pk=pk)
    if grn.status != 'draft':
        messages.error(request, 'Only draft GRNs can be cancelled.')
        return redirect('inventory:grn_detail', pk=grn.pk)
    grn.status = 'cancelled'
    grn.save()
    messages.success(request, f'GRN {grn.grn_number} cancelled.')
    return redirect('inventory:grn_list')


# ══════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════

def _generate_grn_number():
    today = timezone.now().date()
    prefix = f"GRN-{today.year}-"
    last = GRN.objects.filter(grn_number__startswith=prefix).order_by('-grn_number').first()
    if last:
        try:
            num = int(last.grn_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1
    return f"{prefix}{num:04d}"