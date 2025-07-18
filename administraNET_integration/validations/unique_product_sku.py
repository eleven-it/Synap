from .base import BaseValidationRule, register_validation_rule
from django.utils.translation import gettext_lazy as _
from inventory.models import Product
from django.db import models

@register_validation_rule
class UniqueProductSKUValidationRule(BaseValidationRule):
    code = 'unique_product_sku'
    label = _('Unicidad de SKU de productos')
    description = _('Valida que no existan productos duplicados por SKU en la empresa.')

    def validate(self, context=None):
        # Buscar productos duplicados por SKU para la empresa
        duplicates = (
            Product.objects.filter(empresa=self.empresa)
            .values('sku')
            .annotate(count=models.Count('id'))
            .filter(count__gt=1)
        )
        errors = []
        for dup in duplicates:
            errors.append(_('SKU duplicado: %(sku)s (%(count)d productos)') % {'sku': dup['sku'], 'count': dup['count']})
        return {
            'success': not errors,
            'errors': errors,
            'warnings': [],
            'details': {'duplicates': list(duplicates)},
        } 