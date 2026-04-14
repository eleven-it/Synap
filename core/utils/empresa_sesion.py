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

            empresa_service = AdministraNETEmpresaService()
            empresa_data = empresa_service.obtener_empresa(base_empresa)
            if empresa_data:
                nombre_empresa = empresa_data.get("Nombre", "")
                cuit_empresa = (empresa_data.get("CUIT") or "").replace("-", "").replace(" ", "")

                if cuit_empresa:
                    try:
                        empresa_django = Empresa.objects.filter(
                            identificador_fiscal__icontains=cuit_empresa,
                            activa=True,
                        ).first()
                        if empresa_django:
                            return empresa_django
                        if len(cuit_empresa) == 11:
                            cuit_formateado = f"{cuit_empresa[:2]}-{cuit_empresa[2:10]}-{cuit_empresa[10:]}"
                            empresa_django = Empresa.objects.filter(
                                identificador_fiscal__icontains=cuit_formateado,
                                activa=True,
                            ).first()
                            if empresa_django:
                                return empresa_django
                    except Exception as ex:
                        logger.debug("empresa_sesion: búsqueda por CUIT: %s", ex)

                if nombre_empresa:
                    try:
                        empresa_django = Empresa.objects.filter(
                            nombre__iexact=nombre_empresa,
                            activa=True,
                        ).first()
                        if empresa_django:
                            return empresa_django
                        empresa_django = Empresa.objects.filter(
                            nombre__icontains=nombre_empresa,
                            activa=True,
                        ).first()
                        if empresa_django:
                            return empresa_django
                    except Exception as ex:
                        logger.debug("empresa_sesion: búsqueda por nombre: %s", ex)
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
