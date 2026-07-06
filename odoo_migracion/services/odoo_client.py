"""Cliente HTTP JSON-2 para Odoo 19."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, TYPE_CHECKING

import requests
from django.utils.translation import gettext_lazy as _

if TYPE_CHECKING:
    from odoo_migracion.models import OdooConnection

logger = logging.getLogger(__name__)


class OdooApiError(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None, payload: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.payload = payload


class OdooJson2Client:
    """Wrapper sobre POST /json/2/<modelo>/<método> (Odoo 19)."""

    def __init__(
        self,
        connection: "OdooConnection",
        *,
        timeout_seconds: Optional[int] = None,
    ):
        self.connection = connection
        self.timeout = timeout_seconds or connection.timeout_seconds or 60
        self.base_url = (connection.base_url or "").rstrip("/")
        self.database = (connection.database or "").strip()
        self.api_key = connection.get_api_key()

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Authorization": f"bearer {self.api_key}",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Synap-odoo_migracion/1.0",
        }
        if self.database:
            headers["X-Odoo-Database"] = self.database
        return headers

    def call(self, model: str, method: str, payload: Optional[Dict[str, Any]] = None) -> Any:
        if not self.base_url:
            raise OdooApiError(_("Falta la URL base de Odoo en la conexión."))
        if not self.api_key:
            raise OdooApiError(_("No hay API key configurada para esta conexión."))

        url = f"{self.base_url}/json/2/{model}/{method}"
        body = payload or {}
        try:
            response = requests.post(
                url,
                headers=self._headers(),
                json=body,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            logger.warning("Odoo JSON-2 error de red %s %s: %s", model, method, exc)
            raise OdooApiError(_("Error de red al contactar Odoo: %s") % exc) from exc

        if response.status_code >= 400:
            err_payload = None
            try:
                err_payload = response.json()
                message = err_payload.get("message") or str(err_payload)
            except ValueError:
                message = response.text or response.reason
            raise OdooApiError(
                _("Odoo respondió con error (%(code)s): %(msg)s")
                % {"code": response.status_code, "msg": message},
                status_code=response.status_code,
                payload=err_payload,
            )

        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise OdooApiError(_("Respuesta Odoo no es JSON válido.")) from exc

    def search_read(
        self,
        model: str,
        *,
        domain: Optional[List] = None,
        fields: Optional[List[str]] = None,
        limit: int = 80,
        offset: int = 0,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        payload: Dict[str, Any] = {
            "domain": domain or [],
            "fields": fields or [],
            "limit": limit,
            "offset": offset,
        }
        if context:
            payload["context"] = context
        result = self.call(model, "search_read", payload)
        return result if isinstance(result, list) else []

    def create(self, model: str, vals: Dict[str, Any], *, context: Optional[Dict[str, Any]] = None) -> Any:
        payload: Dict[str, Any] = {"vals": vals}
        if context:
            payload["context"] = context
        return self.call(model, "create", payload)

    def write(
        self,
        model: str,
        ids: List[int],
        vals: Dict[str, Any],
        *,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        payload: Dict[str, Any] = {"ids": ids, "vals": vals}
        if context:
            payload["context"] = context
        return self.call(model, "write", payload)

    def smoke_test(self) -> Dict[str, Any]:
        """Verifica conectividad y credenciales."""
        ctx = self.call("res.users", "context_get", {})
        return {"ok": True, "context": ctx}
