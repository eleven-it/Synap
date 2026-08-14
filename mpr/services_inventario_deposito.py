"""Consulta inventario por depósito×artículo (hub MPR inventario_deposito)."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import (
    str_codigo_manual_articulo,
    str_or_default,
    to_date_or_none,
    to_int_or_none,
)

from mpr.inventario_docenas import medidas_inventario_excel
from mpr.services import _nombre_tabla, bulk_cantidad_promedio_bulto
from stock.services.stock_a_fecha import saldos_stock_a_fecha

logger = logging.getLogger(__name__)

TIPO_MPR_2DA = "2daSeleccion"
_BUSQUEDA_MIN_LEN = 2


@dataclass
class InventarioDepositoFiltros:
    depositos: List[int] = field(default_factory=list)
    marcas_incluidos: List[int] = field(default_factory=list)
    busqueda: Optional[str] = None
    id_articulo: Optional[int] = None
    incluir_2da: bool = False
    fecha_corte: date = field(default_factory=date.today)


def parse_filtros_inventario_deposito(
    get_params: Any,
    *,
    marcas_getlist: Optional[Sequence[str]] = None,
) -> InventarioDepositoFiltros:
    """Normaliza query string del reporte inventario_deposito."""
    depositos: List[int] = []
    raw_deps = []
    if hasattr(get_params, "getlist"):
        raw_deps = list(get_params.getlist("depositos") or [])
    if not raw_deps:
        single = get_params.get("depositos") or get_params.get("id_deposito")
        if single not in (None, "", []):
            raw_deps = [single] if not isinstance(single, list) else list(single)
    for d in raw_deps:
        did = to_int_or_none(d)
        if did is not None:
            depositos.append(did)

    marcas: List[int] = []
    raw_marcas = list(marcas_getlist or [])
    if not raw_marcas and hasattr(get_params, "getlist"):
        raw_marcas = list(get_params.getlist("marcas_incluidos") or [])
    if not raw_marcas:
        single_m = get_params.get("marcas_incluidos") or get_params.get("marca")
        if single_m not in (None, "", []):
            raw_marcas = [single_m] if not isinstance(single_m, list) else list(single_m)
    for m in raw_marcas:
        mid = to_int_or_none(m)
        if mid is not None:
            marcas.append(mid)

    q = (get_params.get("q") or "").strip() or None
    if q and len(q) < _BUSQUEDA_MIN_LEN:
        q = None

    incluir_2da = str(get_params.get("incluir_2da") or "0").strip().lower() in (
        "1",
        "true",
        "yes",
        "si",
        "sí",
    )

    raw_fecha = get_params.get("fecha_corte")
    fecha_corte = _to_date_obj(raw_fecha) or date.today()

    return InventarioDepositoFiltros(
        depositos=depositos,
        marcas_incluidos=marcas,
        busqueda=q if not get_params.get("id_articulo") else None,
        id_articulo=to_int_or_none(get_params.get("id_articulo")),
        incluir_2da=incluir_2da,
        fecha_corte=fecha_corte,
    )


def _to_date_obj(value: Any) -> Optional[date]:
    if value is None or (isinstance(value, str) and not value.strip()):
        return None
    parsed = to_date_or_none(value)
    if not parsed:
        return None
    try:
        from datetime import datetime

        return datetime.strptime(str(parsed)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _sql_filtro_tipo_mpr(*, incluir_2da: bool) -> str:
    if incluir_2da:
        return ""
    return f" AND TRIM(COALESCE(d.tipo_mpr, '')) != '{TIPO_MPR_2DA}'"


def _clausula_busqueda(
    busqueda: str,
    *,
    alias: str = "a",
    alias_ce: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    q = (busqueda or "").strip()
    if not q:
        return "", []
    term = f"%{q}%"
    partes = [
        f"IFNULL({alias}.id_manual, '') LIKE %s",
        f"IFNULL({alias}.CodArtProv, '') LIKE %s",
        f"IFNULL({alias}.NombreArticulo, '') LIKE %s",
        f"IFNULL({alias}.NroCodBarra, '') LIKE %s",
        f"IFNULL({alias}.NroCodBarraF, '') LIKE %s",
    ]
    params: List[Any] = [term, term, term, term, term]
    if alias_ce:
        partes.append(f"IFNULL({alias_ce}.valor1, '') LIKE %s")
        partes.append(f"IFNULL({alias_ce}.valor2, '') LIKE %s")
        params.extend([term, term])
    return "(" + " OR ".join(partes) + ")", params


def _build_where_articulo(
    *,
    busqueda: Optional[str],
    marcas_incluidos: List[int],
    id_articulo: Optional[int],
    alias: str = "a",
    alias_ce: Optional[str] = None,
) -> Tuple[str, List[Any]]:
    """Filtros artículo; MUST NOT excluir tipo_art_fab=Tercero (S4)."""
    parts: List[str] = []
    params: List[Any] = []

    if id_articulo is not None:
        parts.append(f"{alias}.IDArt = %s")
        params.append(id_articulo)
        return " AND ".join(parts), params

    if marcas_incluidos:
        ph = ",".join(["%s"] * len(marcas_incluidos))
        parts.append(f"{alias}.CodigoMarca IN ({ph})")
        params.extend(marcas_incluidos)

    if busqueda:
        clausula, params_q = _clausula_busqueda(busqueda, alias=alias, alias_ce=alias_ce)
        if clausula:
            parts.append(clausula)
            params.extend(params_q)

    return (" AND ".join(parts) if parts else "1=1"), params


def calcular_total_docenas(filas: List[Dict[str, Any]]) -> float:
    """Total cabecera = SUM(docenas) del scope visible."""
    return round(sum(float(f.get("docenas") or 0) for f in filas), 2)


def enriquecer_medidas_inventario(
    filas: List[Dict[str, Any]],
    base_empresa: str,
) -> List[Dict[str, Any]]:
    """Añade medidas Stock UM + Docenas por fila."""
    if not filas:
        return []
    ids = [int(f["id_articulo"]) for f in filas if f.get("id_articulo") is not None]
    bulto_map = bulk_cantidad_promedio_bulto(base_empresa, ids) if ids else {}
    out: List[Dict[str, Any]] = []
    for fila in filas:
        aid = fila.get("id_articulo")
        bulto = bulto_map.get(int(aid)) if aid is not None else None
        medidas = medidas_inventario_excel(
            fila.get("saldo"),
            fila.get("tipo_mpr") or "",
            bulto,
        )
        out.append({**fila, **medidas})
    return out


def agrupar_jerarquia_deposito_marca(
    filas: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], float]:
    """
    Jerarquía Depósito → Marca → Artículo.
    Retorna (depositos_jerarquia, total_docenas).
    """
    depositos_map: Dict[int, Dict[str, Any]] = {}
    for fila in filas:
        did = fila.get("id_deposito")
        if did is None:
            continue
        did_int = int(did)
        if did_int not in depositos_map:
            depositos_map[did_int] = {
                "id_deposito": did_int,
                "nombre_deposito": str_or_default(fila.get("nombre_deposito"), "-"),
                "tipo_mpr": str_or_default(fila.get("tipo_mpr"), ""),
                "marcas_map": {},
                "total_docenas": 0.0,
            }
        dep = depositos_map[did_int]
        marca = str_or_default(fila.get("marca_nombre"), "Sin marca")
        marcas_map = dep["marcas_map"]
        if marca not in marcas_map:
            marcas_map[marca] = {
                "marca_nombre": marca,
                "filas": [],
                "subtotal_docenas": 0.0,
            }
        doc = float(fila.get("docenas") or 0)
        marcas_map[marca]["filas"].append(fila)
        marcas_map[marca]["subtotal_docenas"] = round(
            marcas_map[marca]["subtotal_docenas"] + doc, 2
        )
        dep["total_docenas"] = round(dep["total_docenas"] + doc, 2)

    depositos_out: List[Dict[str, Any]] = []
    for did_int in sorted(depositos_map.keys(), key=lambda d: depositos_map[d]["nombre_deposito"]):
        dep = depositos_map[did_int]
        marcas_out = []
        for marca in sorted(dep["marcas_map"].keys()):
            m = dep["marcas_map"][marca]
            m["filas"].sort(
                key=lambda f: (
                    str(f.get("codigo_manual") or ""),
                    str(f.get("talle") or ""),
                )
            )
            marcas_out.append(m)
        depositos_out.append({
            "id_deposito": dep["id_deposito"],
            "nombre_deposito": dep["nombre_deposito"],
            "tipo_mpr": dep["tipo_mpr"],
            "total_docenas": dep["total_docenas"],
            "marcas": marcas_out,
        })

    total = calcular_total_docenas(filas)
    return depositos_out, total


def _usa_stock_deposito(fecha_corte: date) -> bool:
    """Corte=hoy lee stock_deposito; corte pasado reconstruye desde stock."""
    return fecha_corte >= date.today()


def _consultar_filas_historicas(
    base_empresa: str,
    filtros: InventarioDepositoFiltros,
) -> List[Dict[str, Any]]:
    """Proyección depósito×artículo desde saldos_stock_a_fecha + metadatos."""
    saldos = saldos_stock_a_fecha(
        base_empresa,
        filtros.fecha_corte,
        id_depositos=filtros.depositos or None,
    )
    if not saldos:
        return []

    pares = list(saldos.keys())
    condiciones: List[str] = []
    params_pares: List[Any] = []
    for id_art, id_dep in pares:
        condiciones.append("(a.IDArt = %s AND d.CodDeposito = %s)")
        params_pares.extend([id_art, id_dep])

    with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
        tbl_dep = _nombre_tabla(cursor, "deposito")
        tbl_art = _nombre_tabla(cursor, "articulo")
        if not tbl_dep or not tbl_art:
            return []

        tbl_ce = _nombre_tabla(cursor, "articulo_valor_ce")
        tbl_marca = _nombre_tabla(cursor, "marca")

        join_ce = ""
        if tbl_ce:
            tce = tbl_ce.replace("`", "``")
            join_ce = f" LEFT JOIN `{tce}` avce ON avce.id_articulo = a.IDArt"

        join_marca = ""
        select_marca = "'' AS marca_nombre"
        if tbl_marca:
            tm = tbl_marca.replace("`", "``")
            join_marca = f" LEFT JOIN `{tm}` m ON m.CodMarca = a.CodigoMarca"
            select_marca = "COALESCE(m.NombreMarca, '') AS marca_nombre"

        where_dep = (
            "COALESCE(d.anulado, 'No') = 'No' "
            "AND COALESCE(d.suma_stock, 'Si') = 'Si'"
        )
        where_dep += _sql_filtro_tipo_mpr(incluir_2da=filtros.incluir_2da)

        params: List[Any] = list(params_pares)
        if filtros.depositos:
            ph = ",".join(["%s"] * len(filtros.depositos))
            where_dep += f" AND d.CodDeposito IN ({ph})"
            params.extend(filtros.depositos)

        where_art, params_art = _build_where_articulo(
            busqueda=filtros.busqueda,
            marcas_incluidos=filtros.marcas_incluidos,
            id_articulo=filtros.id_articulo,
            alias_ce="avce" if tbl_ce else None,
        )

        tdep = tbl_dep.replace("`", "``")
        tart = tbl_art.replace("`", "``")

        sql = f"""
            SELECT a.IDArt AS id_articulo,
                   d.CodDeposito AS id_deposito,
                   COALESCE(a.id_manual, '') AS codigo_manual,
                   COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                   COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                   COALESCE(a.cantidad_promedio_bulto, 0) AS cantidad_promedio_bulto,
                   COALESCE(TRIM(a.tipo_art_fab), '') AS tipo_art_fab,
                   COALESCE(d.NombreDeposito, '') AS nombre_deposito,
                   COALESCE(d.tipo_mpr, '') AS tipo_mpr,
                   {select_marca},
                   COALESCE(avce.valor1, '') AS talle
            FROM `{tdep}` d
            INNER JOIN `{tart}` a ON 1=1
            {join_ce}
            {join_marca}
            WHERE ({' OR '.join(condiciones)})
              AND {where_dep}
              AND ({where_art})
            ORDER BY d.NombreDeposito, marca_nombre,
                     COALESCE(NULLIF(TRIM(a.id_manual), ''), a.CodigoArticuloT),
                     avce.valor1
        """
        cursor.execute(sql, tuple(params + params_art))
        rows = cursor.fetchall()

    filas_raw: List[Dict[str, Any]] = []
    for r in rows:
        id_art = to_int_or_none(r.get("id_articulo"))
        id_dep = to_int_or_none(r.get("id_deposito"))
        if id_art is None or id_dep is None:
            continue
        saldo = saldos.get((id_art, id_dep))
        if saldo is None or float(saldo) == 0:
            continue
        talle = str_or_default(r.get("talle"), "").strip()
        if talle == "-":
            talle = ""
        filas_raw.append({
            "id_articulo": id_art,
            "id_deposito": id_dep,
            "saldo": float(saldo),
            "codigo_manual": str_codigo_manual_articulo(r.get("codigo_manual")),
            "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
            "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
            "nombre_deposito": str_or_default(r.get("nombre_deposito"), "-"),
            "tipo_mpr": str_or_default(r.get("tipo_mpr"), ""),
            "marca_nombre": str_or_default(r.get("marca_nombre"), "Sin marca") or "Sin marca",
            "talle": talle,
            "cantidad_promedio_bulto": float(r.get("cantidad_promedio_bulto") or 0),
            "tipo_art_fab": str_or_default(r.get("tipo_art_fab"), ""),
        })
    return filas_raw


def consultar_inventario_deposito(
    base_empresa: str,
    filtros: InventarioDepositoFiltros,
) -> Dict[str, Any]:
    """Consulta grano (id_deposito, id_articulo) con medidas y jerarquía."""
    vacio: Dict[str, Any] = {
        "filas": [],
        "depositos_jerarquia": [],
        "total_docenas": 0.0,
        "kpis": {"total_docenas": 0.0, "depositos": 0, "filas": 0},
        "fecha_corte": filtros.fecha_corte,
        "usa_stock_deposito": True,
    }
    if not (base_empresa or "").strip():
        return vacio

    usa_hoy = _usa_stock_deposito(filtros.fecha_corte)
    vacio["usa_stock_deposito"] = usa_hoy

    try:
        if not usa_hoy:
            filas_raw = _consultar_filas_historicas(base_empresa, filtros)
            filas = enriquecer_medidas_inventario(filas_raw, base_empresa)
            depositos_jerarquia, total_docenas = agrupar_jerarquia_deposito_marca(filas)
            ids_dep = {f["id_deposito"] for f in filas if f.get("id_deposito") is not None}
            return {
                "filas": filas,
                "depositos_jerarquia": depositos_jerarquia,
                "total_docenas": total_docenas,
                "kpis": {
                    "total_docenas": total_docenas,
                    "depositos": len(ids_dep),
                    "filas": len(filas),
                },
                "fecha_corte": filtros.fecha_corte,
                "usa_stock_deposito": False,
            }

        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            tbl_sd = _nombre_tabla(cursor, "stock_deposito")
            tbl_dep = _nombre_tabla(cursor, "deposito")
            tbl_art = _nombre_tabla(cursor, "articulo")
            if not tbl_sd or not tbl_dep or not tbl_art:
                return vacio

            tbl_ce = _nombre_tabla(cursor, "articulo_valor_ce")
            tbl_marca = _nombre_tabla(cursor, "marca")

            join_ce = ""
            if tbl_ce:
                tce = tbl_ce.replace("`", "``")
                join_ce = f" LEFT JOIN `{tce}` avce ON avce.id_articulo = a.IDArt"

            join_marca = ""
            select_marca = "'' AS marca_nombre"
            if tbl_marca:
                tm = tbl_marca.replace("`", "``")
                join_marca = f" LEFT JOIN `{tm}` m ON m.CodMarca = a.CodigoMarca"
                select_marca = "COALESCE(m.NombreMarca, '') AS marca_nombre"

            where_dep = (
                "COALESCE(d.anulado, 'No') = 'No' "
                "AND COALESCE(d.suma_stock, 'Si') = 'Si'"
            )
            where_dep += _sql_filtro_tipo_mpr(incluir_2da=filtros.incluir_2da)

            params: List[Any] = []
            if filtros.depositos:
                ph = ",".join(["%s"] * len(filtros.depositos))
                where_dep += f" AND d.CodDeposito IN ({ph})"
                params.extend(filtros.depositos)

            where_art, params_art = _build_where_articulo(
                busqueda=filtros.busqueda,
                marcas_incluidos=filtros.marcas_incluidos,
                id_articulo=filtros.id_articulo,
                alias_ce="avce" if tbl_ce else None,
            )

            tsd = tbl_sd.replace("`", "``")
            tdep = tbl_dep.replace("`", "``")
            tart = tbl_art.replace("`", "``")

            sql = f"""
                SELECT sd.id_articulo, sd.id_deposito,
                       COALESCE(sd.saldo, 0) AS saldo,
                       COALESCE(a.id_manual, '') AS codigo_manual,
                       COALESCE(a.CodigoArticuloT, CAST(a.CodigoArticulo AS CHAR), '') AS codigo_articulo,
                       COALESCE(a.NombreArticulo, '') AS descripcion_articulo,
                       COALESCE(a.cantidad_promedio_bulto, 0) AS cantidad_promedio_bulto,
                       COALESCE(TRIM(a.tipo_art_fab), '') AS tipo_art_fab,
                       COALESCE(d.NombreDeposito, '') AS nombre_deposito,
                       COALESCE(d.tipo_mpr, '') AS tipo_mpr,
                       {select_marca},
                       COALESCE(avce.valor1, '') AS talle
                FROM `{tsd}` sd
                INNER JOIN `{tdep}` d ON d.CodDeposito = sd.id_deposito
                INNER JOIN `{tart}` a ON a.IDArt = sd.id_articulo
                {join_ce}
                {join_marca}
                WHERE {where_dep}
                  AND COALESCE(sd.saldo, 0) != 0
                  AND ({where_art})
                ORDER BY d.NombreDeposito, marca_nombre,
                         COALESCE(NULLIF(TRIM(a.id_manual), ''), a.CodigoArticuloT),
                         avce.valor1
            """
            cursor.execute(sql, tuple(params + params_art))
            rows = cursor.fetchall()

        filas_raw: List[Dict[str, Any]] = []
        for r in rows:
            talle = str_or_default(r.get("talle"), "").strip()
            if talle == "-":
                talle = ""
            filas_raw.append({
                "id_articulo": to_int_or_none(r.get("id_articulo")),
                "id_deposito": to_int_or_none(r.get("id_deposito")),
                "saldo": float(r.get("saldo") or 0),
                "codigo_manual": str_codigo_manual_articulo(r.get("codigo_manual")),
                "codigo_articulo": str_or_default(r.get("codigo_articulo"), "-"),
                "descripcion_articulo": str_or_default(r.get("descripcion_articulo"), "-"),
                "nombre_deposito": str_or_default(r.get("nombre_deposito"), "-"),
                "tipo_mpr": str_or_default(r.get("tipo_mpr"), ""),
                "marca_nombre": str_or_default(r.get("marca_nombre"), "Sin marca") or "Sin marca",
                "talle": talle,
                "cantidad_promedio_bulto": float(r.get("cantidad_promedio_bulto") or 0),
                "tipo_art_fab": str_or_default(r.get("tipo_art_fab"), ""),
            })

        filas = enriquecer_medidas_inventario(filas_raw, base_empresa)
        depositos_jerarquia, total_docenas = agrupar_jerarquia_deposito_marca(filas)
        ids_dep = {f["id_deposito"] for f in filas if f.get("id_deposito") is not None}

        return {
            "filas": filas,
            "depositos_jerarquia": depositos_jerarquia,
            "total_docenas": total_docenas,
            "kpis": {
                "total_docenas": total_docenas,
                "depositos": len(ids_dep),
                "filas": len(filas),
            },
            "fecha_corte": filtros.fecha_corte,
            "usa_stock_deposito": _usa_stock_deposito(filtros.fecha_corte),
        }
    except Exception as exc:
        logger.warning("consultar_inventario_deposito %s: %s", base_empresa, exc, exc_info=True)
        return vacio
