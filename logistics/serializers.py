from rest_framework import serializers
from .models import Vehicle, Driver, DeliveryRoute, DeliveryStop, DeliveryEvent

class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = '__all__'

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = Driver
        fields = '__all__'

class DeliveryRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryRoute
        fields = '__all__'

class DeliveryStopSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryStop
        fields = '__all__'

class DeliveryEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryEvent
        fields = '__all__' 