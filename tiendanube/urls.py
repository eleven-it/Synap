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
    path('restock/rules/<int:pk>/', views.TiendaNubeRestockRuleDetailView.as_view(), name='restock_rule_detail'),
    # Restock Logs
    path('restock/logs/', views.TiendaNubeRestockLogListView.as_view(), name='restock_log_list'),
    path('restock/logs/<int:pk>/', views.TiendaNubeRestockLogDetailView.as_view(), name='restock_log_detail'),
    # Product Restock Policies
    path('restock/policies/', views.TiendaNubeProductRestockPolicyListView.as_view(), name='product_restock_policy_list'),
    path('restock/policies/create/', views.TiendaNubeProductRestockPolicyCreateView.as_view(), name='product_restock_policy_create'),
    path('restock/policies/bulk-create/', views.TiendaNubeProductRestockPolicyBulkCreateView.as_view(), name='product_restock_policy_bulk_create'),
    path('restock/policies/<int:pk>/edit/', views.TiendaNubeProductRestockPolicyUpdateView.as_view(), name='product_restock_policy_update'),
    path('restock/policies/<int:pk>/delete/', views.TiendaNubeProductRestockPolicyDeleteView.as_view(), name='product_restock_policy_delete'),
    path('restock/policies/<int:pk>/', views.TiendaNubeProductRestockPolicyDetailView.as_view(), name='product_restock_policy_detail'),
    path('restock/policies/<int:pk>/execute/', views.TiendaNubeProductRestockPolicyExecuteView.as_view(), name='product_restock_policy_execute'),
    # Sync Management
    path('sync/manual/', views.TiendaNubeManualSyncView.as_view(), name='manual_sync'),
    path('sync/products/', views.TiendaNubeSyncProductsView.as_view(), name='sync_products'),
    path('sync/customers/', views.TiendaNubeSyncCustomersView.as_view(), name='sync_customers'),
    path('sync/all-stock/', views.TiendaNubeSyncAllStockView.as_view(), name='sync_all_stock'),
    # Reports
    path('reports/', views.TiendaNubeReportsView.as_view(), name='reports'),
] 