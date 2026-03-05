"""
Conversión DTO / request payload <-> diccionarios de columnas legacy.
Siempre usa core.utils.administranet_types para INT, DATE, VARCHAR, DECIMAL.
"""
from typing import Any, Dict

from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)


def proveedor_row_to_dto(row: Dict[str, Any]) -> Dict[str, Any]:
    """Mapea una fila de proveedor+contribuyentes a DTO para API."""
    if not row:
        return {}
    return {
        "Codigo": to_int_or_none(row.get("Codigo")),
        "Nombre": str_or_default(row.get("Nombre")),
        "CUIT": str_or_default(row.get("CUIT")),
        "idIVA": to_int_or_none(row.get("idIVA")),
        "IVA": str_or_default(row.get("IVA")),
        "NroCAI": str_or_default(row.get("NroCAI")),
        "FechaCAI": to_date_or_none(row.get("FechaCAI")),
        "obliga_oc_carga_comp": str_or_default(row.get("obliga_oc_carga_comp")),
        "id_cc": to_int_or_none(row.get("id_cc")),
        "cod_ret_iva": str_or_default(row.get("cod_ret_iva")),
        "CodCatRet": to_int_or_none(row.get("CodCatRet")),
        "CodCatRetG": to_int_or_none(row.get("CodCatRetG")),
        "Tipo": str_or_default(row.get("Tipo")),
        "saldo": to_decimal_or_none(row.get("saldo")),
    }


def sucursal_row_to_dto(row: Dict[str, Any]) -> Dict[str, Any]:
    """Mapea una fila de sucursales a DTO."""
    if not row:
        return {}
    return {
        "id_sucursal": to_int_or_none(row.get("id_sucursal")),
        "nombre_sucursal": str_or_default(row.get("nombre_sucursal")),
    }


def dto_to_fact_temporalp_row(
    codigo_proveedor: int,
    id_usuario: int,
    visualiza: str = "No",
) -> Dict[str, Any]:
    """Prepara valores para INSERT/UPDATE en fact_temporalp (lock OP)."""
    return {
        "Codigo": to_int_or_none(codigo_proveedor),
        "Codusuario": to_int_or_none(id_usuario),
        "visualiza": str_or_default(visualiza, "No"),
    }
