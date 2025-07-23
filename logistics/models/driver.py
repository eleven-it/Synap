from django.db import models
from core.models import Empresa

class Driver(models.Model):
    company = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='drivers')
    name = models.CharField(max_length=100)
    license_number = models.CharField(max_length=50)
    phone = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name 