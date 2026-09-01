"""Confirmación en lote de pedido masivo (1 PED por sucursal) + compensación."""

from __future__ import annotations

import logging
import time
from datetime import date
from decimal import Decimal
from typing import Any, Dict, Iterator, List, Optional, Tuple

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from ecom.models import EcomCart, EcomPedidoMasivoDraft
from ecom.services.comprobantes_anulacion import anular_pedido_relay
from ecom.services.mayorista_cart_service import agregar_item, recalcular_totales
from ecom.services.mayorista_checkout_service import CheckoutInput, confirmar
from ecom.services.pedido_cabecera_comercial import (
    PedidoCabeceraComercial,
    parsear_cabecera_desde_body,
    resolver_cabecera_comercial,
)
from ecom.services.pedido_cabecera_relay import puede_anular_pedido_relay
from ecom.services.pedido_masivo_matriz import (
    descuentos_fila_efectivos,
    lineas_con_precio_cero,
    precios_fila_efectivos,
    leer_contexto_cliente_masivo,
    listar_sucursales_cliente,
    validar_multiplos_draft,
)
from ecom.services.ecom_config_mysql import aprobacion_pedidos_activa
from ecom.services.presentacion_articulo import opciones_presentacion_articulo
from ecom.services.vendedor_operativo import resolver_viajante_operativo

logger = logging.getLogger(__name__)

_MOTIVO_COMPENSACION = "Compensación lote pedido masivo Synap (fallo parcial)"
_MOTIVO_ANULA_ORIGEN_SIMPLE = "Edición pedido simple Synap (anula y crea nuevo PED)"
PREVIEW_CELDAS_LIMITE_BLANDO = 200
PREVIEW_TIMEOUT_SEG = 8.0


def _dec(v: Any, default: str = "0") -> Decimal:
    r = to_decimal_or_none(v)
    return r if r is not None else Decimal(default)


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
    descuentos_por_articulo: Dict[int, Decimal],
    validar_stock: bool = True,
    precios_por_articulo: Optional[Dict[int, Decimal]] = None,
) -> Optional[str]:
    agregados = 0
    precios = precios_por_articulo or {}
    for id_art, packs in lineas:
        tipo, mult = _pack_tipo_y_mult(cart.base_empresa, id_art)
        pct = descuentos_por_articulo.get(id_art, Decimal("0"))
        precio_ov = precios.get(id_art)
        _item, err = agregar_item(
            cart,
            id_art,
            packs,
            descuento_cliente=pct,
            tipo_unidad=tipo,
            multiplicador=mult,
            validar_stock=validar_stock,
            precio_unitario_neto=precio_ov,
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


def _resolver_cod_viajante_lote(
    cod_viajante: Optional[int],
    draft: EcomPedidoMasivoDraft,
    sess_user: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    if cod_viajante is not None:
        return cod_viajante
    if sess_user:
        cv = resolver_viajante_operativo(sess_user)
        if cv is not None:
            return cv
    return draft.cod_viajante


def _pie_efectivo(
    draft: EcomPedidoMasivoDraft,
    desc_pie_pct: Optional[Any] = None,
) -> Decimal:
    if desc_pie_pct is not None:
        return _dec(desc_pie_pct)
    return _dec(draft.descuento_pie_pct)


def _limpiar_carritos_efimeros(carritos: List[EcomCart]) -> None:
    for c in carritos:
        try:
            if c.estado == EcomCart.ESTADO_BORRADOR:
                c.items.all().delete()
                c.delete()
        except Exception:
            pass


def _checkout_input_desde_cabecera(
    cabecera: PedidoCabeceraComercial,
    *,
    id_punto_venta: int,
    id_cliente_domicilio: int,
    forma_entrega: str,
    observaciones: str,
    agente_percep: Optional[str],
    es_supervisor: bool,
    dias_entrega: int = 0,
    dias_no_laborables: Optional[list] = None,
) -> CheckoutInput:
    return CheckoutInput(
        tipo=EcomCart.TIPO_PEDIDO,
        id_punto_venta=id_punto_venta,
        id_cliente_domicilio=id_cliente_domicilio,
        forma_entrega=forma_entrega or "",
        observaciones=observaciones,
        agente_percep=agente_percep,
        es_supervisor=es_supervisor,
        fecha_pedido=cabecera.fecha_pedido,
        fecha_entrega=cabecera.fecha_entrega,
        vencimiento=cabecera.vencimiento,
        id_condventa=cabecera.id_condventa,
        cond_venta=cabecera.cond_venta,
        lista_id=cabecera.lista_id,
        dias_entrega=dias_entrega,
        dias_no_laborables=list(dias_no_laborables or []),
    )


def calcular_totales_lote_masivo(
    draft: EcomPedidoMasivoDraft,
    *,
    id_usuario: int,
    desc_pie_pct: Optional[Any] = None,
    lista_id: Optional[int] = None,
    id_deposito: int = 1,
    timeout_seg: float = PREVIEW_TIMEOUT_SEG,
    cabecera: Optional[PedidoCabeceraComercial] = None,
) -> Dict[str, Any]:
    """
    Calcula totales por sucursal y lote usando el mismo flujo que checkout batch.

    Respeta límite blando de celdas y timeout amigable (warning sin bloquear confirmación).
    """
    por_dom = _agrupar_por_sucursal(draft)
    n_celdas = sum(len(v) for v in por_dom.values())
    warnings: List[str] = []
    if n_celdas > PREVIEW_CELDAS_LIMITE_BLANDO:
        warnings.append(
            f"La matriz tiene {n_celdas} celdas con cantidad (límite recomendado "
            f"{PREVIEW_CELDAS_LIMITE_BLANDO}). El preview puede demorar."
        )

    if not por_dom:
        return {
            "ok": True,
            "sucursales": [],
            "total_lote": {"neto": 0.0, "iva": 0.0, "total": 0.0},
            "warning": " ".join(warnings) if warnings else "",
            "preview_incompleto": False,
            "celdas_con_cantidad": 0,
        }

    ctx_cli = leer_contexto_cliente_masivo(draft.base_empresa, draft.id_cliente)
    if cabecera is not None:
        lista_ef = int(cabecera.lista_id)
    else:
        lista_ef = int(lista_id if lista_id is not None else ctx_cli.get("lista_id") or 1)
    desc_map = descuentos_fila_efectivos(draft, draft.base_empresa)
    precio_map = precios_fila_efectivos(draft, draft.base_empresa, lista_id=lista_ef)
    pie = _pie_efectivo(draft, desc_pie_pct)
    cero = _payload_precios_cero(draft, lista_id=lista_ef)
    if cero:
        return {
            "ok": False,
            "sucursales": [],
            "total_lote": {"neto": 0.0, "iva": 0.0, "total": 0.0},
            "warning": "",
            "preview_incompleto": False,
            "celdas_con_cantidad": n_celdas,
            **cero,
        }

    sucursales_out: List[Dict[str, Any]] = []
    carritos_tmp: List[EcomCart] = []
    t0 = time.monotonic()
    preview_incompleto = False

    try:
        for id_dom, lineas in sorted(por_dom.items()):
            if time.monotonic() - t0 > timeout_seg:
                preview_incompleto = True
                warnings.append(
                    "El cálculo de preview superó el tiempo límite. "
                    "Podés confirmar el lote igualmente."
                )
                break

            cart = _crear_carrito_efimero(
                base_empresa=draft.base_empresa,
                id_usuario=id_usuario,
                id_cliente=draft.id_cliente,
                lista_id=lista_ef,
                id_deposito=id_deposito,
            )
            carritos_tmp.append(cart)
            err_load = _cargar_lineas_sucursal(
                cart,
                lineas,
                descuentos_por_articulo=desc_map,
                validar_stock=False,
                precios_por_articulo=precio_map,
            )
            if err_load:
                warnings.append(f"Sucursal {id_dom}: {err_load}")
                continue

            cart.descuento_pie_pct = pie
            recalcular_totales(cart)
            iva_total = _dec(cart.iva_21) + _dec(cart.iva_105)
            sucursales_out.append(
                {
                    "id_cliente_domicilio": id_dom,
                    "neto": float(cart.subtotal_neto or 0),
                    "iva": float(iva_total),
                    "total": float(cart.total or 0),
                }
            )
    finally:
        _limpiar_carritos_efimeros(carritos_tmp)

    neto_lote = sum(s["neto"] for s in sucursales_out)
    iva_lote = sum(s["iva"] for s in sucursales_out)
    total_lote = sum(s["total"] for s in sucursales_out)

    return {
        "ok": True,
        "sucursales": sucursales_out,
        "total_lote": {
            "neto": round(neto_lote, 2),
            "iva": round(iva_lote, 2),
            "total": round(total_lote, 2),
        },
        "warning": " ".join(warnings).strip(),
        "preview_incompleto": preview_incompleto,
        "celdas_con_cantidad": n_celdas,
    }


def _mapa_nombres_sucursales(
    draft: EcomPedidoMasivoDraft,
    *,
    nombres_sucursales: Optional[Dict[int, str]] = None,
) -> Dict[int, str]:
    if nombres_sucursales:
        return {int(k): str(v) for k, v in nombres_sucursales.items()}
    out: Dict[int, str] = {}
    for su in listar_sucursales_cliente(
        draft.base_empresa, draft.id_cliente, cod_viajante=draft.cod_viajante
    ):
        sid = to_int_or_none(su.get("id_cliente_domicilio"))
        if sid is None:
            continue
        out[sid] = str(su.get("nombre") or su.get("etiqueta") or f"Sucursal #{sid}")
    return out


def _mapa_nro_sucursales(draft: EcomPedidoMasivoDraft) -> Dict[int, str]:
    """id_cliente_domicilio → NroCalle (número de sucursal visible en matriz/Excel)."""
    out: Dict[int, str] = {}
    for su in listar_sucursales_cliente(
        draft.base_empresa, draft.id_cliente, cod_viajante=draft.cod_viajante
    ):
        sid = to_int_or_none(su.get("id_cliente_domicilio"))
        if sid is None:
            continue
        nro = str_or_default(su.get("nro"), "").strip()
        if nro and nro != "-":
            out[sid] = nro
    return out


def _detalle_default_pedido_masivo(
    draft: EcomPedidoMasivoDraft,
    id_cliente_domicilio: int,
    nros_sucursal: Optional[Dict[int, str]] = None,
) -> str:
    """
    Texto por defecto de ``comp_ped.Detalle``.

    Usa el **NroCalle** (nº de sucursal de la UI/Excel), no el id de domicilio,
    para no confundir al usuario (p. ej. id 14 ≠ SUC 14).
    """
    id_dom = to_int_or_none(id_cliente_domicilio)
    nro = ""
    if id_dom is not None and nros_sucursal:
        nro = str_or_default(nros_sucursal.get(id_dom), "").strip()
    if not nro or nro == "-":
        # Último recurso: no inventar un NroCalle; dejar el id etiquetado.
        nro = f"#{id_dom}" if id_dom is not None else "?"
    return f"Pedido masivo Synap draft #{draft.pk} sucursal {nro}"


def _evento_fin(
    *,
    ok: bool,
    message: str,
    codigos_movimiento: Optional[List[int]] = None,
    errores: Optional[Dict[str, str]] = None,
    compensacion: Optional[List[str]] = None,
    detalle: Optional[List[Dict[str, Any]]] = None,
    cod_viajante: Optional[int] = None,
    ya_confirmado: bool = False,
    codigos_anulados_intento: Optional[List[int]] = None,
    cod_mov_origen_anulado: Optional[int] = None,
    infracciones_multiplo: Optional[List[Dict[str, Any]]] = None,
    lineas_precio_cero: Optional[List[Dict[str, Any]]] = None,
    code: Optional[str] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "event": "fin",
        "ok": ok,
        "message": message,
        "codigos_movimiento": list(codigos_movimiento or []),
        "errores": dict(errores or {}),
        "compensacion": list(compensacion or []),
    }
    if detalle is not None:
        payload["detalle"] = detalle
    if cod_viajante is not None:
        payload["cod_viajante"] = cod_viajante
    if ya_confirmado:
        payload["ya_confirmado"] = True
    if codigos_anulados_intento is not None:
        payload["codigos_anulados_intento"] = codigos_anulados_intento
    if cod_mov_origen_anulado is not None:
        payload["cod_mov_origen_anulado"] = cod_mov_origen_anulado
    if infracciones_multiplo is not None:
        payload["infracciones_multiplo"] = infracciones_multiplo
    if lineas_precio_cero is not None:
        payload["lineas_precio_cero"] = lineas_precio_cero
    if code:
        payload["code"] = code
    return payload


def _payload_precios_cero(
    draft: EcomPedidoMasivoDraft,
    *,
    lista_id: Optional[int] = None,
) -> Optional[Dict[str, Any]]:
    lineas = lineas_con_precio_cero(
        draft, draft.base_empresa, lista_id=lista_id
    )
    if not lineas:
        return None
    n = len(lineas)
    return {
        "code": "precio_cero",
        "message": (
            f"Hay {n} artículo(s) con precio 0. Corregí el precio antes de continuar."
        ),
        "lineas_precio_cero": lineas,
    }


def _anular_pedido_origen_simple(
    draft: EcomPedidoMasivoDraft,
) -> Tuple[Optional[int], Optional[str]]:
    """
    REQ-CHK-014: si el draft tiene ``cod_mov_origen``, anular el PED pendiente
    antes de confirmar el lote (anula+crea).
    """
    cod_origen = to_int_or_none(getattr(draft, "cod_mov_origen", None))
    if cod_origen is None:
        return None, None
    ok, err = puede_anular_pedido_relay(draft.base_empresa, cod_origen)
    if not ok:
        return None, err or "El pedido origen ya no se puede editar."
    r = anular_pedido_relay(
        draft.base_empresa,
        cod_origen,
        motivo=_MOTIVO_ANULA_ORIGEN_SIMPLE,
    )
    if r.get("msg") != "ok":
        return None, r.get("error") or "No se pudo anular el pedido origen."
    return cod_origen, None


def confirmar_lote_masivo_stream(
    draft: EcomPedidoMasivoDraft,
    *,
    id_usuario: int,
    id_punto_venta: int,
    cod_viajante: Optional[int] = None,
    lista_id: int = 1,
    id_deposito: int = 1,
    desc_pie_pct: Optional[Any] = None,
    forma_entrega: str = "",
    observaciones: str = "",
    agente_percep: Optional[str] = None,
    sess_user: Optional[Dict[str, Any]] = None,
    cabecera: Optional[PedidoCabeceraComercial] = None,
    es_supervisor: bool = False,
    dias_entrega: int = 0,
    dias_no_laborables: Optional[list] = None,
    nombres_sucursales: Optional[Dict[int, str]] = None,
) -> Iterator[Dict[str, Any]]:
    """
    Generador de eventos NDJSON para confirmación en lote (1 PED por sucursal).

    Eventos: ``inicio``, ``sucursal`` (procesando | ok | error), ``fin``.
    Ante fallo: compensación igual que ``confirmar_lote_masivo`` sync.
    """
    if draft.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMADO:
        yield _evento_fin(
            ok=True,
            message="El lote ya estaba confirmado.",
            codigos_movimiento=draft.codigos_movimiento or [],
            ya_confirmado=True,
        )
        return
    if draft.estado == EcomPedidoMasivoDraft.ESTADO_ARCHIVADO:
        yield _evento_fin(ok=False, message="El borrador está archivado.")
        return

    pv = to_int_or_none(id_punto_venta)
    if pv is None:
        yield _evento_fin(ok=False, message="Falta punto de venta.")
        return

    por_dom = _agrupar_por_sucursal(draft)
    if not por_dom:
        yield _evento_fin(ok=False, message="No hay cantidades para confirmar.")
        return

    ok_mult, msg_mult, infracciones = validar_multiplos_draft(draft, draft.base_empresa)
    if not ok_mult:
        yield _evento_fin(
            ok=False,
            message=msg_mult,
            infracciones_multiplo=infracciones,
            code="multiplo_empaque",
        )
        return

    lista_check = int(cabecera.lista_id) if cabecera is not None else int(lista_id or 1)
    cero = _payload_precios_cero(draft, lista_id=lista_check)
    if cero:
        yield _evento_fin(
            ok=False,
            message=cero["message"],
            lineas_precio_cero=cero["lineas_precio_cero"],
            code="precio_cero",
        )
        return

    nombres = _mapa_nombres_sucursales(draft, nombres_sucursales=nombres_sucursales)
    nros_sucursal = _mapa_nro_sucursales(draft)
    detalle_default_obs = (observaciones or "").strip()
    doms_ordenados = sorted(por_dom.items())
    total = len(doms_ordenados)

    cv_efectivo = _resolver_cod_viajante_lote(cod_viajante, draft, sess_user)
    ctx_cli = leer_contexto_cliente_masivo(draft.base_empresa, draft.id_cliente)
    if cabecera is not None:
        lista_ef = int(cabecera.lista_id)
    else:
        lista_ef = int(lista_id or ctx_cli.get("lista_id") or 1)
    desc_map = descuentos_fila_efectivos(draft, draft.base_empresa)
    precio_map = precios_fila_efectivos(draft, draft.base_empresa, lista_id=lista_ef)
    pie = _pie_efectivo(draft, desc_pie_pct)

    cod_origen_anulado, err_origen = _anular_pedido_origen_simple(draft)
    if err_origen:
        yield _evento_fin(ok=False, message=err_origen)
        return

    draft.estado = EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO
    draft.ultimo_error = {}
    draft.save(update_fields=["estado", "ultimo_error", "updated_at"])

    yield {"event": "inicio", "total": total}

    creados: List[int] = []
    carritos_tmp: List[EcomCart] = []
    errores: Dict[str, str] = {}
    detalle_ok: List[Dict[str, Any]] = []

    try:
        for idx, (id_dom, lineas) in enumerate(doms_ordenados, start=1):
            nombre = nombres.get(id_dom) or f"Sucursal #{id_dom}"
            yield {
                "event": "sucursal",
                "index": idx,
                "total": total,
                "id_cliente_domicilio": id_dom,
                "nombre": nombre,
                "estado": "procesando",
            }

            cart = _crear_carrito_efimero(
                base_empresa=draft.base_empresa,
                id_usuario=id_usuario,
                id_cliente=draft.id_cliente,
                lista_id=lista_ef,
                id_deposito=id_deposito,
            )
            carritos_tmp.append(cart)
            err_load = _cargar_lineas_sucursal(
                cart,
                lineas,
                descuentos_por_articulo=desc_map,
                precios_por_articulo=precio_map,
            )
            if err_load:
                errores[str(id_dom)] = err_load
                yield {
                    "event": "sucursal",
                    "index": idx,
                    "total": total,
                    "id_cliente_domicilio": id_dom,
                    "nombre": nombre,
                    "estado": "error",
                    "error": err_load,
                }
                break

            cart.descuento_pie_pct = pie
            recalcular_totales(cart)

            obs_sucursal = detalle_default_obs or _detalle_default_pedido_masivo(
                draft, id_dom, nros_sucursal
            )
            ok, err, result = confirmar(
                cart,
                _checkout_input_desde_cabecera(
                    cabecera,
                    id_punto_venta=pv,
                    id_cliente_domicilio=id_dom,
                    forma_entrega=forma_entrega or "",
                    observaciones=obs_sucursal,
                    agente_percep=agente_percep,
                    es_supervisor=es_supervisor,
                    dias_entrega=dias_entrega,
                    dias_no_laborables=dias_no_laborables,
                )
                if cabecera is not None
                else CheckoutInput(
                    tipo=EcomCart.TIPO_PEDIDO,
                    id_punto_venta=pv,
                    id_cliente_domicilio=id_dom,
                    forma_entrega=forma_entrega or "",
                    observaciones=obs_sucursal,
                    agente_percep=agente_percep,
                    lista_id=lista_ef,
                    es_supervisor=es_supervisor,
                    dias_entrega=dias_entrega,
                    dias_no_laborables=list(dias_no_laborables or []),
                ),
                id_usuario=id_usuario,
                cod_viajante=cv_efectivo,
            )
            if not ok:
                msg_err = err or "Error al confirmar PED."
                errores[str(id_dom)] = msg_err
                yield {
                    "event": "sucursal",
                    "index": idx,
                    "total": total,
                    "id_cliente_domicilio": id_dom,
                    "nombre": nombre,
                    "estado": "error",
                    "error": msg_err,
                }
                break
            cod = to_int_or_none((result or {}).get("codigo_movimiento"))
            if cod is None:
                msg_err = "Checkout OK sin CodigoMovimiento."
                errores[str(id_dom)] = msg_err
                yield {
                    "event": "sucursal",
                    "index": idx,
                    "total": total,
                    "id_cliente_domicilio": id_dom,
                    "nombre": nombre,
                    "estado": "error",
                    "error": msg_err,
                }
                break
            creados.append(cod)
            nro = (result or {}).get("nro_comprobante") or ""
            detalle_ok.append(
                {
                    "id_cliente_domicilio": id_dom,
                    "codigo_movimiento": cod,
                    "nro_comprobante": nro,
                }
            )
            yield {
                "event": "sucursal",
                "index": idx,
                "total": total,
                "id_cliente_domicilio": id_dom,
                "nombre": nombre,
                "estado": "ok",
                "codigo_movimiento": cod,
                "nro_comprobante": nro,
            }

        if errores:
            avisos = _compensar_pedidos(draft.base_empresa, creados)
            _limpiar_carritos_efimeros(carritos_tmp)
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
            yield _evento_fin(
                ok=False,
                message=msg,
                errores=errores,
                compensacion=avisos,
                codigos_anulados_intento=creados,
            )
            return

        draft.estado = EcomPedidoMasivoDraft.ESTADO_CONFIRMADO
        draft.ultimo_error = {}
        draft.codigos_movimiento = creados
        if aprobacion_pedidos_activa(draft.base_empresa):
            draft.estado_aprobacion_lote = EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_PENDIENTE
        else:
            draft.estado_aprobacion_lote = EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_NEUTRO
        draft.save(
            update_fields=[
                "estado",
                "ultimo_error",
                "codigos_movimiento",
                "estado_aprobacion_lote",
                "updated_at",
            ]
        )
        yield _evento_fin(
            ok=True,
            message=f"Se crearon {len(creados)} pedido(s).",
            codigos_movimiento=creados,
            detalle=detalle_ok,
            cod_viajante=cv_efectivo,
            cod_mov_origen_anulado=cod_origen_anulado,
        )
    except Exception as exc:
        logger.exception("confirmar_lote_masivo_stream: %s", exc)
        avisos = _compensar_pedidos(draft.base_empresa, creados)
        _limpiar_carritos_efimeros(carritos_tmp)
        draft.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
        draft.ultimo_error = {"_lote": str(exc)}
        draft.codigos_movimiento = []
        draft.save(
            update_fields=["estado", "ultimo_error", "codigos_movimiento", "updated_at"]
        )
        yield _evento_fin(
            ok=False,
            message=str(exc),
            errores={"_lote": str(exc)},
            compensacion=avisos,
            codigos_anulados_intento=creados,
        )


def confirmar_lote_masivo(
    draft: EcomPedidoMasivoDraft,
    *,
    id_usuario: int,
    id_punto_venta: int,
    cod_viajante: Optional[int] = None,
    lista_id: int = 1,
    id_deposito: int = 1,
    desc_pie_pct: Optional[Any] = None,
    forma_entrega: str = "",
    observaciones: str = "",
    agente_percep: Optional[str] = None,
    sess_user: Optional[Dict[str, Any]] = None,
    cabecera: Optional[PedidoCabeceraComercial] = None,
    es_supervisor: bool = False,
    dias_entrega: int = 0,
    dias_no_laborables: Optional[list] = None,
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Crea 1 PED por sucursal con Σ packs > 0.

    Ante fallo: anula PEDs de la corrida, draft → BORRADOR + ``ultimo_error``,
    celdas intactas. Wrapper sync sobre ``confirmar_lote_masivo_stream``.
    """
    final: Optional[Dict[str, Any]] = None
    for ev in confirmar_lote_masivo_stream(
        draft,
        id_usuario=id_usuario,
        id_punto_venta=id_punto_venta,
        cod_viajante=cod_viajante,
        lista_id=lista_id,
        id_deposito=id_deposito,
        desc_pie_pct=desc_pie_pct,
        forma_entrega=forma_entrega,
        observaciones=observaciones,
        agente_percep=agente_percep,
        sess_user=sess_user,
        cabecera=cabecera,
        es_supervisor=es_supervisor,
        dias_entrega=dias_entrega,
        dias_no_laborables=dias_no_laborables,
    ):
        if ev.get("event") == "fin":
            final = ev
    if not final:
        return False, "Sin respuesta del lote.", {}
    ok = bool(final.get("ok"))
    msg = str(final.get("message") or "")
    payload = {
        k: v
        for k, v in final.items()
        if k not in ("event", "ok", "message")
    }
    return ok, msg, payload
