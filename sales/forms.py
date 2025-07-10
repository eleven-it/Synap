from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from .models import Client, VATValidator
from core.models import Contact, Country, State


class ClientForm(forms.ModelForm):
    """Formulario para crear/editar clientes"""
    
    # Campos adicionales para autocompletado
    country_name = forms.CharField(
        max_length=100, 
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Start typing country name...'),
            'data-autocomplete': 'country'
        }),
        label=_('Country (autocomplete)')
    )
    
    state_name = forms.CharField(
        max_length=100, 
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Start typing state/province name...'),
            'data-autocomplete': 'state'
        }),
        label=_('State/Province (autocomplete)')
    )
    
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


class ContactForm(forms.ModelForm):
    """Formulario para crear/editar contactos"""
    
    # Campos adicionales para autocompletado
    country_name = forms.CharField(
        max_length=100, 
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'data-autocomplete': 'country'
        }),
        label=_('Country (autocomplete)')
    )
    
    state_name = forms.CharField(
        max_length=100, 
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'data-autocomplete': 'state'
        }),
        label=_('State/Province (autocomplete)')
    )
    
    class Meta:
        model = Contact
        fields = [
            'name', 'type', 'first_name', 'last_name', 'company_name', 
            'position', 'department', 'email', 'phone', 'mobile', 'fax', 
            'website', 'address', 'postal_code', 'city', 'state', 'country',
            'latitude', 'longitude', 'notes', 'tags', 'photo', 'is_active', 
            'is_primary'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Enter contact name...')
            }),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'first_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('First name...')
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Last name...')
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Company name...')
            }),
            'position': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Job title...')
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Department...')
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-input',
                'placeholder': _('contact@example.com')
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('+1 234 567 8900')
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('+1 234 567 8900')
            }),
            'fax': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Fax number...')
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-input',
                'placeholder': _('https://www.example.com')
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Enter address...')
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('12345')
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('City...')
            }),
            'state': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('State/Province...')
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('Country...')
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.000001',
                'placeholder': _('e.g., -34.6037')
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'form-input',
                'step': '0.000001',
                'placeholder': _('e.g., -58.3816')
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-textarea',
                'rows': 3,
                'placeholder': _('Enter notes...')
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': _('tag1, tag2, tag3...')
            }),
            'photo': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
            'is_primary': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validar que tenga al menos un método de contacto
        email = cleaned_data.get('email')
        phone = cleaned_data.get('phone')
        mobile = cleaned_data.get('mobile')
        
        if not email and not phone and not mobile:
            raise ValidationError(
                _('Contact must have at least one contact method (email, phone, or mobile).')
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
            ('government', _('Government')),
            ('non_profit', _('Non-profit'))
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Type')
    )
    
    country = forms.ModelChoiceField(
        queryset=Country.objects.filter(is_active=True).order_by('name'),
        required=False,
        empty_label=_('All countries'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Country')
    )
    
    state = forms.ModelChoiceField(
        queryset=State.objects.none(),  # Se llenará dinámicamente
        required=False,
        empty_label=_('All states/provinces'),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('State/Province')
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
    
    is_supplier = forms.ChoiceField(
        choices=[
            ('', _('All')),
            ('True', _('Suppliers only')),
            ('False', _('Non-suppliers only'))
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label=_('Supplier')
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
    
    assigned_seller = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': _('Filter by assigned seller...')
        }),
        label=_('Assigned Seller')
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Si hay un país seleccionado, llenar los estados
        if 'country' in self.data and self.data['country']:
            try:
                country_id = int(self.data['country'])
                self.fields['state'].queryset = State.objects.filter(
                    country_id=country_id,
                    is_active=True
                ).order_by('name')
            except (ValueError, TypeError):
                pass 