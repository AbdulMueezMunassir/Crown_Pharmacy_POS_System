from django.db import models


class Customer(models.Model):
    LOYALTY_TIERS = [
        ('bronze', 'Bronze'),
        ('silver', 'Silver'),
        ('gold', 'Gold'),
        ('platinum', 'Platinum'),
    ]

    patient_id = models.CharField("Patient ID", max_length=30, unique=True, blank=True)
    name = models.CharField(max_length=200)
    mobile = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    nic = models.CharField("NIC Number", max_length=20, blank=True)
    address = models.TextField(blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    allergies = models.TextField(blank=True, help_text="Comma-separated list")
    chronic_conditions = models.TextField(blank=True, help_text="Comma-separated list")
    loyalty_points = models.IntegerField(default=0)
    loyalty_tier = models.CharField(max_length=20, choices=LOYALTY_TIERS, default='bronze')
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    total_invoices = models.PositiveIntegerField(default=0)
    last_purchase_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.patient_id or self.mobile})"

    def save(self, *args, **kwargs):
        if not self.patient_id:
            # Auto-generate PAT-XXXX
            last = Customer.objects.order_by('-id').first()
            next_id = (last.id + 1) if last else 1
            self.patient_id = f"PAT-{next_id:04d}"
        super().save(*args, **kwargs)

    def update_loyalty_tier(self):
        """Call after a sale to auto-upgrade tier."""
        if self.total_spent >= 200000:
            self.loyalty_tier = 'platinum'
        elif self.total_spent >= 100000:
            self.loyalty_tier = 'gold'
        elif self.total_spent >= 50000:
            self.loyalty_tier = 'silver'
        else:
            self.loyalty_tier = 'bronze'
        self.save(update_fields=['loyalty_tier'])