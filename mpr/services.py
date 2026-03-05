"""
Servicios MPR: lectura de lista de producción y órdenes desde MySQL AdministraNET.

Tablas: lista_produccion_agrupada (por id_articulo), lista_produccion_detalle (por pedido + artículo).
Escritura OPT: movimiento_stock, stock, stock_deposito, lista_produccion_agrupada, lista_produccion_historico.
Tipos: usar core.utils.administranet_types para normalización.
"""
import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_connection, mysql_cursor
from core.services.administranet_stock import get_depositos as _get_depositos_core
from core.utils.administranet_types import to_int_or_none, str_or_default, to_date_or_none

logger = logging.getLogger(__name__)

# Motivo 11 = Pedido producción (OPT), 12 = Parte producción (OPP), 9 = Armado en Synap
MOTIVO_OPT_CODIGO = 11
MOTIVO_OPT_TEXTO = "Pedido producción"
MOTIVO_OPP_CODIGO = 12
MOTIVO_OPP_TEXTO = "Parte producción"
MOTIVO_ARMADO_CODIGO = 9
MOTIVO_ARMADO_TEXTO = "Armado"
MOTIVO_RECLASIFICACION_TEXTO = "Reclasificación"


def _formato_nro_comprobante_mstock(id_pv: int, nro: int) -> str:
    """
    Formato de número de comprobante MSTOCK: PV (4 dígitos) + guión + Nro (8 dígitos).
    Equivalente a VB6: Ceros_Nro_pv(PV) & PV & "-" & Ceros_Nro_Comp(Nro) & Nro.
    En VB6 el Nro usado es el actual del talonario (antes de incrementar).
    """
    return f"{id_pv:04d}-{nro:08d}"


def _first_column_value(row) -> Optional[str]:
    """Devuelve el valor de la primera columna de una fila (tuple o dict)."""
    if not row:
        return None
    if isinstance(row, dict):
        return next(iter(row.values()), None)
    return row[0] if len(row) > 0 else None


def _nombre_tabla(cursor, nombre_lower: str) -> Optional[str]:
    """Devuelve el nombre real de la tabla en el servidor (puede variar mayúsculas/minúsculas)."""
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        nombre = (_first_column_value(row) or "").strip()
        if nombre and nombre.lower() == nombre_lower:
            return nombre
    return None


def _formatear_fecha_dd_mm_yyyy(value: Any) -> str:
    """
    Formatea una fecha para visualización en la UI MPR: dd-MM-yyyy.
    Acepta date, datetime o string (yyyy-mm-dd). Si es None o inválido, devuelve "—".
    """
    if value is None:
        return "—"
    if isinstance(value, (date, datetime)):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, str) and value.strip():
        s = value.strip()[:10]
        try:
            # MySQL/ISO suelen devolver yyyy-mm-dd
            dt = datetime.strptime(s, "%Y-%m-%d")
            return dt.strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            pass
    return "—"


def listar_lista_produccion_agrupada(
    base_empresa: str,
    limit: int = 200,
    id_articulo: Optional[int] = None,
    estado_en_proceso: Optional[str] = None,
    solo_atrasadas: bool = False,
) -> List[Dict[str, Any]]:
    """
    Lista producción agrupada por artículo (lista_produccion_agrupada + articulo).

    estado_en_proceso: None = todos, 'Si' = solo en proceso, 'No' = solo pendientes.
    solo_atrasadas: si True, solo filas con fecha_objetivo no nula y fecha_objetivo < hoy (requiere columna en tabla).
    Devuelve filas con: id_lista_produccion, id_articulo, codigo_articulo, descripcion_articulo,
    cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion. Si las tablas no existen, devuelve [].
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_agrupada or not tbl_articulo:
                logger.debug(
                    "Tablas lista_produccion_agrupada o articulo no encontradas en %s",
                    base_empresa,
                )
                return []
            opts = _columnas_opcionales_op_agrupada(cursor, tbl_agrupada)
            col_fecha = opts.get("fecha_objetivo")
            sql = f"""
                SELECT
                    l.id_lista_produccion,
                    l.id_articulo,
                    COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                    COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                    COALESCE(a.id_manual, '') AS codigo_manual,
                    COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                    COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                    COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion
                FROM {tbl_agrupada} l
                INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                WHERE COALESCE(l.cantidad_pendiente_prod, 0) > 0
            """
            params = []
            if id_articulo is not None:
                sql += " AND l.id_articulo = %s"
                params.append(id_articulo)
            if estado_en_proceso in ("Si", "No"):
                sql += " AND COALESCE(l.en_proceso_produccion, 'No') = %s"
                params.append(estado_en_proceso)
            if solo_atrasadas and col_fecha:
                sql += f" AND l.{col_fecha} IS NOT NULL AND l.{col_fecha} < CURDATE()"
            sql += " ORDER BY l.id_lista_produccion, l.id_articulo LIMIT %s"
            params.append(limit)
            try:
                cursor.execute(sql, params)
            except Exception as col_err:
                if "id_manual" in str(col_err) or "Unknown column" in str(col_err):
                    sql_fallback = f"""
                        SELECT
                            l.id_lista_produccion,
                            l.id_articulo,
                            COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                            COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                            COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                            COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                            COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion
                        FROM {tbl_agrupada} l
                        INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                        WHERE COALESCE(l.cantidad_pendiente_prod, 0) > 0
                    """
                    if id_articulo is not None:
                        sql_fallback += " AND l.id_articulo = %s"
                    if estado_en_proceso in ("Si", "No"):
                        sql_fallback += " AND COALESCE(l.en_proceso_produccion, 'No') = %s"
                    if solo_atrasadas and col_fecha:
                        sql_fallback += f" AND l.{col_fecha} IS NOT NULL AND l.{col_fecha} < CURDATE()"
                    sql_fallback += " ORDER BY l.id_lista_produccion, l.id_articulo LIMIT %s"
                    cursor.execute(sql_fallback, params)
                else:
                    raise col_err
            rows = cursor.fetchall()
        result = []
        for r in rows:
            codigo_manual = r.get("codigo_manual")
            if codigo_manual is None:
                codigo_manual = r.get("codigo_articulo") or "-"
            result.append({
                "id_lista_produccion": to_int_or_none(r.get("id_lista_produccion")),
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "codigo_manual": str_or_default(codigo_manual, "-"),
                "cantidad_pedida": to_int_or_none(r.get("cantidad_pedida")) or 0,
                "cantidad_pendiente_prod": to_int_or_none(r.get("cantidad_pendiente_prod")) or 0,
                "en_proceso_produccion": str_or_default(r.get("en_proceso_produccion"), "No"),
            })
        return result
    except Exception as e:
        logger.warning(
            "Error al listar lista_produccion_agrupada en %s: %s",
            base_empresa,
            e,
            exc_info=True,
        )
        return []


def listar_ops_para_cerrar(base_empresa: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    OPTs con pendiente total 0 y aún en proceso (en_proceso_produccion='Si'), listas para cerrar.
    Solo se muestran las que siguen abiertas; al cerrarlas desaparecen de la lista.
    Devuelve: id_lista_produccion, id_articulo, codigo_articulo, descripcion_articulo (una fila por OPT).
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_agrupada or not tbl_articulo:
                return []
            # Solo OPT con pendiente 0 y que sigan en proceso (al menos una fila con en_proceso_produccion='Si')
            cursor.execute(
                f"""
                SELECT l.id_lista_produccion, l.id_articulo,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(a.NombreArticulo, '') AS descripcion_articulo
                FROM {tbl_agrupada} l
                INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                WHERE l.id_lista_produccion IN (
                    SELECT g.id_lista_produccion
                    FROM {tbl_agrupada} g
                    GROUP BY g.id_lista_produccion
                    HAVING COALESCE(SUM(g.cantidad_pendiente_prod), 0) = 0
                      AND MAX(CASE WHEN UPPER(TRIM(COALESCE(g.en_proceso_produccion, ''))) = 'SI' THEN 1 ELSE 0 END) = 1
                  )
                ORDER BY l.id_lista_produccion
                LIMIT %s
                """,
                [limit],
            )
            rows = cursor.fetchall()
            seen = set()
            result = []
            for r in rows:
                id_lista = to_int_or_none(r.get("id_lista_produccion"))
                if id_lista and id_lista not in seen:
                    seen.add(id_lista)
                    result.append({
                        "id_lista_produccion": id_lista,
                        "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                        "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                    })
            return result
    except Exception as e:
        logger.warning("Error al listar OPTs para cerrar en %s: %s", base_empresa, e, exc_info=True)
        return []


def cerrar_op(base_empresa: str, id_lista_produccion: int) -> Tuple[bool, Optional[str]]:
    """Marca una fila de OPT como cerrada (en_proceso_produccion='No'). Solo si pendiente de esa fila es 0. Devuelve (ok, error)."""
    if not (base_empresa or "").strip():
        return False, "Base de datos no indicada."
    id_lista_produccion = to_int_or_none(id_lista_produccion)
    if not id_lista_produccion:
        return False, "OPT no indicada."
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl:
                return False, "Tabla lista_produccion_agrupada no encontrada."
            cursor.execute(
                f"SELECT COALESCE(SUM(cantidad_pendiente_prod), 0) FROM {tbl} WHERE id_lista_produccion = %s",
                [id_lista_produccion],
            )
            row = cursor.fetchone()
            total_pendiente = (row[0] or 0) if row else 0
            if total_pendiente > 0:
                return False, "No se puede cerrar la OPT con pendiente mayor a 0. Registre OPP hasta completar."
            cursor.execute(
                f"UPDATE {tbl} SET en_proceso_produccion = 'No' WHERE id_lista_produccion = %s",
                [id_lista_produccion],
            )
            conn.commit()
        return True, None
    except Exception as e:
        logger.warning("Error al cerrar OPT %s en %s: %s", id_lista_produccion, base_empresa, e, exc_info=True)
        return False, str(e)


def cerrar_opt(base_empresa: str, id_lista_produccion: int) -> Tuple[bool, Optional[str]]:
    """Cierra la OPT (todas sus líneas). Si es OPT agrupada, cierra todas; si no, cierra esa fila. Pendiente total debe ser 0."""
    lineas = get_opt_detalle(base_empresa, id_lista_produccion)
    if not lineas:
        return False, "OPT no encontrada o sin líneas."
    total_pendiente = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
    if total_pendiente > 0:
        return False, "No se puede cerrar la OPT con pendiente mayor a 0. Registre OPP hasta completar."
    ids_unicos = list({l["id_lista_produccion"] for l in lineas if l.get("id_lista_produccion")})
    for id_lista in ids_unicos:
        ok, err = cerrar_op(base_empresa, id_lista)
        if not ok:
            return False, err
    return True, None


def listar_movimientos_recientes_mpr(base_empresa: str, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Últimos movimientos de stock tipo OPT, OPP o Armado para el tablero.
    Devuelve: icon, title, detail, time (relativo o fecha).
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            if not tbl_mov:
                return []
            try:
                cursor.execute(
                    f"""
                    SELECT codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, tipo_mov, detalle
                    FROM {tbl_mov}
                    WHERE COALESCE(anulado, 'No') = 'No'
                      AND (tipo_mov IN ('OPT', 'OPP', 'Armado') OR motivo_movimiento IN ('Pedido producción', 'Parte producción', 'Armado'))
                    ORDER BY codigo_movimiento DESC
                    LIMIT %s
                    """,
                    [limit],
                )
            except Exception:
                cursor.execute(
                    f"""
                    SELECT codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, detalle
                    FROM {tbl_mov}
                    WHERE COALESCE(anulado, 'No') = 'No'
                      AND motivo_movimiento IN ('Pedido producción', 'Parte producción', 'Armado')
                    ORDER BY codigo_movimiento DESC
                    LIMIT %s
                    """,
                    [limit],
                )
            rows = cursor.fetchall()
        result = []
        for r in rows:
            tipo = (r.get("tipo_mov") or r.get("motivo_movimiento") or "").strip()
            if "OPT" in tipo or "Pedido" in (r.get("motivo_movimiento") or ""):
                icon = "rocket_launch"
                title = "OPT liberada"
            elif "OPP" in tipo or "Parte" in (r.get("motivo_movimiento") or ""):
                icon = "assignment"
                title = "OPP registrada"
            elif "Armado" in tipo:
                icon = "build"
                title = "Armado completado"
            else:
                icon = "inventory_2"
                title = "Movimiento stock"
            detail = f"Comp. {r.get('nro_comprobante') or r.get('codigo_movimiento')}"
            detalle_raw = r.get("detalle")
            if detalle_raw:
                detail = (str(detalle_raw) or "")[:50] or detail
            fecha = r.get("fecha")
            time_str = _formatear_fecha_dd_mm_yyyy(fecha)
            id_lista = None
            if detalle_raw:
                match = re.search(r"lista\s*(\d+)", str(detalle_raw), re.IGNORECASE)
                if match:
                    try:
                        id_lista = int(match.group(1))
                    except (TypeError, ValueError):
                        pass
            result.append({
                "icon": icon, "title": title, "detail": detail, "time": time_str,
                "id_lista": id_lista,
            })
        return result
    except Exception as e:
        logger.warning("Error al listar movimientos recientes MPR en %s: %s", base_empresa, e, exc_info=True)
        return []


def listar_ventana_pack(
    base_empresa: str,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Pedido producción trabajo (OPT): artículos con demanda de producción, stock terminado (depósitos suma_stock='Si')
    y cantidad a fabricar. Útil para decidir qué fabricar.

    Devuelve: id_articulo, codigo_articulo, descripcion_articulo, cantidad_pendiente_prod (demanda),
    stock_terminado, cantidad_a_fabricar (max(0, demanda - stock_terminado)).
    """
    if not (base_empresa or "").strip():
        return []
    try:
        # Demanda: agrupada por artículo (suma cantidad_pendiente_prod)
        agrupada = listar_lista_produccion_agrupada(base_empresa, limit=limit * 2)
        by_art = {}
        for r in agrupada:
            id_art = to_int_or_none(r.get("id_articulo"))
            if id_art is None:
                continue
            if id_art not in by_art:
                by_art[id_art] = {
                    "id_articulo": id_art,
                    "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                    "codigo_manual": str_or_default(r.get("codigo_manual"), "-"),
                    "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                    "cantidad_pedida": 0,
                    "cantidad_pendiente_prod": 0,
                }
            by_art[id_art]["cantidad_pendiente_prod"] += r.get("cantidad_pendiente_prod") or 0
            by_art[id_art]["cantidad_pedida"] += r.get("cantidad_pedida") or 0
        if not by_art:
            return []

        ids = list(by_art.keys())
        # Stock terminado: SUM(saldo) en depósitos con suma_stock='Si'
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            if not tbl_sd or not tbl_dep:
                for v in by_art.values():
                    v["stock_terminado"] = 0
                    v["cantidad_a_fabricar"] = v["cantidad_pendiente_prod"]
                    v["cantidad_urgente_abs"] = max(0, v["cantidad_pendiente_prod"] - 0)  # cant pedida - stock (sin reserva)
                    v["cantidad_urgente"] = v["cantidad_urgente_abs"]
                    v["stock_reserva"] = 0
                    v["stock"] = 0
                    v["brecha_reserva"] = 0
                    v["nombre_unimed"] = "-"
                    v["nombre_presentacion"] = "-"
                    v["cantidad_presentacion"] = None
                    v["detalle_stock_depositos_json"] = json.dumps({"filas": [], "total": 0, "disponible": 0, "reserva": 0})
                return sorted(by_art.values(), key=lambda x: -x["cantidad_pendiente_prod"])[:limit]
            # COALESCE(d.suma_stock,'Si') por si la columna no existe aún
            placeholders = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"""
                SELECT sd.id_articulo, COALESCE(SUM(sd.saldo), 0) AS stock_terminado
                FROM {tbl_sd} sd
                INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
                  AND COALESCE(d.anulado, 'No') = 'No'
                  AND COALESCE(d.suma_stock, 'Si') = 'Si'
                WHERE sd.id_articulo IN ({placeholders})
                GROUP BY sd.id_articulo
                """,
                ids,
            )
            stock_map = {}
            for row in cursor.fetchall():
                id_art = to_int_or_none(row.get("id_articulo"))
                if id_art is not None:
                    try:
                        st = float(row.get("stock_terminado") or 0)
                    except (TypeError, ValueError):
                        st = 0
                    stock_map[id_art] = st  # valor real (puede ser negativo)
            # Desglose por depósito (mismos depósitos) para tooltip en Pend. producción
            detalle_por_art = {}
            try:
                cursor.execute(
                    f"""
                    SELECT sd.id_articulo,
                           COALESCE(d.NombreDeposito, CAST(d.CodDeposito AS CHAR), '') AS deposito,
                           COALESCE(sd.saldo, 0) AS stock_terminado
                    FROM {tbl_sd} sd
                    INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
                      AND COALESCE(d.anulado, 'No') = 'No'
                      AND COALESCE(d.suma_stock, 'Si') = 'Si'
                    WHERE sd.id_articulo IN ({placeholders})
                    ORDER BY sd.id_articulo, d.NombreDeposito, d.CodDeposito
                    """,
                    ids,
                )
                for row in cursor.fetchall():
                    id_art = to_int_or_none(row.get("id_articulo"))
                    if id_art is None:
                        continue
                    if id_art not in detalle_por_art:
                        detalle_por_art[id_art] = []
                    try:
                        saldo = float(row.get("stock_terminado") or 0)
                    except (TypeError, ValueError):
                        saldo = 0
                    detalle_por_art[id_art].append({
                        "deposito": str_or_default(row.get("deposito"), "-"),
                        "stock_terminado": saldo,
                    })
            except Exception:
                detalle_por_art = {}
            # articulo: stock_reserva, id_unimed, id_presentacionV, multiplicador_vta
            tbl_art = _nombre_tabla(cursor, "articulo")
            reserva_map = {}
            art_um_pres_map = {}  # id_art -> {id_unimed, id_presentacionV, multiplicador_vta}
            if tbl_art and ids:
                try:
                    cursor.execute(
                        f"""SELECT IDArt, COALESCE(stock_reserva, 0) AS stock_reserva,
                                   id_unimed, id_presentacionV, COALESCE(multiplicador_vta, 0) AS multiplicador_vta,
                                   id_en_abm
                            FROM {tbl_art} WHERE IDArt IN ({placeholders})""",
                        ids,
                    )
                    for r in cursor.fetchall():
                        aid = to_int_or_none(r.get("IDArt"))
                        if aid is not None:
                            try:
                                reserva_map[aid] = float(r.get("stock_reserva") or 0)
                            except (TypeError, ValueError):
                                reserva_map[aid] = 0
                            try:
                                mult = float(r.get("multiplicador_vta") or 0)
                            except (TypeError, ValueError):
                                mult = 0
                            art_um_pres_map[aid] = {
                                "id_unimed": r.get("id_unimed"),
                                "id_presentacionV": r.get("id_presentacionV"),
                                "multiplicador_vta": mult,
                                "id_en_abm": r.get("id_en_abm"),
                            }
                except Exception:
                    pass
            # unidmed: id_unimed -> nombre_unimed (UM)
            tbl_um = _nombre_tabla(cursor, "unidmed")
            unimed_map = {}
            if tbl_um and art_um_pres_map:
                id_unimeds = list({v["id_unimed"] for v in art_um_pres_map.values() if v.get("id_unimed") is not None})
                if id_unimeds:
                    try:
                        ph_um = ",".join(["%s"] * len(id_unimeds))
                        cursor.execute(
                            f"SELECT id_unimed, COALESCE(nombre_unimed, '') AS nombre_unimed FROM {tbl_um} WHERE id_unimed IN ({ph_um})",
                            id_unimeds,
                        )
                        for r in cursor.fetchall():
                            uid = r.get("id_unimed")
                            if uid is not None:
                                unimed_map[uid] = str_or_default(r.get("nombre_unimed"), "-")
                    except Exception:
                        pass
            # Recetas (BOM) por id_en_abm para tooltip en nombre del artículo
            id_en_abm_set = {v.get("id_en_abm") for v in art_um_pres_map.values() if v.get("id_en_abm") is not None}
            bom_cache = {}
            for id_en_abm in id_en_abm_set:
                bom = get_bom_detalle(base_empresa, to_int_or_none(id_en_abm))
                if bom is not None:
                    bom_cache[to_int_or_none(id_en_abm)] = bom
            # presentacion_abm: id_presentacion -> nombre_presentacion
            tbl_pres = _nombre_tabla(cursor, "presentacion_abm")
            pres_map = {}
            if tbl_pres and art_um_pres_map:
                id_pres = list({v["id_presentacionV"] for v in art_um_pres_map.values() if v.get("id_presentacionV") is not None})
                if id_pres:
                    try:
                        ph_pres = ",".join(["%s"] * len(id_pres))
                        cursor.execute(
                            f"SELECT id_presentacion, COALESCE(nombre_presentacion, '') AS nombre_presentacion FROM {tbl_pres} WHERE id_presentacion IN ({ph_pres})",
                            id_pres,
                        )
                        for r in cursor.fetchall():
                            pid = r.get("id_presentacion")
                            if pid is not None:
                                pres_map[pid] = str_or_default(r.get("nombre_presentacion"), "-")
                    except Exception:
                        pass
            for id_art, row in by_art.items():
                st = stock_map.get(id_art, 0)  # valor real (puede ser negativo)
                row["stock_terminado"] = st
                row["cantidad_a_fabricar"] = max(0, row["cantidad_pendiente_prod"] - st)
                # Urgente = max(0, cant pedida - stock sin reserva)
                row["cantidad_urgente_abs"] = max(0, row["cantidad_pendiente_prod"] - st)
                row["cantidad_urgente"] = row["cantidad_urgente_abs"]
                reserva = reserva_map.get(id_art, 0)
                row["stock_reserva"] = reserva
                row["stock"] = st + reserva  # Stock (terminado + reserva), valor real
                row["brecha_reserva"] = reserva_map.get(id_art, 0) - st
                # UM y presentación
                ap = art_um_pres_map.get(id_art) or {}
                id_um = ap.get("id_unimed")
                row["nombre_unimed"] = unimed_map.get(id_um, "-") if id_um is not None else "-"
                id_pres_v = ap.get("id_presentacionV")
                row["nombre_presentacion"] = pres_map.get(id_pres_v, "-") if id_pres_v is not None else "-"
                mult = ap.get("multiplicador_vta") or 0
                if mult and mult > 0:
                    try:
                        row["cantidad_presentacion"] = round(row["cantidad_a_fabricar"] / mult, 2)
                    except (TypeError, ZeroDivisionError):
                        row["cantidad_presentacion"] = None
                else:
                    row["cantidad_presentacion"] = None
                # Tooltip receta (BOM) en nombre del artículo
                id_en_abm = ap.get("id_en_abm")
                bom = bom_cache.get(to_int_or_none(id_en_abm)) if id_en_abm is not None else None
                if bom and bom.get("componentes"):
                    receta = [
                        {
                            "articulo": str_or_default(c.get("codigo_articulo"), "-") + " — " + str_or_default(c.get("descripcion_articulo"), "-"),
                            "cantidad": float(c.get("cantidad_articulo") or 0),
                        }
                        for c in bom["componentes"]
                    ]
                else:
                    receta = []
                row["receta_json"] = json.dumps(receta)
                # Tooltip Stock: solo depósitos con suma_stock='Si' (como el cálculo del campo) + Reserva
                detalle = detalle_por_art.get(id_art) or []
                total_raw = sum(d.get("stock_terminado", 0) for d in detalle)
                row["detalle_stock_depositos"] = detalle
                row["total_stock_detalle"] = total_raw
                row["disponible_detalle"] = total_raw  # valor real (puede ser negativo)
                row["detalle_stock_depositos_json"] = json.dumps({
                    "filas": detalle,
                    "total": total_raw,
                    "disponible": total_raw,
                    "reserva": reserva,
                })
        return sorted(by_art.values(), key=lambda x: -x["cantidad_a_fabricar"])[:limit]
    except Exception as e:
        logger.warning("Error al listar ventana pack en %s: %s", base_empresa, e, exc_info=True)
        return []


def _listar_unidades_por_demanda(
    base_empresa: str,
    demanda_por_componente: Dict[int, float],
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Desglose por unidades: dado demanda_por_componente (id_articulo -> cantidad),
    devuelve filas con stock, cant a fabricar, urgente, etc. por componente.
    """
    if not demanda_por_componente:
        return []
    ids = list(demanda_por_componente.keys())
    placeholders = ",".join(["%s"] * len(ids))
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_sd or not tbl_dep or not tbl_art:
                return []
            cursor.execute(
                f"""
                SELECT sd.id_articulo, COALESCE(SUM(sd.saldo), 0) AS stock_terminado
                FROM {tbl_sd} sd
                INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
                  AND COALESCE(d.anulado, 'No') = 'No'
                  AND COALESCE(d.suma_stock, 'Si') = 'Si'
                WHERE sd.id_articulo IN ({placeholders})
                GROUP BY sd.id_articulo
                """,
                ids,
            )
            stock_map = {}
            for row in cursor.fetchall():
                id_art = to_int_or_none(row.get("id_articulo"))
                if id_art is not None:
                    try:
                        st = float(row.get("stock_terminado") or 0)
                    except (TypeError, ValueError):
                        st = 0
                    stock_map[id_art] = st  # valor real (puede ser negativo)
            detalle_por_art = {}
            try:
                cursor.execute(
                    f"""
                    SELECT sd.id_articulo,
                           COALESCE(d.NombreDeposito, CAST(d.CodDeposito AS CHAR), '') AS deposito,
                           COALESCE(sd.saldo, 0) AS stock_terminado
                    FROM {tbl_sd} sd
                    INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
                      AND COALESCE(d.anulado, 'No') = 'No'
                      AND COALESCE(d.suma_stock, 'Si') = 'Si'
                    WHERE sd.id_articulo IN ({placeholders})
                    ORDER BY sd.id_articulo, d.NombreDeposito, d.CodDeposito
                    """,
                    ids,
                )
                for row in cursor.fetchall():
                    id_art = to_int_or_none(row.get("id_articulo"))
                    if id_art is None:
                        continue
                    if id_art not in detalle_por_art:
                        detalle_por_art[id_art] = []
                    try:
                        saldo = float(row.get("stock_terminado") or 0)
                    except (TypeError, ValueError):
                        saldo = 0
                    detalle_por_art[id_art].append({
                        "deposito": str_or_default(row.get("deposito"), "-"),
                        "stock_terminado": saldo,
                    })
            except Exception:
                detalle_por_art = {}
            cursor.execute(
                f"""SELECT IDArt, COALESCE(id_manual, '') AS id_manual, COALESCE(NombreArticulo, '') AS NombreArticulo,
                           COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS CodigoArticulo,
                           COALESCE(stock_reserva, 0) AS stock_reserva,
                           id_unimed, id_presentacionV, COALESCE(multiplicador_vta, 0) AS multiplicador_vta
                    FROM {tbl_art} WHERE IDArt IN ({placeholders})""",
                ids,
            )
            art_rows = {to_int_or_none(r.get("IDArt")): r for r in cursor.fetchall() if to_int_or_none(r.get("IDArt")) is not None}
            tbl_um = _nombre_tabla(cursor, "unidmed")
            unimed_map = {}
            id_unimeds = list({to_int_or_none(r.get("id_unimed")) for r in art_rows.values() if r.get("id_unimed") is not None})
            id_unimeds = [x for x in id_unimeds if x is not None]
            if tbl_um and id_unimeds:
                ph = ",".join(["%s"] * len(id_unimeds))
                try:
                    cursor.execute(f"SELECT id_unimed, COALESCE(nombre_unimed, '') AS nombre_unimed FROM {tbl_um} WHERE id_unimed IN ({ph})", id_unimeds)
                    for r in cursor.fetchall():
                        uid = r.get("id_unimed")
                        if uid is not None:
                            unimed_map[uid] = str_or_default(r.get("nombre_unimed"), "-")
                except Exception:
                    pass
            tbl_pres = _nombre_tabla(cursor, "presentacion_abm")
            pres_map = {}
            id_pres = list({r.get("id_presentacionV") for r in art_rows.values() if r.get("id_presentacionV") is not None})
            if tbl_pres and id_pres:
                ph = ",".join(["%s"] * len(id_pres))
                try:
                    cursor.execute(f"SELECT id_presentacion, COALESCE(nombre_presentacion, '') AS nombre_presentacion FROM {tbl_pres} WHERE id_presentacion IN ({ph})", id_pres)
                    for r in cursor.fetchall():
                        pid = r.get("id_presentacion")
                        if pid is not None:
                            pres_map[pid] = str_or_default(r.get("nombre_presentacion"), "-")
                except Exception:
                    pass
            result = []
            for id_art in ids:
                demanda = demanda_por_componente.get(id_art, 0)
                art = art_rows.get(id_art) or {}
                st = stock_map.get(id_art, 0)  # valor real (puede ser negativo)
                reserva = float(art.get("stock_reserva") or 0)
                stock = st + reserva
                cant_a_fabricar = max(0, demanda - stock)
                # Urgente = max(0, cant pedida - stock sin reserva)
                cant_urgente_abs = max(0, demanda - st)
                cant_urgente = cant_urgente_abs
                id_pres_v = art.get("id_presentacionV")
                mult = float(art.get("multiplicador_vta") or 0)
                cant_presentacion = round(cant_a_fabricar / mult, 2) if mult and mult > 0 else None
                detalle = detalle_por_art.get(id_art) or []
                total_raw = sum(d.get("stock_terminado", 0) for d in detalle)
                result.append({
                    "id_articulo": id_art,
                    "codigo_articulo": str_or_default(art.get("CodigoArticulo"), "-"),
                    "codigo_manual": str_or_default(art.get("id_manual"), "-"),
                    "descripcion_articulo": str_or_default(art.get("NombreArticulo"), "-"),
                    "cantidad_pedida": demanda,
                    "cantidad_pendiente_prod": demanda,
                    "stock_terminado": st,
                    "stock_reserva": reserva,
                    "stock": stock,
                    "cantidad_a_fabricar": cant_a_fabricar,
                    "cantidad_urgente": cant_urgente,
                    "cantidad_urgente_abs": cant_urgente_abs,
                    "nombre_unimed": unimed_map.get(art.get("id_unimed"), "-"),
                    "nombre_presentacion": pres_map.get(id_pres_v, "-") if id_pres_v is not None else "-",
                    "cantidad_presentacion": cant_presentacion,
                    "detalle_stock_depositos_json": json.dumps({
                        "filas": detalle,
                        "total": total_raw,
                        "disponible": total_raw,
                        "reserva": reserva,
                    }),
                })
            return sorted(result, key=lambda x: -x["cantidad_a_fabricar"])[:limit]
    except Exception as e:
        logger.warning("Error al listar unidades por demanda en %s: %s", base_empresa, e, exc_info=True)
        return []


def listar_ventana_pack_unidades(
    base_empresa: str,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Desglose por unidades (componentes de las recetas de los packs). Toma los artículos
    de listar_ventana_pack con Cant a producir > 0, explota sus BOM (en_abm_formula),
    agrega la demanda por id_articulo componente y devuelve filas con las mismas columnas
    que la ventana pack. Solo lectura, sin checkbox.
    """
    if not (base_empresa or "").strip():
        return []
    filas_pack = listar_ventana_pack(base_empresa, limit=limit * 2)
    demanda_por_componente: Dict[int, float] = {}
    for r in filas_pack:
        cant = r.get("cantidad_a_fabricar") or 0
        if cant <= 0:
            continue
        id_en_abm = get_id_en_abm_por_articulo(base_empresa, r.get("id_articulo") or 0)
        if id_en_abm is None:
            continue
        bom = get_bom_detalle(base_empresa, id_en_abm)
        if not bom or not bom.get("componentes"):
            continue
        for comp in bom["componentes"]:
            id_comp = to_int_or_none(comp.get("id_articulo"))
            if id_comp is None:
                continue
            qty = float(comp.get("cantidad_articulo") or 0) * float(cant)
            demanda_por_componente[id_comp] = demanda_por_componente.get(id_comp, 0) + qty
    return _listar_unidades_por_demanda(base_empresa, demanda_por_componente, limit)


def listar_unidades_desde_seleccion(
    base_empresa: str,
    filas: List[Dict[str, Any]],
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Desglose por unidades a partir de la selección de la ventana Confirmar OPT.
    filas: lista de dicts con id_articulo y cantidad_a_fabricar (packs seleccionados).
    Devuelve componentes de las recetas (BOM) con cantidades agregadas.
    """
    if not (base_empresa or "").strip() or not filas:
        return []
    demanda_por_componente: Dict[int, float] = {}
    for f in filas:
        id_art = to_int_or_none(f.get("id_articulo"))
        if id_art is None:
            continue
        cant = float(f.get("cantidad_a_fabricar") or 0)
        if cant <= 0:
            continue
        id_en_abm = get_id_en_abm_por_articulo(base_empresa, id_art)
        if id_en_abm is None:
            continue
        bom = get_bom_detalle(base_empresa, id_en_abm)
        if not bom or not bom.get("componentes"):
            continue
        for comp in bom["componentes"]:
            id_comp = to_int_or_none(comp.get("id_articulo"))
            if id_comp is None:
                continue
            qty = float(comp.get("cantidad_articulo") or 0) * cant
            demanda_por_componente[id_comp] = demanda_por_componente.get(id_comp, 0) + qty
    return _listar_unidades_por_demanda(base_empresa, demanda_por_componente, limit)


def actualizar_pedidos_produccion(
    base_empresa: str,
    id_usuario: Optional[int],
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    busqueda: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Réplica del botón "Actualización" en Lista_Pedidos_OPT (VB6 Actualiza_Pedidos_Produccion).
    Carga lista_produccion_detalle y lista_produccion_agrupada desde pedidos PED Pendiente + Fabrica (stockp + comp_ped).
    Devuelve (éxito, mensaje).
    """
    if not (base_empresa or "").strip():
        return False, "Base de datos no indicada."
    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            tbl_stockp = _nombre_tabla(cursor, "stockp")
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not all([tbl_stockp, tbl_cp, tbl_detalle, tbl_agrupada]):
                conn.rollback()
                return False, "Faltan tablas stockp, comp_ped, lista_produccion_detalle o lista_produccion_agrupada."
            # Origen: stockp + comp_ped (PED, Anulado='No', estado_pedido_opt='Pendiente', tipo_pedido_opt='Fabrica')
            sql_origin = f"""
                SELECT cp.CodigoMovimiento AS codigo_movimiento_pedido, sp.IDArt AS id_articulo,
                       COALESCE(sp.cantidad, sp.cantidad_pendiente, sp.Cantidad, 0) AS cantidad
                FROM {tbl_stockp} sp
                INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                WHERE COALESCE(cp.Anulado, 'No') = 'No'
                  AND COALESCE(cp.TipoComprobante, '') = 'PED'
                  AND COALESCE(cp.tipo_pedido_opt, '') = 'Fabrica'
            """
            params_origin = []
            # estado_pedido_opt si existe (algunas bases usan tipo_pedido_opt para Pendiente/Produccion)
            try:
                cursor.execute("SHOW COLUMNS FROM {} LIKE %s".format(tbl_cp.replace("`", "`")), ["estado_pedido_opt"])
                if cursor.fetchone():
                    sql_origin += " AND COALESCE(cp.estado_pedido_opt, '') = 'Pendiente'"
            except Exception:
                pass
            if fecha_desde:
                sql_origin += " AND cp.Fecha >= %s"
                params_origin.append(to_date_or_none(fecha_desde) or str(fecha_desde)[:10])
            if fecha_hasta:
                sql_origin += " AND cp.Fecha <= %s"
                params_origin.append(to_date_or_none(fecha_hasta) or str(fecha_hasta)[:10])
            if busqueda and busqueda.strip():
                sql_origin += " AND (cp.NroCompBusq LIKE %s OR cp.NroComprobante LIKE %s)"
                pct = "%" + busqueda.strip() + "%"
                params_origin.extend([pct, pct])
            cursor.execute(sql_origin, params_origin)
            filas_origen = cursor.fetchall()
            codigos_pedido = list({to_int_or_none(r[0]) for r in filas_origen if to_int_or_none(r[0]) is not None})
            if not filas_origen:
                conn.rollback()
                return False, "No existen pedidos nuevos pendientes para entrar en el proceso de producción."
            hoy = date.today().strftime("%Y-%m-%d")
            id_usuario_val = id_usuario if id_usuario is not None else 0
            # 1) lista_produccion_detalle: INSERT si no existe (codigo_movimiento_pedido, id_articulo)
            for row in filas_origen:
                cod_ped = to_int_or_none(row[0])
                id_art = to_int_or_none(row[1])
                try:
                    qty = int(float(row[2] or 0))
                except (TypeError, ValueError):
                    qty = 0
                if cod_ped is None or id_art is None or qty <= 0:
                    continue
                cursor.execute(
                    f"SELECT 1 FROM {tbl_detalle} WHERE codigo_movimiento_pedido = %s AND id_articulo = %s LIMIT 1",
                    [cod_ped, id_art],
                )
                if cursor.fetchone():
                    continue
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_detalle}
                        (codigo_movimiento_pedido, id_articulo, cantidad_pedida, cantidad_pendiente_prod, id_usuario, en_proceso_produccion, Fecha)
                        VALUES (%s, %s, %s, %s, %s, 'No', %s)
                        """,
                        [cod_ped, id_art, qty, qty, id_usuario_val, hoy],
                    )
                except Exception as ins_err:
                    if "1054" in str(ins_err):
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_detalle}
                            (codigo_movimiento_pedido, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion, Fecha)
                            VALUES (%s, %s, %s, %s, 'No', %s)
                            """,
                            [cod_ped, id_art, qty, qty, hoy],
                        )
                    else:
                        raise ins_err
            # 2) Agregar a lista_produccion_agrupada por id_articulo (SUM desde detalle en_proceso_produccion='No')
            cursor.execute(
                f"""
                SELECT id_articulo, COALESCE(SUM(cantidad_pedida), 0) AS total
                FROM {tbl_detalle}
                WHERE COALESCE(en_proceso_produccion, 'No') = 'No'
                GROUP BY id_articulo
                """,
            )
            sumas = cursor.fetchall()
            for row in sumas:
                id_art = to_int_or_none(row[0])
                try:
                    total = int(float(row[1] or 0))
                except (TypeError, ValueError):
                    total = 0
                if id_art is None or total <= 0:
                    continue
                cursor.execute(
                    f"SELECT id_lista_produccion, cantidad_pedida, cantidad_pendiente_prod FROM {tbl_agrupada} WHERE id_articulo = %s LIMIT 1",
                    [id_art],
                )
                existente = cursor.fetchone()
                if existente:
                    id_lista = existente[0]
                    cant_actual = int(float(existente[1] or 0)) + int(float(existente[2] or 0))
                    cursor.execute(
                        f"UPDATE {tbl_agrupada} SET cantidad_pedida = COALESCE(cantidad_pedida, 0) + %s, cantidad_pendiente_prod = COALESCE(cantidad_pendiente_prod, 0) + %s WHERE id_lista_produccion = %s",
                        [total, total, id_lista],
                    )
                else:
                    try:
                        cursor.execute(
                            f"INSERT INTO {tbl_agrupada} (id_articulo, cantidad_pedida, cantidad_pendiente_prod, id_usuario, en_proceso_produccion) VALUES (%s, %s, %s, %s, 'No')",
                            [id_art, total, total, id_usuario_val],
                        )
                    except Exception as ins_err:
                        if "1054" in str(ins_err):
                            cursor.execute(
                                f"INSERT INTO {tbl_agrupada} (id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion) VALUES (%s, %s, %s, 'No')",
                                [id_art, total, total],
                            )
                        else:
                            raise ins_err
            # 3) Marcar detalle como en proceso
            cursor.execute(
                f"UPDATE {tbl_detalle} SET en_proceso_produccion = 'Si' WHERE COALESCE(en_proceso_produccion, 'No') = 'No'",
            )
            # 4) comp_ped: estado_pedido_opt = 'Produccion' para los codigos involucrados
            if codigos_pedido:
                placeholders = ",".join(["%s"] * len(codigos_pedido))
                try:
                    cursor.execute(
                        f"UPDATE {tbl_cp} SET estado_pedido_opt = 'Produccion' WHERE CodigoMovimiento IN ({placeholders})",
                        codigos_pedido,
                    )
                except Exception as upd_err:
                    if "1054" in str(upd_err):
                        try:
                            cursor.execute(
                                f"UPDATE {tbl_cp} SET tipo_pedido_opt = 'Produccion' WHERE CodigoMovimiento IN ({placeholders})",
                                codigos_pedido,
                            )
                        except Exception:
                            pass
                    else:
                        raise upd_err
            conn.commit()
            return True, "Se actualizaron los nuevos pedidos a producir correctamente."
    except Exception as e:
        logger.warning("Error en actualizar_pedidos_produccion en %s: %s", base_empresa, e, exc_info=True)
        return False, str(e) or "Error al actualizar pedidos de producción."


def listar_lista_produccion_detalle(
    base_empresa: str,
    limit: int = 300,
    codigo_movimiento_pedido: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Lista producción detalle por pedido y artículo (lista_produccion_detalle + articulo).

    Devuelve: codigo_movimiento_pedido, id_articulo, codigo_articulo, descripcion_articulo,
    cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion.
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_detalle or not tbl_articulo:
                return []
            sql = f"""
                SELECT
                    d.codigo_movimiento_pedido,
                    d.id_articulo,
                    COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                    COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                    COALESCE(d.cantidad_pedida, 0) AS cantidad_pedida,
                    COALESCE(d.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                    COALESCE(d.en_proceso_produccion, 'No') AS en_proceso_produccion
                FROM {tbl_detalle} d
                INNER JOIN {tbl_articulo} a ON a.IDArt = d.id_articulo
                WHERE COALESCE(d.cantidad_pendiente_prod, 0) > 0
            """
            params = []
            if codigo_movimiento_pedido is not None:
                sql += " AND d.codigo_movimiento_pedido = %s"
                params.append(codigo_movimiento_pedido)
            sql += " ORDER BY d.codigo_movimiento_pedido, d.id_articulo LIMIT %s"
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "codigo_movimiento_pedido": to_int_or_none(r.get("codigo_movimiento_pedido")),
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "cantidad_pedida": to_int_or_none(r.get("cantidad_pedida")) or 0,
                "cantidad_pendiente_prod": to_int_or_none(r.get("cantidad_pendiente_prod")) or 0,
                "en_proceso_produccion": str_or_default(r.get("en_proceso_produccion"), "No"),
            })
        return result
    except Exception as e:
        logger.warning(
            "Error al listar lista_produccion_detalle en %s: %s",
            base_empresa,
            e,
            exc_info=True,
        )
        return []


def listar_detalle_pedidos_por_articulo(
    base_empresa: str,
    id_articulo: int,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Desglose por pedido para un artículo: lista_produccion_detalle + comp_ped + cliente.
    Para tooltip en Pantalla 2 (Pedido producción trabajo OPT agrupar): fecha, nro_pedido, nombre_cliente, cantidad.
    """
    if not (base_empresa or "").strip() or id_articulo is None:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_cli = _nombre_tabla(cursor, "cliente")
            if not tbl_detalle or not tbl_cp:
                return []
            join_cli = f"LEFT JOIN {tbl_cli} cli ON cli.codigo = cp.codigo" if tbl_cli else ""
            sql = f"""
                SELECT
                    cp.Fecha AS fecha,
                    COALESCE(cp.NroComprobante, cp.NroCompBusq, '') AS nro_pedido,
                    COALESCE(cli.nombre_cliente, '') AS nombre_cliente,
                    COALESCE(d.cantidad_pedida, d.cantidad_pendiente_prod, 0) AS cantidad
                FROM {tbl_detalle} d
                INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = d.codigo_movimiento_pedido
                {join_cli}
                WHERE d.id_articulo = %s
                ORDER BY cp.Fecha DESC, d.codigo_movimiento_pedido
                LIMIT %s
            """
            cursor.execute(sql, [id_articulo, limit])
            rows = cursor.fetchall()
        result = []
        for r in rows:
            fecha_val = r.get("fecha")
            if hasattr(fecha_val, "strftime"):
                fecha_str = fecha_val.strftime("%d-%m-%Y")
            elif isinstance(fecha_val, str) and len(fecha_val) >= 10:
                try:
                    from datetime import datetime as dt
                    fecha_str = dt.strptime(fecha_val[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
                except Exception:
                    fecha_str = str(fecha_val)[:10]
            else:
                fecha_str = str(fecha_val or "-")[:10]
            result.append({
                "fecha": fecha_str,
                "nro_pedido": str_or_default(r.get("nro_pedido"), "-"),
                "nombre_cliente": str_or_default(r.get("nombre_cliente"), "-"),
                "cantidad": to_int_or_none(r.get("cantidad")) or 0,
            })
        return result
    except Exception as e:
        logger.warning("Error en listar_detalle_pedidos_por_articulo en %s: %s", base_empresa, e, exc_info=True)
        return []


def get_op_detalle(
    base_empresa: str,
    id_lista_produccion: int,
) -> List[Dict[str, Any]]:
    """
    Devuelve las líneas de una OPT por id_lista_produccion (lista_produccion_agrupada + articulo).

    Incluye todas las filas con ese id_lista_produccion (con o sin pendiente).
    Formato igual que listar_lista_produccion_agrupada. Lista vacía si no hay datos o tablas.
    """
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_agrupada or not tbl_articulo:
                return []
            sql = f"""
                SELECT
                    l.id_lista_produccion,
                    l.id_articulo,
                    COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                    COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                    COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                    COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                    COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion
                FROM {tbl_agrupada} l
                INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                WHERE l.id_lista_produccion = %s
                ORDER BY l.id_articulo
            """
            cursor.execute(sql, [id_lista_produccion])
            rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "id_lista_produccion": to_int_or_none(r.get("id_lista_produccion")),
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "cantidad_pedida": to_int_or_none(r.get("cantidad_pedida")) or 0,
                "cantidad_pendiente_prod": to_int_or_none(r.get("cantidad_pendiente_prod")) or 0,
                "en_proceso_produccion": str_or_default(r.get("en_proceso_produccion"), "No"),
            })
        return result
    except Exception as e:
        logger.warning(
            "Error al obtener detalle OPT id_lista_produccion=%s en %s: %s",
            id_lista_produccion,
            base_empresa,
            e,
            exc_info=True,
        )
        return []


def get_opt_detalle(
    base_empresa: str,
    id_lista_produccion: int,
) -> List[Dict[str, Any]]:
    """
    Devuelve todas las líneas de la OPT que contiene id_lista_produccion.

    Si id_lista_produccion pertenece a una Opt agrupada (OptLinea), devuelve todas las líneas
    de esa OPT. Si no, devuelve get_op_detalle (una sola línea).
    """
    try:
        from mpr.models import OptLinea

        linea = OptLinea.objects.filter(id_lista_produccion=id_lista_produccion).select_related("opt").first()
        if linea and linea.opt.base_empresa == base_empresa:
            ids = list(
                OptLinea.objects.filter(opt=linea.opt).values_list("id_lista_produccion", flat=True)
            )
            result = []
            for id_lista in ids:
                result.extend(get_op_detalle(base_empresa, id_lista))
            return result
    except Exception as e:
        logger.debug("get_opt_detalle OptLinea: %s", e)
    return get_op_detalle(base_empresa, id_lista_produccion)


def get_op_detalle_by_articulo(
    base_empresa: str,
    id_articulo: int,
) -> List[Dict[str, Any]]:
    """
    Devuelve una sola línea de producción para el artículo (OPT de un solo artículo).

    Útil cuando no hay id_lista_produccion. Formato igual que get_op_detalle.
    """
    if not (base_empresa or "").strip() or id_articulo is None:
        return []
    rows = listar_lista_produccion_agrupada(base_empresa, limit=1, id_articulo=id_articulo)
    return rows


def get_depositos_con_suma_stock(
    base_empresa: str,
    id_puesto: Optional[int],
) -> List[Dict[str, Any]]:
    """
    Lista depósitos (misma lógica que get_depositos) añadiendo suma_stock (Si/No).
    Si la columna no existe en deposito, se asume 'Si' para todos.
    """
    depositos = _get_depositos_core(base_empresa, id_puesto)
    if not depositos:
        return []
    cods = [d.get("CodDeposito") for d in depositos if d.get("CodDeposito") is not None]
    if not cods:
        return depositos
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "deposito")
            if not tbl:
                for d in depositos:
                    d["suma_stock"] = "Si"
                return depositos
            placeholders = ",".join(["%s"] * len(cods))
            cursor.execute(
                f"SELECT CodDeposito, COALESCE(suma_stock, 'Si') AS suma_stock FROM {tbl} WHERE CodDeposito IN ({placeholders})",
                cods,
            )
            mapa = {to_int_or_none(r.get("CodDeposito")): str_or_default(r.get("suma_stock"), "Si") for r in cursor.fetchall()}
        for d in depositos:
            d["suma_stock"] = mapa.get(d.get("CodDeposito"), "Si")
    except Exception:
        for d in depositos:
            d["suma_stock"] = "Si"
    return depositos


def listar_depositos_config(base_empresa: str) -> List[Dict[str, Any]]:
    """Lista todos los depósitos no anulados con suma_stock para Config MPR."""
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "deposito")
            if not tbl:
                return []
            try:
                cursor.execute(
                    f"SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito, COALESCE(suma_stock, 'Si') AS suma_stock FROM {tbl} WHERE COALESCE(anulado, 'No') = 'No' ORDER BY NombreDeposito"
                )
            except Exception:
                cursor.execute(
                    f"SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito FROM {tbl} WHERE COALESCE(anulado, 'No') = 'No' ORDER BY NombreDeposito"
                )
                rows = cursor.fetchall()
                return [{"CodDeposito": r.get("CodDeposito"), "NombreDeposito": str_or_default(r.get("NombreDeposito"), "-"), "suma_stock": "Si"} for r in rows]
            rows = cursor.fetchall()
        return [
            {"CodDeposito": d.get("CodDeposito"), "NombreDeposito": str_or_default(d.get("NombreDeposito"), "-"), "suma_stock": str_or_default(d.get("suma_stock"), "Si")}
            for d in rows
        ]
    except Exception as e:
        logger.warning("Error al listar depósitos config en %s: %s", base_empresa, e, exc_info=True)
        return []


def actualizar_deposito_suma_stock(base_empresa: str, cod_deposito: int, valor: str) -> Tuple[bool, Optional[str]]:
    """Actualiza deposito.suma_stock. valor debe ser 'Si' o 'No'. Devuelve (ok, error)."""
    if not (base_empresa or "").strip():
        return False, "Base de datos no indicada."
    cod_deposito = to_int_or_none(cod_deposito)
    if not cod_deposito:
        return False, "Depósito no indicado."
    valor = (valor or "").strip()
    if valor not in ("Si", "No"):
        return False, "Valor debe ser Si o No."
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "deposito")
            if not tbl:
                return False, "Tabla deposito no encontrada."
            cursor.execute(f"UPDATE {tbl} SET suma_stock = %s WHERE CodDeposito = %s", [valor, cod_deposito])
            conn.commit()
        return True, None
    except Exception as e:
        logger.warning("Error al actualizar suma_stock en %s: %s", base_empresa, e, exc_info=True)
        return False, str(e)


def get_deposito_produccion_mpr(base_empresa: str) -> Optional[int]:
    """Devuelve el id_deposito_produccion configurado para esta base (donde se lleva el stock al liberar OPT)."""
    if not (base_empresa or "").strip():
        return None
    try:
        from mpr.models import MprConfig

        c = MprConfig.objects.filter(base_empresa=base_empresa).first()
        return to_int_or_none(c.id_deposito_produccion) if c else None
    except Exception as e:
        logger.warning("Error al obtener depósito producción MPR para %s: %s", base_empresa, e)
        return None


def set_deposito_produccion_mpr(base_empresa: str, id_deposito: Optional[int]) -> bool:
    """Guarda el depósito de producción para esta base. id_deposito puede ser None para borrar."""
    if not (base_empresa or "").strip():
        return False
    try:
        from mpr.models import MprConfig

        MprConfig.objects.update_or_create(
            base_empresa=base_empresa,
            defaults={"id_deposito_produccion": id_deposito},
        )
        return True
    except Exception as e:
        logger.warning("Error al guardar depósito producción MPR para %s: %s", base_empresa, e)
        return False


def listar_pedidos_fabrica(
    base_empresa: str,
    limit: int = 100,
    estado: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Lista pedidos de venta (comp_ped) con estado de producción (tipo_pedido_opt en Pendiente, Produccion, Terminado).
    El filtro opcional estado filtra por tipo_pedido_opt (Pendiente, Produccion, Terminado).
    Devuelve: CodigoMovimiento, NroComprobante, Fecha, Estado, tipo_pedido_opt, nombre_cliente.
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_cli = _nombre_tabla(cursor, "cliente")
            if not tbl_cp:
                return []
            join_cli = f"LEFT JOIN {tbl_cli} cli ON cli.codigo = cp.codigo" if tbl_cli else ""
            sql = f"""
                SELECT cp.CodigoMovimiento, COALESCE(cp.NroComprobante, '') AS NroComprobante,
                       cp.Fecha, COALESCE(cp.Estado, '') AS Estado,
                       COALESCE(cp.tipo_pedido_opt, '') AS tipo_pedido_opt,
                       COALESCE(cli.nombre_cliente, '') AS nombre_cliente
                FROM {tbl_cp} cp
                {join_cli}
                WHERE COALESCE(cp.Anulado, 'No') = 'No'
                  AND COALESCE(cp.TipoComprobante, '') = 'PED'
                  AND COALESCE(cp.tipo_pedido_opt, '') IN ('Pendiente', 'Produccion', 'Terminado')
            """
            params = []
            if estado:
                sql += " AND cp.tipo_pedido_opt = %s"
                params.append(estado)
            sql += " ORDER BY cp.CodigoMovimiento DESC LIMIT %s"
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [
            {
                "CodigoMovimiento": to_int_or_none(r.get("CodigoMovimiento")),
                "NroComprobante": str_or_default(r.get("NroComprobante"), "-"),
                "Fecha": r.get("Fecha"),
                "Estado": str_or_default(r.get("Estado"), "-"),
                "tipo_pedido_opt": str_or_default(r.get("tipo_pedido_opt"), "-"),
                "nombre_cliente": str_or_default(r.get("nombre_cliente"), "-"),
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Error al listar pedidos fábrica en %s: %s", base_empresa, e, exc_info=True)
        return []


def listar_bom_conjuntos(
    base_empresa: str,
    limit: int = 100,
    solo_activos: bool = True,
    solo_en_produccion: bool = False,
) -> List[Dict[str, Any]]:
    """
    Lista conjuntos de armado (en_abm) con cantidad de componentes y datos del artículo armado.
    Devuelve: id_en_abm, nombre_en_abm, anulado, detalle, descuenta_en, n_componentes,
    id_articulo (IDArt del artículo armado), codigo_manual (id_manual del artículo).
    Si solo_en_produccion=True, solo devuelve conjuntos cuyo artículo armado está en
    lista_produccion_agrupada con cantidad_pendiente_prod > 0 o en_proceso_produccion = 'Si'.
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_abm = _nombre_tabla(cursor, "en_abm")
            tbl_formula = _nombre_tabla(cursor, "en_abm_formula")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl_abm:
                return []
            where = " AND COALESCE(e.anulado, 'No') = 'No'" if solo_activos else ""
            subcount = ""
            if tbl_formula:
                subcount = f", (SELECT COUNT(*) FROM {tbl_formula} f WHERE f.id_en_abm = e.id_en_abm AND COALESCE(f.anulado, 'No') = 'No') AS n_componentes"
            else:
                subcount = ", 0 AS n_componentes"
            join_produccion = ""
            join_articulo = ""
            if solo_en_produccion and tbl_articulo and tbl_agrupada:
                join_produccion = f"""
                INNER JOIN {tbl_articulo} a ON a.id_en_abm = e.id_en_abm AND COALESCE(a.ensamblado, 'No') = 'Si'
                INNER JOIN {tbl_agrupada} l ON l.id_articulo = a.IDArt
                    AND (COALESCE(l.cantidad_pendiente_prod, 0) > 0 OR COALESCE(l.en_proceso_produccion, 'No') = 'Si')
                """
            elif tbl_articulo:
                join_articulo = f"LEFT JOIN {tbl_articulo} a ON a.id_en_abm = e.id_en_abm AND COALESCE(a.ensamblado, 'No') = 'Si'"
            cols_articulo = "a.IDArt AS id_articulo, COALESCE(a.id_manual, '') AS codigo_manual" if tbl_articulo else "NULL AS id_articulo, '' AS codigo_manual"
            sql = f"""
                SELECT DISTINCT e.id_en_abm, COALESCE(e.nombre_en_abm, '') AS nombre_en_abm,
                       COALESCE(e.anulado, 'No') AS anulado, COALESCE(e.detalle, '') AS detalle,
                       COALESCE(e.descuenta_en, '') AS descuenta_en
                       {subcount},
                       {cols_articulo}
                FROM {tbl_abm} e
                {join_produccion}
                {join_articulo}
                WHERE 1=1 {where}
                ORDER BY e.nombre_en_abm, e.id_en_abm
                LIMIT %s
            """
            cursor.execute(sql, [limit])
            rows = cursor.fetchall()
        result = []
        for r in rows:
            item = {
                "id_en_abm": to_int_or_none(r.get("id_en_abm")),
                "nombre_en_abm": str_or_default(r.get("nombre_en_abm"), "-"),
                "anulado": str_or_default(r.get("anulado"), "No"),
                "detalle": str_or_default(r.get("detalle"), ""),
                "descuenta_en": str_or_default(r.get("descuenta_en"), ""),
                "n_componentes": to_int_or_none(r.get("n_componentes")) or 0,
            }
            id_art = to_int_or_none(r.get("id_articulo"))
            item["id_articulo"] = id_art
            item["codigo_manual"] = str_or_default(r.get("codigo_manual"), "-") if id_art else "-"
            result.append(item)
        return result
    except Exception as e:
        logger.warning("Error al listar conjuntos de lista de materiales en %s: %s", base_empresa, e, exc_info=True)
        return []


def get_bom_detalle(
    base_empresa: str,
    id_en_abm: int,
) -> Optional[Dict[str, Any]]:
    """
    Devuelve un conjunto de armado (en_abm) y sus componentes (en_abm_formula + articulo).
    cabecera: id_en_abm, nombre_en_abm, anulado, detalle, descuenta_en.
    componentes: lista de {id_articulo, codigo_articulo, descripcion_articulo, cantidad_articulo, tipo_unidad}.
    """
    if not (base_empresa or "").strip() or id_en_abm is None:
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_abm = _nombre_tabla(cursor, "en_abm")
            tbl_formula = _nombre_tabla(cursor, "en_abm_formula")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_abm:
                return None
            cursor.execute(
                f"""
                SELECT id_en_abm, COALESCE(nombre_en_abm, '') AS nombre_en_abm,
                       COALESCE(anulado, 'No') AS anulado, COALESCE(detalle, '') AS detalle,
                       COALESCE(descuenta_en, '') AS descuenta_en
                FROM {tbl_abm}
                WHERE id_en_abm = %s
                """,
                [id_en_abm],
            )
            row = cursor.fetchone()
            if not row:
                return None
            cabecera = {
                "id_en_abm": to_int_or_none(row.get("id_en_abm")),
                "nombre_en_abm": str_or_default(row.get("nombre_en_abm"), "-"),
                "anulado": str_or_default(row.get("anulado"), "No"),
                "detalle": str_or_default(row.get("detalle"), ""),
                "descuenta_en": str_or_default(row.get("descuenta_en"), ""),
            }
            componentes = []
            if tbl_formula and tbl_articulo:
                cursor.execute(
                    f"""
                    SELECT f.id_en_abm_formula, f.id_articulo, f.cantidad_articulo, COALESCE(f.tipo_unidad, '') AS tipo_unidad,
                           COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                           COALESCE(a.NombreArticulo, '') AS descripcion_articulo
                    FROM {tbl_formula} f
                    INNER JOIN {tbl_articulo} a ON a.IDArt = f.id_articulo
                    WHERE f.id_en_abm = %s AND COALESCE(f.anulado, 'No') = 'No'
                    ORDER BY f.id_en_abm_formula
                    """,
                    [id_en_abm],
                )
                for r in cursor.fetchall():
                    componentes.append({
                        "id_en_abm_formula": to_int_or_none(r.get("id_en_abm_formula")),
                        "id_articulo": to_int_or_none(r.get("id_articulo")),
                        "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                        "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                        "cantidad_articulo": float(r.get("cantidad_articulo") or 0),
                        "tipo_unidad": str_or_default(r.get("tipo_unidad"), ""),
                    })
            return {"cabecera": cabecera, "componentes": componentes}
    except Exception as e:
        logger.warning("Error al obtener detalle lista de materiales id_en_abm=%s en %s: %s", id_en_abm, base_empresa, e, exc_info=True)
        return None


def get_id_en_abm_por_articulo(base_empresa: str, id_articulo: int) -> Optional[int]:
    """
    Devuelve id_en_abm del conjunto de lista de materiales asociado al artículo si es armado (ensamblado='Si', id_en_abm no nulo).
    None si no existe o no es artículo armado.
    """
    if not (base_empresa or "").strip() or id_articulo is None:
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_articulo:
                return None
            cursor.execute(
                f"""
                SELECT a.id_en_abm FROM {tbl_articulo} a
                WHERE a.IDArt = %s AND a.id_en_abm IS NOT NULL AND COALESCE(a.ensamblado, 'No') = 'Si'
                LIMIT 1
                """,
                [id_articulo],
            )
            row = cursor.fetchone()
            if not row or row.get("id_en_abm") is None:
                return None
            return to_int_or_none(row.get("id_en_abm"))
    except Exception as e:
        logger.debug("Error al obtener id_en_abm por artículo %s en %s: %s", id_articulo, base_empresa, e)
        return None


def get_articulo_armado_por_bom(base_empresa: str, id_en_abm: int) -> Optional[Dict[str, Any]]:
    """
    Devuelve el artículo armado (ensamblado='Si', id_en_abm=X): id_articulo, codigo_articulo, descripcion_articulo.
    None si no existe o no hay tabla.
    """
    if not (base_empresa or "").strip() or id_en_abm is None:
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_articulo:
                return None
            cursor.execute(
                f"""
                SELECT a.IDArt AS id_articulo,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(a.NombreArticulo, '') AS descripcion_articulo
                FROM {tbl_articulo} a
                WHERE a.id_en_abm = %s AND COALESCE(a.ensamblado, 'No') = 'Si'
                LIMIT 1
                """,
                [id_en_abm],
            )
            row = cursor.fetchone()
            if not row:
                return None
            return {
                "id_articulo": to_int_or_none(row.get("id_articulo")),
                "codigo_articulo": str_or_default(row.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(row.get("descripcion_articulo"), "-"),
            }
    except Exception as e:
        logger.warning("Error al obtener artículo armado id_en_abm=%s en %s: %s", id_en_abm, base_empresa, e, exc_info=True)
        return None


def get_cantidades_armadas_por_opt(
    base_empresa: str, id_lista_produccion: int
) -> Dict[int, int]:
    """
    Devuelve por cada id_articulo la cantidad ya armada para la OPT dada.
    Busca movimientos tipo Armado cuyo detalle contiene "OPT {id_lista_produccion}"
    y suma las Entrada del artículo armado en la tabla stock.
    Devuelve dict id_articulo -> cantidad_ya_armada (entero).
    """
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return {}
    result = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_mov or not tbl_stock:
                return {}
            # Detalle con "OPT N " o "OPT N)" para no confundir OPT 1 con OPT 12
            patron = f"OPT {id_lista_produccion} "
            patron2 = f"OPT {id_lista_produccion})"
            cursor.execute(
                f"""
                SELECT codigo_movimiento FROM {tbl_mov}
                WHERE UPPER(TRIM(COALESCE(tipo_mov,''))) = 'ARMADO'
                  AND (INSTR(COALESCE(detalle,''), %s) > 0 OR INSTR(COALESCE(detalle,''), %s) > 0)
                  AND COALESCE(anulado,'No') <> 'Si'
                """,
                [patron, patron2],
            )
            codigos = [row["codigo_movimiento"] for row in cursor.fetchall() if row.get("codigo_movimiento")]
            if not codigos:
                return {}
            placeholders = ",".join(["%s"] * len(codigos))
            cursor.execute(
                f"""
                SELECT IDArt, COALESCE(SUM(Entrada), 0) AS total_entrada
                FROM {tbl_stock}
                WHERE CodigoMovimiento IN ({placeholders}) AND COALESCE(Entrada, 0) > 0
                GROUP BY IDArt
                """,
                codigos,
            )
            for row in cursor.fetchall():
                id_art = to_int_or_none(row.get("IDArt"))
                if id_art is not None:
                    result[id_art] = int(float(row.get("total_entrada") or 0))
    except Exception as e:
        logger.warning(
            "Error al obtener cantidades armadas por OPT %s en %s: %s",
            id_lista_produccion,
            base_empresa,
            e,
            exc_info=True,
        )
    return result


def ejecutar_armado(
    base_empresa: str,
    id_usuario: int,
    id_en_abm: int,
    cantidad_a_armar: int,
    deposito_origen: int,
    deposito_destino: int,
    id_lista_produccion: Optional[int] = None,
    id_articulo_armado: Optional[int] = None,
) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    Ejecuta armado (lista de materiales): salidas de componentes desde deposito_origen, entrada del artículo armado en deposito_destino.
    Un movimiento_stock (tipo_mov Armado), renglones stock y actualización stock_deposito.
    Si id_lista_produccion se indica, se graba en detalle para trazabilidad (get_cantidades_armadas_por_opt).
    Devuelve (ok, codigo_movimiento, nro_comprobante, mensaje_error).
    """
    if not (base_empresa or "").strip():
        return False, None, None, "Base de datos no indicada."
    if not id_usuario or not id_en_abm or cantidad_a_armar <= 0:
        return False, None, None, "Datos insuficientes (usuario, conjunto o cantidad)."
    deposito_origen = to_int_or_none(deposito_origen)
    deposito_destino = to_int_or_none(deposito_destino)
    if not deposito_origen or not deposito_destino:
        return False, None, None, "Indique depósito origen (componentes) y destino (producto armado)."
    bom = get_bom_detalle(base_empresa, id_en_abm)
    if not bom or not bom.get("componentes"):
        return False, None, None, "El conjunto no existe o no tiene componentes."
    articulo_armado = get_articulo_armado_por_bom(base_empresa, id_en_abm)
    if not articulo_armado:
        return False, None, None, "No hay artículo armado asociado a este conjunto (articulo.ensamblado=Si, id_en_abm)."
    # Validar descuenta_en = 'Mstock' (alineado con VB6 CargaMovStock)
    descuenta_en = (bom.get("cabecera") or {}).get("descuenta_en") or ""
    if isinstance(descuenta_en, str):
        descuenta_en = descuenta_en.strip()
    if descuenta_en and descuenta_en.upper() != "MSTOCK":
        return (
            False,
            None,
            None,
            "El artículo no está definido para ser utilizado por este proceso (descuenta_en debe ser Mstock).",
        )
    id_ref_movstock = 1
    id_pv = 1
    fecha_mov = date.today().isoformat()
    if id_lista_produccion is not None:
        detalle_mov = f"Armado OPT {id_lista_produccion} (conjunto {id_en_abm}, {cantidad_a_armar} u.)"
    else:
        detalle_mov = f"Armado desde MPR (conjunto {id_en_abm}, {cantidad_a_armar} u.)"
    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            try:
                tbl_codmov = _nombre_tabla(cursor, "codmov")
                tbl_talonarios = _nombre_tabla(cursor, "talonarios")
                tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
                tbl_stock = _nombre_tabla(cursor, "stock")
                tbl_sd = _nombre_tabla(cursor, "stock_deposito")
                tbl_articulo = _nombre_tabla(cursor, "articulo")
                if not all([tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd, tbl_articulo]):
                    conn.rollback()
                    return False, None, None, "Faltan tablas necesarias (codmov, talonarios, movimiento_stock, stock, stock_deposito, articulo)."
                # Tablas y soporte de lote en componentes (FIFO)
                tbl_lote = _nombre_tabla(cursor, "lote")
                tbl_lote_stock = _nombre_tabla(cursor, "lote_stock")
                stock_tiene_id_lote = False
                if tbl_stock:
                    cursor.execute(
                        "SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'id_lote'",
                        [tbl_stock],
                    )
                    stock_tiene_id_lote = cursor.fetchone() is not None
                articulos_con_lote = set()
                if tbl_articulo and bom.get("componentes"):
                    ids_comp = [c["id_articulo"] for c in bom["componentes"]]
                    if ids_comp:
                        placeholders = ",".join(["%s"] * len(ids_comp))
                        cursor.execute(
                            f"SELECT IDArt FROM {tbl_articulo} WHERE IDArt IN ({placeholders}) AND UPPER(TRIM(COALESCE(Lote,''))) = 'SI'",
                            ids_comp,
                        )
                        articulos_con_lote = {row[0] for row in cursor.fetchall()}
                # Validar stock de componentes en deposito_origen
                for comp in bom["componentes"]:
                    qty_necesaria = (comp.get("cantidad_articulo") or 0) * cantidad_a_armar
                    if qty_necesaria <= 0:
                        continue
                    cursor.execute(
                        f"SELECT saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s",
                        [comp["id_articulo"], deposito_origen],
                    )
                    row_sd = cursor.fetchone()
                    saldo = float(row_sd[0] or 0) if row_sd else 0
                    if saldo < qty_necesaria:
                        conn.rollback()
                        return (
                            False,
                            None,
                            None,
                            f"Stock insuficiente de componente {comp.get('codigo_articulo')} en depósito origen: tiene {saldo}, se necesitan {qty_necesaria}.",
                        )
                # Codigo movimiento y talonario
                cursor.execute(f"SELECT CodigoMovimiento FROM {tbl_codmov} WHERE codigo = 1 FOR UPDATE")
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False, None, None, "No se pudo obtener código de movimiento."
                codigo_mov = int(row[0] or 0) + 1
                cursor.execute(f"UPDATE {tbl_codmov} SET CodigoMovimiento = %s WHERE codigo = 1", [codigo_mov])
                cursor.execute(
                    f"SELECT Orden, Nro FROM {tbl_talonarios} WHERE TipoComprobante = 'MSTOCK' AND id_punto_venta = %s FOR UPDATE",
                    [id_pv],
                )
                talon_row = cursor.fetchone()
                if not talon_row:
                    conn.rollback()
                    return False, None, None, "No existe talonario MSTOCK para el punto de venta."
                orden_talon, nro_actual = talon_row[0], int(talon_row[1] or 0)
                nro_nuevo = nro_actual + 1
                cursor.execute(f"UPDATE {tbl_talonarios} SET Nro = %s WHERE Orden = %s", [nro_nuevo, orden_talon])
                nro_comprobante = _formato_nro_comprobante_mstock(id_pv, nro_actual)
                nro_comprobante_busq = nro_actual
                # INSERT movimiento_stock (Armado)
                params_mov = [
                    codigo_mov,
                    nro_comprobante,
                    MOTIVO_ARMADO_TEXTO,
                    fecha_mov,
                    deposito_origen,
                    deposito_destino,
                    detalle_mov,
                    id_usuario,
                    id_ref_movstock,
                    1,
                    None,
                    None,
                    None,
                    "Armado",
                    id_pv,
                    nro_comprobante_busq,
                ]
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov,
                    )
                except Exception as ins_err:
                    if "1054" in str(ins_err):
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_mov}
                            (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                             detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                            """,
                            params_mov[:15],
                        )
                    else:
                        raise ins_err
                orden = 0
                # Salidas de componentes desde deposito_origen
                for comp in bom["componentes"]:
                    qty_salida = Decimal(str((comp.get("cantidad_articulo") or 0) * cantidad_a_armar))
                    if qty_salida <= 0:
                        continue
                    id_art = comp["id_articulo"]
                    codigo_art = str_or_default(comp.get("codigo_articulo"), "-")
                    descripcion_art = str_or_default(comp.get("descripcion_articulo"), "-")
                    cursor.execute(
                        f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                        [id_art, deposito_origen],
                    )
                    sd_row = cursor.fetchone()
                    saldo_actual = Decimal(str(sd_row[1] or 0)) if sd_row else Decimal(0)
                    saldo_despues = saldo_actual - qty_salida
                    usa_lote = (
                        id_art in articulos_con_lote
                        and tbl_lote
                        and tbl_lote_stock
                    )
                    if not usa_lote:
                        orden += 1
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                            """,
                            [
                                codigo_mov,
                                id_art,
                                codigo_art,
                                descripcion_art,
                                fecha_mov,
                                qty_salida,
                                saldo_despues,
                                deposito_origen,
                                id_ref_movstock,
                                orden,
                                id_usuario,
                                MOTIVO_ARMADO_TEXTO,
                                nro_comprobante,
                                None,
                            ],
                        )
                        if sd_row:
                            cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_despues, sd_row[0]])
                        else:
                            cursor.execute(
                                f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                                [id_art, deposito_origen, saldo_despues],
                            )
                    else:
                        # Consumo FIFO desde lotes en depósito origen
                        cursor.execute(
                            f"""
                            SELECT l.id_lote, l.cod_lote, l.fecha_vto_lote, ls.id_lote_stock, ls.stock_lote
                            FROM {tbl_lote} l
                            INNER JOIN {tbl_lote_stock} ls ON ls.id_lote = l.id_lote
                            WHERE l.id_articulo = %s AND ls.id_deposito = %s
                              AND COALESCE(l.anulado,'No') = 'No' AND COALESCE(ls.stock_lote,0) > 0
                            ORDER BY l.fecha_vto_lote ASC
                            FOR UPDATE
                            """,
                            [id_art, deposito_origen],
                        )
                        filas_lote = cursor.fetchall()
                        stock_total_lotes = sum(float(f[4] or 0) for f in filas_lote)
                        if stock_total_lotes < float(qty_salida):
                            conn.rollback()
                            return (
                                False,
                                None,
                                None,
                                f"Stock en lotes insuficiente de componente {codigo_art} en depósito origen: "
                                f"disponible en lotes {stock_total_lotes}, se necesitan {qty_salida}.",
                            )
                        qty_restante = qty_salida
                        for fila in filas_lote:
                            if qty_restante <= 0:
                                break
                            id_lote, cod_lote, fecha_vto_lote, id_lote_stock, stock_lote = (
                                fila[0], fila[1], fila[2], fila[3], Decimal(str(fila[4] or 0)),
                            )
                            tomar = min(stock_lote, qty_restante)
                            nuevo_stock_lote = stock_lote - tomar
                            cursor.execute(
                                f"UPDATE {tbl_lote_stock} SET stock_lote = %s WHERE id_lote_stock = %s",
                                [nuevo_stock_lote, id_lote_stock],
                            )
                            cursor.execute(
                                f"UPDATE {tbl_lote} SET stock_total_lote = COALESCE(stock_total_lote, 0) - %s WHERE id_lote = %s",
                                [tomar, id_lote],
                            )
                            orden += 1
                            saldo_despues_lote = saldo_actual - (qty_salida - qty_restante + tomar)
                            if stock_tiene_id_lote:
                                cursor.execute(
                                    f"""
                                    INSERT INTO {tbl_stock}
                                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_lote)
                                    VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
                                    """,
                                    [
                                        codigo_mov,
                                        id_art,
                                        codigo_art,
                                        descripcion_art,
                                        fecha_mov,
                                        tomar,
                                        saldo_despues_lote,
                                        deposito_origen,
                                        id_ref_movstock,
                                        orden,
                                        id_usuario,
                                        MOTIVO_ARMADO_TEXTO,
                                        nro_comprobante,
                                        None,
                                        id_lote,
                                    ],
                                )
                            else:
                                cursor.execute(
                                    f"""
                                    INSERT INTO {tbl_stock}
                                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                    VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                    """,
                                    [
                                        codigo_mov,
                                        id_art,
                                        codigo_art,
                                        descripcion_art,
                                        fecha_mov,
                                        tomar,
                                        saldo_despues_lote,
                                        deposito_origen,
                                        id_ref_movstock,
                                        orden,
                                        id_usuario,
                                        MOTIVO_ARMADO_TEXTO,
                                        nro_comprobante,
                                        None,
                                    ],
                                )
                            qty_restante -= tomar
                        if sd_row:
                            cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_despues, sd_row[0]])
                        else:
                            cursor.execute(
                                f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                                [id_art, deposito_origen, saldo_despues],
                            )
                # Entrada del artículo armado en deposito_destino
                id_art_arm = articulo_armado["id_articulo"]
                codigo_arm = articulo_armado["codigo_articulo"]
                desc_arm = articulo_armado["descripcion_articulo"]
                entrada_arm = Decimal(str(cantidad_a_armar))
                cursor.execute(
                    f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                    [id_art_arm, deposito_destino],
                )
                sd_dest = cursor.fetchone()
                saldo_dest = Decimal(str(sd_dest[1] or 0)) if sd_dest else Decimal(0)
                saldo_dest_despues = saldo_dest + entrada_arm
                orden += 1
                cursor.execute(
                    f"""
                    INSERT INTO {tbl_stock}
                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                    VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                    """,
                    [
                        codigo_mov,
                        id_art_arm,
                        codigo_arm,
                        desc_arm,
                        fecha_mov,
                        entrada_arm,
                        saldo_dest_despues,
                        deposito_destino,
                        id_ref_movstock,
                        orden,
                        id_usuario,
                        MOTIVO_ARMADO_TEXTO,
                        nro_comprobante,
                        None,
                    ],
                )
                if sd_dest:
                    cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_dest_despues, sd_dest[0]])
                else:
                    cursor.execute(
                        f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                        [id_art_arm, deposito_destino, saldo_dest_despues],
                    )
                conn.commit()
                return True, codigo_mov, nro_comprobante, None
            except Exception as e:
                conn.rollback()
                logger.warning("Error en ejecutar_armado: %s", e, exc_info=True)
                return False, None, None, str(e)
    except Exception as e:
        logger.warning("Error de conexión en ejecutar_armado: %s", e, exc_info=True)
        return False, None, None, str(e)


def crear_conjunto_bom(
    base_empresa: str,
    nombre_en_abm: str,
    detalle: Optional[str] = None,
) -> Tuple[bool, Optional[int], Optional[str]]:
    """Crea un conjunto en_abm. Devuelve (ok, id_en_abm, error)."""
    if not (base_empresa or "").strip():
        return False, None, "Base de datos no indicada."
    nombre_en_abm = (nombre_en_abm or "").strip()
    if not nombre_en_abm:
        return False, None, "Nombre del conjunto es obligatorio."
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "en_abm")
            if not tbl:
                return False, None, "Tabla en_abm no encontrada."
            cursor.execute(f"SELECT COALESCE(MAX(id_en_abm), 0) + 1 FROM {tbl}")
            row = cursor.fetchone()
            id_en_abm = int(float(row[0])) if row and row[0] is not None else 1
            detalle_val = (detalle or "").strip() or ""
            cursor.execute(
                f"INSERT INTO {tbl} (id_en_abm, nombre_en_abm, detalle, anulado) VALUES (%s, %s, %s, 'No')",
                [id_en_abm, nombre_en_abm, detalle_val],
            )
            conn.commit()
        return True, id_en_abm, None
    except Exception as e:
        logger.warning("Error al crear conjunto lista de materiales en %s: %s", base_empresa, e, exc_info=True)
        return False, None, str(e)


def actualizar_conjunto_bom(
    base_empresa: str,
    id_en_abm: int,
    nombre_en_abm: str,
    detalle: Optional[str] = None,
    anulado: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Actualiza en_abm. anulado: 'Si' o 'No'. Devuelve (ok, error)."""
    if not (base_empresa or "").strip():
        return False, "Base de datos no indicada."
    id_en_abm = to_int_or_none(id_en_abm)
    if not id_en_abm:
        return False, "Conjunto no indicado."
    nombre_en_abm = (nombre_en_abm or "").strip()
    if not nombre_en_abm:
        return False, "Nombre del conjunto es obligatorio."
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "en_abm")
            if not tbl:
                return False, "Tabla en_abm no encontrada."
            if anulado is not None and anulado in ("Si", "No"):
                cursor.execute(
                    f"UPDATE {tbl} SET nombre_en_abm = %s, detalle = COALESCE(%s, detalle), anulado = %s WHERE id_en_abm = %s",
                    [nombre_en_abm, (detalle or "").strip() or None, anulado, id_en_abm],
                )
            else:
                cursor.execute(
                    f"UPDATE {tbl} SET nombre_en_abm = %s, detalle = %s WHERE id_en_abm = %s",
                    [nombre_en_abm, (detalle or "").strip() or "", id_en_abm],
                )
            conn.commit()
        return True, None
    except Exception as e:
        logger.warning("Error al actualizar conjunto lista de materiales en %s: %s", base_empresa, e, exc_info=True)
        return False, str(e)


def crear_componente_bom(
    base_empresa: str,
    id_en_abm: int,
    id_articulo: int,
    cantidad_articulo: float,
    tipo_unidad: Optional[str] = None,
) -> Tuple[bool, Optional[int], Optional[str]]:
    """Añade un componente a en_abm_formula. Devuelve (ok, id_en_abm_formula, error)."""
    if not (base_empresa or "").strip():
        return False, None, "Base de datos no indicada."
    id_en_abm = to_int_or_none(id_en_abm)
    id_articulo = to_int_or_none(id_articulo)
    if not id_en_abm or not id_articulo:
        return False, None, "Conjunto y artículo son obligatorios."
    cantidad_articulo = float(cantidad_articulo) if cantidad_articulo is not None else 0
    if cantidad_articulo <= 0:
        return False, None, "Cantidad debe ser mayor que cero."
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "en_abm_formula")
            if not tbl:
                return False, None, "Tabla en_abm_formula no encontrada."
            cursor.execute(f"SELECT COALESCE(MAX(id_en_abm_formula), 0) + 1 FROM {tbl}")
            row = cursor.fetchone()
            id_formula = int(float(row[0])) if row and row[0] is not None else 1
            tipo_unidad_val = (tipo_unidad or "").strip() or ""
            cursor.execute(
                f"INSERT INTO {tbl} (id_en_abm_formula, id_en_abm, id_articulo, cantidad_articulo, anulado, tipo_unidad) VALUES (%s, %s, %s, %s, 'No', %s)",
                [id_formula, id_en_abm, id_articulo, cantidad_articulo, tipo_unidad_val],
            )
            conn.commit()
        return True, id_formula, None
    except Exception as e:
        logger.warning("Error al crear componente lista de materiales en %s: %s", base_empresa, e, exc_info=True)
        return False, None, str(e)


def actualizar_componente_bom(
    base_empresa: str,
    id_en_abm_formula: int,
    id_articulo: int,
    cantidad_articulo: float,
    tipo_unidad: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Actualiza un componente en_abm_formula. Devuelve (ok, error)."""
    if not (base_empresa or "").strip():
        return False, "Base de datos no indicada."
    id_en_abm_formula = to_int_or_none(id_en_abm_formula)
    id_articulo = to_int_or_none(id_articulo)
    if not id_en_abm_formula or not id_articulo:
        return False, "Componente y artículo son obligatorios."
    cantidad_articulo = float(cantidad_articulo) if cantidad_articulo is not None else 0
    if cantidad_articulo <= 0:
        return False, "Cantidad debe ser mayor que cero."
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "en_abm_formula")
            if not tbl:
                return False, "Tabla en_abm_formula no encontrada."
            tipo_unidad_val = (tipo_unidad or "").strip() or ""
            cursor.execute(
                f"UPDATE {tbl} SET id_articulo = %s, cantidad_articulo = %s, tipo_unidad = %s WHERE id_en_abm_formula = %s",
                [id_articulo, cantidad_articulo, tipo_unidad_val, id_en_abm_formula],
            )
            conn.commit()
        return True, None
    except Exception as e:
        logger.warning("Error al actualizar componente lista de materiales en %s: %s", base_empresa, e, exc_info=True)
        return False, str(e)


def set_articulo_armado_bom(
    base_empresa: str,
    id_en_abm: int,
    id_articulo: Optional[int],
) -> Tuple[bool, Optional[str]]:
    """
    Asigna o desasigna el artículo armado del conjunto (lista de materiales).
    - Si id_articulo es válido: quita id_en_abm/ensamblado de otros que tengan este id_en_abm,
      luego pone en el artículo elegido id_en_abm=X y ensamblado='Si'.
    - Si id_articulo es None/0: solo quita la asignación de este conjunto (ningún artículo como armado).
    Devuelve (ok, error).
    """
    if not (base_empresa or "").strip():
        return False, "Base de datos no indicada."
    id_en_abm = to_int_or_none(id_en_abm)
    if not id_en_abm:
        return False, "Conjunto (lista de materiales) no indicado."
    id_articulo = to_int_or_none(id_articulo)
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return False, "Tabla articulo no encontrada."
            # Columnas opcionales en bases antiguas (articulo.id_en_abm, articulo.ensamblado)
            has_id_en_abm = False
            has_ensamblado = False
            try:
                cursor.execute(f"SHOW COLUMNS FROM {tbl_art} LIKE 'id_en_abm'")
                if cursor.fetchone():
                    has_id_en_abm = True
                cursor.execute(f"SHOW COLUMNS FROM {tbl_art} LIKE 'ensamblado'")
                if cursor.fetchone():
                    has_ensamblado = True
            except Exception:
                pass
            if not has_id_en_abm:
                return False, "La tabla articulo no tiene columna id_en_abm."
            # Quitar asignación a cualquier artículo que tenga este id_en_abm
            if has_ensamblado:
                cursor.execute(
                    f"UPDATE {tbl_art} SET id_en_abm = NULL, ensamblado = 'No' WHERE id_en_abm = %s",
                    [id_en_abm],
                )
            else:
                cursor.execute(f"UPDATE {tbl_art} SET id_en_abm = NULL WHERE id_en_abm = %s", [id_en_abm])
            if id_articulo:
                if has_ensamblado:
                    cursor.execute(
                        f"UPDATE {tbl_art} SET id_en_abm = %s, ensamblado = 'Si' WHERE IDArt = %s",
                        [id_en_abm, id_articulo],
                    )
                else:
                    cursor.execute(f"UPDATE {tbl_art} SET id_en_abm = %s WHERE IDArt = %s", [id_en_abm, id_articulo])
            conn.commit()
        return True, None
    except Exception as e:
        logger.warning("Error al asignar artículo armado lista de materiales en %s: %s", base_empresa, e, exc_info=True)
        return False, str(e)


def anular_componente_bom(base_empresa: str, id_en_abm_formula: int) -> Tuple[bool, Optional[str]]:
    """Marca anulado='Si' en en_abm_formula. Devuelve (ok, error)."""
    if not (base_empresa or "").strip():
        return False, "Base de datos no indicada."
    id_en_abm_formula = to_int_or_none(id_en_abm_formula)
    if not id_en_abm_formula:
        return False, "Componente no indicado."
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "en_abm_formula")
            if not tbl:
                return False, "Tabla en_abm_formula no encontrada."
            cursor.execute(f"UPDATE {tbl} SET anulado = 'Si' WHERE id_en_abm_formula = %s", [id_en_abm_formula])
            conn.commit()
        return True, None
    except Exception as e:
        logger.warning("Error al anular componente lista de materiales en %s: %s", base_empresa, e, exc_info=True)
        return False, str(e)


def listar_articulos_para_op(
    base_empresa: str,
    limit: int = 300,
) -> List[Dict[str, Any]]:
    """
    Lista artículos para selector de Nueva OPT (id_articulo, codigo_articulo, descripcion_articulo).
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_articulo:
                return []
            cursor.execute(
                f"""
                SELECT a.IDArt AS id_articulo,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(a.NombreArticulo, '') AS descripcion_articulo
                FROM {tbl_articulo} a
                ORDER BY a.CodigoArticuloT, a.IDArt
                LIMIT %s
                """,
                [limit],
            )
            rows = cursor.fetchall()
        return [
            {
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Error al listar artículos para OPT en %s: %s", base_empresa, e, exc_info=True)
        return []


def _columnas_opcionales_op_agrupada(cursor, tbl_agrupada: str) -> Dict[str, str]:
    """
    Devuelve un dict con los nombres reales de columnas opcionales si existen:
    id_deposito_produccion (o id_deposito), prioridad, fecha_objetivo (o fecha_entrega).
    Clave = nombre estándar, valor = nombre real en la tabla.
    """
    out = {}
    try:
        cursor.execute(f"SHOW COLUMNS FROM {tbl_agrupada}")
        rows = cursor.fetchall()
        col_lower = {}
        for r in rows:
            val = _first_column_value(r)
            if val:
                col_lower[str(val).lower()] = str(val)
        for candidato, nombre_estandar in [
            ("id_deposito_produccion", "id_deposito_produccion"),
            ("id_deposito", "id_deposito_produccion"),
            ("prioridad", "prioridad"),
            ("fecha_objetivo", "fecha_objetivo"),
            ("fecha_entrega", "fecha_objetivo"),
        ]:
            if nombre_estandar in out:
                continue
            for c, real in col_lower.items():
                if c == candidato.lower():
                    out[nombre_estandar] = real
                    break
    except Exception:
        pass
    return out


def listar_columnas_opcionales_nueva_op(base_empresa: str) -> Dict[str, bool]:
    """
    Indica qué columnas opcionales tiene lista_produccion_agrupada para Nueva OPT.
    Devuelve: has_deposito_produccion, has_prioridad, has_fecha_objetivo.
    """
    result = {"has_deposito_produccion": False, "has_prioridad": False, "has_fecha_objetivo": False}
    if not (base_empresa or "").strip():
        return result
    try:
        with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
            tbl = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl:
                return result
            opts = _columnas_opcionales_op_agrupada(cursor, tbl)
            result["has_deposito_produccion"] = "id_deposito_produccion" in opts
            result["has_prioridad"] = "prioridad" in opts
            result["has_fecha_objetivo"] = "fecha_objetivo" in opts
    except Exception as e:
        logger.debug("Error al listar columnas opcionales OPT: %s", e)
    return result


def crear_op_agrupada(
    base_empresa: str,
    id_articulo: int,
    cantidad_pedida: int,
    id_usuario: Optional[int] = None,
    id_deposito_produccion: Optional[int] = None,
    prioridad: Optional[int] = None,
    fecha_objetivo: Optional[date] = None,
) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Crea una nueva orden de producción (una línea en lista_produccion_agrupada).

    Inserta id_articulo, cantidad_pedida, cantidad_pendiente_prod = cantidad_pedida,
    id_usuario, en_proceso_produccion = 'Si' (pasa directo a producción, sin Liberar).
    Si la tabla tiene columnas opcionales (id_deposito_produccion, prioridad, fecha_objetivo), las incluye.
    Devuelve (ok, id_lista_produccion, mensaje_error).
    """
    if not (base_empresa or "").strip():
        return False, None, "Base de datos no indicada."
    id_articulo = to_int_or_none(id_articulo)
    if not id_articulo or cantidad_pedida is None or cantidad_pedida <= 0:
        return False, None, "Indique artículo y cantidad positiva."
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_agrupada or not tbl_articulo:
                return False, None, "No se encontraron tablas lista_produccion_agrupada o articulo."
            opts = _columnas_opcionales_op_agrupada(cursor, tbl_agrupada)
            cols = ["id_articulo", "cantidad_pedida", "cantidad_pendiente_prod", "id_usuario", "en_proceso_produccion"]
            vals = [id_articulo, cantidad_pedida, cantidad_pedida, id_usuario, "Si"]
            if "id_deposito_produccion" in opts and id_deposito_produccion is not None:
                cols.append(opts["id_deposito_produccion"])
                vals.append(id_deposito_produccion)
            if "prioridad" in opts and prioridad is not None:
                cols.append(opts["prioridad"])
                vals.append(prioridad)
            if "fecha_objetivo" in opts and fecha_objetivo is not None:
                cols.append(opts["fecha_objetivo"])
                vals.append(fecha_objetivo)
            placeholders = ", ".join(["%s"] * len(vals))
            col_names = ", ".join(cols)
            cursor.execute(
                f"INSERT INTO {tbl_agrupada} ({col_names}) VALUES ({placeholders})",
                vals,
            )
            id_lista = cursor.lastrowid
            conn.commit()
            return True, id_lista, None
    except Exception as e:
        logger.warning("Error al crear OPT agrupada en %s: %s", base_empresa, e, exc_info=True)
        return False, None, str(e)


def crear_opt_multiples_articulos(
    base_empresa: str,
    id_usuario: Optional[int],
    lineas: List[Tuple[int, int]],
) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Crea una OPT (Pedido de producción) con múltiples artículos.

    lineas: lista de (id_articulo, cantidad) con cantidad > 0.
    Inserta una fila en lista_produccion_agrupada por cada (artículo, cantidad) con en_proceso_produccion='Si'.
    Crea registro Opt y OptLinea en Django para agrupar las líneas.
    Devuelve (ok, id_lista_principal, mensaje_error). id_lista_principal es el primer id_lista_produccion.
    """
    if not (base_empresa or "").strip():
        return False, None, "Base de datos no indicada."
    lineas = [(to_int_or_none(a), to_int_or_none(q)) for a, q in lineas]
    lineas = [(a, q) for a, q in lineas if a and q is not None and q > 0]
    if not lineas:
        return False, None, "Indique al menos un artículo con cantidad positiva."
    try:
        from mpr.models import Opt, OptLinea

        ids_creados = []
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_agrupada or not tbl_articulo:
                return False, None, "No se encontraron tablas lista_produccion_agrupada o articulo."
            opts = _columnas_opcionales_op_agrupada(cursor, tbl_agrupada)
            cols = ["id_articulo", "cantidad_pedida", "cantidad_pendiente_prod", "id_usuario", "en_proceso_produccion"]
            for id_articulo, cantidad in lineas:
                vals = [id_articulo, cantidad, cantidad, id_usuario, "Si"]
                placeholders = ", ".join(["%s"] * len(vals))
                col_names = ", ".join(cols)
                cursor.execute(
                    f"INSERT INTO {tbl_agrupada} ({col_names}) VALUES ({placeholders})",
                    vals,
                )
                ids_creados.append((id_articulo, cantidad, cursor.lastrowid))
            conn.commit()

        id_lista_principal = ids_creados[0][2]
        opt = Opt.objects.create(
            base_empresa=base_empresa,
            id_lista_principal=id_lista_principal,
            id_usuario=id_usuario,
        )
        for id_articulo, cantidad, id_lista in ids_creados:
            OptLinea.objects.create(
                opt=opt,
                id_lista_produccion=id_lista,
                id_articulo=id_articulo,
                cantidad_pedida=cantidad,
            )
        return True, id_lista_principal, None
    except Exception as e:
        logger.warning("Error al crear OPT múltiples artículos en %s: %s", base_empresa, e, exc_info=True)
        return False, None, str(e)


def _distribuir_cantidad_a_lineas(
    lineas: List[Dict[str, Any]],
    cantidad_total: int,
) -> List[Tuple[Dict[str, Any], int]]:
    """
    Reparte cantidad_total entre las líneas en orden: cada línea recibe min(pendiente, restante).
    Devuelve lista de (linea, cantidad_liberada) solo para las que tienen cantidad_liberada > 0.
    """
    restante = cantidad_total
    resultado = []
    for linea in lineas:
        pendiente = linea.get("cantidad_pendiente_prod") or 0
        if restante <= 0 or pendiente <= 0:
            continue
        asignar = min(pendiente, restante)
        restante -= asignar
        resultado.append((linea, asignar))
    return resultado


def ejecutar_liberar_opt(
    base_empresa: str,
    id_usuario: int,
    id_lista_produccion: int,
    lineas: List[Dict[str, Any]],
    cantidad_total: int,
    deposito_destino: int,
) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    Ejecuta la liberación OPT: movimiento_stock (motivo 11, tipo_mov OPT), stock (entradas),
    stock_deposito, y actualiza lista_produccion_agrupada. Opcional: lista_produccion_historico.

    lineas: resultado de get_op_detalle (id_articulo, codigo_articulo, descripcion_articulo, cantidad_pendiente_prod, id_lista_produccion).
    cantidad_total: cantidad total a liberar (se reparte entre líneas en orden).
    Devuelve (ok, codigo_movimiento, nro_comprobante, mensaje_error).
    """
    if not (base_empresa or "").strip():
        return False, None, None, "Base de datos no indicada."
    if not id_usuario or not lineas or cantidad_total <= 0 or not deposito_destino:
        return False, None, None, "Datos insuficientes (usuario, líneas, cantidad o depósito)."
    distribucion = _distribuir_cantidad_a_lineas(lineas, cantidad_total)
    if not distribucion:
        return False, None, None, "No hay cantidad a liberar para las líneas indicadas."
    deposito_destino = to_int_or_none(deposito_destino)
    id_ref_movstock = 1
    id_pv = 1
    fecha_mov = date.today().isoformat()
    detalle_mov = f"OPT {id_lista_produccion} desde MPR"
    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            try:
                # Resolver nombres de tablas
                tbl_codmov = _nombre_tabla(cursor, "codmov")
                tbl_talonarios = _nombre_tabla(cursor, "talonarios")
                tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
                tbl_stock = _nombre_tabla(cursor, "stock")
                tbl_sd = _nombre_tabla(cursor, "stock_deposito")
                tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
                if not all([tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd, tbl_agrupada]):
                    conn.rollback()
                    return False, None, None, "Faltan tablas necesarias (codmov, talonarios, movimiento_stock, stock, stock_deposito, lista_produccion_agrupada)."
                # (1) Siguiente codigo_movimiento
                cursor.execute(f"SELECT CodigoMovimiento FROM {tbl_codmov} WHERE codigo = 1 FOR UPDATE")
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False, None, None, "No se pudo obtener código de movimiento."
                codigo_mov = int(row[0] or 0) + 1
                cursor.execute(f"UPDATE {tbl_codmov} SET CodigoMovimiento = %s WHERE codigo = 1", [codigo_mov])
                # (2) Talonario MSTOCK
                cursor.execute(
                    f"SELECT Orden, Nro FROM {tbl_talonarios} WHERE TipoComprobante = 'MSTOCK' AND id_punto_venta = %s FOR UPDATE",
                    [id_pv],
                )
                talon_row = cursor.fetchone()
                if not talon_row:
                    conn.rollback()
                    return False, None, None, "No existe talonario MSTOCK para el punto de venta."
                orden_talon, nro_actual = talon_row[0], int(talon_row[1] or 0)
                nro_nuevo = nro_actual + 1
                cursor.execute(f"UPDATE {tbl_talonarios} SET Nro = %s WHERE Orden = %s", [nro_nuevo, orden_talon])
                # VB6: Nro comprobante usa el número actual del talonario (antes de incrementar); NroBusq = NroComp
                nro_comprobante = _formato_nro_comprobante_mstock(id_pv, nro_actual)
                nro_comprobante_busq = nro_actual
                # (3) INSERT movimiento_stock (OPT: origen = destino = depósito producción)
                params_mov = [
                    codigo_mov,
                    nro_comprobante,
                    MOTIVO_OPT_TEXTO,
                    fecha_mov,
                    deposito_destino,
                    deposito_destino,
                    detalle_mov,
                    id_usuario,
                    id_ref_movstock,
                    1,    # id_proyecto
                    None, # id_cliente
                    None, # id_vendedor
                    "OPT",
                    id_pv,
                    nro_comprobante_busq,
                ]
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov,
                    )
                except Exception as ins_err:
                    if "1054" in str(ins_err):
                        params_mov_sin_busq = params_mov[:15]  # sin nro_comprobante_busq
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_mov}
                            (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                             detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                            """,
                            params_mov_sin_busq,
                        )
                    else:
                        raise ins_err
                # (4) Por cada (linea, cantidad): INSERT stock, actualizar stock_deposito, actualizar lista_produccion_agrupada
                for idx, (linea, qty) in enumerate(distribucion):
                    id_art = to_int_or_none(linea.get("id_articulo"))
                    codigo_art = str_or_default(linea.get("codigo_articulo"), "-")
                    descripcion_art = str_or_default(linea.get("descripcion_articulo"), "-")
                    entrada = Decimal(str(qty))
                    # Saldo actual en depósito
                    cursor.execute(
                        f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                        [id_art, deposito_destino],
                    )
                    sd_row = cursor.fetchone()
                    saldo_actual = Decimal(str(sd_row[1] or 0)) if sd_row else Decimal(0)
                    saldo_despues = saldo_actual + entrada
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_stock}
                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                        VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                        """,
                        [
                            codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov,
                            entrada, saldo_despues, deposito_destino, id_ref_movstock,
                            idx + 1, id_usuario, MOTIVO_OPT_TEXTO, nro_comprobante, None,
                        ],
                    )
                    if sd_row:
                        cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_despues, sd_row[0]])
                    else:
                        cursor.execute(
                            f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                            [id_art, deposito_destino, saldo_despues],
                        )
                    cursor.execute(
                        f"UPDATE {tbl_agrupada} SET cantidad_pendiente_prod = COALESCE(cantidad_pendiente_prod, 0) - %s "
                        "WHERE id_lista_produccion = %s AND id_articulo = %s",
                        [qty, id_lista_produccion, id_art],
                    )
                # Marcar la OPT como "En proceso" (liberada OPT)
                cursor.execute(
                    f"UPDATE {tbl_agrupada} SET en_proceso_produccion = 'Si' WHERE id_lista_produccion = %s",
                    [id_lista_produccion],
                )
                # (5) Opcional: lista_produccion_historico (trazabilidad OPT; id_articulo_formula siempre grabado)
                tbl_historico = _nombre_tabla(cursor, "lista_produccion_historico")
                if tbl_historico:
                    for idx, (linea, qty) in enumerate(distribucion):
                        id_art = to_int_or_none(linea.get("id_articulo"))
                        # id_articulo_formula: mismo que id_articulo cuando no hay desglose por componente (alineado con VB6)
                        id_art_formula = to_int_or_none(linea.get("id_articulo_formula")) or id_art
                        try:
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_historico}
                                (id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada, id_deposito, codigo_movimiento_mstock, codigo_movimiento_opt)
                                VALUES (%s, %s, %s, %s, 0, %s, %s, %s)
                                """,
                                [
                                    id_art,
                                    id_art_formula,
                                    linea.get("cantidad_pedida") or 0,
                                    qty,
                                    deposito_destino,
                                    codigo_mov,
                                    codigo_mov,
                                ],
                            )
                        except Exception as hist_err:
                            logger.warning("No se pudo insertar lista_produccion_historico: %s", hist_err)
                conn.commit()
                # Vincular codigo_movimiento a la Opt para poder imprimir comprobante desde el detalle
                try:
                    from mpr.models import OptLinea

                    opt_linea = OptLinea.objects.filter(
                        id_lista_produccion=id_lista_produccion
                    ).select_related("opt").first()
                    if opt_linea and opt_linea.opt.base_empresa == base_empresa:
                        opt_linea.opt.codigo_movimiento = codigo_mov
                        opt_linea.opt.save(update_fields=["codigo_movimiento"])
                except Exception as opt_err:
                    logger.warning("No se pudo actualizar Opt.codigo_movimiento: %s", opt_err)
                return True, codigo_mov, nro_comprobante, None
            except Exception as e:
                conn.rollback()
                logger.warning("Error en ejecutar_liberar_opt: %s", e, exc_info=True)
                return False, None, None, str(e)
    except Exception as e:
        logger.warning("Error de conexión en ejecutar_liberar_opt: %s", e, exc_info=True)
        return False, None, None, str(e)


def ejecutar_opp(
    base_empresa: str,
    id_usuario: int,
    id_lista_produccion: int,
    lineas: List[Dict[str, Any]],
    cantidad_total: int,
    deposito_origen: int,
    deposito_destino: int,
) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    Registra Parte de producción (OPP): movimiento Salida desde deposito_origen y Entrada a deposito_destino.
    Crea movimiento_stock (tipo_mov OPP, motivo "Parte producción"), renglones stock (Salida en origen, Entrada en destino)
    y actualiza stock_deposito. Actualiza lista_produccion_agrupada (cantidad_pendiente_prod) para que el pendiente de la OPT baje; opcionalmente stockp (cantidad_fab_pendiente_opt) si existe la columna.

    lineas: resultado de get_op_detalle.
    cantidad_total: se reparte entre líneas en orden.
    Devuelve (ok, codigo_movimiento, nro_comprobante, mensaje_error).
    """
    logger.info(
        "ejecutar_opp entrada: base_empresa=%s id_usuario=%s id_lista_produccion=%s cantidad_total=%s deposito_origen=%s deposito_destino=%s num_lineas=%s",
        base_empresa, id_usuario, id_lista_produccion, cantidad_total, deposito_origen, deposito_destino, len(lineas) if lineas else 0,
    )
    logger.debug(
        "ejecutar_opp tipos: id_usuario=%s cantidad_total=%s deposito_origen=%s deposito_destino=%s",
        type(id_usuario).__name__, type(cantidad_total).__name__, type(deposito_origen).__name__, type(deposito_destino).__name__,
    )
    if not (base_empresa or "").strip():
        return False, None, None, "Base de datos no indicada."
    if not id_usuario or not lineas or cantidad_total <= 0:
        return False, None, None, "Datos insuficientes (usuario, líneas o cantidad)."
    deposito_origen = to_int_or_none(deposito_origen)
    deposito_destino = to_int_or_none(deposito_destino)
    if not deposito_origen or not deposito_destino:
        return False, None, None, "Indique depósito origen y destino."
    en_proceso = (lineas[0].get("en_proceso_produccion") or "No").strip().lower() == "si"
    if not en_proceso:
        return False, None, None, "Debe liberar la OPT antes de registrar la parte de producción (OPP)."
    distribucion = _distribuir_cantidad_a_lineas(lineas, cantidad_total)
    if not distribucion:
        return False, None, None, "No hay cantidad a registrar para las líneas indicadas."
    id_ref_movstock = 1
    id_pv = 1
    fecha_mov = date.today().isoformat()
    detalle_mov = f"OPT {id_lista_produccion} desde MPR"
    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            try:
                tbl_codmov = _nombre_tabla(cursor, "codmov")
                tbl_talonarios = _nombre_tabla(cursor, "talonarios")
                tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
                tbl_stock = _nombre_tabla(cursor, "stock")
                tbl_sd = _nombre_tabla(cursor, "stock_deposito")
                tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
                if not all([tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd]):
                    conn.rollback()
                    return False, None, None, "Faltan tablas necesarias (codmov, talonarios, movimiento_stock, stock, stock_deposito)."
                cursor.execute(f"SELECT CodigoMovimiento FROM {tbl_codmov} WHERE codigo = 1 FOR UPDATE")
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False, None, None, "No se pudo obtener código de movimiento."
                codigo_mov = int(row[0] or 0) + 1
                cursor.execute(f"UPDATE {tbl_codmov} SET CodigoMovimiento = %s WHERE codigo = 1", [codigo_mov])
                cursor.execute(
                    f"SELECT Orden, Nro FROM {tbl_talonarios} WHERE TipoComprobante = 'MSTOCK' AND id_punto_venta = %s FOR UPDATE",
                    [id_pv],
                )
                talon_row = cursor.fetchone()
                if not talon_row:
                    conn.rollback()
                    return False, None, None, "No existe talonario MSTOCK para el punto de venta."
                orden_talon, nro_actual = talon_row[0], int(talon_row[1] or 0)
                nro_nuevo = nro_actual + 1
                cursor.execute(f"UPDATE {tbl_talonarios} SET Nro = %s WHERE Orden = %s", [nro_nuevo, orden_talon])
                nro_comprobante = _formato_nro_comprobante_mstock(id_pv, nro_actual)
                nro_comprobante_busq = nro_actual
                # 17 columnas: 8 primeros + tipo_comprobante/anulado literales + 7 últimos. 15 %s y 15 params.
                params_mov = [
                    codigo_mov, nro_comprobante, MOTIVO_OPP_TEXTO, fecha_mov,
                    deposito_origen, deposito_destino, detalle_mov, id_usuario,
                    id_ref_movstock, None, None, None, "OPP", id_pv, nro_comprobante_busq,
                ]
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov,
                    )
                except Exception as ins_err:
                    if "1054" in str(ins_err):
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_mov}
                            (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                             detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                            """,
                            params_mov[:14],
                        )
                    else:
                        raise ins_err
                orden = 0
                for linea, qty in distribucion:
                    id_art = to_int_or_none(linea.get("id_articulo"))
                    codigo_art = str_or_default(linea.get("codigo_articulo"), "-")
                    descripcion_art = str_or_default(linea.get("descripcion_articulo"), "-")
                    salida = Decimal(str(qty))
                    # Salida desde origen
                    cursor.execute(
                        f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                        [id_art, deposito_origen],
                    )
                    sd_orig = cursor.fetchone()
                    saldo_orig = Decimal(str(sd_orig[1] or 0)) if sd_orig else Decimal(0)
                    saldo_orig_despues = saldo_orig - salida
                    orden += 1
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_stock}
                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                        VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                        """,
                        [
                            codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov,
                            salida, saldo_orig_despues, deposito_origen, id_ref_movstock,
                            orden, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None,
                        ],
                    )
                    if sd_orig:
                        cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_orig_despues, sd_orig[0]])
                    else:
                        cursor.execute(
                            f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                            [id_art, deposito_origen, saldo_orig_despues],
                        )
                    # Entrada a destino
                    cursor.execute(
                        f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                        [id_art, deposito_destino],
                    )
                    sd_dest = cursor.fetchone()
                    saldo_dest = Decimal(str(sd_dest[1] or 0)) if sd_dest else Decimal(0)
                    saldo_dest_despues = saldo_dest + salida
                    orden += 1
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_stock}
                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                        VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                        """,
                        [
                            codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov,
                            salida, saldo_dest_despues, deposito_destino, id_ref_movstock,
                            orden, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None,
                        ],
                    )
                    if sd_dest:
                        cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_dest_despues, sd_dest[0]])
                    else:
                        cursor.execute(
                            f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                            [id_art, deposito_destino, saldo_dest_despues],
                        )
                    # Descontar pendiente de la OPT en lista_produccion_agrupada (cada línea tiene su id_lista_produccion en OPT agrupada)
                    id_lista_linea = to_int_or_none(linea.get("id_lista_produccion")) or id_lista_produccion
                    if tbl_agrupada:
                        try:
                            cursor.execute(
                                f"UPDATE {tbl_agrupada} SET cantidad_pendiente_prod = COALESCE(cantidad_pendiente_prod, 0) - %s WHERE id_lista_produccion = %s AND id_articulo = %s",
                                [qty, id_lista_linea, id_art],
                            )
                        except Exception as agg_err:
                            logger.warning("No se pudo actualizar lista_produccion_agrupada en OPP: %s", agg_err)
                conn.commit()
                return True, codigo_mov, nro_comprobante, None
            except Exception as e:
                conn.rollback()
                logger.exception("Error en ejecutar_opp: %s", e)
                try:
                    primera_linea = lineas[0] if lineas else {}
                    logger.warning(
                        "ejecutar_opp contexto: id_lista_produccion=%s cantidad_total=%s deposito_origen=%s deposito_destino=%s "
                        "primera_linea_keys=%s tipos_valores=%s",
                        id_lista_produccion, cantidad_total, deposito_origen, deposito_destino,
                        list(primera_linea.keys()) if isinstance(primera_linea, dict) else type(primera_linea).__name__,
                        {k: type(v).__name__ for k, v in list(primera_linea.items())[:5]} if isinstance(primera_linea, dict) else None,
                    )
                except Exception as log_err:
                    logger.debug("No se pudo registrar contexto ejecutar_opp: %s", log_err)
                return False, None, None, str(e)
    except Exception as e:
        logger.exception("Error de conexión en ejecutar_opp: %s", e)
        return False, None, None, str(e)


def ejecutar_reclasificacion(
    base_empresa: str,
    id_usuario: int,
    id_articulo: int,
    cantidad: int,
    deposito_origen: int,
    deposito_destino: int,
    detalle: Optional[str] = None,
) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    Reclasificación (ej. a 2da selección o Scrap): salida desde deposito_origen, entrada en deposito_destino.
    Un movimiento_stock tipo Reclasificación, dos renglones stock y actualización stock_deposito.
    Devuelve (ok, codigo_movimiento, nro_comprobante, mensaje_error).
    """
    if not (base_empresa or "").strip():
        return False, None, None, "Base de datos no indicada."
    if not id_usuario or not id_articulo or cantidad <= 0:
        return False, None, None, "Datos insuficientes (usuario, artículo o cantidad)."
    deposito_origen = to_int_or_none(deposito_origen)
    deposito_destino = to_int_or_none(deposito_destino)
    if not deposito_origen or not deposito_destino:
        return False, None, None, "Indique depósito origen y destino."
    if deposito_origen == deposito_destino:
        return False, None, None, "Origen y destino deben ser distintos."
    id_ref_movstock = 1
    id_pv = 1
    fecha_mov = date.today().isoformat()
    detalle_mov = (detalle or "").strip() or f"Reclasificación MPR (art. {id_articulo}, {cantidad} u.)"
    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            try:
                tbl_articulo = _nombre_tabla(cursor, "articulo")
                tbl_codmov = _nombre_tabla(cursor, "codmov")
                tbl_talonarios = _nombre_tabla(cursor, "talonarios")
                tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
                tbl_stock = _nombre_tabla(cursor, "stock")
                tbl_sd = _nombre_tabla(cursor, "stock_deposito")
                if not all([tbl_articulo, tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd]):
                    conn.rollback()
                    return False, None, None, "Faltan tablas necesarias."
                cursor.execute(
                    f"SELECT IDArt, COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo, COALESCE(NombreArticulo, '') AS nombre FROM {tbl_articulo} WHERE IDArt = %s",
                    [id_articulo],
                )
                art_row = cursor.fetchone()
                if not art_row:
                    conn.rollback()
                    return False, None, None, "Artículo no encontrado."
                codigo_art = str(art_row[1]) if art_row[1] else "-"
                descripcion_art = str(art_row[2]) if art_row[2] else "-"
                cursor.execute(
                    f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                    [id_articulo, deposito_origen],
                )
                sd_orig = cursor.fetchone()
                saldo_orig = Decimal(str(sd_orig[1] or 0)) if sd_orig else Decimal(0)
                salida = Decimal(str(cantidad))
                if saldo_orig < salida:
                    conn.rollback()
                    return False, None, None, f"Stock insuficiente en depósito origen: tiene {saldo_orig}, se solicitan {cantidad}."
                cursor.execute(f"SELECT CodigoMovimiento FROM {tbl_codmov} WHERE codigo = 1 FOR UPDATE")
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False, None, None, "No se pudo obtener código de movimiento."
                codigo_mov = int(row[0] or 0) + 1
                cursor.execute(f"UPDATE {tbl_codmov} SET CodigoMovimiento = %s WHERE codigo = 1", [codigo_mov])
                cursor.execute(
                    f"SELECT Orden, Nro FROM {tbl_talonarios} WHERE TipoComprobante = 'MSTOCK' AND id_punto_venta = %s FOR UPDATE",
                    [id_pv],
                )
                talon_row = cursor.fetchone()
                if not talon_row:
                    conn.rollback()
                    return False, None, None, "No existe talonario MSTOCK para el punto de venta."
                orden_talon, nro_actual = talon_row[0], int(talon_row[1] or 0)
                nro_nuevo = nro_actual + 1
                cursor.execute(f"UPDATE {tbl_talonarios} SET Nro = %s WHERE Orden = %s", [nro_nuevo, orden_talon])
                nro_comprobante = _formato_nro_comprobante_mstock(id_pv, nro_actual)
                nro_comprobante_busq = nro_actual
                params_mov = [
                    codigo_mov, nro_comprobante, MOTIVO_RECLASIFICACION_TEXTO, fecha_mov,
                    deposito_origen, deposito_destino, detalle_mov, id_usuario,
                    id_ref_movstock, 1, None, None, None, "Reclasificación", id_pv, nro_comprobante_busq,
                ]
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov,
                    )
                except Exception as ins_err:
                    if "1054" in str(ins_err):
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_mov}
                            (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                             detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                            """,
                            params_mov[:15],
                        )
                    else:
                        raise ins_err
                saldo_orig_despues = saldo_orig - salida
                cursor.execute(
                    f"""
                    INSERT INTO {tbl_stock}
                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                    VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, 1, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                    """,
                    [
                        codigo_mov, id_articulo, codigo_art, descripcion_art, fecha_mov,
                        salida, saldo_orig_despues, deposito_origen, id_ref_movstock,
                        id_usuario, MOTIVO_RECLASIFICACION_TEXTO, nro_comprobante, None,
                    ],
                )
                if sd_orig:
                    cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_orig_despues, sd_orig[0]])
                else:
                    cursor.execute(
                        f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                        [id_articulo, deposito_origen, saldo_orig_despues],
                    )
                cursor.execute(
                    f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                    [id_articulo, deposito_destino],
                )
                sd_dest = cursor.fetchone()
                saldo_dest = Decimal(str(sd_dest[1] or 0)) if sd_dest else Decimal(0)
                saldo_dest_despues = saldo_dest + salida
                cursor.execute(
                    f"""
                    INSERT INTO {tbl_stock}
                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                    VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, 2, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                    """,
                    [
                        codigo_mov, id_articulo, codigo_art, descripcion_art, fecha_mov,
                        salida, saldo_dest_despues, deposito_destino, id_ref_movstock,
                        id_usuario, MOTIVO_RECLASIFICACION_TEXTO, nro_comprobante, None,
                    ],
                )
                if sd_dest:
                    cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_dest_despues, sd_dest[0]])
                else:
                    cursor.execute(
                        f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                        [id_articulo, deposito_destino, saldo_dest_despues],
                    )
                conn.commit()
                return True, codigo_mov, nro_comprobante, None
            except Exception as e:
                conn.rollback()
                logger.warning("Error en ejecutar_reclasificacion: %s", e, exc_info=True)
                return False, None, None, str(e)
    except Exception as e:
        logger.warning("Error de conexión en ejecutar_reclasificacion: %s", e, exc_info=True)
        return False, None, None, str(e)


# --- Reportes MPR (solo lectura) ---


def reporte_mpr_pendiente(base_empresa: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Pendiente por artículo (lista_produccion_agrupada con cantidad_pendiente_prod > 0)."""
    return listar_lista_produccion_agrupada(base_empresa, limit=limit)


def reporte_mpr_wip(base_empresa: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Órdenes en progreso: lista_produccion_agrupada con en_proceso_produccion='Si' y pendiente > 0."""
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_agrupada or not tbl_articulo:
                return []
            cursor.execute(
                f"""
                SELECT l.id_lista_produccion, l.id_articulo,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                       COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                       COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod
                FROM {tbl_agrupada} l
                INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                WHERE COALESCE(l.en_proceso_produccion, 'No') = 'Si' AND COALESCE(l.cantidad_pendiente_prod, 0) > 0
                ORDER BY l.id_lista_produccion, l.id_articulo
                LIMIT %s
                """,
                [limit],
            )
            rows = cursor.fetchall()
        return [
            {
                "id_lista_produccion": to_int_or_none(r.get("id_lista_produccion")),
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "cantidad_pedida": float(r.get("cantidad_pedida") or 0),
                "cantidad_pendiente_prod": float(r.get("cantidad_pendiente_prod") or 0),
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Error reporte_mpr_wip en %s: %s", base_empresa, e, exc_info=True)
        return []


def reporte_mpr_stock(base_empresa: str, limit: int = 500) -> List[Dict[str, Any]]:
    """Stock por artículo y depósito (stock_deposito + deposito + articulo). Solo depósitos con suma_stock='Si' si existe la columna."""
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_sd or not tbl_art:
                return []
            join_dep = f"LEFT JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito" if tbl_dep else ""
            sql = f"""
                SELECT sd.id_articulo, sd.id_deposito, COALESCE(sd.saldo, 0) AS saldo,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                       COALESCE(d.NombreDeposito, '') AS nombre_deposito
                FROM {tbl_sd} sd
                INNER JOIN {tbl_art} a ON a.IDArt = sd.id_articulo
                {join_dep}
                WHERE COALESCE(sd.saldo, 0) != 0
                ORDER BY a.CodigoArticuloT, sd.id_deposito
                LIMIT %s
            """
            cursor.execute(sql, [limit])
            rows = cursor.fetchall()
        return [
            {
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "id_deposito": to_int_or_none(r.get("id_deposito")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "saldo": float(r.get("saldo") or 0),
                "nombre_deposito": str_or_default(r.get("nombre_deposito"), "-"),
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Error reporte_mpr_stock en %s: %s", base_empresa, e, exc_info=True)
        return []


def reporte_mpr_bajo_minimo(base_empresa: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Artículos con stock total (depósitos suma_stock=Si) por debajo del mínimo. Usa deposito_reposicion.stock_minimo o articulo.stock_minimo si existen."""
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            tbl_art = _nombre_tabla(cursor, "articulo")
            tbl_rep = _nombre_tabla(cursor, "deposito_reposicion")
            if not tbl_sd or not tbl_art:
                return []
            # Suma saldo por artículo solo en depósitos con suma_stock='Si'
            try:
                cursor.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'suma_stock'", [tbl_dep])
                tiene_suma = cursor.fetchone() is not None
            except Exception:
                tiene_suma = False
            join_dep = f"INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito AND COALESCE(d.anulado, 'No') = 'No'" if tbl_dep else ""
            where_suma = " AND COALESCE(d.suma_stock, 'Si') = 'Si'" if (tbl_dep and tiene_suma) else ""
            # Stock total por artículo
            sql_stock = f"""
                SELECT sd.id_articulo, SUM(COALESCE(sd.saldo, 0)) AS saldo_total
                FROM {tbl_sd} sd {join_dep}
                WHERE 1=1 {where_suma}
                GROUP BY sd.id_articulo
                HAVING saldo_total > 0
            """
            cursor.execute(sql_stock)
            stocks = {int(r["id_articulo"]): float(r["saldo_total"] or 0) for r in cursor.fetchall()}
            # Mínimos: deposito_reposicion (stock_minimo) o articulo.stock_minimo
            try:
                cursor.execute("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'stock_minimo'", [tbl_art])
                art_tiene_min = cursor.fetchone() is not None
            except Exception:
                art_tiene_min = False
            minimos = {}
            if tbl_rep:
                try:
                    cursor.execute(
                        f"SELECT id_articulo, id_deposito, COALESCE(stock_minimo, 0) AS stock_minimo FROM {tbl_rep} WHERE COALESCE(stock_minimo, 0) > 0"
                    )
                    for r in cursor.fetchall():
                        aid = to_int_or_none(r.get("id_articulo"))
                        if aid:
                            minimos[aid] = minimos.get(aid, 0) + float(r.get("stock_minimo") or 0)
                except Exception:
                    pass
            if art_tiene_min and not minimos:
                cursor.execute(f"SELECT IDArt, COALESCE(stock_minimo, 0) AS stock_minimo FROM {tbl_art} WHERE COALESCE(stock_minimo, 0) > 0")
                for r in cursor.fetchall():
                    aid = to_int_or_none(r.get("IDArt"))
                    if aid:
                        minimos[aid] = float(r.get("stock_minimo") or 0)
            if not minimos:
                return []
            cursor.execute(
                f"SELECT IDArt, COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo_articulo, COALESCE(NombreArticulo, '') AS descripcion_articulo FROM {tbl_art} WHERE IDArt IN (%s)"
                % ",".join(["%s"] * len(minimos)),
                list(minimos.keys()),
            )
            arts = {to_int_or_none(r["IDArt"]): r for r in cursor.fetchall()}
        result = []
        for id_art, minimo in minimos.items():
            saldo = stocks.get(id_art, 0)
            if saldo < minimo:
                a = arts.get(id_art) or {}
                result.append({
                    "id_articulo": id_art,
                    "codigo_articulo": str_or_default(a.get("codigo_articulo"), "-"),
                    "descripcion_articulo": str_or_default(a.get("descripcion_articulo"), "-"),
                    "saldo_total": saldo,
                    "stock_minimo": minimo,
                })
            if len(result) >= limit:
                break
        return result[:limit]
    except Exception as e:
        logger.warning("Error reporte_mpr_bajo_minimo en %s: %s", base_empresa, e, exc_info=True)
        return []
