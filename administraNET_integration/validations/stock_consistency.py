from .base import BaseValidationRule, register_validation_rule
from django.utils.translation import gettext_lazy as _
from inventory.models import StockQuant

@register_validation_rule
def StockConsistencyValidationRule(BaseValidationRule):
    code = 'stock_consistency'
    label = _('Consistencia de stock')
    description = _('Valida que no existan productos con stock negativo para la empresa.')

    def validate(self, context=None):
        errors = []
        negativos = StockQuant.objects.filter(empresa=self.empresa, quantity__lt=0)
        if negativos.exists():
            for sq in negativos:
                errors.append(_('Stock negativo: %(sku)s en %(ubicacion)s (cantidad: %(cantidad)s)') % {
                    'sku': sq.product.sku,
                    'ubicacion': sq.location.name,
                    'cantidad': sq.quantity
                })
        return {
            'success': not errors,
            'errors': errors,
            'warnings': [],
            'details': {'negativos': list(negativos.values('product__sku', 'location__name', 'quantity'))},
        } 