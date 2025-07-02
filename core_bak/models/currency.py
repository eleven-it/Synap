from django.db import models
from django.utils.translation import gettext_lazy as _

class Currency(models.Model):
    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    symbol = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = _("Currency")
        verbose_name_plural = _("Currencies")


class ExchangeRate(models.Model):
    from_currency = models.ForeignKey(Currency, related_name='from_rates', on_delete=models.CASCADE)
    to_currency = models.ForeignKey(Currency, related_name='to_rates', on_delete=models.CASCADE)
    rate = models.DecimalField(max_digits=18, decimal_places=6)
    date = models.DateField()

    class Meta:
        unique_together = ('from_currency', 'to_currency', 'date')
        verbose_name = _("Exchange Rate")
        verbose_name_plural = _("Exchange Rates")

    def __str__(self):
        return f"{self.from_currency.code} > {self.to_currency.code} = {self.rate} ({self.date})"
