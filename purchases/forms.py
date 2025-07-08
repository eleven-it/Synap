from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Supplier


class SupplierForm(forms.ModelForm):
    """
    Formulario para crear y editar proveedores
    Siguiendo las reglas de UX/UI e internacionalización
    """
    
    class Meta:
        model = Supplier
        fields = [
            'name', 'code', 'tax_id', 'contact_person', 'email', 'phone', 'mobile',
            'address', 'city', 'state', 'postal_code', 'country',
            'payment_terms', 'credit_limit', 'currency',
            'supplier_category', 'supplier_type',
            'tax_category', 'is_tax_exempt',
            'is_active', 'is_approved', 'notes', 'website'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter supplier name'),
                'autocomplete': 'organization'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter supplier code'),
                'autocomplete': 'off'
            }),
            'tax_id': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter tax ID or VAT number'),
                'pattern': '[A-Z0-9\-\.]+',
                'title': _('Enter a valid tax ID or VAT number')
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter contact person name'),
                'autocomplete': 'name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter email address'),
                'autocomplete': 'email'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter phone number'),
                'autocomplete': 'tel'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter mobile number'),
                'autocomplete': 'tel'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Enter complete address'),
                'autocomplete': 'street-address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter city'),
                'autocomplete': 'address-level2'
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter state/province'),
                'autocomplete': 'address-level1'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter postal code'),
                'autocomplete': 'postal-code'
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter country'),
                'autocomplete': 'country-name'
            }),
            'payment_terms': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('e.g., Net 30, Net 60')
            }),
            'credit_limit': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.01',
                'min': '0',
                'placeholder': _('Enter credit limit')
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select'
            }),
            'supplier_category': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('e.g., Raw Materials, Services, Equipment')
            }),
            'supplier_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'tax_category': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Category for tax calculation')
            }),
            'is_tax_exempt': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'is_approved': forms.CheckboxInput(attrs={
                'class': 'form-checkbox'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 4,
                'placeholder': _('Enter additional notes about this supplier')
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter website URL'),
                'autocomplete': 'url'
            }),
        }
        labels = {
            'name': _('Supplier Name'),
            'code': _('Supplier Code'),
            'tax_id': _('Tax ID / VAT'),
            'contact_person': _('Contact Person'),
            'email': _('Email Address'),
            'phone': _('Phone Number'),
            'mobile': _('Mobile Number'),
            'address': _('Address'),
            'city': _('City'),
            'state': _('State/Province'),
            'postal_code': _('Postal Code'),
            'country': _('Country'),
            'payment_terms': _('Payment Terms'),
            'credit_limit': _('Credit Limit'),
            'currency': _('Default Currency'),
            'supplier_category': _('Category'),
            'supplier_type': _('Type'),
            'tax_category': _('Tax Category'),
            'is_tax_exempt': _('Tax Exempt'),
            'is_active': _('Active'),
            'is_approved': _('Approved'),
            'notes': _('Notes'),
            'website': _('Website'),
        }
        help_texts = {
            'name': _('Enter the complete name of the supplier company'),
            'code': _('Internal code to identify this supplier'),
            'tax_id': _('Enter the tax identification number or VAT number'),
            'contact_person': _('Primary contact person name'),
            'email': _('Primary email address for communications'),
            'phone': _('Primary phone number for contact'),
            'mobile': _('Mobile number for urgent contact'),
            'address': _('Complete address including street, city, state, and postal code'),
            'city': _('City where the supplier is located'),
            'state': _('State or province'),
            'postal_code': _('Postal or ZIP code'),
            'country': _('Country where the supplier is located'),
            'payment_terms': _('Payment terms agreed with this supplier'),
            'credit_limit': _('Maximum credit limit for this supplier'),
            'currency': _('Default currency for transactions with this supplier'),
            'supplier_category': _('Category to classify this supplier'),
            'supplier_type': _('Type of supplier business'),
            'tax_category': _('Tax category for calculation purposes'),
            'is_tax_exempt': _('Check if this supplier is tax exempt'),
            'is_active': _('Check if this supplier is currently active'),
            'is_approved': _('Check if this supplier has been approved'),
            'notes': _('Additional notes or comments about this supplier'),
            'website': _('Official website of the supplier'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Aplicar clases CSS adicionales para campos requeridos
        for field_name, field in self.fields.items():
            if field.required:
                field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' required-field'
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validaciones personalizadas
        name = cleaned_data.get('name')
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        mobile = cleaned_data.get('mobile')
        
        # Validar que tenga al menos un método de contacto
        if not any([email, phone, mobile]):
            raise forms.ValidationError(_('Supplier must have at least one contact method (email, phone, or mobile).'))
        
        # Validar que el nombre no esté vacío
        if name and len(name.strip()) < 2:
            raise forms.ValidationError(_('Supplier name must be at least 2 characters long.'))
        
        return cleaned_data 