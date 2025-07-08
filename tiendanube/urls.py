from django.urls import path
from . import views

app_name = 'tiendanube'

urlpatterns = [
    path('', views.TiendaNubeDashboardView.as_view(), name='dashboard'),
    # Config CRUD
    path('config/', views.TiendaNubeConfigListView.as_view(), name='config_list'),
    path('config/create/', views.TiendaNubeConfigCreateView.as_view(), name='config_create'),
    path('config/<int:pk>/edit/', views.TiendaNubeConfigUpdateView.as_view(), name='config_update'),
    path('config/<int:pk>/delete/', views.TiendaNubeConfigDeleteView.as_view(), name='config_delete'),
    path('config/wizard/', views.TiendaNubeConfigWizardView.as_view(), name='config_wizard'),
    path('config/wizard/callback/', views.TiendaNubeConfigWizardCallbackView.as_view(), name='config_wizard_callback'),
    # Logs
    path('logs/', views.TiendaNubeSyncLogListView.as_view(), name='logs_list'),
    path('logs/<int:pk>/', views.TiendaNubeSyncLogDetailView.as_view(), name='log_detail'),
    # Product Mapping
    path('mappings/', views.TiendaNubeProductMappingListView.as_view(), name='mapping_list'),
    path('mappings/<int:pk>/', views.TiendaNubeProductMappingDetailView.as_view(), name='mapping_detail'),
    # Customer Mapping
    path('customers/', views.TiendaNubeCustomerMappingListView.as_view(), name='customer_mapping_list'),
    path('customers/<int:pk>/', views.TiendaNubeCustomerMappingDetailView.as_view(), name='customer_mapping_detail'),
    # Order Mapping
    path('orders/', views.TiendaNubeOrderMappingListView.as_view(), name='order_mapping_list'),
    path('orders/<int:pk>/', views.TiendaNubeOrderMappingDetailView.as_view(), name='order_mapping_detail'),
    # Restock Rules
    path('restock/rules/', views.TiendaNubeRestockRuleListView.as_view(), name='restock_rule_list'),
    path('restock/rules/create/', views.TiendaNubeRestockRuleCreateView.as_view(), name='restock_rule_create'),
    path('restock/rules/<int:pk>/edit/', views.TiendaNubeRestockRuleUpdateView.as_view(), name='restock_rule_update'),
    path('restock/rules/<int:pk>/delete/', views.TiendaNubeRestockRuleDeleteView.as_view(), name='restock_rule_delete'),
    # Restock Logs
    path('restock/logs/', views.TiendaNubeRestockLogListView.as_view(), name='restock_log_list'),
    # Reports
    path('reports/', views.TiendaNubeReportsView.as_view(), name='reports'),
    # Manual Sync
    path('sync/manual/', views.TiendaNubeManualSyncView.as_view(), name='manual_sync'),
    # Webhooks
    path('webhook/', views.TiendaNubeWebhookView.as_view(), name='webhook'),
] 