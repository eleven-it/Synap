from django.shortcuts import render, redirect
from core.decorators import permiso_requerido

@permiso_requerido("acceso_publico")
def dashboard_view(request):
    if not request.session.get("user"):
        return redirect("login:login")

    return render(request, "clientes/dashboard.html", {"user": request.session["user"]})


