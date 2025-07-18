from .base import BaseValidationRule, register_validation_rule
from django.utils.translation import gettext_lazy as _
from sales.models import Client
import re

@register_validation_rule
class UniqueEmailCustomerValidationRule(BaseValidationRule):
    code = 'unique_email_customer'
    label = _('Clientes con email válido y único')
    description = _('Valida que los emails de los clientes sean válidos y no estén duplicados.')

    def validate(self, context=None):
        errors = []
        seen = set()
        for c in Client.objects.filter(empresa=self.empresa):
            email = c.email
            if not email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                errors.append(_('Cliente %(id)s sin email válido') % {'id': c.id})
            elif email in seen:
                errors.append(_('Email duplicado: %(email)s') % {'email': email})
            else:
                seen.add(email)
        return {
            'success': not errors,
            'errors': errors,
            'warnings': [],
            'details': {},
        } 