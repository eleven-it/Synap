"""
Servicio — Informe "Utilidad gerencial" (+ variante inflación).

Paridad con ``administraNET-ecom/mayoristapp/relay-ventas-netas-gerencia.php``
modo ``verInforme=ut`` (``utilidades_totales_todos`` / ``armar_sql_utilidad``) y
``uti`` (``utilidades_totales_todos_inflacion``).

Calcula, agrupado por dimensión, sobre la tabla ``stock`` unida a ``cuentacliente``:
Venta, Descuento (NC), Venta Neta, Costo, Utilidad y Utilidad %; con variante de
inflación (doble rango + índice de costos).

Reglas de proyecto:
- SQL 100% parametrizado (``cursor.execute(sql, params)``); ids a ``int``.
- Costo por ``stock.PrecioCostoxR`` (no ``PrecioCostoxU*Cantidad``), signo por
  ``stock.TipoComp`` (paridad PHP).
- NC/Desc solo se integran en dimensiones ``cliente/tipocliente/vendedor/zona``
  y sin filtros de nivel artículo (paridad ``traigoArrayNc``).
- Montos con ``Decimal``; salida JSON en ``float``.
- Conexión legacy vía ``core.mysql_pool``.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence

from core.utils.administranet_types import to_date_or_none, to_decimal_or_none, to_int_or_none
from reports.services.connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)

# Renglones de stock considerados y su signo (positivo salvo devolución).
_STOCK_POS = ("Venta", "Venta TPV", "ND Anul NC")
_STOCK_TIPOCOMP = ("Venta", "Venta TPV", "Devol - Cliente", "ND Anul NC")

# Dimensiones de nivel artículo: en ellas NO se integran NC/Desc (paridad PHP).
_ARTICULO_LEVEL = frozenset(
    {"articulo", "proveedor", "rubro", "subrubro", "categoria", "marca"}
)

# Comprobantes de la consulta de NC/descuentos.
_NC_TIPOS = (
    "NCA", "NCB", "NCE", "NCC", "NCM",
    "FA", "FB", "FE", "FC", "FM",
    "NDA", "NDB", "NDE", "NDC", "NDM",
)
_NC_TIPOS_ND = ("NDA", "NDB", "NDE", "NDC", "NDM")
_NC_TIPOS_NC = ("NCA", "NCB", "NCE", "NCC", "NCM")
_NC_TIPOS_FAC = ("FA", "FB", "FE", "FC", "FM")


class _Dim:
    __slots__ = ("cod", "nom", "group", "order", "filter_col", "nc_col")

    def __init__(self, cod: str, nom: str, group: str, order: str, filter_col: str, nc_col: Optional[str]):
        self.cod = cod
        self.nom = nom
        self.group = group
        self.order = order
        self.filter_col = filter_col
        self.nc_col = nc_col  # columna de agrupación en la consulta de NC (o None)


# Config por dimensión (paridad armar_sql_utilidad switch listarPor).
_DIMENSIONES: Dict[str, _Dim] = {
    "cliente": _Dim(
        "cli.Codigo",
        "CONCAT(COALESCE(cli.nombre_cliente,'-'),' (Cod: ',cli.Codigo,')')",
        "cli.Codigo", "cli.nombre_cliente", "cli.Codigo", "cc.Codigo",
    ),
    "tipocliente": _Dim(
        "tpcli.IDTipoCliente", "COALESCE(tpcli.NombreTipoCliente,'-')",
        "tpcli.IDTipoCliente", "tpcli.NombreTipoCliente", "tpcli.IDTipoCliente", "tpcli.IDTipoCliente",
    ),
    "vendedor": _Dim(
        "vend.CodViajante", "COALESCE(vend.Nombre,'-')",
        "vend.CodViajante", "vend.Nombre", "cc.CodViajante", "cc.CodViajante",
    ),
    "zona": _Dim(
        "zonas.id_zona", "COALESCE(zonas.nombre_zona,'-')",
        "zonas.id_zona", "zonas.nombre_zona", "zonas.id_zona", "zonas.id_zona",
    ),
    "articulo": _Dim(
        "arti.IDArt", "COALESCE(arti.NombreArticulo,'-')",
        "arti.IDArt", "arti.NombreArticulo", "arti.IDArt", None,
    ),
    "proveedor": _Dim(
        "prov.Codigo", "COALESCE(prov.Nombre,'-')",
        "prov.Codigo", "prov.Nombre", "prov.Codigo", None,
    ),
    "categoria": _Dim(
        "cat.id_categoria", "COALESCE(cat.nombre_categoria,'-')",
        "cat.id_categoria", "cat.nombre_categoria", "cat.id_categoria", None,
    ),
    "rubro": _Dim(
        "ru.CodigoRubro", "COALESCE(ru.NombreRubro,'-')",
        "ru.CodigoRubro", "ru.NombreRubro", "ru.CodigoRubro", None,
    ),
    "subrubro": _Dim(
        "srub.IdSubRubro", "COALESCE(srub.NombreSubRubro,'-')",
        "srub.IdSubRubro", "srub.NombreSubRubro", "srub.IdSubRubro", None,
    ),
    "marca": _Dim(
        "marca.CodMarca", "COALESCE(marca.NombreMarca,'-')",
        "marca.CodMarca", "marca.NombreMarca", "marca.CodMarca", None,
    ),
}

# Columnas de filtro admitidas (filtrarPor) en la consulta principal.
_FILTRO_COLS: Dict[str, str] = {
    "cliente": "cli.Codigo",
    "tipocliente": "tpcli.IDTipoCliente",
    "vendedor": "cc.CodViajante",
    "articulo": "arti.IDArt",
    "proveedor": "prov.Codigo",
    "zona": "zonas.id_zona",
    "categoria": "cat.id_categoria",
    "rubro": "ru.CodigoRubro",
    "subrubro": "srub.IdSubRubro",
    "marca": "marca.CodMarca",
}

# Columnas de filtro admitidas en la consulta de NC (solo dimensiones de cuentacliente).
_FILTRO_COLS_NC: Dict[str, str] = {
    "cliente": "cli.Codigo",
    "tipocliente": "tpcli.IDTipoCliente",
    "vendedor": "cc.CodViajante",
    "zona": "zonas.id_zona",
}

_JOINS = """
        FROM stock AS st
        LEFT JOIN cuentacliente AS cc ON cc.CodigoMovimiento = st.CodigoMovimiento
        LEFT JOIN articulo AS arti ON arti.IDArt = st.IDArt
        LEFT JOIN rubro AS ru ON ru.CodigoRubro = arti.CodigoRubro
        LEFT JOIN rubro_categoria AS cat ON cat.id_categoria = ru.id_categoria
        LEFT JOIN subrubro AS srub ON srub.IDSubRubro = arti.IDSubRubro
        LEFT JOIN marca ON marca.CodMarca = arti.CodigoMarca
        LEFT JOIN proveedor AS prov ON prov.Codigo = arti.CodigoProveedor
        LEFT JOIN cliente AS cli ON cli.Codigo = st.CodigoCP
        LEFT JOIN viajantes AS vend ON vend.CodViajante = cc.CodViajante
        LEFT JOIN erp_zona AS zonas ON zonas.id_zona = cli.id_zona
        LEFT JOIN tipo_cliente AS tpcli ON tpcli.IDTipoCliente = cli.TipoCliente
"""

COLUMNS_BASE = [
    {"title": "Detalle", "data": "nombre"},
    {"title": "Venta", "data": "venta", "money": True},
    {"title": "Desc", "data": "desc", "money": True},
    {"title": "Venta Neta", "data": "venta_neta", "money": True},
    {"title": "Costo", "data": "costo", "money": True},
    {"title": "Utilidad", "data": "utilidad", "money": True},
    {"title": "Utilidad %", "data": "utilidad_pct", "pct": True},
]
COLUMNS_INFLACION = [
    {"title": "Venta Ant", "data": "venta_ant", "money": True},
    {"title": "Desc Ant", "data": "desc_ant", "money": True},
    {"title": "Índice", "data": "indice", "factor": True},
    {"title": "Venta Esp", "data": "venta_esp", "money": True},
    {"title": "Resultado", "data": "resultado", "factor": True},
]

_CAMPOS_MONTO = ("venta", "desc", "venta_neta", "costo", "utilidad")


def _dec(value: Any) -> Decimal:
    d = to_decimal_or_none(value)
    return d if d is not None else Decimal("0")


def _clean_ids(vals: Sequence[Any]) -> List[int]:
    out: List[int] = []
    for v in vals or []:
        iv = to_int_or_none(v)
        if iv is not None:
            out.append(iv)
    return out


def _signo_case(col: str) -> str:
    pos = " OR ".join([f"st.TipoComp = '{t}'" for t in _STOCK_POS])
    return f"SUM(CASE WHEN {pos} THEN ({col}) ELSE -({col}) END)"


def _signo_case_guard(col: str) -> str:
    """Igual que _signo_case pero acotado a un rango de fechas (para inflación)."""
    pos = " OR ".join([f"st.TipoComp = '{t}'" for t in _STOCK_POS])
    return (
        "SUM(CASE WHEN st.Fecha BETWEEN %s AND %s THEN "
        f"(CASE WHEN {pos} THEN ({col}) ELSE -({col}) END) ELSE 0 END)"
    )


def _rango_inflacion(fecha_desde: str, fecha_hasta: str, tipo_inflacion: Optional[str]) -> tuple[str, str]:
    d0 = date.fromisoformat(fecha_desde)
    d1 = date.fromisoformat(fecha_hasta)
    tipo = str(tipo_inflacion or "mensual").strip().lower()
    if tipo == "anual":
        return (_menos_un_anio(d0).isoformat(), _menos_un_anio(d1).isoformat())
    # mensual (por defecto): desplaza el mismo lapso hacia atrás.
    span = (d1 - d0)
    return ((d0 - span - timedelta(days=1)).isoformat(), (d0 - timedelta(days=1)).isoformat())


def _menos_un_anio(d: date) -> date:
    try:
        return d.replace(year=d.year - 1)
    except ValueError:  # 29/02
        return d.replace(year=d.year - 1, day=28)


def get_utilidad_gerencial(
    base_empresa: str,
    *,
    fecha_desde: Any,
    fecha_hasta: Any,
    listar_por: str = "cliente",
    filtros: Optional[Dict[str, List[Any]]] = None,
    punto_venta_id: Optional[Sequence[int]] = None,
    vendedor_id: Optional[int] = None,
    vendedor_a_cargo: Optional[Sequence[int]] = None,
    con_inflacion: bool = False,
    tipo_inflacion: Optional[str] = None,
) -> Dict[str, Any]:
    desde = to_date_or_none(fecha_desde)
    hasta = to_date_or_none(fecha_hasta)
    if not desde or not hasta:
        raise ValueError("fecha_desde y fecha_hasta son obligatorias (YYYY-MM-DD).")

    listar_por = (listar_por or "cliente").strip().lower()
    dim = _DIMENSIONES.get(listar_por)
    if dim is None:
        raise ValueError(f"listar_por={listar_por!r} no soportado.")

    filtros = filtros or {}
    desde_dos = hasta_dos = None
    if con_inflacion:
        desde_dos, hasta_dos = _rango_inflacion(desde, hasta, tipo_inflacion)

    # NC/Desc solo para dimensiones de cuentacliente y sin filtros de artículo.
    filtro_articulo = any(k in _ARTICULO_LEVEL for k in filtros.keys())
    nc_aplica = dim.nc_col is not None and not filtro_articulo

    # ---- SELECT de sumas ----
    select_parts: List[str] = [f"{dim.cod} AS cod", f"{dim.nom} AS nombre"]
    select_params: List[Any] = []
    if con_inflacion:
        for col in ("st.PrecioVentaxR", "st.PrecioNetoxR", "st.PrecioCostoxR",
                    "(st.PrecioNetoxR - st.PrecioCostoxR)"):
            select_parts.append(_signo_case_guard(col))
            select_params.extend([desde, hasta])
        # Neto2 (rango anterior)
        select_parts.append(_signo_case_guard("st.PrecioNetoxR"))
        select_params.extend([desde_dos, hasta_dos])
        alias = ["venta", "neto", "costo", "utilidad", "neto2"]
    else:
        for col in ("st.PrecioVentaxR", "st.PrecioNetoxR", "st.PrecioCostoxR",
                    "(st.PrecioNetoxR - st.PrecioCostoxR)"):
            select_parts.append(_signo_case(col))
        alias = ["venta", "neto", "costo", "utilidad"]

    select_sql = select_parts[0] + ", " + select_parts[1]
    for name, expr in zip(alias, select_parts[2:]):
        select_sql += f", {expr} AS {name}"

    # ---- WHERE ----
    where: List[str] = ["st.Anulado = 'No'", "st.visualiza_ensamble = 'No'"]
    params: List[Any] = list(select_params)
    tc_ph = ", ".join(["%s"] * len(_STOCK_TIPOCOMP))
    where.append(f"st.TipoComp IN ({tc_ph})")
    params.extend(_STOCK_TIPOCOMP)

    if con_inflacion:
        where.append("((st.Fecha BETWEEN %s AND %s) OR (st.Fecha BETWEEN %s AND %s))")
        params.extend([desde, hasta, desde_dos, hasta_dos])
    else:
        where.append("st.Fecha BETWEEN %s AND %s")
        params.extend([desde, hasta])

    _aplicar_scope_vendedor(where, params, vendedor_id, vendedor_a_cargo, filtros)
    _aplicar_filtros(where, params, filtros, _FILTRO_COLS)
    _aplicar_punto_venta(where, params, punto_venta_id)

    sql = (
        f"SELECT {select_sql} {_JOINS} WHERE " + " AND ".join(where)
        + f" GROUP BY {dim.group} ORDER BY {dim.order} ASC"
    )

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        colnames = [d[0] for d in cursor.description] if cursor.description else []

        nc_map: Dict[Any, Decimal] = {}
        nc_map_inf: Dict[Any, Decimal] = {}
        indice_map: Dict[Any, Decimal] = {}
        if nc_aplica:
            nc_map = _consultar_nc(cursor, dim, filtros, punto_venta_id, desde, hasta)
            if con_inflacion:
                nc_map_inf = _consultar_nc(cursor, dim, filtros, punto_venta_id, desde_dos, hasta_dos)
        if con_inflacion:
            indice_map = _consultar_indice(
                cursor, dim, filtros, punto_venta_id, desde, hasta, desde_dos, hasta_dos,
                vendedor_id, vendedor_a_cargo,
            )

    filas = _armar_filas(rows, colnames, con_inflacion, nc_map, nc_map_inf, indice_map)
    totales = _armar_totales(filas, con_inflacion)
    columns = COLUMNS_BASE + (COLUMNS_INFLACION if con_inflacion else [])

    return {
        "columns": columns,
        "filas": filas,
        "totales": totales,
        "meta": {
            "listar_por": listar_por,
            "con_inflacion": con_inflacion,
            "tipo_inflacion": (tipo_inflacion or "mensual") if con_inflacion else None,
            "rango_anterior": {"desde": desde_dos, "hasta": hasta_dos} if con_inflacion else None,
            "nc_aplica": nc_aplica,
        },
    }


def _aplicar_scope_vendedor(
    where: List[str],
    params: List[Any],
    vendedor_id: Optional[int],
    vendedor_a_cargo: Optional[Sequence[int]],
    filtros: Dict[str, List[Any]],
) -> None:
    if vendedor_id is not None:
        where.append("cc.CodViajante = %s")
        params.append(int(vendedor_id))
        return
    # Supervisor: si no filtró vendedor explícitamente, restringe a su cartera.
    if vendedor_a_cargo and not filtros.get("vendedor"):
        cargo = _clean_ids(vendedor_a_cargo)
        if cargo:
            ph = ", ".join(["%s"] * len(cargo))
            where.append(f"cc.CodViajante IN ({ph})")
            params.extend(cargo)


def _aplicar_filtros(
    where: List[str],
    params: List[Any],
    filtros: Dict[str, List[Any]],
    cols: Dict[str, str],
) -> None:
    for key, col in cols.items():
        vals = filtros.get(key)
        if not vals:
            continue
        clean = _clean_ids(vals)
        if not clean:
            continue
        ph = ", ".join(["%s"] * len(clean))
        where.append(f"{col} IN ({ph})")
        params.extend(clean)


def _aplicar_punto_venta(
    where: List[str], params: List[Any], punto_venta_id: Optional[Sequence[int]]
) -> None:
    pvs = _clean_ids(punto_venta_id or [])
    if pvs:
        ph = ", ".join(["%s"] * len(pvs))
        where.append(f"cc.id_pv IN ({ph})")
        params.extend(pvs)


def _consultar_nc(
    cursor: Any,
    dim: _Dim,
    filtros: Dict[str, List[Any]],
    punto_venta_id: Optional[Sequence[int]],
    desde: str,
    hasta: str,
) -> Dict[Any, Decimal]:
    importe = (
        "SUM(CASE "
        "WHEN cc.TipoNC = 'Devolucion' THEN "
        "(CASE WHEN cc.ImpDesc1 <> 0 OR cc.ImpDesc2 <> 0 THEN (cc.ImpDesc1 + cc.ImpDesc2) ELSE 0 END) "
        f"WHEN cc.TipoComprobante IN ({', '.join(['%s'] * len(_NC_TIPOS_ND))}) THEN cc.SubtotalDesc "
        f"WHEN cc.TipoComprobante IN ({', '.join(['%s'] * len(_NC_TIPOS_NC))}) THEN cc.SubtotalDesc * -1 "
        f"WHEN cc.TipoComprobante IN ({', '.join(['%s'] * len(_NC_TIPOS_FAC))}) THEN (cc.ImpDesc1 + cc.ImpDesc2) * -1 "
        "ELSE 0 END) AS importe"
    )
    params: List[Any] = [*_NC_TIPOS_ND, *_NC_TIPOS_NC, *_NC_TIPOS_FAC]

    where: List[str] = ["cc.Anulado = 'No'"]
    tp_ph = ", ".join(["%s"] * len(_NC_TIPOS))
    where.append(f"cc.TipoComprobante IN ({tp_ph})")
    params.extend(_NC_TIPOS)
    where.append("cc.Fecha BETWEEN %s AND %s")
    params.extend([desde, hasta])
    where.append("(cc.concepto_nd IS NULL OR cc.concepto_nd <> 'Anulacion NC - Mercaderia')")

    _aplicar_filtros(where, params, filtros, _FILTRO_COLS_NC)
    _aplicar_punto_venta(where, params, punto_venta_id)

    sql = (
        f"SELECT {dim.nc_col} AS cod, {importe} "
        "FROM cuentacliente AS cc "
        "LEFT JOIN cliente AS cli ON cli.Codigo = cc.Codigo "
        "LEFT JOIN viajantes AS vend ON vend.CodViajante = cc.CodViajante "
        "LEFT JOIN erp_zona AS zonas ON zonas.id_zona = cli.id_zona "
        "LEFT JOIN tipo_cliente AS tpcli ON tpcli.IDTipoCliente = cli.TipoCliente "
        "WHERE " + " AND ".join(where) + f" GROUP BY {dim.nc_col}"
    )
    cursor.execute(sql, params)
    out: Dict[Any, Decimal] = {}
    for cod, imp in cursor.fetchall():
        out[_key(cod)] = _dec(imp)
    return out


def _consultar_indice(
    cursor: Any,
    dim: _Dim,
    filtros: Dict[str, List[Any]],
    punto_venta_id: Optional[Sequence[int]],
    desde: str,
    hasta: str,
    desde_dos: str,
    hasta_dos: str,
    vendedor_id: Optional[int],
    vendedor_a_cargo: Optional[Sequence[int]],
) -> Dict[Any, Decimal]:
    select = (
        f"{dim.cod} AS cod, "
        "(AVG(CASE WHEN st.Fecha BETWEEN %s AND %s THEN st.PrecioCostoxU ELSE NULL END) / "
        "AVG(CASE WHEN st.Fecha BETWEEN %s AND %s THEN st.PrecioCostoxU ELSE NULL END)) AS indice"
    )
    params: List[Any] = [desde, hasta, desde_dos, hasta_dos]

    where: List[str] = ["st.Anulado = 'No'", "st.visualiza_ensamble = 'No'"]
    tc_ph = ", ".join(["%s"] * len(_STOCK_TIPOCOMP))
    where.append(f"st.TipoComp IN ({tc_ph})")
    params.extend(_STOCK_TIPOCOMP)
    where.append("((st.Fecha BETWEEN %s AND %s) OR (st.Fecha BETWEEN %s AND %s))")
    params.extend([desde, hasta, desde_dos, hasta_dos])

    _aplicar_scope_vendedor(where, params, vendedor_id, vendedor_a_cargo, filtros)
    _aplicar_filtros(where, params, filtros, _FILTRO_COLS)
    _aplicar_punto_venta(where, params, punto_venta_id)

    sql = (
        f"SELECT {select} {_JOINS} WHERE " + " AND ".join(where)
        + f" GROUP BY {dim.group}"
    )
    cursor.execute(sql, params)
    out: Dict[Any, Decimal] = {}
    for cod, indice in cursor.fetchall():
        d = to_decimal_or_none(indice)
        out[_key(cod)] = d if d is not None else Decimal("1")
    return out


def _key(cod: Any) -> Any:
    iv = to_int_or_none(cod)
    return iv if iv is not None else cod


def _armar_filas(
    rows: Sequence[Sequence[Any]],
    colnames: Sequence[str],
    con_inflacion: bool,
    nc_map: Dict[Any, Decimal],
    nc_map_inf: Dict[Any, Decimal],
    indice_map: Dict[Any, Decimal],
) -> List[Dict[str, Any]]:
    filas: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(zip(colnames, row))
        cod = item.get("cod")
        clave = _key(cod)
        neto = _dec(item.get("neto"))
        costo = _dec(item.get("costo"))
        utilidad_base = _dec(item.get("utilidad"))
        venta = _dec(item.get("venta"))
        desc = nc_map.get(clave, Decimal("0"))

        venta_neta = neto + desc
        utilidad = utilidad_base + desc
        utilidad_pct = float(venta_neta / costo) if costo != 0 else 0.0

        fila: Dict[str, Any] = {
            "cod": cod,
            "nombre": item.get("nombre") if item.get("nombre") is not None else "-",
            "venta": float(venta),
            "desc": float(desc),
            "venta_neta": float(venta_neta),
            "costo": float(costo),
            "utilidad": float(utilidad),
            "utilidad_pct": utilidad_pct,
        }

        if con_inflacion:
            neto2 = _dec(item.get("neto2"))
            desc_ant = nc_map_inf.get(clave, Decimal("0"))
            indice = indice_map.get(clave, Decimal("1"))
            indice = indice.quantize(Decimal("0.01"))
            venta_esp = (neto2 + desc_ant) * indice
            if (neto2 * indice) == 0:
                resultado = Decimal("1")
            else:
                resultado = neto / ((neto2 + desc_ant) * indice)
            fila.update(
                {
                    "venta_ant": float(neto2),
                    "desc_ant": float(desc_ant),
                    "indice": float(indice),
                    "venta_esp": float(venta_esp),
                    "resultado": float(resultado),
                }
            )
        filas.append(fila)
    return filas


def _armar_totales(filas: Sequence[Dict[str, Any]], con_inflacion: bool) -> Dict[str, Any]:
    acum = {c: Decimal("0") for c in _CAMPOS_MONTO}
    for fila in filas:
        for c in _CAMPOS_MONTO:
            acum[c] += Decimal(str(fila.get(c, 0)))
    total_neto = acum["venta_neta"]
    total_costo = acum["costo"]
    salida: Dict[str, Any] = {"nombre": "Total Gral"}
    salida.update({c: float(acum[c]) for c in _CAMPOS_MONTO})
    salida["utilidad_pct"] = float(total_neto / total_costo) if total_costo != 0 else 0.0
    if con_inflacion:
        venta_ant = sum((Decimal(str(f.get("venta_ant", 0))) for f in filas), Decimal("0"))
        desc_ant = sum((Decimal(str(f.get("desc_ant", 0))) for f in filas), Decimal("0"))
        salida["venta_ant"] = float(venta_ant)
        salida["desc_ant"] = float(desc_ant)
        salida["indice"] = None
        salida["venta_esp"] = None
        salida["resultado"] = None
    return salida
