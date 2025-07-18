from .base import BaseValidationRule, register_validation_rule
from django.utils.translation import gettext_lazy as _
from core.models import Branch
from administraNET_integration.models import TableMapping

@register_validation_rule
class BranchMappingValidationRule(BaseValidationRule):
    code = 'branch_mapping'
    label = _('Sucursales activas y correctamente mapeadas')
    description = _('Valida que todas las sucursales estén mapeadas y activas.')

    def validate(self, context=None):
        errors = []
        branches = Branch.objects.filter(empresa=self.empresa, is_active=True)
        for branch in branches:
            if not TableMapping.objects.filter(mapping_type='BRANCHES', synap_model_id=branch.id, is_active=True, empresa=self.empresa).exists():
                errors.append(_('Sucursal %(id)s no está correctamente mapeada') % {'id': branch.id})
        return {
            'success': not errors,
            'errors': errors,
            'warnings': [],
            'details': {},
        } 