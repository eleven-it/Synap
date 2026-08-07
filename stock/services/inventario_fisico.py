# -*- coding: utf-8 -*-
"""Servicio inventario físico / conteo ciego (campañas, snapshot, sync offline)."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)

logger = logging.getLogger(__name__)

# --- Estados campaña ---
ESTADO_BORRADOR = "Borrador"
ESTADO_EN_CONTEO = "EnConteo"
ESTADO_EN_REVISION = "EnRevision"
ESTADO_AUTORIZADO = "Autorizado"
ESTADO_APLICADO = "Aplicado"
ESTADO_ANULADO = "Anulado"

ESTADOS_CAMPANA = frozenset(
    {
        ESTADO_BORRADOR,
        ESTADO_EN_CONTEO,
        ESTADO_EN_REVISION,
        ESTADO_AUTORIZADO,
        ESTADO_APLICADO,
        ESTADO_ANULADO,
    }
)

TRANSICIONES_ESTADO: Dict[str, frozenset] = {
    ESTADO_BORRADOR: frozenset({ESTADO_EN_CONTEO, ESTADO_ANULADO}),
    ESTADO_EN_CONTEO: frozenset({ESTADO_EN_REVISION, ESTADO_ANULADO}),
    ESTADO_EN_REVISION: frozenset({ESTADO_AUTORIZADO, ESTADO_EN_CONTEO, ESTADO_ANULADO}),
    ESTADO_AUTORIZADO: frozenset({ESTADO_APLICADO, ESTADO_ANULADO}),
    ESTADO_APLICADO: frozenset(),
    ESTADO_ANULADO: frozenset(),
}

TIPOS_MPR_ELEGIBLES = frozenset({"Terminado", "2daSeleccion"})

# Terminado + Tercero (producto final almacenable/vendible) + packs Fabricado 2da
TIPOS_ART_FAB_ELEGIBLES = frozenset({"Terminado", "Tercero", "Fabricado 2da"})

RESULTADO_ACEPTADO = "aceptado"
RESULTADO_CONFLICTO = "conflicto"
RESULTADO_RECHAZADO = "rechazado"

CAMPOS_PROHIBIDOS_CONTEO = frozenset(
    {
        "saldo_snapshot",
        "saldo_sistema",
        "diferencia",
        "saldo",
        "ajuste_sistema",
        "ajuste_manual",
        "ajuste_efectivo",
        "disponible_ajustado",
        "diferencia_real",
        "saldo_actual_ref",
    }
)


# --- Funciones puras (testeables) ---


def es_tipo_mpr_elegible(tipo_mpr: Any) -> bool:
    return str_or_default(tipo_mpr, "").strip() in TIPOS_MPR_ELEGIBLES


def es_tipo_art_fab_elegible(tipo_art_fab: Any) -> bool:
    return str_or_default(tipo_art_fab, "").strip() in TIPOS_ART_FAB_ELEGIBLES


def _sql_filtro_tipo_art_fab(alias: str = "a") -> Tuple[str, List[Any]]:
    """Fragmento SQL ``AND COALESCE(TRIM(alias.tipo_art_fab), '') IN (...)``."""
    tipos = tuple(TIPOS_ART_FAB_ELEGIBLES)
    ph = ",".join(["%s"] * len(tipos))
    return f"COALESCE(TRIM({alias}.tipo_art_fab), '') IN ({ph})", list(tipos)


def calcular_diferencia(
    cantidad_contada: Any,
    saldo_snapshot: Any,
) -> Decimal:
    contado = to_decimal_or_none(cantidad_contada) or Decimal("0")
    snapshot = to_decimal_or_none(saldo_snapshot) or Decimal("0")
    return contado - snapshot


def ajuste_efectivo(ajuste_sistema: Any, ajuste_manual: Any) -> Decimal:
    """Override manual si existe; si no, neto del sistema post-snapshot."""
    manual = to_decimal_or_none(ajuste_manual)
    if manual is not None:
        return manual
    return to_decimal_or_none(ajuste_sistema) or Decimal("0")


def calcular_disponible_ajustado(saldo_snapshot: Any, ajuste_ef: Any) -> Decimal:
    snapshot = to_decimal_or_none(saldo_snapshot) or Decimal("0")
    ajuste = to_decimal_or_none(ajuste_ef) or Decimal("0")
    return snapshot + ajuste


def calcular_diferencia_real(
    cantidad_contada: Any,
    disponible_ajustado: Any,
) -> Optional[Decimal]:
    contado = to_decimal_or_none(cantidad_contada)
    if contado is None:
        return None
    disp = to_decimal_or_none(disponible_ajustado) or Decimal("0")
    return contado - disp


def hay_descuadre(
    saldo_snapshot: Any,
    ajuste_sistema: Any,
    saldo_actual_ref: Any,
) -> bool:
    """True si stock_deposito.saldo difiere de snapshot + ajuste_sistema (control)."""
    actual = to_decimal_or_none(saldo_actual_ref)
    if actual is None:
        return False
    snapshot = to_decimal_or_none(saldo_snapshot) or Decimal("0")
    ajuste = to_decimal_or_none(ajuste_sistema) or Decimal("0")
    return actual != snapshot + ajuste


def calcular_saldo_final_post_mstock(
    cantidad_contada: Any,
    diferencia_real: Any,
    saldo_actual_ref: Any,
    *,
    disponible_ajustado: Any = None,
) -> Optional[Decimal]:
    """
    Saldo esperado en ``stock_deposito`` tras autorizar el MSTOCK de la línea.

    ``saldo_actual_ref + diferencia_real``. Si no hay ``saldo_actual_ref``, asume
    que el saldo vigente es el disponible ajustado (sin descuadre). Sin conteo → None.
    Solo lectura/UI: no escribe stock ni altera el conteo.
    """
    if to_decimal_or_none(cantidad_contada) is None:
        return None
    diff = to_decimal_or_none(diferencia_real)
    if diff is None:
        return None
    actual = to_decimal_or_none(saldo_actual_ref)
    if actual is None:
        actual = to_decimal_or_none(disponible_ajustado) or Decimal("0")
    return actual + diff


def enriquecer_linea_analizador(linea: Dict[str, Any]) -> Dict[str, Any]:
    """Completa campos derivados de ajuste post-snapshot en una fila del analizador."""
    saldo_snap = to_decimal_or_none(linea.get("saldo_snapshot")) or Decimal("0")
    ajuste_sys = to_decimal_or_none(linea.get("ajuste_sistema"))
    ajuste_man = to_decimal_or_none(linea.get("ajuste_manual"))
    ajuste_eff = ajuste_efectivo(ajuste_sys, ajuste_man)
    disp_ajust = calcular_disponible_ajustado(saldo_snap, ajuste_eff)
    diff_real = to_decimal_or_none(linea.get("diferencia_real"))
    if diff_real is None:
        diff_real = calcular_diferencia_real(linea.get("cantidad_contada"), disp_ajust)
    linea["ajuste_sistema"] = ajuste_sys
    linea["ajuste_manual"] = ajuste_man
    linea["ajuste_efectivo"] = ajuste_eff
    linea["disponible_ajustado"] = disp_ajust
    linea["diferencia_real"] = diff_real
    linea["descuadre"] = hay_descuadre(saldo_snap, ajuste_sys, linea.get("saldo_actual_ref"))
    linea["saldo_final"] = calcular_saldo_final_post_mstock(
        linea.get("cantidad_contada"),
        diff_real,
        linea.get("saldo_actual_ref"),
        disponible_ajustado=disp_ajust,
    )
    return linea


def transicion_estado_permitida(estado_actual: str, estado_nuevo: str) -> bool:
    actual = str_or_default(estado_actual, ESTADO_BORRADOR)
    nuevo = str_or_default(estado_nuevo, "")
    if nuevo not in ESTADOS_CAMPANA:
        return False
    return nuevo in TRANSICIONES_ESTADO.get(actual, frozenset())


def parse_contadores_json(contadores_json: Any) -> List[int]:
    if not contadores_json:
        return []
    try:
        raw = json.loads(contadores_json) if isinstance(contadores_json, str) else contadores_json
    except (TypeError, json.JSONDecodeError):
        return []
    if not isinstance(raw, list):
        return []
    out: List[int] = []
    for item in raw:
        uid = to_int_or_none(item)
        if uid is not None:
            out.append(uid)
    return out


def parse_ids_contadores(valores: Any) -> List[int]:
    """Normaliza valores crudos (lista de POST, string CSV) a ids únicos ordenados.

    Acepta lista/tupla de ids o un string con separadores coma/espacio/salto.
    Descarta no numéricos y duplicados preservando el orden de aparición.
    """
    if valores is None:
        return []
    if isinstance(valores, str):
        crudos: List[Any] = [p for p in valores.replace(";", ",").replace("\n", ",").split(",")]
    elif isinstance(valores, (list, tuple)):
        crudos = list(valores)
    else:
        crudos = [valores]
    out: List[int] = []
    vistos: Set[int] = set()
    for item in crudos:
        uid = to_int_or_none(item)
        if uid is None or uid in vistos:
            continue
        vistos.add(uid)
        out.append(uid)
    return out


def usuario_asignado_a_campana(campana: Dict[str, Any], id_usuario: int) -> bool:
    contadores = parse_contadores_json(campana.get("contadores_json"))
    if not contadores:
        return True
    uid = to_int_or_none(id_usuario)
    return uid is not None and uid in contadores


def evaluar_resultado_evento_sync(
    linea_actual: Optional[Dict[str, Any]],
    id_contador: int,
    cantidad: Decimal,
) -> str:
    if not linea_actual:
        return RESULTADO_ACEPTADO
    prev_contador = to_int_or_none(linea_actual.get("id_contador"))
    prev_cantidad = to_decimal_or_none(linea_actual.get("cantidad_contada"))
    if prev_contador == id_contador:
        return RESULTADO_ACEPTADO
    if prev_cantidad is not None and prev_cantidad != cantidad:
        return RESULTADO_CONFLICTO
    return RESULTADO_ACEPTADO


def serializar_articulo_catalogo_ciego(fila: Dict[str, Any]) -> Dict[str, Any]:
    ean_raw = fila.get("ean") or fila.get("eans") or []
    if isinstance(ean_raw, str):
        ean_list = [e.strip() for e in ean_raw.split(",") if e.strip()]
    elif isinstance(ean_raw, (list, tuple)):
        ean_list = [str_or_default(e, "") for e in ean_raw if str_or_default(e, "")]
    else:
        ean_list = []
    return {
        "id_articulo": to_int_or_none(fila.get("id_articulo")),
        "codigo": str_or_default(fila.get("codigo"), "-"),
        "nombre": str_or_default(fila.get("nombre"), "-"),
        "ean": ean_list,
    }


def serializar_prefetch_ciego(data: Dict[str, Any]) -> Dict[str, Any]:
    articulos = [
        serializar_articulo_catalogo_ciego(a)
        for a in (data.get("articulos") or [])
    ]
    return {
        "id_campana": to_int_or_none(data.get("id_campana")),
        "id_deposito": to_int_or_none(data.get("id_deposito")),
        "catalogo_version": str_or_default(data.get("catalogo_version"), ""),
        "prefetch_ts": data.get("prefetch_ts") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "articulos": articulos,
    }


def serializar_conteo_registrado(fila: Dict[str, Any]) -> Dict[str, Any]:
    """Ítem de registro de conteo para el operario (sin saldo ni diferencia)."""
    cantidad = to_decimal_or_none(fila.get("cantidad") if "cantidad" in fila else fila.get("cantidad_contada"))
    cantidad_txt = ""
    if cantidad is not None:
        if cantidad == cantidad.to_integral_value():
            cantidad_txt = str(int(cantidad))
        else:
            cantidad_txt = format(cantidad.normalize(), "f")
    ts = fila.get("ts") or fila.get("updated_at") or ""
    if hasattr(ts, "strftime"):
        ts = ts.strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "id_articulo": to_int_or_none(fila.get("id_articulo")),
        "codigo": str_or_default(fila.get("codigo"), "-"),
        "nombre": str_or_default(fila.get("nombre"), "-"),
        "cantidad": cantidad_txt,
        "ts": str_or_default(ts, ""),
    }


def serializar_conteos_registrados(data: Dict[str, Any]) -> Dict[str, Any]:
    items = [serializar_conteo_registrado(x) for x in (data.get("contados") or [])]
    return {
        "id_campana": to_int_or_none(data.get("id_campana")),
        "id_deposito": to_int_or_none(data.get("id_deposito")),
        "total_contados": len(items),
        "contados": items,
    }


def serializar_respuesta_sync(
    aceptados: List[Dict[str, Any]],
    conflictos: List[Dict[str, Any]],
    rechazados: List[Dict[str, Any]],
) -> Dict[str, Any]:
    def _limpiar(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for it in items:
            row = {k: v for k, v in it.items() if k not in CAMPOS_PROHIBIDOS_CONTEO}
            out.append(row)
        return out

    return {
        "aceptados": _limpiar(aceptados),
        "conflictos": _limpiar(conflictos),
        "rechazados": _limpiar(rechazados),
    }


def buscar_claves_prohibidas_conteo(payload: Any, prefijo: str = "") -> Set[str]:
    encontradas: Set[str] = set()
    if isinstance(payload, dict):
        for k, v in payload.items():
            clave = f"{prefijo}.{k}" if prefijo else k
            if k in CAMPOS_PROHIBIDOS_CONTEO:
                encontradas.add(k)
            encontradas |= buscar_claves_prohibidas_conteo(v, clave)
    elif isinstance(payload, (list, tuple)):
        for item in payload:
            encontradas |= buscar_claves_prohibidas_conteo(item, prefijo)
    return encontradas


# --- Helpers MySQL ---


def _nombre_tabla(cursor, nombre_lower: str) -> Optional[str]:
    cursor.execute("SHOW TABLES")
    for row in cursor.fetchall():
        nombre = (row[0] if not isinstance(row, dict) else list(row.values())[0]) or ""
        if str(nombre).strip().lower() == nombre_lower:
            return str(nombre).strip()
    return None


def _fetch_deposito(cursor, id_deposito: int) -> Optional[Dict[str, Any]]:
    tbl = _nombre_tabla(cursor, "deposito")
    if not tbl:
        return None
    t = tbl.replace("`", "``")
    cursor.execute(
        f"SELECT CodDeposito, COALESCE(tipo_mpr, '') AS tipo_mpr, "
        f"COALESCE(suma_stock, 'Si') AS suma_stock "
        f"FROM `{t}` WHERE CodDeposito = %s AND COALESCE(anulado, 'No') = 'No'",
        [id_deposito],
    )
    return cursor.fetchone()


def _validar_deposito_elegible(deposito: Optional[Dict[str, Any]]) -> Optional[str]:
    if not deposito:
        return "Depósito no encontrado o anulado."
    if not es_tipo_mpr_elegible(deposito.get("tipo_mpr")):
        return "El depósito no es elegible para inventario físico MPR."
    if str_or_default(deposito.get("suma_stock"), "Si").strip().lower() not in ("si", "sí"):
        return "El depósito no suma stock en inventario MPR."
    return None


def _row_campana(row: Dict[str, Any]) -> Dict[str, Any]:
    if not row:
        return {}
    depositos = []
    try:
        depositos = json.loads(row.get("depositos_json") or "[]")
    except json.JSONDecodeError:
        depositos = []
    return {
        "id_campana": to_int_or_none(row.get("id_campana")),
        "fecha": str(row.get("fecha") or "")[:10],
        "estado": str_or_default(row.get("estado"), ESTADO_BORRADOR),
        "depositos": depositos,
        "catalogo_version": str_or_default(row.get("catalogo_version"), ""),
        "contadores": parse_contadores_json(row.get("contadores_json")),
        "id_usuario_alta": to_int_or_none(row.get("id_usuario_alta")),
        "fecha_snapshot": row.get("fecha_snapshot"),
    }


# --- Operaciones campaña ---


def listar_depositos_elegibles(base_empresa: str) -> List[Dict[str, Any]]:
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl = _nombre_tabla(cursor, "deposito")
            if not tbl:
                return []
            t = tbl.replace("`", "``")
            tipos = tuple(TIPOS_MPR_ELEGIBLES)
            ph = ",".join(["%s"] * len(tipos))
            cursor.execute(
                f"SELECT CodDeposito AS id_deposito, COALESCE(NombreDeposito, '') AS nombre, "
                f"COALESCE(tipo_mpr, '') AS tipo_mpr "
                f"FROM `{t}` "
                f"WHERE COALESCE(anulado, 'No') = 'No' "
                f"AND COALESCE(suma_stock, 'Si') = 'Si' "
                f"AND TRIM(COALESCE(tipo_mpr, '')) IN ({ph}) "
                f"ORDER BY NombreDeposito",
                list(tipos),
            )
            return [dict(r) for r in cursor.fetchall()]
    except Exception as exc:
        logger.warning("listar_depositos_elegibles %s: %s", base_empresa, exc)
        return []


def listar_contadores_candidatos(base_empresa: str) -> List[Dict[str, Any]]:
    """Usuarios de login candidatos a contador (reutiliza el listado MPR).

    Devuelve `[{id_usuario, cod_usuario, nombre_completo}]`. El permiso de conteo
    (`stock.inventario_fisico.contar`) se valida al abrir la app móvil; aquí se
    ofrece el universo de usuarios para asignar.
    """
    base = str_or_default(base_empresa, "").strip()
    if not base:
        return []
    try:
        from mpr.services_operario import listar_usuarios

        usuarios = listar_usuarios(base) or []
    except Exception as exc:
        logger.warning("listar_contadores_candidatos %s: %s", base_empresa, exc)
        return []
    candidatos: List[Dict[str, Any]] = []
    for u in usuarios:
        uid = to_int_or_none(u.get("id_usuario"))
        if uid is None:
            continue
        candidatos.append(
            {
                "id_usuario": uid,
                "cod_usuario": str_or_default(u.get("cod_usuario"), ""),
                "nombre_completo": str_or_default(u.get("nombre_completo"), ""),
            }
        )
    return candidatos


def etiquetar_contadores(
    contadores_ids: Sequence[int],
    candidatos: Sequence[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Enlaza ids asignados con su nombre/código a partir de los candidatos."""
    indice = {
        to_int_or_none(c.get("id_usuario")): c
        for c in (candidatos or [])
        if to_int_or_none(c.get("id_usuario")) is not None
    }
    detalle: List[Dict[str, Any]] = []
    for raw in contadores_ids or []:
        uid = to_int_or_none(raw)
        if uid is None:
            continue
        cand = indice.get(uid)
        if cand:
            nombre = str_or_default(cand.get("nombre_completo"), "").strip()
            cod = str_or_default(cand.get("cod_usuario"), "").strip()
            etiqueta = nombre or cod or f"Usuario #{uid}"
            if nombre and cod:
                etiqueta = f"{cod} · {nombre}"
        else:
            etiqueta = f"Usuario #{uid}"
        detalle.append({"id_usuario": uid, "etiqueta": etiqueta})
    return detalle


def listar_campanas_para_contador(
    base_empresa: str,
    id_usuario: int,
) -> List[Dict[str, Any]]:
    """Campañas EnConteo asignadas al operario contador."""
    uid = to_int_or_none(id_usuario)
    if uid is None:
        return []
    resultado: List[Dict[str, Any]] = []
    for campana in listar_campanas(base_empresa):
        if campana.get("estado") != ESTADO_EN_CONTEO:
            continue
        if usuario_asignado_a_campana(campana, uid):
            resultado.append(campana)
    return resultado


def listar_campanas(base_empresa: str) -> List[Dict[str, Any]]:
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT id_campana, fecha, estado, depositos_json, catalogo_version, "
                "contadores_json, id_usuario_alta, fecha_snapshot, created_at "
                "FROM inv_fisico_campana ORDER BY fecha DESC, id_campana DESC"
            )
            return [_row_campana(r) for r in cursor.fetchall()]
    except Exception as exc:
        logger.warning("listar_campanas %s: %s", base_empresa, exc)
        return []


def obtener_campana(base_empresa: str, id_campana: int) -> Optional[Dict[str, Any]]:
    cid = to_int_or_none(id_campana)
    if cid is None:
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT id_campana, fecha, estado, depositos_json, catalogo_version, "
                "contadores_json, id_usuario_alta, fecha_snapshot, created_at "
                "FROM inv_fisico_campana WHERE id_campana = %s",
                [cid],
            )
            row = cursor.fetchone()
            return _row_campana(row) if row else None
    except Exception as exc:
        logger.warning("obtener_campana %s/%s: %s", base_empresa, id_campana, exc)
        return None


def crear_campana(
    base_empresa: str,
    *,
    fecha: str,
    depositos_ids: Sequence[int],
    id_usuario_alta: int,
) -> Tuple[bool, Dict[str, Any]]:
    fecha_norm = to_date_or_none(fecha)
    if not fecha_norm:
        return False, {"error": "Fecha inválida."}
    dep_ids = [to_int_or_none(d) for d in depositos_ids]
    dep_ids = [d for d in dep_ids if d is not None]
    if not dep_ids:
        return False, {"error": "Debe seleccionar al menos un depósito."}

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            for did in dep_ids:
                dep = _fetch_deposito(cursor, did)
                err = _validar_deposito_elegible(dep)
                if err:
                    return False, {"error": err, "id_deposito": did}

            catalogo_version = uuid.uuid4().hex[:16]
            depositos_json = json.dumps(dep_ids)
            cursor.execute(
                "INSERT INTO inv_fisico_campana "
                "(fecha, estado, depositos_json, catalogo_version, id_usuario_alta, fecha_snapshot) "
                "VALUES (%s, %s, %s, %s, %s, NOW())",
                [fecha_norm, ESTADO_BORRADOR, depositos_json, catalogo_version, id_usuario_alta],
            )
            id_campana = cursor.lastrowid

            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            if not tbl_sd:
                return False, {"error": "Tabla stock_deposito no encontrada."}
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return False, {"error": "Tabla articulo no encontrada."}
            tsd = tbl_sd.replace("`", "``")
            ta = tbl_art.replace("`", "``")
            filtro_art, params_art = _sql_filtro_tipo_art_fab("a")
            lineas = 0
            for did in dep_ids:
                cursor.execute(
                    f"SELECT sd.id_articulo, COALESCE(sd.saldo, 0) AS saldo "
                    f"FROM `{tsd}` sd "
                    f"INNER JOIN `{ta}` a ON a.IDArt = sd.id_articulo "
                    f"WHERE sd.id_deposito = %s AND {filtro_art}",
                    [did, *params_art],
                )
                for fila in cursor.fetchall():
                    id_art = to_int_or_none(fila.get("id_articulo"))
                    if id_art is None:
                        continue
                    saldo = to_decimal_or_none(fila.get("saldo")) or Decimal("0")
                    cursor.execute(
                        "INSERT INTO inv_fisico_linea "
                        "(id_campana, id_articulo, id_deposito, saldo_snapshot, estado_linea) "
                        "VALUES (%s, %s, %s, %s, 'Pendiente') "
                        "ON DUPLICATE KEY UPDATE saldo_snapshot = VALUES(saldo_snapshot)",
                        [id_campana, id_art, did, saldo],
                    )
                    lineas += 1

            return True, {
                "id_campana": id_campana,
                "estado": ESTADO_BORRADOR,
                "lineas": lineas,
                "catalogo_version": catalogo_version,
            }
    except Exception as exc:
        logger.exception("crear_campana %s: %s", base_empresa, exc)
        return False, {"error": "No se pudo crear la campaña."}


def asignar_contadores(
    base_empresa: str,
    id_campana: int,
    contadores_ids: Sequence[int],
) -> Tuple[bool, Dict[str, Any]]:
    contadores = [to_int_or_none(c) for c in contadores_ids]
    contadores = [c for c in contadores if c is not None]
    if not contadores:
        return False, {"error": "Debe indicar al menos un contador."}
    cid = to_int_or_none(id_campana)
    if cid is None:
        return False, {"error": "Campaña inválida."}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "UPDATE inv_fisico_campana SET contadores_json = %s WHERE id_campana = %s",
                [json.dumps(contadores), cid],
            )
            if cursor.rowcount == 0:
                return False, {"error": "Campaña no encontrada."}
            return True, {"id_campana": cid, "contadores": contadores}
    except Exception as exc:
        logger.warning("asignar_contadores %s: %s", base_empresa, exc)
        return False, {"error": "No se pudo asignar contadores."}


def transicionar_campana(
    base_empresa: str,
    id_campana: int,
    estado_nuevo: str,
) -> Tuple[bool, Dict[str, Any]]:
    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        return False, {"error": "Campaña no encontrada."}
    if not transicion_estado_permitida(campana["estado"], estado_nuevo):
        return False, {
            "error": f"Transición {campana['estado']} → {estado_nuevo} no permitida.",
        }
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "UPDATE inv_fisico_campana SET estado = %s WHERE id_campana = %s",
                [estado_nuevo, id_campana],
            )
        return True, {"id_campana": id_campana, "estado": estado_nuevo}
    except Exception as exc:
        logger.warning("transicionar_campana %s: %s", base_empresa, exc)
        return False, {"error": "No se pudo actualizar el estado."}


def obtener_progreso_campana(base_empresa: str, id_campana: int) -> Dict[str, Any]:
    cid = to_int_or_none(id_campana)
    if cid is None:
        return {"total": 0, "contados": 0, "pendientes": 0, "porcentaje": 0}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total, "
                "SUM(CASE WHEN cantidad_contada IS NOT NULL THEN 1 ELSE 0 END) AS contados "
                "FROM inv_fisico_linea WHERE id_campana = %s",
                [cid],
            )
            row = cursor.fetchone() or {}
            total = to_int_or_none(row.get("total")) or 0
            contados = to_int_or_none(row.get("contados")) or 0
            pendientes = max(total - contados, 0)
            pct = round(contados * 100 / total, 1) if total else 0
            return {
                "total": total,
                "contados": contados,
                "pendientes": pendientes,
                "porcentaje": pct,
            }
    except Exception as exc:
        logger.warning("obtener_progreso_campana %s: %s", base_empresa, exc)
        return {"total": 0, "contados": 0, "pendientes": 0, "porcentaje": 0}


# --- Prefetch ciego y sync ---


def prefetch_catalogo_ciego(
    base_empresa: str,
    id_campana: int,
    id_deposito: int,
    id_usuario: int,
) -> Tuple[bool, Dict[str, Any]]:
    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        return False, {"error": "Campaña no encontrada."}
    if campana["estado"] not in (ESTADO_EN_CONTEO, ESTADO_BORRADOR):
        return False, {"error": "La campaña no está abierta para conteo."}
    if not usuario_asignado_a_campana(campana, id_usuario):
        return False, {"error": "No está asignado a esta campaña."}
    dep = to_int_or_none(id_deposito)
    if dep is None or dep not in campana.get("depositos", []):
        return False, {"error": "Depósito no pertenece a la campaña."}

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return False, {"error": "Tabla articulo no encontrada."}
            ta = tbl_art.replace("`", "``")
            filtro_art, params_art = _sql_filtro_tipo_art_fab("a")
            cursor.execute(
                f"SELECT l.id_articulo, "
                f"COALESCE(a.id_manual, '-') AS codigo, "
                f"COALESCE(a.NombreArticulo, '') AS nombre, "
                f"COALESCE(a.NroCodBarra, '') AS ean1, "
                f"COALESCE(a.NroCodBarraF, '') AS ean2 "
                f"FROM inv_fisico_linea l "
                f"INNER JOIN `{ta}` a ON a.IDArt = l.id_articulo "
                f"WHERE l.id_campana = %s AND l.id_deposito = %s AND {filtro_art} "
                f"ORDER BY a.NombreArticulo",
                [id_campana, dep, *params_art],
            )
            articulos = []
            for r in cursor.fetchall():
                eans = []
                for key in ("ean1", "ean2"):
                    val = str_or_default(r.get(key), "").strip()
                    if val and val not in eans:
                        eans.append(val)
                articulos.append(
                    {
                        "id_articulo": r.get("id_articulo"),
                        "codigo": r.get("codigo"),
                        "nombre": r.get("nombre"),
                        "ean": eans,
                    }
                )
            raw = {
                "id_campana": id_campana,
                "id_deposito": dep,
                "catalogo_version": campana.get("catalogo_version"),
                "articulos": articulos,
            }
            return True, serializar_prefetch_ciego(raw)
    except Exception as exc:
        logger.exception("prefetch_catalogo_ciego %s: %s", base_empresa, exc)
        return False, {"error": "No se pudo obtener el catálogo."}


def listar_conteos_registrados_ciego(
    base_empresa: str,
    id_campana: int,
    id_deposito: int,
    id_usuario: int,
) -> Tuple[bool, Dict[str, Any]]:
    """Líneas ya contadas del depósito (ciego: sin saldo/diferencia) para control del operario."""
    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        return False, {"error": "Campaña no encontrada."}
    if campana["estado"] not in (ESTADO_EN_CONTEO, ESTADO_EN_REVISION, ESTADO_BORRADOR):
        return False, {"error": "La campaña no admite consulta de conteos."}
    if not usuario_asignado_a_campana(campana, id_usuario):
        return False, {"error": "No está asignado a esta campaña."}
    dep = to_int_or_none(id_deposito)
    if dep is None or dep not in campana.get("depositos", []):
        return False, {"error": "Depósito no pertenece a la campaña."}

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_art:
                return False, {"error": "Tabla articulo no encontrada."}
            ta = tbl_art.replace("`", "``")
            filtro_art, params_art = _sql_filtro_tipo_art_fab("a")
            cursor.execute(
                f"SELECT l.id_articulo, "
                f"COALESCE(a.id_manual, '-') AS codigo, "
                f"COALESCE(a.NombreArticulo, '') AS nombre, "
                f"l.cantidad_contada AS cantidad, "
                f"l.updated_at AS updated_at "
                f"FROM inv_fisico_linea l "
                f"INNER JOIN `{ta}` a ON a.IDArt = l.id_articulo "
                f"WHERE l.id_campana = %s AND l.id_deposito = %s "
                f"AND l.cantidad_contada IS NOT NULL AND {filtro_art} "
                f"ORDER BY l.updated_at DESC, a.NombreArticulo",
                [id_campana, dep, *params_art],
            )
            contados = [dict(r) for r in cursor.fetchall()]
            return True, serializar_conteos_registrados(
                {
                    "id_campana": id_campana,
                    "id_deposito": dep,
                    "contados": contados,
                }
            )
    except Exception as exc:
        logger.exception("listar_conteos_registrados_ciego %s: %s", base_empresa, exc)
        return False, {"error": "No se pudo obtener el registro de conteos."}


def _proyectar_linea(
    cursor,
    id_campana: int,
    id_articulo: int,
    id_deposito: int,
    id_contador: int,
    cantidad: Decimal,
    *,
    solo_si_sin_contar: bool = False,
) -> int:
    cursor.execute(
        "SELECT saldo_snapshot FROM inv_fisico_linea "
        "WHERE id_campana = %s AND id_articulo = %s AND id_deposito = %s",
        [id_campana, id_articulo, id_deposito],
    )
    snap_row = cursor.fetchone()
    saldo = to_decimal_or_none(snap_row.get("saldo_snapshot") if snap_row else None) or Decimal("0")
    diff = calcular_diferencia(cantidad, saldo)
    sql = (
        "UPDATE inv_fisico_linea SET cantidad_contada = %s, diferencia = %s, "
        "id_contador = %s, estado_linea = 'Contado', updated_at = NOW() "
        "WHERE id_campana = %s AND id_articulo = %s AND id_deposito = %s"
    )
    if solo_si_sin_contar:
        sql += " AND cantidad_contada IS NULL"
    cursor.execute(
        sql,
        [cantidad, diff, id_contador, id_campana, id_articulo, id_deposito],
    )
    return int(cursor.rowcount or 0)


def sync_eventos(
    base_empresa: str,
    id_campana: int,
    eventos: Sequence[Dict[str, Any]],
    id_usuario: int,
) -> Dict[str, Any]:
    aceptados: List[Dict[str, Any]] = []
    conflictos: List[Dict[str, Any]] = []
    rechazados: List[Dict[str, Any]] = []

    uid = to_int_or_none(id_usuario)
    if uid is None:
        rechazados.append({"client_event_id": "", "motivo": "Usuario inválido."})
        return serializar_respuesta_sync(aceptados, conflictos, rechazados)

    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        for ev in eventos or []:
            cid = str_or_default(ev.get("client_event_id"), "").strip()
            rechazados.append(
                {"client_event_id": cid, "motivo": "Campaña no encontrada."}
            )
        return serializar_respuesta_sync(aceptados, conflictos, rechazados)

    eventos_ordenados = sorted(
        list(eventos or []),
        key=lambda e: str_or_default(e.get("client_ts"), ""),
    )

    for ev in eventos_ordenados:
        client_event_id = str_or_default(ev.get("client_event_id"), "").strip()
        if not client_event_id:
            rechazados.append({"client_event_id": "", "motivo": "Falta client_event_id."})
            continue

        if campana["estado"] != ESTADO_EN_CONTEO:
            rechazados.append(
                {
                    "client_event_id": client_event_id,
                    "motivo": "La campaña no está en conteo.",
                }
            )
            continue
        if not usuario_asignado_a_campana(campana, uid):
            rechazados.append(
                {
                    "client_event_id": client_event_id,
                    "motivo": "Sin asignación a la campaña.",
                }
            )
            continue

        try:
            with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
                cursor.execute(
                    "SELECT client_event_id, resultado FROM inv_fisico_evento "
                    "WHERE client_event_id = %s",
                    [client_event_id],
                )
                existente = cursor.fetchone()
                if existente:
                    aceptados.append(
                        {
                            "client_event_id": client_event_id,
                            "resultado": existente.get("resultado", RESULTADO_ACEPTADO),
                            "idempotente": True,
                        }
                    )
                    continue

                id_art = to_int_or_none(ev.get("id_articulo"))
                id_dep = to_int_or_none(ev.get("id_deposito"))
                cantidad = to_decimal_or_none(ev.get("cantidad"))
                client_ts = to_date_or_none(ev.get("client_ts")) or datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                if id_art is None or id_dep is None or cantidad is None:
                    rechazados.append(
                        {
                            "client_event_id": client_event_id,
                            "motivo": "Datos de evento incompletos o inválidos.",
                        }
                    )
                    continue

                cursor.execute(
                    "SELECT id_linea, id_contador, cantidad_contada, saldo_snapshot "
                    "FROM inv_fisico_linea "
                    "WHERE id_campana = %s AND id_articulo = %s AND id_deposito = %s",
                    [id_campana, id_art, id_dep],
                )
                linea = cursor.fetchone()
                if not linea:
                    rechazados.append(
                        {
                            "client_event_id": client_event_id,
                            "motivo": "Artículo no pertenece a la campaña.",
                        }
                    )
                    continue

                resultado = evaluar_resultado_evento_sync(linea, uid, cantidad)
                if resultado == RESULTADO_CONFLICTO:
                    motivo = (
                        "Conflicto: otro contador registró una cantidad distinta "
                        "para el mismo artículo."
                    )
                    cursor.execute(
                        "INSERT INTO inv_fisico_evento "
                        "(client_event_id, id_campana, id_articulo, id_deposito, id_contador, "
                        "cantidad, client_ts, resultado, motivo) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        [
                            client_event_id,
                            id_campana,
                            id_art,
                            id_dep,
                            uid,
                            cantidad,
                            client_ts,
                            RESULTADO_CONFLICTO,
                            motivo,
                        ],
                    )
                    conflictos.append(
                        {"client_event_id": client_event_id, "motivo": motivo, "resultado": resultado}
                    )
                    continue

                cursor.execute(
                    "INSERT INTO inv_fisico_evento "
                    "(client_event_id, id_campana, id_articulo, id_deposito, id_contador, "
                    "cantidad, client_ts, resultado) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        client_event_id,
                        id_campana,
                        id_art,
                        id_dep,
                        uid,
                        cantidad,
                        client_ts,
                        RESULTADO_ACEPTADO,
                    ],
                )
                _proyectar_linea(cursor, id_campana, id_art, id_dep, uid, cantidad)
                aceptados.append(
                    {
                        "client_event_id": client_event_id,
                        "id_articulo": id_art,
                        "cantidad": str(cantidad),
                        "resultado": RESULTADO_ACEPTADO,
                    }
                )
        except Exception as exc:
            logger.warning("sync_evento %s: %s", client_event_id, exc)
            rechazados.append(
                {"client_event_id": client_event_id, "motivo": "Error al procesar el evento."}
            )

    return serializar_respuesta_sync(aceptados, conflictos, rechazados)


# --- Analizador, autorización y MSTOCK (Fase 6) ---

MOTIVO_FALTANTE = 3
MOTIVO_SOBRANTE = 4

ACCION_AUDIT_OVERRIDE_GUARDADO = "override_guardado"
ACCION_AUDIT_OVERRIDE_QUITADO = "override_quitado"
ACCION_AUDIT_OVERRIDE_PISADO = "override_pisado"
ACCION_AUDIT_AUTORIZACION = "autorizacion"
ACCION_AUDIT_CONTADO_CERO_MASIVO = "contado_cero_masivo"

MOTIVO_CONTADO_CERO_SUPERVISOR = "Supervisor: no encontrado / contado 0"


def _insert_auditoria_ajuste(
    cursor,
    *,
    id_campana: int,
    id_linea: int,
    id_articulo: int,
    id_deposito: int,
    accion: str,
    id_usuario: int,
    ajuste_sistema: Optional[Decimal] = None,
    ajuste_anterior: Optional[Decimal] = None,
    ajuste_nuevo: Optional[Decimal] = None,
    diferencia_real: Optional[Decimal] = None,
    codigo_movimiento: Optional[int] = None,
) -> None:
    cursor.execute(
        "INSERT INTO inv_fisico_ajuste_auditoria "
        "(id_campana, id_linea, id_articulo, id_deposito, accion, "
        "ajuste_sistema, ajuste_anterior, ajuste_nuevo, diferencia_real, "
        "codigo_movimiento, id_usuario) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
        [
            id_campana,
            id_linea,
            id_articulo,
            id_deposito,
            accion,
            ajuste_sistema,
            ajuste_anterior,
            ajuste_nuevo,
            diferencia_real,
            codigo_movimiento,
            id_usuario,
        ],
    )


def calcular_ajuste_post_snapshot(
    base_empresa: str,
    id_campana: int,
) -> Dict[Tuple[int, int], Decimal]:
    """Neto agregado (entrada − salida) post-snapshot por (id_articulo, id_deposito)."""
    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        return {}
    fecha_snapshot = campana.get("fecha_snapshot")
    if not fecha_snapshot:
        return {}
    depositos = [
        d for d in (to_int_or_none(x) for x in (campana.get("depositos") or [])) if d is not None
    ]
    if not depositos:
        return {}

    resultado: Dict[Tuple[int, int], Decimal] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_stock:
                return {}
            ts = tbl_stock.replace("`", "``")
            ph = ",".join(["%s"] * len(depositos))
            cursor.execute(
                f"SELECT s.IDArt AS id_articulo, s.CodDeposito AS id_deposito, "
                f"SUM(COALESCE(s.Entrada, 0)) - SUM(COALESCE(s.Salida, 0)) AS neto "
                f"FROM `{ts}` s "
                f"WHERE s.CodDeposito IN ({ph}) "
                f"AND s.FechaControl >= %s "
                f"AND COALESCE(s.Anulado, 'No') <> 'Si' "
                f"GROUP BY s.IDArt, s.CodDeposito",
                [*depositos, fecha_snapshot],
            )
            for row in cursor.fetchall():
                id_art = to_int_or_none(row.get("id_articulo"))
                id_dep = to_int_or_none(row.get("id_deposito"))
                if id_art is None or id_dep is None:
                    continue
                neto = to_decimal_or_none(row.get("neto")) or Decimal("0")
                resultado[(id_art, id_dep)] = neto
    except Exception as exc:
        logger.warning("calcular_ajuste_post_snapshot %s/%s: %s", base_empresa, id_campana, exc)
    return resultado


def listar_movimientos_post_snapshot(
    base_empresa: str,
    id_campana: int,
    id_articulo: int,
    id_deposito: int,
) -> List[Dict[str, Any]]:
    """Desglose de movimientos legacy posteriores al snapshot (solo lectura)."""
    campana = obtener_campana(base_empresa, id_campana)
    if not campana or not campana.get("fecha_snapshot"):
        return []
    id_art = to_int_or_none(id_articulo)
    id_dep = to_int_or_none(id_deposito)
    if id_art is None or id_dep is None:
        return []

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_stock = _nombre_tabla(cursor, "stock")
            if not tbl_stock:
                return []
            ts = tbl_stock.replace("`", "``")
            tbl_ms = _nombre_tabla(cursor, "movimiento_stock")
            join_ms = ""
            select_detalle = "'' AS detalle"
            if tbl_ms:
                tms = tbl_ms.replace("`", "``")
                join_ms = f"LEFT JOIN `{tms}` ms ON ms.codigo_movimiento = s.CodigoMovimiento "
                select_detalle = "COALESCE(ms.detalle, '') AS detalle"
            cursor.execute(
                f"SELECT s.id_stock, s.FechaControl, s.Fecha, "
                f"COALESCE(s.Entrada, 0) AS Entrada, COALESCE(s.Salida, 0) AS Salida, "
                f"COALESCE(s.TipoComp, '-') AS motivo, "
                f"COALESCE(s.NroComprobante, '-') AS nro, "
                f"{select_detalle} "
                f"FROM `{ts}` s "
                f"{join_ms}"
                f"WHERE s.IDArt = %s AND s.CodDeposito = %s "
                f"AND s.FechaControl >= %s AND COALESCE(s.Anulado, 'No') <> 'Si' "
                f"ORDER BY s.FechaControl, s.id_stock",
                [id_art, id_dep, campana["fecha_snapshot"]],
            )
            movimientos: List[Dict[str, Any]] = []
            for row in cursor.fetchall():
                entrada = to_decimal_or_none(row.get("Entrada")) or Decimal("0")
                salida = to_decimal_or_none(row.get("Salida")) or Decimal("0")
                fc = row.get("FechaControl")
                fc_txt = fc.strftime("%d/%m/%Y") if hasattr(fc, "strftime") else str_or_default(fc, "")
                movimientos.append(
                    {
                        "id_stock": to_int_or_none(row.get("id_stock")),
                        "fecha_control": fc_txt,
                        "fecha": row.get("Fecha"),
                        "entrada": entrada,
                        "salida": salida,
                        "neto": entrada - salida,
                        "motivo": str_or_default(row.get("motivo"), "-"),
                        "nro": str_or_default(row.get("nro"), "-"),
                        "detalle": str_or_default(row.get("detalle"), ""),
                    }
                )
            return movimientos
    except Exception as exc:
        logger.warning("listar_movimientos_post_snapshot: %s", exc)
        return []


def _fetch_saldos_deposito(
    cursor,
    id_articulo: int,
    depositos: Sequence[int],
) -> Dict[int, Decimal]:
    tbl_sd = _nombre_tabla(cursor, "stock_deposito")
    if not tbl_sd or not depositos:
        return {}
    tsd = tbl_sd.replace("`", "``")
    ph = ",".join(["%s"] * len(depositos))
    cursor.execute(
        f"SELECT id_deposito, COALESCE(saldo, 0) AS saldo "
        f"FROM `{tsd}` WHERE id_articulo = %s AND id_deposito IN ({ph})",
        [id_articulo, *depositos],
    )
    out: Dict[int, Decimal] = {}
    for row in cursor.fetchall():
        id_dep = to_int_or_none(row.get("id_deposito"))
        if id_dep is not None:
            out[id_dep] = to_decimal_or_none(row.get("saldo")) or Decimal("0")
    return out


def recalcular_ajuste_post_snapshot(
    base_empresa: str,
    id_campana: int,
    *,
    id_usuario: int,
    pisar_overrides: bool = False,
) -> Tuple[bool, Dict[str, Any]]:
    """Persiste ajuste_sistema, saldo_actual_ref y diferencia_real por línea."""
    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        return False, {"error": "Campaña no encontrada."}
    if campana["estado"] in (ESTADO_APLICADO, ESTADO_ANULADO):
        return True, {"omitido": True, "motivo": "estado_final"}

    netos = calcular_ajuste_post_snapshot(base_empresa, id_campana)
    uid = to_int_or_none(id_usuario) or 0
    lineas_actualizadas = 0
    overrides_pisados = 0

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT id_linea, id_articulo, id_deposito, saldo_snapshot, "
                "cantidad_contada, ajuste_manual "
                "FROM inv_fisico_linea WHERE id_campana = %s",
                [id_campana],
            )
            lineas = [dict(r) for r in cursor.fetchall()]

            for linea in lineas:
                id_linea = to_int_or_none(linea.get("id_linea"))
                id_art = to_int_or_none(linea.get("id_articulo"))
                id_dep = to_int_or_none(linea.get("id_deposito"))
                if id_linea is None or id_art is None or id_dep is None:
                    continue

                ajuste_sys = netos.get((id_art, id_dep), Decimal("0"))
                saldo_snap = to_decimal_or_none(linea.get("saldo_snapshot")) or Decimal("0")
                ajuste_manual = to_decimal_or_none(linea.get("ajuste_manual"))

                if pisar_overrides and ajuste_manual is not None:
                    _insert_auditoria_ajuste(
                        cursor,
                        id_campana=id_campana,
                        id_linea=id_linea,
                        id_articulo=id_art,
                        id_deposito=id_dep,
                        accion=ACCION_AUDIT_OVERRIDE_PISADO,
                        id_usuario=uid,
                        ajuste_sistema=ajuste_sys,
                        ajuste_anterior=ajuste_manual,
                        ajuste_nuevo=ajuste_sys,
                    )
                    ajuste_manual = None
                    overrides_pisados += 1

                saldos_dep = _fetch_saldos_deposito(cursor, id_art, [id_dep])
                saldo_actual = saldos_dep.get(id_dep)

                ajuste_eff = ajuste_efectivo(ajuste_sys, ajuste_manual)
                disp_ajust = calcular_disponible_ajustado(saldo_snap, ajuste_eff)
                diff_real = calcular_diferencia_real(linea.get("cantidad_contada"), disp_ajust)

                if pisar_overrides:
                    cursor.execute(
                        "UPDATE inv_fisico_linea SET "
                        "ajuste_sistema = %s, saldo_actual_ref = %s, diferencia_real = %s, "
                        "ajuste_calculado_at = NOW(), "
                        "ajuste_manual = NULL, ajuste_manual_usuario = NULL, ajuste_manual_fecha = NULL "
                        "WHERE id_linea = %s",
                        [ajuste_sys, saldo_actual, diff_real, id_linea],
                    )
                else:
                    cursor.execute(
                        "UPDATE inv_fisico_linea SET "
                        "ajuste_sistema = %s, saldo_actual_ref = %s, diferencia_real = %s, "
                        "ajuste_calculado_at = NOW() "
                        "WHERE id_linea = %s",
                        [ajuste_sys, saldo_actual, diff_real, id_linea],
                    )
                lineas_actualizadas += 1

        return True, {
            "lineas_actualizadas": lineas_actualizadas,
            "overrides_pisados": overrides_pisados,
        }
    except Exception as exc:
        logger.exception("recalcular_ajuste_post_snapshot %s: %s", id_campana, exc)
        return False, {"error": "No se pudo recalcular el ajuste post-snapshot."}


def guardar_override_ajuste(
    base_empresa: str,
    id_campana: int,
    id_linea: int,
    valor: Any,
    id_usuario: int,
) -> Tuple[bool, Dict[str, Any]]:
    nuevo = to_decimal_or_none(valor)
    if nuevo is None:
        return False, {"error": "Valor de ajuste inválido."}
    lid = to_int_or_none(id_linea)
    uid = to_int_or_none(id_usuario)
    if lid is None or uid is None:
        return False, {"error": "Datos inválidos."}

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT id_linea, id_campana, id_articulo, id_deposito, saldo_snapshot, "
                "cantidad_contada, ajuste_sistema, ajuste_manual "
                "FROM inv_fisico_linea WHERE id_linea = %s AND id_campana = %s",
                [lid, id_campana],
            )
            linea = cursor.fetchone()
            if not linea:
                return False, {"error": "Línea no encontrada en la campaña."}

            anterior = to_decimal_or_none(linea.get("ajuste_manual"))
            ajuste_sys = to_decimal_or_none(linea.get("ajuste_sistema")) or Decimal("0")
            saldo_snap = to_decimal_or_none(linea.get("saldo_snapshot")) or Decimal("0")
            disp_ajust = calcular_disponible_ajustado(saldo_snap, nuevo)
            diff_real = calcular_diferencia_real(linea.get("cantidad_contada"), disp_ajust)

            cursor.execute(
                "UPDATE inv_fisico_linea SET ajuste_manual = %s, "
                "ajuste_manual_usuario = %s, ajuste_manual_fecha = NOW(), "
                "diferencia_real = %s WHERE id_linea = %s",
                [nuevo, uid, diff_real, lid],
            )
            _insert_auditoria_ajuste(
                cursor,
                id_campana=id_campana,
                id_linea=lid,
                id_articulo=to_int_or_none(linea.get("id_articulo")) or 0,
                id_deposito=to_int_or_none(linea.get("id_deposito")) or 0,
                accion=ACCION_AUDIT_OVERRIDE_GUARDADO,
                id_usuario=uid,
                ajuste_sistema=ajuste_sys,
                ajuste_anterior=anterior,
                ajuste_nuevo=nuevo,
                diferencia_real=diff_real,
            )
        return True, {
            "id_linea": lid,
            "ajuste_manual": nuevo,
            "diferencia_real": diff_real,
        }
    except Exception as exc:
        logger.warning("guardar_override_ajuste: %s", exc)
        return False, {"error": "No se pudo guardar el override."}


def quitar_override_ajuste(
    base_empresa: str,
    id_campana: int,
    id_linea: int,
    id_usuario: int,
) -> Tuple[bool, Dict[str, Any]]:
    lid = to_int_or_none(id_linea)
    uid = to_int_or_none(id_usuario)
    if lid is None or uid is None:
        return False, {"error": "Datos inválidos."}

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT id_linea, id_campana, id_articulo, id_deposito, saldo_snapshot, "
                "cantidad_contada, ajuste_sistema, ajuste_manual "
                "FROM inv_fisico_linea WHERE id_linea = %s AND id_campana = %s",
                [lid, id_campana],
            )
            linea = cursor.fetchone()
            if not linea:
                return False, {"error": "Línea no encontrada en la campaña."}

            anterior = to_decimal_or_none(linea.get("ajuste_manual"))
            if anterior is None:
                return True, {"id_linea": lid, "sin_override": True}

            ajuste_sys = to_decimal_or_none(linea.get("ajuste_sistema")) or Decimal("0")
            saldo_snap = to_decimal_or_none(linea.get("saldo_snapshot")) or Decimal("0")
            disp_ajust = calcular_disponible_ajustado(saldo_snap, ajuste_sys)
            diff_real = calcular_diferencia_real(linea.get("cantidad_contada"), disp_ajust)

            cursor.execute(
                "UPDATE inv_fisico_linea SET ajuste_manual = NULL, "
                "ajuste_manual_usuario = NULL, ajuste_manual_fecha = NULL, "
                "diferencia_real = %s WHERE id_linea = %s",
                [diff_real, lid],
            )
            _insert_auditoria_ajuste(
                cursor,
                id_campana=id_campana,
                id_linea=lid,
                id_articulo=to_int_or_none(linea.get("id_articulo")) or 0,
                id_deposito=to_int_or_none(linea.get("id_deposito")) or 0,
                accion=ACCION_AUDIT_OVERRIDE_QUITADO,
                id_usuario=uid,
                ajuste_sistema=ajuste_sys,
                ajuste_anterior=anterior,
                ajuste_nuevo=ajuste_sys,
                diferencia_real=diff_real,
            )
        return True, {"id_linea": lid, "diferencia_real": diff_real}
    except Exception as exc:
        logger.warning("quitar_override_ajuste: %s", exc)
        return False, {"error": "No se pudo quitar el override."}


def motivo_mstock_por_diferencia(diferencia: Any) -> Optional[int]:
    diff = to_decimal_or_none(diferencia) or Decimal("0")
    if diff == 0:
        return None
    if diff < 0:
        return MOTIVO_FALTANTE
    return MOTIVO_SOBRANTE


def cantidad_mstock_por_diferencia(diferencia: Any) -> Decimal:
    return abs(to_decimal_or_none(diferencia) or Decimal("0"))


def construir_renglon_mstock(linea: Dict[str, Any]) -> Dict[str, Any]:
    """Renglón para alta_movimiento según signo de diferencia_real (Faltante=salida, Sobrante=entrada)."""
    diferencia = to_decimal_or_none(linea.get("diferencia_real"))
    if diferencia is None:
        diferencia = to_decimal_or_none(linea.get("diferencia")) or Decimal("0")
    motivo = motivo_mstock_por_diferencia(diferencia)
    cantidad = cantidad_mstock_por_diferencia(diferencia)
    id_art = to_int_or_none(linea.get("id_articulo"))
    id_dep = to_int_or_none(linea.get("id_deposito"))
    codigo = str_or_default(linea.get("codigo"), "-")
    nombre = str_or_default(linea.get("nombre"), "-")
    if motivo == MOTIVO_FALTANTE:
        return {
            "IDArt": id_art,
            "CodigoArticulo": codigo,
            "Descripcion": nombre,
            "Cantidad": cantidad,
            "entrada": Decimal("0"),
            "salida": cantidad,
            "ES": "S",
            "CodDeposito": id_dep,
        }
    return {
        "IDArt": id_art,
        "CodigoArticulo": codigo,
        "Descripcion": nombre,
        "Cantidad": cantidad,
        "entrada": cantidad,
        "salida": Decimal("0"),
        "ES": "E",
        "CodDeposito": id_dep,
    }


def evaluar_bloqueo_autorizacion(
    estado_campana: str,
    pendientes_cliente: int,
    conflictos_sync: int,
) -> Tuple[bool, str, str]:
    """Devuelve (bloqueado, codigo, mensaje_es)."""
    estado = str_or_default(estado_campana, "")
    if estado != ESTADO_EN_REVISION:
        return True, "estado_invalido", "La campaña debe estar en revisión para autorizar."
    if pendientes_cliente > 0:
        return (
            True,
            "sync_pendiente",
            f"Hay {pendientes_cliente} conteo(s) sin sincronizar en dispositivos.",
        )
    if conflictos_sync > 0:
        return (
            True,
            "sync_pendiente",
            f"Hay {conflictos_sync} conflicto(s) de sync sin resolver.",
        )
    return False, "", ""


def contar_conflictos_sync(base_empresa: str, id_campana: int) -> int:
    cid = to_int_or_none(id_campana)
    if cid is None:
        return 0
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS total FROM inv_fisico_evento "
                "WHERE id_campana = %s AND resultado = %s",
                [cid, RESULTADO_CONFLICTO],
            )
            row = cursor.fetchone() or {}
            return to_int_or_none(row.get("total")) or 0
    except Exception as exc:
        logger.warning("contar_conflictos_sync %s/%s: %s", base_empresa, id_campana, exc)
        return 0


def parse_marcas_incluidos(raw_values: Optional[Sequence[Any]] = None) -> List[int]:
    """Normaliza IDs de marca desde query string (`marcas_incluidos`)."""
    marcas: List[int] = []
    for raw in raw_values or ():
        mid = to_int_or_none(raw)
        if mid is not None:
            marcas.append(mid)
    return marcas


def build_analizador_query_string(
    *,
    filtro: Optional[str] = None,
    marcas_incluidos: Optional[Sequence[int]] = None,
) -> str:
    """Query string para enlaces del analizador (preserva filtro y marcas)."""
    from urllib.parse import urlencode

    pairs: List[Tuple[str, str]] = []
    filtro_norm = str_or_default(filtro, "").strip()
    if filtro_norm:
        pairs.append(("filtro", filtro_norm))
    for marca_id in marcas_incluidos or ():
        mid = to_int_or_none(marca_id)
        if mid is not None:
            pairs.append(("marcas_incluidos", str(mid)))
    qs = urlencode(pairs)
    return f"?{qs}" if qs else "?"


def _query_lineas_analizador(cursor, id_campana: int) -> List[Dict[str, Any]]:
    tbl_art = _nombre_tabla(cursor, "articulo")
    if not tbl_art:
        return []
    ta = tbl_art.replace("`", "``")
    tbl_marca = _nombre_tabla(cursor, "marca")
    join_marca = ""
    select_marca = "NULL AS id_marca, '' AS nombre_marca"
    if tbl_marca:
        tm = tbl_marca.replace("`", "``")
        join_marca = f"LEFT JOIN `{tm}` m ON m.CodMarca = a.CodigoMarca "
        select_marca = (
            "a.CodigoMarca AS id_marca, COALESCE(m.NombreMarca, '') AS nombre_marca"
        )
    filtro_art, params_art = _sql_filtro_tipo_art_fab("a")
    cursor.execute(
        f"SELECT l.id_linea, l.id_articulo, l.id_deposito, l.saldo_snapshot, "
        f"l.cantidad_contada, l.diferencia, l.diferencia_real, "
        f"l.ajuste_sistema, l.ajuste_manual, l.saldo_actual_ref, "
        f"l.id_contador, l.estado_linea, "
        f"COALESCE(a.id_manual, '-') AS codigo, "
        f"COALESCE(a.NombreArticulo, '') AS nombre, "
        f"{select_marca} "
        f"FROM inv_fisico_linea l "
        f"INNER JOIN `{ta}` a ON a.IDArt = l.id_articulo "
        f"{join_marca}"
        f"WHERE l.id_campana = %s AND {filtro_art} "
        f"ORDER BY ABS(COALESCE(l.diferencia_real, 0)) DESC, a.NombreArticulo",
        [id_campana, *params_art],
    )
    lineas: List[Dict[str, Any]] = []
    for row in cursor.fetchall():
        saldo_snap = to_decimal_or_none(row.get("saldo_snapshot")) or Decimal("0")
        ajuste_sys = to_decimal_or_none(row.get("ajuste_sistema"))
        ajuste_man = to_decimal_or_none(row.get("ajuste_manual"))
        ajuste_eff = ajuste_efectivo(ajuste_sys, ajuste_man)
        disp_ajust = calcular_disponible_ajustado(saldo_snap, ajuste_eff)
        diff_real = to_decimal_or_none(row.get("diferencia_real"))
        if diff_real is None:
            diff_real = calcular_diferencia_real(row.get("cantidad_contada"), disp_ajust)
        lineas.append(
            enriquecer_linea_analizador(
                {
                    "id_linea": to_int_or_none(row.get("id_linea")),
                    "id_articulo": to_int_or_none(row.get("id_articulo")),
                    "id_deposito": to_int_or_none(row.get("id_deposito")),
                    "saldo_snapshot": saldo_snap,
                    "cantidad_contada": to_decimal_or_none(row.get("cantidad_contada")),
                    "diferencia": to_decimal_or_none(row.get("diferencia")),
                    "diferencia_real": diff_real,
                    "ajuste_sistema": ajuste_sys,
                    "ajuste_manual": ajuste_man,
                    "saldo_actual_ref": to_decimal_or_none(row.get("saldo_actual_ref")),
                    "id_contador": to_int_or_none(row.get("id_contador")),
                    "estado_linea": str_or_default(row.get("estado_linea"), "Pendiente"),
                    "codigo": str_or_default(row.get("codigo"), "-"),
                    "nombre": str_or_default(row.get("nombre"), "-"),
                    "id_marca": to_int_or_none(row.get("id_marca")),
                    "nombre_marca": str_or_default(row.get("nombre_marca"), ""),
                }
            )
        )
    return lineas


def listar_lineas_analizador(
    base_empresa: str,
    id_campana: int,
    filtro: Optional[str] = None,
    marcas_incluidos: Optional[Sequence[int]] = None,
) -> List[Dict[str, Any]]:
    cid = to_int_or_none(id_campana)
    if cid is None:
        return []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            lineas = _query_lineas_analizador(cursor, cid)
    except Exception as exc:
        logger.warning("listar_lineas_analizador %s/%s: %s", base_empresa, id_campana, exc)
        return []

    candidatos = listar_contadores_candidatos(base_empresa)
    etiquetas_contador = {
        c["id_usuario"]: c["etiqueta"]
        for c in etiquetar_contadores(
            list({l.get("id_contador") for l in lineas if l.get("id_contador")}),
            candidatos,
        )
    }
    for linea in lineas:
        enriquecer_linea_analizador(linea)
        uid = linea.get("id_contador")
        linea["contador_etiqueta"] = etiquetas_contador.get(uid, "") if uid else ""

    marcas_set: Optional[Set[int]] = None
    if marcas_incluidos:
        marcas_set = {m for m in (to_int_or_none(x) for x in marcas_incluidos) if m is not None}
        if marcas_set:
            lineas = [l for l in lineas if l.get("id_marca") in marcas_set]

    filtro_norm = str_or_default(filtro, "").strip().lower()
    if filtro_norm == "faltante":
        return [l for l in lineas if (l.get("diferencia_real") or Decimal("0")) < 0]
    if filtro_norm == "sobrante":
        return [l for l in lineas if (l.get("diferencia_real") or Decimal("0")) > 0]
    if filtro_norm == "con_diferencia":
        return [l for l in lineas if (l.get("diferencia_real") or Decimal("0")) != 0]
    if filtro_norm in ("no_contados", "no_contado", "sin_contar"):
        return [l for l in lineas if to_decimal_or_none(l.get("cantidad_contada")) is None]
    return lineas


def contar_desglose_no_contados(
    base_empresa: str,
    id_campana: int,
) -> Dict[str, int]:
    """Conteos de líneas sin contar en toda la campaña (sin filtro de marcas)."""
    cid = to_int_or_none(id_campana)
    vacio = {
        "lineas_no_contadas": 0,
        "lineas_con_snap_ne0": 0,
        "lineas_con_mov_post": 0,
    }
    if cid is None:
        return vacio

    total = 0
    snap_ne0 = 0
    mov_post = 0
    netos = calcular_ajuste_post_snapshot(base_empresa, cid)
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT id_articulo, id_deposito, saldo_snapshot "
                "FROM inv_fisico_linea "
                "WHERE id_campana = %s AND cantidad_contada IS NULL",
                [cid],
            )
            for row in cursor.fetchall():
                total += 1
                saldo = to_decimal_or_none(row.get("saldo_snapshot")) or Decimal("0")
                if saldo != Decimal("0"):
                    snap_ne0 += 1
                id_art = to_int_or_none(row.get("id_articulo"))
                id_dep = to_int_or_none(row.get("id_deposito"))
                if id_art is not None and id_dep is not None:
                    neto = netos.get((id_art, id_dep), Decimal("0"))
                    if neto != Decimal("0"):
                        mov_post += 1
    except Exception as exc:
        logger.warning("contar_desglose_no_contados %s/%s: %s", base_empresa, id_campana, exc)
        return vacio

    return {
        "lineas_no_contadas": total,
        "lineas_con_snap_ne0": snap_ne0,
        "lineas_con_mov_post": mov_post,
    }


def contar_lineas_no_contadas(base_empresa: str, id_campana: int) -> int:
    return contar_desglose_no_contados(base_empresa, id_campana)["lineas_no_contadas"]


def marcar_no_contados_como_cero(
    base_empresa: str,
    id_campana: int,
    id_usuario: int,
) -> Tuple[bool, Dict[str, Any]]:
    """Marca masivamente Contado=0 las líneas sin contar (supervisor)."""
    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        return False, {"error": "Campaña no encontrada."}

    if campana["estado"] not in (ESTADO_EN_CONTEO, ESTADO_EN_REVISION):
        return False, {
            "error": (
                f"No se puede marcar contado cero en el estado {campana['estado']}."
            ),
        }

    uid = to_int_or_none(id_usuario)
    cid = to_int_or_none(id_campana)
    if uid is None:
        return False, {"error": "Usuario inválido."}
    if cid is None:
        return False, {"error": "Campaña inválida."}

    desglose = contar_desglose_no_contados(base_empresa, cid)
    lineas_marcadas = 0

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT id_linea, id_articulo, id_deposito "
                "FROM inv_fisico_linea "
                "WHERE id_campana = %s AND cantidad_contada IS NULL",
                [cid],
            )
            lineas = [dict(r) for r in cursor.fetchall()]

            for linea in lineas:
                id_linea = to_int_or_none(linea.get("id_linea"))
                id_art = to_int_or_none(linea.get("id_articulo"))
                id_dep = to_int_or_none(linea.get("id_deposito"))
                if id_linea is None or id_art is None or id_dep is None:
                    continue

                cursor.execute(
                    "SELECT cantidad_contada FROM inv_fisico_linea WHERE id_linea = %s",
                    [id_linea],
                )
                check = cursor.fetchone()
                if check and to_decimal_or_none(check.get("cantidad_contada")) is not None:
                    continue

                filas = _proyectar_linea(
                    cursor,
                    cid,
                    id_art,
                    id_dep,
                    uid,
                    Decimal("0"),
                    solo_si_sin_contar=True,
                )
                if filas == 0:
                    continue

                client_event_id = str(uuid.uuid4())
                client_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                cursor.execute(
                    "INSERT INTO inv_fisico_evento "
                    "(client_event_id, id_campana, id_articulo, id_deposito, id_contador, "
                    "cantidad, client_ts, resultado, motivo) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    [
                        client_event_id,
                        cid,
                        id_art,
                        id_dep,
                        uid,
                        Decimal("0"),
                        client_ts,
                        RESULTADO_ACEPTADO,
                        MOTIVO_CONTADO_CERO_SUPERVISOR,
                    ],
                )
                _insert_auditoria_ajuste(
                    cursor,
                    id_campana=cid,
                    id_linea=id_linea,
                    id_articulo=id_art,
                    id_deposito=id_dep,
                    accion=ACCION_AUDIT_CONTADO_CERO_MASIVO,
                    id_usuario=uid,
                )
                lineas_marcadas += 1
    except Exception as exc:
        logger.exception("marcar_no_contados_como_cero %s/%s: %s", base_empresa, id_campana, exc)
        return False, {"error": "No se pudieron marcar las líneas sin contar."}

    advertencia = None
    ok_recalc, recalc_info = recalcular_ajuste_post_snapshot(
        base_empresa,
        cid,
        id_usuario=uid,
        pisar_overrides=False,
    )
    if not ok_recalc:
        advertencia = recalc_info.get("error") or (
            "No se pudo recalcular el ajuste post-snapshot."
        )

    return True, {
        "lineas_marcadas": lineas_marcadas,
        "lineas_con_snap_ne0": desglose["lineas_con_snap_ne0"],
        "lineas_con_mov_post": desglose["lineas_con_mov_post"],
        "advertencia": advertencia,
        "mensaje": f"{lineas_marcadas} líneas marcadas con Contado = 0.",
    }


def obtener_linea_analizador(
    base_empresa: str,
    id_campana: int,
    id_linea: int,
) -> Optional[Dict[str, Any]]:
    for linea in listar_lineas_analizador(base_empresa, id_campana):
        if linea.get("id_linea") == id_linea:
            return linea
    return None


def listar_eventos_linea(
    base_empresa: str,
    id_campana: int,
    id_articulo: int,
    id_deposito: int,
) -> List[Dict[str, Any]]:
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "SELECT id_evento, id_contador, cantidad, client_ts, server_ts, resultado, motivo "
                "FROM inv_fisico_evento "
                "WHERE id_campana = %s AND id_articulo = %s AND id_deposito = %s "
                "ORDER BY server_ts DESC",
                [id_campana, id_articulo, id_deposito],
            )
            return [dict(r) for r in cursor.fetchall()]
    except Exception as exc:
        logger.warning("listar_eventos_linea: %s", exc)
        return []


def obtener_resumen_monitor(base_empresa: str, id_campana: int) -> Dict[str, Any]:
    progreso = obtener_progreso_campana(base_empresa, id_campana)
    conflictos = contar_conflictos_sync(base_empresa, id_campana)
    campana = obtener_campana(base_empresa, id_campana) or {}
    bloqueado, codigo, mensaje = evaluar_bloqueo_autorizacion(
        campana.get("estado", ""),
        pendientes_cliente=0,
        conflictos_sync=conflictos,
    )
    lineas_diff = listar_lineas_analizador(base_empresa, id_campana, filtro="con_diferencia")
    return {
        **progreso,
        "conflictos_sync": conflictos,
        "lineas_con_diferencia": len(lineas_diff),
        "bloqueo_autorizar": bloqueado and codigo == "sync_pendiente",
        "bloqueo_estado": bloqueado and codigo == "estado_invalido",
        "codigo_bloqueo": codigo,
        "mensaje_bloqueo": mensaje,
    }


def anular_campana(base_empresa: str, id_campana: int) -> Tuple[bool, Dict[str, Any]]:
    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        return False, {"error": "Campaña no encontrada."}
    if campana["estado"] == ESTADO_APLICADO:
        return False, {"error": "No se puede anular una campaña Aplicada. Compensación manual."}
    if campana["estado"] not in (ESTADO_BORRADOR, ESTADO_EN_CONTEO, ESTADO_EN_REVISION):
        return False, {
            "error": f"No se puede anular desde el estado {campana['estado']}.",
        }
    if not transicion_estado_permitida(campana["estado"], ESTADO_ANULADO):
        return False, {"error": "Transición a Anulado no permitida."}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(
                "UPDATE inv_fisico_campana SET estado = %s WHERE id_campana = %s",
                [ESTADO_ANULADO, id_campana],
            )
        return True, {"id_campana": id_campana, "estado": ESTADO_ANULADO}
    except Exception as exc:
        logger.warning("anular_campana %s: %s", id_campana, exc)
        return False, {"error": "No se pudo anular la campaña."}


def _agrupar_lineas_mstock(
    lineas: Sequence[Dict[str, Any]],
) -> List[Tuple[int, int, List[Dict[str, Any]]]]:
    """Agrupa renglones por (id_deposito, motivo_movimiento) para cabecera única."""
    grupos: Dict[Tuple[int, int], List[Dict[str, Any]]] = {}
    for linea in lineas:
        diff = to_decimal_or_none(linea.get("diferencia_real"))
        if diff is None:
            diff = to_decimal_or_none(linea.get("diferencia"))
        motivo = motivo_mstock_por_diferencia(diff)
        if motivo is None:
            continue
        id_dep = to_int_or_none(linea.get("id_deposito")) or 0
        clave = (id_dep, motivo)
        grupos.setdefault(clave, []).append(construir_renglon_mstock(linea))
    return [(dep, motivo, rengs) for (dep, motivo), rengs in sorted(grupos.items())]


def autorizar_y_aplicar_campana(
    base_empresa: str,
    id_campana: int,
    *,
    id_usuario: int,
    id_puesto: Optional[int],
    pendientes_cliente: int = 0,
    id_punto_venta: int = 1,
) -> Tuple[bool, Dict[str, Any]]:
    from core.services.administranet_stock import alta_movimiento

    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        return False, {"error": "Campaña no encontrada."}

    conflictos = contar_conflictos_sync(base_empresa, id_campana)
    bloqueado, codigo, mensaje = evaluar_bloqueo_autorizacion(
        campana["estado"],
        to_int_or_none(pendientes_cliente) or 0,
        conflictos,
    )
    if bloqueado:
        payload: Dict[str, Any] = {
            "bloqueado": True,
            "codigo": codigo,
            "error": mensaje,
        }
        if codigo == "sync_pendiente":
            payload["pendientes_cliente"] = to_int_or_none(pendientes_cliente) or 0
            payload["conflictos_sync"] = conflictos
        return False, payload

    ok_recalc, recalc_info = recalcular_ajuste_post_snapshot(
        base_empresa,
        id_campana,
        id_usuario=id_usuario,
        pisar_overrides=False,
    )
    if not ok_recalc:
        return False, {"error": recalc_info.get("error", "No se pudo recalcular ajustes.")}

    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            lineas_raw = [
                enriquecer_linea_analizador(dict(l))
                for l in _query_lineas_analizador(cursor, id_campana)
            ]
    except Exception as exc:
        logger.exception("autorizar lineas %s: %s", id_campana, exc)
        return False, {"error": "No se pudieron leer las líneas de la campaña."}

    lineas_ajustar = [
        l
        for l in lineas_raw
        if l.get("cantidad_contada") is not None
        and (to_decimal_or_none(l.get("diferencia_real")) or Decimal("0")) != 0
    ]
    grupos = _agrupar_lineas_mstock(lineas_ajustar)

    ok_trans, _ = transicionar_campana(base_empresa, id_campana, ESTADO_AUTORIZADO)
    if not ok_trans:
        return False, {"error": "No se pudo autorizar la campaña."}

    fecha_mov = str_or_default(campana.get("fecha"), "")[:10] or datetime.now().strftime("%Y-%m-%d")
    movimientos_ok = 0
    ultimo_codigo: Optional[int] = None
    errores: List[str] = []

    for id_dep, motivo, renglones in grupos:
        cabecera = {
            "motivo_movimiento": motivo,
            "fecha": fecha_mov,
            "deposito_origen": id_dep,
            "deposito_destino": id_dep,
            "detalle": f"Inventario físico campaña #{id_campana}",
            "id_ref_movstock": 1,
            "id_pv": id_punto_venta,
        }
        ok, codigo_mov, _nro, mensaje_err, _schema = alta_movimiento(
            base_empresa=base_empresa,
            id_usuario=id_usuario,
            id_puesto=id_puesto,
            cabecera=cabecera,
            renglones=renglones,
        )
        if ok:
            movimientos_ok += 1
            if codigo_mov is not None:
                ultimo_codigo = int(codigo_mov)
        else:
            errores.append(mensaje_err or "Error MSTOCK")

    if errores and movimientos_ok == 0:
        transicionar_campana(base_empresa, id_campana, ESTADO_EN_REVISION)
        return False, {"error": "; ".join(errores)}

    ok_aplicado, _ = transicionar_campana(base_empresa, id_campana, ESTADO_APLICADO)
    if not ok_aplicado:
        return False, {"error": "MSTOCK parcial: no se pudo marcar campaña como Aplicada."}

    if ultimo_codigo is not None:
        try:
            with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
                cursor.execute(
                    "UPDATE inv_fisico_campana SET id_movimiento_mstock = %s WHERE id_campana = %s",
                    [ultimo_codigo, id_campana],
                )
                for linea in lineas_ajustar:
                    _insert_auditoria_ajuste(
                        cursor,
                        id_campana=id_campana,
                        id_linea=to_int_or_none(linea.get("id_linea")) or 0,
                        id_articulo=to_int_or_none(linea.get("id_articulo")) or 0,
                        id_deposito=to_int_or_none(linea.get("id_deposito")) or 0,
                        accion=ACCION_AUDIT_AUTORIZACION,
                        id_usuario=id_usuario,
                        ajuste_sistema=to_decimal_or_none(linea.get("ajuste_sistema")),
                        diferencia_real=to_decimal_or_none(linea.get("diferencia_real")),
                        codigo_movimiento=ultimo_codigo,
                    )
        except Exception as exc:
            logger.warning("guardar id_movimiento_mstock / auditoría: %s", exc)

    return True, {
        "id_campana": id_campana,
        "estado": ESTADO_APLICADO,
        "movimientos_mstock": movimientos_ok,
        "lineas_ajustadas": len(lineas_ajustar),
        "codigo_movimiento": ultimo_codigo,
    }

