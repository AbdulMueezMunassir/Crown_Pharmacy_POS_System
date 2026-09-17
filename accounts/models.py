from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('pharmacist', 'Pharmacist'),
        ('salesperson', 'Salesperson'),
    ]

    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default='salesperson'
    )
    phone = models.CharField(max_length=20, blank=True)
    slmc_license = models.CharField("SLMC License #", max_length=50, blank=True)
    employee_id = models.CharField(max_length=30, unique=True, null=True, blank=True)
    is_active_staff = models.BooleanField(default=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['first_name', 'last_name']

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or self.username

    @property
    def is_admin_role(self):
        return self.role == 'admin'

    @property
    def is_pharmacist_role(self):
        return self.role in ('admin', 'pharmacist')

    def __str__(self):
        return f"{self.full_name} ({self.get_role_display()})"