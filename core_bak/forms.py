from django import forms
from .models import UsuarioExtendido, Rol, Permiso, UnitOfMeasure, Currency, ExchangeRate, SystemConfiguration
from django.core.exceptions import ValidationError

class UoMForm(forms.ModelForm):
    class Meta:
        model = UnitOfMeasure
        fields = ['name', 'code', 'category', 'ratio', 'is_reference', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        text_input_classes = 'mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md'
        checkbox_classes = 'h-4 w-4 text-purple-600 border-gray-300 rounded'
        
        self.fields['name'].widget.attrs.update({'class': text_input_classes})
        self.fields['code'].widget.attrs.update({'class': text_input_classes})
        self.fields['category'].widget.attrs.update({'class': text_input_classes})
        self.fields['ratio'].widget.attrs.update({'class': text_input_classes})
        self.fields['is_reference'].widget.attrs.update({'class': checkbox_classes})
        self.fields['is_active'].widget.attrs.update({'class': checkbox_classes})

class CurrencyForm(forms.ModelForm):
    class Meta:
        model = Currency
        fields = ['code', 'name', 'symbol', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_input_classes = 'mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md'
        checkbox_classes = 'h-4 w-4 text-purple-600 border-gray-300 rounded'
        
        self.fields['code'].widget.attrs.update({'class': text_input_classes})
        self.fields['name'].widget.attrs.update({'class': text_input_classes})
        self.fields['symbol'].widget.attrs.update({'class': text_input_classes})
        self.fields['is_active'].widget.attrs.update({'class': checkbox_classes})

class ExchangeRateForm(forms.ModelForm):
    class Meta:
        model = ExchangeRate
        fields = ['from_currency', 'to_currency', 'rate', 'date']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_input_classes = 'mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md'
        
        self.fields['from_currency'].widget.attrs.update({'class': text_input_classes})
        self.fields['to_currency'].widget.attrs.update({'class': text_input_classes})
        self.fields['rate'].widget.attrs.update({'class': text_input_classes})
        self.fields['date'].widget.attrs.update({'class': text_input_classes})

class SystemConfigurationForm(forms.ModelForm):
    class Meta:
        model = SystemConfiguration
        fields = ['key', 'value', 'description', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        text_input_classes = 'mt-1 block w-full px-3 py-2 bg-white border border-gray-300 rounded-md'
        checkbox_classes = 'h-4 w-4 text-purple-600 border-gray-300 rounded'
        
        self.fields['key'].widget.attrs.update({'class': text_input_classes + ' font-mono'})
        self.fields['value'].widget.attrs.update({'class': text_input_classes})
        self.fields['description'].widget.attrs.update({'class': text_input_classes})
        self.fields['is_active'].widget.attrs.update({'class': checkbox_classes})

class UsuarioCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True)

    class Meta:
        model = UsuarioExtendido
        fields = ['email', 'nombre', 'password']

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 6:
            raise ValidationError("La contraseña debe tener al menos 6 caracteres.", code='password_too_short')
        return password 