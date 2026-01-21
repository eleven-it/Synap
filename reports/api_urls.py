from django.urls import path

from .api_views import (
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


