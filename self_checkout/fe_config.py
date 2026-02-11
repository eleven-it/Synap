"""
Configuración FE (Factura Electrónica) AFIP.
Lee desde UI (fe_afip.AFIPConfig por base_empresa) o fallback a .env/settings.
Nunca loguear rutas de cert/key ni CUIT.
"""
import os
import re
from typing import Optional, Tuple


def _get(name: str, default: str = "") -> str:
    """Obtiene var desde decouple, settings o os.environ."""
    try:
        from decouple import config as decouple_config
        val = decouple_config(f"AFIP_{name}", default=None)
    except Exception:
        val = None
    if val is None:
        try:
            from django.conf import settings
            val = getattr(settings, f"AFIP_{name}", None)
        except Exception:
            val = None
    if val is None:
        val = os.environ.get(f"AFIP_{name}", default)
    return str(val).strip() if val else ""


def get_fe_config(base_empresa: Optional[str] = None) -> dict:
    """
    Configuración para pyafipws. Si base_empresa está definida, intenta cargar
    desde fe_afip.AFIPConfig (configuración por UI). Si no hay registro o no hay
    base_empresa, usa variables de entorno (.env / settings).
    """
    if base_empresa and base_empresa.strip():
        try:
            from fe_afip.models import AFIPConfig
            cfg = AFIPConfig.objects.filter(base_empresa=base_empresa.strip(), activo=True).first()
            if cfg and cfg.cert_path and cfg.key_path and cfg.cuit:
                homo = cfg.modo_homologacion
                cache_dir = (getattr(cfg, "cache_dir", None) or "").strip() or "/tmp/pyafipws_cache"
                return {
                    "cert": cfg.cert_path,
                    "key": cfg.key_path,
                    "cuit": str(cfg.cuit).replace("-", "").replace(" ", "")[:11],
                    "wsaa_url": (
                        "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
                        if homo
                        else "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"
                    ),
                    "wsfe_url": (
                        "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
                        if homo
                        else "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
                    ),
                    "cache_dir": cache_dir,
                    "homo": homo,
                }
        except Exception:
            pass
    # Fallback: variables de entorno
    homo = _get("HOMO", "1").lower() in ("1", "true", "yes")
    return {
        "cert": _get("CERT_PATH"),
        "key": _get("KEY_PATH"),
        "cuit": _get("CUIT"),
        "wsaa_url": _get("WSAA_URL") or (
            "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"
            if homo
            else "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"
        ),
        "wsfe_url": _get("WSFE_URL") or (
            "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?WSDL"
            if homo
            else "https://servicios1.afip.gov.ar/wsfev1/service.asmx?WSDL"
        ),
        "cache_dir": _get("CACHE_DIR") or "/tmp/pyafipws_cache",
        "homo": homo,
    }


def is_fe_configured(base_empresa: Optional[str] = None) -> bool:
    """True si hay cert, key y cuit configurados (desde DB o env)."""
    cfg = get_fe_config(base_empresa=base_empresa)
    return bool(cfg["cert"] and cfg["key"] and cfg["cuit"])


def check_afip_connectivity(base_empresa: Optional[str] = None) -> Tuple[bool, str]:
    """
    Comprueba conectividad con AFIP (WSAA). Para healthcheck del autoservicio.
    Returns: (ok: bool, error_message: str). Si ok es True, error_message es ''.
    Si AFIP no está configurado, se considera ok (no se bloquea el kiosco).
    """
    if not is_fe_configured(base_empresa):
        return True, ""
    cfg = get_fe_config(base_empresa)
    try:
        from pyafipws.wsaa import WSAA
        wsaa = WSAA()
        ta = wsaa.Autenticar(
            "wsfe",
            cfg["cert"],
            cfg["key"],
            wsdl=cfg["wsaa_url"],
            cache=cfg["cache_dir"],
            debug=False,
        )
        if ta:
            return True, ""
        err = getattr(wsaa, "Excepcion", None) or getattr(wsaa, "ErrMsg", "WSAA sin ticket")
        return False, str(err)[:200]
    except Exception as e:
        return False, str(e)[:200]


def sanitize_for_log(text: str) -> str:
    """Quita credenciales y rutas sensibles de strings para logs."""
    if not text:
        return ""
    s = str(text)
    s = re.sub(r"/[^\s]*\.(crt|key|pem)([\s\"]|$)", r"***\2", s)
    s = re.sub(r"\b\d{11}\b", "***CUIT***", s)
    return s[:500]
