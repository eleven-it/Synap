"""
Precheck de paridad TPV (permisos_sistema + cliente + caja_abm), solo invocado desde
`cart_confirm` cuando el kiosco está en modo TPV.

Referencias VB6: obliga_selecpv, obliga_cambvendedor, límites de crédito cliente,
limite_efectivo en caja_abm (activa_limite_efectivo).
"""
import logging
from typing import Any, Dict, Optional, Tuple

from self_checkout.db import mysql_cursor
from self_checkout.constants import (
    E_TPV_OBLIGA_PV,
    E_TPV_OBLIGA_VENDEDOR,
    E_TPV_CREDITO_EXCEDIDO,
    E_TPV_LIMITE_EFECTIVO_CAJA,
)

logger = logging.getLogger(__name__)


def _es_si(val: Any) -> bool:
    if val is None:
        return False
    return str(val).strip().lower() in ("si", "sí", "1", "true")


def _permiso_get(permisos: Optional[Dict[str, Any]], clave: str, default: str = "No") -> str:
    if not permisos:
        return default
    for k, v in permisos.items():
        if str(k).lower() == clave.lower():
            return str(v) if v is not None else default
    return default


def cargar_permisos_puesto(base_empresa: str, id_puesto: Optional[int]) -> Optional[Dict[str, Any]]:
    """Lee fila `permisos_sistema` por IDPuesto; None si no hay puesto o tabla."""
    if not id_puesto:
        return None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute(
                "SELECT * FROM permisos_sistema WHERE IDPuesto = %s LIMIT 1",
                [int(id_puesto)],
            )
            row = c.fetchone()
            return dict(row) if row else None
    except Exception as e:
        if "doesn't exist" in str(e) or "Unknown table" in str(e):
            return None
        logger.warning("cargar_permisos_puesto: %s", e)
        return None


def _limite_efectivo_caja_y_supera(
    base_empresa: str,
    kiosk_id: Any,
    importe_efectivo: Optional[float],
) -> Tuple[bool, Optional[str]]:
    """
    Si la caja del kiosco tiene tope de efectivo activo y el ingreso lo supera → (False, mensaje).
    """
    imp_ef = float(importe_efectivo or 0)
    if imp_ef <= 0:
        return True, None
    try:
        from mercadopago.services.payment_service import get_config_for_kiosk
    except Exception:
        return True, None
    try:
        cfg = get_config_for_kiosk(base_empresa, str(kiosk_id or ""))
        id_caja = getattr(cfg, "id_caja_abm", None) if cfg else None
        if not id_caja:
            return True, None
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute(
                """
                SELECT limite_efectivo, activa_limite_efectivo
                FROM caja_abm WHERE id_caja = %s LIMIT 1
                """,
                [int(id_caja)],
            )
            r = c.fetchone()
        if not r:
            return True, None
        activa = _es_si(r.get("activa_limite_efectivo"))
        lim = r.get("limite_efectivo")
        lim_f = float(lim) if lim is not None else 0.0
        if activa and lim_f > 0 and imp_ef > lim_f + 0.02:
            return False, (
                f"El efectivo ingresado ($ {imp_ef:.2f}) supera el límite permitido "
                f"para la caja ($ {lim_f:.2f})."
            )
    except Exception as e:
        logger.warning("limite_efectivo_caja: %s", e)
    return True, None


def _credito_cliente_ok(
    base_empresa: str,
    id_cliente: int,
    total_venta: float,
) -> Tuple[bool, Optional[str]]:
    """Cliente distinto de CF: si tiene tope Credito > 0, saldo + venta no debe superarlo."""
    if not id_cliente or int(id_cliente) <= 1:
        return True, None
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute(
                "SELECT Credito, saldo FROM cliente WHERE Codigo = %s LIMIT 1",
                [int(id_cliente)],
            )
            r = c.fetchone()
        if not r:
            return True, None
        credito = float(r.get("Credito") or 0)
        if credito <= 0:
            return True, None
        saldo = float(r.get("saldo") or 0)
        total_f = float(total_venta or 0)
        if saldo + total_f > credito + 0.02:
            return False, (
                f"La venta supera el límite de crédito del cliente "
                f"(disponible aprox.: $ {max(0.0, credito - saldo):.2f})."
            )
    except Exception as e:
        if "Unknown column" in str(e):
            return True, None
        logger.warning("credito_cliente_ok: %s", e)
    return True, None


def evaluar_precheck_tpv_paridad(
    base_empresa: str,
    *,
    cart_row: Dict[str, Any],
    id_cliente: int,
    total_venta: float,
    tpv_importe_efectivo: Optional[float],
    cod_viajante_en_post: Optional[int],
    id_puesto: Optional[int],
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validaciones de negocio legacy solo para modo TPV.

    Args:
        cod_viajante_en_post: valor explícito enviado en el POST (no el default del kiosco).

    Returns:
        (True, None, None) si OK; si no (False, código_error, mensaje_usuario).
    """
    permisos = cargar_permisos_puesto(base_empresa, id_puesto)

    if _es_si(_permiso_get(permisos, "obliga_selecpv")):
        pv = cart_row.get("id_punto_venta")
        try:
            pv_int = int(pv) if pv is not None else 0
        except (TypeError, ValueError):
            pv_int = 0
        if pv_int <= 0:
            return False, E_TPV_OBLIGA_PV, "Debe seleccionar un punto de venta antes de confirmar."

    if _es_si(_permiso_get(permisos, "obliga_cambvendedor")):
        if cod_viajante_en_post is None:
            return False, E_TPV_OBLIGA_VENDEDOR, "Debe seleccionar un vendedor antes de confirmar."

    ok_cred, msg_cred = _credito_cliente_ok(base_empresa, id_cliente, total_venta)
    if not ok_cred:
        return False, E_TPV_CREDITO_EXCEDIDO, msg_cred

    ok_caja, msg_caja = _limite_efectivo_caja_y_supera(
        base_empresa,
        cart_row.get("kiosk_id"),
        tpv_importe_efectivo,
    )
    if not ok_caja:
        return False, E_TPV_LIMITE_EFECTIVO_CAJA, msg_caja

    return True, None, None
