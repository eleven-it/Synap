"""
Envío de mensajes salientes a Telegram vía Bot API.
Usado por el webhook para responder al usuario.
"""
import json
import logging
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)


def send_telegram_message(
    token: str,
    chat_id: str | int,
    text: str,
    timeout: int = 10,
) -> tuple[bool, str | None]:
    """
    Envía un mensaje de texto al chat de Telegram.
    Returns (success, error_message). error_message es None si success es True.
    """
    if not (token and str(chat_id).strip()):
        return False, "Faltan token o chat_id"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text or "(sin texto)",
        "disable_web_page_preview": True,
    }
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode()
            out = json.loads(body) if body else {}
        if out.get("ok"):
            return True, None
        return False, out.get("description", "sendMessage no ok")
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode()
            err_data = json.loads(err_body)
            msg = err_data.get("description", err_body)
        except Exception:
            msg = str(e)
        logger.warning("Telegram sendMessage HTTP error: %s", msg)
        return False, msg
    except Exception as e:
        logger.exception("Telegram sendMessage failed")
        return False, str(e)
