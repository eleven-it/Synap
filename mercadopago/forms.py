from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Button, HTML
from crispy_forms.bootstrap import TabHolder, Tab
from mercadopago.models import MercadoPagoConfig, MercadoPagoDevice, MercadoPagoTransaction


class MercadoPagoConfigForm(forms.ModelForm):
    """
    Formulario para configuración de MercadoPago
    """
    
    class Meta:
        model = MercadoPagoConfig
        fields = [
            'empresa', 'is_active', 'is_sandbox',
            'client_id', 'client_secret',
            'webhook_url', 'webhook_secret',
            'supported_payment_methods', 'commission_percentage',
            'auto_capture', 'installments_enabled', 'max_installments',
            'smartpos_enabled', 'smartpos_api_key', 'smartpos_webhook_url',
            'allow_multiple_devices', 'max_devices_per_branch', 'device_sync_interval',
            'config'
        ]
        widgets = {
            'client_secret': forms.PasswordInput(attrs={'class': 'mp-input'}),
            'webhook_secret': forms.PasswordInput(attrs={'class': 'mp-input'}),
            'smartpos_api_key': forms.PasswordInput(attrs={'class': 'mp-input'}),
            'supported_payment_methods': forms.CheckboxSelectMultiple(),
            'config': forms.Textarea(attrs={'rows': 4, 'class': 'mp-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'mp-form'
        self.helper.layout = Layout(
            TabHolder(
                Tab(_('Basic Configuration'),
                    Row(
                        Column('empresa', css_class='form-group col-md-6'),
                        Column('is_active', css_class='form-group col-md-6'),
                    ),
                    Row(
                        Column('is_sandbox', css_class='form-group col-md-6'),
                        Column('commission_percentage', css_class='form-group col-md-6'),
                    ),
                    HTML('<hr class="my-4">'),
                    Row(
                        Column('client_id', css_class='form-group col-md-6'),
                        Column('client_secret', css_class='form-group col-md-6'),
                    ),
                ),
                Tab(_('Payment Settings'),
                    Row(
                        Column('auto_capture', css_class='form-group col-md-6'),
                        Column('installments_enabled', css_class='form-group col-md-6'),
                    ),
                    Row(
                        Column('max_installments', css_class='form-group col-md-6'),
                        Column('supported_payment_methods', css_class='form-group col-md-6'),
                    ),
                ),
                Tab(_('SmartPOS Configuration'),
                    Row(
                        Column('smartpos_enabled', css_class='form-group col-md-6'),
                        Column('smartpos_api_key', css_class='form-group col-md-6'),
                    ),
                    Row(
                        Column('smartpos_webhook_url', css_class='form-group col-md-12'),
                    ),
                    HTML('<hr class="my-4">'),
                    Row(
                        Column('allow_multiple_devices', css_class='form-group col-md-6'),
                        Column('max_devices_per_branch', css_class='form-group col-md-6'),
                    ),
                    Row(
                        Column('device_sync_interval', css_class='form-group col-md-6'),
                    ),
                ),
                Tab(_('Webhooks'),
                    Row(
                        Column('webhook_url', css_class='form-group col-md-6'),
                        Column('webhook_secret', css_class='form-group col-md-6'),
                    ),
                ),
                Tab(_('Advanced'),
                    Row(
                        Column('config', css_class='form-group col-md-12'),
                    ),
                ),
            ),
            HTML('<div class="mt-4 flex space-x-4">'),
            Submit('save', _('Save Configuration'), css_class='mp-button-primary'),
            Button('test', _('Test Connection'), css_class='mp-button-secondary', onclick='testConnection()'),
            HTML('</div>'),
        )
        
        # Agregar clases CSS a los campos
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                field.widget.attrs.update({'class': 'mp-input'})
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validaciones adicionales
        if cleaned_data.get('is_sandbox') and cleaned_data.get('is_active'):
            self.add_warning(_('Sandbox mode is active. Consider disabling for production.'))
        
        if cleaned_data.get('commission_percentage', 0) > 100:
            raise forms.ValidationError(_('Commission percentage cannot exceed 100%'))
        
        return cleaned_data


class MercadoPagoDeviceForm(forms.ModelForm):
    """
    Formulario para dispositivos SmartPOS
    """
    
    class Meta:
        model = MercadoPagoDevice
        fields = [
            'name', 'device_type', 'serial_number',
            'empresa', 'branch', 'config',
            'status', 'is_default', 'is_active',
            'device_config', 'supported_payment_methods',
            'firmware_version', 'hardware_model', 'location_description'
        ]
        widgets = {
            'device_config': forms.Textarea(attrs={'rows': 4, 'class': 'mp-input'}),
            'supported_payment_methods': forms.CheckboxSelectMultiple(),
            'location_description': forms.Textarea(attrs={'rows': 3, 'class': 'mp-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'mp-form'
        self.helper.layout = Layout(
            TabHolder(
                Tab(_('Device Information'),
                    Row(
                        Column('name', css_class='form-group col-md-6'),
                        Column('device_type', css_class='form-group col-md-6'),
                    ),
                    Row(
                        Column('serial_number', css_class='form-group col-md-6'),
                        Column('is_default', css_class='form-group col-md-6'),
                    ),
                    Row(
                        Column('empresa', css_class='form-group col-md-6'),
                        Column('branch', css_class='form-group col-md-6'),
                    ),
                    Row(
                        Column('config', css_class='form-group col-md-12'),
                    ),
                ),
                Tab(_('Status & Configuration'),
                    Row(
                        Column('status', css_class='form-group col-md-6'),
                        Column('is_active', css_class='form-group col-md-6'),
                    ),
                    Row(
                        Column('supported_payment_methods', css_class='form-group col-md-12'),
                    ),
                    HTML('<hr class="my-4">'),
                    Row(
                        Column('device_config', css_class='form-group col-md-12'),
                    ),
                ),
                Tab(_('Hardware Information'),
                    Row(
                        Column('firmware_version', css_class='form-group col-md-6'),
                        Column('hardware_model', css_class='form-group col-md-6'),
                    ),
                    Row(
                        Column('location_description', css_class='form-group col-md-12'),
                    ),
                ),
            ),
            HTML('<div class="mt-4 flex space-x-4">'),
            Submit('save', _('Save Device'), css_class='mp-button-primary'),
            Button('sync', _('Sync Status'), css_class='mp-button-secondary', onclick='syncDevice()'),
            HTML('</div>'),
        )
        
        # Agregar clases CSS a los campos
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                field.widget.attrs.update({'class': 'mp-input'})
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validaciones adicionales
        if cleaned_data.get('is_default') and cleaned_data.get('branch'):
            # Verificar que no haya otro dispositivo default en la misma sucursal
            existing_default = MercadoPagoDevice.objects.filter(
                empresa=cleaned_data.get('empresa'),
                branch=cleaned_data.get('branch'),
                is_default=True
            ).exclude(pk=self.instance.pk if self.instance else None)
            
            if existing_default.exists():
                raise forms.ValidationError(_('There is already a default device for this branch'))
        
        return cleaned_data


class TransactionFilterForm(forms.Form):
    """
    Formulario para filtrar transacciones
    """
    status = forms.ChoiceField(
        choices=[('', _('All Status'))] + MercadoPagoTransaction.STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'mp-input'})
    )
    
    payment_method = forms.ChoiceField(
        choices=[
            ('', _('All Methods')),
            ('credit_card', _('Credit Card')),
            ('debit_card', _('Debit Card')),
            ('cash', _('Cash')),
            ('preference', _('Web Preference')),
            ('smartpos', _('SmartPOS')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'mp-input'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'mp-input', 'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'mp-input', 'type': 'date'})
    )
    
    amount_min = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'mp-input', 'placeholder': _('Min amount')})
    )
    
    amount_max = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'mp-input', 'placeholder': _('Max amount')})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'mp-filter-form'
        self.helper.layout = Layout(
            Row(
                Column('status', css_class='form-group col-md-2'),
                Column('payment_method', css_class='form-group col-md-2'),
                Column('date_from', css_class='form-group col-md-2'),
                Column('date_to', css_class='form-group col-md-2'),
                Column('amount_min', css_class='form-group col-md-2'),
                Column('amount_max', css_class='form-group col-md-2'),
            ),
            HTML('<div class="mt-3">'),
            Submit('filter', _('Apply Filters'), css_class='mp-button-secondary'),
            Button('clear', _('Clear'), css_class='mp-button-secondary', onclick='clearFilters()'),
            HTML('</div>'),
        ) 