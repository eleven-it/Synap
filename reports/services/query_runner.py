from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, date
from calendar import monthrange

from django.utils import timezone
from django.db import connections
from django.conf import settings

from ..models import ReportDefinition, ReportExecutionLog
from ..tasks import enqueue_report_refresh
from .sample_data import get_sample_data

logger = logging.getLogger(__name__)


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

    def run(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """Ejecuta la consulta solicitada."""
        started_at = timezone.now()

        # Si es el reporte de ventas netas, ejecutar consulta SQL real
        if report.slug == "ventas_netas":
            return self._run_ventas_netas(report, payload)
        
        # Si es el reporte de cash flow waterfall, ejecutar consulta SQL real
        if report.slug == "cash_flow_waterfall":
            return self._run_cash_flow_waterfall(report, payload)
        
        # Si es el reporte de movimientos detallados de cash flow, ejecutar consulta SQL real
        if report.slug == "cash_flow_detailed_movements":
            return self._run_cash_flow_detailed_movements(report, payload)
        
        # Si es el reporte de flujo de caja por cuentas/cajas, ejecutar consulta SQL real
        if report.slug == "cash_flow_by_account":
            return self._run_cash_flow_by_account(report, payload)
        
        # Si es el reporte de remitos no facturados, ejecutar consulta SQL real
        if report.slug == "uninvoiced_remitos":
            return self._run_uninvoiced_remitos(report, payload)
        
        # Si es el reporte de pedidos pendientes, ejecutar consulta SQL real
        if report.slug == "pending_orders":
            return self._run_pending_orders(report, payload)
        
        # Si es el reporte consolidado de resumen de ventas, ejecutar consulta SQL real
        if report.slug == "sales_summary":
            return self._run_sales_summary(report, payload)
        
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
            enqueue_report_refresh.delay(report.slug)
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
            # Obtener filtros del payload
            filters = payload.get("filters", {})
            
            # Obtener base_empresa del payload (pasado desde la API view)
            base_empresa = filters.get("base_empresa")
            
            # Obtener fechas
            fecha_inicio = filters.get("fecha_inicio")
            fecha_fin = filters.get("fecha_fin")
            dia_actual = filters.get("dia_actual", False)
            mes_actual = filters.get("mes_actual", False)
            año_actual = filters.get("año_actual", False)
            
            # Si está marcado "día en curso", establecer fechas automáticamente
            if dia_actual:
                today = date.today()
                fecha_inicio = today.strftime("%Y-%m-%d")
                fecha_fin = today.strftime("%Y-%m-%d")
            # Si está marcado "año en curso", establecer fechas automáticamente
            elif año_actual:
                today = date.today()
                fecha_inicio = date(today.year, 1, 1).strftime("%Y-%m-%d")  # 1 de enero del año actual
                fecha_fin = date(today.year, 12, 31).strftime("%Y-%m-%d")  # 31 de diciembre del año actual
            # Si está marcado "mes en curso", establecer fechas automáticamente
            elif mes_actual:
                today = date.today()
                fecha_inicio = date(today.year, today.month, 1).strftime("%Y-%m-%d")
                last_day = monthrange(today.year, today.month)[1]
                fecha_fin = date(today.year, today.month, last_day).strftime("%Y-%m-%d")
            
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
            
            # Construir consulta SQL
            # Conectar a la base de datos MySQL de administraNET específica de la empresa
            mysql_config = settings.DATABASES['mysql']
            
            # Usar conexión directa a MySQLdb para cambiar de base de datos
            import MySQLdb
            try:
                conn = MySQLdb.connect(
                    host=mysql_config['HOST'],
                    port=int(mysql_config['PORT']),
                    user=mysql_config['USER'],
                    passwd=mysql_config['PASSWORD'],
                    db=base_empresa,  # Base de datos específica de la empresa
                    charset='latin1'
                )
                cursor = conn.cursor()
            except Exception as conn_error:
                logger.error(f"❌ Error conectando a MySQL ({base_empresa}): {conn_error}")
                raise
            
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
                cursor.close()
                conn.close()
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
            
            cursor.close()
            conn.close()
            
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
            
            # Cerrar conexión si está abierta
            try:
                if 'conn' in locals():
                    conn.close()
            except:
                pass
            
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
            # Obtener filtros del payload
            filters = payload.get("filters", {})
            
            # Obtener base_empresa del payload
            base_empresa = filters.get("base_empresa")
            
            # Obtener fechas
            fecha_inicio = filters.get("fecha_inicio")
            fecha_fin = filters.get("fecha_fin")
            dia_actual = filters.get("dia_actual", False)
            mes_actual = filters.get("mes_actual", False)
            año_actual = filters.get("año_actual", False)
            
            # Si está marcado "día en curso", establecer fechas automáticamente
            if dia_actual:
                today = date.today()
                fecha_inicio = today.strftime("%Y-%m-%d")
                fecha_fin = today.strftime("%Y-%m-%d")
            # Si está marcado "año en curso", establecer fechas automáticamente
            elif año_actual:
                today = date.today()
                fecha_inicio = date(today.year, 1, 1).strftime("%Y-%m-%d")  # 1 de enero del año actual
                fecha_fin = date(today.year, 12, 31).strftime("%Y-%m-%d")  # 31 de diciembre del año actual
            # Si está marcado "mes en curso", establecer fechas automáticamente
            elif mes_actual:
                today = date.today()
                fecha_inicio = date(today.year, today.month, 1).strftime("%Y-%m-%d")
                last_day = monthrange(today.year, today.month)[1]
                fecha_fin = date(today.year, today.month, last_day).strftime("%Y-%m-%d")
            
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
                logger.info(f"🔍 Diagnóstico general del período:")
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
                logger.info(f"🔍 Movimientos por estado 'anulado':")
                for anulado_row in anulados:
                    logger.info(f"   - anulado='{anulado_row[0]}': {anulado_row[1]} movimientos")
            except Exception as diag_error:
                logger.warning(f"⚠️ Error en diagnóstico de anulados: {diag_error}")
            
            # Diagnóstico 3: Analizar comportamiento de cada tipo de comprobante
            # Ver cómo se comportan ingreso y egreso para cada combinación de tipo y tipo_comprobante
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
                logger.info(f"🔍 ANÁLISIS DETALLADO - Comportamiento de tipos de comprobantes en el período:")
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
                logger.info(f"🔍 VALIDACIÓN - Desglose de movimientos por mes:")
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
                logger.info(f"🔍 VALIDACIÓN - Top 10 movimientos con mayor impacto:")
                for det_row in detalle_rows:
                    logger.info(f"   Tipo: '{det_row[0]}' | Comp: '{det_row[1]}' | Fecha: {det_row[2]} | Ingreso: ${det_row[3]:,.2f} | Egreso: ${det_row[4]:,.2f} | Neto: ${det_row[5]:,.2f}")
                    logger.info(f"      Detalle: {det_row[6]} | Comp: {det_row[7]}")
            except Exception as det_error:
                logger.warning(f"⚠️ Error en consulta de validación detallada: {det_error}")
            
            # Consulta de diagnóstico: Verificar suma directa de ingresos y egresos sin filtros
            # Esta consulta se ejecuta ANTES de determinar si los campos están intercambiados
            # para ayudar en la detección
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
                logger.info(f"🔍 DIAGNÓSTICO - Suma directa de campos ORIGINALES (sin corrección):")
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
                cursor.close()
                conn.close()
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
            
            cursor.close()
            conn.close()
            
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
            
            # Cerrar conexión si está abierta
            try:
                if 'conn' in locals():
                    conn.close()
            except:
                pass
            
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
            # Obtener filtros del payload
            filters = payload.get("filters", {})
            base_empresa = payload.get("base_empresa")
            
            # Obtener fechas
            fecha_inicio = filters.get("fecha_inicio")
            fecha_fin = filters.get("fecha_fin")
            dia_actual = filters.get("dia_actual", False)
            mes_actual = filters.get("mes_actual", False)
            año_actual = filters.get("año_actual", False)
            
            # Ajustar fechas según filtros de período
            if dia_actual:
                today = date.today()
                fecha_inicio = today.strftime("%Y-%m-%d")
                fecha_fin = today.strftime("%Y-%m-%d")
            elif año_actual:
                today = date.today()
                fecha_inicio = date(today.year, 1, 1).strftime("%Y-%m-%d")
                fecha_fin = date(today.year, 12, 31).strftime("%Y-%m-%d")
            elif mes_actual:
                today = date.today()
                fecha_inicio = date(today.year, today.month, 1).strftime("%Y-%m-%d")
                last_day = monthrange(today.year, today.month)[1]
                fecha_fin = date(today.year, today.month, last_day).strftime("%Y-%m-%d")
            
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
            
            # Obtener base_empresa si no está en payload
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
            
            cursor.close()
            conn.close()
            
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
            
            try:
                if 'conn' in locals():
                    conn.close()
            except:
                pass
            
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
            # Obtener filtros del payload
            filters = payload.get("filters", {})
            base_empresa = payload.get("base_empresa")
            
            # Obtener fechas
            fecha_inicio = filters.get("fecha_inicio")
            fecha_fin = filters.get("fecha_fin")
            dia_actual = filters.get("dia_actual", False)
            mes_actual = filters.get("mes_actual", False)
            año_actual = filters.get("año_actual", False)
            
            # Ajustar fechas según filtros de período
            if dia_actual:
                today = date.today()
                fecha_inicio = today.strftime("%Y-%m-%d")
                fecha_fin = today.strftime("%Y-%m-%d")
            elif año_actual:
                today = date.today()
                fecha_inicio = date(today.year, 1, 1).strftime("%Y-%m-%d")
                fecha_fin = date(today.year, 12, 31).strftime("%Y-%m-%d")
            elif mes_actual:
                today = date.today()
                fecha_inicio = date(today.year, today.month, 1).strftime("%Y-%m-%d")
                last_day = monthrange(today.year, today.month)[1]
                fecha_fin = date(today.year, today.month, last_day).strftime("%Y-%m-%d")
            
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
            
            # Obtener base_empresa si no está en payload
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
                cursor.close()
                conn.close()
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
            
            cursor.close()
            conn.close()
            
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
            
            try:
                if 'conn' in locals():
                    conn.close()
            except:
                pass
            
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
            # Obtener filtros del payload
            filters = payload.get("filters", {})
            
            # Obtener base_empresa del payload
            base_empresa = filters.get("base_empresa")
            
            # Obtener fechas
            fecha_inicio = filters.get("fecha_inicio")
            fecha_fin = filters.get("fecha_fin")
            dia_actual = filters.get("dia_actual", False)
            mes_actual = filters.get("mes_actual", False)
            año_actual = filters.get("año_actual", False)
            
            # Si está marcado "día en curso", establecer fechas automáticamente
            if dia_actual:
                today = date.today()
                fecha_inicio = today.strftime("%Y-%m-%d")
                fecha_fin = today.strftime("%Y-%m-%d")
            # Si está marcado "año en curso", establecer fechas automáticamente
            elif año_actual:
                today = date.today()
                fecha_inicio = date(today.year, 1, 1).strftime("%Y-%m-%d")
                fecha_fin = date(today.year, 12, 31).strftime("%Y-%m-%d")
            # Si está marcado "mes en curso", establecer fechas automáticamente
            elif mes_actual:
                today = date.today()
                fecha_inicio = date(today.year, today.month, 1).strftime("%Y-%m-%d")
                last_day = monthrange(today.year, today.month)[1]
                fecha_fin = date(today.year, today.month, last_day).strftime("%Y-%m-%d")
            
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
            
            cursor.close()
            conn.close()
            
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
            # Obtener filtros del payload
            filters = payload.get("filters", {})
            
            # Obtener base_empresa del payload
            base_empresa = filters.get("base_empresa")
            
            # Obtener fechas
            fecha_inicio = filters.get("fecha_inicio")
            fecha_fin = filters.get("fecha_fin")
            dia_actual = filters.get("dia_actual", False)
            mes_actual = filters.get("mes_actual", False)
            año_actual = filters.get("año_actual", False)
            
            # Si está marcado "día en curso", establecer fechas automáticamente
            if dia_actual:
                today = date.today()
                fecha_inicio = today.strftime("%Y-%m-%d")
                fecha_fin = today.strftime("%Y-%m-%d")
            # Si está marcado "año en curso", establecer fechas automáticamente
            elif año_actual:
                today = date.today()
                fecha_inicio = date(today.year, 1, 1).strftime("%Y-%m-%d")
                fecha_fin = date(today.year, 12, 31).strftime("%Y-%m-%d")
            # Si está marcado "mes en curso", establecer fechas automáticamente
            elif mes_actual:
                today = date.today()
                fecha_inicio = date(today.year, today.month, 1).strftime("%Y-%m-%d")
                last_day = monthrange(today.year, today.month)[1]
                fecha_fin = date(today.year, today.month, last_day).strftime("%Y-%m-%d")
            
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
            
            cursor.close()
            conn.close()
            
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
    
    def _run_sales_summary(self, report: ReportDefinition, payload: Dict) -> QueryResult:
        """
        Ejecuta la consulta SQL para el reporte consolidado de Resumen de Ventas.
        Consolida los totales de:
        - Ventas Netas (Facturas - Notas de Crédito)
        - Remitos no facturados
        - Pedidos pendientes
        """
        started_at = timezone.now()
        
        try:
            # Obtener filtros del payload
            filters = payload.get("filters", {})
            
            # Obtener base_empresa del payload
            base_empresa = filters.get("base_empresa")
            
            # Obtener fechas
            fecha_inicio = filters.get("fecha_inicio")
            fecha_fin = filters.get("fecha_fin")
            dia_actual = filters.get("dia_actual", False)
            mes_actual = filters.get("mes_actual", False)
            año_actual = filters.get("año_actual", False)
            
            # Si está marcado "día en curso", establecer fechas automáticamente
            if dia_actual:
                today = date.today()
                fecha_inicio = today.strftime("%Y-%m-%d")
                fecha_fin = today.strftime("%Y-%m-%d")
            # Si está marcado "año en curso", establecer fechas automáticamente
            elif año_actual:
                today = date.today()
                fecha_inicio = date(today.year, 1, 1).strftime("%Y-%m-%d")
                fecha_fin = date(today.year, 12, 31).strftime("%Y-%m-%d")
            # Si está marcado "mes en curso", establecer fechas automáticamente
            elif mes_actual:
                today = date.today()
                fecha_inicio = date(today.year, today.month, 1).strftime("%Y-%m-%d")
                last_day = monthrange(today.year, today.month)[1]
                fecha_fin = date(today.year, today.month, last_day).strftime("%Y-%m-%d")
            
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
            
            # 1. Calcular Ventas Netas (Facturas - Notas de Crédito)
            sql_ventas_netas = f"""
                SELECT 
                    SUM(CASE 
                        WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM') 
                        THEN COALESCE(cc.SubtotalDesc, 0)
                        WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM') 
                        THEN -COALESCE(cc.SubtotalDesc, 0)
                        ELSE 0 
                    END) AS ventas_netas
                FROM cuentacliente cc
                WHERE cc.Fecha >= %s
                    AND cc.Fecha <= %s
                    AND cc.Anulado = 'No'
                    AND cc.CodigoMovimiento <> 0
                    AND cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM', 'NCA', 'NCB', 'NCC', 'NCE', 'NCM')
            """
            cursor.execute(sql_ventas_netas, [fecha_inicio, fecha_fin])
            row_ventas = cursor.fetchone()
            ventas_netas = float(row_ventas[0] or 0) if row_ventas else 0.0
            
            # 2. Calcular Remitos no facturados
            sql_remitos = f"""
                SELECT 
                    SUM(COALESCE(cp.SubtotalDesc, 0)) AS total_remitos
                FROM comp_ped cp
                WHERE cp.Fecha >= %s
                    AND cp.Fecha <= %s
                    AND cp.TipoComprobante = 'REM'
                    AND cp.Anulado = 'No'
                    AND cp.Estado = 'Pendiente'
            """
            cursor.execute(sql_remitos, [fecha_inicio, fecha_fin])
            row_remitos = cursor.fetchone()
            remitos_no_facturados = float(row_remitos[0] or 0) if row_remitos else 0.0
            
            # 3. Calcular Pedidos pendientes
            sql_pedidos = f"""
                SELECT 
                    SUM(COALESCE(cp.SubtotalDesc, 0)) AS total_pedidos
                FROM comp_ped cp
                WHERE cp.Fecha >= %s
                    AND cp.Fecha <= %s
                    AND cp.TipoComprobante = 'PED'
                    AND cp.Anulado = 'No'
                    AND cp.Estado IN ('En preparación', 'Preparado')
            """
            cursor.execute(sql_pedidos, [fecha_inicio, fecha_fin])
            row_pedidos = cursor.fetchone()
            pedidos_pendientes = float(row_pedidos[0] or 0) if row_pedidos else 0.0
            
            # 4. Calcular total consolidado
            total_consolidado = ventas_netas + remitos_no_facturados + pedidos_pendientes
            
            cursor.close()
            conn.close()
            
            # Crear un objeto de datos con los totales para que renderCards pueda mostrarlos
            # renderCards espera un array con al menos un objeto que contenga los valores
            data = [{
                "ventas_netas": ventas_netas,
                "remitos_no_facturados": remitos_no_facturados,
                "pedidos_pendientes": pedidos_pendientes,
                "total_consolidado": total_consolidado,
            }]
            
            # Calcular totales (también los ponemos aquí para el summary)
            totals = {
                "ventas_netas": ventas_netas,
                "remitos_no_facturados": remitos_no_facturados,
                "pedidos_pendientes": pedidos_pendientes,
                "total_consolidado": total_consolidado,
            }
            
            # Notas - Solo mostrar el período, el resto de la información es redundante (ya está en las tarjetas)
            notes = [
                f"Período: {self._format_date(fecha_inicio)} a {self._format_date(fecha_fin)}",
            ]
            
            ended_at = timezone.now()
            duration = (ended_at - started_at).total_seconds()
            
            logger.info(f"✅ Consulta Resumen de Ventas completada en {duration:.2f}s")
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


