"""
Cola async para envío de comprobantes por mail.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.urls import reverse

from core.services.outbound_email import (
    correo_saliente_configurado,
    from_email_correo_saliente,
    get_connection_correo_saliente,
)
from ecom.models import EcomMailQueue
from ecom.services.comprobante_mail_relay import obtener_comprobante_para_mail

logger = logging.getLogger(__name__)


def _build_mail_content(
    *,
    site_url: str,
    cod_mov: int,
    comprobante: Dict[str, Any],
) -> tuple[str, str, str]:
    nro = comprobante.get("numerocomprobante")
    tipo = str(comprobante.get("tipocomprobante") or "").strip()
    tipo_upper = tipo.upper()

    pdf_url = ""
    if tipo_upper == "PED" and cod_mov:
        pdf_path = reverse("ecom:mayoristapp_pedido_pdf", args=[int(cod_mov)])
        pdf_url = f"{site_url.rstrip('/')}{pdf_path}"

    subject = f"Comprobante {tipo} {nro}"

    if pdf_url:
        body_text = (
            "Estimado cliente,\n\n"
            f"Confirmamos su pedido {tipo} N.º {nro}.\n"
            f"Puede descargar el comprobante en PDF desde el siguiente enlace:\n{pdf_url}\n\n"
            "Ante cualquier consulta, no dude en contactarnos.\n\n"
            "Atentamente,\n"
            "Equipo comercial — Synap"
        )
        body_html = (
            "<p>Estimado cliente,</p>"
            f"<p>Confirmamos su pedido <strong>{tipo} N.º {nro}</strong>.</p>"
            f"<p>Puede descargar el comprobante en PDF desde el siguiente enlace:</p>"
            f"<p><a href=\"{pdf_url}\">Descargar comprobante (PDF)</a></p>"
            "<p>Ante cualquier consulta, no dude en contactarnos.</p>"
            "<p>Atentamente,<br>Equipo comercial — Synap</p>"
        )
    else:
        body_text = (
            "Estimado cliente,\n\n"
            f"Le informamos que su comprobante {tipo} N.º {nro} ha sido registrado correctamente.\n\n"
            "Ante cualquier consulta, no dude en contactarnos.\n\n"
            "Atentamente,\n"
            "Equipo comercial — Synap"
        )
        body_html = (
            "<p>Estimado cliente,</p>"
            f"<p>Le informamos que su comprobante <strong>{tipo} N.º {nro}</strong> "
            "ha sido registrado correctamente.</p>"
            "<p>Ante cualquier consulta, no dude en contactarnos.</p>"
            "<p>Atentamente,<br>Equipo comercial — Synap</p>"
        )

    return subject, body_text, body_html


def encolar_comprobante_mail(
    *,
    base_empresa: str,
    cod_mov: int,
    tipo_comp: int,
    to_email: str,
    idcliente: Optional[int] = None,
) -> Optional[EcomMailQueue]:
    data = obtener_comprobante_para_mail(base_empresa, cod_mov, tipo_comp, idcliente=idcliente)
    if not data:
        return None
    comprobante = dict(data["comprobante"])
    subject, body_text, body_html = _build_mail_content(
        site_url=getattr(settings, "SITE_URL", "https://synap.administranet.com.ar"),
        cod_mov=cod_mov,
        comprobante=comprobante,
    )
    return EcomMailQueue.objects.create(
        base_empresa=base_empresa,
        to_email=to_email.strip(),
        subject=subject,
        body_text=body_text,
        body_html=body_html,
        payload_json=data,
    )


def _adjuntar_pdf_pedido_si_aplica(msg: EmailMultiAlternatives, item: EcomMailQueue) -> None:
    payload = item.payload_json or {}
    comprobante = payload.get("comprobante") or {}
    tipo = str(comprobante.get("tipocomprobante") or "").strip().upper()
    cod_mov = comprobante.get("codigomovimiento")
    if tipo != "PED" or not cod_mov or not item.base_empresa:
        return
    try:
        from ecom.services.pedido_comprobante_pdf import generar_pedido_pdf

        ok, _err, pdf_bytes = generar_pedido_pdf(item.base_empresa, int(cod_mov))
        if ok and pdf_bytes:
            nro = comprobante.get("numerocomprobante") or cod_mov
            msg.attach(f"pedido_{nro}.pdf", pdf_bytes, "application/pdf")
    except Exception:
        logger.exception(
            "No se pudo adjuntar PDF del pedido cod_mov=%s (se envía solo el cuerpo)",
            cod_mov,
        )


def procesar_mail_queue_item(item_id: int) -> bool:
    with transaction.atomic():
        item = EcomMailQueue.objects.select_for_update().filter(id=item_id).first()
        if item is None:
            return False
        if item.status == EcomMailQueue.STATUS_SENT:
            return True
        item.attempts += 1
        item.save(update_fields=["attempts", "updated_at"])

    if not correo_saliente_configurado():
        EcomMailQueue.objects.filter(id=item_id).update(
            status=EcomMailQueue.STATUS_ERROR,
            last_error="Correo saliente no configurado",
        )
        return False

    try:
        connection = get_connection_correo_saliente()
        msg = EmailMultiAlternatives(
            subject=item.subject,
            body=item.body_text,
            from_email=from_email_correo_saliente(),
            to=[item.to_email],
            connection=connection,
        )
        if item.body_html:
            msg.attach_alternative(item.body_html, "text/html")
        _adjuntar_pdf_pedido_si_aplica(msg, item)
        msg.send(fail_silently=False)
    except Exception as exc:
        EcomMailQueue.objects.filter(id=item_id).update(
            status=EcomMailQueue.STATUS_ERROR,
            last_error=str(exc)[:2000],
        )
        return False

    EcomMailQueue.objects.filter(id=item_id).update(
        status=EcomMailQueue.STATUS_SENT,
        last_error="",
    )
    return True


def procesar_mail_queue_batch(*, limit: int = 50, include_errors: bool = False, max_attempts: int = 5) -> Dict[str, int]:
    lim = max(1, min(int(limit), 500))
    max_try = max(1, min(int(max_attempts), 20))
    statuses = [EcomMailQueue.STATUS_PENDING]
    if include_errors:
        statuses.append(EcomMailQueue.STATUS_ERROR)

    ids = list(
        EcomMailQueue.objects.filter(status__in=statuses, attempts__lt=max_try)
        .order_by("created_at")
        .values_list("id", flat=True)[:lim]
    )
    enviados = 0
    errores = 0
    for item_id in ids:
        ok = procesar_mail_queue_item(item_id)
        if ok:
            enviados += 1
        else:
            errores += 1
    return {"procesados": len(ids), "enviados": enviados, "errores": errores}
