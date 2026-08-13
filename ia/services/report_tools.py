from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass

from django.core.exceptions import PermissionDenied

from reports.domain.catalog import build_catalog_for_user
from reports.models import ReportDefinition
from reports.permissions import ManagerialReportsPermission, OperationalReportsPermission
from reports.services.connection_pool import get_mysql_pool
from reports.services.query_runner import QueryRunnerService, QueryResult
from reports.services.schema_service import ReportSchemaService

from ia.services.date_range_service import DateRangeService
from ia.services.report_intent_refinement_service import ReportIntentHints


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


# Exclusión de cliente(s) en consultas que soportan clientes_excluidos (NOT IN).
_RE_EXCLUIR_CLIENTE_NOMBRE = re.compile(
    r"(?:no\s+inclu\w*|exclu\w*|excepto)\s+(?:a\s+|al\s+|el\s+|la\s+)?cliente\s+(?P<name>[^\.\n]+?)(?:\.|\s*$)",
    re.IGNORECASE,
)
_RE_SIN_CLIENTE = re.compile(
    r"sin\s+(?:el\s+|la\s+)?cliente\s+(?P<name>[^\.\n]+?)(?:\.|\s*$)",
    re.IGNORECASE,
)
_RE_PACK_CODE_KARDEX = re.compile(r"\b(\d{5,}-\d{2,})\b")


def _extraer_fragmento_exclusion_cliente(normalized_text: str) -> str | None:
    """Extrae el texto buscado tras «cliente» cuando el usuario pide excluir (mensaje ya normalizado)."""
    for rx in (_RE_EXCLUIR_CLIENTE_NOMBRE, _RE_SIN_CLIENTE):
        m = rx.search(normalized_text or "")
        if not m:
            continue
        name = (m.group("name") or "").strip()
        name = re.split(r"\s+(?:entre|desde|pero)\s+", name, maxsplit=1)[0].strip()
        if len(name) >= 2:
            return name
    return None


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

    _SPANISH_MONTH_IN_QUERY = re.compile(
        r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)",
        re.IGNORECASE,
    )

    GREETING_TERMS = {
        "hola",
        "buenas",
        "buen dia",
        "buen día",
        "buenas tardes",
        "buenas noches",
        "hello",
        "hi",
    }
    REPORT_SLUG_ALIASES = {
        "sales_summary": [
            "sales_summary",
            "total-consolidado-operativo",
            "resumen-ejecutivo-ventas",
        ],
        "ventas_netas": [
            "ventas_netas",
            "ventas-netas",
        ],
        "uninvoiced_remitos": [
            "uninvoiced_remitos",
            "remitos-no-facturados",
        ],
        "pedidos-pendientes": [
            "pedidos-pendientes",
        ],
        "comprobantes-rutas": [
            "comprobantes-rutas",
            "mayoristapp-lista-comprobantes-rutas",
        ],
        "mpr-pedidos-estado": [
            "mpr-pedidos-estado",
        ],
        "stock-existencias": [
            "stock-existencias",
        ],
        "mpr-kardex-articulo": [
            "mpr-kardex-articulo",
        ],
    }

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
    def resolve_actual_report_slug(cls, canonical_slug: str | None, policy_context) -> str | None:
        if not canonical_slug:
            return None
        candidates = cls.REPORT_SLUG_ALIASES.get(canonical_slug, [canonical_slug])
        authorized_catalog = cls.list_authorized_reports(policy_context)
        authorized_slugs = {entry.slug for entry in authorized_catalog}

        for candidate in candidates:
            if candidate in authorized_slugs:
                return candidate

        existing_slugs = set(
            ReportDefinition.objects.filter(slug__in=candidates, is_active=True).values_list("slug", flat=True)
        )
        for candidate in candidates:
            if candidate in existing_slugs:
                return candidate
        return None

    @classmethod
    def interpret_query(cls, message_text: str, policy_context, *, conversation_snippet: str | None = None) -> InterpretedReportQuery:
        text_current = _normalize_text(message_text)
        canon = (
            _normalize_text(f"{conversation_snippet}\n{message_text}") if conversation_snippet else text_current
        )
        text = canon
        filters = {}
        metadata = {}
        report_slug = None
        intent = "aggregate_summary"

        if cls._is_greeting_or_general_chat(text_current):
            return InterpretedReportQuery(
                intent="general_chat",
                report_slug=None,
                requires_clarification=False,
                clarification_question=None,
                filters={},
                metadata={"general_chat": True},
            )

        if any(term in text for term in ["compar", "contra", " versus ", " vs ", "compará", "compara"]):
            intent = "comparative_analysis"
            metadata["compare_previous_period"] = True

        if any(term in text for term in ["top ", "ranking", "mas vendidos", "mas vendidas", "más vendidos", "mejores"]):
            intent = "ranking"

        monthly_sales_hint = any(
            term in text
            for term in (
                "mensual",
                "mensuales",
                "mes a mes",
                "por mes",
                "cada mes",
                "desglose por mes",
                "evolucion mensual",
                "evolución mensual",
            )
        )
        sales_terms = (
            "venta",
            "ventas",
            "vendimos",
            "facturacion",
            "facturacion total",
            "facturación",
            "ingresos",
        )

        invoice_count_qty = any(
            term in text
            for term in (
                "cantidad",
                "cuantas",
                "cuántas",
                "cuantos",
                "cuántos",
                "numero",
                "número",
                "cual es",
                "cuál es",
                "cuanto es",
                "cuánto es",
            )
        )
        # No usar «comprobante» suelto: en Python "comprobante" in "comprobantes" es True y mezclaba
        # «comprobantes x mes» con conteo de facturas en lugar de importes de ventas.
        invoice_count_fact = (
            "factura" in text
            or "facturas" in text
            or ("emit" in text and "comprob" in text)
        )

        qty_terms_match_current = any(
            term in text_current
            for term in (
                "cantidad",
                "cuantas",
                "cuántas",
                "cuantos",
                "cuántos",
                "numero",
                "número",
                "cual es",
                "cuál es",
                "cuanto es",
                "cuánto es",
            )
        )
        has_factura_qty_in_current = (
            ("factura" in text_current or "facturas" in text_current) and qty_terms_match_current
        )

        # Logística / entregas: usar solo el mensaje actual para no mezclar con «ventas» del transcript previo.
        if "logistica" in text_current and any(
            term in text_current
            for term in (
                "entrega",
                "entregas",
                "reparto",
                "ruta",
                "rutas",
                "transporte",
                "chofer",
                "choferes",
                "remito",
                "remitos",
                "pendiente",
                "pendientes",
                "sin entregar",
                "no entregado",
                "no entregados",
            )
        ):
            report_slug = "comprobantes-rutas"
            intent = "status_query"
            metadata["logistica_lista_comprobantes_rutas"] = True
            if any(
                term in text_current
                for term in (
                    "pendiente",
                    "pendientes",
                    "sin entregar",
                    "no entregado",
                    "no entregados",
                    "falta entregar",
                )
            ):
                filters["logistica_estado_entrega"] = "No"
                metadata["logistica_solo_no_entregados"] = True
        # MPR: resumen por estado OPT (no confundir con PED en depósito `pedidos-pendientes`).
        elif "mpr" in text_current and any(
            term in text_current
            for term in (
                "pedido",
                "pedidos",
                "pendiente",
                "pendientes",
                "produccion",
                "fabrica",
                "opt",
            )
        ):
            report_slug = "mpr-pedidos-estado"
            intent = "status_query"
            metadata["mpr_pedidos_por_estado"] = True
        elif cls._is_kardex_articulo_query(text_current):
            report_slug = "mpr-kardex-articulo"
            intent = "detail_lookup"
            metadata["mpr_kardex_articulo"] = True
            codigo_pack = cls._extract_codigo_articulo_kardex(text_current)
            if codigo_pack:
                filters["codigo_articulo"] = codigo_pack
            if "semi" in text_current:
                metadata["deposito_hint_semi"] = True
                filters["deposito_hint_semi"] = True
        elif (
            "pedido" in text_current
            and any(term in text_current for term in ["pendiente", "preparado", "preparacion", "armado"])
            and "mpr" not in text_current
        ):
            report_slug = "pedidos-pendientes"
            intent = "status_query"
        elif (
            (
                ("comprobante" in text or "comprobantes" in text)
                and (
                    "tipo de comprobante" in text
                    or "tipos de comprobante" in text
                    or "por tipo" in text
                    or "total por tipo" in text
                    or "cada uno" in text
                    or "cantidad de cada" in text
                    or ("desglose" in text and "comprobante" in text)
                )
            )
            or ("total por tipo" in text and ("comprobante" in text or "comprobantes" in text))
        ) and not has_factura_qty_in_current:
            report_slug = "ventas_netas"
            metadata["ventas_por_tipo_comprobante"] = True
            metadata.pop("compare_previous_period", None)
            intent = "ranking"
        elif any(term in text_current for term in ["stock", "existencia", "inventario", "deposito", "depósito"]):
            report_slug = "stock-existencias"
            intent = "detail_lookup" if "deposito" in text_current or "depósito" in text_current else intent
        elif (
            any(term in text for term in sales_terms)
            and (
                monthly_sales_hint
                or any(
                    p in text
                    for p in (
                        "mes x mes",
                        "mes por mes",
                        "comprobantes x mes",
                        "comprobante x mes",
                    )
                )
            )
            and any(
                p in text
                for p in (
                    "total de ventas",
                    "total ventas",
                    "venta total",
                    "importe",
                    "importes",
                    "monto",
                    "montos",
                    "pesos",
                )
            )
        ):
            report_slug = "ventas_netas"
            metadata["ventas_netas_monthly_company_totals"] = True
            metadata.pop("compare_previous_period", None)
            if intent == "aggregate_summary":
                intent = "ranking"
        elif invoice_count_fact and invoice_count_qty:
            report_slug = "ventas_netas"
            metadata["invoice_count_fa_fm"] = True
            _mes_x_mes_frases = (
                "mes x mes",
                "mes por mes",
                "mes a mes",
                "cada mes",
                "mensualmente",
                "desglose mensual",
                "comprobantes x mes",
                "comprobante x mes",
                "comprobantes por mes",
            )
            quiere_mensual = any(p in text for p in _mes_x_mes_frases) or (
                ("listado" in text_current or "detalle" in text_current)
                and ("mes" in text_current or "meses" in text_current)
            )
            tiene_pv = (
                "punto de venta" in text_current
                or "punto de ventas" in text_current
                or ("punto" in text_current and "venta" in text_current)
            )
            if tiene_pv:
                metadata["invoice_count_by_punto_venta"] = True
                if quiere_mensual:
                    metadata["invoice_count_by_punto_venta_mensual"] = True
            elif quiere_mensual:
                metadata["invoice_count_fa_fm_mensual"] = True
            metadata.pop("compare_previous_period", None)
            intent = "status_query"
        elif monthly_sales_hint and any(term in text for term in sales_terms):
            report_slug = "ventas_netas"
            metadata["ventas_netas_monthly_company_totals"] = True
            metadata.pop("compare_previous_period", None)
            if intent == "aggregate_summary":
                intent = "ranking"
        elif any(term in text for term in ["venta neta", "ventas netas", "facturacion neta", "facturacion por sucursal"]):
            report_slug = "ventas_netas"
        elif any(term in text_current for term in ["ventas", "vendimos", "facturacion", "facturacion total", "facturación", "ingresos"]):
            report_slug = "sales_summary"
        elif any(term in text for term in ["remitos", "no facturados", "remitos pendientes"]):
            report_slug = "uninvoiced_remitos"

        if report_slug in {"sales_summary", "ventas_netas", "uninvoiced_remitos", "pedidos-pendientes"} and not metadata.get(
            "invoice_count_fa_fm"
        ) and not metadata.get("ventas_por_tipo_comprobante"):
            period_terms = [
                "hoy",
                "ayer",
                "este mes",
                "mes pasado",
                "ultimos 7 dias",
                "últimos 7 días",
                "ultimos 30 dias",
                "últimos 30 días",
                "este año",
                "año actual",
                "ano actual",
                "trimestre actual",
                "este trimestre",
                "desde",
                "entre",
                "hasta hoy",
            ]
            has_period = (
                any(term in text for term in period_terms)
                or bool(cls._SPANISH_MONTH_IN_QUERY.search(text))
                or DateRangeService.try_parse_explicit_range(text) is not None
            )
            if not has_period:
                return InterpretedReportQuery(
                    intent=intent,
                    report_slug=report_slug,
                    requires_clarification=True,
                    clarification_question="¿Sobre qué período querés hacer la consulta?",
                    filters=filters,
                    metadata=metadata,
                )

        sucursal_match = cls._match_sucursal_from_text(text, policy_context)
        if sucursal_match:
            filters["sucursales"] = [sucursal_match["id"]]
            metadata["sucursal_match"] = sucursal_match["label"]

        if metadata.get("invoice_count_fa_fm") and "sucursal" in text and not filters.get("sucursales"):
            return InterpretedReportQuery(
                intent=intent,
                report_slug=None,
                requires_clarification=True,
                clarification_question=(
                    "No encontré esa sucursal en el listado de Synap. "
                    "Verificá el nombre exacto o consultá sin filtrar por sucursal."
                ),
                filters=filters,
                metadata=metadata,
            )

        deposito_match = cls._match_deposito_from_text(text, policy_context)
        if deposito_match and report_slug == "stock-existencias":
            filters["depositos_incluidos"] = [deposito_match["id"]]
            metadata["deposito_match"] = deposito_match["label"]
        elif deposito_match and report_slug == "mpr-kardex-articulo":
            filters["id_deposito"] = deposito_match["id"]
            metadata["deposito_match"] = deposito_match["label"]

        if report_slug in (
            "ventas_netas",
            "sales_summary",
            "uninvoiced_remitos",
            "pedidos-pendientes",
        ):
            cx = cls._resolve_clientes_excluidos_desde_texto(text, policy_context)
            if cx["action"] == "ambiguous":
                return InterpretedReportQuery(
                    intent=intent,
                    report_slug=report_slug,
                    requires_clarification=True,
                    clarification_question=cx["question"],
                    filters=filters,
                    metadata=metadata,
                )
            if cx["action"] == "not_found":
                return InterpretedReportQuery(
                    intent=intent,
                    report_slug=report_slug,
                    requires_clarification=True,
                    clarification_question=cx["question"],
                    filters=filters,
                    metadata=metadata,
                )
            if cx["action"] == "apply":
                filters["clientes_excluidos"] = cx["codigos"]
                metadata["clientes_excluidos_etiquetas"] = cx["labels"]

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

    _CONF_MIN_INTENT_HINT = 0.35
    _SALES_SLUGS = frozenset({"ventas_netas", "sales_summary"})

    @classmethod
    def _interpretacion_afectada_por_hints(cls, interpreted: InterpretedReportQuery) -> bool:
        if interpreted.report_slug in cls._SALES_SLUGS:
            return True
        md = interpreted.metadata or {}
        return bool(
            md.get("invoice_count_fa_fm")
            or md.get("invoice_count_fa_fm_mensual")
            or md.get("invoice_count_by_punto_venta")
            or md.get("invoice_count_by_punto_venta_mensual")
            or md.get("ventas_netas_monthly_company_totals")
            or md.get("ventas_por_tipo_comprobante")
        )

    @classmethod
    def apply_llm_intent_hints(
        cls,
        interpreted: InterpretedReportQuery,
        hints: ReportIntentHints,
    ) -> InterpretedReportQuery:
        """
        Ajusta metadata/report_slug tras el refinamiento LLM, sin sustituir la heurística completa.
        Solo aplica si la confianza supera el umbral y la consulta está en el ámbito ventas/facturas.
        """
        if interpreted.requires_clarification or interpreted.metadata.get("general_chat"):
            return interpreted
        if hints.confianza < cls._CONF_MIN_INTENT_HINT:
            return interpreted
        if not cls._interpretacion_afectada_por_hints(interpreted):
            return interpreted

        md = dict(interpreted.metadata or {})
        slug = interpreted.report_slug
        intent = interpreted.intent

        def _limpiar_rutas_conteo() -> None:
            for k in (
                "invoice_count_fa_fm",
                "invoice_count_fa_fm_mensual",
                "invoice_count_by_punto_venta",
                "invoice_count_by_punto_venta_mensual",
            ):
                md.pop(k, None)

        def _limpiar_importes_mensuales_negocio() -> None:
            md.pop("ventas_netas_monthly_company_totals", None)

        if hints.metrica == "importes_ventas":
            _limpiar_rutas_conteo()
            md.pop("ventas_por_tipo_comprobante", None)
            if hints.desglose_mensual:
                md["ventas_netas_monthly_company_totals"] = True
                md.pop("compare_previous_period", None)
                slug = "ventas_netas"
                if intent == "aggregate_summary":
                    intent = "ranking"
            else:
                _limpiar_importes_mensuales_negocio()
                if slug in (None, "ventas_netas"):
                    slug = "ventas_netas"
        elif hints.metrica == "cantidad_facturas":
            _limpiar_importes_mensuales_negocio()
            md.pop("ventas_por_tipo_comprobante", None)
            md["invoice_count_fa_fm"] = True
            if hints.desglose_mensual:
                if hints.desglose_por_punto_venta:
                    md["invoice_count_by_punto_venta"] = True
                    md["invoice_count_by_punto_venta_mensual"] = True
                else:
                    md["invoice_count_fa_fm_mensual"] = True
            elif hints.desglose_por_punto_venta:
                md["invoice_count_by_punto_venta"] = True
            intent = "status_query"
            if slug in (None, "sales_summary"):
                slug = "ventas_netas"

        return InterpretedReportQuery(
            intent=intent,
            report_slug=slug,
            requires_clarification=interpreted.requires_clarification,
            clarification_question=interpreted.clarification_question,
            filters=dict(interpreted.filters),
            metadata=md,
        )

    @classmethod
    def _is_greeting_or_general_chat(cls, normalized_text: str) -> bool:
        normalized_text = (normalized_text or "").strip()
        if not normalized_text:
            return False
        if normalized_text in cls.GREETING_TERMS:
            return True
        if len(normalized_text.split()) <= 3 and any(term in normalized_text for term in cls.GREETING_TERMS):
            return True
        return normalized_text in {
            "como estas",
            "como andas",
            "quien sos",
            "que podes hacer",
            "que puedes hacer",
        }

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
    def count_facturas_emitidas_fa_fm(
        *,
        base_empresa: str,
        fecha_inicio: str,
        fecha_fin: str,
        sucursal_ids: list[int] | None = None,
    ) -> tuple[int | None, str | None]:
        """
        Cuenta comprobantes de facturación (FA–FM) por movimiento distinto, alineado a criterios del reporte ventas netas
        (cuentacliente, Anulado='No', CodigoMovimiento<>0).
        """
        if not base_empresa:
            return None, "No se pudo determinar la base de empresa para la consulta."
        where_parts = [
            "cc.Fecha >= %s",
            "cc.Fecha <= %s",
            "cc.Anulado = 'No'",
            "cc.CodigoMovimiento <> 0",
            "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')",
        ]
        params: list = [fecha_inicio, fecha_fin]
        if sucursal_ids:
            placeholders = ",".join(["%s"] * len(sucursal_ids))
            where_parts.append(f"cc.CodSucursal IN ({placeholders})")
            params.extend(sucursal_ids)
        where_clause = " AND ".join(where_parts)
        sql = f"SELECT COUNT(DISTINCT cc.CodigoMovimiento) AS cnt FROM cuentacliente cc WHERE {where_clause}"
        pool = get_mysql_pool()
        try:
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                row = cursor.fetchone()
                cursor.close()
            if not row or row[0] is None:
                return 0, None
            return int(row[0]), None
        except Exception as exc:  # noqa: BLE001
            return None, f"No se pudo ejecutar el conteo en la base operativa: {exc}"

    @staticmethod
    def count_facturas_emitidas_fa_fm_by_punto_venta(
        *,
        base_empresa: str,
        fecha_inicio: str,
        fecha_fin: str,
        sucursal_ids: list[int] | None = None,
    ) -> tuple[list[dict] | None, str | None]:
        """
        Cantidad de facturas FA–FM por movimiento distinto, por punto de venta y tipo de letra (FA…FM).
        """
        if not base_empresa:
            return None, "No se pudo determinar la base de empresa para la consulta."
        where_parts = [
            "cc.Fecha >= %s",
            "cc.Fecha <= %s",
            "cc.Anulado = 'No'",
            "cc.CodigoMovimiento <> 0",
            "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')",
        ]
        params: list = [fecha_inicio, fecha_fin]
        if sucursal_ids:
            placeholders = ",".join(["%s"] * len(sucursal_ids))
            where_parts.append(f"cc.CodSucursal IN ({placeholders})")
            params.extend(sucursal_ids)
        where_clause = " AND ".join(where_parts)
        sql = f"""
            SELECT
                cc.id_pv AS id_punto_venta,
                MAX(pv.nro_punto_venta) AS nro_punto_venta,
                cc.TipoComprobante AS tipo_comprobante,
                COUNT(DISTINCT cc.CodigoMovimiento) AS cantidad
            FROM cuentacliente cc
            LEFT JOIN punto_venta pv ON pv.id_punto_venta = cc.id_pv
            WHERE {where_clause}
            GROUP BY cc.id_pv, cc.TipoComprobante
            HAVING COUNT(DISTINCT cc.CodigoMovimiento) > 0
            ORDER BY COALESCE(cc.id_pv, -1) ASC, cc.TipoComprobante ASC
        """
        pool = get_mysql_pool()
        try:
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows_raw = cursor.fetchall()
                cols = [d[0] for d in cursor.description] if cursor.description else []
                cursor.close()
            out: list[dict] = []
            for row in rows_raw:
                d = dict(zip(cols, row))
                d["cantidad"] = int(d.get("cantidad") or 0)
                tc = d.get("tipo_comprobante")
                d["tipo_comprobante"] = (str(tc).strip() if tc is not None else "")
                out.append(d)
            return out, None
        except Exception as exc:  # noqa: BLE001
            return None, f"No se pudo ejecutar el conteo por punto de venta en la base operativa: {exc}"

    @staticmethod
    def count_facturas_emitidas_fa_fm_by_punto_venta_mensual(
        *,
        base_empresa: str,
        fecha_inicio: str,
        fecha_fin: str,
        sucursal_ids: list[int] | None = None,
    ) -> tuple[list[dict] | None, str | None]:
        """
        Igual que por punto de venta y letra, con una fila por mes calendario (YYYY-MM) según cc.Fecha.
        """
        if not base_empresa:
            return None, "No se pudo determinar la base de empresa para la consulta."
        where_parts = [
            "cc.Fecha >= %s",
            "cc.Fecha <= %s",
            "cc.Anulado = 'No'",
            "cc.CodigoMovimiento <> 0",
            "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')",
        ]
        params: list = [fecha_inicio, fecha_fin]
        if sucursal_ids:
            placeholders = ",".join(["%s"] * len(sucursal_ids))
            where_parts.append(f"cc.CodSucursal IN ({placeholders})")
            params.extend(sucursal_ids)
        where_clause = " AND ".join(where_parts)
        # En f-string, los % de DATE_FORMAT de MySQL deben ir como %% para no chocar con el formateo de Python.
        sql = f"""
            SELECT
                DATE_FORMAT(cc.Fecha, '%%Y-%%m') AS anio_mes,
                cc.id_pv AS id_punto_venta,
                MAX(pv.nro_punto_venta) AS nro_punto_venta,
                cc.TipoComprobante AS tipo_comprobante,
                COUNT(DISTINCT cc.CodigoMovimiento) AS cantidad
            FROM cuentacliente cc
            LEFT JOIN punto_venta pv ON pv.id_punto_venta = cc.id_pv
            WHERE {where_clause}
            GROUP BY DATE_FORMAT(cc.Fecha, '%%Y-%%m'), cc.id_pv, cc.TipoComprobante
            HAVING COUNT(DISTINCT cc.CodigoMovimiento) > 0
            ORDER BY anio_mes ASC, COALESCE(cc.id_pv, -1) ASC, cc.TipoComprobante ASC
        """
        pool = get_mysql_pool()
        try:
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows_raw = cursor.fetchall()
                cols = [d[0] for d in cursor.description] if cursor.description else []
                cursor.close()
            out: list[dict] = []
            for row in rows_raw:
                d = dict(zip(cols, row))
                d["cantidad"] = int(d.get("cantidad") or 0)
                tc = d.get("tipo_comprobante")
                d["tipo_comprobante"] = (str(tc).strip() if tc is not None else "")
                am = d.get("anio_mes")
                if hasattr(am, "strftime"):
                    d["anio_mes"] = am.strftime("%Y-%m")
                else:
                    d["anio_mes"] = str(am)[:7] if am else ""
                out.append(d)
            return out, None
        except Exception as exc:  # noqa: BLE001
            return None, f"No se pudo ejecutar el conteo mensual por punto de venta: {exc}"

    @staticmethod
    def count_facturas_emitidas_fa_fm_por_mes_y_tipo(
        *,
        base_empresa: str,
        fecha_inicio: str,
        fecha_fin: str,
        sucursal_ids: list[int] | None = None,
    ) -> tuple[list[dict] | None, str | None]:
        """
        Facturas FA–FM por mes calendario y tipo de letra (sin agrupar por punto de venta).
        """
        if not base_empresa:
            return None, "No se pudo determinar la base de empresa para la consulta."
        where_parts = [
            "cc.Fecha >= %s",
            "cc.Fecha <= %s",
            "cc.Anulado = 'No'",
            "cc.CodigoMovimiento <> 0",
            "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')",
        ]
        params: list = [fecha_inicio, fecha_fin]
        if sucursal_ids:
            placeholders = ",".join(["%s"] * len(sucursal_ids))
            where_parts.append(f"cc.CodSucursal IN ({placeholders})")
            params.extend(sucursal_ids)
        where_clause = " AND ".join(where_parts)
        sql = f"""
            SELECT
                DATE_FORMAT(cc.Fecha, '%%Y-%%m') AS anio_mes,
                cc.TipoComprobante AS tipo_comprobante,
                COUNT(DISTINCT cc.CodigoMovimiento) AS cantidad
            FROM cuentacliente cc
            WHERE {where_clause}
            GROUP BY DATE_FORMAT(cc.Fecha, '%%Y-%%m'), cc.TipoComprobante
            HAVING COUNT(DISTINCT cc.CodigoMovimiento) > 0
            ORDER BY anio_mes ASC, cc.TipoComprobante ASC
        """
        pool = get_mysql_pool()
        try:
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows_raw = cursor.fetchall()
                cols = [d[0] for d in cursor.description] if cursor.description else []
                cursor.close()
            out: list[dict] = []
            for row in rows_raw:
                d = dict(zip(cols, row))
                d["cantidad"] = int(d.get("cantidad") or 0)
                tc = d.get("tipo_comprobante")
                d["tipo_comprobante"] = (str(tc).strip() if tc is not None else "")
                am = d.get("anio_mes")
                if hasattr(am, "strftime"):
                    d["anio_mes"] = am.strftime("%Y-%m")
                else:
                    d["anio_mes"] = str(am)[:7] if am else ""
                out.append(d)
            return out, None
        except Exception as exc:  # noqa: BLE001
            return None, f"No se pudo ejecutar el conteo mensual por tipo de factura: {exc}"

    @staticmethod
    def aggregate_movimientos_por_tipo_comprobante(
        *,
        base_empresa: str,
        fecha_inicio: str,
        fecha_fin: str,
        sucursal_ids: list[int] | None = None,
    ) -> tuple[list[dict] | None, str | None]:
        """
        Desglose por letra de factura de venta FA–FM en cuentacliente (mismos filtros base que conteos FA–FM).
        No incluye recibos (REC), ajustes (AJ), notas de crédito (NCA…), ni otros tipos.
        Orden: mayor cantidad de comprobantes distintos primero.
        """
        if not base_empresa:
            return None, "No se pudo determinar la base de empresa para la consulta."
        where_parts = [
            "cc.Fecha >= %s",
            "cc.Fecha <= %s",
            "cc.Anulado = 'No'",
            "cc.CodigoMovimiento <> 0",
            # Misma familia que conteos FA–FM y reporte ventas netas (no REC, AJ, NC*, etc.).
            "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')",
        ]
        params: list = [fecha_inicio, fecha_fin]
        if sucursal_ids:
            placeholders = ",".join(["%s"] * len(sucursal_ids))
            where_parts.append(f"cc.CodSucursal IN ({placeholders})")
            params.extend(sucursal_ids)
        where_clause = " AND ".join(where_parts)
        sql = f"""
            SELECT cc.TipoComprobante AS tipo_comprobante,
                   COUNT(DISTINCT cc.CodigoMovimiento) AS cantidad,
                   SUM(COALESCE(cc.SubtotalDesc, 0)) AS total_subtotal
            FROM cuentacliente cc
            WHERE {where_clause}
            GROUP BY cc.TipoComprobante
            ORDER BY cantidad DESC, cc.TipoComprobante ASC
        """
        pool = get_mysql_pool()
        try:
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows_raw = cursor.fetchall()
                cols = [d[0] for d in cursor.description] if cursor.description else []
                cursor.close()
            out = []
            for row in rows_raw:
                d = dict(zip(cols, row))
                d["cantidad"] = int(d.get("cantidad") or 0)
                d["total_subtotal"] = float(d.get("total_subtotal") or 0)
                out.append(d)
            return out, None
        except Exception as exc:  # noqa: BLE001
            return None, f"No se pudo ejecutar el desglose en la base operativa: {exc}"

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

    @classmethod
    def _resolve_clientes_excluidos_desde_texto(cls, normalized_text: str, policy_context) -> dict:
        """
        Si el usuario pide excluir un cliente por nombre, busca en `cliente`.
        - 0 coincidencias: aclaración.
        - 1: aplica clientes_excluidos.
        - >1: lista numerada para que el usuario elija (misma vuelta, requires_clarification).
        """
        frag = _extraer_fragmento_exclusion_cliente(normalized_text)
        if not frag:
            return {"action": "skip"}
        base = getattr(policy_context, "base_empresa", None) or ""
        if not base:
            return {"action": "skip"}
        matches = cls._buscar_clientes_por_nombre_fragmento(base, frag)
        if not matches:
            return {
                "action": "not_found",
                "question": (
                    f"No encontré ningún cliente que coincida con «{frag}». "
                    "Verificá la escritura o probá con más letras del nombre o razón social."
                ),
            }
        if len(matches) == 1:
            m0 = matches[0]
            return {"action": "apply", "codigos": [m0["id"]], "labels": [m0["label"]]}
        lines = [
            f"Hay más de un cliente que coincide con «{frag}». "
            "Indicá cuál querés excluir respondiendo con el número de la lista o el nombre exacto:",
            "",
        ]
        for i, row in enumerate(matches[:15], 1):
            lines.append(f"{i}. {row['label']} (código {row['id']}).")
        if len(matches) > 15:
            lines.append(f"… y {len(matches) - 15} más. Afiná la búsqueda con un texto más específico.")
        return {"action": "ambiguous", "question": "\n".join(lines)}

    @staticmethod
    def _buscar_clientes_por_nombre_fragmento(base_empresa: str, fragment: str) -> list[dict]:
        frag = _normalize_text(fragment)
        if len(frag) < 2:
            return []
        pool = get_mysql_pool()
        like = f"%{frag}%"
        sql = """
            SELECT Codigo, nombre_cliente
            FROM cliente
            WHERE LOWER(COALESCE(nombre_cliente, '')) LIKE %s
            ORDER BY nombre_cliente
            LIMIT 40
        """
        try:
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                cursor.execute(sql, (like,))
                rows = cursor.fetchall()
                cursor.close()
        except Exception:
            return []
        out: list[dict] = []
        for row in rows:
            cod, nom = row[0], row[1]
            label = str(nom or "").strip() or f"Cliente {cod}"
            out.append({"id": cod, "label": label})
        return out

    @staticmethod
    def _is_kardex_articulo_query(normalized_text: str) -> bool:
        if not normalized_text:
            return False
        if "kardex" in normalized_text:
            return True
        if "saldo semi" in normalized_text or (
            "saldo" in normalized_text and "semi" in normalized_text
        ):
            return True
        if "trazabilidad" in normalized_text and any(
            t in normalized_text for t in ("articulo", "artículo", "pack")
        ):
            return True
        if any(
            t in normalized_text
            for t in (
                "trazabilidad articulo",
                "trazabilidad del articulo",
                "trazabilidad del artículo",
            )
        ):
            return True
        if _RE_PACK_CODE_KARDEX.search(normalized_text) and any(
            t in normalized_text for t in ("trazabilidad", "kardex", "semi", "saldo")
        ):
            return True
        return False

    @staticmethod
    def _extract_codigo_articulo_kardex(normalized_text: str) -> str | None:
        m = _RE_PACK_CODE_KARDEX.search(normalized_text or "")
        if m:
            return m.group(1)
        return None

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
