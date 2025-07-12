from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
import json

from .models import CloverDevice, CloverConfiguration


class CloverDeviceForm(forms.ModelForm):
    """Formulario para dispositivos Clover"""
    
    class Meta:
        model = CloverDevice
        fields = [
            'device_id', 'serial_number', 'device_type', 'merchant_id', 'api_token',
            'app_id', 'status', 'is_active', 'is_default', 'supports_contactless',
            'supports_chip', 'supports_magnetic_stripe', 'supports_manual_entry',
            'supports_receipt_printing', 'supports_signature_capture', 'notes'
        ]
        widgets = {
            'device_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter device ID...')
            }),
            'serial_number': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter serial number...')
            }),
            'device_type': forms.Select(attrs={'class': 'form-select'}),
            'merchant_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter merchant ID...')
            }),
            'api_token': forms.TextInput(attrs={
                'class': 'form-input',
                'type': 'password',
                'placeholder': _('Enter API token...')
            }),
            'app_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter app ID...')
            }),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supports_contactless': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supports_chip': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supports_magnetic_stripe': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supports_manual_entry': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supports_receipt_printing': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supports_signature_capture': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Enter notes...')
            }),
        }
    
    def clean_device_id(self):
        """Validar que el device_id sea único por empresa"""
        device_id = self.cleaned_data.get('device_id')
        empresa = getattr(self.instance, 'empresa', None)
        
        if device_id and empresa:
            existing = CloverDevice.objects.filter(
                empresa=empresa,
                device_id=device_id
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing.exists():
                raise ValidationError(_('A device with this ID already exists for this company.'))
        
        return device_id
    
    def clean_api_token(self):
        """Validar formato del API token"""
        api_token = self.cleaned_data.get('api_token')
        
        if api_token and len(api_token) < 10:
            raise ValidationError(_('API token must be at least 10 characters long.'))
        
        return api_token


class CloverConfigurationForm(forms.ModelForm):
    """Formulario para configuración de Clover"""
    
    class Meta:
        model = CloverConfiguration
        fields = [
            'api_base_url', 'api_version', 'default_currency', 'supported_currencies',
            'webhook_secret', 'webhook_url', 'send_email_notifications',
            'notification_email'
        ]
        widgets = {
            'api_base_url': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://api.clover.com'
            }),
            'api_version': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'v3'
            }),
            'default_currency': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'ARS'
            }),
            'supported_currencies': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': '["ARS", "USD", "EUR"]'
            }),
            'webhook_secret': forms.TextInput(attrs={
                'class': 'form-input',
                'type': 'password',
                'placeholder': _('Enter webhook secret...')
            }),
            'webhook_url': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': 'https://yourdomain.com/clover/webhook/'
            }),
            'send_email_notifications': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'notification_email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': 'notifications@yourcompany.com'
            }),
        }
    
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
    
    def clean_webhook_url(self):
        """Validar URL del webhook"""
        webhook_url = self.cleaned_data.get('webhook_url')
        
        if webhook_url and not webhook_url.startswith('https://'):
            raise ValidationError(_('Webhook URL must use HTTPS for security.'))
        
        return webhook_url
    
    def clean_notification_email(self):
        """Validar email de notificación"""
        notification_email = self.cleaned_data.get('notification_email')
        send_notifications = self.cleaned_data.get('send_email_notifications')
        
        if send_notifications and not notification_email:
            raise ValidationError(_('Notification email is required when email notifications are enabled.'))
        
        return notification_email


class CloverPaymentForm(forms.Form):
    """Formulario para procesar pagos con Clover"""
    
    amount = forms.DecimalField(
        label=_('Amount'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0.01'
        })
    )
    
    tip_amount = forms.DecimalField(
        label=_('Tip Amount'),
        max_digits=12,
        decimal_places=2,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0'
        })
    )
    
    tax_amount = forms.DecimalField(
        label=_('Tax Amount'),
        max_digits=12,
        decimal_places=2,
        required=False,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-input',
            'step': '0.01',
            'min': '0'
        })
    )
    
    customer_name = forms.CharField(
        label=_('Customer Name'),
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Enter customer name...')
        })
    )
    
    customer_email = forms.EmailField(
        label=_('Customer Email'),
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': _('customer@example.com')
        })
    )
    
    external_reference = forms.CharField(
        label=_('External Reference'),
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Enter external reference...')
        })
    )
    
    notes = forms.CharField(
        label=_('Notes'),
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3,
            'placeholder': _('Enter payment notes...')
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        amount = cleaned_data.get('amount')
        tip_amount = cleaned_data.get('tip_amount', 0)
        tax_amount = cleaned_data.get('tax_amount', 0)
        
        if amount and amount <= 0:
            raise ValidationError(_('Amount must be greater than zero.'))
        
        if tip_amount and tip_amount < 0:
            raise ValidationError(_('Tip amount cannot be negative.'))
        
        if tax_amount and tax_amount < 0:
            raise ValidationError(_('Tax amount cannot be negative.'))
        
        return cleaned_data 