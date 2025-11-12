"""
Modelos de datos para el sistema de Reportes AI
"""
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from core.models.models import Empresa
import json
import uuid

User = get_user_model()


class ReportRequest(models.Model):
    """
    Registro de solicitudes de reportes
    """
    STATUS_CHOICES = [
        ('pending', _('Pendiente')),
        ('processing', _('Procesando')),
        ('completed', _('Completado')),
        ('error', _('Error')),
        ('cancelled', _('Cancelado')),
    ]
    
    SOURCE_CHOICES = [
        ('web', _('Interfaz Web')),
        ('webhook', _('Webhook Externo')),
        ('api', _('API REST')),
        ('scheduled', _('Programado')),
    ]
    
    # Identificación
    request_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('ID de Solicitud'),
        help_text=_('Identificador único de la solicitud')
    )
    
    # Usuario y empresa (siguiendo arquitectura de core)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='report_requests',
        verbose_name=_('Usuario')
    )
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='report_requests',
        verbose_name=_('Empresa'),
        null=True,
        blank=True
    )
    
    # Datos de la solicitud
    intent = models.CharField(
        max_length=200,
        verbose_name=_('Intención'),
        help_text=_('Intención de negocio del reporte')
    )
    query_text = models.TextField(
        verbose_name=_('Consulta Original'),
        help_text=_('Texto original de la solicitud')
    )
    context = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Contexto'),
        help_text=_('Contexto adicional de la solicitud')
    )
    priority = models.CharField(
        max_length=20,
        default='medium',
        choices=[
            ('low', _('Baja')),
            ('medium', _('Media')),
            ('high', _('Alta')),
            ('urgent', _('Urgente')),
        ],
        verbose_name=_('Prioridad')
    )
    parameters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Parámetros'),
        help_text=_('Parámetros estructurados: periodo, filtros, segmentación')
    )
    
    # Estado y resultados
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name=_('Estado')
    )
    source = models.CharField(
        max_length=50,  # Aumentado para permitir nombres más largos
        choices=SOURCE_CHOICES,
        default='web',
        verbose_name=_('Origen')
    )
    
    # Respuesta generada
    response_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Respuesta'),
        help_text=_('Datos del reporte generado')
    )
    
    # SQL Query generada (para auditoría y mejora continua)
    sql_query = models.TextField(
        blank=True,
        default='',
        verbose_name=_('SQL Query Generada'),
        help_text=_('Query SQL generada por el Data Analyst Agent')
    )
    
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name=_('Mensaje de Error')
    )
    
    # Métricas
    processing_time = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Tiempo de Procesamiento (seg)')
    )
    tokens_used = models.IntegerField(
        default=0,
        verbose_name=_('Tokens Utilizados')
    )
    confidence_score = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Score de Confianza')
    )
    
    # Auditoría
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de Completado')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Actualización')
    )
    
    class Meta:
        verbose_name = _('Solicitud de Reporte')
        verbose_name_plural = _('Solicitudes de Reportes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['request_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.request_id} - {self.get_status_display()}"


class BusinessRule(models.Model):
    """
    Catálogo de reglas de negocio extraídas del código VB6/PHP
    """
    CATEGORY_CHOICES = [
        ('validation', _('Validación')),
        ('business', _('Lógica de Negocio')),
        ('calculation', _('Cálculo')),
        ('workflow', _('Flujo de Trabajo')),
        ('integration', _('Integración')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Baja')),
        ('medium', _('Media')),
        ('high', _('Alta')),
        ('critical', _('Crítica')),
    ]
    
    # Identificación
    name = models.CharField(
        max_length=200,
        verbose_name=_('Nombre'),
        help_text=_('Nombre funcional de la regla')
    )
    
    # Descripción funcional (sin tecnicismos)
    description = models.TextField(
        verbose_name=_('Descripción de Negocio'),
        help_text=_('Explicación en términos de negocio, sin código ni SQL')
    )
    
    # Categorización
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='business',
        verbose_name=_('Categoría')
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name=_('Prioridad')
    )
    
    # Contexto funcional
    module = models.CharField(
        max_length=100,
        verbose_name=_('Módulo de Negocio'),
        help_text=_('Ej: Ventas, Inventario, Cobranzas')
    )
    
    # Lógica de la regla
    conditions = models.TextField(
        default='',
        verbose_name=_('Condiciones'),
        help_text=_('Condiciones de aplicación en lenguaje de negocio')
    )
    
    actions = models.TextField(
        default='',
        verbose_name=_('Acciones'),
        help_text=_('Acciones que se ejecutan cuando se cumple la regla')
    )
    
    # Información de origen (código fuente)
    source_file = models.CharField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name=_('Archivo de Origen'),
        help_text=_('Archivo VB6/PHP donde se encontró la regla')
    )
    
    source_line = models.IntegerField(
        blank=True,
        null=True,
        verbose_name=_('Línea de Código'),
        help_text=_('Número de línea en el archivo fuente')
    )
    
    source_function = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name=_('Función/Procedimiento'),
        help_text=_('Nombre de la función, procedimiento o método donde se encontró la regla')
    )
    
    # Procedimiento de negocio completo
    business_procedure = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Procedimiento de Negocio'),
        help_text=_('Descripción del proceso completo de negocio (ej: Cómo crear una factura, cómo hacer movimiento de stock)')
    )
    
    # Metadata
    tags = models.CharField(
        max_length=500,
        blank=True,
        verbose_name=_('Tags'),
        help_text=_('Tags separados por comas para categorización')
    )
    
    # Estado
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activa')
    )
    
    # Auditoría
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_business_rules',
        verbose_name=_('Creado Por')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Regla de Negocio')
        verbose_name_plural = _('Reglas de Negocio')
        ordering = ['module', 'name']
        indexes = [
            models.Index(fields=['module', 'is_active']),
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.module})"


class AgentMetrics(models.Model):
    """
    Métricas de rendimiento de cada agente
    """
    AGENT_CHOICES = [
        ('orchestrator', _('Orquestador')),
        ('query_interpreter', _('Intérprete de Consulta')),
        ('data_analyst', _('Analista de Datos')),
        ('logic_interpreter', _('Intérprete de Lógica')),
        ('report_generator', _('Generador de Reportes')),
        ('validator', _('Validador')),
        ('webhook', _('Webhook')),
    ]
    
    agent_name = models.CharField(
        max_length=50,
        choices=AGENT_CHOICES,
        verbose_name=_('Agente')
    )
    date = models.DateField(
        auto_now_add=True,
        verbose_name=_('Fecha')
    )
    
    # Métricas de uso
    total_invocations = models.IntegerField(
        default=0,
        verbose_name=_('Total Invocaciones')
    )
    successful_invocations = models.IntegerField(
        default=0,
        verbose_name=_('Invocaciones Exitosas')
    )
    failed_invocations = models.IntegerField(
        default=0,
        verbose_name=_('Invocaciones Fallidas')
    )
    
    # Métricas de calidad
    avg_processing_time = models.FloatField(
        default=0.0,
        verbose_name=_('Tiempo Promedio (seg)')
    )
    avg_confidence_score = models.FloatField(
        default=0.0,
        verbose_name=_('Score Confianza Promedio')
    )
    
    # Métricas de recursos
    total_tokens_used = models.IntegerField(
        default=0,
        verbose_name=_('Total Tokens')
    )
    
    # Control de alucinaciones
    hallucination_count = models.IntegerField(
        default=0,
        verbose_name=_('Alucinaciones Detectadas'),
        help_text=_('Respuestas bloqueadas por validación')
    )
    
    class Meta:
        verbose_name = _('Métrica de Agente')
        verbose_name_plural = _('Métricas de Agentes')
        ordering = ['-date', 'agent_name']
        unique_together = [['agent_name', 'date']]
    
    def __str__(self):
        return f"{self.get_agent_name_display()} - {self.date}"
    
    @property
    def success_rate(self):
        """Calcula la tasa de éxito"""
        if self.total_invocations == 0:
            return 0.0
        return (self.successful_invocations / self.total_invocations) * 100


class NLUTrainingExample(models.Model):
    """
    Ejemplos de entrenamiento para el NLU (Query Interpreter)
    Almacena queries con su intent y slots correctos
    """
    # Query original
    query_text = models.TextField(
        verbose_name=_('Texto de Consulta'),
        help_text=_('Consulta original del usuario')
    )
    
    # Intent clasificado
    intent = models.CharField(
        max_length=100,
        verbose_name=_('Intent'),
        help_text=_('Intención clasificada (ventas, inventario, clientes, etc.)')
    )
    
    # Slots extraídos (JSON)
    slots = models.JSONField(
        default=dict,
        verbose_name=_('Slots'),
        help_text=_('Slots extraídos: categoria, periodo, filtros, segmentaciones, etc.')
    )
    
    # Metadata
    is_canonical = models.BooleanField(
        default=False,
        verbose_name=_('Ejemplo Canónico'),
        help_text=_('Ejemplo congelado para detección de deriva')
    )
    source = models.CharField(
        max_length=50,
        default='manual',
        verbose_name=_('Origen'),
        help_text=_('manual, feedback, webhook, auto-generated')
    )
    priority = models.CharField(
        max_length=20,
        default='normal',
        choices=[
            ('low', _('Baja')),
            ('normal', _('Normal')),
            ('high', _('Alta')),
            ('critical', _('Crítica')),
        ],
        verbose_name=_('Prioridad')
    )
    
    # Auditoría
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='nlu_examples_created'
    )
    
    class Meta:
        verbose_name = _('Ejemplo de Entrenamiento NLU')
        verbose_name_plural = _('Ejemplos de Entrenamiento NLU')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['intent', 'is_active']),
            models.Index(fields=['is_canonical']),
        ]
    
    def __str__(self):
        return f"{self.intent}: {self.query_text[:50]}"


class NLUMetrics(models.Model):
    """
    Métricas de evaluación del NLU por periodo
    """
    # Periodo de evaluación
    evaluation_date = models.DateField(
        verbose_name=_('Fecha de Evaluación')
    )
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('daily', _('Diaria')),
            ('weekly', _('Semanal')),
            ('monthly', _('Mensual')),
        ],
        default='weekly',
        verbose_name=_('Tipo de Periodo')
    )
    
    # Métricas globales
    total_queries = models.IntegerField(
        default=0,
        verbose_name=_('Total de Consultas')
    )
    correctly_classified = models.IntegerField(
        default=0,
        verbose_name=_('Clasificadas Correctamente')
    )
    misclassified = models.IntegerField(
        default=0,
        verbose_name=_('Mal Clasificadas')
    )
    ambiguous = models.IntegerField(
        default=0,
        verbose_name=_('Ambiguas')
    )
    out_of_context = models.IntegerField(
        default=0,
        verbose_name=_('Fuera de Contexto')
    )
    
    # Métricas calculadas
    coverage_rate = models.FloatField(
        default=0.0,
        verbose_name=_('Tasa de Cobertura'),
        help_text=_('% de consultas entendidas sin intervención')
    )
    clarification_rate = models.FloatField(
        default=0.0,
        verbose_name=_('Tasa de Aclaración'),
        help_text=_('% de veces que pide precisión')
    )
    misroute_rate = models.FloatField(
        default=0.0,
        verbose_name=_('Tasa de Error de Enrutamiento'),
        help_text=_('% de enrutamiento a intent equivocado')
    )
    
    # Métricas por intent (JSON)
    intent_metrics = models.JSONField(
        default=dict,
        verbose_name=_('Métricas por Intent'),
        help_text=_('F1, precision, recall por cada intent')
    )
    
    # Métricas de slots
    slot_accuracy = models.FloatField(
        default=0.0,
        verbose_name=_('Exactitud de Slots'),
        help_text=_('% de slots correctamente extraídos')
    )
    
    # Estado del modelo
    model_version = models.CharField(
        max_length=50,
        verbose_name=_('Versión del Modelo')
    )
    
    # Notas
    notes = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Notas')
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Métrica NLU')
        verbose_name_plural = _('Métricas NLU')
        ordering = ['-evaluation_date']
        unique_together = [['evaluation_date', 'period_type']]
        indexes = [
            models.Index(fields=['evaluation_date', 'period_type']),
        ]
    
    def __str__(self):
        return f"NLU Metrics {self.evaluation_date} ({self.period_type})"


class NLUFeedback(models.Model):
    """
    Feedback de usuarios sobre interpretación incorrecta del NLU
    """
    # Query original
    query_text = models.TextField(
        verbose_name=_('Consulta Original')
    )
    
    # Interpretación del sistema
    system_intent = models.CharField(
        max_length=100,
        verbose_name=_('Intent del Sistema')
    )
    system_slots = models.JSONField(
        default=dict,
        verbose_name=_('Slots del Sistema')
    )
    
    # Interpretación correcta
    correct_intent = models.CharField(
        max_length=100,
        verbose_name=_('Intent Correcto')
    )
    correct_slots = models.JSONField(
        default=dict,
        verbose_name=_('Slots Correctos')
    )
    
    # Comentario
    user_comment = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Comentario del Usuario')
    )
    
    # Estado de procesamiento
    status = models.CharField(
        max_length=20,
        default='pending',
        choices=[
            ('pending', _('Pendiente')),
            ('reviewed', _('Revisado')),
            ('processed', _('Procesado')),
            ('ignored', _('Ignorado')),
        ],
        verbose_name=_('Estado')
    )
    
    # Prioridad
    priority = models.CharField(
        max_length=20,
        default='normal',
        choices=[
            ('low', _('Baja')),
            ('normal', _('Normal')),
            ('high', _('Alta')),
            ('critical', _('Crítica')),
        ],
        verbose_name=_('Prioridad')
    )
    
    # Relación con reporte
    report_request = models.ForeignKey(
        'ReportRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='nlu_feedbacks'
    )
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Feedback NLU')
        verbose_name_plural = _('Feedbacks NLU')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Feedback: {self.query_text[:50]}"


class NLUModel(models.Model):
    """
    Versiones del modelo NLU con métricas y estado
    """
    # Identificación
    version = models.CharField(
        max_length=50,
        unique=True,
        verbose_name=_('Versión'),
        help_text=_('ej: v1.0.0, v1.1.0-beta')
    )
    
    # Descripción
    description = models.TextField(
        verbose_name=_('Descripción'),
        help_text=_('Cambios y mejoras en esta versión')
    )
    
    # Estado
    status = models.CharField(
        max_length=20,
        default='shadow',
        choices=[
            ('active', _('Activo')),
            ('shadow', _('En Prueba (Shadow)')),
            ('retired', _('Retirado')),
            ('rollback', _('Rollback')),
        ],
        verbose_name=_('Estado')
    )
    
    # Métricas de calidad
    f1_global = models.FloatField(
        default=0.0,
        verbose_name=_('F1 Global')
    )
    intent_accuracy = models.FloatField(
        default=0.0,
        verbose_name=_('Accuracy de Intent')
    )
    slot_accuracy = models.FloatField(
        default=0.0,
        verbose_name=_('Accuracy de Slots')
    )
    coverage_rate = models.FloatField(
        default=0.0,
        verbose_name=_('Tasa de Cobertura')
    )
    
    # Configuración
    temperature = models.FloatField(
        default=0.2,
        verbose_name=_('Temperature')
    )
    top_p = models.FloatField(
        default=0.9,
        verbose_name=_('Top P')
    )
    
    # Datos de entrenamiento
    training_examples_count = models.IntegerField(
        default=0,
        verbose_name=_('Cantidad de Ejemplos de Entrenamiento')
    )
    canonical_examples_count = models.IntegerField(
        default=0,
        verbose_name=_('Ejemplos Canónicos')
    )
    
    # Fechas
    trained_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de Entrenamiento')
    )
    activated_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de Activación')
    )
    retired_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Fecha de Retiro')
    )
    
    # Auditoría
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    
    class Meta:
        verbose_name = _('Modelo NLU')
        verbose_name_plural = _('Modelos NLU')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['version']),
        ]
    
    def __str__(self):
        return f"NLU Model {self.version} ({self.get_status_display()})"


class RelationshipCandidate(models.Model):
    """
    Catálogo de relaciones entre tablas descubiertas automáticamente
    Sin necesidad de FKs formales en la BD
    """
    # Identificación de la relación
    source_table = models.CharField(
        max_length=100,
        verbose_name=_('Tabla Origen'),
        db_index=True
    )
    source_column = models.CharField(
        max_length=100,
        verbose_name=_('Columna Origen')
    )
    target_table = models.CharField(
        max_length=100,
        verbose_name=_('Tabla Destino'),
        db_index=True
    )
    target_column = models.CharField(
        max_length=100,
        verbose_name=_('Columna Destino')
    )
    
    # Scoring y confianza
    confidence_score = models.FloatField(
        default=0.0,
        verbose_name=_('Score de Confianza'),
        help_text=_('0.0 a 1.0, calculado por múltiples señales')
    )
    
    # Señales que contribuyen al score
    name_match_score = models.FloatField(default=0.0, verbose_name=_('Coincidencia de Nombre'))
    type_compatibility = models.FloatField(default=0.0, verbose_name=_('Compatibilidad de Tipo'))
    domain_inclusion = models.FloatField(default=0.0, verbose_name=_('Inclusión de Dominio'))
    uniqueness_score = models.FloatField(default=0.0, verbose_name=_('Score de Unicidad'))
    logic_interpreter_hint = models.BooleanField(default=False, verbose_name=_('Sugerido por Logic Interpreter'))
    has_index = models.BooleanField(default=False, verbose_name=_('Tiene Índice'))
    
    # Metadata de la relación
    cardinality = models.CharField(
        max_length=20,
        choices=[
            ('1:1', _('Uno a Uno')),
            ('1:N', _('Uno a Muchos')),
            ('N:1', _('Muchos a Uno')),
            ('N:M', _('Muchos a Muchos')),
        ],
        default='N:1',
        verbose_name=_('Cardinalidad')
    )
    role = models.CharField(
        max_length=50,
        default='maestro-detalle',
        verbose_name=_('Rol Funcional'),
        help_text=_('maestro-detalle, catalogo-transaccional, etc.')
    )
    
    # Validación y uso
    validated_by_human = models.BooleanField(
        default=False,
        verbose_name=_('Validada por Humano')
    )
    times_used_successfully = models.IntegerField(
        default=0,
        verbose_name=_('Veces Usada Exitosamente')
    )
    times_failed = models.IntegerField(
        default=0,
        verbose_name=_('Veces Fallida')
    )
    last_used_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Última Vez Usada')
    )
    
    # Auditoría
    discovered_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Descubrimiento')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Actualización')
    )
    
    class Meta:
        verbose_name = _('Relación Candidata')
        verbose_name_plural = _('Relaciones Candidatas')
        unique_together = [['source_table', 'source_column', 'target_table', 'target_column']]
        ordering = ['-confidence_score', '-times_used_successfully']
        indexes = [
            models.Index(fields=['source_table', 'target_table']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['-times_used_successfully']),
        ]
    
    def __str__(self):
        return f"{self.source_table}.{self.source_column} → {self.target_table}.{self.target_column} ({self.confidence_score:.2f})"
    
    def update_confidence(self):
        """Recalcula el score de confianza basándose en todas las señales"""
        weights = {
            'name_match': 0.25,
            'type_compat': 0.15,
            'domain_inclusion': 0.25,
            'uniqueness': 0.15,
            'logic_hint': 0.10,
            'has_index': 0.05,
            'usage_history': 0.05
        }
        
        # Score de historial de uso
        usage_score = 0.0
        if self.times_used_successfully + self.times_failed > 0:
            usage_score = self.times_used_successfully / (self.times_used_successfully + self.times_failed)
        
        # Calcular score total
        self.confidence_score = (
            weights['name_match'] * self.name_match_score +
            weights['type_compat'] * self.type_compatibility +
            weights['domain_inclusion'] * self.domain_inclusion +
            weights['uniqueness'] * self.uniqueness_score +
            weights['logic_hint'] * (1.0 if self.logic_interpreter_hint else 0.0) +
            weights['has_index'] * (1.0 if self.has_index else 0.0) +
            weights['usage_history'] * usage_score
        )
        
        # Validación humana siempre eleva a 0.95+
        if self.validated_by_human:
            self.confidence_score = max(self.confidence_score, 0.95)


class ColumnStatistics(models.Model):
    """
    Estadísticas precalculadas de columnas para descubrimiento de relaciones
    """
    table_name = models.CharField(
        max_length=100,
        verbose_name=_('Nombre de Tabla'),
        db_index=True
    )
    column_name = models.CharField(
        max_length=100,
        verbose_name=_('Nombre de Columna')
    )
    
    # Estadísticas básicas
    total_count = models.IntegerField(default=0, verbose_name=_('Total de Registros'))
    unique_count = models.IntegerField(default=0, verbose_name=_('Valores Únicos'))
    null_count = models.IntegerField(default=0, verbose_name=_('Valores Nulos'))
    
    # Propiedades derivadas
    is_unique = models.BooleanField(default=False, verbose_name=_('Es Único'))
    is_nullable = models.BooleanField(default=True, verbose_name=_('Permite Nulos'))
    null_percentage = models.FloatField(default=0.0, verbose_name=_('% Nulos'))
    
    # Muestreo de valores (para análisis de dominio)
    sample_values = models.JSONField(
        default=list,
        verbose_name=_('Valores de Muestra'),
        help_text=_('Top 20 valores más frecuentes con sus conteos')
    )
    
    # Cache control
    calculated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Calculado En')
    )
    is_stale = models.BooleanField(
        default=False,
        verbose_name=_('Desactualizado'),
        help_text=_('True si hace más de 7 días desde la última actualización')
    )
    
    class Meta:
        verbose_name = _('Estadística de Columna')
        verbose_name_plural = _('Estadísticas de Columnas')
        unique_together = [['table_name', 'column_name']]
        indexes = [
            models.Index(fields=['table_name']),
            models.Index(fields=['is_unique']),
            models.Index(fields=['calculated_at']),
        ]
    
    def __str__(self):
        return f"{self.table_name}.{self.column_name} ({self.unique_count} únicos)"


class SynonymMapping(models.Model):
    """
    Diccionario de sinónimos: términos de negocio → nombres de columnas técnicas
    """
    business_term = models.CharField(
        max_length=100,
        verbose_name=_('Término de Negocio'),
        db_index=True,
        help_text=_('Ej: provincia, cliente, artículo')
    )
    
    column_pattern = models.CharField(
        max_length=200,
        verbose_name=_('Patrón de Columna'),
        help_text=_('Ej: CodProvincia, IDProvincia, ProvinciaId')
    )
    
    confidence = models.FloatField(
        default=0.5,
        verbose_name=_('Confianza'),
        help_text=_('Calculado por uso exitoso')
    )
    
    # Fuente del mapeo
    source = models.CharField(
        max_length=50,
        choices=[
            ('manual', _('Manual')),
            ('logic_interpreter', _('Logic Interpreter')),
            ('discovered', _('Descubierto Automáticamente')),
            ('validated', _('Validado por Usuario')),
        ],
        default='discovered',
        verbose_name=_('Fuente')
    )
    
    # Uso y validación
    times_used = models.IntegerField(default=0, verbose_name=_('Veces Usado'))
    times_successful = models.IntegerField(default=0, verbose_name=_('Veces Exitoso'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Mapeo de Sinónimo')
        verbose_name_plural = _('Mapeos de Sinónimos')
        unique_together = [['business_term', 'column_pattern']]
        ordering = ['-confidence', '-times_successful']
    
    def __str__(self):
        return f"{self.business_term} → {self.column_pattern} ({self.confidence:.2f})"


class QueryCorrection(models.Model):
    """
    Registro de correcciones para active learning
    """
    report_request = models.ForeignKey(
        'ReportRequest',
        on_delete=models.CASCADE,
        related_name='corrections',
        verbose_name=_('Solicitud de Reporte')
    )
    
    # Consulta original
    original_query = models.TextField(verbose_name=_('Query Original'))
    original_sql = models.TextField(verbose_name=_('SQL Original'))
    
    # Corrección
    correction_type = models.CharField(
        max_length=50,
        choices=[
            ('wrong_table', _('Tabla Incorrecta')),
            ('wrong_column', _('Columna Incorrecta')),
            ('missing_join', _('Join Faltante')),
            ('wrong_join', _('Join Incorrecto')),
            ('wrong_filter', _('Filtro Incorrecto')),
            ('performance', _('Problema de Performance')),
        ],
        verbose_name=_('Tipo de Corrección')
    )
    
    corrected_sql = models.TextField(
        blank=True,
        verbose_name=_('SQL Corregida')
    )
    
    correction_notes = models.TextField(
        verbose_name=_('Notas de Corrección'),
        help_text=_('Explicación de qué se corrigió y por qué')
    )
    
    # Aprendizaje aplicado
    applied_to_catalog = models.BooleanField(
        default=False,
        verbose_name=_('Aplicado al Catálogo')
    )
    
    corrected_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='query_corrections',
        verbose_name=_('Corregido Por')
    )
    corrected_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = _('Corrección de Query')
        verbose_name_plural = _('Correcciones de Queries')
        ordering = ['-corrected_at']
    
    def __str__(self):
        return f"Corrección {self.get_correction_type_display()} - {self.corrected_at.strftime('%Y-%m-%d')}"


class LogicTrainingSession(models.Model):
    """
    Sesión de entrenamiento del Logic Interpreter
    Tracking de progreso y resultados en tiempo real
    """
    # Identificación
    session_id = models.CharField(
        max_length=100,
        unique=True,
        verbose_name=_('ID de Sesión'),
        help_text=_('Identificador único de la sesión de entrenamiento')
    )
    
    # Estado
    STATUS_CHOICES = [
        ('running', _('En Ejecución')),
        ('completed', _('Completado')),
        ('error', _('Error')),
        ('cancelled', _('Cancelado')),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='running',
        verbose_name=_('Estado')
    )
    
    # Configuración
    categories = models.JSONField(
        default=list,
        verbose_name=_('Categorías'),
        help_text=_('Categorías a analizar: inventario, ventas, etc.')
    )
    mode = models.CharField(
        max_length=20,
        default='full',
        choices=[
            ('full', _('Completo')),
            ('incremental', _('Incremental')),
        ],
        verbose_name=_('Modo')
    )
    
    # Progreso
    total_forms = models.IntegerField(
        default=0,
        verbose_name=_('Total de Formularios')
    )
    analyzed_forms = models.IntegerField(
        default=0,
        verbose_name=_('Formularios Analizados')
    )
    current_phase = models.CharField(
        max_length=50,
        default='scan',
        verbose_name=_('Fase Actual'),
        help_text=_('scan, analyze, infer, validate, extract, save')
    )
    current_item = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_('Item Actual'),
        help_text=_('Formulario o tabla siendo procesada')
    )
    progress_percentage = models.FloatField(
        default=0.0,
        verbose_name=_('Porcentaje de Progreso')
    )
    
    # Descubrimientos
    entities_discovered = models.JSONField(
        default=list,
        verbose_name=_('Entidades Descubiertas')
    )
    tables_suggested = models.JSONField(
        default=list,
        verbose_name=_('Tablas Sugeridas')
    )
    fields_validated = models.JSONField(
        default=dict,
        verbose_name=_('Campos Validados')
    )
    relations_found = models.JSONField(
        default=list,
        verbose_name=_('Relaciones Encontradas')
    )
    rules_extracted = models.JSONField(
        default=list,
        verbose_name=_('Reglas Extraídas')
    )
    
    # Métricas
    start_time = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Hora de Inicio')
    )
    end_time = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Hora de Fin')
    )
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        verbose_name=_('Duración (segundos)')
    )
    
    # Métricas de calidad
    success_rate = models.FloatField(
        default=0.0,
        verbose_name=_('Tasa de Éxito'),
        help_text=_('% de formularios analizados exitosamente')
    )
    avg_confidence = models.FloatField(
        default=0.0,
        verbose_name=_('Confianza Promedio'),
        help_text=_('Promedio de confianza de tablas sugeridas')
    )
    tables_verified = models.IntegerField(
        default=0,
        verbose_name=_('Tablas Verificadas en MySQL')
    )
    fields_match_rate = models.FloatField(
        default=0.0,
        verbose_name=_('Tasa de Coincidencia de Campos'),
        help_text=_('% de campos sugeridos que existen en MySQL')
    )
    
    # Logs
    log_entries = models.JSONField(
        default=list,
        verbose_name=_('Entradas de Log'),
        help_text=_('Log de eventos durante el entrenamiento')
    )
    
    # Error info
    error_message = models.TextField(
        blank=True,
        default='',
        verbose_name=_('Mensaje de Error')
    )
    
    # Auditoría
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='logic_training_sessions',
        verbose_name=_('Creado Por')
    )
    
    class Meta:
        verbose_name = _('Sesión de Entrenamiento Logic Interpreter')
        verbose_name_plural = _('Sesiones de Entrenamiento Logic Interpreter')
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['session_id']),
            models.Index(fields=['status', '-start_time']),
        ]
    
    def __str__(self):
        return f"Training {self.session_id} ({self.get_status_display()})"
    
    def add_log(self, event_type: str, message: str, level: str = 'info'):
        """Agrega entrada al log"""
        from datetime import datetime
        if not isinstance(self.log_entries, list):
            self.log_entries = []
        
        self.log_entries.append({
            'timestamp': datetime.now().isoformat(),
            'type': event_type,
            'message': message,
            'level': level
        })
        
        # Mantener solo últimos 100 logs
        if len(self.log_entries) > 100:
            self.log_entries = self.log_entries[-100:]
        
        self.save(update_fields=['log_entries'])


class GlossaryTerm(models.Model):
    """
    Glosario de términos funcionales de Administranet
    """
    term = models.CharField(
        max_length=200,
        unique=True,
        verbose_name=_('Término'),
        help_text=_('Término funcional')
    )
    definition = models.TextField(
        verbose_name=_('Definición'),
        help_text=_('Definición en lenguaje de negocio')
    )
    synonyms = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Sinónimos')
    )
    category = models.CharField(
        max_length=100,
        verbose_name=_('Categoría'),
        help_text=_('Ej: Ventas, Inventario, Clientes')
    )
    context = models.CharField(
        max_length=200,
        blank=True,
        default='',
        verbose_name=_('Contexto'),
        help_text=_('Contexto de uso del término')
    )
    examples = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_('Ejemplos de Uso')
    )
    
    # Metadata
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Término del Glosario')
        verbose_name_plural = _('Términos del Glosario')
        ordering = ['category', 'term']
        indexes = [
            models.Index(fields=['term']),
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return self.term


class ChatConversation(models.Model):
    """
    Conversación completa del usuario con el asistente AI
    """
    conversation_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ai_conversations',
        verbose_name=_('Usuario')
    )
    
    # Metadata
    title = models.CharField(
        max_length=200,
        verbose_name=_('Título'),
        help_text=_('Auto-generado del primer mensaje')
    )
    
    # Estado
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activa'),
        help_text=_('Conversación activa o archivada')
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Actualización')
    )
    
    class Meta:
        verbose_name = _('Conversación de Chat')
        verbose_name_plural = _('Conversaciones de Chat')
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', '-updated_at']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.user.username}"
    
    def get_message_count(self):
        """Retorna número de mensajes en la conversación"""
        return self.messages.count()
    
    def get_last_message(self):
        """Retorna último mensaje de la conversación"""
        return self.messages.last()


class ChatMessage(models.Model):
    """
    Mensaje individual en una conversación de chat
    """
    message_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name=_('Conversación')
    )
    
    # Contenido
    role = models.CharField(
        max_length=20,
        choices=[
            ('user', _('Usuario')),
            ('assistant', _('Asistente')),
            ('system', _('Sistema'))
        ],
        verbose_name=_('Rol')
    )
    content = models.TextField(
        verbose_name=_('Contenido')
    )
    
    # Tipo de mensaje
    message_type = models.CharField(
        max_length=50,
        choices=[
            ('text', _('Texto Simple')),
            ('procedure', _('Procedimiento')),
            ('report_data', _('Datos de Reporte')),
            ('report_chart', _('Gráfico')),
            ('download_offer', _('Oferta de Descarga')),
            ('clarification', _('Solicitud de Aclaración')),
            ('error', _('Error'))
        ],
        default='text',
        verbose_name=_('Tipo de Mensaje')
    )
    
    # Contexto de ejecución (para mensajes del asistente)
    intent = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Intención Detectada')
    )
    entities = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Entidades Extraídas')
    )
    
    # Reporte asociado (si el mensaje es sobre un reporte)
    report_request = models.ForeignKey(
        ReportRequest,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='chat_messages',
        verbose_name=_('Solicitud de Reporte')
    )
    
    # Metadata adicional (para exportación, gráficos, etc.)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Metadata Adicional'),
        help_text=_('Datos extra como formato de tabla, opciones de gráfico, etc.')
    )
    
    # Timestamps
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    
    class Meta:
        verbose_name = _('Mensaje de Chat')
        verbose_name_plural = _('Mensajes de Chat')
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['role']),
            models.Index(fields=['message_type']),
        ]
    
    def __str__(self):
        preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{self.get_role_display()}: {preview}"


class ReportExport(models.Model):
    """
    Exportación de reporte a Excel o PDF
    """
    export_id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    # Relaciones
    report_request = models.ForeignKey(
        ReportRequest,
        on_delete=models.CASCADE,
        related_name='exports',
        verbose_name=_('Solicitud de Reporte')
    )
    chat_message = models.ForeignKey(
        ChatMessage,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='exports',
        verbose_name=_('Mensaje de Chat')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='report_exports',
        verbose_name=_('Usuario')
    )
    
    # Formato y archivo
    format = models.CharField(
        max_length=10,
        choices=[
            ('excel', 'Excel'),
            ('pdf', 'PDF'),
            ('csv', 'CSV')
        ],
        verbose_name=_('Formato')
    )
    
    file = models.FileField(
        upload_to='reports_ai/exports/%Y/%m/',
        verbose_name=_('Archivo'),
        max_length=500
    )
    filename = models.CharField(
        max_length=255,
        verbose_name=_('Nombre de Archivo')
    )
    file_size = models.IntegerField(
        verbose_name=_('Tamaño de Archivo (bytes)')
    )
    
    # Template usado
    template_used = models.CharField(
        max_length=100,
        default='default',
        verbose_name=_('Template Usado'),
        help_text=_('Nombre del template usado para la exportación')
    )
    
    # Metadata
    generated_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Generación')
    )
    downloaded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Primera Descarga')
    )
    download_count = models.IntegerField(
        default=0,
        verbose_name=_('Número de Descargas')
    )
    
    # Configuración de exportación
    export_options = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Opciones de Exportación'),
        help_text=_('Opciones como incluir logo, colores, etc.')
    )
    
    class Meta:
        verbose_name = _('Exportación de Reporte')
        verbose_name_plural = _('Exportaciones de Reportes')
        ordering = ['-generated_at']
        indexes = [
            models.Index(fields=['user', '-generated_at']),
            models.Index(fields=['format']),
            models.Index(fields=['report_request']),
        ]
    
    def __str__(self):
        return f"{self.get_format_display()} - {self.filename}"
    
    def mark_downloaded(self):
        """Marca el export como descargado"""
        from django.utils import timezone
        if not self.downloaded_at:
            self.downloaded_at = timezone.now()
        self.download_count += 1
        self.save()


class FunctionalCatalog(models.Model):
    """
    Catálogo funcional para entrenamiento guiado del Logic Interpreter
    
    Documenta procedimientos de negocio con referencia a archivos específicos,
    tablas, campos y reglas funcionales.
    
    Permite entrenamiento rápido y preciso enfocado en procesos clave.
    """
    # Identificación del procedimiento
    module = models.CharField(
        max_length=100,
        verbose_name=_('Módulo Funcional'),
        help_text=_('Ej: Ventas, Stock, Clientes, Facturación'),
        db_index=True
    )
    procedure = models.CharField(
        max_length=200,
        verbose_name=_('Procedimiento'),
        help_text=_('Ej: Crear pedido, Guardar factura, Movimiento de stock'),
        db_index=True
    )
    description = models.TextField(
        blank=True,
        verbose_name=_('Descripción'),
        help_text=_('Descripción detallada del procedimiento')
    )
    
    # Archivos fuente a analizar
    vb6_forms = models.TextField(
        verbose_name=_('Formularios VB6'),
        help_text=_('Nombres de formularios VB6 separados por coma. Ej: Pedido.frm, Pedido_Avanzado.frm')
    )
    vb6_modules = models.TextField(
        blank=True,
        verbose_name=_('Módulos VB6'),
        help_text=_('Módulos .bas o .cls separados por coma')
    )
    php_scripts = models.TextField(
        blank=True,
        verbose_name=_('Scripts PHP'),
        help_text=_('Scripts PHP separados por coma')
    )
    
    # Modelo de negocio (para DataAnalyst)
    entities = models.TextField(
        verbose_name=_('Entidades Involucradas'),
        help_text=_('Entidades de negocio separadas por coma. Ej: Pedido, Cliente, Articulo, Sucursal')
    )
    candidate_tables = models.TextField(
        verbose_name=_('Tablas Candidatas'),
        help_text=_('Tablas de BD separadas por coma. Ej: comp_ped, cuerpostockpe, cliente')
    )
    master_table = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Tabla Maestra'),
        help_text=_('Tabla principal del procedimiento. Ej: comp_ped')
    )
    detail_table = models.CharField(
        max_length=100,
        blank=True,
        verbose_name=_('Tabla Detalle'),
        help_text=_('Tabla de detalle/líneas. Ej: cuerpostockpe')
    )
    key_fields = models.TextField(
        verbose_name=_('Campos Clave'),
        help_text=_('Campos importantes separados por coma. Ej: CodigoMovimiento, Codigo, IDArt, Total')
    )
    
    # Lógica del procedimiento
    relevant_events = models.TextField(
        blank=True,
        verbose_name=_('Eventos Relevantes'),
        help_text=_('Eventos VB6 que disparan el proceso. Ej: Guardar(), cmdGuardar_Click()')
    )
    business_rules = models.TextField(
        verbose_name=_('Reglas Funcionales'),
        help_text=_('Descripción de reglas de negocio aplicables')
    )
    validations = models.TextField(
        blank=True,
        verbose_name=_('Validaciones'),
        help_text=_('Validaciones que se ejecutan. Ej: Cliente activo, Stock suficiente')
    )
    dependencies = models.TextField(
        blank=True,
        verbose_name=_('Dependencias'),
        help_text=_('Otros módulos o procesos relacionados. Ej: Presupuesto, Numeración')
    )
    
    # Relaciones entre tablas
    table_relationships = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_('Relaciones entre Tablas'),
        help_text=_('JSON con relaciones. Ej: {"comp_ped.CodigoMovimiento": "cuerpostockpe.CodigoMovimiento"}')
    )
    
    # Operaciones de BD
    insert_tables = models.TextField(
        blank=True,
        verbose_name=_('Tablas con INSERT'),
        help_text=_('Tablas donde se insertan registros')
    )
    update_tables = models.TextField(
        blank=True,
        verbose_name=_('Tablas con UPDATE'),
        help_text=_('Tablas donde se actualizan registros')
    )
    
    # Metadata de calidad
    confidence = models.FloatField(
        default=0.9,
        verbose_name=_('Confianza Inicial'),
        help_text=_('Nivel de certeza de 0.0 a 1.0')
    )
    priority = models.IntegerField(
        default=5,
        verbose_name=_('Prioridad'),
        help_text=_('1-10, donde 10 es máxima prioridad')
    )
    
    # Control de versiones
    is_active = models.BooleanField(
        default=True,
        verbose_name=_('Activo')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='functional_catalogs_created',
        verbose_name=_('Creado Por')
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_('Fecha de Creación')
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_('Última Actualización')
    )
    last_trained = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Último Entrenamiento'),
        help_text=_('Fecha y hora del último entrenamiento exitoso')
    )
    last_revision = models.DateField(
        auto_now=True,
        verbose_name=_('Última Revisión')
    )
    
    # Notas
    notes = models.TextField(
        blank=True,
        verbose_name=_('Notas'),
        help_text=_('Observaciones o comentarios adicionales')
    )
    
    class Meta:
        verbose_name = _('Entrada de Catálogo Funcional')
        verbose_name_plural = _('Catálogo Funcional')
        ordering = ['-priority', 'module', 'procedure']
        unique_together = ['module', 'procedure']
        indexes = [
            models.Index(fields=['module']),
            models.Index(fields=['is_active', '-priority']),
            models.Index(fields=['-confidence']),
        ]
    
    def __str__(self):
        return f"{self.module} - {self.procedure}"
    
    def get_entities_list(self):
        """Retorna lista de entidades"""
        return [e.strip() for e in self.entities.split(',') if e.strip()]
    
    def get_tables_list(self):
        """Retorna lista de tablas candidatas"""
        return [t.strip() for t in self.candidate_tables.split(',') if t.strip()]
    
    def get_fields_list(self):
        """Retorna lista de campos clave"""
        return [f.strip() for f in self.key_fields.split(',') if f.strip()]
    
    def get_vb6_forms_list(self):
        """Retorna lista de formularios VB6"""
        return [f.strip() for f in self.vb6_forms.split(',') if f.strip()]
    
    def to_training_dict(self):
        """Convierte a diccionario para entrenamiento"""
        return {
            'module': self.module,
            'procedure': self.procedure,
            'description': self.description,
            'vb6_forms': self.get_vb6_forms_list(),
            'vb6_modules': [m.strip() for m in self.vb6_modules.split(',') if m.strip()],
            'entities': self.get_entities_list(),
            'tables': self.get_tables_list(),
            'master_table': self.master_table,
            'detail_table': self.detail_table,
            'key_fields': self.get_fields_list(),
            'events': [e.strip() for e in self.relevant_events.split(',') if e.strip()],
            'rules': self.business_rules,
            'validations': self.validations,
            'dependencies': [d.strip() for d in self.dependencies.split(',') if d.strip()],
            'relationships': self.table_relationships,
            'insert_tables': [t.strip() for t in self.insert_tables.split(',') if t.strip()],
            'update_tables': [t.strip() for t in self.update_tables.split(',') if t.strip()],
            'confidence': self.confidence,
            'priority': self.priority
        }

