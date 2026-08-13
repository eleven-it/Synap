from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import logging
import hashlib
import json
import threading
from datetime import datetime, date
from calendar import monthrange

from django.utils import timezone
from django.db import connections
from django.conf import settings

from ..models import ReportDefinition, ReportExecutionLog
from ..tasks import enqueue_report_refresh
from ..cache import get_cached_report, set_cached_report, build_cache_key
from .sample_data import get_sample_data
from .connection_pool import get_mysql_pool
from .execution_engine import ReportExecutionEngine

logger = logging.getLogger(__name__)

# Cache locks para prevenir cache stampeding
_cache_locks = {}


@dataclass
class QueryResult:
    """Respuesta estructurada para consultas de reportes."""

    meta: Dict
    data: List[Dict]
    totals: Dict[str, float]
    notes: List[str]


class QueryRunnerService:
    """Servicio responsable de ejecutar consultas declarativas."""

    def __init__(self, user):
        self.user = user
        self.execution_engine = None  # Se inicializa lazy cuando se necesita
    
    def _format_date(self, date_str: str) -> str:
        """
        Convierte una fecha del formato YYYY-MM-DD al formato dd/MM/yyyy.
        
        Args:
            date_str: Fecha en formato YYYY-MM-DD
            
        Returns:
            Fecha en formato dd/MM/yyyy
        """
        try:
            if date_str:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                return date_obj.strftime("%d/%m/%Y")
            return date_str
        except (ValueError, AttributeError):
            # Si hay algún error, devolver la fecha original
            return date_str

    def _resolve_period_dates(self, filters: dict) -> tuple:
        """
        Resuelve fecha_inicio y fecha_fin desde filters. Prioriza las recibidas (UI).
        Solo recalcula cuando falta alguna; las fechas mostradas se usan en las consultas SQL.
        Returns:
            (fecha_inicio, fecha_fin) en YYYY-MM-DD, o (None, None) si no se pueden resolver.
        """
        fecha_inicio = filters.get("fecha_inicio") or None
        fecha_fin = filters.get("fecha_fin") or None
        dia_actual = filters.get("dia_actual", False)
        mes_actual = filters.get("mes_actual", False)
        año_actual = filters.get("año_actual", False)
        today = date.today()
        if fecha_inicio and fecha_fin:
            return fecha_inicio, fecha_fin
        if dia_actual:
            s = today.strftime("%Y-%m-%d")
            return s, s
        if año_actual:
            return (
                date(today.year, 1, 1).strftime("%Y-%m-%d"),
                date(today.year, 12, 31).strftime("%Y-%m-%d"),
            )
        if mes_actual:
            last = monthrange(today.year, today.month)[1]
            return (
                date(today.year, today.month, 1).strftime("%Y-%m-%d"),
                date(today.year, today.month, last).strftime("%Y-%m-%d"),
            )
        last = monthrange(today.year, today.month)[1]
        return (
            date(today.year, today.month, 1).strftime("%Y-%m-%d"),
            date(today.year, today.month, last).strftime("%Y-%m-%d"),
        )

    def _get_tenant_id(self, payload: Dict) -> Optional[int]:
        """Obtiene el tenant_id del payload o del usuario."""
        # Intentar obtener desde payload
        filters = payload.get('filters', {})
        tenant_id = filters.get('tenant_id')
        
        # Si no está en payload, intentar desde usuario
        if not tenant_id and hasattr(self.user, 'id'):
            tenant_id = self.user.id
        
        return tenant_id
    
    def _hash_payload(self, filters: Dict) -> str:
        """Genera hash del payload para clave de caché."""
        # Ordenar keys para consistencia
        sorted_filters = json.dumps(filters, sort_keys=True, default=str)
        return hashlib.md5(sorted_filters.encode()).hexdigest()
    
    def _get_cache_ttl(self, report_slug: str, filters: Dict) -> int:
        """
        Calcula TTL dinámico según tipo de reporte y período consultado.
        
        Estrategia:
        - Datos recientes (últimos 7 días): TTL corto (60s) para máxima frescura
        - Datos del mes (8-30 días): TTL medio (300s) para balance
        - Datos históricos (>30 días): TTL largo (900s+) para máxima performance
        """
        # Reportes operativos (alta frecuencia de cambios)
        operational_reports = [
            'cash_flow_waterfall',
            'cash_flow_detailed_movements',
            'cash_flow_by_account',
            'ventas_netas'
        ]
        
        if report_slug in operational_reports:
            # Calcular días desde fecha_fin hasta hoy
            fecha_fin = filters.get('fecha_fin')
            if fecha_fin:
                try:
                    fecha_fin_obj = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
                    dias_desde_fin = (date.today() - fecha_fin_obj).days
                    
                    if dias_desde_fin <= 7:
                        # Datos recientes: TTL corto para máxima frescura
                        return 60  # 1 minuto
                    elif dias_desde_fin <= 30:
                        # Datos del mes: TTL medio para balance
                        return 300  # 5 minutos
                    else:
                        # Datos históricos: TTL largo para máxima performance
                        return 900  # 15 minutos
                except (ValueError, TypeError):
                    # Si hay error parseando fecha, usar default
                    pass
        
        # Reportes gerenciales (baja frecuencia de cambios)
        managerial_reports = ['sales_summary']
        if report_slug in managerial_reports:
            return 1800  # 30 minutos
        
        # Reportes de estado (frecuencia media)
        status_reports = ['uninvoiced_remitos', 'pending_orders', 'bo-stock-facturacion', 'ventas-bom-docenas']
        if report_slug in status_reports:
            return 300  # 5 minutos
        
        # Default: 15 minutos
        return 900
    
    def _get_cached_with_lock(self, tenant_id: Optional[int], slug: str, payload_hash: str) -> Optional[QueryResult]:
        """
        Obtiene caché con protección contra cache stampeding.
        
        Si múltiples requests llegan cuando el caché expira, solo uno ejecuta la consulta.
        """
        # Intentar obtener del caché
        cached = get_cached_report(tenant_id, slug, payload_hash)
        if cached:
            return cached
        
        # Si no hay caché, usar lock para evitar múltiples consultas simultáneas
        lock_key = f"{tenant_id or 'global'}:{slug}:{payload_hash}"
        if lock_key not in _cache_locks:
            _cache_locks[lock_key] = threading.Lock()
        
        with _cache_locks[lock_key]:
            # Verificar nuevamente (otro thread pudo haberlo cacheado mientras esperábamos)
            cached = get_cached_report(tenant_id, slug, payload_hash)
            if cached:
                logger.debug(f"Cache HIT después de lock para {slug}")
                return cached
            
            # No hay caché, retornar None para que se ejecute la consulta
            # (el lock se libera automáticamente al salir del with)
            return None

    def run(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """Ejecuta la consulta solicitada con caché inteligente."""
        started_at = timezone.now()
        
        # Verificar si el reporte usa configuración declarativa
        config = report.config or {}
        if config.get("version") == "declarative-v1":
            # Para reportes declarativos, el ReportExecutionEngine maneja su propio caché
            # con filtros normalizados, así que delegamos directamente
            if self.execution_engine is None:
                pool = get_mysql_pool()
                self.execution_engine = ReportExecutionEngine(connection_pool=pool)
            
            logger.info(f"🔄 Ejecutando reporte declarativo: {report.slug}")
            result = self.execution_engine.run(report, payload, user=self.user)
            return result
        
        # Para reportes legacy, usar la lógica de caché existente
        # Construir clave de caché
        tenant_id = self._get_tenant_id(payload)
        filters = payload.get('filters', {})
        payload_hash = self._hash_payload(filters)
        # Cache buster para BO: OC cubre primero faltante reservado (evitar usar caché antiguo)
        if report.slug == "bo-stock-facturacion":
            cache_payload_hash = f"{payload_hash}:oc_reservado_v1"
        elif report.slug == "ventas-bom-docenas":
            cache_payload_hash = f"{payload_hash}:vbd_v1"
        else:
            cache_payload_hash = payload_hash

        # Intentar obtener del caché con protección contra stampeding (solo si está habilitado)
        if getattr(settings, 'REPORTS_CACHE_ENABLED', False):
            cached_result = self._get_cached_with_lock(tenant_id, report.slug, cache_payload_hash)
            if cached_result:
                logger.info(f"✅ Cache HIT para {report.slug} (payload_hash: {payload_hash[:8]}...)")
                return cached_result
            logger.info(f"❌ Cache MISS para {report.slug} (payload_hash: {payload_hash[:8]}...), ejecutando consulta...")
        
        # Ejecutar consulta según el tipo de reporte (lógica legacy)
        result = None
        if report.slug in ("ventas_netas", "ventas-netas"):
            result = self._run_ventas_netas(report, payload)
        elif report.slug == "cash_flow_waterfall":
            result = self._run_cash_flow_waterfall(report, payload)
        elif report.slug == "cash_flow_detailed_movements":
            result = self._run_cash_flow_detailed_movements(report, payload)
        elif report.slug == "cash_flow_by_account":
            result = self._run_cash_flow_by_account(report, payload)
        elif report.slug in ("uninvoiced_remitos", "remitos-no-facturados"):
            result = self._run_uninvoiced_remitos(report, payload)
        elif report.slug in ("pending_orders", "pedidos-pendientes"):
            result = self._run_pending_orders(report, payload)
        elif report.slug == "sales_summary":
            result = self._run_sales_summary(report, payload)
        elif report.slug == "total-consolidado-operativo":
            result = self._run_total_consolidado_operativo(report, payload)
        elif report.slug == "bo-stock-facturacion":
            result = self._run_backorder_vs_stock_vs_facturacion(report, payload)
        elif report.slug == "ventas-bom-docenas":
            from reports.services.ventas_bom_docenas_runner import run_ventas_bom_docenas

            result = run_ventas_bom_docenas(
                report,
                payload,
                user=self.user,
                resolve_period_dates=self._resolve_period_dates,
            )
        else:
            # Para otros reportes, usar datos de muestra por ahora
            meta, data, totals, notes = get_sample_data(report.slug, payload)
            if not data:
                data = []
                totals = {}
                notes = ["Data source execution not implemented yet."]
                meta = {
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                }
            else:
                meta.update(
                    {
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    }
                )
            result = QueryResult(meta=meta, data=data, totals=totals, notes=notes)
        
        # Calcular TTL inteligente y guardar en caché (solo si está habilitado)
        if result and getattr(settings, 'REPORTS_CACHE_ENABLED', False):
            ttl = self._get_cache_ttl(report.slug, filters)
            set_cached_report(tenant_id, report.slug, cache_payload_hash, result, ttl=ttl)
            logger.info(f"💾 Resultado cacheado para {report.slug} con TTL de {ttl}s")
        
        return result

        # Registrar log básico
        duration = (timezone.now() - started_at).total_seconds() * 1000
        
        # Obtener usuario válido para ForeignKey
        from core.models import UsuarioExtendido
        executed_by_user = None
        if isinstance(self.user, UsuarioExtendido) and getattr(self.user, "is_authenticated", False):
            executed_by_user = self.user
        
        ReportExecutionLog.objects.create(
            report=report,
            executed_by=executed_by_user,
            status="success",
            filters_snapshot=payload.get("filters", {}),
            duration_ms=int(duration),
            notes="\n".join(notes),
        )

        # Programar refresco si corresponde
        try:
            # Celery deshabilitado - ejecutar directamente
            enqueue_report_refresh(report.slug)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unable to enqueue refresh for %s: %s", report.slug, exc)

        return QueryResult(
            meta=meta,
            data=data,
            totals=totals,
            notes=notes,
        )
    
    def _run_ventas_netas(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """
        Ejecuta la consulta SQL para el reporte de Ventas Netas.
        Calcula: Ventas (FA,FB,FC,FE,FM) - NC (NCA,NCB,NCC,NCE,NCM) sin impuestos.
        """
        started_at = timezone.now()
        
        try:
            filters = payload.get("filters", {})
            base_empresa = filters.get("base_empresa")
            fecha_inicio, fecha_fin = self._resolve_period_dates(filters)
            if not fecha_inicio or not fecha_fin:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
                )
            # Si aún no tenemos base_empresa, intentar desde atributos del usuario
            if not base_empresa:
                if hasattr(self.user, 'base_empresa'):
                    base_empresa = self.user.base_empresa
            
            # Si aún no tenemos base_empresa, intentar obtenerla de la configuración
            if not base_empresa:
                # Intentar obtener desde settings o contexto
                base_empresa = getattr(settings, 'DEFAULT_BASE_EMPRESA', None)
            
            if not base_empresa:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se pudo determinar la base de datos de la empresa. Asegúrese de estar logueado correctamente."],
                )
            
            # Obtener filtros de punto de venta y sucursales
            puntos_venta = filters.get("punto_venta", [])
            if isinstance(puntos_venta, str):
                puntos_venta = [puntos_venta] if puntos_venta else []
            elif not isinstance(puntos_venta, list):
                puntos_venta = []
            
            sucursales = filters.get("sucursales", [])
            if isinstance(sucursales, str):
                sucursales = [sucursales] if sucursales else []
            elif not isinstance(sucursales, list):
                sucursales = []
            
            # Clientes a excluir (NOT IN): excluir de la consulta los clientes seleccionados
            clientes_excluidos = filters.get("clientes_excluidos", [])
            if isinstance(clientes_excluidos, str):
                clientes_excluidos = [clientes_excluidos] if clientes_excluidos else []
            elif not isinstance(clientes_excluidos, list):
                clientes_excluidos = []
            
            # Construir consulta SQL
            # Obtener pool de conexiones MySQL (reutiliza conexiones existentes)
            pool = get_mysql_pool()
            
            # Usar connection pool - todas las consultas dentro de este bloque
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
            
            # Construir WHERE conditions
            where_conditions = [
                "cc.Fecha >= %s",
                "cc.Fecha <= %s",
                "cc.Anulado = 'No'",
                "cc.CodigoMovimiento <> 0",
                "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')"
            ]
            params = [fecha_inicio, fecha_fin]
            
            # Filtro de punto de venta
            if puntos_venta:
                puntos_venta_ints = []
                for pv in puntos_venta:
                    try:
                        puntos_venta_ints.append(int(pv))
                    except (ValueError, TypeError):
                        continue
                if puntos_venta_ints:
                    placeholders = ','.join(['%s'] * len(puntos_venta_ints))
                    where_conditions.append(f"cc.id_pv IN ({placeholders})")
                    params.extend(puntos_venta_ints)
            
            # Filtro de sucursales
            if sucursales:
                sucursales_ints = []
                for s in sucursales:
                    try:
                        sucursales_ints.append(int(s))
                    except (ValueError, TypeError):
                        continue
                if sucursales_ints:
                    placeholders = ','.join(['%s'] * len(sucursales_ints))
                    where_conditions.append(f"cc.CodSucursal IN ({placeholders})")
                    params.extend(sucursales_ints)
            
            # Filtro NOT IN: excluir clientes seleccionados (cc.Codigo = cliente)
            if clientes_excluidos:
                clientes_vals = []
                for c in clientes_excluidos:
                    try:
                        # Codigo en cliente puede ser int o string según base; normalizar a string para NOT IN
                        c_str = str(c).strip()
                        if c_str:
                            clientes_vals.append(int(c_str) if c_str.isdigit() else c_str)
                    except (ValueError, TypeError):
                        continue
                if clientes_vals:
                    placeholders = ','.join(['%s'] * len(clientes_vals))
                    where_conditions.append(f"cc.Codigo NOT IN ({placeholders})")
                    params.extend(clientes_vals)
                    logger.info(f"📋 Ventas Netas: aplicando exclusión de {len(clientes_vals)} cliente(s): {clientes_vals[:5]}{'...' if len(clientes_vals) > 5 else ''}")
            
            where_clause = " AND ".join(where_conditions)
            
            # Consulta SQL principal
            # Calcular ventas netas: Suma de facturas - Suma de notas de crédito (ambas sin impuestos)
            # Nota: Usamos %% para escapar % en f-strings de Python (se convierte en % en MySQL)
            sql = f"""
                SELECT 
                    DATE_FORMAT(cc.Fecha, '%%Y-%%m') AS mes,
                    DATE_FORMAT(cc.Fecha, '%%m/%%Y') AS mes_formato,
                    cc.CodSucursal AS id_sucursal,
                    COALESCE(s.nombre_sucursal, 'Sin Sucursal') AS nombre_sucursal,
                    cc.id_pv AS id_punto_venta,
                    COALESCE(CAST(pv.nro_punto_venta AS CHAR), CAST(cc.id_pv AS CHAR), 'Sin PV') AS nro_punto_venta,
                    SUM(CASE 
                        WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') 
                        THEN COALESCE(cc.SubtotalDesc, 0)
                        ELSE 0 
                    END) AS ventas_brutas,
                    SUM(CASE 
                        WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') 
                        THEN COALESCE(cc.SubtotalDesc, 0)
                        ELSE 0 
                    END) AS notas_credito,
                    SUM(CASE 
                        WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') 
                        THEN COALESCE(cc.SubtotalDesc, 0)
                        WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') 
                        THEN -COALESCE(cc.SubtotalDesc, 0)
                        ELSE 0 
                    END) AS ventas_netas
                FROM cuentacliente cc
                LEFT JOIN sucursales s ON s.id_sucursal = cc.CodSucursal
                LEFT JOIN punto_venta pv ON pv.id_punto_venta = cc.id_pv
                WHERE {where_clause}
                GROUP BY 
                    DATE_FORMAT(cc.Fecha, '%%Y-%%m'),
                    cc.CodSucursal,
                    COALESCE(s.nombre_sucursal, 'Sin Sucursal'),
                    cc.id_pv,
                    COALESCE(CAST(pv.nro_punto_venta AS CHAR), CAST(cc.id_pv AS CHAR), 'Sin PV')
                ORDER BY 
                    DATE_FORMAT(cc.Fecha, '%%Y-%%m') DESC,
                    COALESCE(s.nombre_sucursal, 'Sin Sucursal') ASC,
                    COALESCE(pv.nro_punto_venta, cc.id_pv) ASC
            """
            
            logger.info(f"🔍 Ejecutando consulta Ventas Netas: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, base_empresa={base_empresa}")
            logger.debug(f"SQL: {sql}")
            logger.debug(f"Params: {params}")
            
            try:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
            except Exception as sql_error:
                logger.error(f"❌ Error SQL ejecutando consulta: {sql_error}")
                logger.error(f"SQL: {sql}")
                logger.error(f"Params: {params}")
                raise
            
            # Obtener nombres de columnas desde cursor.description
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Convertir resultados a formato de diccionario
            data = []
            totals = {
                "ventas_brutas": 0.0,
                "notas_credito": 0.0,
                "ventas_netas": 0.0,
            }
            
            for row in rows:
                # Convertir tupla a diccionario
                row_dict = dict(zip(columns, row))
                
                # Convertir Decimal a float para JSON
                row_dict["ventas_brutas"] = float(row_dict.get("ventas_brutas", 0) or 0)
                row_dict["notas_credito"] = float(row_dict.get("notas_credito", 0) or 0)
                row_dict["ventas_netas"] = float(row_dict.get("ventas_netas", 0) or 0)
                
                totals["ventas_brutas"] += row_dict["ventas_brutas"]
                totals["notas_credito"] += row_dict["notas_credito"]
                totals["ventas_netas"] += row_dict["ventas_netas"]
                
                data.append(row_dict)
                
                logger.info(f"✅ Consulta ejecutada: {len(data)} registros obtenidos")
            
            # Registrar log de ejecución
            duration = (timezone.now() - started_at).total_seconds() * 1000
            from core.models import UsuarioExtendido
            executed_by_user = None
            if isinstance(self.user, UsuarioExtendido) and getattr(self.user, "is_authenticated", False):
                executed_by_user = self.user
            
            ReportExecutionLog.objects.create(
                report=report,
                executed_by=executed_by_user,
                status="success",
                filters_snapshot=filters,
                duration_ms=int(duration),
                notes=f"Consulta ejecutada exitosamente. {len(data)} registros obtenidos.",
            )
            
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                    "currency": "ARS",
                    "tz": "America/Argentina/Buenos_Aires",
                },
                data=data,
                totals=totals,
                notes=[
                    f"Período: {self._format_date(fecha_inicio)} a {self._format_date(fecha_fin)}",
                    f"Total registros: {len(data)}",
                    "Cálculo: Ventas (FA,FB,FC,FE,FM) - NC (NCA,NCB,NCC,NCE,NCM) sin impuestos",
                ],
            )
                
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"❌ Error ejecutando consulta Ventas Netas: {e}")
            logger.error(f"Traceback completo:\n{error_traceback}")
            
            # Conexión cerrada automáticamente por el context manager
            
            duration = (timezone.now() - started_at).total_seconds() * 1000
            from core.models import UsuarioExtendido
            executed_by_user = None
            if isinstance(self.user, UsuarioExtendido) and getattr(self.user, "is_authenticated", False):
                executed_by_user = self.user
            
            try:
                ReportExecutionLog.objects.create(
                    report=report,
                    executed_by=executed_by_user,
                    status="error",
                    filters_snapshot=filters,
                    duration_ms=int(duration),
                    notes=f"Error: {str(e)}",
                )
            except:
                pass  # Si falla el log, continuar
            
            # Re-lanzar la excepción para que la API view la capture
            raise
    
    def _run_cash_flow_waterfall(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """
        Ejecuta la consulta SQL para el reporte de Cash Flow Waterfall.
        Calcula flujos de caja operativos, de inversión y financiamiento basado en la tabla caja.
        """
        started_at = timezone.now()
        
        try:
            filters = payload.get("filters", {})
            base_empresa = filters.get("base_empresa")
            fecha_inicio, fecha_fin = self._resolve_period_dates(filters)
            if not fecha_inicio or not fecha_fin:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
                )
            if not base_empresa:
                if hasattr(self.user, 'base_empresa'):
                    base_empresa = self.user.base_empresa
            if not base_empresa:
                base_empresa = getattr(settings, 'DEFAULT_BASE_EMPRESA', None)
            
            if not base_empresa:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se pudo determinar la base de datos de la empresa. Asegúrese de estar logueado correctamente."],
                )
            
            # Obtener filtros opcionales
            # NOTA: El filtro de moneda ha sido eliminado para incluir todos los movimientos
            # independientemente de la moneda, manteniendo consistencia con la consulta principal
            id_caja = filters.get("id_caja")
            # id_caja puede ser un array (múltiples cajas) o un string único (una caja)
            if isinstance(id_caja, str):
                id_caja = [id_caja] if id_caja else []
            elif not isinstance(id_caja, list):
                id_caja = []
            
            # Obtener pool de conexiones MySQL (reutiliza conexiones existentes)
            pool = get_mysql_pool()
            
            # Usar connection pool - todas las consultas dentro de este bloque
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                
                # Clasificación de tipos de movimiento según formularios analizados:
            # OPERATIVOS: Facturas de contado, cobranzas, pagos, gastos operativos, movimientos de caja operativos
            # INVERSIÓN: (generalmente no hay en administraNET, pero se puede identificar por tipo)
            # FINANCIAMIENTO: Préstamos, aportes de capital, etc.
            
            # Construir WHERE conditions
            # NOTA: Por ahora NO filtramos por moneda para incluir todos los movimientos
            # que cumplan con las otras condiciones (fecha y anulado)
            where_conditions = [
                "c.fecha >= %s",
                "c.fecha <= %s",
                "c.anulado = 'No'"
            ]
            params = [fecha_inicio, fecha_fin]
            
            # Filtro de caja(s) específica(s) - puede ser una o múltiples
            id_cajas_int = []
            if id_caja and len(id_caja) > 0:
                try:
                    id_cajas_int = [int(c) for c in id_caja if c]
                    if id_cajas_int:
                        # Si hay múltiples cajas, usar IN
                        if len(id_cajas_int) == 1:
                            where_conditions.append("(c.id_caja_abm_origen = %s OR c.id_caja_abm_destino = %s)")
                            params.extend([id_cajas_int[0], id_cajas_int[0]])
                        else:
                            placeholders = ",".join(["%s"] * len(id_cajas_int))
                            where_conditions.append(f"(c.id_caja_abm_origen IN ({placeholders}) OR c.id_caja_abm_destino IN ({placeholders}))")
                            params.extend(id_cajas_int + id_cajas_int)
                except (ValueError, TypeError):
                    id_cajas_int = []
            
            where_clause = " AND ".join(where_conditions)
            
            # Consultas de diagnóstico: Solo ejecutar si DEBUG=True
            # Estas consultas agregan ~500ms de latencia y no son necesarias en producción
            if settings.DEBUG:
                # Diagnóstico 1: Verificar si hay movimientos en el período sin filtros estrictos
                sql_diag_total = """
                    SELECT COUNT(*) as total_movimientos,
                           MIN(c.fecha) as fecha_min,
                           MAX(c.fecha) as fecha_max,
                           COUNT(DISTINCT c.moneda) as monedas_distintas,
                           GROUP_CONCAT(DISTINCT c.moneda) as monedas
                    FROM caja c
                    WHERE c.fecha >= %s AND c.fecha <= %s
                """
                try:
                    cursor.execute(sql_diag_total, [fecha_inicio, fecha_fin])
                    diag_total = cursor.fetchone()
                    logger.info(f"🔍 [DEBUG] Diagnóstico general del período:")
                    logger.info(f"   - Total movimientos (sin filtros): {diag_total[0]}")
                    logger.info(f"   - Fecha mínima: {diag_total[1]}, Fecha máxima: {diag_total[2]}")
                    logger.info(f"   - Monedas distintas: {diag_total[3]} ({diag_total[4]})")
                except Exception as diag_error:
                    logger.warning(f"⚠️ Error en diagnóstico general: {diag_error}")
                
                # Diagnóstico 2: Verificar movimientos con filtro de anulado
                sql_diag_anulado = """
                    SELECT c.anulado, COUNT(*) as cantidad
                    FROM caja c
                    WHERE c.fecha >= %s AND c.fecha <= %s
                    GROUP BY c.anulado
                """
                try:
                    cursor.execute(sql_diag_anulado, [fecha_inicio, fecha_fin])
                    anulados = cursor.fetchall()
                    logger.info(f"🔍 [DEBUG] Movimientos por estado 'anulado':")
                    for anulado_row in anulados:
                        logger.info(f"   - anulado='{anulado_row[0]}': {anulado_row[1]} movimientos")
                except Exception as diag_error:
                    logger.warning(f"⚠️ Error en diagnóstico de anulados: {diag_error}")
                
                # Diagnóstico 3: Analizar comportamiento de cada tipo de comprobante
                sql_diagnostico = f"""
                    SELECT 
                        c.tipo,
                        c.tipo_comprobante,
                        COUNT(*) as cantidad,
                        SUM(CASE WHEN c.ingreso > 0 AND c.egreso = 0 THEN 1 ELSE 0 END) as solo_ingreso,
                        SUM(CASE WHEN c.ingreso = 0 AND c.egreso > 0 THEN 1 ELSE 0 END) as solo_egreso,
                        SUM(CASE WHEN c.ingreso > 0 AND c.egreso > 0 THEN 1 ELSE 0 END) as ambos,
                        SUM(COALESCE(c.ingreso, 0)) AS suma_ingresos,
                        SUM(COALESCE(c.egreso, 0)) AS suma_egresos,
                        SUM(COALESCE(c.ingreso, 0) - COALESCE(c.egreso, 0)) AS neto
                    FROM caja c
                    WHERE {where_clause}
                    GROUP BY c.tipo, c.tipo_comprobante
                    ORDER BY cantidad DESC
                """
                try:
                    cursor.execute(sql_diagnostico, params)
                    tipos_existentes = cursor.fetchall()
                    logger.info(f"🔍 [DEBUG] ANÁLISIS DETALLADO - Comportamiento de tipos de comprobantes en el período:")
                    logger.info(f"   Total de combinaciones tipo/tipo_comprobante: {len(tipos_existentes)}")
                    for tipo_row in tipos_existentes:
                        tipo = tipo_row[0] or 'NULL'
                        tipo_comp = tipo_row[1] or 'NULL'
                        cantidad = tipo_row[2] or 0
                        solo_ing = tipo_row[3] or 0
                        solo_egr = tipo_row[4] or 0
                        ambos = tipo_row[5] or 0
                        suma_ing = float(tipo_row[6] or 0)
                        suma_egr = float(tipo_row[7] or 0)
                        neto = float(tipo_row[8] or 0)
                        
                        logger.info(f"   Tipo: '{tipo}' | Comprobante: '{tipo_comp}' | Cantidad: {cantidad}")
                        logger.info(f"      Solo ingreso: {solo_ing} | Solo egreso: {solo_egr} | Ambos: {ambos}")
                        logger.info(f"      Suma ingresos: ${suma_ing:,.2f} | Suma egresos: ${suma_egr:,.2f} | Neto: ${neto:,.2f}")
                except Exception as diag_error:
                    logger.warning(f"⚠️ No se pudo ejecutar consulta de diagnóstico: {diag_error}")
            else:
                logger.debug(f"⏭️ Consultas de diagnóstico omitidas (DEBUG=False)")
            
            # Primero, obtener el saldo inicial (último saldo antes de la fecha de inicio)
            # Calcular saldo inicial: suma de los últimos saldos de cada caja antes de fecha_inicio
            # El campo 'saldo' es por caja, por lo que debemos sumar los saldos de todas las cajas
            if id_cajas_int and len(id_cajas_int) > 0:
                # Si hay caja(s) específica(s), obtener el saldo de esas cajas
                if len(id_cajas_int) == 1:
                    sql_saldo_inicial = """
                        SELECT c.saldo
                        FROM caja c
                        WHERE c.fecha < %s
                            AND c.anulado = 'No'
                            AND (c.id_caja_abm_origen = %s OR c.id_caja_abm_destino = %s)
                        ORDER BY c.fecha DESC, c.codigo_movimiento DESC LIMIT 1
                    """
                    params_saldo = [fecha_inicio, id_cajas_int[0], id_cajas_int[0]]
                else:
                    # Múltiples cajas: sumar los últimos saldos de cada una
                    placeholders = ",".join(["%s"] * len(id_cajas_int))
                    sql_saldo_inicial = f"""
                        SELECT COALESCE(SUM(saldo_por_caja), 0) as saldo_total
                        FROM (
                            SELECT 
                                DISTINCT c.id_caja_abm_origen,
                                COALESCE((
                                    SELECT c2.saldo 
                                    FROM caja c2 
                                    WHERE c2.id_caja_abm_origen = c.id_caja_abm_origen
                                      AND c2.anulado = 'No'
                                      AND c2.fecha < %s
                                      AND c2.id_caja_abm_origen IN ({placeholders})
                                    ORDER BY c2.fecha DESC, c2.codigo_movimiento DESC 
                                    LIMIT 1
                                ), 0) as saldo_por_caja
                            FROM caja c
                            WHERE c.anulado = 'No'
                              AND c.id_caja_abm_origen IN ({placeholders})
                            GROUP BY c.id_caja_abm_origen
                        ) as saldos_cajas
                    """
                    params_saldo = [fecha_inicio] + id_cajas_int + id_cajas_int
            else:
                # Si vemos todas las cajas, sumar los últimos saldos de cada caja ANTES de fecha_inicio
                # IMPORTANTE: Debemos considerar TODAS las cajas que tienen movimientos (en cualquier momento),
                # no solo las que tienen movimientos antes de fecha_inicio, para que el cálculo sea consistente
                sql_saldo_inicial = """
                    SELECT COALESCE(SUM(saldo_por_caja), 0) as saldo_total
                    FROM (
                        SELECT 
                            DISTINCT c.id_caja_abm_origen,
                            COALESCE((
                                SELECT c2.saldo 
                                FROM caja c2 
                                WHERE c2.id_caja_abm_origen = c.id_caja_abm_origen
                                  AND c2.anulado = 'No'
                                  AND c2.fecha < %s
                                ORDER BY c2.fecha DESC, c2.codigo_movimiento DESC 
                                LIMIT 1
                            ), 0) as saldo_por_caja
                        FROM caja c
                        WHERE c.anulado = 'No'
                        GROUP BY c.id_caja_abm_origen
                    ) as saldos_cajas
                """
                params_saldo = [fecha_inicio]
            
            try:
                cursor.execute(sql_saldo_inicial, params_saldo)
                saldo_inicial_row = cursor.fetchone()
                saldo_inicial = float(saldo_inicial_row[0]) if saldo_inicial_row and saldo_inicial_row[0] else 0.0
                logger.info(f"💰 Saldo inicial calculado: ${saldo_inicial:,.2f}")
                logger.info(f"   Tipo de consulta: {'Caja(s) específica(s) (IDs: ' + ', '.join(map(str, id_cajas_int)) + ')' if id_cajas_int else 'Todas las cajas'}")
                if not id_cajas_int:
                    # Validar que estamos considerando todas las cajas
                    sql_count_cajas = """
                        SELECT COUNT(DISTINCT id_caja_abm_origen)
                        FROM caja
                        WHERE anulado = 'No'
                    """
                    cursor.execute(sql_count_cajas)
                    total_cajas = cursor.fetchone()[0] or 0
                    logger.info(f"   Total de cajas en la base de datos: {total_cajas}")
            except Exception as e:
                logger.warning(f"⚠️ Error calculando saldo inicial, usando 0: {e}")
                logger.error(f"   SQL: {sql_saldo_inicial}")
                logger.error(f"   Params: {params_saldo}")
                saldo_inicial = 0.0
            
            # Consulta SQL principal para obtener flujos por mes
            # IMPORTANTE: Los campos ingreso y egreso siempre están expresados en positivo
            # - Si es un INGRESO: ingreso > 0 y egreso = 0
            # - Si es un EGRESO: ingreso = 0 y egreso > 0
            # Clasificamos los movimientos según el campo 'tipo' y 'tipo_comprobante'
            # Basado en los formularios VB6: CargaMovCaja.frm y Caja.frm
            campo_ingreso_real = "COALESCE(c.ingreso, 0)"
            campo_egreso_real = "COALESCE(c.egreso, 0)"
            
            sql = f"""
                SELECT 
                    DATE_FORMAT(c.fecha, '%%Y-%%m') AS mes,
                    DATE_FORMAT(c.fecha, '%%m/%%Y') AS mes_formato,
                    -- Flujos Operativos: 
                    -- ESTRATEGIA: Incluir TODOS los movimientos EXCEPTO los explícitamente de inversión o financiamiento
                    -- CÁLCULO: ingreso - egreso
                    -- - Si ingreso > 0 y egreso = 0 entonces positivo (entrada de dinero)
                    -- - Si ingreso = 0 y egreso > 0 entonces negativo (salida de dinero)
                    -- - Si ambos > 0 entonces neto (puede ser positivo o negativo)
                    -- NOTA: Las transferencias entre cajas aparecen como egreso en origen e ingreso en destino
                    -- Si vemos todas las cajas, se cancelan. Si vemos una caja específica, solo cuenta el movimiento de esa caja.
                    SUM(CASE 
                        WHEN c.tipo LIKE '%%Inversión%%' OR c.tipo LIKE '%%Activo Fijo%%' 
                             OR c.tipo LIKE '%%Préstamo%%' OR c.tipo LIKE '%%Aporte%%' OR c.tipo LIKE '%%Capital%%'
                        THEN 0
                        -- Excluir cierres de caja (movimientos internos contables que se cancelan entre cajas)
                        WHEN c.tipo LIKE '%%Cierre de Caja%%'
                        THEN 0
                        -- Excluir transferencias entre cajas (se cancelan entre cajas)
                        WHEN c.tipo LIKE '%%Transferencia de Fondos%%'
                        THEN 0
                        ELSE {campo_ingreso_real} - {campo_egreso_real}
                    END) AS operating_flow,
                    -- Flujos de Inversión (generalmente vacío en administraNET)
                    -- Excluir movimientos internos (cierres y transferencias)
                    SUM(CASE 
                        WHEN c.tipo LIKE '%%Cierre de Caja%%' OR c.tipo LIKE '%%Transferencia de Fondos%%'
                        THEN 0
                        WHEN c.tipo LIKE '%%Inversión%%' OR c.tipo LIKE '%%Activo Fijo%%'
                        THEN COALESCE({campo_ingreso_real}, 0) - COALESCE({campo_egreso_real}, 0)
                        ELSE 0
                    END) AS investing_flow,
                    -- Flujos de Financiamiento
                    -- Excluir movimientos internos (cierres y transferencias)
                    SUM(CASE 
                        WHEN c.tipo LIKE '%%Cierre de Caja%%' OR c.tipo LIKE '%%Transferencia de Fondos%%'
                        THEN 0
                        WHEN c.tipo LIKE '%%Préstamo%%' OR c.tipo LIKE '%%Aporte%%' OR c.tipo LIKE '%%Capital%%'
                        THEN COALESCE({campo_ingreso_real}, 0) - COALESCE({campo_egreso_real}, 0)
                        ELSE 0
                    END) AS financing_flow,
                    -- Ingresos operativos (excluyendo movimientos internos e inversión/financiamiento)
                    SUM(CASE 
                        WHEN c.tipo LIKE '%%Inversión%%' OR c.tipo LIKE '%%Activo Fijo%%' 
                             OR c.tipo LIKE '%%Préstamo%%' OR c.tipo LIKE '%%Aporte%%' OR c.tipo LIKE '%%Capital%%'
                             OR c.tipo LIKE '%%Cierre de Caja%%'
                             OR c.tipo LIKE '%%Transferencia de Fondos%%'
                        THEN 0
                        ELSE {campo_ingreso_real}
                    END) AS operating_ingresos,
                    -- Egresos operativos (excluyendo movimientos internos e inversión/financiamiento)
                    SUM(CASE 
                        WHEN c.tipo LIKE '%%Inversión%%' OR c.tipo LIKE '%%Activo Fijo%%' 
                             OR c.tipo LIKE '%%Préstamo%%' OR c.tipo LIKE '%%Aporte%%' OR c.tipo LIKE '%%Capital%%'
                             OR c.tipo LIKE '%%Cierre de Caja%%'
                             OR c.tipo LIKE '%%Transferencia de Fondos%%'
                        THEN 0
                        ELSE {campo_egreso_real}
                    END) AS operating_egresos,
                    -- Total de ingresos y egresos para referencia (usando campos reales)
                    SUM({campo_ingreso_real}) AS total_ingresos,
                    SUM({campo_egreso_real}) AS total_egresos
                FROM caja c
                WHERE {where_clause}
                GROUP BY 
                    DATE_FORMAT(c.fecha, '%%Y-%%m'),
                    DATE_FORMAT(c.fecha, '%%m/%%Y')
                ORDER BY 
                    DATE_FORMAT(c.fecha, '%%Y-%%m') ASC
            """
            
            # Consultas de validación: Solo ejecutar si DEBUG=True
            if settings.DEBUG:
                # Consulta de validación: Desglose de ingresos y egresos por tipo
                sql_validacion = f"""
                    SELECT 
                        DATE_FORMAT(c.fecha, '%%Y-%%m') AS mes,
                        DATE_FORMAT(c.fecha, '%%m/%%Y') AS mes_formato,
                        COUNT(*) as cantidad_movimientos,
                        SUM({campo_ingreso_real}) AS total_ingresos,
                        SUM({campo_egreso_real}) AS total_egresos,
                        SUM({campo_ingreso_real} - {campo_egreso_real}) AS neto,
                        -- Desglose por tipo de movimiento
                        GROUP_CONCAT(DISTINCT c.tipo ORDER BY c.tipo SEPARATOR ', ') as tipos_movimiento,
                        GROUP_CONCAT(DISTINCT c.tipo_comprobante ORDER BY c.tipo_comprobante SEPARATOR ', ') as tipos_comprobante
                    FROM caja c
                    WHERE {where_clause}
                    GROUP BY 
                        DATE_FORMAT(c.fecha, '%%Y-%%m'),
                        DATE_FORMAT(c.fecha, '%%m/%%Y')
                    ORDER BY 
                        DATE_FORMAT(c.fecha, '%%Y-%%m') ASC
                """
                try:
                    cursor.execute(sql_validacion, params)
                    validacion_rows = cursor.fetchall()
                    logger.info(f"🔍 [DEBUG] VALIDACIÓN - Desglose de movimientos por mes:")
                    for val_row in validacion_rows:
                        logger.info(f"   Mes: {val_row[1]} | Movimientos: {val_row[2]} | Ingresos: ${val_row[3]:,.2f} | Egresos: ${val_row[4]:,.2f} | Neto: ${val_row[5]:,.2f}")
                        logger.info(f"      Tipos: {val_row[6]}")
                        logger.info(f"      Comprobantes: {val_row[7]}")
                except Exception as val_error:
                    logger.warning(f"⚠️ Error en consulta de validación: {val_error}")
                
                # Consulta de validación detallada: Top 10 movimientos con mayor impacto
                sql_validacion_detalle = f"""
                    SELECT 
                        c.tipo,
                        c.tipo_comprobante,
                        c.fecha,
                        {campo_ingreso_real} as ingreso,
                        {campo_egreso_real} as egreso,
                        ({campo_ingreso_real} - {campo_egreso_real}) as neto,
                        c.detalle,
                        c.nro_comprobante
                    FROM caja c
                    WHERE {where_clause}
                    ORDER BY ABS({campo_ingreso_real} - {campo_egreso_real}) DESC
                    LIMIT 10
                """
                try:
                    cursor.execute(sql_validacion_detalle, params)
                    detalle_rows = cursor.fetchall()
                    logger.info(f"🔍 [DEBUG] VALIDACIÓN - Top 10 movimientos con mayor impacto:")
                    for det_row in detalle_rows:
                        logger.info(f"   Tipo: '{det_row[0]}' | Comp: '{det_row[1]}' | Fecha: {det_row[2]} | Ingreso: ${det_row[3]:,.2f} | Egreso: ${det_row[4]:,.2f} | Neto: ${det_row[5]:,.2f}")
                        logger.info(f"      Detalle: {det_row[6]} | Comp: {det_row[7]}")
                except Exception as det_error:
                    logger.warning(f"⚠️ Error en consulta de validación detallada: {det_error}")
                
                # Consulta de diagnóstico: Verificar suma directa de ingresos y egresos sin filtros
                sql_diag_suma_original = f"""
                    SELECT 
                        SUM(COALESCE(c.ingreso, 0)) AS suma_ingresos_directa,
                        SUM(COALESCE(c.egreso, 0)) AS suma_egresos_directa,
                        SUM(COALESCE(c.ingreso, 0) - COALESCE(c.egreso, 0)) AS suma_neto_directa,
                        COUNT(*) AS total_movimientos
                    FROM caja c
                    WHERE {where_clause}
                """
                try:
                    cursor.execute(sql_diag_suma_original, params)
                    diag_suma = cursor.fetchone()
                    logger.info(f"🔍 [DEBUG] DIAGNÓSTICO - Suma directa de campos ORIGINALES (sin corrección):")
                    logger.info(f"   Suma de INGRESOS (campo ingreso): ${diag_suma[0]:,.2f}")
                    logger.info(f"   Suma de EGRESOS (campo egreso): ${diag_suma[1]:,.2f}")
                    logger.info(f"   Suma NETO (ingreso - egreso): ${diag_suma[2]:,.2f}")
                    logger.info(f"   Total movimientos: {diag_suma[3]}")
                except Exception as diag_error:
                    logger.warning(f"⚠️ Error en diagnóstico de suma: {diag_error}")
            
            logger.info(f"🔍 Ejecutando consulta Cash Flow Waterfall: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, base_empresa={base_empresa}")
            logger.debug(f"SQL: {sql}")
            logger.debug(f"Params: {params}")
            
            try:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                logger.info(f"📊 Filas obtenidas de la consulta: {len(rows)}")
                if len(rows) > 0:
                    logger.debug(f"Primera fila de ejemplo: {rows[0]}")
                    # Log detallado de la primera fila para diagnóstico
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    if columns:
                        first_row_dict = dict(zip(columns, rows[0]))
                        logger.info(f"🔍 PRIMERA FILA - Valores obtenidos de la consulta SQL:")
                        logger.info(f"   operating_flow: {first_row_dict.get('operating_flow', 'N/A')}")
                        logger.info(f"   operating_ingresos: {first_row_dict.get('operating_ingresos', 'N/A')}")
                        logger.info(f"   operating_egresos: {first_row_dict.get('operating_egresos', 'N/A')}")
                        logger.info(f"   total_ingresos: {first_row_dict.get('total_ingresos', 'N/A')}")
                        logger.info(f"   total_egresos: {first_row_dict.get('total_egresos', 'N/A')}")
            except Exception as sql_error:
                logger.error(f"❌ Error SQL ejecutando consulta: {sql_error}")
                logger.error(f"SQL: {sql}")
                logger.error(f"Params: {params}")
                raise
            
            # Obtener nombres de columnas
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            logger.debug(f"Columnas obtenidas: {columns}")
            
            # Convertir resultados a formato waterfall
            data = []
            totals = {
                "saldo_inicial": float(saldo_inicial),  # Acumulado anterior (suma de todas las cajas)
                "operating_flow": 0.0,
                "operating_ingresos": 0.0,  # Ingresos operativos totales
                "operating_egresos": 0.0,  # Egresos operativos totales
                "investing_flow": 0.0,
                "financing_flow": 0.0,
                "cash_variation": 0.0,  # Se calculará como diferencia entre saldo final e inicial
            }
            
            # Agregar saldo inicial como primer elemento
            # El acumulado se calcula sumando las variaciones desde el saldo inicial del período
            acumulado_actual = saldo_inicial
            data.append({
                "period": "Saldo Inicial",
                "mes": "",
                "mes_formato": "",
                "operating_flow": 0.0,
                "investing_flow": 0.0,
                "financing_flow": 0.0,
                "cash_variation": 0.0,
                "cumulative": float(saldo_inicial),
                "type": "starting"
            })
            
            # Procesar cada mes
            logger.info(f"🔄 Procesando {len(rows)} períodos...")
            
            # Verificar si hay una inconsistencia: si operating_flow es negativo pero operating_ingresos es 0
            # y operating_egresos es positivo, podría indicar que los campos están intercambiados
            # Obtener totales de referencia para validación
            total_ingresos_ref = 0.0
            total_egresos_ref = 0.0
            for row in rows:
                row_dict = dict(zip(columns, row))
                total_ingresos_ref += float(row_dict.get("total_ingresos", 0) or 0)
                total_egresos_ref += float(row_dict.get("total_egresos", 0) or 0)
            
            logger.info(f"🔍 VALIDACIÓN - Totales de referencia:")
            logger.info(f"   total_ingresos (campo ingreso): ${total_ingresos_ref:,.2f}")
            logger.info(f"   total_egresos (campo egreso): ${total_egresos_ref:,.2f}")
            
            for row in rows:
                row_dict = dict(zip(columns, row))
                
                operating_flow = float(row_dict.get("operating_flow", 0) or 0)
                operating_ingresos = float(row_dict.get("operating_ingresos", 0) or 0)
                operating_egresos = float(row_dict.get("operating_egresos", 0) or 0)
                total_ingresos_row = float(row_dict.get("total_ingresos", 0) or 0)
                total_egresos_row = float(row_dict.get("total_egresos", 0) or 0)
                investing_flow = float(row_dict.get("investing_flow", 0) or 0)
                financing_flow = float(row_dict.get("financing_flow", 0) or 0)
                cash_variation = operating_flow + investing_flow + financing_flow
                
                # Obtener el mes del período
                mes_periodo = row_dict.get("mes", "")
                
                # DIAGNÓSTICO: Si operating_ingresos es 0 pero total_ingresos_row es positivo,
                # significa que los movimientos están siendo excluidos incorrectamente
                if operating_ingresos == 0 and total_ingresos_row > 0:
                    logger.warning(f"⚠️ ADVERTENCIA en período {mes_periodo}: operating_ingresos=0 pero total_ingresos={total_ingresos_row:,.2f}")
                    logger.warning(f"   Esto sugiere que los movimientos están siendo excluidos incorrectamente de operating_ingresos")
                
                logger.debug(f"Período {row_dict.get('mes_formato', 'N/A')}: Op={operating_flow} (Ing=${operating_ingresos:,.2f}, Egr=${operating_egresos:,.2f}), Inv={investing_flow}, Fin={financing_flow}, Var={cash_variation}")
                logger.debug(f"   Referencia: total_ingresos={total_ingresos_row:,.2f}, total_egresos={total_egresos_row:,.2f}")
                
                # IMPORTANTE: El acumulado se calcula sumando las variaciones desde el saldo inicial
                # No se usa el saldo real de la base de datos porque eso incluiría todo el historial
                # El acumulado debe reflejar: Saldo Inicial + Suma de Variaciones hasta este mes
                acumulado_actual += cash_variation
                logger.debug(f"Acumulado para {mes_periodo}: ${acumulado_actual:,.2f} (Saldo Inicial ${saldo_inicial:,.2f} + Variaciones acumuladas)")
                
                totals["operating_flow"] += operating_flow
                totals["operating_ingresos"] += operating_ingresos
                totals["operating_egresos"] += operating_egresos
                totals["investing_flow"] += investing_flow
                totals["financing_flow"] += financing_flow
                # Guardar la suma de movimientos para referencia, pero la variación real se calculará después
                if "cash_variation_sum_movements" not in totals:
                    totals["cash_variation_sum_movements"] = 0.0
                totals["cash_variation_sum_movements"] += cash_variation
                
                data.append({
                    "period": row_dict.get("mes_formato", ""),
                    "mes": row_dict.get("mes", ""),
                    "mes_formato": row_dict.get("mes_formato", ""),
                    "operating_flow": operating_flow,
                    "investing_flow": investing_flow,
                    "financing_flow": financing_flow,
                    "cash_variation": cash_variation,
                    "cumulative": float(acumulado_actual),
                    "type": "period"
                })
            
            # SALDO FINAL: Debe calcularse como Saldo Inicial + Variación de Caja
            # Según los estándares de estados de flujo de efectivo:
            # Saldo Final = Saldo Inicial + (Operating Flow + Investing Flow + Financing Flow)
            # El acumulado_actual ya contiene este cálculo: saldo_inicial + suma de variaciones
            saldo_final_mostrar = acumulado_actual
            
            # Validación: Comparar con el saldo real de la base de datos para referencia
            # (pero no usarlo para el cálculo, ya que puede incluir transferencias entre cajas)
            if id_cajas_int and len(id_cajas_int) > 0:
                # Si hay caja(s) específica(s), obtener el saldo de esas cajas para validación
                if len(id_cajas_int) == 1:
                    sql_saldo_final_validacion = """
                        SELECT c.saldo
                        FROM caja c
                        WHERE c.fecha <= %s
                            AND c.anulado = 'No'
                            AND (c.id_caja_abm_origen = %s OR c.id_caja_abm_destino = %s)
                        ORDER BY c.fecha DESC, c.codigo_movimiento DESC LIMIT 1
                    """
                    params_saldo_final = [fecha_fin, id_cajas_int[0], id_cajas_int[0]]
                else:
                    # Múltiples cajas: sumar los últimos saldos de cada una
                    placeholders = ",".join(["%s"] * len(id_cajas_int))
                    sql_saldo_final_validacion = f"""
                        SELECT COALESCE(SUM(saldo_por_caja), 0) as saldo_total
                        FROM (
                            SELECT 
                                DISTINCT c.id_caja_abm_origen,
                                COALESCE((
                                    SELECT c2.saldo 
                                    FROM caja c2 
                                    WHERE c2.id_caja_abm_origen = c.id_caja_abm_origen
                                      AND c2.anulado = 'No'
                                      AND c2.fecha <= %s
                                      AND c2.id_caja_abm_origen IN ({placeholders})
                                    ORDER BY c2.fecha DESC, c2.codigo_movimiento DESC 
                                    LIMIT 1
                                ), 0) as saldo_por_caja
                            FROM caja c
                            WHERE c.anulado = 'No'
                              AND c.id_caja_abm_origen IN ({placeholders})
                            GROUP BY c.id_caja_abm_origen
                        ) as saldos_cajas
                    """
                    params_saldo_final = [fecha_fin] + id_cajas_int + id_cajas_int
            else:
                # Si vemos todas las cajas, sumar los últimos saldos de cada caja para validación
                sql_saldo_final_validacion = """
                    SELECT COALESCE(SUM(saldo_por_caja), 0) as saldo_total
                    FROM (
                        SELECT 
                            DISTINCT c.id_caja_abm_origen,
                            COALESCE((
                                SELECT c2.saldo 
                                FROM caja c2 
                                WHERE c2.id_caja_abm_origen = c.id_caja_abm_origen
                                  AND c2.anulado = 'No'
                                  AND c2.fecha <= %s
                                ORDER BY c2.fecha DESC, c2.codigo_movimiento DESC 
                                LIMIT 1
                            ), 0) as saldo_por_caja
                        FROM caja c
                        WHERE c.anulado = 'No'
                        GROUP BY c.id_caja_abm_origen
                    ) as saldos_cajas
                """
                params_saldo_final = [fecha_fin]
            
            try:
                cursor.execute(sql_saldo_final_validacion, params_saldo_final)
                saldo_final_row = cursor.fetchone()
                saldo_final_real = float(saldo_final_row[0]) if saldo_final_row and saldo_final_row[0] else None
                if saldo_final_real is not None:
                    logger.info(f"💰 Saldo final calculado (Inicial + Variación): ${saldo_final_mostrar:,.2f}")
                    logger.info(f"💰 Saldo final real (suma de cajas en BD): ${saldo_final_real:,.2f}")
                    diferencia = abs(saldo_final_mostrar - saldo_final_real)
                    if diferencia > 1.0:
                        logger.info(f"ℹ️ NOTA: Diferencia de ${diferencia:,.2f} entre saldo calculado y saldo real")
                        logger.info(f"   Esto puede deberse a transferencias entre cajas que se cancelan en los flujos pero afectan los saldos individuales")
                        logger.info(f"   Usando saldo calculado (Inicial + Variación) para mantener consistencia con el estado de flujo de efectivo")
            except Exception as e:
                logger.warning(f"⚠️ Error calculando saldo final para validación: {e}")
                # Continuar con saldo_final_mostrar = acumulado_actual
            
            # Agregar saldo final
            # NOTA: El acumulado del saldo final debe ser el acumulado calculado (saldo_inicial + variaciones)
            # No el saldo real de la base de datos, para mantener consistencia con el resto del reporte
            data.append({
                "period": "Saldo Final",
                "mes": "",
                "mes_formato": "",
                "operating_flow": 0.0,
                "investing_flow": 0.0,
                "financing_flow": 0.0,
                "cash_variation": 0.0,
                "cumulative": float(acumulado_actual),
                "type": "ending"
            })
            
            # Agregar saldo final a los totals (usar el saldo real)
            totals["saldo_final"] = float(saldo_final_mostrar)
            
            # VARIACIÓN DE CAJA: Debe ser la suma de los flujos (operating + investing + financing)
            # Esto representa la variación neta de efectivo generada por las actividades operativas,
            # de inversión y de financiamiento durante el período
            variacion_por_flujos = totals["operating_flow"] + totals["investing_flow"] + totals["financing_flow"]
            totals["cash_variation"] = variacion_por_flujos
            
            # Validación: La variación por flujos debería coincidir con la diferencia de saldos
            # (excepto cuando hay transferencias entre cajas que se cancelan en los flujos pero afectan saldos)
            variacion_por_saldos = saldo_final_mostrar - saldo_inicial
            diferencia = abs(variacion_por_flujos - variacion_por_saldos)
            if diferencia > 0.01:
                logger.info(f"ℹ️ NOTA: Variación por flujos (${variacion_por_flujos:,.2f}) difiere de variación por saldos (${variacion_por_saldos:,.2f})")
                logger.info(f"   Diferencia: ${diferencia:,.2f} (probablemente por transferencias entre cajas)")
                logger.info(f"   Usando variación por flujos para cash_variation (estándar de estados de flujo de efectivo)")
            
            logger.info(f"✅ Consulta ejecutada: {len(data)} períodos obtenidos")
            logger.info(f"💰 Totales: Saldo Inicial={totals['saldo_inicial']}, Operating={totals['operating_flow']}, Investing={totals['investing_flow']}, Financing={totals['financing_flow']}, Variación={totals['cash_variation']}, Saldo Final={totals['saldo_final']}")
            logger.info(f"💵 Saldo inicial: ${saldo_inicial:,.2f}, Saldo final: ${saldo_final_mostrar:,.2f}")
            
            # Validación del cálculo: Verificar consistencia entre diferentes métodos de cálculo
            variacion_por_saldos = saldo_final_mostrar - saldo_inicial
            variacion_suma_movimientos = totals.get('cash_variation_sum_movements', variacion_por_flujos)
            logger.info(f"🔍 VALIDACIÓN DE CÁLCULO:")
            logger.info(f"   Saldo inicial: ${saldo_inicial:,.2f}")
            logger.info(f"   Saldo final: ${saldo_final_mostrar:,.2f}")
            logger.info(f"   Variación por flujos (Op+Inv+Fin): ${variacion_por_flujos:,.2f}")
            logger.info(f"   Variación por saldos (final - inicial): ${variacion_por_saldos:,.2f}")
            logger.info(f"   Variación por suma de movimientos: ${variacion_suma_movimientos:,.2f}")
            logger.info(f"   Diferencia entre métodos: ${abs(variacion_por_flujos - variacion_por_saldos):,.2f}")
            if abs(variacion_por_flujos - variacion_por_saldos) > 0.01:
                logger.info(f"ℹ️ NOTA: La diferencia se debe a transferencias entre cajas que se cancelan en los flujos pero afectan los saldos")
                logger.info(f"   Usando variación por flujos para cash_variation (estándar de estados de flujo de efectivo)")
            
            # Registrar log de ejecución
            duration = (timezone.now() - started_at).total_seconds() * 1000
            from core.models import UsuarioExtendido
            executed_by_user = None
            if isinstance(self.user, UsuarioExtendido) and getattr(self.user, "is_authenticated", False):
                executed_by_user = self.user
            
            ReportExecutionLog.objects.create(
                report=report,
                executed_by=executed_by_user,
                status="success",
                filters_snapshot=filters,
                duration_ms=int(duration),
                notes=f"Consulta ejecutada exitosamente. {len(data)} períodos obtenidos.",
            )
            
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                    "tz": "America/Argentina/Buenos_Aires",
                },
                data=data,
                totals=totals,
                notes=[
                    f"Período: {self._format_date(fecha_inicio)} a {self._format_date(fecha_fin)}",
                    f"Saldo inicial: ${saldo_inicial:,.2f}",
                    f"Saldo final: ${saldo_final_mostrar:,.2f}",
                    f"Variación neta: ${totals['cash_variation']:,.2f}",
                ],
            )
                
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"❌ Error ejecutando consulta Cash Flow Waterfall: {e}")
            logger.error(f"Traceback completo:\n{error_traceback}")
            
            # Conexión cerrada automáticamente por el context manager
            
            duration = (timezone.now() - started_at).total_seconds() * 1000
            from core.models import UsuarioExtendido
            executed_by_user = None
            if isinstance(self.user, UsuarioExtendido) and getattr(self.user, "is_authenticated", False):
                executed_by_user = self.user
            
            try:
                ReportExecutionLog.objects.create(
                    report=report,
                    executed_by=executed_by_user,
                    status="error",
                    filters_snapshot=filters,
                    duration_ms=int(duration),
                    notes=f"Error: {str(e)}",
                )
            except:
                pass
            
            # Re-lanzar la excepción para que la API view la capture
            raise

    def _run_cash_flow_detailed_movements(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """
        Retorna movimientos individuales de caja con información completa:
        - Fecha, Tipo, Categoría, Cliente/Proveedor, Medio, Importe, Cuenta, Flujo
        """
        started_at = timezone.now()
        
        try:
            filters = payload.get("filters", {})
            base_empresa = payload.get("base_empresa")
            fecha_inicio, fecha_fin = self._resolve_period_dates(filters)
            if not fecha_inicio or not fecha_fin:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
                )
            if not base_empresa:
                if hasattr(self.user, 'base_empresa'):
                    base_empresa = self.user.base_empresa
            if not base_empresa:
                base_empresa = getattr(settings, 'DEFAULT_BASE_EMPRESA', None)
            if not base_empresa:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se pudo determinar la base de datos de la empresa."],
                )
            
            # Obtener filtros opcionales
            id_caja = filters.get("id_caja")
            if isinstance(id_caja, str):
                id_caja = [id_caja] if id_caja else []
            elif not isinstance(id_caja, list):
                id_caja = []
            
            # Obtener pool de conexiones MySQL (reutiliza conexiones existentes)
            pool = get_mysql_pool()
            
            # Usar connection pool - todas las consultas dentro de este bloque
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
            
            # Construir WHERE conditions
            where_conditions = [
                "c.fecha >= %s",
                "c.fecha <= %s",
                "c.anulado = 'No'"
            ]
            params = [fecha_inicio, fecha_fin]
            
            # Filtro de caja(s)
            id_cajas_int = []
            if id_caja and len(id_caja) > 0:
                try:
                    id_cajas_int = [int(c) for c in id_caja if c]
                    if id_cajas_int:
                        if len(id_cajas_int) == 1:
                            where_conditions.append("(c.id_caja_abm_origen = %s OR c.id_caja_abm_destino = %s)")
                            params.extend([id_cajas_int[0], id_cajas_int[0]])
                        else:
                            placeholders = ",".join(["%s"] * len(id_cajas_int))
                            where_conditions.append(f"(c.id_caja_abm_origen IN ({placeholders}) OR c.id_caja_abm_destino IN ({placeholders}))")
                            params.extend(id_cajas_int + id_cajas_int)
                except (ValueError, TypeError):
                    id_cajas_int = []
            
            where_clause = " AND ".join(where_conditions)
            
            # Función auxiliar para clasificar flujo y subcategoría
            # Esta lógica se aplicará en Python después de obtener los datos
            
            # Consulta SQL principal con todos los JOINs
            sql = f"""
                SELECT 
                    c.id_caja,
                    c.fecha,
                    c.tipo_comprobante,
                    c.tipo,
                    c.nro_comprobante,
                    c.nro_comp_busq,
                    c.moneda,
                    COALESCE(c.ingreso, 0) as ingreso,
                    COALESCE(c.egreso, 0) as egreso,
                    (COALESCE(c.ingreso, 0) - COALESCE(c.egreso, 0)) as importe_neto,
                    c.codigo_movimiento,
                    c.codigo_cliente,
                    c.codigo_prov,
                    c.tipo_cp,
                    c.detalle,
                    c.cod_gasto,
                    c.cod_sucursal,
                    c.id_caja_abm_origen,
                    c.id_caja_abm_destino,
                    c.nro_doc,
                    c.cod_vendedor,
                    -- Cliente
                    COALESCE(cli.nombre_cliente, '') as nombre_cliente,
                    -- Proveedor
                    COALESCE(prov.Nombre, '') as nombre_proveedor,
                    -- Caja origen
                    COALESCE(caja_origen.nombre_caja, '') as caja_origen_nombre,
                    COALESCE(caja_origen.tipo_caja, '') as caja_origen_tipo,
                    -- Caja destino
                    COALESCE(caja_destino.nombre_caja, '') as caja_destino_nombre,
                    COALESCE(caja_destino.tipo_caja, '') as caja_destino_tipo,
                    -- Gasto
                    COALESCE(g.Nombre, '') as gasto_nombre,
                    COALESCE(g.id_gastos_grupo, 0) as id_gastos_grupo,
                    -- Grupo de gasto
                    COALESCE(gg.nombre_gastos_grupo, '') as grupo_gasto_nombre,
                    -- Sucursal
                    COALESCE(s.nombre_sucursal, '') as nombre_sucursal
                FROM caja c
                LEFT JOIN cliente cli ON cli.Codigo = c.codigo_cliente
                LEFT JOIN proveedor prov ON prov.Codigo = c.codigo_prov
                LEFT JOIN caja_abm caja_origen ON caja_origen.id_caja = c.id_caja_abm_origen
                LEFT JOIN caja_abm caja_destino ON caja_destino.id_caja = c.id_caja_abm_destino
                LEFT JOIN gastos g ON g.Codigo = c.cod_gasto
                LEFT JOIN gastos_grupo gg ON gg.id_gastos_grupo = g.id_gastos_grupo
                LEFT JOIN sucursales s ON s.id_sucursal = c.cod_sucursal
                WHERE {where_clause}
                ORDER BY c.fecha DESC, c.codigo_movimiento DESC
            """
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Procesar resultados y clasificar
            data = []
            for row in rows:
                # Extraer datos de la fila
                id_caja_val = row[0]
                fecha = row[1]
                tipo_comprobante = row[2] or ""
                tipo = row[3] or ""
                nro_comprobante = row[4] or ""
                nro_comp_busq = row[5] or ""
                moneda = row[6] or "Pesos"
                ingreso = float(row[7] or 0)
                egreso = float(row[8] or 0)
                importe_neto = float(row[9] or 0)
                codigo_movimiento = row[10]
                codigo_cliente = row[11]
                codigo_prov = row[12]
                tipo_cp = row[13] or ""
                detalle = row[14] or ""
                cod_gasto = row[15]
                cod_sucursal = row[16]
                id_caja_abm_origen = row[17]
                id_caja_abm_destino = row[18]
                nro_doc = row[19] or ""
                cod_vendedor = row[20]
                nombre_cliente = row[21] or ""
                nombre_proveedor = row[22] or ""
                caja_origen_nombre = row[23] or ""
                caja_origen_tipo = row[24] or ""
                caja_destino_nombre = row[25] or ""
                caja_destino_tipo = row[26] or ""
                gasto_nombre = row[27] or ""
                id_gastos_grupo = row[28]
                grupo_gasto_nombre = row[29] or ""
                nombre_sucursal = row[30] or ""
                
                # Clasificar flujo y subcategoría
                flujo_tipo, flujo_subcategoria = self._classify_movement(
                    tipo_comprobante, tipo, ingreso, egreso, tipo_cp, cod_gasto, gasto_nombre, grupo_gasto_nombre
                )
                
                # Determinar medio de pago desde tipo_comprobante
                medio_pago = self._get_payment_method(tipo_comprobante, tipo)
                
                # Determinar contraparte (cliente o proveedor)
                contraparte = nombre_cliente if tipo_cp == "Cliente" else nombre_proveedor
                if not contraparte:
                    contraparte = ""
                
                # Determinar cuenta (caja origen o destino)
                cuenta = caja_origen_nombre if caja_origen_nombre else (caja_destino_nombre if caja_destino_nombre else "")
                
                # Formatear fecha
                fecha_str = fecha.strftime("%d/%m/%Y") if fecha else ""
                
                data.append({
                    "id_caja": id_caja_val,
                    "fecha": fecha_str,
                    "fecha_raw": fecha.strftime("%Y-%m-%d") if fecha else "",
                    "tipo_comprobante": tipo_comprobante,
                    "tipo": tipo,
                    "nro_comprobante": nro_comprobante,
                    "nro_comp_busq": nro_comp_busq,
                    "moneda": moneda,
                    "ingreso": ingreso,
                    "egreso": egreso,
                    "importe_neto": importe_neto,
                    "codigo_movimiento": codigo_movimiento,
                    "codigo_cliente": codigo_cliente,
                    "codigo_prov": codigo_prov,
                    "tipo_cp": tipo_cp,
                    "contraparte": contraparte,
                    "detalle": detalle,
                    "cod_gasto": cod_gasto,
                    "gasto_nombre": gasto_nombre,
                    "grupo_gasto_nombre": grupo_gasto_nombre,
                    "cod_sucursal": cod_sucursal,
                    "nombre_sucursal": nombre_sucursal,
                    "id_caja_abm_origen": id_caja_abm_origen,
                    "caja_origen_nombre": caja_origen_nombre,
                    "caja_origen_tipo": caja_origen_tipo,
                    "id_caja_abm_destino": id_caja_abm_destino,
                    "caja_destino_nombre": caja_destino_nombre,
                    "caja_destino_tipo": caja_destino_tipo,
                    "cuenta": cuenta,
                    "medio_pago": medio_pago,
                    "nro_doc": nro_doc,
                    "cod_vendedor": cod_vendedor,
                    "flujo_tipo": flujo_tipo,
                    "flujo_subcategoria": flujo_subcategoria,
                })
            
            
            # Calcular totales
            totals = {
                "total_movimientos": len(data),
                "total_ingresos": sum(m["ingreso"] for m in data),
                "total_egresos": sum(m["egreso"] for m in data),
                "total_neto": sum(m["importe_neto"] for m in data),
            }
            
            # Registrar log
            duration = (timezone.now() - started_at).total_seconds() * 1000
            from core.models import UsuarioExtendido
            executed_by_user = None
            if isinstance(self.user, UsuarioExtendido) and getattr(self.user, "is_authenticated", False):
                executed_by_user = self.user
            
            ReportExecutionLog.objects.create(
                report=report,
                executed_by=executed_by_user,
                status="success",
                filters_snapshot=filters,
                duration_ms=int(duration),
                notes=f"Consulta ejecutada exitosamente. {len(data)} movimientos obtenidos.",
            )
            
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                    "tz": "America/Argentina/Buenos_Aires",
                },
                data=data,
                totals=totals,
                notes=[
                    f"Período: {self._format_date(fecha_inicio)} a {self._format_date(fecha_fin)}",
                    f"Total movimientos: {len(data)}",
                ],
            )
                
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"❌ Error ejecutando consulta de movimientos detallados: {e}")
            logger.error(f"Traceback completo:\n{error_traceback}")
            
            # Conexión cerrada automáticamente por el context manager
            
            duration = (timezone.now() - started_at).total_seconds() * 1000
            from core.models import UsuarioExtendido
            executed_by_user = None
            if isinstance(self.user, UsuarioExtendido) and getattr(self.user, "is_authenticated", False):
                executed_by_user = self.user
            
            try:
                ReportExecutionLog.objects.create(
                    report=report,
                    executed_by=executed_by_user,
                    status="error",
                    filters_snapshot=filters,
                    duration_ms=int(duration),
                    notes=f"Error: {str(e)}",
                )
            except:
                pass
            
            raise
    
    def _run_cash_flow_by_account(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """
        Retorna flujo de caja desglosado por cada caja/banco.
        Incluye: nombre_caja, saldo_inicial, saldo_final, flujos por tipo
        """
        started_at = timezone.now()
        
        try:
            filters = payload.get("filters", {})
            base_empresa = payload.get("base_empresa")
            fecha_inicio, fecha_fin = self._resolve_period_dates(filters)
            if not fecha_inicio or not fecha_fin:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
                )
            if not base_empresa:
                if hasattr(self.user, 'base_empresa'):
                    base_empresa = self.user.base_empresa
            if not base_empresa:
                base_empresa = getattr(settings, 'DEFAULT_BASE_EMPRESA', None)
            if not base_empresa:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se pudo determinar la base de datos de la empresa."],
                )
            
            # Obtener filtros opcionales
            id_caja = filters.get("id_caja")
            if isinstance(id_caja, str):
                id_caja = [id_caja] if id_caja else []
            elif not isinstance(id_caja, list):
                id_caja = []
            
            # Obtener pool de conexiones MySQL (reutiliza conexiones existentes)
            pool = get_mysql_pool()
            
            # Usar connection pool - todas las consultas dentro de este bloque
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
            
            # Construir WHERE conditions
            where_conditions = [
                "c.fecha >= %s",
                "c.fecha <= %s",
                "c.anulado = 'No'"
            ]
            params = [fecha_inicio, fecha_fin]
            
            # Filtro de caja(s) - si se especifica, solo mostrar esas cajas
            id_cajas_int = []
            if id_caja and len(id_caja) > 0:
                try:
                    id_cajas_int = [int(c) for c in id_caja if c]
                except (ValueError, TypeError):
                    id_cajas_int = []
            
            # Obtener todas las cajas que tienen movimientos en el período
            # Usamos UNION para obtener tanto cajas origen como destino
            sql_cajas = """
                SELECT DISTINCT 
                    COALESCE(caja_origen.id_caja, caja_destino.id_caja) as id_caja,
                    COALESCE(caja_origen.nombre_caja, caja_destino.nombre_caja, 'Sin Caja') as nombre_caja,
                    COALESCE(caja_origen.tipo_caja, caja_destino.tipo_caja, '') as tipo_caja
                FROM caja c
                LEFT JOIN caja_abm caja_origen ON caja_origen.id_caja = c.id_caja_abm_origen
                LEFT JOIN caja_abm caja_destino ON caja_destino.id_caja = c.id_caja_abm_destino
                WHERE c.fecha >= %s
                    AND c.fecha <= %s
                    AND c.anulado = 'No'
                    AND (c.id_caja_abm_origen IS NOT NULL OR c.id_caja_abm_destino IS NOT NULL)
            """
            params_cajas = [fecha_inicio, fecha_fin]
            
            if id_cajas_int:
                placeholders = ",".join(["%s"] * len(id_cajas_int))
                sql_cajas += f" AND (c.id_caja_abm_origen IN ({placeholders}) OR c.id_caja_abm_destino IN ({placeholders}))"
                params_cajas.extend(id_cajas_int + id_cajas_int)
            
            sql_cajas += " ORDER BY nombre_caja"
            
            cursor.execute(sql_cajas, params_cajas)
            cajas_rows = cursor.fetchall()
            
            if not cajas_rows:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se encontraron cajas con movimientos en el período seleccionado."],
                )
            
            # Para cada caja, calcular saldos y flujos
            data = []
            totals = {
                "total_saldo_inicial": 0.0,
                "total_saldo_final": 0.0,
                "total_operating_flow": 0.0,
                "total_investing_flow": 0.0,
                "total_financing_flow": 0.0,
                "total_cash_variation": 0.0,
            }
            
            for caja_row in cajas_rows:
                id_caja_val = caja_row[0]
                nombre_caja = caja_row[1] or "Sin Caja"
                tipo_caja = caja_row[2] or ""
                
                # Obtener saldo inicial de esta caja (último saldo antes de fecha_inicio)
                sql_saldo_inicial = """
                    SELECT c.saldo
                    FROM caja c
                    WHERE c.fecha < %s
                        AND c.anulado = 'No'
                        AND c.id_caja_abm_origen = %s
                    ORDER BY c.fecha DESC, c.codigo_movimiento DESC
                    LIMIT 1
                """
                cursor.execute(sql_saldo_inicial, [fecha_inicio, id_caja_val])
                saldo_inicial_row = cursor.fetchone()
                saldo_inicial = float(saldo_inicial_row[0]) if saldo_inicial_row and saldo_inicial_row[0] else 0.0
                
                # Obtener saldo final de esta caja (último saldo hasta fecha_fin)
                sql_saldo_final = """
                    SELECT c.saldo
                    FROM caja c
                    WHERE c.fecha <= %s
                        AND c.anulado = 'No'
                        AND c.id_caja_abm_origen = %s
                    ORDER BY c.fecha DESC, c.codigo_movimiento DESC
                    LIMIT 1
                """
                cursor.execute(sql_saldo_final, [fecha_fin, id_caja_val])
                saldo_final_row = cursor.fetchone()
                saldo_final = float(saldo_final_row[0]) if saldo_final_row and saldo_final_row[0] else 0.0
                
                # Calcular flujos para esta caja en el período
                # IMPORTANTE: Para mantener consistencia con la vista consolidada, cada movimiento
                # debe contarse solo una vez en el total. Por lo tanto:
                # - Si la caja es ORIGEN: contar el movimiento completo (ingreso - egreso) como afecta a esa caja
                # - Si la caja es DESTINO: contar el movimiento completo (ingreso - egreso) como afecta a esa caja
                # - Las transferencias se excluyen (se cancelan entre cajas)
                # - Los movimientos con origen y destino diferentes se cuentan en ambas cajas, pero
                #   en la vista consolidada se cuenta una sola vez, por lo que debemos usar la misma lógica:
                #   contar solo movimientos donde la caja es ORIGEN (el saldo se actualiza en la caja origen)
                where_caja = [
                    "c.fecha >= %s",
                    "c.fecha <= %s",
                    "c.anulado = 'No'",
                    "c.id_caja_abm_origen = %s"  # Solo contar movimientos donde esta caja es ORIGEN
                ]
                params_caja = [fecha_inicio, fecha_fin, id_caja_val]
                
                # Excluir transferencias entre cajas (se cancelan)
                # Excluir cierres de caja (movimientos internos)
                # Usar la misma lógica que en la vista consolidada
                sql_flujos = f"""
                    SELECT 
                        SUM(CASE 
                            WHEN c.tipo LIKE '%%Cierre de Caja%%' OR c.tipo LIKE '%%Transferencia de Fondos%%'
                            THEN 0
                            WHEN c.tipo LIKE '%%Inversión%%' OR c.tipo LIKE '%%Activo Fijo%%'
                            THEN 0
                            WHEN c.tipo LIKE '%%Préstamo%%' OR c.tipo LIKE '%%Aporte%%' OR c.tipo LIKE '%%Capital%%'
                            THEN 0
                            ELSE COALESCE(c.ingreso, 0) - COALESCE(c.egreso, 0)
                        END) AS operating_flow,
                        SUM(CASE 
                            WHEN c.tipo LIKE '%%Cierre de Caja%%' OR c.tipo LIKE '%%Transferencia de Fondos%%'
                            THEN 0
                            WHEN c.tipo LIKE '%%Inversión%%' OR c.tipo LIKE '%%Activo Fijo%%'
                            THEN COALESCE(c.ingreso, 0) - COALESCE(c.egreso, 0)
                            ELSE 0
                        END) AS investing_flow,
                        SUM(CASE 
                            WHEN c.tipo LIKE '%%Cierre de Caja%%' OR c.tipo LIKE '%%Transferencia de Fondos%%'
                            THEN 0
                            WHEN c.tipo LIKE '%%Préstamo%%' OR c.tipo LIKE '%%Aporte%%' OR c.tipo LIKE '%%Capital%%'
                            THEN COALESCE(c.ingreso, 0) - COALESCE(c.egreso, 0)
                            ELSE 0
                        END) AS financing_flow
                    FROM caja c
                    WHERE {' AND '.join(where_caja)}
                """
                
                cursor.execute(sql_flujos, params_caja)
                flujos_row = cursor.fetchone()
                
                operating_flow = float(flujos_row[0] or 0) if flujos_row else 0.0
                investing_flow = float(flujos_row[1] or 0) if flujos_row else 0.0
                financing_flow = float(flujos_row[2] or 0) if flujos_row else 0.0
                
                # La variación de caja es la suma de los flujos (consistente con el reporte principal)
                cash_variation = operating_flow + investing_flow + financing_flow
                
                # El saldo final calculado debe ser: saldo_inicial + cash_variation
                # Esto mantiene consistencia con el reporte principal y excluye transferencias entre cajas
                saldo_final_calculado = saldo_inicial + cash_variation
                
                # Agregar a datos
                data.append({
                    "id_caja": id_caja_val,
                    "caja_nombre": nombre_caja,
                    "caja_tipo": tipo_caja,
                    "saldo_inicial": saldo_inicial,
                    "saldo_final": saldo_final_calculado,  # Usar saldo calculado para consistencia
                    "saldo_final_real": saldo_final,  # Mantener saldo real de BD para referencia
                    "operating_flow": operating_flow,
                    "investing_flow": investing_flow,
                    "financing_flow": financing_flow,
                    "cash_variation": cash_variation,
                })
                
                # Acumular totales
                totals["total_saldo_inicial"] += saldo_inicial
                totals["total_saldo_final"] += saldo_final_calculado  # Usar saldo calculado
                totals["total_operating_flow"] += operating_flow
                totals["total_investing_flow"] += investing_flow
                totals["total_financing_flow"] += financing_flow
                totals["total_cash_variation"] += cash_variation
            
            
            # Registrar log
            duration = (timezone.now() - started_at).total_seconds() * 1000
            from core.models import UsuarioExtendido
            executed_by_user = None
            if isinstance(self.user, UsuarioExtendido) and getattr(self.user, "is_authenticated", False):
                executed_by_user = self.user
            
            ReportExecutionLog.objects.create(
                report=report,
                executed_by=executed_by_user,
                status="success",
                filters_snapshot=filters,
                duration_ms=int(duration),
                notes=f"Consulta ejecutada exitosamente. {len(data)} cajas obtenidas.",
            )
            
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                    "tz": "America/Argentina/Buenos_Aires",
                },
                data=data,
                totals=totals,
                notes=[
                    f"Período: {self._format_date(fecha_inicio)} a {self._format_date(fecha_fin)}",
                    f"Total cajas: {len(data)}",
                ],
            )
                
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"❌ Error ejecutando consulta de flujo por cuenta: {e}")
            logger.error(f"Traceback completo:\n{error_traceback}")
            
            # Conexión cerrada automáticamente por el context manager
            
            duration = (timezone.now() - started_at).total_seconds() * 1000
            from core.models import UsuarioExtendido
            executed_by_user = None
            if isinstance(self.user, UsuarioExtendido) and getattr(self.user, "is_authenticated", False):
                executed_by_user = self.user
            
            try:
                ReportExecutionLog.objects.create(
                    report=report,
                    executed_by=executed_by_user,
                    status="error",
                    filters_snapshot=filters,
                    duration_ms=int(duration),
                    notes=f"Error: {str(e)}",
                )
            except:
                pass
            
            raise
    
    def _classify_movement(self, tipo_comprobante, tipo, ingreso, egreso, tipo_cp, cod_gasto, gasto_nombre, grupo_gasto_nombre):
        """
        Clasifica un movimiento en flujo (operativo, inversión, financiamiento) y subcategoría.
        Retorna: (flujo_tipo, flujo_subcategoria)
        
        Basado en los tipos de comprobantes de ingresos y egresos definidos:
        - Ingresos: FA, FB, FC, FE, FM, REC, CHEQ, MCAJ (según contexto), TARJ, OMC, etc.
        - Egresos: FA, FB (compras), CHEQ, MCAJ (según contexto), OP, NCA, etc.
        """
        tipo_comp_upper = tipo_comprobante.upper() if tipo_comprobante else ""
        tipo_upper = tipo.upper() if tipo else ""
        tipo_lower = tipo.lower() if tipo else ""
        
        # OPERATIVO - INGRESOS
        if ingreso > 0:
            # Facturas de venta (FA, FB, FC, FE, FM)
            if tipo_comp_upper in ['FA', 'FB', 'FC', 'FE', 'FM']:
                return ('operativo', 'ingresos_ventas')
            # Cobranzas (REC, CHEQ cuando es cobranza)
            elif tipo_comp_upper in ['REC']:
                return ('operativo', 'ingresos_cobranzas')
            # CHEQ puede ser ingreso (cobranza) o egreso (pago)
            # Si hay cliente asociado, probablemente es cobranza
            elif tipo_comp_upper == 'CHEQ' and tipo_cp == 'Cliente':
                return ('operativo', 'ingresos_cobranzas')
            # MCAJ puede ser ingreso o egreso según el tipo
            # Si el tipo contiene palabras clave de ingreso
            elif tipo_comp_upper == 'MCAJ':
                if any(keyword in tipo_lower for keyword in ['cobro', 'cobranza', 'ingreso', 'deposito', 'depósito']):
                    return ('operativo', 'ingresos_cobranzas')
                elif 'cierre' in tipo_lower:
                    # Cierre de caja es un movimiento interno, pero si tiene ingreso, es operativo
                    return ('operativo', 'ingresos_otros')
                else:
                    return ('operativo', 'ingresos_otros')
            # Tarjeta (TARJ)
            elif tipo_comp_upper == 'TARJ':
                return ('operativo', 'ingresos_ventas')
            # Documento/Pagaré (OMC)
            elif tipo_comp_upper == 'OMC':
                return ('operativo', 'ingresos_cobranzas')
            # Intereses
            elif 'interes' in tipo_lower or 'interés' in tipo_lower:
                return ('operativo', 'ingresos_intereses')
            # Otros ingresos operativos
            else:
                return ('operativo', 'ingresos_otros')
        
        # OPERATIVO - EGRESOS
        elif egreso > 0:
            # Facturas de compra a proveedores (FA, FB cuando tipo_cp es Proveedor)
            if tipo_comp_upper in ['FA', 'FB'] and tipo_cp == 'Proveedor':
                return ('operativo', 'egresos_proveedores')
            # Pago Efectivo (OP)
            elif tipo_comp_upper == 'OP':
                # Puede ser pago a proveedor o gasto, verificar si hay proveedor asociado
                if tipo_cp == 'Proveedor':
                    return ('operativo', 'egresos_proveedores')
                else:
                    return ('operativo', 'egresos_otros')
            # CHEQ puede ser egreso (pago)
            elif tipo_comp_upper == 'CHEQ' and tipo_cp == 'Proveedor':
                return ('operativo', 'egresos_proveedores')
            elif tipo_comp_upper == 'CHEQ':
                return ('operativo', 'egresos_otros')
            # MCAJ puede ser egreso según el tipo
            elif tipo_comp_upper == 'MCAJ':
                if any(keyword in tipo_lower for keyword in ['pago', 'egreso', 'extraccion', 'extracción', 'entrega']):
                    if tipo_cp == 'Proveedor':
                        return ('operativo', 'egresos_proveedores')
                    else:
                        return ('operativo', 'egresos_otros')
                elif 'cierre' in tipo_lower:
                    # Cierre de caja es movimiento interno
                    return ('operativo', 'egresos_otros')
                else:
                    return ('operativo', 'egresos_otros')
            # Nota de Crédito de compra (NCA) - es un egreso negativo (reducción de deuda)
            elif tipo_comp_upper == 'NCA':
                return ('operativo', 'egresos_proveedores')
            # Gastos imputados (cod_gasto > 0)
            elif cod_gasto and cod_gasto > 0:
                # Clasificar por grupo de gasto si está disponible
                if grupo_gasto_nombre:
                    grupo_lower = grupo_gasto_nombre.lower()
                    if 'sueldo' in grupo_lower or 'salario' in grupo_lower:
                        return ('operativo', 'egresos_sueldos')
                    elif 'servicio' in grupo_lower:
                        return ('operativo', 'egresos_servicios')
                    elif 'impuesto' in grupo_lower or 'iva' in grupo_lower:
                        return ('operativo', 'egresos_impuestos')
                    else:
                        return ('operativo', 'egresos_gastos')
                # Si no hay grupo, intentar por nombre de gasto
                elif gasto_nombre:
                    gasto_lower = gasto_nombre.lower()
                    if 'sueldo' in gasto_lower or 'salario' in gasto_lower:
                        return ('operativo', 'egresos_sueldos')
                    elif 'servicio' in gasto_lower:
                        return ('operativo', 'egresos_servicios')
                    elif 'impuesto' in gasto_lower or 'iva' in gasto_lower:
                        return ('operativo', 'egresos_impuestos')
                    else:
                        return ('operativo', 'egresos_gastos')
                else:
                    return ('operativo', 'egresos_gastos')
            # Sueldos (por tipo)
            elif 'sueldo' in tipo_lower or 'salario' in tipo_lower:
                return ('operativo', 'egresos_sueldos')
            # Impuestos (por tipo)
            elif 'impuesto' in tipo_lower or 'iva' in tipo_lower:
                return ('operativo', 'egresos_impuestos')
            # Servicios (por tipo)
            elif 'servicio' in tipo_lower:
                return ('operativo', 'egresos_servicios')
            # Otros egresos operativos
            else:
                return ('operativo', 'egresos_otros')
        
        # INVERSIÓN (por ahora no hay movimientos de inversión identificados)
        # Se puede agregar lógica aquí si se identifican tipos específicos
        
        # FINANCIAMIENTO (por ahora no hay movimientos de financiamiento identificados)
        # Se puede agregar lógica aquí si se identifican tipos específicos
        
        # Por defecto, operativo
        return ('operativo', 'otros')
    
    def _get_payment_method(self, tipo_comprobante, tipo):
        """
        Determina el medio de pago desde tipo_comprobante y tipo.
        Basado en los tipos de comprobantes de administraNET.
        """
        tipo_comp_upper = tipo_comprobante.upper() if tipo_comprobante else ""
        tipo_comp_lower = tipo_comprobante.lower() if tipo_comprobante else ""
        tipo_lower = tipo.lower() if tipo else ""
        
        # CHEQ = Cheque
        if tipo_comp_upper == 'CHEQ' or 'cheque' in tipo_comp_lower or 'cheq' in tipo_comp_lower:
            return "Cheque"
        # TARJ = Tarjeta
        elif tipo_comp_upper == 'TARJ' or 'tarjeta' in tipo_lower or 'tarj' in tipo_comp_lower:
            return "Tarjeta"
        # MCAJ puede ser varios medios según el tipo
        elif tipo_comp_upper == 'MCAJ':
            if 'efectivo' in tipo_lower:
                return "Efectivo"
            elif 'cheque' in tipo_lower or 'cheq' in tipo_lower:
                return "Cheque"
            elif 'transferencia' in tipo_lower or 'transferencia' in tipo_lower:
                return "Transferencia"
            elif 'deposito' in tipo_lower or 'depósito' in tipo_lower:
                return "Depósito"
            else:
                return "Movimiento de Caja"
        # REC = Recibo (generalmente efectivo)
        elif tipo_comp_upper == 'REC':
            if 'efectivo' in tipo_lower:
                return "Efectivo"
            elif 'cheque' in tipo_lower or 'cheq' in tipo_lower:
                return "Cheque"
            else:
                return "Recibo"
        # OP = Orden de Pago (puede ser efectivo o cheque)
        elif tipo_comp_upper == 'OP':
            if 'efectivo' in tipo_lower:
                return "Efectivo"
            elif 'cheque' in tipo_lower or 'cheq' in tipo_lower:
                return "Cheque"
            else:
                return "Orden de Pago"
        # Efectivo (por tipo)
        elif 'efectivo' in tipo_lower:
            return "Efectivo"
        # Transferencia (por tipo)
        elif 'transferencia' in tipo_lower:
            return "Transferencia"
        # Depósito (por tipo)
        elif 'deposito' in tipo_lower or 'depósito' in tipo_lower:
            return "Depósito"
        # Por defecto, usar el tipo_comprobante o "Otro"
        else:
            return tipo_comprobante if tipo_comprobante else "Otro"
    
    def _run_uninvoiced_remitos(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """
        Ejecuta la consulta SQL para el reporte de Remitos no facturados.
        Muestra remitos (TipoComprobante = REM) que están en estado Pendiente y no han sido anulados.
        """
        started_at = timezone.now()
        
        try:
            filters = payload.get("filters", {})
            base_empresa = filters.get("base_empresa")
            fecha_inicio, fecha_fin = self._resolve_period_dates(filters)
            if not fecha_inicio or not fecha_fin:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
                )
            if not base_empresa:
                if hasattr(self.user, 'base_empresa'):
                    base_empresa = self.user.base_empresa
            if not base_empresa:
                base_empresa = getattr(settings, 'DEFAULT_BASE_EMPRESA', None)
            if not base_empresa:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se pudo determinar la base de datos de la empresa. Asegúrese de estar logueado correctamente."],
                )
            puntos_venta = filters.get("punto_venta", [])
            if isinstance(puntos_venta, str):
                puntos_venta = [puntos_venta] if puntos_venta else []
            elif not isinstance(puntos_venta, list):
                puntos_venta = []
            
            sucursales = filters.get("sucursales", [])
            if isinstance(sucursales, str):
                sucursales = [sucursales] if sucursales else []
            elif not isinstance(sucursales, list):
                sucursales = []
            
            # Conectar a la base de datos MySQL de administraNET
            mysql_config = settings.DATABASES['mysql']
            
            import MySQLdb
            try:
                conn = MySQLdb.connect(
                    host=mysql_config['HOST'],
                    port=int(mysql_config['PORT']),
                    user=mysql_config['USER'],
                    passwd=mysql_config['PASSWORD'],
                    db=base_empresa,
                    charset='latin1'
                )
                cursor = conn.cursor()
            except Exception as conn_error:
                logger.error(f"❌ Error conectando a MySQL ({base_empresa}): {conn_error}")
                raise
            
            # Construir condiciones WHERE
            where_conditions = [
                "cp.Fecha >= %s",
                "cp.Fecha <= %s",
                "cp.TipoComprobante = 'REM'",
                "cp.Anulado = 'No'",
                "cp.Estado = 'Pendiente'"
            ]
            params = [fecha_inicio, fecha_fin]
            
            # Filtro de punto de venta
            if puntos_venta:
                puntos_venta_ints = []
                for pv in puntos_venta:
                    try:
                        puntos_venta_ints.append(int(pv))
                    except (ValueError, TypeError):
                        continue
                if puntos_venta_ints:
                    placeholders = ','.join(['%s'] * len(puntos_venta_ints))
                    where_conditions.append(f"cp.id_pv IN ({placeholders})")
                    params.extend(puntos_venta_ints)
            
            # Filtro de sucursales
            if sucursales:
                sucursales_ints = []
                for s in sucursales:
                    try:
                        sucursales_ints.append(int(s))
                    except (ValueError, TypeError):
                        continue
                if sucursales_ints:
                    placeholders = ','.join(['%s'] * len(sucursales_ints))
                    where_conditions.append(f"cp.CodSucursal IN ({placeholders})")
                    params.extend(sucursales_ints)
            
            where_clause = " AND ".join(where_conditions)
            
            # Consulta SQL principal
            sql = f"""
                SELECT 
                    DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
                    cp.NroComprobante AS nro_comprobante,
                    cp.CodSucursal AS id_sucursal,
                    COALESCE(s.nombre_sucursal, 'Sin Sucursal') AS sucursal,
                    cp.id_pv AS id_punto_venta,
                    COALESCE(CAST(pv.nro_punto_venta AS CHAR), CAST(cp.id_pv AS CHAR), 'Sin PV') AS punto_venta,
                    COALESCE(cp.SubtotalDesc, 0) AS subtotal_desc
                FROM comp_ped cp
                LEFT JOIN sucursales s ON s.id_sucursal = cp.CodSucursal
                LEFT JOIN punto_venta pv ON pv.id_punto_venta = cp.id_pv
                WHERE {where_clause}
                ORDER BY 
                    cp.Fecha DESC,
                    cp.NroComprobante ASC
            """
            
            logger.info(f"🔍 Ejecutando consulta Remitos no facturados: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, base_empresa={base_empresa}")
            logger.debug(f"SQL: {sql}")
            logger.debug(f"Params: {params}")
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Obtener nombres de columnas
            column_names = [desc[0] for desc in cursor.description]
            
            # Convertir filas a diccionarios
            data = []
            total_subtotal_desc = 0.0
            
            for row in rows:
                row_dict = dict(zip(column_names, row))
                # Convertir valores numéricos
                subtotal_desc = float(row_dict.get('subtotal_desc', 0) or 0)
                total_subtotal_desc += subtotal_desc
                
                # La fecha ya viene formateada desde SQL (DD/MM/YYYY)
                # No necesitamos procesarla adicionalmente
                
                data.append(row_dict)
            
            # Calcular totales
            totals = {
                "total_subtotal_desc": total_subtotal_desc,
            }
            
            # Notas
            notes = [
                f"Período: {self._format_date(fecha_inicio)} a {self._format_date(fecha_fin)}",
                f"Total de remitos: {len(data)}",
                f"Total: ${total_subtotal_desc:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            ]
            
            
            ended_at = timezone.now()
            duration = (ended_at - started_at).total_seconds()
            
            logger.info(f"✅ Consulta Remitos no facturados completada en {duration:.2f}s: {len(data)} registros")
            
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                },
                data=data,
                totals=totals,
                notes=notes,
            )
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando consulta Remitos no facturados: {e}", exc_info=True)
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                },
                data=[],
                totals={},
                notes=[f"Error al ejecutar la consulta: {str(e)}"],
            )
    
    def _run_pending_orders(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """
        Ejecuta la consulta SQL para el reporte de Pedidos pendientes.
        Muestra pedidos (TipoComprobante = PED) que están en estado 'En preparación' o 'Preparado' y no han sido anulados.
        """
        started_at = timezone.now()
        
        try:
            filters = payload.get("filters", {})
            base_empresa = filters.get("base_empresa")
            fecha_inicio, fecha_fin = self._resolve_period_dates(filters)
            if not fecha_inicio or not fecha_fin:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
                )
            if not base_empresa:
                if hasattr(self.user, 'base_empresa'):
                    base_empresa = self.user.base_empresa
            if not base_empresa:
                base_empresa = getattr(settings, 'DEFAULT_BASE_EMPRESA', None)
            if not base_empresa:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se pudo determinar la base de datos de la empresa. Asegúrese de estar logueado correctamente."],
                )
            mysql_config = settings.DATABASES['mysql']
            import MySQLdb
            try:
                conn = MySQLdb.connect(
                    host=mysql_config['HOST'],
                    port=int(mysql_config['PORT']),
                    user=mysql_config['USER'],
                    passwd=mysql_config['PASSWORD'],
                    db=base_empresa,
                    charset='latin1'
                )
                cursor = conn.cursor()
            except Exception as conn_error:
                logger.error(f"❌ Error conectando a MySQL ({base_empresa}): {conn_error}")
                raise
            
            # Construir condiciones WHERE
            where_conditions = [
                "cp.Fecha >= %s",
                "cp.Fecha <= %s",
                "cp.TipoComprobante = 'PED'",
                "cp.Anulado = 'No'",
                "cp.Estado IN ('En preparación', 'Preparado')"
            ]
            params = [fecha_inicio, fecha_fin]
            
            where_clause = " AND ".join(where_conditions)
            
            # Consulta SQL principal
            sql = f"""
                SELECT 
                    DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
                    cp.TipoComprobante AS tipo_comprobante,
                    cp.NroComprobante AS nro_comprobante,
                    COALESCE(cp.SubtotalDesc, 0) AS subtotal_desc,
                    cp.Estado AS estado
                FROM comp_ped cp
                WHERE {where_clause}
                ORDER BY 
                    cp.Fecha DESC,
                    cp.NroComprobante ASC
            """
            
            logger.info(f"🔍 Ejecutando consulta Pedidos pendientes: fecha_inicio={fecha_inicio}, fecha_fin={fecha_fin}, base_empresa={base_empresa}")
            logger.debug(f"SQL: {sql}")
            logger.debug(f"Params: {params}")
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            # Obtener nombres de columnas
            column_names = [desc[0] for desc in cursor.description]
            
            # Convertir filas a diccionarios
            data = []
            total_subtotal_desc = 0.0
            
            for row in rows:
                row_dict = dict(zip(column_names, row))
                # Convertir valores numéricos
                subtotal_desc = float(row_dict.get('subtotal_desc', 0) or 0)
                total_subtotal_desc += subtotal_desc
                
                # La fecha ya viene formateada desde SQL (DD/MM/YYYY)
                # No necesitamos procesarla adicionalmente
                
                data.append(row_dict)
            
            # Calcular totales
            totals = {
                "total_subtotal_desc": total_subtotal_desc,
            }
            
            # Notas
            notes = [
                f"Período: {self._format_date(fecha_inicio)} a {self._format_date(fecha_fin)}",
                f"Total de pedidos: {len(data)}",
                f"Total: ${total_subtotal_desc:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
            ]
            
            
            ended_at = timezone.now()
            duration = (ended_at - started_at).total_seconds()
            
            logger.info(f"✅ Consulta Pedidos pendientes completada en {duration:.2f}s: {len(data)} registros")
            
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                },
                data=data,
                totals=totals,
                notes=notes,
            )
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando consulta Pedidos pendientes: {e}", exc_info=True)
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                },
                data=[],
                totals={},
                notes=[f"Error al ejecutar la consulta: {str(e)}"],
            )

    def _parse_sucursales_pv(self, filters: Dict) -> Tuple[List[int], List[int]]:
        """Normaliza sucursales y punto_venta desde filters a listas de enteros."""
        sucursales = filters.get("sucursales", [])
        if isinstance(sucursales, str):
            sucursales = [sucursales] if sucursales else []
        elif not isinstance(sucursales, list):
            sucursales = []
        puntos_venta = filters.get("punto_venta", [])
        if isinstance(puntos_venta, str):
            puntos_venta = [puntos_venta] if puntos_venta else []
        elif not isinstance(puntos_venta, list):
            puntos_venta = []
        sucursales_ints = []
        for s in sucursales:
            try:
                sucursales_ints.append(int(s))
            except (ValueError, TypeError):
                continue
        puntos_venta_ints = []
        for pv in puntos_venta:
            try:
                puntos_venta_ints.append(int(pv))
            except (ValueError, TypeError):
                continue
        return sucursales_ints, puntos_venta_ints

    def _parse_clientes_excluidos(self, filters: Dict) -> List:
        """Normaliza clientes_excluidos desde filters para NOT IN en consultas."""
        raw = filters.get("clientes_excluidos", [])
        if isinstance(raw, str):
            raw = [raw] if (raw and str(raw).strip()) else []
        elif not isinstance(raw, list):
            raw = []
        out = []
        for c in raw:
            try:
                c_str = str(c).strip()
                if c_str:
                    out.append(int(c_str) if c_str.isdigit() else c_str)
            except (ValueError, TypeError):
                continue
        return out

    def _get_ventas_netas_total(
        self, cursor, fecha_inicio: str, fecha_fin: str,
        sucursales: Optional[List[int]] = None, puntos_venta: Optional[List[int]] = None,
        clientes_excluidos: Optional[List] = None,
    ) -> float:
        """Total ventas netas (Facturas - NC) para el período y filtros opcionales. Reutilizado por sales_summary y total_consolidado_operativo."""
        where_conditions = [
            "cc.Fecha >= %s", "cc.Fecha <= %s",
            "cc.Anulado = 'No'", "cc.CodigoMovimiento <> 0",
            "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')",
        ]
        params = [fecha_inicio, fecha_fin]
        if puntos_venta:
            placeholders = ",".join(["%s"] * len(puntos_venta))
            where_conditions.append(f"cc.id_pv IN ({placeholders})")
            params.extend(puntos_venta)
        if sucursales:
            placeholders = ",".join(["%s"] * len(sucursales))
            where_conditions.append(f"cc.CodSucursal IN ({placeholders})")
            params.extend(sucursales)
        if clientes_excluidos:
            clientes_vals = []
            for c in clientes_excluidos:
                try:
                    c_str = str(c).strip()
                    if c_str:
                        clientes_vals.append(int(c_str) if c_str.isdigit() else c_str)
                except (ValueError, TypeError):
                    continue
            if clientes_vals:
                placeholders = ",".join(["%s"] * len(clientes_vals))
                where_conditions.append(f"cc.Codigo NOT IN ({placeholders})")
                params.extend(clientes_vals)
        sql = f"""
            SELECT SUM(CASE
                WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(cc.SubtotalDesc, 0)
                WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN -COALESCE(cc.SubtotalDesc, 0)
                ELSE 0
            END) AS ventas_netas
            FROM cuentacliente cc
            WHERE {" AND ".join(where_conditions)}
        """
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return float(row[0] or 0) if row else 0.0

    def _get_remitos_no_facturados_total(
        self, cursor, fecha_inicio: str, fecha_fin: str,
        sucursales: Optional[List[int]] = None, puntos_venta: Optional[List[int]] = None,
        clientes_excluidos: Optional[List] = None,
    ) -> float:
        """Total remitos no facturados (comp_ped REM, Pendiente). Reutilizado por sales_summary y total_consolidado_operativo."""
        where_conditions = [
            "cp.Fecha >= %s", "cp.Fecha <= %s",
            "cp.TipoComprobante = 'REM'", "cp.Anulado = 'No'", "cp.Estado = 'Pendiente'",
        ]
        params = [fecha_inicio, fecha_fin]
        if puntos_venta:
            placeholders = ",".join(["%s"] * len(puntos_venta))
            where_conditions.append(f"cp.id_pv IN ({placeholders})")
            params.extend(puntos_venta)
        if sucursales:
            placeholders = ",".join(["%s"] * len(sucursales))
            where_conditions.append(f"cp.CodSucursal IN ({placeholders})")
            params.extend(sucursales)
        if clientes_excluidos:
            clientes_vals = []
            for c in clientes_excluidos:
                try:
                    c_str = str(c).strip()
                    if c_str:
                        clientes_vals.append(int(c_str) if c_str.isdigit() else c_str)
                except (ValueError, TypeError):
                    continue
            if clientes_vals:
                placeholders = ",".join(["%s"] * len(clientes_vals))
                where_conditions.append(f"cp.Codigo NOT IN ({placeholders})")
                params.extend(clientes_vals)
        sql = f"""
            SELECT SUM(COALESCE(cp.SubtotalDesc, 0)) AS total_remitos
            FROM comp_ped cp
            WHERE {" AND ".join(where_conditions)}
        """
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return float(row[0] or 0) if row else 0.0

    def _get_pedidos_pendientes_total(
        self, cursor, fecha_inicio: str, fecha_fin: str,
        sucursales: Optional[List[int]] = None, puntos_venta: Optional[List[int]] = None,
        clientes_excluidos: Optional[List] = None,
    ) -> float:
        """Total pedidos pendientes de entrega (comp_ped PED, En preparación/Preparado). Reutilizado por sales_summary y total_consolidado_operativo."""
        where_conditions = [
            "cp.Fecha >= %s", "cp.Fecha <= %s",
            "cp.TipoComprobante = 'PED'", "cp.Anulado = 'No'",
            "cp.Estado IN ('En preparación', 'Preparado')",
        ]
        params = [fecha_inicio, fecha_fin]
        if puntos_venta:
            placeholders = ",".join(["%s"] * len(puntos_venta))
            where_conditions.append(f"cp.id_pv IN ({placeholders})")
            params.extend(puntos_venta)
        if sucursales:
            placeholders = ",".join(["%s"] * len(sucursales))
            where_conditions.append(f"cp.CodSucursal IN ({placeholders})")
            params.extend(sucursales)
        if clientes_excluidos:
            clientes_vals = []
            for c in clientes_excluidos:
                try:
                    c_str = str(c).strip()
                    if c_str:
                        clientes_vals.append(int(c_str) if c_str.isdigit() else c_str)
                except (ValueError, TypeError):
                    continue
            if clientes_vals:
                placeholders = ",".join(["%s"] * len(clientes_vals))
                where_conditions.append(f"cp.Codigo NOT IN ({placeholders})")
                params.extend(clientes_vals)
        sql = f"""
            SELECT SUM(COALESCE(cp.SubtotalDesc, 0)) AS total_pedidos
            FROM comp_ped cp
            WHERE {" AND ".join(where_conditions)}
        """
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return float(row[0] or 0) if row else 0.0

    def _run_sales_summary(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """
        Ejecuta la consulta SQL para el reporte consolidado de Resumen de Ventas.
        Consolida los totales de:
        - Ventas Netas (Facturas - Notas de Crédito)
        - Remitos no facturados
        - Pedidos pendientes
        Reutiliza _get_ventas_netas_total, _get_remitos_no_facturados_total, _get_pedidos_pendientes_total.
        """
        started_at = timezone.now()
        
        try:
            filters = payload.get("filters", {})
            base_empresa = filters.get("base_empresa")
            fecha_inicio, fecha_fin = self._resolve_period_dates(filters)
            if not fecha_inicio or not fecha_fin:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
                )
            if not base_empresa:
                if hasattr(self.user, 'base_empresa'):
                    base_empresa = self.user.base_empresa
            if not base_empresa:
                base_empresa = getattr(settings, 'DEFAULT_BASE_EMPRESA', None)
            if not base_empresa:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se pudo determinar la base de datos de la empresa. Asegúrese de estar logueado correctamente."],
                )
            sucursales_ints, puntos_venta_ints = self._parse_sucursales_pv(filters)
            clientes_excluidos = self._parse_clientes_excluidos(filters)
            mysql_config = settings.DATABASES['mysql']
            import MySQLdb
            try:
                conn = MySQLdb.connect(
                    host=mysql_config['HOST'],
                    port=int(mysql_config['PORT']),
                    user=mysql_config['USER'],
                    passwd=mysql_config['PASSWORD'],
                    db=base_empresa,
                    charset='latin1'
                )
                cursor = conn.cursor()
            except Exception as conn_error:
                logger.error(f"❌ Error conectando a MySQL ({base_empresa}): {conn_error}")
                raise

            ventas_netas = self._get_ventas_netas_total(
                cursor, fecha_inicio, fecha_fin,
                sucursales_ints or None, puntos_venta_ints or None,
                clientes_excluidos or None,
            )
            remitos_no_facturados = self._get_remitos_no_facturados_total(
                cursor, fecha_inicio, fecha_fin,
                sucursales_ints or None, puntos_venta_ints or None,
                clientes_excluidos or None,
            )
            pedidos_pendientes = self._get_pedidos_pendientes_total(
                cursor, fecha_inicio, fecha_fin,
                sucursales_ints or None, puntos_venta_ints or None,
                clientes_excluidos or None,
            )
            total_consolidado = ventas_netas + remitos_no_facturados + pedidos_pendientes

            data = [{
                "ventas_netas": ventas_netas,
                "remitos_no_facturados": remitos_no_facturados,
                "pedidos_pendientes": pedidos_pendientes,
                "total_consolidado": total_consolidado,
            }]
            totals = {
                "ventas_netas": ventas_netas,
                "remitos_no_facturados": remitos_no_facturados,
                "pedidos_pendientes": pedidos_pendientes,
                "total_consolidado": total_consolidado,
            }
            notes = [f"Período: {self._format_date(fecha_inicio)} a {self._format_date(fecha_fin)}"]

            logger.info(f"✅ Consulta Resumen de Ventas completada")
            logger.info(f"   Ventas Netas: ${ventas_netas:,.2f}")
            logger.info(f"   Remitos no facturados: ${remitos_no_facturados:,.2f}")
            logger.info(f"   Pedidos pendientes: ${pedidos_pendientes:,.2f}")
            logger.info(f"   Total consolidado: ${total_consolidado:,.2f}")

            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                },
                data=data,
                totals=totals,
                notes=notes,
            )

        except Exception as e:
            logger.error(f"❌ Error ejecutando consulta Resumen de Ventas: {e}", exc_info=True)
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                },
                data=[],
                totals={},
                notes=[f"Error al ejecutar la consulta: {str(e)}"],
            )

    def _run_total_consolidado_operativo(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """
        Reporte legacy Total Consolidado Operativo: 4 KPIs en una columna vertical.
        Ventas Netas, Remitos no facturados, Pedidos pendientes de entrega, Total consolidado.
        Reutiliza _get_ventas_netas_total, _get_remitos_no_facturados_total, _get_pedidos_pendientes_total.
        """
        started_at = timezone.now()
        try:
            filters = payload.get("filters", {})
            base_empresa = filters.get("base_empresa")
            fecha_inicio, fecha_fin = self._resolve_period_dates(filters)
            if not fecha_inicio or not fecha_fin:
                return QueryResult(
                    meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
                    data=[], totals={}, notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
                )
            if not base_empresa:
                base_empresa = getattr(self.user, "base_empresa", None) if hasattr(self.user, "base_empresa") else None
            if not base_empresa:
                base_empresa = getattr(settings, "DEFAULT_BASE_EMPRESA", None)
            if not base_empresa:
                return QueryResult(
                    meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
                    data=[], totals={}, notes=["No se pudo determinar la base de datos de la empresa."],
                )
            sucursales_ints, puntos_venta_ints = self._parse_sucursales_pv(filters)
            clientes_excluidos = self._parse_clientes_excluidos(filters)
            mysql_config = settings.DATABASES["mysql"]
            import MySQLdb
            conn = MySQLdb.connect(
                host=mysql_config["HOST"], port=int(mysql_config["PORT"]),
                user=mysql_config["USER"], passwd=mysql_config["PASSWORD"],
                db=base_empresa, charset="latin1",
            )
            cursor = conn.cursor()
            ventas_netas = self._get_ventas_netas_total(
                cursor, fecha_inicio, fecha_fin,
                sucursales_ints or None, puntos_venta_ints or None,
                clientes_excluidos or None,
            )
            remitos_no_facturados = self._get_remitos_no_facturados_total(
                cursor, fecha_inicio, fecha_fin,
                sucursales_ints or None, puntos_venta_ints or None,
                clientes_excluidos or None,
            )
            pedidos_pendientes = self._get_pedidos_pendientes_total(
                cursor, fecha_inicio, fecha_fin,
                sucursales_ints or None, puntos_venta_ints or None,
                clientes_excluidos or None,
            )
            total_consolidado = ventas_netas + remitos_no_facturados + pedidos_pendientes
            conn.close()

            data = [
                {"label": "VENTAS NETAS", "value": ventas_netas},
                {"label": "REMITOS NO FACTURADOS", "value": remitos_no_facturados},
                {"label": "PEDIDOS PENDIENTES DE ENTREGA", "value": pedidos_pendientes},
                {"label": "TOTAL CONSOLIDADO", "value": total_consolidado},
            ]
            totals = {
                "ventas_netas": ventas_netas,
                "remitos_no_facturados": remitos_no_facturados,
                "pedidos_pendientes": pedidos_pendientes,
                "total_consolidado": total_consolidado,
            }
            notes = [
                f"Período: {self._format_date(fecha_inicio)} a {self._format_date(fecha_fin)}",
            ]
            if sucursales_ints or puntos_venta_ints:
                notes.append("Filtros: sucursales y/o punto de venta aplicados.")
            if clientes_excluidos:
                notes.append(f"Clientes excluidos: {len(clientes_excluidos)} cliente(s) (NOT IN).")
            logger.info(f"✅ Total consolidado operativo: VN=${ventas_netas:,.2f} REM=${remitos_no_facturados:,.2f} PED=${pedidos_pendientes:,.2f} TOTAL=${total_consolidado:,.2f}")
            return QueryResult(meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version}, data=data, totals=totals, notes=notes)
        except Exception as e:
            logger.error(f"❌ Error Total consolidado operativo: {e}", exc_info=True)
            return QueryResult(
                meta={"slug": report.slug, "name": report.name, "category": report.category, "version": report.version},
                data=[], totals={}, notes=[f"Error al ejecutar la consulta: {str(e)}"],
            )

    def _run_backorder_vs_stock_vs_facturacion(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """
        Ejecuta el reporte legacy BO vs Stock vs Facturación.
        Emula el Excel 'BASE ANALISIS BO V2.xlsx'.
        
        Fuentes:
        - Facturación: cuentacliente (FA/FB/FC/FE/FM menos NC*)
        - Remitos no facturados: comp_ped (TipoComprobante='REM', Estado='Pendiente')
        - Backorder: comp_ped (TipoComprobante='PED') + stockp (renglones definitivos)
        - Stock: stock_deposito (saldo, oc_pendiente); Reservado: stockp+comp_ped (Estado En preparación/Preparado)
        - Maestros: articulo + rubro
        
        RESPUESTAS OBLIGATORIAS (Backorder detalle row-level):
        1) ID cliente: comp_ped.Codigo. Tabla maestra: cliente. Join: cliente cli ON cli.Codigo = cp.Codigo.
        2) precio_x_renglon: stockp.PrecioVentaxR (total por renglón; no unitario).
        3) cant_pend: stockp.cantidad_pendiente.
        4) Subrubro: existe. Tabla subrubro, join articulo.IDSubRubro = subrubro.IDSubRubro. Vendedor: existe.
           Tabla viajantes, join comp_ped.CodViajante = viajantes.CodViajante. Sin match -> ''.
        5) Base prueba: 73 filas. Límite 1000, sin paginación server-side; note "mostrando primeros N (límite 1000)".
        """
        started_at = timezone.now()
        
        try:
            # Obtener filtros del payload
            filters = payload.get("filters", {})
            
            # Obtener base_empresa del payload
            base_empresa = filters.get("base_empresa")
            
            fecha_inicio, fecha_fin = self._resolve_period_dates(filters)
            if not fecha_inicio or not fecha_fin:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["Debe proporcionar fecha de inicio y fecha fin, o seleccionar un período predefinido."],
                )
            if not base_empresa:
                if hasattr(self.user, 'base_empresa'):
                    base_empresa = self.user.base_empresa
            if not base_empresa:
                base_empresa = getattr(settings, 'DEFAULT_BASE_EMPRESA', None)
            if not base_empresa:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se pudo determinar la base de datos de la empresa. Asegúrese de estar logueado correctamente."],
                )
            sucursales = filters.get("sucursales", [])
            if isinstance(sucursales, str):
                sucursales = [sucursales] if sucursales else []
            elif not isinstance(sucursales, list):
                sucursales = []
            
            puntos_venta = filters.get("punto_venta", [])
            if isinstance(puntos_venta, str):
                puntos_venta = [puntos_venta] if puntos_venta else []
            elif not isinstance(puntos_venta, list):
                puntos_venta = []
            
            depositos_excluidos = filters.get("depositos_excluidos", [])
            if isinstance(depositos_excluidos, str):
                depositos_excluidos = [depositos_excluidos] if depositos_excluidos else []
            elif not isinstance(depositos_excluidos, list):
                depositos_excluidos = []
            depositos_excluidos = [int(x) for x in depositos_excluidos if str(x).strip() and str(x).replace("-", "").isdigit()]
            
            clientes_excluidos = self._parse_clientes_excluidos(filters)
            
            # Conectar a MySQL
            mysql_config = settings.DATABASES['mysql']
            
            import MySQLdb
            try:
                conn = MySQLdb.connect(
                    host=mysql_config['HOST'],
                    port=int(mysql_config['PORT']),
                    user=mysql_config['USER'],
                    passwd=mysql_config['PASSWORD'],
                    db=base_empresa,
                    charset='latin1'
                )
                cursor = conn.cursor()
            except Exception as conn_error:
                logger.error(f"❌ Error conectando a MySQL ({base_empresa}): {conn_error}")
                raise
            
            logger.info(f"🔍 Ejecutando reporte BO vs Stock vs Facturación: {fecha_inicio} a {fecha_fin}, base={base_empresa}")
            try:
                cursor.execute("SET SESSION max_execution_time = 90000")
            except Exception:
                pass  # MySQL < 8.0.3 o MariaDB: usar solo hints por consulta

            # =========================================================
            # 1. FACTURACIÓN (cuentacliente)
            # =========================================================
            # Error 3024 = timeout (MAX_EXECUTION_TIME), NO error de sintaxis.
            # Si hay 3024: la consulta es válida pero tarda >90s (ej. full scan en cuentacliente).
            # Índices recomendados en administranet89:
            #   CREATE INDEX idx_cc_fecha ON cuentacliente (Fecha);
            #   CREATE INDEX idx_cc_fecha_tipo_anul ON cuentacliente (Fecha, TipoComprobante, Anulado);
            # Ver plan: EXPLAIN <query>; evitar type=ALL, asegurar key usado.
            # MAX_EXECUTION_TIME (ms): evita colgarse con bases grandes. MySQL 5.7.8+.
            params_facturacion = [fecha_inicio, fecha_fin]
            where_fact = [
                "Fecha >= %s", "Fecha <= %s",
                "Anulado = 'No'",
                "TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')",
            ]
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_fact.append(f"Codigo NOT IN ({ph})")
                params_facturacion.extend(clientes_excluidos)
            where_fact_s = " AND ".join(where_fact)
            sql_facturacion = f"""
                SELECT /*+ MAX_EXECUTION_TIME(90000) */
                    SUM(CASE 
                        WHEN TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') 
                        THEN COALESCE(SubtotalDesc, 0)
                        ELSE 0 
                    END) AS ventas,
                    SUM(CASE 
                        WHEN TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') 
                        THEN COALESCE(SubtotalDesc, 0)
                        ELSE 0 
                    END) AS notas_credito
                FROM cuentacliente
                WHERE {where_fact_s}
            """
            cursor.execute(sql_facturacion, params_facturacion)
            row_fact = cursor.fetchone()
            ventas = float(row_fact[0] or 0) if row_fact else 0.0
            notas_credito = float(row_fact[1] or 0) if row_fact else 0.0
            facturacion_neta = ventas - notas_credito
            facturacion_neta_total = facturacion_neta  # Para % ventas y notes
            logger.info("📊 [BO] Facturación (cuentacliente) OK")

            # Facturación por cliente (agregado, 1 fila = 1 cliente)
            # MAPEO:
            # - Tabla clientes: cliente. FK facturación→cliente: cuentacliente.Codigo = cliente.Codigo.
            # - Vendedor: del cliente (cliente.CodViajante -> viajantes.Nombre). No del movimiento.
            # - Zona: cliente.id_zona -> erp_zona.id_zona; erp_zona.nombre_zona.
            # - Última compra: MAX(cc.Fecha) dentro del período filtrado (no global).
            # - Sucursal/PV en facturación: cuentacliente.CodSucursal, id_pv. Filtros aplicados cuando se envían.
            where_fac_cli = [
                "cc.Fecha >= %s",
                "cc.Fecha <= %s",
                "cc.Anulado = 'No'",
                "cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')",
            ]
            params_fac_cli = [fecha_inicio, fecha_fin]
            # BO reporte consolidado: no filtrar por sucursal ni punto de venta
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_fac_cli.append(f"cc.Codigo NOT IN ({ph})")
                params_fac_cli.extend(clientes_excluidos)
            where_fac_cli_s = " AND ".join(where_fac_cli)
            FAC_CLI_LIMIT = 1000
            params_fac_cli.append(FAC_CLI_LIMIT)
            
            sql_fac_cli = f"""
                SELECT /*+ MAX_EXECUTION_TIME(90000) */
                    cl.Codigo AS id_cliente,
                    CONCAT(COALESCE(MAX(cl.nombre_cliente), ''), ' (Cod: ', cl.Codigo, ')') AS cliente,
                    SUM(CASE WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END)
                        - SUM(CASE WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') THEN COALESCE(cc.SubtotalDesc, 0) ELSE 0 END) AS sub_total,
                    MAX(cc.Fecha) AS ultima_compra,
                    COALESCE(MAX(v.Nombre), '') AS vendedor,
                    COALESCE(MAX(z.nombre_zona), '') AS zona,
                    COALESCE(MAX(cl.telefono), '') AS telefono,
                    COALESCE(MAX(cl.Email), '') AS email,
                    COALESCE(MAX(cl.CUIT), '') AS cuit
                FROM cuentacliente cc
                INNER JOIN cliente cl ON cl.Codigo = cc.Codigo
                LEFT JOIN viajantes v ON v.CodViajante = cl.CodViajante
                LEFT JOIN erp_zona z ON z.id_zona = cl.id_zona AND (z.anulado IS NULL OR z.anulado = 'No')
                WHERE {where_fac_cli_s}
                GROUP BY cl.Codigo
                ORDER BY sub_total DESC
                LIMIT %s
            """
            cursor.execute(sql_fac_cli, params_fac_cli)
            fac_cli_rows = cursor.fetchall()
            
            facturacion_por_cliente = []
            for i, r in enumerate(fac_cli_rows, 1):
                sub = float(r[2] or 0)
                porc = round((sub / facturacion_neta_total) * 100, 2) if facturacion_neta_total else 0
                facturacion_por_cliente.append({
                    "nro": i,
                    "id_cliente": r[0],
                    "cliente": (r[1] or "").strip(),
                    "sub_total": sub,
                    "porc_ventas": porc,
                    "ultima_compra": r[3].strftime("%Y-%m-%d") if r[3] else "",
                    "vendedor": (r[4] or "").strip(),
                    "zona": (r[5] or "").strip(),
                    "telefono": (r[6] or "").strip(),
                    "email": (r[7] or "").strip(),
                    "cuit": (r[8] or "").strip(),
                })
            logger.info("📊 [BO] Facturación por cliente OK (%d clientes)", len(facturacion_por_cliente))

            # =========================================================
            # 2. REMITOS NO FACTURADOS (comp_ped)
            # =========================================================
            where_remitos = ["cp.Fecha >= %s", "cp.Fecha <= %s", "cp.TipoComprobante = 'REM'", "cp.Anulado = 'No'", "cp.Estado = 'Pendiente'"]
            params_remitos = [fecha_inicio, fecha_fin]
            # BO reporte consolidado: no filtrar por sucursal ni punto de venta
            if clientes_excluidos:
                placeholders = ','.join(['%s'] * len(clientes_excluidos))
                where_remitos.append(f"cp.Codigo NOT IN ({placeholders})")
                params_remitos.extend(clientes_excluidos)
            
            where_remitos_clause = " AND ".join(where_remitos)
            
            # Total remitos
            sql_remitos_total = f"""
                SELECT /*+ MAX_EXECUTION_TIME(90000) */ SUM(COALESCE(cp.SubtotalDesc, 0)) AS total_remitos
                FROM comp_ped cp
                WHERE {where_remitos_clause}
            """
            cursor.execute(sql_remitos_total, params_remitos)
            row_rem = cursor.fetchone()
            remitos_no_facturados_total = float(row_rem[0] or 0) if row_rem else 0.0
            logger.info("📊 [BO] Remitos total OK")

            # Detalle remitos
            sql_remitos_detalle = f"""
                SELECT /*+ MAX_EXECUTION_TIME(90000) */
                    DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
                    cp.NroComprobante AS nro_comprobante,
                    cp.CodSucursal AS id_sucursal,
                    COALESCE(s.nombre_sucursal, 'Sin Sucursal') AS sucursal,
                    cp.id_pv AS id_punto_venta,
                    COALESCE(CAST(pv.nro_punto_venta AS CHAR), CAST(cp.id_pv AS CHAR), 'Sin PV') AS punto_venta,
                    COALESCE(cp.SubtotalDesc, 0) AS subtotal_desc
                FROM comp_ped cp
                LEFT JOIN sucursales s ON s.id_sucursal = cp.CodSucursal
                LEFT JOIN punto_venta pv ON pv.id_punto_venta = cp.id_pv
                WHERE {where_remitos_clause}
                ORDER BY cp.Fecha DESC, cp.NroComprobante ASC
            """
            cursor.execute(sql_remitos_detalle, params_remitos)
            remitos_rows = cursor.fetchall()
            remitos_detalle = [
                {
                    "fecha": row[0],
                    "nro_comprobante": row[1],
                    "id_sucursal": row[2],
                    "sucursal": row[3],
                    "id_punto_venta": row[4],
                    "punto_venta": row[5],
                    "subtotal_desc": float(row[6] or 0),
                }
                for row in remitos_rows
            ]
            logger.info("📊 [BO] Remitos detalle OK (%d filas)", len(remitos_detalle))

            # =========================================================
            # 3. BACKORDER (comp_ped + stockp + stock_deposito)
            # =========================================================
            # Renglones definitivos de PED en stockp (VB6); comp_ped para cabecera y estados.
            bo_estados = "('Pendiente')"

            # Depósitos excluidos: no sumar su saldo en stock_actual/disponible
            sd_where_excl = ""
            if depositos_excluidos:
                sd_where_excl = " WHERE id_deposito NOT IN (" + ",".join(str(d) for d in depositos_excluidos) + ")"
            clientes_excl_bo = ""
            reservado_excl_clause = ""
            if clientes_excluidos:
                clientes_excl_bo = " AND cp.Codigo NOT IN (" + ",".join(str(c) for c in clientes_excluidos) + ")"
                reservado_excl_clause = " AND cp_res.Codigo NOT IN (" + ",".join(str(c) for c in clientes_excluidos) + ")"

            # Detalle BO por producto con cálculo de cobertura
            # bo_importe = SUM(PrecioVentaxR). Sin fallback: si es 0 es correcto.
            # oc_pendiente = CALCULADO desde stockp+cuentaproveedor (OC Estado=Pendiente). NO usar stock_deposito.saldo_pedido_proveedor.
            # stock_reservado = CALCULADO desde stockp+comp_ped (PED En preparación/Preparado/Parcial; NO Pendiente). NO usar stock_deposito.saldo_pedido_cliente.
            sql_bo_detalle = f"""
                SELECT /*+ MAX_EXECUTION_TIME(90000) */
                    sp.IDArt AS id_art,
                    a.id_manual AS codigo,
                    a.NombreArticulo AS articulo,
                    COALESCE(r.NombreRubro, 'Sin Rubro') AS categoria,
                    SUM(sp.Cantidad) AS bo_qty,
                    SUM(sp.PrecioVentaxR) AS bo_importe,
                    COALESCE(sd.stock_total, 0) AS stock_actual,
                    COALESCE(reservado_sub.reservado, 0) AS stock_reservado,
                    GREATEST(0, COALESCE(sd.stock_total, 0) - COALESCE(reservado_sub.reservado, 0)) AS disponible,
                    GREATEST(0, COALESCE(oc_pendiente_sub.oc_pendiente, 0)) AS oc_pendiente
                FROM stockp sp
                INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                LEFT JOIN articulo a ON a.IDArt = sp.IDArt
                LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
                LEFT JOIN (
                    SELECT id_articulo, SUM(saldo) AS stock_total
                    FROM stock_deposito{sd_where_excl}
                    GROUP BY id_articulo
                ) sd ON sd.id_articulo = sp.IDArt
                LEFT JOIN (
                    SELECT sp_oc.IDArt AS id_articulo,
                        SUM(COALESCE(sp_oc.cantidad_pendiente, sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0))) AS oc_pendiente
                    FROM stockp sp_oc
                    INNER JOIN cuentaproveedor cp_oc ON cp_oc.CodigoMovimiento = sp_oc.CodigoMovimiento
                    WHERE cp_oc.TipoComprobante = 'OC'
                        AND (sp_oc.Comprobante = 'OC' OR sp_oc.Comprobante IS NULL)
                        AND cp_oc.Estado = 'Pendiente'
                        AND cp_oc.Anulado = 'No'
                        AND (sp_oc.anulado IS NULL OR sp_oc.anulado = 'No')
                        AND (COALESCE(sp_oc.cantidad_pendiente, sp_oc.Cantidad - COALESCE(sp_oc.cantidad_entregada, 0)) > 0)
                    GROUP BY sp_oc.IDArt
                ) oc_pendiente_sub ON oc_pendiente_sub.id_articulo = sp.IDArt
                LEFT JOIN (
                    SELECT sp_res.IDArt AS id_articulo,
                        SUM(COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0))) AS reservado
                    FROM stockp sp_res
                    INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_res.CodigoMovimiento
                    WHERE cp_res.TipoComprobante = 'PED'
                        AND (sp_res.Comprobante = 'PED' OR sp_res.Comprobante IS NULL)
                        AND cp_res.Anulado = 'No'
                        AND (sp_res.anulado IS NULL OR sp_res.anulado = 'No')
                        AND cp_res.Estado IN ('En preparación', 'Preparado', 'Parcial')
                        AND (COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) > 0){reservado_excl_clause}
                    GROUP BY sp_res.IDArt
                ) reservado_sub ON reservado_sub.id_articulo = sp.IDArt
                WHERE cp.TipoComprobante = 'PED'
                    AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)
                    AND cp.Anulado = 'No'
                    AND (sp.anulado IS NULL OR sp.anulado = 'No')
                    AND cp.Estado IN {bo_estados}
                    AND sp.CodigoMovimiento IS NOT NULL{clientes_excl_bo}
                GROUP BY sp.IDArt, a.id_manual, a.NombreArticulo, r.NombreRubro, sd.stock_total, oc_pendiente_sub.oc_pendiente, reservado_sub.reservado
                HAVING bo_qty > 0
                ORDER BY bo_importe DESC
            """
            cursor.execute(sql_bo_detalle)
            bo_rows = cursor.fetchall()
            logger.info("📊 [BO] Detalle BO (producto) OK (%d filas)", len(bo_rows))

            # Procesar y calcular cobertura (bo_importe en row[5]; oc_pendiente en row[9])
            backorder_detalle = []
            bo_total_importe = 0.0
            con_stock_total = 0.0
            con_ingreso_total = 0.0
            sin_stock_total = 0.0
            
            for row in bo_rows:
                id_art = row[0]
                codigo = row[1] or ''
                articulo = row[2] or ''
                categoria = row[3] or 'Sin Rubro'
                bo_qty = float(row[4] or 0)
                bo_importe = float(row[5] or 0)
                stock_actual = float(row[6] or 0)
                stock_reservado = float(row[7] or 0)
                disponible = float(row[8] or 0)
                oc_pendiente = float(row[9] or 0)
                
                # Clasificación por qty:
                # - Stock cubre primero reservado; disponible = max(0, stock - reservado).
                # - CON STOCK: parte del BO cubierta por disponible.
                # - OC pend. cubre primero el faltante de reservado; solo el resto se usa para BO.
                # - CON INGRESO: parte restante del BO cubierta por ese OC restante (para BO).
                # - SIN STOCK: resto del BO no cubierto.
                faltante_reservado = max(0.0, stock_reservado - stock_actual)
                oc_para_reservado = min(oc_pendiente, faltante_reservado)
                oc_restante_bo = max(0.0, oc_pendiente - oc_para_reservado)
                con_stock_qty = min(bo_qty, disponible)
                rest = bo_qty - con_stock_qty
                con_ingreso_qty = min(rest, oc_restante_bo)
                sin_stock_qty = rest - con_ingreso_qty
                
                # Prorratear importes por qty
                if bo_qty > 0:
                    con_stock_importe = bo_importe * (con_stock_qty / bo_qty)
                    con_ingreso_importe = bo_importe * (con_ingreso_qty / bo_qty)
                    sin_stock_importe = bo_importe * (sin_stock_qty / bo_qty)
                else:
                    con_stock_importe = 0.0
                    con_ingreso_importe = 0.0
                    sin_stock_importe = 0.0
                
                # Acumular totales
                bo_total_importe += bo_importe
                con_stock_total += con_stock_importe
                con_ingreso_total += con_ingreso_importe
                sin_stock_total += sin_stock_importe
                
                backorder_detalle.append({
                    "id_art": id_art,
                    "codigo": codigo,
                    "articulo": articulo,
                    "categoria": categoria,
                    "bo_qty": bo_qty,
                    "bo_importe": bo_importe,
                    "stock_actual": stock_actual,
                    "stock_reservado": stock_reservado,
                    "disponible": disponible,
                    "oc_pendiente": oc_pendiente,
                    "con_stock_qty": con_stock_qty,
                    "con_stock_importe": con_stock_importe,
                    "con_ingreso_qty": con_ingreso_qty,
                    "con_ingreso_importe": con_ingreso_importe,
                    "sin_stock_qty": sin_stock_qty,
                    "sin_stock_importe": sin_stock_importe,
                })
            
            # Detalle OC pendientes (para tooltip en "OC pend. qty"): fecha, nro, vencimiento, proveedor por artículo
            ids_oc = [r["id_art"] for r in backorder_detalle if (r.get("oc_pendiente") or 0) > 0]
            oc_map = {}
            if ids_oc:
                try:
                    ph = ",".join(["%s"] * len(ids_oc))
                    sql_oc_detalle = f"""
                        SELECT /*+ MAX_EXECUTION_TIME(15000) */
                            sp.IDArt,
                            cp.Fecha,
                            COALESCE(cp.NroCompBusq, '') AS nro_comp_busq,
                            COALESCE(cp.NroComprobante, '') AS nro_comprobante,
                            cp.Vencimiento,
                            COALESCE(prov.Nombre, '') AS proveedor,
                            COALESCE(sp.cantidad_pendiente, sp.Cantidad - COALESCE(sp.cantidad_entregada, 0)) AS qty_pend
                        FROM stockp sp
                        INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                        LEFT JOIN proveedor prov ON prov.Codigo = cp.Codigo
                        WHERE cp.TipoComprobante = 'OC' AND (sp.Comprobante = 'OC' OR sp.Comprobante IS NULL)
                            AND cp.Estado = 'Pendiente' AND cp.Anulado = 'No'
                            AND (sp.anulado IS NULL OR sp.anulado = 'No')
                            AND sp.IDArt IN ({ph})
                            AND (COALESCE(sp.cantidad_pendiente, sp.Cantidad - COALESCE(sp.cantidad_entregada, 0)) > 0)
                        ORDER BY sp.IDArt, cp.Fecha, cp.NroCompBusq
                    """
                    cursor.execute(sql_oc_detalle, ids_oc)
                    oc_rows = cursor.fetchall()

                    def _fmt_oc_date(d):
                        if d is None:
                            return ""
                        return d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)

                    for orow in oc_rows:
                        id_art = orow[0]
                        fecha = orow[1]
                        nro_busq = (orow[2] or "") if orow[2] is not None else ""
                        nro_comp = (orow[3] or "") if orow[3] is not None else ""
                        vto = orow[4]
                        proveedor = (orow[5] or "") if orow[5] is not None else ""
                        qty = float(orow[6] or 0)
                        if id_art not in oc_map:
                            oc_map[id_art] = []
                        oc_map[id_art].append({
                            "fecha": _fmt_oc_date(fecha),
                            "nro_comp_busq": nro_busq,
                            "nro_comprobante": nro_comp,
                            "vencimiento": _fmt_oc_date(vto),
                            "proveedor": proveedor,
                            "qty_pend": qty,
                        })
                    logger.info("📊 [BO] OC detalle (tooltip) OK: %d artículos con OC pendientes", len(oc_map))
                except Exception as ex:
                    logger.warning("📊 [BO] No se pudo cargar detalle OC para tooltip: %s", ex)
            for r in backorder_detalle:
                r["oc_detalle"] = oc_map.get(r["id_art"], [])

            # BO detalle (para tooltip en columna BO QTY): fecha, nro_comprobante, cliente, cantidad por comprobante
            try:
                sql_bo_comp_detalle = f"""
                    SELECT /*+ MAX_EXECUTION_TIME(15000) */
                        sp.IDArt,
                        cp.Fecha,
                        COALESCE(NULLIF(TRIM(cp.NroComprobante), ''), cp.NroCompBusq, '') AS nro_comprobante,
                        COALESCE(NULLIF(TRIM(cli.nombre_cliente), ''), '—') AS cliente,
                        sp.Cantidad
                    FROM stockp sp
                    INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                    LEFT JOIN cliente cli ON cli.Codigo = cp.Codigo
                    WHERE cp.TipoComprobante = 'PED'
                        AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL)
                        AND cp.Anulado = 'No'
                        AND (sp.anulado IS NULL OR sp.anulado = 'No')
                        AND cp.Estado IN {bo_estados}
                        AND sp.CodigoMovimiento IS NOT NULL{clientes_excl_bo}
                    ORDER BY sp.IDArt, cp.Fecha, cp.NroComprobante
                """
                cursor.execute(sql_bo_comp_detalle)
                bo_comp_rows = cursor.fetchall()

                def _fmt_bo_date(d):
                    if d is None:
                        return ""
                    return d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)

                bo_detalle_map: Dict[int, List[Dict]] = {}
                for brow in bo_comp_rows:
                    id_art = brow[0]
                    fecha = brow[1]
                    nro_comp = (brow[2] or "").strip() if brow[2] is not None else ""
                    cliente = (brow[3] or "").strip() if brow[3] is not None else "—"
                    qty = float(brow[4] or 0)
                    if id_art not in bo_detalle_map:
                        bo_detalle_map[id_art] = []
                    bo_detalle_map[id_art].append({
                        "fecha": _fmt_bo_date(fecha),
                        "nro_comprobante": nro_comp or "—",
                        "cliente": cliente or "—",
                        "cantidad": qty,
                    })
                for r in backorder_detalle:
                    r["bo_detalle"] = bo_detalle_map.get(r["id_art"], [])
                logger.info("📊 [BO] BO detalle (tooltip) OK: %d artículos con comprobantes", len(bo_detalle_map))
            except Exception as ex:
                logger.warning("📊 [BO] No se pudo cargar BO detalle para tooltip: %s", ex)
                for r in backorder_detalle:
                    r["bo_detalle"] = []

            # Reservado detalle (para tooltip en columna Reservado): PED En preparación/Preparado/Parcial (NO Pendiente), fecha, nro, cliente, estado, cantidad
            reservado_estados = "('En preparación', 'Preparado', 'Parcial')"
            try:
                sql_reservado_detalle = f"""
                    SELECT /*+ MAX_EXECUTION_TIME(15000) */
                        sp_res.IDArt,
                        cp_res.Fecha,
                        COALESCE(NULLIF(TRIM(cp_res.NroComprobante), ''), cp_res.NroCompBusq, '') AS nro_comprobante,
                        COALESCE(NULLIF(TRIM(cli.nombre_cliente), ''), '—') AS cliente,
                        COALESCE(NULLIF(TRIM(cp_res.Estado), ''), '—') AS estado,
                        COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) AS cantidad
                    FROM stockp sp_res
                    INNER JOIN comp_ped cp_res ON cp_res.CodigoMovimiento = sp_res.CodigoMovimiento
                    LEFT JOIN cliente cli ON cli.Codigo = cp_res.Codigo
                    WHERE cp_res.TipoComprobante = 'PED'
                        AND (sp_res.Comprobante = 'PED' OR sp_res.Comprobante IS NULL)
                        AND cp_res.Anulado = 'No'
                        AND (sp_res.anulado IS NULL OR sp_res.anulado = 'No')
                        AND cp_res.Estado IN {reservado_estados}
                        AND sp_res.CodigoMovimiento IS NOT NULL
                        AND (COALESCE(sp_res.cantidad_pendiente, sp_res.Cantidad - COALESCE(sp_res.cantidad_entregada, 0)) > 0){reservado_excl_clause}
                    ORDER BY sp_res.IDArt, cp_res.Fecha, cp_res.NroComprobante
                """
                cursor.execute(sql_reservado_detalle)
                res_rows = cursor.fetchall()

                def _fmt_res_date(d):
                    if d is None:
                        return ""
                    return d.strftime("%d/%m/%Y") if hasattr(d, "strftime") else str(d)

                reservado_detalle_map: Dict[int, List[Dict]] = {}
                for rrow in res_rows:
                    id_art = rrow[0]
                    fecha = rrow[1]
                    nro_comp = (rrow[2] or "").strip() if rrow[2] is not None else ""
                    cliente = (rrow[3] or "").strip() if rrow[3] is not None else "—"
                    estado = (rrow[4] or "").strip() if rrow[4] is not None else "—"
                    qty = float(rrow[5] or 0)
                    if id_art not in reservado_detalle_map:
                        reservado_detalle_map[id_art] = []
                    reservado_detalle_map[id_art].append({
                        "fecha": _fmt_res_date(fecha),
                        "nro_comprobante": nro_comp or "—",
                        "cliente": cliente or "—",
                        "estado": estado or "—",
                        "cantidad": qty,
                    })
                for r in backorder_detalle:
                    r["reservado_detalle"] = reservado_detalle_map.get(r["id_art"], [])
                logger.info("📊 [BO] Reservado detalle (tooltip) OK: %d artículos con reserva", len(reservado_detalle_map))
            except Exception as ex:
                logger.warning("📊 [BO] No se pudo cargar reservado detalle para tooltip: %s", ex)
                for r in backorder_detalle:
                    r["reservado_detalle"] = []

            # Stock por depósito (para tooltip en columna Stock): cantidad por NombreDeposito (excl. depósitos excluidos)
            ids_art = [r["id_art"] for r in backorder_detalle]
            stock_por_dep_map = {}
            if ids_art:
                try:
                    ph = ",".join(["%s"] * len(ids_art))
                    cursor.execute(f"""
                        SELECT d.CodDeposito, COALESCE(NULLIF(TRIM(d.NombreDeposito), ''), 'Sin nombre') AS nombre_deposito
                        FROM deposito d
                        WHERE (d.anulado IS NULL OR d.anulado = 'No')
                        ORDER BY d.CodDeposito
                    """)
                    depositos_all = cursor.fetchall()
                    depositos = [(cod, nom) for cod, nom in depositos_all if cod not in depositos_excluidos] if depositos_excluidos else depositos_all
                    sd_where_excl = " AND sd.id_deposito NOT IN (" + ",".join(str(d) for d in depositos_excluidos) + ")" if depositos_excluidos else ""
                    cursor.execute(f"""
                        SELECT sd.id_articulo, sd.id_deposito, COALESCE(sd.saldo, 0)
                        FROM stock_deposito sd
                        WHERE sd.id_articulo IN ({ph}){sd_where_excl}
                    """, ids_art)
                    sd_rows = cursor.fetchall()
                    # Map: (id_art, id_deposito) -> saldo
                    saldo_map = {}
                    for row in sd_rows:
                        saldo_map[(row[0], row[1])] = float(row[2] or 0)
                    for r in backorder_detalle:
                        id_art = r["id_art"]
                        stock_por_dep = []
                        for cod_dep, nom_dep in depositos:
                            saldo = saldo_map.get((id_art, cod_dep), 0.0)
                            stock_por_dep.append({"deposito": nom_dep, "saldo": saldo})
                        r["stock_por_deposito"] = stock_por_dep
                    logger.info("📊 [BO] Stock por depósito (tooltip) OK: %d artículos", len(ids_art))
                except Exception as ex:
                    logger.warning("📊 [BO] No se pudo cargar stock por depósito para tooltip: %s", ex)
                    for r in backorder_detalle:
                        r["stock_por_deposito"] = []
            else:
                for r in backorder_detalle:
                    r["stock_por_deposito"] = []

            # Código manual / IDArt: codigo = articulo.id_manual, id_art = stockp.IDArt (articulo.IDArt).
            # Totales: sum(detalle_con_stock.con_stock_importe) == con_stock_total; idem con_ingreso. Se valida y loguea si difieren.
            # Detalle con stock: filas con con_stock_qty > 0, orden por con_stock_importe DESC
            detalle_con_stock = [
                r for r in backorder_detalle
                if (r.get("con_stock_qty") or 0) > 0
            ]
            detalle_con_stock.sort(key=lambda x: -(x.get("con_stock_importe") or 0))
            
            # Detalle con ingreso: filas con con_ingreso_qty > 0, orden por con_ingreso_importe DESC
            detalle_con_ingreso = [
                r for r in backorder_detalle
                if (r.get("con_ingreso_qty") or 0) > 0
            ]
            detalle_con_ingreso.sort(key=lambda x: -(x.get("con_ingreso_importe") or 0))
            
            # Validar que sumas de detalle coincidan con totales del resumen
            sum_con_stock = sum(r.get("con_stock_importe") or 0 for r in detalle_con_stock)
            sum_con_ingreso = sum(r.get("con_ingreso_importe") or 0 for r in detalle_con_ingreso)
            diff_stock = abs(sum_con_stock - con_stock_total)
            diff_ingreso = abs(sum_con_ingreso - con_ingreso_total)
            if diff_stock > 0.01:
                logger.warning(
                    "BO detalle_con_stock: suma(con_stock_importe)=%s != con_stock_total=%s (diff=%s)",
                    sum_con_stock, con_stock_total, diff_stock,
                )
            if diff_ingreso > 0.01:
                logger.warning(
                    "BO detalle_con_ingreso: suma(con_ingreso_importe)=%s != con_ingreso_total=%s (diff=%s)",
                    sum_con_ingreso, con_ingreso_total, diff_ingreso,
                )
            
            # Detalle sin stock: filas con sin_stock_qty > 0, orden por sin_stock_importe DESC.
            # Vista por categoría se obtiene en frontend agrupando por categoria.
            detalle_sin_stock = [
                r for r in backorder_detalle
                if (r.get("sin_stock_qty") or 0) > 0
            ]
            detalle_sin_stock.sort(key=lambda x: -(x.get("sin_stock_importe") or 0))
            sum_sin_stock = sum(r.get("sin_stock_importe") or 0 for r in detalle_sin_stock)
            if abs(sum_sin_stock - sin_stock_total) > 0.01:
                logger.warning(
                    "BO detalle_sin_stock: suma(sin_stock_importe)=%s != sin_stock_total=%s",
                    sum_sin_stock, sin_stock_total,
                )
            
            # =========================================================
            # 3b. BACKORDER DETALLE ROW-LEVEL (Excel-like, un renglón por fila)
            # Cabecera: comp_ped | Renglones: stockp | Cliente: cliente.Codigo | Vendedor: viajantes
            # precio_x_renglon: stockp.PrecioVentaxR. cant_pend: stockp.cantidad_pendiente.
            # Sin límite: se devuelve la cantidad real de renglones.
            # =========================================================
            where_bo_rows = [
                "cp.TipoComprobante = 'PED'",
                "(spr.Comprobante = 'PED' OR spr.Comprobante IS NULL)",
                "cp.Anulado = 'No'",
                "(spr.anulado IS NULL OR spr.anulado = 'No')",
                f"cp.Estado IN {bo_estados}",
                "spr.CodigoMovimiento IS NOT NULL",
            ]
            params_bo_rows = []
            # BO reporte consolidado: no filtrar por sucursal ni punto de venta
            if clientes_excluidos:
                ph = ",".join(["%s"] * len(clientes_excluidos))
                where_bo_rows.append(f"cp.Codigo NOT IN ({ph})")
                params_bo_rows.extend(clientes_excluidos)
            where_bo_rows_clause = " AND ".join(where_bo_rows)
            
            sql_bo_rows = f"""
                SELECT /*+ MAX_EXECUTION_TIME(90000) */
                    DATE_FORMAT(cp.Fecha, '%%d/%%m/%%y') AS fecha,
                    cp.NroComprobante AS nro_comp,
                    COALESCE(spr.Descripcion, a.NombreArticulo, '') AS descripcion,
                    COALESCE(a.id_manual, spr.id_manual, '') AS cod_manual,
                    spr.Cantidad AS cantidad,
                    COALESCE(spr.cantidad_pendiente, 0) AS cant_pend,
                    cp.Estado AS estado,
                    COALESCE(cli.nombre_cliente, '') AS cliente,
                    cp.Codigo AS id_cliente,
                    COALESCE(spr.PrecioVentaxR, 0) AS precio_x_renglon,
                    COALESCE(r.NombreRubro, '') AS nombre_rubro,
                    COALESCE(sr.NombreSubRubro, '') AS nombre_sub_rubro,
                    COALESCE(v.Nombre, '') AS nombre_vendedor
                FROM comp_ped cp
                INNER JOIN stockp spr ON spr.CodigoMovimiento = cp.CodigoMovimiento
                LEFT JOIN articulo a ON a.IDArt = spr.IDArt
                LEFT JOIN rubro r ON r.CodigoRubro = a.CodigoRubro
                LEFT JOIN subrubro sr ON sr.IDSubRubro = a.IDSubRubro
                LEFT JOIN cliente cli ON cli.Codigo = cp.Codigo
                LEFT JOIN viajantes v ON v.CodViajante = cp.CodViajante
                WHERE {where_bo_rows_clause}
                ORDER BY cp.Fecha DESC, cp.NroComprobante ASC, COALESCE(spr.Descripcion, a.NombreArticulo, '') ASC
            """
            cursor.execute(sql_bo_rows, params_bo_rows)
            bo_row_rows = cursor.fetchall()
            logger.info("📊 [BO] Backorder detalle (row-level) OK (%d filas)", len(bo_row_rows))

            backorder_detalle_rows = []
            for r in bo_row_rows:
                backorder_detalle_rows.append({
                    "fecha": r[0],
                    "nro_comp": r[1],
                    "descripcion": r[2] or "",
                    "cod_manual": r[3] or "",
                    "cantidad": float(r[4] or 0),
                    "cant_pend": int(round(float(r[5] or 0))),
                    "estado": r[6] or "",
                    "cliente": r[7] or "",
                    "id_cliente": r[8],
                    "precio_x_renglon": float(r[9] or 0),
                    "nombre_rubro": r[10] or "",
                    "nombre_sub_rubro": r[11] or "",
                    "nombre_vendedor": r[12] or "",
                })
            
            if backorder_detalle_rows:
                logger.info(
                    "📋 [BO] backorder_detalle_rows sample (3 filas): %s",
                    json.dumps(backorder_detalle_rows[:3], default=str, ensure_ascii=False),
                )

            # Detectar si hay más de un depósito (para definición sobre stock_deposito)
            num_depositos = 0
            try:
                cursor.execute("""
                    SELECT COUNT(*) FROM deposito WHERE (anulado IS NULL OR anulado = 'No')
                """)
                r = cursor.fetchone()
                if r:
                    num_depositos = int(r[0] or 0)
                if num_depositos > 1:
                    logger.info("📊 [BO] Más de un depósito en la base (N=%d). Stock agregado por artículo.", num_depositos)
            except Exception as ex:
                logger.debug("📊 [BO] No se pudo contar depósitos: %s", ex)
            
            # Cerrar conexión
            cursor.close()
            conn.close()
            
            # =========================================================
            # 4. CALCULAR TOTALES FINALES
            # =========================================================
            total_importe = facturacion_neta + remitos_no_facturados_total
            
            # =========================================================
            # 5. CONSTRUIR RESULTADO
            # =========================================================
            # Data principal: Resumen estilo Excel
            resumen_data = [
                # Bloque Facturación
                {"concepto": "FACTURACIÓN (neto)", "importe": facturacion_neta, "tipo": "facturacion"},
                {"concepto": "REMITO (no facturados)", "importe": remitos_no_facturados_total, "tipo": "facturacion"},
                {"concepto": "TOTAL FACTURACIÓN + REMITOS", "importe": total_importe, "tipo": "total_facturacion"},
                # Bloque Backorder
                {"concepto": "BACKORDER TOTAL", "importe": bo_total_importe, "tipo": "backorder"},
                {"concepto": "CON STOCK", "importe": con_stock_total, "tipo": "backorder"},
                {"concepto": "CON INGRESO", "importe": con_ingreso_total, "tipo": "backorder"},
                {"concepto": "SIN STOCK", "importe": sin_stock_total, "tipo": "sin_stock"},
            ]
            
            # Totals para KPIs y métricas
            totals = {
                # Facturación
                "ventas": ventas,
                "notas_credito": notas_credito,
                "facturacion_neta": facturacion_neta,
                "facturacion_neta_total": facturacion_neta_total,
                "remitos_no_facturados_total": remitos_no_facturados_total,
                "total_importe": total_importe,
                # Backorder
                "bo_total_importe": bo_total_importe,
                "con_stock_total": con_stock_total,
                "con_ingreso_total": con_ingreso_total,
                "sin_stock_total": sin_stock_total,
                # Conteos
                "total_productos_bo": len(backorder_detalle),
                "total_productos_sin_stock": len(detalle_sin_stock),
                "total_remitos": len(remitos_detalle),
                "total_clientes_facturacion": len(facturacion_por_cliente),
            }
            
            # Notes
            notes = [
                f"Período: {self._format_date(fecha_inicio)} a {self._format_date(fecha_fin)}",
                f"Facturación neta: ${facturacion_neta:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                f"Remitos no facturados: ${remitos_no_facturados_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                f"Total sin stock: ${sin_stock_total:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.'),
                "Reservado = CALCULADO desde stockp+comp_ped (PED En preparación/Preparado/Parcial; NO Pendiente). No usar stock_deposito.saldo_pedido_cliente.",
                "Backorder: renglones desde stockp + comp_ped. CON INGRESO = OC pendientes (calculado desde stockp+cuentaproveedor). OC cubre primero faltante reservado, el resto cubre BO. No usar stock_deposito.saldo_pedido_proveedor.",
                f"Backorder detalle: {len(backorder_detalle_rows)} renglones.",
                "Facturación por cliente: % ventas = (sub_total_cliente / facturacion_neta_total) * 100. Última compra = MAX(fecha) dentro del período.",
                "Facturación: reporte consolidado (todos los depósitos/clientes salvo exclusiones). Tab mostrando primeros " + str(len(facturacion_por_cliente)) + f" clientes (límite {FAC_CLI_LIMIT}).",
            ]
            if depositos_excluidos:
                notes.append(f"Depósitos excluidos: {len(depositos_excluidos)} depósito(s) (stock y disponible sin estos depósitos).")
            if clientes_excluidos:
                notes.append(f"Clientes excluidos: {len(clientes_excluidos)} cliente(s) (facturación, remitos y backorder NOT IN).")
            if num_depositos > 1:
                notes.append(
                    f"Hay {num_depositos} depósitos en la base. Stock y reservado se muestran agregados por artículo (todos los depósitos). "
                    "Definir si se requiere filtro o desglose por depósito."
                )
            if diff_stock > 0.01:
                notes.append(
                    f"⚠️ Detalle con stock: suma(con_stock_importe)={sum_con_stock:.2f} != con_stock_total={con_stock_total:.2f} (diff={diff_stock:.2f})"
                )
            if diff_ingreso > 0.01:
                notes.append(
                    f"⚠️ Detalle con ingreso: suma(con_ingreso_importe)={sum_con_ingreso:.2f} != con_ingreso_total={con_ingreso_total:.2f} (diff={diff_ingreso:.2f})"
                )
            
            # Extra: datasets para tabs y flags para la UI
            extra = {
                "tabs": {
                    "resumen": resumen_data,
                    "detalle_sin_stock": detalle_sin_stock,
                    "detalle_con_stock": detalle_con_stock,
                    "detalle_con_ingreso": detalle_con_ingreso,
                    "facturacion": facturacion_por_cliente,
                    "remitos": remitos_detalle,
                    "backorder_detalle": backorder_detalle,
                    "backorder_detalle_rows": backorder_detalle_rows,
                },
            }
            
            ended_at = timezone.now()
            duration = (ended_at - started_at).total_seconds()
            
            logger.info(f"✅ Reporte BO vs Stock vs Facturación completado en {duration:.2f}s")
            logger.info(f"   Facturación neta: ${facturacion_neta:,.2f}")
            logger.info(f"   Remitos no facturados: ${remitos_no_facturados_total:,.2f}")
            logger.info(f"   Total importe: ${total_importe:,.2f}")
            logger.info(f"   BO total: ${bo_total_importe:,.2f}")
            logger.info(f"   Sin stock: ${sin_stock_total:,.2f}")
            
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                    "extra": extra,
                },
                data=resumen_data,
                totals=totals,
                notes=notes,
            )
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando reporte BO vs Stock vs Facturación: {e}", exc_info=True)
            err_msg = str(e)
            notes_err = [f"Error al ejecutar la consulta: {err_msg}"]
            if "max_execution_time" in err_msg.lower() or "3024" in err_msg or "interrupted" in err_msg.lower():
                notes_err.append(
                    "La consulta superó el tiempo máximo (90 s). Pruebe un período más corto o use filtros (sucursal/punto de venta). "
                    "Si la base es muy grande, añada índices en cuentacliente.Fecha, comp_ped.Fecha, etc."
                )
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                },
                data=[],
                totals={},
                notes=notes_err,
            )

