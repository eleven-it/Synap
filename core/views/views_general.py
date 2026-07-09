from typing import Any, Dict, List

from django.shortcuts import render, redirect
from core.models import UsuarioExtendido
from core.utils import permisos_contextuales
from core.decorators import tiene_permiso, administranet_login_required
from django.views.generic import TemplateView


def get_dashboard_home_visibility(user, apps_menu: List[Dict[str, Any]]) -> Dict[str, bool]:
    """
    Tarjetas del inicio (/core/dashboard/) alineadas con permisos reales de Reports.
    Command Center: reports.view_managerial + ReportDefinition.is_visible (o usuario supervisor).
    Catálogo/workspace: app Reports visible en menú.
    """
    from reports.services.report_visibility import command_center_visible_for_user

    show_reports = any(app.get("id") == "reports" for app in apps_menu)
    empresa = getattr(user, "empresa_activa", None)
    empresa_id = empresa.id if empresa else None
    return {
        "show_command_center": command_center_visible_for_user(user, empresa_id=empresa_id),
        "show_reports": show_reports,
        "show_workspace": show_reports,
    }


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

    # Landing por rol: el operario "puro" (mpr.parte_operario sin mpr.ver) va
    # directo a su carga móvil, sin acceso al dashboard general.
    try:
        from mpr.landing import landing_url_para_usuario
        landing = landing_url_para_usuario(request.user)
        if landing:
            return redirect(landing)
    except Exception:
        pass

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
    
    # Obtener apps visibles para el usuario (ya filtradas por permisos)
    from core.utils import apps_visibles_para_usuario
    apps_menu = apps_visibles_para_usuario(request.user, request)
    
    context = permisos_contextuales(request, "*", debug=True)
    context["apps_menu"] = apps_menu
    context.update(get_dashboard_home_visibility(request.user, apps_menu))
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
