"""
Formularios para el módulo Reports AI
"""
from django import forms
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Row, Column, Submit, HTML
from .models import BusinessRule, GlossaryTerm, FunctionalCatalog


class BusinessRuleSearchForm(forms.Form):
    """Formulario de búsqueda de Business Rules"""
    search = forms.CharField(required=False, max_length=200)
    category = forms.CharField(required=False, max_length=100)
    module = forms.CharField(required=False, max_length=100)
    is_active = forms.ChoiceField(required=False, choices=[('', 'Todos'), ('true', 'Activos'), ('false', 'Inactivos')])


class BusinessRuleImportForm(forms.Form):
    """Formulario para importar Business Rules desde CSV"""
    file = forms.FileField(label='Archivo CSV')


class BusinessRuleBulkActionForm(forms.Form):
    """Formulario para acciones en lote sobre Business Rules"""
    action = forms.ChoiceField(choices=[
        ('activate', 'Activar'),
        ('deactivate', 'Desactivar'),
        ('delete', 'Eliminar')
    ])
    selected_ids = forms.CharField(widget=forms.HiddenInput())


class BusinessRuleForm(forms.ModelForm):
    """Formulario para crear/editar Business Rules"""
    
    class Meta:
        model = BusinessRule
        fields = [
            'module', 'name', 'description', 'category',
            'source_file', 'source_function', 'source_line',
            'business_procedure', 'priority', 'is_active',
            'tags', 'conditions', 'actions'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control text-xs'}),
            'business_procedure': forms.Textarea(attrs={'rows': 10, 'class': 'form-control text-xs font-mono'}),
            'conditions': forms.Textarea(attrs={'rows': 3, 'class': 'form-control text-xs'}),
            'actions': forms.Textarea(attrs={'rows': 3, 'class': 'form-control text-xs'}),
            'tags': forms.TextInput(attrs={'class': 'form-control text-xs', 'placeholder': 'ventas,pedido,cliente'}),
            'module': forms.TextInput(attrs={'class': 'form-control text-xs'}),
            'name': forms.TextInput(attrs={'class': 'form-control text-xs'}),
            'category': forms.Select(attrs={'class': 'form-control text-xs'}),
            'source_file': forms.TextInput(attrs={'class': 'form-control text-xs'}),
            'source_function': forms.TextInput(attrs={'class': 'form-control text-xs'}),
            'source_line': forms.NumberInput(attrs={'class': 'form-control text-xs'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control text-xs', 'min': 1, 'max': 10}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Marcar campos opcionales
        self.fields['source_file'].required = False
        self.fields['source_function'].required = False
        self.fields['source_line'].required = False
        self.fields['business_procedure'].required = False
        self.fields['conditions'].required = False
        self.fields['actions'].required = False


class GlossaryTermForm(forms.ModelForm):
    """Formulario para crear/editar términos del glosario"""
    
    class Meta:
        model = GlossaryTerm
        fields = [
            'term', 'definition', 'category', 'context',
            'synonyms', 'examples', 'is_active'
        ]
        widgets = {
            'term': forms.TextInput(attrs={'class': 'form-control text-xs'}),
            'definition': forms.Textarea(attrs={'rows': 4, 'class': 'form-control text-xs'}),
            'category': forms.TextInput(attrs={'class': 'form-control text-xs'}),
            'context': forms.TextInput(attrs={'class': 'form-control text-xs', 'placeholder': 'Contexto de uso'}),
            'synonyms': forms.Textarea(attrs={'rows': 2, 'class': 'form-control text-xs', 'placeholder': '["pedido", "orden", "compra"]'}),
            'examples': forms.Textarea(attrs={'rows': 3, 'class': 'form-control text-xs', 'placeholder': '["Ejemplo 1", "Ejemplo 2"]'}),
        }


class FunctionalCatalogForm(forms.ModelForm):
    """Formulario para crear/editar entradas del Catálogo Funcional"""
    
    class Meta:
        model = FunctionalCatalog
        fields = [
            'module', 'procedure', 'description',
            'vb6_forms', 'vb6_modules', 'php_scripts',
            'entities', 'candidate_tables', 'master_table', 'detail_table', 'key_fields',
            'relevant_events', 'business_rules', 'validations', 'dependencies',
            'table_relationships', 'insert_tables', 'update_tables',
            'confidence', 'priority', 'is_active', 'notes'
        ]
        widgets = {
            # Identificación
            'module': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: Ventas, Stock, Clientes'
            }),
            'procedure': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: Crear pedido, Guardar factura'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control text-xs',
                'placeholder': 'Descripción detallada del procedimiento'
            }),
            
            # Archivos fuente
            'vb6_forms': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: Pedido.frm, Pedido_Avanzado.frm'
            }),
            'vb6_modules': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: Funciones.bas, MStart.bas'
            }),
            'php_scripts': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: pedido_controller.php'
            }),
            
            # Modelo de negocio
            'entities': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: Pedido, Cliente, Articulo, Sucursal'
            }),
            'candidate_tables': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: comp_ped, cuerpostockpe, cliente, articulo'
            }),
            'master_table': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: comp_ped'
            }),
            'detail_table': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: cuerpostockpe'
            }),
            'key_fields': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: CodigoMovimiento, Codigo, IDArt, Total'
            }),
            
            # Lógica (se descubre automáticamente durante el entrenamiento)
            'relevant_events': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': '🤖 Se descubrirá automáticamente durante el entrenamiento'
            }),
            'business_rules': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control text-xs',
                'placeholder': '🤖 Se descubrirá automáticamente durante el entrenamiento'
            }),
            'validations': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control text-xs',
                'placeholder': '🤖 Se descubrirá automáticamente durante el entrenamiento'
            }),
            'dependencies': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: Presupuesto, Numeración, Stock'
            }),
            
            # Relaciones
            'table_relationships': forms.Textarea(attrs={
                'rows': 4,
                'class': 'form-control text-xs font-mono',
                'placeholder': '{"comp_ped.CodigoMovimiento": "cuerpostockpe.CodigoMovimiento"}'
            }),
            
            # Operaciones BD
            'insert_tables': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: comp_ped, cuerpostockpe, percep_cli'
            }),
            'update_tables': forms.TextInput(attrs={
                'class': 'form-control text-xs',
                'placeholder': 'Ej: codmov, stock_deposito, talonarios'
            }),
            
            # Metadata
            'confidence': forms.NumberInput(attrs={
                'class': 'form-control text-xs',
                'min': 0.0,
                'max': 1.0,
                'step': 0.01
            }),
            'priority': forms.NumberInput(attrs={
                'class': 'form-control text-xs',
                'min': 1,
                'max': 10
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control text-xs',
                'placeholder': 'Observaciones o comentarios adicionales'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Campos opcionales
        optional_fields = [
            'description', 'vb6_modules', 'php_scripts',
            'master_table', 'detail_table', 'relevant_events',
            'business_rules', 'validations', 'dependencies', 'table_relationships',
            'insert_tables', 'update_tables', 'notes'
        ]
        
        for field_name in optional_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False
        
        # Valores por defecto
        if not self.instance.pk:
            self.fields['confidence'].initial = 0.9
            self.fields['priority'].initial = 5
            self.fields['is_active'].initial = True
