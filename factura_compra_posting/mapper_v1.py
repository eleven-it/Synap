"""
Mapeo ExpedienteFacturaCompra → LegacyPostingCommandV1.
Solo lectura de modelo Synap; sin acceso MySQL legacy.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from factura_compra_captura.models import ExpedienteFacturaCompra, LineaExpedienteCompra
from factura_compra_posting.legacy_posting_command_v1 import (
    LegacyPostingCommandV1,
    PostingContextV1,
    PostingHeaderV1,
    StockLineCommandV1,
)


def _meta_block(exp: ExpedienteFacturaCompra) -> dict[str, Any]:
    m = exp.metadata or {}
    blk = m.get("posting_v1") or {}
    if not isinstance(blk, dict):
        return {}
    return blk


def _parse_date(val: Any, default: date) -> date:
    if val is None:
        return default
    if isinstance(val, date) and not isinstance(val, datetime):
        return val
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, str):
        try:
            return date.fromisoformat(val[:10])
        except ValueError:
            return default
    return default


def _decimal(val: Any, default: Decimal = Decimal("0")) -> Decimal:
    if val is None:
        return default
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except Exception:
        return default


def map_expediente_to_command_v1(
    expediente: ExpedienteFacturaCompra,
    *,
    idempotency_key: str,
) -> LegacyPostingCommandV1:
    blk = _meta_block(expediente)
    h_raw = blk.get("header") or {}
    ctx_raw = blk.get("context") or {}
    if not isinstance(h_raw, dict):
        h_raw = {}
    if not isinstance(ctx_raw, dict):
        ctx_raw = {}

    line_qs: list[LineaExpedienteCompra] = list(
        expediente.lineas.order_by("orden").all()
    )
    lines_cmd: list[StockLineCommandV1] = []
    for ln in line_qs:
        meta_ln = ln.metadata if isinstance(ln.metadata, dict) else {}
        vto_lote = None
        if meta_ln.get("vto_lote"):
            vto_lote = _parse_date(meta_ln.get("vto_lote"), date.today())
        cod_lote_raw = meta_ln.get("cod_lote")
        cod_lote = str(cod_lote_raw).strip() if cod_lote_raw else None
        lines_cmd.append(
            StockLineCommandV1(
                orden=ln.orden,
                id_art=int(ln.id_art_legacy or 0),
                cantidad=ln.cantidad,
                codigo_movimiento_oc=ln.codigo_movimiento_oc,
                codigo_movimiento_remito=ln.codigo_movimiento_remito,
                requiere_lote=bool(meta_ln.get("requiere_lote")),
                cod_lote=cod_lote or None,
                vto_lote=vto_lote,
            )
        )

    subtotal = sum(
        (ln.cantidad * ln.precio_unitario for ln in line_qs),
        start=Decimal("0"),
    )
    importe_total = _decimal(h_raw.get("importe_total"), subtotal)
    if importe_total <= 0 and subtotal > 0:
        importe_total = subtotal

    fecha_cb = _parse_date(
        h_raw.get("fecha_comprobante"),
        date.today(),
    )
    fecha_srv = _parse_date(
        ctx_raw.get("fecha_servidor"),
        fecha_cb,
    )

    vales_raw = blk.get("vales_codigos") or []
    vales_t: tuple[int, ...] = ()
    if isinstance(vales_raw, list):
        vales_t = tuple(int(x) for x in vales_raw if x is not None)

    tipo_factura = str(h_raw.get("tipo_factura") or "FA").strip().upper()
    if tipo_factura not in ("FA", "FB", "FC", "FM"):
        tipo_factura = "FA"

    header = PostingHeaderV1(
        codigo_proveedor=int(expediente.codigo_proveedor_legacy or 0),
        fecha_comprobante=fecha_cb,
        importe_total=importe_total,
        nro_comprobante_formateado=str(
            h_raw.get("nro_comprobante_formateado") or ""
        ).strip(),
        tipo_factura=tipo_factura,
        tipo_factura_cabecera=str(
            h_raw.get("tipo_factura_cabecera") or "Factura"
        ),
        origen=str(expediente.origen_datos or "MANUAL").upper(),
        id_cond_compra=int(h_raw.get("id_cond_compra") or 1),
        cond_compra_dias=str(h_raw.get("cond_compra_dias") or "0").strip(),
    )

    context = PostingContextV1(
        id_usuario_legacy=int(ctx_raw.get("id_usuario_legacy") or 1),
        id_vendedor_usuario=int(ctx_raw.get("id_vendedor_usuario") or 1),
        cod_sucursal=int(
            ctx_raw.get("cod_sucursal") or expediente.sucursal_codigo_legacy or 1
        ),
        fecha_servidor=fecha_srv,
        duplicate_check_includes_fm=bool(ctx_raw.get("duplicate_check_includes_fm")),
    )

    return LegacyPostingCommandV1(
        idempotency_key=idempotency_key,
        expediente_id=UUID(str(expediente.id)),
        synap_empresa_id=int(expediente.empresa_id),
        context=context,
        header=header,
        lines=tuple(lines_cmd),
        vales_codigos=vales_t,
    )
