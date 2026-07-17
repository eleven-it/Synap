"""
Configuración y envío de correo saliente (Postgres ``SystemConfiguration`` + fallback Django settings).
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from django.conf import settings
from django.core.mail import EmailMessage, get_connection

from core.models import SystemConfiguration

_CLAVES = {
    "enabled": "email.outbound.enabled",
    "host": "email.outbound.host",
    "port": "email.outbound.port",
    "use_tls": "email.outbound.use_tls",
    "use_ssl": "email.outbound.use_ssl",
    "username": "email.outbound.username",
    "password": "email.outbound.password",
    "from_email": "email.outbound.from_email",
    "timeout": "email.outbound.timeout",
}

_DEFAULTS = {
    "port": 587,
    "use_tls": True,
    "use_ssl": False,
    "timeout": 20,
}


def _normalizar_bool(valor: Optional[str], *, default: bool = False) -> bool:
    if valor is None:
        return default
    v = str(valor).strip().lower()
    if v in ("no", "0", "false", "off", "n"):
        return False
    if v in ("si", "sí", "1", "true", "on", "yes", "y"):
        return True
    return default


def _leer_valor_clave(key: str, default: str = "") -> str:
    obj = (
        SystemConfiguration.objects.filter(key=key, is_active=True).first()
        or SystemConfiguration.objects.filter(key=key).first()
    )
    if obj is None:
        return default
    return str(obj.value or "").strip()


def _guardar_clave(key: str, value: str, *, description: str = "") -> None:
    defaults: Dict[str, Any] = {"value": value, "is_active": True}
    if description:
        defaults["description"] = description
    SystemConfiguration.objects.update_or_create(key=key, defaults=defaults)


def _email_host_settings_util() -> bool:
    host = str(getattr(settings, "EMAIL_HOST", "localhost") or "").strip()
    if not host:
        return False
    if host.lower() in ("localhost", "127.0.0.1"):
        user = str(getattr(settings, "EMAIL_HOST_USER", "") or "").strip()
        return bool(user)
    return True


def _db_correo_habilitado() -> bool:
    enabled = _normalizar_bool(_leer_valor_clave(_CLAVES["enabled"], "false"))
    host = _leer_valor_clave(_CLAVES["host"], "")
    return enabled and bool(host)


def correo_saliente_configurado() -> bool:
    """True si hay SMTP usable (DB activa o fallback settings)."""
    if _db_correo_habilitado():
        return True
    return _email_host_settings_util()


def leer_config_correo_saliente() -> dict:
    """Lee configuración para UI; la contraseña nunca se expone."""
    pwd = _leer_valor_clave(_CLAVES["password"], "")
    port_raw = _leer_valor_clave(_CLAVES["port"], str(_DEFAULTS["port"]))
    timeout_raw = _leer_valor_clave(_CLAVES["timeout"], str(_DEFAULTS["timeout"]))
    try:
        port = int(port_raw or _DEFAULTS["port"])
    except (TypeError, ValueError):
        port = _DEFAULTS["port"]
    try:
        timeout = int(timeout_raw or _DEFAULTS["timeout"])
    except (TypeError, ValueError):
        timeout = _DEFAULTS["timeout"]
    return {
        "enabled": _normalizar_bool(_leer_valor_clave(_CLAVES["enabled"], "false")),
        "host": _leer_valor_clave(_CLAVES["host"], ""),
        "port": port,
        "use_tls": _normalizar_bool(
            _leer_valor_clave(_CLAVES["use_tls"], str(_DEFAULTS["use_tls"]).lower()),
            default=_DEFAULTS["use_tls"],
        ),
        "use_ssl": _normalizar_bool(
            _leer_valor_clave(_CLAVES["use_ssl"], str(_DEFAULTS["use_ssl"]).lower()),
            default=_DEFAULTS["use_ssl"],
        ),
        "username": _leer_valor_clave(_CLAVES["username"], ""),
        "password": "",
        "password_set": bool(pwd),
        "from_email": _leer_valor_clave(_CLAVES["from_email"], ""),
        "timeout": timeout,
    }


def guardar_config_correo_saliente(data: dict) -> dict:
    """Persiste claves en ``SystemConfiguration``. Password vacío no borra la existente."""
    if not isinstance(data, dict):
        data = {}

    if "enabled" in data:
        activo = data["enabled"] in (True, "true", "True", 1, "1", "Si", "si", "Sí")
        _guardar_clave(
            _CLAVES["enabled"],
            "true" if activo else "false",
            description="Correo saliente habilitado",
        )

    if "host" in data:
        _guardar_clave(_CLAVES["host"], str(data.get("host") or "").strip(), description="Servidor SMTP")

    if "port" in data:
        try:
            port = int(data.get("port") or _DEFAULTS["port"])
        except (TypeError, ValueError):
            port = _DEFAULTS["port"]
        _guardar_clave(_CLAVES["port"], str(port), description="Puerto SMTP")

    if "use_tls" in data:
        tls = data["use_tls"] in (True, "true", "True", 1, "1", "Si", "si", "Sí")
        _guardar_clave(_CLAVES["use_tls"], "true" if tls else "false", description="Usar STARTTLS")

    if "use_ssl" in data:
        ssl = data["use_ssl"] in (True, "true", "True", 1, "1", "Si", "si", "Sí")
        _guardar_clave(_CLAVES["use_ssl"], "true" if ssl else "false", description="Usar SSL SMTP")

    if "username" in data:
        _guardar_clave(_CLAVES["username"], str(data.get("username") or "").strip(), description="Usuario SMTP")

    if "password" in data:
        pwd = str(data.get("password") or "")
        if pwd:
            _guardar_clave(_CLAVES["password"], pwd, description="Contraseña SMTP")

    if "from_email" in data:
        _guardar_clave(
            _CLAVES["from_email"],
            str(data.get("from_email") or "").strip(),
            description="Remitente (From)",
        )

    if "timeout" in data:
        try:
            timeout = int(data.get("timeout") or _DEFAULTS["timeout"])
        except (TypeError, ValueError):
            timeout = _DEFAULTS["timeout"]
        _guardar_clave(_CLAVES["timeout"], str(timeout), description="Timeout SMTP (segundos)")

    return leer_config_correo_saliente()


def resolver_parametros_smtp() -> dict:
    """
    Resuelve parámetros SMTP.

    Prioridad: DB ``SystemConfiguration`` si ``enabled`` + ``host``; sino ``settings.EMAIL_*``.
    """
    if _db_correo_habilitado():
        cfg = leer_config_correo_saliente()
        password = _leer_valor_clave(_CLAVES["password"], "")
        from_email = cfg["from_email"] or getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@synap.local")
        return {
            "backend": getattr(settings, "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"),
            "host": cfg["host"],
            "port": cfg["port"],
            "username": cfg["username"],
            "password": password,
            "use_tls": cfg["use_tls"],
            "use_ssl": cfg["use_ssl"],
            "timeout": cfg["timeout"],
            "from_email": from_email,
            "source": "db",
        }

    return {
        "backend": getattr(settings, "EMAIL_BACKEND", "django.core.mail.backends.smtp.EmailBackend"),
        "host": getattr(settings, "EMAIL_HOST", "localhost"),
        "port": int(getattr(settings, "EMAIL_PORT", 587)),
        "username": getattr(settings, "EMAIL_HOST_USER", ""),
        "password": getattr(settings, "EMAIL_HOST_PASSWORD", ""),
        "use_tls": bool(getattr(settings, "EMAIL_USE_TLS", True)),
        "use_ssl": bool(getattr(settings, "EMAIL_USE_SSL", False)),
        "timeout": int(getattr(settings, "EMAIL_TIMEOUT", 20)),
        "from_email": getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@synap.local"),
        "source": "settings",
    }


def get_connection_correo_saliente():
    """Devuelve conexión Django SMTP según ``resolver_parametros_smtp``."""
    params = resolver_parametros_smtp()
    return get_connection(
        backend=params["backend"],
        host=params["host"],
        port=params["port"],
        username=params["username"],
        password=params["password"],
        use_tls=params["use_tls"],
        use_ssl=params["use_ssl"],
        timeout=params["timeout"],
    )


def from_email_correo_saliente() -> str:
    """Remitente efectivo para envíos."""
    return str(resolver_parametros_smtp().get("from_email") or "no-reply@synap.local")


def probar_conexion_correo_saliente(*, to_email: str | None = None) -> dict:
    """Abre conexión SMTP y opcionalmente envía un correo de prueba. Devuelve ``{ok, message}``."""
    if not correo_saliente_configurado():
        return {"ok": False, "message": "Correo saliente no configurado."}

    conn = None
    try:
        conn = get_connection_correo_saliente()
        conn.open()
        if to_email:
            msg = EmailMessage(
                subject="Prueba de correo saliente — Synap",
                body=(
                    "Este es un mensaje de prueba del correo saliente configurado en Synap.\n\n"
                    "Si lo recibiste, la configuración SMTP es correcta."
                ),
                from_email=from_email_correo_saliente(),
                to=[to_email.strip()],
                connection=conn,
            )
            msg.send(fail_silently=False)
            return {"ok": True, "message": f"Correo de prueba enviado a {to_email.strip()}."}
        return {"ok": True, "message": "Conexión SMTP verificada correctamente."}
    except Exception as exc:
        return {"ok": False, "message": f"No se pudo conectar o enviar: {exc}"}
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass
