from django.shortcuts import render, redirect
from firebase_admin import firestore
from core.decorators import permiso_requerido

# Inicializa cliente Firestore
db = firestore.client()

@permiso_requerido("acceso_publico")
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


