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
] 