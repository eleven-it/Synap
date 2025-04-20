from django.shortcuts import render, redirect
from django.views.decorators.csrf import csrf_exempt
from core.decorators import tiene_permiso

@csrf_exempt
@tiene_permiso("administrar_usuarios")
def dashboard_view(request):
    if not request.session.get("user"):
        return redirect("login:login")

    return render(request, "clientes/dashboard.html", {"user": request.session["user"]})


def historial_view(request):
    if not request.session.get("user"):
        return redirect("login:login")

    return render(request, "clientes/historial.html", {"user": request.session["user"]})


def perfil_view(request):
    if not request.session.get("user"):
        return redirect("login:login")

    return render(request, "login/perfil.html", {"user": request.session["user"]})
