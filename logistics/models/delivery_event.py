from django.db import models
from .delivery_stop import DeliveryStop

class DeliveryEvent(models.Model):
    stop = models.ForeignKey(DeliveryStop, on_delete=models.CASCADE, related_name='events')
    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=32, choices=[
        ('departure', 'Departure'),
        ('arrival', 'Arrival'),
        ('incident', 'Incident'),
        ('delivered', 'Delivered'),
        ('return', 'Return'),
    ])
    location = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"Event {self.event_type} at {self.timestamp}" 