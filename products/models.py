from django.db import models
from django.conf import settings


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    DRUG_SCHEDULE_CHOICES = [
        ('OTC', 'Over-the-Counter'),
        ('SCHEDULE_II', 'Schedule II (Controlled)'),
        ('SCHEDULE_III', 'Schedule III'),
        ('PRESCRIPTION_ONLY', 'Prescription Only'),
    ]

    UNIT_CHOICES = [
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('bottle', 'Bottle'),
        ('tube', 'Tube'),
        ('vial', 'Vial'),
        ('ampoule', 'Ampoule'),
        ('sachet', 'Sachet'),
        ('inhaler', 'Inhaler'),
        ('strip', 'Strip'),
        ('box', 'Box'),
        ('ml', 'Milliliter'),
    ]

    # Identity
    sku = models.CharField("SKU", max_length=50, unique=True)
    barcode = models.CharField(max_length=100, unique=True, null=True, blank=True)
    name = models.CharField(max_length=255)
    generic_name = models.CharField(max_length=255, blank=True)
    brand = models.CharField(max_length=150, blank=True)
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products'
    )
    drug_schedule = models.CharField(
        max_length=30, choices=DRUG_SCHEDULE_CHOICES, default='OTC'
    )
    dosage_form = models.CharField(max_length=100, blank=True)
    strength = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)

    # Pricing (all in LKR)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    mrp = models.DecimalField("Maximum Retail Price", max_digits=10, decimal_places=2, null=True, blank=True)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    # Inventory thresholds
    unit_type = models.CharField(max_length=30, choices=UNIT_CHOICES, default='tablet')
    min_stock_level = models.PositiveIntegerField(default=100)
    max_stock_level = models.PositiveIntegerField(default=1000)
    storage_location = models.CharField(max_length=100, blank=True)

    # Special handling flags
    is_cold_chain = models.BooleanField("Requires cold-chain (2-8°C)", default=False)
    is_controlled = models.BooleanField("Controlled substance", default=False)
    is_active = models.BooleanField(default=True)

    # Media & audit
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True, related_name='products_created'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['sku']),
            models.Index(fields=['barcode']),
            models.Index(fields=['name']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.sku})"

    @property
    def total_stock(self):
        """Sum of all available batch quantities."""
        return self.batches.filter(is_active=True).aggregate(
            total=models.Sum('quantity_available')
        )['total'] or 0

    @property
    def earliest_expiry(self):
        """Earliest expiry date among active batches."""
        from django.db.models import Min
        return self.batches.filter(
            is_active=True, quantity_available__gt=0
        ).aggregate(e=Min('expiry_date'))['e']

    @property
    def stock_status(self):
        """Returns in_stock / low_stock / out_of_stock."""
        total = self.total_stock
        if total == 0:
            return 'out_of_stock'
        if total <= self.min_stock_level:
            return 'low_stock'
        return 'in_stock'

    @property
    def margin_percent(self):
        """Profit margin as a percentage."""
        if self.cost_price == 0:
            return 0
        return round(((self.selling_price - self.cost_price) / self.cost_price) * 100, 2)