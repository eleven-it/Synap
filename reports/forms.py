from django import forms
from django.utils.translation import gettext_lazy as _
from .models import Report, ReportTemplate, ReportSchedule, ReportComponent


class ReportForm(forms.ModelForm):
    """
    Formulario para crear y editar reportes
    """
    class Meta:
        model = Report
        fields = ['name', 'description', 'template', 'is_active', 'is_public']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter report name')
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'rows': 3,
                'placeholder': _('Enter report description')
            }),
            'template': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded'
            }),
            'is_public': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded'
            }),
        }
        labels = {
            'name': _('Report Name'),
            'description': _('Description'),
            'template': _('Template'),
            'is_active': _('Active'),
            'is_public': _('Public'),
        }
        help_texts = {
            'name': _('Enter a descriptive name for your report'),
            'description': _('Optional description of the report'),
            'template': _('Select a template to get started'),
            'is_active': _('Active reports can be used and scheduled'),
            'is_public': _('Public reports can be accessed by other users'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar plantillas por empresa si el usuario está autenticado
        if hasattr(self, 'user') and self.user.is_authenticated:
            self.fields['template'].queryset = ReportTemplate.objects.filter(
                empresa=self.user.empresa
            )


class ReportTemplateForm(forms.ModelForm):
    """
    Formulario para crear y editar plantillas de reportes
    """
    class Meta:
        model = ReportTemplate
        fields = ['name', 'description', 'category', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter template name')
            }),
            'description': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'rows': 3,
                'placeholder': _('Enter template description')
            }),
            'category': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded'
            }),
        }
        labels = {
            'name': _('Template Name'),
            'description': _('Description'),
            'category': _('Category'),
            'is_active': _('Active'),
        }
        help_texts = {
            'name': _('Enter a descriptive name for your template'),
            'description': _('Optional description of the template'),
            'category': _('Select the category for this template'),
            'is_active': _('Active templates can be used to create reports'),
        }


class ReportScheduleForm(forms.ModelForm):
    """
    Formulario para crear y editar programaciones de reportes
    """
    class Meta:
        model = ReportSchedule
        fields = ['name', 'report', 'frequency', 'next_run', 'recipients', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter schedule name')
            }),
            'report': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'frequency': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'next_run': forms.DateTimeInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'type': 'datetime-local'
            }),
            'recipients': forms.SelectMultiple(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-orange-600 focus:ring-orange-500 border-gray-300 rounded'
            }),
        }
        labels = {
            'name': _('Schedule Name'),
            'report': _('Report'),
            'frequency': _('Frequency'),
            'next_run': _('Next Run'),
            'recipients': _('Recipients'),
            'is_active': _('Active'),
        }
        help_texts = {
            'name': _('Enter a descriptive name for this schedule'),
            'report': _('Select the report to schedule'),
            'frequency': _('How often should this report be generated'),
            'next_run': _('When should the next report be generated'),
            'recipients': _('Who should receive this report'),
            'is_active': _('Active schedules will run automatically'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrar reportes por empresa si el usuario está autenticado
        if hasattr(self, 'user') and self.user.is_authenticated:
            self.fields['report'].queryset = Report.objects.filter(
                empresa=self.user.empresa,
                is_active=True
            )
            # Filtrar usuarios por empresa para destinatarios
            from core.models import UsuarioExtendido
            self.fields['recipients'].queryset = UsuarioExtendido.objects.filter(
                empresa=self.user.empresa
            )


class ReportComponentForm(forms.ModelForm):
    """
    Formulario para crear y editar componentes de reportes
    """
    class Meta:
        model = ReportComponent
        fields = ['name', 'component_type', 'configuration', 'data_source', 'styling', 'position', 'z_index']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter component name')
            }),
            'component_type': forms.Select(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white'
            }),
            'configuration': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'rows': 4,
                'placeholder': _('Enter component configuration (JSON)')
            }),
            'data_source': forms.TextInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'placeholder': _('Enter data source')
            }),
            'styling': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'rows': 3,
                'placeholder': _('Enter styling configuration (JSON)')
            }),
            'position': forms.Textarea(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'rows': 2,
                'placeholder': _('Enter position configuration (JSON: x, y, width, height)')
            }),
            'z_index': forms.NumberInput(attrs={
                'class': 'w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-orange-500 focus:border-orange-500 dark:bg-gray-700 dark:text-white',
                'min': 0
            }),
        }
        labels = {
            'name': _('Component Name'),
            'component_type': _('Component Type'),
            'configuration': _('Configuration'),
            'data_source': _('Data Source'),
            'styling': _('Styling'),
            'position': _('Position'),
            'z_index': _('Z-Index'),
        }
        help_texts = {
            'name': _('Enter a descriptive name for this component'),
            'component_type': _('Select the type of component'),
            'configuration': _('JSON configuration for the component'),
            'data_source': _('Data source for the component'),
            'styling': _('JSON styling configuration'),
            'position': _('Position and size configuration (JSON)'),
            'z_index': _('Display order in the report'),
        }

    def clean_configuration(self):
        """
        Validar que la configuración sea JSON válido
        """
        import json
        config = self.cleaned_data.get('configuration')
        if config:
            try:
                json.loads(config)
            except json.JSONDecodeError:
                raise forms.ValidationError(_('Invalid JSON configuration'))
        return config

    def clean_styling(self):
        """
        Validar que el styling sea JSON válido
        """
        import json
        styling = self.cleaned_data.get('styling')
        if styling:
            try:
                json.loads(styling)
            except json.JSONDecodeError:
                raise forms.ValidationError(_('Invalid JSON styling'))
        return styling

    def clean_position(self):
        """
        Validar que la posición sea JSON válido
        """
        import json
        position = self.cleaned_data.get('position')
        if position:
            try:
                json.loads(position)
            except json.JSONDecodeError:
                raise forms.ValidationError(_('Invalid JSON position'))
        return position 