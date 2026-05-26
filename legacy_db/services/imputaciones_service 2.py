"""
Servicio de imputación/desimputación de comprobantes a Orden de Pago.
Paridad con VB6 AsigPago.frm / AsigPagoD.frm.
Toda escritura en op_factura y tablas relacionadas debe pasar por este servicio.
"""
import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


def confirmar_imputacion(
    base_empresa: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Confirma la imputación de comprobantes a una OP.
    Paridad VB6 AsigPago: misma secuencia de actualización op_factura/saldos/estados.
    TODO: implementar según ingeniería inversa de AsigPago.frm.
    """
    logger.warning("confirmar_imputacion: no implementado (paridad AsigPago.frm pendiente)")
    return {
        "ok": False,
        "codigo": "NO_IMPLEMENTADO",
        "detalle": "Imputación pendiente de paridad VB6 AsigPago.frm",
    }


def confirmar_desimputacion(
    base_empresa: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Confirma la desimputación de comprobantes de una OP.
    Paridad VB6 AsigPagoD.
    TODO: implementar según ingeniería inversa.
    """
    logger.warning("confirmar_desimputacion: no implementado (paridad AsigPagoD.frm pendiente)")
    return {
        "ok": False,
        "codigo": "NO_IMPLEMENTADO",
        "detalle": "Desimputación pendiente de paridad VB6 AsigPagoD.frm",
    }
