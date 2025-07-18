from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from core.models import Empresa, Branch, UsuarioExtendido


class Report(models.Model):
    """Modelo principal de reportes"""
    
    # Campos básicos
    name = models.CharField(_('Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    
    # Relaciones con core (siguiendo patrón Synap)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, verbose_name=_('Company'))
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, verbose_name=_('Branch'))
    created_by = models.ForeignKey(UsuarioExtendido, on_delete=models.CASCADE, verbose_name=_('Created by'))
    
    # Timestamps
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated at'), auto_now=True)
    
    # Configuración del reporte
    template = models.ForeignKey('ReportTemplate', on_delete=models.CASCADE, verbose_name=_('Template'))
    layout_config = models.JSONField(_('Layout Configuration'), default=dict)
    data_sources = models.JSONField(_('Data Sources'), default=list)
    filters = models.JSONField(_('Filters'), default=dict)
    branding = models.JSONField(_('Branding'), default=dict)
    
    # Estados
    is_active = models.BooleanField(_('Active'), default=True)
    is_public = models.BooleanField(_('Public'), default=False)
    
    class Meta:
        verbose_name = _('Report')
        verbose_name_plural = _('Reports')
        ordering = ['-created_at']
        # Los permisos de reportes se gestionan vía core/constantes_permisos.py siguiendo la lógica de core.
    
    def __str__(self):
        return f"{self.name} - {self.empresa.name}"


class ReportTemplate(models.Model):
    """Templates de reportes"""
    
    # Relaciones con core (siguiendo patrón Synap)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, verbose_name=_('Company'))
    
    name = models.CharField(_('Name'), max_length=200)
    description = models.TextField(_('Description'), blank=True)
    category = models.CharField(_('Category'), max_length=100)  # sales, inventory, accounting, etc.
    
    # Configuración
    layout_schema = models.JSONField(_('Layout Schema'))
    default_data = models.JSONField(_('Default Data'), default=dict)
    styling = models.JSONField(_('Styling'), default=dict)
    
    # Metadata
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    is_system = models.BooleanField(_('System Template'), default=False)
    version = models.CharField(_('Version'), max_length=20, default='1.0.0')
    is_active = models.BooleanField(_('Active'), default=True)
    
    class Meta:
        verbose_name = _('Report Template')
        verbose_name_plural = _('Report Templates')
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.category}) - {self.empresa.name}"


class ReportComponent(models.Model):
    """Componentes de reportes"""
    
    COMPONENT_TYPES = [
        ('chart', _('Chart')),
        ('table', _('Table')),
        ('kpi', _('KPI')),
        ('text', _('Text')),
        ('image', _('Image')),
        ('header', _('Header')),
        ('footer', _('Footer')),
    ]
    
    name = models.CharField(_('Name'), max_length=200)
    component_type = models.CharField(_('Component Type'), max_length=20, choices=COMPONENT_TYPES)
    configuration = models.JSONField(_('Configuration'))
    data_source = models.CharField(_('Data Source'), max_length=200, blank=True)
    styling = models.JSONField(_('Styling'), default=dict)
    
    # Posición y tamaño
    position = models.JSONField(_('Position'))  # {x, y, width, height}
    z_index = models.IntegerField(_('Z-Index'), default=0)
    
    # Relaciones
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='components', verbose_name=_('Report'))
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Parent'))
    
    class Meta:
        verbose_name = _('Report Component')
        verbose_name_plural = _('Report Components')
        ordering = ['z_index', 'id']
    
    def __str__(self):
        return f"{self.name} ({self.get_component_type_display()})"


class ReportSchedule(models.Model):
    """Programación de reportes"""
    
    FREQUENCY_CHOICES = [
        ('daily', _('Daily')),
        ('weekly', _('Weekly')),
        ('monthly', _('Monthly')),
        ('quarterly', _('Quarterly')),
        ('yearly', _('Yearly')),
        ('custom', _('Custom')),
    ]
    
    report = models.ForeignKey(Report, on_delete=models.CASCADE, verbose_name=_('Report'))
    name = models.CharField(_('Name'), max_length=200)
    frequency = models.CharField(_('Frequency'), max_length=20, choices=FREQUENCY_CHOICES)
    cron_expression = models.CharField(_('Cron Expression'), max_length=200, blank=True)
    
    # Configuración de envío
    recipients = models.JSONField(_('Recipients'))  # Lista de emails
    export_format = models.CharField(_('Export Format'), max_length=10, default='pdf')
    subject_template = models.CharField(_('Subject Template'), max_length=200)
    message_template = models.TextField(_('Message Template'), blank=True)
    
    # Estados
    is_active = models.BooleanField(_('Active'), default=True)
    last_run = models.DateTimeField(_('Last Run'), null=True, blank=True)
    next_run = models.DateTimeField(_('Next Run'), null=True, blank=True)
    
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Report Schedule')
        verbose_name_plural = _('Report Schedules')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.report.name}"


class ReportExport(models.Model):
    """Exportaciones de reportes"""
    
    EXPORT_FORMATS = [
        ('pdf', 'PDF'),
        ('excel', 'Excel'),
        ('csv', 'CSV'),
        ('pptx', 'PowerPoint'),
        ('html', 'HTML'),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('processing', _('Processing')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
    ]
    
    report = models.ForeignKey(Report, on_delete=models.CASCADE, verbose_name=_('Report'))
    export_format = models.CharField(_('Export Format'), max_length=10, choices=EXPORT_FORMATS)
    file_path = models.CharField(_('File Path'), max_length=500, blank=True)
    file_size = models.IntegerField(_('File Size'), null=True, blank=True)
    
    # Configuración de exportación
    export_config = models.JSONField(_('Export Configuration'), default=dict)
    branding_config = models.JSONField(_('Branding Configuration'), default=dict)
    
    # Estados
    status = models.CharField(_('Status'), max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(_('Error Message'), blank=True)
    
    # Timestamps
    export_date = models.DateTimeField(_('Export Date'), auto_now_add=True)
    created_at = models.DateTimeField(_('Created at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('Report Export')
        verbose_name_plural = _('Report Exports')
        ordering = ['-export_date']
    
    def __str__(self):
        return f"{self.report.name} - {self.get_export_format_display()} ({self.get_status_display()})" 