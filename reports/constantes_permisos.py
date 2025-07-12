from django.utils.translation import gettext_lazy as _

# Permisos de reportes
REPORTS_PERMISSIONS = {
    'reports.ver': _('View reports'),
    'reports.crear': _('Create reports'),
    'reports.editar': _('Edit reports'),
    'reports.eliminar': _('Delete reports'),
    'reports.exportar': _('Export reports'),
    'reports.programar': _('Schedule reports'),
    'reports.templates': _('Manage templates'),
    'reports.ia': _('Use AI features'),
    'reports.dashboard': _('Access reports dashboard'),
}

# Permisos específicos por tipo de reporte
REPORT_TYPE_PERMISSIONS = {
    'sales': 'sales.ver',
    'inventory': 'inventory.ver',
    'purchases': 'purchases.ver',
    'accounting': 'accounting.ver',
    'general': 'reports.ver',
}

# Permisos para componentes específicos
COMPONENT_PERMISSIONS = {
    'chart': 'reports.ver',
    'table': 'reports.ver',
    'kpi': 'reports.ver',
    'text': 'reports.ver',
    'image': 'reports.ver',
    'header': 'reports.ver',
    'footer': 'reports.ver',
} 