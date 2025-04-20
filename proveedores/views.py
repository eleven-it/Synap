from django.shortcuts import render, redirect
from firebase_admin import firestore
from django.views.decorators.csrf import csrf_exempt
from core.decorators import tiene_permiso
from django.contrib import messages
from core.models import UsuarioExtendido
from firebase_admin import auth

# Inicializa cliente Firestore
db = firestore.client()

@csrf_exempt
@tiene_permiso("administrar_usuarios")
def dashboard_view(request):
    user = request.session.get("user")
    if not user:
        return redirect("login:login")

    uid = user.get("uid")
    if not uid:
        return redirect("login:login")

    # 🔍 Consultar tipo_usuario desde Firestore
    doc_ref = db.collection("usuarios").document(uid)
    doc = doc_ref.get()

    if not doc.exists:
        return redirect("login:completar_perfil")

    tipo = doc.to_dict().get("tipo_usuario")

    if tipo != "proveedor":
        return redirect("login:login")

    return render(request, "proveedores/dashboard.html", {"user": user})

def perfil_view(request):
    user_data = request.session.get("user")
    if not user_data:
        return redirect("login:login")

    try:
        usuario = UsuarioExtendido.objects.get(uid=user_data["uid"])
    except UsuarioExtendido.DoesNotExist:
        messages.error(request, "Usuario no encontrado.")
        return redirect("login:login")

    if request.method == "POST":
        nombre = request.POST.get("nombre", "").strip()
        idioma = request.POST.get("idioma", "es")
        nueva = request.POST.get("nueva_password", "")
        confirmar = request.POST.get("confirmar_password", "")

        if nombre:
            usuario.nombre = nombre
        if idioma in ["es", "en", "pt"]:
            usuario.idioma = idioma

        if nueva:
            if nueva == confirmar:
                try:
                    auth.update_user(uid=usuario.uid, password=nueva)
                    messages.success(request, "Contraseña actualizada correctamente.")
                except Exception as e:
                    messages.error(request, f"Error al cambiar la contraseña: {e}")
            else:
                messages.error(request, "Las contraseñas no coinciden.")

        usuario.save()
        request.session["user"]["nombre"] = usuario.nombre
        request.session["user"]["idioma"] = usuario.idioma
        messages.success(request, "Cambios guardados correctamente.")
        return redirect("proveedores:perfil")

    return render(request, "proveedores/perfil.html", {"user": user_data})


def historial_view(request):
    user = request.session.get("user")
    if not user:
        return redirect("login:login")
    return render(request, "proveedores/historial.html", {"user": user})
