from decimal import Decimal
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from core.models import SystemConfiguration, ExchangeRate, Currency

def get_base_currency():
    try:
        config = SystemConfiguration.objects.first()
        if not config or not config.base_currency:
            raise Exception(_("No base currency defined for the system."))
        return config.base_currency
    except ObjectDoesNotExist:
        raise Exception(_("No system configuration defined."))

def convert_currency(amount, from_currency, to_currency, date=None):
    """
    Convierte un monto entre dos monedas, usando la cotización vigente en una fecha.
    Si ambas monedas son iguales, retorna el monto original.
    """
    if not amount:
        return Decimal('0.00')

    if from_currency == to_currency:
        return amount

    date = date or timezone.now().date()

    try:
        rate = ExchangeRate.objects.get(
            from_currency=from_currency,
            to_currency=to_currency,
            date=date
        ).rate
        return amount * rate
    except ExchangeRate.DoesNotExist:
        raise Exception(_("No exchange rate found from %(from_code)s to %(to_code)s for date %(date)s.") % {'from_code': from_currency.code, 'to_code': to_currency.code, 'date': date})

def convert_to_base(amount, currency, date=None):
    base_currency = get_base_currency()
    return convert_currency(amount, currency, base_currency, date=date)

def convert_from_base(amount, currency, date=None):
    base_currency = get_base_currency()
    return convert_currency(amount, base_currency, currency, date=date)