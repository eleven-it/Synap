"""
Cliente HTTP para la API del ERP Synap. Autenticación JWT firmado.
No importar código desde Synap; solo requests HTTP.
"""
import logging
import time
from typing import Any

import jwt
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


class SynapClientError(Exception):
    """Error en llamada a Synap API."""
    def __init__(self, message: str, status_code: int | None = None, response_body: Any = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class SynapClient:
    """
    Cliente para la API interna de Synap.
    - base_url desde SUPPORT_SYNAP_API_URL
    - JWT firmado con SUPPORT_SYNAP_JWT_SECRET
    - Retries con backoff, timeouts
    """

    def __init__(
        self,
        base_url: str | None = None,
        jwt_secret: str | None = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        self.base_url = (base_url or getattr(settings, "SUPPORT_SYNAP_API_URL", "")).rstrip("/")
        self.jwt_secret = jwt_secret or getattr(settings, "SUPPORT_SYNAP_JWT_SECRET", "")
        self.timeout = timeout
        self.max_retries = max_retries
        self._token: str | None = None
        self._token_exp: float = 0

    def _get_token(self) -> str:
        """Obtiene o genera JWT para autenticación."""
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        if not self.jwt_secret:
            return ""
        payload = {"sub": "support-service", "exp": int(time.time()) + 3600}
        self._token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        if isinstance(self._token, bytes):
            self._token = self._token.decode()
        self._token_exp = time.time() + 3600
        return self._token

    def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        idempotency_key: str | None = None,
    ) -> dict:
        if not self.base_url:
            raise SynapClientError("SUPPORT_SYNAP_API_URL no configurado")
        url = f"{self.base_url}{path}"
        headers = {"Content-Type": "application/json"}
        token = self._get_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        last_error = None
        for attempt in range(self.max_retries):
            try:
                r = requests.request(
                    method,
                    url,
                    json=json,
                    headers=headers,
                    timeout=self.timeout,
                )
                if r.status_code >= 400:
                    raise SynapClientError(
                        f"Synap API error: {r.status_code}",
                        status_code=r.status_code,
                        response_body=r.text,
                    )
                return r.json() if r.content else {}
            except requests.RequestException as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        raise SynapClientError(str(last_error))

    def get_empresas(self) -> list[dict]:
        """Lista empresas. Stub/contrato: GET /api/empresas o similar."""
        try:
            return self._request("GET", "/api/empresas/").get("results", [])
        except SynapClientError:
            return []

    def get_empresa(self, synap_id: str) -> dict | None:
        """Detalle empresa por synap_id."""
        try:
            return self._request("GET", f"/api/empresas/{synap_id}/")
        except SynapClientError as e:
            if e.status_code == 404:
                return None
            raise
