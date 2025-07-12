from rest_framework.routers import DefaultRouter
from mercadopago.api.views import (
    MercadoPagoConfigViewSet,
    MercadoPagoDeviceViewSet,
    MercadoPagoTransactionViewSet
)

router = DefaultRouter()
router.register(r'config', MercadoPagoConfigViewSet, basename='mercadopago-config')
router.register(r'device', MercadoPagoDeviceViewSet, basename='mercadopago-device')
router.register(r'transaction', MercadoPagoTransactionViewSet, basename='mercadopago-transaction')

urlpatterns = router.urls 