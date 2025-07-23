from django import forms
from .models import AccountReceivable, CreditLimitLog, FinancialReport

class AccountReceivableForm(forms.ModelForm):
    class Meta:
        model = AccountReceivable
        fields = '__all__'

class CreditLimitLogForm(forms.ModelForm):
    class Meta:
        model = CreditLimitLog
        fields = '__all__'

class FinancialReportForm(forms.ModelForm):
    class Meta:
        model = FinancialReport
        fields = '__all__' 