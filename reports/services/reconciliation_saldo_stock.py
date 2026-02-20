"""
Reconciliación: stock_deposito.Saldo vs saldo según movimientos en stock.

Compara por artículo:
  A) SUM(stock_deposito.saldo) — dato persistido por VB6
  B) Saldo según movimientos: SUM(entrada_efectiva) − SUM(salida_efectiva) sin doble cuenta:
     - Salida: solo REM (Remito Salida) o FA/FB/FC sin codmov_remito (venta directa). No se cuenta FA cuando ya existe REM.
     - Entrada: todas salvo REM con TipoComp 'Anul Remito' (no duplicar con NC devolución).

Ver docs/self_checkout/STOCK_VB6_PROCEDIMIENTOS_GUARDADO.md.
"""
from typing import Dict, List, Any
import logging

from .connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)


def run_reconciliation(base_empresa: str) -> Dict[str, Any]:
    """
    Ejecuta la reconciliación Saldo vs saldo según movimientos stock por artículo.

    Args:
        base_empresa: Nombre de la base de datos MySQL.

    Returns:
        Dict con coincidencias, diferencias, totales y error opcional.
    """
    result: Dict[str, Any] = {
        "coincidencias": [],
        "diferencias": [],
        "total_articulos": 0,
        "total_coincidencias": 0,
        "total_diferencias": 0,
        "error": None,
    }

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()

            # A) stock_deposito: SUM(saldo) por id_articulo
            sql_a = """
                SELECT id_articulo, SUM(COALESCE(saldo, 0)) AS saldo_total
                FROM stock_deposito
                GROUP BY id_articulo
            """
            cursor.execute(sql_a)
            map_a: Dict[int, float] = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}

            # B) Saldo según movimientos: evita doble cuenta REM+FA y NCB+REM Anul
            # Salida efectiva: REM (Remito Salida) O FA/FB/FC con codmov_remito nulo (venta directa)
            # Entrada efectiva: toda Entrada salvo REM con TipoComp 'Anul Remito'
            sql_b = """
                SELECT s.IDArt,
                       SUM(
                           COALESCE(s.Entrada, 0)
                           * CASE WHEN COALESCE(s.Comprobante, '') = 'REM'
                                   AND COALESCE(s.TipoComp, '') = 'Anul Remito' THEN 0 ELSE 1 END
                       ) - SUM(
                           COALESCE(s.Salida, 0)
                           * CASE
                               WHEN COALESCE(s.Comprobante, '') = 'REM'
                                    AND COALESCE(s.TipoComp, '') = 'Remito Salida' THEN 1
                               WHEN COALESCE(s.Comprobante, '') IN ('FA', 'FB', 'FC')
                                    AND (s.codmov_remito IS NULL OR s.codmov_remito = 0) THEN 1
                               ELSE 0
                             END
                       ) AS saldo_movimientos
                FROM stock s
                WHERE (s.anulado IS NULL OR s.anulado = 'No')
                GROUP BY s.IDArt
            """
            try:
                cursor.execute(sql_b)
                map_b = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
            except Exception as e:
                # Si faltan columnas (Comprobante, TipoComp, codmov_remito), usar fórmula simple
                logger.warning(
                    "Saldo según movimientos con regla anti-doble-cuenta no disponible (%s), usando SUM(Entrada)-SUM(Salida).",
                    e,
                )
                sql_b = """
                    SELECT s.IDArt,
                           SUM(COALESCE(s.Entrada, 0)) - SUM(COALESCE(s.Salida, 0)) AS saldo_movimientos
                    FROM stock s
                    WHERE (s.anulado IS NULL OR s.anulado = 'No')
                    GROUP BY s.IDArt
                """
                try:
                    cursor.execute(sql_b)
                    map_b = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
                except Exception as e2:
                    # Si Entrada/Salida no existen, intentar con Cantidad y Tipo (ES)
                    logger.warning("stock.Entrada/Salida no disponibles, intentando alternativa: %s", e2)
                    sql_b_alt = """
                        SELECT s.IDArt,
                               SUM(CASE WHEN COALESCE(s.ES, 'E') IN ('E', 'Entrada') THEN COALESCE(s.Cantidad, 0)
                                        ELSE -COALESCE(s.Cantidad, 0) END) AS saldo_movimientos
                        FROM stock s
                        WHERE (s.anulado IS NULL OR s.anulado = 'No')
                        GROUP BY s.IDArt
                    """
                    try:
                        cursor.execute(sql_b_alt)
                        map_b = {row[0]: float(row[1] or 0) for row in cursor.fetchall()}
                    except Exception as e3:
                        logger.warning("Alternativa stock tampoco disponible: %s", e3)
                        map_b = {}

            all_ids = set(map_a.keys()) | set(map_b.keys())

            if all_ids:
                ph = ",".join(["%s"] * len(all_ids))
                cursor.execute(
                    f"SELECT IDArt, COALESCE(id_manual,'') AS id_manual, COALESCE(NombreArticulo,'') AS NombreArticulo FROM articulo WHERE IDArt IN ({ph})",
                    list(all_ids),
                )
                art_info: Dict[int, tuple] = {row[0]: (row[1] or "", row[2] or "") for row in cursor.fetchall()}
            else:
                art_info = {}

            coincidencias: List[Dict[str, Any]] = []
            diferencias: List[Dict[str, Any]] = []

            for id_art in sorted(all_ids):
                a = map_a.get(id_art, 0.0)
                b = map_b.get(id_art, 0.0)
                diff = round(a - b, 4)
                codigo = art_info.get(id_art, ("", ""))[0] if all_ids else ""
                nombre = art_info.get(id_art, ("", ""))[1] if all_ids else ""

                r = {
                    "id_art": id_art,
                    "codigo": codigo,
                    "articulo": nombre,
                    "saldo_actual": a,
                    "teorico_stock": b,
                    "diferencia": diff,
                }

                if abs(diff) < 0.001:
                    coincidencias.append(r)
                else:
                    diferencias.append(r)

            result["coincidencias"] = coincidencias
            result["diferencias"] = diferencias
            result["total_articulos"] = len(all_ids)
            result["total_coincidencias"] = len(coincidencias)
            result["total_diferencias"] = len(diferencias)
            logger.info(
                "Reconciliación Saldo stock: %d artículos, %d coincidencias, %d diferencias",
                len(all_ids), len(coincidencias), len(diferencias),
            )

    except Exception as e:
        logger.exception("Error en reconciliación saldo stock: %s", e)
        result["error"] = str(e)

    return result
