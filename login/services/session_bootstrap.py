"""
Bootstrap de sesión Django post-autenticación AdministraNET (password o WebAuthn unlock).
"""
import logging

from login.administranet_auth import AdministraNETAuth

logger = logging.getLogger(__name__)


def bootstrap_synap_session(
    request,
    user_data,
    base_empresa,
    *,
    session_age=None,
    auth_service=None,
    ip_address=None,
):
    """
    Crea sesión AdministraNET + sesión Django y ejecuta hooks post-login.

    Args:
        request: HttpRequest Django
        user_data: dict retornado por validate_user / get_user_by_id
        base_empresa: base MySQL seleccionada
        session_age: segundos para request.session.set_expiry (ej. WEBAUTHN_SESSION_AGE)
        auth_service: instancia AdministraNETAuth opcional
        ip_address: IP cliente; default REMOTE_ADDR

    Returns:
        dict con id_sesion AdministraNET (puede ser None)
    """
    if auth_service is None:
        auth_service = AdministraNETAuth()
    if ip_address is None:
        ip_address = request.META.get("REMOTE_ADDR", "127.0.0.1")

    session_data = auth_service.create_session(user_data, base_empresa, ip_address)
    nombre_empresa_login = auth_service.nombre_empresa_por_base(base_empresa) or base_empresa

    request.session["user"] = {
        "id_usuario": user_data["id_usuario"],
        "cod_usuario": user_data["cod_usuario"],
        "nombre_usuario": user_data["nombre_usuario"],
        "apellido_usuario": user_data["apellido_usuario"],
        "nombre_completo": f"{user_data['nombre_usuario']} {user_data['apellido_usuario']}",
        "id_empresa": user_data["id_empresa"],
        "id_sucursal": user_data["id_sucursal"],
        "id_puesto": user_data["id_puesto"],
        "nombre_puesto": user_data.get("nombre_puesto"),
        "base_empresa": base_empresa,
        "nombre_empresa": nombre_empresa_login,
        "id_sesion": session_data["id_sesion"] if session_data else None,
    }

    try:
        from ecom.services.mayoristapp_sesion_contexto import contexto_usuario_mayoristapp

        contexto_usuario_mayoristapp(request, persistir=True)
    except Exception as e:
        logger.debug("Contexto mayoristapp post-login (no crítico): %s", e)

    try:
        from core.services.synap_permisos_seed import asegurar_synap_schema_si_procede

        asegurar_synap_schema_si_procede(base_empresa)
    except Exception as e:
        logger.debug("Asegurar esquema Synap post-login (no crítico): %s", e)

    try:
        from mpr.repositories.operario_usuario import resolver_operario_por_usuario

        id_operario = resolver_operario_por_usuario(base_empresa, user_data["id_usuario"])
        if id_operario:
            request.session["user"]["id_operario"] = id_operario
            request.session.modified = True
    except Exception as e:
        logger.debug("Resolver operario MPR post-login (no crítico): %s", e)

    if session_age is not None:
        request.session.set_expiry(session_age)

    return session_data
