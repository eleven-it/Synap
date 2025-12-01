from django.shortcuts import render, redirect
from core.models import UsuarioExtendido
from core.utils import permisos_contextuales
from core.decorators import tiene_permiso, administranet_login_required
from django.views.generic import TemplateView

@administranet_login_required
def dashboard_view(request):
    """
    Vista del dashboard principal
    Usa sesión personalizada de administraNET en lugar de Django auth
    """
    # Verificar que existe sesión de usuario
    session_user = request.session.get("user")
    if not session_user:
        return redirect("login:login")
    
    # Obtener usuario extendido si existe, sino usar datos de sesión
    try:
        usuario = request.user
        if isinstance(usuario, UsuarioExtendido):
            print("🧠 Usuario:", usuario.email if hasattr(usuario, 'email') else session_user.get('cod_usuario'))
            print("🧠 UID:", usuario.uid if hasattr(usuario, 'uid') else session_user.get('id_usuario'))
            if hasattr(usuario, 'roles'):
                print("🧠 ROLES:", [r.nombre for r in usuario.roles.all()])
    except Exception as e:
        # Si no hay usuario extendido, usar datos de sesión directamente
        print(f"⚠️ Usuario extendido no disponible: {e}")
    
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

class MenuExampleView(TemplateView):
    """Vista de ejemplo para mostrar la nueva arquitectura de menús."""
    template_name = 'core/menu_example.html'
    
    def dispatch(self, request, *args, **kwargs):
        # Verificar sesión personalizada
        if "user" not in request.session:
            return redirect("login:login")
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # El context processor ya proporciona apps_menu y demás variables
        return context
