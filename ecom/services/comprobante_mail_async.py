"""
Cola async para envío de comprobantes por mail.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction

from ecom.models import EcomMailQueue
from ecom.services.comprobante_mail_relay import obtener_comprobante_para_mail


def _build_mail_content(
    *,
    site_url: str,
    token: str,
    comprobante: Dict[str, Any],
) -> tuple[str, str, str]:
    url = f"{site_url.rstrip('/')}/fin-comprobante.php?p={token}"
    nro = comprobante.get("numerocomprobante")
    tipo = comprobante.get("tipocomprobante")
    subject = f"Comprobante {tipo} {nro}"
    body_text = (
        "Hola,\n\n"
        f"Tu comprobante {tipo} {nro} está disponible.\n"
        f"Podés visualizarlo en: {url}\n\n"
        "Mensaje automático de Synap."
    )
    body_html = (
        "<p>Hola,</p>"
        f"<p>Tu comprobante <strong>{tipo} {nro}</strong> está disponible.</p>"
        f"<p><a href=\"{url}\">Ver comprobante</a></p>"
        "<p>Mensaje automático de Synap.</p>"
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
    token = str(data["token"])
    comprobante = dict(data["comprobante"])
    subject, body_text, body_html = _build_mail_content(
        site_url=getattr(settings, "SITE_URL", "https://synap.administranet.com.ar"),
        token=token,
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


def procesar_mail_queue_item(item_id: int) -> bool:
    with transaction.atomic():
        item = EcomMailQueue.objects.select_for_update().filter(id=item_id).first()
        if item is None:
            return False
        if item.status == EcomMailQueue.STATUS_SENT:
            return True
        item.attempts += 1
        item.save(update_fields=["attempts", "updated_at"])

    try:
        msg = EmailMultiAlternatives(
            subject=item.subject,
            body=item.body_text,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@synap.local"),
            to=[item.to_email],
        )
        if item.body_html:
            msg.attach_alternative(item.body_html, "text/html")
        msg.send(fail_silently=False)
    except Exception as exc:
        EcomMailQueue.objects.filter(id=item.id).update(status=EcomMailQueue.STATUS_ERROR, last_error=str(exc)[:2000])
        return False

    EcomMailQueue.objects.filter(id=item.id).update(status=EcomMailQueue.STATUS_SENT, last_error="")
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

