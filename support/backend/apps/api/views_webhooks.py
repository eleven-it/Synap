"""Webhooks de canales (Telegram, WhatsApp, Email). Dedupe por (channel_type, external_message_id)."""
import json
import logging

from django.urls import path
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.cases.models import Message, MessageDirection, MessageSenderType
from apps.cases.services import get_or_create_case_for_channel
from apps.companies.models import Company
from apps.integrations.services import copilot_reply
from apps.integrations.telegram_outbound import send_telegram_message
from apps.system_config.services import get_first_active_channel_config

logger = logging.getLogger(__name__)


def _is_duplicate_message(channel_type: str, external_message_id: str) -> bool:
    """True si ya existe un mensaje con ese (channel_type, external_message_id)."""
    if not (channel_type and external_message_id):
        return False
    return Message.objects.filter(
        channel_type=channel_type,
        external_message_id=external_message_id,
    ).exists()


def _extract_dedupe_keys(request, channel_type: str) -> tuple[str, str]:
    """Extrae external_message_id del body según canal (stub: body.external_message_id o message.message_id)."""
    data = _get_webhook_body(request)
    ext_id = data.get("external_message_id") or (data.get("message", {}) or {}).get("message_id")
    if ext_id is not None:
        ext_id = str(ext_id).strip()
    else:
        ext_id = ""
    return channel_type, ext_id


def _get_webhook_body(request) -> dict:
    """Cuerpo del webhook: request.data (DRF) o JSON del body."""
    data = getattr(request, "data", None)
    if data is not None and isinstance(data, dict):
        return data
    try:
        body = getattr(request, "body", b"") or b""
        if body:
            return json.loads(body.decode("utf-8"))
    except (ValueError, TypeError, AttributeError):
        pass
    return {}


def _parse_telegram_message(data: dict) -> dict | None:
    """
    Extrae message o edited_message y campos: message_id, chat_id, text.
    Returns dict con message_id, chat_id, text o None si no hay mensaje con texto.
    """
    msg = data.get("message") or data.get("edited_message")
    if not msg or not isinstance(msg, dict):
        return None
    text = (msg.get("text") or "").strip()
    if not text:
        return None
    message_id = msg.get("message_id")
    chat = msg.get("chat") or {}
    chat_id = chat.get("id")
    if message_id is None or chat_id is None:
        return None
    return {"message_id": str(message_id), "chat_id": chat_id, "text": text}


@api_view(["POST"])
@permission_classes([AllowAny])
def telegram_webhook(request):
    """
    Webhook Telegram: recibe mensaje, crea/usar caso, responde con IA y envía a Telegram.
    Dedupe por (telegram, message_id). Responde 200 siempre para no reintentar por Telegram.
    """
    data = _get_webhook_body(request)
    parsed = _parse_telegram_message(data)
    channel_type = "telegram"
    if not parsed:
        ext_id = data.get("external_message_id")
        if ext_id is not None and _is_duplicate_message(channel_type, str(ext_id).strip()):
            return Response({"duplicate": True}, status=status.HTTP_200_OK)
        return Response(status=status.HTTP_200_OK)

    message_id = parsed["message_id"]
    chat_id = parsed["chat_id"]
    text = parsed["text"]

    if _is_duplicate_message(channel_type, message_id):
        return Response({"duplicate": True}, status=status.HTTP_200_OK)

    config, company_id = get_first_active_channel_config("telegram")
    if not config:
        logger.warning("Webhook Telegram: no hay config activa de canal telegram")
        return Response(status=status.HTTP_200_OK)

    token = config.get("token") or config.get("bot_token")
    if not token:
        logger.warning("Webhook Telegram: config sin token")
        return Response(status=status.HTTP_200_OK)

    if company_id is not None:
        try:
            company = Company.objects.get(pk=company_id)
        except Company.DoesNotExist:
            company = Company.objects.first()
    else:
        company = Company.objects.first()
    if not company:
        logger.warning("Webhook Telegram: no hay empresa")
        return Response(status=status.HTTP_200_OK)

    case, _ = get_or_create_case_for_channel(
        company=company,
        channel_type=channel_type,
        external_id=str(chat_id),
        support_user=None,
    )

    Message.objects.create(
        case=case,
        channel_type=channel_type,
        external_channel_id=str(chat_id),
        external_message_id=message_id,
        sender_type=MessageSenderType.USER,
        content=text,
        direction=MessageDirection.INBOUND,
    )

    reply_text, _, _ = copilot_reply(text, case=case)

    ok, err = send_telegram_message(token, chat_id, reply_text)
    if not ok:
        logger.warning("Webhook Telegram: fallo envío respuesta: %s", err)

    Message.objects.create(
        case=case,
        channel_type=channel_type,
        external_channel_id=str(chat_id),
        external_message_id="",
        sender_type=MessageSenderType.AI,
        content=reply_text,
        direction=MessageDirection.OUTBOUND,
    )

    return Response(status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def whatsapp_webhook(request):
    """Webhook WhatsApp. Dedupe por (whatsapp, external_message_id). Stub: 202."""
    channel_type, ext_id = _extract_dedupe_keys(request, "whatsapp")
    if _is_duplicate_message(channel_type, ext_id):
        return Response({"duplicate": True}, status=status.HTTP_200_OK)
    return Response(status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@permission_classes([AllowAny])
def email_webhook(request):
    """Webhook Email (inbound). Dedupe por (email, external_message_id). Stub: 202."""
    channel_type, ext_id = _extract_dedupe_keys(request, "email")
    if _is_duplicate_message(channel_type, ext_id):
        return Response({"duplicate": True}, status=status.HTTP_200_OK)
    return Response(status=status.HTTP_202_ACCEPTED)


urlpatterns = [
    path("webhooks/telegram/", telegram_webhook),
    path("webhooks/whatsapp/", whatsapp_webhook),
    path("webhooks/email/", email_webhook),
]
