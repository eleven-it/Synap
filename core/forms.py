from django import forms
from .models import UsuarioExtendido, Rol, Permiso, UnitOfMeasure, Currency, ExchangeRate, SystemConfiguration, Contact, ContactRelationship
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext_lazy as _

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

class ContactInlineForm(forms.ModelForm):
    """
    Formulario inline para gestionar contactos relacionados
    Similar al comportamiento de Odoo v18
    """
    
    # Campos adicionales para la relación
    relationship_type = forms.ChoiceField(
        choices=ContactRelationship.RELATIONSHIP_TYPES,
        initial='secondary',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_active = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    notes = forms.CharField(
        max_length=500,
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Notes about this relationship...')})
    )
    
    # Campos para crear nuevo contacto
    create_new = forms.BooleanField(
        initial=False,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    class Meta:
        model = Contact
        fields = [
            'name', 'type', 'first_name', 'last_name', 'company_name',
            'position', 'department', 'email', 'phone', 'mobile', 'fax',
            'website', 'address', 'postal_code', 'city', 'state', 'country'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Contact name')}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('First name')}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Last name')}),
            'company_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Company name')}),
            'position': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Job title')}),
            'department': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Department')}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': _('Email address')}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Phone number')}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Mobile number')}),
            'fax': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Fax number')}),
            'website': forms.URLInput(attrs={'class': 'form-control', 'placeholder': _('Website URL')}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': _('Address')}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Postal code')}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('City')}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('State/Province')}),
            'country': forms.TextInput(attrs={'class': 'form-control', 'placeholder': _('Country')}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Hacer algunos campos opcionales cuando se usa inline
        self.fields['name'].required = False
        self.fields['email'].required = False
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Si se está creando un nuevo contacto, validar campos requeridos
        if cleaned_data.get('create_new'):
            if not cleaned_data.get('name') and not (cleaned_data.get('first_name') or cleaned_data.get('last_name')):
                raise forms.ValidationError(_('Contact must have a name or first/last name.'))
            
            if not any([cleaned_data.get('email'), cleaned_data.get('phone'), cleaned_data.get('mobile')]):
                raise forms.ValidationError(_('Contact must have at least one contact method.'))
        
        return cleaned_data


class ContactRelationshipFormSet(forms.BaseInlineFormSet):
    """
    FormSet para gestionar múltiples contactos relacionados
    """
    
    def clean(self):
        super().clean()
        
        # Validar que al menos haya un contacto
        if not any(form.cleaned_data and not form.cleaned_data.get('DELETE', False) for form in self.forms):
            raise forms.ValidationError(_('At least one contact is required.'))
        
        # Validar que no haya contactos duplicados
        contacts = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                contact_id = form.cleaned_data.get('id')
                if contact_id:
                    contacts.append(contact_id)
        
        if len(contacts) != len(set(contacts)):
            raise forms.ValidationError(_('Duplicate contacts are not allowed.'))


def get_contact_formset(instance=None, data=None, files=None, prefix='contacts'):
    """
    Factory function para crear el formset de contactos
    """
    from django.forms import inlineformset_factory
    
    ContactFormSet = inlineformset_factory(
        parent_model=Contact,  # Modelo padre (se usará para la relación)
        model=ContactRelationship,
        form=ContactInlineForm,
        formset=ContactRelationshipFormSet,
        extra=1,  # Un formulario extra para agregar nuevos
        can_delete=True,
        fields=['contact', 'relationship_type', 'is_active', 'notes'],
        exclude=['content_type', 'object_id']
    )
    
    return ContactFormSet(instance=instance, data=data, files=files, prefix=prefix)


def get_contact_inline_formset(parent_model, instance=None, data=None, files=None, prefix='contacts'):
    """
    Factory function para crear un formset inline de contactos para cualquier modelo padre
    """
    from django.forms import inlineformset_factory
    
    ContactInlineFormSet = inlineformset_factory(
        parent_model=parent_model,
        model=ContactRelationship,
        form=ContactInlineForm,
        formset=ContactRelationshipFormSet,
        extra=1,
        can_delete=True,
        fields=['contact', 'relationship_type', 'is_active', 'notes'],
        exclude=['content_type', 'object_id']
    )
    
    return ContactInlineFormSet(instance=instance, data=data, files=files, prefix=prefix) 