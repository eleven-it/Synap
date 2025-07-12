from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.db.models import Q
from .models import (
    TaxGroup, Tax, FiscalPosition, FiscalPositionTax,
    ChartOfAccounts, Journal, JournalEntry, JournalEntryLine,
    AccountTypes, FiscalYear, AccountingPeriod
)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Button, HTML


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


class ChartOfAccountsForm(forms.ModelForm):
    """Formulario para crear y editar cuentas contables"""
    
    class Meta:
        model = ChartOfAccounts
        fields = [
            'name', 'code', 'parent', 'account_type', 'is_active',
            'is_reconcilable', 'allow_reconciliation', 'deprecated',
            'is_tax_account', 'tax_type'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter account name')
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter account code')
            }),
            'parent': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'account_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700'
            }),
            'is_reconcilable': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700'
            }),
            'allow_reconciliation': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700'
            }),
            'deprecated': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700'
            }),
            'is_tax_account': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700'
            }),
            'tax_type': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter tax type (e.g., VAT, Income Tax)')
            }),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if empresa:
            # Filtrar cuentas padre por empresa
            self.fields['parent'].queryset = ChartOfAccounts.objects.filter(
                empresa=empresa,
                is_active=True
            ).order_by('code', 'name')
            
            # Agregar opción vacía para cuentas padre
            self.fields['parent'].empty_label = _("Select parent account (optional)")
        
        # Configurar etiquetas y ayuda
        self.fields['name'].label = _("Account Name")
        self.fields['code'].label = _("Account Code")
        self.fields['parent'].label = _("Parent Account")
        self.fields['account_type'].label = _("Account Type")
        self.fields['is_active'].label = _("Active")
        self.fields['is_reconcilable'].label = _("Reconcilable")
        self.fields['allow_reconciliation'].label = _("Allow Reconciliation")
        self.fields['deprecated'].label = _("Deprecated")
        self.fields['is_tax_account'].label = _("Tax Account")
        self.fields['tax_type'].label = _("Tax Type")
        
        # Configurar ayuda
        self.fields['name'].help_text = _("Enter a descriptive name for this account")
        self.fields['code'].help_text = _("Unique code to identify this account")
        self.fields['parent'].help_text = _("Parent account for hierarchical structure")
        self.fields['account_type'].help_text = _("Type of account (Assets, Liabilities, Equity, Income, Expenses)")
        self.fields['is_active'].help_text = _("Enable this account for use in transactions")
        self.fields['is_reconcilable'].help_text = _("Allow manual reconciliation of this account")
        self.fields['allow_reconciliation'].help_text = _("Allow automatic reconciliation")
        self.fields['deprecated'].help_text = _("Mark account as deprecated (not for new transactions)")
        self.fields['is_tax_account'].help_text = _("Mark this account as a tax account")
        self.fields['tax_type'].help_text = _("Type of tax for tax accounts")
        
        # Configurar valores por defecto
        if not self.instance.pk:
            self.fields['is_active'].initial = True
            self.fields['is_reconcilable'].initial = False
            self.fields['allow_reconciliation'].initial = False
            self.fields['deprecated'].initial = False
            self.fields['is_tax_account'].initial = False

    def clean_code(self):
        """Validar que el código sea único por empresa"""
        code = self.cleaned_data['code']
        empresa = getattr(self.instance, 'empresa', None)
        
        if not empresa and hasattr(self, 'empresa'):
            empresa = self.empresa
        
        if empresa:
            # Verificar si ya existe una cuenta con el mismo código
            existing_account = ChartOfAccounts.objects.filter(
                empresa=empresa,
                code=code
            )
            
            if self.instance.pk:
                existing_account = existing_account.exclude(pk=self.instance.pk)
            
            if existing_account.exists():
                raise ValidationError(_("An account with this code already exists in this company."))
        
        return code.upper() if code else code

    def clean(self):
        """Validaciones adicionales del formulario"""
        cleaned_data = super().clean()
        
        # Validar que si se selecciona una cuenta padre, tenga el mismo tipo
        parent = cleaned_data.get('parent')
        account_type = cleaned_data.get('account_type')
        
        if parent and account_type and parent.account_type != account_type:
            raise ValidationError(_("Child account must have the same type as parent account."))
        
        # Validar que no se seleccione como padre una cuenta que sea hija de esta
        if self.instance.pk and parent:
            if self._is_descendant(parent, self.instance):
                raise ValidationError(_("Cannot select a descendant account as parent."))
        
        # Validar campos de cuenta de impuestos
        is_tax_account = cleaned_data.get('is_tax_account')
        tax_type = cleaned_data.get('tax_type')
        
        if is_tax_account and not tax_type:
            raise ValidationError(_("Tax type is required for tax accounts."))
        
        return cleaned_data

    def _is_descendant(self, potential_parent, account):
        """Verificar si una cuenta es descendiente de otra"""
        current = potential_parent
        while current:
            if current == account:
                return True
            current = current.parent
        return False


class JournalForm(forms.ModelForm):
    """Formulario para crear y editar diarios contables"""
    
    class Meta:
        model = Journal
        fields = [
            'name', 'code', 'journal_type', 'default_account', 'is_active',
            'sequence_id', 'tax_account'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter journal name')
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter journal code')
            }),
            'journal_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'default_account': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded dark:border-gray-600 dark:bg-gray-700'
            }),
            'sequence_id': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter sequence number')
            }),
            'tax_account': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if empresa:
            # Filtrar cuentas por empresa
            self.fields['default_account'].queryset = ChartOfAccounts.objects.filter(
                empresa=empresa,
                is_active=True
            ).order_by('code', 'name')
            
            # Filtrar cuentas de impuestos
            self.fields['tax_account'].queryset = ChartOfAccounts.objects.filter(
                empresa=empresa,
                is_active=True,
                is_tax_account=True
            ).order_by('code', 'name')
            
            # Agregar opción vacía
            self.fields['default_account'].empty_label = _("Select default account (optional)")
            self.fields['tax_account'].empty_label = _("Select tax account (optional)")
        
        # Configurar etiquetas y ayuda
        self.fields['name'].label = _("Journal Name")
        self.fields['code'].label = _("Journal Code")
        self.fields['journal_type'].label = _("Journal Type")
        self.fields['default_account'].label = _("Default Account")
        self.fields['is_active'].label = _("Active")
        self.fields['sequence_id'].label = _("Sequence ID")
        self.fields['tax_account'].label = _("Tax Account")
        
        # Configurar ayuda
        self.fields['name'].help_text = _("Enter a descriptive name for this journal")
        self.fields['code'].help_text = _("Unique code to identify this journal")
        self.fields['journal_type'].help_text = _("Type of journal (Sales, Purchase, Cash, Bank, Miscellaneous)")
        self.fields['default_account'].help_text = _("Default account for journal entries")
        self.fields['is_active'].help_text = _("Enable this journal for use")
        self.fields['sequence_id'].help_text = _("Sequence number for journal entries")
        self.fields['tax_account'].help_text = _("Default tax account for this journal")
        
        # Configurar valores por defecto
        if not self.instance.pk:
            self.fields['is_active'].initial = True
            self.fields['sequence_id'].initial = 1

    def clean_code(self):
        """Validar que el código sea único por empresa"""
        code = self.cleaned_data['code']
        empresa = getattr(self.instance, 'empresa', None)
        
        if not empresa and hasattr(self, 'empresa'):
            empresa = self.empresa
        
        if empresa:
            # Verificar si ya existe un diario con el mismo código
            existing_journal = Journal.objects.filter(
                empresa=empresa,
                code=code
            )
            
            if self.instance.pk:
                existing_journal = existing_journal.exclude(pk=self.instance.pk)
            
            if existing_journal.exists():
                raise ValidationError(_("A journal with this code already exists in this company."))
        
        return code.upper() if code else code

    def clean(self):
        """Validaciones adicionales del formulario"""
        cleaned_data = super().clean()
        
        # Validar que la cuenta por defecto sea del tipo correcto según el tipo de diario
        journal_type = cleaned_data.get('journal_type')
        default_account = cleaned_data.get('default_account')
        
        if journal_type and default_account:
            # Mapear tipos de diario a tipos de cuenta
            type_mapping = {
                'sale': 'income',
                'purchase': 'expenses',
                'cash': 'assets',
                'bank': 'assets',
                'misc': None,  # Misc puede usar cualquier tipo
            }
            
            expected_account_type = type_mapping.get(journal_type)
            if expected_account_type and default_account.account_type != expected_account_type:
                raise ValidationError(
                    _("Default account type does not match journal type. Expected: {}").format(
                        dict(AccountTypes.CHOICES).get(expected_account_type, expected_account_type)
                    )
                )
        
        return cleaned_data 

class JournalEntryForm(forms.ModelForm):
    """Formulario para crear y editar asientos contables"""
    
    class Meta:
        model = JournalEntry
        fields = [
            'journal', 'number', 'date', 'reference', 'narration'
        ]
        widgets = {
            'journal': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'number': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter entry number')
            }),
            'date': forms.DateInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'type': 'date'
            }),
            'reference': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter reference')
            }),
            'narration': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'rows': 3,
                'placeholder': _('Enter narration')
            }),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if empresa:
            # Filtrar diarios por empresa
            self.fields['journal'].queryset = Journal.objects.filter(
                empresa=empresa,
                is_active=True
            ).order_by('code', 'name')
        
        # Configurar etiquetas y ayuda
        self.fields['journal'].label = _("Journal")
        self.fields['number'].label = _("Entry Number")
        self.fields['date'].label = _("Entry Date")
        self.fields['reference'].label = _("Reference")
        self.fields['narration'].label = _("Narration")
        
        # Configurar ayuda
        self.fields['journal'].help_text = _("Select the journal for this entry")
        self.fields['number'].help_text = _("Unique number for this journal entry")
        self.fields['date'].help_text = _("Date of the journal entry")
        self.fields['reference'].help_text = _("Optional reference for this entry")
        self.fields['narration'].help_text = _("Description of the journal entry")
        
        # Configurar valores por defecto
        if not self.instance.pk:
            from django.utils import timezone
            self.fields['date'].initial = timezone.now().date()

    def clean_number(self):
        """Validar que el número sea único por empresa"""
        number = self.cleaned_data['number']
        empresa = getattr(self.instance, 'empresa', None)
        
        if not empresa and hasattr(self, 'empresa'):
            empresa = self.empresa
        
        if empresa:
            # Verificar si ya existe un asiento con el mismo número
            existing_entry = JournalEntry.objects.filter(
                empresa=empresa,
                number=number
            )
            
            if self.instance.pk:
                existing_entry = existing_entry.exclude(pk=self.instance.pk)
            
            if existing_entry.exists():
                raise ValidationError(_("A journal entry with this number already exists in this company."))
        
        return number.upper() if number else number


class JournalEntryLineForm(forms.ModelForm):
    """Formulario para líneas de asiento contable"""
    
    class Meta:
        model = JournalEntryLine
        fields = [
            'account', 'partner', 'debit', 'credit', 'name',
            'amount_currency', 'currency'
        ]
        widgets = {
            'account': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'partner': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'debit': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'credit': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter description')
            }),
            'amount_currency': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'step': '0.01',
                'placeholder': '0.00'
            }),
            'currency': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
        }

    def __init__(self, *args, **kwargs):
        empresa = kwargs.pop('empresa', None)
        super().__init__(*args, **kwargs)
        
        if empresa:
            # Filtrar cuentas por empresa
            self.fields['account'].queryset = ChartOfAccounts.objects.filter(
                empresa=empresa,
                is_active=True
            ).order_by('code', 'name')
            
            # Filtrar clientes por empresa (si existe el modelo)
            try:
                from sales.models import Client
                self.fields['partner'].queryset = Client.objects.filter(
                    empresa=empresa,
                    is_active=True
                ).order_by('name')
            except ImportError:
                self.fields['partner'].queryset = self.fields['partner'].queryset.none()
            
            # Filtrar monedas
            try:
                from core.models import Currency
                self.fields['currency'].queryset = Currency.objects.filter(
                    is_active=True
                ).order_by('name')
            except ImportError:
                self.fields['currency'].queryset = self.fields['currency'].queryset.none()
        
        # Configurar etiquetas y ayuda
        self.fields['account'].label = _("Account")
        self.fields['partner'].label = _("Partner")
        self.fields['debit'].label = _("Debit")
        self.fields['credit'].label = _("Credit")
        self.fields['name'].label = _("Description")
        self.fields['amount_currency'].label = _("Amount Currency")
        self.fields['currency'].label = _("Currency")
        
        # Configurar ayuda
        self.fields['account'].help_text = _("Select the account for this line")
        self.fields['partner'].help_text = _("Select partner (optional)")
        self.fields['debit'].help_text = _("Debit amount")
        self.fields['credit'].help_text = _("Credit amount")
        self.fields['name'].help_text = _("Description of this line")
        self.fields['amount_currency'].help_text = _("Amount in foreign currency")
        self.fields['currency'].help_text = _("Foreign currency")
        
        # Configurar valores por defecto
        if not self.instance.pk:
            self.fields['debit'].initial = 0
            self.fields['credit'].initial = 0

    def clean(self):
        """Validar que no tenga débito y crédito al mismo tiempo"""
        cleaned_data = super().clean()
        debit = cleaned_data.get('debit', 0)
        credit = cleaned_data.get('credit', 0)
        
        if debit > 0 and credit > 0:
            raise ValidationError(_("A line cannot have both debit and credit amounts."))
        
        if debit == 0 and credit == 0:
            raise ValidationError(_("A line must have either debit or credit amount."))
        
        return cleaned_data


# FormSet para las líneas del asiento
from django.forms import inlineformset_factory

JournalEntryLineFormSet = inlineformset_factory(
    JournalEntry,
    JournalEntryLine,
    form=JournalEntryLineForm,
    extra=1,
    can_delete=True,
    min_num=2,  # Mínimo 2 líneas para un asiento
    validate_min=True,
) 

# --- FORMULARIOS DE PERÍODOS CONTABLES ---

class FiscalYearForm(forms.ModelForm):
    """Formulario para años fiscales"""
    
    class Meta:
        model = FiscalYear
        fields = [
            'name', 'code', 'description', 'date_from', 'date_to',
            'is_active', 'period_length', 'auto_create_periods',
            'allow_negative_cash', 'allow_negative_equity'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter fiscal year name')
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter fiscal year code')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Enter description')
            }),
            'date_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_to': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'period_length': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 12
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6'),
                Column('code', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Row(
                Column('date_from', css_class='form-group col-md-6'),
                Column('date_to', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            'description',
            Row(
                Column('period_length', css_class='form-group col-md-4'),
                Column('auto_create_periods', css_class='form-group col-md-4'),
                Column('is_active', css_class='form-group col-md-4'),
                css_class='form-row'
            ),
            Row(
                Column('allow_negative_cash', css_class='form-group col-md-6'),
                Column('allow_negative_equity', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            HTML('<hr>'),
            Row(
                Column(
                    Submit('submit', _('Save'), css_class='btn btn-primary'),
                    Button('cancel', _('Cancel'), css_class='btn btn-secondary', onclick='history.back()'),
                    css_class='col-lg-10 col-lg-offset-2'
                )
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_from and date_to and date_from >= date_to:
            raise forms.ValidationError(_('Start date must be before end date.'))
        
        return cleaned_data


class AccountingPeriodForm(forms.ModelForm):
    """Formulario para períodos contables"""
    
    class Meta:
        model = AccountingPeriod
        fields = [
            'fiscal_year', 'name', 'code', 'description', 'date_from', 'date_to',
            'is_active', 'is_adjustment', 'sequence', 'allow_entries', 'allow_adjustments'
        ]
        widgets = {
            'fiscal_year': forms.Select(attrs={
                'class': 'form-control'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter period name')
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Enter period code')
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': _('Enter description')
            }),
            'date_from': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'date_to': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'sequence': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'form-horizontal'
        self.helper.label_class = 'col-lg-2'
        self.helper.field_class = 'col-lg-8'
        
        # Filtrar años fiscales por empresa
        if 'instance' in kwargs and kwargs['instance']:
            empresa = kwargs['instance'].empresa
        else:
            # Esto se manejará en la vista
            empresa = None
        
        if empresa:
            self.fields['fiscal_year'].queryset = FiscalYear.objects.filter(
                empresa=empresa,
                is_active=True
            ).order_by('-date_from')
        
        self.helper.layout = Layout(
            'fiscal_year',
            Row(
                Column('name', css_class='form-group col-md-6'),
                Column('code', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            Row(
                Column('date_from', css_class='form-group col-md-6'),
                Column('date_to', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            'description',
            Row(
                Column('sequence', css_class='form-group col-md-4'),
                Column('is_active', css_class='form-group col-md-4'),
                Column('is_adjustment', css_class='form-group col-md-4'),
                css_class='form-row'
            ),
            Row(
                Column('allow_entries', css_class='form-group col-md-6'),
                Column('allow_adjustments', css_class='form-group col-md-6'),
                css_class='form-row'
            ),
            HTML('<hr>'),
            Row(
                Column(
                    Submit('submit', _('Save'), css_class='btn btn-primary'),
                    Button('cancel', _('Cancel'), css_class='btn btn-secondary', onclick='history.back()'),
                    css_class='col-lg-10 col-lg-offset-2'
                )
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        fiscal_year = cleaned_data.get('fiscal_year')
        
        if date_from and date_to and date_from >= date_to:
            raise forms.ValidationError(_('Start date must be before end date.'))
        
        if fiscal_year and date_from and date_to:
            if date_from < fiscal_year.date_from or date_to > fiscal_year.date_to:
                raise forms.ValidationError(_('Period dates must be within the fiscal year.'))
        
        return cleaned_data 