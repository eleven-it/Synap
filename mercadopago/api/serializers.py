from rest_framework import serializers
from mercadopago.models import MercadoPagoConfig, MercadoPagoDevice, MercadoPagoTransaction

class MercadoPagoConfigSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source='empresa.name', read_only=True)
    class Meta:
        model = MercadoPagoConfig
        fields = '__all__'

class MercadoPagoDeviceSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source='empresa.name', read_only=True)
    branch_nombre = serializers.CharField(source='branch.name', read_only=True)
    config_id = serializers.PrimaryKeyRelatedField(source='config', read_only=True)
    class Meta:
        model = MercadoPagoDevice
        fields = '__all__'

class MercadoPagoTransactionSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source='empresa.name', read_only=True)
    branch_nombre = serializers.CharField(source='branch.name', read_only=True)
    device_nombre = serializers.CharField(source='device.name', read_only=True)
    class Meta:
        model = MercadoPagoTransaction
        fields = '__all__' 