from django.db import models
from .vehicle import Vehicle
from .driver import Driver

class DeliveryRoute(models.Model):
    date = models.DateField()
    vehicle = models.ForeignKey(Vehicle, on_delete=models.PROTECT)
    driver = models.ForeignKey(Driver, on_delete=models.PROTECT)
    state = models.CharField(max_length=32, choices=[
        ('planned', 'Planned'),
        ('in_transit', 'In Transit'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], default='planned')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Route {self.id} - {self.date}" 