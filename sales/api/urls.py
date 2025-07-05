from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet, ContactViewSet, SalesOrderViewSet, InvoiceViewSet,
    PaymentViewSet, DeliveryOrderViewSet, ReturnDeliveryViewSet,
    CreditNoteViewSet, PriceListViewSet, PaymentTermViewSet, ApprovalLogViewSet
)

# Configurar router para las vistas
router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'sales-orders', SalesOrderViewSet, basename='sales-order')
router.register(r'invoices', InvoiceViewSet, basename='invoice')
router.register(r'payments', PaymentViewSet, basename='payment')
router.register(r'delivery-orders', DeliveryOrderViewSet, basename='delivery-order')
router.register(r'return-deliveries', ReturnDeliveryViewSet, basename='return-delivery')
router.register(r'credit-notes', CreditNoteViewSet, basename='credit-note')
router.register(r'price-lists', PriceListViewSet, basename='price-list')
router.register(r'payment-terms', PaymentTermViewSet, basename='payment-term')
router.register(r'approval-logs', ApprovalLogViewSet, basename='approval-log')

# URLs de la API
urlpatterns = [
    # Incluir todas las rutas del router
    path('', include(router.urls)),
    
    # Endpoints adicionales específicos
    path('dashboard/', include([
        path('stats/', SalesOrderViewSet.as_view({'get': 'dashboard_stats'}), name='dashboard-stats'),
    ])),
    
    # Endpoints para reportes
    path('reports/', include([
        path('sales-summary/', ClientViewSet.as_view({'get': 'sales_summary'}), name='client-sales-summary'),
    ])),
]

# Agregar URLs de autenticación si es necesario
# urlpatterns += [
#     path('auth/', include('rest_framework.urls')),
# ] 