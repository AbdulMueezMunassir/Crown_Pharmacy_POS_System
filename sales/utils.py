from django.utils import timezone
from .models import Sale


def generate_invoice_number(prefix='INV'):
    """Generate sequential invoice number like INV-2026-09-0001."""
    today = timezone.now().date()
    year_month = today.strftime('%Y-%m')
    pattern = f"{prefix}-{year_month}-"

    last = Sale.objects.filter(
        invoice_number__startswith=pattern
    ).order_by('-invoice_number').first()

    if last:
        try:
            num = int(last.invoice_number.split('-')[-1]) + 1
        except (ValueError, IndexError):
            num = 1
    else:
        num = 1

    return f"{pattern}{num:04d}"