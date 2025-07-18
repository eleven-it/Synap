from .base import BaseValidationRule, register_validation_rule
from django.utils.translation import gettext_lazy as _
from inventory.models import Product

@register_validation_rule
class NonNegativeStockValidationRule(BaseValidationRule):
    code = 'non_negative_stock'
    label = _('Stock no negativo en productos')
    description = _('Valida que ningún producto tenga stock negativo.')

    def validate(self, context=None):
        errors = []
        for prod in Product.objects.filter(empresa=self.empresa):
            if prod.stock is not None and prod.stock < 0:
                errors.append(_('Producto ID %(id)s con stock negativo') % {'id': prod.id})
        return {
            'success': not errors,
            'errors': errors,
            'warnings': [],
            'details': {},
        } 