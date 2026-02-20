"""Vistas de configuración Factura Electrónica AFIP. base_empresa desde sesión activa."""
import os
import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.conf import settings as django_settings
from django.http import JsonResponse

from core.decorators import administranet_login_required, tiene_permiso
from core.services.administranet_empresas import AdministraNETEmpresaService
from fe_afip.models import AFIPConfig
from fe_afip.services.cert_arca import generate_csr, save_certificate_and_apply, validate_cert_cuit

logger = logging.getLogger(__name__)

# Sesión: fe_afip_pending = { "token": str, "cuit": str, "alias": str, "base_empresa": str }
SESSION_PENDING_KEY = "fe_afip_pending"


def _base_empresa_from_session(request):
    """Base empresa activa en la sesión."""
    return (request.session.get("user") or {}).get("base_empresa") or ""


def _get_cuit_from_administranet(base_empresa: str):
    """
    Obtiene CUIT y nombre de la empresa desde administraNET (tabla DatosEmpresa).
    Returns: (cuit_11, cuit_formateado, nombre_empresa, mysql_error).
    Si no hay empresa o CUIT inválido: (None, None, nombre_empresa, None).
    Si falla la conexión MySQL: (None, None, "", mysql_error).
    """
    if not base_empresa:
        logger.debug("fe_afip: base_empresa vacío en sesión.")
        return None, None, "", None
    try:
        svc = AdministraNETEmpresaService()
        empresa = svc.obtener_empresa(base_empresa)
        mysql_error = getattr(svc, "_last_mysql_error", None)
        nombre_empresa = (empresa.get("Nombre") or empresa.get("nombre") or "").strip() if empresa else ""
        if not empresa:
            logger.warning("fe_afip: no se encontró registro en DatosEmpresa para base_empresa=%s.", base_empresa)
            return None, None, nombre_empresa or "", mysql_error
        # Aceptar CUIT en mayúscula o minúscula (MySQL puede devolver según lower_case_table_names)
        cuit_val = empresa.get("CUIT") or empresa.get("cuit") or ""
        raw = (cuit_val or "").strip().replace("-", "").replace(" ", "")
        if len(raw) != 11 or not raw.isdigit():
            logger.info(
                "fe_afip: CUIT ausente o inválido en DatosEmpresa para %s (raw=%r, len=%s). Configurá el CUIT en administraNET.",
                base_empresa, raw[:20] if raw else "", len(raw),
            )
            return None, None, nombre_empresa, None
        formateado = f"{raw[:2]}-{raw[2:10]}-{raw[10]}" if len(raw) == 11 else raw
        return raw, formateado, nombre_empresa, None
    except Exception as e:
        logger.warning("fe_afip: no se pudo obtener datos de administraNET para %s: %s", base_empresa, e)
        return None, None, "", str(e)


@administranet_login_required
@tiene_permiso("fe_afip.view_afipconfig")
def config_list(request):
    base_empresa = _base_empresa_from_session(request)
    if not base_empresa:
        messages.error(request, "No hay empresa activa en la sesión.")
        return render(request, "fe_afip/config_list.html", {"config": None, "base_empresa": "", "can_manage_certs": False})
    config = AFIPConfig.objects.filter(base_empresa=base_empresa, activo=True).first()
    return render(request, "fe_afip/config_list.html", {
        "config": config,
        "base_empresa": base_empresa,
        "can_manage_certs": _can_manage_certs(request),
    })


def _config_form_context(base_empresa, config):
    """
    Contexto común para config_form: datos de empresa desde administraNET.
    cuit_no_disponible es True solo cuando no se obtiene CUIT de DatosEmpresa (conexión, tabla vacía o CUIT sin cargar).
    mysql_connection_error se rellena cuando falla la conexión a MySQL para mostrar diagnóstico.
    """
    cuit_empresa, cuit_formateado, nombre_empresa, mysql_error = _get_cuit_from_administranet(base_empresa)
    return {
        "config": config,
        "base_empresa": base_empresa,
        "cuit_empresa": cuit_empresa,
        "cuit_formateado": cuit_formateado,
        "nombre_empresa": nombre_empresa,
        "cuit_no_disponible": cuit_empresa is None,
        "mysql_connection_error": mysql_error or "",
    }


@administranet_login_required
@tiene_permiso("fe_afip.view_afipconfig")
def config_form(request, pk=None):
    base_empresa = _base_empresa_from_session(request)
    if not base_empresa:
        messages.error(request, "No hay empresa activa en la sesión. Seleccioná una empresa para configurar Facturación Electrónica AFIP.")
        return redirect("fe_afip:config_list")
    if pk:
        config = get_object_or_404(AFIPConfig, pk=pk)
        if config.base_empresa != base_empresa:
            raise PermissionDenied("No podés editar la configuración de otra empresa.")
    else:
        config = AFIPConfig.objects.filter(base_empresa=base_empresa).first()

    if request.method == "POST":
        perm = "fe_afip.change_afipconfig" if config else "fe_afip.add_afipconfig"
        if hasattr(request.user, "tiene_permiso") and not request.user.tiene_permiso(perm):
            raise PermissionDenied("Sin permiso para esta acción.")
        cuit_empresa, _cuit_fmt, _nombre, _mysql_err = _get_cuit_from_administranet(base_empresa)
        if not cuit_empresa:
            messages.error(request, "El CUIT de la empresa debe estar configurado en administraNET (DatosEmpresa) para guardar la configuración.")
            ctx = _config_form_context(base_empresa, config)
            ctx.update({
                "cert_path": request.POST.get("cert_path", ""),
                "key_path": request.POST.get("key_path", ""),
                "cache_dir": (request.POST.get("cache_dir") or "/tmp/pyafipws_cache").strip(),
                "modo_homologacion": request.POST.get("modo_homologacion") == "on",
                "name": (request.POST.get("name") or "Default").strip(),
            })
            return render(request, "fe_afip/config_form.html", ctx)
        name = (request.POST.get("name") or "Default").strip()
        cert_path = (request.POST.get("cert_path") or "").strip()
        key_path = (request.POST.get("key_path") or "").strip()
        modo_homologacion = request.POST.get("modo_homologacion") == "on"
        cache_dir = (request.POST.get("cache_dir") or "/tmp/pyafipws_cache").strip()
        if not cache_dir:
            cache_dir = "/tmp/pyafipws_cache"
        if not cert_path or not key_path:
            messages.error(request, "Certificado y clave privada son obligatorios.")
            return render(request, "fe_afip/config_form.html", _config_form_context(base_empresa, config))
        if cert_path:
            ok, err = validate_cert_cuit(cert_path, cuit_empresa)
            if not ok:
                messages.error(request, err)
                ctx = _config_form_context(base_empresa, config)
                ctx.update({
                    "cert_path": cert_path,
                    "key_path": key_path,
                    "cache_dir": cache_dir,
                    "modo_homologacion": modo_homologacion,
                    "name": name,
                })
                return render(request, "fe_afip/config_form.html", ctx)
        if config:
            config.name = name
            config.cert_path = cert_path
            config.key_path = key_path
            config.cuit = cuit_empresa
            config.modo_homologacion = modo_homologacion
            config.cache_dir = cache_dir
            config.save()
            messages.success(request, "Configuración AFIP actualizada.")
        else:
            AFIPConfig.objects.create(
                name=name,
                base_empresa=base_empresa,
                cert_path=cert_path,
                key_path=key_path,
                cuit=cuit_empresa,
                modo_homologacion=modo_homologacion,
                cache_dir=cache_dir,
                activo=True,
            )
            messages.success(request, "Configuración AFIP creada. Usá Homologación para todas las pruebas.")
        return redirect("fe_afip:config_list")

    return render(request, "fe_afip/config_form.html", _config_form_context(base_empresa, config))


def _get_allowed_roots():
    """Raíces bajo las cuales se permite listar archivos/directorios."""
    return getattr(django_settings, "FE_AFIP_BROWSE_ROOTS", ["/", "/tmp", "/var", "/home"])


def _path_under_allowed_root(path: str) -> bool:
    """True si path (absoluto, normalizado) está bajo alguna raíz permitida."""
    if not path or not os.path.isabs(path):
        return False
    try:
        real = os.path.realpath(path)
    except OSError:
        return False
    for root in _get_allowed_roots():
        if not root:
            continue
        root_real = os.path.realpath(root)
        if real == root_real or real.startswith(root_real + os.sep):
            return True
    return False


@administranet_login_required
@tiene_permiso("fe_afip.view_afipconfig")
def browse_path(request):
    """
    API para el explorador de archivos/directorios en la config AFIP.
    GET ?path=/some/dir → JSON { ok, entries: [ { name, path, is_dir } ], current_path }.
    path debe estar bajo FE_AFIP_BROWSE_ROOTS.
    """
    req_path = (request.GET.get("path") or "").strip() or os.sep
    if not os.path.isabs(req_path):
        req_path = os.path.abspath(req_path)
    try:
        current = os.path.realpath(req_path)
    except OSError as e:
        logger.warning("browse_path realpath: %s", e)
        return JsonResponse({"ok": False, "error": "Ruta no válida"})
    if not os.path.isdir(current):
        return JsonResponse({"ok": False, "error": "No es un directorio"})
    if not _path_under_allowed_root(current):
        return JsonResponse({"ok": False, "error": "Ruta no permitida para explorar"})
    entries = []
    try:
        names = sorted(os.listdir(current))
    except OSError as e:
        logger.warning("browse_path listdir: %s", e)
        return JsonResponse({"ok": False, "error": "No se puede listar el directorio"})
    for name in names:
        if name.startswith("."):
            continue
        full = os.path.join(current, name)
        try:
            is_dir = os.path.isdir(full)
        except OSError:
            continue
        try:
            path_real = os.path.realpath(full)
        except OSError:
            continue
        if is_dir and not _path_under_allowed_root(path_real):
            continue
        entries.append({"name": name, "path": path_real, "is_dir": is_dir})
    entries.sort(key=lambda e: (not e["is_dir"], e["name"].lower()))
    try:
        parent = os.path.dirname(current)
    except OSError:
        parent = None
    if parent and parent != current and _path_under_allowed_root(parent):
        entries.insert(0, {"name": "..", "path": os.path.realpath(parent), "is_dir": True})
    return JsonResponse({
        "ok": True,
        "current_path": current,
        "entries": entries,
    })


def _can_manage_certs(request):
    """Solo administrador/supervisor o quien tenga permiso de editar configuración AFIP."""
    if hasattr(request.user, "is_admin") and request.user.is_admin():
        return True
    if getattr(request.user, "cod_usuario", "").lower() == "supervisor":
        return True
    for perm in ("fe_afip.change_afipconfig", "fe_afip.add_afipconfig"):
        if hasattr(request.user, "tiene_permiso") and request.user.tiene_permiso(perm):
            return True
    return False


@administranet_login_required
def cert_wizard(request):
    """
    Asistente certificados ARCA: paso 1 generar CSR, paso 2 subir .crt.
    Solo usuarios con permiso de administrar configuración AFIP.
    """
    if not _can_manage_certs(request):
        raise PermissionDenied("Solo administradores o supervisores pueden gestionar certificados AFIP.")
    base_empresa = _base_empresa_from_session(request)
    if not base_empresa:
        messages.error(request, "No hay empresa activa en la sesión.")
        return redirect("fe_afip:config_list")

    config = AFIPConfig.objects.filter(base_empresa=base_empresa, activo=True).first()
    cuit_empresa, cuit_formateado, nombre_empresa, _mysql_err = _get_cuit_from_administranet(base_empresa)
    cuit_no_disponible = cuit_empresa is None

    # POST paso 1: generar CSR (CUIT siempre desde administraNET, no desde el formulario)
    if request.method == "POST" and request.POST.get("step") == "1":
        if cuit_no_disponible:
            messages.error(request, "El CUIT de la empresa debe estar configurado en administraNET (DatosEmpresa) para generar el CSR.")
            return render(request, "fe_afip/cert_wizard.html", {
                "base_empresa": base_empresa,
                "config": config,
                "nombre_empresa": nombre_empresa,
                "cuit_empresa": None,
                "cuit_formateado": "",
                "cuit_no_disponible": True,
                "mysql_connection_error": _mysql_err or "",
                "step": 1,
                "csr_pem": None,
                "arca_url": None,
            })
        alias = (request.POST.get("alias") or "synap").strip() or "synap"
        try:
            csr_pem, _key_path, token = generate_csr(cuit=cuit_empresa, alias=alias)
        except ValueError as e:
            messages.error(request, str(e))
            return render(request, "fe_afip/cert_wizard.html", {
                "base_empresa": base_empresa,
                "config": config,
                "nombre_empresa": nombre_empresa,
                "cuit_empresa": cuit_empresa,
                "cuit_formateado": cuit_formateado,
                "cuit_no_disponible": False,
                "mysql_connection_error": "",
                "step": 1,
                "csr_pem": None,
                "arca_url": None,
            })
        request.session[SESSION_PENDING_KEY] = {
            "token": token,
            "cuit": cuit_empresa,
            "alias": alias,
            "base_empresa": base_empresa,
        }
        request.session.modified = True
        return render(request, "fe_afip/cert_wizard.html", {
            "base_empresa": base_empresa,
            "config": config,
            "nombre_empresa": nombre_empresa,
            "cuit_empresa": cuit_empresa,
            "cuit_formateado": cuit_formateado,
            "cuit_no_disponible": False,
            "mysql_connection_error": "",
            "step": 2,
            "csr_pem": csr_pem,
            "arca_url": "https://serviciosweb.afip.gob.ar/clavefiscal/adminrel/agregarCertificado.aspx",
        })

    # GET: si piden volver al paso 1, limpiar sesión de certificado pendiente
    if request.method == "GET" and request.GET.get("reset") == "1":
        if SESSION_PENDING_KEY in request.session:
            del request.session[SESSION_PENDING_KEY]
            request.session.modified = True
        return redirect("fe_afip:cert_wizard")

    # GET o sin step: mostrar paso 1 o 2 según sesión
    pending = request.session.get(SESSION_PENDING_KEY) or {}
    if pending.get("base_empresa") == base_empresa and pending.get("token"):
        return render(request, "fe_afip/cert_wizard.html", {
            "base_empresa": base_empresa,
            "config": config,
            "nombre_empresa": nombre_empresa,
            "cuit_empresa": cuit_empresa,
            "cuit_formateado": cuit_formateado,
            "cuit_no_disponible": cuit_no_disponible,
            "mysql_connection_error": _mysql_err or "",
            "step": 2,
            "csr_pem": None,
            "arca_url": "https://serviciosweb.afip.gob.ar/clavefiscal/adminrel/agregarCertificado.aspx",
        })
    return render(request, "fe_afip/cert_wizard.html", {
        "base_empresa": base_empresa,
        "config": config,
        "nombre_empresa": nombre_empresa,
        "cuit_empresa": cuit_empresa,
        "cuit_formateado": cuit_formateado,
        "cuit_no_disponible": cuit_no_disponible,
        "mysql_connection_error": _mysql_err or "",
        "step": 1,
        "csr_pem": None,
        "arca_url": None,
    })


@administranet_login_required
def cert_upload(request):
    """
    POST: subir archivo .crt/.pem obtenido de ARCA; guardar y actualizar AFIPConfig.
    Solo administrador/supervisor o permiso fe_afip.change_afipconfig/add.
    """
    if not _can_manage_certs(request):
        raise PermissionDenied("Solo administradores o supervisores pueden subir certificados AFIP.")
    base_empresa = _base_empresa_from_session(request)
    if not base_empresa:
        messages.error(request, "No hay empresa activa en la sesión.")
        return redirect("fe_afip:config_list")

    if request.method != "POST":
        return redirect("fe_afip:cert_wizard")

    pending = request.session.get(SESSION_PENDING_KEY) or {}
    if pending.get("base_empresa") != base_empresa or not pending.get("token"):
        messages.error(request, "Sesión de certificado expirada. Generá de nuevo el CSR en el paso 1.")
        if SESSION_PENDING_KEY in request.session:
            del request.session[SESSION_PENDING_KEY]
            request.session.modified = True
        return redirect("fe_afip:cert_wizard")

    cert_file = request.FILES.get("cert_file")
    if not cert_file:
        messages.error(request, "Seleccioná el archivo del certificado (.crt o .pem) descargado de AFIP.")
        return redirect("fe_afip:cert_wizard")

    try:
        cert_content = cert_file.read()
    except Exception as e:
        logger.warning("cert_upload read: %s", e)
        messages.error(request, "No se pudo leer el archivo.")
        return redirect("fe_afip:cert_wizard")

    if len(cert_content) > 10240:
        messages.error(request, "El archivo es demasiado grande.")
        return redirect("fe_afip:cert_wizard")

    try:
        cert_path, key_path = save_certificate_and_apply(
            token=pending["token"],
            cert_file_content=cert_content,
            base_empresa=base_empresa,
            cuit=pending.get("cuit", ""),
        )
    except ValueError as e:
        messages.error(request, str(e))
        return redirect("fe_afip:cert_wizard")

    if SESSION_PENDING_KEY in request.session:
        del request.session[SESSION_PENDING_KEY]
        request.session.modified = True

    modo_homologacion = request.POST.get("modo_homologacion", "1") == "1"
    config = AFIPConfig.objects.filter(base_empresa=base_empresa).first()
    cuit_clean = (pending.get("cuit") or "").replace("-", "").replace(" ", "")
    cache_dir = getattr(config, "cache_dir", None) or "/tmp/pyafipws_cache"
    if config:
        config.cert_path = cert_path
        config.key_path = key_path
        if cuit_clean and len(cuit_clean) == 11:
            config.cuit = cuit_clean
        config.modo_homologacion = modo_homologacion
        config.save()
        messages.success(request, "Certificado importado y configuración AFIP actualizada.")
    else:
        AFIPConfig.objects.create(
            name="Default",
            base_empresa=base_empresa,
            cert_path=cert_path,
            key_path=key_path,
            cuit=cuit_clean or "",
            modo_homologacion=modo_homologacion,
            cache_dir=cache_dir,
            activo=True,
        )
        messages.success(request, "Certificado importado y configuración AFIP creada.")

    return redirect("fe_afip:config_list")
