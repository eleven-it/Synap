from .views_auth import *
from .views_errores import *
from .views_general import dashboard_view, perfil_view, historial_view
from .views_permisos import (
    listar_permisos_view, 
    crear_editar_permiso_view, 
    eliminar_permiso_view,
    toggle_valor_permiso_view
)
from .views_roles import listar_roles_view, crear_editar_rol_view, eliminar_rol_view
from .views_usuarios import usuarios_admin_view, crear_usuario_view, editar_usuario_view, eliminar_usuario_view, validar_integridad_usuarios_view
from .views_permisos_sistema import (
    listar_puestos_permisos_view,
    editar_permisos_puesto_view,
    toggle_navbar_menu_global_view,
    toggle_navbar_granular_view,
)
from .views_uom import UoMListView, UoMCreateView, UoMUpdateView, UoMDeleteView
from .views_currency import (
    CurrencyListView, CurrencyCreateView, CurrencyUpdateView, CurrencyDeleteView,
    ExchangeRateListView, ExchangeRateCreateView, ExchangeRateUpdateView, ExchangeRateDeleteView
)
from .views_system_config import (
    SystemConfigurationListView, SystemConfigurationCreateView, 
    SystemConfigurationUpdateView, SystemConfigurationDeleteView
)
from .views_contacts import (
    ContactListView, ContactCreateView, ContactUpdateView, 
    ContactDetailView, ContactDeleteView, ContactRelationshipListView,
    ContactableCreateView, ContactableUpdateView
)
from . import hook_admin
