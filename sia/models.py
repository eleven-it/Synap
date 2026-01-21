"""
Strategic Insights & Alignment (SIA) - Models

Este módulo captura percepciones estratégicas de directivos, consolida FODAs,
ratings y genera matrices CAME para análisis ejecutivo.

ARQUITECTURA DE BASES DE DATOS:
--------------------------------
- Todos los modelos de SIA se almacenan en PostgreSQL (base de datos 'default')
- Los modelos reutilizados (Empresa, UsuarioExtendido) también están en PostgreSQL
- MySQL (administraNET) se usa SOLO para autenticación y lectura de datos legacy,
  NO para almacenar modelos de Django

INTEGRACIÓN CON administraNET:
-------------------------------
- Los usuarios se autentican contra MySQL de administraNET (tabla 'usuarios')
- Los usuarios autenticados se mapean a UsuarioExtendido en PostgreSQL
- Las empresas se pueden sincronizar desde MySQL (tabla 'empresas') a Empresa en PostgreSQL
- Los roles y permisos de administraNET se pueden mapear a Rol y Permiso en PostgreSQL
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from core.models import Empresa, UsuarioExtendido


# ============================================================================
# MODELOS REUTILIZADOS (todos en PostgreSQL)
# ============================================================================
# 
# 1. EMPRESA: core.models.Empresa
#    - Ubicación: PostgreSQL (default)
#    - Uso en SIA: EvaluationCycle.empresa (ForeignKey)
#    - Justificación: Modelo troncal del sistema, representa empresas/clientes
#    - Puede sincronizarse desde MySQL (tabla 'empresas' de administraNET)
#    - NO se duplica: Es el único modelo de empresa en el proyecto
#
# 2. USUARIO: core.models.UsuarioExtendido
#    - Ubicación: PostgreSQL (default)
#    - Uso en SIA: 
#      * StrategicSurveyResponse.user (ForeignKey)
#      * EvaluationCycle.created_by (ForeignKey, opcional)
#      * CameAction.assigned_to (ForeignKey, opcional)
#      * CameAction.created_by (ForeignKey, opcional)
#    - Justificación: Modelo troncal del sistema, representa usuarios del sistema
#    - Se mapea desde usuarios de administraNET (MySQL) después de autenticación
#    - NO se duplica: Es el único modelo de usuario en el proyecto
#
# 3. ÁREA/DEPARTAMENTO: NO EXISTE modelo organizacional en el proyecto
#    - Modelos relacionados encontrados (NO son equivalentes):
#      * tiendanube_administranet.models.AdministraNETDepartamento
#        → Es GEOGRÁFICO (provincias/partidos), NO organizacional
#      * core.models.Contact.department
#        → Es solo un CharField (texto libre), NO un modelo relacionable
#    - Justificación para crear sia.Department:
#      * Necesitamos un modelo relacionable (ForeignKey) para áreas organizacionales
#      * Permite mantener integridad referencial y evitar duplicación de nombres
#      * Permite análisis por departamento en las evaluaciones estratégicas
#      * NO duplica nada existente porque no hay modelo organizacional en el proyecto
#


class Department(models.Model):
    """
    Modelo para representar áreas/departamentos organizacionales dentro de una empresa.
    
    JUSTIFICACIÓN DE CREACIÓN (NO duplica modelos existentes):
    -----------------------------------------------------------
    - AdministraNETDepartamento (tiendanube_administranet): Es GEOGRÁFICO (provincias/partidos)
    - Contact.department (core): Es solo CharField, no modelo relacionable
    - NO existe modelo de departamento/área ORGANIZACIONAL en el proyecto
    
    Este modelo es específico de SIA y representa la estructura organizacional
    de una empresa (ej: "Ventas", "Marketing", "IT", "RRHH", etc.).
    
    Permite que un mismo departamento (por nombre) pueda existir en múltiples empresas,
    pero cada instancia está vinculada a una empresa específica.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='sia_departments',
        verbose_name=_('Company'),
        help_text=_('Company to which this department belongs')
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_('Department Name'),
        help_text=_('Name of the organizational department/area')
    )
    code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name=_('Department Code'),
        help_text=_('Optional internal code for the department')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Description'),
        help_text=_('Optional description of the department')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Whether this department is currently active')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        verbose_name = _('Department')
        verbose_name_plural = _('Departments')
        ordering = ['empresa', 'name']
        indexes = [
            models.Index(fields=['empresa', 'name']),
            models.Index(fields=['is_active']),
        ]
        unique_together = ['empresa', 'name']  # Un nombre de departamento único por empresa

    def __str__(self):
        return f"{self.name} ({self.empresa.nombre})"


class EvaluationCycle(models.Model):
    """
    Representa un ciclo de evaluación estratégica (por ejemplo: anual, trimestral).
    
    Cada ciclo agrupa múltiples respuestas de directivos de una empresa.
    Permite comparar evaluaciones a lo largo del tiempo.
    """
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='sia_evaluation_cycles',
        verbose_name=_('Company'),
        help_text=_('Company for which this evaluation cycle is conducted')
    )
    name = models.CharField(
        max_length=255,
        verbose_name=_('Cycle Name'),
        help_text=_('Name of the evaluation cycle (e.g., "Q1 2024", "Annual 2024")')
    )
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Description'),
        help_text=_('Optional description of the evaluation cycle')
    )
    start_date = models.DateField(
        verbose_name=_('Start Date'),
        help_text=_('Start date of the evaluation cycle')
    )
    end_date = models.DateField(
        verbose_name=_('End Date'),
        help_text=_('End date of the evaluation cycle')
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Active'),
        help_text=_('Whether this cycle is currently active and accepting responses')
    )
    created_by = models.ForeignKey(
        UsuarioExtendido,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_evaluation_cycles',
        verbose_name=_('Created By'),
        help_text=_('User who created this evaluation cycle')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        verbose_name = _('Evaluation Cycle')
        verbose_name_plural = _('Evaluation Cycles')
        ordering = ['-start_date', 'empresa', 'name']
        indexes = [
            models.Index(fields=['empresa', 'start_date']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} - {self.empresa.nombre}"

    def clean(self):
        """Validar que la fecha de inicio sea anterior a la fecha de fin"""
        from django.core.exceptions import ValidationError
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError(_('Start date must be before end date.'))


class StrategicSurveyResponse(models.Model):
    """
    Respuesta completa de un directivo a la encuesta estratégica.
    
    Agrupa todos los componentes de una evaluación individual:
    - Mini-FODA (hasta 3 ítems por cuadrante)
    - Ratings (1-10) en diferentes dimensiones
    - Preguntas abiertas
    """
    evaluation_cycle = models.ForeignKey(
        EvaluationCycle,
        on_delete=models.CASCADE,
        related_name='survey_responses',
        verbose_name=_('Evaluation Cycle'),
        help_text=_('Evaluation cycle to which this response belongs')
    )
    user = models.ForeignKey(
        UsuarioExtendido,
        on_delete=models.CASCADE,
        related_name='sia_survey_responses',
        verbose_name=_('User'),
        help_text=_('Executive user who completed this survey')
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='survey_responses',
        verbose_name=_('Department'),
        help_text=_('Department/area of the executive')
    )
    
    # Estado de la respuesta
    STATUS_CHOICES = [
        ('draft', _('Draft')),
        ('submitted', _('Submitted')),
        ('reviewed', _('Reviewed')),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name=_('Status'),
        help_text=_('Current status of the survey response')
    )
    
    # Fechas
    submitted_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Submitted At'),
        help_text=_('Date and time when the survey was submitted')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        verbose_name = _('Strategic Survey Response')
        verbose_name_plural = _('Strategic Survey Responses')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['evaluation_cycle', 'user']),
            models.Index(fields=['status']),
            models.Index(fields=['department']),
        ]
        unique_together = ['evaluation_cycle', 'user']  # Un usuario solo puede responder una vez por ciclo

    def __str__(self):
        return f"{self.user.nombre_completo} - {self.evaluation_cycle.name}"

    def clean(self):
        """Validaciones de integridad de negocio"""
        from django.core.exceptions import ValidationError
        
        # Validar que si department no es nulo, pertenezca a la misma empresa que el ciclo
        if self.department is not None and self.evaluation_cycle_id:
            # Asegurarse de que evaluation_cycle esté cargado
            if not hasattr(self.evaluation_cycle, 'empresa'):
                try:
                    self.evaluation_cycle = EvaluationCycle.objects.select_related('empresa').get(pk=self.evaluation_cycle_id)
                except EvaluationCycle.DoesNotExist:
                    return  # Si no existe, la validación de ForeignKey lo capturará
            
            if self.department.empresa != self.evaluation_cycle.empresa:
                raise ValidationError({
                    'department': _('The selected department must belong to the same company as the evaluation cycle.')
                })
    
    def save(self, *args, **kwargs):
        """Actualizar submitted_at cuando el status cambia a 'submitted'"""
        if self.status == 'submitted' and not self.submitted_at:
            self.submitted_at = timezone.now()
        super().save(*args, **kwargs)


class FodaItem(models.Model):
    """
    Representa un ítem individual del FODA (Fortaleza, Oportunidad, Debilidad, Amenaza).
    
    Cada respuesta puede tener hasta 3 ítems por cuadrante.
    """
    survey_response = models.ForeignKey(
        StrategicSurveyResponse,
        on_delete=models.CASCADE,
        related_name='foda_items',
        verbose_name=_('Survey Response'),
        help_text=_('Survey response to which this FODA item belongs')
    )
    
    QUADRANT_CHOICES = [
        ('strength', 'Fortaleza'),
        ('weakness', 'Debilidad'),
        ('opportunity', 'Oportunidad'),
        ('threat', 'Amenaza'),
    ]
    quadrant = models.CharField(
        max_length=20,
        choices=QUADRANT_CHOICES,
        verbose_name='Cuadrante',
        help_text='Cuadrante FODA al que pertenece este elemento'
    )
    description = models.TextField(
        verbose_name='Descripción',
        help_text='Descripción del elemento FODA'
    )
    priority = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
        verbose_name='Prioridad',
        help_text='Prioridad dentro del cuadrante (1-3, donde 1 es la más alta)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        verbose_name = _('FODA Item')
        verbose_name_plural = _('FODA Items')
        ordering = ['survey_response', 'quadrant', 'priority']
        indexes = [
            models.Index(fields=['survey_response', 'quadrant']),
            models.Index(fields=['quadrant']),
        ]

    def __str__(self):
        return f"{self.get_quadrant_display()}: {self.description[:50]}..."


class Rating(models.Model):
    """
    Representa un rating numérico (1-10) en una dimensión específica.
    
    Cada respuesta puede tener múltiples ratings en diferentes dimensiones.
    """
    survey_response = models.ForeignKey(
        StrategicSurveyResponse,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name=_('Survey Response'),
        help_text=_('Survey response to which this rating belongs')
    )
    
    DIMENSION_CHOICES = [
        ('area_health', 'Salud del Área'),
        ('team_performance', 'Rendimiento del Equipo'),
        ('strategy_alignment', 'Alineación Estratégica'),
        ('process_maturity', 'Madurez del Proceso'),
        ('tech_maturity', 'Madurez Tecnológica'),
    ]
    dimension = models.CharField(
        max_length=50,
        choices=DIMENSION_CHOICES,
        verbose_name='Dimensión',
        help_text='Dimensión que se está evaluando'
    )
    value = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        verbose_name='Valor del Rating',
        help_text='Valor del rating de 1 a 10'
    )
    notes = models.TextField(
        blank=True,
        null=True,
        verbose_name='Notas',
        help_text='Notas opcionales que explican el rating'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        verbose_name = _('Rating')
        verbose_name_plural = _('Ratings')
        ordering = ['survey_response', 'dimension']
        indexes = [
            models.Index(fields=['survey_response', 'dimension']),
            models.Index(fields=['dimension']),
        ]
        unique_together = ['survey_response', 'dimension']  # Un rating por dimensión por respuesta

    def __str__(self):
        return f"{self.get_dimension_display()}: {self.value}/10"


class OpenAnswer(models.Model):
    """
    Representa una respuesta a una pregunta abierta de la encuesta estratégica.
    
    Ejemplos de preguntas:
    - 3 prioridades críticas para el próximo año
    - Principales riesgos del área
    - Oportunidades del mercado no aprovechadas
    """
    survey_response = models.ForeignKey(
        StrategicSurveyResponse,
        on_delete=models.CASCADE,
        related_name='open_answers',
        verbose_name=_('Survey Response'),
        help_text=_('Survey response to which this answer belongs')
    )
    
    QUESTION_TYPE_CHOICES = [
        ('critical_priorities', 'Prioridades Críticas'),
        ('main_risks', 'Riesgos Principales'),
        ('unexploited_opportunities', 'Oportunidades No Aprovechadas'),
        ('other', 'Otro'),
    ]
    question_type = models.CharField(
        max_length=50,
        choices=QUESTION_TYPE_CHOICES,
        verbose_name='Tipo de Pregunta',
        help_text='Tipo de pregunta abierta que se está respondiendo'
    )
    question_text = models.CharField(
        max_length=500,
        verbose_name='Texto de la Pregunta',
        help_text='Texto de la pregunta (puede personalizarse por ciclo)'
    )
    answer = models.TextField(
        verbose_name='Respuesta',
        help_text='Respuesta a la pregunta abierta'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        verbose_name = _('Open Answer')
        verbose_name_plural = _('Open Answers')
        ordering = ['survey_response', 'question_type']
        indexes = [
            models.Index(fields=['survey_response', 'question_type']),
            models.Index(fields=['question_type']),
        ]

    def __str__(self):
        return f"{self.get_question_type_display()}: {self.answer[:50]}..."


class CameAction(models.Model):
    """
    Representa una acción CAME (Corregir, Afrontar, Mantener, Explotar).
    
    Las acciones CAME se derivan del análisis del FODA consolidado:
    - Corregir: acciones para mejorar debilidades
    - Afrontar: acciones para mitigar amenazas
    - Mantener: acciones para preservar fortalezas
    - Explotar: acciones para aprovechar oportunidades
    """
    evaluation_cycle = models.ForeignKey(
        EvaluationCycle,
        on_delete=models.CASCADE,
        related_name='came_actions',
        verbose_name=_('Evaluation Cycle'),
        help_text=_('Evaluation cycle to which this action belongs')
    )
    
    ACTION_TYPE_CHOICES = [
        ('correct', _('Correct')),
        ('address', _('Address')),
        ('maintain', _('Maintain')),
        ('exploit', _('Exploit')),
    ]
    action_type = models.CharField(
        max_length=20,
        choices=ACTION_TYPE_CHOICES,
        verbose_name=_('Action Type'),
        help_text=_('Type of CAME action')
    )
    title = models.CharField(
        max_length=255,
        verbose_name=_('Action Title'),
        help_text=_('Title of the action')
    )
    description = models.TextField(
        verbose_name=_('Description'),
        help_text=_('Detailed description of the action')
    )
    
    # Relación opcional con ítem FODA que originó esta acción
    related_foda_item = models.ForeignKey(
        FodaItem,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='came_actions',
        verbose_name=_('Related FODA Item'),
        help_text=_('FODA item that originated this action (optional)')
    )
    
    # Prioridad y estado
    priority = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Priority'),
        help_text=_('Priority of the action (1-5, where 1 is highest)')
    )
    
    STATUS_CHOICES = [
        ('planned', _('Planned')),
        ('in_progress', _('In Progress')),
        ('completed', _('Completed')),
        ('cancelled', _('Cancelled')),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned',
        verbose_name=_('Status'),
        help_text=_('Current status of the action')
    )
    
    # Responsable y fechas
    assigned_to = models.ForeignKey(
        UsuarioExtendido,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_came_actions',
        verbose_name=_('Assigned To'),
        help_text=_('User responsible for executing this action')
    )
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name=_('Due Date'),
        help_text=_('Expected completion date')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Completed At'),
        help_text=_('Date and time when the action was completed')
    )
    
    # Auditoría
    created_by = models.ForeignKey(
        UsuarioExtendido,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_came_actions',
        verbose_name=_('Created By'),
        help_text=_('User who created this action')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Created at')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Updated at')
    )

    class Meta:
        verbose_name = _('CAME Action')
        verbose_name_plural = _('CAME Actions')
        ordering = ['evaluation_cycle', 'action_type', 'priority']
        indexes = [
            models.Index(fields=['evaluation_cycle', 'action_type']),
            models.Index(fields=['status']),
            models.Index(fields=['assigned_to']),
        ]

    def __str__(self):
        return f"{self.get_action_type_display()}: {self.title}"

    def save(self, *args, **kwargs):
        """Actualizar completed_at cuando el status cambia a 'completed'"""
        if self.status == 'completed' and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status != 'completed' and self.completed_at:
            self.completed_at = None
        super().save(*args, **kwargs)

