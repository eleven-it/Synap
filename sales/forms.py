from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import json
from .models import (
    Client, VATValidator, SalesOrder, SalesOrderLine, PriceList, PriceListItem,
    PaymentTerm, PaymentTermLine, Invoice, InvoiceLine, Payment,
    DeliveryOrder, DeliveryOrderLine, ReturnDelivery, CreditNote, ApprovalLog,
    POSSession, POSTerminal, POSSale, POSPayment, POSPromotion,
    PaymentMethod, PaymentProcessor
)


class ClientForm(forms.ModelForm):
    """Formulario para crear/editar clientes"""
    
    class Meta:
        model = Client
        fields = [
            'name', 'code', 'tax_id', 'address', 'city', 'state', 'postal_code', 'country',
            'contact_person', 'email', 'phone', 'mobile', 'website', 'notes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter client name...')
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter client code...')
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter Tax ID...')
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Enter full address...')
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter city name...')
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter state/province...')
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('12345')
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter country...')
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter contact person...')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': _('client@example.com')
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('+1 234 567 8900')
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('+1 234 567 8900')
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': _('https://www.example.com')
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Enter notes...')
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que tenga al menos un método de contacto
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        mobile = cleaned_data.get('mobile')
        
        if not email and not phone and not mobile:
            raise ValidationError(
                _('Client must have at least one contact method (email, phone, or mobile).')
            )
        
        return cleaned_data


class ClientSearchForm(forms.Form):
    """Formulario de búsqueda para clientes"""
    
    search = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Search by name, email, tax_id...')
        }),
        label=_('Search')
    )
    
    type = forms.ChoiceField(
        choices=[
            ('', _('All types')),
            ('individual', _('Individual')),
            ('company', _('Company')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Type')
    )
    
    is_customer = forms.ChoiceField(
        choices=[
            ('', _('All')),
            ('True', _('Customers only')),
            ('False', _('Non-customers only'))
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Customer')
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', _('All')),
            ('True', _('Active only')),
            ('False', _('Inactive only'))
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Status')
    )


class PaymentMethodForm(forms.ModelForm):
    """Formulario para medios de pago"""
    
    class Meta:
        model = PaymentMethod
        fields = [
            'name', 'code', 'description', 'payment_type', 'card_type',
            'icon', 'color', 'logo_url', 'is_active', 'is_default', 'order',
            'branches', 'commission_percentage', 'fixed_commission',
            'minimum_amount', 'maximum_amount', 'requires_reference',
            'requires_card_number', 'requires_expiry', 'requires_cvv',
            'requires_installments', 'max_installments', 'processing_time_hours',
            'supports_refunds', 'supports_partial_refunds', 'processor_name',
            'processor_config', 'requires_3d_secure', 'supports_tokenization',
            'supported_currencies', 'supported_countries'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'code': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 3}),
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'card_type': forms.Select(attrs={'class': 'form-select'}),
            'icon': forms.TextInput(attrs={'class': 'form-input'}),
            'color': forms.TextInput(attrs={'class': 'form-input', 'type': 'color'}),
            'logo_url': forms.URLInput(attrs={'class': 'form-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'order': forms.NumberInput(attrs={'class': 'form-input'}),
            'branches': forms.SelectMultiple(attrs={'class': 'form-select'}),
            'commission_percentage': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'fixed_commission': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'minimum_amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'maximum_amount': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'requires_reference': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'requires_card_number': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'requires_expiry': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'requires_cvv': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'requires_installments': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'max_installments': forms.NumberInput(attrs={'class': 'form-input'}),
            'processing_time_hours': forms.NumberInput(attrs={'class': 'form-input'}),
            'supports_refunds': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supports_partial_refunds': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'processor_name': forms.TextInput(attrs={'class': 'form-input'}),
            'processor_config': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'requires_3d_secure': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supports_tokenization': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supported_currencies': forms.TextInput(attrs={'class': 'form-input'}),
            'supported_countries': forms.TextInput(attrs={'class': 'form-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar campos según el tipo de pago
        if 'payment_type' in self.data:
            self._configure_fields_for_payment_type(self.data['payment_type'])
        elif self.instance and self.instance.pk:
            self._configure_fields_for_payment_type(self.instance.payment_type)
    
    def _configure_fields_for_payment_type(self, payment_type):
        """Configurar campos según el tipo de pago"""
        if payment_type == 'card':
            self.fields['card_type'].required = True
            self.fields['requires_card_number'].initial = True
            self.fields['requires_expiry'].initial = True
            self.fields['requires_cvv'].initial = True
        else:
            self.fields['card_type'].required = False
    
    def clean_code(self):
        """Validar código único por empresa"""
        code = self.cleaned_data.get('code')
        empresa = self.cleaned_data.get('empresa')
        
        if code and empresa:
            existing = PaymentMethod.objects.filter(
                empresa=empresa,
                code=code
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise ValidationError(_('A payment method with this code already exists for this company.'))
        
        return code
    
    def clean_supported_currencies(self):
        """Validar formato de monedas soportadas"""
        currencies = self.cleaned_data.get('supported_currencies')
        if currencies:
            try:
                if isinstance(currencies, str):
                    currencies = json.loads(currencies)
                if not isinstance(currencies, list):
                    raise ValueError
                # Validar que sean códigos de moneda válidos (3 letras)
                for currency in currencies:
                    if not isinstance(currency, str) or len(currency) != 3:
                        raise ValueError
            except (ValueError, json.JSONDecodeError):
                raise ValidationError(_('Supported currencies must be a valid JSON array of 3-letter currency codes.'))
        
        return currencies
    
    def clean_supported_countries(self):
        """Validar formato de países soportados"""
        countries = self.cleaned_data.get('supported_countries')
        if countries:
            try:
                if isinstance(countries, str):
                    countries = json.loads(countries)
                if not isinstance(countries, list):
                    raise ValueError
                # Validar que sean códigos de país válidos (2 letras)
                for country in countries:
                    if not isinstance(country, str) or len(country) != 2:
                        raise ValueError
            except (ValueError, json.JSONDecodeError):
                raise ValidationError(_('Supported countries must be a valid JSON array of 2-letter country codes.'))
        
        return countries
    
    def clean_processor_config(self):
        """Validar configuración del procesador"""
        config = self.cleaned_data.get('processor_config')
        if config:
            try:
                if isinstance(config, str):
                    config = json.loads(config)
                if not isinstance(config, dict):
                    raise ValueError
            except (ValueError, json.JSONDecodeError):
                raise ValidationError(_('Processor configuration must be a valid JSON object.'))
        
        return config


class PaymentProcessorForm(forms.ModelForm):
    """Formulario para procesadores de pago"""
    
    class Meta:
        model = PaymentProcessor
        fields = [
            'name', 'processor_type', 'is_active', 'api_key', 'api_secret',
            'webhook_url', 'webhook_secret', 'config'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'processor_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'api_key': forms.TextInput(attrs={'class': 'form-input'}),
            'api_secret': forms.PasswordInput(attrs={'class': 'form-input'}),
            'webhook_url': forms.URLInput(attrs={'class': 'form-input'}),
            'webhook_secret': forms.PasswordInput(attrs={'class': 'form-input'}),
            'config': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
        }
    
    def clean_config(self):
        """Validar configuración JSON"""
        config = self.cleaned_data.get('config')
        if config:
            try:
                if isinstance(config, str):
                    config = json.loads(config)
                if not isinstance(config, dict):
                    raise ValueError
            except (ValueError, json.JSONDecodeError):
                raise ValidationError(_('Configuration must be a valid JSON object.'))
        
        return config
    
    def clean(self):
        """Validaciones adicionales"""
        cleaned_data = super().clean()
        
        # Validar que tenga credenciales si está activo
        if cleaned_data.get('is_active'):
            processor_type = cleaned_data.get('processor_type')
            api_key = cleaned_data.get('api_key')
            api_secret = cleaned_data.get('api_secret')
            
            if processor_type in ['stripe', 'paypal', 'mercadopago']:
                if not api_key or not api_secret:
                    raise ValidationError(
                        _('API Key and API Secret are required for this processor type.')
                    )
        
        return cleaned_data 