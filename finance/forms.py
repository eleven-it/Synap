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

class SqlChatForm(forms.Form):
    """
    Formulario para consultas SQL de IA en lenguaje natural.
    """
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'placeholder': 'Ej: "Muéstrame las ventas del último mes" o "¿Cuáles son mis compras más altas?"'
        }),
        label="Consulta",
        help_text="Describe lo que quieres saber sobre tus datos financieros"
    )
    
    year = forms.IntegerField(
        required=False,
        min_value=1990,
        max_value=2100,
        label="Año",
        help_text="Filtrar por año específico (opcional)"
    )
    
    currency = forms.ChoiceField(
        required=False,
        choices=[
            ('', '(todas las monedas)'),
            ('ARS', 'ARS'),
            ('USD', 'USD'),
            ('EUR', 'EUR')
        ],
        label="Moneda",
        help_text="Filtrar por moneda específica (opcional)"
    )
    
    date_from = forms.DateField(
        required=False,
        label="Desde",
        help_text="Fecha de inicio (opcional)",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        label="Hasta",
        help_text="Fecha de fin (opcional)",
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from > date_to:
            raise forms.ValidationError("La fecha 'Desde' debe ser anterior o igual a la fecha 'Hasta'.")
        
        return cleaned_data 