"""
Vistas de autenticación para administraNET Analytics
Reemplaza Firebase con autenticación directa contra MySQL de administraNET Gestión
"""
import json
import logging
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from urllib.parse import urlparse
from .administranet_auth import AdministraNETAuth
from core.models import Empresa

logger = logging.getLogger(__name__)


@csrf_exempt
def login_view(request):
    """
    Vista de login para administraNET Analytics
    Reemplaza la autenticación Firebase con autenticación directa a MySQL
    """
    if request.session.get("user"):
        return redirect("core:dashboard")

    # Inicializar servicio con configuración por defecto del .env
    auth_service = AdministraNETAuth()
    
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            cod_usuario = data.get("cod_usuario", "").strip()
            password = data.get("password", "").strip()
            base_empresa = data.get("base_empresa", "").strip()
            server = data.get("server", "").strip()
            # Usar puerto del .env si no se envía (evita "Unknown database" por conectar al puerto equivocado)
            default_port = str(settings.DATABASES["mysql"].get("PORT", "3306"))
            port = data.get("port", default_port).strip() or default_port
            
            if not cod_usuario or not password or not base_empresa:
                return JsonResponse({
                    "error": "Usuario, contraseña y empresa son requeridos"
                }, status=400)
            
            # Si se proporciona servidor, usar también el puerto configurado
            if server:
                auth_service = AdministraNETAuth(server=server, port=port)
            
            # Validar usuario
            user_data = auth_service.validate_user(cod_usuario, password, base_empresa)
            
            if not user_data:
                return JsonResponse({
                    "error": "Usuario y contraseña incorrectos"
                }, status=401)
            
            # Obtener IP del cliente
            ip_address = request.META.get('REMOTE_ADDR', '127.0.0.1')
            # Crear sesión en administraNET
            session_data = auth_service.create_session(user_data, base_empresa, ip_address)
            
            # Guardar datos en sesión Django
            request.session["user"] = {
                "id_usuario": user_data['id_usuario'],
                "cod_usuario": user_data['cod_usuario'],
                "nombre_usuario": user_data['nombre_usuario'],
                "apellido_usuario": user_data['apellido_usuario'],
                "nombre_completo": f"{user_data['nombre_usuario']} {user_data['apellido_usuario']}",
                "id_empresa": user_data['id_empresa'],
                "id_sucursal": user_data['id_sucursal'],
                "id_puesto": user_data['id_puesto'],
                "nombre_puesto": user_data.get('nombre_puesto'),
                "base_empresa": base_empresa,
                "id_sesion": session_data['id_sesion'] if session_data else None
            }
            
            # Sincronización automática de permisos Synap → permiso_sistema (con cache por empresa)
            try:
                from core.services.sync_permisos_synap import asegurar_permisos_synap_si_procede
                asegurar_permisos_synap_si_procede(base_empresa)
            except Exception as e:
                logger.debug("Sync permisos post-login (no crítico): %s", e)
            
            logger.info(f"✅ Login exitoso: {cod_usuario} en empresa {base_empresa}")
            
            # Validar y retornar next si está presente
            next_url = request.GET.get("next")
            if next_url and urlparse(next_url).path.startswith("/"):
                return JsonResponse({"redirect": next_url})
            
            return JsonResponse({"redirect": reverse("core:dashboard")})

        except Exception as e:
            logger.error(f"❌ Error en login: {e}", exc_info=True)
            return JsonResponse({"error": str(e)}, status=400)
    
    # GET request - mostrar formulario de login
    auth_service = AdministraNETAuth()
    
    # Obtener lista de empresas desde la base 'empresas' del servidor configurado
    # Similar a como lo hace administraNET Gestión: conecta a base 'empresas' y hace SELECT * FROM empresas
    empresas = auth_service.get_empresas()
    servidores = auth_service.get_servidores()
    
    # Servidor por defecto: siempre desde DB_HOST/DB_PORT del .env (settings)
    mysql_config = settings.DATABASES['mysql']
    db_host = mysql_config.get('HOST', '')
    db_port = str(mysql_config.get('PORT', '3306'))
    server_default = {
        'host': db_host,
        'port': db_port,
        'descripcion': f'Servidor {db_host}'
    }
    
    logger.info(f"📋 Mostrando login con {len(empresas)} empresas disponibles (servidor={db_host})")
    
    return render(request, "login/login_administranet.html", {
        'empresas': empresas,
        'servidores': servidores,
        'server_default': server_default,
        'db_host': db_host,
        'db_port': db_port,
    })


def get_empresas_api(request):
    """
    API para obtener empresas disponibles (AJAX)
    """
    try:
        server = request.GET.get('server', '')
        port = request.GET.get('port', '3306')
        
        auth_service = AdministraNETAuth(server=server, port=port) if server else AdministraNETAuth()
        empresas = auth_service.get_empresas()
        
        return JsonResponse({
            'success': True,
            'empresas': empresas
        })
    except Exception as e:
        logger.error(f"Error al obtener empresas: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def logout_view(request):
    """
    Cerrar sesión completa en administraNET Analytics
    
    Proceso:
    1. Guardar datos necesarios (id_sesion, base_empresa) ANTES de limpiar
    2. Cerrar sesión en administraNET (UPDATE fechafin)
    3. Limpiar sesión de Django completamente
    4. Crear respuesta de redirección
    5. Eliminar cookies explícitamente
    6. Retornar respuesta
    
    IMPORTANTE: El orden es crítico para evitar que el middleware recree el usuario
    """
    # PASO 1: Guardar datos necesarios ANTES de limpiar la sesión
    user_data = None
    id_sesion = None
    base_empresa = None
    id_vendedor_usr = None

    if hasattr(request, 'session') and request.session:
        user_data = request.session.get("user")
        if user_data:
            id_sesion = user_data.get('id_sesion')
            base_empresa = user_data.get('base_empresa')
            id_vendedor_usr = user_data.get('id_vendedor_usr')

    # PASO 1b: Cierra_Logueo_Vendedor (paridad Principal VB6) — antes de cerrar sesión
    if id_vendedor_usr is not None and base_empresa:
        try:
            auth_service = AdministraNETAuth()
            with auth_service.get_connection(base_empresa) as connection:
                cursor = connection.cursor()
                cursor.execute("""
                    UPDATE viajantes
                    SET logueado = 'No', detalle_logueo = NULL, ip_logueo = NULL
                    WHERE CodViajante = %s
                """, [id_vendedor_usr])
                connection.commit()
                cursor.close()
            logger.info("Cierra_Logueo_Vendedor: CodViajante=%s", id_vendedor_usr)
        except Exception as e:
            logger.warning("Cierra_Logueo_Vendedor no aplicado (viajantes): %s", e)

    # PASO 2: Cerrar sesión en administraNET (MySQL) - DEBE ser antes de limpiar Django
    if id_sesion and base_empresa:
        try:
            auth_service = AdministraNETAuth()
            with auth_service.get_connection(base_empresa) as connection:
                cursor = connection.cursor()
                cursor.execute("""
                    UPDATE sesion
                    SET fechafin = NOW()
                    WHERE id_sesion = %s AND fechafin IS NULL
                """, [id_sesion])
                connection.commit()
                cursor.close()
            logger.info("Sesión %s cerrada en administraNET", id_sesion)
        except Exception as e:
            logger.error(f"❌ Error al cerrar sesión en administraNET: {e}", exc_info=True)
            # Continuar con el logout aunque falle el cierre en administraNET
    
    # PASO 3: Limpiar sesión de Django completamente
    if hasattr(request, 'session') and request.session:
        try:
            # Eliminar todas las claves de la sesión
            session_keys = list(request.session.keys())
            for key in session_keys:
                try:
                    del request.session[key]
                except (KeyError, AttributeError):
                    pass
            logger.debug(f"Eliminadas {len(session_keys)} claves de sesión")
        except Exception as e:
            logger.warning(f"Error al eliminar claves de sesión: {e}")
        
        try:
            # Limpiar y regenerar la clave de sesión (importante para seguridad)
            request.session.flush()
            logger.debug("Sesión flush() ejecutado")
        except Exception as e:
            logger.warning(f"Error al hacer flush de sesión: {e}")
        
        try:
            # Establecer expiración inmediata
            request.session.set_expiry(0)
            logger.debug("Expiración de sesión establecida en 0")
        except Exception as e:
            logger.warning(f"Error al establecer expiración de sesión: {e}")
    
    # PASO 4: Crear respuesta de redirección
    # Usar URL absoluta para evitar problemas con middlewares que interceptan redirects
    try:
        login_url = reverse("login:login")
        logger.debug(f"URL de login obtenida: {login_url}")
    except Exception as e:
        logger.error(f"Error al obtener URL de login: {e}")
        login_url = "/login/"
    
    # Crear redirect con HttpResponseRedirect explícito
    # Esto asegura que el redirect funcione incluso si hay middlewares que interceptan
    response = HttpResponseRedirect(login_url)
    
    # Verificar que el redirect se creó correctamente
    if not hasattr(response, 'url') or response.url != login_url:
        logger.error(f"Error: El redirect no se creó correctamente. URL esperada: {login_url}")
        # Fallback: crear redirect manualmente
        response = HttpResponseRedirect(login_url)
    
    logger.info(f"✅ Redirect a login: {login_url} (status: {response.status_code})")
    
    # PASO 5: Eliminar cookies explícitamente del navegador
    # Cookie de sesión
    try:
        session_cookie_name = getattr(settings, 'SESSION_COOKIE_NAME', 'sessionid')
        session_cookie_path = getattr(settings, 'SESSION_COOKIE_PATH', '/')
        session_cookie_domain = getattr(settings, 'SESSION_COOKIE_DOMAIN', None)
        session_cookie_samesite = getattr(settings, 'SESSION_COOKIE_SAMESITE', 'Lax')
        session_cookie_secure = getattr(settings, 'SESSION_COOKIE_SECURE', False)
        session_cookie_httponly = getattr(settings, 'SESSION_COOKIE_HTTPONLY', True)
        
        response.delete_cookie(
            session_cookie_name,
            path=session_cookie_path,
            domain=session_cookie_domain,
            samesite=session_cookie_samesite,
            secure=session_cookie_secure
        )
        logger.debug(f"Cookie de sesión '{session_cookie_name}' eliminada")
    except Exception as e:
        logger.warning(f"No se pudo eliminar la cookie de sesión: {e}")
    
    # Cookie CSRF
    try:
        csrf_cookie_name = getattr(settings, 'CSRF_COOKIE_NAME', 'csrftoken')
        csrf_cookie_path = getattr(settings, 'CSRF_COOKIE_PATH', '/')
        csrf_cookie_domain = getattr(settings, 'CSRF_COOKIE_DOMAIN', None)
        csrf_cookie_samesite = getattr(settings, 'CSRF_COOKIE_SAMESITE', 'Lax')
        csrf_cookie_secure = getattr(settings, 'CSRF_COOKIE_SECURE', False)
        
        response.delete_cookie(
            csrf_cookie_name,
            path=csrf_cookie_path,
            domain=csrf_cookie_domain,
            samesite=csrf_cookie_samesite,
            secure=csrf_cookie_secure
        )
        logger.debug(f"Cookie CSRF '{csrf_cookie_name}' eliminada")
    except Exception as e:
        logger.warning(f"No se pudo eliminar la cookie CSRF: {e}")
    
    # PASO 6: Logging final y retornar respuesta
    logger.info(f"✅ Logout completado para usuario {user_data.get('cod_usuario') if user_data else 'desconocido'}")
    return response


def perfil_view(request):
    """Vista de perfil de usuario"""
    session_user = request.session.get("user")
    if not session_user:
        return redirect("login:login")

    if request.method == "POST":
        # Perfil de usuario - sin cambio de idioma (solo español)
        messages.success(request, "Perfil actualizado correctamente")
        return redirect("login:perfil")

    return render(request, "login/perfil.html", {
        "user": session_user
    })
