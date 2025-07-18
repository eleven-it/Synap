"""
Context processors para la integración AdministraNET
"""

from django.utils.translation import gettext as _
from core.models import UsuarioExtendido


def administraNET_integration_menu(request):
    """
    Context processor que procesa el menú de integración AdministraNET
    y reemplaza dinámicamente {empresa_id} por el ID real de la empresa activa.
    """
    user = getattr(request, 'user', None)
    empresa_activa = None
    
    # Obtener empresa activa del usuario
    if user and hasattr(user, 'is_authenticated') and user.is_authenticated:
        if hasattr(user, 'empresa_activa') and user.empresa_activa:
            empresa_activa = user.empresa_activa
        else:
            # Fallback: obtener desde la sesión
            empresa_id = request.session.get('empresa_activa_id')
            if empresa_id:
                try:
                    empresa_activa = user.empresa_activa.__class__.objects.get(id=empresa_id, activa=True)
                except:
                    pass
    
    # Configuración del menú con URLs que requieren empresa_id
    menu_config = [
        {
            'seccion': _('PANEL PRINCIPAL'),
            'items': [
                {
                    'label': _('Panel Principal'),
                    'url': '/administraNET_integration/',
                    'icon': 'dashboard',
                },
                {
                    'label': _('Status'),
                    'url': '/administraNET_integration/status/',
                    'icon': 'monitor_heart',
                },
            ]
        },
        {
            'seccion': _('CONFIGURACIÓN'),
            'items': [
                {
                    'label': _('Connection Settings'),
                    'url': '/administraNET_integration/connection/',
                    'icon': 'settings',
                },
                {
                    'label': _('Mapeos'),
                    'url': '/administraNET_integration/mappings/',
                    'icon': 'link',
                },
                {
                    'label': _('Sync Settings'),
                    'url': '/administraNET_integration/sync-settings/',
                    'icon': 'sync',
                },
            ]
        },
        {
            'seccion': _('SYNCHRONIZATION'),
            'items': [
                {
                    'label': _('Manual Sync'),
                    'url': '/administraNET_integration/manual-sync/',
                    'icon': 'play_arrow',
                },
                {
                    'label': _('Sync History'),
                    'url': '/administraNET_integration/sync-history/',
                    'icon': 'history',
                },
                {
                    'label': _('Data Validation'),
                    'url': '/administraNET_integration/validation/',
                    'icon': 'verified',
                },
            ]
        },
        {
            'seccion': _('MONITORING'),
            'items': [
                {
                    'label': _('Logs'),
                    'url': '/administraNET_integration/sync-history/',
                    'icon': 'article',
                },
                {
                    'label': _('Error Reports'),
                    'url': '/administraNET_integration/sync-history/',
                    'icon': 'error',
                },
                {
                    'label': _('Performance'),
                    'url': '/administraNET_integration/status/',
                    'icon': 'speed',
                },
            ]
        }
    ]
    
    # Procesar URLs que requieren empresa_id
    if empresa_activa:
        # Agregar ítems que requieren empresa_id solo si hay empresa activa
        menu_config[1]['items'].append({
            'label': _('Validation Settings'),
            'url': f'/administraNET_integration/validation-settings/{empresa_activa.id}/',
            'icon': 'rule',
        })
        menu_config[2]['items'].append({
            'label': _('Validation History'),
            'url': f'/administraNET_integration/validation-history/',
            'icon': 'fact_check',
        })
    
    return {
        'administraNET_integration_menu': menu_config,
        'empresa_activa': empresa_activa,
    } 