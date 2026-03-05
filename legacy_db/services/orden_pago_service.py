"""
Servicio de Orden de Pago: abre/cierra lock (fact_temporalp) y confirma OP.
Paridad con VB6 OrdenPago.frm: misma secuencia y tablas.
Toda escritura en tablas legacy debe pasar por este servicio (y sus repositorios).
"""
import logging
from typing import Any, Dict, Optional

from core.mysql_pool import get_connection

from legacy_db.repositories import (
    acquire_lock_op_proveedor,
    release_lock_op_proveedor,
    check_lock_op_proveedor,
)
from legacy_db.validators import PrecheckError

logger = logging.getLogger(__name__)


def open_orden_pago(
    base_empresa: str,
    codigo_proveedor: int,
    id_usuario: int,
    cod_usuario: str,
) -> Dict[str, Any]:
    """
    Toma el lock de OP para el proveedor (adquire fact_temporalp).
    Debe llamarse al abrir el formulario de Orden de Pago.
    Devuelve {"ok": True} o {"ok": False, "codigo": "OP_BLOQUEADA", "codigo_usuario": "..."}.
    """
    lock = check_lock_op_proveedor(base_empresa, codigo_proveedor, id_usuario)
    if lock:
        return {
            "ok": False,
            "codigo": PrecheckError.OP_BLOQUEADA,
            "codigo_usuario": lock.get("codigo_usuario") or "",
        }
    try:
        with get_connection(base_empresa) as conn:
            acquire_lock_op_proveedor(conn, codigo_proveedor, id_usuario, cod_usuario)
            conn.commit()
        return {"ok": True}
    except Exception as e:
        logger.exception("open_orden_pago: %s", e)
        return {"ok": False, "codigo": "ERROR", "detalle": str(e)}


def close_orden_pago(
    base_empresa: str,
    codigo_proveedor: int,
    id_usuario: int,
) -> None:
    """
    Libera el lock de OP (release fact_temporalp).
    Debe llamarse al cerrar o cancelar el formulario de Orden de Pago.
    """
    try:
        with get_connection(base_empresa) as conn:
            release_lock_op_proveedor(conn, codigo_proveedor, id_usuario)
            conn.commit()
    except Exception as e:
        logger.exception("close_orden_pago: %s", e)


def confirmar_orden_pago_a_cuenta(
    base_empresa: str,
    payload: Dict[str, Any],
    id_usuario: int,
    cod_usuario: str,
) -> Dict[str, Any]:
    """
    Confirma una Orden de Pago "a cuenta" en una sola transacción.
    Paridad VB6: mismas tablas, mismo orden (cabecera, detalle, op_factura, saldos, etc.).
    TODO: implementar según ingeniería inversa de OrdenPago.frm (guardado a cuenta).
    Por ahora devuelve error controlado para no escribir sin paridad completa.
    """
    codigo_proveedor = payload.get("codigo_proveedor") or payload.get("Codigo")
    if not codigo_proveedor:
        return {"ok": False, "codigo": PrecheckError.SIN_PROVEEDOR}

    try:
        with get_connection(base_empresa) as conn:
            conn.autocommit(False)
            try:
                # TODO: insertar cabecera OP, movimientos, actualizar op_factura/saldos
                # según secuencia exacta de VB6 OrdenPago (a cuenta).
                raise NotImplementedError(
                    "confirmar_orden_pago_a_cuenta: implementar según OrdenPago.frm (VB6)"
                )
            except NotImplementedError:
                conn.rollback()
                return {"ok": False, "codigo": "NO_IMPLEMENTADO", "detalle": "Escritura OP a cuenta pendiente de paridad VB6"}
            except Exception as e:
                conn.rollback()
                raise
            conn.commit()
        return {"ok": True}
    except Exception as e:
        logger.exception("confirmar_orden_pago_a_cuenta: %s", e)
        return {"ok": False, "codigo": "ERROR", "detalle": str(e)}
