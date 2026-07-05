"""
Servicio de catálogo de productos mayorista (listado paginado + ficha de detalle).

Fase P0: solo lectura, con precio calculado vía price_rules_engine y stock disponible
vía self_checkout.StockService.
"""

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none, str_or_default
from ecom.services.price_rules_engine import calcular_precio_articulo_row
from self_checkout.services.stock_service import StockService


def _d(v: Any, default: str = "0") -> Decimal:
    return to_decimal_or_none(v) or Decimal(default)


def _i(v: Any, default: int = 0) -> int:
    val = to_int_or_none(v)
    return val if val is not None else default


def _s(v: Any, default: str = "") -> str:
    return str_or_default(v, default)


_SELECT_LISTADO_COLS = """
    articulo.IDArt,
    articulo.id_manual,
    articulo.CodigoArticuloT,
    articulo.NombreArticulo,
    articulo.Precio1V,
    articulo.Precio2V,
    articulo.Precio3V,
    articulo.Precio4V,
    articulo.Precio5V,
    articulo.PNOficial,
    articulo.impuesto_interno,
    articulo.CodigoProveedor,
    articulo.CodigoRubro,
    articulo.IDSubRubro,
    articulo.promocion,
    articulo.promocion_por,
    articulo.promocion_cant,
    articulo.promocion_tipo,
    articulo.promocion_alcance,
    articulo.promocion_lista1,
    articulo.promocion_lista2,
    articulo.promocion_lista3,
    articulo.promocion_lista4,
    articulo.promocion_lista5,
    articulo.promocion_listaoficial,
    articulo.promocion_vigencia_desde,
    articulo.promocion_vigencia_hasta,
    iva.Alicuota AS alic_iva,
    rubro.NombreRubro,
    subrubro.NombreSubRubro,
    marca.NombreMarca
"""

_FROM_JOINS_LISTADO = """
    FROM articulo
    LEFT JOIN iva ON iva.ID = articulo.Alicuota
    LEFT JOIN rubro ON rubro.CodigoRubro = articulo.CodigoRubro
    LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSubRubro
    LEFT JOIN marca ON marca.CodMarca = articulo.CodigoMarca
"""


def _construir_where_catalogo(filtros: Dict[str, Any]) -> tuple:
    """Construye el WHERE parametrizado del catálogo ecommerce (compartido listado/export)."""
    where_clauses = ["articulo.Discontinuo = 'No'", "articulo.ecommerce = 'Si'"]
    params: List[Any] = []

    if filtros.get("rubro") is not None:
        where_clauses.append("articulo.CodigoRubro = %s")
        params.append(to_int_or_none(filtros["rubro"]))

    if filtros.get("subrubro") is not None:
        where_clauses.append("articulo.IDSubRubro = %s")
        params.append(to_int_or_none(filtros["subrubro"]))

    if filtros.get("marca") is not None:
        where_clauses.append("articulo.CodigoMarca = %s")
        params.append(to_int_or_none(filtros["marca"]))

    if filtros.get("laboratorio") is not None:
        where_clauses.append("articulo.CodLaboratorio = %s")
        params.append(to_int_or_none(filtros["laboratorio"]))

    if filtros.get("proveedor") is not None:
        where_clauses.append("articulo.CodigoProveedor = %s")
        params.append(to_int_or_none(filtros["proveedor"]))

    if filtros.get("solo_promocion"):
        where_clauses.append("articulo.promocion = 'Si'")

    if filtros.get("q"):
        q_term = f"%{filtros['q']}%"
        where_clauses.append(
            "(articulo.NombreArticulo LIKE %s OR articulo.CodigoArticuloT LIKE %s OR articulo.id_manual LIKE %s)"
        )
        params.extend([q_term, q_term, q_term])

    # Restricciones de catálogo por punto de venta (excluir artículos/rubros/subrubros).
    for clave, columna in (
        ("excluir_articulos", "articulo.IDArt"),
        ("excluir_rubros", "articulo.CodigoRubro"),
        ("excluir_subrubros", "articulo.IDSubRubro"),
    ):
        ids = [i for i in (to_int_or_none(x) for x in (filtros.get(clave) or [])) if i is not None]
        if ids:
            placeholders = ",".join(["%s"] * len(ids))
            where_clauses.append(f"{columna} NOT IN ({placeholders})")
            params.extend(ids)

    return " AND ".join(where_clauses), params


def contar_articulos_catalogo(
    base_empresa: str,
    *,
    filtros: Optional[Dict[str, Any]] = None,
    conn: Any = None,
) -> int:
    """Cuenta artículos del catálogo para un conjunto de filtros (guardrail de export)."""
    where_sql, params = _construir_where_catalogo(filtros or {})
    sql = f"SELECT COUNT(*) FROM articulo WHERE {where_sql}"
    pool = get_mysql_pool()
    use_external = conn is not None
    if not use_external:
        conn = pool.get_connection(base_empresa)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        return _i(cur.fetchone()[0], 0)
    finally:
        if not use_external:
            conn.close()


def obtener_filas_catalogo(
    base_empresa: str,
    *,
    filtros: Optional[Dict[str, Any]] = None,
    conn: Any = None,
) -> List[Dict[str, Any]]:
    """
    Trae TODAS las filas del catálogo (sin paginar) para el export de lista de precios.
    Ordena por rubro/subrubro/nombre (paridad legacy). Devuelve dicts crudos (sin precio).
    """
    where_sql, params = _construir_where_catalogo(filtros or {})
    sql = f"""
        SELECT {_SELECT_LISTADO_COLS}
        {_FROM_JOINS_LISTADO}
        WHERE {where_sql}
        ORDER BY rubro.NombreRubro, subrubro.NombreSubRubro, articulo.NombreArticulo
    """
    pool = get_mysql_pool()
    use_external = conn is not None
    if not use_external:
        conn = pool.get_connection(base_empresa)
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, row)) for row in cur.fetchall()]
    finally:
        if not use_external:
            conn.close()


def listar_articulos_paginado(
    base_empresa: str,
    *,
    filtros: Optional[Dict[str, Any]] = None,
    lista_id: int,
    codigo_cliente: Optional[int],
    descuento_cliente: Decimal,
    iva_incluido: bool,
    id_deposito: int,
    pagina: int = 1,
    tam: int = 20,
    conn: Any = None,
) -> Dict[str, Any]:
    """
    Listado paginado de artículos del catálogo ecommerce con precio calculado y stock disponible.

    Args:
        base_empresa: Base de datos de la empresa.
        filtros: Dict con filtros opcionales (rubro, subrubro, marca, laboratorio, proveedor, q, solo_promocion).
        lista_id: ID de lista de precios (1..5 o 6).
        codigo_cliente: ID del cliente (None si no hay cliente).
        descuento_cliente: Descuento de renglón/cliente (%).
        iva_incluido: Si True, precio con IVA; si False, neto.
        id_deposito: ID del depósito activo para stock.
        pagina: Página solicitada (1-indexed).
        tam: Tamaño de página (máx 100).
        conn: Conexión MySQL opcional (se crea una si no se provee).

    Returns:
        {items: [...], total, pagina, tam, total_paginas}
    """
    filtros = filtros or {}
    tam = min(max(1, tam), 100)
    pagina = max(1, pagina)
    offset = (pagina - 1) * tam

    where_sql, params = _construir_where_catalogo(filtros)

    sql_count = f"""
        SELECT COUNT(*)
        FROM articulo
        WHERE {where_sql}
    """

    sql_items = f"""
        SELECT {_SELECT_LISTADO_COLS}
        {_FROM_JOINS_LISTADO}
        WHERE {where_sql}
        ORDER BY articulo.NombreArticulo
        LIMIT %s OFFSET %s
    """

    pool = get_mysql_pool()
    use_external_conn = conn is not None

    if not use_external_conn:
        conn = pool.get_connection(base_empresa)

    try:
        cur = conn.cursor()
        cur.execute(sql_count, params)
        total = _i(cur.fetchone()[0], 0)

        cur.execute(sql_items, params + [tam, offset])
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()

        ids_articulos = [_i(row[cols.index("IDArt")], 0) for row in rows]
        stock_map = {}
        if ids_articulos:
            stock_service = StockService(base_empresa)
            stock_map = stock_service.get_disponible_map(ids_articulos, id_deposito)

        items = []
        for row in rows:
            art_dict = dict(zip(cols, row))
            id_art = _i(art_dict.get("IDArt"), 0)

            precio = calcular_precio_articulo_row(
                art_dict,
                lista_id=lista_id,
                codigo_cliente=codigo_cliente,
                descuento_cliente=descuento_cliente,
                iva_incluido=iva_incluido,
                conn=conn,
            )

            items.append(
                {
                    "id_articulo": id_art,
                    "id_manual": _s(art_dict.get("id_manual"), ""),
                    "codigo": _s(art_dict.get("CodigoArticuloT"), ""),
                    "nombre": _s(art_dict.get("NombreArticulo"), ""),
                    "rubro": _s(art_dict.get("NombreRubro"), ""),
                    "subrubro": _s(art_dict.get("NombreSubRubro"), ""),
                    "marca": _s(art_dict.get("NombreMarca"), ""),
                    "precio": float(precio),
                    "stock_disponible": float(stock_map.get(id_art, Decimal("0"))),
                    "tiene_foto": False,
                    "en_promocion": _s(art_dict.get("promocion"), "No").strip().lower() == "si",
                }
            )

        total_paginas = math.ceil(total / tam) if tam > 0 else 0

        return {
            "items": items,
            "total": total,
            "pagina": pagina,
            "tam": tam,
            "total_paginas": total_paginas,
        }
    finally:
        if not use_external_conn:
            conn.close()


_COLUMNAS_PRECIO_ARTICULO = """
    articulo.IDArt,
    articulo.id_manual,
    articulo.CodigoArticuloT,
    articulo.NombreArticulo,
    articulo.Precio1V,
    articulo.Precio2V,
    articulo.Precio3V,
    articulo.Precio4V,
    articulo.Precio5V,
    articulo.PNOficial,
    articulo.impuesto_interno,
    articulo.CodigoProveedor,
    articulo.CodigoRubro,
    articulo.IDSubRubro,
    articulo.promocion,
    articulo.promocion_por,
    articulo.promocion_cant,
    articulo.promocion_tipo,
    articulo.promocion_alcance,
    articulo.promocion_lista1,
    articulo.promocion_lista2,
    articulo.promocion_lista3,
    articulo.promocion_lista4,
    articulo.promocion_lista5,
    articulo.promocion_listaoficial,
    articulo.promocion_vigencia_desde,
    articulo.promocion_vigencia_hasta,
    iva.Alicuota AS alic_iva
"""


def obtener_articulo_row_precio(
    base_empresa: str,
    idart: int,
    *,
    conn: Any = None,
) -> Optional[Dict[str, Any]]:
    """
    Devuelve la fila cruda del artículo con las columnas necesarias para calcular precio
    (Precio1V..Precio5V, PNOficial, alic_iva, impuesto_interno, promo, claves de regla).

    Fuente única para que el carrito (P1) y el checkout (P2) precien con el mismo motor.
    Devuelve None si el artículo no existe o no está activo en el catálogo ecommerce.
    """
    sql = f"""
        SELECT {_COLUMNAS_PRECIO_ARTICULO}
        FROM articulo
        LEFT JOIN iva ON iva.ID = articulo.Alicuota
        WHERE articulo.Discontinuo = 'No'
          AND articulo.ecommerce = 'Si'
          AND articulo.IDArt = %s
        LIMIT 1
    """
    pool = get_mysql_pool()
    use_external_conn = conn is not None
    if not use_external_conn:
        conn = pool.get_connection(base_empresa)
    try:
        cur = conn.cursor()
        cur.execute(sql, [idart])
        cols = [d[0] for d in cur.description] if cur.description else []
        row = cur.fetchone()
        if not row:
            return None
        return dict(zip(cols, row))
    finally:
        if not use_external_conn:
            conn.close()


def resolver_precio_articulo(
    base_empresa: str,
    id_articulo: int,
    *,
    lista_id: int,
    codigo_cliente: Optional[int],
    descuento_cliente: Decimal,
    iva_incluido: bool = False,
    conn: Any = None,
) -> Optional[tuple]:
    """
    Resuelve (precio, row) para un artículo con el motor único, usando una sola conexión.

    Fuente única de precio para carrito (P1) y checkout (P2): garantiza paridad con el
    listado/ficha del catálogo (P0). Devuelve None si el artículo no existe/está inactivo.
    """
    pool = get_mysql_pool()
    use_external_conn = conn is not None
    if not use_external_conn:
        conn = pool.get_connection(base_empresa)
    try:
        row = obtener_articulo_row_precio(base_empresa, id_articulo, conn=conn)
        if row is None:
            return None
        precio = calcular_precio_articulo_row(
            row,
            lista_id=lista_id,
            codigo_cliente=codigo_cliente,
            descuento_cliente=descuento_cliente,
            iva_incluido=iva_incluido,
            conn=conn,
        )
        return precio, row
    finally:
        if not use_external_conn:
            conn.close()


def obtener_detalle_articulo(
    base_empresa: str,
    *,
    idart: Optional[int] = None,
    codigo: Optional[str] = None,
    lista_id: int,
    codigo_cliente: Optional[int],
    descuento_cliente: Decimal,
    iva_incluido: bool,
    id_deposito: int,
    conn: Any = None,
) -> Optional[Dict[str, Any]]:
    """
    Obtiene la ficha de detalle de un artículo (por IDArt o código).

    Args:
        base_empresa: Base de datos de la empresa.
        idart: ID del artículo (IDArt).
        codigo: Código del artículo (CodigoArticuloT o id_manual).
        lista_id: ID de lista de precios (1..5 o 6).
        codigo_cliente: ID del cliente (None si no hay cliente).
        descuento_cliente: Descuento de renglón/cliente (%).
        iva_incluido: Si True, precio con IVA; si False, neto.
        id_deposito: ID del depósito activo.
        conn: Conexión MySQL opcional.

    Returns:
        Dict con datos del artículo o None si no existe/inactivo.
    """
    if idart is None and codigo is None:
        return None

    where_clause = "articulo.Discontinuo = 'No' AND articulo.ecommerce = 'Si'"
    params: List[Any] = []

    if idart is not None:
        where_clause += " AND articulo.IDArt = %s"
        params.append(idart)
    elif codigo is not None:
        where_clause += " AND (articulo.CodigoArticuloT = %s OR articulo.id_manual = %s)"
        params.extend([codigo, codigo])

    sql = f"""
        SELECT
            articulo.IDArt,
            articulo.id_manual,
            articulo.CodigoArticuloT,
            articulo.NombreArticulo,
            articulo.Detalle,
            articulo.detalle_web,
            articulo.Precio1V,
            articulo.Precio2V,
            articulo.Precio3V,
            articulo.Precio4V,
            articulo.Precio5V,
            articulo.PNOficial,
            articulo.impuesto_interno,
            articulo.CodigoProveedor,
            articulo.CodigoRubro,
            articulo.IDSubRubro,
            articulo.promocion,
            articulo.promocion_por,
            articulo.promocion_cant,
            articulo.promocion_tipo,
            articulo.promocion_alcance,
            articulo.promocion_lista1,
            articulo.promocion_lista2,
            articulo.promocion_lista3,
            articulo.promocion_lista4,
            articulo.promocion_lista5,
            articulo.promocion_listaoficial,
            articulo.promocion_vigencia_desde,
            articulo.promocion_vigencia_hasta,
            iva.Alicuota AS alic_iva,
            rubro.NombreRubro,
            subrubro.NombreSubRubro,
            marca.NombreMarca
        FROM articulo
        LEFT JOIN iva ON iva.ID = articulo.Alicuota
        LEFT JOIN rubro ON rubro.CodigoRubro = articulo.CodigoRubro
        LEFT JOIN subrubro ON subrubro.IDSubRubro = articulo.IDSubRubro
        LEFT JOIN marca ON marca.CodMarca = articulo.CodigoMarca
        WHERE {where_clause}
        LIMIT 1
    """

    pool = get_mysql_pool()
    use_external_conn = conn is not None

    if not use_external_conn:
        conn = pool.get_connection(base_empresa)

    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        row = cur.fetchone()

        if not row:
            return None

        art_dict = dict(zip(cols, row))
        id_art = _i(art_dict.get("IDArt"), 0)

        precio = calcular_precio_articulo_row(
            art_dict,
            lista_id=lista_id,
            codigo_cliente=codigo_cliente,
            descuento_cliente=descuento_cliente,
            iva_incluido=iva_incluido,
            conn=conn,
        )

        precio_neto = calcular_precio_articulo_row(
            art_dict,
            lista_id=lista_id,
            codigo_cliente=codigo_cliente,
            descuento_cliente=descuento_cliente,
            iva_incluido=False,
            conn=conn,
        )

        stock_service = StockService(base_empresa)
        stock_disponible = stock_service.get_disponible(id_art, id_deposito)

        sql_stock_depositos = """
            SELECT
                sd.id_deposito,
                d.NombreDeposito AS nombre_deposito,
                COALESCE(sd.saldo, 0) AS saldo,
                COALESCE(sd.saldo_pedido_cliente, 0) AS saldo_pedido_cliente
            FROM stock_deposito sd
            LEFT JOIN deposito d ON d.CodDeposito = sd.id_deposito
            WHERE sd.id_articulo = %s
        """
        cur.execute(sql_stock_depositos, [id_art])
        stock_depositos = []
        for sd_row in cur.fetchall():
            saldo = _d(sd_row[2], "0")
            reservado = _d(sd_row[3], "0")
            disponible = max(Decimal("0"), saldo - reservado)
            stock_depositos.append(
                {
                    "id_deposito": _i(sd_row[0], 0),
                    "nombre_deposito": _s(sd_row[1], ""),
                    "saldo": float(saldo),
                    "saldo_pedido": float(reservado),
                    "disponible": float(disponible),
                }
            )

        promo_data = None
        if _s(art_dict.get("promocion"), "No").strip().lower() == "si":
            promo_data = {
                "tipo": _s(art_dict.get("promocion_tipo"), ""),
                "por": float(_d(art_dict.get("promocion_por"), "0")),
                "cant": _i(art_dict.get("promocion_cant"), 0),
                "alcance": _s(art_dict.get("promocion_alcance"), ""),
                "vigencia_desde": str(art_dict.get("promocion_vigencia_desde") or ""),
                "vigencia_hasta": str(art_dict.get("promocion_vigencia_hasta") or ""),
            }

        return {
            "id_articulo": id_art,
            "id_manual": _s(art_dict.get("id_manual"), ""),
            "codigo": _s(art_dict.get("CodigoArticuloT"), ""),
            "nombre": _s(art_dict.get("NombreArticulo"), ""),
            "descripcion": _s(art_dict.get("detalle_web") or art_dict.get("Detalle"), ""),
            "rubro": _s(art_dict.get("NombreRubro"), ""),
            "subrubro": _s(art_dict.get("NombreSubRubro"), ""),
            "marca": _s(art_dict.get("NombreMarca"), ""),
            "precio": float(precio),
            "precio_neto": float(precio_neto),
            "stock_disponible": float(stock_disponible),
            "stock_depositos": stock_depositos,
            "tiene_foto": False,
            "promocion": promo_data,
        }
    finally:
        if not use_external_conn:
            conn.close()
