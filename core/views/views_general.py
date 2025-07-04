from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.models import UsuarioExtendido
from core.utils import permisos_contextuales
from core.decorators import tiene_permiso
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

@login_required
def dashboard_view(request):
    usuario = request.user
    if not isinstance(usuario, UsuarioExtendido):
        return redirect("login:login")

    print("🧠 Usuario:", usuario.email)
    print("🧠 UID:", usuario.uid)
    print("🧠 ROLES:", [r.nombre for r in usuario.roles.all()])

    context = permisos_contextuales(request, "*", debug=True)
    return render(request, "core/dashboard.html", context)

@tiene_permiso("usuarios.perfil")
def perfil_view(request):
    """Vista para que el usuario edite su perfil."""
    return render(request, "core/perfil.html")

@tiene_permiso("usuarios.historial")
def historial_view(request):
    """Vista para ver el historial de actividad."""
    return render(request, "core/historial.html")

class MenuExampleView(LoginRequiredMixin, TemplateView):
    """Vista de ejemplo para mostrar la nueva arquitectura de menús."""
    template_name = 'core/menu_example.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # El context processor ya proporciona apps_menu y demás variables
        return context
