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

from mpr.exceptions import MprSchemaError, formatear_error_esquema

logger = logging.getLogger(__name__)

# Motivo 11 = Pedido producción (OPT), 12 = Parte producción (OPP), 9 = Armado en Synap
MOTIVO_OPT_CODIGO = 11
MOTIVO_OPT_TEXTO = "Pedido producción"
MOTIVO_OPP_CODIGO = 12
MOTIVO_OPP_TEXTO = "Parte producción"
MOTIVO_ARMADO_CODIGO = 9
MOTIVO_ARMADO_TEXTO = "Armado"
MOTIVO_RECLASIFICACION_TEXTO = "Reclasificación"

# movimiento_stock.tipo_mov: OPT = liberación OPT, OPP = registrar OPP, OPA = armado. tipo_comprobante es el tipo de talonario (MSTOCK).
TIPO_MOV_OPT = "OPT"
TIPO_MOV_OPP = "OPP"
TIPO_MOV_OPA = "OPA"


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


_tabla_cache: Dict[str, Dict[str, Optional[str]]] = {}


def _nombre_tabla(cursor, nombre_lower: str) -> Optional[str]:
    """Devuelve el nombre real de la tabla en el servidor (cachea SHOW TABLES por base)."""
    db_key = ""
    try:
        cursor.execute("SELECT DATABASE()")
        db_key = (_first_column_value(cursor.fetchone()) or "")
    except Exception:
        pass
    if db_key and db_key in _tabla_cache:
        return _tabla_cache[db_key].get(nombre_lower)
    cursor.execute("SHOW TABLES")
    mapa: Dict[str, Optional[str]] = {}
    for row in cursor.fetchall():
        nombre = (_first_column_value(row) or "").strip()
        if nombre:
            mapa[nombre.lower()] = nombre
    if db_key:
        _tabla_cache[db_key] = mapa
    return mapa.get(nombre_lower)


# ---------------------------------------------------------------------------
# Helpers bulk: evitar N+1 al consultar BOM, artículos armados, id_en_abm
# ---------------------------------------------------------------------------

def bulk_id_en_abm(base_empresa: str, id_articulos: List[int]) -> Dict[int, int]:
    """Dado un lote de IDArt, devuelve {id_articulo: id_en_abm} para los que son ensamblados."""
    if not id_articulos:
        return {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "articulo")
            if not tbl:
                return {}
            ph = ",".join(["%s"] * len(id_articulos))
            cursor.execute(
                f"SELECT IDArt, id_en_abm FROM {tbl} WHERE IDArt IN ({ph}) "
                f"AND id_en_abm IS NOT NULL AND COALESCE(ensamblado, 'No') = 'Si'",
                list(id_articulos),
            )
            return {to_int_or_none(r["IDArt"]): to_int_or_none(r["id_en_abm"])
                    for r in cursor.fetchall()
                    if r.get("IDArt") and r.get("id_en_abm")}
    except Exception as e:
        logger.warning("bulk_id_en_abm error: %s", e)
        return {}


def bulk_articulo_armado(base_empresa: str, id_en_abms: List[int]) -> Dict[int, Dict[str, Any]]:
    """Dado un lote de id_en_abm, devuelve {id_en_abm: {id_articulo, codigo_articulo, descripcion_articulo}}."""
    if not id_en_abms:
        return {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "articulo")
            if not tbl:
                return {}
            ph = ",".join(["%s"] * len(id_en_abms))
            cursor.execute(
                f"SELECT a.id_en_abm, a.IDArt AS id_articulo, "
                f"COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo, "
                f"COALESCE(a.NombreArticulo, '') AS descripcion_articulo "
                f"FROM {tbl} a WHERE a.id_en_abm IN ({ph}) AND COALESCE(a.ensamblado, 'No') = 'Si'",
                list(id_en_abms),
            )
            result = {}
            for r in cursor.fetchall():
                abm_id = to_int_or_none(r.get("id_en_abm"))
                if abm_id is not None:
                    result[abm_id] = {
                        "id_articulo": to_int_or_none(r.get("id_articulo")),
                        "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                        "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                    }
            return result
    except Exception as e:
        logger.warning("bulk_articulo_armado error: %s", e)
        return {}


def bulk_bom_detalle(base_empresa: str, id_en_abms: List[int]) -> Dict[int, Dict[str, Any]]:
    """Dado un lote de id_en_abm, devuelve {id_en_abm: {cabecera, componentes}} en 2 queries."""
    if not id_en_abms:
        return {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_abm = _nombre_tabla(cursor, "en_abm")
            tbl_formula = _nombre_tabla(cursor, "en_abm_formula")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_abm:
                return {}
            ph = ",".join(["%s"] * len(id_en_abms))
            cursor.execute(
                f"SELECT id_en_abm, COALESCE(nombre_en_abm, '') AS nombre_en_abm, "
                f"COALESCE(anulado, 'No') AS anulado, COALESCE(detalle, '') AS detalle, "
                f"COALESCE(descuenta_en, '') AS descuenta_en "
                f"FROM {tbl_abm} WHERE id_en_abm IN ({ph})",
                list(id_en_abms),
            )
            cabeceras = {}
            for r in cursor.fetchall():
                abm_id = to_int_or_none(r.get("id_en_abm"))
                if abm_id is not None:
                    cabeceras[abm_id] = {
                        "id_en_abm": abm_id,
                        "nombre_en_abm": str_or_default(r.get("nombre_en_abm"), "-"),
                        "anulado": str_or_default(r.get("anulado"), "No"),
                        "detalle": str_or_default(r.get("detalle"), ""),
                        "descuenta_en": str_or_default(r.get("descuenta_en"), ""),
                    }
            comps_map: Dict[int, list] = {abm_id: [] for abm_id in cabeceras}
            if tbl_formula and tbl_articulo and cabeceras:
                cursor.execute(
                    f"SELECT f.id_en_abm, f.id_en_abm_formula, f.id_articulo, "
                    f"f.cantidad_articulo, COALESCE(f.tipo_unidad, '') AS tipo_unidad, "
                    f"COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo, "
                    f"COALESCE(a.NombreArticulo, '') AS descripcion_articulo "
                    f"FROM {tbl_formula} f INNER JOIN {tbl_articulo} a ON a.IDArt = f.id_articulo "
                    f"WHERE f.id_en_abm IN ({ph}) AND COALESCE(f.anulado, 'No') = 'No' "
                    f"ORDER BY f.id_en_abm, f.id_en_abm_formula",
                    list(id_en_abms),
                )
                for r in cursor.fetchall():
                    abm_id = to_int_or_none(r.get("id_en_abm"))
                    if abm_id in comps_map:
                        comps_map[abm_id].append({
                            "id_en_abm_formula": to_int_or_none(r.get("id_en_abm_formula")),
                            "id_articulo": to_int_or_none(r.get("id_articulo")),
                            "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                            "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                            "cantidad_articulo": float(r.get("cantidad_articulo") or 0),
                            "tipo_unidad": str_or_default(r.get("tipo_unidad"), ""),
                        })
            return {
                abm_id: {"cabecera": cab, "componentes": comps_map.get(abm_id, [])}
                for abm_id, cab in cabeceras.items()
            }
    except Exception as e:
        logger.warning("bulk_bom_detalle error: %s", e)
        return {}


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
                raise MprSchemaError(
                    "Faltan tablas en la base de datos: lista_produccion_agrupada o articulo. "
                    "Cree las tablas o verifique el esquema para usar MPR."
                )
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
    except MprSchemaError:
        raise
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
                raise MprSchemaError(
                    "Faltan tablas en la base de datos: lista_produccion_agrupada o articulo. Cree las tablas o verifique el esquema para usar MPR."
                )
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
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error al listar OPTs para cerrar en %s: %s", base_empresa, e, exc_info=True)
        return []


def listar_opt_en_proceso(base_empresa: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    OPTs ya liberadas y en proceso (en_proceso_produccion='Si'), sin filtrar por pendiente.
    Una fila por OPT con id_lista_produccion, descripción y unidades para el tablero.
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_agrupada or not tbl_articulo:
                raise MprSchemaError(
                    "Faltan tablas en la base de datos: lista_produccion_agrupada o articulo. Cree las tablas o verifique el esquema para usar MPR."
                )
            cursor.execute(
                f"""
                SELECT l.id_lista_produccion, l.id_articulo,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                       COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                       COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod
                FROM {tbl_agrupada} l
                INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                WHERE l.id_lista_produccion IN (
                    SELECT g.id_lista_produccion
                    FROM {tbl_agrupada} g
                    GROUP BY g.id_lista_produccion
                    HAVING MAX(CASE WHEN UPPER(TRIM(COALESCE(g.en_proceso_produccion, ''))) = 'SI' THEN 1 ELSE 0 END) = 1
                )
                ORDER BY l.id_lista_produccion, l.id_articulo
                LIMIT %s
                """,
                [max(limit * 20, 200)],
            )
            rows = cursor.fetchall()
        seen = set()
        result = []
        for r in rows or []:
            id_lista = to_int_or_none(r.get("id_lista_produccion"))
            if id_lista is None or id_lista in seen:
                continue
            seen.add(id_lista)
            desc = str_or_default(r.get("descripcion_articulo"), "-")
            if len(desc) > 45:
                desc = desc[:42] + "..."
            result.append({
                "id_lista_produccion": id_lista,
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": desc,
                "cantidad_pedida": to_int_or_none(r.get("cantidad_pedida")) or 0,
                "cantidad_pendiente_prod": to_int_or_none(r.get("cantidad_pendiente_prod")) or 0,
            })
            if len(result) >= limit:
                break
        return result
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error al listar OPTs en proceso en %s: %s", base_empresa, e, exc_info=True)
        return []


def estado_acciones_opt(
    base_empresa: str, id_lista_produccion: int
) -> Dict[str, Any]:
    """
    Estado y acciones disponibles para una OPT en proceso.
    Devuelve: total_pendiente_opp, puede_crear_opp, puede_crear_opa, puede_cerrar.
    Usado por el tablero para mostrar el botón principal (Crear OPP, Crear OPA o Cerrar).
    """
    out = {
        "total_pendiente_opp": 0,
        "puede_crear_opp": False,
        "puede_crear_opa": False,
        "puede_cerrar": False,
    }
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return out
    try:
        lineas = get_opt_detalle(base_empresa, id_lista_produccion)
        if not lineas:
            lineas = get_op_detalle(base_empresa, id_lista_produccion)
        total_pendiente_opp = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
        out["total_pendiente_opp"] = total_pendiente_opp
        out["puede_crear_opp"] = total_pendiente_opp > 0

        lineas_armado = get_lineas_armado_opt(base_empresa, id_lista_produccion)
        cantidades_armadas = get_cantidades_armadas_por_opt(base_empresa, id_lista_produccion)
        hay_restante_armar = False
        for linea in lineas:
            id_art = linea.get("id_articulo")
            if id_art is None:
                continue
            cantidad_pedida = linea.get("cantidad_pedida") or 0
            cantidad_ya_armada = cantidades_armadas.get(id_art, 0)
            restante = max(0, cantidad_pedida - cantidad_ya_armada)
            if restante > 0:
                hay_restante_armar = True
                break
        tiene_lineas_armado = bool(lineas_armado)
        puede_armar = tiene_lineas_armado and hay_restante_armar
        if puede_armar and lineas_armado:
            alguno_armable = any((ln.get("max_packs_armable") or 0) > 0 for ln in lineas_armado)
            puede_armar = puede_armar and alguno_armable
        out["puede_crear_opa"] = puede_armar
        out["puede_cerrar"] = total_pendiente_opp == 0 and not hay_restante_armar
    except Exception as e:
        logger.warning(
            "Error en estado_acciones_opt id_lista=%s en %s: %s",
            id_lista_produccion,
            base_empresa,
            e,
            exc_info=True,
        )
    return out


def _actualizar_comp_ped_estado_produccion(
    cursor,
    tbl_cp: str,
    codigos_movimiento: List[int],
    estado: str,
) -> None:
    """
    Actualiza comp_ped.estado_pedido_opt al valor indicado para los CodigoMovimiento dados.
    estado: 'Produccion' o 'Terminado'.
    """
    if not codigos_movimiento:
        return
    placeholders = ",".join(["%s"] * len(codigos_movimiento))
    if estado == "Terminado":
        cursor.execute(
            f"UPDATE {tbl_cp} SET estado_pedido_opt = 'Terminado' "
            f"WHERE CodigoMovimiento IN ({placeholders}) AND COALESCE(estado_pedido_opt, '') = 'Produccion'",
            codigos_movimiento,
        )
    else:
        cursor.execute(
            f"UPDATE {tbl_cp} SET estado_pedido_opt = %s WHERE CodigoMovimiento IN ({placeholders})",
            [estado] + codigos_movimiento,
        )


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
                raise MprSchemaError(
                    "Falta la tabla lista_produccion_agrupada en la base de datos. Cree la tabla o verifique el esquema para usar MPR."
                )
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
            hora_salida_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                f"SELECT codigo_movimiento_opt FROM {tbl} WHERE id_lista_produccion = %s AND codigo_movimiento_opt IS NOT NULL LIMIT 1",
                [id_lista_produccion],
            )
            row_cod = cursor.fetchone()
            codigo_mov_opt = to_int_or_none(row_cod[0]) if row_cod and row_cod[0] is not None else None
            if codigo_mov_opt is not None:
                tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
                if tbl_mov:
                    try:
                        cursor.execute(
                            f"UPDATE {tbl_mov} SET hora_salida_opt = %s WHERE codigo_movimiento = %s",
                            [hora_salida_dt, codigo_mov_opt],
                        )
                    except Exception as upd_err:
                        if "1054" in str(upd_err) or "Unknown column" in str(upd_err).lower():
                            try:
                                cursor.execute(
                                    f"UPDATE {tbl_mov} SET hora_salida = %s WHERE codigo_movimiento = %s",
                                    [hora_salida_dt, codigo_mov_opt],
                                )
                            except Exception as _:
                                pass
                        else:
                            logger.warning("No se pudo actualizar hora_salida_opt en movimiento_stock: %s", upd_err)
            conn.commit()
        return True, None
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error al cerrar OPT %s en %s: %s", id_lista_produccion, base_empresa, e, exc_info=True)
        return False, str(e)


def cerrar_opt(base_empresa: str, id_lista_produccion: int) -> Tuple[bool, Optional[str]]:
    """Cierra la OPT (todas sus líneas). Si es OPT agrupada, cierra todas; si no, cierra esa fila. Pendiente total debe ser 0.
    Actualiza comp_ped.estado_pedido_opt a 'Terminado' para los pedidos asociados a esta OPT."""
    lineas = get_opt_detalle(base_empresa, id_lista_produccion)
    if not lineas:
        return False, "OPT no encontrada o sin líneas."
    total_pendiente = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
    if total_pendiente > 0:
        return False, "No se puede cerrar la OPT con pendiente mayor a 0. Registre OPP hasta completar."
    # Marcar pedidos asociados a esta OPT como Terminado (id_articulo de las líneas → detalle → codigo_movimiento_pedido)
    ids_articulo = list({l["id_articulo"] for l in lineas if l.get("id_articulo") is not None})
    if ids_articulo:
        try:
            with get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
                tbl_cp = _nombre_tabla(cursor, "comp_ped")
                if tbl_detalle and tbl_cp:
                    ph = ",".join(["%s"] * len(ids_articulo))
                    cursor.execute(
                        f"SELECT DISTINCT codigo_movimiento_pedido FROM {tbl_detalle} WHERE id_articulo IN ({ph})",
                        ids_articulo,
                    )
                    codigos = [to_int_or_none(r[0]) for r in cursor.fetchall() if to_int_or_none(r[0]) is not None]
                    if codigos:
                        _actualizar_comp_ped_estado_produccion(cursor, tbl_cp, codigos, "Terminado")
                conn.commit()
        except Exception as e:
            logger.warning("Error al actualizar comp_ped a Terminado al cerrar OPT %s: %s", id_lista_produccion, e)
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
                      AND (tipo_mov IN ('OPT', 'OPP', 'OPA', 'Armado') OR motivo_movimiento IN ('Pedido producción', 'Parte producción', 'Armado'))
                    ORDER BY codigo_movimiento DESC
                    LIMIT %s
                    """,
                    [limit],
                )
            except Exception as e1:
                if "1054" in str(e1) or "Unknown column" in str(e1).lower():
                    raise MprSchemaError(formatear_error_esquema(e1, "movimiento_stock")) from e1
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
            elif "OPA" in tipo or "Armado" in tipo:
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
    except MprSchemaError:
        raise
    except Exception as e:
        if "1054" in str(e) or "Unknown column" in str(e).lower():
            raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
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
    stock_terminado, stock_reserva (indicador, no saldo), cantidad_a_fabricar (max(0, demanda - stock_terminado + stock_reserva)),
    cantidad_urgente_abs (max(0, demanda - stock_terminado); la reserva no interviene).
    """
    if not (base_empresa or "").strip():
        return []
    try:
        # Demanda: solo pendiente no asignada a OPT (en_proceso_produccion='No'), para no mostrar
        # artículos que ya están en una OPT creada/liberada.
        agrupada = listar_lista_produccion_agrupada(
            base_empresa, limit=limit * 2, estado_en_proceso="No"
        )
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
        # Restar cantidades ya asignadas a OPTs (lista_produccion_agrupada con id_opt IS NOT NULL).
        try:
            with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
                tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
                if tbl_agrupada:
                    cursor.execute(
                        f"SELECT id_articulo, COALESCE(SUM(cantidad_pedida), 0) AS total FROM {tbl_agrupada} WHERE id_opt IS NOT NULL GROUP BY id_articulo"
                    )
                    opt_totals = {to_int_or_none(r.get("id_articulo")): (r.get("total") or 0) for r in cursor.fetchall() if to_int_or_none(r.get("id_articulo")) is not None}
                    for id_art in list(by_art.keys()):
                        restar = int(float(opt_totals.get(id_art, 0) or 0))
                        if restar <= 0:
                            continue
                        by_art[id_art]["cantidad_pendiente_prod"] = max(
                            0, (by_art[id_art]["cantidad_pendiente_prod"] or 0) - restar
                        )
                        by_art[id_art]["cantidad_pedida"] = max(
                            0, (by_art[id_art]["cantidad_pedida"] or 0) - restar
                        )
                        if by_art[id_art]["cantidad_pendiente_prod"] <= 0:
                            del by_art[id_art]
        except Exception as e:
            logger.debug("No se pudo restar cantidades OPT (agrupada id_opt) en ventana-pack: %s", e)
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
            bom_cache = bulk_bom_detalle(base_empresa, [to_int_or_none(x) for x in id_en_abm_set if x is not None])
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
                reserva = reserva_map.get(id_art, 0)
                row["stock_terminado"] = st
                row["cantidad_a_fabricar"] = max(0, row["cantidad_pendiente_prod"] - st + reserva)
                # Urgente = max(0, cant pedida - saldo); la reserva no interviene
                row["cantidad_urgente_abs"] = max(0, row["cantidad_pendiente_prod"] - st)
                row["cantidad_urgente"] = row["cantidad_urgente_abs"]
                row["stock_reserva"] = reserva
                row["stock"] = st  # Solo suma de saldos; reserva no se usa para saldos
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
    except MprSchemaError:
        raise
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
                cant_a_fabricar = max(0, demanda - st + reserva)
                # Urgente = max(0, cant pedida - saldo); la reserva no interviene
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
                    "stock": st,
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
    art_ids = [to_int_or_none(r.get("id_articulo")) for r in filas_pack if (r.get("cantidad_a_fabricar") or 0) > 0]
    art_ids = [a for a in art_ids if a is not None]
    abm_map = bulk_id_en_abm(base_empresa, art_ids) if art_ids else {}
    bom_map = bulk_bom_detalle(base_empresa, list(set(abm_map.values()))) if abm_map else {}
    demanda_por_componente: Dict[int, float] = {}
    for r in filas_pack:
        cant = r.get("cantidad_a_fabricar") or 0
        if cant <= 0:
            continue
        id_en_abm = abm_map.get(to_int_or_none(r.get("id_articulo")))
        if id_en_abm is None:
            continue
        bom = bom_map.get(id_en_abm)
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
    art_ids = [to_int_or_none(f.get("id_articulo")) for f in filas if float(f.get("cantidad_a_fabricar") or 0) > 0]
    art_ids = [a for a in art_ids if a is not None]
    abm_map = bulk_id_en_abm(base_empresa, art_ids) if art_ids else {}
    bom_map = bulk_bom_detalle(base_empresa, list(set(abm_map.values()))) if abm_map else {}
    demanda_por_componente: Dict[int, float] = {}
    for f in filas:
        id_art = to_int_or_none(f.get("id_articulo"))
        if id_art is None:
            continue
        cant = float(f.get("cantidad_a_fabricar") or 0)
        if cant <= 0:
            continue
        id_en_abm = abm_map.get(id_art)
        if id_en_abm is None:
            continue
        bom = bom_map.get(id_en_abm)
        if not bom or not bom.get("componentes"):
            continue
        for comp in bom["componentes"]:
            id_comp = to_int_or_none(comp.get("id_articulo"))
            if id_comp is None:
                continue
            qty = float(comp.get("cantidad_articulo") or 0) * cant
            demanda_por_componente[id_comp] = demanda_por_componente.get(id_comp, 0) + qty
    return _listar_unidades_por_demanda(base_empresa, demanda_por_componente, limit)


def lineas_opt_desde_formulario_unidades(
    base_empresa: str,
    filas_pack: List[Dict[str, Any]],
    post_data: Any,
) -> List[Tuple[int, int, Optional[int]]]:
    """
    Convierte el POST del formulario de Confirmar OPT (unidades/componentes) en lineas
    (id_articulo_pack, cantidad_pack, id_operario) para crear_opt_multiples_articulos.

    lista_produccion_agrupada tiene filas por pack (artículo del pedido), no por componente.
    El formulario muestra unidades (componentes BOM); esta función mapea cantidades y operario
    de los componentes al pack para poder buscar la fila en agrupada.
    """
    if not (base_empresa or "").strip() or not filas_pack:
        return []
    pack_ids = [to_int_or_none(f.get("id_articulo")) for f in filas_pack]
    pack_ids = [a for a in pack_ids if a is not None]
    abm_map = bulk_id_en_abm(base_empresa, pack_ids) if pack_ids else {}
    bom_map = bulk_bom_detalle(base_empresa, list(set(abm_map.values()))) if abm_map else {}
    lineas: List[Tuple[int, int, Optional[int]]] = []
    for f in filas_pack:
        id_pack = to_int_or_none(f.get("id_articulo"))
        if not id_pack:
            continue
        id_en_abm = abm_map.get(id_pack)
        if id_en_abm is None:
            continue
        bom = bom_map.get(id_en_abm)
        if not bom or not bom.get("componentes"):
            continue
        # Obtener cantidad pack y operario desde cualquier componente del pack con cantidad > 0 en el formulario
        pack_qty = 0
        id_operario = None
        for comp in bom["componentes"]:
            id_comp = to_int_or_none(comp.get("id_articulo"))
            cant_articulo = float(comp.get("cantidad_articulo") or 0)
            if id_comp is None or cant_articulo <= 0:
                continue
            qty_comp_str = (post_data.get("cant_" + str(id_comp)) or "0").strip()
            try:
                qty_comp = int(float(qty_comp_str)) if qty_comp_str else 0
            except (ValueError, TypeError):
                qty_comp = 0
            if qty_comp > 0:
                qty_pack = int(qty_comp / cant_articulo) if cant_articulo else 0
                if qty_pack > pack_qty:
                    pack_qty = qty_pack
                if id_operario is None:
                    id_operario_raw = (post_data.get("operario_" + str(id_comp)) or "").strip()
                    try:
                        id_operario = int(id_operario_raw) if id_operario_raw else None
                    except (ValueError, TypeError):
                        id_operario = None
        if pack_qty <= 0:
            continue
        lineas.append((id_pack, pack_qty, id_operario))
    return lineas


def actualizar_pedidos_produccion(
    base_empresa: str,
    id_usuario: Optional[int],
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    busqueda: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Réplica del botón "Actualización" en Lista_Pedidos_OPT (VB6 Actualiza_Pedidos_Produccion).
    Carga lista_produccion_detalle y lista_produccion_agrupada desde pedidos PED (Anulado='No',
    estado_pedido_opt='Pendiente' si aplica), solo artículos con articulo.tipo_art_fab = 'Terminado'.
    Solo escribe en lista_produccion_detalle (INSERT) y lista_produccion_agrupada (INSERT/UPDATE).
    Nunca asigna en_proceso_produccion = 'Si' (eso solo ocurre al crear la OPT con crear_opt_multiples_articulos).
    Solo inserta/actualiza con en_proceso_produccion = 'No' y solo toca filas con en_proceso_produccion = 'No' en agrupada.
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
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not all([tbl_stockp, tbl_cp, tbl_detalle, tbl_agrupada, tbl_articulo]):
                conn.rollback()
                faltan = [n for n, t in [
                    ("stockp", tbl_stockp), ("comp_ped", tbl_cp), ("lista_produccion_detalle", tbl_detalle),
                    ("lista_produccion_agrupada", tbl_agrupada), ("articulo", tbl_articulo),
                ] if not t]
                raise MprSchemaError(
                    f"Faltan tablas en la base de datos: {', '.join(faltan)}. Cree las tablas o verifique el esquema para usar MPR."
                )
            # Origen: stockp + comp_ped + articulo (PED, Anulado='No', estado_pedido_opt='Pendiente' si aplica, tipo_art_fab='Terminado').
            sql_origin = f"""
                SELECT cp.CodigoMovimiento AS codigo_movimiento_pedido, sp.IDArt AS id_articulo,
                       COALESCE(sp.cantidad, sp.cantidad_pendiente, sp.Cantidad, 0) AS cantidad
                FROM {tbl_stockp} sp
                INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                INNER JOIN {tbl_articulo} a ON a.IDArt = sp.IDArt AND COALESCE(TRIM(a.tipo_art_fab), '') = 'Terminado'
                WHERE COALESCE(cp.Anulado, 'No') = 'No'
                  AND COALESCE(cp.TipoComprobante, '') = 'PED'
            """
            params_origin = []
            # Solo pedidos pendientes de producción (estado_pedido_opt = 'Pendiente')
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
            if not filas_origen:
                conn.rollback()
                return False, (
                    "No hay pedidos pendientes que se puedan incorporar a producción. "
                    "Revise en «Pedido producción trabajo (OPT)»: que el rango de fechas incluya sus pedidos, "
                    "que los pedidos tengan ítems cargados y que los artículos estén dados de alta como terminados para fabricación."
                )
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
            # 2) lista_produccion_agrupada: cantidad_pedida = SUM(detalle) (valor actual del pedido); cantidad_pendiente_prod solo se actualiza al crear OPP, no aquí
            cursor.execute(
                f"""
                SELECT id_articulo, COALESCE(SUM(cantidad_pedida), 0) AS total_pedida
                FROM {tbl_detalle}
                WHERE COALESCE(en_proceso_produccion, 'No') = 'No'
                GROUP BY id_articulo
                """,
            )
            sumas = cursor.fetchall()
            for row in sumas:
                id_art = to_int_or_none(row[0])
                try:
                    total_pedida = int(float(row[1] or 0))
                except (TypeError, ValueError):
                    total_pedida = 0
                if id_art is None:
                    continue
                # Solo considerar filas aún no en OPT (en_proceso_produccion = 'No'); no tocar filas ya en producción
                cursor.execute(
                    f"SELECT id_lista_produccion, cantidad_pendiente_prod FROM {tbl_agrupada} WHERE id_articulo = %s AND COALESCE(TRIM(en_proceso_produccion), 'No') = 'No' LIMIT 1",
                    [id_art],
                )
                existente = cursor.fetchone()
                if existente:
                    id_lista = existente[0]
                    # Solo actualizar cantidad_pedida. Nunca poner en_proceso_produccion = 'Si' aquí (solo al crear OPT)
                    cursor.execute(
                        f"UPDATE {tbl_agrupada} SET cantidad_pedida = %s WHERE id_lista_produccion = %s AND COALESCE(TRIM(en_proceso_produccion), 'No') = 'No'",
                        [total_pedida, id_lista],
                    )
                else:
                    # Nueva fila: cantidad_pedida y cantidad_pendiente_prod = total (pendiente de producir todo)
                    try:
                        cursor.execute(
                            f"INSERT INTO {tbl_agrupada} (id_articulo, cantidad_pedida, cantidad_pendiente_prod, id_usuario, en_proceso_produccion) VALUES (%s, %s, %s, %s, 'No')",
                            [id_art, total_pedida, total_pedida, id_usuario_val],
                        )
                    except Exception as ins_err:
                        if "1054" in str(ins_err):
                            cursor.execute(
                                f"INSERT INTO {tbl_agrupada} (id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion) VALUES (%s, %s, %s, 'No')",
                                [id_art, total_pedida, total_pedida],
                            )
                        else:
                            raise ins_err
                    id_lista = cursor.lastrowid
                # Trazabilidad: vincular filas de detalle (en_proceso_produccion='No') de este artículo a la línea de agrupada
                try:
                    cursor.execute(
                        f"UPDATE {tbl_detalle} SET id_lista_produccion = %s WHERE id_articulo = %s AND COALESCE(TRIM(en_proceso_produccion), 'No') = 'No'",
                        [id_lista, id_art],
                    )
                except Exception as upd_det:
                    if "1054" not in str(upd_det):
                        raise upd_det
            conn.commit()
            return True, "Se actualizaron los nuevos pedidos a producir correctamente."
    except MprSchemaError:
        raise
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
    cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion,
    id_lista_detalle, id_lista_produccion (si existen en esquema).
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_detalle or not tbl_articulo:
                return []
            sql_base = f"""
                SELECT
                    d.codigo_movimiento_pedido,
                    d.id_articulo,
                    COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                    COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                    COALESCE(d.cantidad_pedida, 0) AS cantidad_pedida,
                    COALESCE(d.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                    COALESCE(d.en_proceso_produccion, 'No') AS en_proceso_produccion
            """
            sql_extra = ", d.id_lista_detalle, d.id_lista_produccion"
            params = []
            sql = sql_base + sql_extra + f"""
                FROM {tbl_detalle} d
                INNER JOIN {tbl_articulo} a ON a.IDArt = d.id_articulo
                WHERE COALESCE(d.cantidad_pendiente_prod, 0) > 0
            """
            if codigo_movimiento_pedido is not None:
                sql += " AND d.codigo_movimiento_pedido = %s"
                params.append(codigo_movimiento_pedido)
            sql += " ORDER BY d.codigo_movimiento_pedido, d.id_articulo LIMIT %s"
            params.append(limit)
            try:
                cursor.execute(sql, params)
            except Exception as col_err:
                if "1054" in str(col_err):
                    sql = sql_base + f"""
                FROM {tbl_detalle} d
                INNER JOIN {tbl_articulo} a ON a.IDArt = d.id_articulo
                WHERE COALESCE(d.cantidad_pendiente_prod, 0) > 0
                    """
                    if codigo_movimiento_pedido is not None:
                        sql += " AND d.codigo_movimiento_pedido = %s"
                    sql += " ORDER BY d.codigo_movimiento_pedido, d.id_articulo LIMIT %s"
                    cursor.execute(sql, params)
                else:
                    raise col_err
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
                "id_lista_detalle": to_int_or_none(r.get("id_lista_detalle")),
                "id_lista_produccion": to_int_or_none(r.get("id_lista_produccion")),
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
                    COALESCE(d.cantidad_pedida, d.cantidad_pendiente_prod, 0) AS cantidad,
                    d.id_lista_detalle,
                    d.id_lista_produccion
                FROM {tbl_detalle} d
                INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = d.codigo_movimiento_pedido
                {join_cli}
                WHERE d.id_articulo = %s
                ORDER BY cp.Fecha DESC, d.codigo_movimiento_pedido
                LIMIT %s
            """
            try:
                cursor.execute(sql, [id_articulo, limit])
            except Exception as col_err:
                if "1054" in str(col_err):
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
                else:
                    raise col_err
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
            item = {
                "fecha": fecha_str,
                "nro_pedido": str_or_default(r.get("nro_pedido"), "-"),
                "nombre_cliente": str_or_default(r.get("nombre_cliente"), "-"),
                "cantidad": to_int_or_none(r.get("cantidad")) or 0,
            }
            if "id_lista_detalle" in r or "id_lista_produccion" in r:
                item["id_lista_detalle"] = to_int_or_none(r.get("id_lista_detalle"))
                item["id_lista_produccion"] = to_int_or_none(r.get("id_lista_produccion"))
            result.append(item)
        return result
    except Exception as e:
        logger.warning("Error en listar_detalle_pedidos_por_articulo en %s: %s", base_empresa, e, exc_info=True)
        return []


def bulk_detalle_pedidos_por_articulos(
    base_empresa: str,
    id_articulos: List[int],
    limit_por_articulo: int = 30,
) -> Dict[int, List[Dict[str, Any]]]:
    """Versión bulk de listar_detalle_pedidos_por_articulo: 1 query para N artículos."""
    if not (base_empresa or "").strip() or not id_articulos:
        return {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_cli = _nombre_tabla(cursor, "cliente")
            if not tbl_detalle or not tbl_cp:
                return {}
            ph = ",".join(["%s"] * len(id_articulos))
            join_cli = f"LEFT JOIN {tbl_cli} cli ON cli.codigo = cp.codigo" if tbl_cli else ""
            try:
                cursor.execute(
                    f"""SELECT d.id_articulo, cp.Fecha AS fecha,
                               COALESCE(cp.NroComprobante, cp.NroCompBusq, '') AS nro_pedido,
                               COALESCE(cli.nombre_cliente, '') AS nombre_cliente,
                               COALESCE(d.cantidad_pedida, d.cantidad_pendiente_prod, 0) AS cantidad
                        FROM {tbl_detalle} d
                        INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = d.codigo_movimiento_pedido
                        {join_cli}
                        WHERE d.id_articulo IN ({ph})
                        ORDER BY d.id_articulo, cp.Fecha DESC""",
                    list(id_articulos),
                )
            except Exception as col_err:
                if "1054" not in str(col_err):
                    raise
                cursor.execute(
                    f"""SELECT d.id_articulo, cp.Fecha AS fecha,
                               COALESCE(cp.NroComprobante, cp.NroCompBusq, '') AS nro_pedido,
                               '' AS nombre_cliente,
                               COALESCE(d.cantidad_pedida, d.cantidad_pendiente_prod, 0) AS cantidad
                        FROM {tbl_detalle} d
                        INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = d.codigo_movimiento_pedido
                        WHERE d.id_articulo IN ({ph})
                        ORDER BY d.id_articulo, cp.Fecha DESC""",
                    list(id_articulos),
                )
            result: Dict[int, list] = {aid: [] for aid in id_articulos}
            for r in cursor.fetchall():
                aid = to_int_or_none(r.get("id_articulo"))
                if aid is None or aid not in result:
                    continue
                if len(result[aid]) >= limit_por_articulo:
                    continue
                fecha_val = r.get("fecha")
                if hasattr(fecha_val, "strftime"):
                    fecha_str = fecha_val.strftime("%d-%m-%Y")
                elif isinstance(fecha_val, str) and len(fecha_val) >= 10:
                    try:
                        fecha_str = datetime.strptime(fecha_val[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
                    except Exception:
                        fecha_str = str(fecha_val)[:10]
                else:
                    fecha_str = str(fecha_val or "-")[:10]
                result[aid].append({
                    "fecha": fecha_str,
                    "nro_pedido": str_or_default(r.get("nro_pedido"), "-"),
                    "nombre_cliente": str_or_default(r.get("nombre_cliente"), "-"),
                    "cantidad": to_int_or_none(r.get("cantidad")) or 0,
                })
            return result
    except Exception as e:
        logger.warning("Error en bulk_detalle_pedidos_por_articulos en %s: %s", base_empresa, e, exc_info=True)
        return {}


def get_op_detalle(
    base_empresa: str,
    id_lista_produccion: int,
) -> List[Dict[str, Any]]:
    """
    Devuelve las líneas de una OPT por id_lista_produccion (lista_produccion_agrupada + articulo).

    Incluye todas las filas con ese id_lista_produccion (con o sin pendiente).
    Usa LEFT JOIN con articulo para no perder la fila si no hay coincidencia (evita 404 tras crear OPT).
    Si no existe tabla articulo, consulta solo agrupada. Lista vacía si no hay datos o tablas.
    """
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl_agrupada:
                return []
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            rows = []
            if tbl_articulo:
                # LEFT JOIN para no perder la fila si articulo no existe o no coincide (evita 404 tras crear OPT)
                sql = f"""
                    SELECT
                        l.id_lista_produccion,
                        l.id_articulo,
                        COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '-') AS codigo_articulo,
                        COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                        COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                        COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                        COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion,
                        l.id_operario_opt,
                        l.id_opt
                    FROM {tbl_agrupada} l
                    LEFT JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                    WHERE l.id_lista_produccion = %s
                    ORDER BY l.id_articulo
                """
                try:
                    cursor.execute(sql, [id_lista_produccion])
                    rows = cursor.fetchall()
                except Exception as col_err:
                    if "1054" in str(col_err) or "unknown column" in str(col_err).lower():
                        sql_fallback = f"""
                            SELECT
                                l.id_lista_produccion,
                                l.id_articulo,
                                COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '-') AS codigo_articulo,
                                COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                                COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                                COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                                COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion
                            FROM {tbl_agrupada} l
                            LEFT JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                            WHERE l.id_lista_produccion = %s
                            ORDER BY l.id_articulo
                        """
                        cursor.execute(sql_fallback, [id_lista_produccion])
                        rows = cursor.fetchall()
                    else:
                        raise
            if not rows:
                # Sin articulo o sin filas: intentar solo agrupada (evita 404 tras crear OPT)
                for sql_agrupada in [
                    f"SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion, id_operario_opt, id_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s",
                    f"SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion FROM {tbl_agrupada} WHERE id_lista_produccion = %s",
                ]:
                    try:
                        cursor.execute(sql_agrupada, [id_lista_produccion])
                        rows = cursor.fetchall()
                        if rows:
                            break
                    except Exception:
                        continue
        result = []
        for r in rows or []:
            r = {str(k).lower(): v for k, v in (r or {}).items()}
            row = {
                "id_lista_produccion": to_int_or_none(r.get("id_lista_produccion")),
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "cantidad_pedida": to_int_or_none(r.get("cantidad_pedida")) or 0,
                "cantidad_pendiente_prod": to_int_or_none(r.get("cantidad_pendiente_prod")) or 0,
                "en_proceso_produccion": str_or_default(r.get("en_proceso_produccion"), "No"),
            }
            row["id_operario_opt"] = to_int_or_none(r.get("id_operario_opt"))
            row["id_opt"] = to_int_or_none(r.get("id_opt"))
            result.append(row)
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

    Si en lista_produccion_agrupada la fila tiene id_opt no nulo, devuelve todas las líneas
    con ese id_opt. Si no, devuelve get_op_detalle (una sola línea).
    """
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl_agrupada:
                return get_op_detalle(base_empresa, id_lista_produccion)
            try:
                cursor.execute(
                    f"SELECT id_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                    [id_lista_produccion],
                )
                row = cursor.fetchone()
            except Exception as col_err:
                if "1054" in str(col_err) or "unknown column" in str(col_err).lower():
                    return get_op_detalle(base_empresa, id_lista_produccion)
                raise
            row_lower = {str(k).lower(): v for k, v in (row or {}).items()}
            id_opt_val = to_int_or_none(row_lower.get("id_opt"))
            if row and id_opt_val is not None:
                cursor.execute(
                    f"SELECT id_lista_produccion FROM {tbl_agrupada} WHERE id_opt = %s ORDER BY id_lista_produccion",
                    [id_opt_val],
                )
                ids = []
                for r in cursor.fetchall() or []:
                    r_lower = {str(k).lower(): v for k, v in (r or {}).items()}
                    lid = to_int_or_none(r_lower.get("id_lista_produccion"))
                    if lid is not None:
                        ids.append(lid)
                if ids:
                    result = []
                    for id_lista in ids:
                        result.extend(get_op_detalle(base_empresa, id_lista))
                    if result:
                        return result
    except Exception as e:
        logger.debug("get_opt_detalle agrupada id_opt: %s", e)
    # Fallback: una sola línea por id_lista_produccion (OPT sin agrupar o lectura directa)
    return get_op_detalle(base_empresa, id_lista_produccion)


def get_codigo_movimiento_opt(
    base_empresa: str,
    id_lista_produccion: int,
) -> Optional[int]:
    """
    Devuelve el CodigoMovimiento del comprobante MSTOCK de la OPT (para imprimir comprobante).

    Lee codigo_movimiento_opt de lista_produccion_agrupada: si la fila es la principal
    (id_lista_produccion = id_opt) lo toma de ahí; si no, obtiene id_opt y lee de la fila principal.
    """
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl_agrupada:
                return None
            try:
                cursor.execute(
                    f"SELECT id_opt, codigo_movimiento_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                    [id_lista_produccion],
                )
                row = cursor.fetchone()
            except Exception as col_err:
                if "1054" in str(col_err) or "unknown column" in str(col_err).lower():
                    return None
                raise
            if not row:
                return None
            id_opt = to_int_or_none(row.get("id_opt"))
            cod = to_int_or_none(row.get("codigo_movimiento_opt"))
            if id_opt is not None and id_lista_produccion == id_opt:
                return cod
            if id_opt is not None:
                cursor.execute(
                    f"SELECT codigo_movimiento_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                    [id_opt],
                )
                row_principal = cursor.fetchone()
                return to_int_or_none(row_principal.get("codigo_movimiento_opt")) if row_principal else None
            return cod
    except Exception as e:
        logger.debug("get_codigo_movimiento_opt: %s", e)
        return None


def get_lineas_opt_directo(
    base_empresa: str,
    id_lista: int,
) -> List[Dict[str, Any]]:
    """
    Fallback: obtiene líneas de la OPT consultando directamente lista_produccion_agrupada.
    Usar cuando get_opt_detalle/get_op_detalle devuelvan [] (p. ej. diferencias de esquema o BD).
    Devuelve lista de dicts con id_articulo, codigo_articulo, descripcion_articulo,
    cantidad_pedida, cantidad_pendiente_prod, id_lista_produccion, en_proceso_produccion.
    """
    if not (base_empresa or "").strip() or id_lista is None:
        return []
    result = []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl_agrupada:
                return []
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            # Intentar por id_lista_produccion; si no hay filas, por id_opt (OPT multi-artículo)
            raw_rows = []
            for sql_where, params in [
                ("id_lista_produccion = %s", [id_lista]),
                ("id_opt = %s", [id_lista]),
            ]:
                try:
                    cols = "id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion"
                    cursor.execute(
                        f"SELECT {cols} FROM {tbl_agrupada} WHERE {sql_where} ORDER BY id_lista_produccion, id_articulo",
                        params,
                    )
                    raw_rows = cursor.fetchall()
                except Exception as col_err:
                    if "1054" in str(col_err) or "unknown column" in str(col_err).lower():
                        try:
                            cursor.execute(
                                f"SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod FROM {tbl_agrupada} WHERE id_lista_produccion = %s ORDER BY id_articulo",
                                [id_lista],
                            )
                            raw_rows = cursor.fetchall()
                        except Exception:
                            raw_rows = []
                    else:
                        raise
                if not raw_rows:
                    continue
                for r in raw_rows:
                    r = {str(k).lower(): v for k, v in (r or {}).items()}
                    id_art = to_int_or_none(r.get("id_articulo") or r.get("idart"))
                    id_lista_prod = to_int_or_none(r.get("id_lista_produccion"))
                    qty_ped = to_int_or_none(r.get("cantidad_pedida")) or 0
                    qty_pend = to_int_or_none(r.get("cantidad_pendiente_prod")) or 0
                    en_proc = str_or_default(r.get("en_proceso_produccion"), "No")
                    codigo = "-"
                    descr = ""
                    if tbl_articulo and id_art:
                        try:
                            cursor.execute(
                                "SELECT CodigoArticuloT, CodigoArticulo, NombreArticulo FROM {} WHERE IDArt = %s LIMIT 1".format(
                                    tbl_articulo
                                ),
                                [id_art],
                            )
                            art_row = cursor.fetchone()
                            if art_row:
                                art_row = {str(k).lower(): v for k, v in art_row.items()}
                                codigo = str_or_default(
                                    art_row.get("codigoarticulot") or art_row.get("codigoarticulo"), "-"
                                )
                                descr = str_or_default(art_row.get("nombrearticulo"), "")
                        except Exception:
                            pass
                    result.append({
                        "id_lista_produccion": id_lista_prod,
                        "id_articulo": id_art,
                        "codigo_articulo": codigo,
                        "descripcion_articulo": descr,
                        "cantidad_pedida": qty_ped,
                        "cantidad_pendiente_prod": qty_pend,
                        "en_proceso_produccion": en_proc,
                    })
                if result:
                    break
    except Exception as e:
        logger.warning(
            "get_lineas_opt_directo id_lista=%s base_empresa=%s: %s",
            id_lista,
            base_empresa,
            e,
            exc_info=True,
        )
    return result


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


# Valores válidos para deposito.tipo_mpr (uso MPR por depósito)
TIPO_MPR_PRODUCCION = "Produccion"
TIPO_MPR_SEMI_ELABORADO = "SemiElaborado"
TIPO_MPR_TERMINADO = "Terminado"
TIPO_MPR_SCRAP = "Scrap"
TIPO_MPR_2DA_SELECCION = "2daSeleccion"

TIPOS_MPR_OPP = (TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_SCRAP, TIPO_MPR_2DA_SELECCION)


def listar_depositos_config(base_empresa: str) -> List[Dict[str, Any]]:
    """Lista todos los depósitos no anulados con suma_stock y tipo_mpr para Config MPR.
    Si falta la tabla deposito o la columna tipo_mpr, lanza MprSchemaError para mostrar modal de error."""
    if not (base_empresa or "").strip():
        return []
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        tbl = _nombre_tabla(cursor, "deposito")
        if not tbl:
            raise MprSchemaError(
                "Falta la tabla «deposito» en la base de datos. "
                "Cree la tabla según el esquema de AdministraNET para usar la configuración de depósitos MPR."
            )
        try:
            cursor.execute(
                f"SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito, "
                f"COALESCE(suma_stock, 'Si') AS suma_stock, tipo_mpr FROM {tbl} "
                f"WHERE COALESCE(anulado, 'No') = 'No' ORDER BY NombreDeposito"
            )
        except Exception as e:
            err_msg = str(e).strip()
            if "1054" in err_msg or "Unknown column" in err_msg.lower():
                raise MprSchemaError(
                    formatear_error_esquema(e, "deposito")
                    + " Para la configuración MPR por tipo (Producción, Semi Elaborado, etc.) ejecute: "
                    "ALTER TABLE deposito ADD COLUMN tipo_mpr VARCHAR(20) NULL;"
                )
            if "1146" in err_msg or "doesn't exist" in err_msg.lower():
                raise MprSchemaError(formatear_error_esquema(e, "deposito")) from e
            raise
        rows = cursor.fetchall()
    return [
        {
            "CodDeposito": d.get("CodDeposito"),
            "NombreDeposito": str_or_default(d.get("NombreDeposito"), "-"),
            "suma_stock": str_or_default(d.get("suma_stock"), "Si"),
            "tipo_mpr": (d.get("tipo_mpr") or "").strip() or None,
        }
        for d in rows
    ]


def actualizar_deposito_tipo_mpr(
    base_empresa: str, cod_deposito: int, tipo_mpr: Optional[str]
) -> Tuple[bool, Optional[str]]:
    """Actualiza deposito.tipo_mpr. tipo_mpr debe ser uno de los TIPO_MPR_* o None/vacío.
    Solo un depósito por tipo (unicidad). Devuelve (ok, error)."""
    if not (base_empresa or "").strip():
        return False, "Base de datos no indicada."
    cod_deposito = to_int_or_none(cod_deposito)
    if not cod_deposito:
        return False, "Depósito no indicado."
    valor_interno = None
    if tipo_mpr and (tipo_mpr := (tipo_mpr or "").strip()):
        validos = (TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_TERMINADO, TIPO_MPR_SCRAP, TIPO_MPR_2DA_SELECCION)
        if tipo_mpr not in validos:
            return False, f"Tipo MPR no válido. Use: {', '.join(validos)}."
        valor_interno = tipo_mpr
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "deposito")
            if not tbl:
                raise MprSchemaError(
                    "Falta la tabla «deposito» en la base de datos. Cree la tabla o verifique el esquema para usar MPR."
                )
            if valor_interno:
                cursor.execute(
                    f"SELECT COUNT(*) AS n FROM {tbl} WHERE tipo_mpr = %s AND CodDeposito != %s",
                    [valor_interno, cod_deposito],
                )
                row = cursor.fetchone()
                if row and (row[0] if isinstance(row, (list, tuple)) else row.get("n", 0)) > 0:
                    return False, f"Otro depósito ya tiene el tipo «{valor_interno}». Cada tipo debe estar asignado a un solo depósito."
            cursor.execute(
                f"UPDATE {tbl} SET tipo_mpr = %s WHERE CodDeposito = %s",
                [valor_interno, cod_deposito],
            )
            conn.commit()
        return True, None
    except MprSchemaError:
        raise
    except Exception as e:
        err_msg = str(e).strip()
        if "1054" in err_msg or "Unknown column" in err_msg.lower():
            raise MprSchemaError(
                formatear_error_esquema(e, "deposito")
                + " Ejecute: ALTER TABLE deposito ADD COLUMN tipo_mpr VARCHAR(20) NULL;"
            )
        logger.warning("Error al actualizar tipo_mpr en %s: %s", base_empresa, e, exc_info=True)
        return False, str(e)


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
                raise MprSchemaError(
                    "Falta la tabla deposito en la base de datos. Cree la tabla o verifique el esquema para usar MPR."
                )
            cursor.execute(f"UPDATE {tbl} SET suma_stock = %s WHERE CodDeposito = %s", [valor, cod_deposito])
            conn.commit()
        return True, None
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error al actualizar suma_stock en %s: %s", base_empresa, e, exc_info=True)
        return False, str(e)


def _get_deposito_por_tipo_mpr(base_empresa: str, tipo: str) -> Optional[int]:
    """Devuelve CodDeposito del depósito que tiene tipo_mpr = tipo, o None."""
    if not (base_empresa or "").strip() or not tipo:
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "deposito")
            if not tbl:
                return None
            cursor.execute(
                f"SELECT CodDeposito FROM {tbl} WHERE tipo_mpr = %s AND COALESCE(anulado, 'No') = 'No' LIMIT 1",
                [tipo],
            )
            row = cursor.fetchone()
            if row:
                return to_int_or_none(row.get("CodDeposito") if isinstance(row, dict) else row[0])
    except Exception as e:
        logger.warning("Error al obtener depósito tipo_mpr=%s en %s: %s", tipo, base_empresa, e)
    return None


def get_deposito_produccion_mpr(base_empresa: str) -> Optional[int]:
    """Devuelve el depósito de producción (tipo_mpr=Produccion o MprConfig.id_deposito_produccion)."""
    cod = _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_PRODUCCION)
    if cod is not None:
        return cod
    try:
        from mpr.models import MprConfig

        c = MprConfig.objects.filter(base_empresa=base_empresa).first()
        return to_int_or_none(c.id_deposito_produccion) if c else None
    except Exception as e:
        logger.warning("Error al obtener depósito producción MPR para %s: %s", base_empresa, e)
        return None


def get_deposito_terminado_mpr(base_empresa: str) -> Optional[int]:
    """Devuelve el depósito de terminado (tipo_mpr=Terminado) para destino del armado."""
    return _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_TERMINADO)


def get_deposito_semi_elaborado_mpr(base_empresa: str) -> Optional[int]:
    """Devuelve el depósito semi elaborado (tipo_mpr=SemiElaborado)."""
    return _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_SEMI_ELABORADO)


def get_depositos_opp(base_empresa: str) -> List[Dict[str, Any]]:
    """Lista depósitos que son destino válido de OPP: tipo_mpr en (SemiElaborado, Scrap, 2daSeleccion).
    Orden por nombre. Si falta tabla/columna lanza MprSchemaError."""
    if not (base_empresa or "").strip():
        return []
    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        tbl = _nombre_tabla(cursor, "deposito")
        if not tbl:
            raise MprSchemaError(
                "Falta la tabla «deposito» en la base de datos. Cree la tabla según el esquema de AdministraNET."
            )
        placeholders = ",".join(["%s"] * len(TIPOS_MPR_OPP))
        try:
            cursor.execute(
                f"SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito FROM {tbl} "
                f"WHERE tipo_mpr IN ({placeholders}) AND COALESCE(anulado, 'No') = 'No' ORDER BY NombreDeposito",
                list(TIPOS_MPR_OPP),
            )
        except Exception as e:
            if "1054" in str(e) or "Unknown column" in str(e).lower():
                raise MprSchemaError(
                    formatear_error_esquema(e, "deposito")
                    + " Ejecute: ALTER TABLE deposito ADD COLUMN tipo_mpr VARCHAR(20) NULL;"
                )
            raise
        rows = cursor.fetchall()
    return [
        {"CodDeposito": r.get("CodDeposito"), "NombreDeposito": str_or_default(r.get("NombreDeposito"), "-")}
        for r in rows
    ]


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
    Lista pedidos de venta (comp_ped) con estado de producción (estado_pedido_opt en Pendiente, Produccion, Terminado).
    El filtro opcional estado filtra por estado_pedido_opt (Pendiente, Produccion, Terminado).
    Devuelve: CodigoMovimiento, NroComprobante, Fecha, Estado, estado_pedido_opt, nombre_cliente.
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_cli = _nombre_tabla(cursor, "cliente")
            if not tbl_cp:
                raise MprSchemaError(
                    "Falta la tabla comp_ped en la base de datos. Cree la tabla o verifique el esquema para usar MPR."
                )
            join_cli = f"LEFT JOIN {tbl_cli} cli ON cli.codigo = cp.codigo" if tbl_cli else ""
            sql = f"""
                SELECT cp.CodigoMovimiento, COALESCE(cp.NroComprobante, '') AS NroComprobante,
                       cp.Fecha, COALESCE(cp.Estado, '') AS Estado,
                       COALESCE(cp.estado_pedido_opt, '') AS estado_pedido_opt,
                       COALESCE(cli.nombre_cliente, '') AS nombre_cliente
                FROM {tbl_cp} cp
                {join_cli}
                WHERE COALESCE(cp.Anulado, 'No') = 'No'
                  AND COALESCE(cp.TipoComprobante, '') = 'PED'
                  AND COALESCE(cp.estado_pedido_opt, '') IN ('Pendiente', 'Produccion', 'Terminado')
            """
            params = []
            if estado:
                sql += " AND cp.estado_pedido_opt = %s"
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
                "estado_pedido_opt": str_or_default(r.get("estado_pedido_opt"), "-"),
                "nombre_cliente": str_or_default(r.get("nombre_cliente"), "-"),
            }
            for r in rows
        ]
    except MprSchemaError:
        raise
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
                raise MprSchemaError(
                    "Falta la tabla en_abm en la base de datos. Cree la tabla o verifique el esquema para usar MPR (Lista de materiales)."
                )
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
    except MprSchemaError:
        raise
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


def get_lineas_armado_opt(
    base_empresa: str,
    id_lista: int,
) -> List[Dict[str, Any]]:
    """
    Devuelve las líneas de la OPT que son armables (tienen BOM, ensamblado='Si', descuenta_en='Mstock'),
    con BOM y saldo en Semi Elaborado por componente. Para uso en paso 4 del wizard y vista armado desde OPT.
    """
    if not (base_empresa or "").strip() or id_lista is None:
        return []
    lineas = get_opt_detalle(base_empresa, id_lista)
    if not lineas:
        return []
    deposito_semi = get_deposito_semi_elaborado_mpr(base_empresa)
    if not deposito_semi:
        return []
    result = []
    art_ids = [to_int_or_none(l.get("id_articulo")) for l in lineas]
    art_ids = [a for a in art_ids if a is not None]
    if not art_ids:
        return []
    abm_map = bulk_id_en_abm(base_empresa, art_ids)
    abm_ids = list(set(abm_map.values()))
    bom_map = bulk_bom_detalle(base_empresa, abm_ids) if abm_ids else {}
    armado_map = bulk_articulo_armado(base_empresa, abm_ids) if abm_ids else {}
    componentes_ids = set()
    lineas_con_bom = []
    for linea in lineas:
        id_art = to_int_or_none(linea.get("id_articulo"))
        if id_art is None:
            continue
        id_en_abm = abm_map.get(id_art)
        if not id_en_abm:
            continue
        articulo_armado = armado_map.get(id_en_abm)
        bom = bom_map.get(id_en_abm)
        if not articulo_armado or not bom or not bom.get("componentes"):
            continue
        descuenta_en = (bom.get("cabecera") or {}).get("descuenta_en") or ""
        if isinstance(descuenta_en, str):
            descuenta_en = descuenta_en.strip()
        if descuenta_en and descuenta_en.upper() != "MSTOCK":
            continue
        for comp in bom["componentes"]:
            cid = to_int_or_none(comp.get("id_articulo"))
            if cid is not None:
                componentes_ids.add(cid)
        lineas_con_bom.append({
            "linea": linea,
            "id_en_abm": id_en_abm,
            "articulo_armado": articulo_armado,
            "bom": bom,
        })
    if not lineas_con_bom or not componentes_ids:
        return []
    # Una sola consulta de saldos en Semi Elaborado para todos los componentes
    saldos_semi = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            if tbl_sd and componentes_ids:
                placeholders = ",".join(["%s"] * len(componentes_ids))
                cursor.execute(
                    f"SELECT id_articulo, saldo FROM {tbl_sd} WHERE id_deposito = %s AND id_articulo IN ({placeholders})",
                    [deposito_semi] + list(componentes_ids),
                )
                for row in cursor.fetchall() or []:
                    r = {str(k).lower(): v for k, v in (row or {}).items()}
                    aid = to_int_or_none(r.get("id_articulo"))
                    if aid is not None:
                        saldos_semi[aid] = float(r.get("saldo") or 0)
    except Exception as e:
        logger.warning("Error al obtener saldos Semi Elaborado en get_lineas_armado_opt: %s", e)
    for item in lineas_con_bom:
        linea = item["linea"]
        bom = item["bom"]
        componentes = []
        for comp in bom.get("componentes") or []:
            c = dict(comp)
            cid = to_int_or_none(comp.get("id_articulo"))
            c["saldo_semi_elaborado"] = saldos_semi.get(cid, 0) if cid is not None else 0
            componentes.append(c)
        max_packs_armable = 0
        for c in componentes:
            cant = float(c.get("cantidad_articulo") or 0)
            if cant > 0:
                saldo = float(c.get("saldo_semi_elaborado") or 0)
                packs_i = int(saldo // cant)
                max_packs_armable = min(max_packs_armable, packs_i) if max_packs_armable else packs_i
        tooltip_data = [
            {"codigo": str_or_default(c.get("codigo_articulo"), "-"), "saldo": float(c.get("saldo_semi_elaborado") or 0)}
            for c in componentes
        ]
        result.append({
            "id_articulo": to_int_or_none(linea.get("id_articulo")),
            "codigo_articulo": str_or_default(linea.get("codigo_articulo"), "-"),
            "descripcion_articulo": str_or_default(linea.get("descripcion_articulo"), "-"),
            "id_en_abm": item["id_en_abm"],
            "nombre_bom": (bom.get("cabecera") or {}).get("nombre_en_abm") or "-",
            "bom": {"cabecera": bom.get("cabecera"), "componentes": componentes},
            "articulo_armado": item["articulo_armado"],
            "max_packs_armable": max_packs_armable,
            "tooltip_semi_elaborado_json": json.dumps(tooltip_data, ensure_ascii=False),
        })
    return result


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
                WHERE UPPER(TRIM(COALESCE(tipo_mov,''))) IN ('OPA', 'ARMADO')
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


def listar_opp_por_opt(base_empresa: str, id_lista_produccion: int) -> List[Dict[str, Any]]:
    """
    Lista las partes de producción (OPP) ya registradas para una OPT.
    Busca en movimiento_stock por tipo_mov = 'OPP' y detalle que contenga "OPT {id} desde".
    Devuelve lista de dicts: codigo_movimiento, nro_comprobante, fecha, deposito_origen, deposito_destino,
    nombre_origen, nombre_destino (opcional), cantidad_total. Orden: más reciente primero.
    """
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return []
    result = []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            if not tbl_mov or not tbl_stock:
                return []
            # Patrón exacto para no confundir OPT 1 con OPT 12 (detalle = "OPT {id} desde MPR")
            patron = f"OPT {id_lista_produccion} desde"
            try:
                cursor.execute(
                    f"""
                    SELECT codigo_movimiento, nro_comprobante, fecha, deposito_origen, deposito_destino
                    FROM {tbl_mov}
                    WHERE (UPPER(TRIM(COALESCE(tipo_mov,''))) = 'OPP' OR COALESCE(motivo_movimiento,'') = 'Parte producción')
                      AND INSTR(COALESCE(detalle,''), %s) > 0
                      AND COALESCE(anulado,'No') <> 'Si'
                    ORDER BY codigo_movimiento DESC
                    """,
                    [patron],
                )
            except Exception as e1:
                if "1054" in str(e1) or "Unknown column" in str(e1).lower():
                    raise MprSchemaError(formatear_error_esquema(e1, "movimiento_stock")) from e1
                raise
            rows = cursor.fetchall()
            if not rows:
                return []
            codigos = [to_int_or_none(r.get("codigo_movimiento")) for r in rows if r.get("codigo_movimiento") is not None]
            codigos = [c for c in codigos if c is not None]
            # Cantidad total por movimiento (suma de Entrada en stock)
            cantidades = {}
            if codigos and tbl_stock:
                placeholders = ",".join(["%s"] * len(codigos))
                cursor.execute(
                    f"""
                    SELECT CodigoMovimiento, COALESCE(SUM(Entrada), 0) AS total
                    FROM {tbl_stock}
                    WHERE CodigoMovimiento IN ({placeholders})
                    GROUP BY CodigoMovimiento
                    """,
                    codigos,
                )
                for row in cursor.fetchall():
                    cod = to_int_or_none(row.get("CodigoMovimiento"))
                    if cod is not None:
                        cantidades[cod] = int(float(row.get("total") or 0))
            # Nombres de depósitos (origen y destino únicos)
            cods_dep = set()
            for r in rows:
                cods_dep.add(to_int_or_none(r.get("deposito_origen")))
                cods_dep.add(to_int_or_none(r.get("deposito_destino")))
            cods_dep.discard(None)
            nombres_dep = {}
            if cods_dep and tbl_dep:
                placeholders = ",".join(["%s"] * len(cods_dep))
                cursor.execute(
                    f"SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito FROM {tbl_dep} WHERE CodDeposito IN ({placeholders})",
                    list(cods_dep),
                )
                for row in cursor.fetchall():
                    cod = to_int_or_none(row.get("CodDeposito"))
                    if cod is not None:
                        nombres_dep[cod] = str_or_default(row.get("NombreDeposito"), "-")
            for r in rows:
                cod_mov = to_int_or_none(r.get("codigo_movimiento"))
                dep_orig = to_int_or_none(r.get("deposito_origen"))
                dep_dest = to_int_or_none(r.get("deposito_destino"))
                result.append({
                    "codigo_movimiento": cod_mov,
                    "nro_comprobante": str_or_default(r.get("nro_comprobante"), "-"),
                    "fecha": r.get("fecha"),
                    "deposito_origen": dep_orig,
                    "deposito_destino": dep_dest,
                    "nombre_origen": nombres_dep.get(dep_orig, str(dep_orig) if dep_orig is not None else "-"),
                    "nombre_destino": nombres_dep.get(dep_dest, str(dep_dest) if dep_dest is not None else "-"),
                    "cantidad_total": cantidades.get(cod_mov, 0),
                })
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning(
            "Error al listar OPP por OPT %s en %s: %s",
            id_lista_produccion,
            base_empresa,
            e,
            exc_info=True,
        )
    return result


def listar_opa_por_opt(base_empresa: str, id_lista_produccion: int) -> List[Dict[str, Any]]:
    """
    Lista los armados (OPA) ya registrados para una OPT.
    Busca en movimiento_stock por tipo_mov IN ('OPA', 'Armado') y detalle que contenga "OPT {id}".
    Devuelve lista de dicts: codigo_movimiento, nro_comprobante, fecha, deposito_origen, deposito_destino,
    nombre_origen, nombre_destino, cantidad_total (suma Entrada del artículo armado). Orden: más reciente primero.
    """
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return []
    result = []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            if not tbl_mov or not tbl_stock:
                return []
            patron = f"OPT {id_lista_produccion} "
            patron2 = f"OPT {id_lista_produccion})"
            try:
                cursor.execute(
                    f"""
                    SELECT codigo_movimiento, nro_comprobante, fecha, deposito_origen, deposito_destino
                    FROM {tbl_mov}
                    WHERE UPPER(TRIM(COALESCE(tipo_mov,''))) IN ('OPA', 'ARMADO')
                      AND (INSTR(COALESCE(detalle,''), %s) > 0 OR INSTR(COALESCE(detalle,''), %s) > 0)
                      AND COALESCE(anulado,'No') <> 'Si'
                    ORDER BY codigo_movimiento DESC
                    """,
                    [patron, patron2],
                )
            except Exception as e1:
                if "1054" in str(e1) or "Unknown column" in str(e1).lower():
                    raise MprSchemaError(formatear_error_esquema(e1, "movimiento_stock")) from e1
                raise
            rows = cursor.fetchall()
            if not rows:
                return []
            codigos = [to_int_or_none(r.get("codigo_movimiento")) for r in rows if r.get("codigo_movimiento") is not None]
            codigos = [c for c in codigos if c is not None]
            cantidades = {}
            if codigos and tbl_stock:
                placeholders = ",".join(["%s"] * len(codigos))
                cursor.execute(
                    f"""
                    SELECT CodigoMovimiento, COALESCE(SUM(Entrada), 0) AS total
                    FROM {tbl_stock}
                    WHERE CodigoMovimiento IN ({placeholders})
                    GROUP BY CodigoMovimiento
                    """,
                    codigos,
                )
                for row in cursor.fetchall():
                    cod = to_int_or_none(row.get("CodigoMovimiento"))
                    if cod is not None:
                        cantidades[cod] = int(float(row.get("total") or 0))
            cods_dep = set()
            for r in rows:
                cods_dep.add(to_int_or_none(r.get("deposito_origen")))
                cods_dep.add(to_int_or_none(r.get("deposito_destino")))
            cods_dep.discard(None)
            nombres_dep = {}
            if cods_dep and tbl_dep:
                placeholders = ",".join(["%s"] * len(cods_dep))
                cursor.execute(
                    f"SELECT CodDeposito, COALESCE(NombreDeposito, '') AS NombreDeposito FROM {tbl_dep} WHERE CodDeposito IN ({placeholders})",
                    list(cods_dep),
                )
                for row in cursor.fetchall():
                    cod = to_int_or_none(row.get("CodDeposito"))
                    if cod is not None:
                        nombres_dep[cod] = str_or_default(row.get("NombreDeposito"), "-")
            for r in rows:
                cod_mov = to_int_or_none(r.get("codigo_movimiento"))
                dep_orig = to_int_or_none(r.get("deposito_origen"))
                dep_dest = to_int_or_none(r.get("deposito_destino"))
                result.append({
                    "codigo_movimiento": cod_mov,
                    "nro_comprobante": str_or_default(r.get("nro_comprobante"), "-"),
                    "fecha": r.get("fecha"),
                    "deposito_origen": dep_orig,
                    "deposito_destino": dep_dest,
                    "nombre_origen": nombres_dep.get(dep_orig, str(dep_orig) if dep_orig is not None else "-"),
                    "nombre_destino": nombres_dep.get(dep_dest, str(dep_dest) if dep_dest is not None else "-"),
                    "cantidad_total": cantidades.get(cod_mov, 0),
                })
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning(
            "Error al listar OPA por OPT %s en %s: %s",
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
    hora_evento = datetime.now().strftime("%H:%M:%S")
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
                    faltan = [n for n, t in [
                        ("codmov", tbl_codmov), ("talonarios", tbl_talonarios), ("movimiento_stock", tbl_mov),
                        ("stock", tbl_stock), ("stock_deposito", tbl_sd), ("articulo", tbl_articulo),
                    ] if not t]
                    raise MprSchemaError(
                        f"Faltan tablas en la base de datos: {', '.join(faltan)}. Cree las tablas o verifique el esquema para usar MPR."
                    )
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
                    TIPO_MOV_OPA,  # tipo_mov: OPA (armado), no "Armado"
                    id_pv,
                    nro_comprobante_busq,
                ]
                # 16 columnas (sin nro_comprobante_busq): 15 %s + literal 'No' = 16 valores; 15 params (id_ref, id_proy, id_cli, id_vend, tipo_mov, id_pv)
                params_mov_ins = (
                    params_mov[:8] + ["MSTOCK"] + [params_mov[8], params_mov[9], params_mov[10], params_mov[11], params_mov[13], params_mov[14]]
                )
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'No', %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov_ins,
                    )
                except Exception as ins_err:
                    err_str = str(ins_err)
                    if "1054" in err_str or "unknown column" in err_str.lower() or "doesn't exist" in err_str.lower():
                        try:
                            # Fallback sin nro_comprobante_busq (y sin id_pv): 15 columnas, 13 %s + 2 literales → 13 params
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_mov}
                                (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                                 detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s)
                                """,
                                params_mov[:13],
                            )
                        except Exception as ins_err2:
                            raise MprSchemaError(formatear_error_esquema(ins_err2, "movimiento_stock")) from ins_err2
                    else:
                        logger.warning(
                            "ejecutar_armado: error en INSERT movimiento_stock (no es esquema): %s", ins_err, exc_info=True
                        )
                        raise
                codigo_mov_opt_armado = get_codigo_movimiento_opt(base_empresa, id_lista_produccion) if id_lista_produccion else None
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
                        params_comp = [
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
                        ]
                        params_comp_opt_abm = params_comp + [codigo_mov_opt_armado, id_en_abm]
                        try:
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                                """,
                                params_comp_opt_abm,
                            )
                        except Exception as stock_err:
                            if "1054" in str(stock_err):
                                cursor.execute(
                                    f"""
                                    INSERT INTO {tbl_stock}
                                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                    VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                    """,
                                    params_comp,
                                )
                            else:
                                raise
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
                                params_lote = [
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
                                ]
                                params_lote_opt_abm = params_lote + [codigo_mov_opt_armado, id_en_abm]
                                try:
                                    cursor.execute(
                                        f"""
                                        INSERT INTO {tbl_stock}
                                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_lote, codigo_mov_opt, id_en_abm)
                                        VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s, %s)
                                        """,
                                        params_lote_opt_abm,
                                    )
                                except Exception as stock_err:
                                    if "1054" in str(stock_err):
                                        cursor.execute(
                                            f"""
                                            INSERT INTO {tbl_stock}
                                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_lote)
                                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
                                            """,
                                            params_lote,
                                        )
                                    else:
                                        raise
                            else:
                                params_sin_lote = [
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
                                ]
                                params_sin_lote_opt_abm = params_sin_lote + [codigo_mov_opt_armado, id_en_abm]
                                try:
                                    cursor.execute(
                                        f"""
                                        INSERT INTO {tbl_stock}
                                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                                        VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                                        """,
                                        params_sin_lote_opt_abm,
                                    )
                                except Exception as stock_err:
                                    if "1054" in str(stock_err):
                                        cursor.execute(
                                            f"""
                                            INSERT INTO {tbl_stock}
                                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                            """,
                                            params_sin_lote,
                                        )
                                    else:
                                        raise
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
                params_entrada_arm = [
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
                ]
                params_entrada_arm_opt_abm = params_entrada_arm + [codigo_mov_opt_armado, id_en_abm]
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_stock}
                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                        VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                        """,
                        params_entrada_arm_opt_abm,
                    )
                except Exception as stock_err:
                    if "1054" in str(stock_err):
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                            """,
                            params_entrada_arm,
                        )
                    else:
                        raise
                if sd_dest:
                    cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_dest_despues, sd_dest[0]])
                else:
                    cursor.execute(
                        f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                        [id_art_arm, deposito_destino, saldo_dest_despues],
                    )
                # Log de eventos: lista_produccion_historico (tipo_evento='OPA'). id_articulo = pack armado, id_articulo_formula = NULL (evento por pack).
                tbl_historico = _nombre_tabla(cursor, "lista_produccion_historico")
                if tbl_historico and id_art_arm is not None:
                    try:
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_historico}
                            (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                             id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                             nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento)
                            VALUES (%s, %s, NULL, 0, 0, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s)
                            """,
                            [
                                TIPO_MOV_OPA,
                                id_art_arm,
                                cantidad_a_armar,
                                deposito_destino,
                                deposito_origen,
                                deposito_destino,
                                codigo_mov,
                                nro_comprobante,
                                id_usuario,
                                id_lista_produccion if id_lista_produccion is not None else None,
                                fecha_mov,
                                hora_evento,
                            ],
                        )
                    except Exception as hist_err:
                        logger.warning("No se pudo insertar lista_produccion_historico (OPA): %s", hist_err)
                conn.commit()
                return True, codigo_mov, nro_comprobante, None
            except MprSchemaError:
                conn.rollback()
                raise
            except Exception as e:
                conn.rollback()
                if "1054" in str(e) or "Unknown column" in str(e).lower():
                    raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
                logger.warning("Error en ejecutar_armado: %s", e, exc_info=True)
                return False, None, None, str(e)
    except MprSchemaError:
        raise
    except Exception as e:
        if "1054" in str(e) or "Unknown column" in str(e).lower():
            raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
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
                raise MprSchemaError(
                    "Falta la tabla en_abm en la base de datos. Cree la tabla o verifique el esquema para usar MPR (Lista de materiales)."
                )
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
    except MprSchemaError:
        raise
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
                raise MprSchemaError(
                    "Falta la tabla en_abm en la base de datos. Cree la tabla o verifique el esquema para usar MPR (Lista de materiales)."
                )
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
    except MprSchemaError:
        raise
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
                raise MprSchemaError(
                    "Falta la tabla en_abm_formula en la base de datos. Cree la tabla o verifique el esquema para usar MPR (Lista de materiales)."
                )
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
    except MprSchemaError:
        raise
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
                raise MprSchemaError(
                    "Falta la tabla en_abm_formula en la base de datos. Cree la tabla o verifique el esquema para usar MPR (Lista de materiales)."
                )
            tipo_unidad_val = (tipo_unidad or "").strip() or ""
            cursor.execute(
                f"UPDATE {tbl} SET id_articulo = %s, cantidad_articulo = %s, tipo_unidad = %s WHERE id_en_abm_formula = %s",
                [id_articulo, cantidad_articulo, tipo_unidad_val, id_en_abm_formula],
            )
            conn.commit()
        return True, None
    except MprSchemaError:
        raise
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
                raise MprSchemaError(
                    "Falta la tabla articulo en la base de datos. Cree la tabla o verifique el esquema para usar MPR."
                )
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
                raise MprSchemaError(
                    "La tabla articulo no tiene la columna id_en_abm. Agregue la columna o verifique el esquema para usar MPR (Lista de materiales)."
                )
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
    except MprSchemaError:
        raise
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
                raise MprSchemaError(
                    "Falta la tabla en_abm_formula en la base de datos. Cree la tabla o verifique el esquema para usar MPR (Lista de materiales)."
                )
            cursor.execute(f"UPDATE {tbl} SET anulado = 'Si' WHERE id_en_abm_formula = %s", [id_en_abm_formula])
            conn.commit()
        return True, None
    except MprSchemaError:
        raise
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


def listar_empleados_operarios(
    base_empresa: str,
    busqueda: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Lista empleados (operarios) desde sue_abm_empleado para selector en Confirmar OPT.
    Filtra anulado='No'. Si busqueda está definida, filtra por nombre_empleado LIKE %busqueda%.
    Devuelve lista de { "id": id_sue_abm_empleado, "label": nombre_empleado }.
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "sue_abm_empleado")
            if not tbl:
                return []
            if busqueda and (busqueda or "").strip():
                q = (busqueda or "").strip()
                cursor.execute(
                    f"""
                    SELECT id_sue_abm_empleado, COALESCE(nombre_empleado, '') AS nombre_empleado
                    FROM {tbl}
                    WHERE (COALESCE(anulado, 'No') = 'No')
                      AND (nombre_empleado LIKE %s)
                    ORDER BY nombre_empleado
                    LIMIT %s
                    """,
                    [f"%{q}%", limit],
                )
            else:
                cursor.execute(
                    f"""
                    SELECT id_sue_abm_empleado, COALESCE(nombre_empleado, '') AS nombre_empleado
                    FROM {tbl}
                    WHERE COALESCE(anulado, 'No') = 'No'
                    ORDER BY nombre_empleado
                    LIMIT %s
                    """,
                    [limit],
                )
            rows = cursor.fetchall()
            columns = [d[0] for d in cursor.description] if cursor.description else []
            result = []
            for row in rows:
                row_dict = dict(zip(columns, row)) if columns else {}
                id_emp = to_int_or_none(row_dict.get("id_sue_abm_empleado"))
                nombre = str_or_default(row_dict.get("nombre_empleado"), "-")
                if id_emp is not None:
                    result.append({"id": id_emp, "label": nombre})
            return result
    except Exception as e:
        logger.warning("Error al listar empleados operarios en %s: %s", base_empresa, e, exc_info=True)
        return []


def listar_operarios_crud(
    base_empresa: str,
    incluir_anulados: bool = False,
    busqueda: Optional[str] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """
    Lista operarios (sue_abm_empleado) para CRUD.
    Devuelve lista de dict con id_sue_abm_empleado, nombre_empleado, id_cliente, anulado.
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "sue_abm_empleado")
            if not tbl:
                return []
            if incluir_anulados:
                where = "1=1"
                params: List[Any] = []
            else:
                where = "COALESCE(anulado, 'No') = 'No'"
                params = []
            if busqueda and (busqueda or "").strip():
                where += " AND (nombre_empleado LIKE %s)"
                params.append(f"%{(busqueda or '').strip()}%")
            params.append(limit)
            cursor.execute(
                f"""
                SELECT id_sue_abm_empleado, COALESCE(nombre_empleado, '') AS nombre_empleado,
                       id_cliente, COALESCE(anulado, 'No') AS anulado
                FROM {tbl}
                WHERE {where}
                ORDER BY anulado ASC, nombre_empleado
                LIMIT %s
                """,
                params,
            )
            rows = cursor.fetchall()
            columns = [d[0] for d in cursor.description] if cursor.description else []
            result = []
            for row in rows:
                row_dict = dict(zip(columns, row)) if columns else {}
                result.append({
                    "id_sue_abm_empleado": to_int_or_none(row_dict.get("id_sue_abm_empleado")),
                    "nombre_empleado": str_or_default(row_dict.get("nombre_empleado"), ""),
                    "id_cliente": to_int_or_none(row_dict.get("id_cliente")),
                    "anulado": str_or_default(row_dict.get("anulado"), "No"),
                })
            return result
    except Exception as e:
        logger.warning("Error al listar operarios CRUD en %s: %s", base_empresa, e, exc_info=True)
        return []


def obtener_operario(base_empresa: str, id_sue_abm_empleado: int) -> Optional[Dict[str, Any]]:
    """Obtiene un operario por id_sue_abm_empleado. Devuelve None si no existe."""
    if not (base_empresa or "").strip() or id_sue_abm_empleado is None:
        return None
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "sue_abm_empleado")
            if not tbl:
                return None
            cursor.execute(
                f"""
                SELECT id_sue_abm_empleado, COALESCE(nombre_empleado, '') AS nombre_empleado,
                       id_cliente, COALESCE(anulado, 'No') AS anulado
                FROM {tbl}
                WHERE id_sue_abm_empleado = %s
                """,
                [id_sue_abm_empleado],
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [d[0] for d in cursor.description] if cursor.description else []
            row_dict = dict(zip(columns, row)) if columns else {}
            return {
                "id_sue_abm_empleado": to_int_or_none(row_dict.get("id_sue_abm_empleado")),
                "nombre_empleado": str_or_default(row_dict.get("nombre_empleado"), ""),
                "id_cliente": to_int_or_none(row_dict.get("id_cliente")),
                "anulado": str_or_default(row_dict.get("anulado"), "No"),
            }
    except Exception as e:
        logger.warning("Error al obtener operario %s en %s: %s", id_sue_abm_empleado, base_empresa, e, exc_info=True)
        return None


def crear_operario(
    base_empresa: str,
    nombre_empleado: str,
    id_cliente: Optional[int] = None,
) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Crea un operario en sue_abm_empleado.
    Devuelve (ok, id_sue_abm_empleado, mensaje_error).
    """
    if not (base_empresa or "").strip():
        return False, None, "Falta base_empresa"
    nombre = (nombre_empleado or "").strip()
    if not nombre:
        return False, None, "El nombre del operario es obligatorio."
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "sue_abm_empleado")
            if not tbl:
                return False, None, "Tabla sue_abm_empleado no encontrada."
            new_id = None
            try:
                cursor.execute(
                    f"""
                    INSERT INTO {tbl} (nombre_empleado, id_cliente, anulado)
                    VALUES (%s, %s, 'No')
                    """,
                    [nombre, id_cliente],
                )
                new_id = cursor.lastrowid
            except Exception as insert_err:
                if "default value" in str(insert_err).lower() or "field" in str(insert_err).lower():
                    cursor.execute(f"SELECT COALESCE(MAX(id_sue_abm_empleado), 0) + 1 FROM {tbl}")
                    row = cursor.fetchone()
                    new_id = to_int_or_none(row[0]) if row else 1
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl} (id_sue_abm_empleado, nombre_empleado, id_cliente, anulado)
                        VALUES (%s, %s, %s, 'No')
                        """,
                        [new_id, nombre, id_cliente],
                    )
                else:
                    raise
            conn.commit()
            if new_id is None or new_id == 0:
                cursor.execute(f"SELECT MAX(id_sue_abm_empleado) FROM {tbl}")
                row = cursor.fetchone()
                new_id = to_int_or_none(row[0]) if row else None
            return True, new_id, None
    except Exception as e:
        logger.warning("Error al crear operario en %s: %s", base_empresa, e, exc_info=True)
        return False, None, str(e)


def actualizar_operario(
    base_empresa: str,
    id_sue_abm_empleado: int,
    nombre_empleado: str,
    id_cliente: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Actualiza nombre_empleado e id_cliente de un operario.
    Devuelve (ok, mensaje_error).
    """
    if not (base_empresa or "").strip() or id_sue_abm_empleado is None:
        return False, "Parámetros inválidos"
    nombre = (nombre_empleado or "").strip()
    if not nombre:
        return False, "El nombre del operario es obligatorio."
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "sue_abm_empleado")
            if not tbl:
                return False, "Tabla sue_abm_empleado no encontrada."
            cursor.execute(
                f"""
                UPDATE {tbl}
                SET nombre_empleado = %s, id_cliente = %s
                WHERE id_sue_abm_empleado = %s
                """,
                [nombre, id_cliente, id_sue_abm_empleado],
            )
            conn.commit()
            return True, None
    except Exception as e:
        logger.warning("Error al actualizar operario %s en %s: %s", id_sue_abm_empleado, base_empresa, e, exc_info=True)
        return False, str(e)


def anular_operario(base_empresa: str, id_sue_abm_empleado: int) -> Tuple[bool, Optional[str]]:
    """Marca operario como anulado (anulado='Si'). Devuelve (ok, mensaje_error)."""
    if not (base_empresa or "").strip() or id_sue_abm_empleado is None:
        return False, "Parámetros inválidos"
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "sue_abm_empleado")
            if not tbl:
                return False, "Tabla sue_abm_empleado no encontrada."
            cursor.execute(
                f"UPDATE {tbl} SET anulado = 'Si' WHERE id_sue_abm_empleado = %s",
                [id_sue_abm_empleado],
            )
            conn.commit()
            return True, None
    except Exception as e:
        logger.warning("Error al anular operario %s en %s: %s", id_sue_abm_empleado, base_empresa, e, exc_info=True)
        return False, str(e)


def reactivar_operario(base_empresa: str, id_sue_abm_empleado: int) -> Tuple[bool, Optional[str]]:
    """Marca operario como activo (anulado='No'). Devuelve (ok, mensaje_error)."""
    if not (base_empresa or "").strip() or id_sue_abm_empleado is None:
        return False, "Parámetros inválidos"
    try:
        with get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            tbl = _nombre_tabla(cursor, "sue_abm_empleado")
            if not tbl:
                return False, "Tabla sue_abm_empleado no encontrada."
            cursor.execute(
                f"UPDATE {tbl} SET anulado = 'No' WHERE id_sue_abm_empleado = %s",
                [id_sue_abm_empleado],
            )
            conn.commit()
            return True, None
    except Exception as e:
        logger.warning("Error al reactivar operario %s en %s: %s", id_sue_abm_empleado, base_empresa, e, exc_info=True)
        return False, str(e)


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
                raise MprSchemaError(
                    "Faltan tablas en la base de datos: lista_produccion_agrupada o articulo. Cree las tablas o verifique el esquema para usar MPR."
                )
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
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error al crear OPT agrupada en %s: %s", base_empresa, e, exc_info=True)
        return False, None, str(e)


def crear_opt_multiples_articulos(
    base_empresa: str,
    id_usuario: Optional[int],
    lineas: List[Tuple[int, int, Optional[int]]],
) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Crea una OPT (Pedido de producción) con múltiples artículos.

    No inserta filas nuevas: actualiza las existentes en lista_produccion_agrupada y
    lista_produccion_detalle (en_proceso_produccion = 'Si', id_opt, id_operario_opt).
    La OPT se identifica por id_opt en lista_produccion_agrupada (no se usan mpr_opt/mpr_opt_linea).

    lineas: lista de (id_articulo, cantidad, id_operario_opt) con cantidad > 0.
    Requiere que existan filas en lista_produccion_agrupada con en_proceso_produccion = 'No'
    para cada artículo (ejecutar «Actualizar» pedidos antes).
    Devuelve (ok, id_lista_principal, mensaje_error).
    """
    if not (base_empresa or "").strip():
        return False, None, "Base de datos no indicada."
    normalized = []
    for item in lineas:
        if len(item) >= 3:
            a, q, op = to_int_or_none(item[0]), to_int_or_none(item[1]), to_int_or_none(item[2])
        else:
            a, q, op = to_int_or_none(item[0]), to_int_or_none(item[1]), None
        if a and q is not None and q > 0:
            normalized.append((a, q, op))
    lineas = normalized
    if not lineas:
        return False, None, "Indique al menos un artículo con cantidad positiva."
    try:
        ids_creados = []
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            try:
                tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
                tbl_articulo = _nombre_tabla(cursor, "articulo")
                if not tbl_agrupada or not tbl_articulo:
                    raise MprSchemaError(
                        "Faltan tablas en la base de datos: lista_produccion_agrupada o articulo. Cree las tablas o verifique el esquema para usar MPR."
                    )
                # Resolver id_lista_produccion existente por artículo (solo filas con en_proceso_produccion = 'No')
                for id_articulo, cantidad, id_operario_opt in lineas:
                    cursor.execute(
                        f"""
                        SELECT id_lista_produccion FROM {tbl_agrupada}
                        WHERE id_articulo = %s AND COALESCE(TRIM(en_proceso_produccion), 'No') = 'No'
                        ORDER BY id_lista_produccion LIMIT 1
                        """,
                        [id_articulo],
                    )
                    row = cursor.fetchone()
                    if not row:
                        return (
                            False,
                            None,
                            f"No hay fila en lista de producción (en_proceso_produccion='No') para el artículo {id_articulo}. Ejecute «Actualizar» pedidos primero.",
                        )
                    id_lista = to_int_or_none(row[0])
                    if not id_lista:
                        return False, None, f"No se pudo obtener id_lista_produccion para artículo {id_articulo}."
                    ids_creados.append((id_articulo, cantidad, id_lista, id_operario_opt))
                id_lista_principal = ids_creados[0][2]
                # Actualizar lista_produccion_agrupada: en_proceso_produccion, cantidad_pendiente_prod, id_opt, id_operario_opt
                for id_articulo, cantidad, id_lista, id_operario_opt in ids_creados:
                    try:
                        cursor.execute(
                            f"UPDATE {tbl_agrupada} SET en_proceso_produccion = 'Si', cantidad_pendiente_prod = %s, id_opt = %s, id_operario_opt = %s WHERE id_lista_produccion = %s",
                            [cantidad, id_lista_principal, id_operario_opt, id_lista],
                        )
                    except Exception as upd_err:
                        err_msg = str(upd_err).lower()
                        if "1054" in str(upd_err) or "unknown column" in err_msg or "id_opt" in err_msg or "id_operario_opt" in err_msg:
                            raise MprSchemaError(
                                "Faltan columnas id_opt o id_operario_opt en lista_produccion_agrupada. "
                                "Ejecute el script docs/mpr/sql/alter_lista_produccion_agrupada_mpr_opt.sql en la base MySQL."
                            ) from upd_err
                        logger.warning("No se pudo actualizar lista_produccion_agrupada id_lista=%s: %s", id_lista, upd_err)
                        return False, None, f"Error al actualizar lista de producción (id_lista={id_lista})."
                # Marcar pedidos en producción y lista_produccion_detalle.en_proceso_produccion = 'Si'
                ids_lista_produccion = [lid for _, _, lid, _ in ids_creados]
                tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
                tbl_cp = _nombre_tabla(cursor, "comp_ped")
                if tbl_detalle and tbl_cp and ids_lista_produccion:
                    ph = ",".join(["%s"] * len(ids_lista_produccion))
                    try:
                        cursor.execute(
                            f"UPDATE {tbl_detalle} SET en_proceso_produccion = 'Si' WHERE id_lista_produccion IN ({ph})",
                            ids_lista_produccion,
                        )
                    except Exception as det_err:
                        if "1054" in str(det_err):
                            ids_articulo = [a for a, *_ in lineas]
                            ph_art = ",".join(["%s"] * len(ids_articulo))
                            cursor.execute(
                                f"SELECT DISTINCT codigo_movimiento_pedido FROM {tbl_detalle} WHERE id_articulo IN ({ph_art})",
                                ids_articulo,
                            )
                            codigos = [to_int_or_none(r[0]) for r in cursor.fetchall() if to_int_or_none(r[0]) is not None]
                            if codigos:
                                _actualizar_comp_ped_estado_produccion(cursor, tbl_cp, codigos, "Produccion")
                                try:
                                    ph_cod = ",".join(["%s"] * len(codigos))
                                    cursor.execute(
                                        f"UPDATE {tbl_detalle} SET en_proceso_produccion = 'Si' WHERE codigo_movimiento_pedido IN ({ph_cod}) AND id_articulo IN ({ph_art})",
                                        codigos + ids_articulo,
                                    )
                                except Exception as det_err2:
                                    logger.warning("No se pudo actualizar lista_produccion_detalle.en_proceso_produccion: %s", det_err2)
                        else:
                            logger.warning("No se pudo actualizar lista_produccion_detalle.en_proceso_produccion: %s", det_err)
                    else:
                        codigos = []
                        try:
                            cursor.execute(
                                f"SELECT DISTINCT codigo_movimiento_pedido FROM {tbl_detalle} WHERE id_lista_produccion IN ({ph})",
                                ids_lista_produccion,
                            )
                            codigos = [to_int_or_none(r[0]) for r in cursor.fetchall() if to_int_or_none(r[0]) is not None]
                        except Exception:
                            pass
                        if codigos:
                            _actualizar_comp_ped_estado_produccion(cursor, tbl_cp, codigos, "Produccion")
                conn.commit()
                return True, id_lista_principal, None
            except Exception:
                conn.rollback()
                raise
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error al crear OPT múltiples artículos en %s: %s", base_empresa, e, exc_info=True)
        return False, None, str(e)


def _explode_packs_to_components(
    base_empresa: str,
    distribucion: List[Tuple[Dict[str, Any], int]],
) -> Dict[int, float]:
    """
    Explota una distribución (pack, qty_pack) a cantidades por artículo componente.

    Por cada (linea, qty_pack): si el artículo tiene BOM (id_en_abm, en_abm_formula),
    suma por cada componente qty_pack * cantidad_articulo; si no tiene BOM, trata
    el artículo como componente (suma id_articulo, qty_pack).
    Devuelve dict id_articulo -> qty_total (agregado por componente).
    """
    if not (base_empresa or "").strip() or not distribucion:
        return {}
    agregado: Dict[int, float] = {}
    pack_ids = list({to_int_or_none(l.get("id_articulo")) for l, q in distribucion if to_int_or_none(l.get("id_articulo")) and q > 0})
    abm_map = bulk_id_en_abm(base_empresa, pack_ids) if pack_ids else {}
    bom_cache = bulk_bom_detalle(base_empresa, list(set(abm_map.values()))) if abm_map else {}

    for linea, qty_pack in distribucion:
        id_pack = to_int_or_none(linea.get("id_articulo"))
        if id_pack is None or qty_pack <= 0:
            continue
        id_en_abm = abm_map.get(id_pack)
        bom = bom_cache.get(id_en_abm) if id_en_abm else None
        if bom and bom.get("componentes"):
            for comp in bom["componentes"]:
                id_comp = to_int_or_none(comp.get("id_articulo"))
                if id_comp is None:
                    continue
                cant = float(comp.get("cantidad_articulo") or 0) * qty_pack
                if cant > 0:
                    agregado[id_comp] = agregado.get(id_comp, 0) + cant
        else:
            # Sin BOM: el artículo es su propio "componente"
            agregado[id_pack] = agregado.get(id_pack, 0) + float(qty_pack)

    return agregado


def get_opp_componentes_disponibles(
    base_empresa: str,
    id_lista_produccion: int,
) -> List[Dict[str, Any]]:
    """
    Devuelve la lista de componentes con unidades disponibles para distribuir en OPP.

    Explota los packs de la OPT (get_opt_detalle) × cantidad_pendiente_prod vía BOM;
    agrega por id_articulo componente y devuelve id_articulo, codigo_articulo,
    descripcion_articulo, disponible_unidades. Orden estable por id_articulo.
    """
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return []
    lineas = get_opt_detalle(base_empresa, id_lista_produccion)
    if not lineas:
        return []
    distribucion = [
        (linea, int(linea.get("cantidad_pendiente_prod") or 0))
        for linea in lineas
        if (int(linea.get("cantidad_pendiente_prod") or 0) > 0)
    ]
    if not distribucion:
        return []
    agregado = _explode_packs_to_components(base_empresa, distribucion)
    if not agregado:
        return []
    ids = sorted(agregado.keys())
    resultado = []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_articulo:
                for id_art in ids:
                    resultado.append({
                        "id_articulo": id_art,
                        "codigo_articulo": str(id_art),
                        "descripcion_articulo": "-",
                        "disponible_unidades": agregado[id_art],
                    })
                return resultado
            placeholders = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"""
                SELECT IDArt, COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo,
                       COALESCE(NombreArticulo, '') AS descripcion
                FROM {tbl_articulo}
                WHERE IDArt IN ({placeholders})
                """,
                ids,
            )
            art_por_id = {}
            for r in cursor.fetchall() or []:
                aid = to_int_or_none(r.get("IDArt"))
                if aid is not None:
                    art_por_id[aid] = (
                        str_or_default(r.get("codigo"), str(aid)),
                        str_or_default(r.get("descripcion"), "-"),
                    )
            for id_art in ids:
                codigo, descripcion = art_por_id.get(id_art, (str(id_art), "-"))
                resultado.append({
                    "id_articulo": id_art,
                    "codigo_articulo": codigo,
                    "descripcion_articulo": descripcion,
                    "disponible_unidades": agregado[id_art],
                })
    except Exception as e:
        logger.warning(
            "Error al obtener componentes OPP disponibles base_empresa=%s id_lista=%s: %s",
            base_empresa, id_lista_produccion, e,
            exc_info=True,
        )
        return []
    return resultado


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
    Ejecuta la liberación OPT: movimiento_stock (motivo 11, tipo_mov OPT), stock (entradas de
    componentes en depósito Producción), stock_deposito, y actualiza lista_produccion_agrupada.
    La distribución (pack, qty) se explota a componentes vía BOM; se mueven componentes, no packs.
    Opcional: lista_produccion_historico (una fila por componente).

    lineas: resultado de get_opt_detalle (packs con cantidad_pendiente_prod).
    cantidad_total: cantidad total a liberar en unidades pack (se reparte entre líneas).
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
    hora_evento = datetime.now().strftime("%H:%M:%S")
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
                tbl_articulo = _nombre_tabla(cursor, "articulo")
                if not all([tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd, tbl_agrupada]):
                    conn.rollback()
                    faltan = [n for n, t in [
                        ("codmov", tbl_codmov), ("talonarios", tbl_talonarios), ("movimiento_stock", tbl_mov),
                        ("stock", tbl_stock), ("stock_deposito", tbl_sd), ("lista_produccion_agrupada", tbl_agrupada),
                    ] if not t]
                    raise MprSchemaError(
                        f"Faltan tablas en la base de datos: {', '.join(faltan)}. Cree las tablas o verifique el esquema para usar MPR."
                    )
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
                # (3) INSERT movimiento_stock (OPT: origen = destino = depósito producción).
                # tipo_comprobante = 'MSTOCK' (talonario); tipo_mov = TIPO_MOV_OPT; id_operario_opt = mismo que lista_produccion_agrupada.
                # hora_entrada_opt = fecha y hora en que se crea la OPT (liberación).
                id_operario_opt = to_int_or_none(lineas[0].get("id_operario_opt")) if lineas else None
                hora_entrada_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
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
                    TIPO_MOV_OPT,  # tipo_mov: OPT (no confundir con tipo_comprobante que es MSTOCK)
                    id_pv,
                    nro_comprobante_busq,
                    id_operario_opt,
                ]
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq, id_operario_opt, hora_entrada_opt)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov + [hora_entrada_dt],
                    )
                except Exception as ins_err:
                    if "1054" in str(ins_err):
                        try:
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_mov}
                                (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                                 detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq, hora_entrada_opt)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                params_mov[:15] + [hora_entrada_dt],
                            )
                        except Exception as ins_err2:
                            if "1054" in str(ins_err2):
                                try:
                                    cursor.execute(
                                        f"""
                                        INSERT INTO {tbl_mov}
                                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq, id_operario_opt)
                                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s, %s)
                                        """,
                                        params_mov[:17],
                                    )
                                except Exception as ins_err3:
                                    if "1054" in str(ins_err3):
                                        params_mov_sin_busq = params_mov[:15]
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
                                        raise MprSchemaError(formatear_error_esquema(ins_err3, "movimiento_stock")) from ins_err3
                            else:
                                raise MprSchemaError(formatear_error_esquema(ins_err2, "movimiento_stock")) from ins_err2
                    else:
                        raise MprSchemaError(formatear_error_esquema(ins_err, "movimiento_stock")) from ins_err
                # (4) Explotar distribución (pack, qty) a componentes y mover componentes a Producción
                componentes_qty = _explode_packs_to_components(base_empresa, distribucion)
                id_en_abm_liberar = None
                if distribucion:
                    id_art_pack_primero = to_int_or_none(distribucion[0][0].get("id_articulo"))
                    if id_art_pack_primero is not None:
                        id_en_abm_liberar = get_id_en_abm_por_articulo(base_empresa, id_art_pack_primero)
                articulo_info: Dict[int, Tuple[str, str]] = {}
                if componentes_qty and tbl_articulo:
                    ids_comp = list(componentes_qty.keys())
                    placeholders = ",".join(["%s"] * len(ids_comp))
                    cursor.execute(
                        f"SELECT IDArt, COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo, COALESCE(NombreArticulo, '') AS descripcion FROM {tbl_articulo} WHERE IDArt IN ({placeholders})",
                        ids_comp,
                    )
                    for r in cursor.fetchall() or []:
                        aid = to_int_or_none(r[0])
                        if aid is not None:
                            articulo_info[aid] = (str_or_default(r[1], "-"), str_or_default(r[2], "-"))
                orden = 0
                for id_art in sorted(componentes_qty.keys()):
                    qty = componentes_qty[id_art]
                    if qty <= 0:
                        continue
                    codigo_art, descripcion_art = articulo_info.get(id_art, ("-", "-"))
                    entrada = Decimal(str(qty))
                    orden += 1
                    cursor.execute(
                        f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                        [id_art, deposito_destino],
                    )
                    sd_row = cursor.fetchone()
                    saldo_actual = Decimal(str(sd_row[1] or 0)) if sd_row else Decimal(0)
                    saldo_despues = saldo_actual + entrada
                    params_stock = [
                        codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov,
                        entrada, saldo_despues, deposito_destino, id_ref_movstock,
                        orden, id_usuario, MOTIVO_OPT_TEXTO, nro_comprobante, None,
                    ]
                    params_stock_con_opt_abm = params_stock + [codigo_mov, id_en_abm_liberar]
                    try:
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                            """,
                            params_stock_con_opt_abm,
                        )
                    except Exception as stock_err:
                        if "1054" in str(stock_err):
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                """,
                                params_stock,
                            )
                        else:
                            raise
                    if sd_row:
                        cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_despues, sd_row[0]])
                    else:
                        cursor.execute(
                            f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                            [id_art, deposito_destino, saldo_despues],
                        )
                # Actualizar lista_produccion_agrupada por pack: marcar en proceso (NO decrementar cantidad_pendiente_prod al liberar)
                for linea, _ in distribucion:
                    id_lista_linea = to_int_or_none(linea.get("id_lista_produccion")) or id_lista_produccion
                    id_art_pack = to_int_or_none(linea.get("id_articulo"))
                    if id_art_pack is not None:
                        cursor.execute(
                            f"UPDATE {tbl_agrupada} SET en_proceso_produccion = 'Si' "
                            "WHERE id_lista_produccion = %s AND id_articulo = %s",
                            [id_lista_linea, id_art_pack],
                        )
                cursor.execute(
                    f"UPDATE {tbl_agrupada} SET en_proceso_produccion = 'Si' WHERE id_lista_produccion = %s",
                    [id_lista_produccion],
                )
                # (5) Log de eventos por (pack, componente): id_articulo = pack, id_articulo_formula = componente
                tbl_historico = _nombre_tabla(cursor, "lista_produccion_historico")
                if tbl_historico and distribucion:
                    for linea, qty_pack in distribucion:
                        id_art_pack = to_int_or_none(linea.get("id_articulo"))
                        if id_art_pack is None or qty_pack <= 0:
                            continue
                        comps_esta_linea = _explode_packs_to_components(base_empresa, [(linea, qty_pack)])
                        for id_art_comp in sorted(comps_esta_linea.keys()):
                            qty_comp = comps_esta_linea[id_art_comp]
                            if qty_comp <= 0:
                                continue
                            try:
                                cursor.execute(
                                    f"""
                                    INSERT INTO {tbl_historico}
                                    (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                     id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                     nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento)
                                    VALUES ('OPT', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    [
                                        id_art_pack,
                                        id_art_comp,
                                        qty_comp,
                                        deposito_destino,
                                        deposito_destino,
                                        deposito_destino,
                                        codigo_mov,
                                        codigo_mov,
                                        nro_comprobante,
                                        id_usuario,
                                        id_lista_produccion,
                                        fecha_mov,
                                        hora_evento,
                                        fecha_mov,
                                        hora_evento,
                                    ],
                                )
                            except Exception as hist_err:
                                logger.warning("No se pudo insertar lista_produccion_historico: %s", hist_err)
                conn.commit()
                # Vincular codigo_movimiento a la OPT en lista_produccion_agrupada (fila principal) para imprimir comprobante
                try:
                    cursor.execute(
                        f"SELECT id_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                        [id_lista_produccion],
                    )
                    row_opt = cursor.fetchone()
                    id_opt_val = to_int_or_none(row_opt[0]) if row_opt and row_opt[0] is not None else None
                    if id_opt_val is not None:
                        cursor.execute(
                            f"UPDATE {tbl_agrupada} SET codigo_movimiento_opt = %s WHERE id_lista_produccion = %s",
                            [codigo_mov, id_opt_val],
                        )
                        conn.commit()
                except Exception as opt_err:
                    if "1054" not in str(opt_err) and "unknown column" not in str(opt_err).lower():
                        logger.warning("No se pudo actualizar lista_produccion_agrupada.codigo_movimiento_opt: %s", opt_err)
                return True, codigo_mov, nro_comprobante, None
            except MprSchemaError:
                conn.rollback()
                raise
            except Exception as e:
                conn.rollback()
                if "1054" in str(e) or "Unknown column" in str(e).lower():
                    raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
                logger.warning("Error en ejecutar_liberar_opt: %s", e, exc_info=True)
                return False, None, None, str(e)
    except MprSchemaError:
        raise
    except Exception as e:
        if "1054" in str(e) or "Unknown column" in str(e).lower():
            raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
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
    distribucion: Optional[List[Tuple[Dict[str, Any], int]]] = None,
) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    Registra Parte de producción (OPP): movimiento Salida desde deposito_origen (Producción) y Entrada
    a deposito_destino (Semi Elaborado, Scrap, 2da) para los componentes. La distribución (pack, qty)
    se explota a componentes vía BOM; se mueven componentes, no packs. Valida stock de componentes en
    origen antes de crear movimientos. Actualiza lista_produccion_agrupada (cantidad_pendiente_prod por pack).

    lineas: resultado de get_opt_detalle (packs).
    distribucion: opcional. Lista de (linea_dict, cantidad_pack) por destino; si no se pasa, se calcula con _distribuir_cantidad_a_lineas.
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
    if distribucion is None:
        distribucion = _distribuir_cantidad_a_lineas(lineas, cantidad_total)
    if not distribucion:
        return False, None, None, "No hay cantidad a registrar para las líneas indicadas."
    # Validar que ninguna línea asigne más que el pendiente original del artículo
    for linea, qty in distribucion:
        id_art = to_int_or_none(linea.get("id_articulo"))
        pendiente = int(linea.get("cantidad_pendiente_prod") or 0)
        if id_art is not None and qty > pendiente:
            codigo = linea.get("codigo_articulo") or id_art
            return False, None, None, (
                f"Artículo {codigo}: la cantidad ({qty}) no puede superar el pendiente ({pendiente})."
            )
    id_ref_movstock = 1
    id_pv = 1
    fecha_mov = date.today().isoformat()
    hora_evento = datetime.now().strftime("%H:%M:%S")
    detalle_mov = f"OPT {id_lista_produccion} desde MPR"
    codigo_mov_opt = get_codigo_movimiento_opt(base_empresa, id_lista_produccion)
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
                tbl_articulo = _nombre_tabla(cursor, "articulo")
                if not all([tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd]):
                    conn.rollback()
                    faltan = [n for n, t in [
                        ("codmov", tbl_codmov), ("talonarios", tbl_talonarios), ("movimiento_stock", tbl_mov),
                        ("stock", tbl_stock), ("stock_deposito", tbl_sd),
                    ] if not t]
                    raise MprSchemaError(
                        f"Faltan tablas en la base de datos: {', '.join(faltan)}. Cree las tablas o verifique el esquema para usar MPR."
                    )
                # Explotar distribución (pack, qty) a componentes y validar stock en origen (Producción)
                componentes_qty = _explode_packs_to_components(base_empresa, distribucion)
                if componentes_qty and tbl_sd:
                    for id_comp in componentes_qty:
                        qty_necesaria = componentes_qty[id_comp]
                        if qty_necesaria <= 0:
                            continue
                        cursor.execute(
                            f"SELECT saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s",
                            [id_comp, deposito_origen],
                        )
                        row_sd = cursor.fetchone()
                        saldo_orig = float(row_sd[0] or 0) if row_sd else 0
                        if saldo_orig < qty_necesaria:
                            codigo_comp = str(id_comp)
                            if tbl_articulo:
                                cursor.execute(
                                    f"SELECT COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') FROM {tbl_articulo} WHERE IDArt = %s",
                                    [id_comp],
                                )
                                rcod = cursor.fetchone()
                                if rcod:
                                    codigo_comp = str_or_default(rcod[0], codigo_comp)
                            conn.rollback()
                            return False, None, None, (
                                f"Stock insuficiente del componente {codigo_comp} en Producción: tiene {int(saldo_orig)}, se necesitan {int(qty_necesaria)}."
                            )
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
                        try:
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_mov}
                                (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                                 detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                                """,
                                params_mov[:14],
                            )
                        except Exception as ins_err2:
                            raise MprSchemaError(formatear_error_esquema(ins_err2, "movimiento_stock")) from ins_err2
                    else:
                        raise MprSchemaError(formatear_error_esquema(ins_err, "movimiento_stock")) from ins_err
                # Cargar codigo/descripcion de componentes desde articulo
                id_en_abm_opp = None
                if distribucion:
                    id_art_pack_opp = to_int_or_none(distribucion[0][0].get("id_articulo"))
                    if id_art_pack_opp is not None:
                        id_en_abm_opp = get_id_en_abm_por_articulo(base_empresa, id_art_pack_opp)
                articulo_info_opp: Dict[int, Tuple[str, str]] = {}
                if componentes_qty and tbl_articulo:
                    ids_comp = list(componentes_qty.keys())
                    placeholders = ",".join(["%s"] * len(ids_comp))
                    cursor.execute(
                        f"SELECT IDArt, COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo, COALESCE(NombreArticulo, '') AS descripcion FROM {tbl_articulo} WHERE IDArt IN ({placeholders})",
                        ids_comp,
                    )
                    for r in cursor.fetchall() or []:
                        aid = to_int_or_none(r[0])
                        if aid is not None:
                            articulo_info_opp[aid] = (str_or_default(r[1], "-"), str_or_default(r[2], "-"))
                orden = 0
                for id_art in sorted(componentes_qty.keys()):
                    qty = componentes_qty[id_art]
                    if qty <= 0:
                        continue
                    codigo_art, descripcion_art = articulo_info_opp.get(id_art, ("-", "-"))
                    salida = Decimal(str(qty))
                    # Salida desde origen (Producción)
                    cursor.execute(
                        f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                        [id_art, deposito_origen],
                    )
                    sd_orig = cursor.fetchone()
                    saldo_orig = Decimal(str(sd_orig[1] or 0)) if sd_orig else Decimal(0)
                    saldo_orig_despues = saldo_orig - salida
                    orden += 1
                    params_salida = [
                        codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov,
                        salida, saldo_orig_despues, deposito_origen, id_ref_movstock,
                        orden, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None,
                    ]
                    params_salida_opt_abm = params_salida + [codigo_mov_opt, id_en_abm_opp]
                    try:
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                            """,
                            params_salida_opt_abm,
                        )
                    except Exception as stock_err:
                        if "1054" in str(stock_err):
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                """,
                                params_salida,
                            )
                        else:
                            raise
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
                    params_entrada = [
                        codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov,
                        salida, saldo_dest_despues, deposito_destino, id_ref_movstock,
                        orden, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None,
                    ]
                    params_entrada_opt_abm = params_entrada + [codigo_mov_opt, id_en_abm_opp]
                    try:
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                            """,
                            params_entrada_opt_abm,
                        )
                    except Exception as stock_err:
                        if "1054" in str(stock_err):
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                """,
                                params_entrada,
                            )
                        else:
                            raise
                    if sd_dest:
                        cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_dest_despues, sd_dest[0]])
                    else:
                        cursor.execute(
                            f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                            [id_art, deposito_destino, saldo_dest_despues],
                        )
                # Descontar pendiente por pack en lista_produccion_agrupada
                for linea, qty in distribucion:
                    id_lista_linea = to_int_or_none(linea.get("id_lista_produccion")) or id_lista_produccion
                    id_art_pack = to_int_or_none(linea.get("id_articulo"))
                    if tbl_agrupada and id_art_pack is not None:
                        try:
                            cursor.execute(
                                f"UPDATE {tbl_agrupada} SET cantidad_pendiente_prod = GREATEST(0, COALESCE(cantidad_pendiente_prod, 0) - %s) WHERE id_lista_produccion = %s AND id_articulo = %s",
                                [qty, id_lista_linea, id_art_pack],
                            )
                        except Exception as agg_err:
                            logger.warning("No se pudo actualizar lista_produccion_agrupada en OPP: %s", agg_err)
                # Log de eventos por (pack, componente): id_articulo = pack, id_articulo_formula = componente
                tbl_historico = _nombre_tabla(cursor, "lista_produccion_historico")
                if tbl_historico and distribucion:
                    for linea, qty in distribucion:
                        id_art_pack = to_int_or_none(linea.get("id_articulo"))
                        if id_art_pack is None or qty <= 0:
                            continue
                        comps_esta_linea = _explode_packs_to_components(base_empresa, [(linea, qty)])
                        for id_art_comp in sorted(comps_esta_linea.keys()):
                            qty_comp = comps_esta_linea[id_art_comp]
                            if qty_comp <= 0:
                                continue
                            try:
                                cursor.execute(
                                    f"""
                                    INSERT INTO {tbl_historico}
                                    (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                     id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                     nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento)
                                    VALUES ('OPP', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    [
                                        id_art_pack,
                                        id_art_comp,
                                        qty_comp,
                                        deposito_destino,
                                        deposito_origen,
                                        deposito_destino,
                                        codigo_mov,
                                        codigo_mov_opt,
                                        nro_comprobante,
                                        id_usuario,
                                        id_lista_produccion,
                                        fecha_mov,
                                        hora_evento,
                                        fecha_mov,
                                        hora_evento,
                                    ],
                                )
                            except Exception as hist_err:
                                logger.warning("No se pudo insertar lista_produccion_historico (OPP): %s", hist_err)
                conn.commit()
                return True, codigo_mov, nro_comprobante, None
            except MprSchemaError:
                conn.rollback()
                raise
            except Exception as e:
                conn.rollback()
                if "1054" in str(e) or "Unknown column" in str(e).lower():
                    raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
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
    except MprSchemaError:
        raise
    except Exception as e:
        if "1054" in str(e) or "Unknown column" in str(e).lower():
            raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
        logger.exception("Error de conexión en ejecutar_opp: %s", e)
        return False, None, None, str(e)


def _calcular_decrementos_pack_desde_componentes(
    base_empresa: str,
    lineas: List[Dict[str, Any]],
    total_dispatch: Dict[int, float],
) -> List[Tuple[int, int, float]]:
    """
    Dado total_dispatch (id_componente -> unidades distribuidas) y lineas de la OPT (packs),
    calcula cuánto decrementar cantidad_pendiente_prod por cada pack (equivalente pack).
    Escala proporcionalmente cuando un componente es compartido por varios packs.
    Devuelve lista de (id_lista_produccion, id_articulo_pack, d_p) para actualizar lista_produccion_agrupada.
    """
    if not lineas or not total_dispatch:
        return []
    # Por cada pack: BOM -> (comp, qty). d_p_raw = min_comp(total_dispatch[comp]/qty), d_p = min(pendiente, d_p_raw)
    pack_bom: List[Tuple[Dict[str, Any], Dict[int, float]]] = []  # (linea, {id_comp: qty_en_bom})
    for linea in lineas:
        id_pack = to_int_or_none(linea.get("id_articulo"))
        if id_pack is None:
            continue
        id_en_abm = get_id_en_abm_por_articulo(base_empresa, id_pack)
        bom = get_bom_detalle(base_empresa, id_en_abm) if id_en_abm else None
        bom_qty: Dict[int, float] = {}
        if bom and bom.get("componentes"):
            for c in bom["componentes"]:
                id_comp = to_int_or_none(c.get("id_articulo"))
                if id_comp is not None:
                    qty = float(c.get("cantidad_articulo") or 0)
                    if qty > 0:
                        bom_qty[id_comp] = qty
        if not bom_qty:
            # Sin BOM: el pack es su propio "componente"
            bom_qty[id_pack] = 1.0
        pack_bom.append((linea, bom_qty))
    # d_p sin escalar
    decrements: List[Tuple[int, int, float]] = []
    for linea, bom_qty in pack_bom:
        id_lista_linea = to_int_or_none(linea.get("id_lista_produccion"))
        id_art_pack = to_int_or_none(linea.get("id_articulo"))
        pendiente = float(linea.get("cantidad_pendiente_prod") or 0)
        if id_lista_linea is None or id_art_pack is None or pendiente <= 0:
            continue
        d_p_raw = float("inf")
        for id_comp, qty_bom in bom_qty.items():
            total = total_dispatch.get(id_comp) or 0
            if qty_bom <= 0:
                continue
            d_p_raw = min(d_p_raw, total / qty_bom)
        if d_p_raw == float("inf"):
            d_p_raw = 0
        d_p = min(pendiente, d_p_raw)
        decrements.append((id_lista_linea, id_art_pack, d_p))
    # Escalar si para algún comp: sum_p (d_p * bom_p(comp)) > total_dispatch[comp]
    usage: Dict[int, float] = {}
    for (_, bom_qty), (_, _, d_p) in zip(pack_bom, decrements):
        for id_comp, qty in bom_qty.items():
            usage[id_comp] = usage.get(id_comp, 0) + d_p * qty
    scale = 1.0
    for id_comp, total in total_dispatch.items():
        if total <= 0:
            continue
        u = usage.get(id_comp, 0)
        if u > total:
            scale = min(scale, total / u)
    if scale < 1.0:
        decrements = [(id_lista, id_art, d_p * scale) for id_lista, id_art, d_p in decrements]
    # Redondear a enteros (truncar para no superar lo distribuido)
    return [(id_lista, id_art, int(d_p)) for id_lista, id_art, d_p in decrements if int(d_p) > 0]


def ejecutar_opp_por_componentes(
    base_empresa: str,
    id_usuario: int,
    id_lista_produccion: int,
    deposito_origen: int,
    distribucion_por_deposito: Dict[int, List[Tuple[int, float]]],
) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    Registra OPP a partir de distribución por componente y depósito.
    distribucion_por_deposito: { cod_deposito_destino: [ (id_componente, qty_unidades), ... ] }.
    Valida stock en Producción, crea movimientos por depósito (Salida origen, Entrada destino),
    actualiza lista_produccion_agrupada con equivalentes pack (vía _calcular_decrementos_pack_desde_componentes).
    Devuelve (ok, codigo_movimiento_ultimo, nro_comprobante_ultimo, mensaje_error).
    """
    if not (base_empresa or "").strip():
        return False, None, None, "Base de datos no indicada."
    if not id_usuario:
        return False, None, None, "Usuario no indicado."
    deposito_origen = to_int_or_none(deposito_origen)
    if not deposito_origen:
        return False, None, None, "Depósito origen no indicado."
    # Filtrar depósitos con cantidades y agregar total_dispatch
    depositos_con_qty = [
        (cod_dep, [(id_c, float(q)) for id_c, q in lista if (to_int_or_none(id_c) is not None and float(q or 0) > 0)])
        for cod_dep, lista in (distribucion_por_deposito or {}).items()
        if lista
    ]
    depositos_con_qty = [(cod_dep, lista) for cod_dep, lista in depositos_con_qty if lista]
    if not depositos_con_qty:
        return False, None, None, "Indique al menos una cantidad mayor a 0 en algún depósito."
    total_dispatch: Dict[int, float] = {}
    for _cod_dep, lista in depositos_con_qty:
        for id_comp, qty in lista:
            id_c = to_int_or_none(id_comp)
            if id_c is not None:
                total_dispatch[id_c] = total_dispatch.get(id_c, 0) + qty
    lineas = get_opt_detalle(base_empresa, id_lista_produccion)
    if not lineas:
        return False, None, None, "No se encontraron líneas para esta OPT."
    en_proceso = (lineas[0].get("en_proceso_produccion") or "No").strip().lower() == "si"
    if not en_proceso:
        return False, None, None, "Debe liberar la OPT antes de registrar la parte de producción (OPP)."
    decrements = _calcular_decrementos_pack_desde_componentes(base_empresa, lineas, total_dispatch)
    codigo_mov_opt = get_codigo_movimiento_opt(base_empresa, id_lista_produccion)
    component_to_pack: Dict[int, int] = {}
    for linea in lineas:
        id_pack = to_int_or_none(linea.get("id_articulo"))
        if id_pack is None:
            continue
        comps = _explode_packs_to_components(base_empresa, [(linea, 1)])
        for c in comps:
            component_to_pack.setdefault(c, id_pack)
    id_ref_movstock = 1
    id_pv = 1
    fecha_mov = date.today().isoformat()
    hora_evento = datetime.now().strftime("%H:%M:%S")
    detalle_mov = f"OPT {id_lista_produccion} desde MPR"
    ultimo_codigo_mov = None
    ultimo_nro_comp = None
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
                tbl_articulo = _nombre_tabla(cursor, "articulo")
                tbl_historico = _nombre_tabla(cursor, "lista_produccion_historico")
                tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
                if not all([tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd]):
                    conn.rollback()
                    return False, None, None, "Faltan tablas necesarias para OPP."
                # Validar stock en origen por componente
                if tbl_sd and tbl_articulo:
                    for id_comp in total_dispatch:
                        qty_necesaria = total_dispatch[id_comp]
                        if qty_necesaria <= 0:
                            continue
                        cursor.execute(
                            f"SELECT saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s",
                            [id_comp, deposito_origen],
                        )
                        row_sd = cursor.fetchone()
                        saldo_orig = float(row_sd[0] or 0) if row_sd else 0
                        if saldo_orig < qty_necesaria:
                            codigo_comp = str(id_comp)
                            cursor.execute(
                                f"SELECT COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') FROM {tbl_articulo} WHERE IDArt = %s",
                                [id_comp],
                            )
                            rcod = cursor.fetchone()
                            if rcod:
                                codigo_comp = str_or_default(rcod[0], codigo_comp)
                            conn.rollback()
                            return False, None, None, (
                                f"Stock insuficiente del componente {codigo_comp} en Producción: tiene {int(saldo_orig)}, se necesitan {int(qty_necesaria)}."
                            )
                # Cargar codigo/descripcion de componentes
                articulo_info: Dict[int, Tuple[str, str]] = {}
                if tbl_articulo and total_dispatch:
                    ids_comp = list(total_dispatch.keys())
                    placeholders = ",".join(["%s"] * len(ids_comp))
                    cursor.execute(
                        f"SELECT IDArt, COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo, COALESCE(NombreArticulo, '') AS descripcion FROM {tbl_articulo} WHERE IDArt IN ({placeholders})",
                        ids_comp,
                    )
                    for r in cursor.fetchall() or []:
                        aid = to_int_or_none(r[0])
                        if aid is not None:
                            articulo_info[aid] = (str_or_default(r[1], "-"), str_or_default(r[2], "-"))
                for deposito_destino, lista_comp_qty in depositos_con_qty:
                    deposito_destino = to_int_or_none(deposito_destino)
                    if not deposito_destino or deposito_destino == deposito_origen:
                        continue
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
                        return False, None, None, "No existe talonario MSTOCK."
                    orden_talon, nro_actual = talon_row[0], int(talon_row[1] or 0)
                    nro_nuevo = nro_actual + 1
                    cursor.execute(f"UPDATE {tbl_talonarios} SET Nro = %s WHERE Orden = %s", [nro_nuevo, orden_talon])
                    nro_comprobante = _formato_nro_comprobante_mstock(id_pv, nro_actual)
                    nro_comprobante_busq = nro_actual
                    ultimo_codigo_mov = codigo_mov
                    ultimo_nro_comp = nro_comprobante
                    params_mov = [
                        codigo_mov, _formato_nro_comprobante_mstock(id_pv, nro_actual), MOTIVO_OPP_TEXTO, fecha_mov,
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
                            try:
                                cursor.execute(
                                    f"""
                                    INSERT INTO {tbl_mov}
                                    (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                                     detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                                    """,
                                    params_mov[:14],
                                )
                            except Exception:
                                conn.rollback()
                                raise MprSchemaError(formatear_error_esquema(ins_err, "movimiento_stock")) from ins_err
                        else:
                            conn.rollback()
                            raise
                    orden = 0
                    for id_art, qty in sorted(lista_comp_qty, key=lambda x: (x[0], x[1])):
                        if qty <= 0:
                            continue
                        id_art_pack_opp = component_to_pack.get(id_art)
                        id_en_abm_opp_comp = get_id_en_abm_por_articulo(base_empresa, id_art_pack_opp) if id_art_pack_opp is not None else None
                        codigo_art, descripcion_art = articulo_info.get(id_art, ("-", "-"))
                        salida = Decimal(str(qty))
                        cursor.execute(
                            f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                            [id_art, deposito_origen],
                        )
                        sd_orig = cursor.fetchone()
                        saldo_orig = Decimal(str(sd_orig[1] or 0)) if sd_orig else Decimal(0)
                        saldo_orig_despues = saldo_orig - salida
                        orden += 1
                        params_salida_comp = [codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov, salida, saldo_orig_despues, deposito_origen, id_ref_movstock, orden, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None]
                        params_salida_comp_opt_abm = params_salida_comp + [codigo_mov_opt, id_en_abm_opp_comp]
                        try:
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                                """,
                                params_salida_comp_opt_abm,
                            )
                        except Exception as stock_err:
                            if "1054" in str(stock_err):
                                cursor.execute(
                                    f"""
                                    INSERT INTO {tbl_stock}
                                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                    VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                    """,
                                    params_salida_comp,
                                )
                            else:
                                raise
                        if sd_orig:
                            cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_orig_despues, sd_orig[0]])
                        else:
                            cursor.execute(f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)", [id_art, deposito_origen, saldo_orig_despues])
                        cursor.execute(
                            f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                            [id_art, deposito_destino],
                        )
                        sd_dest = cursor.fetchone()
                        saldo_dest = Decimal(str(sd_dest[1] or 0)) if sd_dest else Decimal(0)
                        saldo_dest_despues = saldo_dest + salida
                        orden += 1
                        params_entrada_comp = [codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov, salida, saldo_dest_despues, deposito_destino, id_ref_movstock, orden, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None]
                        params_entrada_comp_opt_abm = params_entrada_comp + [codigo_mov_opt, id_en_abm_opp_comp]
                        try:
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                                VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                                """,
                                params_entrada_comp_opt_abm,
                            )
                        except Exception as stock_err:
                            if "1054" in str(stock_err):
                                cursor.execute(
                                    f"""
                                    INSERT INTO {tbl_stock}
                                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                    VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                    """,
                                    params_entrada_comp,
                                )
                            else:
                                raise
                        if sd_dest:
                            cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_dest_despues, sd_dest[0]])
                        else:
                            cursor.execute(f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)", [id_art, deposito_destino, saldo_dest_despues])
                        if tbl_historico:
                            id_art_pack_opp = component_to_pack.get(id_art)
                            try:
                                cursor.execute(
                                    f"""
                                    INSERT INTO {tbl_historico}
                                    (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                     id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                     nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento)
                                    VALUES ('OPP', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    [id_art_pack_opp, id_art, qty, deposito_destino, deposito_origen, deposito_destino, codigo_mov, codigo_mov_opt, nro_comprobante, id_usuario, id_lista_produccion, fecha_mov, hora_evento, fecha_mov, hora_evento],
                                )
                            except Exception as hist_err:
                                logger.warning(
                                    "No se pudo insertar lista_produccion_historico (OPP por componentes): %s",
                                    hist_err,
                                    exc_info=True,
                                )
                # Decrementar pendiente por pack en lista_produccion_agrupada
                if tbl_agrupada and decrements:
                    for id_lista_linea, id_art_pack, d_p in decrements:
                        if d_p <= 0:
                            continue
                        try:
                            cursor.execute(
                                f"UPDATE {tbl_agrupada} SET cantidad_pendiente_prod = GREATEST(0, COALESCE(cantidad_pendiente_prod, 0) - %s) WHERE id_lista_produccion = %s AND id_articulo = %s",
                                [d_p, id_lista_linea, id_art_pack],
                            )
                        except Exception as agg_err:
                            logger.warning("No se pudo actualizar lista_produccion_agrupada en OPP por componentes: %s", agg_err)
                # Decrementar cantidad_pendiente_prod en lista_produccion_detalle (mismo equivalente pack que en agrupada)
                if tbl_detalle and decrements:
                    for id_lista_linea, id_art_pack, d_p in decrements:
                        if d_p <= 0:
                            continue
                        try:
                            cursor.execute(
                                f"SELECT COALESCE(SUM(cantidad_pendiente_prod), 0) FROM {tbl_detalle} WHERE id_lista_produccion = %s AND id_articulo = %s",
                                [id_lista_linea, id_art_pack],
                            )
                            row_sum = cursor.fetchone()
                            total_det = float(row_sum[0] or 0) if row_sum else 0
                            if total_det <= 0:
                                continue
                            factor = max(0.0, (total_det - d_p) / total_det)
                            cursor.execute(
                                f"UPDATE {tbl_detalle} SET cantidad_pendiente_prod = cantidad_pendiente_prod * %s WHERE id_lista_produccion = %s AND id_articulo = %s",
                                [factor, id_lista_linea, id_art_pack],
                            )
                        except Exception as det_err:
                            if "1054" not in str(det_err) and "unknown column" not in str(det_err).lower():
                                logger.warning("No se pudo actualizar lista_produccion_detalle en OPP por componentes: %s", det_err)
                conn.commit()
                return True, ultimo_codigo_mov, ultimo_nro_comp, None
            except MprSchemaError:
                conn.rollback()
                raise
            except Exception as e:
                conn.rollback()
                logger.exception("Error en ejecutar_opp_por_componentes: %s", e)
                return False, None, None, str(e)
    except MprSchemaError:
        raise
    except Exception as e:
        logger.exception("Error de conexión en ejecutar_opp_por_componentes: %s", e)
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
                    faltan = [n for n, t in [
                        ("articulo", tbl_articulo), ("codmov", tbl_codmov), ("talonarios", tbl_talonarios),
                        ("movimiento_stock", tbl_mov), ("stock", tbl_stock), ("stock_deposito", tbl_sd),
                    ] if not t]
                    raise MprSchemaError(
                        f"Faltan tablas en la base de datos: {', '.join(faltan)}. Cree las tablas o verifique el esquema para usar MPR."
                    )
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
                        try:
                            cursor.execute(
                                f"""
                                INSERT INTO {tbl_mov}
                                (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                                 detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                                """,
                                params_mov[:15],
                            )
                        except Exception as ins_err2:
                            raise MprSchemaError(formatear_error_esquema(ins_err2, "movimiento_stock")) from ins_err2
                    else:
                        raise MprSchemaError(formatear_error_esquema(ins_err, "movimiento_stock")) from ins_err
                saldo_orig_despues = saldo_orig - salida
                params_stock_rec_salida = [
                    codigo_mov, id_articulo, codigo_art, descripcion_art, fecha_mov,
                    salida, saldo_orig_despues, deposito_origen, id_ref_movstock,
                    id_usuario, MOTIVO_RECLASIFICACION_TEXTO, nro_comprobante, None,
                ]
                params_stock_rec_salida_opt_abm = params_stock_rec_salida + [None, None]
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_stock}
                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                        VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, 1, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                        """,
                        params_stock_rec_salida_opt_abm,
                    )
                except Exception as stock_err:
                    if "1054" in str(stock_err):
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, 1, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                            """,
                            params_stock_rec_salida,
                        )
                    else:
                        raise
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
                params_stock_rec_entrada = [
                    codigo_mov, id_articulo, codigo_art, descripcion_art, fecha_mov,
                    salida, saldo_dest_despues, deposito_destino, id_ref_movstock,
                    id_usuario, MOTIVO_RECLASIFICACION_TEXTO, nro_comprobante, None,
                ]
                params_stock_rec_entrada_opt_abm = params_stock_rec_entrada + [None, None]
                try:
                    cursor.execute(
                        f"""
                        INSERT INTO {tbl_stock}
                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                        VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, 2, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                        """,
                        params_stock_rec_entrada_opt_abm,
                    )
                except Exception as stock_err:
                    if "1054" in str(stock_err):
                        cursor.execute(
                            f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, 2, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                            """,
                            params_stock_rec_entrada,
                        )
                    else:
                        raise
                if sd_dest:
                    cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_dest_despues, sd_dest[0]])
                else:
                    cursor.execute(
                        f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                        [id_articulo, deposito_destino, saldo_dest_despues],
                    )
                conn.commit()
                return True, codigo_mov, nro_comprobante, None
            except MprSchemaError:
                conn.rollback()
                raise
            except Exception as e:
                conn.rollback()
                if "1054" in str(e) or "Unknown column" in str(e).lower():
                    raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
                logger.warning("Error en ejecutar_reclasificacion: %s", e, exc_info=True)
                return False, None, None, str(e)
    except MprSchemaError:
        raise
    except Exception as e:
        if "1054" in str(e) or "Unknown column" in str(e).lower():
            raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
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
