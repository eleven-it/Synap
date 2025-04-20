import json
import logging
from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse, HttpResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from firebase_admin import auth, firestore
from core.utils import sincronizar_usuario_desde_firestore
from core.models import UsuarioExtendido, Rol

logger = logging.getLogger(__name__)

def firebase_config_js(request):
    config = settings.FIREBASE_CONFIG

    login_url = reverse("login:login")
    logout_url = reverse("login:logout")
    reset_url = reverse("login:reset_password")

    js_content = f"""
    const firebaseConfig = {{
        apiKey: "{config['apiKey']}",
        authDomain: "{config['authDomain']}",
        projectId: "{config['projectId']}",
        storageBucket: "{config['storageBucket']}",
        messagingSenderId: "{config['messagingSenderId']}",
        appId: "{config['appId']}",
        measurementId: "{config['measurementId']}",
        clientId: "{config.get('clientId', '')}"
    }};

    const backendRoutes = {{
        login: "{login_url}",
        logout: "{logout_url}",
        resetPassword: "{reset_url}"
    }};
    """
    return HttpResponse(js_content, content_type="application/javascript")


@csrf_exempt
def login_view(request):
    if request.session.get("user"):
        tipo = request.session["user"].get("tipo_usuario")
        if tipo == "cliente":
            return redirect("clientes:dashboard")
        elif tipo == "proveedor":
            return redirect("proveedores:dashboard")
        else:
            return redirect("login:completar_perfil")

    if request.method == "POST":
        try:
            data = json.loads(request.body)
            id_token = data.get("idToken")

            if not id_token:
                return JsonResponse({"error": "No se recibió ID Token"}, status=400)

            decoded_token = auth.verify_id_token(id_token)
            usuario_extendido = sincronizar_usuario_desde_firestore(decoded_token)

            permisos_rol = set(usuario_extendido.rol.permisos.values_list("codigo", flat=True)) if usuario_extendido.rol else set()
            permisos_directos = set(usuario_extendido.permisos_extra.values_list("codigo", flat=True))
            todos_permisos = permisos_rol | permisos_directos

            request.session["user"] = {
                "uid": usuario_extendido.uid,
                "email": usuario_extendido.email,
                "nombre": usuario_extendido.nombre,
                "rol": usuario_extendido.rol.nombre if usuario_extendido.rol else "",
                "permisos": list(todos_permisos),
                "tipo_usuario": usuario_extendido.rol.nombre if usuario_extendido.rol else "",
                "idioma": usuario_extendido.idioma or "es"
            }

            if not usuario_extendido.nombre or not usuario_extendido.rol:
                return JsonResponse({"redirect": reverse("login:completar_perfil")}, status=200)

            if usuario_extendido.rol.nombre.lower() == "cliente":
                return JsonResponse({"redirect": reverse("clientes:dashboard")}, status=200)
            elif usuario_extendido.rol.nombre.lower() == "proveedor":
                return JsonResponse({"redirect": reverse("proveedores:dashboard")}, status=200)

            return JsonResponse({"redirect": reverse("login:completar_perfil")}, status=200)

        except Exception as e:
            logger.error(f"❌ Error al verificar token: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, "login/login.html")


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
    return render(request, "login/register.html")


def perfil_view(request):
    session_user = request.session.get("user")
    if not session_user:
        return redirect("login:login")

    try:
        usuario = UsuarioExtendido.objects.get(uid=session_user["uid"])
    except UsuarioExtendido.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
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

        # Validación y cambio de contraseña
        if nueva_password:
            if nueva_password != confirmar_password:
                messages.error(request, "Las contraseñas no coinciden.")
                return render(request, "login/perfil.html", {
                    "user": request.session["user"]
                })
            try:
                from firebase_admin import auth
                auth.update_user(uid=usuario.uid, password=nueva_password)
                messages.success(request, "Contraseña actualizada correctamente.")
            except Exception as e:
                messages.error(request, f"Error al actualizar contraseña: {e}")
                return render(request, "login/perfil.html", {
                    "user": request.session["user"]
                })

        usuario.save()

        # Refrescar sesión
        request.session["user"]["nombre"] = usuario.nombre
        request.session["user"]["idioma"] = usuario.idioma

        messages.success(request, "✅ Cambios guardados correctamente.")
        return redirect("login:perfil")

def completar_perfil_view(request):
    user = request.session.get("user")
    if not user:
        return redirect("login:login")

    try:
        usuario = UsuarioExtendido.objects.get(uid=user["uid"])
    except UsuarioExtendido.DoesNotExist:
        messages.error(request, "El usuario no fue encontrado.")
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
            if rol:
                usuario.rol = rol

        usuario.save()

        # Refrescar los datos en la sesión
        request.session["user"] = {
            "uid": usuario.uid,
            "email": usuario.email,
            "nombre": usuario.nombre,
            "rol": usuario.rol.nombre if usuario.rol else "",
            "tipo_usuario": usuario.rol.nombre if usuario.rol else "",
            "idioma": usuario.idioma,
        }

        messages.success(request, "¡Perfil actualizado correctamente!")
        return redirect("login:completar_perfil")

    return render(request, "login/completar_perfil.html", {
        "user": request.session["user"],
    })
