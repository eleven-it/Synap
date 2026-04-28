"""
Resumen de consumos por artículo (paridad ``relay-consumos-resumen.php`` v1.1).

Agregación ``stock`` por cliente y ventana de fechas. Precios con motor de reglas/promociones
(``price_rules_engine``) y cálculo base Decimal (``price_calculator``).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import to_date_or_none, to_decimal_or_none, to_int_or_none

from ecom.services.price_calculator import ListaPrecioInvalidaError, calcular_precio, validar_lista_precio
from ecom.services.price_rules_engine import (
    calcular_precio_con_motor,
    resolver_promocion_articulo,
    resolver_regla_precio,
)


def _json_safe_row(item: Dict[str, Any]) -> Dict[str, Any]:
    for k, v in list(item.items()):
        if isinstance(v, Decimal):
            item[k] = float(v)
        elif isinstance(v, (date, datetime)):
            item[k] = v.isoformat()
        elif isinstance(v, bytes):
            item[k] = v.decode("utf-8", errors="replace")
    return item


def _lista_precio_texto_a_id(texto: Optional[str]) -> int:
    """Mapea ``Lista 1`` … ``Lista 5`` y ``Lista Oficial`` → id 1..6 (``price_calculator``)."""
    t = str_or_empty_lista(texto)
    key = t.replace(" ", "").lower()
    if key == "listaoficial":
        return 6
    for i in range(1, 6):
        if key == f"lista{i}":
            return i
    return 1


def str_or_empty_lista(texto: Optional[str]) -> str:
    s = str(texto or "").strip()
    return s if s else "Lista 1"


def _precio_neto_segun_lista(row: Dict[str, Any], lista_id: int) -> Decimal:
    cols = {
        1: "Precio1V",
        2: "Precio2V",
        3: "Precio3V",
        4: "Precio4V",
        5: "Precio5V",
        6: "PNOficial",
    }
    col = cols.get(lista_id, "Precio1V")
    return to_decimal_or_none(row.get(col)) or Decimal("0")


def _tipo_cliente_opcional(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def leer_lista_desc_tipo_cliente(base_empresa: str, codigo_cliente: int) -> Tuple[str, Decimal, Optional[str]]:
    """Lista de precios, descuento renglón y tipo cliente desde ``cliente``."""
    sql = """
        SELECT
            cliente.ListaPrecio AS listaPrecio,
            cliente.descuento_por_cli AS descRenglon,
            cliente.TipoCliente AS TipoCliente
        FROM cliente
        WHERE cliente.Codigo = %s
        LIMIT 1
    """
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [codigo_cliente])
        row = cursor.fetchone()
        if not row:
            return "Lista 1", Decimal("0"), None
        lista = str_or_empty_lista(row[0])
        desc = to_decimal_or_none(row[1]) or Decimal("0")
        tipo = _tipo_cliente_opcional(row[2])
        return lista, desc, tipo


def listar_consumos_resumen_relay(
    base_empresa: str,
    codigo_cliente: int,
    *,
    lista_precio_cliente: Optional[str] = None,
    descuento_renglon: Optional[Decimal] = None,
    tipo_cliente: Any = None,
    iva_incluido_sesion: str = "no",
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    limit: int = 20,
) -> Tuple[List[Dict[str, Any]], str]:
    """
    Devuelve ``(filas, advertencia_precios_v1)``.

    Si ``lista_precio_cliente`` es None, se lee de MySQL junto con descuento y tipo.
    """
    fd = to_date_or_none(fecha_desde)
    fh = to_date_or_none(fecha_hasta)
    if not fh:
        fh = date.today().isoformat()
    if not fd:
        hasta_d = date.fromisoformat(fh)
        fd = (hasta_d - timedelta(days=365)).isoformat()

    lim = max(1, min(int(to_int_or_none(limit) or 20), 100))

    lp_db, dr_db, tc_db = leer_lista_desc_tipo_cliente(base_empresa, codigo_cliente)
    lista_txt = str_or_empty_lista(lista_precio_cliente) if lista_precio_cliente is not None else lp_db
    desc = descuento_renglon if descuento_renglon is not None else dr_db
    if tipo_cliente is not None:
        tipo_eff = _tipo_cliente_opcional(tipo_cliente)
    else:
        tipo_eff = tc_db

    lista_id = _lista_precio_texto_a_id(lista_txt)
    try:
        validar_lista_precio(lista_id)
    except ListaPrecioInvalidaError:
        lista_id = 1

    iva_incl = str(iva_incluido_sesion or "no").strip().lower()
    incluir_iva = iva_incl not in ("no", "n", "0", "false")

    sql = """
        SELECT
            agg.IDArt AS IDArt,
            agg.Cuantos AS Cuantos,
            articulo.id_manual AS id_manual,
            articulo.NombreArticulo AS NombreArticulo,
            marca.NombreMarca AS Marca,
            modelo.NombreModelo AS Modelo,
            rubro.NombreRubro AS NombRub,
            subrubro.NombreSubRubro AS NombSubRub,
            articulo.Precio1V AS Precio1V,
            articulo.Precio2V AS Precio2V,
            articulo.Precio3V AS Precio3V,
            articulo.Precio4V AS Precio4V,
            articulo.Precio5V AS Precio5V,
            articulo.PNOficial AS PNOficial,
            iva.Alicuota AS Alic,
            articulo.impuesto_interno AS impuesto_interno,
            articulo.CodigoProveedor AS CodigoProveedor,
            articulo.CodigoRubro AS CodigoRubro,
            articulo.IDSubRubro AS IDSubRubro,
            articulo.promocion AS promocion,
            articulo.promocion_tipo AS promocion_tipo,
            articulo.promocion_por AS promocion_por,
            articulo.promocion_cant AS promocion_cant,
            articulo.promocion_vigencia_desde AS promocion_vigencia_desde,
            articulo.promocion_vigencia_hasta AS promocion_vigencia_hasta,
            articulo.promocion_listaoficial AS promocion_listaoficial,
            articulo.promocion_lista1 AS promocion_lista1,
            articulo.promocion_lista2 AS promocion_lista2,
            articulo.promocion_lista3 AS promocion_lista3,
            articulo.promocion_lista4 AS promocion_lista4,
            articulo.promocion_lista5 AS promocion_lista5
        FROM (
            SELECT stock.IDArt AS IDArt, SUM(stock.Cantidad) AS Cuantos
            FROM stock
            INNER JOIN articulo ON articulo.IDArt = stock.IDArt
            WHERE stock.CodigoCP = %s
              AND stock.Fecha BETWEEN %s AND %s
              AND articulo.Discontinuo = 'No'
              AND articulo.tipo_art = 'Articulo'
            GROUP BY stock.IDArt
        ) AS agg
        INNER JOIN articulo ON articulo.IDArt = agg.IDArt
        LEFT JOIN iva ON articulo.Alicuota = iva.id
        LEFT JOIN subrubro ON subrubro.IdSubRubro = articulo.IdSubRubro
        LEFT JOIN rubro ON rubro.CodigoRubro = articulo.CodigoRubro
        LEFT JOIN modelo ON modelo.CodModelo = articulo.CodigoModelo
        LEFT JOIN marca ON marca.CodMarca = modelo.CodMarca
        ORDER BY agg.Cuantos DESC
        LIMIT %s
    """

    advertencia = "Paridad de precios v1.1 activa (reglas + promociones + redondeo Decimal)."

    pool = get_mysql_pool()
    out: List[Dict[str, Any]] = []
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        cursor.execute(sql, [codigo_cliente, fd, fh, lim])
        cols = [d[0] for d in cursor.description] if cursor.description else []
        for row in cursor.fetchall():
            raw = dict(zip(cols, row))
            precio_base = _precio_neto_segun_lista(raw, lista_id)
            alic = to_decimal_or_none(raw.get("Alic")) or Decimal("21")
            imp_int = to_decimal_or_none(raw.get("impuesto_interno")) or Decimal("0")

            neto_con_desc = calcular_precio(
                precio_base,
                lista_id,
                desc,
                incluir_iva=False,
                alicuota_iva=alic,
                impuesto_interno_pct=imp_int,
                tipo_cliente=tipo_eff,
            )
            regla = resolver_regla_precio(conn, raw, codigo_cliente)
            promo = None if regla is not None else resolver_promocion_articulo(raw, lista_id)
            precio_final = calcular_precio_con_motor(
                precio_base=precio_base,
                lista_id=lista_id,
                descuento_cliente=desc,
                alicuota_iva=alic,
                impuesto_interno_pct=imp_int,
                incluir_iva=incluir_iva,
                tipo_cliente=tipo_eff,
                regla=regla,
                promo=promo,
            )

            fila = {
                "IDArt": raw.get("IDArt"),
                "id_manual": raw.get("id_manual"),
                "Cuantos": raw.get("Cuantos"),
                "NombreArticulo": raw.get("NombreArticulo"),
                "Marca": raw.get("Marca"),
                "Modelo": raw.get("Modelo"),
                "NombRub": raw.get("NombRub"),
                "NombSubRub": raw.get("NombSubRub"),
                "lista_precio_aplicada": lista_txt,
                "precio_neto_con_descuento": float(neto_con_desc),
                "precio_mostrado": float(precio_final),
                "iva_incluido_en_precio_mostrado": incluir_iva,
                "regla_aplicada": (regla.tipo_calculo if regla is not None else None),
                "promo_aplicada": (promo.promo_tipo if promo is not None else None),
            }
            out.append(_json_safe_row(fila))

    return out, advertencia
