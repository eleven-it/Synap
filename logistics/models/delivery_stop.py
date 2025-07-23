from django.db import models
from .delivery_route import DeliveryRoute
from sales.models import SalesOrder

class DeliveryStop(models.Model):
    route = models.ForeignKey(DeliveryRoute, on_delete=models.CASCADE, related_name='stops')
    sales_order = models.ForeignKey(SalesOrder, on_delete=models.PROTECT)
    client = models.ForeignKey('sales.Client', on_delete=models.PROTECT)
    address = models.CharField(max_length=255)
    scheduled_time = models.DateTimeField()
    delivered_time = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=32, choices=[
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ], default='pending')
    proof_of_delivery = models.FileField(upload_to='proofs/', null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Stop {self.id} - {self.address}" 