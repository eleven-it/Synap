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
from typing import Any, Dict, List, Optional, Set, Tuple

from core.mysql_pool import get_connection, mysql_cursor
from core.services.administranet_stock import get_depositos as _get_depositos_core
from core.services.legacy_mysql_schema.helpers import (
    columna_existe,
    columna_primary_key,
    es_nombre_logico_id_lista_detalle,
    nombre_columna_ci,
)
from core.utils.administranet_types import to_int_or_none, str_or_default, str_codigo_manual_articulo, to_date_or_none, to_decimal_or_none, to_decimal_or_none

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

# lista_produccion_detalle: codigo_movimiento_pedido = 0 indica demanda sintética por reserva (no existe fila en comp_ped).
COD_MOV_PEDIDO_DEMANDA_RESERVA = 0
ORIGEN_DEMANDA_RESERVA = "RESERVA"

# movimiento_stock.tipo_mov: OPT = liberación OPT, OPP = registrar OPP, OPA = armado. tipo_comprobante es el tipo de talonario (MSTOCK).
TIPO_MOV_OPT = "OPT"
TIPO_MOV_OPP = "OPP"
TIPO_MOV_OPA = "OPA"


def _mpr_codigo_opt_placeholder_desde_principal(id_lista_principal: Optional[int]) -> Optional[int]:
    """
    Antes de liberar la OPT, se guarda en lista_produccion_agrupada.codigo_movimiento_opt un valor
    negativo (-id_lista_principal) en todas las líneas del lote para agruparlas sin usar id_opt.
    Al liberar, se reemplaza por el CodigoMovimiento real del MSTOCK (> 0).
    """
    p = to_int_or_none(id_lista_principal)
    if p is None or p <= 0:
        return None
    return -abs(int(p))


def _mpr_es_codigo_movimiento_opt_mstock(cod: Optional[int]) -> bool:
    """True si codigo_movimiento_opt es el código real de movimiento_stock (liberación OPT)."""
    return cod is not None and cod > 0


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


def _row_dict_lower_keys(row: Any) -> Dict[str, Any]:
    """Claves en minúsculas para lectura estable con DictCursor MySQL (alias/columnas mixtos)."""
    if not isinstance(row, dict):
        return {}
    return {str(k).lower(): v for k, v in row.items()}


def docenas_desde_unidades_opt(unidades: Any, cantidad_promedio_bulto: Any) -> float:
    """
    Equivalente «docenas» / bulto para OPT y ventana pack: unidades / articulo.cantidad_promedio_bulto.
    Si el bulto no está definido o es <= 0, se usa 12 (mismo criterio que el cálculo previo por docena fija).
    """
    try:
        u = float(unidades or 0)
    except (TypeError, ValueError):
        u = 0.0
    try:
        b = float(cantidad_promedio_bulto) if cantidad_promedio_bulto is not None else 0.0
    except (TypeError, ValueError):
        b = 0.0
    divisor = b if b > 0 else 12.0
    try:
        return round(u / divisor, 2)
    except ZeroDivisionError:
        return 0.0


def divisor_docena_pack(cantidad_promedio_bulto: Any) -> int:
    """Unidades por docena en pantallas pack/OPT: ``cantidad_promedio_bulto`` o 12 si no aplica."""
    try:
        b = float(cantidad_promedio_bulto) if cantidad_promedio_bulto is not None else 0.0
    except (TypeError, ValueError):
        b = 0.0
    return int(b) if b > 0 else 12


def descomponer_docenas_unidades(
    cantidad: Any,
    cantidad_promedio_bulto: Any = None,
    *,
    unidades_por_docena_fijo: Optional[int] = None,
) -> Dict[str, int]:
    """
    Descompone una cantidad entera en docenas completas y unidades sueltas.

    Pack/OPT: divisor = ``divisor_docena_pack(cantidad_promedio_bulto)``.
    Componentes OPP (BOM): ``unidades_por_docena_fijo=12``.
    """
    try:
        total = int(float(cantidad or 0))
    except (TypeError, ValueError):
        total = 0
    total = max(0, total)
    if unidades_por_docena_fijo is not None:
        divisor = int(unidades_por_docena_fijo) if int(unidades_por_docena_fijo) > 0 else 12
    else:
        divisor = divisor_docena_pack(cantidad_promedio_bulto)
    docenas, unidades = divmod(total, divisor)
    return {"docenas": docenas, "unidades": unidades, "divisor": divisor, "total": total}


def texto_docenas_unidades(
    cantidad: Any,
    cantidad_promedio_bulto: Any = None,
    *,
    unidades_por_docena_fijo: Optional[int] = None,
) -> str:
    """Texto UI: «N docenas · M unidades»."""
    partes = descomponer_docenas_unidades(
        cantidad,
        cantidad_promedio_bulto,
        unidades_por_docena_fijo=unidades_por_docena_fijo,
    )
    return f"{partes['docenas']} docenas · {partes['unidades']} unidades"


def docenas_enteras_desde_packs(cantidad_packs: Any, cantidad_promedio_bulto: Any) -> int:
    """
    Docenas completas equivalentes a una cantidad en packs (división entera por bulto).
    Usado en armado: solo packs enteros; no se muestran unidades sueltas del resto.
    """
    try:
        packs = max(0, int(float(cantidad_packs or 0)))
    except (TypeError, ValueError):
        packs = 0
    divisor = divisor_docena_pack(cantidad_promedio_bulto)
    return packs // divisor


def bulk_cantidad_promedio_bulto(
    base_empresa: str,
    id_articulos: List[int],
) -> Dict[int, float]:
    """Devuelve {id_articulo: cantidad_promedio_bulto} (0 si falta columna o valor)."""
    if not (base_empresa or "").strip() or not id_articulos:
        return {}
    ids = [int(i) for i in id_articulos if i is not None]
    if not ids:
        return {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "articulo")
            if not tbl:
                return {i: 0.0 for i in ids}
            bulto_sql = _fragmento_sql_cantidad_promedio_bulto(cursor, tbl)
            ph = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"SELECT IDArt{bulto_sql} FROM {tbl} WHERE IDArt IN ({ph})",
                ids,
            )
            out: Dict[int, float] = {i: 0.0 for i in ids}
            for r in cursor.fetchall() or []:
                aid = to_int_or_none(r.get("IDArt") or r.get("idart"))
                if aid is None:
                    continue
                try:
                    out[aid] = float(r.get("cantidad_promedio_bulto") or 0)
                except (TypeError, ValueError):
                    out[aid] = 0.0
            return out
    except Exception as e:
        logger.warning("bulk_cantidad_promedio_bulto error: %s", e)
        return {i: 0.0 for i in ids}


def _etiqueta_linea_opt(linea: Dict[str, Any]) -> str:
    cod = (linea.get("codigo_manual") or linea.get("codigo_articulo") or "").strip()
    desc = (linea.get("descripcion_articulo") or "").strip()
    if cod and desc:
        return f"{cod} {desc}"[:80]
    return cod or desc or str(linea.get("id_articulo") or "-")


def build_resumen_metrica_opt(
    total_packs: int,
    lineas_detalle: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Presentación C4 para totales del encabezado OPT.

    Si hay una sola línea o todas comparten el mismo divisor de docena, el total se muestra
    como docenas · unidades. Si hay varios artículos con distinto bulto, total en packs
    más desglose por línea.
    """
    try:
        total = max(0, int(total_packs or 0))
    except (TypeError, ValueError):
        total = 0
    filas: List[Dict[str, Any]] = []
    divisores: set = set()
    for item in lineas_detalle or []:
        try:
            packs = max(0, int(item.get("packs") or 0))
        except (TypeError, ValueError):
            packs = 0
        bulto = item.get("bulto", 0)
        partes = descomponer_docenas_unidades(packs, bulto)
        divisores.add(partes["divisor"])
        filas.append({
            "etiqueta": str(item.get("etiqueta") or "-"),
            "packs": packs,
            "bulto": bulto,
            "docenas": partes["docenas"],
            "unidades": partes["unidades"],
            "texto_docenas_unidades": texto_docenas_unidades(packs, bulto),
        })
    unico_divisor = len(divisores) == 1
    una_linea = len(filas) <= 1
    puede_total_docenas = una_linea or unico_divisor
    divisor_total = next(iter(divisores)) if unico_divisor and divisores else (
        divisor_docena_pack(filas[0]["bulto"]) if filas else 12
    )
    if puede_total_docenas:
        if unico_divisor:
            kw_fijo = {"unidades_por_docena_fijo": divisor_total}
            total_partes = descomponer_docenas_unidades(total, **kw_fijo)
            texto_total = texto_docenas_unidades(total, **kw_fijo)
        elif filas:
            total_partes = descomponer_docenas_unidades(total, filas[0]["bulto"])
            texto_total = texto_docenas_unidades(total, filas[0]["bulto"])
        else:
            total_partes = descomponer_docenas_unidades(total, 0)
            texto_total = texto_docenas_unidades(total, 0)
        return {
            "packs": total,
            "mostrar_desglose": False,
            "texto_principal": texto_total,
            "docenas": total_partes["docenas"],
            "unidades": total_partes["unidades"],
            "lineas": filas,
        }
    return {
        "packs": total,
        "mostrar_desglose": True,
        "texto_principal": f"{total} packs",
        "docenas": None,
        "unidades": None,
        "lineas": filas,
    }


def enriquecer_lineas_opt_presentacion_pack(
    lineas: List[Dict[str, Any]],
    bulto_por_articulo: Dict[int, float],
) -> None:
    """Añade en cada línea campos ``*_du`` y textos para plantillas OPT (pack + bulto por artículo)."""
    campos = (
        "cantidad_pedida",
        "cantidad_pendiente_prod",
        "cantidad_en_esta_opt",
        "cantidad_ya_armada",
        "cantidad_restante_armar",
        "cantidad_a_otros_depositos",
    )
    for linea in lineas or []:
        id_art = to_int_or_none(linea.get("id_articulo"))
        bulto = float(bulto_por_articulo.get(id_art, 0) if id_art is not None else 0)
        linea["cantidad_promedio_bulto"] = bulto
        for campo in campos:
            val = linea.get(campo)
            if val is None:
                continue
            try:
                if int(val) < 0:
                    continue
            except (TypeError, ValueError):
                continue
            partes = descomponer_docenas_unidades(val, bulto)
            linea[f"{campo}_du"] = partes
            linea[f"{campo}_texto_du"] = texto_docenas_unidades(val, bulto)


def enriquecer_componentes_opp_presentacion(componentes: List[Dict[str, Any]]) -> None:
    """Pendiente distribuible en docenas · unidades (divisor fijo 12)."""
    for comp in componentes or []:
        max_u = comp.get("max_distribuible_unidades")
        if max_u is None:
            max_u = comp.get("disponible_unidades", 0)
        partes = descomponer_docenas_unidades(max_u, unidades_por_docena_fijo=12)
        comp["pendiente_du"] = partes
        comp["pendiente_texto_du"] = texto_docenas_unidades(max_u, unidades_por_docena_fijo=12)


def cantidad_opp_presentacion_du(cantidad: Any) -> Dict[str, int]:
    """Desglose docenas + unidades sueltas para UI OPP (1 docena = 12 unidades)."""
    return descomponer_docenas_unidades(cantidad, unidades_por_docena_fijo=12)


def enriquecer_movimientos_opp_presentacion_du(movimientos: List[Dict[str, Any]]) -> None:
    """Añade ``cantidad_du`` a filas OPP listadas (cantidad_total en unidades)."""
    for mov in movimientos or []:
        if mov.get("cantidad_total") is None:
            continue
        mov["cantidad_du"] = cantidad_opp_presentacion_du(mov.get("cantidad_total"))


def lineas_texto_cantidad_opp(unidades: Any) -> List[str]:
    """Líneas UI/PDF OPP: docenas y unidades sueltas (divisor 12)."""
    du = cantidad_opp_presentacion_du(unidades)
    return [f"{du['docenas']} docenas", f"{du['unidades']} unidades"]


def lineas_texto_cantidad_pack(packs: Any, cantidad_promedio_bulto: Any) -> List[str]:
    """Líneas UI/PDF pack: packs, docenas y unidades sueltas."""
    try:
        total_packs = max(0, int(float(packs or 0)))
    except (TypeError, ValueError):
        total_packs = 0
    partes = descomponer_docenas_unidades(total_packs, cantidad_promedio_bulto)
    return [
        f"{total_packs} packs",
        f"{partes['docenas']} docenas",
        f"{partes['unidades']} unidades",
    ]


def _clave_grupo_articulo_movimiento(fila: Dict[str, Any]) -> str:
    id_art = to_int_or_none(fila.get("id_articulo"))
    if id_art is not None:
        return f"id:{id_art}"
    cod = str_or_default(fila.get("codigo_articulo"), "")
    desc = str_or_default(fila.get("descripcion"), "")
    return f"cod:{cod}|{desc}"


def fila_movimiento_desde_renglon_stock(
    r: Dict[str, Any],
    *,
    presentacion_opp_du: bool = False,
) -> Dict[str, Any]:
    """Normaliza un renglón de ``stock`` para modal/PDF de comprobante."""
    entrada = r.get("Entrada")
    salida = r.get("Salida")
    saldo = r.get("saldo")
    row: Dict[str, Any] = {
        "id_articulo": to_int_or_none(r.get("IDArt")),
        "codigo_articulo": str_or_default(r.get("CodigoArticulo"), "—"),
        "descripcion": str_or_default(r.get("Descripcion"), "—"),
        "nombre_deposito": str_or_default(r.get("nombre_deposito"), "—"),
        "cod_deposito": to_int_or_none(r.get("CodDeposito")),
        "entrada": float(to_decimal_or_none(entrada) or 0),
        "salida": float(to_decimal_or_none(salida) or 0),
        "saldo": float(to_decimal_or_none(saldo) if saldo is not None else 0),
    }
    if presentacion_opp_du:
        row["entrada_du"] = cantidad_opp_presentacion_du(row["entrada"])
        row["salida_du"] = cantidad_opp_presentacion_du(row["salida"])
        row["saldo_du"] = cantidad_opp_presentacion_du(row["saldo"])
    return row


def agrupar_filas_movimiento_por_articulo(filas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrupa filas de un mismo movimiento por artículo (celda consolidada tipo Excel).
    Conserva el orden de aparición.
    """
    grupos: List[Dict[str, Any]] = []
    indice: Dict[str, int] = {}
    for fila in filas or []:
        clave = _clave_grupo_articulo_movimiento(fila)
        if clave not in indice:
            indice[clave] = len(grupos)
            grupos.append({
                "id_articulo": fila.get("id_articulo"),
                "codigo_articulo": fila.get("codigo_articulo"),
                "descripcion": fila.get("descripcion"),
                "filas": [],
            })
        grupos[indice[clave]]["filas"].append(fila)
    return grupos


def build_grupos_articulo_renglones_movimiento(
    renglones: List[Dict[str, Any]],
    *,
    presentacion_opp_du: bool = False,
) -> List[Dict[str, Any]]:
    """Renglones MySQL ``stock`` → grupos por artículo para comprobante."""
    filas = [
        fila_movimiento_desde_renglon_stock(r, presentacion_opp_du=presentacion_opp_du)
        for r in (renglones or [])
    ]
    return agrupar_filas_movimiento_por_articulo(filas)


def _fragmento_sql_cantidad_promedio_bulto(cursor, tbl_art: str) -> str:
    """
    Fragmento SQL para SELECT desde ``articulo``: lee la columna de bulto real
    (nombre case-insensitive) o constante 0 si no existe.
    """
    col = nombre_columna_ci(cursor, tbl_art, "cantidad_promedio_bulto")
    if not col:
        return ", 0 AS cantidad_promedio_bulto"
    c = col.replace("`", "``")
    return f", COALESCE(`{c}`, 0) AS cantidad_promedio_bulto"


def _explosion_demanda_componentes_pedido_reserva_pack(
    filas_pack: List[Dict[str, Any]],
    abm_map: Dict[int, int],
    bom_map: Dict[int, Any],
) -> Tuple[Dict[int, float], Dict[int, float]]:
    """
    Por cada pack con cantidad a fabricar CF, parte atribuible a pedido vs stock del pack
    ``n_base_ped = max(0, P_ped - S_pack)`` y parte a colchón del terminado
    ``n_res_tail = max(0, CF - n_base_ped)``; explota BOM y acumula por id componente.
    """
    dem_ped: Dict[int, float] = {}
    dem_res: Dict[int, float] = {}
    for r in filas_pack or []:
        try:
            cf = float(r.get("cantidad_a_fabricar") or 0)
        except (TypeError, ValueError):
            cf = 0.0
        if cf <= 0:
            continue
        id_pack = to_int_or_none(r.get("id_articulo"))
        if id_pack is None:
            continue
        try:
            p_ped = float(r.get("cantidad_pedida_pedido") or 0)
        except (TypeError, ValueError):
            p_ped = 0.0
        try:
            st_pack = float(r.get("stock_terminado") or 0)
        except (TypeError, ValueError):
            st_pack = 0.0
        n_base_ped = max(0.0, p_ped - st_pack)
        n_res_tail = max(0.0, cf - n_base_ped)
        id_en_abm = abm_map.get(id_pack)
        if id_en_abm is None:
            continue
        bom = bom_map.get(id_en_abm)
        if not bom or not bom.get("componentes"):
            continue
        for comp in bom["componentes"]:
            id_comp = to_int_or_none(comp.get("id_articulo"))
            if id_comp is None:
                continue
            try:
                coef = float(comp.get("cantidad_articulo") or 0)
            except (TypeError, ValueError):
                coef = 0.0
            if coef <= 0:
                continue
            dem_ped[id_comp] = dem_ped.get(id_comp, 0.0) + coef * n_base_ped
            dem_res[id_comp] = dem_res.get(id_comp, 0.0) + coef * n_res_tail
    return dem_ped, dem_res


def obtener_pp_ped_y_stock_pack_por_articulos(
    base_empresa: str,
    id_articulos: List[int],
) -> Dict[int, Dict[str, float]]:
    """
    P_ped y stock terminado (depósitos suma_stock='Si') para artículos pack concretos.

    Consulta acotada para el wizard «agrupar»: datos en vivo sin recalcular listar_ventana_pack.
    """
    ids = sorted({x for x in (to_int_or_none(i) for i in (id_articulos or [])) if x is not None})
    if not (base_empresa or "").strip() or not ids:
        return {}
    out: Dict[int, Dict[str, float]] = {
        aid: {"cantidad_pedida_pedido": 0.0, "stock_terminado": 0.0} for aid in ids
    }
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            if tbl_detalle:
                ph = ",".join(["%s"] * len(ids))
                try:
                    cursor.execute(
                        f"""
                        SELECT d.id_articulo,
                               COALESCE(SUM(CASE WHEN COALESCE(d.codigo_movimiento_pedido, 0) <> 0
                                    THEN COALESCE(d.cantidad_pedida, 0) ELSE 0 END), 0) AS p_ped
                        FROM {tbl_detalle} d
                        WHERE d.id_articulo IN ({ph})
                          AND COALESCE(TRIM(d.en_proceso_produccion), 'No') = 'No'
                        GROUP BY d.id_articulo
                        """,
                        ids,
                    )
                    for r in cursor.fetchall() or []:
                        aid = to_int_or_none(r.get("id_articulo"))
                        if aid is None or aid not in out:
                            continue
                        try:
                            out[aid]["cantidad_pedida_pedido"] = float(r.get("p_ped") or 0)
                        except (TypeError, ValueError):
                            out[aid]["cantidad_pedida_pedido"] = 0.0
                except Exception as e_split:
                    logger.debug(
                        "No se pudo cargar P_ped para selección ventana-pack: %s", e_split
                    )
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            if tbl_sd and tbl_dep:
                ph = ",".join(["%s"] * len(ids))
                try:
                    cursor.execute(
                        f"""
                        SELECT sd.id_articulo, COALESCE(SUM(sd.saldo), 0) AS stock_terminado
                        FROM {tbl_sd} sd
                        INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
                          AND COALESCE(d.anulado, 'No') = 'No'
                          AND COALESCE(d.suma_stock, 'Si') = 'Si'
                        WHERE sd.id_articulo IN ({ph})
                        GROUP BY sd.id_articulo
                        """,
                        ids,
                    )
                    for r in cursor.fetchall() or []:
                        aid = to_int_or_none(r.get("id_articulo"))
                        if aid is None or aid not in out:
                            continue
                        try:
                            out[aid]["stock_terminado"] = float(r.get("stock_terminado") or 0)
                        except (TypeError, ValueError):
                            out[aid]["stock_terminado"] = 0.0
                except Exception as e_st:
                    logger.debug(
                        "No se pudo cargar stock terminado para selección ventana-pack: %s", e_st
                    )
    except Exception as e:
        logger.warning(
            "Error en obtener_pp_ped_y_stock_pack_por_articulos en %s: %s",
            base_empresa,
            e,
            exc_info=True,
        )
    return out


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


def _mpr_ejecutar_insert_intentos(
    cursor,
    intentos: List[Tuple[str, List[Any]]],
) -> None:
    """
    Ejecuta el primer INSERT SQL que no falle por columna inexistente (1054).
    Pasar intentos ordenados del esquema más completo al más reducido (p. ej. stock, historico).
    """
    ultimo: Optional[Exception] = None
    for sql, params in intentos:
        try:
            cursor.execute(sql, params)
            return
        except Exception as e:
            err = str(e).lower()
            if "1054" not in str(e) and "unknown column" not in err:
                raise
            ultimo = e
    if ultimo:
        raise ultimo


def _update_detalle_id_operario_opt(
    cursor,
    tbl_detalle: str,
    id_operario_opt: Optional[int],
    id_lista_produccion: int,
    id_articulo: int,
) -> None:
    """Actualiza lista_produccion_detalle.id_operario_opt si la columna existe."""
    oid = to_int_or_none(id_operario_opt)
    if oid is None or not tbl_detalle:
        return
    try:
        cursor.execute(
            f"UPDATE {tbl_detalle} SET id_operario_opt = %s "
            f"WHERE id_lista_produccion = %s AND id_articulo = %s",
            [oid, id_lista_produccion, id_articulo],
        )
    except Exception as e:
        if "1054" not in str(e) and "unknown column" not in str(e).lower():
            raise
        logger.debug("lista_produccion_detalle.id_operario_opt no actualizado (columna ausente): %s", e)


def _incrementar_cantidad_fabricada_acumulada_agrupada(
    cursor,
    tbl_agrupada: str,
    id_lista_produccion: int,
    id_articulo: int,
    cantidad: int,
) -> None:
    """
    Suma cantidad a lista_produccion_agrupada.cantidad_fabricada_acumulada para la línea indicada.
    Si la columna no existe (error 1054), se ignora sin fallar el armado.
    """
    qty = to_int_or_none(cantidad) or 0
    if qty <= 0 or not tbl_agrupada:
        return
    id_l = to_int_or_none(id_lista_produccion)
    id_a = to_int_or_none(id_articulo)
    if not id_l or not id_a:
        return
    try:
        cursor.execute(
            f"UPDATE {tbl_agrupada} SET cantidad_fabricada_acumulada = "
            f"COALESCE(cantidad_fabricada_acumulada, 0) + %s "
            f"WHERE id_lista_produccion = %s AND id_articulo = %s",
            [qty, id_l, id_a],
        )
    except Exception as e:
        err = str(e).lower()
        if "1054" in str(e) or "unknown column" in err:
            logger.debug(
                "cantidad_fabricada_acumulada no actualizada (columna ausente o esquema): %s", e
            )
            return
        raise


# ---------------------------------------------------------------------------
# Helpers bulk: evitar N+1 al consultar BOM, artículos armados, id_en_abm
# ---------------------------------------------------------------------------

def bulk_id_en_abm(
    base_empresa: str,
    id_articulos: List[int],
    *,
    requiere_ensamblado_si: bool = True,
) -> Dict[int, int]:
    """
    Dado un lote de IDArt, devuelve {id_articulo: id_en_abm}.

    Con ``requiere_ensamblado_si=True`` (por defecto) solo incluye artículos con
    ``ensamblado = 'Si'`` (criterio de armado OPT / liberación).

    Con ``requiere_ensamblado_si=False`` incluye cualquier artículo con ``id_en_abm``
    no nulo, alineado con el tooltip de receta en ventana-pack y con la explosión BOM
    de la pestaña Unidades (demanda MPR): en AdministraNET un terminado puede tener
    receta configurada sin marcar ensamblado.
    """
    if not id_articulos:
        return {}
    filtro_ens = (
        " AND COALESCE(ensamblado, 'No') = 'Si'"
        if requiere_ensamblado_si
        else ""
    )
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "articulo")
            if not tbl:
                return {}
            ph = ",".join(["%s"] * len(id_articulos))
            cursor.execute(
                f"SELECT IDArt, id_en_abm FROM {tbl} WHERE IDArt IN ({ph}) "
                f"AND id_en_abm IS NOT NULL{filtro_ens}",
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


def _bulk_bom_detalle_con_cursor(
    cursor,
    id_en_abms: List[int],
) -> Dict[int, Dict[str, Any]]:
    """Misma lógica que bulk_bom_detalle reutilizando el cursor abierto."""
    ids = [to_int_or_none(x) for x in (id_en_abms or [])]
    ids = [x for x in ids if x is not None]
    if not ids:
        return {}
    tbl_abm = _nombre_tabla(cursor, "en_abm")
    tbl_formula = _nombre_tabla(cursor, "en_abm_formula")
    tbl_articulo = _nombre_tabla(cursor, "articulo")
    if not tbl_abm:
        return {}
    ph = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"SELECT id_en_abm, COALESCE(nombre_en_abm, '') AS nombre_en_abm, "
        f"COALESCE(anulado, 'No') AS anulado, COALESCE(detalle, '') AS detalle, "
        f"COALESCE(descuenta_en, '') AS descuenta_en "
        f"FROM {tbl_abm} WHERE id_en_abm IN ({ph})",
        ids,
    )
    cabeceras: Dict[int, Dict[str, Any]] = {}
    for r in cursor.fetchall() or []:
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
            ids,
        )
        for r in cursor.fetchall() or []:
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


def bulk_bom_detalle(base_empresa: str, id_en_abms: List[int]) -> Dict[int, Dict[str, Any]]:
    """Dado un lote de id_en_abm, devuelve {id_en_abm: {cabecera, componentes}} en 2 queries."""
    if not id_en_abms:
        return {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            return _bulk_bom_detalle_con_cursor(cursor, id_en_abms)
    except Exception as e:
        logger.warning("bulk_bom_detalle error: %s", e)
        return {}


def _ventana_pack_by_art_desde_agrupada(
    cursor,
    tbl_agrupada: str,
    tbl_articulo: str,
    opts: Dict[str, str],
    limit: int,
    fecha_desde: Optional[date],
    fecha_hasta: Optional[date],
) -> Dict[int, Dict[str, Any]]:
    """Demanda agrupada por id_articulo (una fila por pack) para ventana-pack."""
    col_fab = opts.get("cantidad_fabricada_acumulada")
    fab_agg = (
        f"SUM(COALESCE(l.{col_fab}, 0)) AS cantidad_fabricada_acumulada"
        if col_fab
        else "0 AS cantidad_fabricada_acumulada"
    )
    col_cod_mov_opt = opts.get("codigo_movimiento_opt")
    sql_excl_opt_lib = ""
    if col_cod_mov_opt:
        sql_excl_opt_lib = f" AND NOT (COALESCE(l.{col_cod_mov_opt}, 0) > 0)"
    sql = f"""
        SELECT
            l.id_articulo,
            MAX(COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '')) AS codigo_articulo,
            MAX(COALESCE(a.NombreArticulo, '')) AS descripcion_articulo,
            MAX(COALESCE(a.id_manual, '')) AS codigo_manual,
            SUM(COALESCE(l.cantidad_pedida, 0)) AS cantidad_pedida,
            SUM(COALESCE(l.cantidad_pendiente_prod, 0)) AS cantidad_pendiente_prod,
            {fab_agg}
        FROM {tbl_agrupada} l
        INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
        WHERE COALESCE(l.cantidad_pendiente_prod, 0) > 0
          AND COALESCE(NULLIF(TRIM(l.en_proceso_produccion), ''), 'No') = 'No'
          {sql_excl_opt_lib}
        GROUP BY l.id_articulo
    """
    params: List[Any] = []
    sql, params = _append_filtro_periodo_agrupada(
        cursor,
        sql,
        params,
        tbl_agrupada=tbl_agrupada,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        col_fecha=opts.get("fecha_objetivo"),
    )
    sql += " ORDER BY SUM(COALESCE(l.cantidad_pendiente_prod, 0)) DESC LIMIT %s"
    params.append(limit)
    try:
        cursor.execute(sql, params)
        rows = cursor.fetchall() or []
    except Exception as col_err:
        if "id_manual" in str(col_err) or "unknown column" in str(col_err).lower():
            sql = f"""
                SELECT
                    l.id_articulo,
                    MAX(COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '')) AS codigo_articulo,
                    MAX(COALESCE(a.NombreArticulo, '')) AS descripcion_articulo,
                    '' AS codigo_manual,
                    SUM(COALESCE(l.cantidad_pedida, 0)) AS cantidad_pedida,
                    SUM(COALESCE(l.cantidad_pendiente_prod, 0)) AS cantidad_pendiente_prod,
                    {fab_agg}
                FROM {tbl_agrupada} l
                INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                WHERE COALESCE(l.cantidad_pendiente_prod, 0) > 0
                  AND COALESCE(NULLIF(TRIM(l.en_proceso_produccion), ''), 'No') = 'No'
                  {sql_excl_opt_lib}
                GROUP BY l.id_articulo
            """
            params_fb: List[Any] = []
            sql, params_fb = _append_filtro_periodo_agrupada(
                cursor,
                sql,
                params_fb,
                tbl_agrupada=tbl_agrupada,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                col_fecha=opts.get("fecha_objetivo"),
            )
            sql += " ORDER BY SUM(COALESCE(l.cantidad_pendiente_prod, 0)) DESC LIMIT %s"
            params_fb.append(limit)
            cursor.execute(sql, params_fb)
            rows = cursor.fetchall() or []
        else:
            raise
    by_art: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        id_art = to_int_or_none(row.get("id_articulo"))
        if id_art is None:
            continue
        try:
            fab_acum = float(row.get("cantidad_fabricada_acumulada") or 0)
        except (TypeError, ValueError):
            fab_acum = 0.0
        by_art[id_art] = {
            "id_articulo": id_art,
            "codigo_articulo": str_or_default(row.get("codigo_articulo"), "-"),
            "codigo_manual": str_codigo_manual_articulo(row.get("codigo_manual")),
            "descripcion_articulo": str_or_default(row.get("descripcion_articulo"), "-"),
            "cantidad_pedida": to_int_or_none(row.get("cantidad_pedida")) or 0,
            "cantidad_pendiente_prod": to_int_or_none(row.get("cantidad_pendiente_prod")) or 0,
            "cantidad_fabricada_acumulada": fab_acum,
            "id_listas": set(),
        }
    return by_art


def _ventana_pack_pp_ped_q_res(
    cursor,
    tbl_detalle: Optional[str],
    ids: List[int],
) -> Tuple[Dict[int, float], Dict[int, float]]:
    split_p_ped: Dict[int, float] = {}
    split_q_res: Dict[int, float] = {}
    if not tbl_detalle or not ids:
        return split_p_ped, split_q_res
    ph = ",".join(["%s"] * len(ids))
    try:
        cursor.execute(
            f"""
            SELECT d.id_articulo,
                   COALESCE(SUM(CASE WHEN COALESCE(d.codigo_movimiento_pedido, 0) <> 0
                        THEN COALESCE(d.cantidad_pedida, 0) ELSE 0 END), 0) AS p_ped,
                   COALESCE(SUM(CASE WHEN COALESCE(d.codigo_movimiento_pedido, 0) = 0
                        THEN COALESCE(d.cantidad_pedida, 0) ELSE 0 END), 0) AS q_res
            FROM {tbl_detalle} d
            WHERE d.id_articulo IN ({ph})
              AND COALESCE(TRIM(d.en_proceso_produccion), 'No') = 'No'
            GROUP BY d.id_articulo
            """,
            ids,
        )
        for r in cursor.fetchall() or []:
            aid = to_int_or_none(r.get("id_articulo"))
            if aid is None:
                continue
            try:
                split_p_ped[aid] = float(r.get("p_ped") or 0)
            except (TypeError, ValueError):
                split_p_ped[aid] = 0.0
            try:
                split_q_res[aid] = float(r.get("q_res") or 0)
            except (TypeError, ValueError):
                split_q_res[aid] = 0.0
    except Exception as e_split:
        logger.debug("No se pudo cargar desglose P_ped/Q_res en ventana-pack: %s", e_split)
    return split_p_ped, split_q_res


def _etiqueta_origen_demanda_desde_split(p_ped: float, q_res: float) -> str:
    """Etiqueta visible: Pedido, Reserva, Pedido + reserva o — (misma regla que ventana-pack)."""
    p = float(p_ped or 0)
    q = float(q_res or 0)
    if p > 0 and q > 0:
        return "Pedido + reserva"
    if q > 0:
        return "Reserva"
    if p > 0:
        return "Pedido"
    return "—"


def bulk_origen_demanda_por_articulo(
    base_empresa: str, id_articulos: List[int]
) -> Dict[int, Dict[str, Any]]:
    """
    Origen de demanda por artículo (P_ped / Q_res en lista_produccion_detalle).
    Retorna {id_articulo: {origen_demanda_etiqueta, cantidad_pedida_pedido, cantidad_demanda_reserva}}.
    """
    ids = sorted(
        {
            x
            for x in (to_int_or_none(a) for a in (id_articulos or []))
            if x is not None
        }
    )
    out: Dict[int, Dict[str, Any]] = {}
    if not (base_empresa or "").strip() or not ids:
        return out
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            split_p_ped, split_q_res = _ventana_pack_pp_ped_q_res(cursor, tbl_detalle, ids)
        for aid in ids:
            p_ped = float(split_p_ped.get(aid, 0.0))
            q_res = float(split_q_res.get(aid, 0.0))
            out[aid] = {
                "cantidad_pedida_pedido": p_ped,
                "cantidad_demanda_reserva": q_res,
                "origen_demanda_etiqueta": _etiqueta_origen_demanda_desde_split(p_ped, q_res),
            }
    except Exception as e:
        logger.warning(
            "bulk_origen_demanda_por_articulo %s: %s", base_empresa, e, exc_info=True
        )
    return out


def aplicar_origen_demanda_a_filas(
    filas: List[Dict[str, Any]], mapa: Dict[int, Dict[str, Any]]
) -> None:
    """Inyecta origen_demanda_etiqueta (y desglose P_ped/Q_res) en filas con id_articulo."""
    for f in filas or []:
        aid = to_int_or_none(f.get("id_articulo"))
        if aid is None:
            continue
        info = mapa.get(aid) or {}
        f["origen_demanda_etiqueta"] = info.get("origen_demanda_etiqueta") or "—"
        f["cantidad_pedida_pedido"] = info.get("cantidad_pedida_pedido")
        f["cantidad_demanda_reserva"] = info.get("cantidad_demanda_reserva")


def resumen_origen_demanda_opt(lineas: List[Dict[str, Any]]) -> str:
    """Un solo origen, «Varios» si mezcla, o — si no hay datos."""
    etiquetas = {
        str(l.get("origen_demanda_etiqueta") or "").strip()
        for l in (lineas or [])
        if str(l.get("origen_demanda_etiqueta") or "").strip() not in ("", "—")
    }
    if not etiquetas:
        return "—"
    if len(etiquetas) == 1:
        return etiquetas.pop()
    return "Varios"


def calcular_porcentaje_progreso_opt(
    en_proceso: bool, cantidad_pendiente_opp: int
) -> int:
    """
    Progreso del timeline OPT (5 pasos) para listados.
    Misma lógica simplificada que el detalle: Pedida → En prod. → OPP → Pend. 0 → Cerrado.
    """
    pend = max(0, int(cantidad_pendiente_opp or 0))
    paso_pedida = True
    paso_cerrado = not en_proceso
    if paso_cerrado:
        return 100
    paso_liberada = True
    paso_producida_opp = pend <= 0
    paso_pendiente_cero = pend <= 0
    num_pasos = sum([
        paso_pedida,
        paso_liberada,
        paso_producida_opp,
        paso_pendiente_cero,
        paso_cerrado,
    ])
    return min(100, round(100 * num_pasos / 5))


def _mpr_parse_id_lista_desde_detalle_opp(detalle: str) -> Optional[int]:
    """Extrae id_lista_produccion de detalle OPP «OPT N desde…»."""
    m = re.search(r"OPT\s+(\d+)\s+desde", detalle or "", re.IGNORECASE)
    return to_int_or_none(m.group(1)) if m else None


def _mpr_parse_id_lista_desde_detalle_opa(detalle: str) -> Optional[int]:
    """Extrae id_lista_produccion de detalle OPA «OPT N …»."""
    m = re.search(r"OPT\s+(\d+)(?:\s|\)|$)", detalle or "", re.IGNORECASE)
    return to_int_or_none(m.group(1)) if m else None


def bulk_semi_elaborado_opp_por_opts(
    base_empresa: str, id_listas: List[int]
) -> Dict[int, Dict[int, int]]:
    """
    Cantidades OPP en Semi elaborado por OPT y artículo (unidades de componente/pack en stock).
    Retorna {id_lista: {id_articulo: cantidad}}.
    """
    ids = sorted({int(i) for i in (id_listas or []) if i is not None})
    out: Dict[int, Dict[int, int]] = {i: {} for i in ids}
    if not ids or not (base_empresa or "").strip():
        return out
    deposito_semi = get_deposito_semi_elaborado_mpr(base_empresa)
    if deposito_semi is None:
        return out
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_mov or not tbl_stock:
                return out
            condiciones = " OR ".join(
                ["INSTR(COALESCE(detalle,''), %s) > 0" for _ in ids]
            )
            params_pat = [f"OPT {i} desde" for i in ids]
            cursor.execute(
                f"""
                SELECT codigo_movimiento, detalle FROM {tbl_mov}
                WHERE (UPPER(TRIM(COALESCE(tipo_mov,''))) = 'OPP'
                       OR COALESCE(motivo_movimiento,'') = 'Parte producción')
                  AND ({condiciones})
                  AND COALESCE(anulado,'No') <> 'Si'
                """,
                params_pat,
            )
            mov_rows = cursor.fetchall() or []
            cod_a_lista: Dict[int, int] = {}
            codigos: List[int] = []
            for row in mov_rows:
                cod = to_int_or_none(row.get("codigo_movimiento"))
                id_l = _mpr_parse_id_lista_desde_detalle_opp(str(row.get("detalle") or ""))
                if cod is None or id_l is None or id_l not in out:
                    continue
                cod_a_lista[int(cod)] = int(id_l)
                codigos.append(int(cod))
            if not codigos:
                return out
            ph = ",".join(["%s"] * len(codigos))
            cursor.execute(
                f"""
                SELECT CodigoMovimiento, IDArt, COALESCE(SUM(Entrada), 0) AS total
                FROM {tbl_stock}
                WHERE CodigoMovimiento IN ({ph})
                  AND CodDeposito = %s
                  AND COALESCE(Entrada, 0) > 0
                GROUP BY CodigoMovimiento, IDArt
                """,
                codigos + [deposito_semi],
            )
            for row in cursor.fetchall() or []:
                cod = to_int_or_none(row.get("CodigoMovimiento"))
                id_art = to_int_or_none(row.get("IDArt"))
                if cod is None or id_art is None:
                    continue
                id_l = cod_a_lista.get(int(cod))
                if id_l is None:
                    continue
                qty = int(float(row.get("total") or 0))
                if qty <= 0:
                    continue
                bucket = out[id_l]
                bucket[id_art] = bucket.get(id_art, 0) + qty
    except Exception as e:
        logger.warning(
            "bulk_semi_elaborado_opp_por_opts %s: %s", base_empresa, e, exc_info=True
        )
    return out


def bulk_cantidades_armadas_por_opts(
    base_empresa: str, id_listas: List[int]
) -> Dict[int, Dict[int, int]]:
    """Cantidades ya armadas por OPT y pack: {id_lista: {id_articulo: qty}}."""
    ids = sorted({int(i) for i in (id_listas or []) if i is not None})
    out: Dict[int, Dict[int, int]] = {i: {} for i in ids}
    if not ids or not (base_empresa or "").strip():
        return out
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_mov or not tbl_stock:
                return out
            condiciones = " OR ".join(
                [
                    "(INSTR(COALESCE(detalle,''), %s) > 0 OR INSTR(COALESCE(detalle,''), %s) > 0)"
                    for _ in ids
                ]
            )
            params_pat: List[str] = []
            for i in ids:
                params_pat.extend([f"OPT {i} ", f"OPT {i})"])
            cursor.execute(
                f"""
                SELECT codigo_movimiento, detalle FROM {tbl_mov}
                WHERE UPPER(TRIM(COALESCE(tipo_mov,''))) IN ('OPA', 'ARMADO')
                  AND ({condiciones})
                  AND COALESCE(anulado,'No') <> 'Si'
                """,
                params_pat,
            )
            mov_rows = cursor.fetchall() or []
            cod_a_lista: Dict[int, int] = {}
            codigos: List[int] = []
            for row in mov_rows:
                cod = to_int_or_none(row.get("codigo_movimiento"))
                det = str(row.get("detalle") or "")
                id_l = _mpr_parse_id_lista_desde_detalle_opa(det)
                if cod is None or id_l is None or id_l not in out:
                    continue
                cod_a_lista[int(cod)] = int(id_l)
                codigos.append(int(cod))
            if not codigos:
                return out
            ph = ",".join(["%s"] * len(codigos))
            cursor.execute(
                f"""
                SELECT CodigoMovimiento, IDArt, COALESCE(SUM(Entrada), 0) AS total_entrada
                FROM {tbl_stock}
                WHERE CodigoMovimiento IN ({ph}) AND COALESCE(Entrada, 0) > 0
                GROUP BY CodigoMovimiento, IDArt
                """,
                codigos,
            )
            for row in cursor.fetchall() or []:
                cod = to_int_or_none(row.get("CodigoMovimiento"))
                id_art = to_int_or_none(row.get("IDArt"))
                if cod is None or id_art is None:
                    continue
                id_l = cod_a_lista.get(int(cod))
                if id_l is None:
                    continue
                qty = int(float(row.get("total_entrada") or 0))
                if qty <= 0:
                    continue
                bucket = out[id_l]
                bucket[id_art] = bucket.get(id_art, 0) + qty
    except Exception as e:
        logger.warning(
            "bulk_cantidades_armadas_por_opts %s: %s", base_empresa, e, exc_info=True
        )
    return out


def bulk_restante_armar_opt_listado(
    base_empresa: str,
    filas: List[Dict[str, Any]],
    abm_map: Dict[int, Optional[int]],
) -> Dict[str, int]:
    """
    Por par (id_lista, id_articulo): packs aún por armar (semi − ya armado).
    Clave ``"{id_lista}:{id_articulo}"``.
    """
    candidatos = [
        f for f in (filas or [])
        if to_int_or_none(f.get("id_lista_produccion")) is not None
        and int(f.get("cantidad_pendiente_prod") or 0) <= 0
        and abm_map.get(f.get("id_articulo"))
    ]
    ids = sorted({int(f["id_lista_produccion"]) for f in candidatos})
    if not ids:
        return {}
    semi_por_opt = bulk_semi_elaborado_opp_por_opts(base_empresa, ids)
    armadas_por_opt = bulk_cantidades_armadas_por_opts(base_empresa, ids)
    resultado: Dict[str, int] = {}
    for f in candidatos:
        id_lista = int(f["id_lista_produccion"])
        id_art = f.get("id_articulo")
        if not id_art:
            continue
        semi_map = semi_por_opt.get(id_lista, {})
        equiv = bulk_componentes_a_equivalentes_pack(
            base_empresa, [id_art], semi_map
        )
        disponible = equiv.get(id_art, 0)
        ya_armada = armadas_por_opt.get(id_lista, {}).get(id_art, 0)
        restante = max(0, int(disponible) - int(ya_armada))
        resultado[f"{id_lista}:{id_art}"] = restante
    return resultado


def bulk_mstock_imputacion_por_articulo(
    base_empresa: str, id_articulos: List[int]
) -> Dict[int, Dict[str, Any]]:
    """
    Resumen de MSTOCK Armado 1ra pendiente de imputar por pack.
    {id_articulo_pack: {codigo_movimiento, id_lote_armado, cantidad_pendiente_imputar, n_mstock}}.
    """
    from mpr.models import (
        ESTADO_IMPUTACION_PARCIAL,
        ESTADO_IMPUTACION_PENDIENTE,
        MODO_ARMADO_1RA,
        MprArmadoSurtidoMovimiento,
    )

    ids = sorted(
        {x for x in (to_int_or_none(a) for a in (id_articulos or [])) if x is not None}
    )
    out: Dict[int, Dict[str, Any]] = {}
    if not ids or not (base_empresa or "").strip():
        return out
    movs = (
        MprArmadoSurtidoMovimiento.objects.filter(
            base_empresa=(base_empresa or "").strip(),
            modo=MODO_ARMADO_1RA,
            id_articulo_pack__in=ids,
            estado_imputacion__in=[
                ESTADO_IMPUTACION_PENDIENTE,
                ESTADO_IMPUTACION_PARCIAL,
            ],
        )
        .order_by("-creado_en")
        .only(
            "codigo_movimiento",
            "id_articulo_pack",
            "cantidad_packs",
            "id_lote_armado_id",
            "estado_imputacion",
        )
    )
    for m in movs:
        aid = int(m.id_articulo_pack)
        imputado = _cantidad_imputada_mstock(base_empresa, m.codigo_movimiento)
        pend = int(m.cantidad_packs or 0) - imputado
        if pend <= 0:
            continue
        if aid not in out:
            out[aid] = {
                "codigo_movimiento": m.codigo_movimiento,
                "id_lote_armado": str(m.id_lote_armado_id) if m.id_lote_armado_id else None,
                "cantidad_pendiente_imputar": pend,
                "n_mstock": 1,
            }
        else:
            out[aid]["n_mstock"] = int(out[aid].get("n_mstock") or 0) + 1
            out[aid]["cantidad_pendiente_imputar"] = int(
                out[aid].get("cantidad_pendiente_imputar") or 0
            ) + pend
    return out


def _fase_clave_prioridad(clave: str) -> int:
    orden = {
        "demanda": 0,
        "pendiente": 1,
        "en_produccion_opp": 2,
        "en_produccion": 3,
        "lista_cerrar": 4,
        "cerrada": 5,
    }
    return orden.get(clave or "", 1)


def agrupar_filas_opt_listado_por_lote(
    filas: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Agrupa filas con el mismo codigo_movimiento_opt (lote OPT multi-artículo).
    Cada grupo expone lineas[] y métricas agregadas; es_grupo=True si hay >1 línea.
    """
    from collections import OrderedDict

    grupos: "OrderedDict[int, Dict[str, Any]]" = OrderedDict()
    sin_codigo: List[Dict[str, Any]] = []
    for f in filas or []:
        cod = to_int_or_none(f.get("codigo_movimiento_opt"))
        if cod is None or cod <= 0:
            f["es_grupo"] = False
            sin_codigo.append(f)
            continue
        if cod not in grupos:
            grupos[cod] = {
                "es_grupo": False,
                "codigo_movimiento_opt": cod,
                "lineas": [],
            }
        grupos[cod]["lineas"].append(f)

    resultado: List[Dict[str, Any]] = []
    for cod, g in grupos.items():
        lineas_g = g["lineas"]
        g["es_grupo"] = len(lineas_g) > 1
        g["id_lista_produccion"] = min(
            to_int_or_none(ln.get("id_lista_produccion")) or 0 for ln in lineas_g
        )
        g["cantidad_pedida"] = sum(int(ln.get("cantidad_pedida") or 0) for ln in lineas_g)
        g["cantidad_pendiente_prod"] = sum(
            int(ln.get("cantidad_pendiente_prod") or 0) for ln in lineas_g
        )
        g["cantidad_pendiente_mostrar"] = sum(
            int(ln.get("cantidad_pendiente_mostrar") or 0) for ln in lineas_g
        )
        g["porcentaje_progreso"] = min(
            int(ln.get("porcentaje_progreso") or 0) for ln in lineas_g
        )
        g["origen_demanda_etiqueta"] = resumen_origen_demanda_opt(lineas_g)
        peor = min(lineas_g, key=lambda ln: _fase_clave_prioridad(ln.get("fase_clave")))
        g["fase_clave"] = peor.get("fase_clave")
        g["etiqueta_fase"] = peor.get("etiqueta_fase")
        g["en_proceso_produccion"] = any(
            (ln.get("en_proceso_produccion") or "No").strip() == "Si" for ln in lineas_g
        )
        id_lista = g["id_lista_produccion"]
        if id_lista:
            g["detail_url"] = reverse_mpr_opt_detail(id_lista)
            from django.urls import reverse as dj_reverse
            g["crear_opp_url"] = dj_reverse("mpr:parte_produccion")
            g["cerrar_url"] = dj_reverse("mpr:opt_cerrar", kwargs={"id_lista": id_lista})
        else:
            g["detail_url"] = None
            g["crear_opp_url"] = None
            g["cerrar_url"] = None
        g["armado_url"] = lineas_g[0].get("armado_url")
        g["accion_principal"] = None
        g["mostrar_link_armado"] = any(ln.get("mostrar_link_armado") for ln in lineas_g)
        g["tiene_armado_pendiente"] = any(ln.get("tiene_armado_pendiente") for ln in lineas_g)
        g["restante_armar"] = sum(int(ln.get("restante_armar") or 0) for ln in lineas_g)
        g["mostrar_link_imputacion"] = any(
            ln.get("mostrar_link_imputacion") for ln in lineas_g
        )
        g["imputacion_url"] = next(
            (ln.get("imputacion_url") for ln in lineas_g if ln.get("imputacion_url")),
            None,
        )
        g["codigo_articulo"] = (
            f"{len(lineas_g)} artículos" if g["es_grupo"] else lineas_g[0].get("codigo_articulo")
        )
        g["descripcion_articulo"] = (
            " · ".join(
                str(ln.get("codigo_articulo") or "")[:20] for ln in lineas_g[:3]
            )
            + ("…" if len(lineas_g) > 3 else "")
            if g["es_grupo"]
            else lineas_g[0].get("descripcion_articulo")
        )
        if any(ln.get("accion_principal") == "cerrar" for ln in lineas_g):
            g["accion_principal"] = "cerrar"
        elif any(ln.get("accion_principal") == "crear_opp" for ln in lineas_g):
            g["accion_principal"] = "crear_opp"
        if not g["es_grupo"]:
            ln0 = lineas_g[0]
            for key in (
                "es_opt_creada", "codigo_articulo", "descripcion_articulo", "codigo_manual",
                "id_articulo", "en_proceso_produccion", "puede_crear_opp", "puede_cerrar",
                "tiene_bom_armable", "mstock_pendiente_imputar",
            ):
                if key in ln0:
                    g[key] = ln0[key]
        resultado.append(g)
    resultado.extend(sin_codigo)
    return resultado


def reverse_mpr_opt_detail(id_lista: int) -> str:
    """URL detalle OPT (evita import circular django.urls en tests unitarios)."""
    from django.urls import reverse

    return reverse("mpr:opt_detail", kwargs={"id_lista": id_lista})


def _ventana_pack_pedidos_resumen(
    cursor,
    tbl_detalle: Optional[str],
    tbl_cp: Optional[str],
    tbl_cli: Optional[str],
    ids: List[int],
    split_q_res: Dict[int, float],
) -> Dict[int, List[Dict[str, Any]]]:
    pedidos_por_articulo: Dict[int, List[Dict[str, Any]]] = {aid: [] for aid in ids}
    if not tbl_detalle or not tbl_cp or not ids:
        return pedidos_por_articulo
    ph = ",".join(["%s"] * len(ids))
    join_cli = f"LEFT JOIN {tbl_cli} cli ON cli.codigo = cp.codigo" if tbl_cli else ""
    sql_ped = f"""
        SELECT d.id_articulo,
               cp.CodigoMovimiento AS codigo_movimiento_pedido,
               MAX(COALESCE(cp.NroComprobante, cp.NroCompBusq, '')) AS nro_pedido,
               MAX(COALESCE(cp.estado_pedido_opt, '')) AS estado_pedido_opt,
               MAX(COALESCE(cli.nombre_cliente, '')) AS nombre_cliente
        FROM {tbl_detalle} d
        INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = d.codigo_movimiento_pedido
        {join_cli}
        WHERE d.id_articulo IN ({ph})
          AND COALESCE(d.codigo_movimiento_pedido, 0) <> 0
        GROUP BY d.id_articulo, cp.CodigoMovimiento
        ORDER BY d.id_articulo, nro_pedido DESC, cp.CodigoMovimiento DESC
    """
    sql_ped_sin_cli = f"""
        SELECT d.id_articulo,
               cp.CodigoMovimiento AS codigo_movimiento_pedido,
               MAX(COALESCE(cp.NroComprobante, cp.NroCompBusq, '')) AS nro_pedido,
               MAX(COALESCE(cp.estado_pedido_opt, '')) AS estado_pedido_opt,
               '' AS nombre_cliente
        FROM {tbl_detalle} d
        INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = d.codigo_movimiento_pedido
        WHERE d.id_articulo IN ({ph})
          AND COALESCE(d.codigo_movimiento_pedido, 0) <> 0
        GROUP BY d.id_articulo, cp.CodigoMovimiento
        ORDER BY d.id_articulo, nro_pedido DESC, cp.CodigoMovimiento DESC
    """
    rows_ped: List[Any] = []
    try:
        cursor.execute(sql_ped, ids)
        rows_ped = list(cursor.fetchall() or [])
    except Exception as e_ped:
        err = str(e_ped).lower()
        if "1054" in str(e_ped) or "unknown column" in err:
            try:
                cursor.execute(sql_ped_sin_cli, ids)
                rows_ped = list(cursor.fetchall() or [])
            except Exception as e2:
                logger.debug("No se pudo cargar pedidos_resumen en ventana-pack: %s", e2)
        else:
            logger.debug("No se pudo cargar pedidos_resumen desde detalle en ventana-pack: %s", e_ped)
    pedidos_ya_vistos: Dict[int, Set[str]] = {aid: set() for aid in ids}
    for r in rows_ped:
        aid = to_int_or_none(r.get("id_articulo"))
        if aid is None or aid not in pedidos_por_articulo:
            continue
        cod_mov = r.get("codigo_movimiento_pedido")
        if cod_mov is not None and str(cod_mov).strip() != "":
            clave_unica = str(cod_mov).strip()
        else:
            clave_unica = "nro:" + str_or_default(r.get("nro_pedido"), "-")
        if clave_unica in pedidos_ya_vistos[aid]:
            continue
        pedidos_ya_vistos[aid].add(clave_unica)
        pedidos_por_articulo[aid].append({
            "nro_pedido": str_or_default(r.get("nro_pedido"), "-"),
            "estado_pedido_opt": str_or_default(r.get("estado_pedido_opt"), "-"),
            "nombre_cliente": str_or_default(r.get("nombre_cliente"), "-"),
        })
    for aid in ids:
        q_res = float(split_q_res.get(aid, 0.0))
        if q_res > 0:
            pedidos_por_articulo[aid].append({
                "es_demanda_reserva": True,
                "nro_pedido": "—",
                "estado_pedido_opt": "Demanda reserva",
                "nombre_cliente": "",
                "cantidad_demanda_reserva": q_res,
            })
        pedidos_por_articulo[aid].sort(
            key=lambda p: str(p.get("nro_pedido") or ""),
            reverse=True,
        )
    return pedidos_por_articulo


def _ventana_pack_stock_maps(
    cursor,
    tbl_sd: Optional[str],
    tbl_dep: Optional[str],
    ids: List[int],
    *,
    incluir_detalle: bool,
) -> Tuple[Dict[int, float], Dict[int, List[Dict[str, Any]]]]:
    stock_map: Dict[int, float] = {}
    detalle_por_art: Dict[int, List[Dict[str, Any]]] = {}
    if not tbl_sd or not tbl_dep or not ids:
        return stock_map, detalle_por_art
    ph = ",".join(["%s"] * len(ids))
    if incluir_detalle:
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
                WHERE sd.id_articulo IN ({ph})
                ORDER BY sd.id_articulo, d.NombreDeposito, d.CodDeposito
                """,
                ids,
            )
            for row in cursor.fetchall() or []:
                id_art = to_int_or_none(row.get("id_articulo"))
                if id_art is None:
                    continue
                try:
                    saldo = float(row.get("stock_terminado") or 0)
                except (TypeError, ValueError):
                    saldo = 0.0
                detalle_por_art.setdefault(id_art, []).append({
                    "deposito": str_or_default(row.get("deposito"), "-"),
                    "stock_terminado": saldo,
                })
                stock_map[id_art] = stock_map.get(id_art, 0.0) + saldo
        except Exception:
            detalle_por_art = {}
            stock_map = {}
    if not stock_map:
        cursor.execute(
            f"""
            SELECT sd.id_articulo, COALESCE(SUM(sd.saldo), 0) AS stock_terminado
            FROM {tbl_sd} sd
            INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
              AND COALESCE(d.anulado, 'No') = 'No'
              AND COALESCE(d.suma_stock, 'Si') = 'Si'
            WHERE sd.id_articulo IN ({ph})
            GROUP BY sd.id_articulo
            """,
            ids,
        )
        for row in cursor.fetchall() or []:
            id_art = to_int_or_none(row.get("id_articulo"))
            if id_art is not None:
                try:
                    stock_map[id_art] = float(row.get("stock_terminado") or 0)
                except (TypeError, ValueError):
                    stock_map[id_art] = 0.0
    return stock_map, detalle_por_art


def _formatear_fecha_dd_mm_yyyy(value) -> str:
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


def _append_filtro_periodo_agrupada(
    cursor,
    sql: str,
    params: list,
    *,
    tbl_agrupada: str,
    alias_l: str = "l",
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    col_fecha: Optional[str] = None,
) -> tuple[str, list]:
    """Restringe filas agrupadas al período: pedidos vinculados (comp_ped.Fecha) o fecha_objetivo."""
    if fecha_desde is None and fecha_hasta is None:
        return sql, params
    fd = fecha_desde or date(1900, 1, 1)
    fh = fecha_hasta or date(9999, 12, 31)
    tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
    tbl_cp = _nombre_tabla(cursor, "comp_ped")
    if tbl_detalle and tbl_cp:
        sql += f"""
            AND (
                EXISTS (
                    SELECT 1 FROM {tbl_detalle} d
                    INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = d.codigo_movimiento_pedido
                    WHERE d.id_lista_produccion = {alias_l}.id_lista_produccion
                      AND COALESCE(d.codigo_movimiento_pedido, 0) <> 0
                      AND cp.Fecha >= %s AND cp.Fecha <= %s
                )
        """
        params.extend([fd, fh])
        if col_fecha:
            sql += f"""
                OR (
                    NOT EXISTS (
                        SELECT 1 FROM {tbl_detalle} d2
                        WHERE d2.id_lista_produccion = {alias_l}.id_lista_produccion
                          AND COALESCE(d2.codigo_movimiento_pedido, 0) <> 0
                    )
                    AND {alias_l}.{col_fecha} IS NOT NULL
                    AND {alias_l}.{col_fecha} >= %s AND {alias_l}.{col_fecha} <= %s
                )
            """
            params.extend([fd, fh])
        sql += ")"
    elif col_fecha:
        sql += f" AND {alias_l}.{col_fecha} >= %s AND {alias_l}.{col_fecha} <= %s"
        params.extend([fd, fh])
    return sql, params


def listar_lista_produccion_agrupada(
    base_empresa: str,
    limit: int = 200,
    id_articulo: Optional[int] = None,
    estado_en_proceso: Optional[str] = None,
    solo_atrasadas: bool = False,
    excluir_filas_opt_liberadas_mstock: bool = False,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Lista producción agrupada por artículo (lista_produccion_agrupada + articulo).

    estado_en_proceso: None = todos, 'Si' = solo en proceso, 'No' = solo pendientes.
    solo_atrasadas: si True, solo filas con fecha_objetivo no nula y fecha_objetivo < hoy (requiere columna en tabla).
    excluir_filas_opt_liberadas_mstock: si True y existe columna codigo_movimiento_opt, excluye filas con
    codigo_movimiento_opt > 0 (OPT ya liberada: código real de movimiento_stock). Esas filas no son demanda
    nueva; al cerrar la OPT deberían quedar con pendiente 0; si quedan datos inconsistentes, no deben
    duplicar totales en ventana-pack / demanda.
    Devuelve filas con: id_lista_produccion, id_articulo, codigo_articulo, descripcion_articulo,
    cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion,
    cantidad_fabricada_acumulada (0 si la columna no existe en la tabla).
    Si faltan ``lista_produccion_agrupada`` o ``articulo``, lanza ``MprSchemaError``.
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
            col_fab = opts.get("cantidad_fabricada_acumulada")
            fab_sel = (
                f"COALESCE(l.{col_fab}, 0) AS cantidad_fabricada_acumulada"
                if col_fab
                else "0 AS cantidad_fabricada_acumulada"
            )
            col_cod_mov_opt = opts.get("codigo_movimiento_opt")
            sql_excl_opt_lib = ""
            if excluir_filas_opt_liberadas_mstock and col_cod_mov_opt:
                sql_excl_opt_lib = f" AND NOT (COALESCE(l.{col_cod_mov_opt}, 0) > 0)"
            sql = f"""
                SELECT
                    l.id_lista_produccion,
                    l.id_articulo,
                    COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                    COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                    COALESCE(a.id_manual, '') AS codigo_manual,
                    COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                    COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                    l.cantidad_asignada_opt,
                    COALESCE(NULLIF(TRIM(l.en_proceso_produccion), ''), 'No') AS en_proceso_produccion,
                    {fab_sel}
                FROM {tbl_agrupada} l
                INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                WHERE COALESCE(l.cantidad_pendiente_prod, 0) > 0{sql_excl_opt_lib}
            """
            params = []
            if id_articulo is not None:
                sql += " AND l.id_articulo = %s"
                params.append(id_articulo)
            if estado_en_proceso in ("Si", "No"):
                # Mismo criterio que actualizar_pedidos_produccion (TRIM) para no excluir filas legacy con espacios
                sql += " AND COALESCE(NULLIF(TRIM(l.en_proceso_produccion), ''), 'No') = %s"
                params.append(estado_en_proceso)
            if solo_atrasadas and col_fecha:
                sql += f" AND l.{col_fecha} IS NOT NULL AND l.{col_fecha} < CURDATE()"
            sql, params = _append_filtro_periodo_agrupada(
                cursor,
                sql,
                params,
                tbl_agrupada=tbl_agrupada,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                col_fecha=col_fecha,
            )
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
                            '' AS codigo_manual,
                            COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                            COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                            l.cantidad_asignada_opt,
                            COALESCE(NULLIF(TRIM(l.en_proceso_produccion), ''), 'No') AS en_proceso_produccion,
                            {fab_sel}
                        FROM {tbl_agrupada} l
                        INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                        WHERE COALESCE(l.cantidad_pendiente_prod, 0) > 0{sql_excl_opt_lib}
                    """
                    if id_articulo is not None:
                        sql_fallback += " AND l.id_articulo = %s"
                    if estado_en_proceso in ("Si", "No"):
                        sql_fallback += " AND COALESCE(NULLIF(TRIM(l.en_proceso_produccion), ''), 'No') = %s"
                    if solo_atrasadas and col_fecha:
                        sql_fallback += f" AND l.{col_fecha} IS NOT NULL AND l.{col_fecha} < CURDATE()"
                    sql_fallback, params = _append_filtro_periodo_agrupada(
                        cursor,
                        sql_fallback,
                        params,
                        tbl_agrupada=tbl_agrupada,
                        fecha_desde=fecha_desde,
                        fecha_hasta=fecha_hasta,
                        col_fecha=col_fecha,
                    )
                    sql_fallback += " ORDER BY l.id_lista_produccion, l.id_articulo LIMIT %s"
                    cursor.execute(sql_fallback, params)
                else:
                    raise col_err
            rows = cursor.fetchall()
        result = []
        for r in rows:
            result.append({
                "id_lista_produccion": to_int_or_none(r.get("id_lista_produccion")),
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "codigo_manual": str_codigo_manual_articulo(r.get("codigo_manual")),
                "cantidad_pedida": to_int_or_none(r.get("cantidad_pedida")) or 0,
                "cantidad_pendiente_prod": to_int_or_none(r.get("cantidad_pendiente_prod")) or 0,
                "cantidad_asignada_opt": to_int_or_none(r.get("cantidad_asignada_opt")),
                "en_proceso_produccion": str_or_default(r.get("en_proceso_produccion"), "No"),
                "cantidad_fabricada_acumulada": float(r.get("cantidad_fabricada_acumulada") or 0),
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


def listar_opt_listado(
    base_empresa: str,
    limit: int = 500,
    estado_en_proceso: Optional[str] = None,
    solo_atrasadas: bool = False,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Lista para la pantalla «Órdenes de Producción de Trabajo»: solo OPTs ya creadas (liberadas).
    No incluye demanda (filas sin codigo_movimiento_opt). Incluye OPTs cerradas (pendiente 0).
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_agrupada or not tbl_articulo:
                raise MprSchemaError(
                    "Faltan tablas en la base de datos: lista_produccion_agrupada o articulo."
                )
            opts = _columnas_opcionales_op_agrupada(cursor, tbl_agrupada)
            col_fecha = opts.get("fecha_objetivo")
            has_codigo_mov_opt = False
            try:
                sql = f"""
                    SELECT
                        l.id_lista_produccion,
                        l.id_articulo,
                        COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                        COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                        COALESCE(a.id_manual, '') AS codigo_manual,
                        COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                        COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                        l.cantidad_asignada_opt,
                        COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion,
                        l.codigo_movimiento_opt
                    FROM {tbl_agrupada} l
                    INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                    WHERE l.codigo_movimiento_opt IS NOT NULL AND l.codigo_movimiento_opt > 0
                """
                params = []
                if estado_en_proceso in ("Si", "No"):
                    sql += " AND COALESCE(l.en_proceso_produccion, 'No') = %s"
                    params.append(estado_en_proceso)
                if solo_atrasadas and col_fecha:
                    sql += f" AND l.{col_fecha} IS NOT NULL AND l.{col_fecha} < CURDATE() AND COALESCE(l.cantidad_pendiente_prod, 0) > 0"
                sql, params = _append_filtro_periodo_agrupada(
                    cursor,
                    sql,
                    params,
                    tbl_agrupada=tbl_agrupada,
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                    col_fecha=col_fecha,
                )
                sql += " ORDER BY l.id_lista_produccion DESC, l.id_articulo LIMIT %s"
                params.append(limit)
                cursor.execute(sql, params)
                has_codigo_mov_opt = True
            except Exception as e:
                if "1054" in str(e) or "Unknown column" in str(e).lower() or "codigo_movimiento_opt" in str(e):
                    # Sin columna codigo_movimiento_opt: solo OPT en proceso (excluir demanda)
                    sql = f"""
                        SELECT
                            l.id_lista_produccion,
                            l.id_articulo,
                            COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                            COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                            COALESCE(a.id_manual, '') AS codigo_manual,
                            COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                            COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                            l.cantidad_asignada_opt,
                            COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion
                        FROM {tbl_agrupada} l
                        INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                        WHERE COALESCE(l.en_proceso_produccion, 'No') = 'Si'
                    """
                    params = []
                    if estado_en_proceso in ("Si", "No"):
                        sql += " AND COALESCE(l.en_proceso_produccion, 'No') = %s"
                        params.append(estado_en_proceso)
                    if solo_atrasadas and col_fecha:
                        sql += f" AND l.{col_fecha} IS NOT NULL AND l.{col_fecha} < CURDATE() AND COALESCE(l.cantidad_pendiente_prod, 0) > 0"
                    sql, params = _append_filtro_periodo_agrupada(
                        cursor,
                        sql,
                        params,
                        tbl_agrupada=tbl_agrupada,
                        fecha_desde=fecha_desde,
                        fecha_hasta=fecha_hasta,
                        col_fecha=col_fecha,
                    )
                    sql += " ORDER BY l.id_lista_produccion DESC, l.id_articulo LIMIT %s"
                    params.append(limit)
                    cursor.execute(sql, params)
                else:
                    raise
            rows = cursor.fetchall()
        result = []
        for r in rows:
            codigo_mov_opt = to_int_or_none(r.get("codigo_movimiento_opt")) if has_codigo_mov_opt else None
            en_proceso = str_or_default(r.get("en_proceso_produccion"), "No").strip()
            es_opt_creada = (
                _mpr_es_codigo_movimiento_opt_mstock(codigo_mov_opt) if has_codigo_mov_opt else (en_proceso == "Si")
            )
            result.append({
                "id_lista_produccion": to_int_or_none(r.get("id_lista_produccion")),
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "codigo_manual": str_codigo_manual_articulo(r.get("codigo_manual")),
                "cantidad_pedida": to_int_or_none(r.get("cantidad_pedida")) or 0,
                "cantidad_pendiente_prod": to_int_or_none(r.get("cantidad_pendiente_prod")) or 0,
                "cantidad_asignada_opt": to_int_or_none(r.get("cantidad_asignada_opt")),
                "en_proceso_produccion": en_proceso,
                "codigo_movimiento_opt": codigo_mov_opt,
                "es_opt_creada": es_opt_creada,
            })
        return result
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning(
            "Error al listar OPT listado en %s: %s",
            base_empresa,
            e,
            exc_info=True,
        )
        return []


def contar_opt_atrasadas_distintas(base_empresa: str) -> int:
    """Cantidad de OPT distintas vencidas (fecha objetivo pasada y pendiente > 0). Para KPI tablero."""
    if not (base_empresa or "").strip():
        return 0
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl_agrupada:
                return 0
            opts = _columnas_opcionales_op_agrupada(cursor, tbl_agrupada)
            col_fecha = opts.get("fecha_objetivo")
            if not col_fecha:
                return 0
            try:
                cursor.execute(
                    f"""
                    SELECT COUNT(DISTINCT l.id_lista_produccion) AS total
                    FROM {tbl_agrupada} l
                    WHERE l.codigo_movimiento_opt IS NOT NULL AND l.codigo_movimiento_opt > 0
                      AND l.{col_fecha} IS NOT NULL AND l.{col_fecha} < CURDATE()
                      AND COALESCE(l.cantidad_pendiente_prod, 0) > 0
                    """,
                )
            except Exception as e:
                if "1054" in str(e) or "unknown column" in str(e).lower():
                    cursor.execute(
                        f"""
                        SELECT COUNT(DISTINCT l.id_lista_produccion) AS total
                        FROM {tbl_agrupada} l
                        WHERE COALESCE(l.en_proceso_produccion, 'No') = 'Si'
                          AND l.{col_fecha} IS NOT NULL AND l.{col_fecha} < CURDATE()
                          AND COALESCE(l.cantidad_pendiente_prod, 0) > 0
                        """,
                    )
                else:
                    raise
            row = cursor.fetchone()
            return to_int_or_none(row.get("total") if isinstance(row, dict) else None) or 0
    except Exception as e:
        logger.warning("Error al contar OPT atrasadas en %s: %s", base_empresa, e, exc_info=True)
        return 0


def listar_opt_atrasadas_tablero(
    base_empresa: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """OPT vencidas para el tablero: una fila por id_lista_produccion (sin traer 500 líneas)."""
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_agrupada or not tbl_articulo:
                return []
            opts = _columnas_opcionales_op_agrupada(cursor, tbl_agrupada)
            col_fecha = opts.get("fecha_objetivo")
            if not col_fecha:
                return []
            sql_tpl = """
                SELECT l.id_lista_produccion,
                       MAX(COALESCE(a.NombreArticulo, '')) AS descripcion_articulo,
                       SUM(COALESCE(l.cantidad_pendiente_prod, 0)) AS cantidad_pendiente_prod
                FROM {tbl_agrupada} l
                INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                WHERE {where_extra}
                  AND l.{col_fecha} IS NOT NULL AND l.{col_fecha} < CURDATE()
                  AND COALESCE(l.cantidad_pendiente_prod, 0) > 0
                GROUP BY l.id_lista_produccion
                ORDER BY l.id_lista_produccion DESC
                LIMIT %s
            """
            rows = []
            try:
                cursor.execute(
                    sql_tpl.format(
                        tbl_agrupada=tbl_agrupada,
                        tbl_articulo=tbl_articulo,
                        col_fecha=col_fecha,
                        where_extra="l.codigo_movimiento_opt IS NOT NULL AND l.codigo_movimiento_opt > 0",
                    ),
                    [limit],
                )
                rows = cursor.fetchall() or []
            except Exception as e:
                if "1054" in str(e) or "unknown column" in str(e).lower():
                    cursor.execute(
                        sql_tpl.format(
                            tbl_agrupada=tbl_agrupada,
                            tbl_articulo=tbl_articulo,
                            col_fecha=col_fecha,
                            where_extra="COALESCE(l.en_proceso_produccion, 'No') = 'Si'",
                        ),
                        [limit],
                    )
                    rows = cursor.fetchall() or []
                else:
                    raise
        return [
            {
                "id_lista_produccion": to_int_or_none(r.get("id_lista_produccion")),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "cantidad_pendiente_prod": to_int_or_none(r.get("cantidad_pendiente_prod")) or 0,
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Error al listar OPT atrasadas tablero en %s: %s", base_empresa, e, exc_info=True)
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


def _estado_acciones_opt_vacio() -> Dict[str, Any]:
    return {
        "total_pendiente_opp": 0,
        "puede_crear_opp": False,
        "puede_cerrar": False,
    }


def _ids_miembros_grupo_opt_bulk(
    base_empresa: str,
    id_listas: List[int],
) -> Dict[int, List[int]]:
    """Mapa id_lista (entrada) → ids lista_produccion del mismo lote OPT (paridad get_opt_detalle)."""
    ids_in = sorted({int(i) for i in id_listas if i is not None})
    if not ids_in or not (base_empresa or "").strip():
        return {}
    result: Dict[int, List[int]] = {i: [i] for i in ids_in}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl:
                return result
            ph = ",".join(["%s"] * len(ids_in))
            row_by_id: Dict[int, Dict[str, Any]] = {}
            tiene_id_opt = True
            try:
                cursor.execute(
                    f"SELECT id_lista_produccion, codigo_movimiento_opt, id_opt FROM {tbl} "
                    f"WHERE id_lista_produccion IN ({ph})",
                    ids_in,
                )
            except Exception as col_err:
                if "1054" in str(col_err) or "unknown column" in str(col_err).lower():
                    tiene_id_opt = False
                    try:
                        cursor.execute(
                            f"SELECT id_lista_produccion, codigo_movimiento_opt FROM {tbl} "
                            f"WHERE id_lista_produccion IN ({ph})",
                            ids_in,
                        )
                    except Exception:
                        return result
                else:
                    raise
            for r in cursor.fetchall() or []:
                r_l = _row_dict_lower_keys(r)
                lid = to_int_or_none(r_l.get("id_lista_produccion"))
                if lid is not None:
                    row_by_id[lid] = r_l

            cods: Set[int] = set()
            id_opts: Set[int] = set()
            for lid in ids_in:
                row = row_by_id.get(lid, {})
                cod = to_int_or_none(row.get("codigo_movimiento_opt"))
                if cod is not None and cod != 0:
                    cods.add(int(cod))
                if tiene_id_opt:
                    id_opt = to_int_or_none(row.get("id_opt"))
                    if id_opt is not None and id_opt != 0:
                        id_opts.add(int(id_opt))

            members_by_cod: Dict[int, List[int]] = {}
            if cods:
                ph_c = ",".join(["%s"] * len(cods))
                cursor.execute(
                    f"SELECT id_lista_produccion, codigo_movimiento_opt FROM {tbl} "
                    f"WHERE codigo_movimiento_opt IN ({ph_c}) ORDER BY id_lista_produccion",
                    list(cods),
                )
                for r in cursor.fetchall() or []:
                    r_l = _row_dict_lower_keys(r)
                    cod = to_int_or_none(r_l.get("codigo_movimiento_opt"))
                    lid = to_int_or_none(r_l.get("id_lista_produccion"))
                    if cod is not None and lid is not None:
                        members_by_cod.setdefault(int(cod), []).append(int(lid))

            members_by_id_opt: Dict[int, List[int]] = {}
            if id_opts and tiene_id_opt:
                try:
                    ph_o = ",".join(["%s"] * len(id_opts))
                    cursor.execute(
                        f"SELECT id_lista_produccion, id_opt FROM {tbl} "
                        f"WHERE id_opt IN ({ph_o}) ORDER BY id_lista_produccion",
                        list(id_opts),
                    )
                    for r in cursor.fetchall() or []:
                        r_l = _row_dict_lower_keys(r)
                        id_opt = to_int_or_none(r_l.get("id_opt"))
                        lid = to_int_or_none(r_l.get("id_lista_produccion"))
                        if id_opt is not None and lid is not None:
                            members_by_id_opt.setdefault(int(id_opt), []).append(int(lid))
                except Exception:
                    pass

            for lid in ids_in:
                row = row_by_id.get(lid, {})
                cod = to_int_or_none(row.get("codigo_movimiento_opt"))
                if cod is not None and cod != 0:
                    miembros = members_by_cod.get(int(cod))
                    if miembros:
                        result[lid] = sorted(set(miembros))
                        continue
                if tiene_id_opt:
                    id_opt = to_int_or_none(row.get("id_opt"))
                    if id_opt is not None and id_opt != 0:
                        miembros = members_by_id_opt.get(int(id_opt))
                        if miembros:
                            result[lid] = sorted(set(miembros))
    except Exception as e:
        logger.warning(
            "_ids_miembros_grupo_opt_bulk %s: %s", base_empresa, e, exc_info=True
        )
    return result


def _lineas_opt_minimas_bulk(
    base_empresa: str,
    id_listas: List[int],
) -> Dict[int, List[Dict[str, Any]]]:
    """Líneas mínimas indexadas por id_lista_produccion."""
    ids = sorted({int(i) for i in id_listas if i is not None})
    if not ids or not (base_empresa or "").strip():
        return {}
    out: Dict[int, List[Dict[str, Any]]] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl:
                return {}
            ph = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"""
                SELECT id_lista_produccion, id_articulo,
                       COALESCE(cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod
                FROM {tbl}
                WHERE id_lista_produccion IN ({ph})
                """,
                ids,
            )
            for r in cursor.fetchall() or []:
                r_l = _row_dict_lower_keys(r)
                lid = to_int_or_none(r_l.get("id_lista_produccion"))
                if lid is None:
                    continue
                out.setdefault(lid, []).append({
                    "id_lista_produccion": lid,
                    "id_articulo": to_int_or_none(r_l.get("id_articulo")),
                    "cantidad_pendiente_prod": to_int_or_none(r_l.get("cantidad_pendiente_prod")) or 0,
                })
    except Exception as e:
        logger.warning("_lineas_opt_minimas_bulk %s: %s", base_empresa, e, exc_info=True)
    return out


def _lineas_grupo_opt_bulk(
    base_empresa: str,
    id_listas: List[int],
) -> Dict[int, List[Dict[str, Any]]]:
    """Líneas del grupo OPT por cada id_lista de entrada."""
    ids_in = [int(i) for i in id_listas if i is not None]
    if not ids_in:
        return {}
    grupos = _ids_miembros_grupo_opt_bulk(base_empresa, ids_in)
    all_members = sorted({m for members in grupos.values() for m in members})
    lineas_por_id = _lineas_opt_minimas_bulk(base_empresa, all_members)
    result: Dict[int, List[Dict[str, Any]]] = {}
    for id_in in ids_in:
        lineas: List[Dict[str, Any]] = []
        for mid in grupos.get(id_in, [id_in]):
            lineas.extend(lineas_por_id.get(mid, []))
        if not lineas:
            lineas = get_opt_detalle(base_empresa, id_in)
            if not lineas:
                lineas = get_op_detalle(base_empresa, id_in)
        result[id_in] = lineas
    return result


def _stock_deposito_por_articulos(
    base_empresa: str,
    id_deposito: Optional[int],
    id_articulos: List[int],
) -> Dict[int, float]:
    """Saldo en stock_deposito por id_articulo."""
    dep = to_int_or_none(id_deposito)
    ids = sorted({int(i) for i in id_articulos if i is not None})
    if not dep or not ids or not (base_empresa or "").strip():
        return {i: 0.0 for i in ids}
    out: Dict[int, float] = {i: 0.0 for i in ids}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            if not tbl_sd:
                return out
            ph = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"""
                SELECT id_articulo, COALESCE(saldo, 0) AS saldo
                FROM {tbl_sd}
                WHERE id_deposito = %s AND id_articulo IN ({ph})
                """,
                [dep, *ids],
            )
            for rs in cursor.fetchall() or []:
                r_l = _row_dict_lower_keys(rs)
                aid = to_int_or_none(r_l.get("id_articulo"))
                if aid is None:
                    continue
                try:
                    out[int(aid)] = float(r_l.get("saldo") or 0)
                except (TypeError, ValueError):
                    out[int(aid)] = 0.0
    except Exception as e:
        logger.warning("_stock_deposito_por_articulos %s: %s", base_empresa, e, exc_info=True)
    return out


def estado_acciones_opt_bulk(
    base_empresa: str,
    id_listas: List[int],
) -> Dict[int, Dict[str, Any]]:
    """
    Variante batch de estado_acciones_opt para tablero y listados.
    Devuelve {id_lista: {total_pendiente_opp, puede_crear_opp, puede_cerrar}}.
    """
    ids = sorted({int(i) for i in (id_listas or []) if i is not None})
    vacio = _estado_acciones_opt_vacio()
    if not ids or not (base_empresa or "").strip():
        return {}
    try:
        lineas_por_id = _lineas_grupo_opt_bulk(base_empresa, ids)
        deposito_origen = get_deposito_produccion_mpr(base_empresa)

        pendientes_positivos: Dict[int, List[Dict[str, Any]]] = {}
        pack_ids_global: Set[int] = set()
        totales: Dict[int, int] = {}

        for id_lista in ids:
            lineas = lineas_por_id.get(id_lista, [])
            total = sum(int(l.get("cantidad_pendiente_prod") or 0) for l in lineas)
            totales[id_lista] = total
            if total <= 0:
                continue
            pendientes_positivos[id_lista] = lineas
            for linea in lineas:
                qty = int(linea.get("cantidad_pendiente_prod") or 0)
                if qty <= 0:
                    continue
                id_pack = to_int_or_none(linea.get("id_articulo"))
                if id_pack:
                    pack_ids_global.add(int(id_pack))

        abm_map = (
            bulk_id_en_abm(base_empresa, list(pack_ids_global), requiere_ensamblado_si=False)
            if pack_ids_global
            else {}
        )
        bom_cache = (
            bulk_bom_detalle(base_empresa, list(set(abm_map.values())))
            if abm_map
            else {}
        )

        def _explode_con_cache(distribucion):
            agregado: Dict[int, float] = {}
            for linea, qty_pack in distribucion:
                id_pack = to_int_or_none(linea.get("id_articulo"))
                if id_pack is None or qty_pack <= 0:
                    continue
                id_en_abm = abm_map.get(int(id_pack))
                bom = bom_cache.get(id_en_abm) if id_en_abm else None
                if bom and bom.get("componentes"):
                    for comp in bom["componentes"]:
                        id_comp = to_int_or_none(comp.get("id_articulo"))
                        if id_comp is None:
                            continue
                        cant = float(comp.get("cantidad_articulo") or 0) * qty_pack
                        if cant > 0:
                            agregado[int(id_comp)] = agregado.get(int(id_comp), 0) + cant
                else:
                    agregado[int(id_pack)] = agregado.get(int(id_pack), 0) + float(qty_pack)
            return agregado

        agregado_por_opt: Dict[int, Dict[int, float]] = {}
        for id_lista, lineas in pendientes_positivos.items():
            distribucion = [
                (ln, int(ln.get("cantidad_pendiente_prod") or 0))
                for ln in lineas
                if int(ln.get("cantidad_pendiente_prod") or 0) > 0
            ]
            agregado_por_opt[id_lista] = _explode_con_cache(distribucion)

        all_comp_ids = sorted({
            comp
            for ag in agregado_por_opt.values()
            for comp in ag.keys()
        })
        stock_cache = (
            _stock_deposito_por_articulos(base_empresa, deposito_origen, all_comp_ids)
            if deposito_origen and all_comp_ids
            else {}
        )

        out: Dict[int, Dict[str, Any]] = {}
        for id_lista in ids:
            total = totales.get(id_lista, 0)
            puede_cerrar = total == 0
            puede_crear_opp = False
            if total > 0:
                ag = agregado_por_opt.get(id_lista, {})
                if deposito_origen and ag:
                    puede_crear_opp = any(
                        min(float(pend), float(stock_cache.get(int(comp), 0.0))) > 0
                        for comp, pend in ag.items()
                    )
                elif ag:
                    puede_crear_opp = any(float(p) > 0 for p in ag.values())
            out[id_lista] = {
                "total_pendiente_opp": total,
                "puede_crear_opp": puede_crear_opp,
                "puede_cerrar": puede_cerrar,
            }
        return out
    except Exception as e:
        logger.warning(
            "estado_acciones_opt_bulk %s ids=%s: %s",
            base_empresa,
            ids,
            e,
            exc_info=True,
        )
        return {i: dict(vacio) for i in ids}


def estado_acciones_opt(
    base_empresa: str, id_lista_produccion: int
) -> Dict[str, Any]:
    """
    Estado y acciones disponibles para una OPT en proceso.
    Devuelve: total_pendiente_opp, puede_crear_opp, puede_cerrar.
    Usado por el tablero para mostrar el botón principal (Crear OPP o Cerrar).
    Armado 1ra/2da está desacoplado de la OPT (menú Producción).
    """
    out = {
        "total_pendiente_opp": 0,
        "puede_crear_opp": False,
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
        deposito_origen = get_deposito_produccion_mpr(base_empresa)
        componentes_opp = get_opp_componentes_disponibles(
            base_empresa,
            id_lista_produccion,
            deposito_origen,
        )
        hay_disponible_opp = any(
            float(c.get("max_distribuible_unidades") or 0) > 0
            for c in (componentes_opp or [])
        )
        out["puede_crear_opp"] = hay_disponible_opp

        # Cierre OPT: solo pendiente OPP (armado desacoplado de OPT; imputación supervisor aparte).
        out["puede_cerrar"] = total_pendiente_opp == 0
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
    estado: 'Produccion', 'Parcial' (parcialmente producido, queda pendiente) o 'Terminado'.
    """
    if not codigos_movimiento:
        return
    placeholders = ",".join(["%s"] * len(codigos_movimiento))
    if estado == ESTADO_PEDIDO_OPT_TERMINADO:
        cursor.execute(
            f"UPDATE {tbl_cp} SET estado_pedido_opt = %s "
            f"WHERE CodigoMovimiento IN ({placeholders}) AND COALESCE(estado_pedido_opt, '') IN ('Produccion', 'Parcial')",
            [ESTADO_PEDIDO_OPT_TERMINADO] + codigos_movimiento,
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
                f"SELECT codigo_movimiento_opt FROM {tbl} WHERE id_lista_produccion = %s "
                f"AND codigo_movimiento_opt IS NOT NULL AND codigo_movimiento_opt > 0 LIMIT 1",
                [id_lista_produccion],
            )
            row_cod = cursor.fetchone()
            codigo_mov_opt = to_int_or_none(row_cod[0]) if row_cod and row_cod[0] is not None else None
            if _mpr_es_codigo_movimiento_opt_mstock(codigo_mov_opt):
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
    """Cierra la OPT (todas sus líneas). Pendiente total debe ser 0.
    Si hay cantidad pedida no armada, restaura ese restante en agrupada/detalle y deja el pedido en estado 'Parcial'.
    Actualiza comp_ped.estado_pedido_opt: 'Parcial' si queda demanda en lista_produccion_detalle, 'Terminado' si no.
    Actualiza lista_produccion_agrupada (cantidad_pendiente_prod, en_proceso 'No'; limpia placeholder negativo
    en codigo_movimiento_opt si aplica) y movimiento_stock (hora_salida_opt) cuando hay MSTOCK liberado."""
    lineas = get_opt_detalle(base_empresa, id_lista_produccion)
    if not lineas:
        return False, "OPT no encontrada o sin líneas."
    total_pendiente = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
    if total_pendiente > 0:
        return False, "No se puede cerrar la OPT con pendiente mayor a 0. Registre OPP hasta completar."
    id_lista_principal = lineas[0].get("id_lista_produccion")
    cantidades_armadas = get_cantidades_armadas_por_opt(base_empresa, id_lista_principal) if id_lista_principal else {}
    ids_unicos = list({l["id_lista_produccion"] for l in lineas if l.get("id_lista_produccion")})
    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            if not tbl_agrupada:
                conn.rollback()
                raise MprSchemaError("Falta la tabla lista_produccion_agrupada.")
            hora_salida_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            nuevas_listas_restauradas = []
            for linea in lineas:
                id_lista = to_int_or_none(linea.get("id_lista_produccion"))
                id_art = to_int_or_none(linea.get("id_articulo"))
                cantidad_pedida = int(linea.get("cantidad_pedida") or 0)
                cantidad_ya_armada = int(cantidades_armadas.get(id_art, 0))
                cantidad_restante = max(0, cantidad_pedida - cantidad_ya_armada)
                if id_lista is None:
                    continue
                id_lista_detalle_ref = id_lista
                id_lista_nueva = None
                cantidad_restante_para_copia = 0
                # Si hay demanda restaurada (cantidad_restante > 0), crear nueva fila en agrupada para que
                # "Generar OPT" cree una OPT con nuevo número (no reutilice esta id_lista cerrada).
                if cantidad_restante > 0:
                    cantidad_restante_para_copia = cantidad_restante
                    id_lista_nueva = None
                    ins_err_final: Optional[Exception] = None
                    intentos_ins_agr = [
                        (
                            f"INSERT INTO {tbl_agrupada} (id_articulo, cantidad_pedida, cantidad_pendiente_prod, cantidad_fabricada_acumulada, id_usuario, en_proceso_produccion) VALUES (%s, %s, %s, %s, NULL, 'No')",
                            [id_art, cantidad_restante, cantidad_restante, cantidad_ya_armada],
                        ),
                        (
                            f"INSERT INTO {tbl_agrupada} (id_articulo, cantidad_pedida, cantidad_pendiente_prod, id_usuario, en_proceso_produccion) VALUES (%s, %s, %s, NULL, 'No')",
                            [id_art, cantidad_restante, cantidad_restante],
                        ),
                        (
                            f"INSERT INTO {tbl_agrupada} (id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion) VALUES (%s, %s, %s, 'No')",
                            [id_art, cantidad_restante, cantidad_restante],
                        ),
                    ]
                    for sql_ins, vals_ins in intentos_ins_agr:
                        try:
                            cursor.execute(sql_ins, vals_ins)
                            id_lista_nueva = cursor.lastrowid
                            break
                        except Exception as ins_try:
                            ins_err_final = ins_try
                            esq = str(ins_try).lower()
                            if (
                                "1054" not in str(ins_try)
                                and "unknown column" not in esq
                                and "1364" not in str(ins_try)
                            ):
                                conn.rollback()
                                return False, str(ins_try)
                    if id_lista_nueva is None:
                        conn.rollback()
                        return False, str(ins_err_final) if ins_err_final else "INSERT agrupada falló."
                    try:
                        cursor.execute(
                            f"UPDATE {tbl_agrupada} SET cantidad_asignada_opt = %s WHERE id_lista_produccion = %s",
                            [cantidad_restante, id_lista_nueva],
                        )
                    except Exception:
                        pass
                    nuevas_listas_restauradas.append(id_lista_nueva)
                    # Copiar detalle a la nueva lista se hace después de restar lo armado (más abajo), para mantener
                    # ambas OPTs (118 y la nueva) referenciadas al mismo pedido: 118 conserva filas con 0, la nueva con cantidad_restante.
                    cantidad_restante = 0
                try:
                    cursor.execute(
                        f"""
                        UPDATE {tbl_agrupada}
                        SET cantidad_pendiente_prod = %s,
                            en_proceso_produccion = 'No',
                            id_operario_opt = NULL,
                            codigo_movimiento_opt = CASE
                                WHEN codigo_movimiento_opt IS NOT NULL AND codigo_movimiento_opt < 0 THEN NULL
                                ELSE codigo_movimiento_opt
                            END
                        WHERE id_lista_produccion = %s
                        """,
                        [cantidad_restante, id_lista],
                    )
                except Exception as upd_agr:
                    if "1054" in str(upd_agr) or "unknown column" in str(upd_agr).lower():
                        try:
                            cursor.execute(
                                f"UPDATE {tbl_agrupada} SET cantidad_pendiente_prod = %s, en_proceso_produccion = 'No', id_operario_opt = NULL WHERE id_lista_produccion = %s",
                                [cantidad_restante, id_lista],
                            )
                        except Exception as e2:
                            conn.rollback()
                            return False, str(e2)
                    else:
                        conn.rollback()
                        return False, str(upd_agr)
                if tbl_detalle and cantidad_ya_armada > 0:
                    try:
                        cursor.execute(
                            f"SELECT id_lista_detalle, COALESCE(cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod FROM {tbl_detalle} WHERE id_lista_produccion = %s ORDER BY id_lista_detalle",
                            [id_lista_detalle_ref],
                        )
                        detalle_rows = cursor.fetchall()
                    except Exception as col_err:
                        if "1054" in str(col_err) or "id_lista_produccion" in str(col_err).lower() or "id_lista_detalle" in str(col_err).lower():
                            detalle_rows = []
                        else:
                            raise col_err
                    else:
                        detalle_rows = detalle_rows or []
                    remaining_to_subtract = cantidad_ya_armada
                    for d in detalle_rows:
                        if remaining_to_subtract <= 0:
                            break
                        id_det = d[0] if isinstance(d, (list, tuple)) else d.get("id_lista_detalle")
                        raw_qty = d[1] if isinstance(d, (list, tuple)) else d.get("cantidad_pendiente_prod")
                        qty = int(float(raw_qty or 0))
                        subtract = min(qty, remaining_to_subtract)
                        new_qty = max(0, qty - subtract)
                        remaining_to_subtract -= subtract
                        try:
                            cursor.execute(
                                f"UPDATE {tbl_detalle} SET cantidad_pendiente_prod = %s WHERE id_lista_detalle = %s",
                                [new_qty, id_det],
                            )
                        except Exception as ud:
                            logger.debug("No se pudo actualizar lista_produccion_detalle id_lista_detalle=%s: %s", id_det, ud)
                # Después de restar lo armado: copiar detalle a la nueva OPT y poner a 0 el de la cerrada, para que
                # ambas OPTs (la cerrada y la nueva) queden referenciadas al mismo pedido (Ver OPTs por pedido).
                if id_lista_nueva and tbl_detalle and cantidad_restante_para_copia > 0:
                    try:
                        cursor.execute(
                            f"""SELECT codigo_movimiento_pedido, id_articulo, COALESCE(cantidad_pedida, 0), COALESCE(id_usuario, 0)
                                FROM {tbl_detalle} WHERE id_lista_produccion = %s AND id_articulo = %s""",
                            [id_lista, id_art],
                        )
                        detalle_orig = cursor.fetchall()
                    except Exception:
                        detalle_orig = []
                    if detalle_orig:
                        hoy_det = date.today().strftime("%Y-%m-%d")
                        primera_fila = True
                        for d in detalle_orig:
                            cod_ped = to_int_or_none(d[0]) if isinstance(d, (list, tuple)) else to_int_or_none(d.get("codigo_movimiento_pedido"))
                            id_art_det = to_int_or_none(d[1]) if isinstance(d, (list, tuple)) else to_int_or_none(d.get("id_articulo"))
                            cant_pedida = int(d[2]) if isinstance(d, (list, tuple)) else int(d.get("cantidad_pedida") or 0)
                            id_usu = d[3] if isinstance(d, (list, tuple)) else d.get("id_usuario") or 0
                            if cod_ped is None or id_art_det is None:
                                continue
                            qty_nueva = cantidad_restante_para_copia if primera_fila else 0
                            primera_fila = False
                            try:
                                cursor.execute(
                                    f"""INSERT INTO {tbl_detalle}
                                        (codigo_movimiento_pedido, id_articulo, cantidad_pedida, cantidad_pendiente_prod, id_usuario, en_proceso_produccion, Fecha, id_lista_produccion)
                                        VALUES (%s, %s, %s, %s, %s, 'No', %s, %s)""",
                                    [cod_ped, id_art_det, cant_pedida, qty_nueva, id_usu, hoy_det, id_lista_nueva],
                                )
                            except Exception as ins_det:
                                if "1054" in str(ins_det) or "Unknown column" in str(ins_det).lower():
                                    try:
                                        cursor.execute(
                                            f"""INSERT INTO {tbl_detalle}
                                                (codigo_movimiento_pedido, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion, Fecha)
                                                VALUES (%s, %s, %s, %s, 'No', %s)""",
                                            [cod_ped, id_art_det, cant_pedida, qty_nueva, hoy_det],
                                        )
                                        id_det_nuevo = cursor.lastrowid
                                        if id_det_nuevo:
                                            cursor.execute(
                                                f"UPDATE {tbl_detalle} SET id_lista_produccion = %s WHERE id_lista_detalle = %s",
                                                [id_lista_nueva, id_det_nuevo],
                                            )
                                    except Exception as e2:
                                        logger.debug("Fallback INSERT detalle al cerrar OPT: %s", e2)
                                else:
                                    raise ins_det
                        cursor.execute(
                            f"UPDATE {tbl_detalle} SET cantidad_pendiente_prod = 0 WHERE id_lista_produccion = %s AND id_articulo = %s",
                            [id_lista, id_art],
                        )
            codigos_a_estado: Dict[int, str] = {}
            codigos: List[int] = []
            ids_para_codigos = ids_unicos + nuevas_listas_restauradas
            if tbl_detalle and tbl_cp and ids_para_codigos:
                ph = ",".join(["%s"] * len(ids_para_codigos))
                try:
                    cursor.execute(
                        f"SELECT DISTINCT codigo_movimiento_pedido FROM {tbl_detalle} WHERE id_lista_produccion IN ({ph})",
                        ids_para_codigos,
                    )
                    codigos = [
                        c for c in (
                            to_int_or_none(r[0]) for r in cursor.fetchall()
                        ) if c is not None and c != COD_MOV_PEDIDO_DEMANDA_RESERVA
                    ]
                except Exception as e_col:
                    if "1054" in str(e_col) or "id_lista_produccion" in str(e_col).lower():
                        ids_art = [l["id_articulo"] for l in lineas if l.get("id_articulo") is not None]
                        if ids_art:
                            ph_art = ",".join(["%s"] * len(ids_art))
                            cursor.execute(
                                f"SELECT DISTINCT codigo_movimiento_pedido FROM {tbl_detalle} WHERE id_articulo IN ({ph_art})",
                                ids_art,
                            )
                            codigos = [
                                c for c in (
                                    to_int_or_none(r[0]) for r in cursor.fetchall()
                                ) if c is not None and c != COD_MOV_PEDIDO_DEMANDA_RESERVA
                            ]
                    else:
                        raise e_col
                for cod in codigos:
                    try:
                        cursor.execute(
                            f"SELECT COALESCE(SUM(cantidad_pendiente_prod), 0) FROM {tbl_detalle} WHERE codigo_movimiento_pedido = %s",
                            [cod],
                        )
                        row = cursor.fetchone()
                        total_pend_det = int(float(row[0] or 0)) if row else 0
                        codigos_a_estado[cod] = ESTADO_PEDIDO_OPT_PARCIAL if total_pend_det > 0 else ESTADO_PEDIDO_OPT_TERMINADO
                    except Exception:
                        codigos_a_estado[cod] = ESTADO_PEDIDO_OPT_TERMINADO
            for cod, estado in codigos_a_estado.items():
                _actualizar_comp_ped_estado_produccion(cursor, tbl_cp, [cod], estado)
            for id_lista in ids_unicos:
                try:
                    cursor.execute(
                        f"SELECT codigo_movimiento_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s "
                        f"AND codigo_movimiento_opt IS NOT NULL AND codigo_movimiento_opt > 0 LIMIT 1",
                        [id_lista],
                    )
                    row_cod = cursor.fetchone()
                    codigo_mov_opt = to_int_or_none(row_cod[0]) if row_cod and row_cod[0] is not None else None
                    if _mpr_es_codigo_movimiento_opt_mstock(codigo_mov_opt) and tbl_mov:
                        try:
                            cursor.execute(
                                f"UPDATE {tbl_mov} SET hora_salida_opt = %s WHERE codigo_movimiento = %s",
                                [hora_salida_dt, codigo_mov_opt],
                            )
                        except Exception as upd_err:
                            if "1054" in str(upd_err) or "unknown column" in str(upd_err).lower():
                                try:
                                    cursor.execute(
                                        f"UPDATE {tbl_mov} SET hora_salida = %s WHERE codigo_movimiento = %s",
                                        [hora_salida_dt, codigo_mov_opt],
                                    )
                                except Exception:
                                    pass
                            else:
                                logger.warning("No se pudo actualizar hora_salida_opt en movimiento_stock: %s", upd_err)
                except Exception:
                    pass
            conn.commit()
        return True, None
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error al cerrar OPT %s en %s: %s", id_lista_produccion, base_empresa, e, exc_info=True)
        return False, str(e)


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


def _demanda_desde_pedidos_pendientes(
    base_empresa: str,
    limit: int,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    busqueda: Optional[str] = None,
) -> Tuple[Dict[int, Dict[str, Any]], Dict[int, set]]:
    """
    Demanda agregada por artículo desde pedidos PED pendientes (comp_ped + stockp + articulo).
    Mismo criterio que el origen de actualizar_pedidos_produccion: Anulado='No', TipoComprobante='PED',
    estado_pedido_opt IN ('Pendiente','Parcial'), tipo_art_fab='Terminado'.
    Devuelve (by_art: id_articulo -> dict con id_articulo, codigo_articulo, descripcion_articulo, codigo_manual,
    cantidad_pedida, cantidad_pendiente_prod, codigos_pedido), codigos_pedido_por_articulo).
    lista_produccion_detalle se inserta/actualiza al crear la OPT; esta función no depende de ella.
    """
    by_art: Dict[int, Dict[str, Any]] = {}
    codigos_pedido_por_articulo: Dict[int, set] = {}
    if not (base_empresa or "").strip():
        return by_art, codigos_pedido_por_articulo
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_stockp = _nombre_tabla(cursor, "stockp")
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not all([tbl_stockp, tbl_cp, tbl_articulo]):
                return by_art, codigos_pedido_por_articulo
            sql = f"""
                SELECT cp.CodigoMovimiento AS codigo_movimiento_pedido, sp.IDArt AS id_articulo,
                       COALESCE(sp.cantidad, sp.cantidad_pendiente, sp.Cantidad, 0) AS cantidad,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                       COALESCE(a.id_manual, '') AS codigo_manual
                FROM {tbl_stockp} sp
                INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                INNER JOIN {tbl_articulo} a ON a.IDArt = sp.IDArt AND COALESCE(TRIM(a.tipo_art_fab), '') = 'Terminado'
                WHERE COALESCE(cp.Anulado, 'No') = 'No'
                  AND COALESCE(cp.TipoComprobante, '') = 'PED'
            """
            params: List[Any] = []
            try:
                cursor.execute("SHOW COLUMNS FROM {} LIKE %s".format(tbl_cp), ["estado_pedido_opt"])
                if cursor.fetchone():
                    sql += " AND COALESCE(cp.estado_pedido_opt, '') IN ('Pendiente', 'Parcial')"
            except Exception:
                pass
            if fecha_desde:
                sql += " AND cp.Fecha >= %s"
                params.append(to_date_or_none(fecha_desde) or str(fecha_desde)[:10])
            if fecha_hasta:
                sql += " AND cp.Fecha <= %s"
                params.append(to_date_or_none(fecha_hasta) or str(fecha_hasta)[:10])
            if busqueda and busqueda.strip():
                sql += " AND (cp.NroCompBusq LIKE %s OR cp.NroComprobante LIKE %s)"
                pct = "%" + busqueda.strip() + "%"
                params.extend([pct, pct])
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        for r in rows:
            id_art = to_int_or_none(r.get("id_articulo"))
            cod_ped = to_int_or_none(r.get("codigo_movimiento_pedido"))
            try:
                qty = int(float(r.get("cantidad") or 0))
            except (TypeError, ValueError):
                qty = 0
            if id_art is None or qty <= 0:
                continue
            if id_art not in by_art:
                by_art[id_art] = {
                    "id_articulo": id_art,
                    "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                    "codigo_manual": str_codigo_manual_articulo(r.get("codigo_manual")),
                    "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                    "cantidad_pedida": 0,
                    "cantidad_pendiente_prod": 0,
                }
            by_art[id_art]["cantidad_pedida"] += qty
            by_art[id_art]["cantidad_pendiente_prod"] += qty
            if id_art not in codigos_pedido_por_articulo:
                codigos_pedido_por_articulo[id_art] = set()
            if cod_ped is not None:
                codigos_pedido_por_articulo[id_art].add(cod_ped)
        # Limitar por cantidad de artículos
        if len(by_art) > limit:
            ordenados = sorted(by_art.items(), key=lambda x: -x[1]["cantidad_pendiente_prod"])
            by_art = dict(ordenados[:limit])
            codigos_pedido_por_articulo = {k: codigos_pedido_por_articulo[k] for k in by_art if k in codigos_pedido_por_articulo}
        return by_art, codigos_pedido_por_articulo
    except Exception as e:
        logger.warning("Error _demanda_desde_pedidos_pendientes en %s: %s", base_empresa, e, exc_info=True)
        return {}, {}


def _mpr_lista_detalle_tiene_columna_origen_demanda(cursor, tbl_detalle: str) -> bool:
    tq = tbl_detalle.replace("`", "``")
    try:
        cursor.execute(f"SHOW COLUMNS FROM `{tq}` LIKE %s", ["origen_demanda"])
        return cursor.fetchone() is not None
    except Exception:
        return False


def _mpr_columna_pk_fila_lista_produccion_detalle(cursor, tbl_detalle: str) -> str:
    """
    Columna autonumérica que identifica la fila en ``lista_produccion_detalle``.
    Tras la migración MPR de trazabilidad es ``id_lista_detalle``; en bases legacy
    la misma columna puede seguir llamándose ``id_lista_produccion`` (ver
    ``run_mpr_lista_produccion_detalle_trazabilidad_mysql``).
    Si existe una columna ``id_lista_detalle`` no-PK junto a PK ``id_lista_produccion``,
    se usa la PK real del esquema (evita leer FK como fila).
    """
    pk_fisica = columna_primary_key(cursor, tbl_detalle)
    if pk_fisica:
        if es_nombre_logico_id_lista_detalle(pk_fisica):
            return pk_fisica
        pk_norm = re.sub(r"[^a-z0-9]", "", pk_fisica.lower())
        if pk_norm == "idlistaproduccion":
            return pk_fisica
    if columna_existe(cursor, tbl_detalle, "id_lista_detalle"):
        return "id_lista_detalle"
    if columna_existe(cursor, tbl_detalle, "id_lista_produccion"):
        return "id_lista_produccion"
    return "id_lista_detalle"


def _demanda_detalle_pk_columna(cursor, tbl_detalle: str) -> str:
    """PK de fila en lista_produccion_detalle (legacy o migrado)."""
    return _mpr_columna_pk_fila_lista_produccion_detalle(cursor, tbl_detalle)


def _demanda_detalle_pendiente_actual(
    cursor,
    tbl_detalle: str,
    pk_col: str,
    *,
    id_fila: Optional[int] = None,
    codigo_movimiento_pedido: Optional[int] = None,
    id_articulo: Optional[int] = None,
) -> int:
    """Lee pendiente de producción en detalle (por PK de fila o suma pedido+artículo)."""
    if id_fila is not None:
        cursor.execute(
            f"SELECT COALESCE(cantidad_pendiente_prod, 0) FROM `{tbl_detalle}` "
            f"WHERE `{pk_col}` = %s",
            [int(id_fila)],
        )
        row = cursor.fetchone()
        pend_fila = int(float(row[0] or 0)) if row else 0
        if pend_fila > 0:
            return pend_fila
        # id_fila puede ser FK confundida con PK o fila ya consumida: usar suma pedido+artículo
        if codigo_movimiento_pedido is not None and id_articulo is not None:
            cursor.execute(
                f"SELECT COALESCE(SUM(cantidad_pendiente_prod), 0) FROM `{tbl_detalle}` "
                f"WHERE codigo_movimiento_pedido = %s AND id_articulo = %s",
                [int(codigo_movimiento_pedido), int(id_articulo)],
            )
            row_sum = cursor.fetchone()
            return int(float(row_sum[0] or 0)) if row_sum else 0
        return 0
    if codigo_movimiento_pedido is None or id_articulo is None:
        return 0
    cursor.execute(
        f"SELECT COALESCE(SUM(cantidad_pendiente_prod), 0) FROM `{tbl_detalle}` "
        f"WHERE codigo_movimiento_pedido = %s AND id_articulo = %s",
        [int(codigo_movimiento_pedido), int(id_articulo)],
    )
    row = cursor.fetchone()
    return int(float(row[0] or 0)) if row else 0


def _demanda_detalle_decrementar_pendiente(
    cursor,
    tbl_detalle: str,
    pk_col: str,
    cantidad: int,
    *,
    id_fila: Optional[int] = None,
    codigo_movimiento_pedido: Optional[int] = None,
    id_articulo: Optional[int] = None,
) -> None:
    """Reduce cantidad_pendiente_prod en detalle (fila puntual o reparto FIFO por PK)."""
    qty = int(cantidad or 0)
    if qty <= 0:
        return
    if id_fila is not None:
        pend = _demanda_detalle_pendiente_actual(
            cursor, tbl_detalle, pk_col, id_fila=int(id_fila)
        )
        if pend > 0:
            cursor.execute(
                f"UPDATE `{tbl_detalle}` SET cantidad_pendiente_prod = %s "
                f"WHERE `{pk_col}` = %s",
                [max(0, pend - qty), int(id_fila)],
            )
            return
    if codigo_movimiento_pedido is None or id_articulo is None:
        return
    restante = qty
    cursor.execute(
        f"SELECT `{pk_col}`, COALESCE(cantidad_pendiente_prod, 0) AS pend "
        f"FROM `{tbl_detalle}` "
        f"WHERE codigo_movimiento_pedido = %s AND id_articulo = %s "
        f"AND COALESCE(cantidad_pendiente_prod, 0) > 0 "
        f"ORDER BY `{pk_col}`",
        [int(codigo_movimiento_pedido), int(id_articulo)],
    )
    rows = cursor.fetchall() or []
    for row in rows:
        if restante <= 0:
            break
        if isinstance(row, (list, tuple)):
            rid, pend_raw = row[0], row[1]
        else:
            rid = row.get(pk_col)
            pend_raw = row.get("pend")
        pend = int(float(pend_raw or 0))
        if pend <= 0:
            continue
        take = min(restante, pend)
        cursor.execute(
            f"UPDATE `{tbl_detalle}` SET cantidad_pendiente_prod = %s "
            f"WHERE `{pk_col}` = %s",
            [max(0, pend - take), rid],
        )
        restante -= take


def _sincronizar_demanda_reserva_lista_detalle(
    cursor,
    tbl_detalle: str,
    tbl_articulo: str,
    tbl_sd: Optional[str],
    tbl_dep: Optional[str],
    id_usuario_val: int,
    hoy_str: str,
) -> None:
    """
    Mantiene en lista_produccion_detalle una fila por artículo con codigo_movimiento_pedido = 0
    (demanda por quiebre de reserva): cantidad objetivo max(0, R − S), con R = articulo.stock_reserva
    y S = saldo terminado (mismo criterio que ventana OPT: depósitos suma_stock = 'Si').
    Ajusta cantidad_pendiente_prod al cambiar la meta sin pisar avance OPP de forma brusca:
    min(nueva_meta, pendiente_anterior + max(0, nueva_meta − pedida_anterior)).
    """
    tq = tbl_detalle.replace("`", "``")
    ta = tbl_articulo.replace("`", "``")
    pk_detalle = _mpr_columna_pk_fila_lista_produccion_detalle(cursor, tbl_detalle)
    tiene_origen = _mpr_lista_detalle_tiene_columna_origen_demanda(cursor, tbl_detalle)
    # Mismo criterio de fabricación que pedidos PED: solo artículos «terminados»; comparación sin distinguir mayúsculas
    # por datos legacy (p. ej. 'TERMINADO', 'terminado').
    cursor.execute(
        f"""
        SELECT a.IDArt, COALESCE(a.stock_reserva, 0) AS stock_reserva
        FROM `{ta}` a
        WHERE LOWER(COALESCE(TRIM(a.tipo_art_fab), '')) = 'terminado'
          AND COALESCE(a.stock_reserva, 0) > 0
        """
    )
    candidatos = cursor.fetchall() or []
    stock_por_art: Dict[int, float] = {}
    if tbl_sd and tbl_dep:
        ts = tbl_sd.replace("`", "``")
        td = tbl_dep.replace("`", "``")
        try:
            cursor.execute(
                f"""
                SELECT sd.id_articulo, COALESCE(SUM(sd.saldo), 0) AS stock_terminado
                FROM `{ts}` sd
                INNER JOIN `{td}` d ON d.CodDeposito = sd.id_deposito
                  AND COALESCE(d.anulado, 'No') = 'No'
                  AND COALESCE(d.suma_stock, 'Si') = 'Si'
                GROUP BY sd.id_articulo
                """
            )
            for row in cursor.fetchall() or []:
                aid = to_int_or_none(row[0])
                if aid is None:
                    continue
                try:
                    stock_por_art[aid] = float(row[1] or 0)
                except (TypeError, ValueError):
                    stock_por_art[aid] = 0.0
        except Exception:
            stock_por_art = {}
    for row in candidatos:
        try:
            id_art = to_int_or_none(row[0] if not isinstance(row, dict) else row.get("IDArt"))
            if id_art is None:
                continue
            try:
                reserva = float(
                    (row[1] if not isinstance(row, dict) else row.get("stock_reserva")) or 0
                )
            except (TypeError, ValueError):
                reserva = 0.0
            st = float(stock_por_art.get(id_art, 0.0))
            new_q = max(0.0, reserva - st)
            cursor.execute(
                f"""
                SELECT `{pk_detalle}`,
                       COALESCE(cantidad_pedida, 0),
                       COALESCE(cantidad_pendiente_prod, 0)
                FROM `{tq}` d
                WHERE d.codigo_movimiento_pedido = %s
                  AND d.id_articulo = %s
                  AND COALESCE(TRIM(d.en_proceso_produccion), 'No') = 'No'
                LIMIT 1
                """,
                [COD_MOV_PEDIDO_DEMANDA_RESERVA, id_art],
            )
            ex = cursor.fetchone()
            if new_q <= 0:
                if ex:
                    id_det = ex[0]
                    cursor.execute(f"DELETE FROM `{tq}` WHERE `{pk_detalle}` = %s", [id_det])
                continue
            if ex:
                id_det = ex[0]
                try:
                    old_ped = float(ex[1] or 0)
                    old_pend = float(ex[2] or 0)
                except (TypeError, ValueError):
                    old_ped, old_pend = 0.0, 0.0
                new_pend = min(new_q, old_pend + max(0.0, new_q - old_ped))
                new_pend = max(0.0, new_pend)
                if tiene_origen:
                    try:
                        cursor.execute(
                            f"UPDATE `{tq}` SET cantidad_pedida = %s, cantidad_pendiente_prod = %s, origen_demanda = %s WHERE `{pk_detalle}` = %s",
                            [new_q, new_pend, ORIGEN_DEMANDA_RESERVA, id_det],
                        )
                    except Exception as upd_err:
                        if "1054" in str(upd_err) or "unknown column" in str(upd_err).lower():
                            cursor.execute(
                                f"UPDATE `{tq}` SET cantidad_pedida = %s, cantidad_pendiente_prod = %s WHERE `{pk_detalle}` = %s",
                                [new_q, new_pend, id_det],
                            )
                        else:
                            raise upd_err
                else:
                    cursor.execute(
                        f"UPDATE `{tq}` SET cantidad_pedida = %s, cantidad_pendiente_prod = %s WHERE `{pk_detalle}` = %s",
                        [new_q, new_pend, id_det],
                    )
            else:
                try:
                    if tiene_origen:
                        cursor.execute(
                            f"""
                            INSERT INTO `{tq}`
                            (codigo_movimiento_pedido, id_articulo, cantidad_pedida, cantidad_pendiente_prod,
                             id_usuario, en_proceso_produccion, Fecha, origen_demanda)
                            VALUES (%s, %s, %s, %s, %s, 'No', %s, %s)
                            """,
                            [
                                COD_MOV_PEDIDO_DEMANDA_RESERVA,
                                id_art,
                                new_q,
                                new_q,
                                id_usuario_val,
                                hoy_str,
                                ORIGEN_DEMANDA_RESERVA,
                            ],
                        )
                    else:
                        cursor.execute(
                            f"""
                            INSERT INTO `{tq}`
                            (codigo_movimiento_pedido, id_articulo, cantidad_pedida, cantidad_pendiente_prod,
                             id_usuario, en_proceso_produccion, Fecha)
                            VALUES (%s, %s, %s, %s, %s, 'No', %s)
                            """,
                            [
                                COD_MOV_PEDIDO_DEMANDA_RESERVA,
                                id_art,
                                new_q,
                                new_q,
                                id_usuario_val,
                                hoy_str,
                            ],
                        )
                except Exception as ins_err:
                    if "1054" in str(ins_err) or "unknown column" in str(ins_err).lower():
                        cursor.execute(
                            f"""
                            INSERT INTO `{tq}`
                            (codigo_movimiento_pedido, id_articulo, cantidad_pedida, cantidad_pendiente_prod,
                             en_proceso_produccion, Fecha)
                            VALUES (%s, %s, %s, %s, 'No', %s)
                            """,
                            [COD_MOV_PEDIDO_DEMANDA_RESERVA, id_art, new_q, new_q, hoy_str],
                        )
                    else:
                        raise ins_err
        except Exception as e_art:
            id_log = to_int_or_none(row[0] if not isinstance(row, dict) else row.get("IDArt"))
            err_txt = str(e_art).lower()
            if "1452" in str(e_art) or "1216" in str(e_art) or "foreign key" in err_txt:
                logger.error(
                    "MPR demanda reserva: fallo en artículo %s (posible FK codigo_movimiento_pedido → comp_ped; "
                    "ejecute migración «MPR — tabla lista_produccion_detalle» o elimine esa FK). Detalle: %s",
                    id_log,
                    e_art,
                )
            else:
                logger.warning(
                    "MPR demanda reserva: no se pudo sincronizar artículo %s en %s: %s",
                    id_log,
                    tbl_detalle,
                    e_art,
                    exc_info=True,
                )
            continue


def listar_ventana_pack(
    base_empresa: str,
    limit: int = 200,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    *,
    modo_ligero: bool = False,
) -> List[Dict[str, Any]]:
    """
    Orden de Producción de Trabajo (OPT): artículos con demanda de producción desde lista_produccion_agrupada
    (cantidad_pendiente_prod > 0, en_proceso_produccion='No'; excluye filas con codigo_movimiento_opt > 0 = OPT ya liberada),
    stock terminado (depósitos suma_stock='Si') y cantidad a fabricar.
    Solo devuelve filas con cantidad_a_fabricar > 0: si el saldo cubre pedido + reserva maestra, la demanda
    para producir está satisfecha y el artículo no se muestra en ventana-pack.
    La demanda depende de que se haya ejecutado actualizar_pedidos_produccion (o al crear la OPT).
    pedidos_resumen se arma desde lista_produccion_detalle + comp_ped (códigos de pedido distintos de 0);
    la demanda por reserva (detalle con codigo_movimiento_pedido = 0) aparece como fila sintética en el tooltip.
    P_ped = suma de cantidad_pedida en detalle con código de pedido ≠ 0; Q_res = fila código 0; R = articulo.stock_reserva;
    cantidad_a_fabricar = max(0, P_ped + R − S); urgente = max(0, P_ped − S) (la reserva no suma a urgente).
    Docenas (cantidad_a_fabricar_docenas / cantidad_urgente_docenas): unidades / articulo.cantidad_promedio_bulto
    (si bulto ≤ 0 o ausente, divisor 12).
    Devuelve: id_articulo, codigo_articulo, descripcion_articulo, cantidad_pedida (total agrupada), cantidad_pedida_pedido,
    cantidad_demanda_reserva, cantidad_pendiente_prod, cantidad_parcial_fabricada, stock_terminado,
    cantidad_a_fabricar, cantidad_urgente_abs, origen_demanda_etiqueta, pedidos_resumen.
    """
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_cli = _nombre_tabla(cursor, "cliente")
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")

            if not tbl_agrupada or not tbl_articulo:
                return []

            opts = _columnas_opcionales_op_agrupada(cursor, tbl_agrupada)
            has_fabricada_col = bool(opts.get("cantidad_fabricada_acumulada"))

            by_art = _ventana_pack_by_art_desde_agrupada(
                cursor,
                tbl_agrupada,
                tbl_articulo,
                opts,
                limit,
                fecha_desde,
                fecha_hasta,
            )
            if not by_art:
                return []

            ids = list(by_art.keys())
            split_p_ped, split_q_res = _ventana_pack_pp_ped_q_res(cursor, tbl_detalle, ids)

            stock_map: Dict[int, float] = {}
            detalle_por_art: Dict[int, List[Dict[str, Any]]] = {}
            if tbl_sd and tbl_dep:
                stock_map, detalle_por_art = _ventana_pack_stock_maps(
                    cursor,
                    tbl_sd,
                    tbl_dep,
                    ids,
                    incluir_detalle=not modo_ligero,
                )

            reserva_map: Dict[int, float] = {}
            art_um_pres_map: Dict[int, Dict[str, Any]] = {}
            if tbl_articulo and ids:
                placeholders = ",".join(["%s"] * len(ids))
                try:
                    bulto_sql = _fragmento_sql_cantidad_promedio_bulto(cursor, tbl_articulo)
                    cursor.execute(
                        f"""SELECT IDArt, COALESCE(stock_reserva, 0) AS stock_reserva,
                                   id_unimed, id_presentacionV, COALESCE(multiplicador_vta, 0) AS multiplicador_vta,
                                   id_en_abm{bulto_sql}
                            FROM {tbl_articulo} WHERE IDArt IN ({placeholders})""",
                        ids,
                    )
                    for r in cursor.fetchall() or []:
                        aid = to_int_or_none(r.get("IDArt"))
                        if aid is None:
                            continue
                        try:
                            reserva_map[aid] = float(r.get("stock_reserva") or 0)
                        except (TypeError, ValueError):
                            reserva_map[aid] = 0.0
                        try:
                            mult = float(r.get("multiplicador_vta") or 0)
                        except (TypeError, ValueError):
                            mult = 0.0
                        try:
                            bulto = float(r.get("cantidad_promedio_bulto") or 0)
                        except (TypeError, ValueError):
                            bulto = 0.0
                        art_um_pres_map[aid] = {
                            "id_unimed": r.get("id_unimed"),
                            "id_presentacionV": r.get("id_presentacionV"),
                            "multiplicador_vta": mult,
                            "id_en_abm": r.get("id_en_abm"),
                            "cantidad_promedio_bulto": bulto,
                        }
                except Exception:
                    pass

            for id_art, row in by_art.items():
                st = stock_map.get(id_art, 0.0)
                reserva = reserva_map.get(id_art, 0.0)
                p_ped = float(split_p_ped.get(id_art, 0.0))
                q_res = float(split_q_res.get(id_art, 0.0))
                cant_pedida = float(row.get("cantidad_pedida") or 0)
                cant_pend = float(row.get("cantidad_pendiente_prod") or 0)
                fab_acum = float(row.get("cantidad_fabricada_acumulada") or 0)
                row["cantidad_pedida_pedido"] = p_ped
                row["cantidad_demanda_reserva"] = q_res
                if has_fabricada_col:
                    row["cantidad_parcial_fabricada"] = max(0.0, fab_acum)
                else:
                    row["cantidad_parcial_fabricada"] = max(0.0, cant_pedida - cant_pend)
                row["stock_terminado"] = st
                row["stock_reserva"] = reserva
                row["cantidad_a_fabricar"] = max(0.0, p_ped + reserva - st)
                row["cantidad_urgente_abs"] = max(0.0, p_ped - st)
                row["cantidad_urgente"] = row["cantidad_urgente_abs"]
                row["origen_demanda_etiqueta"] = _etiqueta_origen_demanda_desde_split(p_ped, q_res)

            con_brecha = [
                r for r in by_art.values() if float(r.get("cantidad_a_fabricar") or 0) > 0
            ]
            filas_final = sorted(con_brecha, key=lambda x: -x["cantidad_a_fabricar"])[:limit]
            if not filas_final:
                return []

            ids_final = [to_int_or_none(r.get("id_articulo")) for r in filas_final]
            ids_final = [x for x in ids_final if x is not None]

            pedidos_por_articulo: Dict[int, List[Dict[str, Any]]] = {aid: [] for aid in ids_final}
            if not modo_ligero:
                pedidos_por_articulo = _ventana_pack_pedidos_resumen(
                    cursor,
                    tbl_detalle,
                    tbl_cp,
                    tbl_cli,
                    ids_final,
                    {aid: split_q_res.get(aid, 0.0) for aid in ids_final},
                )

            unimed_map: Dict[Any, str] = {}
            bom_cache: Dict[Any, Any] = {}
            pres_map: Dict[Any, str] = {}
            if not modo_ligero:
                tbl_um = _nombre_tabla(cursor, "unidmed")
                if tbl_um and art_um_pres_map:
                    id_unimeds = list({
                        v["id_unimed"]
                        for aid, v in art_um_pres_map.items()
                        if aid in ids_final and v.get("id_unimed") is not None
                    })
                    if id_unimeds:
                        try:
                            ph_um = ",".join(["%s"] * len(id_unimeds))
                            cursor.execute(
                                f"SELECT id_unimed, COALESCE(nombre_unimed, '') AS nombre_unimed "
                                f"FROM {tbl_um} WHERE id_unimed IN ({ph_um})",
                                id_unimeds,
                            )
                            for r in cursor.fetchall() or []:
                                uid = r.get("id_unimed")
                                if uid is not None:
                                    unimed_map[uid] = str_or_default(r.get("nombre_unimed"), "-")
                        except Exception:
                            pass
                id_en_abm_set = [
                    to_int_or_none(art_um_pres_map[aid].get("id_en_abm"))
                    for aid in ids_final
                    if aid in art_um_pres_map and art_um_pres_map[aid].get("id_en_abm") is not None
                ]
                id_en_abm_set = [x for x in id_en_abm_set if x is not None]
                if id_en_abm_set:
                    bom_cache = _bulk_bom_detalle_con_cursor(cursor, id_en_abm_set)
                tbl_pres = _nombre_tabla(cursor, "presentacion_abm")
                if tbl_pres and art_um_pres_map:
                    id_pres = list({
                        v["id_presentacionV"]
                        for aid, v in art_um_pres_map.items()
                        if aid in ids_final and v.get("id_presentacionV") is not None
                    })
                    if id_pres:
                        try:
                            ph_pres = ",".join(["%s"] * len(id_pres))
                            cursor.execute(
                                f"SELECT id_presentacion, COALESCE(nombre_presentacion, '') AS nombre_presentacion "
                                f"FROM {tbl_pres} WHERE id_presentacion IN ({ph_pres})",
                                id_pres,
                            )
                            for r in cursor.fetchall() or []:
                                pid = r.get("id_presentacion")
                                if pid is not None:
                                    pres_map[pid] = str_or_default(r.get("nombre_presentacion"), "-")
                        except Exception:
                            pass

            for row in filas_final:
                id_art = to_int_or_none(row.get("id_articulo"))
                if id_art is None:
                    continue
                st = float(row.get("stock_terminado") or 0)
                reserva = float(row.get("stock_reserva") or 0)
                row["pedidos_resumen"] = pedidos_por_articulo.get(id_art) or []
                row["stock"] = st
                row["brecha_reserva"] = reserva - st
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
                try:
                    bulto_pack = float(ap.get("cantidad_promedio_bulto") or 0)
                except (TypeError, ValueError):
                    bulto_pack = 0.0
                row["cantidad_promedio_bulto"] = bulto_pack
                row["cantidad_a_fabricar_docenas"] = docenas_desde_unidades_opt(
                    row["cantidad_a_fabricar"], bulto_pack
                )
                row["cantidad_urgente_docenas"] = docenas_desde_unidades_opt(
                    row["cantidad_urgente_abs"], bulto_pack
                )
                if modo_ligero:
                    row["nombre_unimed"] = "-"
                    row["nombre_presentacion"] = "-"
                    row["cantidad_presentacion"] = None
                    row["receta_json"] = json.dumps([])
                    row["detalle_stock_depositos"] = []
                    row["total_stock_detalle"] = st
                    row["disponible_detalle"] = st
                    row["detalle_stock_depositos_json"] = json.dumps({
                        "filas": [],
                        "total": st,
                        "disponible": st,
                        "reserva": reserva,
                    })
                else:
                    id_en_abm = ap.get("id_en_abm")
                    bom = bom_cache.get(to_int_or_none(id_en_abm)) if id_en_abm is not None else None
                    if bom and bom.get("componentes"):
                        receta = [
                            {
                                "articulo": (
                                    str_or_default(c.get("codigo_articulo"), "-")
                                    + " — "
                                    + str_or_default(c.get("descripcion_articulo"), "-")
                                ),
                                "cantidad": float(c.get("cantidad_articulo") or 0),
                            }
                            for c in bom["componentes"]
                        ]
                    else:
                        receta = []
                    row["receta_json"] = json.dumps(receta)
                    detalle = detalle_por_art.get(id_art) or []
                    total_raw = sum(d.get("stock_terminado", 0) for d in detalle)
                    row["detalle_stock_depositos"] = detalle
                    row["total_stock_detalle"] = total_raw
                    row["disponible_detalle"] = total_raw
                    row["detalle_stock_depositos_json"] = json.dumps({
                        "filas": detalle,
                        "total": total_raw,
                        "disponible": total_raw,
                        "reserva": reserva,
                    })

            return filas_final
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error al listar ventana pack en %s: %s", base_empresa, e, exc_info=True)
        return []


def _listar_unidades_por_demanda(
    base_empresa: str,
    demanda_pedido: Dict[int, float],
    demanda_reserva_pack: Dict[int, float],
    limit: int = 200,
    *,
    restar_saldo_semi_en_cant_fabricar: bool = True,
) -> List[Dict[str, Any]]:
    """
    Desglose por unidades (BOM): demanda en dos vectores (pedido vs reserva del pack terminado),
    saldo **solo** del depósito configurado como ``tipo_mpr=SemiElaborado``.

    No se usa ``articulo.stock_reserva`` del componente (colchón solo en pack terminado).
    Docenas: unidades / ``cantidad_promedio_bulto`` (÷ 12 si bulto ≤ 0).

    Si ``restar_saldo_semi_en_cant_fabricar`` es False (pantalla Confirmar OPT tras Continuar),
    ``cantidad_a_fabricar`` por fila es la demanda bruta ``dem_ped + dem_res`` (sin restar saldo Semi),
    para que los valores editables reflejen lo elegido en ventana-pack/BOM; la columna Urgente sigue
    usando la brecha frente al saldo en Semi elaborado.
    """
    all_ids = set(demanda_pedido.keys()) | set(demanda_reserva_pack.keys())
    if not all_ids:
        return []

    def _tot(i: int) -> float:
        try:
            return float(demanda_pedido.get(i, 0) or 0) + float(demanda_reserva_pack.get(i, 0) or 0)
        except (TypeError, ValueError):
            return 0.0

    ids = sorted(all_ids, key=lambda i: -_tot(i))[:limit]
    placeholders = ",".join(["%s"] * len(ids))
    id_semi = get_deposito_semi_elaborado_mpr(base_empresa)
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_sd or not tbl_dep or not tbl_art:
                return []
            stock_map: Dict[int, float] = {}
            detalle_por_art: Dict[int, List[Dict[str, Any]]] = {}
            if id_semi is None:
                for ia in ids:
                    stock_map[ia] = 0.0
                    detalle_por_art[ia] = [{
                        "deposito": "(Sin depósito Semi elaborado — configurar en MPR)",
                        "stock_terminado": 0.0,
                    }]
            else:
                cursor.execute(
                    f"""
                    SELECT sd.id_articulo, COALESCE(SUM(sd.saldo), 0) AS stock_terminado
                    FROM {tbl_sd} sd
                    INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
                      AND COALESCE(d.anulado, 'No') = 'No'
                    WHERE sd.id_articulo IN ({placeholders})
                      AND sd.id_deposito = %s
                    GROUP BY sd.id_articulo
                    """,
                    tuple(ids) + (id_semi,),
                )
                for row in cursor.fetchall() or []:
                    id_art = to_int_or_none(row.get("id_articulo"))
                    if id_art is not None:
                        try:
                            stock_map[id_art] = float(row.get("stock_terminado") or 0)
                        except (TypeError, ValueError):
                            stock_map[id_art] = 0.0
                for ia in ids:
                    stock_map.setdefault(ia, 0.0)
                try:
                    cursor.execute(
                        f"""
                        SELECT sd.id_articulo,
                               COALESCE(d.NombreDeposito, CAST(d.CodDeposito AS CHAR), '') AS deposito,
                               COALESCE(sd.saldo, 0) AS stock_terminado
                        FROM {tbl_sd} sd
                        INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
                          AND COALESCE(d.anulado, 'No') = 'No'
                        WHERE sd.id_articulo IN ({placeholders})
                          AND sd.id_deposito = %s
                        ORDER BY sd.id_articulo, d.NombreDeposito, d.CodDeposito
                        """,
                        tuple(ids) + (id_semi,),
                    )
                    for row in cursor.fetchall() or []:
                        id_art = to_int_or_none(row.get("id_articulo"))
                        if id_art is None:
                            continue
                        detalle_por_art.setdefault(id_art, [])
                        try:
                            saldo = float(row.get("stock_terminado") or 0)
                        except (TypeError, ValueError):
                            saldo = 0.0
                        detalle_por_art[id_art].append({
                            "deposito": str_or_default(row.get("deposito"), "-"),
                            "stock_terminado": saldo,
                        })
                except Exception:
                    for ia in ids:
                        detalle_por_art.setdefault(ia, [])
            bulto_sel_u = _fragmento_sql_cantidad_promedio_bulto(cursor, tbl_art)
            cursor.execute(
                f"""SELECT IDArt AS id_articulo,
                           COALESCE(id_manual, '') AS codigo_manual,
                           COALESCE(NombreArticulo, '') AS descripcion_articulo,
                           COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo_articulo,
                           COALESCE(stock_reserva, 0) AS stock_reserva,
                           id_unimed, id_presentacionV AS id_presentacionv,
                           COALESCE(multiplicador_vta, 0) AS multiplicador_vta{bulto_sel_u}
                    FROM {tbl_art} WHERE IDArt IN ({placeholders})""",
                ids,
            )
            art_rows: Dict[int, Dict[str, Any]] = {}
            for r in cursor.fetchall() or []:
                d = _row_dict_lower_keys(r)
                rid = to_int_or_none(d.get("id_articulo"))
                if rid is not None:
                    art_rows[rid] = d
            tbl_um = _nombre_tabla(cursor, "unidmed")
            unimed_map: Dict[Any, str] = {}
            id_unimeds = list(
                {to_int_or_none(r.get("id_unimed")) for r in art_rows.values() if r.get("id_unimed") is not None}
            )
            id_unimeds = [x for x in id_unimeds if x is not None]
            if tbl_um and id_unimeds:
                ph = ",".join(["%s"] * len(id_unimeds))
                try:
                    cursor.execute(
                        f"SELECT id_unimed, COALESCE(nombre_unimed, '') AS nombre_unimed FROM {tbl_um} WHERE id_unimed IN ({ph})",
                        id_unimeds,
                    )
                    for r in cursor.fetchall():
                        uid = r.get("id_unimed")
                        if uid is not None:
                            unimed_map[uid] = str_or_default(r.get("nombre_unimed"), "-")
                except Exception:
                    pass
            tbl_pres = _nombre_tabla(cursor, "presentacion_abm")
            pres_map: Dict[Any, str] = {}
            id_pres = list(
                {r.get("id_presentacionv") for r in art_rows.values() if r.get("id_presentacionv") is not None}
            )
            if tbl_pres and id_pres:
                ph = ",".join(["%s"] * len(id_pres))
                try:
                    cursor.execute(
                        f"SELECT id_presentacion, COALESCE(nombre_presentacion, '') AS nombre_presentacion FROM {tbl_pres} WHERE id_presentacion IN ({ph})",
                        id_pres,
                    )
                    for r in cursor.fetchall():
                        pid = r.get("id_presentacion")
                        if pid is not None:
                            pres_map[pid] = str_or_default(r.get("nombre_presentacion"), "-")
                except Exception:
                    pass
            result: List[Dict[str, Any]] = []
            for id_art in ids:
                try:
                    dem_ped = float(demanda_pedido.get(id_art, 0) or 0)
                except (TypeError, ValueError):
                    dem_ped = 0.0
                try:
                    dem_res = float(demanda_reserva_pack.get(id_art, 0) or 0)
                except (TypeError, ValueError):
                    dem_res = 0.0
                dem_total = dem_ped + dem_res
                if dem_ped > 0 and dem_res > 0:
                    origen_u = "Pedido + reserva pack"
                elif dem_res > 0:
                    origen_u = "Reserva pack"
                elif dem_ped > 0:
                    origen_u = "Pedido"
                else:
                    origen_u = "—"
                art = art_rows.get(id_art) or {}
                st = float(stock_map.get(id_art, 0) or 0)
                if restar_saldo_semi_en_cant_fabricar:
                    cant_a_fabricar = max(0.0, dem_total - st)
                else:
                    cant_a_fabricar = max(0.0, dem_total)
                cant_urgente_abs = max(0.0, dem_ped - st)
                cant_urgente = cant_urgente_abs
                id_pres_v = art.get("id_presentacionv")
                mult = float(art.get("multiplicador_vta") or 0)
                cant_presentacion = round(cant_a_fabricar / mult, 2) if mult and mult > 0 else None
                try:
                    bulto_comp = float(art.get("cantidad_promedio_bulto") or 0)
                except (TypeError, ValueError):
                    bulto_comp = 0.0
                detalle = detalle_por_art.get(id_art) or []
                total_raw = sum(float(d.get("stock_terminado") or 0) for d in detalle)
                result.append({
                    "id_articulo": id_art,
                    "codigo_articulo": str_or_default(art.get("codigo_articulo"), "-"),
                    "codigo_manual": str_codigo_manual_articulo(art.get("codigo_manual")),
                    "descripcion_articulo": str_or_default(art.get("descripcion_articulo"), "-"),
                    "cantidad_pedida": dem_total,
                    "cantidad_demanda_pedido": dem_ped,
                    "cantidad_demanda_reserva_pack": dem_res,
                    "origen_demanda_unidades_etiqueta": origen_u,
                    "cantidad_pendiente_prod": dem_total,
                    "stock_terminado": st,
                    "stock_reserva": 0.0,
                    "stock": st,
                    "cantidad_promedio_bulto": bulto_comp,
                    "cantidad_a_fabricar": cant_a_fabricar,
                    "cantidad_urgente": cant_urgente,
                    "cantidad_urgente_abs": cant_urgente_abs,
                    "cantidad_a_fabricar_docenas": docenas_desde_unidades_opt(cant_a_fabricar, bulto_comp),
                    "cantidad_urgente_docenas": docenas_desde_unidades_opt(cant_urgente_abs, bulto_comp),
                    "nombre_unimed": unimed_map.get(art.get("id_unimed"), "-"),
                    "nombre_presentacion": pres_map.get(id_pres_v, "-") if id_pres_v is not None else "-",
                    "cantidad_presentacion": cant_presentacion,
                    "detalle_stock_depositos_json": json.dumps({
                        "filas": detalle,
                        "total": total_raw,
                        "disponible": total_raw,
                        "reserva": 0,
                        "deposito_semi_configurado": id_semi is not None,
                    }, ensure_ascii=False),
                })
            return sorted(result, key=lambda x: -float(x.get("cantidad_a_fabricar") or 0))[:limit]
    except Exception as e:
        logger.warning("Error al listar unidades por demanda en %s: %s", base_empresa, e, exc_info=True)
        return []


def listar_ventana_pack_unidades(
    base_empresa: str,
    limit: int = 200,
    filas_pack: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Desglose por unidades (componentes de las recetas de los packs). Toma los artículos
    de listar_ventana_pack con Cant a producir > 0, explota sus BOM (en_abm_formula),
    particiona demanda por componente en **pedido** vs **reserva del pack terminado**,
    saldo solo en depósito **Semi elaborado** (tipo MPR). Solo lectura, sin checkbox.
    Si se pasa filas_pack (resultado ya calculado de listar_ventana_pack), se reutiliza
    y no se vuelve a llamar a listar_ventana_pack (reduce conexiones MySQL).
    """
    if not (base_empresa or "").strip():
        return []
    if filas_pack is None:
        filas_pack = listar_ventana_pack(base_empresa, limit=limit * 2)
    art_ids = [to_int_or_none(r.get("id_articulo")) for r in filas_pack if (r.get("cantidad_a_fabricar") or 0) > 0]
    art_ids = [a for a in art_ids if a is not None]
    abm_map = bulk_id_en_abm(base_empresa, art_ids, requiere_ensamblado_si=False) if art_ids else {}
    bom_map = bulk_bom_detalle(base_empresa, list(set(abm_map.values()))) if abm_map else {}
    dem_ped, dem_res = _explosion_demanda_componentes_pedido_reserva_pack(filas_pack, abm_map, bom_map)
    return _listar_unidades_por_demanda(base_empresa, dem_ped, dem_res, limit)


def listar_unidades_desde_seleccion(
    base_empresa: str,
    filas: List[Dict[str, Any]],
    limit: int = 200,
    *,
    refresco_pack: Optional[Dict[int, Dict[str, float]]] = None,
) -> List[Dict[str, Any]]:
    """
    Desglose por unidades a partir de la selección de la ventana Confirmar OPT.
    filas: lista de dicts con id_articulo y cantidad_a_fabricar (packs seleccionados).
    Devuelve componentes de las recetas (BOM) con cantidades agregadas.
    Siempre refresca P_ped y stock del pack en MySQL (solo los id seleccionados).
    """
    if not (base_empresa or "").strip() or not filas:
        return []
    art_ids_sel = [
        to_int_or_none(f.get("id_articulo"))
        for f in filas
        if to_int_or_none(f.get("id_articulo")) is not None
    ]
    if refresco_pack is None:
        refresco = obtener_pp_ped_y_stock_pack_por_articulos(base_empresa, art_ids_sel)
    else:
        refresco = refresco_pack
    filas_enriquecidas: List[Dict[str, Any]] = []
    for f in filas:
        ff = dict(f)
        aid = to_int_or_none(ff.get("id_articulo"))
        ref = refresco.get(aid) if aid is not None else None
        if ref:
            ff["cantidad_pedida_pedido"] = ref.get("cantidad_pedida_pedido", 0.0)
            ff["stock_terminado"] = ref.get("stock_terminado", 0.0)
        else:
            ff.setdefault(
                "cantidad_pedida_pedido",
                float(ff.get("cantidad_pedida_pedido") or ff.get("cantidad_pedida") or 0),
            )
            ff.setdefault("stock_terminado", float(ff.get("stock_terminado") or 0))
        filas_enriquecidas.append(ff)
    art_ids = [to_int_or_none(f.get("id_articulo")) for f in filas_enriquecidas if float(f.get("cantidad_a_fabricar") or 0) > 0]
    art_ids = [a for a in art_ids if a is not None]
    abm_map = bulk_id_en_abm(base_empresa, art_ids, requiere_ensamblado_si=False) if art_ids else {}
    bom_map = bulk_bom_detalle(base_empresa, list(set(abm_map.values()))) if abm_map else {}
    dem_ped, dem_res = _explosion_demanda_componentes_pedido_reserva_pack(filas_enriquecidas, abm_map, bom_map)
    return _listar_unidades_por_demanda(
        base_empresa,
        dem_ped,
        dem_res,
        limit,
        restar_saldo_semi_en_cant_fabricar=False,
    )


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
    abm_map = bulk_id_en_abm(base_empresa, pack_ids, requiere_ensamblado_si=False) if pack_ids else {}
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


def _mpr_en_proceso_detalle_es_si(val: Any) -> bool:
    """True si la línea de lista_produccion_detalle está en producción (no debe pisarse desde Actualizar)."""
    s = str_or_default(val, "No").strip().lower()
    return s in ("si", "sí", "yes")


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
    Además sincroniza la demanda por reserva (fila detalle con codigo_movimiento_pedido = 0).
    Si no hay pedidos en el rango, la operación sigue siendo correcta y solo aplica la sincronización por reserva.

    Reconciliación (demanda vs pedido modificado antes de crear OPT):
    - Para cada par (pedido, artículo) del origen con cantidad > 0: INSERT si no existe detalle; si existe y
      en_proceso_produccion es pendiente, UPDATE cantidad_pedida / cantidad_pendiente_prod (preserva fabricado
      parcial: pendiente_nuevo = max(0, cantidad_pedido - max(0, pedida_old - pendiente_old))).
    - Elimina líneas de detalle pendientes (en_proceso No, cod_ped <> 0) cuyo pedido está en el alcance del
      SELECT origen pero el par (cod_ped, id_art) ya no aparece con cantidad > 0 (línea borrada o qty 0).
    - No modifica codigo_movimiento_pedido = 0 (demanda por reserva) ni líneas en_proceso Si.
    - Tras SUM por artículo, pone a cero filas de lista_produccion_agrupada pendientes sin filas en detalle.

    Solo escribe en lista_produccion_detalle (INSERT/UPDATE/DELETE selectivo) y lista_produccion_agrupada (INSERT/UPDATE).
    Nunca asigna en_proceso_produccion = 'Si' (eso solo ocurre al crear la OPT con crear_opt_multiples_articulos).
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
            # Solo pedidos pendientes de producción (Pendiente o Parcial: con demanda aún no cubierta)
            try:
                cursor.execute("SHOW COLUMNS FROM {} LIKE %s".format(tbl_cp.replace("`", "`")), ["estado_pedido_opt"])
                if cursor.fetchone():
                    sql_origin += " AND COALESCE(cp.estado_pedido_opt, '') IN ('Pendiente', 'Parcial')"
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
            filas_origen = cursor.fetchall() or []
            hoy = date.today().strftime("%Y-%m-%d")
            id_usuario_val = id_usuario if id_usuario is not None else 0
            # Alcance del SELECT origen: pedidos que entraron en el filtro (fecha/búsqueda). Solo reconciliar huérfanos ahí.
            codigos_scope: Set[int] = set()
            pares_origen: Set[Tuple[int, int]] = set()
            for row in filas_origen:
                cod_ped = to_int_or_none(row[0])
                id_art = to_int_or_none(row[1])
                try:
                    qty_scan = int(float(row[2] or 0))
                except (TypeError, ValueError):
                    qty_scan = 0
                if cod_ped is not None:
                    codigos_scope.add(cod_ped)
                if cod_ped is not None and id_art is not None and qty_scan > 0:
                    pares_origen.add((cod_ped, id_art))
            # 1) lista_produccion_detalle: INSERT o UPDATE desde PED; no modifica cod_ped=0 ni líneas en_proceso Si
            for row in filas_origen:
                cod_ped = to_int_or_none(row[0])
                id_art = to_int_or_none(row[1])
                try:
                    qty = int(float(row[2] or 0))
                except (TypeError, ValueError):
                    qty = 0
                if cod_ped is None or id_art is None or qty <= 0:
                    continue
                ep_val = "No"
                ex = None
                try:
                    cursor.execute(
                        f"""
                        SELECT cantidad_pedida, cantidad_pendiente_prod,
                               COALESCE(NULLIF(TRIM(en_proceso_produccion), ''), 'No')
                        FROM {tbl_detalle}
                        WHERE codigo_movimiento_pedido = %s AND id_articulo = %s
                        LIMIT 1
                        """,
                        [cod_ped, id_art],
                    )
                    ex = cursor.fetchone()
                    if ex is not None and len(ex) > 2:
                        ep_val = ex[2]
                except Exception as sel_err:
                    if "1054" not in str(sel_err):
                        raise sel_err
                    cursor.execute(
                        f"""
                        SELECT cantidad_pedida, cantidad_pendiente_prod
                        FROM {tbl_detalle}
                        WHERE codigo_movimiento_pedido = %s AND id_articulo = %s
                        LIMIT 1
                        """,
                        [cod_ped, id_art],
                    )
                    ex = cursor.fetchone()
                if not ex:
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
                    continue
                try:
                    ped_old = int(float(ex[0] or 0))
                    pend_old = int(float(ex[1] or 0))
                except (TypeError, ValueError):
                    ped_old, pend_old = 0, 0
                if _mpr_en_proceso_detalle_es_si(ep_val):
                    continue
                fab = max(0, ped_old - pend_old)
                ped_new = qty
                pend_new = max(0, ped_new - fab)
                cursor.execute(
                    f"""
                    UPDATE {tbl_detalle}
                    SET cantidad_pedida = %s, cantidad_pendiente_prod = %s
                    WHERE codigo_movimiento_pedido = %s AND id_articulo = %s
                      AND COALESCE(NULLIF(TRIM(en_proceso_produccion), ''), 'No') = 'No'
                    """,
                    [ped_new, pend_new, cod_ped, id_art],
                )
            # 1b) Quitar líneas PED pendientes que ya no están en el origen (mismo alcance de pedidos del SELECT)
            if codigos_scope:
                cod_list = sorted(codigos_scope)
                ph_cod = ",".join(["%s"] * len(cod_list))
                if pares_origen:
                    plist = list(pares_origen)
                    ph_pairs = ",".join(["(%s,%s)"] * len(plist))
                    flat_pairs: List[Any] = []
                    for c_p, a_p in plist:
                        flat_pairs.extend([c_p, a_p])
                    cursor.execute(
                        f"""
                        DELETE FROM {tbl_detalle}
                        WHERE COALESCE(NULLIF(TRIM(en_proceso_produccion), ''), 'No') = 'No'
                          AND codigo_movimiento_pedido <> 0
                          AND codigo_movimiento_pedido IN ({ph_cod})
                          AND (codigo_movimiento_pedido, id_articulo) NOT IN ({ph_pairs})
                        """,
                        cod_list + flat_pairs,
                    )
                else:
                    cursor.execute(
                        f"""
                        DELETE FROM {tbl_detalle}
                        WHERE COALESCE(NULLIF(TRIM(en_proceso_produccion), ''), 'No') = 'No'
                          AND codigo_movimiento_pedido <> 0
                          AND codigo_movimiento_pedido IN ({ph_cod})
                        """,
                        cod_list,
                    )
            tbl_sd_ap = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep_ap = _nombre_tabla(cursor, "deposito")
            try:
                _sincronizar_demanda_reserva_lista_detalle(
                    cursor,
                    tbl_detalle,
                    tbl_articulo,
                    tbl_sd_ap,
                    tbl_dep_ap,
                    id_usuario_val,
                    hoy,
                )
            except Exception as e_res:
                logger.warning("Sincronización demanda por reserva en actualizar_pedidos_produccion (%s): %s", base_empresa, e_res)
            # 2) lista_produccion_agrupada: cantidad_pedida = SUM(detalle.cantidad_pedida);
            #    cantidad_pendiente_prod = SUM(detalle.cantidad_pendiente_prod) (alineado con OPP, no forzar pendiente = pedida).
            cursor.execute(
                f"""
                SELECT id_articulo,
                       COALESCE(SUM(cantidad_pedida), 0) AS total_pedida,
                       COALESCE(SUM(cantidad_pendiente_prod), 0) AS total_pendiente
                FROM {tbl_detalle}
                WHERE COALESCE(NULLIF(TRIM(en_proceso_produccion), ''), 'No') = 'No'
                GROUP BY id_articulo
                """,
            )
            sumas = cursor.fetchall()
            ids_in_sum: Set[int] = set()
            for row in sumas:
                id_art = to_int_or_none(row[0])
                try:
                    total_pedida = int(float(row[1] or 0))
                except (TypeError, ValueError):
                    total_pedida = 0
                try:
                    total_pendiente = int(float(row[2] or 0))
                except (TypeError, ValueError):
                    total_pendiente = 0
                if id_art is None:
                    continue
                ids_in_sum.add(id_art)
                # Solo considerar filas aún no en OPT (en_proceso_produccion = 'No'); no tocar filas ya en producción
                cursor.execute(
                    f"SELECT id_lista_produccion, cantidad_pendiente_prod FROM {tbl_agrupada} WHERE id_articulo = %s AND COALESCE(TRIM(en_proceso_produccion), 'No') = 'No' LIMIT 1",
                    [id_art],
                )
                existente = cursor.fetchone()
                if existente:
                    id_lista = existente[0]
                    # Actualizar pedida agregada y pendiente real desde detalle (tras OPP el pendiente puede ser menor que la pedida).
                    cursor.execute(
                        f"UPDATE {tbl_agrupada} SET cantidad_pedida = %s, cantidad_pendiente_prod = %s WHERE id_lista_produccion = %s AND COALESCE(TRIM(en_proceso_produccion), 'No') = 'No'",
                        [total_pedida, total_pendiente, id_lista],
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
            # 3) Agrupada pendiente sin líneas en detalle (p. ej. solo había demanda PED eliminada en reconciliación)
            cursor.execute(
                f"""
                SELECT id_lista_produccion, id_articulo FROM {tbl_agrupada}
                WHERE COALESCE(TRIM(en_proceso_produccion), 'No') = 'No'
                """,
            )
            for zrow in cursor.fetchall() or []:
                id_lista_z = zrow[0]
                id_art_z = to_int_or_none(zrow[1])
                if id_art_z is None or id_art_z in ids_in_sum:
                    continue
                cursor.execute(
                    f"""
                    UPDATE {tbl_agrupada}
                    SET cantidad_pedida = 0, cantidad_pendiente_prod = 0
                    WHERE id_lista_produccion = %s
                      AND COALESCE(TRIM(en_proceso_produccion), 'No') = 'No'
                    """,
                    [id_lista_z],
                )
            conn.commit()
            partes_msg: List[str] = []
            if filas_origen:
                partes_msg.append(
                    "Se sincronizaron pedidos pendientes con la lista de producción (cantidades, líneas y agrupada)."
                )
            partes_msg.append("Se sincronizó la demanda por reserva de stock.")
            return True, " ".join(partes_msg)
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
    Para tooltip en Pantalla 2 (Orden de Producción de Trabajo OPT agrupar): fecha, nro_pedido, nombre_cliente, cantidad.
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


def _filas_a_op_detalle(rows: List[Any]) -> List[Dict[str, Any]]:
    """Normaliza filas SQL de lista_produccion_agrupada (+ articulo) al dict de detalle OPT."""
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
            "cantidad_asignada_opt": to_int_or_none(r.get("cantidad_asignada_opt")),
            "en_proceso_produccion": str_or_default(r.get("en_proceso_produccion"), "No"),
        }
        row["id_operario_opt"] = to_int_or_none(r.get("id_operario_opt"))
        result.append(row)
    return result


def get_op_detalle_bulk(
    base_empresa: str,
    id_listas: List[int],
) -> List[Dict[str, Any]]:
    """Varias OPT en una sola consulta (evita N+1 en get_opt_detalle agrupada)."""
    ids = [to_int_or_none(x) for x in (id_listas or [])]
    ids = sorted({x for x in ids if x is not None})
    if not (base_empresa or "").strip() or not ids:
        return []
    if len(ids) == 1:
        return get_op_detalle(base_empresa, ids[0])
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl_agrupada:
                return []
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            placeholders = ",".join(["%s"] * len(ids))
            rows = []
            if tbl_articulo:
                sql = f"""
                    SELECT
                        l.id_lista_produccion,
                        l.id_articulo,
                        COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '-') AS codigo_articulo,
                        COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                        COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida,
                        COALESCE(l.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                        COALESCE(l.cantidad_asignada_opt, 0) AS cantidad_asignada_opt,
                        COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion,
                        l.id_operario_opt
                    FROM {tbl_agrupada} l
                    LEFT JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                    WHERE l.id_lista_produccion IN ({placeholders})
                    ORDER BY l.id_lista_produccion, l.id_articulo
                """
                try:
                    cursor.execute(sql, ids)
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
                                COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion,
                                l.id_operario_opt
                            FROM {tbl_agrupada} l
                            LEFT JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                            WHERE l.id_lista_produccion IN ({placeholders})
                            ORDER BY l.id_lista_produccion, l.id_articulo
                        """
                        cursor.execute(sql_fallback, ids)
                        rows = cursor.fetchall()
                    else:
                        raise
            if not rows:
                for sql_agrupada in [
                    f"SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, cantidad_asignada_opt, en_proceso_produccion, id_operario_opt FROM {tbl_agrupada} WHERE id_lista_produccion IN ({placeholders})",
                    f"SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion, id_operario_opt FROM {tbl_agrupada} WHERE id_lista_produccion IN ({placeholders})",
                    f"SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion FROM {tbl_agrupada} WHERE id_lista_produccion IN ({placeholders})",
                ]:
                    try:
                        cursor.execute(sql_agrupada, ids)
                        rows = cursor.fetchall()
                        if rows:
                            break
                    except Exception:
                        continue
        return _filas_a_op_detalle(rows)
    except Exception as e:
        logger.warning(
            "Error al obtener detalle OPT bulk ids=%s en %s: %s",
            ids,
            base_empresa,
            e,
            exc_info=True,
        )
        return []


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
                        COALESCE(l.cantidad_asignada_opt, 0) AS cantidad_asignada_opt,
                        COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion,
                        l.id_operario_opt
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
                                COALESCE(l.en_proceso_produccion, 'No') AS en_proceso_produccion,
                                l.id_operario_opt
                            FROM {tbl_agrupada} l
                            LEFT JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                            WHERE l.id_lista_produccion = %s
                            ORDER BY l.id_articulo
                        """
                        try:
                            cursor.execute(sql_fallback, [id_lista_produccion])
                            rows = cursor.fetchall()
                        except Exception:
                            raise col_err
                    else:
                        raise
            if not rows:
                # Sin articulo o sin filas: intentar solo agrupada (evita 404 tras crear OPT)
                for sql_agrupada in [
                    f"SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, cantidad_asignada_opt, en_proceso_produccion, id_operario_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s",
                    f"SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion, id_operario_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s",
                    f"SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion FROM {tbl_agrupada} WHERE id_lista_produccion = %s",
                ]:
                    try:
                        cursor.execute(sql_agrupada, [id_lista_produccion])
                        rows = cursor.fetchall()
                        if rows:
                            break
                    except Exception:
                        continue
        return _filas_a_op_detalle(rows)
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

    Agrupa por lista_produccion_agrupada.codigo_movimiento_opt (mismo valor en todas las líneas del lote):
    negativo = placeholder (-id_lista_principal) antes de liberar; positivo = CodigoMovimiento MSTOCK tras liberar.
    Compatibilidad: si existe columna id_opt con datos heredados y no hay codigo_movimiento_opt útil, se usa id_opt.
    Si no aplica agrupación, devuelve get_op_detalle (una sola línea).
    """
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl_agrupada:
                return get_op_detalle(base_empresa, id_lista_produccion)
            row = None
            try:
                cursor.execute(
                    f"SELECT codigo_movimiento_opt, id_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                    [id_lista_produccion],
                )
                row = cursor.fetchone()
            except Exception as col_err:
                if "1054" in str(col_err) or "unknown column" in str(col_err).lower():
                    try:
                        cursor.execute(
                            f"SELECT codigo_movimiento_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                            [id_lista_produccion],
                        )
                        row = cursor.fetchone()
                    except Exception as col_err2:
                        if "1054" in str(col_err2) or "unknown column" in str(col_err2).lower():
                            return get_op_detalle(base_empresa, id_lista_produccion)
                        raise col_err2
                else:
                    raise
            row_lower = {str(k).lower(): v for k, v in (row or {}).items()}
            cod = to_int_or_none(row_lower.get("codigo_movimiento_opt"))
            id_opt_legacy = to_int_or_none(row_lower.get("id_opt")) if "id_opt" in row_lower else None
            ids: List[int] = []
            if cod is not None and cod != 0:
                cursor.execute(
                    f"SELECT id_lista_produccion FROM {tbl_agrupada} WHERE codigo_movimiento_opt = %s ORDER BY id_lista_produccion",
                    [cod],
                )
                for r in cursor.fetchall() or []:
                    r_l = {str(k).lower(): v for k, v in (r or {}).items()}
                    lid = to_int_or_none(r_l.get("id_lista_produccion"))
                    if lid is not None:
                        ids.append(lid)
            elif id_opt_legacy is not None and id_opt_legacy != 0:
                try:
                    cursor.execute(
                        f"SELECT id_lista_produccion FROM {tbl_agrupada} WHERE id_opt = %s ORDER BY id_lista_produccion",
                        [id_opt_legacy],
                    )
                    for r in cursor.fetchall() or []:
                        r_l = {str(k).lower(): v for k, v in (r or {}).items()}
                        lid = to_int_or_none(r_l.get("id_lista_produccion"))
                        if lid is not None:
                            ids.append(lid)
                except Exception:
                    ids = []
            if ids:
                result = get_op_detalle_bulk(base_empresa, ids)
                if result:
                    return result
    except Exception as e:
        logger.debug("get_opt_detalle agrupada codigo_movimiento_opt: %s", e)
    return get_op_detalle(base_empresa, id_lista_produccion)


def get_codigo_movimiento_opt(
    base_empresa: str,
    id_lista_produccion: int,
) -> Optional[int]:
    """
    Devuelve el CodigoMovimiento del comprobante MSTOCK de la OPT (para imprimir comprobante).

    Lee codigo_movimiento_opt de lista_produccion_agrupada: solo valores > 0 (MSTOCK real).
    Si la fila tiene placeholder negativo (antes de liberar), devuelve None.
    Compatibilidad heredada: si codigo_movimiento_opt es NULL y existe id_opt, lee la fila principal.
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
                    f"SELECT codigo_movimiento_opt, id_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                    [id_lista_produccion],
                )
                row = cursor.fetchone()
            except Exception as col_err:
                if "1054" in str(col_err) or "unknown column" in str(col_err).lower():
                    try:
                        cursor.execute(
                            f"SELECT codigo_movimiento_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                            [id_lista_produccion],
                        )
                        row = cursor.fetchone()
                    except Exception:
                        return None
                else:
                    raise
            if not row:
                return None
            row = {str(k).lower(): v for k, v in row.items()}
            cod = to_int_or_none(row.get("codigo_movimiento_opt"))
            if _mpr_es_codigo_movimiento_opt_mstock(cod):
                return cod
            if cod is not None and cod < 0:
                return None
            id_opt_legacy = to_int_or_none(row.get("id_opt")) if "id_opt" in row else None
            if id_opt_legacy is not None and id_opt_legacy != id_lista_produccion:
                try:
                    cursor.execute(
                        f"SELECT codigo_movimiento_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                        [id_opt_legacy],
                    )
                    row_p = cursor.fetchone()
                    if row_p:
                        row_p = {str(k).lower(): v for k, v in row_p.items()}
                        cod_p = to_int_or_none(row_p.get("codigo_movimiento_opt"))
                        if _mpr_es_codigo_movimiento_opt_mstock(cod_p):
                            return cod_p
                except Exception:
                    pass
            return None
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
            # Por id_lista_produccion; si no hay filas, por mismo codigo_movimiento_opt que esa lista (lote multi-artículo)
            raw_rows = []
            wheres_params: List[Tuple[str, List[Any]]] = [
                ("id_lista_produccion = %s", [id_lista]),
            ]
            try:
                cursor.execute(
                    f"SELECT codigo_movimiento_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s "
                    f"AND codigo_movimiento_opt IS NOT NULL LIMIT 1",
                    [id_lista],
                )
                rgrp = cursor.fetchone()
                rgrp = {str(k).lower(): v for k, v in (rgrp or {}).items()} if rgrp else {}
                cgrp = to_int_or_none(rgrp.get("codigo_movimiento_opt"))
                if cgrp is not None and cgrp != 0:
                    wheres_params.append(
                        (
                            "codigo_movimiento_opt = %s",
                            [cgrp],
                        )
                    )
            except Exception:
                pass
            try:
                cursor.execute(
                    f"SELECT id_opt FROM {tbl_agrupada} WHERE id_lista_produccion = %s LIMIT 1",
                    [id_lista],
                )
                rleg = cursor.fetchone()
                rleg = {str(k).lower(): v for k, v in (rleg or {}).items()} if rleg else {}
                ido = to_int_or_none(rleg.get("id_opt"))
                if ido is not None and ido != 0:
                    wheres_params.append(("id_opt = %s", [ido]))
            except Exception:
                pass
            for sql_where, params in wheres_params:
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

    Con RequestScopedMysqlMiddleware activo, el resultado se cachea por request
    (base_empresa + id_puesto) para evitar consultas repetidas en la misma vista.
    """
    from mpr.request_scope_cache import (
        get_cached_depositos_con_suma_stock,
        mpr_request_cache_enabled,
        set_cached_depositos_con_suma_stock,
    )

    key = ((base_empresa or "").strip(), id_puesto)
    if mpr_request_cache_enabled():
        cached = get_cached_depositos_con_suma_stock(key)
        if cached is not None:
            return cached

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
    if mpr_request_cache_enabled():
        set_cached_depositos_con_suma_stock(key, depositos)
    return depositos


# Estados de comp_ped.estado_pedido_opt (producción del pedido)
ESTADO_PEDIDO_OPT_PENDIENTE = "Pendiente"
ESTADO_PEDIDO_OPT_PRODUCCION = "Produccion"
ESTADO_PEDIDO_OPT_PARCIAL = "Parcial"  # Cerrada al menos una OPT con pendiente restante
ESTADO_PEDIDO_OPT_TERMINADO = "Terminado"

# Valores válidos para deposito.tipo_mpr (uso MPR por depósito)
TIPO_MPR_PRODUCCION = "Produccion"
TIPO_MPR_SEMI_ELABORADO = "SemiElaborado"
TIPO_MPR_TERMINADO = "Terminado"
TIPO_MPR_SCRAP = "Scrap"
TIPO_MPR_2DA_SELECCION = "2daSeleccion"
TIPO_MPR_PLANCHADO = "Planchado"

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
        validos = (TIPO_MPR_PRODUCCION, TIPO_MPR_SEMI_ELABORADO, TIPO_MPR_TERMINADO, TIPO_MPR_SCRAP, TIPO_MPR_2DA_SELECCION, TIPO_MPR_PLANCHADO)
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
    """Depósito donde se registra el stock al liberar OPT: el que tiene tipo_mpr=Producción en AdministraNET."""
    return _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_PRODUCCION)


def get_deposito_terminado_mpr(base_empresa: str) -> Optional[int]:
    """Devuelve el depósito de terminado (tipo_mpr=Terminado) para destino del armado."""
    return _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_TERMINADO)


def get_deposito_semi_elaborado_mpr(base_empresa: str) -> Optional[int]:
    """Devuelve el depósito semi elaborado (tipo_mpr=SemiElaborado)."""
    return _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_SEMI_ELABORADO)


def get_deposito_desperdicio_mpr(base_empresa: str) -> Optional[int]:
    """Devuelve el depósito desperdicio (tipo_mpr=Scrap). Solo este destino se usa para la sugerencia de reponer."""
    return _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_SCRAP)


def get_deposito_2da_seleccion_mpr(base_empresa: str) -> Optional[int]:
    """Depósito 2.ª selección (tipo_mpr=2daSeleccion), origen típico del armado surtido."""
    return _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_2DA_SELECCION)


def get_deposito_planchado_mpr(base_empresa: str) -> Optional[int]:
    """Depósito de planchado (tipo_mpr=Planchado): etapa de inspección aprobatoria desde Producción."""
    return _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_PLANCHADO)


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


def listar_pedidos_fabrica(
    base_empresa: str,
    limit: int = 100,
    estado: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Lista pedidos de venta (comp_ped) con estado de producción (estado_pedido_opt: Pendiente, Produccion, Parcial, Terminado).
    El filtro opcional estado filtra por estado_pedido_opt.
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
                  AND COALESCE(cp.estado_pedido_opt, '') IN ('Pendiente', 'Produccion', 'Parcial', 'Terminado')
            """
            params = []
            if estado:
                sql += " AND cp.estado_pedido_opt = %s"
                params.append(estado)
            if fecha_desde:
                sql += " AND cp.Fecha >= %s"
                params.append(fecha_desde)
            if fecha_hasta:
                sql += " AND cp.Fecha <= %s"
                params.append(fecha_hasta)
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


def contar_pedidos_fabrica(
    base_empresa: str,
    estado: Optional[str] = None,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> int:
    """Cuenta pedidos PED con estado_pedido_opt (para KPI tablero sin limit=500)."""
    if not (base_empresa or "").strip():
        return 0
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            if not tbl_cp:
                raise MprSchemaError(
                    "Falta la tabla comp_ped en la base de datos. Cree la tabla o verifique el esquema para usar MPR."
                )
            sql = f"""
                SELECT COUNT(*) AS total
                FROM {tbl_cp} cp
                WHERE COALESCE(cp.Anulado, 'No') = 'No'
                  AND COALESCE(cp.TipoComprobante, '') = 'PED'
                  AND COALESCE(cp.estado_pedido_opt, '') IN ('Pendiente', 'Produccion', 'Parcial', 'Terminado')
            """
            params: List[Any] = []
            if estado:
                sql += " AND cp.estado_pedido_opt = %s"
                params.append(estado)
            if fecha_desde:
                sql += " AND cp.Fecha >= %s"
                params.append(fecha_desde)
            if fecha_hasta:
                sql += " AND cp.Fecha <= %s"
                params.append(fecha_hasta)
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return to_int_or_none(row.get("total") if isinstance(row, dict) else None) or 0
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error al contar pedidos fábrica en %s: %s", base_empresa, e, exc_info=True)
        return 0


def listar_opts_por_pedido(
    base_empresa: str,
    codigo_movimiento_pedido: int,
) -> List[Dict[str, Any]]:
    """
    Trazabilidad: OPTs (líneas de lista_produccion) vinculadas a un pedido (comp_ped.CodigoMovimiento).
    Relación: lista_produccion_detalle.codigo_movimiento_pedido → id_lista_produccion → lista_produccion_agrupada.
    Devuelve por cada línea: id_lista_produccion, id_lista_principal (número de OPT = id_lista de la línea principal),
    id_articulo, en_proceso_produccion, cantidad_pedida, cantidad_pendiente_prod.
    id_opt en el dict es alias de id_lista_principal por compatibilidad con plantillas antiguas.
    """
    if not (base_empresa or "").strip() or codigo_movimiento_pedido is None:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl_detalle or not tbl_agrupada:
                return []
            rows = []
            try:
                cursor.execute(
                    f"""
                    SELECT d.id_lista_produccion, d.id_articulo, COALESCE(d.cantidad_pedida, 0) AS cantidad_pedida,
                           COALESCE(d.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                           g.codigo_movimiento_opt, g.id_opt,
                           COALESCE(g.en_proceso_produccion, 'No') AS en_proceso_produccion
                    FROM {tbl_detalle} d
                    INNER JOIN {tbl_agrupada} g ON g.id_lista_produccion = d.id_lista_produccion
                    WHERE d.codigo_movimiento_pedido = %s
                    ORDER BY d.id_lista_produccion
                    """,
                    [codigo_movimiento_pedido],
                )
                rows = cursor.fetchall()
            except Exception as e_col:
                if "1054" in str(e_col) or "unknown column" in str(e_col).lower():
                    try:
                        cursor.execute(
                            f"""
                            SELECT d.id_lista_produccion, d.id_articulo, COALESCE(d.cantidad_pedida, 0) AS cantidad_pedida,
                                   COALESCE(d.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                                   g.codigo_movimiento_opt,
                                   COALESCE(g.en_proceso_produccion, 'No') AS en_proceso_produccion
                            FROM {tbl_detalle} d
                            INNER JOIN {tbl_agrupada} g ON g.id_lista_produccion = d.id_lista_produccion
                            WHERE d.codigo_movimiento_pedido = %s
                            ORDER BY d.id_lista_produccion
                            """,
                            [codigo_movimiento_pedido],
                        )
                        rows = cursor.fetchall()
                    except Exception as e2:
                        if "1054" in str(e2) or "id_lista_produccion" in str(e2).lower():
                            return []
                        raise e2
                elif "id_lista_produccion" in str(e_col).lower():
                    return []
                else:
                    raise e_col
            codigos_pos: Set[int] = set()
            for r in rows or []:
                r = {str(k).lower(): v for k, v in (r or {}).items()}
                c = to_int_or_none(r.get("codigo_movimiento_opt"))
                if _mpr_es_codigo_movimiento_opt_mstock(c):
                    codigos_pos.add(int(c))
            min_por_codigo: Dict[int, int] = {}
            if codigos_pos:
                ph = ",".join(["%s"] * len(codigos_pos))
                try:
                    cursor.execute(
                        f"""
                        SELECT codigo_movimiento_opt, MIN(id_lista_produccion) AS m
                        FROM {tbl_agrupada}
                        WHERE codigo_movimiento_opt IN ({ph})
                        GROUP BY codigo_movimiento_opt
                        """,
                        list(codigos_pos),
                    )
                    for rr in cursor.fetchall() or []:
                        rr = {str(k).lower(): v for k, v in (rr or {}).items()}
                        cc = to_int_or_none(rr.get("codigo_movimiento_opt"))
                        mm = to_int_or_none(rr.get("m"))
                        if cc is not None and mm is not None:
                            min_por_codigo[int(cc)] = int(mm)
                except Exception:
                    pass
            result = []
            for r in rows or []:
                r = {str(k).lower(): v for k, v in (r or {}).items()}
                id_lista_linea = to_int_or_none(r.get("id_lista_produccion"))
                cod = to_int_or_none(r.get("codigo_movimiento_opt"))
                id_opt_legacy = to_int_or_none(r.get("id_opt")) if "id_opt" in r else None
                id_lista_principal: Optional[int] = None
                if id_opt_legacy is not None and id_opt_legacy != 0:
                    id_lista_principal = id_opt_legacy
                elif cod is not None and cod < 0:
                    id_lista_principal = -int(cod)
                elif _mpr_es_codigo_movimiento_opt_mstock(cod) and cod is not None:
                    id_lista_principal = min_por_codigo.get(int(cod), id_lista_linea)
                else:
                    id_lista_principal = id_lista_linea
                result.append({
                    "id_lista_produccion": id_lista_linea,
                    "id_lista_principal": id_lista_principal,
                    "id_opt": id_lista_principal,
                    "id_articulo": to_int_or_none(r.get("id_articulo")),
                    "cantidad_pedida": int(r.get("cantidad_pedida") or 0),
                    "cantidad_pendiente_prod": int(r.get("cantidad_pendiente_prod") or 0),
                    "en_proceso_produccion": str_or_default(r.get("en_proceso_produccion"), "No"),
                })
            return result
    except Exception as e:
        logger.warning("Error al listar OPTs por pedido %s en %s: %s", codigo_movimiento_pedido, base_empresa, e)
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
            item["codigo_manual"] = str_codigo_manual_articulo(r.get("codigo_manual")) if id_art else "-"
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
    bulto_por_pack = bulk_cantidad_promedio_bulto(base_empresa, art_ids)
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
        id_art_pack = to_int_or_none(linea.get("id_articulo"))
        bulto_pack = float(bulto_por_pack.get(id_art_pack, 0) if id_art_pack is not None else 0)
        max_docenas = docenas_enteras_desde_packs(max_packs_armable, bulto_pack)
        result.append({
            "id_articulo": id_art_pack,
            "codigo_articulo": str_or_default(linea.get("codigo_articulo"), "-"),
            "descripcion_articulo": str_or_default(linea.get("descripcion_articulo"), "-"),
            "id_en_abm": item["id_en_abm"],
            "nombre_bom": (bom.get("cabecera") or {}).get("nombre_en_abm") or "-",
            "bom": {"cabecera": bom.get("cabecera"), "componentes": componentes},
            "articulo_armado": item["articulo_armado"],
            "max_packs_armable": max_packs_armable,
            "max_docenas_armable": max_docenas,
            "cantidad_promedio_bulto": bulto_pack,
        })
    return result


def _bom_lineas_para_precarga_armado(
    base_empresa: str,
    id_articulo: int,
    id_en_abm: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Líneas BOM para precargar carrito (1ra): catálogo armado o detalle ABM."""
    lineas = lineas_bom_pack_1ra(base_empresa, int(id_articulo))
    if lineas:
        return [
            {
                "id_articulo": int(bl["id_articulo"]),
                "cantidad_por_pack": int(bl["cantidad_por_pack"]),
                "codigo_articulo": bl.get("codigo_articulo"),
                "descripcion_articulo": bl.get("descripcion_articulo"),
            }
            for bl in lineas
        ]
    id_abm = to_int_or_none(id_en_abm) or get_id_en_abm_por_articulo(
        base_empresa, int(id_articulo)
    )
    if not id_abm:
        return []
    bom = get_bom_detalle(base_empresa, int(id_abm))
    resultado: List[Dict[str, Any]] = []
    for comp in (bom or {}).get("componentes") or []:
        id_c = to_int_or_none(comp.get("id_articulo"))
        qty = int(float(comp.get("cantidad_articulo") or 0))
        if id_c and qty > 0:
            resultado.append({
                "id_articulo": int(id_c),
                "cantidad_por_pack": qty,
                "codigo_articulo": comp.get("codigo_articulo"),
                "descripcion_articulo": comp.get("descripcion_articulo"),
            })
    return resultado


def construir_items_precarga_armado_desde_opt(
    base_empresa: str,
    id_lista: int,
    id_articulo: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Ítems listos para rehidratar el carrito de Armado 1ra desde una OPT.
    Usa la misma lógica de cantidad pendiente que el listado OPT
    (``bulk_restante_armar_opt_listado``), no ``get_lineas_armado_opt`` (más restrictivo).
    """
    if not (base_empresa or "").strip() or id_lista is None:
        return []
    lineas_opt = get_opt_detalle(base_empresa, int(id_lista))
    filtro = to_int_or_none(id_articulo)
    ids_candidatos: List[int] = []
    meta_por_art: Dict[int, Dict[str, Any]] = {}
    for ln in lineas_opt or []:
        id_art = to_int_or_none(ln.get("id_articulo"))
        if id_art is None:
            continue
        if filtro is not None and int(id_art) != int(filtro):
            continue
        ids_candidatos.append(int(id_art))
        meta_por_art[int(id_art)] = ln
    if filtro is not None and int(filtro) not in meta_por_art:
        ids_candidatos.append(int(filtro))
    ids_candidatos = sorted(set(ids_candidatos))
    if not ids_candidatos:
        return []
    abm_map = bulk_id_en_abm(base_empresa, ids_candidatos)
    filas_bulk = [
        {
            "id_lista_produccion": int(id_lista),
            "id_articulo": id_a,
            "cantidad_pendiente_prod": 0,
        }
        for id_a in ids_candidatos
        if abm_map.get(id_a)
    ]
    if not filas_bulk:
        return []
    restante_map = bulk_restante_armar_opt_listado(
        base_empresa, filas_bulk, abm_map
    )
    items: List[Dict[str, Any]] = []
    for f in filas_bulk:
        id_a = int(f["id_articulo"])
        rest = int(restante_map.get(f"{int(id_lista)}:{id_a}", 0) or 0)
        if rest <= 0:
            continue
        bom_lineas = _bom_lineas_para_precarga_armado(
            base_empresa, id_a, abm_map.get(id_a)
        )
        if not bom_lineas:
            continue
        meta = meta_por_art.get(id_a) or {}
        items.append({
            "id_articulo_pack": id_a,
            "codigo_articulo_pack": str_or_default(meta.get("codigo_articulo"), "-"),
            "descripcion_articulo_pack": str_or_default(
                meta.get("descripcion_articulo"), "-"
            ),
            "cantidad_packs": rest,
            "lineas": bom_lineas,
        })
    return items


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


def _equivalentes_pack_desde_bom(
    id_pack: int,
    id_en_abm: Optional[int],
    bom: Optional[Dict[str, Any]],
    componente_cantidades: Dict[int, int],
) -> int:
    """Calcula equivalente en packs a partir de BOM ya cargado (sin queries)."""
    if not id_pack or not componente_cantidades:
        return 0
    if not id_en_abm:
        return int(componente_cantidades.get(id_pack, 0))
    if not bom or not bom.get("componentes"):
        return int(componente_cantidades.get(id_pack, 0))
    min_packs: Optional[float] = None
    for c in bom["componentes"]:
        id_comp = to_int_or_none(c.get("id_articulo"))
        qty_bom = float(c.get("cantidad_articulo") or 0)
        if id_comp is None or qty_bom <= 0:
            continue
        qty_comp = float(componente_cantidades.get(id_comp, 0) or 0)
        packs_this = qty_comp / qty_bom
        if min_packs is None or packs_this < min_packs:
            min_packs = packs_this
    return int(min_packs) if min_packs is not None else 0


def bulk_componentes_a_equivalentes_pack(
    base_empresa: str,
    pack_ids: List[int],
    componente_cantidades: Dict[int, int],
) -> Dict[int, int]:
    """
    Versión bulk de componentes_a_equivalentes_pack: 2 queries (abm + BOM) para N packs.
    """
    if not (base_empresa or "").strip() or not pack_ids or not componente_cantidades:
        return {}
    unique_ids = sorted({x for x in (to_int_or_none(p) for p in pack_ids) if x is not None})
    if not unique_ids:
        return {}
    abm_map = bulk_id_en_abm(base_empresa, unique_ids)
    id_en_abms = [v for v in abm_map.values() if v is not None]
    bom_map = bulk_bom_detalle(base_empresa, id_en_abms) if id_en_abms else {}
    return {
        pid: _equivalentes_pack_desde_bom(
            pid,
            abm_map.get(pid),
            bom_map.get(abm_map.get(pid)) if abm_map.get(pid) else None,
            componente_cantidades,
        )
        for pid in unique_ids
    }


def componentes_a_equivalentes_pack(
    base_empresa: str,
    id_pack: int,
    componente_cantidades: Dict[int, int],
) -> int:
    """
    Convierte cantidades en unidades de componente (medias, etc.) a equivalente en packs
    usando el BOM del pack. Así 3 medias (1 pack = 3 medias) se muestran como 1 pack.

    componente_cantidades: id_componente -> cantidad (unidades de componente).
    Devuelve entero: equivalente en packs (mínimo sobre componentes del BOM: qty_comp / cantidad_articulo).
    """
    if not id_pack or not componente_cantidades:
        return 0
    bulk = bulk_componentes_a_equivalentes_pack(base_empresa, [id_pack], componente_cantidades)
    return bulk.get(id_pack, 0)


def get_cantidad_opp_por_destino_opt(
    base_empresa: str, id_lista_produccion: int
) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, int]]:
    """
    Devuelve por artículo la cantidad de OPP que fue a Semi elaborado, a otros depósitos y solo a desperdicio (Scrap).
    Solo la que va a Semi elaborado es armable. La sugerencia de reponer se muestra solo para unidades a desperdicio.

    Returns:
        (semi_elaborado_por_articulo, otros_por_articulo, desperdicio_por_articulo)
        - semi_elaborado_por_articulo: id_articulo -> cantidad que entró a depósito Semi elaborado
        - otros_por_articulo: id_articulo -> cantidad que entró a otros depósitos (no armable)
        - desperdicio_por_articulo: id_articulo -> cantidad que entró solo al depósito Desperdicio (tipo_mpr=Scrap)
    """
    semi = {}
    otros = {}
    desperdicio = {}
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return semi, otros, desperdicio
    deposito_semi = get_deposito_semi_elaborado_mpr(base_empresa)
    deposito_desperdicio = get_deposito_desperdicio_mpr(base_empresa)
    if deposito_semi is None:
        return semi, otros, desperdicio
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_mov or not tbl_stock:
                return semi, otros, desperdicio
            patron = f"OPT {id_lista_produccion} desde"
            cursor.execute(
                f"""
                SELECT codigo_movimiento FROM {tbl_mov}
                WHERE (UPPER(TRIM(COALESCE(tipo_mov,''))) = 'OPP' OR COALESCE(motivo_movimiento,'') = 'Parte producción')
                  AND INSTR(COALESCE(detalle,''), %s) > 0
                  AND COALESCE(anulado,'No') <> 'Si'
                """,
                [patron],
            )
            rows = cursor.fetchall()
            codigos = [to_int_or_none(r.get("codigo_movimiento")) for r in rows if r.get("codigo_movimiento") is not None]
            codigos = [c for c in codigos if c is not None]
            if not codigos:
                return semi, otros, desperdicio
            placeholders = ",".join(["%s"] * len(codigos))
            cursor.execute(
                f"""
                SELECT IDArt, CodDeposito, COALESCE(SUM(Entrada), 0) AS total
                FROM {tbl_stock}
                WHERE CodigoMovimiento IN ({placeholders}) AND COALESCE(Entrada, 0) > 0
                GROUP BY IDArt, CodDeposito
                """,
                codigos,
            )
            for row in cursor.fetchall():
                id_art = to_int_or_none(row.get("IDArt"))
                cod_dep = to_int_or_none(row.get("CodDeposito"))
                total = int(float(row.get("total") or 0))
                if id_art is None or total <= 0:
                    continue
                if cod_dep == deposito_semi:
                    semi[id_art] = semi.get(id_art, 0) + total
                else:
                    otros[id_art] = otros.get(id_art, 0) + total
                    if deposito_desperdicio is not None and cod_dep == deposito_desperdicio:
                        desperdicio[id_art] = desperdicio.get(id_art, 0) + total
    except Exception as e:
        logger.warning(
            "Error al obtener cantidades OPP por destino para OPT %s en %s: %s",
            id_lista_produccion,
            base_empresa,
            e,
            exc_info=True,
        )
    return semi, otros, desperdicio


def get_cantidad_opp_2da_seleccion_opt(
    base_empresa: str, id_lista_produccion: int
) -> Dict[int, int]:
    """Unidades por artículo enviadas a depósito 2.ª selección vía OPP de esta OPT."""
    resultado: Dict[int, int] = {}
    if not (base_empresa or "").strip() or id_lista_produccion is None:
        return resultado
    deposito_2da = get_deposito_2da_seleccion_mpr(base_empresa)
    if deposito_2da is None:
        return resultado
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_mov or not tbl_stock:
                return resultado
            patron = f"OPT {id_lista_produccion} desde"
            cursor.execute(
                f"""
                SELECT codigo_movimiento FROM {tbl_mov}
                WHERE (UPPER(TRIM(COALESCE(tipo_mov,''))) = 'OPP' OR COALESCE(motivo_movimiento,'') = 'Parte producción')
                  AND INSTR(COALESCE(detalle,''), %s) > 0
                  AND COALESCE(anulado,'No') <> 'Si'
                """,
                [patron],
            )
            codigos = [
                c
                for c in (
                    to_int_or_none(r.get("codigo_movimiento"))
                    for r in (cursor.fetchall() or [])
                )
                if c is not None
            ]
            if not codigos:
                return resultado
            placeholders = ",".join(["%s"] * len(codigos))
            cursor.execute(
                f"""
                SELECT IDArt, COALESCE(SUM(Entrada), 0) AS total
                FROM {tbl_stock}
                WHERE CodigoMovimiento IN ({placeholders})
                  AND CodDeposito = %s
                  AND COALESCE(Entrada, 0) > 0
                GROUP BY IDArt
                """,
                codigos + [deposito_2da],
            )
            for row in cursor.fetchall() or []:
                id_art = to_int_or_none(row.get("IDArt"))
                total = int(float(row.get("total") or 0))
                if id_art is not None and total > 0:
                    resultado[id_art] = resultado.get(id_art, 0) + total
    except Exception as e:
        logger.warning(
            "Error al obtener OPP en 2.ª selección para OPT %s en %s: %s",
            id_lista_produccion,
            base_empresa,
            e,
            exc_info=True,
        )
    return resultado


def opt_puede_armado_surtido(
    base_empresa: str, id_lista_produccion: Optional[int]
) -> Tuple[bool, str]:
    """
    Condiciones para armado surtido vinculado a una OPT (``?id_lista=``):
    al menos una OPP registrada y cantidad > 0 enviada a 2.ª selección.
    Sin ``id_lista`` (acceso desde menú) no aplica el bloqueo.
    """
    if id_lista_produccion is None or int(id_lista_produccion or 0) == 0:
        return True, ""
    if not listar_opp_por_opt(base_empresa, int(id_lista_produccion)):
        return False, "Registre al menos una parte de producción (OPP) en esta OPT."
    if get_deposito_2da_seleccion_mpr(base_empresa) is None:
        return False, "No hay depósito 2.ª selección configurado (tipo_mpr=2daSeleccion)."
    qty_2da = get_cantidad_opp_2da_seleccion_opt(base_empresa, int(id_lista_produccion))
    if sum(qty_2da.values()) <= 0:
        return (
            False,
            "Registre una OPP con envío a 2.ª selección antes de armar surtido.",
        )
    return True, ""


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
            enriquecer_movimientos_opp_presentacion_du(result)
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
    id_operario: Optional[int] = None,
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
                id_op_arm = to_int_or_none(id_operario)
                intentos_m_arm: List[Tuple[str, List[Any]]] = []
                if id_op_arm is not None:
                    intentos_m_arm.append((
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, id_operario_opt)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'No', %s, %s, %s, %s, %s, %s, %s)
                        """,
                        list(params_mov_ins) + [id_op_arm],
                    ))
                intentos_m_arm.append((
                    f"""
                    INSERT INTO {tbl_mov}
                    (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                     detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'No', %s, %s, %s, %s, %s, %s)
                    """,
                    params_mov_ins,
                ))
                intentos_m_arm.append((
                    f"""
                    INSERT INTO {tbl_mov}
                    (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                     detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s)
                    """,
                    params_mov[:13],
                ))
                try:
                    _mpr_ejecutar_insert_intentos(cursor, intentos_m_arm)
                except Exception as ins_err:
                    logger.warning(
                        "ejecutar_armado: error en INSERT movimiento_stock: %s", ins_err, exc_info=True
                    )
                    raise MprSchemaError(formatear_error_esquema(ins_err, "movimiento_stock")) from ins_err
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
                        intentos_sc: List[Tuple[str, List[Any]]] = []
                        if id_en_abm is not None:
                            if id_op_arm is not None:
                                intentos_sc.append((
                                    f"""
                                    INSERT INTO {tbl_stock}
                                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm, id_operario_opt)
                                    VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s, %s)
                                    """,
                                    params_comp_opt_abm + [id_op_arm],
                                ))
                            intentos_sc.append((
                                f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                                """,
                                params_comp_opt_abm,
                            ))
                        if id_op_arm is not None:
                            intentos_sc.append((
                                f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_operario_opt)
                                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
                                """,
                                params_comp + [id_op_arm],
                            ))
                        intentos_sc.append((
                            f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                            """,
                            params_comp,
                        ))
                        _mpr_ejecutar_insert_intentos(cursor, intentos_sc)
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
                                intentos_sl: List[Tuple[str, List[Any]]] = []
                                if id_en_abm is not None:
                                    if id_op_arm is not None:
                                        intentos_sl.append((
                                            f"""
                                            INSERT INTO {tbl_stock}
                                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_lote, codigo_mov_opt, id_en_abm, id_operario_opt)
                                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s, %s, %s)
                                            """,
                                            params_lote_opt_abm + [id_op_arm],
                                        ))
                                    intentos_sl.append((
                                        f"""
                                        INSERT INTO {tbl_stock}
                                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_lote, codigo_mov_opt, id_en_abm)
                                        VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s, %s)
                                        """,
                                        params_lote_opt_abm,
                                    ))
                                if id_op_arm is not None:
                                    intentos_sl.append((
                                        f"""
                                        INSERT INTO {tbl_stock}
                                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_lote, id_operario_opt)
                                        VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                                        """,
                                        params_lote + [id_op_arm],
                                    ))
                                intentos_sl.append((
                                    f"""
                                    INSERT INTO {tbl_stock}
                                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_lote)
                                    VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
                                    """,
                                    params_lote,
                                ))
                                _mpr_ejecutar_insert_intentos(cursor, intentos_sl)
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
                                intentos_snl: List[Tuple[str, List[Any]]] = []
                                if id_en_abm is not None:
                                    if id_op_arm is not None:
                                        intentos_snl.append((
                                            f"""
                                            INSERT INTO {tbl_stock}
                                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm, id_operario_opt)
                                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s, %s)
                                            """,
                                            params_sin_lote_opt_abm + [id_op_arm],
                                        ))
                                    intentos_snl.append((
                                        f"""
                                        INSERT INTO {tbl_stock}
                                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                                        VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                                        """,
                                        params_sin_lote_opt_abm,
                                    ))
                                if id_op_arm is not None:
                                    intentos_snl.append((
                                        f"""
                                        INSERT INTO {tbl_stock}
                                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_operario_opt)
                                        VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
                                        """,
                                        params_sin_lote + [id_op_arm],
                                    ))
                                intentos_snl.append((
                                    f"""
                                    INSERT INTO {tbl_stock}
                                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                    VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                    """,
                                    params_sin_lote,
                                ))
                                _mpr_ejecutar_insert_intentos(cursor, intentos_snl)
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
                intentos_ea: List[Tuple[str, List[Any]]] = []
                if id_en_abm is not None:
                    if id_op_arm is not None:
                        intentos_ea.append((
                            f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm, id_operario_opt)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s, %s)
                            """,
                            params_entrada_arm_opt_abm + [id_op_arm],
                        ))
                    intentos_ea.append((
                        f"""
                        INSERT INTO {tbl_stock}
                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                        VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                        """,
                        params_entrada_arm_opt_abm,
                    ))
                if id_op_arm is not None:
                    intentos_ea.append((
                        f"""
                        INSERT INTO {tbl_stock}
                        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_operario_opt)
                        VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
                        """,
                        params_entrada_arm + [id_op_arm],
                    ))
                intentos_ea.append((
                    f"""
                    INSERT INTO {tbl_stock}
                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                    VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                    """,
                    params_entrada_arm,
                ))
                _mpr_ejecutar_insert_intentos(cursor, intentos_ea)
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
                        id_op_h_arm = to_int_or_none(id_operario)
                        base_opa = [
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
                        ]
                        intentos_opa: List[Tuple[str, List[Any]]] = []
                        if id_op_h_arm is not None:
                            intentos_opa.append((
                                f"""
                                INSERT INTO {tbl_historico}
                                (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                 id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                 nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento, id_operario, id_operario_opt)
                                VALUES (%s, %s, NULL, 0, 0, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                base_opa + [id_op_h_arm, id_op_h_arm],
                            ))
                            intentos_opa.append((
                                f"""
                                INSERT INTO {tbl_historico}
                                (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                 id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                 nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento, id_operario)
                                VALUES (%s, %s, NULL, 0, 0, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s)
                                """,
                                base_opa + [id_op_h_arm],
                            ))
                        intentos_opa.append((
                            f"""
                            INSERT INTO {tbl_historico}
                            (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                             id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                             nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento)
                            VALUES (%s, %s, NULL, 0, 0, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s)
                            """,
                            base_opa,
                        ))
                        _mpr_ejecutar_insert_intentos(cursor, intentos_opa)
                    except Exception as hist_err:
                        logger.warning("No se pudo insertar lista_produccion_historico (OPA): %s", hist_err)
                tbl_detalle_arm = _nombre_tabla(cursor, "lista_produccion_detalle")
                if tbl_detalle_arm and id_lista_produccion is not None and id_art_arm is not None:
                    _update_detalle_id_operario_opt(
                        cursor, tbl_detalle_arm, id_op_arm, int(id_lista_produccion), int(id_art_arm)
                    )
                tbl_agrupada_arm = _nombre_tabla(cursor, "lista_produccion_agrupada")
                id_lp_arm = to_int_or_none(id_lista_produccion)
                if tbl_agrupada_arm and id_lp_arm and id_art_arm is not None:
                    _incrementar_cantidad_fabricada_acumulada_agrupada(
                        cursor,
                        tbl_agrupada_arm,
                        id_lp_arm,
                        int(id_art_arm),
                        int(cantidad_a_armar),
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
            ("cantidad_fabricada_acumulada", "cantidad_fabricada_acumulada"),
            ("codigo_movimiento_opt", "codigo_movimiento_opt"),
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
    fecha_objetivo: Optional[date] = None,
) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Crea una OPT (Pedido de producción) con múltiples artículos.

    No inserta filas nuevas: actualiza las existentes en lista_produccion_agrupada y
    lista_produccion_detalle (en_proceso_produccion = 'Si', codigo_movimiento_opt placeholder,
    id_operario_opt). Todas las líneas del lote comparten el mismo codigo_movimiento_opt negativo
    (-id_lista_principal) hasta liberar; luego Synap guarda el CodigoMovimiento MSTOCK (> 0).
    No se usan mpr_opt/mpr_opt_linea. Requiere columna codigo_movimiento_opt (script MPR OPT).

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
                # Resolver id_lista_produccion existente por artículo (solo filas con en_proceso_produccion = 'No').
                # Ordenar por id_lista_produccion DESC para preferir la fila más reciente (p. ej. la creada al cerrar
                # una OPT con demanda restaurada), así "Generar OPT" crea una OPT con número nuevo y no reutiliza la cerrada.
                for id_articulo, cantidad, id_operario_opt in lineas:
                    cursor.execute(
                        f"""
                        SELECT id_lista_produccion FROM {tbl_agrupada}
                        WHERE id_articulo = %s AND COALESCE(TRIM(en_proceso_produccion), 'No') = 'No'
                        ORDER BY id_lista_produccion DESC LIMIT 1
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
                placeholder_cod = _mpr_codigo_opt_placeholder_desde_principal(id_lista_principal)
                if placeholder_cod is None:
                    conn.rollback()
                    return False, None, "No se pudo calcular el identificador de lote OPT (id_lista_principal)."
                opts = _columnas_opcionales_op_agrupada(cursor, tbl_agrupada)
                usar_fecha = "fecha_objetivo" in opts and fecha_objetivo is not None
                col_fecha = opts.get("fecha_objetivo") if usar_fecha else None
                # Actualizar lista_produccion_agrupada: en_proceso, pendiente, codigo_movimiento_opt (placeholder), operario, cantidad_asignada_opt [, fecha]
                for id_articulo, cantidad, id_lista, id_operario_opt in ids_creados:
                    set_parts = [
                        "en_proceso_produccion = 'Si'",
                        "cantidad_pendiente_prod = %s",
                        "cantidad_asignada_opt = %s",
                        "codigo_movimiento_opt = %s",
                        "id_operario_opt = %s",
                    ]
                    params = [cantidad, cantidad, placeholder_cod, id_operario_opt]
                    if col_fecha and fecha_objetivo is not None:
                        set_parts.append(f"{col_fecha} = %s")
                        params.append(fecha_objetivo)
                    params.append(id_lista)
                    try:
                        cursor.execute(
                            f"UPDATE {tbl_agrupada} SET {', '.join(set_parts)} WHERE id_lista_produccion = %s",
                            params,
                        )
                    except Exception as upd_err:
                        if "1054" in str(upd_err) or "unknown column" in str(upd_err).lower() or "cantidad_asignada_opt" in str(upd_err).lower():
                            set_parts_fb = [
                                "en_proceso_produccion = 'Si'",
                                "cantidad_pendiente_prod = %s",
                                "codigo_movimiento_opt = %s",
                                "id_operario_opt = %s",
                            ]
                            params_fb = [cantidad, placeholder_cod, id_operario_opt]
                            if col_fecha and fecha_objetivo is not None:
                                set_parts_fb.append(f"{col_fecha} = %s")
                                params_fb.append(fecha_objetivo)
                            params_fb.append(id_lista)
                            try:
                                cursor.execute(
                                    f"UPDATE {tbl_agrupada} SET {', '.join(set_parts_fb)} WHERE id_lista_produccion = %s",
                                    params_fb,
                                )
                            except Exception as fallback_err:
                                err_msg = str(fallback_err).lower()
                                if "1054" in str(fallback_err) or "unknown column" in err_msg or "codigo_movimiento_opt" in err_msg or "id_operario_opt" in err_msg:
                                    raise MprSchemaError(
                                        "Faltan columnas codigo_movimiento_opt o id_operario_opt en lista_produccion_agrupada. "
                                        "Ejecute el script docs/mpr/sql/alter_lista_produccion_agrupada_mpr_opt.sql en la base MySQL."
                                    ) from fallback_err
                                logger.warning("No se pudo actualizar lista_produccion_agrupada id_lista=%s: %s", id_lista, fallback_err)
                                return False, None, f"Error al actualizar lista de producción (id_lista={id_lista})."
                        else:
                            raise upd_err
                tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
                if tbl_detalle:
                    for id_articulo, _c, id_lista, id_operario_opt in ids_creados:
                        _update_detalle_id_operario_opt(
                            cursor, tbl_detalle, id_operario_opt, id_lista, id_articulo
                        )
                # Marcar pedidos en producción y lista_produccion_detalle.en_proceso_produccion = 'Si'
                ids_lista_produccion = [lid for _, _, lid, _ in ids_creados]
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
    abm_map = bulk_id_en_abm(base_empresa, pack_ids, requiere_ensamblado_si=False) if pack_ids else {}
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
    id_deposito_origen: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Devuelve la lista de componentes con unidades disponibles para distribuir en OPP.

    Explota los packs de la OPT (get_opt_detalle) × cantidad_pendiente_prod vía BOM;
    agrega por id_articulo componente y devuelve:
      - pendiente_unidades: demanda pendiente por componente en la OPT
      - stock_produccion_unidades: saldo actual en depósito de Producción (si se informa)
      - max_distribuible_unidades: mínimo entre pendiente y stock origen (si se informa)
      - disponible_unidades: alias retrocompatible de pendiente_unidades
    Orden estable por id_articulo.
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
            stock_prod_por_id: Dict[int, float] = {}
            dep_origen = to_int_or_none(id_deposito_origen)
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            if dep_origen and tbl_sd:
                cursor.execute(
                    f"""
                    SELECT id_articulo, COALESCE(saldo, 0) AS saldo
                    FROM {tbl_sd}
                    WHERE id_deposito = %s
                      AND id_articulo IN ({placeholders})
                    """,
                    [dep_origen, *ids],
                )
                for rs in cursor.fetchall() or []:
                    aid = to_int_or_none(rs.get("id_articulo"))
                    if aid is None:
                        continue
                    try:
                        stock_prod_por_id[aid] = float(rs.get("saldo") or 0)
                    except (TypeError, ValueError):
                        stock_prod_por_id[aid] = 0.0
            for id_art in ids:
                codigo, descripcion = art_por_id.get(id_art, (str(id_art), "-"))
                pendiente = float(agregado[id_art] or 0)
                stock_prod = float(stock_prod_por_id.get(id_art, 0.0))
                max_distrib = min(pendiente, stock_prod) if dep_origen else pendiente
                resultado.append({
                    "id_articulo": id_art,
                    "codigo_articulo": codigo,
                    "descripcion_articulo": descripcion,
                    "pendiente_unidades": pendiente,
                    "stock_produccion_unidades": stock_prod,
                    "max_distribuible_unidades": max_distrib,
                    "disponible_unidades": pendiente,
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
                # (4) Etapa 5: el asiento físico en stock_deposito[Produccion] lo realiza
                # registrar_parte_produccion (OPP-parte) vía _registrar_asiento_fisico_opp_parte.
                # ejecutar_liberar_opt conserva SOLO el comprobante MSTOCK OPT y las actualizaciones
                # a lista_produccion_agrupada/historico/detalle.
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
                        id_op_hist = to_int_or_none(linea.get("id_operario_opt"))
                        comps_esta_linea = _explode_packs_to_components(base_empresa, [(linea, qty_pack)])
                        for id_art_comp in sorted(comps_esta_linea.keys()):
                            qty_comp = comps_esta_linea[id_art_comp]
                            if qty_comp <= 0:
                                continue
                            base_hist = [
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
                            ]
                            intentos_hist: List[Tuple[str, List[Any]]] = []
                            if id_op_hist is not None:
                                intentos_hist.append((
                                    f"""
                                    INSERT INTO {tbl_historico}
                                    (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                     id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                     nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento, id_operario, id_operario_opt)
                                    VALUES ('OPT', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    base_hist + [id_op_hist, id_op_hist],
                                ))
                                intentos_hist.append((
                                    f"""
                                    INSERT INTO {tbl_historico}
                                    (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                     id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                     nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento, id_operario)
                                    VALUES ('OPT', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    base_hist + [id_op_hist],
                                ))
                            intentos_hist.append((
                                f"""
                                INSERT INTO {tbl_historico}
                                (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                 id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                 nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento)
                                VALUES ('OPT', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                base_hist,
                            ))
                            try:
                                _mpr_ejecutar_insert_intentos(cursor, intentos_hist)
                            except Exception as hist_err:
                                logger.warning("No se pudo insertar lista_produccion_historico: %s", hist_err)
                tbl_detalle_lib = _nombre_tabla(cursor, "lista_produccion_detalle")
                if tbl_detalle_lib and distribucion:
                    for linea_lb, _qp in distribucion:
                        id_ll = to_int_or_none(linea_lb.get("id_lista_produccion")) or id_lista_produccion
                        id_ap = to_int_or_none(linea_lb.get("id_articulo"))
                        if id_ap is None:
                            continue
                        _update_detalle_id_operario_opt(
                            cursor,
                            tbl_detalle_lib,
                            to_int_or_none(linea_lb.get("id_operario_opt")),
                            id_ll,
                            id_ap,
                        )
                conn.commit()
                # Vincular CodigoMovimiento MSTOCK a todas las líneas del lote OPT (mismo placeholder o misma OPT)
                try:
                    ids_lineas_set: Set[int] = set()
                    ilp = to_int_or_none(id_lista_produccion)
                    if ilp is not None:
                        ids_lineas_set.add(int(ilp))
                    for linea_lb, _qp in distribucion:
                        lid = to_int_or_none((linea_lb or {}).get("id_lista_produccion"))
                        if lid is not None:
                            ids_lineas_set.add(int(lid))
                    ids_lineas = sorted(ids_lineas_set)
                    for lid in ids_lineas:
                        cursor.execute(
                            f"UPDATE {tbl_agrupada} SET codigo_movimiento_opt = %s WHERE id_lista_produccion = %s",
                            [codigo_mov, lid],
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
    DEPRECATED (E6): pendiente eliminación hasta migrar wizard paso 3.
    Usar registrar_parte_produccion / RegistrarParteProduccionView en su lugar.

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
                id_mov_op = (
                    to_int_or_none(distribucion[0][0].get("id_operario_opt"))
                    if distribucion
                    else None
                )
                params_mov = [
                    codigo_mov, nro_comprobante, MOTIVO_OPP_TEXTO, fecha_mov,
                    deposito_origen, deposito_destino, detalle_mov, id_usuario,
                    id_ref_movstock, None, None, None, "OPP", id_pv, nro_comprobante_busq,
                ]
                intentos_mov_opp: List[Tuple[str, List[Any]]] = []
                if id_mov_op is not None:
                    intentos_mov_opp.append((
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq, id_operario_opt)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        list(params_mov) + [id_mov_op],
                    ))
                intentos_mov_opp.append((
                    f"""
                    INSERT INTO {tbl_mov}
                    (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                     detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s)
                    """,
                    params_mov,
                ))
                intentos_mov_opp.append((
                    f"""
                    INSERT INTO {tbl_mov}
                    (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                     detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                    """,
                    params_mov[:14],
                ))
                try:
                    _mpr_ejecutar_insert_intentos(cursor, intentos_mov_opp)
                except Exception as ins_err:
                    raise MprSchemaError(formatear_error_esquema(ins_err, "movimiento_stock")) from ins_err
                # Cargar codigo/descripcion de componentes desde articulo (todas las líneas OPP)
                all_comp_opp: set = set()
                for linea_o, qo in distribucion:
                    if qo <= 0:
                        continue
                    for cid in _explode_packs_to_components(base_empresa, [(linea_o, qo)]).keys():
                        all_comp_opp.add(cid)
                articulo_info_opp: Dict[int, Tuple[str, str]] = {}
                if all_comp_opp and tbl_articulo:
                    ids_comp = list(all_comp_opp)
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
                sql_opp_sal_abm_op = f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm, id_operario_opt)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s, %s)
                            """
                sql_opp_sal_abm = f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                            """
                sql_opp_sal_op = f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_operario_opt)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
                            """
                sql_opp_sal_min = f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                            VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                            """
                sql_opp_ent_abm_op = f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm, id_operario_opt)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s, %s)
                            """
                sql_opp_ent_abm = f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                            """
                sql_opp_ent_op = f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_operario_opt)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
                            """
                sql_opp_ent_min = f"""
                            INSERT INTO {tbl_stock}
                            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                            VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                            """
                for linea, qty_pack in distribucion:
                    if qty_pack <= 0:
                        continue
                    id_op_line = to_int_or_none(linea.get("id_operario_opt"))
                    id_art_pack_linea = to_int_or_none(linea.get("id_articulo"))
                    id_en_abm_linea = (
                        get_id_en_abm_por_articulo(base_empresa, id_art_pack_linea)
                        if id_art_pack_linea is not None
                        else None
                    )
                    comps_line = _explode_packs_to_components(base_empresa, [(linea, qty_pack)])
                    for id_art in sorted(comps_line.keys()):
                        qty = comps_line[id_art]
                        if qty <= 0:
                            continue
                        codigo_art, descripcion_art = articulo_info_opp.get(id_art, ("-", "-"))
                        salida = Decimal(str(qty))
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
                        intentos_sal: List[Tuple[str, List[Any]]] = []
                        if id_en_abm_linea is not None:
                            p_abm = params_salida + [codigo_mov_opt, id_en_abm_linea]
                            if id_op_line is not None:
                                intentos_sal.append((sql_opp_sal_abm_op, p_abm + [id_op_line]))
                            intentos_sal.append((sql_opp_sal_abm, p_abm))
                        if id_op_line is not None:
                            intentos_sal.append((sql_opp_sal_op, params_salida + [id_op_line]))
                        intentos_sal.append((sql_opp_sal_min, params_salida))
                        _mpr_ejecutar_insert_intentos(cursor, intentos_sal)
                        if sd_orig:
                            cursor.execute(
                                f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s",
                                [saldo_orig_despues, sd_orig[0]],
                            )
                        else:
                            cursor.execute(
                                f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                                [id_art, deposito_origen, saldo_orig_despues],
                            )
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
                        intentos_ent: List[Tuple[str, List[Any]]] = []
                        if id_en_abm_linea is not None:
                            p_abm_e = params_entrada + [codigo_mov_opt, id_en_abm_linea]
                            if id_op_line is not None:
                                intentos_ent.append((sql_opp_ent_abm_op, p_abm_e + [id_op_line]))
                            intentos_ent.append((sql_opp_ent_abm, p_abm_e))
                        if id_op_line is not None:
                            intentos_ent.append((sql_opp_ent_op, params_entrada + [id_op_line]))
                        intentos_ent.append((sql_opp_ent_min, params_entrada))
                        _mpr_ejecutar_insert_intentos(cursor, intentos_ent)
                        if sd_dest:
                            cursor.execute(
                                f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s",
                                [saldo_dest_despues, sd_dest[0]],
                            )
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
                        id_op_opp = to_int_or_none(linea.get("id_operario_opt"))
                        comps_esta_linea = _explode_packs_to_components(base_empresa, [(linea, qty)])
                        for id_art_comp in sorted(comps_esta_linea.keys()):
                            qty_comp = comps_esta_linea[id_art_comp]
                            if qty_comp <= 0:
                                continue
                            base_opp = [
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
                            ]
                            intentos_opp_h: List[Tuple[str, List[Any]]] = []
                            if id_op_opp is not None:
                                intentos_opp_h.append((
                                    f"""
                                    INSERT INTO {tbl_historico}
                                    (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                     id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                     nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento, id_operario, id_operario_opt)
                                    VALUES ('OPP', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    base_opp + [id_op_opp, id_op_opp],
                                ))
                                intentos_opp_h.append((
                                    f"""
                                    INSERT INTO {tbl_historico}
                                    (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                     id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                     nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento, id_operario)
                                    VALUES ('OPP', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    base_opp + [id_op_opp],
                                ))
                            intentos_opp_h.append((
                                f"""
                                INSERT INTO {tbl_historico}
                                (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                 id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                 nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento)
                                VALUES ('OPP', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                base_opp,
                            ))
                            try:
                                _mpr_ejecutar_insert_intentos(cursor, intentos_opp_h)
                            except Exception as hist_err:
                                logger.warning("No se pudo insertar lista_produccion_historico (OPP): %s", hist_err)
                tbl_detalle_opp = _nombre_tabla(cursor, "lista_produccion_detalle")
                if tbl_detalle_opp and distribucion:
                    for linea_d, _qd in distribucion:
                        id_ll = to_int_or_none(linea_d.get("id_lista_produccion")) or id_lista_produccion
                        id_ap = to_int_or_none(linea_d.get("id_articulo"))
                        if id_ap is None:
                            continue
                        _update_detalle_id_operario_opt(
                            cursor,
                            tbl_detalle_opp,
                            to_int_or_none(linea_d.get("id_operario_opt")),
                            id_ll,
                            id_ap,
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
    id_operario_por_componente: Optional[Dict[int, int]] = None,
) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    DEPRECATED (E6): pendiente eliminación hasta migrar wizard paso 3.
    Usar registrar_parte_produccion / RegistrarParteProduccionView en su lugar.

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
    id_operario_por_componente = id_operario_por_componente or {}
    for id_c, qty in total_dispatch.items():
        if qty > 0 and to_int_or_none(id_operario_por_componente.get(id_c)) is None:
            return False, None, None, f"Falta operario para el componente {id_c}."
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
                    id_mov_opp_pc = None
                    for _ia, _iq in lista_comp_qty:
                        if _iq <= 0:
                            continue
                        id_mov_opp_pc = to_int_or_none(id_operario_por_componente.get(_ia))
                        if id_mov_opp_pc:
                            break
                    params_mov = [
                        codigo_mov, _formato_nro_comprobante_mstock(id_pv, nro_actual), MOTIVO_OPP_TEXTO, fecha_mov,
                        deposito_origen, deposito_destino, detalle_mov, id_usuario,
                        id_ref_movstock, None, None, None, "OPP", id_pv, nro_comprobante_busq,
                    ]
                    intentos_mov_pc: List[Tuple[str, List[Any]]] = []
                    if id_mov_opp_pc is not None:
                        intentos_mov_pc.append((
                            f"""
                            INSERT INTO {tbl_mov}
                            (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                             detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq, id_operario_opt)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            list(params_mov) + [id_mov_opp_pc],
                        ))
                    intentos_mov_pc.append((
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov,
                    ))
                    intentos_mov_pc.append((
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov[:14],
                    ))
                    try:
                        _mpr_ejecutar_insert_intentos(cursor, intentos_mov_pc)
                    except Exception as ins_err:
                        conn.rollback()
                        raise MprSchemaError(formatear_error_esquema(ins_err, "movimiento_stock")) from ins_err
                    orden = 0
                    sql_pc_sal_abm_op = f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm, id_operario_opt)
                                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s, %s)
                                """
                    sql_pc_sal_abm = f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                                """
                    sql_pc_sal_op = f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_operario_opt)
                                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
                                """
                    sql_pc_sal_min = f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                """
                    sql_pc_ent_abm_op = f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm, id_operario_opt)
                                VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s, %s)
                                """
                    sql_pc_ent_abm = f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, codigo_mov_opt, id_en_abm)
                                VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                                """
                    sql_pc_ent_op = f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_operario_opt)
                                VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
                                """
                    sql_pc_ent_min = f"""
                                INSERT INTO {tbl_stock}
                                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                                VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                                """
                    for id_art, qty in sorted(lista_comp_qty, key=lambda x: (x[0], x[1])):
                        if qty <= 0:
                            continue
                        id_operario_evt = to_int_or_none(id_operario_por_componente.get(id_art))
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
                        params_salida_comp = [
                            codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov, salida, saldo_orig_despues,
                            deposito_origen, id_ref_movstock, orden, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None,
                        ]
                        intentos_sal_pc: List[Tuple[str, List[Any]]] = []
                        if id_en_abm_opp_comp is not None:
                            p_abm_s = params_salida_comp + [codigo_mov_opt, id_en_abm_opp_comp]
                            if id_operario_evt is not None:
                                intentos_sal_pc.append((sql_pc_sal_abm_op, p_abm_s + [id_operario_evt]))
                            intentos_sal_pc.append((sql_pc_sal_abm, p_abm_s))
                        if id_operario_evt is not None:
                            intentos_sal_pc.append((sql_pc_sal_op, params_salida_comp + [id_operario_evt]))
                        intentos_sal_pc.append((sql_pc_sal_min, params_salida_comp))
                        _mpr_ejecutar_insert_intentos(cursor, intentos_sal_pc)
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
                        params_entrada_comp = [
                            codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov, salida, saldo_dest_despues,
                            deposito_destino, id_ref_movstock, orden, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None,
                        ]
                        intentos_ent_pc: List[Tuple[str, List[Any]]] = []
                        if id_en_abm_opp_comp is not None:
                            p_abm_e = params_entrada_comp + [codigo_mov_opt, id_en_abm_opp_comp]
                            if id_operario_evt is not None:
                                intentos_ent_pc.append((sql_pc_ent_abm_op, p_abm_e + [id_operario_evt]))
                            intentos_ent_pc.append((sql_pc_ent_abm, p_abm_e))
                        if id_operario_evt is not None:
                            intentos_ent_pc.append((sql_pc_ent_op, params_entrada_comp + [id_operario_evt]))
                        intentos_ent_pc.append((sql_pc_ent_min, params_entrada_comp))
                        _mpr_ejecutar_insert_intentos(cursor, intentos_ent_pc)
                        if sd_dest:
                            cursor.execute(f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s", [saldo_dest_despues, sd_dest[0]])
                        else:
                            cursor.execute(f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)", [id_art, deposito_destino, saldo_dest_despues])
                        if tbl_historico:
                            try:
                                # 13 placeholders en INSERT mínimo (sin id_operario*); no duplicar fecha/hora.
                                base_hist_pc = [
                                    id_art_pack_opp,
                                    id_art,
                                    qty,
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
                                ]
                                intentos_hpc: List[Tuple[str, List[Any]]] = []
                                if id_operario_evt is not None:
                                    intentos_hpc.append((
                                        f"""
                                        INSERT INTO {tbl_historico}
                                        (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                         id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                         nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento, id_operario, id_operario_opt)
                                        VALUES ('OPP', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """,
                                        base_hist_pc + [id_operario_evt, id_operario_evt],
                                    ))
                                    intentos_hpc.append((
                                        f"""
                                        INSERT INTO {tbl_historico}
                                        (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                         id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                         nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento, id_operario)
                                        VALUES ('OPP', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                        """,
                                        base_hist_pc + [id_operario_evt],
                                    ))
                                intentos_hpc.append((
                                    f"""
                                    INSERT INTO {tbl_historico}
                                    (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                                     id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                                     nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento)
                                    VALUES ('OPP', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                    """,
                                    base_hist_pc,
                                ))
                                _mpr_ejecutar_insert_intentos(cursor, intentos_hpc)
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
                if tbl_detalle and decrements:
                    for id_lista_linea, id_art_pack, _d_p in decrements:
                        id_op_det_pack = None
                        for id_comp, qtd in total_dispatch.items():
                            if qtd <= 0:
                                continue
                            if component_to_pack.get(id_comp) == id_art_pack:
                                id_op_det_pack = to_int_or_none(id_operario_por_componente.get(id_comp))
                                if id_op_det_pack:
                                    break
                        _update_detalle_id_operario_opt(
                            cursor, tbl_detalle, id_op_det_pack, id_lista_linea, id_art_pack
                        )
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


# --- Armado surtido (composición libre, sin BOM) ---

TIPO_ART_FAB_PACK_ARMADO_SURTIDO = "Fabricado 2da"


TIPO_ART_FAB_PACK_ARMADO_SURTIDO = "Fabricado 2da"
LOTE_ARMADO_SURTIDO_MAX_ITEMS = 20


def calcular_demanda_item_lote(item: Dict[str, Any]) -> Dict[int, Decimal]:
    """Demanda de componentes para un ítem del lote: id_articulo → unidades totales."""
    demanda: Dict[int, Decimal] = {}
    cantidad_packs = to_int_or_none(item.get("cantidad_packs")) or 0
    if cantidad_packs < 1:
        return demanda
    for ln in item.get("lineas") or []:
        id_a = to_int_or_none(ln.get("id_articulo"))
        qty_pp = to_int_or_none(ln.get("cantidad_por_pack")) or 0
        if not id_a or qty_pp < 1:
            continue
        total = Decimal(str(qty_pp * cantidad_packs))
        demanda[id_a] = demanda.get(id_a, Decimal(0)) + total
    return demanda


def calcular_demanda_agregada_lote(armados: List[Dict[str, Any]]) -> Dict[int, Decimal]:
    """Suma consumo por componente en todo el lote pendiente."""
    demanda: Dict[int, Decimal] = {}
    for item in armados or []:
        for id_a, qty in calcular_demanda_item_lote(item).items():
            demanda[id_a] = demanda.get(id_a, Decimal(0)) + qty
    return demanda


def _normalizar_lineas_composicion_lote(raw_lineas: Any) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    if not isinstance(raw_lineas, list) or not raw_lineas:
        return [], "Indique al menos un componente en la composición."
    lineas: List[Dict[str, Any]] = []
    for ln in raw_lineas:
        if not isinstance(ln, dict):
            return [], "Composición inválida."
        id_a = to_int_or_none(ln.get("id_articulo"))
        qty = to_int_or_none(ln.get("cantidad_por_pack"))
        if not id_a:
            return [], "Cada línea de composición debe tener un artículo válido."
        if not qty or qty < 1:
            return [], "Cada componente debe tener cantidad por pack ≥ 1."
        lineas.append({"id_articulo": int(id_a), "cantidad_por_pack": int(qty)})
    return lineas, None


def normalizar_item_lote_armado_surtido(raw: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Normaliza un ítem del lote desde JSON/dict."""
    if not isinstance(raw, dict):
        return None, "Ítem de lote inválido."
    id_pack = to_int_or_none(raw.get("id_articulo_pack"))
    cantidad_packs = to_int_or_none(raw.get("cantidad_packs"))
    if not id_pack:
        return None, "Seleccione el pack terminado."
    if not cantidad_packs or cantidad_packs < 1:
        return None, "Indique cantidad de packs (entero ≥ 1)."
    lineas, err_ln = _normalizar_lineas_composicion_lote(raw.get("lineas"))
    if err_ln:
        return None, err_ln
    return {
        "id_articulo_pack": int(id_pack),
        "cantidad_packs": int(cantidad_packs),
        "lineas": lineas,
    }, None


def normalizar_armados_lote_json(data: Any) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
    """Parsea lista de armados desde el objeto JSON del POST (`armados` o lista directa)."""
    if data is None:
        return [], None
    if isinstance(data, list):
        raw_items = data
    elif isinstance(data, dict):
        raw_items = data.get("armados")
        if raw_items is None:
            return None, "Formato de lote inválido: falta clave «armados»."
        if not isinstance(raw_items, list):
            return None, "Formato de lote inválido: «armados» debe ser una lista."
    else:
        return None, "Formato de lote inválido."
    armados: List[Dict[str, Any]] = []
    for raw in raw_items:
        item, err = normalizar_item_lote_armado_surtido(raw)
        if err:
            return None, err
        if item:
            armados.append(item)
    return armados, None


def _normalizar_modo_armado(modo: Optional[str], default: str = "2da") -> str:
    m = str_or_default(modo, default).strip().lower()
    return m if m in ("1ra", "2da") else default


def parse_cabecera_lote_armado_surtido(post: Dict[str, Any]) -> Dict[str, Any]:
    """Cabecera compartida del lote desde campos POST."""
    detalle = str_or_default(post.get("detalle"), "").strip()[:200] or None
    return {
        "deposito_origen": to_int_or_none(post.get("deposito_origen")),
        "deposito_destino": to_int_or_none(post.get("deposito_destino")),
        "id_operario": to_int_or_none(post.get("id_operario")),
        "detalle": detalle,
        "id_lista_produccion": to_int_or_none(post.get("id_lista")),
        "modo": _normalizar_modo_armado(post.get("modo")),
    }


def parse_cabecera_lote_armado(post: Dict[str, Any]) -> Dict[str, Any]:
    """Alias canónico (Armado 1ra/2da unificado)."""
    return parse_cabecera_lote_armado_surtido(post)


def parse_lote_armado_surtido_post(request) -> Tuple[Optional[Dict[str, Any]], Optional[List[Dict[str, Any]]], Optional[str]]:
    """
    Extrae cabecera + armados desde POST (campo lote_json + cabecera HTML).
    Devuelve (cabecera, armados, error).
    """
    import json

    cabecera = parse_cabecera_lote_armado_surtido(request.POST)
    raw_json = (request.POST.get("lote_json") or "").strip()
    if not raw_json:
        return cabecera, None, "Agregue al menos un armado al lote."
    try:
        data = json.loads(raw_json)
    except (TypeError, ValueError, json.JSONDecodeError):
        return cabecera, None, "El lote enviado no tiene un formato JSON válido."
    armados, err = normalizar_armados_lote_json(data)
    if err:
        return cabecera, None, err
    if not armados:
        return cabecera, None, "Agregue al menos un armado al lote."
    return cabecera, armados, None


def validar_reglas_lote_armado_surtido(
    armados: List[Dict[str, Any]],
    *,
    deposito_origen: Optional[int] = None,
    deposito_destino: Optional[int] = None,
    id_operario: Optional[int] = None,
    require_non_empty: bool = True,
) -> Tuple[bool, Optional[str]]:
    """
    Reglas del lote: límite, packs únicos, cruce pack/componente, validación por ítem.
    Si se pasan depósitos y operario, delega validar_datos_armado_surtido por ítem.
    """
    items = list(armados or [])
    if require_non_empty and not items:
        return False, "Agregue al menos un armado al lote."
    if len(items) > LOTE_ARMADO_SURTIDO_MAX_ITEMS:
        return False, f"Máximo {LOTE_ARMADO_SURTIDO_MAX_ITEMS} armados por lote."
    packs_vistos: Set[int] = set()
    todos_packs: Set[int] = set()
    todos_componentes: Set[int] = set()
    for item in items:
        id_pack = to_int_or_none(item.get("id_articulo_pack"))
        if not id_pack:
            return False, "Seleccione el pack terminado."
        if id_pack in packs_vistos:
            return False, "El pack ya está en el lote. Edite la fila existente."
        packs_vistos.add(id_pack)
        todos_packs.add(id_pack)
        lineas = item.get("lineas") or []
        for ln in lineas:
            id_c = to_int_or_none(ln.get("id_articulo"))
            if id_c:
                todos_componentes.add(int(id_c))
        if deposito_origen is not None or deposito_destino is not None or id_operario is not None:
            ok_item, err_item = validar_datos_armado_surtido(
                int(item.get("cantidad_packs") or 0),
                deposito_origen,
                deposito_destino,
                lineas,
                id_operario=id_operario,
                id_articulo_pack=id_pack,
            )
            if not ok_item:
                return False, err_item
    cruce = todos_packs & todos_componentes
    if cruce:
        id_conflicto = sorted(cruce)[0]
        return False, (
            f"El artículo {id_conflicto} no puede ser pack y componente en el mismo lote."
        )
    return True, None


def validar_reglas_lote_armado(
    armados: List[Dict[str, Any]],
    *,
    modo: str = "2da",
    deposito_origen: Optional[int] = None,
    deposito_destino: Optional[int] = None,
    id_operario: Optional[int] = None,
    require_non_empty: bool = True,
    base_empresa: Optional[str] = None,
) -> Tuple[bool, Optional[str]]:
    """Reglas del lote unificado Armado 1ra/2da (modo + reglas comunes)."""
    modo_n = _normalizar_modo_armado(modo)
    be = (base_empresa or "").strip()
    if modo_n == "1ra" and be:
        dep_semi = get_deposito_semi_elaborado_mpr(be)
        if dep_semi and deposito_origen is not None and int(deposito_origen) != int(dep_semi):
            return False, "Armado 1ra: el depósito origen debe ser Semi elaborado."
        for item in armados or []:
            id_pack = to_int_or_none(item.get("id_articulo_pack"))
            if not id_pack:
                continue
            if not articulo_habilitado_armado_1ra(be, int(id_pack)):
                return False, "El pack seleccionado no tiene BOM válido para Armado 1ra."
            ok_bom, err_bom = validar_composicion_bom_1ra(be, int(id_pack), item.get("lineas") or [])
            if not ok_bom:
                return False, err_bom
    elif modo_n == "2da" and be:
        for item in armados or []:
            id_pack = to_int_or_none(item.get("id_articulo_pack"))
            if id_pack and not articulo_habilitado_armado_surtido(be, int(id_pack)):
                return False, (
                    f"El pack seleccionado no tiene tipo_art_fab '{TIPO_ART_FAB_PACK_ARMADO_SURTIDO}'."
                )
    return validar_reglas_lote_armado_surtido(
        armados,
        deposito_origen=deposito_origen,
        deposito_destino=deposito_destino,
        id_operario=id_operario,
        require_non_empty=require_non_empty,
    )


def validar_reglas_item_candidato_lote(
    lote_actual: List[Dict[str, Any]],
    item_candidato: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Valida agregar un ítem al carrito (sin cabecera operario/depósitos)."""
    item, err = normalizar_item_lote_armado_surtido(item_candidato)
    if err or not item:
        return False, err or "Ítem inválido."
    if len(lote_actual or []) >= LOTE_ARMADO_SURTIDO_MAX_ITEMS:
        return False, f"Máximo {LOTE_ARMADO_SURTIDO_MAX_ITEMS} armados por lote."
    id_pack = item["id_articulo_pack"]
    for existente in lote_actual or []:
        if to_int_or_none(existente.get("id_articulo_pack")) == id_pack:
            return False, "El pack ya está en el lote. Edite la fila existente."
    lote_simulado = list(lote_actual or []) + [item]
    return validar_reglas_lote_armado_surtido(lote_simulado, require_non_empty=True)


def validar_datos_armado_surtido(
    cantidad_packs: int,
    deposito_origen: Optional[int],
    deposito_destino: Optional[int],
    lineas_composicion: List[Dict[str, Any]],
    id_operario: Optional[int] = None,
    id_articulo_pack: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """Validaciones previas (sin MySQL). Devuelve (ok, mensaje_error)."""
    if not id_articulo_pack:
        return False, "Seleccione el pack terminado."
    if not cantidad_packs or cantidad_packs < 1:
        return False, "Indique cantidad de packs (entero ≥ 1)."
    if not id_operario:
        return False, "Seleccione operario."
    dep_o = to_int_or_none(deposito_origen)
    dep_d = to_int_or_none(deposito_destino)
    if not dep_o or not dep_d:
        return False, "Indique depósito origen y destino."
    if dep_o == dep_d:
        return False, "Origen y destino deben ser distintos."
    if not lineas_composicion:
        return False, "Indique al menos un componente en la composición."
    vistos: Set[int] = set()
    for ln in lineas_composicion:
        id_a = to_int_or_none(ln.get("id_articulo"))
        qty = to_int_or_none(ln.get("cantidad_por_pack"))
        if not id_a:
            return False, "Cada línea de composición debe tener un artículo válido."
        if id_a in vistos:
            return False, f"El artículo {id_a} está repetido en la composición."
        vistos.add(id_a)
        if not qty or qty < 1:
            return False, "Cada componente debe tener cantidad por pack ≥ 1."
    return True, None


def articulo_habilitado_armado_surtido(base_empresa: str, id_articulo: int) -> bool:
    """True si el pack tiene articulo.tipo_art_fab = 'Fabricado 2da'."""
    id_art = to_int_or_none(id_articulo)
    if not (base_empresa or "").strip() or not id_art:
        return False
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "articulo")
            if not tbl or not columna_existe(cursor, tbl, "tipo_art_fab"):
                return False
            cursor.execute(
                f"""
                SELECT IDArt
                FROM {tbl}
                WHERE IDArt = %s
                  AND COALESCE(TRIM(tipo_art_fab), '') = %s
                LIMIT 1
                """,
                [id_art, TIPO_ART_FAB_PACK_ARMADO_SURTIDO],
            )
            return cursor.fetchone() is not None
    except Exception as e:
        logger.warning("articulo_habilitado_armado_surtido %s: %s", base_empresa, e, exc_info=True)
        return False


def listar_packs_armado_surtido(base_empresa: str) -> List[Dict[str, Any]]:
    """Packs terminados: artículos con articulo.tipo_art_fab = 'Fabricado 2da'."""
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "articulo")
            if not tbl or not columna_existe(cursor, tbl, "tipo_art_fab"):
                return []
            cursor.execute(
                f"""
                SELECT IDArt AS id_articulo,
                       COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(NombreArticulo, '') AS descripcion_articulo
                FROM {tbl}
                WHERE COALESCE(TRIM(tipo_art_fab), '') = %s
                ORDER BY CodigoArticuloT, IDArt
                """,
                [TIPO_ART_FAB_PACK_ARMADO_SURTIDO],
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
        logger.warning("listar_packs_armado_surtido %s: %s", base_empresa, e, exc_info=True)
        return []


def _tablas_armado_1ra(cursor) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Resuelve articulo, en_abm y en_abm_formula con un solo SHOW TABLES."""
    cursor.execute("SHOW TABLES")
    by_lower: Dict[str, str] = {}
    for row in cursor.fetchall() or []:
        nombre = str_or_default(_first_column_value(row), "").strip()
        if nombre:
            by_lower[nombre.lower()] = nombre
    return (
        by_lower.get("articulo"),
        by_lower.get("en_abm"),
        by_lower.get("en_abm_formula"),
    )


def _sql_filtro_descuenta_en_mstock(alias: str = "ab") -> str:
    """BOM armable 1ra: descuenta_en vacío o MSTOCK."""
    return f"""(
                  TRIM(COALESCE({alias}.descuenta_en, '')) = ''
                  OR UPPER(TRIM({alias}.descuenta_en)) = 'MSTOCK'
              )"""


def articulo_habilitado_armado_1ra(base_empresa: str, id_articulo: int) -> bool:
    """Pack 1ra: ensamblado=Si con BOM MSTOCK (una sola query EXISTS)."""
    if not (base_empresa or "").strip() or not id_articulo:
        return False
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art, tbl_abm, tbl_formula = _tablas_armado_1ra(cursor)
            if not tbl_art or not tbl_abm or not tbl_formula:
                return False
            cursor.execute(
                f"""
                SELECT 1 AS ok
                FROM {tbl_art} a
                INNER JOIN {tbl_abm} ab ON ab.id_en_abm = a.id_en_abm
                INNER JOIN {tbl_formula} f
                    ON f.id_en_abm = ab.id_en_abm
                    AND COALESCE(f.anulado, 'No') = 'No'
                WHERE a.IDArt = %s
                  AND UPPER(TRIM(COALESCE(a.ensamblado,''))) = 'SI'
                  AND a.id_en_abm IS NOT NULL
                  AND {_sql_filtro_descuenta_en_mstock('ab')}
                LIMIT 1
                """,
                [id_articulo],
            )
            return bool(cursor.fetchone())
    except Exception as e:
        logger.warning("articulo_habilitado_armado_1ra %s: %s", base_empresa, e, exc_info=True)
        return False


def listar_packs_armado_1ra(base_empresa: str) -> List[Dict[str, Any]]:
    """Packs Armado 1ra: ensamblado=Si con BOM válido (una query JOIN, sin N+1)."""
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art, tbl_abm, tbl_formula = _tablas_armado_1ra(cursor)
            if not tbl_art or not tbl_abm or not tbl_formula:
                return []
            cursor.execute(
                f"""
                SELECT DISTINCT a.IDArt AS id_articulo,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(a.NombreArticulo, '') AS descripcion_articulo
                FROM {tbl_art} a
                INNER JOIN {tbl_abm} ab ON ab.id_en_abm = a.id_en_abm
                INNER JOIN {tbl_formula} f
                    ON f.id_en_abm = ab.id_en_abm
                    AND COALESCE(f.anulado, 'No') = 'No'
                WHERE UPPER(TRIM(COALESCE(a.ensamblado,''))) = 'SI'
                  AND a.id_en_abm IS NOT NULL
                  AND {_sql_filtro_descuenta_en_mstock('ab')}
                ORDER BY codigo_articulo, a.IDArt
                """,
            )
            rows = cursor.fetchall() or []
        return [
            {
                "id_articulo": id_a,
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
            }
            for r in rows
            if (id_a := to_int_or_none(r.get("id_articulo"))) is not None
        ]
    except Exception as e:
        logger.warning("listar_packs_armado_1ra %s: %s", base_empresa, e, exc_info=True)
        return []


def listar_packs_armado_catalogo(
    base_empresa: str,
    modo: str,
    busqueda: Optional[str] = None,
    limit: int = 25,
    ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """
    Catálogo de packs para Armado (API lazy): búsqueda acotada por código/descripción/id.
    modo: '1ra' (BOM Mstock) o '2da' (tipo_art_fab Fabricado 2da).
    """
    if not (base_empresa or "").strip():
        return []
    modo_norm = (modo or "1ra").strip().lower()
    try:
        lim = max(1, min(int(limit or 25), 50))
    except (TypeError, ValueError):
        lim = 25
    id_filtro = sorted({x for x in (to_int_or_none(i) for i in (ids or [])) if x is not None})
    q = (busqueda or "").strip()
    like_params: List[Any] = []
    filtro_busqueda = ""
    if q and not id_filtro:
        like = f"%{q}%"
        like_params = [like, like, like]
        filtro_busqueda = """
          AND (
                COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') LIKE %s
             OR COALESCE(a.NombreArticulo, '') LIKE %s
             OR CAST(a.IDArt AS CHAR) LIKE %s
          )
        """
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            if modo_norm == "2da":
                tbl = _nombre_tabla(cursor, "articulo")
                if not tbl or not columna_existe(cursor, tbl, "tipo_art_fab"):
                    return []
                bulto_sql = _fragmento_sql_cantidad_promedio_bulto(cursor, tbl)
                params: List[Any] = [TIPO_ART_FAB_PACK_ARMADO_SURTIDO]
                filtro_ids = ""
                if id_filtro:
                    ph = ",".join(["%s"] * len(id_filtro))
                    filtro_ids = f" AND a.IDArt IN ({ph})"
                    params.extend(id_filtro)
                if like_params:
                    params.extend(like_params)
                params.append(lim)
                cursor.execute(
                    f"""
                    SELECT a.IDArt AS id_articulo,
                           COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                           COALESCE(a.NombreArticulo, '') AS descripcion_articulo{bulto_sql}
                    FROM {tbl} a
                    WHERE COALESCE(TRIM(a.tipo_art_fab), '') = %s
                    {filtro_ids}
                    {filtro_busqueda if like_params else ''}
                    ORDER BY codigo_articulo, a.IDArt
                    LIMIT %s
                    """,
                    params,
                )
            else:
                tbl_art, tbl_abm, tbl_formula = _tablas_armado_1ra(cursor)
                if not tbl_art or not tbl_abm or not tbl_formula:
                    return []
                bulto_sql = _fragmento_sql_cantidad_promedio_bulto(cursor, tbl_art)
                params = []
                filtro_ids = ""
                if id_filtro:
                    ph = ",".join(["%s"] * len(id_filtro))
                    filtro_ids = f" AND a.IDArt IN ({ph})"
                    params.extend(id_filtro)
                if like_params:
                    params.extend(like_params)
                params.append(lim)
                cursor.execute(
                    f"""
                    SELECT DISTINCT a.IDArt AS id_articulo,
                           COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                           COALESCE(a.NombreArticulo, '') AS descripcion_articulo{bulto_sql}
                    FROM {tbl_art} a
                    INNER JOIN {tbl_abm} ab ON ab.id_en_abm = a.id_en_abm
                    INNER JOIN {tbl_formula} f
                        ON f.id_en_abm = ab.id_en_abm
                        AND COALESCE(f.anulado, 'No') = 'No'
                    WHERE UPPER(TRIM(COALESCE(a.ensamblado,''))) = 'SI'
                      AND a.id_en_abm IS NOT NULL
                      AND {_sql_filtro_descuenta_en_mstock('ab')}
                    {filtro_ids}
                    {filtro_busqueda if like_params else ''}
                    ORDER BY codigo_articulo, a.IDArt
                    LIMIT %s
                    """,
                    params,
                )
            rows = cursor.fetchall() or []
        out = []
        for r in rows:
            id_a = to_int_or_none(r.get("id_articulo"))
            if id_a is None:
                continue
            try:
                bulto = float(r.get("cantidad_promedio_bulto") or 0)
            except (TypeError, ValueError):
                bulto = 0.0
            out.append({
                "id_articulo": id_a,
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "cantidad_promedio_bulto": bulto if bulto > 0 else 12,
            })
        return out
    except Exception as e:
        logger.warning(
            "listar_packs_armado_catalogo modo=%s %s: %s",
            modo_norm,
            base_empresa,
            e,
            exc_info=True,
        )
        return []


def lineas_bom_pack_1ra(base_empresa: str, id_articulo_pack: int) -> List[Dict[str, Any]]:
    """Componentes BOM para un pack 1ra (cantidad por pack)."""
    if not articulo_habilitado_armado_1ra(base_empresa, id_articulo_pack):
        return []
    id_en_abm = get_id_en_abm_por_articulo(base_empresa, id_articulo_pack)
    if not id_en_abm:
        return []
    bom = get_bom_detalle(base_empresa, id_en_abm)
    lineas = []
    for comp in (bom or {}).get("componentes") or []:
        id_c = to_int_or_none(comp.get("id_articulo"))
        qty = int(float(comp.get("cantidad_articulo") or 0))
        if id_c and qty > 0:
            lineas.append({
                "id_articulo": id_c,
                "cantidad_por_pack": qty,
                "codigo_articulo": str_or_default(comp.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(comp.get("descripcion_articulo"), "-"),
            })
    return lineas


def validar_composicion_bom_1ra(
    base_empresa: str,
    id_articulo_pack: int,
    lineas_post: List[Dict[str, Any]],
) -> Tuple[bool, Optional[str]]:
    """Anti-tamper: composición POST debe coincidir con BOM."""
    esperadas = lineas_bom_pack_1ra(base_empresa, id_articulo_pack)
    if not esperadas:
        return False, "No se encontró BOM para el pack seleccionado."
    map_esp: Dict[int, int] = {}
    for ln in esperadas:
        map_esp[int(ln["id_articulo"])] = int(ln["cantidad_por_pack"])
    map_post: Dict[int, int] = {}
    for ln in lineas_post or []:
        id_c = to_int_or_none(ln.get("id_articulo"))
        qty = to_int_or_none(ln.get("cantidad_por_pack"))
        if id_c and qty and int(qty) > 0:
            map_post[int(id_c)] = int(qty)
    if map_post != map_esp:
        return False, "La composición no coincide con la lista de materiales del pack."
    return True, None


def calcular_max_packs_armado_1ra(
    base_empresa: str,
    id_articulo_pack: int,
    deposito_semi: Optional[int] = None,
) -> int:
    """Máximo de packs armables según stock semi de componentes BOM."""
    dep = deposito_semi or get_deposito_semi_elaborado_mpr(base_empresa)
    if not dep:
        return 0
    lineas = lineas_bom_pack_1ra(base_empresa, id_articulo_pack)
    if not lineas:
        return 0
    ids_comp = [ln["id_articulo"] for ln in lineas]
    saldos: Dict[int, float] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            if tbl_sd and ids_comp:
                ph = ",".join(["%s"] * len(ids_comp))
                cursor.execute(
                    f"SELECT id_articulo, saldo FROM {tbl_sd} WHERE id_deposito = %s AND id_articulo IN ({ph})",
                    [dep] + ids_comp,
                )
                for row in cursor.fetchall() or []:
                    aid = to_int_or_none(row.get("id_articulo"))
                    if aid is not None:
                        saldos[aid] = float(row.get("saldo") or 0)
    except Exception as e:
        logger.warning("calcular_max_packs_armado_1ra saldos: %s", e)
        return 0
    max_packs = 0
    for ln in lineas:
        qty = int(ln["cantidad_por_pack"])
        if qty <= 0:
            continue
        saldo = saldos.get(int(ln["id_articulo"]), 0)
        packs_i = int(saldo // qty)
        max_packs = min(max_packs, packs_i) if max_packs else packs_i
    return max(0, max_packs)


def listar_articulos_stock_deposito(
    base_empresa: str,
    id_deposito: int,
    busqueda: Optional[str] = None,
    limit: int = 40,
) -> List[Dict[str, Any]]:
    """Artículos con saldo > 0 en el depósito indicado (para composición armado surtido)."""
    if not (base_empresa or "").strip():
        return []
    dep = to_int_or_none(id_deposito)
    if not dep:
        return []
    lim = max(1, min(int(limit or 40), 100))
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            if not tbl_art or not tbl_sd:
                return []
            params: List[Any] = [dep]
            filtro_q = ""
            if busqueda and (busqueda or "").strip():
                q = f"%{(busqueda or '').strip()}%"
                filtro_q = (
                    " AND (a.CodigoArticuloT LIKE %s OR CAST(a.CodigoArticulo AS CHAR) LIKE %s "
                    "OR a.NombreArticulo LIKE %s)"
                )
                params.extend([q, q, q])
            params.append(lim)
            cursor.execute(
                f"""
                SELECT a.IDArt AS id_articulo,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                       sd.saldo AS saldo
                FROM {tbl_sd} sd
                INNER JOIN {tbl_art} a ON a.IDArt = sd.id_articulo
                WHERE sd.id_deposito = %s AND COALESCE(sd.saldo, 0) > 0
                {filtro_q}
                ORDER BY a.CodigoArticuloT, a.IDArt
                LIMIT %s
                """,
                params,
            )
            rows = cursor.fetchall()
        return [
            {
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "saldo": float(r.get("saldo") or 0),
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("listar_articulos_stock_deposito %s dep %s: %s", base_empresa, id_deposito, e, exc_info=True)
        return []


def _mpr_costo_stock_desde_articulo(
    precio_costo_u: Any,
    cantidad: Decimal,
) -> Tuple[Decimal, Decimal]:
    """Precio unitario y total de costo para renglón stock (desde articulo.PrecioCosto)."""
    pc_u = to_decimal_or_none(precio_costo_u) or Decimal(0)
    cant = cantidad or Decimal(0)
    pc_r = (pc_u * cant).quantize(Decimal("0.000001"))
    return pc_u, pc_r


def _fetch_articulos_map(cursor, tbl_articulo: str, ids: List[int]) -> Dict[int, Dict[str, Any]]:
    if not ids or not tbl_articulo:
        return {}
    placeholders = ",".join(["%s"] * len(ids))
    precio_sel = (
        "COALESCE(PrecioCosto, 0)"
        if columna_existe(cursor, tbl_articulo, "PrecioCosto")
        else "0"
    )
    cursor.execute(
        f"""
        SELECT IDArt,
               COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo,
               COALESCE(NombreArticulo, '') AS nombre,
               {precio_sel} AS precio_costo
        FROM {tbl_articulo}
        WHERE IDArt IN ({placeholders})
        """,
        ids,
    )
    out: Dict[int, Dict[str, Any]] = {}
    for row in cursor.fetchall():
        if isinstance(row, dict):
            id_a = to_int_or_none(row.get("IDArt"))
            if not id_a:
                continue
            out[int(id_a)] = {
                "codigo_articulo": str_or_default(row.get("codigo"), "-"),
                "descripcion_articulo": str_or_default(row.get("nombre"), "-"),
                "precio_costo": to_decimal_or_none(row.get("precio_costo")) or Decimal(0),
            }
        else:
            id_a = int(row[0])
            out[id_a] = {
                "codigo_articulo": str_or_default(row[1], "-"),
                "descripcion_articulo": str_or_default(row[2], "-"),
                "precio_costo": to_decimal_or_none(row[3]) or Decimal(0),
            }
    return out


def _articulos_con_lote_ids(cursor, tbl_articulo: str, ids: List[int]) -> Set[int]:
    """IDs de artículos con Lote=Si en AdministraNET."""
    if not tbl_articulo or not ids:
        return set()
    placeholders = ",".join(["%s"] * len(ids))
    cursor.execute(
        f"SELECT IDArt FROM {tbl_articulo} WHERE IDArt IN ({placeholders}) AND UPPER(TRIM(COALESCE(Lote,''))) = 'SI'",
        ids,
    )
    return {
        int(row.get("IDArt") if isinstance(row, dict) else row[0])
        for row in cursor.fetchall()
    }


def _mpr_insert_renglon_stock_armado(
    cursor,
    tbl_stock: str,
    codigo_mov: int,
    id_art: int,
    codigo_art: str,
    descripcion_art: str,
    fecha_mov: str,
    entrada: Decimal,
    salida: Decimal,
    saldo: Decimal,
    deposito: int,
    id_ref_movstock: int,
    orden: int,
    id_usuario: int,
    nro_comprobante: str,
    id_operario: Optional[int] = None,
    id_lote: Optional[int] = None,
    precio_costo_u: Optional[Decimal] = None,
) -> None:
    """Inserta renglón en stock (Armado surtido); tolera esquemas sin columnas opcionales."""
    cantidad = entrada if entrada > 0 else salida
    pc_u, pc_r = _mpr_costo_stock_desde_articulo(precio_costo_u, cantidad)
    params_tail = [
        deposito,
        id_ref_movstock,
        orden,
        id_usuario,
        MOTIVO_ARMADO_TEXTO,
        nro_comprobante,
        None,
    ]
    params_base = [
        codigo_mov,
        id_art,
        codigo_art,
        descripcion_art,
        fecha_mov,
        entrada,
        salida,
        saldo,
    ] + params_tail
    params_con_costo = params_base[:8] + [cantidad, pc_u, pc_r] + params_tail
    intentos: List[Tuple[str, List[Any]]] = []
    id_op = to_int_or_none(id_operario)

    def _agregar_variantes(params: List[Any], cols_extra: str, vals_extra: str) -> None:
        intentos.append((
            f"""
            INSERT INTO {tbl_stock}
            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo,
             Cantidad, PrecioCostoxU, PrecioCostoxR, CodDeposito,
             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante{cols_extra})
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s{vals_extra})
            """,
            params,
        ))

    if precio_costo_u is not None:
        if id_lote is not None:
            if id_op is not None:
                _agregar_variantes(
                    params_con_costo + [id_lote, id_op],
                    ", id_lote, id_operario_opt",
                    ", %s, %s",
                )
            _agregar_variantes(params_con_costo + [id_lote], ", id_lote", ", %s")
        elif id_op is not None:
            _agregar_variantes(params_con_costo + [id_op], ", id_operario_opt", ", %s")
        _agregar_variantes(params_con_costo, "", "")

    if id_lote is not None:
        params_lote = params_base + [id_lote]
        if id_op is not None:
            intentos.append((
                f"""
                INSERT INTO {tbl_stock}
                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_lote, id_operario_opt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s, %s)
                """,
                params_lote + [id_op],
            ))
        intentos.append((
            f"""
            INSERT INTO {tbl_stock}
            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_lote)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
            """,
            params_lote,
        ))
    elif id_op is not None:
        intentos.append((
            f"""
            INSERT INTO {tbl_stock}
            (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
             id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante, id_operario_opt)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s, %s)
            """,
            params_base + [id_op],
        ))
    intentos.append((
        f"""
        INSERT INTO {tbl_stock}
        (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
         id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
        """,
        params_base,
    ))
    _mpr_ejecutar_insert_intentos(cursor, intentos)


def _mpr_consumir_salida_componente_surtido(
    cursor,
    tbl_stock: str,
    tbl_sd: str,
    tbl_lote: Optional[str],
    tbl_lote_stock: Optional[str],
    stock_tiene_id_lote: bool,
    usa_lote: bool,
    codigo_mov: int,
    id_art: int,
    codigo_art: str,
    descripcion_art: str,
    fecha_mov: str,
    qty_salida: Decimal,
    deposito_origen: int,
    id_ref_movstock: int,
    orden: int,
    id_usuario: int,
    nro_comprobante: str,
    id_operario: Optional[int],
    precio_costo_u: Optional[Decimal] = None,
) -> Tuple[int, Optional[str]]:
    """
    Salida de componente en armado surtido (sin lote o FIFO por lote).
    Devuelve (orden_siguiente, mensaje_error).
    """
    cursor.execute(
        f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
        [id_art, deposito_origen],
    )
    sd_row = cursor.fetchone()
    saldo_actual = Decimal(str(sd_row[1] or 0)) if sd_row else Decimal(0)
    saldo_despues = saldo_actual - qty_salida

    if not usa_lote:
        orden += 1
        _mpr_insert_renglon_stock_armado(
            cursor,
            tbl_stock,
            codigo_mov,
            id_art,
            codigo_art,
            descripcion_art,
            fecha_mov,
            Decimal(0),
            qty_salida,
            saldo_despues,
            deposito_origen,
            id_ref_movstock,
            orden,
            id_usuario,
            nro_comprobante,
            id_operario=id_operario,
            precio_costo_u=precio_costo_u,
        )
        if sd_row:
            cursor.execute(
                f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s",
                [saldo_despues, sd_row[0]],
            )
        else:
            cursor.execute(
                f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                [id_art, deposito_origen, saldo_despues],
            )
        return orden, None

    if not tbl_lote or not tbl_lote_stock:
        return orden, f"El artículo {codigo_art} usa lote pero faltan tablas de lote en la base."

    cursor.execute(
        f"""
        SELECT l.id_lote, ls.id_lote_stock, ls.stock_lote
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
    stock_total_lotes = sum(float(f[2] or 0) for f in filas_lote)
    if stock_total_lotes < float(qty_salida):
        return (
            orden,
            f"Stock en lotes insuficiente de {codigo_art} en depósito origen: "
            f"disponible en lotes {stock_total_lotes}, se necesitan {qty_salida}.",
        )
    qty_restante = qty_salida
    for fila in filas_lote:
        if qty_restante <= 0:
            break
        id_lote, id_lote_stock, stock_lote = fila[0], fila[1], Decimal(str(fila[2] or 0))
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
        saldo_parcial = saldo_actual - (qty_salida - qty_restante + tomar)
        id_lote_ins = id_lote if stock_tiene_id_lote else None
        _mpr_insert_renglon_stock_armado(
            cursor,
            tbl_stock,
            codigo_mov,
            id_art,
            codigo_art,
            descripcion_art,
            fecha_mov,
            Decimal(0),
            tomar,
            saldo_parcial,
            deposito_origen,
            id_ref_movstock,
            orden,
            id_usuario,
            nro_comprobante,
            id_operario=id_operario,
            id_lote=id_lote_ins,
            precio_costo_u=precio_costo_u,
        )
        qty_restante -= tomar
    if sd_row:
        cursor.execute(
            f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s",
            [saldo_despues, sd_row[0]],
        )
    else:
        cursor.execute(
            f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
            [id_art, deposito_origen, saldo_despues],
        )
    return orden, None


def _guardar_historial_armado_surtido(
    cursor,
    tbl_historico: str,
    id_art_pack: int,
    cantidad_packs: int,
    deposito_origen: int,
    deposito_destino: int,
    codigo_mov: int,
    nro_comprobante: str,
    id_usuario: int,
    id_lista_produccion: Optional[int],
    fecha_mov: str,
    hora_evento: str,
    id_operario: Optional[int],
    num_componentes: int,
) -> None:
    if not tbl_historico:
        return
    det = f"Armado surtido MPR ({num_componentes} componentes)"
    base_opa = [
        TIPO_MOV_OPA,
        id_art_pack,
        cantidad_packs,
        deposito_destino,
        deposito_origen,
        deposito_destino,
        codigo_mov,
        nro_comprobante,
        id_usuario,
        id_lista_produccion,
        fecha_mov,
        hora_evento,
    ]
    intentos_opa: List[Tuple[str, List[Any]]] = []
    id_op_h = to_int_or_none(id_operario)
    if id_op_h is not None:
        intentos_opa.append((
            f"""
            INSERT INTO {tbl_historico}
            (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
             id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
             nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento, id_operario, id_operario_opt)
            VALUES (%s, %s, NULL, 0, 0, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s, %s, %s)
            """,
            base_opa + [id_op_h, id_op_h],
        ))
    intentos_opa.append((
        f"""
        INSERT INTO {tbl_historico}
        (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
         id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
         nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento)
        VALUES (%s, %s, NULL, 0, 0, %s, %s, %s, %s, %s, NULL, %s, %s, %s, %s, %s)
        """,
        base_opa,
    ))
    try:
        _mpr_ejecutar_insert_intentos(cursor, intentos_opa)
    except Exception as hist_err:
        logger.warning("Historial armado surtido: %s", hist_err)


def guardar_composicion_armado_surtido(
    base_empresa: str,
    codigo_movimiento: int,
    id_articulo_pack: int,
    cantidad_packs: int,
    deposito_origen: int,
    deposito_destino: int,
    lineas_enriquecidas: List[Dict[str, Any]],
    id_usuario: int,
    id_operario: Optional[int] = None,
    id_lista_produccion: Optional[int] = None,
    detalle: Optional[str] = None,
    *,
    modo: str = "2da",
    id_lote_armado=None,
    estado_imputacion: str = "na",
) -> None:
    from mpr.models import (
        ESTADO_IMPUTACION_NA,
        ESTADO_IMPUTACION_PENDIENTE,
        MODO_ARMADO_1RA,
        MprArmadoSurtidoLinea,
        MprArmadoSurtidoMovimiento,
    )

    modo_n = _normalizar_modo_armado(modo)
    est_imp = estado_imputacion
    if modo_n == MODO_ARMADO_1RA and est_imp == ESTADO_IMPUTACION_NA:
        est_imp = ESTADO_IMPUTACION_PENDIENTE

    mov = MprArmadoSurtidoMovimiento.objects.create(
        base_empresa=base_empresa.strip(),
        codigo_movimiento=int(codigo_movimiento),
        id_articulo_pack=int(id_articulo_pack),
        cantidad_packs=int(cantidad_packs),
        deposito_origen=int(deposito_origen),
        deposito_destino=int(deposito_destino),
        id_lista_produccion=to_int_or_none(id_lista_produccion),
        id_operario=to_int_or_none(id_operario),
        id_usuario=int(id_usuario),
        detalle=(detalle or "").strip()[:500],
        modo=modo_n,
        id_lote_armado_id=id_lote_armado,
        estado_imputacion=est_imp,
    )
    bulk = []
    for ln in lineas_enriquecidas:
        qty_pack = int(ln.get("cantidad_por_pack") or 0)
        bulk.append(
            MprArmadoSurtidoLinea(
                movimiento=mov,
                id_articulo_componente=int(ln["id_articulo"]),
                codigo_articulo=str_or_default(ln.get("codigo_articulo"), "-"),
                descripcion_articulo=str_or_default(ln.get("descripcion_articulo"), "-"),
                cantidad_por_pack=qty_pack,
                cantidad_total=qty_pack * int(cantidad_packs),
            )
        )
    if bulk:
        MprArmadoSurtidoLinea.objects.bulk_create(bulk)


def _detalle_mov_armado_1ra(
    id_articulo_pack: int,
    cantidad_packs: int,
    lineas_composicion: List[Dict[str, Any]],
    *,
    detalle: Optional[str] = None,
    id_lista_produccion: Optional[int] = None,
) -> str:
    n_comp = len(lineas_composicion or [])
    if (detalle or "").strip():
        return (detalle or "").strip()
    if id_lista_produccion:
        return (
            f"Armado OPT {id_lista_produccion} (1ra MPR, pack {id_articulo_pack}, "
            f"{cantidad_packs} packs, {n_comp} componentes)"
        )
    return (
        f"Armado 1ra MPR (pack {id_articulo_pack}, {cantidad_packs} packs, {n_comp} componentes)"
    )


def _detalle_mov_armado_surtido(
    id_articulo_pack: int,
    cantidad_packs: int,
    lineas_composicion: List[Dict[str, Any]],
    *,
    detalle: Optional[str] = None,
    id_lista_produccion: Optional[int] = None,
) -> str:
    n_comp = len(lineas_composicion or [])
    return (detalle or "").strip() or (
        f"Armado surtido MPR (pack {id_articulo_pack}, {cantidad_packs} packs, {n_comp} componentes)"
        + (f" OPT {id_lista_produccion}" if id_lista_produccion else "")
    )


def _ejecutar_armado_surtido_tx(
    cursor,
    _conn,
    *,
    id_usuario: int,
    id_articulo_pack: int,
    cantidad_packs: int,
    deposito_origen: int,
    deposito_destino: int,
    lineas_composicion: List[Dict[str, Any]],
    id_operario: Optional[int] = None,
    id_lista_produccion: Optional[int] = None,
    detalle_mov: Optional[str] = None,
) -> Tuple[bool, Optional[int], Optional[str], Optional[str], List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Núcleo transaccional de armado surtido sobre cursor activo.
    No realiza commit/rollback ante errores de negocio; delega al caller.
    Devuelve info_pack en el 6.º elemento (descripción y saldos del pack en destino).
    """
    id_ref_movstock = 1
    id_pv = 1
    fecha_mov = date.today().isoformat()
    hora_evento = datetime.now().strftime("%H:%M:%S")
    n_comp = len(lineas_composicion or [])
    lineas_enriquecidas: List[Dict[str, Any]] = []
    detalle_mov = detalle_mov or _detalle_mov_armado_surtido(
        id_articulo_pack,
        cantidad_packs,
        lineas_composicion,
        id_lista_produccion=id_lista_produccion,
    )

    try:
        tbl_codmov = _nombre_tabla(cursor, "codmov")
        tbl_talonarios = _nombre_tabla(cursor, "talonarios")
        tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
        tbl_stock = _nombre_tabla(cursor, "stock")
        tbl_sd = _nombre_tabla(cursor, "stock_deposito")
        tbl_articulo = _nombre_tabla(cursor, "articulo")
        if not all([tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd, tbl_articulo]):
            raise MprSchemaError("Faltan tablas de stock para armado surtido.")

        ids_todos = [int(id_articulo_pack)] + [
            int(to_int_or_none(ln.get("id_articulo")) or 0) for ln in lineas_composicion
        ]
        arts = _fetch_articulos_map(cursor, tbl_articulo, [i for i in ids_todos if i])
        if id_articulo_pack not in arts:
            return False, None, None, "Pack terminado no encontrado en artículos.", lineas_enriquecidas, None
        pack_info = arts[id_articulo_pack]

        tbl_lote = _nombre_tabla(cursor, "lote")
        tbl_lote_stock = _nombre_tabla(cursor, "lote_stock")
        stock_tiene_id_lote = False
        if tbl_stock:
            cursor.execute(
                "SELECT 1 FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = 'id_lote'",
                [tbl_stock],
            )
            stock_tiene_id_lote = cursor.fetchone() is not None

        ids_comp = [int(ln["id_articulo"]) for ln in lineas_composicion]
        articulos_con_lote = _articulos_con_lote_ids(cursor, tbl_articulo, ids_comp)
        for ln in lineas_composicion:
            id_c = int(ln["id_articulo"])
            qty_pp = int(ln["cantidad_por_pack"])
            info = arts.get(id_c)
            if not info:
                return False, None, None, f"Componente {id_c} no encontrado.", lineas_enriquecidas, None
            necesario = qty_pp * cantidad_packs
            usa_lote = id_c in articulos_con_lote and tbl_lote and tbl_lote_stock
            if usa_lote:
                cursor.execute(
                    f"""
                    SELECT COALESCE(SUM(ls.stock_lote), 0)
                    FROM {tbl_lote} l
                    INNER JOIN {tbl_lote_stock} ls ON ls.id_lote = l.id_lote
                    WHERE l.id_articulo = %s AND ls.id_deposito = %s
                      AND COALESCE(l.anulado,'No') = 'No' AND COALESCE(ls.stock_lote,0) > 0
                    """,
                    [id_c, deposito_origen],
                )
                row_lote = cursor.fetchone()
                saldo_lotes = float(row_lote[0] or 0) if row_lote else 0
                if saldo_lotes < necesario:
                    return (
                        False,
                        None,
                        None,
                        f"Stock en lotes insuficiente de {info['codigo_articulo']} en origen: "
                        f"disponible {saldo_lotes}, se necesitan {necesario}.",
                        lineas_enriquecidas,
                        None,
                    )
            cursor.execute(
                f"SELECT saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s",
                [id_c, deposito_origen],
            )
            row_sd = cursor.fetchone()
            saldo = Decimal(str(row_sd[0] or 0)) if row_sd else Decimal(0)
            if saldo < Decimal(str(necesario)):
                return (
                    False,
                    None,
                    None,
                    f"Stock insuficiente de {info['codigo_articulo']} en origen: "
                    f"tiene {saldo}, se necesitan {necesario}.",
                    lineas_enriquecidas,
                    None,
                )
            lineas_enriquecidas.append({
                "id_articulo": id_c,
                "cantidad_por_pack": qty_pp,
                "codigo_articulo": info["codigo_articulo"],
                "descripcion_articulo": info["descripcion_articulo"],
                "usa_lote": usa_lote,
                "precio_costo": info.get("precio_costo") or Decimal(0),
            })

        cursor.execute(f"SELECT CodigoMovimiento FROM {tbl_codmov} WHERE codigo = 1 FOR UPDATE")
        row = cursor.fetchone()
        if not row:
            return False, None, None, "No se pudo obtener código de movimiento.", lineas_enriquecidas, None
        codigo_mov = int(row[0] or 0) + 1
        cursor.execute(f"UPDATE {tbl_codmov} SET CodigoMovimiento = %s WHERE codigo = 1", [codigo_mov])

        cursor.execute(
            f"SELECT Orden, Nro FROM {tbl_talonarios} WHERE TipoComprobante = 'MSTOCK' AND id_punto_venta = %s FOR UPDATE",
            [id_pv],
        )
        talon_row = cursor.fetchone()
        if not talon_row:
            return (
                False,
                None,
                None,
                "No existe talonario MSTOCK para el punto de venta.",
                lineas_enriquecidas,
                None,
            )
        orden_talon, nro_actual = talon_row[0], int(talon_row[1] or 0)
        nro_nuevo = nro_actual + 1
        cursor.execute(f"UPDATE {tbl_talonarios} SET Nro = %s WHERE Orden = %s", [nro_nuevo, orden_talon])
        nro_comprobante = _formato_nro_comprobante_mstock(id_pv, nro_actual)
        nro_comprobante_busq = nro_actual

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
            TIPO_MOV_OPA,
            id_pv,
            nro_comprobante_busq,
        ]
        params_mov_ins = (
            params_mov[:8] + ["MSTOCK"] + [params_mov[8], params_mov[9], params_mov[10], params_mov[11], params_mov[13], params_mov[14]]
        )
        id_op_arm = to_int_or_none(id_operario)
        intentos_m: List[Tuple[str, List[Any]]] = []
        if id_op_arm is not None:
            intentos_m.append((
                f"""
                INSERT INTO {tbl_mov}
                (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                 detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, id_operario_opt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'No', %s, %s, %s, %s, %s, %s, %s)
                """,
                list(params_mov_ins) + [id_op_arm],
            ))
        intentos_m.append((
            f"""
            INSERT INTO {tbl_mov}
            (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
             detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'No', %s, %s, %s, %s, %s, %s)
            """,
            params_mov_ins,
        ))
        _mpr_ejecutar_insert_intentos(cursor, intentos_m)

        orden = 0
        for ln in lineas_enriquecidas:
            id_c = ln["id_articulo"]
            qty_salida = Decimal(str(ln["cantidad_por_pack"] * cantidad_packs))
            orden, err_cons = _mpr_consumir_salida_componente_surtido(
                cursor,
                tbl_stock,
                tbl_sd,
                tbl_lote,
                tbl_lote_stock,
                stock_tiene_id_lote,
                bool(ln.get("usa_lote")),
                codigo_mov,
                id_c,
                ln["codigo_articulo"],
                ln["descripcion_articulo"],
                fecha_mov,
                qty_salida,
                deposito_origen,
                id_ref_movstock,
                orden,
                id_usuario,
                nro_comprobante,
                id_operario,
                ln.get("precio_costo"),
            )
            if err_cons:
                return False, None, None, err_cons, lineas_enriquecidas, None

        id_pack = int(id_articulo_pack)
        entrada_pack = Decimal(str(cantidad_packs))
        cursor.execute(
            f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
            [id_pack, deposito_destino],
        )
        sd_dest = cursor.fetchone()
        saldo_dest = Decimal(str(sd_dest[1] or 0)) if sd_dest else Decimal(0)
        saldo_dest_despues = saldo_dest + entrada_pack
        orden += 1
        _mpr_insert_renglon_stock_armado(
            cursor,
            tbl_stock,
            codigo_mov,
            id_pack,
            pack_info["codigo_articulo"],
            pack_info["descripcion_articulo"],
            fecha_mov,
            entrada_pack,
            Decimal(0),
            saldo_dest_despues,
            deposito_destino,
            id_ref_movstock,
            orden,
            id_usuario,
            nro_comprobante,
            id_operario=id_operario,
            precio_costo_u=pack_info.get("precio_costo"),
        )
        if sd_dest:
            cursor.execute(
                f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s",
                [saldo_dest_despues, sd_dest[0]],
            )
        else:
            cursor.execute(
                f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                [id_pack, deposito_destino, saldo_dest_despues],
            )

        tbl_historico = _nombre_tabla(cursor, "lista_produccion_historico")
        _guardar_historial_armado_surtido(
            cursor,
            tbl_historico,
            id_pack,
            cantidad_packs,
            deposito_origen,
            deposito_destino,
            codigo_mov,
            nro_comprobante,
            id_usuario,
            id_lista_produccion,
            fecha_mov,
            hora_evento,
            id_operario,
            n_comp,
        )
        info_pack = {
            "codigo_articulo_pack": str_or_default(pack_info.get("codigo_articulo"), ""),
            "descripcion_articulo_pack": str_or_default(pack_info.get("descripcion_articulo"), ""),
            "saldo_inicial": _saldo_modal_armado_surtido(saldo_dest),
            "saldo_final": _saldo_modal_armado_surtido(saldo_dest_despues),
        }
        return True, codigo_mov, nro_comprobante, None, lineas_enriquecidas, info_pack
    except MprSchemaError:
        raise
    except Exception as e:
        if "1054" in str(e) or "Unknown column" in str(e).lower():
            raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
        logger.warning("_ejecutar_armado_surtido_tx: %s", e, exc_info=True)
        return False, None, None, str(e), lineas_enriquecidas, None


def ejecutar_armado_surtido(
    base_empresa: str,
    id_usuario: int,
    id_articulo_pack: int,
    cantidad_packs: int,
    deposito_origen: int,
    deposito_destino: int,
    lineas_composicion: List[Dict[str, Any]],
    id_operario: Optional[int] = None,
    id_lista_produccion: Optional[int] = None,
    detalle: Optional[str] = None,
) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """
    Armado surtido: N salidas de componentes desde origen y entrada del pack en destino.
    Sin BOM; composición libre. Devuelve (ok, codigo_movimiento, nro_comprobante, error).
    """
    if not (base_empresa or "").strip():
        return False, None, None, "Base de datos no indicada."
    if not id_usuario:
        return False, None, None, "Usuario no indicado."
    ok_val, err_val = validar_datos_armado_surtido(
        cantidad_packs,
        deposito_origen,
        deposito_destino,
        lineas_composicion,
        id_operario=id_operario,
        id_articulo_pack=id_articulo_pack,
    )
    if not ok_val:
        return False, None, None, err_val
    if not articulo_habilitado_armado_surtido(base_empresa, id_articulo_pack):
        return False, None, None, (
            f"El pack seleccionado no tiene tipo_art_fab '{TIPO_ART_FAB_PACK_ARMADO_SURTIDO}'."
        )

    deposito_origen = int(to_int_or_none(deposito_origen) or 0)
    deposito_destino = int(to_int_or_none(deposito_destino) or 0)
    detalle_mov = _detalle_mov_armado_surtido(
        id_articulo_pack,
        cantidad_packs,
        lineas_composicion,
        detalle=detalle,
        id_lista_produccion=id_lista_produccion,
    )
    lineas_enriquecidas: List[Dict[str, Any]] = []
    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            ok_tx, codigo_mov, nro_comprobante, err_tx, lineas_enriquecidas, info_pack = _ejecutar_armado_surtido_tx(
                cursor,
                conn,
                id_usuario=id_usuario,
                id_articulo_pack=int(id_articulo_pack),
                cantidad_packs=int(cantidad_packs),
                deposito_origen=deposito_origen,
                deposito_destino=deposito_destino,
                lineas_composicion=lineas_composicion,
                id_operario=id_operario,
                id_lista_produccion=id_lista_produccion,
                detalle_mov=detalle_mov,
            )
            if not ok_tx:
                conn.rollback()
                return False, None, None, err_tx
            conn.commit()

        if codigo_mov is None or nro_comprobante is None:
            return False, None, None, "No se pudo confirmar el movimiento de armado surtido."

        guardar_composicion_armado_surtido(
            base_empresa,
            codigo_mov,
            id_articulo_pack,
            cantidad_packs,
            deposito_origen,
            deposito_destino,
            lineas_enriquecidas,
            id_usuario,
            id_operario=id_operario,
            id_lista_produccion=id_lista_produccion,
            detalle=detalle_mov,
        )
        return True, codigo_mov, nro_comprobante, None
    except MprSchemaError:
        raise
    except Exception as e:
        if "1054" in str(e) or "Unknown column" in str(e).lower():
            raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
        logger.warning("Conexión ejecutar_armado_surtido: %s", e, exc_info=True)
        return False, None, None, str(e)


def validar_stock_agregado_lote(
    base_empresa: str,
    deposito_origen: int,
    armados: List[Dict[str, Any]],
    item_extra: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Valida stock agregado de componentes para el lote actual + opcional item candidato.
    Devuelve (ok, conflictos).
    """
    items = list(armados or [])
    if item_extra:
        item_norm, err_item = normalizar_item_lote_armado_surtido(item_extra)
        if err_item or not item_norm:
            return False, [{
                "id_articulo": None,
                "codigo_articulo": "-",
                "necesario": 0,
                "disponible": 0,
                "mensaje": err_item or "Ítem de lote inválido.",
            }]
        items.append(item_norm)

    demanda = calcular_demanda_agregada_lote(items)
    if not demanda:
        return True, []

    dep_o = to_int_or_none(deposito_origen)
    if not dep_o:
        return False, [{
            "id_articulo": None,
            "codigo_articulo": "-",
            "necesario": 0,
            "disponible": 0,
            "mensaje": "Depósito origen inválido.",
        }]

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            if not tbl_sd or not tbl_articulo:
                raise MprSchemaError("Faltan tablas de stock para validar lote de armado surtido.")

            ids = sorted(int(i) for i in demanda.keys())
            placeholders = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"""
                SELECT id_articulo, COALESCE(saldo, 0) AS saldo
                FROM {tbl_sd}
                WHERE id_deposito = %s AND id_articulo IN ({placeholders})
                """,
                [dep_o] + ids,
            )
            saldos: Dict[int, Decimal] = {}
            for row in cursor.fetchall() or []:
                id_a = to_int_or_none((row or {}).get("id_articulo"))
                if id_a:
                    saldos[int(id_a)] = Decimal(str((row or {}).get("saldo") or 0))
            arts = _fetch_articulos_map(cursor, tbl_articulo, ids)
            tbl_lote = _nombre_tabla(cursor, "lote")
            tbl_lote_stock = _nombre_tabla(cursor, "lote_stock")
            articulos_con_lote = _articulos_con_lote_ids(cursor, tbl_articulo, ids)

            conflictos: List[Dict[str, Any]] = []
            for id_a, necesario in demanda.items():
                id_int = int(id_a)
                necesario_dec = Decimal(str(necesario))
                info = arts.get(id_int) or {}
                cod = str_or_default(info.get("codigo_articulo"), str(id_int))

                if id_int in articulos_con_lote and tbl_lote and tbl_lote_stock:
                    cursor.execute(
                        f"""
                        SELECT COALESCE(SUM(ls.stock_lote), 0) AS saldo_lotes
                        FROM {tbl_lote} l
                        INNER JOIN {tbl_lote_stock} ls ON ls.id_lote = l.id_lote
                        WHERE l.id_articulo = %s AND ls.id_deposito = %s
                          AND COALESCE(l.anulado,'No') = 'No' AND COALESCE(ls.stock_lote,0) > 0
                        """,
                        [id_int, dep_o],
                    )
                    row_lote = cursor.fetchone() or {}
                    saldo_lotes = Decimal(str((row_lote.get("saldo_lotes") if isinstance(row_lote, dict) else row_lote[0]) or 0))
                    if saldo_lotes < necesario_dec:
                        conflictos.append({
                            "id_articulo": id_int,
                            "codigo_articulo": cod,
                            "necesario": float(necesario_dec),
                            "disponible": float(saldo_lotes),
                            "mensaje": "Stock en lotes insuficiente para agregar al lote.",
                        })
                        continue

                disponible = saldos.get(id_int, Decimal(0))
                if disponible >= necesario_dec:
                    continue
                conflictos.append({
                    "id_articulo": id_int,
                    "codigo_articulo": cod,
                    "necesario": float(necesario_dec),
                    "disponible": float(disponible),
                    "mensaje": "Stock insuficiente para agregar al lote.",
                })
            return len(conflictos) == 0, conflictos
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("validar_stock_agregado_lote %s: %s", base_empresa, e, exc_info=True)
        return False, [{
            "id_articulo": None,
            "codigo_articulo": "-",
            "necesario": 0,
            "disponible": 0,
            "mensaje": f"Error validando stock agregado del lote: {e}",
        }]


def _saldo_modal_armado_surtido(val: Any) -> Optional[float]:
    """Saldo para modal de resultado (entero si aplica)."""
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    if f == int(f):
        return float(int(f))
    return round(f, 4)


def _descripcion_pack_armado_surtido(
    info_pack: Optional[Dict[str, Any]],
    item: Dict[str, Any],
) -> str:
    info = info_pack or {}
    cod = str_or_default(info.get("codigo_articulo_pack"), "")
    desc = str_or_default(info.get("descripcion_articulo_pack"), "")
    if cod and desc:
        return f"{cod} — {desc}"
    if desc:
        return desc
    if cod:
        return cod
    id_pack = to_int_or_none(item.get("id_articulo_pack"))
    return str(id_pack) if id_pack else "-"


def _item_fallido_lote_armado_surtido(
    item: Dict[str, Any],
    error: str,
) -> Dict[str, Any]:
    return {
        "id_articulo_pack": to_int_or_none(item.get("id_articulo_pack")),
        "cantidad_packs": int(to_int_or_none(item.get("cantidad_packs")) or 0),
        "lineas": list(item.get("lineas") or []),
        "error": str_or_default(error, "Error no especificado."),
    }


def _item_exitoso_lote_armado_surtido(
    item: Dict[str, Any],
    codigo_movimiento: int,
    nro_comprobante: str,
    info_pack: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    cantidad = int(to_int_or_none(item.get("cantidad_packs")) or 0)
    info = info_pack or {}
    return {
        "id_articulo_pack": to_int_or_none(item.get("id_articulo_pack")),
        "codigo_articulo_pack": str_or_default(info.get("codigo_articulo_pack"), "") or None,
        "descripcion_articulo_pack": str_or_default(info.get("descripcion_articulo_pack"), "") or None,
        "descripcion_pack": _descripcion_pack_armado_surtido(info_pack, item),
        "cantidad_packs": cantidad,
        "cantidad_grabada": cantidad,
        "saldo_inicial": info.get("saldo_inicial"),
        "saldo_final": info.get("saldo_final"),
        "codigo_movimiento": int(codigo_movimiento),
        "nro_comprobante": str_or_default(nro_comprobante, "-"),
    }


def ejecutar_lote_armado(
    base_empresa: str,
    id_usuario: int,
    cabecera: Dict[str, Any],
    armados: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Orquestador unificado Armado 1ra/2da. Commit por ítem exitoso.
    """
    from mpr.models import MprArmadoLote

    modo = _normalizar_modo_armado(cabecera.get("modo"))
    cabecera = dict(cabecera or {})
    cabecera["modo"] = modo

    resultado: Dict[str, Any] = {"exitosos": [], "fallidos": [], "id_lote_armado": None}
    items = list(armados or [])
    if not items:
        resultado["fallidos"].append(_item_fallido_lote_armado_surtido({}, "Agregue al menos un armado al lote."))
        return resultado
    if not (base_empresa or "").strip():
        for item in items:
            resultado["fallidos"].append(_item_fallido_lote_armado_surtido(item, "Base de datos no indicada."))
        return resultado
    if not id_usuario:
        for item in items:
            resultado["fallidos"].append(_item_fallido_lote_armado_surtido(item, "Usuario no indicado."))
        return resultado

    deposito_origen = to_int_or_none(cabecera.get("deposito_origen"))
    deposito_destino = to_int_or_none(cabecera.get("deposito_destino"))
    id_operario = to_int_or_none(cabecera.get("id_operario"))
    id_lista_produccion = to_int_or_none(cabecera.get("id_lista_produccion"))
    detalle_lote = str_or_default(cabecera.get("detalle"), "").strip() or None

    ok_reglas, err_reglas = validar_reglas_lote_armado(
        items,
        modo=modo,
        deposito_origen=deposito_origen,
        deposito_destino=deposito_destino,
        id_operario=id_operario,
        require_non_empty=True,
        base_empresa=base_empresa,
    )
    if not ok_reglas:
        for item in items:
            resultado["fallidos"].append(_item_fallido_lote_armado_surtido(item, err_reglas or "Lote inválido."))
        return resultado

    lote_obj = MprArmadoLote.objects.create(
        base_empresa=(base_empresa or "").strip(),
        modo=modo,
        id_operario=id_operario,
        id_usuario=int(id_usuario),
        deposito_origen=int(deposito_origen or 0),
        deposito_destino=int(deposito_destino or 0),
        cantidad_items=len(items),
    )
    resultado["id_lote_armado"] = str(lote_obj.id)

    for item in items:
        id_articulo_pack = int(to_int_or_none(item.get("id_articulo_pack")) or 0)
        cantidad_packs = int(to_int_or_none(item.get("cantidad_packs")) or 0)
        lineas = list(item.get("lineas") or [])

        if modo == "1ra":
            if not articulo_habilitado_armado_1ra(base_empresa, id_articulo_pack):
                resultado["fallidos"].append(_item_fallido_lote_armado_surtido(
                    item, "El pack seleccionado no tiene BOM válido para Armado 1ra.",
                ))
                continue
            ok_bom, err_bom = validar_composicion_bom_1ra(base_empresa, id_articulo_pack, lineas)
            if not ok_bom:
                resultado["fallidos"].append(_item_fallido_lote_armado_surtido(item, err_bom or "BOM inválido."))
                continue
            detalle_mov = _detalle_mov_armado_1ra(
                id_articulo_pack, cantidad_packs, lineas, detalle=detalle_lote,
                id_lista_produccion=id_lista_produccion,
            )
        else:
            if not articulo_habilitado_armado_surtido(base_empresa, id_articulo_pack):
                resultado["fallidos"].append(_item_fallido_lote_armado_surtido(
                    item,
                    f"El pack seleccionado no tiene tipo_art_fab '{TIPO_ART_FAB_PACK_ARMADO_SURTIDO}'.",
                ))
                continue
            detalle_mov = _detalle_mov_armado_surtido(
                id_articulo_pack,
                cantidad_packs,
                lineas,
                detalle=detalle_lote,
                id_lista_produccion=id_lista_produccion,
            )

        try:
            lineas_enriquecidas: List[Dict[str, Any]] = []
            with get_connection(base_empresa) as conn:
                conn.autocommit(False)
                cursor = conn.cursor()
                ok_tx, codigo_mov, nro_comprobante, err_tx, lineas_enriquecidas, info_pack = _ejecutar_armado_surtido_tx(
                    cursor,
                    conn,
                    id_usuario=int(id_usuario),
                    id_articulo_pack=id_articulo_pack,
                    cantidad_packs=cantidad_packs,
                    deposito_origen=int(deposito_origen or 0),
                    deposito_destino=int(deposito_destino or 0),
                    lineas_composicion=lineas,
                    id_operario=id_operario,
                    id_lista_produccion=id_lista_produccion,
                    detalle_mov=detalle_mov,
                )
                if not ok_tx:
                    conn.rollback()
                    resultado["fallidos"].append(_item_fallido_lote_armado_surtido(
                        item, err_tx or "No se pudo ejecutar el armado.",
                    ))
                    continue
                conn.commit()

            if codigo_mov is None or nro_comprobante is None:
                resultado["fallidos"].append(_item_fallido_lote_armado_surtido(
                    item, "No se pudo confirmar el movimiento de armado.",
                ))
                continue

            guardar_composicion_armado_surtido(
                base_empresa,
                codigo_mov,
                id_articulo_pack,
                cantidad_packs,
                int(deposito_origen or 0),
                int(deposito_destino or 0),
                lineas_enriquecidas,
                int(id_usuario),
                id_operario=id_operario,
                id_lista_produccion=id_lista_produccion,
                detalle=detalle_mov,
                modo=modo,
                id_lote_armado=lote_obj.id,
            )
            resultado["exitosos"].append(_item_exitoso_lote_armado_surtido(
                item, codigo_mov, nro_comprobante, info_pack=info_pack,
            ))
        except MprSchemaError:
            raise
        except Exception as e:
            if "1054" in str(e) or "Unknown column" in str(e).lower():
                raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e
            logger.warning("ejecutar_lote_armado item %s: %s", id_articulo_pack, e, exc_info=True)
            resultado["fallidos"].append(_item_fallido_lote_armado_surtido(item, str(e)))

    lote_obj.cantidad_exitosos = len(resultado.get("exitosos") or [])
    lote_obj.cantidad_fallidos = len(resultado.get("fallidos") or [])
    lote_obj.save(update_fields=["cantidad_exitosos", "cantidad_fallidos"])
    return resultado


def ejecutar_lote_armado_surtido(
    base_empresa: str,
    id_usuario: int,
    cabecera: Dict[str, Any],
    armados: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Ejecuta lote FIFO de armados surtido (modo 2da).
    Commit por ítem exitoso y continuación ante errores de negocio.
    """
    cab = dict(cabecera or {})
    cab["modo"] = _normalizar_modo_armado(cab.get("modo"), default="2da")
    if cab["modo"] != "2da":
        cab["modo"] = "2da"
    return ejecutar_lote_armado(base_empresa, id_usuario, cab, armados)


# --- Imputación Armado 1ra (supervisor) ---


def _cantidad_imputada_mstock(base_empresa: str, codigo_movimiento: int) -> int:
    from django.db.models import Sum

    from mpr.models import MprImputacionArmado

    total = (
        MprImputacionArmado.objects.filter(
            base_empresa=(base_empresa or "").strip(),
            codigo_movimiento=int(codigo_movimiento),
        ).aggregate(s=Sum("cantidad"))["s"]
    )
    return int(total or 0)


def _bulk_nro_comprobante_movimientos(
    base_empresa: str, codigos: List[int]
) -> Dict[int, str]:
    if not codigos:
        return {}
    out: Dict[int, str] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "movimiento_stock")
            if not tbl:
                return {}
            ph = ",".join(["%s"] * len(codigos))
            cursor.execute(
                f"SELECT codigo_movimiento, nro_comprobante FROM {tbl} "
                f"WHERE codigo_movimiento IN ({ph})",
                codigos,
            )
            for row in cursor.fetchall() or []:
                cod = to_int_or_none(row.get("codigo_movimiento"))
                if cod is not None:
                    out[cod] = str_or_default(row.get("nro_comprobante"), str(cod))
    except Exception as e:
        logger.warning("_bulk_nro_comprobante_movimientos %s: %s", base_empresa, e)
    return out


def _bulk_etiquetas_articulos(
    base_empresa: str, ids: List[int]
) -> Dict[int, Dict[str, str]]:
    if not ids:
        return {}
    out: Dict[int, Dict[str, str]] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "articulo")
            if not tbl:
                return {}
            ph = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"""SELECT IDArt AS id_articulo,
                           COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo_articulo,
                           COALESCE(NombreArticulo, '') AS descripcion_articulo
                    FROM {tbl} WHERE IDArt IN ({ph})""",
                ids,
            )
            for row in cursor.fetchall() or []:
                aid = to_int_or_none(row.get("id_articulo"))
                if aid is not None:
                    out[aid] = {
                        "codigo_articulo": str_or_default(row.get("codigo_articulo"), "-"),
                        "descripcion_articulo": str_or_default(
                            row.get("descripcion_articulo"), "-"
                        ),
                    }
    except Exception as e:
        logger.warning("_bulk_etiquetas_articulos %s: %s", base_empresa, e)
    return out


def _listar_demanda_abierta_fifo(
    base_empresa: str, id_articulo: int, limit: int = 50
) -> List[Dict[str, Any]]:
    """Demanda abierta por artículo ordenada FIFO (fecha pedido ascendente)."""
    if not (base_empresa or "").strip() or not id_articulo:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            tbl_cli = _nombre_tabla(cursor, "cliente")
            if not tbl_detalle or not tbl_cp:
                return []
            pk_col = _demanda_detalle_pk_columna(cursor, tbl_detalle)
            join_cli = (
                f"LEFT JOIN {tbl_cli} cli ON cli.codigo = cp.codigo" if tbl_cli else ""
            )
            fk_agrupada_sql = ""
            if (
                columna_existe(cursor, tbl_detalle, "id_lista_produccion")
                and pk_col != "id_lista_produccion"
            ):
                fk_agrupada_sql = ", d.id_lista_produccion"
            sql = f"""
                SELECT d.codigo_movimiento_pedido,
                       COALESCE(d.cantidad_pendiente_prod, 0) AS cantidad_pendiente_prod,
                       d.`{pk_col}` AS id_fila_detalle
                       {fk_agrupada_sql},
                       cp.Fecha AS fecha,
                       COALESCE(cp.NroComprobante, cp.NroCompBusq, '') AS nro_pedido,
                       COALESCE(cli.nombre_cliente, '') AS nombre_cliente
                FROM {tbl_detalle} d
                INNER JOIN {tbl_cp} cp ON cp.CodigoMovimiento = d.codigo_movimiento_pedido
                {join_cli}
                WHERE d.id_articulo = %s
                  AND COALESCE(d.cantidad_pendiente_prod, 0) > 0
                  AND d.codigo_movimiento_pedido <> %s
                ORDER BY cp.Fecha ASC, d.codigo_movimiento_pedido ASC, d.`{pk_col}` ASC
                LIMIT %s
            """
            cursor.execute(
                sql,
                [id_articulo, COD_MOV_PEDIDO_DEMANDA_RESERVA, limit],
            )
            rows = cursor.fetchall() or []
        result = []
        for r in rows:
            item = {
                "codigo_movimiento_pedido": to_int_or_none(
                    r.get("codigo_movimiento_pedido")
                ),
                "cantidad_pendiente_prod": int(
                    float(r.get("cantidad_pendiente_prod") or 0)
                ),
                "nro_pedido": str_or_default(r.get("nro_pedido"), "-"),
                "nombre_cliente": str_or_default(r.get("nombre_cliente"), "-"),
            "id_lista_detalle": to_int_or_none(r.get("id_fila_detalle")),
            "id_fila_detalle": to_int_or_none(r.get("id_fila_detalle")),
            "id_lista_produccion": to_int_or_none(r.get("id_lista_produccion")),
            }
            fecha_val = r.get("fecha")
            if hasattr(fecha_val, "strftime"):
                item["fecha"] = fecha_val.strftime("%d/%m/%Y")
            else:
                item["fecha"] = str(fecha_val or "-")[:10]
            result.append(item)
        return result
    except Exception as e:
        logger.warning(
            "_listar_demanda_abierta_fifo %s art %s: %s",
            base_empresa,
            id_articulo,
            e,
            exc_info=True,
        )
        return []


def _actualizar_estado_imputacion_movimiento(
    movimiento,
    cantidad_imputada: int,
) -> None:
    from mpr.models import (
        ESTADO_IMPUTACION_COMPLETO,
        ESTADO_IMPUTACION_PARCIAL,
        ESTADO_IMPUTACION_PENDIENTE,
    )

    total = int(movimiento.cantidad_packs or 0)
    if cantidad_imputada <= 0:
        estado = ESTADO_IMPUTACION_PENDIENTE
    elif cantidad_imputada >= total:
        estado = ESTADO_IMPUTACION_COMPLETO
    else:
        estado = ESTADO_IMPUTACION_PARCIAL
    if movimiento.estado_imputacion != estado:
        movimiento.estado_imputacion = estado
        movimiento.save(update_fields=["estado_imputacion"])


def listar_mstock_pendientes_imputacion(
    base_empresa: str,
    filtros: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    MSTOCK Armado 1ra con imputación incompleta (Synap + legacy).
    Excluye Armado 2da.
    """
    from mpr.models import (
        ESTADO_IMPUTACION_COMPLETO,
        ESTADO_IMPUTACION_PARCIAL,
        ESTADO_IMPUTACION_PENDIENTE,
        MODO_ARMADO_1RA,
        MprArmadoSurtidoMovimiento,
    )

    if not (base_empresa or "").strip():
        return []
    filtros = filtros or {}
    qs = MprArmadoSurtidoMovimiento.objects.filter(
        base_empresa=(base_empresa or "").strip(),
        modo=MODO_ARMADO_1RA,
        estado_imputacion__in=[
            ESTADO_IMPUTACION_PENDIENTE,
            ESTADO_IMPUTACION_PARCIAL,
        ],
    ).select_related("id_lote_armado").order_by("-creado_en")

    id_lote_filtro = filtros.get("id_lote_armado")
    if id_lote_filtro:
        qs = qs.filter(id_lote_armado_id=id_lote_filtro)
    id_art_filtro = to_int_or_none(filtros.get("id_articulo_pack"))
    if id_art_filtro:
        qs = qs.filter(id_articulo_pack=int(id_art_filtro))

    movs = list(qs)
    if not movs:
        return []

    codigos = [m.codigo_movimiento for m in movs]
    ids_pack = list({m.id_articulo_pack for m in movs})
    nro_map = _bulk_nro_comprobante_movimientos(base_empresa, codigos)
    art_map = _bulk_etiquetas_articulos(base_empresa, ids_pack)

    resultado: List[Dict[str, Any]] = []
    for m in movs:
        imputado = _cantidad_imputada_mstock(base_empresa, m.codigo_movimiento)
        pendiente = int(m.cantidad_packs or 0) - imputado
        if pendiente <= 0:
            if m.estado_imputacion != ESTADO_IMPUTACION_COMPLETO:
                m.estado_imputacion = ESTADO_IMPUTACION_COMPLETO
                m.save(update_fields=["estado_imputacion"])
            continue
        art = art_map.get(m.id_articulo_pack, {})
        lote = m.id_lote_armado
        resultado.append({
            "codigo_movimiento": m.codigo_movimiento,
            "nro_comprobante": nro_map.get(m.codigo_movimiento, str(m.codigo_movimiento)),
            "id_articulo_pack": m.id_articulo_pack,
            "codigo_articulo_pack": art.get("codigo_articulo", str(m.id_articulo_pack)),
            "descripcion_articulo_pack": art.get("descripcion_articulo", ""),
            "cantidad_armada": int(m.cantidad_packs or 0),
            "cantidad_imputada": imputado,
            "cantidad_pendiente_imputar": pendiente,
            "creado_en": m.creado_en,
            "id_operario": m.id_operario,
            "id_lote_armado": str(lote.id) if lote else None,
            "lote_ejecutado_en": lote.ejecutado_en if lote else None,
            "estado_imputacion": m.estado_imputacion,
        })
    return resultado


def sugerir_imputacion_fifo(
    base_empresa: str, codigo_movimiento: int
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Sugiere líneas FIFO sobre demanda abierta del mismo pack.
    Retorna lista de {codigo_movimiento_pedido, cantidad, origen_regla, ...}.
    """
    from mpr.models import MODO_ARMADO_1RA, ORIGEN_REGLA_FIFO, MprArmadoSurtidoMovimiento

    cod = to_int_or_none(codigo_movimiento)
    if not cod:
        return [], "Movimiento no indicado."
    try:
        mov = MprArmadoSurtidoMovimiento.objects.get(
            base_empresa=(base_empresa or "").strip(),
            codigo_movimiento=int(cod),
            modo=MODO_ARMADO_1RA,
        )
    except MprArmadoSurtidoMovimiento.DoesNotExist:
        return [], "MSTOCK de Armado 1ra no encontrado."

    disponible = int(mov.cantidad_packs or 0) - _cantidad_imputada_mstock(
        base_empresa, int(cod)
    )
    if disponible <= 0:
        return [], "No queda cantidad pendiente de imputar en este MSTOCK."

    demanda = _listar_demanda_abierta_fifo(base_empresa, mov.id_articulo_pack)
    sugerencias: List[Dict[str, Any]] = []
    restante = disponible
    for d in demanda:
        if restante <= 0:
            break
        need = int(d.get("cantidad_pendiente_prod") or 0)
        if need <= 0:
            continue
        qty = min(restante, need)
        if qty <= 0:
            continue
        sugerencias.append({
            "codigo_movimiento_pedido": d["codigo_movimiento_pedido"],
            "cantidad": qty,
            "origen_regla": ORIGEN_REGLA_FIFO,
            "id_lista_detalle": d.get("id_lista_detalle"),
            "id_fila_detalle": d.get("id_fila_detalle") or d.get("id_lista_detalle"),
            "id_lista_produccion": d.get("id_lista_produccion"),
            "nro_pedido": d.get("nro_pedido"),
            "nombre_cliente": d.get("nombre_cliente"),
            "fecha_pedido": d.get("fecha"),
        })
        restante -= qty
    if not sugerencias:
        return [], "No hay demanda abierta para este artículo."
    return sugerencias, None


def confirmar_imputacion_armado(
    base_empresa: str,
    codigo_movimiento: int,
    lineas: List[Dict[str, Any]],
    id_supervisor: int,
) -> Tuple[bool, Optional[str]]:
    """
    Confirma imputación de un MSTOCK 1ra a uno o más pedidos.
    lineas: [{codigo_movimiento_pedido, cantidad, origen_regla, id_lista_detalle?, notas?}]
    """
    from mpr.models import (
        MODO_ARMADO_1RA,
        ORIGEN_REGLA_FIFO,
        ORIGEN_REGLA_MANUAL,
        MprArmadoSurtidoMovimiento,
        MprImputacionArmado,
    )

    if not (base_empresa or "").strip():
        return False, "Base de datos no indicada."
    if not id_supervisor:
        return False, "Supervisor no identificado."
    cod = to_int_or_none(codigo_movimiento)
    if not cod:
        return False, "Movimiento no indicado."
    if not lineas:
        return False, "Indique al menos una línea de imputación."

    try:
        mov = MprArmadoSurtidoMovimiento.objects.get(
            base_empresa=(base_empresa or "").strip(),
            codigo_movimiento=int(cod),
            modo=MODO_ARMADO_1RA,
        )
    except MprArmadoSurtidoMovimiento.DoesNotExist:
        return False, "MSTOCK de Armado 1ra no encontrado."

    ya_imputado = _cantidad_imputada_mstock(base_empresa, int(cod))
    total_nuevo = 0
    normalizadas: List[Dict[str, Any]] = []
    for ln in lineas:
        qty = int(to_int_or_none(ln.get("cantidad")) or 0)
        cod_ped = to_int_or_none(ln.get("codigo_movimiento_pedido"))
        if qty <= 0 or not cod_ped:
            continue
        regla = str(ln.get("origen_regla") or ORIGEN_REGLA_MANUAL).strip().upper()
        if regla not in (ORIGEN_REGLA_FIFO, ORIGEN_REGLA_MANUAL):
            regla = ORIGEN_REGLA_MANUAL
        normalizadas.append({
            "codigo_movimiento_pedido": int(cod_ped),
            "cantidad": qty,
            "origen_regla": regla,
            "id_lista_detalle": to_int_or_none(ln.get("id_lista_detalle")),
            "id_lista_produccion": to_int_or_none(ln.get("id_lista_produccion")),
            "notas": str_or_default(ln.get("notas"), "").strip()[:500],
        })
        total_nuevo += qty

    if not normalizadas:
        return False, "Las líneas de imputación no son válidas."
    if ya_imputado + total_nuevo > int(mov.cantidad_packs or 0):
        restante = max(0, int(mov.cantidad_packs or 0) - ya_imputado)
        return False, f"No puede imputar más de {restante} pack(s) en este MSTOCK."

    codigos_pedido = list({ln["codigo_movimiento_pedido"] for ln in normalizadas})
    registros_synap: List[Dict[str, Any]] = []

    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            cursor = conn.cursor()
            tbl_detalle = _nombre_tabla(cursor, "lista_produccion_detalle")
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_cp = _nombre_tabla(cursor, "comp_ped")
            pk_det = _demanda_detalle_pk_columna(cursor, tbl_detalle) if tbl_detalle else "id_lista_detalle"

            for ln in normalizadas:
                qty = ln["cantidad"]
                cod_ped = ln["codigo_movimiento_pedido"]
                id_fila = to_int_or_none(ln.get("id_lista_detalle"))

                if tbl_detalle:
                    pend_actual = _demanda_detalle_pendiente_actual(
                        cursor,
                        tbl_detalle,
                        pk_det,
                        id_fila=id_fila,
                        codigo_movimiento_pedido=int(cod_ped),
                        id_articulo=int(mov.id_articulo_pack),
                    )
                    if qty > pend_actual:
                        conn.rollback()
                        return False, (
                            f"La cantidad a imputar ({qty}) supera la demanda pendiente "
                            f"({pend_actual}) del pedido."
                        )
                    _demanda_detalle_decrementar_pendiente(
                        cursor,
                        tbl_detalle,
                        pk_det,
                        qty,
                        id_fila=id_fila,
                        codigo_movimiento_pedido=int(cod_ped),
                        id_articulo=int(mov.id_articulo_pack),
                    )

                id_lista = ln.get("id_lista_produccion")
                if tbl_agrupada and id_lista:
                    try:
                        cursor.execute(
                            f"UPDATE {tbl_agrupada} SET cantidad_pendiente_prod = "
                            f"GREATEST(0, COALESCE(cantidad_pendiente_prod, 0) - %s) "
                            f"WHERE id_lista_produccion = %s AND id_articulo = %s",
                            [qty, id_lista, mov.id_articulo_pack],
                        )
                    except Exception as agg_err:
                        logger.debug(
                            "Imputación: no se actualizó agrupada id_lista=%s: %s",
                            id_lista,
                            agg_err,
                        )

                registros_synap.append(ln)

            if tbl_cp and tbl_detalle and codigos_pedido:
                for cod_p in codigos_pedido:
                    try:
                        cursor.execute(
                            f"SELECT COALESCE(SUM(cantidad_pendiente_prod), 0) FROM {tbl_detalle} "
                            f"WHERE codigo_movimiento_pedido = %s",
                            [cod_p],
                        )
                        row = cursor.fetchone()
                        total_pend = int(float(row[0] or 0)) if row else 0
                        estado = (
                            ESTADO_PEDIDO_OPT_PARCIAL
                            if total_pend > 0
                            else ESTADO_PEDIDO_OPT_TERMINADO
                        )
                        _actualizar_comp_ped_estado_produccion(
                            cursor, tbl_cp, [cod_p], estado
                        )
                    except Exception as st_err:
                        logger.warning(
                            "Imputación: estado pedido cod=%s: %s", cod_p, st_err
                        )

            conn.commit()
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning(
            "confirmar_imputacion_armado cod=%s: %s", cod, e, exc_info=True
        )
        return False, str(e) or "Error al confirmar imputación."

    for ln in registros_synap:
        MprImputacionArmado.objects.create(
            base_empresa=(base_empresa or "").strip(),
            codigo_movimiento=int(cod),
            id_articulo_pack=int(mov.id_articulo_pack),
            cantidad=ln["cantidad"],
            codigo_movimiento_pedido=ln["codigo_movimiento_pedido"],
            id_lista_detalle=ln.get("id_lista_detalle"),
            origen_regla=ln["origen_regla"],
            id_usuario_supervisor=int(id_supervisor),
            notas=ln.get("notas") or "",
        )

    nuevo_total = ya_imputado + total_nuevo
    _actualizar_estado_imputacion_movimiento(mov, nuevo_total)
    return True, None


# --- Reportes MPR (solo lectura) ---


def reporte_mpr_pendiente(base_empresa: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Pendiente por artículo (lista_produccion_agrupada con cantidad_pendiente_prod > 0)."""
    return listar_lista_produccion_agrupada(
        base_empresa, limit=limit, excluir_filas_opt_liberadas_mstock=True
    )


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


# --- Stubs para reportes MPR (Spec/TDD): implementación pendiente ---


def reporte_mpr_pedidos_por_estado(base_empresa: str) -> List[Dict[str, Any]]:
    """Resumen de pedidos por estado_pedido_opt (Pendiente, Produccion, Parcial, Terminado). Ver ESPEC_MPR_PEDIDOS_ESTADO."""
    if not (base_empresa or "").strip():
        return []
    try:
        pedidos = listar_pedidos_fabrica(base_empresa, limit=500, estado=None)
        conteo = {"Pendiente": 0, "Produccion": 0, "Parcial": 0, "Terminado": 0}
        for p in pedidos:
            est = (p.get("estado_pedido_opt") or "").strip()
            if est in conteo:
                conteo[est] += 1
        return [
            {"estado": "Pendiente", "cantidad": conteo["Pendiente"]},
            {"estado": "Produccion", "cantidad": conteo["Produccion"]},
            {"estado": "Parcial", "cantidad": conteo["Parcial"]},
            {"estado": "Terminado", "cantidad": conteo["Terminado"]},
        ]
    except Exception as e:
        logger.warning("Error reporte_mpr_pedidos_por_estado en %s: %s", base_empresa, e, exc_info=True)
        return []


def reporte_mpr_brecha_demanda(base_empresa: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Demanda vs stock (brecha) por artículo. Ver ESPEC_MPR_BRECHA_DEMANDA."""
    if not (base_empresa or "").strip():
        return []
    try:
        filas = listar_ventana_pack(base_empresa, limit=limit * 2)
        result = []
        for r in filas:
            demanda = float(r.get("cantidad_pendiente_prod") or 0)
            stock_t = float(r.get("stock_terminado") or 0)
            a_fabricar = float(r.get("cantidad_a_fabricar") or 0)
            urgente_abs = float(r.get("cantidad_urgente_abs") or r.get("cantidad_urgente") or 0)
            result.append({
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "demanda_pendiente": demanda,
                "stock_terminado": stock_t,
                "cantidad_a_fabricar": max(0, a_fabricar),
                "urgente": 1 if urgente_abs > 0 else 0,
            })
        result.sort(key=lambda x: (-x["urgente"], -x["cantidad_a_fabricar"]))
        return result[:limit]
    except Exception as e:
        logger.warning("Error reporte_mpr_brecha_demanda en %s: %s", base_empresa, e, exc_info=True)
        return []


def reporte_mpr_movimientos(base_empresa: str, limit: int = 200) -> List[Dict[str, Any]]:
    """Movimientos de producción (OPT/OPP/OPA/Armado) en formato tabla. Ver ESPEC_MPR_MOVIMIENTOS_PRODUCCION."""
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
                else:
                    raise
            rows = cursor.fetchall()
        result = []
        for r in rows:
            tipo = (r.get("tipo_mov") or r.get("motivo_movimiento") or "").strip()
            if "OPT" in tipo or "Pedido" in (r.get("motivo_movimiento") or ""):
                tipo_mov = "OPT"
            elif "OPP" in tipo or "Parte" in (r.get("motivo_movimiento") or ""):
                tipo_mov = "OPP"
            elif "OPA" in tipo or "Armado" in tipo:
                tipo_mov = "OPA"
            else:
                tipo_mov = tipo or "Armado"
            detalle_raw = r.get("detalle")
            detalle_str = (str(detalle_raw)[:80] if detalle_raw else "") or "-"
            fecha = r.get("fecha")
            fecha_str = _formatear_fecha_dd_mm_yyyy(fecha) if fecha is not None else "-"
            result.append({
                "fecha": fecha_str,
                "tipo_mov": tipo_mov,
                "codigo_movimiento": r.get("codigo_movimiento"),
                "nro_comprobante": str_or_default(r.get("nro_comprobante"), "-"),
                "detalle": detalle_str,
            })
        return result
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error reporte_mpr_movimientos en %s: %s", base_empresa, e, exc_info=True)
        return []


def reporte_mpr_desperdicio(
    base_empresa: str,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """OPP a depósito desperdicio (Scrap). Ver ESPEC_MPR_DESPERDICIO."""
    if not (base_empresa or "").strip():
        return []
    cod_scrap = _get_deposito_por_tipo_mpr(base_empresa, TIPO_MPR_SCRAP)
    if cod_scrap is None:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_mov or not tbl_stock:
                return []
            where_fecha = ""
            params_mov = [cod_scrap, cod_scrap]
            if fecha_desde:
                where_fecha += " AND m.fecha >= %s"
                params_mov.append(fecha_desde)
            if fecha_hasta:
                where_fecha += " AND m.fecha <= %s"
                params_mov.append(fecha_hasta)
            params_mov.append(limit * 3)
            cursor.execute(
                f"""
                SELECT m.codigo_movimiento, m.nro_comprobante, m.fecha, m.detalle
                FROM {tbl_mov} m
                WHERE (UPPER(TRIM(COALESCE(m.tipo_mov,''))) = 'OPP' OR COALESCE(m.motivo_movimiento,'') = 'Parte producción')
                  AND (m.deposito_destino = %s OR (m.id_deposito_destino = %s AND 1=1))
                  AND COALESCE(m.anulado,'No') <> 'Si'
                  {where_fecha}
                ORDER BY m.codigo_movimiento DESC
                LIMIT %s
                """,
                params_mov,
            )
            movs = cursor.fetchall()
            if not movs:
                return []
            codigos = [to_int_or_none(m.get("codigo_movimiento")) for m in movs if m.get("codigo_movimiento") is not None]
            codigos = [c for c in codigos if c is not None]
            if not codigos:
                return []
            ph = ",".join(["%s"] * len(codigos))
            cursor.execute(
                f"""
                SELECT s.CodigoMovimiento, s.id_articulo, COALESCE(SUM(s.Entrada), 0) AS cantidad
                FROM {tbl_stock} s
                WHERE s.CodigoMovimiento IN ({ph})
                GROUP BY s.CodigoMovimiento, s.id_articulo
                """,
                codigos,
            )
            stock_rows = cursor.fetchall()
            id_arts = list({to_int_or_none(r.get("id_articulo")) for r in stock_rows if to_int_or_none(r.get("id_articulo")) is not None})
            nombres_art = {}
            if tbl_art and id_arts:
                ph_art = ",".join(["%s"] * len(id_arts))
                cursor.execute(
                    f"""
                    SELECT IDArt, COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo, COALESCE(NombreArticulo, '') AS nombre
                    FROM {tbl_art} WHERE IDArt IN ({ph_art})
                    """,
                    id_arts,
                )
                for r in cursor.fetchall():
                    aid = to_int_or_none(r.get("IDArt"))
                    if aid is not None:
                        nombres_art[aid] = str_or_default(r.get("codigo"), "-") + " " + str_or_default(r.get("nombre"), "")
            mov_by_cod = {to_int_or_none(m.get("codigo_movimiento")): m for m in movs if to_int_or_none(m.get("codigo_movimiento")) is not None}
            result = []
            for s in stock_rows:
                cod = to_int_or_none(s.get("CodigoMovimiento"))
                id_art = to_int_or_none(s.get("id_articulo"))
                qty = int(float(s.get("cantidad") or 0))
                if qty <= 0 or cod is None:
                    continue
                m = mov_by_cod.get(cod)
                if not m:
                    continue
                detalle = (m.get("detalle") or "") or ""
                opt_match = re.search(r"OPT\s*(\d+)", detalle, re.IGNORECASE)
                opt_asoc = opt_match.group(1) if opt_match else (str(m.get("nro_comprobante")) or "-")
                fecha_val = m.get("fecha")
                fecha_str = _formatear_fecha_dd_mm_yyyy(fecha_val) if fecha_val is not None else "-"
                articulo_str = (nombres_art.get(id_art) or str(id_art) if id_art is not None else "-").strip()
                result.append({
                    "articulo": articulo_str or "-",
                    "cantidad_desperdicio": qty,
                    "opt_asociada": opt_asoc,
                    "fecha": fecha_str,
                })
            return result[:limit]
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error reporte_mpr_desperdicio en %s: %s", base_empresa, e, exc_info=True)
        return []


def reporte_mpr_produccion_por_operario(
    base_empresa: str,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Producción por operario desde eventos reales (OPP/OPA) en lista_produccion_historico."""
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_historico = _nombre_tabla(cursor, "lista_produccion_historico")
            tbl_empleado = _nombre_tabla(cursor, "sue_abm_empleado")
            if not tbl_historico:
                return []
            sql = f"""
                SELECT COALESCE(h.id_operario_opt, h.id_operario) AS id_operario_efectivo,
                       COUNT(*) AS nro_eventos,
                       COALESCE(SUM(
                           CASE
                               WHEN UPPER(TRIM(COALESCE(h.tipo_evento, ''))) = 'OPP' THEN COALESCE(h.cantidad_movimiento, 0)
                               WHEN UPPER(TRIM(COALESCE(h.tipo_evento, ''))) IN ('OPA', 'ARMADO') THEN COALESCE(h.cantidad_armada, 0)
                               ELSE 0
                           END
                       ), 0) AS cantidad_packs
                FROM {tbl_historico} h
                WHERE COALESCE(h.id_operario_opt, h.id_operario) IS NOT NULL
                  AND UPPER(TRIM(COALESCE(h.tipo_evento, ''))) IN ('OPP', 'OPA', 'ARMADO')
            """
            params: List[Any] = []
            if fecha_desde:
                sql += " AND h.fecha >= %s"
                params.append(to_date_or_none(fecha_desde) or str(fecha_desde)[:10])
            if fecha_hasta:
                sql += " AND h.fecha <= %s"
                params.append(to_date_or_none(fecha_hasta) or str(fecha_hasta)[:10])
            sql += (
                " GROUP BY COALESCE(h.id_operario_opt, h.id_operario) "
                "ORDER BY nro_eventos DESC, cantidad_packs DESC LIMIT %s"
            )
            params.append(limit)
            try:
                cursor.execute(sql, params)
            except Exception as ex_hist:
                if "1054" not in str(ex_hist) and "unknown column" not in str(ex_hist).lower():
                    raise
                sql_fb = f"""
                    SELECT h.id_operario AS id_operario_efectivo,
                           COUNT(*) AS nro_eventos,
                           COALESCE(SUM(
                               CASE
                                   WHEN UPPER(TRIM(COALESCE(h.tipo_evento, ''))) = 'OPP' THEN COALESCE(h.cantidad_movimiento, 0)
                                   WHEN UPPER(TRIM(COALESCE(h.tipo_evento, ''))) IN ('OPA', 'ARMADO') THEN COALESCE(h.cantidad_armada, 0)
                                   ELSE 0
                               END
                           ), 0) AS cantidad_packs
                    FROM {tbl_historico} h
                    WHERE h.id_operario IS NOT NULL
                      AND UPPER(TRIM(COALESCE(h.tipo_evento, ''))) IN ('OPP', 'OPA', 'ARMADO')
                """
                params_fb: List[Any] = []
                if fecha_desde:
                    sql_fb += " AND h.fecha >= %s"
                    params_fb.append(to_date_or_none(fecha_desde) or str(fecha_desde)[:10])
                if fecha_hasta:
                    sql_fb += " AND h.fecha <= %s"
                    params_fb.append(to_date_or_none(fecha_hasta) or str(fecha_hasta)[:10])
                sql_fb += (
                    " GROUP BY h.id_operario "
                    "ORDER BY nro_eventos DESC, cantidad_packs DESC LIMIT %s"
                )
                params_fb.append(limit)
                cursor.execute(sql_fb, params_fb)
            rows = cursor.fetchall()
            id_operarios = list({
                to_int_or_none(r.get("id_operario_efectivo"))
                for r in rows
                if to_int_or_none(r.get("id_operario_efectivo")) is not None
            })
            nombres = {}
            if tbl_empleado and id_operarios:
                ph = ",".join(["%s"] * len(id_operarios))
                cursor.execute(
                    f"""
                    SELECT id_sue_abm_empleado, COALESCE(nombre_empleado, '') AS nombre_empleado
                    FROM {tbl_empleado}
                    WHERE id_sue_abm_empleado IN ({ph}) AND COALESCE(anulado, 'No') = 'No'
                    """,
                    id_operarios,
                )
                for r in cursor.fetchall():
                    oid = to_int_or_none(r.get("id_sue_abm_empleado"))
                    if oid is not None:
                        nombres[oid] = str_or_default(r.get("nombre_empleado"), "-").strip() or f"Operario {oid}"
            result = []
            for r in rows:
                oid = to_int_or_none(r.get("id_operario_efectivo"))
                nro = int(float(r.get("nro_eventos") or 0))
                packs = int(float(r.get("cantidad_packs") or 0))
                result.append({
                    "operario": nombres.get(oid, f"Operario {oid}" if oid is not None else "Sin asignar"),
                    "nro_opt_asignadas": nro,
                    "cantidad_packs": packs,
                })
            return result
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error reporte_mpr_produccion_por_operario en %s: %s", base_empresa, e, exc_info=True)
        return []


def reporte_mpr_opt_cerradas(
    base_empresa: str,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """OPT cerradas (en_proceso='No', pendiente=0). Ver ESPEC_MPR_OPT_CERRADAS."""
    if not (base_empresa or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            tbl_articulo = _nombre_tabla(cursor, "articulo")
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            if not tbl_agrupada or not tbl_articulo:
                return []
            # OPT cerradas: en_proceso='No' y cantidad_pendiente_prod=0 (por id_lista)
            has_codigo_mov_opt = True
            try:
                cursor.execute(
                    f"""
                    SELECT l.id_lista_produccion, l.id_articulo, l.codigo_movimiento_opt,
                           COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                           COALESCE(a.NombreArticulo, '') AS nombre_articulo,
                           COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida
                    FROM {tbl_agrupada} l
                    INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                    WHERE UPPER(TRIM(COALESCE(l.en_proceso_produccion, ''))) = 'NO'
                      AND COALESCE(l.cantidad_pendiente_prod, 0) = 0
                      AND l.id_lista_produccion IN (
                          SELECT g.id_lista_produccion FROM {tbl_agrupada} g
                          GROUP BY g.id_lista_produccion
                          HAVING COALESCE(SUM(g.cantidad_pendiente_prod), 0) = 0
                            AND MAX(CASE WHEN UPPER(TRIM(COALESCE(g.en_proceso_produccion, ''))) = 'NO' THEN 1 ELSE 0 END) = 1
                      )
                    ORDER BY l.id_lista_produccion DESC, l.id_articulo
                    LIMIT %s
                    """,
                    [limit * 10],
                )
            except Exception as e1:
                if "1054" in str(e1) or "Unknown column" in str(e1).lower() or "codigo_movimiento_opt" in str(e1):
                    has_codigo_mov_opt = False
                    cursor.execute(
                        f"""
                        SELECT l.id_lista_produccion, l.id_articulo,
                               COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                               COALESCE(a.NombreArticulo, '') AS nombre_articulo,
                               COALESCE(l.cantidad_pedida, 0) AS cantidad_pedida
                        FROM {tbl_agrupada} l
                        INNER JOIN {tbl_articulo} a ON a.IDArt = l.id_articulo
                        WHERE UPPER(TRIM(COALESCE(l.en_proceso_produccion, ''))) = 'NO'
                          AND COALESCE(l.cantidad_pendiente_prod, 0) = 0
                          AND l.id_lista_produccion IN (
                              SELECT g.id_lista_produccion FROM {tbl_agrupada} g
                              GROUP BY g.id_lista_produccion
                              HAVING COALESCE(SUM(g.cantidad_pendiente_prod), 0) = 0
                                AND MAX(CASE WHEN UPPER(TRIM(COALESCE(g.en_proceso_produccion, ''))) = 'NO' THEN 1 ELSE 0 END) = 1
                          )
                        ORDER BY l.id_lista_produccion DESC, l.id_articulo
                        LIMIT %s
                        """,
                        [limit * 10],
                    )
                else:
                    raise
            rows = cursor.fetchall()
            by_lista = {}
            for r in rows:
                id_lista = to_int_or_none(r.get("id_lista_produccion"))
                if id_lista is None:
                    continue
                if id_lista not in by_lista:
                    by_lista[id_lista] = {
                        "articulos": [],
                        "cantidad_total": 0,
                        "codigo_movimiento_opt": to_int_or_none(r.get("codigo_movimiento_opt")) if has_codigo_mov_opt else None,
                    }
                art_str = (str_or_default(r.get("codigo_articulo"), "") + " " + str_or_default(r.get("nombre_articulo"), "")).strip()
                if art_str:
                    by_lista[id_lista]["articulos"].append(art_str)
                by_lista[id_lista]["cantidad_total"] += int(float(r.get("cantidad_pedida") or 0))
            if not by_lista:
                return []
            # Fecha cierre: max fecha movimiento_stock por codigo_movimiento_opt
            codigos_mov = list({
                v["codigo_movimiento_opt"]
                for v in by_lista.values()
                if _mpr_es_codigo_movimiento_opt_mstock(v.get("codigo_movimiento_opt"))
            })
            fechas_opt = {}
            if tbl_mov and codigos_mov and has_codigo_mov_opt:
                ph = ",".join(["%s"] * len(codigos_mov))
                where_fecha = ""
                params_mov = list(codigos_mov)
                if fecha_desde:
                    where_fecha += " AND m.fecha >= %s"
                    params_mov.append(fecha_desde)
                if fecha_hasta:
                    where_fecha += " AND m.fecha <= %s"
                    params_mov.append(fecha_hasta)
                cursor.execute(
                    f"""
                    SELECT m.codigo_movimiento, MAX(m.fecha) AS fecha_max
                    FROM {tbl_mov} m
                    WHERE m.codigo_movimiento IN ({ph}) AND COALESCE(m.anulado, 'No') <> 'Si' {where_fecha}
                    GROUP BY m.codigo_movimiento
                    """,
                    params_mov,
                )
                for r in cursor.fetchall():
                    cod = to_int_or_none(r.get("codigo_movimiento"))
                    if cod is not None:
                        fechas_opt[cod] = r.get("fecha_max")
            result = []
            for id_lista, data in sorted(by_lista.items(), key=lambda x: -x[0])[:limit]:
                cod_mov = data.get("codigo_movimiento_opt")
                fecha_cierre = fechas_opt.get(cod_mov) if cod_mov is not None else None
                if fecha_desde or fecha_hasta:
                    if fecha_cierre is None:
                        continue
                    fecha_str = str(fecha_cierre)[:10] if fecha_cierre else ""
                    if fecha_desde and fecha_str < fecha_desde:
                        continue
                    if fecha_hasta and fecha_str > fecha_hasta:
                        continue
                articulos_str = ", ".join(data["articulos"][:5]) if data["articulos"] else "-"
                if len(data["articulos"]) > 5:
                    articulos_str += "…"
                    result.append({
                    "id_opt": id_lista,
                    "articulos": articulos_str,
                    "cantidad_total": data["cantidad_total"],
                    "fecha_cierre": _formatear_fecha_dd_mm_yyyy(fecha_cierre) if fecha_cierre is not None else "-",
                })
            return result
    except MprSchemaError:
        raise
    except Exception as e:
        logger.warning("Error reporte_mpr_opt_cerradas en %s: %s", base_empresa, e, exc_info=True)
        return []


# ---------------------------------------------------------------------------
# ETAPA 2: Tablero de Demanda Consolidado por Artículo
# ---------------------------------------------------------------------------

def _query_enviado_packs(
    cursor,
    tbl_agrupada: str,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
) -> Dict[int, float]:
    """
    Retorna {id_articulo: sum(cantidad_asignada_opt)} para packs con OPT formalmente
    liberada (codigo_movimiento_opt > 0) en el rango de fechas indicado.

    Si la columna codigo_movimiento_opt no existe, retorna {} (compatible con bases
    sin la columna opcional).
    """
    try:
        opts = _columnas_opcionales_op_agrupada(cursor, tbl_agrupada)
        col_cod_mov = opts.get("codigo_movimiento_opt")
        if not col_cod_mov:
            return {}
        col_fecha = opts.get("fecha_objetivo")
        where_fecha = ""
        params: List = []
        if col_fecha and fecha_desde:
            where_fecha += f" AND {col_fecha} >= %s"
            params.append(fecha_desde)
        if col_fecha and fecha_hasta:
            where_fecha += f" AND {col_fecha} <= %s"
            params.append(fecha_hasta)
        cursor.execute(
            f"""
            SELECT id_articulo, COALESCE(SUM(COALESCE(cantidad_asignada_opt, 0)), 0) AS total_env
            FROM {tbl_agrupada}
            WHERE COALESCE(`{col_cod_mov}`, 0) > 0
              AND COALESCE(cantidad_asignada_opt, 0) > 0
              {where_fecha}
            GROUP BY id_articulo
            """,
            params,
        )
        result: Dict[int, float] = {}
        for r in cursor.fetchall() or []:
            aid = to_int_or_none(r.get("id_articulo") if isinstance(r, dict) else r[0])
            if aid is not None:
                try:
                    result[aid] = float(r.get("total_env", 0) if isinstance(r, dict) else r[1] or 0)
                except (TypeError, ValueError):
                    result[aid] = 0.0
        return result
    except Exception as e:
        logger.debug("_query_enviado_packs error: %s", e)
        return {}


def _pivot_stock_por_tipo_mpr(
    base_empresa: str,
    ids_articulo: List[int],
) -> Tuple[Dict[int, Dict[str, float]], Dict[int, Dict[str, float]]]:
    """
    Consulta pivote única para los 6 tipos MPR físicos. Una sola round-trip SQL.

    Devuelve una tupla ``(stock, stock_suma)``:
    - ``stock``: {id_articulo: {tipo_mpr: saldo}} con el saldo real de cada etapa
      (todos los depósitos de ese tipo). Alimenta las columnas por etapa del tablero.
    - ``stock_suma``: {id_articulo: {tipo_mpr: saldo_que_suma}} con el saldo únicamente
      de los depósitos con ``suma_stock='Si'``. Alimenta la columna Total (respeta el
      flag de configuración de cada depósito, igual que el resto del sistema).
    """
    ids = [x for x in (to_int_or_none(i) for i in (ids_articulo or [])) if x is not None]
    if not ids or not (base_empresa or "").strip():
        return {}, {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            if not tbl_sd or not tbl_dep:
                return {}, {}
            ph = ",".join(["%s"] * len(ids))
            tipos_validos = (
                TIPO_MPR_PRODUCCION,
                TIPO_MPR_PLANCHADO,
                TIPO_MPR_2DA_SELECCION,
                TIPO_MPR_SEMI_ELABORADO,
                TIPO_MPR_TERMINADO,
                TIPO_MPR_SCRAP,
            )
            tipos_ph = ",".join(["%s"] * len(tipos_validos))
            cursor.execute(
                f"""
                SELECT sd.id_articulo, d.tipo_mpr,
                       COALESCE(SUM(sd.saldo), 0) AS saldo,
                       COALESCE(SUM(CASE WHEN COALESCE(d.suma_stock, 'Si') = 'Si'
                                         THEN sd.saldo ELSE 0 END), 0) AS saldo_suma
                FROM {tbl_sd} sd
                INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
                  AND COALESCE(d.anulado, 'No') = 'No'
                  AND d.tipo_mpr IN ({tipos_ph})
                WHERE sd.id_articulo IN ({ph})
                GROUP BY sd.id_articulo, d.tipo_mpr
                """,
                list(tipos_validos) + ids,
            )
            from collections import defaultdict
            stock: Dict[int, Dict[str, float]] = defaultdict(lambda: {t: 0.0 for t in tipos_validos})
            stock_suma: Dict[int, Dict[str, float]] = defaultdict(lambda: {t: 0.0 for t in tipos_validos})
            for r in cursor.fetchall() or []:
                aid = to_int_or_none(r.get("id_articulo"))
                tipo = str(r.get("tipo_mpr") or "")
                if aid is not None and tipo:
                    try:
                        stock[aid][tipo] = float(r.get("saldo") or 0)
                    except (TypeError, ValueError):
                        stock[aid][tipo] = 0.0
                    try:
                        stock_suma[aid][tipo] = float(r.get("saldo_suma") or 0)
                    except (TypeError, ValueError):
                        stock_suma[aid][tipo] = 0.0
            return dict(stock), dict(stock_suma)
    except Exception as e:
        logger.warning("_pivot_stock_por_tipo_mpr error: %s", e)
        return {}, {}


def _enviado_produccion_por_componente(
    enviado_pack_map: Dict[int, float],
    abm_map: Dict[int, int],
    bom_map: Dict[int, Any],
) -> Dict[int, float]:
    """
    Explota la cantidad de OPT liberada (nivel pack) a componentes vía BOM.

    PROVISIONAL en etapa 2: aproxima OPT_liberado_acumulado al nivel componente.
    # ETAPA 4-5: refinar enviado → usar ledger OPT_liberado_acumulado - OPP_registrado
                  cuando ejecutar_liberar_opt() deje de escribir a stock_deposito.

    Función pura sin I/O; testeable con mocks.
    """
    result: Dict[int, float] = {}
    for id_pack, cant_opt in (enviado_pack_map or {}).items():
        try:
            cant_opt_f = float(cant_opt or 0)
        except (TypeError, ValueError):
            cant_opt_f = 0.0
        if cant_opt_f <= 0:
            continue
        id_en_abm = abm_map.get(id_pack)
        if id_en_abm is None:
            continue
        bom = bom_map.get(id_en_abm)
        if not bom or not bom.get("componentes"):
            continue
        for comp in bom["componentes"]:
            id_comp = to_int_or_none(comp.get("id_articulo"))
            if id_comp is None:
                continue
            try:
                coef = float(comp.get("cantidad_articulo") or 0)
            except (TypeError, ValueError):
                coef = 0.0
            if coef <= 0:
                continue
            result[id_comp] = result.get(id_comp, 0.0) + coef * cant_opt_f
    return result


def _fetch_descripciones_articulo(
    base_empresa: str,
    ids_articulo: List[int],
) -> Dict[int, Tuple[str, str]]:
    """
    Retorna {id_articulo: (codigo_manual, descripcion)} para los artículos dados.
    """
    ids = [x for x in (to_int_or_none(i) for i in (ids_articulo or [])) if x is not None]
    if not ids or not (base_empresa or "").strip():
        return {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "articulo")
            if not tbl:
                return {}
            ph = ",".join(["%s"] * len(ids))
            cursor.execute(
                f"""
                SELECT IDArt AS id_articulo,
                       COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS id_manual,
                       COALESCE(NombreArticulo, '') AS descripcion
                FROM {tbl}
                WHERE IDArt IN ({ph})
                """,
                ids,
            )
            result: Dict[int, Tuple[str, str]] = {}
            for r in cursor.fetchall() or []:
                aid = to_int_or_none(r.get("id_articulo"))
                if aid is not None:
                    result[aid] = (
                        str_or_default(r.get("id_manual"), "-"),
                        str_or_default(r.get("descripcion"), "-"),
                    )
            return result
    except Exception as e:
        logger.warning("_fetch_descripciones_articulo error: %s", e)
        return {}


# =============================================================================
# Etapa 7: Envío directo a producción desde el Tablero (ledger-componente)
# =============================================================================


def _query_enviado_tablero_componente(
    base_empresa: str,
    comp_ids: List[int],
) -> Dict[int, Decimal]:
    """Suma de envíos directos al tablero por componente (no anulados).

    Backward-safe: retorna {} si comp_ids vacío o sin registros.
    """
    from django.db.models import Sum
    from mpr.models import MprEnvioProduccion

    if not base_empresa or not comp_ids:
        return {}
    qs = (
        MprEnvioProduccion.objects.filter(
            base_empresa=base_empresa,
            id_articulo__in=comp_ids,
            anulado=False,
        )
        .values("id_articulo")
        .annotate(total=Sum("cantidad"))
    )
    return {row["id_articulo"]: row["total"] for row in qs}


def _query_enviados_todos_componentes(
    base_empresa: str,
) -> Dict[int, "Decimal"]:
    """Suma envíos activos por componente para toda la empresa (sin filtro __in).

    Uso exclusivo: construir_grilla_parte. No reemplaza _query_enviado_tablero_componente.
    """
    from django.db.models import Sum
    from mpr.models import MprEnvioProduccion

    if not (base_empresa or "").strip():
        return {}
    qs = (
        MprEnvioProduccion.objects
        .filter(base_empresa=base_empresa, anulado=False)
        .values("id_articulo")
        .annotate(total=Sum("cantidad"))
    )
    return {row["id_articulo"]: row["total"] for row in qs}


def enviar_a_produccion_lote(
    base_empresa: str,
    id_usuario: int,
    items: List[Tuple[int, "Decimal"]],
    pendientes: Optional[Dict[int, "Decimal"]] = None,
) -> Tuple[bool, int, List[str], Optional[str]]:
    """Crea N registros MprEnvioProduccion en transacción atómica.

    - Omite filas con cantidad <= 0 (warning, no error).
    - Warning no-bloqueante si cantidad > pendiente (si pendientes provisto).
    - NO escribe en MySQL legacy (ledger-only Synap Postgres).

    Args:
        base_empresa: Scope de empresa.
        id_usuario: ID usuario AdministraNET.
        items: Lista de (id_articulo, cantidad).
        pendientes: Mapa {id_articulo: pendiente} para warnings de sobreenvío.

    Returns:
        (ok, n_creados, warnings, error|None)
    """
    from django.db import transaction
    from mpr.models import MprEnvioProduccion

    pendientes = pendientes or {}
    warnings_list: List[str] = []
    to_create: List[MprEnvioProduccion] = []

    for id_art, cantidad in items:
        id_art_int = to_int_or_none(id_art)
        qty = to_decimal_or_none(cantidad)
        if id_art_int is None or qty is None or qty <= Decimal("0"):
            warnings_list.append(
                f"Artículo {id_art}: cantidad inválida o cero, omitido."
            )
            continue
        pend = pendientes.get(id_art_int)
        if pend is not None:
            pend_dec = to_decimal_or_none(pend)
            if pend_dec is not None and qty > pend_dec:
                warnings_list.append(
                    f"Artículo {id_art_int}: cantidad {qty} supera pendiente"
                    f" {pend_dec} — enviado igual."
                )
        to_create.append(
            MprEnvioProduccion(
                base_empresa=str_or_default(base_empresa, "-"),
                id_articulo=id_art_int,
                cantidad=qty,
                id_usuario=id_usuario or 0,
            )
        )

    if not to_create:
        return True, 0, warnings_list, None

    try:
        with transaction.atomic():
            MprEnvioProduccion.objects.bulk_create(to_create)
        return True, len(to_create), warnings_list, None
    except Exception as exc:
        logger.error(
            "enviar_a_produccion_lote: error: %s", exc, exc_info=True
        )
        return False, 0, warnings_list, str(exc)


def listar_tablero_por_articulo(
    base_empresa: str,
    *,
    fecha_desde: Optional[date] = None,
    fecha_hasta: Optional[date] = None,
    solo_pendiente: bool = False,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """
    Tablero de demanda consolidado por artículo/componente. 10 columnas del pipeline MPR.

    Algoritmo (14 pasos):
    1.  listar_ventana_pack(base, limit*2, fecha_desde, fecha_hasta) → filas_pack (demanda pendiente)
    2.  _query_enviado_packs(cursor, tbl_agrupada, fecha_desde, fecha_hasta) → enviado_pack_map
    3.  art_ids = union(filas_pack.id_articulo, enviado_pack_map.keys())
    4.  abm_map = bulk_id_en_abm(base, art_ids)  — único batch ABM
    5.  bom_map = bulk_bom_detalle(base, abm_map.values())  — único batch BOM
    6.  dem_ped, dem_res = _explosion_demanda_componentes_pedido_reserva_pack(filas_pack, abm_map, bom_map)
    7.  enviado_comp = _enviado_produccion_por_componente(enviado_pack_map, abm_map, bom_map)
    8.  comp_ids = set(dem_ped) | set(dem_res)  — solo componentes con demanda
    9.  stock_pivot = _pivot_stock_por_tipo_mpr(base, list(comp_ids))  — 1 round-trip
    10. desc_map = _fetch_descripciones_articulo(base, list(comp_ids))  — 1 query
    11. Por cada comp_id construir fila con 10 columnas canónicas
    12. sort(key=lambda r: -r['pendiente'])
    13. if solo_pendiente: filtrar r['pendiente'] > 0
    14. return[:limit]

    Shape de fila retornada:
        id_articulo, codigo_manual, descripcion_articulo, demanda, urgente,
        pendiente, enviado (max(0, OPT_liberado_acum − OPP_parte_acum), por BOM a componente),
        produccion, planchado, segunda_seleccion, semi_elaborado, desperdicio,
        terminado, total.

    Columna Enviado: fórmula definitiva Etapa 4 — max(0, OPT_liberado_acumulado − OPP_parte_acumulado),
    explotada por BOM al nivel componente (paso 2b + paso 7).
    """
    from mpr.pipeline import TIPOS_QUE_SUMAN_STOCK

    if not (base_empresa or "").strip():
        return []

    # Paso 1: demanda pendiente de packs
    filas_pack = listar_ventana_pack(base_empresa, limit=limit * 2,
                                     fecha_desde=str(fecha_desde) if fecha_desde else None,
                                     fecha_hasta=str(fecha_hasta) if fecha_hasta else None)

    # Paso 2: packs con OPT liberada (OPT_liberado_acumulado)
    enviado_pack_map: Dict[int, float] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_agrupada = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if tbl_agrupada:
                enviado_pack_map = _query_enviado_packs(
                    cursor, tbl_agrupada, fecha_desde, fecha_hasta
                )
    except Exception as e:
        logger.debug("listar_tablero_por_articulo: error obteniendo enviado packs: %s", e)

    # Paso 2b: descontar OPP-parte acumulado → fórmula definitiva Enviado (Etapa 4)
    # Sólo se ejecuta cuando hay packs con OPT liberada; backward-safe si enviado_pack_map vacío.
    if enviado_pack_map:
        try:
            opp_map = opp_parte_acumulado_por_pack(base_empresa, list(enviado_pack_map))
            if opp_map:
                all_aids = set(enviado_pack_map) | set(opp_map)
                enviado_pack_map = {
                    aid: max(0.0, enviado_pack_map.get(aid, 0.0) - float(opp_map.get(aid, Decimal("0"))))
                    for aid in all_aids
                }
        except Exception as e:
            logger.debug("listar_tablero_por_articulo: error en paso 2b OPP-parte: %s", e)

    # Paso 3: union de artículos (packs con demanda + packs con OPT)
    art_ids: List[int] = []
    seen: Set[int] = set()
    for fp in filas_pack:
        aid = to_int_or_none(fp.get("id_articulo"))
        if aid is not None and aid not in seen:
            art_ids.append(aid)
            seen.add(aid)
    for aid in enviado_pack_map:
        if aid not in seen:
            art_ids.append(aid)
            seen.add(aid)

    if not art_ids:
        return []

    # Paso 4: ABM map (incluye packs sin ensamblado=Si para explosión BOM)
    abm_map = bulk_id_en_abm(base_empresa, art_ids, requiere_ensamblado_si=False)

    # Paso 5: BOM map
    id_en_abms = [v for v in abm_map.values() if v is not None]
    bom_map = bulk_bom_detalle(base_empresa, id_en_abms)

    # Paso 6: explosión demanda pack → componentes
    dem_ped, dem_res = _explosion_demanda_componentes_pedido_reserva_pack(
        filas_pack, abm_map, bom_map
    )

    # Paso 7: explosión enviado (OPT) pack → componentes
    enviado_comp = _enviado_produccion_por_componente(enviado_pack_map, abm_map, bom_map)

    # Paso 8: conjunto de componentes con demanda derivada
    comp_ids: Set[int] = set(dem_ped.keys()) | set(dem_res.keys())
    if not comp_ids:
        return []

    # Paso 7b: envíos directos tablero nivel COMPONENTE (E7, backward-safe)
    envios_tablero: Dict[int, Decimal] = {}
    if comp_ids:
        try:
            envios_tablero = _query_enviado_tablero_componente(base_empresa, list(comp_ids))
        except Exception as _e7b:
            logger.debug("listar_tablero_por_articulo paso 7b: %s", _e7b)

    # Paso 9: stock físico pivote por tipo MPR (saldo real por etapa + saldo que suma stock)
    stock_pivot, stock_suma_pivot = _pivot_stock_por_tipo_mpr(base_empresa, list(comp_ids))

    # Paso 10: descripciones de artículos componentes
    desc_map = _fetch_descripciones_articulo(base_empresa, list(comp_ids))

    # Paso 11: construir filas
    filas: List[Dict[str, Any]] = []
    tipos_suma = TIPOS_QUE_SUMAN_STOCK
    for comp_id in comp_ids:
        demanda = dem_ped.get(comp_id, 0.0) + dem_res.get(comp_id, 0.0)
        urgente = dem_ped.get(comp_id, 0.0)
        # Enviado = OPT path (E4) + envíos directos tablero (E7), sin doble conteo
        enviado_opt = enviado_comp.get(comp_id, 0.0)
        stock_comp = stock_pivot.get(comp_id, {})
        suma_comp = stock_suma_pivot.get(comp_id, {})
        produccion = stock_comp.get(TIPO_MPR_PRODUCCION, 0.0)
        segunda_seleccion = stock_comp.get(TIPO_MPR_2DA_SELECCION, 0.0)
        semi_elaborado = stock_comp.get(TIPO_MPR_SEMI_ELABORADO, 0.0)
        desperdicio = stock_comp.get(TIPO_MPR_SCRAP, 0.0)
        terminado = stock_comp.get(TIPO_MPR_TERMINADO, 0.0)
        # Total: suma del saldo que suma stock (respeta deposito.suma_stock por depósito),
        # restringido a los tipos físicos que integran el Total (excluye Desperdicio/Scrap).
        total = sum(
            suma_comp.get(t, 0.0)
            for t in tipos_suma
        )
        # Fórmula E7: Enviado_tablero = max(0, SUM(envíos_tablero) − stock_produccion)
        # Evita doble conteo: los envíos tablero que ya generaron parte se reflejan en stock_prod.
        stock_prod = stock_comp.get(TIPO_MPR_PRODUCCION, 0.0)
        envios_dir = float(envios_tablero.get(comp_id, Decimal("0")))
        enviado_tablero_val = max(0.0, envios_dir - stock_prod)
        enviado = enviado_opt + enviado_tablero_val
        pendiente = max(0.0, demanda - (enviado + total))
        codigo_manual, descripcion = desc_map.get(comp_id, ("-", "-"))
        filas.append({
            "id_articulo": comp_id,
            "codigo_manual": codigo_manual,
            "descripcion_articulo": descripcion,
            "demanda": demanda,
            "urgente": urgente,
            "pendiente": pendiente,
            "enviado": enviado,
            "produccion": produccion,
            "segunda_seleccion": segunda_seleccion,
            "semi_elaborado": semi_elaborado,
            "desperdicio": desperdicio,
            "terminado": terminado,
            "total": total,
        })

    # Paso 12: ordenar por pendiente descendente (más críticos primero)
    filas.sort(key=lambda r: -r["pendiente"])

    # Paso 13: filtro opcional solo con pendiente
    if solo_pendiente:
        filas = [r for r in filas if r["pendiente"] > 0]

    # Paso 14: limit
    return filas[:limit]


# =============================================================================
# Etapa 3: Turnos (CRUD) + Roster Rotativo
# =============================================================================

def _parse_fecha_ddmmaaaa(fecha_str: str) -> Tuple[Optional[date], Optional[str]]:
    """
    Parsea fecha en formato dd/MM/yyyy a objeto date.
    Retorna (fecha_obj, None) si OK, (None, mensaje_error) si falla.
    """
    if not (fecha_str or "").strip():
        return None, "Fecha vacía."
    try:
        fecha_obj = datetime.strptime(fecha_str.strip(), "%d/%m/%Y").date()
        return fecha_obj, None
    except ValueError:
        return None, "Formato de fecha inválido. Use dd/MM/yyyy."


def _fmt_fecha_ddmmaaaa(fecha) -> str:
    """
    Formatea fecha (date o datetime) a dd/MM/yyyy para UI.
    """
    if fecha is None:
        return "-"
    if isinstance(fecha, (date, datetime)):
        return fecha.strftime("%d/%m/%Y")
    return "-"


def listar_turnos(
    base_empresa: str,
    solo_activos: bool = True,
) -> List[Dict[str, Any]]:
    """
    Lista turnos de producción de la empresa.
    Retorna lista de dict con id, nombre, hora_inicio, hora_fin, activo.
    """
    from mpr.models import MprTurno
    if not (base_empresa or "").strip():
        return []
    try:
        qs = MprTurno.objects.filter(base_empresa=base_empresa)
        if solo_activos:
            qs = qs.filter(activo=True)
        qs = qs.order_by("nombre")
        return [
            {
                "id": t.id,
                "nombre": t.nombre,
                "hora_inicio": t.hora_inicio.strftime("%H:%M"),
                "hora_fin": t.hora_fin.strftime("%H:%M"),
                "activo": t.activo,
            }
            for t in qs
        ]
    except Exception as e:
        logger.warning("Error al listar turnos en %s: %s", base_empresa, e, exc_info=True)
        return []


def obtener_turno(base_empresa: str, id_turno: int) -> Optional[Any]:
    """
    Obtiene un turno por ID y empresa. Retorna instancia MprTurno o None.
    """
    from mpr.models import MprTurno
    if not (base_empresa or "").strip():
        return None
    try:
        return MprTurno.objects.get(base_empresa=base_empresa, id=id_turno)
    except MprTurno.DoesNotExist:
        return None
    except Exception as e:
        logger.warning("Error al obtener turno %s en %s: %s", id_turno, base_empresa, e, exc_info=True)
        return None


def crear_turno(
    base_empresa: str,
    nombre: str,
    hora_inicio: str,
    hora_fin: str,
) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Crea un nuevo turno de producción.
    Args:
        hora_inicio, hora_fin: strings en formato HH:MM.
    Returns:
        (ok, id_turno, mensaje_error)
    """
    from mpr.models import MprTurno
    from django.db import IntegrityError
    if not (base_empresa or "").strip():
        return False, None, "Empresa inválida."
    if not (nombre or "").strip():
        return False, None, "El nombre del turno no puede estar vacío."
    try:
        h_inicio = datetime.strptime((hora_inicio or "").strip(), "%H:%M").time()
        h_fin = datetime.strptime((hora_fin or "").strip(), "%H:%M").time()
    except ValueError:
        return False, None, "Formato de hora inválido. Use HH:MM."
    if h_inicio == h_fin:
        return False, None, "La hora de inicio y fin no pueden ser iguales."
    try:
        turno = MprTurno.objects.create(
            base_empresa=base_empresa.strip(),
            nombre=nombre.strip(),
            hora_inicio=h_inicio,
            hora_fin=h_fin,
            activo=True,
        )
        return True, turno.id, None
    except IntegrityError:
        return False, None, "Ya existe un turno con ese nombre en la empresa."
    except Exception as e:
        logger.error("Error al crear turno en %s: %s", base_empresa, e, exc_info=True)
        return False, None, "Error al crear turno."


def actualizar_turno(
    base_empresa: str,
    id_turno: int,
    nombre: str,
    hora_inicio: str,
    hora_fin: str,
) -> Tuple[bool, Optional[str]]:
    """
    Actualiza un turno existente.
    Returns:
        (ok, mensaje_error)
    """
    from django.db import IntegrityError
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    if not (nombre or "").strip():
        return False, "El nombre del turno no puede estar vacío."
    turno = obtener_turno(base_empresa, id_turno)
    if not turno:
        return False, "Turno no encontrado."
    try:
        h_inicio = datetime.strptime((hora_inicio or "").strip(), "%H:%M").time()
        h_fin = datetime.strptime((hora_fin or "").strip(), "%H:%M").time()
    except ValueError:
        return False, "Formato de hora inválido. Use HH:MM."
    if h_inicio == h_fin:
        return False, "La hora de inicio y fin no pueden ser iguales."
    try:
        turno.nombre = nombre.strip()
        turno.hora_inicio = h_inicio
        turno.hora_fin = h_fin
        turno.save()
        return True, None
    except IntegrityError:
        return False, "Ya existe un turno con ese nombre en la empresa."
    except Exception as e:
        logger.error("Error al actualizar turno %s en %s: %s", id_turno, base_empresa, e, exc_info=True)
        return False, "Error al actualizar turno."


def toggle_turno_activo(
    base_empresa: str,
    id_turno: int,
    activo: bool,
) -> Tuple[bool, Optional[str]]:
    """
    Cambia el estado activo/inactivo de un turno.
    Returns:
        (ok, mensaje_error)
    """
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    turno = obtener_turno(base_empresa, id_turno)
    if not turno:
        return False, "Turno no encontrado."
    try:
        turno.activo = activo
        turno.save()
        return True, None
    except Exception as e:
        logger.error("Error al cambiar estado turno %s en %s: %s", id_turno, base_empresa, e, exc_info=True)
        return False, "Error al cambiar estado del turno."


def listar_roster_semana(
    base_empresa: str,
    fecha_lunes: date,
) -> Dict[str, Any]:
    """
    Lista asignaciones de roster para una semana (lunes a domingo).
    Returns:
        Dict con:
        - operarios: [{"id": int, "nombre": str}]
        - dias: [{"fecha": date, "fecha_str": "dd/MM/yyyy", "dia_nombre": "Lu"}] (7 días)
        - asignaciones: {id_operario: {"YYYY-MM-DD": {"id_turno": int, "nombre_turno": str}}}
    """
    from mpr.models import MprRosterDia
    from datetime import timedelta
    if not (base_empresa or "").strip():
        return {"operarios": [], "dias": [], "asignaciones": {}}
    dias_semana = []
    nombres_dia = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sá", "Do"]
    for i in range(7):
        fecha = fecha_lunes + timedelta(days=i)
        dias_semana.append({
            "fecha": fecha,
            "fecha_str": _fmt_fecha_ddmmaaaa(fecha),
            "dia_nombre": nombres_dia[fecha.weekday()],
        })
    operarios_raw = listar_empleados_operarios(base_empresa, busqueda=None, limit=500)
    fecha_fin = fecha_lunes + timedelta(days=6)
    try:
        asignaciones_qs = MprRosterDia.objects.filter(
            base_empresa=base_empresa,
            fecha__gte=fecha_lunes,
            fecha__lte=fecha_fin,
        ).select_related("turno")
        asignaciones_dict: Dict[int, Dict[str, Any]] = {}
        for asig in asignaciones_qs:
            op_id = asig.id_operario
            if op_id not in asignaciones_dict:
                asignaciones_dict[op_id] = {}
            asignaciones_dict[op_id][asig.fecha.isoformat()] = {
                "id_turno": asig.turno.id,
                "nombre_turno": asig.turno.nombre,
            }
        return {
            "operarios": [{"id": op["id"], "nombre": op["label"]} for op in operarios_raw],
            "dias": dias_semana,
            "asignaciones": asignaciones_dict,
        }
    except Exception as e:
        logger.error("Error al listar roster semana en %s: %s", base_empresa, e, exc_info=True)
        return {"operarios": [], "dias": [], "asignaciones": {}}


def asignar_turno_roster(
    base_empresa: str,
    fecha_str: str,
    id_operario: int,
    id_turno: int,
) -> Tuple[bool, Optional[str]]:
    """
    Asigna (o reasigna) un turno a un operario en una fecha.
    Usa update_or_create para garantizar constraint único (no duplica).
    Validaciones: fecha >= hoy, turno existe, operario existe.
    Returns:
        (ok, mensaje_error)
    """
    from mpr.models import MprRosterDia
    from django.db import IntegrityError
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    fecha_obj, error = _parse_fecha_ddmmaaaa(fecha_str)
    if error:
        return False, error
    hoy = date.today()
    if fecha_obj < hoy:
        return False, "No se pueden asignar turnos en fechas pasadas."
    turno = obtener_turno(base_empresa, id_turno)
    if not turno:
        return False, "Turno no encontrado."
    operario_data = obtener_operario(base_empresa, id_operario)
    if not operario_data:
        return False, "Operario no encontrado."
    try:
        MprRosterDia.objects.update_or_create(
            base_empresa=base_empresa,
            fecha=fecha_obj,
            id_operario=id_operario,
            defaults={"turno": turno},
        )
        return True, None
    except IntegrityError as e:
        logger.error("IntegrityError al asignar turno roster en %s: %s", base_empresa, e, exc_info=True)
        return False, "Error de integridad: el operario ya tiene un turno asignado para esta fecha."
    except Exception as e:
        logger.error("Error al asignar turno roster en %s: %s", base_empresa, e, exc_info=True)
        return False, "Error al asignar turno."


def eliminar_asignacion_roster(
    base_empresa: str,
    fecha_str: str,
    id_operario: int,
) -> Tuple[bool, Optional[str]]:
    """
    Elimina la asignación de turno de un operario en una fecha.
    Validación: fecha >= hoy.
    Returns:
        (ok, mensaje_error)
    """
    from mpr.models import MprRosterDia
    if not (base_empresa or "").strip():
        return False, "Empresa inválida."
    fecha_obj, error = _parse_fecha_ddmmaaaa(fecha_str)
    if error:
        return False, error
    hoy = date.today()
    if fecha_obj < hoy:
        return False, "No se pueden eliminar asignaciones de fechas pasadas."
    try:
        deleted, _ = MprRosterDia.objects.filter(
            base_empresa=base_empresa,
            fecha=fecha_obj,
            id_operario=id_operario,
        ).delete()
        if deleted == 0:
            return False, "No se encontró asignación para eliminar."
        return True, None
    except Exception as e:
        logger.error("Error al eliminar asignación roster en %s: %s", base_empresa, e, exc_info=True)
        return False, "Error al eliminar asignación."


# ---------------------------------------------------------------------------
# ETAPA 4: Parte de Producción (Ledger OPP-parte)
# ---------------------------------------------------------------------------

def opp_parte_acumulado_por_pack(
    base_empresa: str,
    pack_ids: Optional[List[int]] = None,
) -> Dict[int, Decimal]:
    """
    {id_articulo: SUM(linea.cantidad) + SUM(ajuste.delta)} agrupado por id_articulo,
    filtrado por parte__base_empresa=base_empresa.

    pack_ids opcional para filtrar subconjunto.
    Backward-safe: retorna {} si no hay partes.
    NO lee stock_deposito ni tablas MySQL legacy.
    """
    from mpr.models import MprParteAjuste, MprParteLinea
    from django.db.models import Sum

    if not (base_empresa or "").strip():
        return {}
    try:
        lineas_qs = MprParteLinea.objects.filter(parte__base_empresa=base_empresa)
        ajustes_qs = MprParteAjuste.objects.filter(parte__base_empresa=base_empresa)
        if pack_ids is not None:
            lineas_qs = lineas_qs.filter(id_articulo__in=pack_ids)
            ajustes_qs = ajustes_qs.filter(id_articulo__in=pack_ids)

        lineas_agg = lineas_qs.values("id_articulo").annotate(total=Sum("cantidad"))
        ajustes_agg = ajustes_qs.values("id_articulo").annotate(total=Sum("delta"))

        acum: Dict[int, Decimal] = {}
        for row in lineas_agg:
            aid = to_int_or_none(row["id_articulo"])
            if aid is not None:
                acum[aid] = acum.get(aid, Decimal("0")) + (to_decimal_or_none(row["total"]) or Decimal("0"))
        for row in ajustes_agg:
            aid = to_int_or_none(row["id_articulo"])
            if aid is not None:
                acum[aid] = acum.get(aid, Decimal("0")) + (to_decimal_or_none(row["total"]) or Decimal("0"))
        return acum
    except Exception as e:
        logger.warning("opp_parte_acumulado_por_pack error en %s: %s", base_empresa, e, exc_info=True)
        return {}


def registrar_parte_produccion(
    base_empresa: str,
    fecha_produccion,
    turno_id: int,
    id_usuario: int,
    lineas: List[Dict[str, Any]],
    notas: str = "",
) -> Tuple[Any, List[str]]:
    """
    Crea MprParte + MprParteLineas en transacción atómica (ledger-only).
    NO escribe stock_deposito ni movimiento_stock.

    lineas: [{id_articulo: int, id_operario: int, cantidad: Decimal/float/str}]
    Returns: (parte, warnings_español)
    """
    from django.db import transaction
    from django.core.exceptions import ValidationError as DjValidationError
    from mpr.models import MprParte, MprParteLinea, MprTurno

    if not (base_empresa or "").strip():
        raise ValueError("Empresa inválida.")

    warnings: List[str] = []

    try:
        turno = MprTurno.objects.get(pk=turno_id)
    except MprTurno.DoesNotExist:
        raise ValueError(f"Turno {turno_id} no encontrado.")

    deposito_produccion = get_deposito_produccion_mpr(base_empresa)

    # Pre-snapshot Fabricando ANTES del atomic() — batch, sin N+1
    comp_ids_reg: List[int] = [
        to_int_or_none(c.get("id_articulo"))
        for c in (lineas or [])
        if to_int_or_none(c.get("id_articulo")) is not None
    ]
    cantidad_por_comp: Dict[int, "Decimal"] = {
        to_int_or_none(c.get("id_articulo")): (to_decimal_or_none(c.get("cantidad")) or Decimal("0"))
        for c in (lineas or [])
        if to_int_or_none(c.get("id_articulo")) is not None
    }
    fab_pre: Dict[int, float] = {}
    desc_pre: Dict[int, tuple] = {}
    try:
        if comp_ids_reg:
            envios_pre = _query_enviado_tablero_componente(base_empresa, comp_ids_reg)
            stock_pre, _ = _pivot_stock_por_tipo_mpr(base_empresa, comp_ids_reg)
            desc_pre = _fetch_descripciones_articulo(base_empresa, comp_ids_reg)
            for comp in comp_ids_reg:
                enviado = float(envios_pre.get(comp, 0) or 0)
                stock_prod = stock_pre.get(comp, {}).get(TIPO_MPR_PRODUCCION, 0.0)
                fab_pre[comp] = max(0.0, enviado - stock_prod)
    except Exception as e:
        logger.warning("registrar_parte_produccion: error en pre-snapshot Fabricando: %s", e)

    with transaction.atomic():
        parte = MprParte.objects.create(
            base_empresa=base_empresa,
            fecha_produccion=fecha_produccion,
            turno=turno,
            id_usuario=to_int_or_none(id_usuario) or 0,
            notas=str_or_default(notas, ""),
        )
        lineas_creadas: List[Tuple[Dict[str, Any], Decimal]] = []
        for cel in (lineas or []):
            id_art = to_int_or_none(cel.get("id_articulo"))
            id_op = to_int_or_none(cel.get("id_operario"))
            cantidad = to_decimal_or_none(cel.get("cantidad"))
            if id_art is None or id_op is None or cantidad is None:
                continue
            if cantidad <= 0:
                continue
            op_data = obtener_operario(base_empresa, id_op)
            nombre_snap = str_or_default(
                op_data.get("nombre_empleado") if op_data else None, "-"
            )
            MprParteLinea.objects.update_or_create(
                parte=parte,
                id_articulo=id_art,
                id_operario=id_op,
                defaults={"cantidad": cantidad, "operario_nombre": nombre_snap},
            )
            lineas_creadas.append(({"id_articulo": id_art}, cantidad))

        # Partes E8: componentes sin OPT activa en lista_produccion_agrupada → id_lista=None
        parte.id_lista_produccion = None
        parte.save(update_fields=["id_lista_produccion"])

        # Asiento físico en depósito Producción (E8: directo por componente, sin explosión BOM).
        # Guardia de idempotencia: no re-ejecutar si ya fue confirmado.
        if not parte.movimiento_fisico_ok:
            if deposito_produccion and lineas_creadas:
                _registrar_asiento_fisico_opp_parte(
                    base_empresa=base_empresa,
                    id_usuario=to_int_or_none(id_usuario) or 0,
                    parte=parte,
                    lineas_pack_qty=lineas_creadas,
                    deposito_produccion=deposito_produccion,
                    ya_componentes=True,
                )
            parte.movimiento_fisico_ok = True
            parte.save(update_fields=["movimiento_fisico_ok"])

    # Warnings no bloqueantes si se superó Fabricando disponible (español)
    try:
        for comp in comp_ids_reg:
            qty = float(cantidad_por_comp.get(comp, Decimal("0")) or 0)
            fab = fab_pre.get(comp, 0.0)
            if qty > fab:
                cod, desc = desc_pre.get(comp, ("-", "-"))
                warnings.append(
                    f"Atención: se registraron {qty:.1f} u. de {desc} ({cod}) "
                    f"pero solo {fab:.1f} u. estaban en Fabricando. El parte fue guardado."
                )
    except Exception as e:
        logger.warning("registrar_parte_produccion: error generando warnings: %s", e)

    return parte, warnings


def agregar_ajuste_parte(
    base_empresa: str,
    parte_id: str,
    id_articulo: int,
    id_operario: int,
    delta,
    motivo: str,
    id_usuario: int,
) -> Any:
    """
    Crea MprParteAjuste (delta append-only). Valida que cantidad_efectiva+delta >= 0.
    Raises django.core.exceptions.ValidationError (español) si quedaría negativo.
    Returns: MprParteAjuste creado.
    """
    from django.core.exceptions import ValidationError
    from django.db.models import Sum
    from mpr.models import MprParte, MprParteAjuste, MprParteLinea

    try:
        parte = MprParte.objects.get(pk=parte_id, base_empresa=base_empresa)
    except MprParte.DoesNotExist:
        raise ValidationError(f"Parte {parte_id} no encontrada para empresa {base_empresa}.")

    delta_dec = to_decimal_or_none(delta)
    if delta_dec is None:
        raise ValidationError("El delta del ajuste es inválido.")

    try:
        linea = MprParteLinea.objects.get(parte=parte, id_articulo=id_articulo, id_operario=id_operario)
        cantidad_base = linea.cantidad
    except MprParteLinea.DoesNotExist:
        raise ValidationError(
            f"No existe línea para artículo {id_articulo}, operario {id_operario} en este parte."
        )

    ajustes_previos = MprParteAjuste.objects.filter(
        parte=parte, id_articulo=id_articulo, id_operario=id_operario
    ).aggregate(total=Sum("delta"))["total"] or Decimal("0")

    cantidad_efectiva = cantidad_base + ajustes_previos
    if cantidad_efectiva + delta_dec < 0:
        raise ValidationError(
            f"El ajuste dejaría la cantidad efectiva en negativo "
            f"(actual: {cantidad_efectiva}, delta: {delta_dec})."
        )

    ajuste = MprParteAjuste.objects.create(
        parte=parte,
        id_articulo=to_int_or_none(id_articulo) or id_articulo,
        id_operario=to_int_or_none(id_operario) or id_operario,
        delta=delta_dec,
        motivo=str_or_default(motivo, "-"),
        id_usuario=to_int_or_none(id_usuario) or 0,
        ajuste_fisico_ok=False,
    )

    # Registrar delta físico en depósito Producción (Etapa 5).
    deposito_produccion = get_deposito_produccion_mpr(base_empresa)
    id_art_int = to_int_or_none(id_articulo) or id_articulo
    id_usuario_int = to_int_or_none(id_usuario) or 0
    if deposito_produccion and id_art_int is not None:
        try:
            _registrar_delta_stock_ajuste(
                base_empresa=base_empresa,
                id_usuario=id_usuario_int,
                id_articulo=id_art_int,
                delta=delta_dec,
                deposito_id=deposito_produccion,
            )
            ajuste.ajuste_fisico_ok = True
            ajuste.save(update_fields=["ajuste_fisico_ok"])
        except (ValidationError, Exception) as e:
            # Si el delta físico falla, revertir la creación del ajuste
            # para mantener coherencia entre ledger y stock físico.
            ajuste.delete()
            raise

    return ajuste


def construir_grilla_parte(
    base_empresa: str,
    fecha,
    turno_id: int,
) -> Dict[str, Any]:
    """
    Construye la grilla componentes × operarios para la pantalla de captura (E8).

    Fuente de filas: componentes con Fabricando > 0 desde MprEnvioProduccion (E7).
    Fabricando(comp) = max(0, Σ_envíos(comp) − stock_produccion(comp)).

    Returns:
      {
        "componentes":     [{id_articulo, codigo_manual, descripcion, fabricando}],
        "componentes_vacio": bool,
        "operarios":       [{id_operario, nombre}],
        "celdas":          {(id_articulo, id_operario): Decimal},
        "roster_vacio":    bool,
      }
    """
    from mpr.models import MprParteLinea, MprParteAjuste, MprParte, MprRosterDia
    from django.db.models import Sum

    resultado: Dict[str, Any] = {
        "componentes": [],
        "componentes_vacio": False,
        "operarios": [],
        "celdas": {},
        "roster_vacio": False,
    }

    if not (base_empresa or "").strip():
        resultado["roster_vacio"] = True
        resultado["componentes_vacio"] = True
        return resultado

    # Operarios del roster para esa fecha y turno
    roster_qs = MprRosterDia.objects.filter(
        base_empresa=base_empresa,
        fecha=fecha,
        turno_id=turno_id,
    ).select_related("turno")

    operarios_list: List[Dict[str, Any]] = []
    for r in roster_qs:
        op_data = obtener_operario(base_empresa, r.id_operario)
        nombre = str_or_default(op_data.get("nombre_empleado") if op_data else None, "-")
        operarios_list.append({"id_operario": r.id_operario, "nombre": nombre})

    resultado["roster_vacio"] = len(operarios_list) == 0
    resultado["operarios"] = operarios_list

    # Componentes con Fabricando > 0 desde ledger MprEnvioProduccion (E7)
    componentes_list: List[Dict[str, Any]] = []
    try:
        envios_map = _query_enviados_todos_componentes(base_empresa)
        if not envios_map:
            resultado["componentes_vacio"] = True
            resultado["componentes"] = []
        else:
            comp_ids = list(envios_map.keys())
            stock_pivot, _ = _pivot_stock_por_tipo_mpr(base_empresa, comp_ids)

            # Calcular Fabricando por componente: max(0, enviado − stock_produccion)
            fabricando_map: Dict[int, float] = {}
            for comp in comp_ids:
                enviado = float(envios_map.get(comp) or 0)
                stock_prod = stock_pivot.get(comp, {}).get(TIPO_MPR_PRODUCCION, 0.0)
                fabricando_map[comp] = max(0.0, enviado - stock_prod)

            comp_activos = [c for c in comp_ids if fabricando_map.get(c, 0.0) > 0]

            if not comp_activos:
                resultado["componentes_vacio"] = True
                resultado["componentes"] = []
            else:
                desc_map = _fetch_descripciones_articulo(base_empresa, comp_activos)
                for comp in comp_activos:
                    cod, desc = desc_map.get(comp, ("-", "-"))
                    componentes_list.append({
                        "id_articulo": comp,
                        "codigo_manual": str_codigo_manual_articulo(cod),
                        "descripcion": str_or_default(desc, "-"),
                        "fabricando": fabricando_map[comp],
                    })
                resultado["componentes_vacio"] = len(componentes_list) == 0
                resultado["componentes"] = componentes_list
    except Exception as e:
        logger.warning("construir_grilla_parte: error obteniendo componentes en %s: %s", base_empresa, e)
        resultado["componentes_vacio"] = True

    # Celdas pre-existentes (cantidades efectivas del último parte para esta fecha+turno)
    celdas: Dict[tuple, Decimal] = {}
    try:
        partes_qs = MprParte.objects.filter(
            base_empresa=base_empresa,
            fecha_produccion=fecha,
            turno_id=turno_id,
        ).prefetch_related("lineas", "ajustes")
        for parte in partes_qs:
            ajustes_por_clave: Dict[tuple, Decimal] = {}
            for aj in parte.ajustes.all():
                clave = (aj.id_articulo, aj.id_operario)
                ajustes_por_clave[clave] = ajustes_por_clave.get(clave, Decimal("0")) + aj.delta
            for linea in parte.lineas.all():
                clave = (linea.id_articulo, linea.id_operario)
                efectiva = linea.cantidad + ajustes_por_clave.get(clave, Decimal("0"))
                celdas[clave] = celdas.get(clave, Decimal("0")) + efectiva
    except Exception as e:
        logger.warning("construir_grilla_parte: error obteniendo celdas en %s: %s", base_empresa, e)

    resultado["celdas"] = celdas

    # E8: adjuntar a cada componente sus celdas alineadas con el orden de operarios,
    # para que el template pueda precargar el valor por celda sin lookup por tupla.
    for comp in componentes_list:
        cid = comp["id_articulo"]
        comp["celdas_ops"] = [
            {
                "id_operario": op["id_operario"],
                "nombre": op["nombre"],
                "cantidad": celdas.get((cid, op["id_operario"]), ""),
            }
            for op in operarios_list
        ]

    return resultado


def listar_partes(
    base_empresa: str,
    fecha=None,
    turno_id: Optional[int] = None,
):
    """
    QuerySet de MprParte filtrado por base_empresa; opcionalmente por fecha y/o turno_id.
    Prefetch lineas para evitar N+1.
    """
    from mpr.models import MprParte
    if not (base_empresa or "").strip():
        from mpr.models import MprParte as _M
        return _M.objects.none()
    qs = MprParte.objects.filter(base_empresa=base_empresa).prefetch_related("lineas")
    if fecha is not None:
        qs = qs.filter(fecha_produccion=fecha)
    if turno_id is not None:
        qs = qs.filter(turno_id=turno_id)
    return qs


def obtener_parte(
    base_empresa: str,
    parte_id: str,
) -> Optional[Any]:
    """
    Obtiene MprParte por UUID y base_empresa. Retorna None si no existe o empresa no coincide.
    """
    from mpr.models import MprParte
    if not (base_empresa or "").strip() or not parte_id:
        return None
    try:
        return MprParte.objects.get(pk=parte_id, base_empresa=base_empresa)
    except MprParte.DoesNotExist:
        return None


# =============================================================================
# Etapa 5: Transiciones por lote + desmontaje de automatismos
# =============================================================================

def _registrar_asiento_fisico_opp_parte(
    base_empresa: str,
    id_usuario: int,
    parte: Any,
    lineas_pack_qty: List[Tuple[Dict[str, Any], Any]],
    deposito_produccion: int,
    ya_componentes: bool = False,
) -> None:
    """Registra el asiento físico de una parte de producción en el depósito Producción.

    Escribe en MySQL legacy:
    - INSERT movimiento_stock (tipo_mov='OPP', motivo='Parte producción')
    - Por cada componente: INSERT stock (Entrada=qty) + UPDATE/INSERT stock_deposito

    Cuando ``ya_componentes=True``, las líneas son ya componentes directos (E8):
    no se llama ``_explode_packs_to_components``. Cuando es False (default), se
    mantiene el comportamiento original (explosión BOM). Backward-safe.

    Debe llamarse dentro del ``transaction.atomic()`` de ``registrar_parte_produccion``.
    El commit MySQL se realiza aquí, ANTES de que Django cierre el atomic block.

    Raises: MprSchemaError si faltan tablas; ValidationError si componentes vacíos.
    """
    from django.core.exceptions import ValidationError as DjValidationError

    if not lineas_pack_qty:
        return

    if ya_componentes:
        # E8: las líneas son componentes directos — no explotar BOM
        componentes_total = {
            int(l["id_articulo"]): float(q)
            for l, q in lineas_pack_qty
            if float(q) > 0
        }
    else:
        # Comportamiento original (E4/E5): explosión BOM desde packs
        componentes_total = _explode_packs_to_components(base_empresa, [
            (l, float(q)) for l, q in lineas_pack_qty if to_decimal_or_none(q) and float(q) > 0
        ])

    if not componentes_total:
        raise DjValidationError(
            "No se pudo determinar los componentes del parte (BOM vacío o artículos sin BOM). "
            "Verifique la fórmula de los artículos antes de registrar el parte."
        )

    id_ref_movstock = 1
    id_pv = 1
    fecha_mov = date.today().isoformat()
    detalle_mov = f"OPP-parte {parte.pk} desde MPR"

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
            if not all([tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd]):
                faltan = [n for n, t in [
                    ("codmov", tbl_codmov), ("talonarios", tbl_talonarios),
                    ("movimiento_stock", tbl_mov), ("stock", tbl_stock), ("stock_deposito", tbl_sd),
                ] if not t]
                conn.rollback()
                raise MprSchemaError(
                    f"Faltan tablas para asiento físico OPP-parte: {', '.join(faltan)}."
                )

            # (1) Siguiente codigo_movimiento
            cursor.execute(f"SELECT CodigoMovimiento FROM {tbl_codmov} WHERE codigo = 1 FOR UPDATE")
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                raise MprSchemaError("No se pudo obtener código de movimiento para el asiento físico.")
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
                raise MprSchemaError("No existe talonario MSTOCK para el punto de venta (OPP-parte).")
            orden_talon, nro_actual = talon_row[0], int(talon_row[1] or 0)
            nro_nuevo = nro_actual + 1
            cursor.execute(f"UPDATE {tbl_talonarios} SET Nro = %s WHERE Orden = %s", [nro_nuevo, orden_talon])
            nro_comprobante = _formato_nro_comprobante_mstock(id_pv, nro_actual)
            nro_comprobante_busq = nro_actual

            # (3) INSERT movimiento_stock (OPP, deposito_produccion → deposito_produccion)
            params_mov_base = [
                codigo_mov, nro_comprobante, MOTIVO_OPP_TEXTO, fecha_mov,
                deposito_produccion, deposito_produccion, detalle_mov, id_usuario,
                id_ref_movstock, None, None, None, TIPO_MOV_OPP, id_pv, nro_comprobante_busq,
            ]
            intentos_mov: List[Tuple[str, List[Any]]] = [
                (
                    f"""
                    INSERT INTO {tbl_mov}
                    (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                     detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s)
                    """,
                    params_mov_base,
                ),
                (
                    f"""
                    INSERT INTO {tbl_mov}
                    (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                     detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                    """,
                    params_mov_base[:14],
                ),
            ]
            try:
                _mpr_ejecutar_insert_intentos(cursor, intentos_mov)
            except Exception as e:
                conn.rollback()
                raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e

            # (4) Cargar codigo/descripcion de componentes
            all_comp_ids: set = set(componentes_total.keys())
            articulo_info: Dict[int, Tuple[str, str]] = {}
            if all_comp_ids and tbl_articulo:
                ids_comp = list(all_comp_ids)
                placeholders = ",".join(["%s"] * len(ids_comp))
                cursor.execute(
                    f"SELECT IDArt, COALESCE(CodigoArticuloT, CAST(CodigoArticulo AS CHAR), '') AS codigo, "
                    f"COALESCE(NombreArticulo, '') AS descripcion FROM {tbl_articulo} WHERE IDArt IN ({placeholders})",
                    ids_comp,
                )
                for r in cursor.fetchall() or []:
                    aid = to_int_or_none(r[0])
                    if aid is not None:
                        articulo_info[aid] = (str_or_default(r[1], "-"), str_or_default(r[2], "-"))

            # SQL mínimo para INSERT stock (Entrada a depósito Producción)
            sql_stock_min = f"""
                INSERT INTO {tbl_stock}
                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                VALUES (%s, %s, %s, %s, %s, %s, 0, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                """

            orden = 0
            for id_art in sorted(componentes_total.keys()):
                qty = componentes_total[id_art]
                if qty <= 0:
                    continue
                codigo_art, descripcion_art = articulo_info.get(id_art, ("-", "-"))
                entrada = Decimal(str(qty))
                orden += 1

                cursor.execute(
                    f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                    [id_art, deposito_produccion],
                )
                sd_row = cursor.fetchone()
                saldo_actual = Decimal(str(sd_row[1] or 0)) if sd_row else Decimal(0)
                saldo_despues = saldo_actual + entrada

                params_stock = [
                    codigo_mov, id_art, codigo_art, descripcion_art, fecha_mov,
                    entrada, saldo_despues, deposito_produccion, id_ref_movstock,
                    orden, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None,
                ]
                try:
                    _mpr_ejecutar_insert_intentos(cursor, [(sql_stock_min, params_stock)])
                except Exception as e:
                    conn.rollback()
                    raise MprSchemaError(formatear_error_esquema(e, "stock")) from e

                if sd_row:
                    cursor.execute(
                        f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s",
                        [saldo_despues, sd_row[0]],
                    )
                else:
                    cursor.execute(
                        f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                        [id_art, deposito_produccion, saldo_despues],
                    )

            # Historico OPP-parte (E6): best-effort, no interrumpe el asiento físico.
            try:
                _escribir_historico_opp_parte(
                    cursor, parte, lineas_pack_qty, codigo_mov, id_usuario, fecha_mov, deposito_produccion
                )
            except Exception as hist_err:
                logger.warning(
                    "_registrar_asiento_fisico_opp_parte: historico no escrito en %s: %s",
                    base_empresa, hist_err,
                )

            conn.commit()
        except MprSchemaError:
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise MprSchemaError(f"Error en asiento físico OPP-parte: {e}") from e


def _registrar_delta_stock_ajuste(
    base_empresa: str,
    id_usuario: int,
    id_articulo: int,
    delta: Decimal,
    deposito_id: int,
) -> None:
    """Registra el delta físico de un ajuste en el depósito indicado (normalmente Producción).

    - delta > 0: Entrada al stock.
    - delta < 0: Salida del stock; valida que el saldo no quede negativo.

    Raises:
        django.core.exceptions.ValidationError: si el saldo quedaría negativo.
        MprSchemaError: si faltan tablas o hay error de esquema.
    """
    from django.core.exceptions import ValidationError as DjValidationError

    if delta == 0:
        return

    id_ref_movstock = 1
    id_pv = 1
    fecha_mov = date.today().isoformat()
    detalle_mov = f"Ajuste físico OPP-parte art.{id_articulo} desde MPR"

    with get_connection(base_empresa) as conn:
        conn.autocommit(False)
        cursor = conn.cursor()
        try:
            tbl_codmov = _nombre_tabla(cursor, "codmov")
            tbl_talonarios = _nombre_tabla(cursor, "talonarios")
            tbl_mov = _nombre_tabla(cursor, "movimiento_stock")
            tbl_stock = _nombre_tabla(cursor, "stock")
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            if not all([tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd]):
                conn.rollback()
                raise MprSchemaError("Faltan tablas para registrar delta físico del ajuste.")

            # Validar saldo antes de operar (si delta < 0)
            if delta < 0:
                cursor.execute(
                    f"SELECT saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                    [id_articulo, deposito_id],
                )
                sd_check = cursor.fetchone()
                saldo_actual = Decimal(str(sd_check[0] or 0)) if sd_check else Decimal(0)
                if saldo_actual + delta < 0:
                    conn.rollback()
                    raise DjValidationError(
                        f"Saldo insuficiente en Producción para aplicar el ajuste "
                        f"(saldo actual: {saldo_actual}, delta: {delta})."
                    )

            # codmov + talonario
            cursor.execute(f"SELECT CodigoMovimiento FROM {tbl_codmov} WHERE codigo = 1 FOR UPDATE")
            row = cursor.fetchone()
            if not row:
                conn.rollback()
                raise MprSchemaError("No se pudo obtener código de movimiento para el ajuste físico.")
            codigo_mov = int(row[0] or 0) + 1
            cursor.execute(f"UPDATE {tbl_codmov} SET CodigoMovimiento = %s WHERE codigo = 1", [codigo_mov])

            cursor.execute(
                f"SELECT Orden, Nro FROM {tbl_talonarios} WHERE TipoComprobante = 'MSTOCK' AND id_punto_venta = %s FOR UPDATE",
                [id_pv],
            )
            talon_row = cursor.fetchone()
            if not talon_row:
                conn.rollback()
                raise MprSchemaError("No existe talonario MSTOCK para el ajuste físico.")
            orden_talon, nro_actual = talon_row[0], int(talon_row[1] or 0)
            nro_nuevo = nro_actual + 1
            cursor.execute(f"UPDATE {tbl_talonarios} SET Nro = %s WHERE Orden = %s", [nro_nuevo, orden_talon])
            nro_comprobante = _formato_nro_comprobante_mstock(id_pv, nro_actual)
            nro_comprobante_busq = nro_actual

            # INSERT movimiento_stock
            params_mov = [
                codigo_mov, nro_comprobante, MOTIVO_OPP_TEXTO, fecha_mov,
                deposito_id, deposito_id, detalle_mov, id_usuario,
                id_ref_movstock, None, None, None, TIPO_MOV_OPP, id_pv, nro_comprobante_busq,
            ]
            intentos_mov: List[Tuple[str, List[Any]]] = [
                (
                    f"""
                    INSERT INTO {tbl_mov}
                    (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                     detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s)
                    """,
                    params_mov,
                ),
                (
                    f"""
                    INSERT INTO {tbl_mov}
                    (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                     detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                    """,
                    params_mov[:14],
                ),
            ]
            try:
                _mpr_ejecutar_insert_intentos(cursor, intentos_mov)
            except Exception as e:
                conn.rollback()
                raise MprSchemaError(formatear_error_esquema(e, "movimiento_stock")) from e

            # INSERT stock (Entrada si delta>0, Salida si delta<0)
            abs_delta = abs(delta)
            es_entrada = delta > 0
            entrada_val = abs_delta if es_entrada else Decimal(0)
            salida_val = abs_delta if not es_entrada else Decimal(0)

            cursor.execute(
                f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                [id_articulo, deposito_id],
            )
            sd_row = cursor.fetchone()
            saldo_base = Decimal(str(sd_row[1] or 0)) if sd_row else Decimal(0)
            saldo_despues = saldo_base + delta  # delta puede ser negativo

            sql_stock_min = f"""
                INSERT INTO {tbl_stock}
                (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                 id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                """
            params_stock = [
                codigo_mov, id_articulo, str(id_articulo), "-", fecha_mov,
                entrada_val, salida_val, saldo_despues, deposito_id,
                id_ref_movstock, 1, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None,
            ]
            try:
                cursor.execute(sql_stock_min, params_stock)
            except Exception as e:
                conn.rollback()
                raise MprSchemaError(formatear_error_esquema(e, "stock")) from e

            if sd_row:
                cursor.execute(
                    f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s",
                    [saldo_despues, sd_row[0]],
                )
            else:
                cursor.execute(
                    f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                    [id_articulo, deposito_id, saldo_despues],
                )

            conn.commit()
        except (DjValidationError, MprSchemaError):
            try:
                conn.rollback()
            except Exception:
                pass
            raise
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            raise MprSchemaError(f"Error al registrar delta físico del ajuste: {e}") from e


def transferir_stock_entre_etapas(
    base_empresa: str,
    id_usuario: int,
    id_articulo: int,
    tipo_origen: str,
    tipo_destino: str,
    cantidad: Any,
    notas: str = "",
    fecha: "Optional[date]" = None,
) -> Tuple[bool, Optional[int], Optional[str], Optional[str]]:
    """Transfiere stock físico de un depósito MPR a otro (transición entre etapas).

    Opera a nivel componente (el caller ya ha explotado el pack si corresponde).
    Valida con ``validar_transicion``, lanza MSTOCK (Salida origen + Entrada destino),
    actualiza ``stock_deposito`` en ambos depósitos y crea un registro ``MprTransicionLote``.

    Args:
        fecha: fecha del asiento MSTOCK. Si es None se usa ``date.today()``.
            Permite cargas diferidas (informe de fábrica días posteriores).

    Returns:
        (ok, codigo_movimiento, nro_comprobante, mensaje_error)
    """
    from django.core.exceptions import ValidationError as DjValidationError
    from mpr.models import MprTransicionLote
    from mpr.pipeline import validar_transicion

    cantidad_dec = to_decimal_or_none(cantidad)

    # Validaciones previas (sin acceso a DB)
    if not (base_empresa or "").strip():
        return False, None, None, "Base de datos no indicada."
    if not id_articulo or not tipo_origen or not tipo_destino:
        return False, None, None, "Faltan parámetros obligatorios (articulo, origen, destino)."
    if cantidad_dec is None or cantidad_dec <= 0:
        return False, None, None, "La cantidad debe ser mayor a cero."

    # Pre-validación de legalidad de la transición (saldo_origen=0 sólo valida el grafo)
    ok_legal, msg_legal = validar_transicion(tipo_origen, tipo_destino, cantidad_dec, saldo_origen=Decimal("9999999"))
    if not ok_legal:
        return False, None, None, msg_legal

    # Resolver depósitos
    deposito_origen_id = _get_deposito_por_tipo_mpr(base_empresa, tipo_origen)
    deposito_destino_id = _get_deposito_por_tipo_mpr(base_empresa, tipo_destino)
    if not deposito_origen_id:
        return False, None, None, f"No se encontró el depósito de origen '{tipo_origen}' en la base de datos."
    if not deposito_destino_id:
        return False, None, None, f"No se encontró el depósito de destino '{tipo_destino}' en la base de datos."

    id_ref_movstock = 1
    id_pv = 1
    fecha_mov = (fecha or date.today()).isoformat()
    detalle_mov = f"Transición MPR {tipo_origen}→{tipo_destino} art.{id_articulo}"

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
                if not all([tbl_codmov, tbl_talonarios, tbl_mov, tbl_stock, tbl_sd]):
                    conn.rollback()
                    faltan = [n for n, t in [
                        ("codmov", tbl_codmov), ("talonarios", tbl_talonarios),
                        ("movimiento_stock", tbl_mov), ("stock", tbl_stock), ("stock_deposito", tbl_sd),
                    ] if not t]
                    return False, None, None, f"Faltan tablas para la transición: {', '.join(faltan)}."

                # SELECT saldo origen FOR UPDATE
                cursor.execute(
                    f"SELECT saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                    [id_articulo, deposito_origen_id],
                )
                sd_origen = cursor.fetchone()
                saldo_origen = Decimal(str(sd_origen[0] or 0)) if sd_origen else Decimal(0)

                # Re-validar con saldo real
                ok_real, msg_real = validar_transicion(tipo_origen, tipo_destino, cantidad_dec, saldo_origen=saldo_origen)
                if not ok_real:
                    conn.rollback()
                    return False, None, None, msg_real

                # codmov FOR UPDATE
                cursor.execute(f"SELECT CodigoMovimiento FROM {tbl_codmov} WHERE codigo = 1 FOR UPDATE")
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return False, None, None, "No se pudo obtener código de movimiento para la transición."
                codigo_mov = int(row[0] or 0) + 1
                cursor.execute(f"UPDATE {tbl_codmov} SET CodigoMovimiento = %s WHERE codigo = 1", [codigo_mov])

                # Talonario MSTOCK FOR UPDATE
                cursor.execute(
                    f"SELECT Orden, Nro FROM {tbl_talonarios} WHERE TipoComprobante = 'MSTOCK' AND id_punto_venta = %s FOR UPDATE",
                    [id_pv],
                )
                talon_row = cursor.fetchone()
                if not talon_row:
                    conn.rollback()
                    return False, None, None, "No existe talonario MSTOCK para la transición."
                orden_talon, nro_actual = talon_row[0], int(talon_row[1] or 0)
                nro_nuevo = nro_actual + 1
                cursor.execute(f"UPDATE {tbl_talonarios} SET Nro = %s WHERE Orden = %s", [nro_nuevo, orden_talon])
                nro_comprobante = _formato_nro_comprobante_mstock(id_pv, nro_actual)
                nro_comprobante_busq = nro_actual

                # INSERT movimiento_stock (origen → destino)
                params_mov = [
                    codigo_mov, nro_comprobante, MOTIVO_OPP_TEXTO, fecha_mov,
                    deposito_origen_id, deposito_destino_id, detalle_mov, id_usuario,
                    id_ref_movstock, None, None, None, TIPO_MOV_OPP, id_pv, nro_comprobante_busq,
                ]
                intentos_mov: List[Tuple[str, List[Any]]] = [
                    (
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv, nro_comprobante_busq)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov,
                    ),
                    (
                        f"""
                        INSERT INTO {tbl_mov}
                        (codigo_movimiento, nro_comprobante, motivo_movimiento, fecha, deposito_origen, deposito_destino,
                         detalle, id_usuario, tipo_comprobante, anulado, id_ref_movstock, id_proyecto, id_cliente, id_vendedor, tipo_mov, id_pv)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'MSTOCK', 'No', %s, %s, %s, %s, %s, %s)
                        """,
                        params_mov[:14],
                    ),
                ]
                try:
                    _mpr_ejecutar_insert_intentos(cursor, intentos_mov)
                except Exception as e:
                    conn.rollback()
                    return False, None, None, formatear_error_esquema(e, "movimiento_stock")

                sql_stock_min = f"""
                    INSERT INTO {tbl_stock}
                    (CodigoMovimiento, IDArt, CodigoArticulo, Descripcion, Fecha, Entrada, Salida, saldo, CodDeposito,
                     id_ref_movstock, Orden, IdUsuario, Tipo, TipoComp, Comprobante, NroComprobante, anulado, CodViajante)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'Movimiento Stock', %s, 'MSTOCK', %s, 'No', %s)
                    """

                id_art_str = str(id_articulo)

                # INSERT stock Salida desde origen
                cursor.execute(
                    f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                    [id_articulo, deposito_origen_id],
                )
                sd_orig_row = cursor.fetchone()
                saldo_orig_base = Decimal(str(sd_orig_row[1] or 0)) if sd_orig_row else Decimal(0)
                saldo_orig_despues = saldo_orig_base - cantidad_dec
                params_salida = [
                    codigo_mov, id_articulo, id_art_str, "-", fecha_mov,
                    Decimal(0), cantidad_dec, saldo_orig_despues, deposito_origen_id,
                    id_ref_movstock, 1, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None,
                ]
                try:
                    cursor.execute(sql_stock_min, params_salida)
                except Exception as e:
                    conn.rollback()
                    return False, None, None, formatear_error_esquema(e, "stock (salida)")

                if sd_orig_row:
                    cursor.execute(
                        f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s",
                        [saldo_orig_despues, sd_orig_row[0]],
                    )
                else:
                    cursor.execute(
                        f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                        [id_articulo, deposito_origen_id, saldo_orig_despues],
                    )

                # INSERT stock Entrada al destino
                cursor.execute(
                    f"SELECT id_stock_deposito, saldo FROM {tbl_sd} WHERE id_articulo = %s AND id_deposito = %s FOR UPDATE",
                    [id_articulo, deposito_destino_id],
                )
                sd_dest_row = cursor.fetchone()
                saldo_dest_base = Decimal(str(sd_dest_row[1] or 0)) if sd_dest_row else Decimal(0)
                saldo_dest_despues = saldo_dest_base + cantidad_dec
                params_entrada = [
                    codigo_mov, id_articulo, id_art_str, "-", fecha_mov,
                    cantidad_dec, Decimal(0), saldo_dest_despues, deposito_destino_id,
                    id_ref_movstock, 2, id_usuario, MOTIVO_OPP_TEXTO, nro_comprobante, None,
                ]
                try:
                    cursor.execute(sql_stock_min, params_entrada)
                except Exception as e:
                    conn.rollback()
                    return False, None, None, formatear_error_esquema(e, "stock (entrada)")

                if sd_dest_row:
                    cursor.execute(
                        f"UPDATE {tbl_sd} SET saldo = %s WHERE id_stock_deposito = %s",
                        [saldo_dest_despues, sd_dest_row[0]],
                    )
                else:
                    cursor.execute(
                        f"INSERT INTO {tbl_sd} (id_articulo, id_deposito, saldo) VALUES (%s, %s, %s)",
                        [id_articulo, deposito_destino_id, saldo_dest_despues],
                    )

                conn.commit()

            except (MprSchemaError, Exception) as e:
                try:
                    conn.rollback()
                except Exception:
                    pass
                if isinstance(e, MprSchemaError):
                    raise
                return False, None, None, f"Error al procesar la transición: {e}"

    except MprSchemaError as e:
        return False, None, None, str(e)
    except Exception as e:
        return False, None, None, f"Error inesperado en la transición: {e}"

    # Crear registro de trazabilidad en Django ORM (post-commit MySQL)
    try:
        MprTransicionLote.objects.create(
            base_empresa=base_empresa,
            id_articulo=id_articulo,
            tipo_origen=tipo_origen,
            tipo_destino=tipo_destino,
            cantidad=cantidad_dec,
            codigo_movimiento=codigo_mov,
            id_usuario=id_usuario,
        )
    except Exception as e:
        logger.warning(
            "transferir_stock_entre_etapas: no se pudo crear MprTransicionLote tras commit MySQL: %s", e
        )

    return True, codigo_mov, nro_comprobante, None


# =============================================================================
# Etapa 6: Trazabilidad OPT
# =============================================================================


def _capturar_id_lista_opt_activa(
    base_empresa: str,
    id_articulos: List[int],
) -> Optional[int]:
    """Retorna el id_lista_produccion de la OPT activa más reciente para los artículos dados.

    Consulta lista_produccion_agrupada con en_proceso_produccion='Si'.
    Best-effort: si múltiples activas → toma la de mayor id_lista_produccion + warning.
    Retorna None si no hay OPT activa o falla MySQL.
    """
    if not id_articulos:
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "lista_produccion_agrupada")
            if not tbl:
                return None
            ph = ",".join(["%s"] * len(id_articulos))
            cursor.execute(
                f"SELECT id_lista_produccion FROM {tbl} "
                f"WHERE id_articulo IN ({ph}) "
                f"AND COALESCE(NULLIF(TRIM(en_proceso_produccion), ''), 'No') = 'Si' "
                f"ORDER BY id_lista_produccion DESC LIMIT 2",
                id_articulos,
            )
            rows = cursor.fetchall() or []
            if not rows:
                return None
            ids = [to_int_or_none(r.get("id_lista_produccion")) for r in rows if r.get("id_lista_produccion")]
            ids = [i for i in ids if i is not None]
            if len(ids) > 1:
                logger.warning(
                    "_capturar_id_lista_opt_activa: ambigüedad en %s artículos %s → "
                    "múltiples OPTs activas %s; usando %s (mayor id)",
                    base_empresa, id_articulos, ids, ids[0],
                )
            return ids[0] if ids else None
    except Exception as exc:
        logger.warning("_capturar_id_lista_opt_activa: fallo en %s: %s", base_empresa, exc)
        return None


def _escribir_historico_opp_parte(
    cursor,
    parte: Any,
    lineas_pack_qty: List[Tuple[Dict[str, Any], Any]],
    codigo_mov: int,
    id_usuario: int,
    fecha_mov: str,
    deposito_produccion: int,
) -> None:
    """Registra eventos OPP-parte en lista_produccion_historico (best-effort).

    Si parte.id_lista_produccion es None o la tabla no existe → silencioso.
    Usa el cursor ya abierto (mismo contexto de conexión del asiento físico).
    Debe estar envuelta en try/except en el caller para no interrumpir el asiento físico.
    """
    if parte.id_lista_produccion is None:
        return
    tbl = _nombre_tabla(cursor, "lista_produccion_historico")
    if not tbl:
        logger.warning(
            "_escribir_historico_opp_parte: tabla lista_produccion_historico no encontrada; "
            "omitiendo historico para parte %s",
            parte.pk,
        )
        return
    hora_evento = datetime.now().strftime("%H:%M:%S")
    id_lista = to_int_or_none(parte.id_lista_produccion)
    for linea_dict, cantidad in (lineas_pack_qty or []):
        id_art = to_int_or_none(linea_dict.get("id_articulo"))
        if id_art is None:
            continue
        qty = float(to_decimal_or_none(cantidad) or 0)
        if qty <= 0:
            continue
        params_base = [
            id_art,                # id_articulo
            None,                  # id_articulo_formula (no aplica, registro por pack)
            qty,                   # cantidad_movimiento
            deposito_produccion,   # id_deposito
            deposito_produccion,   # id_deposito_origen
            deposito_produccion,   # id_deposito_destino
            codigo_mov,            # codigo_movimiento_mstock
            None,                  # codigo_movimiento_opt
            None,                  # nro_comprobante
            id_usuario,            # id_usuario
            id_lista,              # id_lista_produccion
            fecha_mov,             # fecha
            hora_evento,           # hora_evento
        ]
        intentos: List[Tuple[str, List[Any]]] = [
            (
                f"""
                INSERT INTO {tbl}
                (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                 id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                 nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento, id_operario)
                VALUES ('OPP', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                params_base + [id_usuario],
            ),
            (
                f"""
                INSERT INTO {tbl}
                (tipo_evento, id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada,
                 id_deposito, id_deposito_origen, id_deposito_destino, codigo_movimiento_mstock, codigo_movimiento_opt,
                 nro_comprobante, id_usuario, id_lista_produccion, fecha, hora_evento)
                VALUES ('OPP', %s, %s, 0, %s, 0, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                params_base,
            ),
        ]
        try:
            _mpr_ejecutar_insert_intentos(cursor, intentos)
        except Exception as exc:
            logger.warning(
                "_escribir_historico_opp_parte: no se pudo insertar en %s para parte %s art %s: %s",
                tbl, parte.pk, id_art, exc,
            )


def construir_trazabilidad_opt(
    base_empresa: str,
    id_lista_produccion: int,
) -> Dict[str, Any]:
    """Construye la trazabilidad completa de una OPT integrando 6 fuentes de datos.

    Retorna:
        {
            cabecera: {id_lista, id_articulo, codigo_manual, descripcion, cantidad_pedida, estado},
            eventos: [{tipo, fecha, hora, descripcion, cantidad, operario, fuente, codigo_movimiento, id_lista_produccion}],
            fuentes_fallidas: [nombre_fuente, ...]
        }
    Cada fuente se integra con try/except independiente. Los eventos se ordenan cronológicamente.
    Eventos sin OPT asociada se marcan fuente='sin_opt'.
    Fechas en formato dd/MM/yyyy.
    """
    from mpr.models import MprParte, MprParteAjuste, MprParteLinea, MprTransicionLote, MprArmadoSurtidoMovimiento, MprImputacionArmado

    id_lista = to_int_or_none(id_lista_produccion)
    if not id_lista or not (base_empresa or "").strip():
        return {"cabecera": {}, "eventos": [], "fuentes_fallidas": []}

    cabecera: Dict[str, Any] = {}
    eventos: List[Dict[str, Any]] = []
    fuentes_fallidas: List[str] = []

    def _fmt_fecha(v):
        if v is None:
            return None
        if hasattr(v, "strftime"):
            return v.strftime("%d/%m/%Y")
        d = to_date_or_none(str(v))
        return d.strftime("%d/%m/%Y") if d else str(v)

    # --- Cabecera desde get_op_detalle ---
    try:
        lineas_opt = get_op_detalle(base_empresa, id_lista)
        if lineas_opt:
            r0 = lineas_opt[0]
            cabecera = {
                "id_lista": id_lista,
                "id_articulo": to_int_or_none(r0.get("id_articulo")),
                "codigo_manual": str_or_default(r0.get("codigo_manual") or r0.get("codigo_articulo"), "-"),
                "descripcion": str_or_default(r0.get("descripcion_articulo"), "-"),
                "cantidad_pedida": to_int_or_none(r0.get("cantidad_pedida")) or 0,
                "estado": "en_proceso" if (r0.get("en_proceso_produccion") or "No").strip().lower() == "si" else "cerrada",
                "base_empresa": base_empresa,
            }
    except Exception as exc:
        logger.warning("construir_trazabilidad_opt: cabecera fallida para %s id_lista=%s: %s", base_empresa, id_lista, exc)
        fuentes_fallidas.append("cabecera_opt")

    if not cabecera:
        return {"cabecera": {}, "eventos": [], "fuentes_fallidas": fuentes_fallidas}

    id_articulo_pack = cabecera.get("id_articulo")

    # --- Fuente 1: lista_produccion_historico ---
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_hist = _nombre_tabla(cursor, "lista_produccion_historico")
            if tbl_hist:
                cursor.execute(
                    f"SELECT tipo_evento, id_articulo, cantidad_movimiento, fecha, hora_evento, "
                    f"id_usuario, id_operario, codigo_movimiento_mstock "
                    f"FROM {tbl_hist} WHERE id_lista_produccion = %s ORDER BY fecha, hora_evento",
                    [id_lista],
                )
                for row in (cursor.fetchall() or []):
                    tipo = str_or_default(row.get("tipo_evento"), "OPP")
                    fecha_raw = row.get("fecha")
                    eventos.append({
                        "tipo": tipo,
                        "fecha": _fmt_fecha(fecha_raw),
                        "fecha_sort": to_date_or_none(str(fecha_raw)) if fecha_raw else None,
                        "hora": str_or_default(row.get("hora_evento"), "00:00:00"),
                        "descripcion": f"Evento {tipo} (historico)",
                        "cantidad": float(to_decimal_or_none(row.get("cantidad_movimiento")) or 0),
                        "operario": str(to_int_or_none(row.get("id_operario")) or "-"),
                        "fuente": "historico",
                        "codigo_movimiento": to_int_or_none(row.get("codigo_movimiento_mstock")),
                        "id_lista_produccion": id_lista,
                    })
    except Exception as exc:
        logger.warning("construir_trazabilidad_opt: fuente historico fallida %s id_lista=%s: %s", base_empresa, id_lista, exc)
        fuentes_fallidas.append("lista_produccion_historico")

    # --- Fuente 2: movimiento_stock (OPP legacy) via listar_opp_por_opt ---
    try:
        opps = listar_opp_por_opt(base_empresa, id_lista)
        for opp in (opps or []):
            fecha_raw = opp.get("fecha")
            eventos.append({
                "tipo": "OPP",
                "fecha": _fmt_fecha(fecha_raw),
                "fecha_sort": to_date_or_none(str(fecha_raw)) if fecha_raw else None,
                "hora": "00:00:00",
                "descripcion": f"OPP legacy movimiento_stock (cod. {opp.get('codigo_movimiento', '-')})",
                "cantidad": float(opp.get("cantidad_total") or 0),
                "operario": "-",
                "fuente": "movimiento_stock",
                "codigo_movimiento": to_int_or_none(opp.get("codigo_movimiento")),
                "id_lista_produccion": id_lista,
            })
    except Exception as exc:
        logger.warning("construir_trazabilidad_opt: fuente opp_legacy fallida %s id_lista=%s: %s", base_empresa, id_lista, exc)
        fuentes_fallidas.append("movimiento_stock_opp")

    # --- Fuente 3: MprParte + MprParteAjuste (E4+) ---
    try:
        partes_qs = MprParte.objects.filter(
            base_empresa=base_empresa, id_lista_produccion=id_lista
        ).prefetch_related("lineas")
        for parte in partes_qs:
            fecha_p = parte.fecha_produccion
            turno_nombre = str(parte.turno_id)
            try:
                turno_nombre = parte.turno.nombre
            except Exception:
                pass
            for linea in parte.lineas.all():
                eventos.append({
                    "tipo": "OPP",
                    "fecha": _fmt_fecha(fecha_p),
                    "fecha_sort": fecha_p,
                    "hora": parte.registrado_en.strftime("%H:%M:%S") if parte.registrado_en else "00:00:00",
                    "descripcion": f"Parte producción turno {turno_nombre} art.{linea.id_articulo}",
                    "cantidad": float(linea.cantidad),
                    "operario": str_or_default(linea.operario_nombre, str(linea.id_operario)),
                    "fuente": "mpr_parte",
                    "codigo_movimiento": None,
                    "id_lista_produccion": id_lista,
                })
            for ajuste in MprParteAjuste.objects.filter(parte=parte):
                eventos.append({
                    "tipo": "OPP-ajuste",
                    "fecha": _fmt_fecha(ajuste.creado_en.date()),
                    "fecha_sort": ajuste.creado_en.date(),
                    "hora": ajuste.creado_en.strftime("%H:%M:%S"),
                    "descripcion": f"Ajuste parte {str(ajuste.motivo or '-')} art.{ajuste.id_articulo}",
                    "cantidad": float(ajuste.delta),
                    "operario": str(ajuste.id_operario),
                    "fuente": "mpr_parte_ajuste",
                    "codigo_movimiento": None,
                    "id_lista_produccion": id_lista,
                })
    except Exception as exc:
        logger.warning("construir_trazabilidad_opt: fuente mpr_parte fallida %s id_lista=%s: %s", base_empresa, id_lista, exc)
        fuentes_fallidas.append("mpr_parte")

    # --- Fuente 4: MprTransicionLote (por artículo pack de la OPT) ---
    if id_articulo_pack is not None:
        try:
            for tl in MprTransicionLote.objects.filter(
                base_empresa=base_empresa, id_articulo=id_articulo_pack
            ).order_by("creado_en"):
                fecha_t = tl.creado_en.date()
                eventos.append({
                    "tipo": "Transicion",
                    "fecha": _fmt_fecha(fecha_t),
                    "fecha_sort": fecha_t,
                    "hora": tl.creado_en.strftime("%H:%M:%S"),
                    "descripcion": f"Transición {tl.tipo_origen} → {tl.tipo_destino} art.{tl.id_articulo}",
                    "cantidad": float(tl.cantidad),
                    "operario": str(tl.id_usuario),
                    "fuente": "mpr_transicion_lote",
                    "codigo_movimiento": tl.codigo_movimiento,
                    "id_lista_produccion": id_lista,
                })
        except Exception as exc:
            logger.warning("construir_trazabilidad_opt: fuente transicion fallida %s: %s", base_empresa, exc)
            fuentes_fallidas.append("mpr_transicion_lote")

    # --- Fuente 5: MprArmadoSurtidoMovimiento ---
    try:
        for arm in MprArmadoSurtidoMovimiento.objects.filter(
            base_empresa=base_empresa, id_lista_produccion=id_lista
        ).order_by("creado_en"):
            fecha_a = arm.creado_en.date()
            eventos.append({
                "tipo": "Armado",
                "fecha": _fmt_fecha(fecha_a),
                "fecha_sort": fecha_a,
                "hora": arm.creado_en.strftime("%H:%M:%S"),
                "descripcion": f"Armado {arm.modo} {arm.cantidad_packs} packs",
                "cantidad": float(arm.cantidad_packs),
                "operario": str(arm.id_operario or arm.id_usuario),
                "fuente": "mpr_armado",
                "codigo_movimiento": arm.codigo_movimiento,
                "id_lista_produccion": id_lista,
            })
    except Exception as exc:
        logger.warning("construir_trazabilidad_opt: fuente armado fallida %s: %s", base_empresa, exc)
        fuentes_fallidas.append("mpr_armado")

    # --- Fuente 6: MprImputacionArmado (via codigos de armados) ---
    try:
        codigos_armado = [
            e["codigo_movimiento"] for e in eventos
            if e.get("fuente") == "mpr_armado" and e.get("codigo_movimiento") is not None
        ]
        if codigos_armado:
            for imp in MprImputacionArmado.objects.filter(
                base_empresa=base_empresa, codigo_movimiento__in=codigos_armado
            ).order_by("imputado_en"):
                fecha_i = imp.imputado_en.date()
                eventos.append({
                    "tipo": "Imputacion",
                    "fecha": _fmt_fecha(fecha_i),
                    "fecha_sort": fecha_i,
                    "hora": imp.imputado_en.strftime("%H:%M:%S"),
                    "descripcion": f"Imputación armado {imp.cantidad} packs (cod. {imp.codigo_movimiento_pedido})",
                    "cantidad": float(imp.cantidad),
                    "operario": str(imp.id_usuario_supervisor),
                    "fuente": "mpr_imputacion",
                    "codigo_movimiento": imp.codigo_movimiento,
                    "id_lista_produccion": id_lista,
                })
    except Exception as exc:
        logger.warning("construir_trazabilidad_opt: fuente imputacion fallida %s: %s", base_empresa, exc)
        fuentes_fallidas.append("mpr_imputacion")

    # Ordenar cronológicamente
    from datetime import date as _date
    eventos.sort(key=lambda e: (e.get("fecha_sort") or _date.min, e.get("hora") or "00:00:00"))
    # Limpiar campo auxiliar de sort
    for ev in eventos:
        ev.pop("fecha_sort", None)

    return {"cabecera": cabecera, "eventos": eventos, "fuentes_fallidas": fuentes_fallidas}


def construir_trazabilidad_articulo(
    base_empresa: str,
    id_articulo: int,
    fecha_desde: Optional[Any] = None,
    fecha_hasta: Optional[Any] = None,
) -> Dict[str, Any]:
    """Construye trazabilidad agregada para un artículo en un rango de fechas.

    Llama listar_lista_produccion_agrupada para obtener las OPTs del artículo,
    luego construir_trazabilidad_opt para cada OPT y agrega todos los eventos.
    Eventos huérfanos (sin OPT) se marcan como fuente='sin_opt' y descripcion='sin OPT asociada'.
    Retorna {eventos: [...], fuentes_fallidas: [...]}.
    """
    from datetime import date as _date

    id_art = to_int_or_none(id_articulo)
    if not id_art or not (base_empresa or "").strip():
        return {"eventos": [], "fuentes_fallidas": []}

    fd = to_date_or_none(str(fecha_desde)) if fecha_desde else None
    fh = to_date_or_none(str(fecha_hasta)) if fecha_hasta else None

    todos_eventos: List[Dict[str, Any]] = []
    todas_fuentes_fallidas: List[str] = []

    try:
        opts = listar_lista_produccion_agrupada(base_empresa, id_articulo=id_art)
    except Exception as exc:
        logger.warning("construir_trazabilidad_articulo: no se pudo listar opts %s art %s: %s", base_empresa, id_art, exc)
        return {"eventos": [], "fuentes_fallidas": ["listar_lista_produccion_agrupada"]}

    for opt in (opts or []):
        id_lista_row = to_int_or_none(opt.get("id_lista_produccion"))
        if id_lista_row is None:
            todos_eventos.append({
                "tipo": "sin_opt",
                "fecha": None,
                "hora": "00:00:00",
                "descripcion": "sin OPT asociada",
                "cantidad": 0,
                "operario": "-",
                "fuente": "sin_opt",
                "codigo_movimiento": None,
                "id_lista_produccion": None,
            })
            continue
        try:
            traza = construir_trazabilidad_opt(base_empresa, id_lista_row)
            for ev in traza.get("eventos", []):
                # Filtrar por rango de fechas
                fecha_ev = None
                if ev.get("fecha"):
                    fecha_ev = to_date_or_none(ev["fecha"].replace("/", "-") if "/" in str(ev["fecha"]) else ev["fecha"])
                    if fecha_ev is None and ev.get("fecha"):
                        try:
                            parts = str(ev["fecha"]).split("/")
                            if len(parts) == 3:
                                fecha_ev = _date(int(parts[2]), int(parts[1]), int(parts[0]))
                        except Exception:
                            pass
                if fd and fecha_ev and fecha_ev < fd:
                    continue
                if fh and fecha_ev and fecha_ev > fh:
                    continue
                todos_eventos.append(ev)
            todas_fuentes_fallidas.extend(traza.get("fuentes_fallidas", []))
        except Exception as exc:
            logger.warning("construir_trazabilidad_articulo: error en opt %s: %s", id_lista_row, exc)
            todas_fuentes_fallidas.append(f"opt_{id_lista_row}")

    todas_fuentes_fallidas = list(dict.fromkeys(todas_fuentes_fallidas))
    todos_eventos.sort(key=lambda e: (
        to_date_or_none(e["fecha"].replace("/", "-") if e.get("fecha") and "/" in str(e["fecha"]) else (e.get("fecha") or "")) or _date.min,
        e.get("hora") or "00:00:00",
    ))

    return {"eventos": todos_eventos, "fuentes_fallidas": todas_fuentes_fallidas}


# =============================================================================
# Etapa 9: Acciones Consolidadas — Grillas de Lote (Inspección / Clasificación)
# =============================================================================


def _construir_grilla_transicion_lote(
    base_empresa: str,
    tipo_origen: str,
) -> List[Dict[str, Any]]:
    """Universo de artículos con saldo físico en el depósito MPR de tipo_origen.

    Query directa stock_deposito JOIN deposito WHERE tipo_mpr=tipo_origen AND saldo>0
    para la empresa dada.  Luego llama _pivot_stock_por_tipo_mpr para confirmar saldo
    y _fetch_descripciones_articulo para obtener código y descripción.

    Returns: lista ordenada por codigo_manual de
        [{id_articulo, codigo_manual, descripcion, disponible}]
    """
    if not (base_empresa or "").strip() or not (tipo_origen or "").strip():
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            if not tbl_sd or not tbl_dep:
                return []
            cursor.execute(
                f"""
                SELECT DISTINCT sd.id_articulo
                FROM {tbl_sd} sd
                INNER JOIN {tbl_dep} d ON d.CodDeposito = sd.id_deposito
                WHERE COALESCE(d.anulado, 'No') = 'No'
                  AND d.tipo_mpr = %s
                  AND sd.saldo > 0
                """,
                [tipo_origen],
            )
            rows = cursor.fetchall() or []
    except Exception as e:
        logger.warning("_construir_grilla_transicion_lote error consultando candidatos: %s", e)
        return []

    ids_candidatos = [to_int_or_none(r.get("id_articulo")) for r in rows]
    ids_candidatos = [i for i in ids_candidatos if i is not None]
    if not ids_candidatos:
        return []

    stock, _ = _pivot_stock_por_tipo_mpr(base_empresa, ids_candidatos)
    ids_activos = [
        aid for aid in ids_candidatos
        if stock.get(aid, {}).get(tipo_origen, 0.0) > 0
    ]
    if not ids_activos:
        return []

    descripciones = _fetch_descripciones_articulo(base_empresa, ids_activos)
    componentes: List[Dict[str, Any]] = []
    for aid in ids_activos:
        codigo_manual, descripcion = descripciones.get(aid, ("-", "-"))
        componentes.append({
            "id_articulo": aid,
            "codigo_manual": str_or_default(codigo_manual, "-"),
            "descripcion": str_or_default(descripcion, "-"),
            "disponible": stock[aid].get(tipo_origen, 0.0),
        })
    componentes.sort(key=lambda c: c["codigo_manual"])
    return componentes


def construir_grilla_clasificacion_produccion(base_empresa: str) -> Dict[str, Any]:
    """Grilla de la pantalla 'Clasificación de producción' (Etapa 10).

    Lista los componentes con saldo físico en Producción. La clasificación sale
    directo de Producción hacia {Semi Elaborado | 2da Selección | Desperdicio}:
    el planchado es un momento dentro de la producción y no deja stock.

    Returns: {"componentes": [...], "componentes_vacio": bool}
        donde cada componente expone ``disponible`` (saldo en Producción).
    """
    componentes = _construir_grilla_transicion_lote(base_empresa, TIPO_MPR_PRODUCCION)
    return {"componentes": componentes, "componentes_vacio": len(componentes) == 0}


def transferir_stock_lote(
    base_empresa: str,
    id_usuario: int,
    items: List[Dict[str, Any]],
    fecha: "Optional[date]" = None,
) -> Dict[str, Any]:
    """Ejecuta N transferencias de stock en modo best-effort (sin atomic()).

    Cada item debe tener: {id_articulo, tipo_origen, tipo_destino, cantidad}.
    Si un ítem falla (ok=False o excepción), se acumula en errores y se continúa.

    Args:
        fecha: fecha del parte para el asiento MSTOCK. Si es None se usa la del
            sistema. Permite cargas diferidas (informe de fábrica días posteriores).

    Returns: {exitosas: int, fallidas: int,
               errores: [(id_articulo, mensaje)], comprobantes: [str]}
    """
    resultado: Dict[str, Any] = {
        "exitosas": 0,
        "fallidas": 0,
        "errores": [],
        "comprobantes": [],
    }
    for item in (items or []):
        id_art = to_int_or_none(item.get("id_articulo"))
        try:
            ok, _codigo_mov, nro, msg = transferir_stock_entre_etapas(
                base_empresa=base_empresa,
                id_usuario=id_usuario,
                id_articulo=item.get("id_articulo"),
                tipo_origen=item.get("tipo_origen", ""),
                tipo_destino=item.get("tipo_destino", ""),
                cantidad=item.get("cantidad"),
                fecha=fecha,
            )
            if ok:
                resultado["exitosas"] += 1
                resultado["comprobantes"].append(nro or "")
            else:
                resultado["fallidas"] += 1
                resultado["errores"].append((id_art, msg or "Error desconocido"))
        except Exception as e:
            resultado["fallidas"] += 1
            resultado["errores"].append((id_art, str(e)))
    return resultado
