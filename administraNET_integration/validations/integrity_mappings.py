from .base import BaseValidationRule, register_validation_rule
from django.utils.translation import gettext_lazy as _
from administraNET_integration.models import TableMapping

@register_validation_rule
class IntegrityMappingsValidationRule(BaseValidationRule):
    code = 'integrity_mappings'
    label = _('Integridad de mapeos de tablas')
    description = _('Valida que todos los mapeos de tablas requeridos estén configurados y activos.')

    def validate(self, context=None):
        required_types = ['PRODUCTS', 'CUSTOMERS', 'BRANCHES']
        errors = []
        for t in required_types:
            if not TableMapping.objects.filter(mapping_type=t, is_active=True, empresa=self.empresa).exists():
                errors.append(_('Falta el mapeo activo para %(tipo)s') % {'tipo': t})
        return {
            'success': not errors,
            'errors': errors,
            'warnings': [],
            'details': {},
        } 