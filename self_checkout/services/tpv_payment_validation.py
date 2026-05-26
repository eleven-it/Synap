"""
Validación de medios de cobro TPV alineada a TPV.frm (suma medios + intereses ≈ total).
Solo debe usarse cuando el kiosco tiene modo_tpv activo (ver `kiosk_es_modo_tpv`).
"""
from typing import Optional, Tuple

from self_checkout.services.kiosk_service import KioskSessionService

# Misma tolerancia que ConfirmationService (redondeo float / moneda)
TOLERANCIA_MEDIOS_TPV = 0.02


def kiosk_es_modo_tpv(base_empresa: str, kiosk_id) -> bool:
    """True si `self_checkout_kiosk.modo_tpv` está activo para este kiosco."""
    if kiosk_id is None or kiosk_id == '':
        return False
    cfg = KioskSessionService(base_empresa).get_kiosk_config(str(kiosk_id))
    if not cfg:
        return False
    return bool(cfg.get('modo_tpv'))


def evaluar_suma_medios_pago(
    total_f: float,
    tpv_importe_efectivo: Optional[float],
    tpv_importe_tarjeta: Optional[float],
    tpv_intereses: Optional[float] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Replica la lógica de `ConfirmationService` al insertar `cuentacliente`:
    - Si ambos importes son None → sin validación aquí (el servicio asigna tarjeta = total).
    - Si hay desglose: efectivo + tarjeta + intereses debe coincidir con total_f.
    - Si la suma explícita es ~0 → mensaje tipo VB6 «al menos un medio».

    Returns:
        (True, None) si OK o si aplica el camino default (ambos None).
        (False, mensaje) si rechazo.
    """
    total_f = float(total_f or 0)
    if tpv_importe_efectivo is None and tpv_importe_tarjeta is None:
        return True, None

    tpv_imp_efectivo = float(tpv_importe_efectivo) if tpv_importe_efectivo is not None else 0.0
    tpv_imp_tarjeta = float(tpv_importe_tarjeta) if tpv_importe_tarjeta is not None else 0.0
    tpv_imp_int = float(tpv_intereses) if tpv_intereses is not None else 0.0

    suma_medios = tpv_imp_efectivo + tpv_imp_tarjeta + tpv_imp_int

    if suma_medios <= 0.005:
        return False, 'Debe ingresar por lo menos un medio de cobro disponible.'

    if abs(suma_medios - total_f) > TOLERANCIA_MEDIOS_TPV:
        return False, (
            f'La suma de medios de cobro ($ {suma_medios:.2f}) no coincide con el total ($ {total_f:.2f})'
        )

    return True, None
