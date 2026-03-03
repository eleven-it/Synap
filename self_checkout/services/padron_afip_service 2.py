"""
Servicio de consulta al padrón AFIP por CUIT para determinar condición fiscal (FA/FB).

Diferencias Padrón A4 vs A5 (AFIP):
- A5: datos actuales (inscripción vigente), acceso público. Recomendado para tipo comprobante (A/B/C).
- A4: datos históricos (inscripciones pasadas), más restringido por AFIP.
Si solo tenés A4 autorizado en AFIP (o A5 falla), se intenta A4 como fallback.
"""
import logging
from typing import Optional, Tuple

from self_checkout.fe_config import get_fe_config, is_fe_configured, sanitize_for_log

logger = logging.getLogger(__name__)

# Condiciones IVA que corresponden a Factura A (según AFIP / administraNET).
# RI, Monotributo, Sujeto no categorizado, etc. → FA. Resto → FB.
IDIVA_FA = {1, 6, 7}  # 1=RI, 6=Monotributo, 7=Sujeto no categorizado. 2=RNI puede ser FA con resol 5003 (no lo usamos por padrón).


def _consultar_con_alcance(
    cfg: dict,
    cuit_clean: str,
    wsaa_service: str,
    base_url: str,
    WSSrPadronCls,
) -> Tuple[Optional[str], Optional[str], Optional[dict]]:
    """Ejecuta una consulta al padrón con un alcance (A4 o A5). Returns (tipo, denominacion, error_detail)."""
    from pyafipws.wsaa import WSAA

    wsaa = WSAA()
    padron = WSSrPadronCls()
    padron.LanzarExcepciones = False

    ta = wsaa.Autenticar(
        wsaa_service,
        cfg["cert"],
        cfg["key"],
        wsdl=cfg.get("wsaa_url"),
        cache=cfg.get("cache_dir", "/tmp/pyafipws_cache"),
        debug=False,
    )
    if not ta:
        err = getattr(wsaa, "Excepcion", "WSAA error")
        return None, None, {"msg": str(err)}

    padron_url = base_url + "?wsdl"
    cache_dir = cfg.get("cache_dir", "/tmp/pyafipws_cache")
    try:
        ok = padron.Conectar(cache_dir, padron_url)
    except TypeError:
        ok = padron.Conectar(cache=cache_dir, url=padron_url)
    if not ok:
        return None, None, {"msg": "No se pudo conectar al padrón AFIP"}

    padron.Cuit = cfg["cuit"]
    padron.SetTicketAcceso(ta)
    ok = padron.Consultar(cuit_clean)
    if not ok:
        err = getattr(padron, "Excepcion", None) or getattr(padron, "ErrMsg", "Padrón no respondió")
        return None, None, {"msg": str(err)}

    raw = getattr(padron, "cat_iva", None) or getattr(padron, "imp_iva", None) or getattr(padron, "CondicionIVA", None)
    id_iva = None
    if raw is not None:
        try:
            id_iva = int(raw)
        except (TypeError, ValueError):
            id_iva = {"AC": 1, "EX": 4, "CF": 5, "MT": 6}.get((raw or "").strip().upper())

    denominacion = getattr(padron, "denominacion", None) or getattr(padron, "Denominacion", None) or ""
    tipo = "FA" if (id_iva is not None and id_iva in IDIVA_FA) else "FB"
    return tipo, (denominacion or "").strip() or None, None


def _es_error_autorizacion(error_detail: Optional[dict]) -> bool:
    """True si el error sugiere que hay que intentar otro alcance (ej. computador no autorizado para A5)."""
    if not error_detail or not error_detail.get("msg"):
        return False
    msg = (error_detail.get("msg") or "").lower()
    return (
        "coe.notauthorized" in msg
        or "computador no autorizado" in msg
        or "no autorizado" in msg
        or "no se pudo conectar" in msg
    )


def consultar_condicion_fiscal(base_empresa: str, cuit: str) -> Tuple[Optional[str], Optional[str], Optional[dict]]:
    """
    Consulta el padrón AFIP por CUIT y devuelve si corresponde emitir FA o FB.
    Intenta primero Padrón A5; si falla por autorización/conexión, intenta A4.
    Returns: (tipo_comprobante, denominacion, error_detail)
    """
    cuit_clean = (cuit or "").replace("-", "").replace(" ", "").strip()
    if len(cuit_clean) != 11 or not cuit_clean.isdigit():
        return None, None, {"msg": "CUIT inválido (debe tener 11 dígitos)"}

    if not is_fe_configured(base_empresa):
        return None, None, {"msg": "AFIP no configurado (cert/key/cuit)"}

    cfg = get_fe_config(base_empresa)
    homo = cfg.get("homo", True)
    if homo:
        base_url_a5 = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA5"
        base_url_a4 = "https://awshomo.afip.gov.ar/sr-padron/webservices/personaServiceA4"
    else:
        base_url_a5 = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA5"
        base_url_a4 = "https://aws.afip.gov.ar/sr-padron/webservices/personaServiceA4"

    # Importar ambas clases si están disponibles
    WSSrPadronA5 = WSSrPadronA4 = None
    try:
        from pyafipws.wsaa import WSAA
        from pyafipws.ws_sr_padron import WSSrPadronA5 as _A5, WSSrPadronA4 as _A4
        WSSrPadronA5, WSSrPadronA4 = _A5, _A4
    except ImportError as e:
        try:
            from pyafipws.wsaa import WSAA
            from pyafipws.ws_sr_padron import WSSrPadronA4 as _A4
            WSSrPadronA4 = _A4
        except ImportError:
            pass
        if not WSSrPadronA5 and not WSSrPadronA4:
            logger.warning(
                "Módulo padrón AFIP no disponible en pyafipws (%s). Instalá: pip install git+https://github.com/reingart/pyafipws.git",
                sanitize_for_log(str(e)),
            )
            return None, None, {"msg": "Módulo padrón AFIP no disponible (pyafipws.ws_sr_padron). Instalá/actualizá pyafipws."}

    try:
        # 1) Intentar A5 (recomendado, datos actuales)
        if WSSrPadronA5:
            tipo, denom, err = _consultar_con_alcance(
                cfg, cuit_clean, "ws_sr_padron_a5", base_url_a5, WSSrPadronA5
            )
            if err is None:
                return tipo, denom, None
            if not _es_error_autorizacion(err):
                logger.warning("Padrón A5 falló para CUIT ***%s: %s", cuit_clean[-4:], sanitize_for_log((err or {}).get("msg", "")))
                return None, None, err
            logger.info("Padrón A5 no autorizado o no disponible, intentando A4")

        # 2) Fallback a A4
        if WSSrPadronA4:
            tipo, denom, err = _consultar_con_alcance(
                cfg, cuit_clean, "ws_sr_padron_a4", base_url_a4, WSSrPadronA4
            )
            if err is None:
                return tipo, denom, None
            logger.warning("Padrón A4 falló para CUIT ***%s: %s", cuit_clean[-4:], sanitize_for_log((err or {}).get("msg", "")))
            return None, None, err

        # Solo teníamos A5 y falló por autorización
        return None, None, {"msg": "Padrón A5 no autorizado. En AFIP autorizá la IP para Padrón A5 o Padrón A4."}
    except Exception as e:
        logger.exception("Padrón AFIP exception")
        return None, None, {"msg": sanitize_for_log(str(e))}
