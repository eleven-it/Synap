from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Crear router para las APIs
router = DefaultRouter()

# Rutas para proveedores
router.register(r'suppliers', views.SupplierViewSet, basename='supplier')

# Rutas para solicitudes de compra
router.register(r'requests', views.PurchaseRequestViewSet, basename='purchase-request')

# Rutas para cotizaciones
router.register(r'quotations', views.PurchaseQuotationViewSet, basename='purchase-quotation')

# Rutas para órdenes de compra
router.register(r'orders', views.PurchaseOrderViewSet, basename='purchase-order')

# Rutas para recepciones
router.register(r'receipts', views.PurchaseReceiptViewSet, basename='purchase-receipt')

# Rutas para evaluaciones de proveedores
router.register(r'ratings', views.SupplierRatingViewSet, basename='supplier-rating')

# Rutas para flujos de aprobación
router.register(r'approval-workflows', views.ApprovalWorkflowViewSet, basename='approval-workflow')
router.register(r'approval-levels', views.ApprovalLevelViewSet, basename='approval-level')
router.register(r'approval-records', views.ApprovalRecordViewSet, basename='approval-record')

# URLs del módulo de compras
urlpatterns = [
    # Incluir todas las rutas del router
    path('', include(router.urls)),
    
    # Rutas adicionales específicas
    path('dashboard/', views.PurchaseDashboardView.as_view(), name='purchase-dashboard'),
    path('reports/', views.PurchaseReportsView.as_view(), name='purchase-reports'),
] 