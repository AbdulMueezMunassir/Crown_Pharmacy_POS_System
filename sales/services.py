from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError

from inventory.models import Batch
from products.models import Product


def find_fefo_batch(product_id, requested_qty=1):
    """
    Find the earliest expiring valid batch for a product (FEFO).
    Returns the batch or None if no valid stock.
    """
    return Batch.objects.filter(
        product_id=product_id,
        is_active=True,
        quantity_available__gte=requested_qty,
        expiry_date__gt=date.today(),
        quality_status='approved',
    ).order_by('expiry_date', 'created_at').first()


def get_all_valid_batches(product_id):
    """Return all valid (non-expired, in-stock) batches sorted by FEFO."""
    return Batch.objects.filter(
        product_id=product_id,
        is_active=True,
        quantity_available__gt=0,
        expiry_date__gt=date.today(),
        quality_status='approved',
    ).order_by('expiry_date', 'created_at')


def validate_stock_available(product_id, quantity):
    """Check if enough valid stock is available (across all batches)."""
    total = sum(
        b.quantity_available
        for b in get_all_valid_batches(product_id)
    )
    return total >= quantity, total


@transaction.atomic
def deduct_fefo_stock(product_id, quantity, sale=None):
    """
    Deduct quantity from FEFO batches.
    Returns list of (batch, quantity_taken) tuples for sale item creation.
    Raises ValidationError if insufficient stock.
    """
    remaining = quantity
    allocations = []

    batches = get_all_valid_batches(product_id).select_for_update()

    for batch in batches:
        if remaining <= 0:
            break

        take = min(batch.quantity_available, remaining)

        # Update batch
        batch.quantity_available -= take
        batch.save(update_fields=['quantity_available'])

        allocations.append((batch, take))
        remaining -= take

    if remaining > 0:
        raise ValidationError(
            f'Insufficient valid stock for product. Short by {remaining} units.'
        )

    return allocations


@transaction.atomic
def restore_batch_stock(batch_id, quantity):
    """Restore stock to a batch (for returns)."""
    try:
        batch = Batch.objects.select_for_update().get(id=batch_id)
        batch.quantity_available += quantity
        batch.save(update_fields=['quantity_available'])
        return True
    except Batch.DoesNotExist:
        return False