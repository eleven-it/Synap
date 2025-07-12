from django.urls import path, include
from . import views

app_name = 'clover'

urlpatterns = [
    # Dashboard principal
    path('', views.clover_dashboard, name='dashboard'),
    
    # Gestión de dispositivos
    path('devices/', views.CloverDeviceListView.as_view(), name='device_list'),
    path('devices/create/', views.CloverDeviceCreateView.as_view(), name='device_create'),
    path('devices/<int:pk>/', views.CloverDeviceDetailView.as_view(), name='device_detail'),
    path('devices/<int:pk>/edit/', views.CloverDeviceUpdateView.as_view(), name='device_update'),
    path('devices/<int:pk>/delete/', views.CloverDeviceDeleteView.as_view(), name='device_delete'),
    path('devices/<int:device_id>/test-connection/', views.test_device_connection, name='test_connection'),
    
    # Gestión de transacciones
    path('transactions/', views.CloverTransactionListView.as_view(), name='transaction_list'),
    path('transactions/<int:pk>/', views.CloverTransactionDetailView.as_view(), name='transaction_detail'),
    path('transactions/<int:transaction_id>/process/', views.process_payment, name='process_payment'),
    path('transactions/<int:transaction_id>/refund/', views.refund_transaction, name='refund_transaction'),
    
    # Configuración
    path('configuration/', views.clover_configuration, name='configuration'),
    
    # APIs RESTful
    path('api/', include('clover.api.urls')),
] 