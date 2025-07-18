"""
Formularios para el wizard multi-step de clientes
Incluye selección de tipo de cliente y responsabilidad fiscal dinámica
"""

import json
from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from .models import Client, PaymentMethod, PaymentProcessor, PaymentTerm
from core.models import Country, State, FiscalResponsibility, Empresa, Branch
from .models import PaymentTermLine


class ClientWizardStep1Form(forms.ModelForm):
    """
    Paso 1: Solo selección de tipo de cliente
    """
    client_type = forms.ChoiceField(
        choices=[
            ('individual', _('Persona')),
            ('company', _('Empresa')),
        ],
        widget=forms.RadioSelect(attrs={'class': 'hidden'}),
        initial='individual',
        label=_('Tipo de Cliente'),
        help_text=_('Selecciona si es una persona o una empresa')
    )

    class Meta:
        model = Client
        fields = ['client_type']

    def clean(self):
        cleaned_data = super().clean()
        # Solo validar que client_type esté presente
        if not cleaned_data.get('client_type'):
            self.add_error('client_type', _('Debes seleccionar el tipo de cliente.'))
        return cleaned_data


class ClientWizardStep2Form(forms.ModelForm):
    """
    Paso 2: Datos principales según tipo de cliente
    """
    
    # Campos dinámicos según tipo de cliente
    first_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Nombre')
        }),
        label=_('Nombre')
    )
    
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Apellido')
        }),
        label=_('Apellido')
    )
    
    document_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Número de documento')
        }),
        label=_('Número de Documento')
    )
    
    company_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Nombre de la empresa')
        }),
        label=_('Nombre de la Empresa')
    )
    
    fiscal_responsibility = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input autocomplete-field',
            'placeholder': _('Responsabilidad fiscal'),
            'data-autocomplete-url': '/sales/api/fiscal-responsibilities-autocomplete/',
            'autocomplete': 'off'
        }),
        label=_('Responsabilidad Fiscal')
    )
    
    # Campos de contacto y ubicación
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': _('Email')
        }),
        label=_('Email')
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Teléfono')
        }),
        label=_('Teléfono')
    )
    
    address = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Dirección')
        }),
        label=_('Dirección')
    )
    
    city = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Ciudad')
        }),
        label=_('Ciudad')
    )
    
    postal_code = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Código Postal')
        }),
        label=_('Código Postal')
    )
    
    class Meta:
        model = Client
        fields = []  # No usar campos del modelo para evitar conflictos
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Convertir campos country y state a CharField con autocomplete
        self.fields['country'] = forms.CharField(
            max_length=100,
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-input autocomplete-field',
                'placeholder': _('País'),
                'data-autocomplete-url': '/sales/api/countries-autocomplete/',
                'autocomplete': 'off'
            }),
            label=_('País')
        )
        
        self.fields['state'] = forms.CharField(
            max_length=100,
            required=False,
            widget=forms.TextInput(attrs={
                'class': 'form-input autocomplete-field',
                'placeholder': _('Estado/Provincia'),
                'data-autocomplete-url': '/sales/api/states-autocomplete/',
                'autocomplete': 'off'
            }),
            label=_('Estado/Provincia')
        )
    
    def clean(self):
        cleaned_data = super().clean()
        client_type = self.initial.get('client_type', 'individual')
        
        # Validaciones específicas según tipo de cliente
        if client_type == 'individual':
            if not cleaned_data.get('first_name'):
                self.add_error('first_name', _('El nombre es requerido para personas.'))
            if not cleaned_data.get('last_name'):
                self.add_error('last_name', _('El apellido es requerido para personas.'))
            if not cleaned_data.get('document_number'):
                self.add_error('document_number', _('El número de documento es requerido para personas.'))
        elif client_type == 'company':
            if not cleaned_data.get('company_name'):
                self.add_error('company_name', _('El nombre de la empresa es requerido.'))
            if not cleaned_data.get('fiscal_responsibility'):
                self.add_error('fiscal_responsibility', _('La responsabilidad fiscal es requerida para empresas.'))
        
        # Asegurar que los campos opcionales tengan valores por defecto si están vacíos
        for field_name in ['email', 'phone', 'address', 'city', 'postal_code', 'state', 'country']:
            if field_name in cleaned_data and not cleaned_data[field_name]:
                cleaned_data[field_name] = ''
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Asignar campos según tipo de cliente
        client_type = self.initial.get('client_type', 'individual')
        if client_type == 'individual':
            instance.name = f"{self.cleaned_data.get('first_name', '')} {self.cleaned_data.get('last_name', '')}".strip()
            instance.document_number = self.cleaned_data.get('document_number')
            instance.type = 'individual'
        elif client_type == 'company':
            instance.name = self.cleaned_data.get('company_name')
            instance.fiscal_responsibility = self.cleaned_data.get('fiscal_responsibility')
            instance.type = 'company'
        
        if commit:
            instance.save()
        return instance


class ClientWizardStep3Form(forms.ModelForm):
    """
    Paso 3: Configuración comercial
    """
    
    payment_terms = forms.CharField(
        max_length=128,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input autocomplete-field',
            'placeholder': _('Condiciones de pago'),
            'data-autocomplete-url': '/sales/api/payment-terms-autocomplete/',
            'autocomplete': 'off'
        }),
        label=_('Condiciones de Pago')
    )
    
    class Meta:
        model = Client
        fields = [
            'credit_limit', 'payment_terms', 'customer_category',
            'default_discount', 'is_vip', 'is_prospect'
        ]
        widgets = {
            'credit_limit': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0'
            }),
            'payment_terms': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Condiciones de pago')
            }),
            'customer_category': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Categoría del cliente')
            }),
            'default_discount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
        }


class ContactSearchForm(forms.Form):
    """
    Formulario para búsqueda de contactos existentes
    """
    
    search = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Buscar contactos...')
        })
    )
    
    contact_type = forms.ChoiceField(
        choices=[
            ('', _('Todos los tipos')),
            ('person', _('Persona')),
            ('company', _('Empresa')),
            ('employee', _('Empleado')),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ContactRelationshipForm(forms.Form):
    """
    Formulario para agregar relación de contacto
    """
    
    contact = forms.ModelChoiceField(
        queryset=None,  # Se configurará dinámicamente
        label=_('Contacto'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    relationship_type = forms.ChoiceField(
        choices=[
            ('primary', _('Contacto Principal')),
            ('secondary', _('Contacto Secundario')),
            ('billing', _('Contacto de Facturación')),
            ('technical', _('Contacto Técnico')),
            ('decision_maker', _('Tomador de Decisiones')),
            ('representative', _('Representante')),
            ('other', _('Otro')),
        ],
        label=_('Tipo de Relación'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    notes = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 2,
            'placeholder': _('Notas sobre la relación')
        })
    )
    
    def __init__(self, *args, **kwargs):
        from core.models import Contact
        super().__init__(*args, **kwargs)
        self.fields['contact'].queryset = Contact.objects.filter(is_active=True) 


class PaymentMethodForm(forms.ModelForm):
    """
    Formulario para gestión de medios de pago
    Incluye integración con Clover y MercadoPago
    """
    
    class Meta:
        model = PaymentMethod
        fields = [
            'name', 'code', 'description', 'payment_type', 'card_type',
            'icon', 'color', 'logo_url', 'is_active', 'is_default', 'order',
            'commission_percentage', 'fixed_commission', 'minimum_amount', 'maximum_amount',
            'requires_reference', 'requires_card_number', 'requires_expiry', 'requires_cvv',
            'requires_installments', 'max_installments', 'processing_time_hours',
            'supports_refunds', 'supports_partial_refunds', 'processor_name',
            'processor_config', 'requires_3d_secure', 'supports_tokenization',
            'supported_currencies', 'supported_countries', 'branches'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Nombre del medio de pago')
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Código único (ej: CASH, VISA, MP)')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Descripción detallada del medio de pago')
            }),
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'card_type': forms.Select(attrs={'class': 'form-select'}),
            'icon': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Icono Material Design (ej: credit_card, cash)')
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-input',
                'type': 'color',
                'placeholder': '#3B82F6'
            }),
            'logo_url': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': _('URL del logo del medio de pago')
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_default': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'order': forms.NumberInput(attrs={'class': 'form-input'}),
            'commission_percentage': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'max': '100'
            }),
            'fixed_commission': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0'
            }),
            'minimum_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0'
            }),
            'maximum_amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0'
            }),
            'requires_reference': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'requires_card_number': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'requires_expiry': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'requires_cvv': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'requires_installments': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'max_installments': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '1',
                'max': '60'
            }),
            'processing_time_hours': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': '0'
            }),
            'supports_refunds': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supports_partial_refunds': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'processor_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Nombre del procesador (ej: MercadoPago, Clover)')
            }),
            'requires_3d_secure': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supports_tokenization': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'supported_currencies': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': _('Códigos de moneda separados por comas (ej: ARS, USD, EUR)')
            }),
            'supported_countries': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 2,
                'placeholder': _('Códigos de país separados por comas (ej: AR, US, ES)')
            }),
            'branches': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar queryset para branches
        if 'empresa' in self.initial:
            empresa = self.initial['empresa']
            self.fields['branches'].queryset = empresa.branches.all()
        elif self.instance and self.instance.empresa:
            self.fields['branches'].queryset = self.instance.empresa.branches.all()
        else:
            self.fields['branches'].queryset = Branch.objects.none()
        
        # Configurar campos JSON como texto
        if self.instance and self.instance.processor_config:
            self.fields['processor_config'] = forms.CharField(
                widget=forms.Textarea(attrs={
                    'class': 'form-textarea',
                    'rows': 4,
                    'placeholder': _('Configuración JSON del procesador')
                }),
                initial=json.dumps(self.instance.processor_config, indent=2),
                required=False
            )
        
        if self.instance and self.instance.supported_currencies:
            self.fields['supported_currencies'].initial = ', '.join(self.instance.supported_currencies)
        
        if self.instance and self.instance.supported_countries:
            self.fields['supported_countries'].initial = ', '.join(self.instance.supported_countries)
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar código único
        code = cleaned_data.get('code')
        if code:
            code = code.upper().strip()
            cleaned_data['code'] = code
            
            # Verificar que el código sea único para la empresa
            empresa = self.instance.empresa if self.instance else None
            if empresa:
                existing = PaymentMethod.objects.filter(
                    empresa=empresa, code=code
                ).exclude(pk=self.instance.pk if self.instance else None)
                if existing.exists():
                    self.add_error('code', _('Este código ya existe para esta empresa.'))
        
        # Procesar campos JSON
        processor_config = cleaned_data.get('processor_config')
        if processor_config and isinstance(processor_config, str):
            try:
                cleaned_data['processor_config'] = json.loads(processor_config)
            except json.JSONDecodeError:
                self.add_error('processor_config', _('Configuración JSON inválida.'))
        
        # Procesar listas de monedas y países
        currencies = cleaned_data.get('supported_currencies')
        if currencies and isinstance(currencies, str):
            cleaned_data['supported_currencies'] = [
                c.strip().upper() for c in currencies.split(',') if c.strip()
            ]
        
        countries = cleaned_data.get('supported_countries')
        if countries and isinstance(countries, str):
            cleaned_data['supported_countries'] = [
                c.strip().upper() for c in countries.split(',') if c.strip()
            ]
        
        return cleaned_data


class PaymentProcessorForm(forms.ModelForm):
    """
    Formulario para gestión de procesadores de pago
    Incluye configuración específica para Clover y MercadoPago
    """
    
    # Campos adicionales para configuración específica
    mercadopago_access_token = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': _('Access Token de MercadoPago')
        }),
        help_text=_('Token de acceso para la API de MercadoPago')
    )
    
    mercadopago_public_key = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Public Key de MercadoPago')
        }),
        help_text=_('Clave pública para MercadoPago')
    )
    
    clover_app_id = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('App ID de Clover')
        }),
        help_text=_('ID de la aplicación Clover')
    )
    
    clover_app_secret = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': _('App Secret de Clover')
        }),
        help_text=_('Secret de la aplicación Clover')
    )
    
    clover_merchant_id = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Merchant ID de Clover')
        }),
        help_text=_('ID del comercio en Clover')
    )
    
    class Meta:
        model = PaymentProcessor
        fields = [
            'name', 'processor_type', 'is_active', 'api_key', 'api_secret',
            'webhook_url', 'webhook_secret', 'config'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Nombre del procesador')
            }),
            'processor_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'api_key': forms.PasswordInput(attrs={
                'class': 'form-input',
                'placeholder': _('API Key')
            }),
            'api_secret': forms.PasswordInput(attrs={
                'class': 'form-input',
                'placeholder': _('API Secret')
            }),
            'webhook_url': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': _('URL del webhook')
            }),
            'webhook_secret': forms.PasswordInput(attrs={
                'class': 'form-input',
                'placeholder': _('Secret del webhook')
            }),
            'config': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 6,
                'placeholder': _('Configuración JSON adicional')
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Cargar configuración específica si existe
        if self.instance and self.instance.config:
            config = self.instance.config
            
            # MercadoPago
            if self.instance.processor_type == 'mercadopago':
                self.fields['mercadopago_access_token'].initial = config.get('access_token', '')
                self.fields['mercadopago_public_key'].initial = config.get('public_key', '')
            
            # Clover
            elif self.instance.processor_type == 'clover':
                self.fields['clover_app_id'].initial = config.get('app_id', '')
                self.fields['clover_app_secret'].initial = config.get('app_secret', '')
                self.fields['clover_merchant_id'].initial = config.get('merchant_id', '')
        
        # Configurar campos JSON como texto
        if self.instance and self.instance.config:
            self.fields['config'] = forms.CharField(
                widget=forms.Textarea(attrs={
                    'class': 'form-textarea',
                    'rows': 6,
                    'placeholder': _('Configuración JSON adicional')
                }),
                initial=json.dumps(self.instance.config, indent=2),
                required=False
            )
    
    def clean(self):
        cleaned_data = super().clean()
        processor_type = cleaned_data.get('processor_type')
        
        # Validaciones específicas por tipo de procesador
        if processor_type == 'mercadopago':
            access_token = cleaned_data.get('mercadopago_access_token')
            public_key = cleaned_data.get('mercadopago_public_key')
            
            if not access_token:
                self.add_error('mercadopago_access_token', _('Access Token es requerido para MercadoPago.'))
            if not public_key:
                self.add_error('mercadopago_public_key', _('Public Key es requerida para MercadoPago.'))
            
            # Actualizar configuración
            config = cleaned_data.get('config', {})
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except json.JSONDecodeError:
                    config = {}
            
            config.update({
                'access_token': access_token,
                'public_key': public_key
            })
            cleaned_data['config'] = config
        
        elif processor_type == 'clover':
            app_id = cleaned_data.get('clover_app_id')
            app_secret = cleaned_data.get('clover_app_secret')
            merchant_id = cleaned_data.get('clover_merchant_id')
            
            if not app_id:
                self.add_error('clover_app_id', _('App ID es requerido para Clover.'))
            if not app_secret:
                self.add_error('clover_app_secret', _('App Secret es requerido para Clover.'))
            if not merchant_id:
                self.add_error('clover_merchant_id', _('Merchant ID es requerido para Clover.'))
            
            # Actualizar configuración
            config = cleaned_data.get('config', {})
            if isinstance(config, str):
                try:
                    config = json.loads(config)
                except json.JSONDecodeError:
                    config = {}
            
            config.update({
                'app_id': app_id,
                'app_secret': app_secret,
                'merchant_id': merchant_id
            })
            cleaned_data['config'] = config
        
        # Procesar configuración JSON
        config = cleaned_data.get('config')
        if config and isinstance(config, str):
            try:
                cleaned_data['config'] = json.loads(config)
            except json.JSONDecodeError:
                self.add_error('config', _('Configuración JSON inválida.'))
        
        return cleaned_data 


class PaymentTermForm(forms.ModelForm):
    class Meta:
        model = PaymentTerm
        fields = ['name', 'description', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': _('Nombre de la condición de pago')}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'placeholder': _('Descripción'), 'rows': 2}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
        labels = {
            'name': _('Nombre'),
            'description': _('Descripción'),
            'is_active': _('Activa'),
        }


class PaymentTermLineForm(forms.ModelForm):
    class Meta:
        model = PaymentTermLine
        fields = ['percent', 'days', 'sequence']
        widgets = {
            'percent': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0', 'max': '100', 'placeholder': _('Porcentaje')}),
            'days': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': _('Días desde la fecha')}),
            'sequence': forms.NumberInput(attrs={'class': 'form-input', 'placeholder': _('Orden')}),
        }
        labels = {
            'percent': _('Porcentaje'),
            'days': _('Días desde la fecha'),
            'sequence': _('Orden'),
        }


class ClientSearchForm(forms.Form):
    """
    Formulario de búsqueda de clientes para TPV
    Permite búsqueda rápida por documento, nombre o email
    """
    
    search_type = forms.ChoiceField(
        choices=[
            ('document', _('Documento')),
            ('name', _('Nombre')),
            ('email', _('Email')),
            ('phone', _('Teléfono')),
        ],
        initial='document',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    search_term = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Buscar cliente...'),
            'autocomplete': 'off'
        })
    )
    
    include_inactive = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        help_text=_('Incluir clientes inactivos')
    )
    
    def clean_search_term(self):
        search_term = self.cleaned_data.get('search_term', '').strip()
        if len(search_term) < 2:
            raise ValidationError(_('El término de búsqueda debe tener al menos 2 caracteres.'))
        return search_term


class POSClientSelectionForm(forms.Form):
    """
    Formulario para selección de cliente en TPV
    Incluye opción para cliente ocasional
    """
    
    client_selection_type = forms.ChoiceField(
        choices=[
            ('existing', _('Cliente Existente')),
            ('occasional', _('Cliente Ocasional')),
        ],
        initial='existing',
        widget=forms.RadioSelect(attrs={'class': 'hidden'})
    )
    
    # Para cliente existente
    client_id = forms.ModelChoiceField(
        queryset=Client.objects.filter(is_active=True),
        required=False,
        empty_label=_('Seleccionar cliente...'),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    # Para cliente ocasional
    occasional_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Nombre del cliente ocasional')
        })
    )
    
    occasional_document = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Documento (DNI, CUIT, etc.)')
        })
    )
    
    occasional_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': _('Email (opcional)')
        })
    )
    
    occasional_phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Teléfono (opcional)')
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        selection_type = cleaned_data.get('client_selection_type')
        
        if selection_type == 'existing':
            if not cleaned_data.get('client_id'):
                self.add_error('client_id', _('Debe seleccionar un cliente existente.'))
        
        elif selection_type == 'occasional':
            if not cleaned_data.get('occasional_name'):
                self.add_error('occasional_name', _('El nombre es requerido para clientes ocasionales.'))
            if not cleaned_data.get('occasional_document'):
                self.add_error('occasional_document', _('El documento es requerido para clientes ocasionales.'))
        
        return cleaned_data
    
    def get_client_data(self):
        """
        Retorna los datos del cliente seleccionado o creado
        """
        selection_type = self.cleaned_data.get('client_selection_type')
        
        if selection_type == 'existing':
            return {
                'type': 'existing',
                'client': self.cleaned_data.get('client_id'),
                'is_occasional': False
            }
        else:
            return {
                'type': 'occasional',
                'client_data': {
                    'name': self.cleaned_data.get('occasional_name'),
                    'document_number': self.cleaned_data.get('occasional_document'),
                    'email': self.cleaned_data.get('occasional_email'),
                    'phone': self.cleaned_data.get('occasional_phone'),
                },
                'is_occasional': True
            } 


class ContactManagementForm(forms.Form):
    """
    Formulario para gestión de contactos en el wizard de clientes
    Permite crear nuevos contactos y gestionar relaciones
    """
    
    # Campos para nuevo contacto
    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Nombre completo del contacto')
        }),
        help_text=_('Nombre completo del contacto')
    )
    
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': _('Email del contacto')
        }),
        help_text=_('Email del contacto (opcional)')
    )
    
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Teléfono del contacto')
        }),
        help_text=_('Teléfono del contacto (opcional)')
    )
    
    position = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Cargo o posición')
        }),
        help_text=_('Cargo o posición en la empresa (opcional)')
    )
    
    # Tipo de relación
    relationship_type = forms.ChoiceField(
        choices=[
            ('primary', _('Contacto Principal')),
            ('secondary', _('Contacto Secundario')),
            ('billing', _('Contacto de Facturación')),
            ('technical', _('Contacto Técnico')),
            ('decision_maker', _('Tomador de Decisiones')),
            ('representative', _('Representante')),
            ('other', _('Otro')),
        ],
        initial='secondary',
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text=_('Tipo de relación con el cliente')
    )
    
    # Notas adicionales
    notes = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3,
            'placeholder': _('Notas adicionales sobre el contacto')
        }),
        help_text=_('Notas adicionales sobre el contacto (opcional)')
    )
    
    def clean(self):
        cleaned_data = super().clean()
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        
        # Al menos email o teléfono debe estar presente
        if not email and not phone:
            raise ValidationError(_('El contacto debe tener al menos un email o teléfono.'))
        
        return cleaned_data
    
    def save_contact(self, client):
        """
        Crear el contacto y asociarlo al cliente
        """
        from core.models import Contact
        
        # Crear el contacto
        contact_data = {
            'name': self.cleaned_data['name'],
            'email': self.cleaned_data['email'],
            'phone': self.cleaned_data['phone'],
            'position': self.cleaned_data['position'],
            'empresa': client.empresa,
        }
        
        # Si el cliente es empresa, usar su nombre como company_name del contacto
        if client.type == 'company':
            contact_data['company_name'] = client.name
        
        contact = Contact.objects.create(**contact_data)
        
        # Crear la relación
        relationship = client.add_contact(
            contact, 
            self.cleaned_data['relationship_type'],
            notes=self.cleaned_data.get('notes', '')
        )
        
        return contact, relationship 