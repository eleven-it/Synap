"""Serializers REST v1 — comprobantes mayoristapp."""

from __future__ import annotations

from typing import Any

# Mapeo snake_case (API v1) → camelCase (servicios legacy / PHP)
_PEDIDOS_SNAKE_TO_CAMEL: dict[str, str] = {
    "campo_busca": "campoBusca",
    "fecha_desde": "fechaDesde",
    "fecha_hasta": "fechaHasta",
    "numero_comp": "numeroComp",
    "estado_pedido": "estadoPedido",
    "tipo_pedido": "tipoPedido",
    "lista_ped": "listaPed",
    "filtra_vendedor": "filtraVendedor",
    "campo_anulado": "campoAnulado",
}


def pedidos_request_to_relay_body(data: dict[str, Any] | None) -> dict[str, Any]:
    """Normaliza el cuerpo REST v1 al dict esperado por ``listar_pedidos_relay``."""
    if not data:
        return {}
    out: dict[str, Any] = {}
    for key, value in data.items():
        relay_key = _PEDIDOS_SNAKE_TO_CAMEL.get(key, key)
        out[relay_key] = value
    return out
