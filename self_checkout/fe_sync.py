"""
Sincronización con ARCA: último comprobante autorizado y recuperación de CAE.
- get_ultimo_autorizado_afip: alinea numeración talonarios vs AFIP (FECompUltimoAutorizado).
- consultar_cae_comprobante: recupera CAE de un comprobante ya autorizado (FECompConsultar).
"""
import logging
from typing import Optional, Tuple

from self_checkout.fe_config import (
    get_fe_config,
    is_fe_configured,
    sanitize_for_log,
    validate_fe_certificates_readable,
)

logger = logging.getLogger(__name__)

# tipo_cbte AFIP: 1=FA, 6=FB, 11=FC (Factura C Monotributo/Exento)
TIPO_CBTE_AFIP = {"FA": 1, "FB": 6, "FC": 11}


def get_ultimo_autorizado_afip(
    base_empresa: str,
    id_punto_venta: int,
    tipo_comprobante: str,
) -> Tuple[Optional[int], Optional[str]]:
    """
    Obtiene el último número de comprobante autorizado en AFIP para el PV y tipo dados.
    Equivalente a RecuperaLastCMP / FECompUltimoAutorizado.
    Returns: (ultimo_nro, error_message). Si error_message no es None, falló la consulta.
    """
    if not is_fe_configured(base_empresa):
        return None, "AFIP no configurado"
    cfg = get_fe_config(base_empresa)
    ok_read, err_read = validate_fe_certificates_readable(cfg)
    if not ok_read:
        return None, err_read[:300]
    tipo_cbte = TIPO_CBTE_AFIP.get(tipo_comprobante.upper() if tipo_comprobante else "FB", 6)
    pto_vta = int(id_punto_venta)

    try:
        from pyafipws.wsaa import WSAA
        from pyafipws.wsfev1 import WSFEv1
    except ImportError as e:
        logger.warning("pyafipws no disponible: %s", sanitize_for_log(str(e)))
        return None, "pyafipws no instalado"

    wsaa = WSAA()
    wsfev1 = WSFEv1()
    wsfev1.LanzarExcepciones = False

    try:
        ta = wsaa.Autenticar(
            "wsfe",
            cfg["cert"],
            cfg["key"],
            wsdl=cfg["wsaa_url"],
            cache=cfg["cache_dir"],
            debug=False,
        )
        if not ta:
            err = getattr(wsaa, "Excepcion", None) or getattr(wsaa, "ErrMsg", "WSAA error")
            return None, str(err)[:300]

        wsfev1.Cuit = cfg["cuit"]
        wsfev1.SetTicketAcceso(ta)
        ok = wsfev1.Conectar(cfg["cache_dir"], cfg["wsfe_url"])
        if not ok:
            return None, "Conectar WSFEv1 falló"

        # FECompUltimoAutorizado: último número autorizado para PV y tipo (pyafipws: CompUltimoAutorizado(tipo_cbte, pto_vta))
        nro = None
        if hasattr(wsfev1, "CompUltimoAutorizado"):
            try:
                nro = wsfev1.CompUltimoAutorizado(tipo_cbte, pto_vta)
            except Exception:
                pass
        if nro is None and hasattr(wsfev1, "CbteNro"):
            nro = wsfev1.CbteNro
        if nro is None:
            err = getattr(wsfev1, "ErrMsg", None) or getattr(wsfev1, "Obs", "AFIP no devolvió último comprobante")
            return None, (err or "Error al obtener último comprobante autorizado")[:300]

        return int(nro), None
    except Exception as e:
        logger.exception("get_ultimo_autorizado_afip: %s", e)
        return None, str(e)[:300]


def consultar_cae_comprobante(
    base_empresa: str,
    id_punto_venta: int,
    tipo_comprobante: str,
    nro_comprobante: int,
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Consulta en AFIP el CAE de un comprobante ya autorizado (FECompConsultar).
    Útil cuando la respuesta de CAESolicitar se perdió por corte de conexión.
    Returns: (cae, vto_cae, error_message). Si error_message no es None, no se pudo recuperar.
    """
    if not is_fe_configured(base_empresa):
        return None, None, "AFIP no configurado"
    cfg = get_fe_config(base_empresa)
    ok_read, err_read = validate_fe_certificates_readable(cfg)
    if not ok_read:
        return None, None, err_read[:300]
    tipo_cbte = TIPO_CBTE_AFIP.get(tipo_comprobante.upper() if tipo_comprobante else "FB", 6)
    pto_vta = int(id_punto_venta)
    cbte_nro = int(nro_comprobante)

    try:
        from pyafipws.wsaa import WSAA
        from pyafipws.wsfev1 import WSFEv1
    except ImportError as e:
        logger.warning("pyafipws no disponible: %s", sanitize_for_log(str(e)))
        return None, None, "pyafipws no instalado"

    wsaa = WSAA()
    wsfev1 = WSFEv1()
    wsfev1.LanzarExcepciones = False

    try:
        ta = wsaa.Autenticar(
            "wsfe",
            cfg["cert"],
            cfg["key"],
            wsdl=cfg["wsaa_url"],
            cache=cfg["cache_dir"],
            debug=False,
        )
        if not ta:
            err = getattr(wsaa, "Excepcion", None) or getattr(wsaa, "ErrMsg", "WSAA error")
            return None, None, str(err)[:300]

        wsfev1.Cuit = cfg["cuit"]
        wsfev1.SetTicketAcceso(ta)
        ok = wsfev1.Conectar(cfg["cache_dir"], cfg["wsfe_url"])
        if not ok:
            return None, None, "Conectar WSFEv1 falló"

        # FECompConsultar: por PtoVta, CbteTipo, CbteNro devuelve datos del comprobante incl. CAE
        ok_consulta = False
        if hasattr(wsfev1, "CompConsultar"):
            ok_consulta = wsfev1.CompConsultar(pto_vta, tipo_cbte, cbte_nro)
        elif hasattr(wsfev1, "ConsultarComprobante"):
            ok_consulta = wsfev1.ConsultarComprobante(pto_vta, tipo_cbte, cbte_nro)
        if not ok_consulta:
            err = getattr(wsfev1, "ErrMsg", None) or getattr(wsfev1, "Obs", "Comprobante no encontrado en AFIP")
            return None, None, (err or "Error al consultar comprobante")[:300]

        cae = getattr(wsfev1, "CAE", None) or getattr(wsfev1, "CodAutorizacion", None)
        vto = getattr(wsfev1, "Vencimiento", None) or getattr(wsfev1, "CbteFch", None)
        if cae:
            return str(cae).strip(), str(vto).strip() if vto else None, None
        return None, None, "AFIP no devolvió CAE en la consulta"
    except Exception as e:
        logger.exception("consultar_cae_comprobante: %s", e)
        return None, None, str(e)[:300]
