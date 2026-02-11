"""
Reconciliación: saldo_pedido_proveedor (stock_deposito) vs movimientos teóricos.

Contexto VB6:
- OC: pendiente + (crea orden)
- Remito: mueve stock (recepción física). VB6 suma a saldo_pedido_proveedor (posible bug).
- Factura OC: mueve stock solo si NO hay remito previo (directa desde OC). VB6 suma.
- Factura Remito: NO mueve stock (el remito ya lo hizo). VB6 no toca saldo_pedido_proveedor.
- Anulación OC: pendiente -

Este servicio calcula:
1) Teórico VB6 = +OC + Remitos + Facturas OC - Anulaciones (replica lo que hace VB6)
2) Teórico conceptual = +OC - Remitos - Facturas OC - Anulaciones (pendiente por recibir correcto)
3) B = stockp.cantidad_pendiente (OC Pendiente)

Compara con actual (stock_deposito.saldo_pedido_proveedor).
"""
from typing import Dict, List, Any, Optional, Tuple
import logging
from dataclasses import dataclass

from .connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)


@dataclass
class EjercicioInfo:
    id_ejercicio: int
    fecdesde: str
    fechasta: str
    nombre: str


@dataclass
class ReconciliacionArticulo:
    id_art: int
    codigo: str
    articulo: str
    saldo_actual: float
    teorico_vb6: float
    teorico_conceptual: float
    calculo_stockp: float  # B: stockp.cantidad_pendiente OC Pendiente
    diferencia_vb6: float
    diferencia_conceptual: float
    mov_oc: float
    mov_remito: float
    mov_factura_oc: float
    mov_anulacion: float


def listar_ejercicios(base_empresa: str) -> List[Dict[str, Any]]:
    """
    Lista ejercicios disponibles en cont_ejercicio para usar en filtros.
    """
    result: List[Dict[str, Any]] = []
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id_ejercicio, fecdesde_ejercicio, fechasta_ejercicio,
                       COALESCE(nombre_ejercicio, CONCAT(fecdesde_ejercicio, ' - ', fechasta_ejercicio)),
                       COALESCE(activo_ejercicio, 'No')
                FROM cont_ejercicio
                ORDER BY id_ejercicio DESC
                LIMIT 20
                """
            )
            for row in cursor.fetchall():
                result.append({
                    "id": row[0],
                    "fecdesde": str(row[1]) if row[1] else "",
                    "fechasta": str(row[2]) if row[2] else "",
                    "nombre": row[3] or "",
                    "activo": (row[4] or "").lower() == "si",
                })
    except Exception as e:
        logger.warning("No se pudo listar ejercicios: %s", e)
    return result


def get_ejercicio(base_empresa: str, ejercicio_id: Optional[int] = None) -> Optional[EjercicioInfo]:
    """
    Obtiene rango de fechas de 1 ejercicio desde cont_ejercicio.
    Si ejercicio_id es None, usa el ejercicio activo o el más reciente.
    """
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            if ejercicio_id:
                cursor.execute(
                    """
                    SELECT id_ejercicio, fecdesde_ejercicio, fechasta_ejercicio,
                           COALESCE(nombre_ejercicio, CONCAT(fecdesde_ejercicio, ' - ', fechasta_ejercicio))
                    FROM cont_ejercicio WHERE id_ejercicio = %s
                    """,
                    (ejercicio_id,),
                )
            else:
                cursor.execute(
                    """
                    SELECT id_ejercicio, fecdesde_ejercicio, fechasta_ejercicio,
                           COALESCE(nombre_ejercicio, CONCAT(fecdesde_ejercicio, ' - ', fechasta_ejercicio))
                    FROM cont_ejercicio
                    WHERE activo_ejercicio = 'Si'
                    ORDER BY id_ejercicio DESC
                    LIMIT 1
                    """
                )
            row = cursor.fetchone()
            if row:
                return EjercicioInfo(
                    id_ejercicio=row[0],
                    fecdesde=str(row[1]) if row[1] else "",
                    fechasta=str(row[2]) if row[2] else "",
                    nombre=row[3] or "",
                )
        except Exception as e:
            logger.warning("cont_ejercicio no disponible: %s", e)
    return None


def run_reconciliation(
    base_empresa: str,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    solo_ejercicio: bool = False,
) -> Dict[str, Any]:
    """
    Ejecuta la reconciliación saldo_pedido_proveedor vs movimientos teóricos (sumando como VB6).

    Args:
        base_empresa: Nombre de la base de datos MySQL.
        fecha_desde: Filtro opcional para movimientos (si None, usa todo el historial).
        fecha_hasta: Filtro opcional.
        solo_ejercicio: Si True y hay fechas, calcula teórico solo con movimientos en el periodo
                        (para validar si el saldo se explica sumando en ese ejercicio).

    Returns:
        Dict con coincidencias, diferencias, totales y desglose por tipo de movimiento.
    """
    result: Dict[str, Any] = {
        "coincidencias": [],
        "diferencias": [],
        "total_articulos": 0,
        "total_coincidencias": 0,
        "total_diferencias": 0,
        "ejercicio": None,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "resumen_movimientos": {},
        "error": None,
    }

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()

            filtro_fecha = ""
            params_fecha: List[Any] = []
            if fecha_desde and fecha_hasta:
                filtro_fecha = " AND cp.Fecha >= %s AND cp.Fecha <= %s "
                params_fecha = [fecha_desde, fecha_hasta]

            # 1) OC creadas: + stockp.Cantidad (cuentaproveedor TipoComprobante='OC', Anulado='No')
            sql_oc = f"""
                SELECT sp.IDArt, SUM(COALESCE(sp.Cantidad, 0)) AS total
                FROM stockp sp
                INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                WHERE cp.TipoComprobante = 'OC'
                  AND (cp.Anulado IS NULL OR cp.Anulado = 'No')
                  AND (sp.anulado IS NULL OR sp.anulado = 'No')
                  {filtro_fecha}
                GROUP BY sp.IDArt
            """
            cursor.execute(sql_oc, params_fecha)
            map_oc: Dict[int, float] = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}

            # 2) Remitos desde OC: + stockp.Cantidad por cada línea de REM ligada a OC (oc_remp)
            filtro_rem = filtro_fecha.replace("cp.", "cp_rem.") if filtro_fecha else ""
            sql_rem = f"""
                SELECT s.IDArt, SUM(COALESCE(sp.Cantidad, 0)) AS total
                FROM stock s
                INNER JOIN cuentaproveedor cp_rem ON cp_rem.CodigoMovimiento = s.CodigoMovimiento
                  AND cp_rem.TipoComprobante = 'REM'
                  AND (cp_rem.Anulado IS NULL OR cp_rem.Anulado = 'No')
                  {filtro_rem}
                INNER JOIN oc_remp ocrem ON ocrem.codigo_movimiento_remp = s.CodigoMovimiento
                  AND (ocrem.Anulado IS NULL OR ocrem.Anulado = 'No')
                INNER JOIN stockp sp ON sp.CodigoMovimiento = ocrem.codigo_movimiento_oc
                  AND sp.IDArt = s.IDArt
                  AND (sp.anulado IS NULL OR sp.anulado = 'No')
                GROUP BY s.IDArt
            """
            try:
                cursor.execute(sql_rem, params_fecha)
                map_rem = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
            except Exception as e:
                logger.warning("oc_remp/REM no disponible: %s", e)
                map_rem = {}

            # 3) Facturas OC: + stockp.Cantidad por cada línea de Factura ligada a OC (oc_factp)
            filtro_fa = filtro_fecha.replace("cp.", "cp_fa.") if filtro_fecha else ""
            sql_fa = f"""
                SELECT s.IDArt, SUM(COALESCE(sp.Cantidad, 0)) AS total
                FROM stock s
                INNER JOIN oc_factp ocf ON ocf.codigo_movimientof = s.CodigoMovimiento
                  AND (ocf.Anulado IS NULL OR ocf.Anulado = 'No')
                INNER JOIN cuentaproveedor cp_fa ON cp_fa.CodigoMovimiento = s.CodigoMovimiento
                  AND (cp_fa.Anulado IS NULL OR cp_fa.Anulado = 'No')
                  {filtro_fa}
                INNER JOIN stockp sp ON sp.CodigoMovimiento = ocf.codigo_movimiento_oc
                  AND sp.IDArt = s.IDArt
                  AND (sp.anulado IS NULL OR sp.anulado = 'No')
                GROUP BY s.IDArt
            """
            try:
                cursor.execute(sql_fa, params_fecha)
                map_fa = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
            except Exception as e:
                logger.warning("oc_factp/Factura OC no disponible: %s", e)
                map_fa = {}

            # 4) Anulaciones OC: - stockp.Cantidad (Anulado='Si')
            # Nota: no hay fecha de anulación fácil; incluimos todas las anulaciones
            sql_anul = """
                SELECT sp.IDArt, SUM(COALESCE(sp.Cantidad, 0)) AS total
                FROM stockp sp
                INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                WHERE cp.TipoComprobante = 'OC'
                  AND cp.Anulado = 'Si'
                GROUP BY sp.IDArt
            """
            cursor.execute(sql_anul)
            map_anul: Dict[int, float] = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}

            # 5) Saldo actual: stock_deposito
            cursor.execute("""
                SELECT id_articulo, SUM(COALESCE(saldo_pedido_proveedor, 0)) AS total
                FROM stock_deposito
                GROUP BY id_articulo
            """)
            map_actual: Dict[int, float] = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}

            # 6) B: stockp.cantidad_pendiente (OC Pendiente/Parcial) - pendiente real por recibir
            sql_b = """
                SELECT sp.IDArt,
                       SUM(COALESCE(sp.cantidad_pendiente, sp.Cantidad - COALESCE(sp.cantidad_entregada, 0))) AS qty
                FROM stockp sp
                INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                WHERE cp.TipoComprobante = 'OC'
                  AND cp.Estado IN ('Pendiente', 'Parcial')
                  AND (cp.Anulado IS NULL OR cp.Anulado = 'No')
                  AND (sp.anulado IS NULL OR sp.anulado = 'No')
                  AND (COALESCE(sp.cantidad_pendiente, sp.Cantidad - COALESCE(sp.cantidad_entregada, 0)) > 0)
                GROUP BY sp.IDArt
            """
            cursor.execute(sql_b)
            map_b: Dict[int, float] = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}

            # Combinar y calcular teóricos por artículo
            all_ids = set(map_oc.keys()) | set(map_rem.keys()) | set(map_fa.keys()) | set(map_anul.keys()) | set(map_actual.keys()) | set(map_b.keys())

            if all_ids:
                ph = ",".join(["%s"] * len(all_ids))
                cursor.execute(
                    f"SELECT IDArt, COALESCE(id_manual,'') AS id_manual, COALESCE(NombreArticulo,'') AS NombreArticulo FROM articulo WHERE IDArt IN ({ph})",
                    list(all_ids),
                )
                art_info: Dict[int, Tuple[str, str]] = {row[0]: (row[1] or "", row[2] or "") for row in cursor.fetchall()}
            else:
                art_info = {}

            coincidencias: List[ReconciliacionArticulo] = []
            diferencias: List[ReconciliacionArticulo] = []
            total_mov_oc = 0.0
            total_mov_rem = 0.0
            total_mov_fa = 0.0
            total_mov_anul = 0.0

            for id_art in sorted(all_ids):
                mov_oc = map_oc.get(id_art, 0.0)
                mov_rem = map_rem.get(id_art, 0.0)
                mov_fa = map_fa.get(id_art, 0.0)
                mov_anul = map_anul.get(id_art, 0.0)
                actual = map_actual.get(id_art, 0.0)
                calc_b = map_b.get(id_art, 0.0)

                # Teórico VB6: replica lo que hace VB6 (+OC +Rem +FactOC -Anul)
                teorico_vb6 = mov_oc + mov_rem + mov_fa - mov_anul
                # Teórico conceptual: pendiente por recibir correcto (+OC -Rem -FactOC -Anul)
                teorico_conceptual = mov_oc - mov_rem - mov_fa - mov_anul

                diff_vb6 = round(actual - teorico_vb6, 4)
                diff_conceptual = round(calc_b - teorico_conceptual, 4)

                total_mov_oc += mov_oc
                total_mov_rem += mov_rem
                total_mov_fa += mov_fa
                total_mov_anul += mov_anul

                codigo, nombre = art_info.get(id_art, ("", ""))
                r = ReconciliacionArticulo(
                    id_art=id_art,
                    codigo=codigo,
                    articulo=nombre,
                    saldo_actual=actual,
                    teorico_vb6=teorico_vb6,
                    teorico_conceptual=teorico_conceptual,
                    calculo_stockp=calc_b,
                    diferencia_vb6=diff_vb6,
                    diferencia_conceptual=diff_conceptual,
                    mov_oc=mov_oc,
                    mov_remito=mov_rem,
                    mov_factura_oc=mov_fa,
                    mov_anulacion=mov_anul,
                )
                # Coincidencia si Actual ≈ Teórico VB6 Y B ≈ Teórico conceptual
                if abs(diff_vb6) < 0.001 and abs(diff_conceptual) < 0.001:
                    coincidencias.append(r)
                else:
                    diferencias.append(r)

            result["coincidencias"] = [
                {
                    "id_art": r.id_art,
                    "codigo": r.codigo,
                    "articulo": r.articulo,
                    "saldo_actual": r.saldo_actual,
                    "teorico_vb6": r.teorico_vb6,
                    "teorico_conceptual": r.teorico_conceptual,
                    "calculo_stockp": r.calculo_stockp,
                    "mov_oc": r.mov_oc,
                    "mov_remito": r.mov_remito,
                    "mov_factura_oc": r.mov_factura_oc,
                    "mov_anulacion": r.mov_anulacion,
                }
                for r in coincidencias
            ]
            result["diferencias"] = [
                {
                    "id_art": r.id_art,
                    "codigo": r.codigo,
                    "articulo": r.articulo,
                    "saldo_actual": r.saldo_actual,
                    "teorico_vb6": r.teorico_vb6,
                    "teorico_conceptual": r.teorico_conceptual,
                    "calculo_stockp": r.calculo_stockp,
                    "diferencia_vb6": r.diferencia_vb6,
                    "diferencia_conceptual": r.diferencia_conceptual,
                    "mov_oc": r.mov_oc,
                    "mov_remito": r.mov_remito,
                    "mov_factura_oc": r.mov_factura_oc,
                    "mov_anulacion": r.mov_anulacion,
                }
                for r in diferencias
            ]
            result["total_articulos"] = len(all_ids)
            result["total_coincidencias"] = len(coincidencias)
            result["total_diferencias"] = len(diferencias)
            teorico_vb6_total = total_mov_oc + total_mov_rem + total_mov_fa - total_mov_anul
            teorico_conceptual_total = total_mov_oc - total_mov_rem - total_mov_fa - total_mov_anul
            result["resumen_movimientos"] = {
                "mov_oc": total_mov_oc,
                "mov_remito": total_mov_rem,
                "mov_factura_oc": total_mov_fa,
                "mov_anulacion": total_mov_anul,
                "teorico_vb6_total": teorico_vb6_total,
                "teorico_conceptual_total": teorico_conceptual_total,
                "actual_total": sum(map_actual.values()),
                "calculo_stockp_total": sum(map_b.values()),
            }
            logger.info(
                "Reconciliación saldo_pedido_proveedor: %d artículos, %d coincidencias, %d diferencias",
                len(all_ids), len(coincidencias), len(diferencias),
            )

    except Exception as e:
        logger.exception("Error en reconciliación saldo_pedido_proveedor: %s", e)
        result["error"] = str(e)

    return result


def get_movimiento_detalle(
    base_empresa: str,
    id_art: int,
    tipo: str,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Devuelve el listado de comprobantes (nrocomprobante, fecha, cantidad) que componen
    cada tipo de movimiento para un artículo dado.
    tipo: 'oc' | 'rem' | 'factoc' | 'anul'
    """
    result: List[Dict[str, Any]] = []
    filtro_fecha = ""
    params_fecha: List[Any] = []
    if fecha_desde and fecha_hasta:
        filtro_fecha = " AND cp.Fecha >= %s AND cp.Fecha <= %s "
        params_fecha = [fecha_desde, fecha_hasta]

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()

            if tipo == "oc":
                sql = f"""
                    SELECT COALESCE(NULLIF(TRIM(cp.NroComprobante), ''), cp.NroCompBusq, '') AS nro_comprobante,
                           cp.Fecha AS fecha,
                           COALESCE(sp.Cantidad, 0) AS cantidad
                    FROM stockp sp
                    INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                    WHERE sp.IDArt = %s
                      AND cp.TipoComprobante = 'OC'
                      AND (cp.Anulado IS NULL OR cp.Anulado = 'No')
                      AND (sp.anulado IS NULL OR sp.anulado = 'No')
                      {filtro_fecha}
                    ORDER BY cp.Fecha, cp.NroComprobante
                """
                cursor.execute(sql, [id_art] + params_fecha)

            elif tipo == "rem":
                filtro_rem = filtro_fecha.replace("cp.", "cp_rem.") if filtro_fecha else ""
                sql = f"""
                    SELECT COALESCE(NULLIF(TRIM(cp_rem.NroComprobante), ''), cp_rem.NroCompBusq, '') AS nro_comprobante,
                           cp_rem.Fecha AS fecha,
                           COALESCE(sp.Cantidad, 0) AS cantidad
                    FROM stock s
                    INNER JOIN cuentaproveedor cp_rem ON cp_rem.CodigoMovimiento = s.CodigoMovimiento
                      AND cp_rem.TipoComprobante = 'REM'
                      AND (cp_rem.Anulado IS NULL OR cp_rem.Anulado = 'No')
                      {filtro_rem}
                    INNER JOIN oc_remp ocrem ON ocrem.codigo_movimiento_remp = s.CodigoMovimiento
                      AND (ocrem.Anulado IS NULL OR ocrem.Anulado = 'No')
                    INNER JOIN stockp sp ON sp.CodigoMovimiento = ocrem.codigo_movimiento_oc
                      AND sp.IDArt = s.IDArt
                      AND (sp.anulado IS NULL OR sp.anulado = 'No')
                    WHERE s.IDArt = %s
                    ORDER BY cp_rem.Fecha, cp_rem.NroComprobante
                """
                try:
                    cursor.execute(sql, [id_art] + params_fecha)
                except Exception as e:
                    logger.warning("oc_remp/REM no disponible para detalle: %s", e)
                    return []

            elif tipo == "factoc":
                filtro_fa = filtro_fecha.replace("cp.", "cp_fa.") if filtro_fecha else ""
                sql = f"""
                    SELECT COALESCE(NULLIF(TRIM(cp_fa.NroComprobante), ''), cp_fa.NroCompBusq, '') AS nro_comprobante,
                           cp_fa.Fecha AS fecha,
                           COALESCE(sp.Cantidad, 0) AS cantidad
                    FROM stock s
                    INNER JOIN oc_factp ocf ON ocf.codigo_movimientof = s.CodigoMovimiento
                      AND (ocf.Anulado IS NULL OR ocf.Anulado = 'No')
                    INNER JOIN cuentaproveedor cp_fa ON cp_fa.CodigoMovimiento = s.CodigoMovimiento
                      AND (cp_fa.Anulado IS NULL OR cp_fa.Anulado = 'No')
                      {filtro_fa}
                    INNER JOIN stockp sp ON sp.CodigoMovimiento = ocf.codigo_movimiento_oc
                      AND sp.IDArt = s.IDArt
                      AND (sp.anulado IS NULL OR sp.anulado = 'No')
                    WHERE s.IDArt = %s
                    ORDER BY cp_fa.Fecha, cp_fa.NroComprobante
                """
                try:
                    cursor.execute(sql, [id_art] + params_fecha)
                except Exception as e:
                    logger.warning("oc_factp/Factura OC no disponible para detalle: %s", e)
                    return []

            elif tipo == "anul":
                sql = """
                    SELECT COALESCE(NULLIF(TRIM(cp.NroComprobante), ''), cp.NroCompBusq, '') AS nro_comprobante,
                           cp.Fecha AS fecha,
                           COALESCE(sp.Cantidad, 0) AS cantidad
                    FROM stockp sp
                    INNER JOIN cuentaproveedor cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                    WHERE sp.IDArt = %s
                      AND cp.TipoComprobante = 'OC'
                      AND cp.Anulado = 'Si'
                    ORDER BY cp.Fecha, cp.NroComprobante
                """
                cursor.execute(sql, [id_art])

            else:
                return []

            for row in cursor.fetchall():
                nro = str(row[0] or "")
                fecha = str(row[1]) if row[1] else ""
                cantidad = float(row[2] or 0)
                result.append({"nro_comprobante": nro, "fecha": fecha, "cantidad": cantidad})
    except Exception as e:
        logger.exception("Error en get_movimiento_detalle: %s", e)
    return result
