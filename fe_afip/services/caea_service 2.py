"""
Obtención y renovación automática de CAEA según plazos AFIP.
Período 1 = días 1-15 del mes; período 2 = días 16 al último.
Solicitud permitida dentro de los 5 días corridos previos al inicio de cada período.
"""
import logging
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


def _config_from_afip_config(cfg) -> dict:
    """Construye dict de config pyafipws desde modelo AFIPConfig."""
    homo = getattr(cfg, "modo_homologacion", True)
    cache_dir = (getattr(cfg, "cache_dir", None) or "").strip() or "/tmp/pyafipws_cache"
    cuit = str(getattr(cfg, "cuit", "") or "").replace("-", "").replace(" ", "")[:11]
    return {
        "cert": getattr(cfg, "cert_path", "") or "",
        "key": getattr(cfg, "key_path", "") or "",
        "cuit": cuit,
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


def periodo_orden_from_date(d: date) -> Tuple[str, int]:
    """
    Devuelve (periodo YYYYMM, orden) para la quincena que contiene la fecha.
    Orden 1 = días 1-15, orden 2 = días 16-fin.
    """
    periodo = d.strftime("%Y%m")
    orden = 1 if d.day <= 15 else 2
    return periodo, orden


def last_day_of_quincena(year: int, month: int, orden: int) -> date:
    """Último día del período quincenal."""
    if orden == 1:
        return date(year, month, 15)
    # orden 2: último día del mes
    if month == 12:
        return date(year, 12, 31)
    return date(year, month + 1, 1) - timedelta(days=1)


def periods_to_request_today() -> List[Tuple[str, int]]:
    """
    Períodos para los que hoy está permitido solicitar CAEA (5 días previos al inicio).
    - Período 1 (días 1-15): se puede solicitar los días 27, 28, 29, 30, 31 del mes anterior.
    - Período 2 (días 16-fin): se puede solicitar los días 11, 12, 13, 14, 15 del mismo mes.
    """
    today = date.today()
    out = []
    # Ventana período 1 del mes siguiente: estamos en últimos 5 días del mes
    if today.day >= 27:
        # Próximo mes, orden 1
        next_month = today.month + 1 if today.month < 12 else 1
        next_year = today.year if today.month < 12 else today.year + 1
        periodo1 = f"{next_year}{next_month:02d}"
        out.append((periodo1, 1))
    # Ventana período 2 del mes actual: estamos entre 11 y 15
    if 11 <= today.day <= 15:
        periodo2 = today.strftime("%Y%m")
        out.append((periodo2, 2))
    return out


def get_caea_stored(base_empresa: str, periodo: str, orden: int) -> Optional[str]:
    """
    Devuelve el código CAEA almacenado para base_empresa/periodo/orden, o None.
    """
    from fe_afip.models import CAEACode

    base_empresa = (base_empresa or "").strip()
    if not base_empresa or not periodo or orden not in (1, 2):
        return None
    rec = CAEACode.objects.filter(
        base_empresa=base_empresa,
        periodo=str(periodo),
        orden=orden,
    ).first()
    return (rec.codigo or "").strip() or None if rec else None


def request_and_store_caea(
    base_empresa: str,
    periodo: str,
    orden: int,
    config: dict,
) -> Tuple[Optional[str], Optional[date], Optional[str]]:
    """
    Solicita CAEA a AFIP (CAEAConsultar, si no hay CAEASolicitar) y lo persiste.
    Returns: (codigo, vencimiento, error_message). Si error_message no es None, falló.
    """
    from fe_afip.models import CAEACode

    if not config.get("cert") or not config.get("key") or not config.get("cuit"):
        return None, None, "Config AFIP incompleta (cert/key/cuit)"

    try:
        from pyafipws.wsaa import WSAA
        from pyafipws.wsfev1 import WSFEv1
    except ImportError as e:
        logger.warning("pyafipws no disponible: %s", e)
        return None, None, "pyafipws no instalado"

    wsaa = WSAA()
    wsfev1 = WSFEv1()
    wsfev1.LanzarExcepciones = False

    try:
        ta = wsaa.Autenticar(
            "wsfe",
            config["cert"],
            config["key"],
            wsdl=config["wsaa_url"],
            cache=config["cache_dir"],
            debug=False,
        )
        if not ta:
            err = getattr(wsaa, "Excepcion", None) or getattr(wsaa, "ErrMsg", "WSAA error")
            return None, None, str(err)[:300]

        wsfev1.Cuit = config["cuit"]
        wsfev1.SetTicketAcceso(ta)
        ok = wsfev1.Conectar(config["cache_dir"], config["wsfe_url"])
        if not ok:
            return None, None, "Conectar WSFEv1 falló"

        caea = wsfev1.CAEAConsultar(periodo, orden)
        source = CAEACode.SOURCE_CONSULTAR
        if not caea:
            caea = wsfev1.CAEASolicitar(periodo, orden)
            source = CAEACode.SOURCE_SOLICITAR
        if not caea:
            err = getattr(wsfev1, "ErrMsg", None) or getattr(wsfev1, "Obs", "AFIP no devolvió CAEA")
            return None, None, (err or "No se pudo obtener CAEA")[:300]

        codigo = str(caea).strip()
        # Vencimiento: último día de la quincena
        try:
            y, m = int(periodo[:4]), int(periodo[4:6])
            vto = last_day_of_quincena(y, m, orden)
        except Exception:
            vto = None

        CAEACode.objects.update_or_create(
            base_empresa=base_empresa.strip(),
            periodo=periodo,
            orden=orden,
            defaults={
                "codigo": codigo,
                "vencimiento": vto,
                "source": source,
            },
        )
        logger.info("CAEA obtenido y guardado: base=%s periodo=%s orden=%s source=%s", base_empresa, periodo, orden, source)
        return codigo, vto, None
    except Exception as e:
        logger.exception("request_and_store_caea: %s", e)
        return None, None, str(e)[:300]


def run_auto_request_for_base(base_empresa: str) -> List[Tuple[str, int, bool, str]]:
    """
    Para una base_empresa con AFIP configurada, solicita CAEA para todos los períodos
    que correspondan a la ventana de 5 días de hoy y aún no estén almacenados.
    Returns: lista de (periodo, orden, ok, message).
    """
    from fe_afip.models import AFIPConfig, CAEACode

    base_empresa = (base_empresa or "").strip()
    if not base_empresa:
        return []

    cfg = AFIPConfig.objects.filter(base_empresa=base_empresa, activo=True).first()
    if not cfg or not cfg.cert_path or not cfg.key_path or not cfg.cuit:
        logger.debug("CAEA auto: base %s sin config AFIP activa", base_empresa)
        return []

    config = _config_from_afip_config(cfg)
    results = []
    for periodo, orden in periods_to_request_today():
        if get_caea_stored(base_empresa, periodo, orden):
            results.append((periodo, orden, True, "ya existía"))
            continue
        codigo, vto, err = request_and_store_caea(base_empresa, periodo, orden, config)
        ok = err is None
        results.append((periodo, orden, ok, err or "ok"))
    return results
