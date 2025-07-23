from django.db import models
from core.models import Empresa

class Vehicle(models.Model):
    company = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='vehicles')
    license_plate = models.CharField(max_length=20, unique=True)
    type = models.CharField(max_length=50)
    capacity_kg = models.DecimalField(max_digits=8, decimal_places=2)
    brand = models.CharField(max_length=50, blank=True, null=True)
    model = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.license_plate} - {self.type}" 