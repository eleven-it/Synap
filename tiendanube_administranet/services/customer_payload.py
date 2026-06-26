"""Normalización de payloads cliente → AdministraNET (administranet_types)."""

from typing import Any, Dict

from core.utils.administranet_types import str_or_default, to_int_or_none

_INT_FIELDS = frozenset({
    'IDDistrito', 'CodProvincia', 'IDDepartamento', 'IDIva', 'CodViajante',
    'TipoCliente', 'id_tiendanube', 'Credito', 'Descuento',
})


def normalize_adminet_customer_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """Valida y normaliza tipos antes de INSERT/UPDATE en tabla cliente."""
    normalized: Dict[str, Any] = {}
    for key, value in data.items():
        if key in _INT_FIELDS:
            normalized[key] = to_int_or_none(value)
        elif isinstance(value, str) or value is None:
            normalized[key] = str_or_default(value, '-')
        else:
            normalized[key] = value
    return normalized
