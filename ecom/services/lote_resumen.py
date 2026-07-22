"""
Resumen consolidado de un lote masivo confirmado (reconciliación draft ↔ PED MySQL).
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_decimal_or_none, to_int_or_none

from ecom.models import EcomPedidoMasivoDraft
from ecom.services.aprobacion_pedidos import puede_aprobar_lote
from ecom.services.batch_checkout_masivo import _agrupar_por_sucursal, _mapa_nombres_sucursales
from ecom.services.ecom_config_mysql import aprobacion_pedidos_activa
from ecom.services.pedido_masivo_matriz import _nombre_cliente, listar_sucursales_cliente
from ecom.services.pedidos_hub_pipeline import (
    _columna_ped_mysql,
    _draft_en_alcance_hub,
    _etiqueta_sucursal,
    url_pedido_masivo_modo_simple,
    url_resumen_lote_masivo,
)

logger = logging.getLogger(__name__)


class LoteResumenError(Exception):
    """Error de acceso o estado al construir el resumen."""

    def __init__(self, message: str, *, status: int = 404):
        super().__init__(message)
        self.message = message
        self.status = status


def _fetch_pedidos_lote_detalle(
    base_empresa: str,
    codigos: List[int],
) -> Dict[int, Dict[str, Any]]:
    unicos = sorted({c for c in codigos if to_int_or_none(c) is not None})
    if not base_empresa or not unicos:
        return {}
    placeholders = ",".join(["%s"] * len(unicos))
    sql = f"""
        SELECT
            cp.CodigoMovimiento,
            cp.NroComprobante,
            cp.Anulado,
            cp.Estado,
            TRIM(COALESCE(cp.autorizacion_sistema, '')) AS autorizacion,
            TRIM(COALESCE(cp.estado_aprobacion_comercial, '-')) AS estado_aprobacion_comercial,
            cp.ImporteVenta,
            (cp.SubtotalDesc + cp.IVA1 + cp.IVA2 + COALESCE(cp.total_percep, 0)) AS total_calc,
            cda.id_cliente_domicilio,
            COALESCE(cd.Calle, '') AS calle_domicilio,
            COALESCE(cd.NroCalle, '') AS nro_domicilio
        FROM comp_ped cp
        LEFT JOIN cliente_datos_adicionales cda
          ON cda.CodigoMovimiento = cp.CodigoMovimiento
         AND cda.TipoComprobante = 'PED'
        LEFT JOIN cliente_domicilio cd
          ON cd.id_cliente_domicilio = cda.id_cliente_domicilio
        WHERE cp.TipoComprobante = 'PED'
          AND cp.CodigoMovimiento IN ({placeholders})
    """
    out: Dict[int, Dict[str, Any]] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, unicos)
            for row in cursor.fetchall() or []:
                cod = to_int_or_none(row.get("CodigoMovimiento"))
                if cod is not None:
                    out[cod] = dict(row)
    except Exception as exc:
        logger.warning("_fetch_pedidos_lote_detalle: %s", exc)
    return out


def _mapa_cod_mov_por_domicilio(
    draft: EcomPedidoMasivoDraft,
    codigos: List[int],
    pedidos: Dict[int, Dict[str, Any]],
) -> Dict[int, int]:
    """``id_cliente_domicilio → cod_mov`` (MySQL + fallback orden checkout)."""
    por_dom: Dict[int, int] = {}
    for cod, row in pedidos.items():
        id_dom = to_int_or_none(row.get("id_cliente_domicilio"))
        if id_dom is not None:
            por_dom[id_dom] = cod

    faltantes = [c for c in codigos if c not in pedidos or to_int_or_none(
        pedidos[c].get("id_cliente_domicilio")
    ) is None]
    if faltantes:
        doms_ordenados = sorted(_agrupar_por_sucursal(draft).keys())
        for idx, cod in enumerate(codigos):
            if cod not in faltantes:
                continue
            if idx < len(doms_ordenados):
                id_dom = int(doms_ordenados[idx])
                if id_dom not in por_dom:
                    por_dom[id_dom] = cod
    return por_dom


def _estado_operativo_etiqueta(
    row: Optional[Dict[str, Any]],
    *,
    aprobacion_on: bool,
) -> str:
    if not row:
        return "no_generada"
    if (row.get("Anulado") or "").strip().lower() in ("si", "sí"):
        return "anulada"
    col = _columna_ped_mysql(
        str(row.get("Anulado") or ""),
        str(row.get("autorizacion") or ""),
        str(row.get("Estado") or ""),
        estado_aprobacion_comercial=str(row.get("estado_aprobacion_comercial") or "-"),
        aprobacion_activa=aprobacion_on,
    )
    if col == "anulado":
        return "anulada"
    if col in ("en_curso", "aprobado", "por_autorizar", "enviado", "cerrado"):
        return col
    return str(row.get("Estado") or "en_curso").strip().lower() or "en_curso"


def _etiqueta_estado_operativo(codigo: str) -> str:
    mapa = {
        "anulada": "Anulada",
        "no_generada": "No generada",
        "por_autorizar": "Por autorizar",
        "aprobado": "Aprobado",
        "en_curso": "En preparación",
        "enviado": "Pendiente",
        "cerrado": "Cerrado",
    }
    return mapa.get(codigo, codigo.replace("_", " ").capitalize())


def _etiqueta_estado_comercial(valor: str) -> str:
    v = (valor or "-").strip().lower()
    mapa = {
        "-": "—",
        "pendiente": "Pendiente",
        "aprobado": "Aprobado",
        "rechazado": "Rechazado",
    }
    return mapa.get(v, valor)


def cargar_draft_resumen(
    base_empresa: str,
    draft_id: int,
    sess_user: Dict[str, Any],
) -> EcomPedidoMasivoDraft:
    """Carga draft confirmado en alcance; lanza ``LoteResumenError`` si no aplica."""
    if not base_empresa:
        raise LoteResumenError("Sin base_empresa.", status=400)
    draft = EcomPedidoMasivoDraft.objects.filter(
        pk=draft_id,
        base_empresa=base_empresa,
    ).first()
    if not draft:
        raise LoteResumenError("Lote no encontrado.", status=404)
    if draft.estado != EcomPedidoMasivoDraft.ESTADO_CONFIRMADO:
        raise LoteResumenError("El lote no está confirmado.", status=404)
    if not _draft_en_alcance_hub(draft, sess_user, base_empresa):
        raise LoteResumenError("No tiene permiso para ver este lote.", status=403)
    return draft


def construir_resumen_lote(
    base_empresa: str,
    draft_id: int,
    sess_user: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Payload del resumen: cabecera lote, sucursales reconciliadas y totales.

    Reconcilia ``codigos_movimiento[]`` con PED MySQL (activo / Anulada / No generada).
    """
    draft = cargar_draft_resumen(base_empresa, draft_id, sess_user)
    aprobacion_on = aprobacion_pedidos_activa(base_empresa)
    codigos = [
        c for c in (to_int_or_none(x) for x in (draft.codigos_movimiento or []))
        if c is not None
    ]
    pedidos = _fetch_pedidos_lote_detalle(base_empresa, codigos)
    cod_por_dom = _mapa_cod_mov_por_domicilio(draft, codigos, pedidos)
    nombres_suc = _mapa_nombres_sucursales(draft)
    por_dom = _agrupar_por_sucursal(draft)
    sucs_vcm = listar_sucursales_cliente(
        base_empresa, draft.id_cliente, cod_viajante=draft.cod_viajante
    )
    ids_vcm = {
        sid
        for s in sucs_vcm
        if (sid := to_int_or_none(s.get("id_cliente_domicilio"))) is not None
    }
    if ids_vcm:
        doms_con_ped = set(cod_por_dom.keys())
        doms_esperados = sorted(
            d for d in por_dom.keys() if d in ids_vcm or d in doms_con_ped
        )
    else:
        doms_esperados = sorted(por_dom.keys())

    sucursales: List[Dict[str, Any]] = []
    importe_total = Decimal("0")
    ped_vivos = 0

    for id_dom in doms_esperados:
        nombre = nombres_suc.get(id_dom) or f"Sucursal #{id_dom}"
        cod_mov = cod_por_dom.get(id_dom)
        row = pedidos.get(cod_mov) if cod_mov is not None else None
        if cod_mov is None:
            estado_op = "no_generada"
        else:
            estado_op = _estado_operativo_etiqueta(row, aprobacion_on=aprobacion_on)
        presente = estado_op not in ("anulada", "no_generada")
        if presente and row:
            ped_vivos += 1
            imp = to_decimal_or_none(row.get("ImporteVenta"))
            if imp is None or imp <= 0:
                imp = to_decimal_or_none(row.get("total_calc")) or Decimal("0")
            importe_total += imp

        nro = ""
        est_com = "-"
        url_ped = ""
        if row and cod_mov is not None:
            nro = str(row.get("NroComprobante") or cod_mov)
            est_com = str(row.get("estado_aprobacion_comercial") or "-")
            if presente:
                url_ped = url_pedido_masivo_modo_simple(cod_mov=cod_mov)

        sucursales.append(
            {
                "id_cliente_domicilio": id_dom,
                "nombre": nombre,
                "cod_mov": cod_mov,
                "nro": nro,
                "estado_operativo": estado_op,
                "estado_operativo_label": _etiqueta_estado_operativo(estado_op),
                "estado_comercial": est_com,
                "estado_comercial_label": _etiqueta_estado_comercial(est_com),
                "presente": presente,
                "importe": float(
                    to_decimal_or_none(row.get("ImporteVenta") if row else None)
                    or to_decimal_or_none(row.get("total_calc") if row else None)
                    or Decimal("0")
                ),
                "url": url_ped,
            }
        )

    n_esperadas = len(doms_esperados)
    fecha_conf = draft.updated_at.strftime("%d/%m/%Y") if draft.updated_at else ""
    estado_lote = (
        draft.estado_aprobacion_lote or EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_NEUTRO
    )

    return {
        "ok": True,
        "lote": {
            "draft_id": draft.pk,
            "cliente": _nombre_cliente(base_empresa, draft.id_cliente),
            "id_cliente": draft.id_cliente,
            "cod_viajante": draft.cod_viajante,
            "fecha": fecha_conf,
            "fecha_confirmacion": fecha_conf,
            "n_sucursales": n_esperadas,
            "estado_aprobacion_lote": estado_lote,
            "estado_aprobacion_lote_label": _etiqueta_estado_comercial(estado_lote),
            "puede_aprobar_lote": (
                aprobacion_on and puede_aprobar_lote(base_empresa, sess_user, draft)
            ),
            "aprobacion_comercial_activa": aprobacion_on,
            "contador_pedidos": f"{ped_vivos}/{n_esperadas}",
            "totales": {
                "ped_vivos": ped_vivos,
                "ped_esperados": n_esperadas,
                "importe": float(importe_total),
            },
            "url_matriz_readonly": reverse_matriz_readonly(draft.pk),
            "url_resumen": url_resumen_lote_masivo(draft.pk),
        },
        "sucursales": sucursales,
    }


def reverse_matriz_readonly(draft_id: int) -> str:
    """URL de la matriz en solo lectura para el iframe del resumen (``embed=1``)."""
    from django.urls import reverse

    base = reverse("ecom:mayoristapp_pedido_masivo_sucursales")
    return f"{base}?draft={int(draft_id)}&readonly=1&embed=1"
