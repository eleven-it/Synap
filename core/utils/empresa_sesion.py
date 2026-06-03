"""
Resolución de ``core.models.Empresa`` (Synap) a partir de la sesión AdministraNET.

``AdministraNETUser`` no expone ``empresa_activa`` como instancia Django; la empresa
operativa se identifica con ``session['user']['base_empresa']`` (nombre de base MySQL)
y debe cruzarse con ``Empresa`` por CUIT/nombre como en ``usuario_y_permisos``.
"""
from __future__ import annotations

import logging
from django.http import HttpRequest

logger = logging.getLogger(__name__)


def session_base_empresa_from_request(request: HttpRequest) -> str | None:
    """Nombre de base MySQL activa en sesión (``base_empresa``)."""
    base_empresa = None
    if hasattr(request, "session") and request.session:
        session_user = request.session.get("user", {}) or {}
        base_empresa = session_user.get("base_empresa")
    if not base_empresa and hasattr(request, "user") and request.user:
        base_empresa = getattr(request.user, "base_empresa", None)
    if base_empresa:
        return str(base_empresa).strip() or None
    return None


def _normalizar_cuit(cuit_raw: str) -> tuple[str, str]:
    """Devuelve (solo_dígitos, valor_para_identificador_fiscal)."""
    cuit = (cuit_raw or "").replace("-", "").replace(" ", "")
    if len(cuit) == 11:
        display = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10:]}"
    else:
        display = (cuit_raw or cuit).strip()
    return cuit, display


def _buscar_empresa_por_datosempresa(empresa_data: dict, *, solo_activas: bool = True):
    """Cruce DatosEmpresa → ``core.Empresa`` (misma lógica que el context processor)."""
    from core.models import Empresa

    nombre_empresa = (empresa_data.get("Nombre") or "").strip()
    cuit_empresa = (empresa_data.get("CUIT") or "").replace("-", "").replace(" ", "")

    qs_filter = {"activa": True} if solo_activas else {}

    if cuit_empresa:
        empresa_django = Empresa.objects.filter(
            identificador_fiscal__icontains=cuit_empresa, **qs_filter
        ).first()
        if empresa_django:
            return empresa_django
        if len(cuit_empresa) == 11:
            cuit_formateado = f"{cuit_empresa[:2]}-{cuit_empresa[2:10]}-{cuit_empresa[10:]}"
            empresa_django = Empresa.objects.filter(
                identificador_fiscal__icontains=cuit_formateado, **qs_filter
            ).first()
            if empresa_django:
                return empresa_django

    if nombre_empresa:
        empresa_django = Empresa.objects.filter(
            nombre__iexact=nombre_empresa, **qs_filter
        ).first()
        if empresa_django:
            return empresa_django
        return Empresa.objects.filter(nombre__icontains=nombre_empresa, **qs_filter).first()

    return None


def provision_empresa_desde_datosempresa(base_empresa: str):
    """
    Crea o reactiva ``core.Empresa`` a partir de ``DatosEmpresa`` (una empresa por base MySQL).
    Usado cuando el cruce por sesión falla pero hay CUIT válido en AdministraNET.
    """
    from core.models import Empresa
    from core.services.administranet_empresas import AdministraNETEmpresaService

    base = (base_empresa or "").strip()
    if not base:
        return None

    try:
        empresa_data = AdministraNETEmpresaService().obtener_empresa(base)
    except Exception as ex:
        logger.warning("provision_empresa: error leyendo DatosEmpresa (%s): %s", base, ex)
        return None

    if not empresa_data:
        return None

    existente = _buscar_empresa_por_datosempresa(empresa_data, solo_activas=False)
    if existente:
        if not existente.activa:
            existente.activa = True
            existente.save(update_fields=["activa", "fecha_modificacion"])
        return existente

    nombre = (empresa_data.get("Nombre") or base).strip()[:255]
    if not nombre:
        return None
    _, cuit_display = _normalizar_cuit(empresa_data.get("CUIT") or "")
    if not cuit_display:
        logger.warning("provision_empresa: base %s sin CUIT en DatosEmpresa", base)
        return None

    try:
        empresa, created = Empresa.objects.get_or_create(
            identificador_fiscal=cuit_display,
            defaults={
                "nombre": nombre,
                "razon_social": nombre,
                "activa": True,
            },
        )
        if created:
            logger.info(
                "provision_empresa: creada Empresa id=%s para base %s (CUIT %s)",
                empresa.pk,
                base,
                cuit_display,
            )
        return empresa
    except Exception as ex:
        logger.exception("provision_empresa: no se pudo crear Empresa para %s: %s", base, ex)
        return None


def empresa_django_diagnostico(request: HttpRequest) -> dict:
    """
    Datos para mensajes de soporte cuando no hay ``Empresa`` Django vinculada a la sesión.
    """
    from core.models import Empresa
    from core.services.administranet_empresas import AdministraNETEmpresaService

    base = session_base_empresa_from_request(request)
    out: dict = {
        "base_empresa": base,
        "nombre_datosempresa": None,
        "cuit_datosempresa": None,
        "empresa_inactiva_id": None,
        "empresas_activas_cuit_similar": [],
    }
    if not base:
        out["error"] = "sin_base_empresa_en_sesion"
        return out

    try:
        empresa_data = AdministraNETEmpresaService().obtener_empresa(base)
    except Exception as ex:
        out["error"] = f"datosempresa: {ex}"
        return out

    if not empresa_data:
        out["error"] = "datosempresa_vacio"
        return out

    nombre = (empresa_data.get("Nombre") or "").strip()
    cuit_raw = (empresa_data.get("CUIT") or "").strip()
    out["nombre_datosempresa"] = nombre or None
    out["cuit_datosempresa"] = cuit_raw or None

    inactiva = _buscar_empresa_por_datosempresa(empresa_data, solo_activas=False)
    if inactiva and not inactiva.activa:
        out["empresa_inactiva_id"] = inactiva.pk

    cuit_digits, _ = _normalizar_cuit(cuit_raw)
    if cuit_digits:
        similares = list(
            Empresa.objects.filter(identificador_fiscal__icontains=cuit_digits[:8]).values(
                "id", "nombre", "identificador_fiscal", "activa"
            )[:5]
        )
        out["empresas_activas_cuit_similar"] = similares

    return out


def ensure_empresa_django_from_request(request: HttpRequest, *, auto_provision: bool = True):
    """
    Resuelve ``Empresa`` para persistencia en Synap (PostgreSQL).
    Si no hay match y ``auto_provision``, intenta alta desde ``DatosEmpresa``.
    """
    empresa = get_empresa_django_from_request(request)
    if empresa:
        return empresa
    if not auto_provision:
        return None
    base = session_base_empresa_from_request(request)
    if not base:
        return None
    return provision_empresa_desde_datosempresa(base)


def get_empresa_django_from_request(request: HttpRequest):
    """
    Obtiene la empresa Django activa según sesión / usuario.

    Prioridad alineada con ``sia.permissions.get_user_empresa`` (sin depender del app ``sia``):

    1. ``session['user']['base_empresa']`` + datos ``DatosEmpresa`` (MySQL) → match por CUIT/nombre.
    2. ``request.user.base_empresa`` si no estaba en sesión.
    3. ``id_empresa`` en sesión o usuario → ``Empresa.objects.filter(id=…)``.
    4. ``session['empresa_id']`` (compatibilidad).
    5. ``request.user.empresa_activa`` si existe (``UsuarioExtendido``).
    """
    from core.models import Empresa

    base_empresa = None
    id_empresa = None

    if hasattr(request, "session") and request.session:
        session_user = request.session.get("user", {})
        base_empresa = session_user.get("base_empresa")
        id_empresa = session_user.get("id_empresa")

    if not base_empresa and hasattr(request, "user") and request.user:
        base_empresa = getattr(request.user, "base_empresa", None)
        if id_empresa is None:
            id_empresa = getattr(request.user, "id_empresa", None)

    if base_empresa:
        try:
            from core.services.administranet_empresas import AdministraNETEmpresaService

            empresa_data = AdministraNETEmpresaService().obtener_empresa(base_empresa)
            if empresa_data:
                empresa_django = _buscar_empresa_por_datosempresa(empresa_data, solo_activas=True)
                if empresa_django:
                    return empresa_django
        except Exception as ex:
            logger.warning("empresa_sesion: error resolviendo desde base_empresa: %s", ex)

    if id_empresa:
        try:
            empresa = Empresa.objects.filter(id=id_empresa, activa=True).first()
            if empresa:
                return empresa
        except Exception:
            pass

    if hasattr(request, "session") and request.session:
        empresa_id = request.session.get("empresa_id")
        if empresa_id:
            try:
                return Empresa.objects.get(id=empresa_id, activa=True)
            except Empresa.DoesNotExist:
                pass

    if hasattr(request, "user") and request.user and hasattr(request.user, "empresa_activa"):
        em = getattr(request.user, "empresa_activa", None)
        if em:
            if isinstance(em, Empresa):
                return em
            # Objetos mock del context processor no son instancias ORM
            try:
                pk = getattr(em, "pk", None) or getattr(em, "id", None)
                if pk is not None:
                    return Empresa.objects.filter(id=pk, activa=True).first()
            except Exception:
                pass

    return None
