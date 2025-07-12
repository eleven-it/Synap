from django.urls import path
from . import views

app_name = 'clover_api'

urlpatterns = [
    # APIs para dispositivos
    path('devices/', views.CloverDeviceViewSet.as_view({'get': 'list', 'post': 'create'}), name='device-list'),
    path('devices/<int:pk>/', views.CloverDeviceViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='device-detail'),
    path('devices/<int:pk>/test-connection/', views.CloverDeviceViewSet.as_view({'post': 'test_connection'}), name='device-test-connection'),
    
    # APIs para transacciones
    path('transactions/', views.CloverTransactionViewSet.as_view({'get': 'list', 'post': 'create'}), name='transaction-list'),
    path('transactions/<int:pk>/', views.CloverTransactionViewSet.as_view({'get': 'retrieve'}), name='transaction-detail'),
    path('transactions/<int:pk>/process/', views.CloverTransactionViewSet.as_view({'post': 'process_payment'}), name='transaction-process'),
    path('transactions/<int:pk>/refund/', views.CloverTransactionViewSet.as_view({'post': 'refund'}), name='transaction-refund'),
    
    # APIs para pagos
    path('payments/', views.CloverPaymentViewSet.as_view({'post': 'create_payment'}), name='payment-create'),
    path('payments/<int:pk>/', views.CloverPaymentViewSet.as_view({'get': 'retrieve'}), name='payment-detail'),
    
    # Webhooks
    path('webhooks/', views.CloverWebhookView.as_view(), name='webhook'),
] 