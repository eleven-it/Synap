from django.urls import path

from .ventas_netas_relay_views import (
    VentasNetasGerenciaRelayAPIView,
    VentasNetasRelayAPIView,
)
from .clientes_sin_ventas_relay_views import (
    ClientesSinVentasGerenciaRelayAPIView,
    ClientesSinVentasRelayAPIView,
)
from .cobranzas_vendedor_relay_views import (
    CobranzasVendedorGerenciaRelayAPIView,
    CobranzasVendedorRelayAPIView,
)
from .utilidad_gerencial_relay_views import (
    UtilidadGerencialGerenciaRelayAPIView,
    UtilidadGerencialRelayAPIView,
)
from .logistica_lista_comprobantes_rutas_views import (
    LogisticaListaComprobantesClientesAutocompleteAPIView,
    LogisticaListaComprobantesEntregaAPIView,
    LogisticaListaComprobantesMotivosAPIView,
    LogisticaListaComprobantesRemitoDetalleAPIView,
)
from .executive_summary_api_views import (
    ExecutiveSummaryAPIView,
    PuntoVentaCanalEjecutivoAPIView,
    SucursalCanalEjecutivoAPIView,
)
from .executive_dashboard_api_views import (
    ExecutiveDashboardAPIView,
    ExecutiveDashboardVentasResumenAPIView,
    ExecutiveDashboardInventarioResumenAPIView,
    ExecutiveDashboardComprasResumenAPIView,
    ExecutiveDashboardManufacturaResumenAPIView,
    ExecutiveDashboardCruzadosResumenAPIView,
    ExecutiveDashboardVentasPedidosPendientesAPIView,
    ExecutiveDashboardVentasRemitosNoFacturadosAPIView,
    ExecutiveDashboardCruzadosBackorderAPIView,
    ExecutiveDashboardInventarioExistenciasAPIView,
    ExecutiveDashboardTesoreriaResumenAPIView,
    ExecutiveDashboardVentasCobrosResumenAPIView,
    ExecutiveDashboardTesoreriaBancoResumenAPIView,
    ExecutiveDashboardVentasCobrosDetalleAPIView,
    ExecutiveDashboardTesoreriaMovimientosCajaAPIView,
)
from .api_views import (
    ReconciliacionMovimientoDetalleAPIView,
    ReportCatalogAPIView,
    ReportQueryAPIView,
    KPIAPIView,
    ReportExportAPIView,
    WorkspaceSelectionAPIView,
    ReportFiltersAPIView,
    ReportVisibilityAPIView,
    ReportSchemaAPIView,
    ReportBuilderConfigAPIView,
    ReportBuilderPreviewAPIView,
    ReportBuilderWidgetsAPIView,
    ReportBuilderHistoryAPIView,
    ReportBuilderRollbackAPIView,
    BuilderDatasourcesAPIView,
    BuilderDatasourceFieldsAPIView,
    BuilderDatasourceRelationshipsAPIView,
    BuilderJoinsSuggestAPIView,
    BuilderJoinsCandidatesAPIView,
    BuilderRelationshipBlockAPIView,
    BuilderTemplatesAPIView,
    BuilderTemplateApplyAPIView,
    ReportExportImportAPIView,
    LearnedRelationshipsAPIView,
    SchemaMetadataAPIView,
    DataMapAPIView,
    RelationshipValidationAPIView,
    RelationshipGovernanceAPIView,
    ClusterManagementAPIView,
    ReferenceValuesAPIView,
)

app_name = "reports-api"

urlpatterns = [
    path(
        "ventas-netas/relay/",
        VentasNetasRelayAPIView.as_view(),
        name="reports-ventas-netas-relay",
    ),
    path(
        "ventas-netas/relay/gerencia/",
        VentasNetasGerenciaRelayAPIView.as_view(),
        name="reports-ventas-netas-relay-gerencia",
    ),
    path(
        "clientes-sin-ventas/relay/",
        ClientesSinVentasRelayAPIView.as_view(),
        name="reports-clientes-sin-ventas-relay",
    ),
    path(
        "clientes-sin-ventas/relay/gerencia/",
        ClientesSinVentasGerenciaRelayAPIView.as_view(),
        name="reports-clientes-sin-ventas-relay-gerencia",
    ),
    path(
        "cobranzas-vendedor/relay/",
        CobranzasVendedorRelayAPIView.as_view(),
        name="reports-cobranzas-vendedor-relay",
    ),
    path(
        "cobranzas-vendedor/relay/gerencia/",
        CobranzasVendedorGerenciaRelayAPIView.as_view(),
        name="reports-cobranzas-vendedor-relay-gerencia",
    ),
    path(
        "utilidad-gerencial/relay/",
        UtilidadGerencialRelayAPIView.as_view(),
        name="reports-utilidad-gerencial-relay",
    ),
    path(
        "utilidad-gerencial/relay/gerencia/",
        UtilidadGerencialGerenciaRelayAPIView.as_view(),
        name="reports-utilidad-gerencial-relay-gerencia",
    ),
    path(
        "logistica/lista-comprobantes-rutas/clientes/autocomplete/",
        LogisticaListaComprobantesClientesAutocompleteAPIView.as_view(),
        name="reports-logistica-lista-cr-clientes-autocomplete",
    ),
    path(
        "logistica/lista-comprobantes-rutas/remito/<int:cod_mov>/",
        LogisticaListaComprobantesRemitoDetalleAPIView.as_view(),
        name="reports-logistica-lista-cr-remito-detalle",
    ),
    path(
        "logistica/lista-comprobantes-rutas/entrega/",
        LogisticaListaComprobantesEntregaAPIView.as_view(),
        name="reports-logistica-lista-cr-entrega",
    ),
    path(
        "logistica/lista-comprobantes-rutas/motivos-no-entrega/",
        LogisticaListaComprobantesMotivosAPIView.as_view(),
        name="reports-logistica-lista-cr-motivos",
    ),
    path("reconciliacion-movimiento-detalle/", ReconciliacionMovimientoDetalleAPIView.as_view(), name="reports-reconciliacion-movimiento-detalle"),
    path("executive-summary/", ExecutiveSummaryAPIView.as_view(), name="reports-executive-summary"),
    path(
        "sucursal-canal-ejecutivo/",
        SucursalCanalEjecutivoAPIView.as_view(),
        name="reports-sucursal-canal-ejecutivo",
    ),
    path("pv-canal-ejecutivo/", PuntoVentaCanalEjecutivoAPIView.as_view(), name="reports-pv-canal-ejecutivo"),
    path("executive-dashboard/", ExecutiveDashboardAPIView.as_view(), name="reports-executive-dashboard"),
    path(
        "executive-dashboard/ventas/resumen/",
        ExecutiveDashboardVentasResumenAPIView.as_view(),
        name="reports-executive-dashboard-ventas-resumen",
    ),
    path(
        "executive-dashboard/inventario/resumen/",
        ExecutiveDashboardInventarioResumenAPIView.as_view(),
        name="reports-executive-dashboard-inventario-resumen",
    ),
    path(
        "executive-dashboard/compras/resumen/",
        ExecutiveDashboardComprasResumenAPIView.as_view(),
        name="reports-executive-dashboard-compras-resumen",
    ),
    path(
        "executive-dashboard/manufactura/resumen/",
        ExecutiveDashboardManufacturaResumenAPIView.as_view(),
        name="reports-executive-dashboard-manufactura-resumen",
    ),
    path(
        "executive-dashboard/cruzados/resumen/",
        ExecutiveDashboardCruzadosResumenAPIView.as_view(),
        name="reports-executive-dashboard-cruzados-resumen",
    ),
    path(
        "executive-dashboard/ventas/pedidos-pendientes/",
        ExecutiveDashboardVentasPedidosPendientesAPIView.as_view(),
        name="reports-executive-dashboard-ventas-pedidos-pendientes",
    ),
    path(
        "executive-dashboard/ventas/remitos-no-facturados/",
        ExecutiveDashboardVentasRemitosNoFacturadosAPIView.as_view(),
        name="reports-executive-dashboard-ventas-remitos-nf",
    ),
    path(
        "executive-dashboard/cruzados/backorder/",
        ExecutiveDashboardCruzadosBackorderAPIView.as_view(),
        name="reports-executive-dashboard-cruzados-backorder",
    ),
    path(
        "executive-dashboard/inventario/existencias/",
        ExecutiveDashboardInventarioExistenciasAPIView.as_view(),
        name="reports-executive-dashboard-inventario-existencias",
    ),
    path(
        "executive-dashboard/tesoreria/resumen/",
        ExecutiveDashboardTesoreriaResumenAPIView.as_view(),
        name="reports-executive-dashboard-tesoreria-resumen",
    ),
    path(
        "executive-dashboard/ventas/cobros/resumen/",
        ExecutiveDashboardVentasCobrosResumenAPIView.as_view(),
        name="reports-executive-dashboard-ventas-cobros-resumen",
    ),
    path(
        "executive-dashboard/tesoreria/banco/resumen/",
        ExecutiveDashboardTesoreriaBancoResumenAPIView.as_view(),
        name="reports-executive-dashboard-tesoreria-banco-resumen",
    ),
    path(
        "executive-dashboard/ventas/cobros/detalle/",
        ExecutiveDashboardVentasCobrosDetalleAPIView.as_view(),
        name="reports-executive-dashboard-ventas-cobros-detalle",
    ),
    path(
        "executive-dashboard/tesoreria/movimientos-caja/",
        ExecutiveDashboardTesoreriaMovimientosCajaAPIView.as_view(),
        name="reports-executive-dashboard-tesoreria-movimientos-caja",
    ),
    path("catalog/", ReportCatalogAPIView.as_view(), name="reports-catalog"),
    path("query/", ReportQueryAPIView.as_view(), name="reports-query"),
    path("kpi/", KPIAPIView.as_view(), name="reports-kpi"),
    path("export/", ReportExportAPIView.as_view(), name="reports-export"),
    path("workspace/", WorkspaceSelectionAPIView.as_view(), name="reports-workspace"),
    path("filters/", ReportFiltersAPIView.as_view(), name="reports-filters"),
    path("visibility/", ReportVisibilityAPIView.as_view(), name="reports-visibility"),
    path("<slug:slug>/schema/", ReportSchemaAPIView.as_view(), name="reports-schema"),
    path("<slug:slug>/builder/config/", ReportBuilderConfigAPIView.as_view(), name="reports-builder-config"),
    path("<slug:slug>/builder/preview/", ReportBuilderPreviewAPIView.as_view(), name="reports-builder-preview"),
    path("<slug:slug>/builder/widgets/", ReportBuilderWidgetsAPIView.as_view(), name="reports-builder-widgets"),
    path("<slug:slug>/builder/history/", ReportBuilderHistoryAPIView.as_view(), name="reports-builder-history"),
    path("<slug:slug>/builder/rollback/", ReportBuilderRollbackAPIView.as_view(), name="reports-builder-rollback"),
    # FASE BV-1: Semantic Datasources
    path("builder/datasources/", BuilderDatasourcesAPIView.as_view(), name="reports-builder-datasources"),
    path("builder/datasources/<str:name>/fields/", BuilderDatasourceFieldsAPIView.as_view(), name="reports-builder-datasource-fields"),
    path("builder/datasources/<str:name>/relationships/", BuilderDatasourceRelationshipsAPIView.as_view(), name="reports-builder-datasource-relationships"),
    path("builder/joins/suggest/", BuilderJoinsSuggestAPIView.as_view(), name="reports-builder-joins-suggest"),
    path("builder/joins/candidates/", BuilderJoinsCandidatesAPIView.as_view(), name="reports-builder-joins-candidates"),
    path("builder/relationships/block/", BuilderRelationshipBlockAPIView.as_view(), name="reports-builder-relationships-block"),
    # Templates
    path("builder/templates/", BuilderTemplatesAPIView.as_view(), name="reports-builder-templates"),
    path("builder/templates/<int:template_id>/apply/", BuilderTemplateApplyAPIView.as_view(), name="reports-builder-template-apply"),
    # Export/Import
    path("builder/export-import/", ReportExportImportAPIView.as_view(), name="reports-builder-export-import"),
    # Endpoints de solo lectura para exportación frontend
    path("builder/learned-relationships/", LearnedRelationshipsAPIView.as_view(), name="reports-builder-learned-relationships"),
    path("builder/schema-metadata/", SchemaMetadataAPIView.as_view(), name="reports-builder-schema-metadata"),
    path("builder/data-map/", DataMapAPIView.as_view(), name="reports-data-map"),
    # Endpoints de validación y gobernanza de relaciones
    path("builder/data-map/validate-relationship/", RelationshipValidationAPIView.as_view(), name="reports-validate-relationship"),
    path("builder/data-map/relationships/<int:relationship_id>/approve/", RelationshipGovernanceAPIView.as_view(), name="reports-relationship-approve"),
    path("builder/data-map/relationships/<int:relationship_id>/deprecate/", RelationshipGovernanceAPIView.as_view(), name="reports-relationship-deprecate"),
    path("builder/data-map/relationships/<int:relationship_id>/", RelationshipGovernanceAPIView.as_view(), name="reports-relationship-edit"),
    path("builder/data-map/clusters/", ClusterManagementAPIView.as_view(), name="reports-clusters"),
    path("builder/data-map/clusters/<str:cluster_id>/", ClusterManagementAPIView.as_view(), name="reports-cluster-detail"),
    # API para valores de referencia (filtros dinámicos)
    path("builder/reference-values/", ReferenceValuesAPIView.as_view(), name="reports-reference-values"),
]


