"""
Interfaces y stubs de adaptadores de canal.
Contrato: validar webhook, parsear mensaje, enviar respuesta.
"""
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class InboundMessage:
    """Mensaje entrante normalizado."""
    channel_type: str
    external_id: str
    text: str
    attachments: list[dict]
    timestamp: Any
    raw_payload: dict


@dataclass
class SendResult:
    """Resultado de envío por canal."""
    success: bool
    error: str | None = None


class BaseChannelAdapter:
    """Interfaz común para canales."""

    channel_type: str = ""

    def validate_webhook(self, request) -> bool:
        """Valida firma del webhook. Stub: True."""
        return True

    def parse_webhook(self, request) -> InboundMessage | None:
        """Parsea el cuerpo del webhook a InboundMessage. Stub: None."""
        return None

    def send_message(self, external_id: str, text: str, attachments: list[dict] | None = None) -> SendResult:
        """Envía mensaje al usuario por el canal. Stub: log."""
        logger.info("send_message stub %s", self.channel_type, extra={"external_id": external_id})
        return SendResult(success=True)


class TelegramAdapter(BaseChannelAdapter):
    channel_type = "telegram"

    def parse_webhook(self, request) -> InboundMessage | None:
        body = getattr(request, "data", None) or request.body
        if not body:
            return None
        import json
        try:
            d = json.loads(body) if isinstance(body, (bytes, str)) else body
            msg = d.get("message", {})
            return InboundMessage(
                channel_type="telegram",
                external_id=str(msg.get("from", {}).get("id", "")),
                text=msg.get("text", ""),
                attachments=[],
                timestamp=msg.get("date"),
                raw_payload=d,
            )
        except Exception:
            return None


class WhatsAppAdapter(BaseChannelAdapter):
    channel_type = "whatsapp"


class EmailAdapter(BaseChannelAdapter):
    channel_type = "email"
