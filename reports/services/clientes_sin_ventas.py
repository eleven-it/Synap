"""
Servicio — Informe "Clientes sin ventas por vendedor" (paridad mayoristapp
``relay-clientes-vendedor.php``).

Lista clientes activos que NO tienen comprobantes en un período (excluyendo notas
de crédito y anulados), agrupados por vendedor, con resumen por vendedor y global
para gráficos.

Reglas de proyecto:
- SQL 100% parametrizado (``cursor.execute(sql, params)``); nunca concatenar
  fechas ni ids de usuario.
- Listas de ``CodViajante`` normalizadas a ``int`` antes de armar cláusulas ``IN``.
- Conexión legacy vía ``core.mysql_pool`` (``get_mysql_pool().get_connection(base)``),
  mismo patrón que ``reports/services/ventas_netas.py``.
- Tipos AdministraNET normalizados con ``core.utils.administranet_types``.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence

from core.utils.administranet_types import str_or_default, to_date_or_none, to_int_or_none
from reports.services.connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)

# Columnas expuestas al front (compatibles con la tabla del informe).
COLUMNS: List[Dict[str, str]] = [
    {"title": "Cod. Cliente", "data": "CodigoDisplay"},
    {"title": "Cliente", "data": "Nombre_cliente"},
    {"title": "Última compra", "data": "UltimaCompra"},
    {"title": "Vendedor", "data": "VendedorLabel"},
]

_ORDEN_SIN_COMPRA = "9999-12-31"


def parse_filtrar_por(raw: Optional[str]) -> List[int]:
    """
    Extrae los ``CodViajante`` numéricos del filtro acumulado.

    Formato legacy: ``"vendedor|<id>|<label>|<indice>||vendedor|<id>|..."``.
    Descarta ``todos`` y cualquier valor no numérico (defensa anti-inyección).
    Devuelve la lista de enteros únicos preservando el orden.
    """
    out: List[int] = []
    if not raw:
        return out
    for linea in str(raw).split("||"):
        if not linea:
            continue
        partes = linea.split("|")
        if len(partes) >= 2 and partes[0] == "vendedor":
            val = partes[1].strip()
            if val and val.lower() != "todos":
                iv = to_int_or_none(val)
                if iv is not None:
                    out.append(iv)
    seen: set = set()
    uniq: List[int] = []
    for x in out:
        if x not in seen:
            seen.add(x)
            uniq.append(x)
    return uniq


def _clausula_in(column: str, ids: Sequence[int]) -> tuple[str, List[int]]:
    """Devuelve (fragmento SQL parametrizado, params) para ``column IN (...)``."""
    ids_int = [int(i) for i in ids]
    placeholders = ", ".join(["%s"] * len(ids_int))
    return (f" AND {column} IN ({placeholders})", ids_int)


def _normalize_scope_ids(values: Optional[Sequence]) -> List[int]:
    out: List[int] = []
    for raw in values or []:
        parsed = to_int_or_none(raw)
        if parsed is not None:
            out.append(parsed)
    return out


def _cc_periodo_scope_on_clause(
    *,
    table_alias: str = "cc_periodo",
    sucursales: Optional[Sequence[int]] = None,
    puntos_venta: Optional[Sequence[int]] = None,
) -> tuple[str, List[int]]:
    """Cláusulas de alcance sucursal/PV para ON de anti-join (nunca en WHERE)."""
    parts: List[str] = []
    params: List[int] = []
    suc_ids = _normalize_scope_ids(sucursales)
    pv_ids = _normalize_scope_ids(puntos_venta)
    if suc_ids:
        ph = ", ".join(["%s"] * len(suc_ids))
        parts.append(f"{table_alias}.CodSucursal IN ({ph})")
        params.extend(suc_ids)
    if pv_ids:
        ph = ", ".join(["%s"] * len(pv_ids))
        parts.append(f"{table_alias}.id_pv IN ({ph})")
        params.extend(pv_ids)
    if not parts:
        return "", []
    return " AND " + " AND ".join(parts), params


def _fmt_fecha_ddmmaaaa(value: Any) -> str:
    """Fecha a dd/MM/yyyy (español); '-' si vacía/nula."""
    if value is None or value == "":
        return "-"
    if isinstance(value, (datetime, date)):
        return value.strftime("%d/%m/%Y")
    iso = to_date_or_none(value)
    if not iso:
        return "-"
    try:
        return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return "-"


def _orden_fecha(value: Any) -> str:
    """Clave de orden ISO; los clientes sin compra van al final."""
    if value is None or value == "":
        return _ORDEN_SIN_COMPRA
    if isinstance(value, (datetime, date)):
        return value.strftime("%Y-%m-%d")
    return to_date_or_none(value) or _ORDEN_SIN_COMPRA


def listado_vendedores_seleccion(
    base_empresa: str,
    *,
    cod_viajantes: Optional[Sequence[int]] = None,
) -> List[Dict[str, str]]:
    """
    Lista de vendedores (viajantes activos) para el filtro, como ``[{label, value}]``.

    ``cod_viajantes``: si es una lista no vacía, restringe a esos códigos (permisos
    operativos/supervisor resueltos por la vista); ``None``/vacía = todos (gerencial).
    """
    sql = (
        "SELECT viajantes.CodViajante AS valor, "
        "CONCAT(viajantes.Nombre, ' (cod:', viajantes.CodViajante, ')') AS texto "
        "FROM viajantes WHERE viajantes.Anulado = 'No'"
    )
    params: List[Any] = []
    if cod_viajantes:
        frag, ids = _clausula_in("viajantes.CodViajante", cod_viajantes)
        sql += frag
        params.extend(ids)
    sql += " ORDER BY viajantes.Nombre ASC"

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    salida: List[Dict[str, str]] = []
    for valor, texto in rows:
        texto_s = str_or_default(texto, "")
        salida.append({"label": texto_s, "value": f"{valor}|{texto_s}"})
    return salida


def get_clientes_sin_ventas(
    base_empresa: str,
    *,
    fecha_desde: Any,
    fecha_hasta: Any,
    cod_viajantes: Optional[Sequence[int]] = None,
    sucursales: Optional[Sequence[int]] = None,
    puntos_venta: Optional[Sequence[int]] = None,
    usa_id_manual: bool = False,
    incluir_domicilio: bool = False,
) -> Dict[str, Any]:
    """
    Devuelve el informe de clientes sin ventas en el período.

    ``cod_viajantes``: lista no vacía = restringe a esos ``CodViajante``; ``None``/vacía
    = sin restricción (gerencial). La vista relay resuelve permisos y anti-bypass.
    """
    desde = to_date_or_none(fecha_desde)
    hasta = to_date_or_none(fecha_hasta)
    if not desde or not hasta:
        raise ValueError("fecha_desde y fecha_hasta son obligatorias (YYYY-MM-DD).")

    campo_id = (
        "COALESCE(NULLIF(cliente.id_manual_cli, ''), cliente.Codigo)"
        if usa_id_manual
        else "cliente.Codigo"
    )
    campo_domicilio = ""
    if incluir_domicilio:
        campo_domicilio = (
            "(SELECT CONCAT(cd.Calle, ' ', cd.NroCalle) FROM cliente_domicilio AS cd "
            "WHERE cd.id_cliente = cliente.Codigo "
            "ORDER BY cd.id_cliente_domicilio DESC LIMIT 1) AS DomicilioSimple, "
        )

    where_vendedor = ""
    where_params: List[Any] = []
    if cod_viajantes:
        frag, ids = _clausula_in("cliente.CodViajante", cod_viajantes)
        where_vendedor = frag
        where_params = ids

    scope_on, scope_params = _cc_periodo_scope_on_clause(
        table_alias="cc_periodo",
        sucursales=sucursales,
        puntos_venta=puntos_venta,
    )
    ultima_scope_on, ultima_scope_params = _cc_periodo_scope_on_clause(
        table_alias="cc2",
        sucursales=sucursales,
        puntos_venta=puntos_venta,
    )

    sql = f"""
        SELECT
            viajantes.CodViajante,
            COALESCE(viajantes.Nombre, '(sin vendedor)') AS NombreViajante,
            cliente.Codigo,
            cliente.id_manual_cli AS IdManual,
            cliente.Nombre_cliente,
            {campo_id} AS CodigoDisplay,
            {campo_domicilio}
            (
                SELECT MAX(cc2.Fecha)
                FROM cuentacliente AS cc2
                WHERE cc2.Codigo = cliente.Codigo
                  AND cc2.Anulado = 'No'
                  AND cc2.TipoComprobante NOT IN ('NCA','NCB')
                  {ultima_scope_on}
            ) AS UltimaCompra
        FROM cliente
        LEFT JOIN cuentacliente AS cc_periodo
            ON  cc_periodo.Codigo = cliente.Codigo
            AND cc_periodo.Fecha BETWEEN %s AND %s
            AND cc_periodo.TipoComprobante NOT IN ('NCA','NCB')
            AND cc_periodo.Anulado = 'No'
            {scope_on}
        LEFT JOIN viajantes
            ON viajantes.CodViajante = cliente.CodViajante
        WHERE cc_periodo.Codigo IS NULL
          AND cliente.Estado = 'Activo'
          AND cliente.Codigo <> 1
          {where_vendedor}
        GROUP BY cliente.Codigo
        ORDER BY viajantes.Nombre ASC, cliente.Nombre_cliente ASC
    """
    params: List[Any] = [
        *ultima_scope_params,
        desde,
        hasta,
        *scope_params,
        *where_params,
    ]

    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        colnames = [d[0] for d in cursor.description] if cursor.description else []

        datos = _armar_filas(rows, colnames, incluir_domicilio)

        resumen_vendedores, resumen_global = _resumen_por_vendedor(
            cursor,
            desde,
            hasta,
            where_vendedor,
            where_params,
            sucursales=sucursales,
            puntos_venta=puntos_venta,
        )

    modo_todos = len(resumen_vendedores) > 1
    total = len(datos)
    totales = [f"Total: {total}", "", "", ""]

    return {
        "columns": COLUMNS,
        "datos": datos,
        "datosFormateado": datos,
        "totales": totales,
        "totalesFormateado": totales,
        "resumenVendedores": resumen_vendedores,
        "resumenGlobal": resumen_global,
        "modoTodosVendedores": modo_todos,
    }


def _armar_filas(
    rows: Sequence[Sequence[Any]],
    colnames: Sequence[str],
    incluir_domicilio: bool,
) -> List[Dict[str, Any]]:
    datos: List[Dict[str, Any]] = []
    for row in rows:
        item = dict(zip(colnames, row))
        cod_viaj = to_int_or_none(item.get("CodViajante"))
        nombre_viaj = str_or_default(item.get("NombreViajante"), "(sin vendedor)")
        vendedor_label = f"{nombre_viaj} (Cod: {cod_viaj if cod_viaj is not None else '-'})"
        nombre_cliente = str_or_default(item.get("Nombre_cliente"), "-")
        if incluir_domicilio:
            dom = str_or_default(item.get("DomicilioSimple"), "")
            if dom:
                nombre_cliente = f"{nombre_cliente} | {dom}"
        ultima = item.get("UltimaCompra")
        datos.append(
            {
                "id": item.get("Codigo"),
                "CodViajante": cod_viaj,
                "NombreViajante": nombre_viaj,
                "VendedorLabel": vendedor_label,
                "CodigoDisplay": str_or_default(item.get("CodigoDisplay"), "-"),
                "Nombre_cliente": nombre_cliente,
                "UltimaCompra": _fmt_fecha_ddmmaaaa(ultima),
                "UltimaCompraOrden": _orden_fecha(ultima),
            }
        )
    return datos


def _resumen_por_vendedor(
    cursor: Any,
    desde: str,
    hasta: str,
    where_vendedor: str,
    where_params: Sequence[Any],
    *,
    sucursales: Optional[Sequence[int]] = None,
    puntos_venta: Optional[Sequence[int]] = None,
) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    scope_on, scope_params = _cc_periodo_scope_on_clause(
        table_alias="cc_periodo",
        sucursales=sucursales,
        puntos_venta=puntos_venta,
    )
    sql_resumen = f"""
        SELECT
            viajantes.CodViajante,
            COALESCE(viajantes.Nombre, '(sin vendedor)') AS NombreViajante,
            COUNT(DISTINCT cliente.Codigo) AS total_clientes,
            COUNT(DISTINCT CASE WHEN cc_periodo.Codigo IS NULL THEN cliente.Codigo END) AS clientes_no_activos,
            COUNT(DISTINCT CASE WHEN cc_periodo.Codigo IS NOT NULL THEN cliente.Codigo END) AS clientes_activos
        FROM cliente
        LEFT JOIN cuentacliente AS cc_periodo
            ON  cc_periodo.Codigo = cliente.Codigo
            AND cc_periodo.Fecha BETWEEN %s AND %s
            AND cc_periodo.TipoComprobante NOT IN ('NCA','NCB')
            AND cc_periodo.Anulado = 'No'
            {scope_on}
        LEFT JOIN viajantes
            ON viajantes.CodViajante = cliente.CodViajante
        WHERE cliente.Estado = 'Activo'
          AND cliente.Codigo <> 1
          {where_vendedor}
        GROUP BY viajantes.CodViajante, viajantes.Nombre
        ORDER BY viajantes.Nombre ASC
    """
    cursor.execute(sql_resumen, [desde, hasta, *scope_params, *where_params])
    filas = cursor.fetchall()

    resumen: List[Dict[str, Any]] = []
    total_g = activos_g = no_activos_g = 0
    for cod, nombre, total, no_activos, activos in filas:
        cod_i = to_int_or_none(cod) or 0
        nombre_s = str_or_default(nombre, "(sin vendedor)")
        total_i = to_int_or_none(total) or 0
        activos_i = to_int_or_none(activos) or 0
        no_activos_i = to_int_or_none(no_activos) or 0
        resumen.append(
            {
                "CodViajante": cod_i,
                "VendedorLabel": f"{nombre_s} (Cod: {cod_i})",
                "total": total_i,
                "activos": activos_i,
                "noActivos": no_activos_i,
            }
        )
        total_g += total_i
        activos_g += activos_i
        no_activos_g += no_activos_i

    return resumen, {"total": total_g, "activos": activos_g, "noActivos": no_activos_g}
