from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from mercadopago.models import MercadoPagoConfig, MercadoPagoDevice, MercadoPagoTransaction
from mercadopago.api.serializers import (
    MercadoPagoConfigSerializer,
    MercadoPagoDeviceSerializer,
    MercadoPagoTransactionSerializer
)
from mercadopago.services.payment_service import MercadoPagoPaymentService
from mercadopago.services.smartpos_service import MercadoPagoDeviceManager

class MercadoPagoConfigViewSet(viewsets.ModelViewSet):
    queryset = MercadoPagoConfig.objects.all()
    serializer_class = MercadoPagoConfigSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['get'])
    def test_connection(self, request, pk=None):
        config = self.get_object()
        service = MercadoPagoPaymentService(config.empresa)
        result = service.test_connection()
        return Response(result)

    @action(detail=True, methods=['get'])
    def validate(self, request, pk=None):
        config = self.get_object()
        service = MercadoPagoPaymentService(config.empresa)
        result = service.validate_configuration()
        return Response(result)

class MercadoPagoDeviceViewSet(viewsets.ModelViewSet):
    queryset = MercadoPagoDevice.objects.all()
    serializer_class = MercadoPagoDeviceSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        empresa_id = request.query_params.get('empresa')
        manager = MercadoPagoDeviceManager(empresa_id)
        summary = manager.get_device_summary()
        return Response(summary)

    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        device = self.get_object()
        from mercadopago.services.smartpos_service import MercadoPagoSmartPOSService
        service = MercadoPagoSmartPOSService(device)
        result = service.sync_device_status()
        return Response(result)

class MercadoPagoTransactionViewSet(viewsets.ModelViewSet):
    queryset = MercadoPagoTransaction.objects.all()
    serializer_class = MercadoPagoTransactionSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def summary(self, request):
        empresa_id = request.query_params.get('empresa')
        service = MercadoPagoPaymentService(empresa_id)
        summary = service.get_transaction_summary()
        return Response(summary) 