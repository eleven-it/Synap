"""
URLs para la aplicación tiendanube_administranet.
"""

from django.urls import path
from . import views
from .views import mapping_configuration

app_name = 'tiendanube_administranet'

urlpatterns = [
    # Dashboard y vistas principales
    path('', views.StatusView.as_view(), name='dashboard'),
    path('test/', views.TestView.as_view(), name='test'),
    
    # Configuraciones
    path('config/tiendanube/', views.TiendanubeConfigView.as_view(), name='tiendanube_config'),
    path('config/tiendanube/list/', views.TiendanubeConfigListView.as_view(), name='tiendanube_config_list'),
    path('config/tiendanube/create/', views.TiendanubeConfigCreateView.as_view(), name='tiendanube_config_create'),
    path('config/tiendanube/<int:pk>/edit/', views.TiendanubeConfigUpdateView.as_view(), name='tiendanube_config_update'),
    path('config/tiendanube/<int:pk>/delete/', views.TiendanubeConfigDeleteView.as_view(), name='tiendanube_config_delete'),
    path('config/tiendanube/wizard/', views.TiendanubeConfigWizardView.as_view(), name='tiendanube_config_wizard'),
    path('config/tiendanube/wizard/callback/', views.TiendanubeConfigWizardCallbackView.as_view(), name='tiendanube_config_wizard_callback'),
    path('config/adminet/', views.AdministraNETConfigView.as_view(), name='adminet_config'),
    path('config/auto-sync/', views.AutoSyncConfigView.as_view(), name='auto_sync_config'),
    
    # Configuración dinámica de mapeos
    path('mappings/<str:mapping_type>/', mapping_configuration.DynamicMappingConfigurationView.as_view(), name='dynamic_mapping_config'),
    path('mappings/', mapping_configuration.FieldMappingListView.as_view(), name='field_mapping_list'),
    path('mappings/create/', mapping_configuration.FieldMappingCreateView.as_view(), name='field_mapping_create'),
    path('mappings/<int:pk>/edit/', mapping_configuration.FieldMappingUpdateView.as_view(), name='field_mapping_update'),
    path('mappings/initialize/', mapping_configuration.initialize_mappings_view, name='initialize_mappings'),
    path('mappings/refresh-cache/', mapping_configuration.refresh_mappings_cache, name='refresh_mappings_cache'),
    
    # Clientes
    path('customers/', views.CustomerMappingListView.as_view(), name='customer_mapping_list'),
    path('customers/create/', views.CustomerMappingCreateView.as_view(), name='customer_mapping_create'),
    path('customers/<int:pk>/', views.CustomerMappingDetailView.as_view(), name='customer_mapping_detail'),
    path('customers/<int:pk>/edit/', views.CustomerMappingUpdateView.as_view(), name='customer_mapping_update'),
    path('customers/<int:pk>/delete/', views.CustomerMappingDeleteView.as_view(), name='customer_mapping_delete'),
    path('customers/sync/', views.SyncCustomersView.as_view(), name='sync_customers'),
    
    # Productos
    path('products/', views.product_list, name='product_list'),
    path('products/create/', views.product_create, name='product_create'),
    path('products/<int:product_id>/', views.product_detail, name='product_detail'),
    path('products/<int:product_id>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:product_id>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:product_id>/sync/', views.product_sync, name='product_sync'),
    path('products/sync-all/', views.product_sync_all, name='product_sync_all'),
    path('products/import-from-tiendanube/', views.product_import_from_tiendanube, name='product_import_from_tiendanube'),
    
    # Variantes de productos
    path('products/<int:product_id>/variants/', views.variant_list, name='variant_list'),
    path('products/<int:product_id>/variants/create/', views.variant_create, name='variant_create'),
    path('variants/<int:variant_id>/edit/', views.variant_edit, name='variant_edit'),
    path('variants/<int:variant_id>/delete/', views.variant_delete, name='variant_delete'),
    path('variants/<int:variant_id>/sync/', views.variant_sync, name='variant_sync'),
    
    # Categorías de productos
    path('categories/', views.category_list, name='category_list'),
    path('categories/import-from-tiendanube/', views.category_import_from_tiendanube, name='category_import_from_tiendanube'),
    
    # Órdenes
    path('orders/', views.OrderMappingListView.as_view(), name='order_mapping_list'),
    path('orders/create/', views.OrderMappingCreateView.as_view(), name='order_mapping_create'),
    path('orders/<int:pk>/', views.OrderMappingDetailView.as_view(), name='order_mapping_detail'),
    path('orders/<int:pk>/edit/', views.OrderMappingUpdateView.as_view(), name='order_mapping_update'),
    path('orders/<int:pk>/delete/', views.OrderMappingDeleteView.as_view(), name='order_mapping_delete'),
    
    # Sincronización
    path('sync/manual/', views.ManualSyncView.as_view(), name='manual_sync'),
    path('sync/history/', views.SyncHistoryView.as_view(), name='sync_history'),
    path('status/', views.StatusView.as_view(), name='status'),
    
    # Logs de sincronización
    path('logs/<int:pk>/', views.SyncLogDetailView.as_view(), name='sync_log_detail'),
    
    # Webhooks
    path('webhooks/', views.WebhookConfigListView.as_view(), name='webhook_config_list'),
    path('webhooks/create/', views.WebhookConfigCreateView.as_view(), name='webhook_config_create'),
    path('webhooks/<int:pk>/', views.WebhookConfigDetailView.as_view(), name='webhook_config_detail'),
    path('webhooks/<int:pk>/edit/', views.WebhookConfigUpdateView.as_view(), name='webhook_config_update'),
    path('webhooks/<int:pk>/delete/', views.WebhookConfigDeleteView.as_view(), name='webhook_config_delete'),
    
    # Eventos de webhook
    path('webhook-events/', views.WebhookEventListView.as_view(), name='webhook_event_list'),
    path('webhook-events/<int:pk>/', views.WebhookEventDetailView.as_view(), name='webhook_event_detail'),
    path('webhook-events/<int:pk>/debug/', views.WebhookEventDebugView.as_view(), name='webhook_event_debug'),
    
    # APIs AJAX
    path('api/customers/sync-from-tiendanube/', views.sync_customers_from_tiendanube_ajax, name='sync_customers_from_tiendanube_ajax'),
    path('api/customers/sync-from-adminet/', views.sync_customers_from_adminet_ajax, name='sync_customers_from_adminet_ajax'),
    path('api/customers/<int:mapping_id>/sync/', views.sync_mapping_ajax, name='sync_mapping_ajax'),
    path('api/statistics/', views.get_statistics_ajax, name='get_statistics_ajax'),
    path('api/test-connections/', views.test_connections_ajax, name='test_connections_ajax'),
    path('api/test-adminet-connection/', views.test_adminet_connection_ajax, name='test_adminet_connection_ajax'),
    path('api/migrate-adminet-schema/', views.migrate_adminet_schema_ajax, name='migrate_adminet_schema_ajax'),
    path('api/test-tiendanube-connection/', views.test_tiendanube_connection_ajax, name='test_tiendanube_connection_ajax'),
    path('api/trigger-sync/', views.trigger_sync_ajax, name='trigger_sync_ajax'),
    path('api/sync-history/', views.get_sync_history_ajax, name='get_sync_history_ajax'),
    
    # APIs de productos
    path('api/products/', views.api_products, name='api_products'),
    path('api/products/<int:product_id>/', views.api_product_detail, name='api_product_detail'),
    path('api/products/<int:product_id>/sync/', views.api_product_sync, name='api_product_sync'),
    
    # APIs de clientes
    path('api/customers/search/', views.search_customers_ajax, name='search_customers_ajax'),
    path('api/customers/<int:customer_id>/orders/', views.get_customer_orders_ajax, name='get_customer_orders_ajax'),
    path('api/customers/validate/', views.validate_customer_data_ajax, name='validate_customer_data_ajax'),
    path('api/customers/statistics/', views.get_customer_statistics_ajax, name='get_customer_statistics_ajax'),
    path('api/customers/bulk-update/', views.bulk_update_customers_ajax, name='bulk_update_customers_ajax'),
    path('api/customers/export/', views.export_customers_ajax, name='export_customers_ajax'),
    
    # APIs de mapeos dinámicos
    path('api/mappings/<str:mapping_type>/', mapping_configuration.get_mappings_api, name='get_mappings_api'),
    
    # Webhooks
    path('api/webhooks/<int:webhook_id>/test/', views.test_webhook_ajax, name='test_webhook_ajax'),
    path('api/webhooks/<int:webhook_id>/toggle/', views.toggle_webhook_ajax, name='toggle_webhook_ajax'),
    path('api/webhooks/sync/', views.sync_webhooks_ajax, name='sync_webhooks_ajax'),
    path('api/webhook-events/<int:event_id>/retry/', views.retry_webhook_event_ajax, name='retry_webhook_event_ajax'),
    path('webhook/', views.webhook_endpoint, name='webhook_endpoint'),
    path('webhook-status/', views.webhook_status, name='webhook_status'),
    path('webhook-configure/', views.configure_webhooks, name='configure_webhooks'),
    
    # Validation URLs
    path('validation/', views.DataValidationView.as_view(), name='data_validation'),
    path('validation/validate/', views.ValidateDataAjaxView.as_view(), name='validate_data_ajax'),
    path('validation/fix/', views.FixInconsistenciesAjaxView.as_view(), name='fix_inconsistencies_ajax'),
    path('validation/sync/', views.SyncUpdatesAjaxView.as_view(), name='sync_updates_ajax'),
] 