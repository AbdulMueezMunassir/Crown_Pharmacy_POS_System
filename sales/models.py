from django.db import models
from django.conf import settings
from django.utils import timezone


class Sale(models.Model):
    STATUS_CHOICES = [
        ('completed', 'Completed'),
        ('partially_returned', 'Partially Returned'),
        ('returned', 'Returned'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_CHOICES = [
        ('cash', 'Cash'),
        ('card', 'Card'),
        ('digital', 'Digital / QR'),
        ('insurance', 'Insurance'),
        ('split', 'Split Payment'),
        ('credit', 'Store Credit'),
    ]

    invoice_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='sales'
    )
    customer_name = models.CharField(max_length=200, blank=True)
    customer_mobile = models.CharField(max_length=20, blank=True)
    customer_email = models.EmailField(blank=True)

    salesperson = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='sales_made'
    )

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    payment_details = models.JSONField(default=dict, blank=True)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    change_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='completed')
    notes = models.TextField(blank=True)
    prescription_ref = models.CharField("Prescription Reference", max_length=100, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['invoice_number']),
            models.Index(fields=['created_at']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"{self.invoice_number} — LKR {self.grand_total}"


class SaleItem(models.Model):
    """A line on a sale. Each line is tied to ONE batch (FEFO)."""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    batch = models.ForeignKey('inventory.Batch', on_delete=models.PROTECT)

    product_name = models.CharField(max_length=255)
    batch_number = models.CharField(max_length=100)
    expiry_date = models.DateField()

    quantity = models.PositiveIntegerField()
    returned_quantity = models.PositiveIntegerField(default=0)

    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    line_total = models.DecimalField(max_digits=12, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product_name} x{self.quantity}"

    @property
    def total_after_discount(self):
        return self.line_total - self.discount_amount


class Return(models.Model):
    REASON_CHOICES = [
        ('unopened', 'Unopened / Patient Changed Mind'),
        ('adverse', 'Adverse Reaction'),
        ('wrong_item', 'Wrong Item Dispensed'),
        ('damaged', 'Damaged Packaging'),
        ('expired', 'Expired Product'),
        ('doctor_change', 'Doctor Changed Prescription'),
    ]
    REFUND_CHOICES = [
        ('cash', 'Cash Refund'),
        ('card', 'Card Refund'),
        ('credit', 'Store Credit'),
        ('exchange', 'Exchange'),
    ]
    DISPOSITION_CHOICES = [
        ('restock', 'Restock to Active FEFO'),
        ('quarantine', 'Quarantine'),
        ('destroy', 'Destroy'),
        ('return_supplier', 'Return to Supplier'),
    ]

    return_number = models.CharField(max_length=50, unique=True)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='returns')
    customer = models.ForeignKey(
        'customers.Customer', on_delete=models.SET_NULL,
        null=True, blank=True
    )
    reason_code = models.CharField(max_length=30, choices=REASON_CHOICES)
    reason_notes = models.TextField(blank=True)
    refund_method = models.CharField(max_length=20, choices=REFUND_CHOICES)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')],
        default='pending'
    )
    authorized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='returns_authorized'
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='returns_processed'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.return_number} — {self.sale.invoice_number}"


class ReturnItem(models.Model):
    return_ref = models.ForeignKey(Return, on_delete=models.CASCADE, related_name='items')
    sale_item = models.ForeignKey(SaleItem, on_delete=models.PROTECT)
    batch = models.ForeignKey('inventory.Batch', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    condition = models.CharField(max_length=50)
    disposition = models.CharField(max_length=30, choices=Return.DISPOSITION_CHOICES)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)