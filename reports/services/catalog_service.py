from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

from django.db.models import Q

from core.utils.permissions import user_has_full_access
from ..models import ReportDefinition, ReportCategory

# Slugs con metadata inferida «comprobantes» / «listados» (orden + etiqueta «Informe legacy» en tarjetas).
_LEGACY_COMPROBANTES_SLUGS = frozenset(
    {
        "pedidos-pendientes",
        "remitos-no-facturados",
        "remitos_no_facturados",
        "uninvoiced_remitos",
        "cash_flow_detailed_movements",
        "cash_flow_by_account",
        "mayoristapp-comprobantes-no-cancelados",
        "comprobantes-rutas",
    }
)
_LEGACY_LISTADOS_SLUGS = frozenset(
    {
        "ventas_netas",
        "sales_summary",
        "total-consolidado-operativo",
        "inventario_rotacion_cobertura",
        "clientes_churn_ltv",
        "mayoristapp-devoluciones",
        "mayoristapp-filtros-estadisticas",
        "mayoristapp-presupuestos-vendedor",
        "mayoristapp-estado-pedidos-preparacion",
        "ventas-objetivos-vs-bo",
        "ventas-por-vendedor",
        "stock-existencias",
        "resumen-ejecutivo-ventas",
    }
)
_LEGACY_ORDER_DEFAULT = 999


def _infer_legacy_section(slug: str) -> Optional[str]:
    s = (slug or "").strip().lower()
    if s in _LEGACY_COMPROBANTES_SLUGS:
        return "comprobantes"
    if s in _LEGACY_LISTADOS_SLUGS:
        return "listados"
    return None


def _legacy_order_from_metadata(metadata: dict, config: dict) -> int:
    raw = metadata.get("catalog_legacy_order")
    if raw is None:
        raw = config.get("catalog_legacy_order")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return _LEGACY_ORDER_DEFAULT


def split_legacy_catalog(entries: List["CatalogEntry"]) -> Tuple[List["CatalogEntry"], List["CatalogEntry"]]:
    """Ordena entradas por sección legacy (orden explícito + nombre)."""
    comprobantes = sorted(
        [e for e in entries if e.legacy_section == "comprobantes"],
        key=lambda e: (e.legacy_order, e.name.lower()),
    )
    listados = sorted(
        [e for e in entries if e.legacy_section == "listados"],
        key=lambda e: (e.legacy_order, e.name.lower()),
    )
    return comprobantes, listados


DISPLAY_LABELS = {
    # Métricas
    "revenue": "Ingresos",
    "orders": "Órdenes",
    "gross_margin": "Margen bruto",
    "avg_ticket": "Ticket promedio",
    "conversion_rate": "Tasa de conversión",
    "transactions": "Transacciones",
    "new_clients": "Clientes nuevos",
    "repeat_clients": "Clientes recurrentes",
    "churn_rate": "Churn",
    "ltv": "LTV",
    "stock": "Stock",
    "rotation_days": "Rotación (días)",
    "coverage_days": "Cobertura (días)",
    "orders": "Órdenes",
    "lead_time": "Lead time",
    "compliance_rate": "Nivel de cumplimiento",
    "unit_cost_variance": "Variación costo unitario",
    "balance": "Saldo",
    "dso": "DSO",
    "overdue_amount": "Monto vencido",
    "dpo": "DPO",
    "discounts_lost": "Descuentos perdidos",
    "otif": "OTIF",
    "cycle_time": "Tiempo de ciclo",
    "backorders": "Backorders",
    "cogs": "Costo de ventas",
    "ebitda": "EBITDA",
    "net_income": "Resultado neto",
    "budget": "Presupuesto",
    "variance": "Desviación",
    "variance_abs": "Desviación absoluta",
    "variance_pct": "% Desviación",
    "current_ratio": "Razón corriente",
    "quick_ratio": "Prueba ácida",
    "debt_to_equity": "Ratio deuda/capital",
    "total_debt": "Deuda total",
    "interest_expense": "Gasto intereses",
    "interest_coverage": "Cobertura intereses",
    "dso": "DSO",
    "dio": "DIO",
    "ccc": "CCC",
    "operating_flow": "Flujo operativo",
    "investing_flow": "Flujo de inversión",
    "financing_flow": "Flujo de financiamiento",
    "cash_variation": "Variación de caja",
    "burn_rate": "Burn rate",
    "runway_months": "Runway (meses)",
    "cash_balance": "Saldo de caja",
    # Dimensiones
    "date": "Fecha",
    "channel": "Canal",
    "segment": "Segmento",
    "month": "Mes",
    "product_family": "Familia de producto",
    "warehouse": "Depósito",
    "supplier": "Proveedor",
    "supplier_group": "Grupo de proveedores",
    "aging_bucket": "Bucket de antigüedad",
    "customer_segment": "Segmento de clientes",
    "route": "Ruta",
    "branch": "Sucursal",
    "business_unit": "Unidad de negocio",
    "account": "Cuenta",
}

REFRESH_LABELS = {
    "realtime": "Casi en tiempo real",
    "hourly": "Horario",
    "daily": "Diario",
    "weekly": "Semanal",
    "monthly": "Mensual",
}


def _labelize(values: Iterable[str]) -> List[str]:
    return [DISPLAY_LABELS.get(value, value.replace("_", " ").title()) for value in values]


@dataclass
class CatalogEntry:
    """Entrada del catálogo expuesta a menú y APIs."""

    slug: str
    name: str
    description: str
    category: str
    refresh_interval: str
    version: str
    tags: List[str]
    metrics: List[str]
    dimensions: List[str]
    is_visible: bool = True
    is_declarative: bool = False
    # Sección en catálogo «Informes Legacy» (comprobantes / listados); None = sin bloque dedicado.
    legacy_section: Optional[str] = None
    legacy_order: int = _LEGACY_ORDER_DEFAULT


class CatalogService:
    """Servicio que construye el catálogo filtrado por permisos."""

    def __init__(self, user):
        self.user = user

    def _get_base_queryset(self, empresa_id: int | None) -> Iterable[ReportDefinition]:
        """Obtiene el queryset base respetando multiempresa."""
        filters = Q(is_active=True)
        if empresa_id:
            filters &= Q(empresa_id__isnull=True) | Q(empresa_id=empresa_id)
        
        # Filtrar por show_in_catalog: solo mostrar reportes que están habilitados para el catálogo
        filters &= Q(show_in_catalog=True)
        
        # Si el usuario NO es el supervisor (por cod_usuario), filtrar por is_visible
        # Solo el usuario 'supervisor' (por cod_usuario) puede ver todos los reportes
        # Los usuarios con puesto "Supervisor" (por nombre_puesto) solo ven reportes visibles
        is_supervisor_user = False
        if hasattr(self.user, 'cod_usuario') and (self.user.cod_usuario or '').lower() == 'supervisor':
            is_supervisor_user = True
        
        if not is_supervisor_user:
            # Para usuarios con puesto Supervisor u otros, solo mostrar reportes visibles
            # Esto incluye usuarios con puesto "Supervisor" (como lvillanueva)
            filters &= Q(is_visible=True)
        
        return ReportDefinition.objects.filter(filters).select_related("empresa").prefetch_related("widgets")

    def get_catalog(self, empresa_id: int | None) -> List[CatalogEntry]:
        """Devuelve las entradas autorizadas."""
        queryset = self._get_base_queryset(empresa_id)
        catalog: List[CatalogEntry] = []

        can_operational = self.user_has_permission("reports.view_operational")
        can_managerial = self.user_has_permission("reports.view_managerial")

        for definition in queryset:
            if definition.category == ReportCategory.OPERATIONAL and not can_operational:
                continue
            if definition.category == ReportCategory.MANAGERIAL and not can_managerial:
                continue

            config = definition.config or {}
            metadata = definition.metadata or {}
            metrics = _labelize(config.get("metrics", []))
            dimensions = _labelize(config.get("dimensions", []))
            is_declarative = config.get("version") == "declarative-v1"

            legacy_section = metadata.get("catalog_legacy_section") or config.get("catalog_legacy_section")
            if legacy_section not in ("comprobantes", "listados"):
                legacy_section = _infer_legacy_section(definition.slug)
            legacy_order = _legacy_order_from_metadata(metadata, config)

            catalog.append(
                CatalogEntry(
                    slug=definition.slug,
                    name=definition.name,
                    description=definition.description,
                    category=definition.category,
                    refresh_interval=REFRESH_LABELS.get(definition.refresh_interval, definition.refresh_interval.title()),
                    version=definition.version,
                    tags=config.get("tags", []),
                    metrics=metrics,
                    dimensions=dimensions,
                    is_visible=definition.is_visible,
                    is_declarative=is_declarative,
                    legacy_section=legacy_section,
                    legacy_order=legacy_order,
                )
            )
        # Orden: categoría (gerencial antes que operativo), luego orden legacy, luego nombre.
        catalog.sort(key=lambda e: (e.category, e.legacy_order, e.name.lower()))
        return catalog

    def user_has_permission(self, code: str) -> bool:
        """Evalúa permisos soportando superusuarios y comodín."""
        if not self.user or not getattr(self.user, "is_authenticated", False):
            return False
        if user_has_full_access(self.user):
            return True
        if hasattr(self.user, "tiene_permiso") and callable(self.user.tiene_permiso):
            return self.user.tiene_permiso(code)
        if hasattr(self.user, "get_permisos_totales"):
            permisos = self.user.get_permisos_totales()
            return "*" in permisos or code in permisos
        return False


