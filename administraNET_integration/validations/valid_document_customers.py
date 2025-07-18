from .base import BaseValidationRule, register_validation_rule
from django.utils.translation import gettext_lazy as _
from sales.models import Client
from django.db import models
import re

@register_validation_rule
class ValidDocumentCustomerValidationRule(BaseValidationRule):
    code = 'valid_document_customer'
    label = _('Clientes con documento válido y único')
    description = _('Valida que los clientes tengan CUIT/CUIL/DNI válido y no duplicado.')

    def validate(self, context=None):
        errors = []
        seen = set()
        for c in Client.objects.filter(empresa=self.empresa):
            doc = c.document_number
            if not doc or not re.match(r'^[0-9]{7,11}$', doc):
                errors.append(_('Cliente %(id)s sin documento válido') % {'id': c.id})
            elif doc in seen:
                errors.append(_('Documento duplicado: %(doc)s') % {'doc': doc})
            else:
                seen.add(doc)
        return {
            'success': not errors,
            'errors': errors,
            'warnings': [],
            'details': {},
        } 