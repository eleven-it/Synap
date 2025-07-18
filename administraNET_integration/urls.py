from django.urls import path, include
from .views.sync_settings import SyncSettingsView, TestConnectionView, ExportConfigView, ResetDefaultsView
from .views.panel import AdminetPanelView
from .views.status import AdminetStatusView
from .views.connection import AdminetConnectionView
from .views.mappings import AdminetMappingsView
from .views.manual_sync import AdminetManualSyncView
from .views.sync_history import AdminetSyncHistoryView
from .views.validation import AdminetValidationView
from .views.mapping_edit import AdminetMappingEditView
from .views.sync_log_detail import AdminetSyncLogDetailView
from .views.mapping_delete import AdminetMappingDeleteView
from .views.validation_settings import validation_settings
from .views.validation_history import validation_history
from .views.test_connection import TestConnectionView as ConnectionTestView, ConnectionDiagnosticView
from .views.toggle_integration import ToggleIntegrationView, IntegrationStatusView, ForceToggleView
# Importar solo vistas existentes para evitar errores de linter

app_name = 'adminet'

urlpatterns = [
    path('', AdminetPanelView.as_view(), name='adminet_panel'),
    path('status/', AdminetStatusView.as_view(), name='adminet_status'),
    path('connection/', AdminetConnectionView.as_view(), name='adminet_connection'),
    path('connection/test-connection/', AdminetConnectionView.as_view(), name='adminet_test_connection'),
    path('connection/connection-info/', AdminetConnectionView.as_view(), name='adminet_connection_info'),
    path('test-connection/', ConnectionTestView.as_view(), name='test_connection'),
    path('test-connection/diagnostic/', ConnectionDiagnosticView.as_view(), name='connection_diagnostic'),
    path('toggle-integration/', ToggleIntegrationView.as_view(), name='toggle_integration'),
    path('toggle-integration/status/', IntegrationStatusView.as_view(), name='integration_status'),
    path('toggle-integration/force/', ForceToggleView.as_view(), name='force_toggle'),
    path('mappings/', AdminetMappingsView.as_view(), name='adminet_mappings'),
    path('mappings/add/', AdminetMappingEditView.as_view(), name='adminet_mapping_add'),
    path('mappings/<int:pk>/edit/', AdminetMappingEditView.as_view(), name='adminet_mapping_edit'),
    path('mappings/<int:pk>/delete/', AdminetMappingDeleteView.as_view(), name='adminet_mapping_delete'),
    path('manual-sync/', AdminetManualSyncView.as_view(), name='adminet_manual_sync'),
    path('manual-sync/test-connection/', AdminetManualSyncView.as_view(), name='adminet_manual_test_connection'),
    path('manual-sync/sync-status/', AdminetManualSyncView.as_view(), name='adminet_manual_sync_status'),
    path('manual-sync/cancel-sync/', AdminetManualSyncView.as_view(), name='adminet_manual_cancel_sync'),
    path('sync-history/', AdminetSyncHistoryView.as_view(), name='adminet_sync_history'),
    path('sync-history/<int:pk>/', AdminetSyncLogDetailView.as_view(), name='adminet_sync_log_detail'),
    path('validation/', AdminetValidationView.as_view(), name='adminet_validation'),
    path('sync-settings/', SyncSettingsView.as_view(), name='sync_settings'),
    path('sync-settings/test-connection/', TestConnectionView.as_view(), name='sync_test_connection'),
    path('sync-settings/export-config/', ExportConfigView.as_view(), name='sync_export_config'),
    path('sync-settings/reset-defaults/', ResetDefaultsView.as_view(), name='sync_reset_defaults'),
    path('validation-settings/<int:empresa_id>/', validation_settings, name='validation_settings'),
    # Incluir URLs de la API
    path('api/', include('administraNET_integration.api.urls')),
    # Otras rutas se agregarán conforme se implementen las vistas
]

urlpatterns += [
    path('validation-history/', validation_history, name='validation_history'),
] 