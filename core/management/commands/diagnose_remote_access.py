"""
Diagnóstico de acceso remoto (hosts, SSL redirect, cookies seguras).

Solo lectura + logs de depuración; no modifica configuración.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand


# #region agent log
_DEBUG_LOG_CANDIDATES = (
    Path("/app/.cursor/debug-faad26.log"),
    Path("/Users/sebastian/Documents/Administranet/Proyectos/Synap-v1/Synap/.cursor/debug-faad26.log"),
)


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict, run_id: str = "access-pre"):
    payload = {
        "sessionId": "faad26",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    for path in _DEBUG_LOG_CANDIDATES:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
            break
        except OSError:
            continue
# #endregion


class Command(BaseCommand):
    help = "Diagnostica configuración que bloquea acceso remoto (ALLOWED_HOSTS, SSL, cookies)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--host-header",
            default="",
            help="Host que usa el cliente remoto (IP o dominio) para simular DisallowedHost",
        )

    def handle(self, *args, **options):
        host_header = (options.get("host_header") or "").strip()
        env = str(getattr(settings, "ENVIRONMENT", "")).strip()
        debug = bool(settings.DEBUG)
        ssl_redirect = bool(getattr(settings, "SECURE_SSL_REDIRECT", False))
        allowed = list(getattr(settings, "ALLOWED_HOSTS", []) or [])
        site_url = str(getattr(settings, "SITE_URL", "") or "")
        csrf_origins = list(getattr(settings, "CSRF_TRUSTED_ORIGINS", []) or [])
        cookie_secure = bool(getattr(settings, "SESSION_COOKIE_SECURE", False))
        csrf_secure = bool(getattr(settings, "CSRF_COOKIE_SECURE", False))
        proxy_header = getattr(settings, "SECURE_PROXY_SSL_HEADER", None)

        self.stdout.write("🔍 Diagnóstico acceso remoto Synap")
        self.stdout.write(f"   ENVIRONMENT={env} DEBUG={debug}")
        self.stdout.write(f"   SECURE_SSL_REDIRECT={ssl_redirect}")
        self.stdout.write(f"   SESSION_COOKIE_SECURE={cookie_secure} CSRF_COOKIE_SECURE={csrf_secure}")
        self.stdout.write(f"   SITE_URL={site_url or '-'}")
        self.stdout.write(f"   ALLOWED_HOSTS={allowed}")
        self.stdout.write(f"   CSRF_TRUSTED_ORIGINS={csrf_origins}")
        self.stdout.write(f"   SECURE_PROXY_SSL_HEADER={proxy_header}")

        # #region agent log
        _agent_log(
            "F",
            "diagnose_remote_access.py:settings",
            "Flags seguridad/acceso",
            {
                "environment": env,
                "debug": debug,
                "secure_ssl_redirect": ssl_redirect,
                "session_cookie_secure": cookie_secure,
                "csrf_cookie_secure": csrf_secure,
                "site_url": site_url,
                "allowed_hosts": allowed,
                "csrf_trusted_origins": csrf_origins,
                "proxy_ssl_header": list(proxy_header) if proxy_header else None,
            },
        )
        # #endregion

        host_ok = None
        if host_header:
            host_ok = (
                "*" in allowed
                or host_header in allowed
                or any(host_header.endswith(h[1:]) for h in allowed if h.startswith("."))
            )
            self.stdout.write(f"   Host '{host_header}' en ALLOWED_HOSTS={host_ok}")
            # #region agent log
            _agent_log(
                "G",
                "diagnose_remote_access.py:host",
                "Chequeo ALLOWED_HOSTS para Host remoto",
                {"host_header": host_header, "allowed": host_ok},
            )
            # #endregion

        local_status = None
        local_location = None
        local_error = None
        try:
            req = Request("http://127.0.0.1:8000/", method="GET")
            with urlopen(req, timeout=5) as resp:
                local_status = resp.status
                local_location = resp.headers.get("Location")
        except HTTPError as exc:
            local_status = exc.code
            local_location = exc.headers.get("Location") if exc.headers else None
            local_error = str(exc)
        except URLError as exc:
            local_error = str(exc.reason if hasattr(exc, "reason") else exc)
        except Exception as exc:  # noqa: BLE001 — diagnóstico
            local_error = str(exc)

        self.stdout.write(
            f"   curl local http://127.0.0.1:8000/ → status={local_status} "
            f"Location={local_location} error={local_error}"
        )
        # #region agent log
        _agent_log(
            "H",
            "diagnose_remote_access.py:local_http",
            "Respuesta HTTP local (detecta redirect SSL)",
            {
                "status": local_status,
                "location": local_location,
                "error": local_error,
                "likely_ssl_redirect": bool(
                    local_status in (301, 302) and local_location and str(local_location).startswith("https://")
                ),
            },
        )
        # #endregion

        hints = []
        if ssl_redirect and not debug:
            hints.append(
                "SECURE_SSL_REDIRECT=True: HTTP se redirige a HTTPS. "
                "Sin proxy/TLS en el servidor, el acceso por http://IP:8000 falla."
            )
        if host_header and host_ok is False:
            hints.append(
                f"Agregar '{host_header}' a ALLOWED_HOSTS en .env y reiniciar el contenedor."
            )
        if cookie_secure or csrf_secure:
            hints.append(
                "Cookies Secure=True: en HTTP puro el navegador no guarda sesión/CSRF."
            )
        # Señales típicas de staging con NAT público → LAN
        public_hints = []
        if "181.174.198.194" in allowed or host_header in ("181.174.198.194", "192.168.0.2"):
            public_hints.append(
                "Acceso desde Internet debe ser http://181.174.198.194:8100/ "
                "(NAT→192.168.0.2:8000). 192.168.0.2 solo funciona en la LAN."
            )
        if debug and not ssl_redirect:
            public_hints.append(
                "DEBUG=True ⇒ SECURE_SSL_REDIRECT=False: si localhost:8000 responde "
                "y el remoto no, el bloqueo es red/NAT/firewall, no Django SSL."
            )
        hints.extend(public_hints)

        for hint in hints:
            self.stdout.write(self.style.WARNING(f"   ⚠️  {hint}"))

        # #region agent log
        _agent_log(
            "I",
            "diagnose_remote_access.py:hints",
            "Pistas de bloqueo remoto",
            {"hints": hints, "hint_count": len(hints)},
        )
        _agent_log(
            "K",
            "diagnose_remote_access.py:nat_hint",
            "Escenario NAT público vs IP privada",
            {
                "expected_public_url": "http://181.174.198.194:8100/",
                "lan_url": "http://192.168.0.2:8000/",
                "host_header": host_header or None,
                "debug_true_ssl_off": bool(debug and not ssl_redirect),
            },
        )
        # #endregion
