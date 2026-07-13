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
from ecom.services.cliente_relay import cod_viajante_desde_sesion_usuario
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
        "meta": meta or {},
    }


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
    out = []
    for c in qs:
        fecha = c.updated_at.strftime("%d/%m/%Y") if c.updated_at else ""
        out.append(
            _tarjeta(
                tipo="carrito",
                columna="borrador",
                titulo=f"Pedido simple · cliente {c.idcliente or '—'}",
                subtitulo=f"{c.n_items} ítems · total ${c.total}",
                fecha=fecha,
                url=reverse("ecom:mayoristapp_compra"),
                id_ref=f"cart-{c.pk}",
                meta={"cart_id": c.pk, "id_cliente": c.idcliente},
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
    out = []
    for d in qs:
        fecha = d.updated_at.strftime("%d/%m/%Y") if d.updated_at else ""
        err = bool(d.ultimo_error)
        out.append(
            _tarjeta(
                tipo="masivo",
                columna="borrador",
                titulo=f"Masivo · cliente {d.id_cliente}",
                subtitulo="Error al confirmar" if err else "Matriz por sucursales",
                fecha=fecha,
                url=reverse("ecom:mayoristapp_pedido_masivo_sucursales")
                + f"?draft={d.pk}",
                id_ref=f"masivo-{d.pk}",
                badge_error=err,
                meta={"draft_id": d.pk, "id_cliente": d.id_cliente},
            )
        )
    return out


def _columna_ped_mysql(
    anulado: str,
    autorizacion: str,
    estado: str,
) -> str:
    if (anulado or "").strip().lower() in ("si", "sí"):
        return "anulado"
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
    elif not puede_ver_todos_pedidos(sess_user):
        cv = cod_viajante_desde_sesion_usuario(sess_user)
        if cv is not None:
            where.append("cp.CodViajante = %s")
            params.append(cv)

    params.append(max(1, min(int(limit), 500)))
    sql = f"""
        SELECT
            cp.CodigoMovimiento,
            cp.NroComprobante,
            DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
            cp.Estado,
            cp.Anulado,
            TRIM(COALESCE(cp.autorizacion_sistema, '')) AS autorizacion,
            cp.Codigo AS id_cliente,
            COALESCE(c.nombre_cliente, '') AS nombre_cliente,
            (cp.SubtotalDesc + cp.IVA1 + cp.IVA2 + COALESCE(cp.total_percep, 0)) AS total
        FROM comp_ped cp
        LEFT JOIN cliente c ON c.Codigo = cp.Codigo
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
                )
                cod = int(row["CodigoMovimiento"])
                nro = str(row.get("NroComprobante") or cod)
                cliente = (row.get("nombre_cliente") or "").strip() or f"Cliente {row.get('id_cliente')}"
                total = float(row.get("total") or 0)
                out.append(
                    _tarjeta(
                        tipo="ped",
                        columna=col,
                        titulo=f"PED {nro}",
                        subtitulo=f"{cliente} · ${total:,.2f}",
                        fecha=str(row.get("fecha") or ""),
                        url=reverse("ecom:mayoristapp_pedido_detalle", args=[cod]),
                        id_ref=f"ped-{cod}",
                        meta={
                            "codigo_movimiento": cod,
                            "estado": row.get("Estado"),
                            "autorizacion": row.get("autorizacion"),
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
    items: List[Dict[str, Any]] = []
    if id_u is not None and base_empresa:
        items.extend(_borradores_carrito(base_empresa, id_u))
        items.extend(_borradores_masivo(base_empresa, id_u))
    if base_empresa:
        items.extend(_pedidos_mysql(base_empresa, sess_user, dias=dias))

    columnas: Dict[str, List[Dict[str, Any]]] = {k: [] for k in COLUMNAS}
    for it in items:
        col = it.get("columna") or "enviado"
        if col not in columnas:
            col = "enviado"
        columnas[col].append(it)

    borradores_activos = len(columnas["borrador"])
    return {
        "vista": vista if vista in ("lista", "kanban") else "kanban",
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
