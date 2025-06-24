from django.urls import path
from . import views

app_name = 'inventario_api'

urlpatterns = [
    # TiendaNube API endpoints
    path('tiendanube/status/', views.tiendanube_sync_status, name='tiendanube_sync_status'),
    path('tiendanube/sync/products/', views.tiendanube_sync_products, name='tiendanube_sync_products'),
    path('tiendanube/sync/stock/', views.tiendanube_sync_stock, name='tiendanube_sync_stock'),
    path('tiendanube/products/', views.tiendanube_products, name='tiendanube_products'),
    path('tiendanube/logs/', views.tiendanube_sync_logs, name='tiendanube_sync_logs'),
    path('tiendanube/test-connection/', views.tiendanube_test_connection, name='tiendanube_test_connection'),
    path('tiendanube/create-webhook/', views.tiendanube_create_webhook, name='tiendanube_create_webhook'),
    path('tiendanube/config/', views.tiendanube_config, name='tiendanube_config'),
    path('tiendanube/config/create-from-env/', views.tiendanube_create_config_from_env, name='tiendanube_create_config_from_env'),
    path('tiendanube/webhook/', views.tiendanube_webhook_handler, name='tiendanube_webhook_handler'),
    path('tiendanube/dashboard/', views.tiendanube_dashboard_data, name='tiendanube_dashboard_data'),
] 