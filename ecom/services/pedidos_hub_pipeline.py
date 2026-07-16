"""
Pipeline del hub Pedidos Lista|Kanban: unifica borradores Postgres + PED MySQL.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.db.models import Count
from django.urls import reverse

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_int_or_none
from ecom.models import EcomCart, EcomPedidoMasivoDraft
from ecom.services.alcance_comercial import alcance_viajantes_comercial
from ecom.services.aprobacion_pedidos import puede_aprobar_pedido
from ecom.services.ecom_config_mysql import (
    aprobacion_pedidos_activa,
    workflow_jerarquia_comercial_activo,
)
from ecom.services.pedido_permisos import puede_ver_todos_pedidos

logger = logging.getLogger(__name__)

COLUMNAS = (
    "borrador",
    "enviado",
    "por_autorizar",
    "aprobado",
    "anulado",
)

_LABELS = {
    "borrador": "Borrador",
    "enviado": "Enviado",
    "por_autorizar": "Por autorizar",
    "aprobado": "Aprobado",
    "anulado": "Anulado",
}


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


def _borradores_carrito(
    base_empresa: str,
    id_usuario: int,
) -> List[Dict[str, Any]]:
    qs = (
        EcomCart.objects.filter(
            base_empresa=base_empresa,
            id_usuario=id_usuario,
            estado=EcomCart.ESTADO_BORRADOR,
        )
        .annotate(n_items=Count("items"))
        .filter(n_items__gt=0)
        .order_by("-updated_at")[:50]
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
                tipo="carrito",
                columna="borrador",
                titulo=f"Pedido simple · {nombre}",
                subtitulo=f"{c.n_items} ítems · total ${c.total}",
                fecha=fecha,
                url=reverse("ecom:mayoristapp_venta"),
                id_ref=f"cart-{c.pk}",
                meta={
                    "cart_id": c.pk,
                    "id_cliente": c.idcliente,
                    "nombre_cliente": nombres.get(idc, "") if idc is not None else "",
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
        out.append(
            _tarjeta(
                tipo="masivo",
                columna="borrador",
                titulo=f"Masivo · {nombre}",
                subtitulo="Error al confirmar" if err else "Matriz por sucursales",
                fecha=fecha,
                url=reverse("ecom:mayoristapp_pedido_masivo_sucursales")
                + f"?draft={d.pk}",
                id_ref=f"masivo-{d.pk}",
                badge_error=err,
                meta={
                    "draft_id": d.pk,
                    "id_cliente": d.id_cliente,
                    "nombre_cliente": nombres.get(idc, "") if idc is not None else "",
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
    est_com = (estado_aprobacion_comercial or "-").strip().lower()
    if aprobacion_activa:
        if est_com == "pendiente":
            return "por_autorizar"
        if est_com == "rechazado":
            return "enviado"
        auth = (autorizacion or "").strip()
        if auth == "No Autorizado":
            return "por_autorizar"
        est = (estado or "").strip().lower()
        if est in ("pendiente",):
            return "enviado"
        return "aprobado"
    auth = (autorizacion or "").strip()
    if auth == "No Autorizado":
        return "por_autorizar"
    est = (estado or "").strip().lower()
    if est in ("pendiente",):
        return "enviado"
    return "aprobado"


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
                        url=reverse("ecom:mayoristapp_venta") + f"?cod_mov={cod}",
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
        items.extend(_borradores_carrito(base_empresa, id_u))
        items.extend(_borradores_masivo(base_empresa, id_u))
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

    columnas: Dict[str, List[Dict[str, Any]]] = {k: [] for k in COLUMNAS}
    for it in items:
        col = it.get("columna") or "enviado"
        if col not in columnas:
            col = "enviado"
        columnas[col].append(it)

    borradores_activos = len(columnas["borrador"])
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
            for cid in COLUMNAS
        ],
        "items": items,
        "borradores_activos": borradores_activos,
        "labels": _LABELS,
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
