"""
URLs de API para la integración Tiendanube-AdministraNET.
"""

from django.urls import path
from . import views

app_name = 'tiendanube_administranet_api'

urlpatterns = [
    # Configuraciones
    path('config/tiendanube/', views.TiendanubeConfigViewSet.as_view({'get': 'list', 'post': 'create'}), name='tiendanube_config_list'),
    path('config/tiendanube/<int:pk>/', views.TiendanubeConfigViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='tiendanube_config_detail'),
    path('config/adminet/', views.AdministraNETConfigViewSet.as_view({'get': 'list', 'post': 'create'}), name='adminet_config_list'),
    path('config/adminet/<int:pk>/', views.AdministraNETConfigViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='adminet_config_detail'),
    
    # Mapeos de clientes
    path('customers/', views.CustomerMappingViewSet.as_view({'get': 'list', 'post': 'create'}), name='customer_mapping_list'),
    path('customers/<int:pk>/', views.CustomerMappingViewSet.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}), name='customer_mapping_detail'),
    path('customers/<int:pk>/sync/', views.CustomerMappingViewSet.as_view({'post': 'sync'}), name='customer_mapping_sync'),
    
    # Logs de sincronización
    path('logs/', views.SyncLogViewSet.as_view({'get': 'list'}), name='sync_log_list'),
    path('logs/<int:pk>/', views.SyncLogViewSet.as_view({'get': 'retrieve'}), name='sync_log_detail'),
    
    # Estadísticas
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),
    
    # Sincronización
    path('sync/from-tiendanube/', views.SyncFromTiendanubeView.as_view(), name='sync_from_tiendanube'),
    path('sync/from-adminet/', views.SyncFromAdminetView.as_view(), name='sync_from_adminet'),
    path('sync/test-connections/', views.TestConnectionsView.as_view(), name='test_connections'),
] 