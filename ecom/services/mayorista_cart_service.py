"""
Servicio de carrito mayorista (Fase P1).

Persistencia en Postgres `synap` (modelos EcomCart/EcomCartItem). El precio del renglón
se calcula con el motor único (`price_rules_engine` vía `catalogo_producto.resolver_precio_articulo`)
y el stock se valida contra MySQL legacy vía `self_checkout.StockService`.

Sin escritura a MySQL legacy en esta fase (el checkout P2 hará el alta transaccional).
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none, str_or_default
from ecom.models import EcomCart, EcomCartItem
from ecom.services.catalogo_producto import resolver_precio_articulo
from self_checkout.services.stock_service import StockService

Q2 = Decimal("0.01")
IVA_21 = Decimal("21")
IVA_105 = Decimal("10.5")


def _q2(v: Any) -> Decimal:
    return (v if isinstance(v, Decimal) else Decimal(str(v))).quantize(Q2, rounding=ROUND_HALF_UP)


def _dec(v: Any, default: str = "0") -> Decimal:
    r = to_decimal_or_none(v)
    return r if r is not None else Decimal(default)


def _s(v: Any, default: str = "") -> str:
    return str_or_default(v, default)


# --------------------------------------------------------------------------- #
# Carrito
# --------------------------------------------------------------------------- #

def obtener_o_crear_carrito(
    base_empresa: str,
    id_usuario: int,
    *,
    idcliente: Optional[int] = None,
    lista_id: int = 1,
    id_deposito: int = 1,
    iva_incluido: bool = True,
    tipo_comprobante: str = EcomCart.TIPO_PEDIDO,
) -> EcomCart:
    """
    Devuelve el carrito borrador del vendedor (uno por base_empresa+id_usuario), creándolo si
    no existe. Si cambia el cliente seleccionado, vacía el carrito (paridad pop jcart del PHP).
    Actualiza el contexto (lista, depósito, iva_incluido, tipo) con los valores de sesión.
    """
    cart = (
        EcomCart.objects.filter(
            base_empresa=base_empresa,
            id_usuario=id_usuario,
            estado=EcomCart.ESTADO_BORRADOR,
        )
        .order_by("-updated_at")
        .first()
    )

    if cart is None:
        return EcomCart.objects.create(
            base_empresa=base_empresa,
            id_usuario=id_usuario,
            idcliente=idcliente,
            lista_id=lista_id,
            id_deposito=id_deposito,
            iva_incluido=iva_incluido,
            tipo_comprobante=tipo_comprobante or EcomCart.TIPO_PEDIDO,
        )

    cliente_cambio = (
        idcliente is not None
        and cart.idcliente is not None
        and int(cart.idcliente) != int(idcliente)
    )
    if cliente_cambio:
        cart.items.all().delete()
    if idcliente is not None:
        cart.idcliente = idcliente

    cart.lista_id = lista_id
    cart.id_deposito = id_deposito
    cart.iva_incluido = iva_incluido
    if tipo_comprobante:
        cart.tipo_comprobante = tipo_comprobante
    cart.save()

    if cliente_cambio:
        recalcular_totales(cart)
    return cart


@transaction.atomic
def agregar_item(
    cart: EcomCart,
    id_articulo: int,
    cantidad: Any,
    *,
    descuento_cliente: Any = Decimal("0"),
) -> Tuple[Optional[EcomCartItem], Optional[str]]:
    """
    Agrega (o consolida) un artículo al carrito. Precio del renglón vía motor; valida stock
    disponible con la cantidad total del artículo. Devuelve (item, error).
    """
    cantidad = _dec(cantidad)
    if cantidad <= 0:
        return None, "La cantidad debe ser mayor a 0."

    id_articulo = to_int_or_none(id_articulo)
    if id_articulo is None:
        return None, "Artículo inválido."

    existing = cart.items.filter(id_articulo=id_articulo).first()
    cant_actual = existing.cantidad if existing else Decimal("0")
    cant_total = cant_actual + cantidad

    ok, err = _validar_stock(cart, id_articulo, cant_total)
    if not ok:
        return None, err

    res = resolver_precio_articulo(
        cart.base_empresa,
        id_articulo,
        lista_id=cart.lista_id,
        codigo_cliente=cart.idcliente,
        descuento_cliente=_dec(descuento_cliente),
        iva_incluido=False,
    )
    if res is None:
        return None, "Artículo no encontrado o inactivo."
    precio_neto, row = res

    if existing is not None:
        existing.cantidad = cant_total
        existing.precio_unitario_neto = _dec(precio_neto)
        _aplicar_datos_articulo(existing, row)
        existing.save()
        item = existing
    else:
        orden = (cart.items.count() or 0) + 1
        item = EcomCartItem(
            cart=cart,
            id_articulo=id_articulo,
            cantidad=cantidad,
            precio_unitario_neto=_dec(precio_neto),
            lista_id=cart.lista_id,
            orden=orden,
        )
        _aplicar_datos_articulo(item, row)
        item.save()

    recalcular_totales(cart)
    return item, None


def actualizar_cantidad(
    cart: EcomCart, item_id: int, cantidad: Any
) -> Tuple[bool, Optional[str]]:
    """Fija la cantidad de un renglón (revalida stock con la nueva cantidad)."""
    cantidad = _dec(cantidad)
    if cantidad <= 0:
        return False, "La cantidad debe ser mayor a 0."
    item = cart.items.filter(id=item_id).first()
    if item is None:
        return False, "Renglón no encontrado."

    ok, err = _validar_stock(cart, item.id_articulo, cantidad)
    if not ok:
        return False, err

    item.cantidad = cantidad
    item.save(update_fields=["cantidad"])
    recalcular_totales(cart)
    return True, None


def actualizar_descuento_item(
    cart: EcomCart, item_id: int, porcentaje: Any
) -> Tuple[bool, Optional[str]]:
    """Aplica el descuento porcentual (0–100) de un renglón."""
    pct = _dec(porcentaje)
    if pct < 0 or pct > 100:
        return False, "El descuento debe estar entre 0 y 100 %."
    item = cart.items.filter(id=item_id).first()
    if item is None:
        return False, "Renglón no encontrado."
    item.porcentaje_descuento = pct
    item.save(update_fields=["porcentaje_descuento"])
    recalcular_totales(cart)
    return True, None


def quitar_item(cart: EcomCart, item_id: int) -> bool:
    """Quita un renglón del carrito."""
    borrados, _ = cart.items.filter(id=item_id).delete()
    if borrados:
        recalcular_totales(cart)
        return True
    return False


def limpiar(cart: EcomCart) -> None:
    """Vacía el carrito."""
    cart.items.all().delete()
    recalcular_totales(cart)


def aplicar_descuento_pie(cart: EcomCart, porcentaje: Any) -> Tuple[bool, Optional[str]]:
    """Aplica el descuento al pie (0–100) a todo el carrito."""
    pct = _dec(porcentaje)
    if pct < 0 or pct > 100:
        return False, "El descuento debe estar entre 0 y 100 %."
    cart.descuento_pie_pct = pct
    cart.save(update_fields=["descuento_pie_pct"])
    recalcular_totales(cart)
    return True, None


# --------------------------------------------------------------------------- #
# Totales (paridad Jcart.update_subtotal)
# --------------------------------------------------------------------------- #

def recalcular_totales(cart: EcomCart) -> None:
    """
    Recalcula los totales del carrito con desglose por alícuota (21 / 10,5 / exento),
    impuesto interno y descuento al pie (aplicado sobre el neto por alícuota).
    """
    pie = cart.descuento_pie_pct or Decimal("0")
    factor = (Decimal("100") - pie) / Decimal("100")

    neto21 = neto105 = exento = neto_otros = Decimal("0")
    iva21 = iva105 = iva_otros = interno_total = Decimal("0")

    for item in cart.items.all():
        neto_sin = _dec(item.cantidad) * _dec(item.precio_unitario_neto)
        neto_line = _q2(neto_sin * (Decimal("100") - _dec(item.porcentaje_descuento)) / Decimal("100"))
        alic = _dec(item.alicuota_iva)
        impint = _dec(item.impuesto_interno_pct)

        # Totales del renglón (antes del descuento al pie) para mostrar en UI
        iva_line_row = _q2(neto_line * alic / Decimal("100"))
        interno_line_row = _q2(neto_line * impint / Decimal("100"))
        item.neto = neto_line
        item.iva = iva_line_row
        item.total = _q2(neto_line + iva_line_row + interno_line_row)
        item.save(update_fields=["neto", "iva", "total"])

        # Aportes al total del carrito (con descuento al pie)
        neto_pie = _q2(neto_line * factor)
        iva_pie = _q2(neto_pie * alic / Decimal("100"))
        interno_total += _q2(neto_pie * impint / Decimal("100"))

        if alic == IVA_21:
            neto21 += neto_pie
            iva21 += iva_pie
        elif alic == IVA_105:
            neto105 += neto_pie
            iva105 += iva_pie
        elif alic == 0:
            exento += neto_pie
        else:
            neto_otros += neto_pie
            iva_otros += iva_pie

    subtotal_neto = _q2(neto21 + neto105 + exento + neto_otros)
    iva_total = _q2(iva21 + iva105 + iva_otros)
    total = _q2(subtotal_neto + iva_total + interno_total)

    cart.neto_gravado_21 = _q2(neto21)
    cart.neto_gravado_105 = _q2(neto105)
    cart.iva_21 = _q2(iva21)
    cart.iva_105 = _q2(iva105)
    cart.exento = _q2(exento)
    cart.impuesto_interno_total = _q2(interno_total)
    cart.subtotal_neto = subtotal_neto
    cart.total = total
    cart.save(
        update_fields=[
            "neto_gravado_21",
            "neto_gravado_105",
            "iva_21",
            "iva_105",
            "exento",
            "impuesto_interno_total",
            "subtotal_neto",
            "total",
            "updated_at",
        ]
    )


# --------------------------------------------------------------------------- #
# Serialización
# --------------------------------------------------------------------------- #

def serializar_carrito(cart: EcomCart) -> Dict[str, Any]:
    """Estructura JSON del carrito para las respuestas de la API."""
    items = [
        {
            "id": item.id,
            "id_articulo": item.id_articulo,
            "codigo": item.codigo,
            "id_manual": item.id_manual,
            "descripcion": item.descripcion,
            "cantidad": float(item.cantidad),
            "precio_unitario_neto": float(item.precio_unitario_neto),
            "alicuota_iva": float(item.alicuota_iva),
            "impuesto_interno_pct": float(item.impuesto_interno_pct),
            "porcentaje_descuento": float(item.porcentaje_descuento),
            "en_promocion": (item.promocion or "").strip().lower() == "si",
            "promocion_tipo": item.promocion_tipo,
            "neto": float(item.neto),
            "iva": float(item.iva),
            "total": float(item.total),
            "orden": item.orden,
        }
        for item in cart.items.all()
    ]
    iva_total = _q2(_dec(cart.iva_21) + _dec(cart.iva_105))
    return {
        "cart_id": cart.id,
        "idcliente": cart.idcliente,
        "lista_id": cart.lista_id,
        "id_deposito": cart.id_deposito,
        "iva_incluido": cart.iva_incluido,
        "tipo_comprobante": cart.tipo_comprobante,
        "estado": cart.estado,
        "descuento_pie_pct": float(cart.descuento_pie_pct),
        "items": items,
        "totales": {
            "neto_gravado_21": float(cart.neto_gravado_21),
            "neto_gravado_105": float(cart.neto_gravado_105),
            "iva_21": float(cart.iva_21),
            "iva_105": float(cart.iva_105),
            "iva_total": float(iva_total),
            "exento": float(cart.exento),
            "impuesto_interno_total": float(cart.impuesto_interno_total),
            "subtotal_neto": float(cart.subtotal_neto),
            "total": float(cart.total),
        },
        "cantidad_items": len(items),
    }


# --------------------------------------------------------------------------- #
# Helpers internos
# --------------------------------------------------------------------------- #

def _validar_stock(cart: EcomCart, id_articulo: int, cantidad_total: Decimal) -> Tuple[bool, Optional[str]]:
    stock = StockService(cart.base_empresa)
    ok, err = stock.validar_disponible_items(
        [{"id_articulo": id_articulo, "cantidad": cantidad_total}],
        cart.id_deposito,
    )
    if ok:
        return True, None
    disp = (err or {}).get("disponible", 0)
    return False, f"Stock insuficiente. Disponible: {disp}."


def _aplicar_datos_articulo(item: EcomCartItem, row: Dict[str, Any]) -> None:
    """Copia identificación, alícuota, impuesto interno y promoción desde la fila del artículo."""
    item.codigo = _s(row.get("CodigoArticuloT"), "")[:64]
    item.id_manual = _s(row.get("id_manual"), "")[:64]
    item.descripcion = _s(row.get("NombreArticulo"), "")[:255]
    item.alicuota_iva = _dec(row.get("alic_iva"), "21")
    item.impuesto_interno_pct = _dec(row.get("impuesto_interno"), "0")
    item.promocion = _s(row.get("promocion"), "")[:8]
    item.promocion_tipo = _s(row.get("promocion_tipo"), "")[:64]
    item.promocion_por = _dec(row.get("promocion_por"), "0")
    item.promocion_cant = to_int_or_none(row.get("promocion_cant")) or 0
