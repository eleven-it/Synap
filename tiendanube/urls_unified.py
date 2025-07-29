from django.urls import path
from . import views_unified

app_name = 'tiendanube_unified'

urlpatterns = [
    # Dashboard principal
    path('dashboard/', views_unified.UnifiedCustomerSyncDashboardView.as_view(), name='unified_dashboard'),
    
    # Mapeos de clientes
    path('mappings/', views_unified.UnifiedCustomerMappingListView.as_view(), name='unified_mapping_list'),
    path('mappings/create/', views_unified.UnifiedCustomerMappingCreateView.as_view(), name='unified_mapping_create'),
    path('mappings/<int:pk>/', views_unified.UnifiedCustomerMappingDetailView.as_view(), name='unified_mapping_detail'),
    path('mappings/<int:pk>/edit/', views_unified.UnifiedCustomerMappingUpdateView.as_view(), name='unified_mapping_update'),
    path('mappings/<int:pk>/delete/', views_unified.UnifiedCustomerMappingDeleteView.as_view(), name='unified_mapping_delete'),
    
    # Logs de sincronización
    path('logs/', views_unified.UnifiedSyncLogListView.as_view(), name='unified_sync_log_list'),
    
    # Endpoints AJAX para sincronización
    path('sync/from-tiendanube/', views_unified.unified_sync_customers_from_tiendanube, name='unified_sync_from_tiendanube'),
    path('sync/to-tiendanube/', views_unified.unified_sync_customers_to_tiendanube, name='unified_sync_to_tiendanube'),
    path('sync/with-adminet/', views_unified.unified_sync_customers_with_adminet, name='unified_sync_with_adminet'),
    path('sync/migrate/', views_unified.unified_migrate_from_old_systems, name='unified_migrate_from_old_systems'),
    
    # Endpoints AJAX para gestión de mapeos
    path('mappings/create-ajax/', views_unified.unified_create_mapping_ajax, name='unified_create_mapping_ajax'),
    path('mappings/delete-ajax/', views_unified.unified_delete_mapping_ajax, name='unified_delete_mapping_ajax'),
    
    # Endpoints para obtener datos
    path('adminet/customers/', views_unified.unified_get_adminet_customers, name='unified_get_adminet_customers'),
    path('tiendanube/customers/', views_unified.unified_get_tiendanube_customers, name='unified_get_tiendanube_customers'),
] 