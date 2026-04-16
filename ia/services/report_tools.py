from __future__ import annotations

import unicodedata
from dataclasses import asdict, dataclass

from django.core.exceptions import PermissionDenied

from reports.domain.catalog import build_catalog_for_user
from reports.models import ReportDefinition
from reports.permissions import ManagerialReportsPermission, OperationalReportsPermission
from reports.services.connection_pool import get_mysql_pool
from reports.services.query_runner import QueryRunnerService, QueryResult
from reports.services.schema_service import ReportSchemaService


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


@dataclass
class InterpretedReportQuery:
    intent: str
    report_slug: str | None
    requires_clarification: bool
    clarification_question: str | None
    filters: dict
    metadata: dict


class ReportToolsService:
    """Herramientas internas del Asistente de Reportes."""

    @staticmethod
    def get_user_context(policy_context) -> dict:
        return {
            "empresa_id": getattr(policy_context.empresa, "id", None),
            "legacy_user_id": policy_context.legacy_user_id,
            "legacy_user_code": policy_context.legacy_user_code,
            "base_empresa": policy_context.base_empresa,
            "timezone": policy_context.timezone,
            "locale": policy_context.locale,
            "permissions": sorted(policy_context.permissions),
        }

    @staticmethod
    def list_authorized_reports(policy_context) -> list:
        empresa_id = policy_context.empresa.id if policy_context.empresa else None
        return build_catalog_for_user(policy_context.user, empresa_id)

    @classmethod
    def interpret_query(cls, message_text: str, policy_context) -> InterpretedReportQuery:
        text = _normalize_text(message_text)
        filters = {}
        metadata = {}
        report_slug = None
        intent = "aggregate_summary"

        if any(term in text for term in ["compar", "contra", " versus ", " vs ", "compará", "compara"]):
            intent = "comparative_analysis"
            metadata["compare_previous_period"] = True

        if any(term in text for term in ["top ", "ranking", "mas vendidos", "mas vendidas", "más vendidos", "mejores"]):
            intent = "ranking"

        if "pedido" in text and any(term in text for term in ["pendiente", "preparado", "preparacion", "armado"]):
            report_slug = "pedidos-pendientes"
            intent = "status_query"
        elif any(term in text for term in ["stock", "existencia", "inventario", "deposito", "depósito"]):
            report_slug = "stock-existencias"
            intent = "detail_lookup" if "deposito" in text or "depósito" in text else intent
        elif any(term in text for term in ["venta neta", "ventas netas", "facturacion neta", "facturacion por sucursal"]):
            report_slug = "ventas_netas"
        elif any(term in text for term in ["ventas", "vendimos", "facturacion", "facturacion total", "facturación", "ingresos"]):
            report_slug = "sales_summary"
        elif any(term in text for term in ["remitos", "no facturados", "remitos pendientes"]):
            report_slug = "uninvoiced_remitos"

        if report_slug in {"sales_summary", "ventas_netas", "uninvoiced_remitos", "pedidos-pendientes"}:
            if not any(term in text for term in ["hoy", "ayer", "este mes", "mes pasado", "ultimos 7 dias", "últimos 7 días", "ultimos 30 dias", "últimos 30 días", "este año", "año actual", "ano actual", "trimestre actual", "este trimestre"]):
                return InterpretedReportQuery(
                    intent=intent,
                    report_slug=report_slug,
                    requires_clarification=True,
                    clarification_question="¿Sobre qué período querés hacer la consulta?",
                    filters=filters,
                    metadata=metadata,
                )

        sucursal_match = cls._match_sucursal_from_text(message_text, policy_context)
        if sucursal_match:
            filters["sucursales"] = [sucursal_match["id"]]
            metadata["sucursal_match"] = sucursal_match["label"]

        deposito_match = cls._match_deposito_from_text(message_text, policy_context)
        if deposito_match and report_slug == "stock-existencias":
            filters["depositos_incluidos"] = [deposito_match["id"]]
            metadata["deposito_match"] = deposito_match["label"]

        if not report_slug:
            return InterpretedReportQuery(
                intent=intent,
                report_slug=None,
                requires_clarification=True,
                clarification_question="Todavía no pude determinar qué reporte de Synap responde mejor esa consulta. ¿Querés consultar ventas, pedidos, remitos o stock?",
                filters=filters,
                metadata=metadata,
            )

        return InterpretedReportQuery(
            intent=intent,
            report_slug=report_slug,
            requires_clarification=False,
            clarification_question=None,
            filters=filters,
            metadata=metadata,
        )

    @staticmethod
    def get_report_definition(report_slug: str) -> ReportDefinition:
        return ReportDefinition.objects.get(slug=report_slug, is_active=True)

    @staticmethod
    def validate_report_permissions(report: ReportDefinition, request_user) -> None:
        dummy_request = type("DummyRequest", (), {"user": request_user})
        if report.is_operational() and not OperationalReportsPermission().has_permission(dummy_request, None):
            raise PermissionDenied("No tenés permisos para reportes operativos.")
        if report.is_managerial() and not ManagerialReportsPermission().has_permission(dummy_request, None):
            raise PermissionDenied("No tenés permisos para reportes gerenciales.")

    @staticmethod
    def get_report_schema(report: ReportDefinition) -> dict:
        schema = ReportSchemaService().build_schema(report)
        return {
            "slug": schema.slug,
            "name": schema.name,
            "category": schema.category,
            "is_declarative": schema.is_declarative,
            "metrics": [asdict(item) for item in schema.metrics],
            "dimensions": [asdict(item) for item in schema.dimensions],
            "options": schema.options,
        }

    @staticmethod
    def run_report_query(report: ReportDefinition, payload: dict, request_user) -> QueryResult:
        return QueryRunnerService(request_user).run(report, payload)

    @staticmethod
    def build_payload(*, report_slug: str, base_filters: dict, policy_context, date_range, limit: int = 200) -> dict:
        filters = dict(base_filters or {})
        if policy_context.base_empresa:
            filters["base_empresa"] = policy_context.base_empresa
        if date_range and date_range.start_date and date_range.end_date:
            filters["fecha_inicio"] = date_range.start_date
            filters["fecha_fin"] = date_range.end_date

        if report_slug == "stock-existencias":
            filters.setdefault("incluir_stock_cero", True)
            limit = 500

        return {
            "slug": report_slug,
            "filters": filters,
            "limit": limit,
        }

    @staticmethod
    def _match_sucursal_from_text(message_text: str, policy_context) -> dict | None:
        rows = ReportToolsService._load_named_rows(
            policy_context.base_empresa,
            sql="""
                SELECT id_sucursal, nombre_sucursal
                FROM sucursales
                WHERE anulado = 'No' OR anulado IS NULL
                ORDER BY nombre_sucursal
            """,
            row_mapper=lambda row: {"id": int(row[0]), "label": str(row[1] or "").strip()},
        )
        normalized_text = _normalize_text(message_text)
        for row in rows:
            label = _normalize_text(row["label"])
            if ReportToolsService._matches_label(normalized_text, label):
                return row
        return None

    @staticmethod
    def _match_deposito_from_text(message_text: str, policy_context) -> dict | None:
        rows = ReportToolsService._load_named_rows(
            policy_context.base_empresa,
            sql="""
                SELECT CodDeposito, NombreDeposito
                FROM deposito
                ORDER BY NombreDeposito
            """,
            row_mapper=lambda row: {"id": int(row[0]), "label": str(row[1] or "").strip()},
        )
        normalized_text = _normalize_text(message_text)
        for row in rows:
            label = _normalize_text(row["label"])
            if ReportToolsService._matches_label(normalized_text, label):
                return row
        return None

    @staticmethod
    def _load_named_rows(base_empresa: str, sql: str, row_mapper):
        if not base_empresa:
            return []
        pool = get_mysql_pool()
        try:
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute(sql)
                rows = cursor.fetchall()
                cursor.close()
            return [row_mapper(row) for row in rows]
        except Exception:
            return []

    @staticmethod
    def _matches_label(normalized_text: str, normalized_label: str) -> bool:
        if not normalized_text or not normalized_label:
            return False
        if normalized_label in normalized_text:
            return True
        label_tokens = [token for token in normalized_label.split() if len(token) >= 4]
        return any(token in normalized_text for token in label_tokens)
