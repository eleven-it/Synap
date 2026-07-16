"""
Pipeline del hub Pedidos Lista|Kanban: unifica borradores Postgres + PED MySQL.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Count
from django.urls import reverse

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_int_or_none
from ecom.models import EcomCart, EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.services.alcance_comercial import alcance_viajantes_comercial
from ecom.services.pedido_masivo_matriz import listar_sucursales_cliente, obtener_o_crear_draft
from ecom.services.pedido_plantilla_service import _salida_a_packs_matriz
from ecom.services.aprobacion_pedidos import puede_aprobar_pedido
from ecom.services.ecom_config_mysql import (
    aprobacion_pedidos_activa,
    workflow_jerarquia_comercial_activo,
)
from ecom.services.pedido_permisos import puede_ver_todos_pedidos

logger = logging.getLogger(__name__)

COLUMNAS_SIN_APROBACION = (
    "borrador",
    "enviado",
    "en_curso",
    "cerrado",
    "anulado",
)

COLUMNAS_CON_APROBACION = (
    "borrador",
    "enviado",
    "por_autorizar",
    "aprobado",
    "en_curso",
    "cerrado",
    "anulado",
)

# Compat: callers/tests que esperan el conjunto completo de ids.
COLUMNAS = COLUMNAS_CON_APROBACION

_LABELS = {
    "borrador": "Borrador",
    "enviado": "Enviado",
    "por_autorizar": "Por autorizar",
    "aprobado": "Aprobado",
    "en_curso": "En curso",
    "cerrado": "Entregado / Cerrado",
    "anulado": "Anulado",
}

_ESTADOS_CERRADOS = frozenset(
    {
        "cerrado",
        "facturado",
        "entregado",
    }
)

_ESTADOS_EN_CURSO = frozenset(
    {
        "en preparación",
        "en preparacion",
        "preparado",
        "en remito",
        "parcial",
    }
)


def columnas_hub_visibles(*, aprobacion_activa: bool) -> tuple:
    """Columnas Kanban/Lista: sin Por autorizar/Aprobado si la aprobación comercial está off."""
    if aprobacion_activa:
        return COLUMNAS_CON_APROBACION
    return COLUMNAS_SIN_APROBACION


def _tarjeta(
    *,
    tipo: str,
    columna: str,
    titulo: str,
    subtitulo: str = "",
    fecha: str = "",
    url: str = "",
    id_ref: str = "",
    badge_error: bool = False,
    sucursal: str = "",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "tipo": tipo,
        "columna": columna,
        "titulo": titulo,
        "subtitulo": subtitulo,
        "fecha": fecha,
        "url": url,
        "id_ref": id_ref,
        "badge_error": badge_error,
        "sucursal": sucursal,
        "meta": meta or {},
    }


def _nombres_clientes(base_empresa: str, ids: List[int]) -> Dict[int, str]:
    """Resuelve nombres de cliente en un solo query batch."""
    unicos = sorted({i for i in ids if to_int_or_none(i) is not None})
    if not base_empresa or not unicos:
        return {}
    placeholders = ",".join(["%s"] * len(unicos))
    sql = f"""
        SELECT Codigo, COALESCE(nombre_cliente, '') AS nombre_cliente
        FROM cliente
        WHERE Codigo IN ({placeholders})
    """
    out: Dict[int, str] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, unicos)
            for row in cursor.fetchall() or []:
                cod = to_int_or_none(row.get("Codigo"))
                if cod is not None:
                    out[cod] = (row.get("nombre_cliente") or "").strip()
    except Exception as e:
        logger.warning("_nombres_clientes: %s", e)
    return out


def _etiqueta_cliente(nombre: str, id_cliente: Optional[int]) -> str:
    nombre = (nombre or "").strip()
    if nombre:
        return nombre
    idc = to_int_or_none(id_cliente)
    return f"Cliente {idc}" if idc is not None else "Cliente —"


def url_pedido_masivo_modo_simple(
    *,
    cod_mov: Optional[int] = None,
    draft: Optional[int] = None,
) -> str:
    """URL canónica de captura pedido simple (matriz 1 columna)."""
    base = reverse("ecom:mayoristapp_pedido_masivo_sucursales")
    params: List[str] = ["modo=simple"]
    if draft is not None:
        params.append(f"draft={int(draft)}")
    if cod_mov is not None:
        params.append(f"cod_mov={int(cod_mov)}")
    return f"{base}?{'&'.join(params)}"


def _etiqueta_sucursal(calle: str, nro: str, id_dom: Optional[int]) -> str:
    """Misma convención que ``listar_sucursales_cliente`` en pedido_masivo_matriz."""
    calle = (calle or "").strip()
    nro = (nro or "").strip()
    nombre_parts = [p for p in (calle, nro) if p and p != "-"]
    nombre = " ".join(nombre_parts).strip()
    if nombre:
        return nombre
    idd = to_int_or_none(id_dom)
    return f"Sucursal #{idd}" if idd is not None else ""


def _borradores_carrito_legacy(
    base_empresa: str,
    id_usuario: int,
) -> List[Dict[str, Any]]:
    """Tarjetas legacy `EcomCart` con CTA migrar/archivar (no borrador masivo estándar)."""
    qs = (
        EcomCart.objects.filter(
            base_empresa=base_empresa,
            id_usuario=id_usuario,
            estado=EcomCart.ESTADO_BORRADOR,
            tipo_comprobante=EcomCart.TIPO_PEDIDO,
        )
        .annotate(n_items=Count("items"))
        .filter(n_items__gt=0)
        .order_by("-updated_at")[:20]
    )
    ids_cliente = [c.idcliente for c in qs if c.idcliente]
    nombres = _nombres_clientes(base_empresa, ids_cliente)
    out = []
    for c in qs:
        fecha = c.updated_at.strftime("%d/%m/%Y") if c.updated_at else ""
        idc = to_int_or_none(c.idcliente)
        nombre = _etiqueta_cliente(nombres.get(idc, "") if idc is not None else "", idc)
        out.append(
            _tarjeta(
                tipo="carrito_legacy",
                columna="borrador",
                titulo=f"Carrito legacy · {nombre}",
                subtitulo=f"{c.n_items} ítems · migrar a borrador masivo",
                fecha=fecha,
                url="",
                id_ref=f"cart-legacy-{c.pk}",
                meta={
                    "cart_id": c.pk,
                    "id_cliente": c.idcliente,
                    "nombre_cliente": nombres.get(idc, "") if idc is not None else "",
                    "legacy_carrito": True,
                },
            )
        )
    return out


def _borradores_masivo(
    base_empresa: str,
    id_usuario: int,
) -> List[Dict[str, Any]]:
    qs = EcomPedidoMasivoDraft.objects.filter(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        estado__in=(
            EcomPedidoMasivoDraft.ESTADO_BORRADOR,
            EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
        ),
    ).order_by("-updated_at")[:50]
    ids_cliente = [d.id_cliente for d in qs if d.id_cliente]
    nombres = _nombres_clientes(base_empresa, ids_cliente)
    out = []
    for d in qs:
        fecha = d.updated_at.strftime("%d/%m/%Y") if d.updated_at else ""
        err = bool(d.ultimo_error)
        idc = to_int_or_none(d.id_cliente)
        nombre = _etiqueta_cliente(nombres.get(idc, "") if idc is not None else "", idc)
        es_simple = (d.modo or "").strip().lower() == EcomPedidoMasivoDraft.MODO_SIMPLE
        if es_simple:
            url = url_pedido_masivo_modo_simple(draft=d.pk)
            titulo = f"Pedido simple · {nombre}"
            subtitulo = "Error al confirmar" if err else "Borrador pedido simple"
        else:
            url = reverse("ecom:mayoristapp_pedido_masivo_sucursales") + f"?draft={d.pk}"
            titulo = f"Masivo · {nombre}"
            subtitulo = "Error al confirmar" if err else "Matriz por sucursales"
        out.append(
            _tarjeta(
                tipo="masivo",
                columna="borrador",
                titulo=titulo,
                subtitulo=subtitulo,
                fecha=fecha,
                url=url,
                id_ref=f"masivo-{d.pk}",
                badge_error=err,
                meta={
                    "draft_id": d.pk,
                    "id_cliente": d.id_cliente,
                    "nombre_cliente": nombres.get(idc, "") if idc is not None else "",
                    "modo": d.modo,
                },
            )
        )
    return out


def _masivos_anulados(
    base_empresa: str,
    id_usuario: int,
) -> List[Dict[str, Any]]:
    qs = EcomPedidoMasivoDraft.objects.filter(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        estado=EcomPedidoMasivoDraft.ESTADO_ANULADO,
    ).order_by("-updated_at")[:50]
    ids_cliente = [d.id_cliente for d in qs if d.id_cliente]
    nombres = _nombres_clientes(base_empresa, ids_cliente)
    out = []
    for d in qs:
        fecha = d.updated_at.strftime("%d/%m/%Y") if d.updated_at else ""
        idc = to_int_or_none(d.id_cliente)
        nombre = _etiqueta_cliente(nombres.get(idc, "") if idc is not None else "", idc)
        out.append(
            _tarjeta(
                tipo="masivo",
                columna="anulado",
                titulo=f"Masivo · {nombre}",
                subtitulo="Borrador anulado · Recuperable",
                fecha=fecha,
                url=reverse("ecom:mayoristapp_pedido_masivo_sucursales")
                + f"?draft={d.pk}",
                id_ref=f"masivo-anulado-{d.pk}",
                meta={
                    "draft_id": d.pk,
                    "id_cliente": d.id_cliente,
                    "nombre_cliente": nombres.get(idc, "") if idc is not None else "",
                },
            )
        )
    return out


def _columna_ped_mysql(
    anulado: str,
    autorizacion: str,
    estado: str,
    *,
    estado_aprobacion_comercial: str = "-",
    aprobacion_activa: bool = False,
) -> str:
    if (anulado or "").strip().lower() in ("si", "sí"):
        return "anulado"
    est = (estado or "").strip().lower()
    if est in _ESTADOS_CERRADOS:
        return "cerrado"

    est_com = (estado_aprobacion_comercial or "-").strip().lower()
    if aprobacion_activa:
        if est_com == "pendiente":
            return "por_autorizar"
        if est_com == "rechazado":
            return "enviado"
        auth = (autorizacion or "").strip()
        if auth == "No Autorizado":
            return "por_autorizar"
        if est in ("pendiente",):
            return "enviado"
        if est in _ESTADOS_EN_CURSO:
            return "en_curso"
        return "aprobado"

    # Sin aprobación comercial: no usar columnas Por autorizar / Aprobado.
    if est in ("pendiente",):
        return "enviado"
    if est in _ESTADOS_EN_CURSO:
        return "en_curso"
    return "enviado"


def _pedidos_mysql(
    base_empresa: str,
    sess_user: Dict[str, Any],
    *,
    dias: int = 60,
    limit: int = 200,
    aprobacion_on: Optional[bool] = None,
) -> List[Dict[str, Any]]:
    where = [
        "cp.TipoComprobante = 'PED'",
        "cp.Fecha >= DATE_SUB(CURDATE(), INTERVAL %s DAY)",
    ]
    params: List[Any] = [max(1, min(int(dias), 365))]

    tipousuario = (sess_user.get("tipousuario") or "").strip().lower()
    if tipousuario == "cliente":
        idc = to_int_or_none(sess_user.get("idcliente") or sess_user.get("Codigo"))
        if idc is not None:
            where.append("cp.Codigo = %s")
            params.append(idc)
    elif (
        puede_ver_todos_pedidos(sess_user)
        and not workflow_jerarquia_comercial_activo(base_empresa)
    ):
        pass
    else:
        alcance = alcance_viajantes_comercial(base_empresa, sess_user)
        if not alcance:
            where.append("1 = 0")
        elif len(alcance) == 1:
            where.append("cp.CodViajante = %s")
            params.append(alcance[0])
        else:
            ph = ",".join(["%s"] * len(alcance))
            where.append(f"cp.CodViajante IN ({ph})")
            params.extend(alcance)

    params.append(max(1, min(int(limit), 500)))
    if aprobacion_on is None:
        aprobacion_on = aprobacion_pedidos_activa(base_empresa)
    sql = f"""
        SELECT
            cp.CodigoMovimiento,
            cp.NroComprobante,
            DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
            cp.Estado,
            cp.Anulado,
            TRIM(COALESCE(cp.autorizacion_sistema, '')) AS autorizacion,
            TRIM(COALESCE(cp.estado_aprobacion_comercial, '-')) AS estado_aprobacion_comercial,
            cp.CodViajante,
            cp.Codigo AS id_cliente,
            COALESCE(c.nombre_cliente, '') AS nombre_cliente,
            cp.ImporteVenta,
            (cp.SubtotalDesc + cp.IVA1 + cp.IVA2 + COALESCE(cp.total_percep, 0)) AS total_calc,
            cda.id_cliente_domicilio,
            COALESCE(cd.Calle, '') AS calle_domicilio,
            COALESCE(cd.NroCalle, '') AS nro_domicilio
        FROM comp_ped cp
        LEFT JOIN cliente c ON c.Codigo = cp.Codigo
        LEFT JOIN cliente_datos_adicionales cda
          ON cda.CodigoMovimiento = cp.CodigoMovimiento
         AND cda.TipoComprobante = 'PED'
        LEFT JOIN cliente_domicilio cd
          ON cd.id_cliente_domicilio = cda.id_cliente_domicilio
        WHERE {' AND '.join(where)}
        ORDER BY cp.Fecha DESC, cp.CodigoMovimiento DESC
        LIMIT %s
    """
    out: List[Dict[str, Any]] = []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, params)
            for row in cursor.fetchall() or []:
                col = _columna_ped_mysql(
                    str(row.get("Anulado") or ""),
                    str(row.get("autorizacion") or ""),
                    str(row.get("Estado") or ""),
                    estado_aprobacion_comercial=str(
                        row.get("estado_aprobacion_comercial") or "-"
                    ),
                    aprobacion_activa=aprobacion_on,
                )
                cod = int(row["CodigoMovimiento"])
                nro = str(row.get("NroComprobante") or cod)
                id_cliente = to_int_or_none(row.get("id_cliente"))
                nombre_cliente = (row.get("nombre_cliente") or "").strip()
                cliente = _etiqueta_cliente(nombre_cliente, id_cliente)
                importe_venta = row.get("ImporteVenta")
                if importe_venta is not None and float(importe_venta or 0) > 0:
                    total = float(importe_venta)
                else:
                    total = float(row.get("total_calc") or 0)
                id_dom = to_int_or_none(row.get("id_cliente_domicilio"))
                sucursal = _etiqueta_sucursal(
                    str(row.get("calle_domicilio") or ""),
                    str(row.get("nro_domicilio") or ""),
                    id_dom,
                )
                ped_aprob = {
                    "CodigoMovimiento": cod,
                    "CodViajante": to_int_or_none(row.get("CodViajante")),
                    "estado_aprobacion_comercial": row.get("estado_aprobacion_comercial"),
                }
                puede_aprobar = (
                    aprobacion_on
                    and col == "por_autorizar"
                    and puede_aprobar_pedido(base_empresa, sess_user, ped_aprob)
                )
                est_com = str(row.get("estado_aprobacion_comercial") or "-").strip().lower()
                out.append(
                    _tarjeta(
                        tipo="ped",
                        columna=col,
                        titulo=f"PED {nro}",
                        subtitulo=f"{cliente} · ${total:,.2f}",
                        fecha=str(row.get("fecha") or ""),
                        url=url_pedido_masivo_modo_simple(cod_mov=cod),
                        id_ref=f"ped-{cod}",
                        sucursal=sucursal,
                        meta={
                            "codigo_movimiento": cod,
                            "estado": row.get("Estado"),
                            "autorizacion": row.get("autorizacion"),
                            "estado_aprobacion_comercial": row.get("estado_aprobacion_comercial"),
                            "puede_aprobar": puede_aprobar,
                            "aprobacion_comercial_activa": aprobacion_on,
                            "id_cliente": id_cliente,
                            "nombre_cliente": nombre_cliente,
                            "id_cliente_domicilio": id_dom,
                            "sucursal": sucursal,
                            "rechazado_comercial": est_com == "rechazado",
                        },
                    )
                )
    except Exception as e:
        logger.warning("pedidos_hub_pipeline MySQL: %s", e)
    return out


def construir_hub_pedidos(
    base_empresa: str,
    sess_user: Dict[str, Any],
    *,
    id_usuario: Optional[int] = None,
    vista: str = "kanban",
    dias: int = 60,
) -> Dict[str, Any]:
    """
    Devuelve columnas + items planos para Lista|Kanban.

    ``vista``: ``lista`` | ``kanban`` (solo metadato; mismos datos).
    """
    id_u = to_int_or_none(id_usuario if id_usuario is not None else sess_user.get("id_usuario"))
    aprobacion_on = aprobacion_pedidos_activa(base_empresa) if base_empresa else False
    items: List[Dict[str, Any]] = []
    if id_u is not None and base_empresa:
        items.extend(_borradores_masivo(base_empresa, id_u))
        items.extend(_borradores_carrito_legacy(base_empresa, id_u))
        items.extend(_masivos_anulados(base_empresa, id_u))
    if base_empresa:
        items.extend(
            _pedidos_mysql(
                base_empresa,
                sess_user,
                dias=dias,
                aprobacion_on=aprobacion_on,
            )
        )

    ids_visibles = columnas_hub_visibles(aprobacion_activa=aprobacion_on)
    columnas: Dict[str, List[Dict[str, Any]]] = {k: [] for k in ids_visibles}
    for it in items:
        col = it.get("columna") or "enviado"
        if col not in columnas:
            # Pedidos mid-flow sin columna visible (p. ej. aprobación off) → Enviado.
            col = "enviado" if "enviado" in columnas else ids_visibles[0]
            it = {**it, "columna": col}
        columnas[col].append(it)

    items_visibles = [it for col_items in columnas.values() for it in col_items]
    labels_visibles = {cid: _LABELS[cid] for cid in ids_visibles}
    borradores_activos = len(
        [
            it
            for it in (columnas.get("borrador") or [])
            if it.get("tipo") == "masivo"
        ]
    )
    return {
        "vista": vista if vista in ("lista", "kanban") else "kanban",
        "layout_movil": "chips_cards",
        "aprobacion_comercial_activa": aprobacion_on,
        "columnas": [
            {
                "id": cid,
                "label": _LABELS[cid],
                "count": len(columnas[cid]),
                "items": columnas[cid],
            }
            for cid in ids_visibles
        ],
        "items": items_visibles,
        "borradores_activos": borradores_activos,
        "labels": labels_visibles,
    }


def archivar_borrador_masivo(draft_id: int, id_usuario: int, base_empresa: str) -> bool:
    """Archiva un draft del usuario (para Nuevo → Masivo con confirmación)."""
    n = EcomPedidoMasivoDraft.objects.filter(
        pk=draft_id,
        id_usuario=id_usuario,
        base_empresa=base_empresa,
        estado__in=(
            EcomPedidoMasivoDraft.ESTADO_BORRADOR,
            EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
        ),
    ).update(estado=EcomPedidoMasivoDraft.ESTADO_ARCHIVADO)
    return n > 0


def archivar_carrito_legacy(cart_id: int, id_usuario: int, base_empresa: str) -> bool:
    """Descarta un borrador `EcomCart` legacy (ítems + carrito)."""
    cart = (
        EcomCart.objects.filter(
            pk=cart_id,
            id_usuario=id_usuario,
            base_empresa=base_empresa,
            estado=EcomCart.ESTADO_BORRADOR,
        )
        .first()
    )
    if not cart:
        return False
    with transaction.atomic():
        cart.items.all().delete()
        cart.delete()
    return True


def migrar_carrito_legacy_a_draft(
    cart_id: int,
    id_usuario: int,
    base_empresa: str,
    *,
    cod_viajante: Optional[int] = None,
) -> Tuple[Optional[int], Optional[str]]:
    """
    Convierte ítems de ``EcomCart`` borrador a celdas de draft masivo ``modo=simple``.
    Devuelve ``(draft_id, error)``.
    """
    cart = (
        EcomCart.objects.filter(
            pk=cart_id,
            id_usuario=id_usuario,
            base_empresa=base_empresa,
            estado=EcomCart.ESTADO_BORRADOR,
        )
        .prefetch_related("items")
        .first()
    )
    if not cart:
        return None, "Carrito no encontrado."
    id_cliente = to_int_or_none(cart.idcliente)
    if id_cliente is None:
        return None, "El carrito no tiene cliente asociado."

    sucursales = listar_sucursales_cliente(
        base_empresa,
        id_cliente,
        to_int_or_none(cod_viajante),
    )
    if not sucursales:
        return None, "El cliente no tiene sucursales activas para migrar el borrador."
    id_domicilio = to_int_or_none(sucursales[0].get("id_cliente_domicilio"))
    if id_domicilio is None:
        return None, "No se pudo resolver el domicilio del cliente."

    draft, err = obtener_o_crear_draft(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        id_cliente=id_cliente,
        cod_viajante=to_int_or_none(cod_viajante),
        modo=EcomPedidoMasivoDraft.MODO_SIMPLE,
        id_domicilio_fijo=id_domicilio,
    )
    if err or draft is None:
        return None, err or "No se pudo crear el borrador masivo."

    celdas_nuevas: List[EcomPedidoMasivoDraftCelda] = []
    for item in cart.items.all().order_by("orden", "id"):
        salida = item.cantidad or Decimal("0")
        if salida <= 0:
            continue
        packs, _aviso = _salida_a_packs_matriz(
            base_empresa,
            int(item.id_articulo),
            salida,
            tipo_unidad_linea=str(item.tipo_unidad or ""),
            descripcion=str(item.descripcion or ""),
        )
        if packs <= 0:
            continue
        celdas_nuevas.append(
            EcomPedidoMasivoDraftCelda(
                draft=draft,
                id_articulo=int(item.id_articulo),
                id_cliente_domicilio=id_domicilio,
                cantidad_packs=packs,
            )
        )

    with transaction.atomic():
        draft.celdas.all().delete()
        if celdas_nuevas:
            EcomPedidoMasivoDraftCelda.objects.bulk_create(celdas_nuevas)
        draft.modo = EcomPedidoMasivoDraft.MODO_SIMPLE
        draft.id_domicilio_fijo = id_domicilio
        draft.id_cliente = id_cliente
        draft.descuento_pie_pct = cart.descuento_pie_pct
        if cod_viajante is not None:
            draft.cod_viajante = cod_viajante
        draft.save(
            update_fields=[
                "modo",
                "id_domicilio_fijo",
                "id_cliente",
                "cod_viajante",
                "descuento_pie_pct",
                "updated_at",
            ]
        )
        cart.items.all().delete()
        cart.delete()

    return draft.pk, None
