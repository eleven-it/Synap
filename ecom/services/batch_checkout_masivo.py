"""Confirmación en lote de pedido masivo (1 PED por sucursal) + compensación."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none
from ecom.models import EcomCart, EcomPedidoMasivoDraft
from ecom.services.comprobantes_anulacion import anular_pedido_relay
from ecom.services.mayorista_cart_service import agregar_item
from ecom.services.mayorista_checkout_service import CheckoutInput, confirmar
from ecom.services.presentacion_articulo import opciones_presentacion_articulo

logger = logging.getLogger(__name__)

_MOTIVO_COMPENSACION = "Compensación lote pedido masivo Synap (fallo parcial)"


def _pack_tipo_y_mult(base_empresa: str, id_articulo: int) -> Tuple[str, Decimal]:
    """Presentación preferida para «packs» de la matriz (Bulto > Display > defecto)."""
    opts = opciones_presentacion_articulo(base_empresa, id_articulo)
    por_tipo = {o["tipo"]: o for o in (opts.get("opciones") or [])}
    for preferido in ("Bulto", "Display"):
        if preferido in por_tipo:
            m = to_decimal_or_none(por_tipo[preferido].get("multiplicador")) or Decimal("1")
            return preferido, m
    defecto = str(opts.get("tipo_unidad_defecto") or "Unidad")
    m = Decimal("1")
    if defecto in por_tipo:
        m = to_decimal_or_none(por_tipo[defecto].get("multiplicador")) or Decimal("1")
    return defecto, m


def _agrupar_por_sucursal(
    draft: EcomPedidoMasivoDraft,
) -> Dict[int, List[Tuple[int, Decimal]]]:
    """id_cliente_domicilio → [(id_articulo, cantidad_packs), ...]."""
    por_dom: Dict[int, List[Tuple[int, Decimal]]] = {}
    for c in draft.celdas.all():
        qty = to_decimal_or_none(c.cantidad_packs) or Decimal("0")
        if qty <= 0:
            continue
        idd = int(c.id_cliente_domicilio)
        por_dom.setdefault(idd, []).append((int(c.id_articulo), qty))
    return por_dom


def _crear_carrito_efimero(
    *,
    base_empresa: str,
    id_usuario: int,
    id_cliente: int,
    lista_id: int,
    id_deposito: int,
) -> EcomCart:
    """Carrito borrador dedicado al lote (no reutiliza el de compra simple)."""
    return EcomCart.objects.create(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        idcliente=id_cliente,
        lista_id=lista_id,
        id_deposito=id_deposito,
        iva_incluido=True,
        tipo_comprobante=EcomCart.TIPO_PEDIDO,
        estado=EcomCart.ESTADO_BORRADOR,
    )


def _cargar_lineas_sucursal(
    cart: EcomCart,
    lineas: List[Tuple[int, Decimal]],
    *,
    descuento_cliente: Decimal = Decimal("0"),
) -> Optional[str]:
    agregados = 0
    for id_art, packs in lineas:
        tipo, mult = _pack_tipo_y_mult(cart.base_empresa, id_art)
        _item, err = agregar_item(
            cart,
            id_art,
            packs,
            descuento_cliente=descuento_cliente,
            tipo_unidad=tipo,
            multiplicador=mult,
        )
        if err:
            return f"Artículo {id_art}: {err}"
        agregados += 1
    if agregados == 0:
        return "Sin líneas válidas para la sucursal."
    return None


def _compensar_pedidos(base_empresa: str, creados: List[int]) -> List[str]:
    avisos: List[str] = []
    for cod in reversed(creados):
        r = anular_pedido_relay(
            base_empresa,
            cod,
            motivo=_MOTIVO_COMPENSACION,
        )
        if r.get("msg") != "ok":
            avisos.append(f"PED {cod}: {r.get('error') or 'no anulado'}")
            logger.error("Compensación fallida PED %s: %s", cod, r)
    return avisos


def confirmar_lote_masivo(
    draft: EcomPedidoMasivoDraft,
    *,
    id_usuario: int,
    id_punto_venta: int,
    cod_viajante: Optional[int] = None,
    lista_id: int = 1,
    id_deposito: int = 1,
    descuento_cliente: Decimal = Decimal("0"),
    forma_entrega: str = "",
    observaciones: str = "",
    agente_percep: Optional[str] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Crea 1 PED por sucursal con Σ packs > 0.

    Ante fallo: anula PEDs de la corrida, draft → BORRADOR + ``ultimo_error``,
    celdas intactas.
    """
    if draft.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMADO:
        return True, "El lote ya estaba confirmado.", {
            "codigos_movimiento": draft.codigos_movimiento or [],
            "ya_confirmado": True,
        }
    if draft.estado == EcomPedidoMasivoDraft.ESTADO_ARCHIVADO:
        return False, "El borrador está archivado.", {}

    pv = to_int_or_none(id_punto_venta)
    if pv is None:
        return False, "Falta punto de venta.", {}

    por_dom = _agrupar_por_sucursal(draft)
    if not por_dom:
        return False, "No hay cantidades para confirmar.", {}

    draft.estado = EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO
    draft.ultimo_error = {}
    draft.save(update_fields=["estado", "ultimo_error", "updated_at"])

    creados: List[int] = []
    carritos_tmp: List[EcomCart] = []
    errores: Dict[str, str] = {}
    detalle_ok: List[Dict[str, Any]] = []

    try:
        for id_dom, lineas in sorted(por_dom.items()):
            cart = _crear_carrito_efimero(
                base_empresa=draft.base_empresa,
                id_usuario=id_usuario,
                id_cliente=draft.id_cliente,
                lista_id=lista_id,
                id_deposito=id_deposito,
            )
            carritos_tmp.append(cart)
            err_load = _cargar_lineas_sucursal(
                cart, lineas, descuento_cliente=descuento_cliente
            )
            if err_load:
                errores[str(id_dom)] = err_load
                break

            ok, err, result = confirmar(
                cart,
                CheckoutInput(
                    tipo=EcomCart.TIPO_PEDIDO,
                    id_punto_venta=pv,
                    id_cliente_domicilio=id_dom,
                    forma_entrega=forma_entrega or "",
                    observaciones=observaciones
                    or f"Pedido masivo Synap draft #{draft.pk} sucursal {id_dom}",
                    agente_percep=agente_percep,
                ),
                id_usuario=id_usuario,
                cod_viajante=cod_viajante if cod_viajante is not None else draft.cod_viajante,
            )
            if not ok:
                errores[str(id_dom)] = err or "Error al confirmar PED."
                break
            cod = to_int_or_none((result or {}).get("codigo_movimiento"))
            if cod is None:
                errores[str(id_dom)] = "Checkout OK sin CodigoMovimiento."
                break
            creados.append(cod)
            detalle_ok.append(
                {
                    "id_cliente_domicilio": id_dom,
                    "codigo_movimiento": cod,
                    "nro_comprobante": (result or {}).get("nro_comprobante") or "",
                }
            )

        if errores:
            avisos = _compensar_pedidos(draft.base_empresa, creados)
            # Limpiar carritos efímeros aún en borrador
            for c in carritos_tmp:
                if c.estado == EcomCart.ESTADO_BORRADOR:
                    c.items.all().delete()
                    c.delete()
            draft.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
            draft.ultimo_error = {
                **errores,
                **({"_compensacion": "; ".join(avisos)} if avisos else {}),
            }
            draft.codigos_movimiento = []
            draft.save(
                update_fields=["estado", "ultimo_error", "codigos_movimiento", "updated_at"]
            )
            msg = next(iter(errores.values()))
            return False, msg, {
                "errores": errores,
                "compensacion": avisos,
                "codigos_anulados_intento": creados,
            }

        draft.estado = EcomPedidoMasivoDraft.ESTADO_CONFIRMADO
        draft.ultimo_error = {}
        draft.codigos_movimiento = creados
        draft.save(
            update_fields=["estado", "ultimo_error", "codigos_movimiento", "updated_at"]
        )
        return True, f"Se crearon {len(creados)} pedido(s).", {
            "codigos_movimiento": creados,
            "detalle": detalle_ok,
        }
    except Exception as exc:
        logger.exception("confirmar_lote_masivo: %s", exc)
        avisos = _compensar_pedidos(draft.base_empresa, creados)
        for c in carritos_tmp:
            try:
                if c.estado == EcomCart.ESTADO_BORRADOR:
                    c.items.all().delete()
                    c.delete()
            except Exception:
                pass
        draft.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
        draft.ultimo_error = {"_lote": str(exc)}
        draft.codigos_movimiento = []
        draft.save(
            update_fields=["estado", "ultimo_error", "codigos_movimiento", "updated_at"]
        )
        return False, str(exc), {"compensacion": avisos}
