from django.urls import path, include
from . import views
from .views import views_api
from core.views.cdn_wizard import CDNWizardView
from core.views.views import empresa_crear_view, empresa_editar_view, empresa_listar_view, empresa_eliminar_view, branch_list_view, branch_create_view, branch_edit_view, branch_delete_view, cambiar_empresa_branch
from core.views.views_general import MenuExampleView
from django.views.generic import TemplateView

app_name = 'core'

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('perfil/', views.perfil_view, name='perfil'),
    path('historial/', views.historial_view, name='historial'),

    # API Endpoints
    path('api/users/<int:user_id>/', views_api.UserDetailApiView.as_view(), name='api_user_detail'),
    path('api/permissions/', views_api.PermissionListApiView.as_view(), name='api_permission_list'),
    path('api/roles/', views_api.RoleListCreateApiView.as_view(), name='api_role_list_create'),
    path('api/roles/<int:rol_id>/', views_api.RoleDetailApiView.as_view(), name='api_role_detail'),

    # Usuarios
    path('usuarios/', views.usuarios_admin_view, name='usuarios'),
    path('usuarios/crear/', views.UsuarioCreateView.as_view(), name='crear_usuario'),

    # Permisos
    path('permisos/', views.listar_permisos_view, name='listar_permisos'),
    path('permisos/crear/', views.crear_editar_permiso_view, name='crear_permiso'),
    path('permisos/<int:permiso_id>/editar/', views.crear_editar_permiso_view, name='editar_permiso'),
    path('permisos/<int:permiso_id>/eliminar/', views.eliminar_permiso_view, name='eliminar_permiso'),
    path('permisos/sincronizar/', views.sincronizar_sistema_view, name='sincronizar_sistema'),

    # Roles
    path('roles/', views.listar_roles_view, name='listar_roles'),
    path('roles/crear/', views.crear_editar_rol_view, name='crear_rol'),
    path('roles/<int:rol_id>/editar/', views.crear_editar_rol_view, name='editar_rol'),
    path('roles/<int:rol_id>/eliminar/', views.eliminar_rol_view, name='eliminar_rol'),
    
    # UoM
    path('uom/', views.UoMListView.as_view(), name='uom_list'),
    path('uom/crear/', views.UoMCreateView.as_view(), name='uom_create'),
    path('uom/<int:pk>/editar/', views.UoMUpdateView.as_view(), name='uom_update'),
    path('uom/<int:pk>/eliminar/', views.UoMDeleteView.as_view(), name='uom_delete'),

    # Monedas
    path('monedas/', views.CurrencyListView.as_view(), name='currency_list'),
    path('monedas/crear/', views.CurrencyCreateView.as_view(), name='currency_create'),
    path('monedas/<int:pk>/editar/', views.CurrencyUpdateView.as_view(), name='currency_update'),
    path('monedas/<int:pk>/eliminar/', views.CurrencyDeleteView.as_view(), name='currency_delete'),

    # Tipos de Cambio
    path('tipos-de-cambio/', views.ExchangeRateListView.as_view(), name='exchange_rate_list'),
    path('tipos-de-cambio/crear/', views.ExchangeRateCreateView.as_view(), name='exchange_rate_create'),
    path('tipos-de-cambio/<int:pk>/editar/', views.ExchangeRateUpdateView.as_view(), name='exchange_rate_update'),
    path('tipos-de-cambio/<int:pk>/eliminar/', views.ExchangeRateDeleteView.as_view(), name='exchange_rate_delete'),

    # Configuración del Sistema
    path('configuracion/', views.SystemConfigurationListView.as_view(), name='system_config_list'),
    path('configuracion/crear/', views.SystemConfigurationCreateView.as_view(), name='system_config_create'),
    path('configuracion/<int:pk>/editar/', views.SystemConfigurationUpdateView.as_view(), name='system_config_update'),
    path('configuracion/<int:pk>/eliminar/', views.SystemConfigurationDeleteView.as_view(), name='system_config_delete'),

    # URL de Errores
    path('403/', views.error_403_view, name='error_403'),

    # CDN Wizard
    path('cdn-wizard/', CDNWizardView.as_view(), name='cdn_wizard'),

    # Empresas
    path('empresas/', empresa_listar_view, name='empresa_listar'),
    path('empresas/nueva/', empresa_crear_view, name='empresa_crear'),
    path('empresas/<int:empresa_id>/editar/', empresa_editar_view, name='empresa_editar'),
    path('empresas/<int:empresa_id>/eliminar/', empresa_eliminar_view, name='empresa_eliminar'),
    path('empresas/<int:empresa_id>/sucursales/', branch_list_view, name='branch_list'),
    path('empresas/<int:empresa_id>/sucursales/nueva/', branch_create_view, name='branch_create'),
    path('empresas/<int:empresa_id>/sucursales/<int:branch_id>/editar/', branch_edit_view, name='branch_edit'),
    path('empresas/<int:empresa_id>/sucursales/<int:branch_id>/eliminar/', branch_delete_view, name='branch_delete'),
    path('cambiar-empresa-branch/', cambiar_empresa_branch, name='cambiar_empresa_branch'),
    
    # Ejemplo de Nueva Arquitectura de Menús
    path('menu-example/', MenuExampleView.as_view(), name='menu_example'),
    
    # Nuevo Dashboard con Arquitectura de Apps
    path('dashboard-apps/', TemplateView.as_view(template_name='dashboard_apps.html'), name='dashboard_apps'),
]


