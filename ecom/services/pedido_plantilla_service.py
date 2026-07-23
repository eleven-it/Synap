"""
Repetir pedido anterior: copia solo artículo + cantidad al carrito borrador.
Precios siempre vía ``resolver_precio_articulo`` (nunca desde ``stockp`` histórico).

Carga PED → borrador masivo (modo simple): ``cargar_pedido_en_draft_masivo``.
"""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction

from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from ecom.models import EcomCart, EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.services import mayorista_cart_service as cart_svc
from ecom.services.batch_checkout_masivo import _pack_tipo_y_mult
from ecom.services.catalogo_producto import resolver_precio_articulo
from ecom.services.cliente_relay import cliente_accesible_por_sesion
from ecom.services.comprobantes_relay import detalle_pedido_relay
from ecom.services.pedido_cabecera_relay import cabecera_pedido_relay
from ecom.services.pedido_masivo_matriz import (
    leer_contexto_cliente_masivo,
    obtener_o_crear_draft,
)
from ecom.services.vendedor_operativo import resolver_viajante_operativo
from self_checkout.services.stock_service import StockService


def _es_cliente_sesion(sess_user: Dict[str, Any]) -> bool:
    return (sess_user.get("tipousuario") or "").strip().lower() == "cliente"


def _descuento_cliente(base: str, idcliente: int) -> Decimal:
    """Descuento de renglón del cliente (columna legacy ``descuento_por_cli``)."""
    from core.mysql_pool import get_mysql_pool

    pool = get_mysql_pool()
    with pool.get_connection(base) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT descuento_por_cli FROM cliente WHERE Codigo = %s LIMIT 1",
            [idcliente],
        )
        row = cur.fetchone()
    if not row or row[0] is None:
        return Decimal("0")
    return to_decimal_or_none(row[0]) or Decimal("0")


def validar_pedido_como_plantilla(
    base_empresa: str,
    cod_mov: int,
    sess_user: Dict[str, Any],
    idcliente_contexto: Optional[int],
    *,
    es_cliente: Optional[bool] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Valida que el PED pertenezca al cliente en contexto y sea repetible.
    Devuelve (cabecera, error).
    """
    if es_cliente is None:
        es_cliente = _es_cliente_sesion(sess_user)

    cab = cabecera_pedido_relay(base_empresa, cod_mov)
    if not cab:
        return None, "Pedido no encontrado."
    if str(cab.get("anulado") or "").strip().lower() in ("si", "sí"):
        return None, "No se puede repetir un pedido anulado."

    id_ped = to_int_or_none(cab.get("id_cliente"))
    if id_ped is None:
        return None, "Pedido sin cliente asociado."

    if es_cliente:
        id_ctx = to_int_or_none(idcliente_contexto)
        if id_ctx is None or int(id_ctx) != int(id_ped):
            return None, "No tiene permiso para repetir este pedido."
    else:
        if idcliente_contexto is None:
            return None, "Seleccione un cliente para repetir el pedido."
        if int(idcliente_contexto) != int(id_ped):
            return None, "El pedido no corresponde al cliente seleccionado."
        if not cliente_accesible_por_sesion(base_empresa, int(id_ped), sess_user):
            return None, "No tiene permiso para operar con este cliente."

    return cab, None


def _salida_a_packs_matriz(
    base_empresa: str,
    id_articulo: int,
    salida_base: Decimal,
    *,
    tipo_unidad_linea: str = "",
    descripcion: str = "",
) -> Tuple[Decimal, Optional[str]]:
    """
    Convierte ``stockp.Salida`` (unidades base) a cantidad_packs de la matriz
    (presentación preferida Bulto > Display > defecto). Redondea a 3 decimales.
    """
    tipo_pack, mult = _pack_tipo_y_mult(base_empresa, id_articulo)
    if mult <= 0:
        mult = Decimal("1")
    packs_exact = salida_base / mult
    packs = packs_exact.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    avisos: List[str] = []
    tu_linea = str_or_default(tipo_unidad_linea, "").strip()
    tipos_estandar = {tipo_pack.lower(), "unidad", "bulto", "display"}
    if tu_linea and tu_linea.lower() not in tipos_estandar:
        etiqueta = descripcion or f"Art. {id_articulo}"
        avisos.append(
            f"{etiqueta}: unidad «{tu_linea}» convertida a packs «{tipo_pack}»."
        )
    if packs_exact != packs:
        etiqueta = descripcion or f"Art. {id_articulo}"
        avisos.append(
            f"{etiqueta}: cantidad ajustada por redondeo "
            f"({salida_base} u. → {packs} {tipo_pack})."
        )
    aviso = " ".join(avisos) if avisos else None
    return packs, aviso


def _pedido_origen_editable(cab: Dict[str, Any]) -> bool:
    anulado = str(cab.get("anulado") or "").strip().lower() in ("si", "sí")
    estado = str(cab.get("estado") or "").strip()
    return not anulado and estado == "Pendiente"


def cargar_pedido_en_draft_masivo(
    base_empresa: str,
    cod_mov: int,
    sess_user: Dict[str, Any],
    *,
    id_usuario: int,
    idcliente_contexto: Optional[int] = None,
    es_cliente: Optional[bool] = None,
    draft_id: Optional[int] = None,
    consulta: bool = False,
) -> Tuple[Optional[EcomPedidoMasivoDraft], Optional[str], Dict[str, Any]]:
    """
    Valida PED, resuelve domicilio, crea/reutiliza draft modo=simple y copia
    renglones ``stockp`` a celdas (packs Bulto>Display). No muta MySQL.

    Devuelve ``(draft, error, meta)`` donde ``meta`` incluye ``advertencias`` y
    ``editable`` para la UI.
    """
    meta: Dict[str, Any] = {"advertencias": [], "editable": False}
    cod = to_int_or_none(cod_mov)
    id_u = to_int_or_none(id_usuario)
    if cod is None or id_u is None or not base_empresa:
        return None, "Parámetros inválidos.", meta

    cab = cabecera_pedido_relay(base_empresa, cod)
    if not cab:
        return None, "Pedido no encontrado.", meta
    if str(cab.get("tipo_comprobante") or "").strip().upper() != "PED":
        return None, "Solo se pueden cargar pedidos (PED).", meta
    if str(cab.get("anulado") or "").strip().lower() in ("si", "sí"):
        return None, "No se puede cargar un pedido anulado.", meta

    id_cliente = to_int_or_none(cab.get("id_cliente"))
    if id_cliente is None:
        return None, "Pedido sin cliente asociado.", meta

    ctx_cliente = idcliente_contexto if idcliente_contexto is not None else id_cliente
    _, err = validar_pedido_como_plantilla(
        base_empresa,
        cod,
        sess_user,
        ctx_cliente,
        es_cliente=es_cliente,
    )
    if err:
        return None, err, meta

    id_domicilio = to_int_or_none(cab.get("id_cliente_domicilio"))
    if id_domicilio is None or id_domicilio <= 0:
        return None, "El pedido no tiene domicilio de entrega asociado.", meta

    editable = _pedido_origen_editable(cab)
    if consulta:
        editable = False
    meta["editable"] = editable
    meta["consulta"] = consulta
    meta["estado_origen"] = str(cab.get("estado") or "").strip()
    meta["cod_mov_origen"] = cod
    meta["id_domicilio_fijo"] = id_domicilio

    cv = resolver_viajante_operativo(sess_user)
    if cv is None:
        cv = to_int_or_none(cab.get("cod_viajante"))

    draft, err_draft = obtener_o_crear_draft(
        base_empresa=base_empresa,
        id_usuario=id_u,
        id_cliente=id_cliente,
        cod_viajante=cv,
        draft_id=draft_id,
        modo=EcomPedidoMasivoDraft.MODO_SIMPLE,
        id_domicilio_fijo=id_domicilio,
        cod_mov_origen=cod,
        consulta=consulta,
    )
    if err_draft or draft is None:
        return None, err_draft or "No se pudo crear el borrador.", meta

    renglones = detalle_pedido_relay(base_empresa, cod)
    advertencias: List[str] = []
    celdas_nuevas: List[EcomPedidoMasivoDraftCelda] = []

    for row in renglones:
        id_art = to_int_or_none(row.get("IDArt"))
        if id_art is None:
            continue
        salida = to_decimal_or_none(row.get("Salida")) or Decimal("0")
        if salida <= 0:
            continue
        packs, aviso = _salida_a_packs_matriz(
            base_empresa,
            id_art,
            salida,
            tipo_unidad_linea=str_or_default(row.get("tipo_unidad"), ""),
            descripcion=str_or_default(row.get("Descripcion"), ""),
        )
        if aviso:
            advertencias.append(aviso)
        if packs <= 0:
            continue
        celdas_nuevas.append(
            EcomPedidoMasivoDraftCelda(
                draft=draft,
                id_articulo=id_art,
                id_cliente_domicilio=id_domicilio,
                cantidad_packs=packs,
            )
        )

    ctx_cli = leer_contexto_cliente_masivo(base_empresa, id_cliente)
    pie_pct = to_decimal_or_none(ctx_cli.get("descPie")) or Decimal("0")

    with transaction.atomic():
        draft.celdas.all().delete()
        if celdas_nuevas:
            EcomPedidoMasivoDraftCelda.objects.bulk_create(celdas_nuevas)
        draft.modo = EcomPedidoMasivoDraft.MODO_SIMPLE
        draft.cod_mov_origen = cod
        draft.id_domicilio_fijo = id_domicilio
        draft.id_cliente = id_cliente
        if cv is not None:
            draft.cod_viajante = cv
        update_fields = [
            "modo",
            "cod_mov_origen",
            "id_domicilio_fijo",
            "id_cliente",
            "cod_viajante",
            "descuento_pie_pct",
            "updated_at",
        ]
        if consulta:
            draft.estado = EcomPedidoMasivoDraft.ESTADO_ARCHIVADO
            update_fields.insert(-1, "estado")
        draft.save(update_fields=update_fields)

    meta["advertencias"] = advertencias
    return draft, None, meta


def preview_desde_pedido(
    base_empresa: str,
    cod_mov: int,
    sess_user: Dict[str, Any],
    idcliente_contexto: Optional[int],
    cart: EcomCart,
    *,
    es_cliente: Optional[bool] = None,
    cantidades_override: Optional[Dict[int, Any]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Preview de renglones con precio actual; sin precios históricos si es_cliente."""
    if es_cliente is None:
        es_cliente = _es_cliente_sesion(sess_user)

    cab, err = validar_pedido_como_plantilla(
        base_empresa, cod_mov, sess_user, idcliente_contexto, es_cliente=es_cliente
    )
    if err:
        return None, err

    id_cliente = int(cab["id_cliente"])
    desc_cli = _descuento_cliente(base_empresa, id_cliente)
    renglones_raw = detalle_pedido_relay(base_empresa, cod_mov)
    stock_svc = StockService(base_empresa)
    filas: List[Dict[str, Any]] = []
    advertencias: List[str] = []

    for row in renglones_raw:
        id_art = to_int_or_none(row.get("IDArt"))
        if id_art is None:
            continue
        cant = cantidades_override.get(id_art) if cantidades_override else None
        if cant is None:
            cant = row.get("Salida") or row.get("Cantidad") or 0
        cant = to_decimal_or_none(cant) or Decimal("0")
        if cant <= 0:
            continue

        res = resolver_precio_articulo(
            base_empresa,
            id_art,
            lista_id=cart.lista_id,
            codigo_cliente=id_cliente,
            descuento_cliente=desc_cli,
            iva_incluido=False,
        )
        if res is None:
            advertencias.append(
                f"Artículo {row.get('Descripcion') or id_art} no disponible y no se incluirá."
            )
            continue

        precio_neto, art_row = res
        alic = to_decimal_or_none(art_row.get("alic_iva")) or Decimal("21")
        neto_r = (to_decimal_or_none(precio_neto) or Decimal("0")) * cant
        iva_r = neto_r * alic / Decimal("100")
        disp = stock_svc.get_disponible(id_art, cart.id_deposito)

        item: Dict[str, Any] = {
            "id_articulo": id_art,
            "codigo": row.get("CodigoArticulo"),
            "descripcion": row.get("Descripcion"),
            "cantidad": float(cant),
            "precio_unitario_neto": float(precio_neto),
            "subtotal_neto": float(neto_r),
            "subtotal_iva": float(iva_r),
            "subtotal_total": float(neto_r + iva_r),
            "stock_disponible": float(disp) if disp is not None else None,
            "incluido": True,
        }
        if not es_cliente:
            hist_neto = to_decimal_or_none(row.get("PrecioNetoxU"))
            if hist_neto is not None:
                item["precio_historico_unitario_neto"] = float(hist_neto)
        filas.append(item)

    if not filas:
        return None, "Ningún artículo del pedido está disponible para repetir."

    payload: Dict[str, Any] = {
        "codigo_movimiento": cod_mov,
        "nro_comprobante": cab.get("nro_comprobante"),
        "fecha": cab.get("fecha"),
        "id_cliente": id_cliente,
        "nombre_cliente": cab.get("nombre_cliente"),
        "renglones": filas,
        "advertencias": advertencias,
        "es_cliente": es_cliente,
    }
    if not es_cliente:
        payload["total_historico"] = cab.get("total")
    return payload, None


def cargar_desde_pedido(
    base_empresa: str,
    cod_mov: int,
    sess_user: Dict[str, Any],
    idcliente_contexto: Optional[int],
    cart: EcomCart,
    id_usuario: int,
    *,
    modo: str = "reemplazar",
    es_cliente: Optional[bool] = None,
    cantidades: Optional[Dict[int, Any]] = None,
    omitir_validacion_stock: bool = False,
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Carga renglones al carrito borrador."""
    if es_cliente is None:
        es_cliente = _es_cliente_sesion(sess_user)

    preview, err = preview_desde_pedido(
        base_empresa,
        cod_mov,
        sess_user,
        idcliente_contexto,
        cart,
        es_cliente=es_cliente,
        cantidades_override=cantidades,
    )
    if err or not preview:
        return None, err or "No se pudo preparar el pedido."

    if modo == "reemplazar":
        cart_svc.limpiar(cart)

    id_cliente = int(preview["id_cliente"])
    if cart.idcliente != id_cliente:
        cart.idcliente = id_cliente
        cart.save(update_fields=["idcliente", "updated_at"])

    desc_cli = _descuento_cliente(base_empresa, id_cliente)
    errores: List[str] = []
    for fila in preview["renglones"]:
        if not fila.get("incluido"):
            continue
        id_art = int(fila["id_articulo"])
        cant = fila["cantidad"]
        _item, e = cart_svc.agregar_item(
            cart,
            id_art,
            cant,
            descuento_cliente=desc_cli,
            validar_stock=not omitir_validacion_stock,
        )
        if e:
            errores.append(f"{fila.get('descripcion') or id_art}: {e}")

    if errores and not cart.items.exists():
        return None, "; ".join(errores)

    result = {
        "carrito": cart_svc.serializar_carrito(cart),
        "origen_codigo_movimiento": cod_mov,
        "origen_nro_comprobante": preview.get("nro_comprobante"),
        "advertencias": list(preview.get("advertencias") or []) + errores,
    }
    return result, None
