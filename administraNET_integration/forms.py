from django import forms
from django.utils.translation import gettext_lazy as _
from administraNET_integration.models import TableMapping
import json

class TableMappingForm(forms.ModelForm):
    # Campos para mapeo visual
    preset_mapping_type = forms.ChoiceField(
        choices=[],
        required=False,
        label=_('Tipo de Mapeo Predefinido'),
        help_text=_('Seleccionar un tipo predefinido para configurar automáticamente')
    )
    
    # Campos para mapeo de campos específicos
    field_mappings_json = forms.CharField(
        widget=forms.HiddenInput(),
        required=False,
        label=_('Mapeo de Campos (JSON)')
    )
    
    class Meta:
        model = TableMapping
        fields = [
            'mapping_type', 'administraNET_table', 'synap_model', 'is_active', 'sync_direction', 'sync_frequency', 'use_preset_mapping'
        ]
        widgets = {
            'mapping_type': forms.Select(attrs={
                'class': 'text-xs p-2 rounded border-gray-300 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all font-sans',
                'onchange': 'updatePresetOptions()'
            }),
            'administraNET_table': forms.TextInput(attrs={
                'class': 'text-xs p-2 rounded border-gray-300 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all font-sans',
                'placeholder': _('ej: clientes')
            }),
            'synap_model': forms.TextInput(attrs={
                'class': 'text-xs p-2 rounded border-gray-300 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all font-sans',
                'placeholder': _('ej: sales.Client')
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
            }),
            'sync_direction': forms.Select(attrs={
                'class': 'text-xs p-2 rounded border-gray-300 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all font-sans'
            }),
            'sync_frequency': forms.NumberInput(attrs={
                'class': 'text-xs p-2 rounded border-gray-300 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all font-sans',
                'min': '1',
                'max': '1440'
            }),
            'use_preset_mapping': forms.CheckboxInput(attrs={
                'class': 'form-checkbox h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded',
                'onchange': 'togglePresetFields()'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar opciones de mapeo predefinido
        preset_choices = [('', _('-- Seleccionar tipo predefinido --'))]
        presets = TableMapping.get_preset_mappings()
        
        for mapping_type, preset in presets.items():
            preset_choices.append((
                mapping_type,
                f"{dict(TableMapping.MAPPING_TYPES)[mapping_type]} ({preset['table']} → {preset['model']})"
            ))
        
        self.fields['preset_mapping_type'].choices = preset_choices
        
        # Si es una instancia existente, configurar valores
        if self.instance and self.instance.pk:
            if self.instance.use_preset_mapping:
                self.fields['preset_mapping_type'].initial = self.instance.mapping_type
            
            # Convertir field_mappings a JSON para el campo oculto
            if self.instance.field_mappings:
                self.fields['field_mappings_json'].initial = json.dumps(
                    self.instance.field_mappings, indent=2
                )
    
    def clean(self):
        cleaned_data = super().clean()
        
        use_preset = cleaned_data.get('use_preset_mapping', False)
        preset_type = cleaned_data.get('preset_mapping_type')
        mapping_type = cleaned_data.get('mapping_type')
        
        if use_preset and preset_type:
            # Usar configuración predefinida
            presets = TableMapping.get_preset_mappings()
            preset = presets[preset_type]
            
            cleaned_data['mapping_type'] = preset_type
            cleaned_data['administraNET_table'] = preset['table']
            cleaned_data['synap_model'] = preset['model']
            cleaned_data['field_mappings'] = preset['fields']
            
        else:
            # Validar campos personalizados
            administraNET_table = cleaned_data.get('administraNET_table')
            synap_model = cleaned_data.get('synap_model')
            
            if not administraNET_table:
                raise forms.ValidationError(_('Debe especificar el nombre de la tabla de administraNET.'))
            
            if not synap_model:
                raise forms.ValidationError(_('Debe especificar el modelo de Synap.'))
            
            # Validar JSON de mapeo de campos
            field_mappings_json = cleaned_data.get('field_mappings_json')
            if field_mappings_json:
                try:
                    field_mappings = json.loads(field_mappings_json)
                    if not isinstance(field_mappings, dict):
                        raise ValueError()
                    cleaned_data['field_mappings'] = field_mappings
                except (json.JSONDecodeError, ValueError):
                    raise forms.ValidationError(_('El mapeo de campos debe ser un JSON válido.'))
            else:
                cleaned_data['field_mappings'] = {}
        
        return cleaned_data
    
    def clean_field_mappings_json(self):
        """Validar JSON de mapeo de campos"""
        data = self.cleaned_data.get('field_mappings_json')
        if data:
            try:
                field_mappings = json.loads(data)
                if not isinstance(field_mappings, dict):
                    raise forms.ValidationError(_('El mapeo de campos debe ser un diccionario válido.'))
                return data
            except json.JSONDecodeError:
                raise forms.ValidationError(_('El mapeo de campos debe ser un JSON válido.'))
        return data


class FieldMappingForm(forms.Form):
    """Formulario para mapeo individual de campos"""
    admin_field = forms.CharField(
        max_length=255,
        label=_('Campo administraNET'),
        widget=forms.TextInput(attrs={
            'class': 'text-xs p-2 rounded border-gray-300 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all font-sans',
            'placeholder': _('ej: nombre_cliente')
        })
    )
    
    synap_field = forms.CharField(
        max_length=255,
        label=_('Campo Synap'),
        widget=forms.TextInput(attrs={
            'class': 'text-xs p-2 rounded border-gray-300 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all font-sans',
            'placeholder': _('ej: name')
        })
    )
    
    field_type = forms.ChoiceField(
        choices=[
            ('text', _('Texto')),
            ('number', _('Número')),
            ('date', _('Fecha')),
            ('boolean', _('Booleano')),
            ('decimal', _('Decimal')),
            ('email', _('Email')),
            ('phone', _('Teléfono')),
            ('url', _('URL')),
        ],
        label=_('Tipo de Campo'),
        widget=forms.Select(attrs={
            'class': 'text-xs p-2 rounded border-gray-300 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all font-sans'
        })
    )
    
    required = forms.BooleanField(
        required=False,
        label=_('Requerido'),
        widget=forms.CheckboxInput(attrs={
            'class': 'form-checkbox h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded'
        })
    )
    
    description = forms.CharField(
        max_length=255,
        required=False,
        label=_('Descripción'),
        widget=forms.TextInput(attrs={
            'class': 'text-xs p-2 rounded border-gray-300 dark:border-neutral-700 bg-gray-50 dark:bg-neutral-800 focus:ring-2 focus:ring-blue-400 focus:border-blue-400 transition-all font-sans',
            'placeholder': _('Descripción opcional del campo')
        })
    ) 