"""
Sistema de permisos para Reports AI
Siguiendo la lógica de core para consistencia
"""
from django.utils.translation import gettext_lazy as _


# Permisos del módulo siguiendo el patrón de core
REPORTS_AI_PERMISSIONS = {
    'view_reports': {
        'name': _('Ver Reportes AI'),
        'description': _('Permite visualizar reportes generados por AI'),
    },
    'generate_reports': {
        'name': _('Generar Reportes AI'),
        'description': _('Permite solicitar la generación de nuevos reportes'),
    },
    'configure_reports_ai': {
        'name': _('Configurar Reportes AI'),
        'description': _('Permite configurar agentes, reglas y parámetros del sistema'),
    },
    'view_agent_metrics': {
        'name': _('Ver Métricas de Agentes'),
        'description': _('Permite visualizar estadísticas y métricas de los agentes AI'),
    },
    'manage_business_rules': {
        'name': _('Gestionar Reglas de Negocio'),
        'description': _('Permite crear, editar y eliminar reglas de negocio'),
    },
    'access_webhooks': {
        'name': _('Acceder a Webhooks'),
        'description': _('Permite invocar reportes vía webhooks externos'),
    },
}


def get_all_permissions():
    """
    Retorna todos los permisos del módulo
    Compatible con el sistema de permisos de core
    """
    return REPORTS_AI_PERMISSIONS

