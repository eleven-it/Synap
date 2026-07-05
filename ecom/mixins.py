"""Mixins compartidos para APIs ecom."""

from __future__ import annotations

DEPRECATION_REPLACEMENT_PEDIDOS = (
    "/ecom/api/v1/mayoristapp/comprobantes/pedidos/"
)


class DeprecationHeaderMixin:
    """Añade cabecera Deprecation en endpoints legacy."""

    deprecation_link: str = ""

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        if self.deprecation_link:
            response["Deprecation"] = "true"
            response["Link"] = f'<{self.deprecation_link}>; rel="successor-version"'
        return response
