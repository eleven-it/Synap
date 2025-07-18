from .base import BaseValidationRule, register_validation_rule
from django.utils.translation import gettext_lazy as _
from inventory.models import Product
from django.db import models

@register_validation_rule
class RequiredFieldsProductValidationRule(BaseValidationRule):
    code = 'required_fields_product'
    label = _('Campos obligatorios en productos')
    description = _('Valida que todos los productos tengan nombre, SKU y precio.')

    def validate(self, context=None):
        missing = Product.objects.filter(empresa=self.empresa).filter(
            models.Q(name__isnull=True) | models.Q(name='') |
            models.Q(sku__isnull=True) | models.Q(sku='') |
            models.Q(price__isnull=True) | models.Q(price__lte=0)
        )
        errors = []
        for prod in missing:
            errors.append(_('Producto ID %(id)s con datos incompletos (nombre, SKU o precio)') % {'id': prod.id})
        return {
            'success': not errors,
            'errors': errors,
            'warnings': [],
            'details': {'missing': list(missing.values('id','name','sku','price'))},
        } 