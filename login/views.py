import json
import firebase_admin.auth as auth
import logging

from django.urls import reverse
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from firebase_admin import auth
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required

logger = logging.getLogger(__name__)

def firebase_config_js(request):
    config = settings.FIREBASE_CONFIG

    login_url = reverse("login:login")
    logout_url = reverse("login:logout")
    reset_url = reverse("login:reset_password")

    js_content = f"""
// Archivo generado automáticamente por Django

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

function getCookie(name) {{
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {{
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {{
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {{
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }}
        }}
    }}
    return cookieValue;
}}

export {{ firebaseConfig, backendRoutes, getCookie }};
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
            logger.info(f"🟢 Token decodificado correctamente: {decoded_token}")
            request.session["user"] = decoded_token

            return JsonResponse({"message": "Login exitoso"}, status=200)

        except Exception as e:
            logger.error(f"❌ Error al verificar token: {str(e)}")
            return JsonResponse({"error": str(e)}, status=400)

    return render(request, "login/login.html")

def logout_view(request):
    request.session.flush()  # Elimina toda la sesión
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
    if not request.session.get("user"):
        return redirect("login:login")  # Redirige si no está logueado

    return render(request, "login/perfil.html", {"user": request.session["user"]})

def dashboard_view(request):
    if "user" not in request.session:
        return redirect("login:login")

    user_info = request.session.get("user", {})
    return render(request, "dashboard/dashboard.html", {"user": user_info})

def completar_perfil_view(request):
    return render(request, "login/completar_perfil.html")