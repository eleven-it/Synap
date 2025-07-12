from django.urls import path
from mercadopago.views import admin as admin_views
from mercadopago.views import webhooks

app_name = 'mercadopago'

urlpatterns = [
    path('config/', admin_views.config_list, name='config_list'),
    path('config/edit/<int:pk>/', admin_views.config_edit, name='config_edit'),
    path('config/new/', admin_views.config_edit, name='config_new'),
    path('config/test/<int:pk>/', admin_views.config_test_connection, name='config_test'),

    path('device/', admin_views.device_list, name='device_list'),
    path('device/edit/<int:pk>/', admin_views.device_edit, name='device_edit'),
    path('device/new/', admin_views.device_edit, name='device_new'),
    path('device/sync/<int:pk>/', admin_views.device_sync, name='device_sync'),

    path('transaction/', admin_views.transaction_list, name='transaction_list'),
    path('transaction/<int:pk>/', admin_views.transaction_detail, name='transaction_detail'),
    
    # Webhooks
    path('webhook/', webhooks.webhook_handler, name='webhook'),
    path('smartpos-webhook/', webhooks.smartpos_webhook_handler, name='smartpos_webhook'),
] 