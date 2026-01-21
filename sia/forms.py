"""
Formularios para el módulo Strategic Insights & Alignment (SIA)
"""
from django import forms
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, HTML
from sia.models import (
    Department,
    EvaluationCycle,
    StrategicSurveyResponse,
    FodaItem,
    Rating,
    OpenAnswer,
    CameAction,
)
from core.models import Empresa, UsuarioExtendido


class DepartmentForm(forms.ModelForm):
    """Formulario para Department."""
    
    class Meta:
        model = Department
        # Empresa NO está en los campos editables - se asigna automáticamente desde el contexto
        fields = ['name', 'code', 'description', 'is_active']
        labels = {
            'name': 'Nombre del Departamento',
            'code': 'Código',
            'description': 'Descripción',
            'is_active': 'Activo',
        }
        help_texts = {
            'name': 'Nombre del departamento o área organizacional (ej: Ventas, Marketing, IT, RRHH)',
            'code': 'Código interno opcional para identificar el departamento',
            'description': 'Descripción opcional del departamento',
            'is_active': 'Indica si el departamento está activo y disponible para asignación',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'placeholder': 'Ej: Ventas, Marketing, IT'}),
            'code': forms.TextInput(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'placeholder': 'Opcional'}),
            'description': forms.Textarea(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'rows': 3, 'placeholder': 'Descripción del departamento...'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded dark:bg-gray-700 dark:border-gray-600'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='w-full md:w-2/3'),
                Column('code', css_class='w-full md:w-1/3'),
            ),
            'description',
            'is_active',
        )


class EvaluationCycleForm(forms.ModelForm):
    """Formulario para EvaluationCycle."""
    
    class Meta:
        model = EvaluationCycle
        # Empresa NO está en los campos editables - se asigna automáticamente desde el contexto
        fields = ['name', 'description', 'start_date', 'end_date', 'is_active']
        labels = {
            'name': 'Nombre del Ciclo',
            'description': 'Descripción',
            'start_date': 'Fecha de Inicio',
            'end_date': 'Fecha de Fin',
            'is_active': 'Activo',
        }
        help_texts = {
            'name': 'Nombre del ciclo de evaluación (ej: "Q1 2024", "Anual 2024")',
            'description': 'Descripción opcional del ciclo de evaluación',
            'start_date': 'Fecha de inicio del ciclo de evaluación',
            'end_date': 'Fecha de fin del ciclo de evaluación',
            'is_active': 'Indica si este ciclo está activo y acepta respuestas de los directivos',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500'}),
            'description': forms.Textarea(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'rows': 3}),
            'start_date': forms.DateInput(attrs={'type': 'date', 'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'id': 'id_start_date'}),
            'end_date': forms.DateInput(attrs={'type': 'date', 'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'id': 'id_end_date'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-orange-600 rounded focus:ring-orange-500'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # No usar helper de crispy-forms con layout personalizado
        # El template renderizará los campos manualmente con as_crispy_field
        self.helper = FormHelper()
        self.helper.form_tag = False  # No renderizar el tag <form>
    
    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError('La fecha de inicio debe ser anterior a la fecha de fin.')
        
        return cleaned_data


class FodaItemForm(forms.ModelForm):
    """Formulario para FodaItem (usado en formsets)."""
    
    class Meta:
        model = FodaItem
        fields = ['quadrant', 'description', 'priority']
        labels = {
            'quadrant': 'Cuadrante',
            'description': 'Descripción',
            'priority': 'Prioridad',
        }
        help_texts = {
            'quadrant': 'Selecciona el cuadrante FODA al que pertenece este elemento',
            'description': 'Descripción detallada del elemento FODA',
            'priority': 'Prioridad dentro del cuadrante (1-3, donde 1 es la más alta)',
        }
        widgets = {
            'quadrant': forms.Select(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500'}),
            'description': forms.Textarea(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'rows': 2, 'placeholder': 'Describe el elemento FODA...'}),
            'priority': forms.NumberInput(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'min': 1, 'max': 3}),
        }


class FodaItemFormSet(BaseInlineFormSet):
    """Formset para FodaItem con validación de máximo 3 items por cuadrante."""
    
    def clean(self):
        """Validar que no haya más de 3 items por cuadrante"""
        if any(self.errors):
            return
        
        # Contar items por cuadrante
        quadrant_counts = {}
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                quadrant = form.cleaned_data.get('quadrant')
                if quadrant:
                    quadrant_counts[quadrant] = quadrant_counts.get(quadrant, 0) + 1
        
        # Validar máximo 3 por cuadrante
        for quadrant, count in quadrant_counts.items():
            if count > 3:
                quadrant_display = dict(FodaItem.QUADRANT_CHOICES).get(quadrant, quadrant)
                # Traducir nombres de cuadrantes al español
                quadrant_es = {
                    'strength': 'Fortalezas',
                    'weakness': 'Debilidades',
                    'opportunity': 'Oportunidades',
                    'threat': 'Amenazas',
                }.get(quadrant, quadrant_display)
                raise forms.ValidationError(
                    f'Solo puedes agregar un máximo de 3 elementos para el cuadrante "{quadrant_es}". Tienes {count} elementos.'
                )


class RatingForm(forms.ModelForm):
    """Formulario para Rating (usado en formsets)."""
    
    class Meta:
        model = Rating
        fields = ['dimension', 'value', 'notes']
        labels = {
            'dimension': 'Dimensión',
            'value': 'Valor (1-10)',
            'notes': 'Notas',
        }
        help_texts = {
            'dimension': 'Dimensión estratégica que se está evaluando',
            'value': 'Valor del rating de 1 a 10 (donde 10 es el mejor)',
            'notes': 'Notas opcionales que explican el rating asignado',
        }
        widgets = {
            'dimension': forms.Select(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500'}),
            'value': forms.HiddenInput(),  # Se renderiza manualmente en el template con el slider
            'notes': forms.Textarea(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'rows': 2, 'placeholder': 'Explica el rating asignado...'}),
        }


class OpenAnswerForm(forms.ModelForm):
    """Formulario para OpenAnswer (usado en formsets)."""
    
    class Meta:
        model = OpenAnswer
        fields = ['question_type', 'question_text', 'answer']
        labels = {
            'question_type': 'Tipo de Pregunta',
            'question_text': 'Pregunta',
            'answer': 'Respuesta',
        }
        help_texts = {
            'question_type': 'Tipo de pregunta abierta que se está respondiendo',
            'question_text': 'Texto de la pregunta (puede personalizarse)',
            'answer': 'Respuesta detallada a la pregunta abierta',
        }
        widgets = {
            'question_type': forms.Select(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500'}),
            'question_text': forms.TextInput(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'placeholder': 'Ej: ¿Cuáles son las 3 prioridades críticas?'}),
            'answer': forms.Textarea(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500', 'rows': 3, 'placeholder': 'Escribe tu respuesta aquí...'}),
        }


class StrategicSurveyResponseForm(forms.ModelForm):
    """Formulario principal para StrategicSurveyResponse."""
    
    class Meta:
        model = StrategicSurveyResponse
        # evaluation_cycle NO está en fields - se asigna automáticamente desde la vista
        fields = ['department']
        labels = {
            'department': 'Departamento',
        }
        help_texts = {
            'department': 'Departamento o área del directivo (opcional)',
        }
        widgets = {
            'department': forms.Select(attrs={'class': 'text-xs border-gray-300 dark:border-gray-600 rounded-md dark:bg-gray-700 dark:text-gray-100 focus:ring-2 focus:ring-orange-500 focus:border-orange-500'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.empresa = kwargs.pop('empresa', None)
        self.evaluation_cycle = kwargs.pop('evaluation_cycle', None)
        super().__init__(*args, **kwargs)
        
        # Filtrar departments por empresa si se proporciona
        from sia.models import Department
        if self.empresa:
            self.fields['department'].queryset = Department.objects.filter(
                empresa=self.empresa,
                is_active=True
            ).order_by('name')
        else:
            self.fields['department'].queryset = Department.objects.filter(
                is_active=True
            ).order_by('name')
        
        # Personalizar cómo se muestra cada opción: solo el nombre, sin la empresa
        # Ya que el formulario está filtrado por empresa activa, no necesitamos mostrar la empresa
        def label_from_instance(obj):
            return obj.name
        
        self.fields['department'].label_from_instance = label_from_instance
        
        # Hacer department opcional
        self.fields['department'].required = False
        
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('evaluation_cycle', css_class='w-full md:w-1/2'),
                Column('department', css_class='w-full md:w-1/2'),
            ),
        )
    
    def clean(self):
        cleaned_data = super().clean()
        # La validación de department.empresa == evaluation_cycle.empresa
        # se hace en el método clean() del modelo
        return cleaned_data


# Formsets inline para StrategicSurveyResponse
# Nota: FodaItemFormSet (la clase) se define arriba, aquí creamos la factory
FodaItemFormSet = inlineformset_factory(
    StrategicSurveyResponse,
    FodaItem,
    form=FodaItemForm,
    formset=FodaItemFormSet,  # Usa la clase definida arriba
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)

RatingFormSet = inlineformset_factory(
    StrategicSurveyResponse,
    Rating,
    form=RatingForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)

OpenAnswerFormSet = inlineformset_factory(
    StrategicSurveyResponse,
    OpenAnswer,
    form=OpenAnswerForm,
    extra=1,
    can_delete=True,
    min_num=0,
    validate_min=False,
)


class CameActionForm(forms.ModelForm):
    """Formulario para CameAction."""
    
    class Meta:
        model = CameAction
        fields = [
            'evaluation_cycle', 'action_type', 'title', 'description',
            'related_foda_item', 'priority', 'status', 'assigned_to', 'due_date'
        ]
        widgets = {
            'evaluation_cycle': forms.Select(attrs={'class': 'text-xs border-gray-300 rounded-md'}),
            'action_type': forms.Select(attrs={'class': 'text-xs border-gray-300 rounded-md'}),
            'title': forms.TextInput(attrs={'class': 'text-xs border-gray-300 rounded-md'}),
            'description': forms.Textarea(attrs={'class': 'text-xs border-gray-300 rounded-md', 'rows': 4}),
            'related_foda_item': forms.Select(attrs={'class': 'text-xs border-gray-300 rounded-md'}),
            'priority': forms.NumberInput(attrs={'class': 'text-xs border-gray-300 rounded-md', 'min': 1, 'max': 5}),
            'status': forms.Select(attrs={'class': 'text-xs border-gray-300 rounded-md'}),
            'assigned_to': forms.Select(attrs={'class': 'text-xs border-gray-300 rounded-md'}),
            'due_date': forms.DateInput(attrs={'type': 'date', 'class': 'text-xs border-gray-300 rounded-md'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('evaluation_cycle', css_class='w-full md:w-1/2'),
                Column('action_type', css_class='w-full md:w-1/2'),
            ),
            'title',
            'description',
            Row(
                Column('related_foda_item', css_class='w-full md:w-1/2'),
                Column('priority', css_class='w-full md:w-1/4'),
                Column('status', css_class='w-full md:w-1/4'),
            ),
            Row(
                Column('assigned_to', css_class='w-full md:w-1/2'),
                Column('due_date', css_class='w-full md:w-1/2'),
            ),
        )

