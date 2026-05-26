"""
Servicio de Factura de Compra: validaciones y confirmación.
Paridad con VB6 PFactura.frm: mismas tablas y secuencia.
Toda escritura en tablas legacy debe pasar por este servicio (y sus repositorios).
"""
import logging
from typing import Any, Dict

from legacy_db.validators import (
    PrecheckError,
    validar_cai_vigente,
    validar_obliga_oc_para_factura,
    tipo_factura_segun_idiva,
)

logger = logging.getLogger(__name__)


def precheck_factura_compra(
    obliga_oc_carga_comp: str,
    fecha_cai: Any,
) -> Dict[str, Any]:
    """
    Precheck antes de abrir formulario Factura de Compra.
    Devuelve {"ok": True} o {"ok": False, "codigo": "CAI_VENCIDO"|"REQUIERE_OC"}.
    """
    ok_cai, err_cai = validar_cai_vigente(fecha_cai)
    if not ok_cai:
        return {"ok": False, "codigo": err_cai}
    ok_oc, err_oc = validar_obliga_oc_para_factura(obliga_oc_carga_comp)
    if not ok_oc:
        return {"ok": False, "codigo": err_oc}
    return {"ok": True}


def confirmar_factura_compra(
    base_empresa: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Confirma una Factura de Compra (FA/FB/FC) en una sola transacción.
    Paridad VB6 PFactura: mismas tablas, mismo orden (cabecera, detalle, numeración, op_factura, etc.).
    TODO: implementar según ingeniería inversa de PFactura.frm.
    Por ahora devuelve error controlado.
    """
    # TODO: con get_connection(base_empresa), autocommit(False), ejecutar en orden:
    # - numerador, cabecera factura compra, detalle, op_factura/saldos, etc.
    logger.warning("confirmar_factura_compra: no implementado (paridad PFactura.frm pendiente)")
    return {
        "ok": False,
        "codigo": "NO_IMPLEMENTADO",
        "detalle": "Escritura Factura de Compra pendiente de paridad VB6 PFactura.frm",
    }
