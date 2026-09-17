from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Batch(models.Model):
    """
    Represents a specific batch of a product with its own expiry date.
    FEFO (First Expiry, First Out) is enforced at dispense time.
    """
    QUALITY_STATUS = [
        ('approved', 'Approved'),
        ('quarantine', 'Quarantined'),
        ('rejected', 'Rejected'),
        ('returned', 'Returned to Supplier'),
    ]

    product = models.ForeignKey(
        'products.Product', on_delete=models.CASCADE,
        related_name='batches'
    )
    batch_number = models.CharField(max_length=100)
    supplier = models.ForeignKey(
        'suppliers.Supplier', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='batches'
    )

    quantity_received = models.PositiveIntegerField()
    quantity_available = models.PositiveIntegerField()
    quantity_reserved = models.PositiveIntegerField(default=0)

    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)

    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField()
    received_date = models.DateField(default=timezone.now)

    grn_number = models.CharField("GRN Number", max_length=50, blank=True)
    storage_location = models.CharField(max_length=100, blank=True)
    cold_chain_verified = models.BooleanField(default=False)
    quality_status = models.CharField(max_length=20, choices=QUALITY_STATUS, default='approved')

    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['expiry_date', 'created_at']
        unique_together = [('product', 'batch_number')]
        indexes = [
            models.Index(fields=['expiry_date']),
            models.Index(fields=['product', 'quantity_available']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.product.name} - {self.batch_number} (exp: {self.expiry_date})"

    @property
    def days_until_expiry(self):
        delta = self.expiry_date - timezone.now().date()
        return delta.days

    @property
    def is_expired(self):
        return self.expiry_date < timezone.now().date()

    @property
    def is_expiring_critical(self):
        """Within 30 days."""
        return 0 <= self.days_until_expiry <= 30

    @property
    def is_expiring_warning(self):
        """Within 31-90 days."""
        return 31 <= self.days_until_expiry <= 90

    @property
    def expiry_status(self):
        days = self.days_until_expiry
        if days < 0:
            return 'expired'
        if days <= 30:
            return 'critical_30'
        if days <= 90:
            return 'warning_90'
        return 'safe'

    @property
    def is_available_for_sale(self):
        """Can this batch be dispensed?"""
        return (
            self.is_active
            and not self.is_expired
            and self.quantity_available > 0
            and self.quality_status == 'approved'
        )


class GRN(models.Model):
    """Goods Received Note — a stock receiving event."""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('posted', 'Posted to Inventory'),
        ('cancelled', 'Cancelled'),
    ]

    grn_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(
        'suppliers.Supplier', on_delete=models.PROTECT,
        related_name='grns'
    )
    supplier_invoice = models.CharField(max_length=100, blank=True)
    do_number = models.CharField("Delivery Order #", max_length=100, blank=True)
    po_number = models.CharField("Purchase Order #", max_length=100, blank=True)
    inward_date = models.DateField(default=timezone.now)

    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    trade_discount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    vat_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    net_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    received_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='grns_received'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'GRN'

    def __str__(self):
        return f"{self.grn_number} — {self.supplier.name}"


class GRNItem(models.Model):
    """A single line on a GRN (one product/batch)."""
    grn = models.ForeignKey(GRN, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('products.Product', on_delete=models.PROTECT)
    batch = models.ForeignKey(
        Batch, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='grn_items'
    )
    batch_number = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()
    free_quantity = models.PositiveIntegerField(default=0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    manufacturing_date = models.DateField(null=True, blank=True)
    expiry_date = models.DateField()
    line_total = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"{self.product.name} x{self.quantity} ({self.batch_number})"

    def save(self, *args, **kwargs):
        subtotal = (self.quantity + self.free_quantity) * self.cost_price
        discount = subtotal * (self.discount_percent / 100)
        self.line_total = subtotal - discount
        super().save(*args, **kwargs)