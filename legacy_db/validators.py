"""
Reglas de negocio idénticas a VB6 para comprobantes de compra.
Los servicios deben llamar a estos validadores antes de escribir en tablas legacy.
"""
from datetime import date
from typing import Optional, Tuple

from core.utils.administranet_types import to_date_or_none, to_int_or_none


# Códigos de error para API (errores tipados, sin cambiar reglas)
class PrecheckError:
    CAI_VENCIDO = "CAI_VENCIDO"
    REQUIERE_OC = "REQUIERE_OC"
    OP_BLOQUEADA = "OP_BLOQUEADA"
    SIN_FACTURAS_IMPUTAR = "SIN_FACTURAS_IMPUTAR"
    SIN_DESCUENTOS_NC = "SIN_DESCUENTOS_NC"
    SIN_PROVEEDOR = "SIN_PROVEEDOR"
    OK = "OK"


def validar_cai_vigente(
    fecha_cai: Optional[str],
    fecha_actual: Optional[date] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Paridad VB6: FechaCAI del proveedor debe ser >= fecha actual.
    Devuelve (True, None) si OK, (False, PrecheckError.CAI_VENCIDO) si vencido.
    """
    if fecha_cai is None:
        return True, None
    f = to_date_or_none(fecha_cai)
    if f is None:
        return True, None
    hoy = fecha_actual or date.today()
    try:
        from datetime import datetime
        f_date = datetime.strptime(f, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return True, None
    if f_date < hoy:
        return False, PrecheckError.CAI_VENCIDO
    return True, None


def validar_obliga_oc_para_factura(obliga_oc_carga_comp: Optional[str]) -> Tuple[bool, Optional[str]]:
    """
    Paridad VB6: si proveedor tiene obliga_oc_carga_comp = 'Si', no puede cargar factura sin OC.
    Devuelve (True, None) si puede, (False, PrecheckError.REQUIERE_OC) si no.
    """
    if not obliga_oc_carga_comp or str(obliga_oc_carga_comp).strip() != "Si":
        return True, None
    return False, PrecheckError.REQUIERE_OC


def tipo_factura_segun_idiva(id_iva: Optional[int]) -> str:
    """
    Paridad VB6: determina FA / FB / FC según idIVA del proveedor.
    - RI (1) o RICBU (7) -> FA
    - RIM (6) -> FB
    - MON (2), EX (3), Consumidor Final (4) -> FC
    """
    iva = to_int_or_none(id_iva)
    if iva is None:
        return "FC"
    if iva in (1, 7):
        return "FA"
    if iva == 6:
        return "FB"
    if iva in (2, 3, 4):
        return "FC"
    return "FC"
