import json
from decimal import Decimal
from datetime import date
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .models import Sale, SaleItem
from .services import find_fefo_batch, validate_stock_available, deduct_fefo_stock
from .utils import generate_invoice_number
from products.models import Product
from customers.models import Customer
from inventory.models import Batch


# ══════════════════════════════════════════════════════════
# POS SCREEN
# ══════════════════════════════════════════════════════════

@login_required
def pos(request):
    """Main POS / Billing screen."""
    # Quick picks: fast movers with valid stock
    quick_picks = Product.objects.filter(
        is_active=True,
        batches__quantity_available__gt=0,
        batches__expiry_date__gt=date.today(),
    ).distinct().order_by('name')[:12]

    context = {
        'quick_picks': quick_picks,
        'today': date.today(),
    }
    return render(request, 'sales/pos.html', context)


# ══════════════════════════════════════════════════════════
# AJAX APIs FOR POS
# ══════════════════════════════════════════════════════════

@login_required
def api_product_search(request):
    """Fuzzy-ish product search API for POS."""
    q = request.GET.get('q', '').strip()
    if len(q) < 2:
        return JsonResponse({'results': []})

    products = Product.objects.filter(
        is_active=True,
    ).filter(
        Q(name__icontains=q) |
        Q(generic_name__icontains=q) |
        Q(sku__icontains=q) |
        Q(barcode=q)
    ).prefetch_related('batches')[:10]

    results = []
    for p in products:
        # FEFO batch
        fefo = find_fefo_batch(p.id, requested_qty=1)
        total_available = sum(
            b.quantity_available for b in p.batches.all()
            if b.expiry_date > date.today() and b.is_active
        )

        results.append({
            'id': p.id,
            'name': p.name,
            'generic_name': p.generic_name,
            'sku': p.sku,
            'barcode': p.barcode or '',
            'selling_price': float(fefo.selling_price) if fefo else float(p.selling_price),
            'total_stock': total_available,
            'batch_number': fefo.batch_number if fefo else None,
            'batch_id': fefo.id if fefo else None,
            'expiry_date': fefo.expiry_date.strftime('%d %b %Y') if fefo else None,
            'days_until_expiry': fefo.days_until_expiry if fefo else None,
            'expiry_status': fefo.expiry_status if fefo else None,
            'unit_type': p.get_unit_type_display(),
        })

    return JsonResponse({'results': results})


@login_required
def api_product_batches(request, product_id):
    """Return all valid batches for a product (for manual batch override)."""
    batches = Batch.objects.filter(
        product_id=product_id,
        is_active=True,
        quantity_available__gt=0,
        expiry_date__gt=date.today(),
        quality_status='approved',
    ).order_by('expiry_date')

    return JsonResponse({
        'batches': [{
            'id': b.id,
            'batch_number': b.batch_number,
            'quantity_available': b.quantity_available,
            'expiry_date': b.expiry_date.strftime('%d %b %Y'),
            'days_until_expiry': b.days_until_expiry,
            'expiry_status': b.expiry_status,
            'selling_price': float(b.selling_price),
        } for b in batches]
    })


@login_required
@require_POST
def api_checkout(request):
    """
    Complete a sale — the critical transaction.
    Expects JSON:
    {
      "items": [{"product_id": int, "quantity": int, "unit_price": float, "discount_percent": float, "batch_id": int (optional)}],
      "customer": {"id": int (optional), "name": str, "mobile": str, "email": str},
      "payment_method": "cash"|"card"|"digital"|"insurance"|"split",
      "amount_paid": float,
      "discount_amount": float
    }
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    items = data.get('items', [])
    if not items:
        return JsonResponse({'error': 'Cart is empty'}, status=400)

    customer_data = data.get('customer', {})
    payment_method = data.get('payment_method', 'cash')
    amount_paid = Decimal(str(data.get('amount_paid', 0)))
    extra_discount = Decimal(str(data.get('discount_amount', 0)))

    try:
        with transaction.atomic():
            # ── Customer ──────────────────────────────
            customer = None
            if customer_data.get('id'):
                customer = Customer.objects.filter(id=customer_data['id']).first()
            elif customer_data.get('mobile'):
                customer = Customer.objects.filter(mobile=customer_data['mobile']).first()

            # ── Compute totals from server-side prices ──
            subtotal = Decimal('0')
            line_items = []

            for item in items:
                product_id = int(item['product_id'])
                quantity = int(item['quantity'])
                product = Product.objects.get(id=product_id)

                # FEFO allocation
                allocations = deduct_fefo_stock(product_id, quantity)

                for batch, take in allocations:
                    unit_price = batch.selling_price
                    line_total = unit_price * take
                    subtotal += line_total

                    line_items.append({
                        'product': product,
                        'batch': batch,
                        'quantity': take,
                        'unit_price': unit_price,
                        'line_total': line_total,
                    })

            # ── Grand total ──────────────────────────
            grand_total = subtotal - extra_discount
            if grand_total < 0:
                grand_total = Decimal('0')
            change = amount_paid - grand_total if amount_paid > grand_total else Decimal('0')

            # ── Create Sale ──────────────────────────
            sale = Sale.objects.create(
                invoice_number=generate_invoice_number(),
                customer=customer,
                customer_name=customer_data.get('name', '') or (customer.name if customer else ''),
                customer_mobile=customer_data.get('mobile', '') or (customer.mobile if customer else ''),
                customer_email=customer_data.get('email', '') or (customer.email if customer else ''),
                salesperson=request.user,
                subtotal=subtotal,
                discount_amount=extra_discount,
                tax_amount=Decimal('0'),
                grand_total=grand_total,
                payment_method=payment_method,
                amount_paid=amount_paid,
                change_amount=change,
                status='completed',
            )

            # ── Create SaleItems ─────────────────────
            for li in line_items:
                SaleItem.objects.create(
                    sale=sale,
                    product=li['product'],
                    batch=li['batch'],
                    product_name=li['product'].name,
                    batch_number=li['batch'].batch_number,
                    expiry_date=li['batch'].expiry_date,
                    quantity=li['quantity'],
                    unit_price=li['unit_price'],
                    line_total=li['line_total'],
                )

            # ── Update customer loyalty ──────────────
            if customer:
                customer.total_spent = (customer.total_spent or Decimal('0')) + grand_total
                customer.total_invoices = (customer.total_invoices or 0) + 1
                customer.loyalty_points = (customer.loyalty_points or 0) + int(grand_total / 100)
                from django.utils import timezone
                customer.last_purchase_date = timezone.now()
                customer.save(update_fields=[
                    'total_spent', 'total_invoices', 'loyalty_points', 'last_purchase_date'
                ])
                customer.update_loyalty_tier()

            return JsonResponse({
                'success': True,
                'sale_id': sale.id,
                'invoice_number': sale.invoice_number,
                'grand_total': float(grand_total),
                'change': float(change),
                'redirect': f'/sales/{sale.id}/invoice/',
            })

    except ValidationError as e:
        return JsonResponse({'error': str(e)}, status=400)
    except Product.DoesNotExist:
        return JsonResponse({'error': 'Product not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': f'Checkout failed: {str(e)}'}, status=500)


# ══════════════════════════════════════════════════════════
# SALES HISTORY
# ══════════════════════════════════════════════════════════

@login_required
def sale_list(request):
    qs = Sale.objects.select_related('salesperson', 'customer').order_by('-created_at')

    # Salesperson: only see their own sales (unless admin)
    if request.user.role == 'salesperson':
        qs = qs.filter(salesperson=request.user)

    # Filters
    search = request.GET.get('q', '').strip()
    if search:
        qs = qs.filter(
            Q(invoice_number__icontains=search) |
            Q(customer_name__icontains=search) |
            Q(customer_mobile__icontains=search)
        )

    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    payment_filter = request.GET.get('payment', '')
    if payment_filter:
        qs = qs.filter(payment_method=payment_filter)

    date_filter = request.GET.get('date', '')
    if date_filter == 'today':
        qs = qs.filter(created_at__date=date.today())
    elif date_filter == 'week':
        from datetime import timedelta
        qs = qs.filter(created_at__date__gte=date.today() - timedelta(days=7))
    elif date_filter == 'month':
        qs = qs.filter(created_at__date__gte=date.today().replace(day=1))

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'payment_filter': payment_filter,
        'date_filter': date_filter,
        'total_count': qs.count(),
    }
    return render(request, 'sales/history.html', context)


@login_required
def sale_detail(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    return render(request, 'sales/sale_detail.html', {'sale': sale})


@login_required
def invoice_view(request, pk):
    """Printable invoice for a sale."""
    sale = get_object_or_404(Sale, pk=pk)
    return render(request, 'sales/invoice.html', {'sale': sale})


# Import for validation errors
from django.core.exceptions import ValidationError