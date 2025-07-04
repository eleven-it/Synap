import json
import logging
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django_project.firebase_config import get_firebase_app
import firebase_admin
from firebase_admin import firestore
from firebase_admin import auth
from core.utils import sincronizar_usuario_desde_firestore
from core.models import UsuarioExtendido, Rol, Empresa
from urllib.parse import urlparse
from django.utils import translation
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)

def firebase_config_js(request):
    config = settings.FIREBASE_CONFIG

    login_url = reverse("login:login")
    logout_url = reverse("login:logout")
    reset_url = reverse("login:reset_password")

    js_content = f"""
export const firebaseConfig = {{
    apiKey: "{config['apiKey']}",
    authDomain: "{config['authDomain']}",
    projectId: "{config['projectId']}",
    storageBucket: "{config['storageBucket']}",
    messagingSenderId: "{config['messagingSenderId']}",
    appId: "{config['appId']}",
    measurementId: "{config.get('measurementId', '')}",
    clientId: "{config.get('clientId', '')}"
}};

export const backendRoutes = {{
    login: "{login_url}",
    logout: "{logout_url}",
    resetPassword: "{reset_url}"
}};

export function getCookie(name) {{
    const value = `; ${{document.cookie}}`;
    const parts = value.split(`; ${{name}}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
}}
"""

    return HttpResponse(js_content, content_type="application/javascript")


@csrf_exempt
def login_view(request):
    if request.session.get("user"):
        return redirect("core:dashboard")

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            id_token = data.get("idToken")

            if not id_token or not isinstance(id_token, str):
                return JsonResponse({"error": "ID Token inválido o ausente"}, status=400)

            get_firebase_app()
            decoded_token = auth.verify_id_token(id_token)
            usuario_extendido = sincronizar_usuario_desde_firestore(decoded_token)

            # Actualizar último acceso
            usuario_extendido.actualizar_ultimo_acceso()

            permisos_roles = set()
            if hasattr(usuario_extendido, "roles"):
                for rol in usuario_extendido.roles.all():
                    permisos_roles |= set(rol.permisos.values_list("codigo", flat=True))
            permisos_directos = set(usuario_extendido.permisos_extra.values_list("codigo", flat=True))
            permisos_totales = permisos_roles | permisos_directos

            request.session["user"] = {
                "uid": usuario_extendido.uid,
                "idioma": usuario_extendido.idioma or "es"
            }

            logger.info(f"✅ Login exitoso: {usuario_extendido.email} ({usuario_extendido.uid})")

            # ✅ Validar y retornar next si está presente
            next_url = request.GET.get("next")
            if next_url and urlparse(next_url).path.startswith("/"):
                return JsonResponse({"redirect": next_url})
            return JsonResponse({"redirect": reverse("core:dashboard")})

        except Exception as e:
            logger.error(f"❌ Error en login: {e}")
            return JsonResponse({"error": str(e)}, status=400)

    # Si es GET, devolvemos el template según el dispositivo
    if hasattr(request, 'is_mobile') and request.is_mobile:
        template_name = "login/login_mobile.html"
    else:
        template_name = "login/login.html"
    
    # Obtener empresa activa para el contexto
    empresa_activa = Empresa.objects.filter(activa=True).first()
    
    return render(request, template_name, {
        'empresa_activa': empresa_activa
    })


def logout_view(request):
    request.session.flush()
    return render(request, "login/logout.html")

def reset_password_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        try:
            link = auth.generate_password_reset_link(email)
            return JsonResponse({"message": "Correo enviado"}, status=200)
        except Exception as e:
            logger.error(f"Error al generar link de reseteo: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, "login/reset_password.html")

def register_view(request):
    if request.session.get("user"):
        return redirect("dashboard:home")
    
    # Seleccionar template según el dispositivo
    if hasattr(request, 'is_mobile') and request.is_mobile:
        template_name = "login/register_mobile.html"
    else:
        template_name = "login/register.html"
    
    # Obtener empresa activa para el contexto
    empresa_activa = Empresa.objects.filter(activa=True).first()
    
    return render(request, template_name, {
        'empresa_activa': empresa_activa
    })

def perfil_view(request):
    session_user = request.session.get("user")
    if not session_user:
        return redirect("login:login")

    try:
        usuario = UsuarioExtendido.objects.get(uid=session_user["uid"])
    except UsuarioExtendido.DoesNotExist:
        messages.error(request, _( "User not found." ))
        return redirect("login:login")

    if request.method == "POST":
        nuevo_nombre = request.POST.get("nombre", "").strip()
        nuevo_idioma = request.POST.get("idioma", "es")
        nueva_password = request.POST.get("nueva_password", "")
        confirmar_password = request.POST.get("confirmar_password", "")

        if nuevo_nombre:
            usuario.nombre = nuevo_nombre

        if nuevo_idioma in ["es", "en", "pt"]:
            usuario.idioma = nuevo_idioma
            # Actualizar idioma en la sesión y en la request
            request.session["django_language"] = nuevo_idioma
            translation.activate(nuevo_idioma)

        # Validación y cambio de contraseña
        if nueva_password:
            if nueva_password != confirmar_password:
                messages.error(request, _( "Passwords do not match." ))
                return render(request, "login/perfil.html", {
                    "usuario": usuario,
                    "user": request.session["user"]
                })
            try:
                auth.update_user(uid=usuario.uid, password=nueva_password)
                messages.success(request, _( "Password updated successfully." ))
            except Exception as e:
                messages.error(request, _( "Error updating password: %(error)s" ) % {"error": e})
                return render(request, "login/perfil.html", {
                    "usuario": usuario,
                    "user": request.session["user"]
                })

        usuario.save()

        # Refrescar sesión
        request.session["user"]["nombre"] = usuario.nombre
        request.session["user"]["idioma"] = usuario.idioma

        messages.success(request, _( "✅ Changes saved successfully." ))
        return redirect("login:perfil")

    # GET request - mostrar el formulario
    return render(request, "login/perfil.html", {
        "usuario": usuario,
        "user": request.session["user"]
    })

def completar_perfil_view(request):
    user = request.session.get("user")
    if not user:
        return redirect("login:login")

    try:
        usuario = UsuarioExtendido.objects.get(uid=user["uid"])
    except UsuarioExtendido.DoesNotExist:
        messages.error(request, _( "User not found." ))
        return redirect("login:login")

    if request.method == "POST":
        nuevo_nombre = request.POST.get("nombre", "").strip()
        idioma = request.POST.get("idioma", "es")
        rol_nombre = request.POST.get("rol_nombre", "").strip()

        if nuevo_nombre:
            usuario.nombre = nuevo_nombre
        if idioma in ["es", "en", "pt"]:
            usuario.idioma = idioma
        if rol_nombre:
            rol = Rol.objects.filter(nombre__iexact=rol_nombre).first()
            if rol and rol not in usuario.roles.all():
                usuario.roles.add(rol)

        usuario.save()

        # Refrescar los datos en la sesión
        request.session["user"] = {
            "uid": usuario.uid,
            "email": usuario.email,
            "nombre": usuario.nombre,
            "idioma": usuario.idioma,
        }

        messages.success(request, _( "Profile updated successfully!" ))
        return redirect("login:completar_perfil")

    return render(request, "login/completar_perfil.html", {
        "user": request.session["user"],
    })

def index_view(request):
    # Obtener empresa activa para el contexto
    empresa_activa = Empresa.objects.filter(activa=True).first()
    
    # Seleccionar template según el dispositivo
    if hasattr(request, 'is_mobile') and request.is_mobile:
        template_name = "login/index_mobile.html"
    else:
        template_name = "login/index.html"
    
    return render(request, template_name, {
        'empresa_activa': empresa_activa
    })
