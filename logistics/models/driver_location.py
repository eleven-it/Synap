from django.db import models
from django.utils import timezone

class DriverLocation(models.Model):
    driver = models.OneToOneField('logistics.Driver', on_delete=models.CASCADE, related_name='last_location')
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)
    accuracy = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=32, default='smartphone')

    def __str__(self):
        return f"{self.driver} @ {self.latitude},{self.longitude} ({self.timestamp})"

class DriverLocationHistory(models.Model):
    driver = models.ForeignKey('logistics.Driver', on_delete=models.CASCADE, related_name='location_history')
    latitude = models.FloatField()
    longitude = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)
    accuracy = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=32, default='smartphone')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.driver} @ {self.latitude},{self.longitude} ({self.timestamp})" 