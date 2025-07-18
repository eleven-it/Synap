from .base import BaseValidationRule, register_validation_rule
from django.utils.translation import gettext_lazy as _
from inventory.models import Product

@register_validation_rule
class PositivePriceValidationRule(BaseValidationRule):
    code = 'positive_price'
    label = _('Precios positivos en productos')
    description = _('Valida que todos los productos tengan precios mayores a cero.')

    def validate(self, context=None):
        errors = []
        for prod in Product.objects.filter(empresa=self.empresa):
            if prod.price is None or prod.price <= 0:
                errors.append(_('Producto ID %(id)s con precio no válido') % {'id': prod.id})
        return {
            'success': not errors,
            'errors': errors,
            'warnings': [],
            'details': {},
        } 