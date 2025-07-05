from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import (
    TaxGroup, Tax, FiscalPosition, FiscalPositionTax,
    ChartOfAccounts, Journal, JournalEntry, JournalEntryLine
)


class TaxGroupForm(forms.ModelForm):
    """Formulario para grupos de impuestos"""
    
    class Meta:
        model = TaxGroup
        fields = ['name', 'code', 'description', 'account_id', 'refund_account_id', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'placeholder': _('Enter tax group name')
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'placeholder': _('Enter tax group code')
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'rows': 3,
                'placeholder': _('Enter description')
            }),
            'account_id': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent'
            }),
            'refund_account_id': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar cuentas por empresa del usuario
        if 'instance' in kwargs and kwargs['instance']:
            empresa = kwargs['instance'].empresa
        else:
            # Para formularios de creación, necesitaremos obtener la empresa del request
            empresa = None
        
        if empresa:
            self.fields['account_id'].queryset = ChartOfAccounts.objects.filter(
                empresa=empresa, is_active=True
            ).order_by('code')
            self.fields['refund_account_id'].queryset = ChartOfAccounts.objects.filter(
                empresa=empresa, is_active=True
            ).order_by('code')


class TaxForm(forms.ModelForm):
    """Formulario para crear y editar impuestos individuales"""
    
    class Meta:
        model = Tax
        fields = [
            'name', 'code', 'description', 'tax_group', 'sequence',
            'amount_type', 'amount', 'account_id', 'refund_account_id', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter tax name'),
                'required': True
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter tax code'),
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Optional description of the tax')
            }),
            'tax_group': forms.Select(attrs={
                'class': 'form-select'
            }),
            'sequence': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 1,
                'placeholder': '10'
            }),
            'amount_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': '21.00'
            }),
            'account_id': forms.Select(attrs={
                'class': 'form-select'
            }),
            'refund_account_id': forms.Select(attrs={
                'class': 'form-select'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            })
        }
    
    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if empresa:
            # Filtrar grupos de impuestos por empresa
            self.fields['tax_group'].queryset = TaxGroup.objects.filter(
                empresa=empresa
            ).order_by('name')
            
            # Filtrar cuentas por empresa
            accounts_queryset = ChartOfAccounts.objects.filter(
                empresa=empresa,
                is_active=True
            ).order_by('code', 'name')
            
            self.fields['account_id'].queryset = accounts_queryset
            self.fields['refund_account_id'].queryset = accounts_queryset
            
            # Agregar opción vacía para cuentas opcionales
            self.fields['refund_account_id'].empty_label = _("Select refund account (optional)")
        
        # Configurar etiquetas y ayuda
        self.fields['name'].label = _("Tax Name")
        self.fields['code'].label = _("Tax Code")
        self.fields['description'].label = _("Description")
        self.fields['tax_group'].label = _("Tax Group")
        self.fields['sequence'].label = _("Sequence")
        self.fields['amount_type'].label = _("Amount Type")
        self.fields['amount'].label = _("Tax Amount")
        self.fields['account_id'].label = _("Tax Account")
        self.fields['refund_account_id'].label = _("Refund Account")
        self.fields['is_active'].label = _("Active")
        
        # Configurar ayuda
        self.fields['name'].help_text = _("Enter a descriptive name for this tax")
        self.fields['code'].help_text = _("Unique code to identify this tax")
        self.fields['description'].help_text = _("Optional description of the tax purpose")
        self.fields['tax_group'].help_text = _("Group this tax belongs to (optional)")
        self.fields['sequence'].help_text = _("Order of application (lower numbers first)")
        self.fields['amount_type'].help_text = _("Whether the tax is a percentage or fixed amount")
        self.fields['amount'].help_text = _("Tax rate or fixed amount")
        self.fields['account_id'].help_text = _("Account where tax amounts will be recorded")
        self.fields['refund_account_id'].help_text = _("Account for tax refunds (optional)")
        self.fields['is_active'].help_text = _("Enable this tax for use in transactions")
        
        # Configurar valores por defecto
        if not self.instance.pk:
            self.fields['sequence'].initial = 10
            self.fields['amount_type'].initial = 'percent'
            self.fields['amount'].initial = 0.00
            self.fields['is_active'].initial = True
    
    def clean_code(self):
        """Validar que el código sea único por empresa"""
        code = self.cleaned_data['code']
        empresa = getattr(self.instance, 'empresa', None)
        
        if not empresa and hasattr(self, 'empresa'):
            empresa = self.empresa
        
        if empresa:
            # Verificar si ya existe un impuesto con el mismo código
            existing_tax = Tax.objects.filter(
                empresa=empresa,
                code=code
            )
            
            if self.instance.pk:
                existing_tax = existing_tax.exclude(pk=self.instance.pk)
            
            if existing_tax.exists():
                raise ValidationError(_("A tax with this code already exists in this company."))
        
        return code.upper() if code else code
    
    def clean_amount(self):
        """Validar el monto del impuesto"""
        amount = self.cleaned_data['amount']
        amount_type = self.cleaned_data.get('amount_type')
        
        if amount is not None:
            if amount < 0:
                raise ValidationError(_("Tax amount cannot be negative."))
            
            if amount_type == 'percent' and amount > 100:
                raise ValidationError(_("Tax percentage cannot exceed 100%."))
        
        return amount
    
    def clean(self):
        """Validaciones adicionales del formulario"""
        cleaned_data = super().clean()
        
        # Validar que si se selecciona una cuenta de reembolso, también debe seleccionarse una cuenta principal
        account_id = cleaned_data.get('account_id')
        refund_account_id = cleaned_data.get('refund_account_id')
        
        if refund_account_id and not account_id:
            raise ValidationError(_("You must select a main tax account before selecting a refund account."))
        
        # Validar que las cuentas sean diferentes
        if account_id and refund_account_id and account_id == refund_account_id:
            raise ValidationError(_("Tax account and refund account must be different."))
        
        return cleaned_data


class FiscalPositionForm(forms.ModelForm):
    """Formulario para posiciones fiscales"""
    
    class Meta:
        model = FiscalPosition
        fields = ['name', 'code', 'description', 'country_id', 'state_id', 'zip_from', 'zip_to', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'placeholder': _('Enter fiscal position name')
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'placeholder': _('Enter fiscal position code')
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'rows': 3,
                'placeholder': _('Enter description')
            }),
            'country_id': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'placeholder': _('Country code (e.g., AR)')
            }),
            'state_id': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'placeholder': _('State/Province code')
            }),
            'zip_from': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'placeholder': _('Zip code from')
            }),
            'zip_to': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent',
                'placeholder': _('Zip code to')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded'
            }),
        }


class FiscalPositionTaxForm(forms.ModelForm):
    """Formulario para mapeos de posición fiscal"""
    
    class Meta:
        model = FiscalPositionTax
        fields = ['tax_src_id', 'tax_dest_id']
        widgets = {
            'tax_src_id': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent'
            }),
            'tax_dest_id': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-transparent'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar impuestos por empresa
        if 'instance' in kwargs and kwargs['instance']:
            empresa = kwargs['instance'].fiscal_position.empresa
        else:
            empresa = None
        
        if empresa:
            self.fields['tax_src_id'].queryset = Tax.objects.filter(
                empresa=empresa, is_active=True
            ).order_by('tax_group__name', 'name')
            self.fields['tax_dest_id'].queryset = Tax.objects.filter(
                empresa=empresa, is_active=True
            ).order_by('tax_group__name', 'name')


class TaxBulkForm(forms.Form):
    """Formulario para acciones masivas en impuestos"""
    
    ACTION_CHOICES = [
        ('activate', _('Activate Selected')),
        ('deactivate', _('Deactivate Selected')),
        ('delete', _('Delete Selected')),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        label=_("Action"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tax_ids = forms.MultipleChoiceField(
        choices=[],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-checkbox'}),
        label=_("Select Taxes")
    )
    
    def __init__(self, *args, **kwargs):
        taxes = kwargs.pop('taxes', [])
        super().__init__(*args, **kwargs)
        
        if taxes:
            self.fields['tax_ids'].choices = [(tax.id, tax.name) for tax in taxes]


class TaxImportForm(forms.Form):
    """Formulario para importar impuestos desde archivo"""
    
    IMPORT_FORMAT_CHOICES = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('json', 'JSON'),
    ]
    
    file = forms.FileField(
        label=_("Import File"),
        help_text=_("Select a file to import taxes"),
        widget=forms.FileInput(attrs={
            'class': 'form-input',
            'accept': '.csv,.xlsx,.xls,.json'
        })
    )
    
    format = forms.ChoiceField(
        choices=IMPORT_FORMAT_CHOICES,
        label=_("File Format"),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    update_existing = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Update existing taxes"),
        help_text=_("Update taxes that already exist (by code)"),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
    
    create_missing_groups = forms.BooleanField(
        required=False,
        initial=True,
        label=_("Create missing tax groups"),
        help_text=_("Automatically create tax groups that don't exist"),
        widget=forms.CheckboxInput(attrs={'class': 'form-checkbox'})
    )
    
    def clean_file(self):
        """Validar el archivo de importación"""
        file = self.cleaned_data['file']
        
        if file:
            # Validar tamaño del archivo (máximo 5MB)
            if file.size > 5 * 1024 * 1024:
                raise ValidationError(_("File size must be less than 5MB."))
            
            # Validar extensión
            allowed_extensions = ['.csv', '.xlsx', '.xls', '.json']
            file_extension = file.name.lower()
            
            if not any(file_extension.endswith(ext) for ext in allowed_extensions):
                raise ValidationError(_("Invalid file format. Please upload a CSV, Excel, or JSON file."))
        
        return file 