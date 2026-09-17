from django.db import models
from django.conf import settings


class Supplier(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    ]

    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    nmra_license = models.CharField("NMRA Wholesaler License", max_length=100, blank=True)
    license_expiry = models.DateField(null=True, blank=True)
    credit_terms = models.CharField(max_length=50, blank=True, default='30 Days Credit')
    payment_terms_days = models.PositiveIntegerField(default=30)
    outstanding_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    reliability_score = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'

    def __str__(self):
        return f"{self.code} — {self.name}"

    @property
    def is_license_valid(self):
        from django.utils import timezone
        if not self.license_expiry:
            return False
        return self.license_expiry > timezone.now().date()