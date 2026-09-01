"""
Relay ventas netas (paridad administraNET-ecom mayoristapp relay-ventas-netas*.php).

Reutiliza el patrón MySQL de QueryRunnerService._run_ventas_netas / _get_ventas_netas_total:
``get_mysql_pool().get_connection(base_empresa)`` + ``cursor.execute(sql, params)``.
Criterio de comprobantes: mismo whitelist FA/FB/… y NC que ``reports/services/query_runner.py``.
"""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.connection_pool import get_mysql_pool
from core.utils.administranet_types import to_int_or_none
from ecom.services.filtros_estadisticas_relay import listado_filtros_estadisticas

logger = logging.getLogger(__name__)

# Mismo conjunto que QueryRunnerService._run_ventas_netas / _get_ventas_netas_total
_TIPOS_COMPROBANTE: Tuple[str, ...] = (
    "FA",
    "FB",
    "FC",
    "FE",
    "FM",
    "NCA",
    "NCB",
    "NCC",
    "NCE",
    "NCM",
)


def parse_filtrar_por(raw: Optional[str]) -> Dict[str, List[Any]]:
    """
    Parsea filtrarPor estilo PHP (pares clave|val1|val2|| otra_clave|...).
    Valores numéricos se convierten a int cuando aplica.
    """
    if not raw or not str(raw).strip():
        return {}
    out: Dict[str, List[Any]] = {}
    for chunk in str(raw).split("||"):
        chunk = chunk.strip()
        if not chunk:
            continue
        parts = chunk.split("|")
        if len(parts) < 2:
            continue
        key = parts[0].strip().lower()
        values: List[Any] = []
        for p in parts[1:]:
            p = p.strip()
            if not p:
                continue
            if p.isdigit():
                values.append(int(p))
            else:
                try:
                    values.append(int(p))
                except ValueError:
                    values.append(p)
        if key and values:
            out[key] = values
    return out


def _sum_monto_sql() -> str:
    return """
        SUM(CASE
            WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
                THEN COALESCE(cc.SubtotalDesc, 0)
            WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
                THEN -COALESCE(cc.SubtotalDesc, 0)
            ELSE 0
        END) AS ventas_netas
    """


def _sum_monto_sql_stock_line() -> str:
    """
    Importe por renglón ``stock`` (PrecioNetoxR), signo según ``cc.TipoComprobante``.
    Alineado a ramas PHP por ``stock`` + ``cuentacliente`` (no repite SubtotalDesc por línea).
    """
    return """
        SUM(CASE
            WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
                THEN COALESCE(st.PrecioNetoxR, 0)
            WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
                THEN -COALESCE(st.PrecioNetoxR, 0)
            ELSE 0
        END) AS ventas_netas
    """


def _sum_unidades_sql_stock_line() -> str:
    return """
        SUM(CASE
            WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
                THEN COALESCE(st.Cantidad, 0)
            WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
                THEN -COALESCE(st.Cantidad, 0)
            ELSE 0
        END) AS ventas_netas
    """


def _sum_peso_sql_stock_line() -> str:
    """
    Peso estimado por renglón: cantidad * coeficiente de peso (articulo_val_ce id_articulo_ce=1).
    """
    return """
        SUM(CASE
            WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
                THEN COALESCE(st.Cantidad, 0) * COALESCE(kg.valor, 0)
            WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
                THEN -COALESCE(st.Cantidad, 0) * COALESCE(kg.valor, 0)
            ELSE 0
        END) AS ventas_netas
    """


def _sum_utilidad_sql_stock_line(*, inflacion_factor: float = 1.0) -> str:
    factor = float(inflacion_factor or 1.0)
    # Costo estimado por renglón: cantidad * precio costo artículo.
    return f"""
        SUM(CASE
            WHEN cc.TipoComprobante IN ('FA', 'FB', 'FC', 'FE', 'FM')
                THEN (COALESCE(st.PrecioNetoxR, 0) - (COALESCE(st.Cantidad, 0) * COALESCE(art.PrecioCosto, 0))) * {factor}
            WHEN cc.TipoComprobante IN ('NCA', 'NCB', 'NCC', 'NCE', 'NCM')
                THEN -(COALESCE(st.PrecioNetoxR, 0) - (COALESCE(st.Cantidad, 0) * COALESCE(art.PrecioCosto, 0))) * {factor}
            ELSE 0
        END) AS ventas_netas
    """


_STOCK_TIPO_COMP_VENTAS = (
    "Venta",
    "Venta TPV",
    "Devol - Cliente",
    "ND Anul NC",
)


def _append_filtros_articulo_rubro(
    where: List[str], params: List[Any], filtros: Dict[str, List[Any]]
) -> None:
    """Filtros sobre artículo/rubro (solo listados que unen ``stock`` + ``articulo``)."""
    allowed = {
        "rubro": "ru.CodigoRubro",
        "subrubro": "art.IDSubRubro",
        "articulo": "art.IDArt",
    }
    for key, col in allowed.items():
        vals = filtros.get(key)
        if not vals:
            continue
        clean: List[Any] = []
        for v in vals:
            try:
                clean.append(int(v))
            except (TypeError, ValueError):
                continue
        if not clean:
            continue
        ph = ",".join(["%s"] * len(clean))
        where.append(f"{col} IN ({ph})")
        params.extend(clean)


def _where_fecha_y_base(
    rango_doble: bool,
    fecha_desde: date,
    fecha_hasta: date,
    fecha_desde_dos: Optional[date],
    fecha_hasta_dos: Optional[date],
) -> Tuple[List[str], List[Any]]:
    """Condiciones de fecha parametrizadas (uno o dos rangos OR)."""
    if (
        rango_doble
        and fecha_desde_dos is not None
        and fecha_hasta_dos is not None
    ):
        return (
            [
                "((cc.Fecha >= %s AND cc.Fecha <= %s) OR (cc.Fecha >= %s AND cc.Fecha <= %s))"
            ],
            [fecha_desde, fecha_hasta, fecha_desde_dos, fecha_hasta_dos],
        )
    return (["cc.Fecha >= %s", "cc.Fecha <= %s"], [fecha_desde, fecha_hasta])


def _append_tipo_comprobante(where: List[str], params: List[Any]) -> None:
    placeholders = ",".join(["%s"] * len(_TIPOS_COMPROBANTE))
    where.append(f"cc.TipoComprobante IN ({placeholders})")
    params.extend(_TIPOS_COMPROBANTE)


def _append_vendedor(
    where: List[str],
    params: List[Any],
    vendedor_id: Optional[int],
    vendedor_a_cargo: Optional[Sequence[int]],
) -> None:
    if vendedor_id is not None:
        where.append("cc.CodViajante = %s")
        params.append(vendedor_id)
        return
    if vendedor_a_cargo:
        cargo = [int(x) for x in vendedor_a_cargo if x is not None]
        if cargo:
            ph = ",".join(["%s"] * len(cargo))
            where.append(f"cc.CodViajante IN ({ph})")
            params.extend(cargo)


def _append_filtros_cuentacliente(
    where: List[str], params: List[Any], filtros: Dict[str, List[Any]]
) -> None:
    """AND campo IN (%s...) solo para claves admitidas (whitelist)."""
    allowed = {
        "cliente": "cc.Codigo",
        "codigo_cliente": "cc.Codigo",
        "vendedor": "cc.CodViajante",
        "codviajante": "cc.CodViajante",
    }
    for key, col in allowed.items():
        vals = filtros.get(key)
        if not vals:
            continue
        clean: List[Any] = []
        for v in vals:
            try:
                clean.append(int(v))
            except (TypeError, ValueError):
                continue
        if not clean:
            continue
        ph = ",".join(["%s"] * len(clean))
        where.append(f"{col} IN ({ph})")
        params.extend(clean)


def _normalize_int_ids(values: Optional[Sequence[Any]]) -> List[int]:
    """Lista de enteros únicos; ignora None e inválidos."""
    if not values:
        return []
    out: List[int] = []
    seen: set[int] = set()
    for v in values:
        parsed = to_int_or_none(v)
        if parsed is not None and parsed not in seen:
            seen.add(parsed)
            out.append(parsed)
    return out


def _append_sucursales_punto_venta(
    where: List[str],
    params: List[Any],
    *,
    sucursales: Optional[Sequence[Any]] = None,
    punto_venta: Optional[Sequence[Any]] = None,
    punto_venta_id: Optional[int] = None,
) -> None:
    """Filtros explícitos sucursal/PV (no van en whitelist filtrarPor)."""
    suc_ids = _normalize_int_ids(sucursales)
    if suc_ids:
        ph = ",".join(["%s"] * len(suc_ids))
        where.append(f"cc.CodSucursal IN ({ph})")
        params.extend(suc_ids)

    pv_ids = set(_normalize_int_ids(punto_venta))
    scalar_pv = to_int_or_none(punto_venta_id)
    if scalar_pv is not None:
        pv_ids.add(scalar_pv)
    if pv_ids:
        pv_list = sorted(pv_ids)
        ph = ",".join(["%s"] * len(pv_list))
        where.append(f"cc.id_pv IN ({ph})")
        params.extend(pv_list)


def get_ventas_netas(
    *,
    base_empresa: str,
    fecha_desde: date,
    fecha_hasta: date,
    vendedor_id: Optional[int],
    listar_por: str = "mes",
    tipo: str = "monto",
    filtros: Optional[Dict[str, List[Any]]] = None,
    rango_doble: bool = False,
    fecha_desde_dos: Optional[date] = None,
    fecha_hasta_dos: Optional[date] = None,
    op_rango: Optional[str] = None,
    incluir_utilidades: bool = False,
    punto_venta_id: Optional[int] = None,
    sucursales: Optional[Sequence[Any]] = None,
    punto_venta: Optional[Sequence[Any]] = None,
    vendedor_a_cargo: Optional[Sequence[int]] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Servicio central relay (SQL parametrizado).

    - vendedor_id=None sin vendedor_a_cargo → sin filtro CodViajante (gerencia).
    - ``listar_por`` ``rubro`` / ``subrubro`` / ``articulo`` / ``marca`` / ``zona`` /
      ``tipocliente`` / ``proveedor``: agregación por renglones ``stock`` + ``PrecioNetoxR``.
    - tipo ``monto`` soportado; ``unidades`` / ``peso`` devuelven vacío hasta
      portar ramas stock del PHP (documentado en respuesta).
    - incluir_utilidades: reservado; si True y no hay implementación, se ignora
      y se deja nota en ``meta``.
    """
    filtros = filtros or {}
    listar_por = (listar_por or "mes").strip().lower()
    tipo = (tipo or "monto").strip().lower()

    meta: Dict[str, Any] = {
        "listar_por": listar_por,
        "tipo": tipo,
        "relay": "ventas_netas",
        "op_rango": op_rango,
    }
    if incluir_utilidades:
        meta["incluir_utilidades"] = True
        meta["metrica"] = "utilidad_neta"
    if kwargs:
        meta["relay_kwargs"] = {k: kwargs[k] for k in sorted(kwargs)}

    empty = {"data": [], "cabeceras": [], "titulos": [], "meta": meta}

    if listar_por not in (
        "mes",
        "cliente",
        "vendedor",
        "rubro",
        "subrubro",
        "articulo",
        "marca",
        "zona",
        "tipocliente",
        "proveedor",
    ):
        meta["nota"] = (
            f"listar_por={listar_por!r} no soportado en relay v1 "
            "(implementar subrubro/marca/zona según SPEC_VENTAS_NETAS)."
        )
        return empty

    where: List[str] = [
        "cc.Anulado = 'No'",
        "cc.CodigoMovimiento <> 0",
    ]
    params: List[Any] = []

    w_fecha, p_fecha = _where_fecha_y_base(
        rango_doble, fecha_desde, fecha_hasta, fecha_desde_dos, fecha_hasta_dos
    )
    where.extend(w_fecha)
    params.extend(p_fecha)
    _append_tipo_comprobante(where, params)
    _append_vendedor(where, params, vendedor_id, vendedor_a_cargo)
    _append_filtros_cuentacliente(where, params, filtros)

    if listar_por in ("rubro", "subrubro", "articulo", "marca", "zona", "tipocliente", "proveedor"):
        _append_filtros_articulo_rubro(where, params, filtros)
        where.append("st.Anulado = %s")
        params.append("No")
        ph_tc = ",".join(["%s"] * len(_STOCK_TIPO_COMP_VENTAS))
        where.append(f"st.TipoComp IN ({ph_tc})")
        params.extend(_STOCK_TIPO_COMP_VENTAS)
        where.append("(ru.CodigoRubro IS NULL OR ru.anulado = 'No')")
        where.append(sql_excluir_tipo_art_gasto("art"))
        meta["nota"] = (
            "listar_por rubro/subrubro/articulo/marca/zona/tipocliente/proveedor: "
            "importe por renglones stock.PrecioNetoxR "
            "(ramas Venta/TPV/Devol/ND Anul NC); total puede diferir del agregado solo cuentacliente."
        )
    elif tipo not in ("monto", ""):
        meta["nota"] = (
            f"tipo={tipo!r} soportado solo en listar_por de stock "
            "(rubro/subrubro/articulo/marca/zona/tipocliente/proveedor)."
        )
        return empty

    _append_sucursales_punto_venta(
        where,
        params,
        sucursales=sucursales,
        punto_venta=punto_venta,
        punto_venta_id=punto_venta_id,
    )

    where_clause = " AND ".join(where)
    sum_sql = _sum_monto_sql()
    sum_sql_stock = _sum_monto_sql_stock_line()
    sum_sql_stock_unidades = _sum_unidades_sql_stock_line()
    sum_sql_stock_peso = _sum_peso_sql_stock_line()

    tipo_inflacion_raw = kwargs.get("tipoInflacion")
    inflacion_factor = 1.0
    if tipo_inflacion_raw not in (None, ""):
        try:
            pct = float(tipo_inflacion_raw)
            inflacion_factor = 1.0 + (pct / 100.0)
            meta["tipo_inflacion_pct"] = pct
        except (TypeError, ValueError):
            meta["nota_inflacion"] = "tipoInflacion inválido; se usa 0%."

    if incluir_utilidades and listar_por not in (
        "rubro",
        "subrubro",
        "articulo",
        "marca",
        "zona",
        "tipocliente",
        "proveedor",
    ):
        meta["nota"] = "ut/uti soportado solo en dimensiones basadas en stock."
        return empty

    if incluir_utilidades:
        sum_sql_stock_line = _sum_utilidad_sql_stock_line(inflacion_factor=inflacion_factor)
    elif tipo in ("", "monto"):
        sum_sql_stock_line = sum_sql_stock
    elif tipo == "unidades":
        sum_sql_stock_line = sum_sql_stock_unidades
    elif tipo == "peso":
        sum_sql_stock_line = sum_sql_stock_peso
    else:
        meta["nota"] = f"tipo={tipo!r} pendiente de paridad PHP."
        return empty

    if listar_por == "mes":
        sql = f"""
            SELECT
                DATE_FORMAT(cc.Fecha, '%%Y-%%m') AS periodo,
                DATE_FORMAT(cc.Fecha, '%%m/%%Y') AS periodo_etiqueta,
                {sum_sql}
            FROM cuentacliente cc
            WHERE {where_clause}
            GROUP BY DATE_FORMAT(cc.Fecha, '%%Y-%%m'), DATE_FORMAT(cc.Fecha, '%%m/%%Y')
            ORDER BY periodo ASC
        """
        cabeceras = ["periodo", "periodo_etiqueta", "ventas_netas"]
        titulos = ["Período", "Período", "Ventas netas"]
    elif listar_por == "cliente":
        sql = f"""
            SELECT
                cc.Codigo AS codigo_cliente,
                COALESCE(MAX(cli.nombre_cliente), '') AS nombre_cliente,
                {sum_sql}
            FROM cuentacliente cc
            LEFT JOIN cliente cli ON cli.Codigo = cc.Codigo
            WHERE {where_clause}
            GROUP BY cc.Codigo
            ORDER BY ventas_netas DESC, cc.Codigo ASC
        """
        cabeceras = ["codigo_cliente", "nombre_cliente", "ventas_netas"]
        titulos = ["Cliente", "Nombre", "Ventas netas"]
    elif listar_por == "vendedor":
        sql = f"""
            SELECT
                cc.CodViajante AS cod_vendedor,
                COALESCE(MAX(vj.Nombre), '') AS nombre_vendedor,
                {sum_sql}
            FROM cuentacliente cc
            LEFT JOIN viajantes vj ON vj.CodViajante = cc.CodViajante
            WHERE {where_clause}
            GROUP BY cc.CodViajante
            ORDER BY ventas_netas DESC, cc.CodViajante ASC
        """
        cabeceras = ["cod_vendedor", "nombre_vendedor", "ventas_netas"]
        titulos = ["Vendedor", "Nombre", "Ventas netas"]
    elif listar_por == "rubro":
        sql = f"""
            SELECT
                ru.CodigoRubro AS codigo_rubro,
                COALESCE(MAX(ru.NombreRubro), '') AS nombre_rubro,
                {sum_sql_stock_line}
            FROM stock st
            INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
            LEFT JOIN articulo art ON art.IDArt = st.IDArt
            LEFT JOIN rubro ru ON ru.CodigoRubro = art.CodigoRubro
            LEFT JOIN articulo_val_ce kg ON (kg.id_articulo = art.IDArt AND kg.id_articulo_ce = 1)
            WHERE {where_clause}
            GROUP BY ru.CodigoRubro
            ORDER BY ventas_netas DESC, ru.CodigoRubro ASC
        """
        cabeceras = ["codigo_rubro", "nombre_rubro", "ventas_netas"]
        titulos = ["Rubro", "Nombre", "Ventas netas"]
    elif listar_por == "subrubro":
        sql = f"""
            SELECT
                art.IDSubRubro AS id_subrubro,
                COALESCE(MAX(sr.NombreSubRubro), '') AS nombre_subrubro,
                {sum_sql_stock_line}
            FROM stock st
            INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
            LEFT JOIN articulo art ON art.IDArt = st.IDArt
            LEFT JOIN rubro ru ON ru.CodigoRubro = art.CodigoRubro
            LEFT JOIN subrubro sr ON sr.IDSubRubro = art.IDSubRubro
            LEFT JOIN articulo_val_ce kg ON (kg.id_articulo = art.IDArt AND kg.id_articulo_ce = 1)
            WHERE {where_clause}
            GROUP BY art.IDSubRubro
            ORDER BY ventas_netas DESC, art.IDSubRubro ASC
        """
        cabeceras = ["id_subrubro", "nombre_subrubro", "ventas_netas"]
        titulos = ["Subrubro", "Nombre", "Ventas netas"]
    elif listar_por == "articulo":
        sql = f"""
            SELECT
                art.IDArt AS id_articulo,
                COALESCE(MAX(art.id_manual), '') AS id_manual,
                COALESCE(MAX(art.NombreArticulo), '') AS nombre_articulo,
                {sum_sql_stock_line}
            FROM stock st
            INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
            LEFT JOIN articulo art ON art.IDArt = st.IDArt
            LEFT JOIN rubro ru ON ru.CodigoRubro = art.CodigoRubro
            LEFT JOIN articulo_val_ce kg ON (kg.id_articulo = art.IDArt AND kg.id_articulo_ce = 1)
            WHERE {where_clause}
            GROUP BY art.IDArt
            ORDER BY ventas_netas DESC, art.IDArt ASC
        """
        cabeceras = ["id_articulo", "id_manual", "nombre_articulo", "ventas_netas"]
        titulos = ["Artículo", "Id manual", "Nombre", "Ventas netas"]
    elif listar_por == "marca":
        sql = f"""
            SELECT
                art.CodigoMarca AS codigo_marca,
                COALESCE(MAX(marca.NombreMarca), '') AS nombre_marca,
                {sum_sql_stock_line}
            FROM stock st
            INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
            LEFT JOIN articulo art ON art.IDArt = st.IDArt
            LEFT JOIN rubro ru ON ru.CodigoRubro = art.CodigoRubro
            LEFT JOIN marca ON marca.CodMarca = art.CodigoMarca
            LEFT JOIN articulo_val_ce kg ON (kg.id_articulo = art.IDArt AND kg.id_articulo_ce = 1)
            WHERE {where_clause}
            GROUP BY art.CodigoMarca
            ORDER BY ventas_netas DESC, art.CodigoMarca ASC
        """
        cabeceras = ["codigo_marca", "nombre_marca", "ventas_netas"]
        titulos = ["Marca", "Nombre", "Ventas netas"]
    elif listar_por == "zona":
        sql = f"""
            SELECT
                cli.id_zona AS id_zona,
                COALESCE(MAX(zonas.nombre_zona), '') AS nombre_zona,
                {sum_sql_stock_line}
            FROM stock st
            INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
            LEFT JOIN articulo art ON art.IDArt = st.IDArt
            LEFT JOIN rubro ru ON ru.CodigoRubro = art.CodigoRubro
            LEFT JOIN cliente cli ON cli.Codigo = cc.Codigo
            LEFT JOIN erp_zona zonas ON zonas.id_zona = cli.id_zona
            LEFT JOIN articulo_val_ce kg ON (kg.id_articulo = art.IDArt AND kg.id_articulo_ce = 1)
            WHERE {where_clause}
            GROUP BY cli.id_zona
            ORDER BY ventas_netas DESC, cli.id_zona ASC
        """
        cabeceras = ["id_zona", "nombre_zona", "ventas_netas"]
        titulos = ["Zona", "Nombre", "Ventas netas"]
    elif listar_por == "tipocliente":
        sql = f"""
            SELECT
                cli.TipoCliente AS id_tipo_cliente,
                COALESCE(MAX(tpcli.NombreTipoCliente), '') AS nombre_tipo_cliente,
                {sum_sql_stock_line}
            FROM stock st
            INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
            LEFT JOIN articulo art ON art.IDArt = st.IDArt
            LEFT JOIN rubro ru ON ru.CodigoRubro = art.CodigoRubro
            LEFT JOIN cliente cli ON cli.Codigo = cc.Codigo
            LEFT JOIN tipo_cliente tpcli ON tpcli.IDTipoCliente = cli.TipoCliente
            LEFT JOIN articulo_val_ce kg ON (kg.id_articulo = art.IDArt AND kg.id_articulo_ce = 1)
            WHERE {where_clause}
            GROUP BY cli.TipoCliente
            ORDER BY ventas_netas DESC, cli.TipoCliente ASC
        """
        cabeceras = ["id_tipo_cliente", "nombre_tipo_cliente", "ventas_netas"]
        titulos = ["Tipo cliente", "Nombre", "Ventas netas"]
    else:
        sql = f"""
            SELECT
                art.CodigoProveedor AS codigo_proveedor,
                COALESCE(MAX(prov.Nombre), '') AS nombre_proveedor,
                {sum_sql_stock_line}
            FROM stock st
            INNER JOIN cuentacliente cc ON cc.CodigoMovimiento = st.CodigoMovimiento
            LEFT JOIN articulo art ON art.IDArt = st.IDArt
            LEFT JOIN rubro ru ON ru.CodigoRubro = art.CodigoRubro
            LEFT JOIN proveedor prov ON prov.Codigo = art.CodigoProveedor
            LEFT JOIN articulo_val_ce kg ON (kg.id_articulo = art.IDArt AND kg.id_articulo_ce = 1)
            WHERE {where_clause}
            GROUP BY art.CodigoProveedor
            ORDER BY ventas_netas DESC, art.CodigoProveedor ASC
        """
        cabeceras = ["codigo_proveedor", "nombre_proveedor", "ventas_netas"]
        titulos = ["Proveedor", "Nombre", "Ventas netas"]

    pool = get_mysql_pool()
    try:
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            colnames = [d[0] for d in cursor.description] if cursor.description else []
    except Exception as exc:
        logger.exception("get_ventas_netas SQL error base=%s", base_empresa)
        raise

    data: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(zip(colnames, row))
        if "ventas_netas" in item and item["ventas_netas"] is not None:
            v = item["ventas_netas"]
            if isinstance(v, Decimal):
                item["ventas_netas"] = float(v)
            else:
                item["ventas_netas"] = float(v or 0)
        data.append(item)

    return {
        "data": data,
        "cabeceras": cabeceras,
        "titulos": titulos,
        "meta": meta,
    }


def listado_seleccion_ventas_netas(
    *,
    base_empresa: str,
    tabla: str,
    usa_id_manual: bool,
    vendedor_a_cargo: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    arr_vend: List[int] = []
    for v in vendedor_a_cargo or []:
        try:
            arr_vend.append(int(v))
        except (TypeError, ValueError):
            continue
    rows = listado_filtros_estadisticas(
        base_empresa=base_empresa,
        tabla=str(tabla or "").strip().lower(),
        usa_id_manual=bool(usa_id_manual),
        arr_vend_cargo=arr_vend,
    )
    return {
        "data": rows,
        "cabeceras": ["label", "value"],
        "titulos": ["Etiqueta", "Valor"],
        "meta": {"relay": "ventas_netas", "queInforme": "seleccion", "tabla": tabla},
    }
