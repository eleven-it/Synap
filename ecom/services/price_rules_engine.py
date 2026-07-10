"""
Motor de reglas y promociones para precios mayoristapp.

Objetivo: acercar la paridad con ``util-calculaprecio.inc.php`` en un servicio
usable desde relays sin acoplarlos a lógica SQL procedural.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none
from ecom.services.price_calculator import (
    calcular_neto_desde_monto_fijo_ttc,
    calcular_precio,
    vigencia_promo,
)


@dataclass
class ReglaPrecio:
    tipo_calculo: str
    importe_regla: Decimal
    prioridad_regla: str = "Desc. Cliente"
    promocion_por: Optional[Decimal] = None
    promocion_cant: Optional[int] = None


@dataclass
class PromocionArticulo:
    promo_tipo: str
    promo_por: Decimal
    promo_cant: int


def _d(v: Any, default: str = "0") -> Decimal:
    return to_decimal_or_none(v) or Decimal(default)


def _i(v: Any, default: int = 0) -> int:
    return to_int_or_none(v) if to_int_or_none(v) is not None else default


def _norm(s: Any) -> str:
    raw = str(s or "").strip().lower()
    return raw.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")


def _promo_habilitada_para_lista(art: dict, lista_id: int) -> bool:
    col = {
        1: "promocion_lista1",
        2: "promocion_lista2",
        3: "promocion_lista3",
        4: "promocion_lista4",
        5: "promocion_lista5",
        6: "promocion_listaoficial",
    }.get(lista_id, "promocion_lista1")
    return str(art.get(col) or "No").strip().lower() == "si"


def resolver_promocion_articulo(art: dict, lista_id: int) -> Optional[PromocionArticulo]:
    if str(art.get("promocion") or "No").strip().lower() != "si":
        return None
    if not _promo_habilitada_para_lista(art, lista_id):
        return None
    if not vigencia_promo(art.get("promocion_vigencia_desde"), art.get("promocion_vigencia_hasta")):
        return None
    return PromocionArticulo(
        promo_tipo=str(art.get("promocion_tipo") or "").strip() or "Importe descuento",
        promo_por=_d(art.get("promocion_por"), "0"),
        promo_cant=_i(art.get("promocion_cant"), 0),
    )


def resolver_regla_precio(conn: Any, art: dict, codigo_cliente: int) -> Optional[ReglaPrecio]:
    """Orden: particular -> masiva -> general (aproximación robusta)."""
    id_art = to_int_or_none(art.get("IDArt"))
    cod_prov = to_int_or_none(art.get("CodigoProveedor"))
    cod_rubro = to_int_or_none(art.get("CodigoRubro"))
    id_subr = to_int_or_none(art.get("IDSubRubro"))
    if id_art is None:
        return None

    hoy = date.today().isoformat()
    cur = conn.cursor()

    # 1) Regla particular (reglas_precio)
    cur.execute(
        """
        SELECT tipo_calculo, importe_regla, promocion_por, promocion_cant
        FROM reglas_precio
        WHERE id_articulo = %s
          AND id_cliente = %s
          AND anulado = 'No'
          AND %s BETWEEN vigencia_desde AND vigencia_hasta
        LIMIT 1
        """,
        [id_art, codigo_cliente, hoy],
    )
    r = cur.fetchone()
    if r:
        return ReglaPrecio(
            tipo_calculo=str(r[0] or ""),
            importe_regla=_d(r[1], "0"),
            promocion_por=_d(r[2], "0"),
            promocion_cant=_i(r[3], 0),
        )

    # 2) Reglas masivas (se prioriza mayor especificidad)
    combos = [
        ("id_proveedor = %s AND id_sub_rubro = %s", [cod_prov, id_subr]),
        ("id_proveedor = %s AND id_rubro = %s", [cod_prov, cod_rubro]),
        ("id_proveedor = %s AND id_rubro IS NULL AND id_sub_rubro IS NULL", [cod_prov]),
        ("id_sub_rubro = %s AND id_proveedor IS NULL AND id_rubro IS NULL", [id_subr]),
        ("id_rubro = %s AND id_proveedor IS NULL AND id_sub_rubro IS NULL", [cod_rubro]),
    ]
    for cond, vals in combos:
        if any(v is None for v in vals):
            continue
        cur.execute(
            f"""
            SELECT tipo_calculo, importe_regla, 'Desc. Cliente' AS prioridad_regla
            FROM reglas_precio_masivas
            WHERE anulado = 'No'
              AND id_cliente = %s
              AND %s BETWEEN vigencia_desde AND vigencia_hasta
              AND {cond}
            LIMIT 1
            """,
            [codigo_cliente, hoy, *vals],
        )
        r = cur.fetchone()
        if r:
            return ReglaPrecio(
                tipo_calculo=str(r[0] or ""),
                importe_regla=_d(r[1], "0"),
                prioridad_regla=str(r[2] or "Desc. Cliente"),
            )

    # 3) Reglas generales (alta art)
    combos_gen = [
        ("id_proveedor = %s AND id_sub_rubro = %s", [cod_prov, id_subr]),
        ("id_proveedor = %s AND id_rubro = %s", [cod_prov, cod_rubro]),
        ("id_proveedor = %s AND id_rubro IS NULL AND id_sub_rubro IS NULL", [cod_prov]),
        ("id_sub_rubro = %s AND id_proveedor IS NULL AND id_rubro IS NULL", [id_subr]),
        ("id_rubro = %s AND id_proveedor IS NULL AND id_sub_rubro IS NULL", [cod_rubro]),
    ]
    for cond, vals in combos_gen:
        if any(v is None for v in vals):
            continue
        cur.execute(
            f"""
            SELECT tipo_calculo, importe_regla, COALESCE(prioridad_regla, 'Desc. Cliente')
            FROM reglas_precio_alta_art
            WHERE anulado = 'No'
              AND %s BETWEEN vigencia_desde AND vigencia_hasta
              AND {cond}
            LIMIT 1
            """,
            [hoy, *vals],
        )
        r = cur.fetchone()
        if r:
            return ReglaPrecio(
                tipo_calculo=str(r[0] or ""),
                importe_regla=_d(r[1], "0"),
                prioridad_regla=str(r[2] or "Desc. Cliente"),
            )
    return None


def _resolver_regla_desde_filas_catalogo(art: dict, filas: list) -> Optional[ReglaPrecio]:
    """Aplica el mismo orden de prioridad que resolver_regla_precio (masivas / generales)."""
    cod_prov = to_int_or_none(art.get("CodigoProveedor"))
    cod_rubro = to_int_or_none(art.get("CodigoRubro"))
    id_subr = to_int_or_none(art.get("IDSubRubro"))

    def _coincide(cond_idx: int, fila: dict) -> bool:
        p = to_int_or_none(fila.get("id_proveedor"))
        r = to_int_or_none(fila.get("id_rubro"))
        s = to_int_or_none(fila.get("id_sub_rubro"))
        if cond_idx == 0:
            return cod_prov is not None and id_subr is not None and p == cod_prov and s == id_subr
        if cond_idx == 1:
            return cod_prov is not None and cod_rubro is not None and p == cod_prov and r == cod_rubro
        if cond_idx == 2:
            return cod_prov is not None and p == cod_prov and r is None and s is None
        if cond_idx == 3:
            return id_subr is not None and s == id_subr and p is None and r is None
        if cond_idx == 4:
            return cod_rubro is not None and r == cod_rubro and p is None and s is None
        return False

    for cond_idx in range(5):
        for fila in filas:
            if _coincide(cond_idx, fila):
                return ReglaPrecio(
                    tipo_calculo=str(fila.get("tipo_calculo") or ""),
                    importe_regla=_d(fila.get("importe_regla"), "0"),
                    prioridad_regla=str(fila.get("prioridad_regla") or "Desc. Cliente"),
                )
    return None


def resolver_reglas_precio_map(
    conn: Any,
    articulos: list,
    codigo_cliente: int,
) -> dict[int, ReglaPrecio]:
    """
    Resuelve reglas de precio para un lote de artículos con pocas consultas SQL
    (particular + masivas + generales), en lugar de N×resolver_regla_precio.
    """
    ids_art = [
        i
        for i in (to_int_or_none(a.get("IDArt")) for a in articulos)
        if i is not None
    ]
    if not ids_art:
        return {}

    hoy = date.today().isoformat()
    cur = conn.cursor()
    resultado: dict[int, ReglaPrecio] = {}

    placeholders = ",".join(["%s"] * len(ids_art))
    cur.execute(
        f"""
        SELECT id_articulo, tipo_calculo, importe_regla, promocion_por, promocion_cant
        FROM reglas_precio
        WHERE id_cliente = %s
          AND id_articulo IN ({placeholders})
          AND anulado = 'No'
          AND %s BETWEEN vigencia_desde AND vigencia_hasta
        """,
        [codigo_cliente, *ids_art, hoy],
    )
    for row in cur.fetchall():
        id_a = _i(row[0])
        if id_a not in resultado:
            resultado[id_a] = ReglaPrecio(
                tipo_calculo=str(row[1] or ""),
                importe_regla=_d(row[2], "0"),
                promocion_por=_d(row[3], "0"),
                promocion_cant=_i(row[4], 0),
            )

    pendientes = [a for a in articulos if to_int_or_none(a.get("IDArt")) not in resultado]
    if not pendientes:
        return resultado

    cur.execute(
        """
        SELECT tipo_calculo, importe_regla, id_proveedor, id_rubro, id_sub_rubro
        FROM reglas_precio_masivas
        WHERE id_cliente = %s
          AND anulado = 'No'
          AND %s BETWEEN vigencia_desde AND vigencia_hasta
        """,
        [codigo_cliente, hoy],
    )
    masivas = [
        {
            "tipo_calculo": r[0],
            "importe_regla": r[1],
            "id_proveedor": r[2],
            "id_rubro": r[3],
            "id_sub_rubro": r[4],
            "prioridad_regla": "Desc. Cliente",
        }
        for r in cur.fetchall()
    ]

    cur.execute(
        """
        SELECT tipo_calculo, importe_regla, id_proveedor, id_rubro, id_sub_rubro,
               COALESCE(prioridad_regla, 'Desc. Cliente')
        FROM reglas_precio_alta_art
        WHERE anulado = 'No'
          AND %s BETWEEN vigencia_desde AND vigencia_hasta
        """,
        [hoy],
    )
    generales = [
        {
            "tipo_calculo": r[0],
            "importe_regla": r[1],
            "id_proveedor": r[2],
            "id_rubro": r[3],
            "id_sub_rubro": r[4],
            "prioridad_regla": r[5],
        }
        for r in cur.fetchall()
    ]

    for art in pendientes:
        id_art = to_int_or_none(art.get("IDArt"))
        if id_art is None or id_art in resultado:
            continue
        regla = _resolver_regla_desde_filas_catalogo(art, masivas)
        if regla is None:
            regla = _resolver_regla_desde_filas_catalogo(art, generales)
        if regla is not None:
            resultado[id_art] = regla

    return resultado


def calcular_precio_con_motor(
    *,
    precio_base: Decimal,
    lista_id: int,
    descuento_cliente: Decimal,
    alicuota_iva: Decimal,
    impuesto_interno_pct: Decimal,
    incluir_iva: bool,
    tipo_cliente: Optional[str],
    regla: Optional[ReglaPrecio],
    promo: Optional[PromocionArticulo],
) -> Decimal:
    """Aplica regla/promoción con fallback a cálculo base."""
    if regla is not None:
        tipo = _norm(regla.tipo_calculo)
        if tipo == "descuento":
            return calcular_precio(
                precio_base,
                lista_id,
                descuento_cliente,
                incluir_iva=incluir_iva,
                alicuota_iva=alicuota_iva,
                impuesto_interno_pct=impuesto_interno_pct,
                tipo_cliente=tipo_cliente,
                descuento_regla_pct=regla.importe_regla,
                prioridad_regla=regla.prioridad_regla,
            )
        if tipo == "marcacion":
            factor = Decimal("1") + (regla.importe_regla / Decimal("100"))
            base_marcado = (precio_base * factor).quantize(Decimal("0.01"))
            return calcular_precio(
                base_marcado,
                lista_id,
                Decimal("0"),
                incluir_iva=incluir_iva,
                alicuota_iva=alicuota_iva,
                impuesto_interno_pct=impuesto_interno_pct,
                tipo_cliente=tipo_cliente,
            )
        if tipo == "precio fijo":
            return calcular_precio(
                regla.importe_regla,
                lista_id,
                Decimal("0"),
                incluir_iva=incluir_iva,
                alicuota_iva=alicuota_iva,
                impuesto_interno_pct=impuesto_interno_pct,
                tipo_cliente=tipo_cliente,
            )
        # Cantidad - Unidad u otros: por ahora precio base
        return calcular_precio(
            precio_base,
            lista_id,
            descuento_cliente,
            incluir_iva=incluir_iva,
            alicuota_iva=alicuota_iva,
            impuesto_interno_pct=impuesto_interno_pct,
            tipo_cliente=tipo_cliente,
        )

    if promo is not None:
        tipo_promo = _norm(promo.promo_tipo)
        if tipo_promo == "monto fijo":
            if incluir_iva:
                return calcular_precio(
                    precio_base,
                    lista_id,
                    descuento_cliente,
                    incluir_iva=True,
                    alicuota_iva=alicuota_iva,
                    impuesto_interno_pct=impuesto_interno_pct,
                    tipo_cliente=tipo_cliente,
                    promo_tipo="Monto fijo",
                    promo_porc=promo.promo_por,
                )
            neto_calc, _desc, _ttc = calcular_neto_desde_monto_fijo_ttc(
                precio_base,
                promo.promo_por,
                alicuota_iva,
            )
            return neto_calc.quantize(Decimal("0.01"))
        if tipo_promo == "cantidad - intervalo":
            # En PHP suele no fijar descuento porcentual efectivo en esta etapa.
            return calcular_precio(
                precio_base,
                lista_id,
                descuento_cliente,
                incluir_iva=incluir_iva,
                alicuota_iva=alicuota_iva,
                impuesto_interno_pct=impuesto_interno_pct,
                tipo_cliente=tipo_cliente,
            )
        # Importe descuento / Cantidad / Cantidad - Unidad:
        # aproximación estable: porcentaje promo compite con descuento cliente.
        return calcular_precio(
            precio_base,
            lista_id,
            descuento_cliente,
            incluir_iva=incluir_iva,
            alicuota_iva=alicuota_iva,
            impuesto_interno_pct=impuesto_interno_pct,
            tipo_cliente=tipo_cliente,
            descuento_regla_pct=promo.promo_por,
            prioridad_regla="Desc. Cliente",
        )

    return calcular_precio(
        precio_base,
        lista_id,
        descuento_cliente,
        incluir_iva=incluir_iva,
        alicuota_iva=alicuota_iva,
        impuesto_interno_pct=impuesto_interno_pct,
        tipo_cliente=tipo_cliente,
    )


def calcular_precio_articulo_row(
    art: dict,
    *,
    lista_id: int,
    codigo_cliente: Optional[int],
    descuento_cliente: Decimal,
    iva_incluido: bool,
    conn: Any,
    regla_precio: Optional[ReglaPrecio] = None,
    resolver_regla: bool = True,
) -> Decimal:
    """
    Función integradora para calcular precio de un artículo (fuente única para listado/ficha/carrito).

    Resuelve precio_base desde la columna de lista del row, alícuotas, reglas y promociones,
    y delega en calcular_precio_con_motor para el cálculo final.

    Args:
        art: dict con claves del row de articulo (IDArt, Precio1V..Precio5V, PNOficial, alic_iva,
             impuesto_interno, CodigoProveedor, CodigoRubro, IDSubRubro, promocion, promocion_por, etc.).
        lista_id: ID de lista de precios (1..5 o 6 para Lista Oficial).
        codigo_cliente: ID del cliente (None si no hay cliente en sesión).
        descuento_cliente: Descuento de renglón/cliente (porcentaje 0-100).
        iva_incluido: Si True, devuelve precio con IVA; si False, neto.
        conn: Conexión MySQL para consultar reglas.
        regla_precio: Regla ya resuelta (p. ej. lote TPV); si resolver_regla=False se usa tal cual.
        resolver_regla: Si False, no consulta reglas_precio* (usar con regla_precio precalculada).

    Returns:
        Precio calculado (Decimal).
    """
    col_precio = {
        1: "Precio1V",
        2: "Precio2V",
        3: "Precio3V",
        4: "Precio4V",
        5: "Precio5V",
        6: "PNOficial",
    }.get(lista_id)
    if col_precio is None:
        col_precio = "Precio1V"

    precio_base = _d(art.get(col_precio), "0")
    alicuota_iva = _d(art.get("alic_iva"), "21")
    impuesto_interno_pct = _d(art.get("impuesto_interno"), "0")

    tipo_cliente = None if codigo_cliente is None else "C"

    regla = regla_precio
    if resolver_regla and codigo_cliente is not None and conn is not None:
        try:
            regla = resolver_regla_precio(conn, art, codigo_cliente)
        except Exception:
            pass

    promo = resolver_promocion_articulo(art, lista_id)

    return calcular_precio_con_motor(
        precio_base=precio_base,
        lista_id=lista_id,
        descuento_cliente=descuento_cliente,
        alicuota_iva=alicuota_iva,
        impuesto_interno_pct=impuesto_interno_pct,
        incluir_iva=iva_incluido,
        tipo_cliente=tipo_cliente,
        regla=regla,
        promo=promo,
    )
