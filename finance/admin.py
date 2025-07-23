from django.contrib import admin
from .models import AccountReceivable, CreditLimitLog, FinancialReport

admin.site.register(AccountReceivable)
admin.site.register(CreditLimitLog)
admin.site.register(FinancialReport) 