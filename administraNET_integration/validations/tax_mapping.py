from .base import BaseValidationRule, register_validation_rule
from django.utils.translation import gettext_lazy as _
from inventory.models import Product
from sales.models import Client

@register_validation_rule
class TaxMappingValidationRule(BaseValidationRule):
    code = 'tax_mapping'
    label = _('Validación de mapeos de impuestos')
    description = _('Valida que productos y clientes tengan los impuestos requeridos mapeados.')

    def validate(self, context=None):
        errors = []
        for prod in Product.objects.filter(empresa=self.empresa):
            if not hasattr(prod, 'tax') or not prod.tax or not getattr(prod.tax, 'is_active', True):
                errors.append(_('Producto ID %(id)s sin impuesto válido') % {'id': prod.id})
        for cli in Client.objects.filter(empresa=self.empresa):
            if not hasattr(cli, 'tax') or not cli.tax or not getattr(cli.tax, 'is_active', True):
                errors.append(_('Cliente ID %(id)s sin impuesto válido') % {'id': cli.id})
        return {
            'success': not errors,
            'errors': errors,
            'warnings': [],
            'details': {},
        } 