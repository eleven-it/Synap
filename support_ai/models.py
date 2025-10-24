from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator


class SupportTicket(models.Model):
    """Modelo principal para tickets de soporte"""
    
    PRIORITY_CHOICES = [
        ('low', _('Baja')),
        ('medium', _('Media')),
        ('high', _('Alta')),
        ('urgent', _('Urgente')),
    ]
    
    STATUS_CHOICES = [
        ('open', _('Abierto')),
        ('in_progress', _('En Progreso')),
        ('waiting_customer', _('Esperando Cliente')),
        ('waiting_agent', _('Esperando Agente')),
        ('resolved', _('Resuelto')),
        ('closed', _('Cerrado')),
    ]
    
    CHANNEL_CHOICES = [
        ('web', _('Web')),
        ('email', _('Email')),
        ('whatsapp', _('WhatsApp')),
        ('voice', _('Voz')),
    ]
    
    # Identificación básica
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ticket_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # Relaciones principales
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='support_tickets', verbose_name=_('Cliente'))
    assigned_agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets', verbose_name=_('Agente Asignado'))
    
    # Información del ticket
    subject = models.CharField(max_length=200, verbose_name=_('Asunto'))
    description = models.TextField(verbose_name=_('Descripción'))
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name=_('Prioridad'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name=_('Estado'))
    channel = models.CharField(max_length=10, choices=CHANNEL_CHOICES, default='web', verbose_name=_('Canal'))
    
    # IA y automatización
    ai_confidence = models.FloatField(default=0.0, verbose_name=_('Confianza IA'))
    ai_resolved = models.BooleanField(default=False, verbose_name=_('Resuelto por IA'))
    escalation_reason = models.TextField(blank=True, verbose_name=_('Razón de Escalamiento'))
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Fecha Actualización'))
    resolved_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Fecha Resolución'))
    
    # Configuración de SLA
    sla_hours = models.IntegerField(default=24, verbose_name=_('SLA Horas'))
    sla_deadline = models.DateTimeField(null=True, blank=True, verbose_name=_('Deadline SLA'))
    
    class Meta:
        verbose_name = _('Ticket de Soporte')
        verbose_name_plural = _('Tickets de Soporte')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.ticket_number} - {self.subject}"
    
    def save(self, *args, **kwargs):
        if not self.ticket_number:
            # Generar número de ticket único
            last_ticket = SupportTicket.objects.order_by('-id').first()
            if last_ticket and last_ticket.ticket_number:
                try:
                    last_number = int(last_ticket.ticket_number.split('-')[-1])
                    new_number = last_number + 1
                except (ValueError, IndexError):
                    new_number = 1
            else:
                new_number = 1
            
            self.ticket_number = f"TKT-{new_number:06d}"
        
        super().save(*args, **kwargs)


class Conversation(models.Model):
    """Modelo para las conversaciones de soporte"""
    
    MESSAGE_TYPE_CHOICES = [
        ('user', _('Usuario')),
        ('ai', _('IA')),
        ('agent', _('Agente')),
        ('system', _('Sistema')),
    ]
    
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='conversations', verbose_name=_('Ticket'))
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, verbose_name=_('Tipo de Mensaje'))
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Remitente'))
    
    # Contenido del mensaje
    content = models.TextField(verbose_name=_('Contenido'))
    content_processed = models.TextField(blank=True, verbose_name=_('Contenido Procesado'))
    
    # Archivos adjuntos
    attachments = models.JSONField(default=list, blank=True, verbose_name=_('Adjuntos'))
    
    # Metadatos de IA
    ai_agent_used = models.CharField(max_length=50, blank=True, verbose_name=_('Agente IA Utilizado'))
    ai_confidence = models.FloatField(default=0.0, verbose_name=_('Confianza IA'))
    ai_processing_time = models.FloatField(default=0.0, verbose_name=_('Tiempo Procesamiento IA'))
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    read_at = models.DateTimeField(null=True, blank=True, verbose_name=_('Fecha Lectura'))
    
    class Meta:
        verbose_name = _('Conversación')
        verbose_name_plural = _('Conversaciones')
        ordering = ['created_at']
    
    def __str__(self):
        return f"Conversación #{self.ticket.ticket_number} - {self.message_type}"


class AIAgent(models.Model):
    """Modelo para configurar agentes de IA especializados"""
    
    AGENT_TYPE_CHOICES = [
        ('supervisor', _('Supervisor General')),
        ('facturacion', _('Facturación')),
        ('configuracion', _('Configuración')),
        ('ventas', _('Ventas')),
        ('inventario', _('Inventario')),
        ('multimodal', _('Multimodal')),
        ('voz', _('Voz')),
    ]
    
    name = models.CharField(max_length=100, verbose_name=_('Nombre'))
    agent_type = models.CharField(max_length=20, choices=AGENT_TYPE_CHOICES, verbose_name=_('Tipo de Agente'))
    description = models.TextField(verbose_name=_('Descripción'))
    
    # Configuración del agente
    is_active = models.BooleanField(default=True, verbose_name=_('Activo'))
    priority = models.IntegerField(default=1, verbose_name=_('Prioridad'))
    
    # Configuración de IA
    model_name = models.CharField(max_length=100, default='gpt-4o', verbose_name=_('Modelo IA'))
    temperature = models.FloatField(default=0.7, verbose_name=_('Temperatura'))
    max_tokens = models.IntegerField(default=1000, verbose_name=_('Máximo Tokens'))
    
    # Prompt y contexto
    system_prompt = models.TextField(verbose_name=_('Prompt del Sistema'))
    context_rules = models.JSONField(default=dict, blank=True, verbose_name=_('Reglas de Contexto'))
    
    # Métricas
    total_conversations = models.IntegerField(default=0, verbose_name=_('Total Conversaciones'))
    success_rate = models.FloatField(default=0.0, verbose_name=_('Tasa de Éxito'))
    avg_response_time = models.FloatField(default=0.0, verbose_name=_('Tiempo Respuesta Promedio'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Fecha Actualización'))
    
    class Meta:
        verbose_name = _('Agente IA')
        verbose_name_plural = _('Agentes IA')
        ordering = ['priority', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_agent_type_display()})"


class SupportConfiguration(models.Model):
    """Modelo para configuraciones globales del sistema de soporte"""
    
    # Configuración general
    auto_assign_tickets = models.BooleanField(default=True, verbose_name=_('Asignación Automática'))
    enable_ai_responses = models.BooleanField(default=True, verbose_name=_('Respuestas IA Habilitadas'))
    enable_voice_input = models.BooleanField(default=True, verbose_name=_('Entrada de Voz Habilitada'))
    enable_file_upload = models.BooleanField(default=True, verbose_name=_('Subida de Archivos Habilitada'))
    
    # Configuración de escalamiento
    ai_confidence_threshold = models.FloatField(default=0.7, verbose_name=_('Umbral Confianza IA'))
    max_ai_conversations = models.IntegerField(default=5, verbose_name=_('Máximo Conversaciones IA'))
    escalation_keywords = models.JSONField(default=list, blank=True, verbose_name=_('Palabras Clave Escalamiento'))
    
    # Configuración de canales
    web_enabled = models.BooleanField(default=True, verbose_name=_('Web Habilitado'))
    email_enabled = models.BooleanField(default=True, verbose_name=_('Email Habilitado'))
    whatsapp_enabled = models.BooleanField(default=False, verbose_name=_('WhatsApp Habilitado'))
    voice_enabled = models.BooleanField(default=True, verbose_name=_('Voz Habilitado'))
    
    # Configuración de archivos
    max_file_size = models.IntegerField(default=10, verbose_name=_('Tamaño Máximo Archivo (MB)'))
    allowed_file_types = models.JSONField(default=list, blank=True, verbose_name=_('Tipos de Archivo Permitidos'))
    
    # Configuración de SLA
    default_sla_hours = models.IntegerField(default=24, verbose_name=_('SLA Horas por Defecto'))
    business_hours = models.JSONField(default=dict, blank=True, verbose_name=_('Horarios de Negocio'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Fecha Actualización'))
    
    class Meta:
        verbose_name = _('Configuración de Soporte')
        verbose_name_plural = _('Configuraciones de Soporte')
    
    def __str__(self):
        return "Configuración Global de Soporte"


class SystemSettings(models.Model):
    """
    Configuraciones del sistema para IA y otros parámetros globales
    """
    # Configuración de IA
    ai_model = models.CharField(
        max_length=50,
        choices=[
            ('gpt-4o-mini', 'GPT-4o Mini'),
            ('gpt-4o', 'GPT-4o'),
            ('claude-3-haiku', 'Claude 3 Haiku'),
            ('claude-3-sonnet', 'Claude 3 Sonnet'),
        ],
        default='gpt-4o-mini',
        verbose_name=_('Modelo de IA')
    )
    
    daily_cost_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=10.00,
        verbose_name=_('Límite de Costo Diario')
    )
    
    auto_assignment = models.BooleanField(
        default=True,
        verbose_name=_('Asignación Automática de Tickets')
    )
    
    max_response_time = models.PositiveIntegerField(
        default=24,
        verbose_name=_('Tiempo Máximo de Respuesta (horas)')
    )
    
    # Configuración de caché
    enable_cache = models.BooleanField(default=True, verbose_name=_('Caché Habilitado'))
    cache_ttl = models.PositiveIntegerField(default=3600, verbose_name=_('TTL de Caché (segundos)'))
    
    # Configuración de métricas
    enable_metrics = models.BooleanField(default=True, verbose_name=_('Métricas Habilitadas'))
    metrics_retention_days = models.PositiveIntegerField(default=90, verbose_name=_('Retención de Métricas (días)'))
    
    # Configuración de seguridad
    max_login_attempts = models.PositiveIntegerField(default=5, verbose_name=_('Máximo Intentos de Login'))
    session_timeout = models.PositiveIntegerField(default=480, verbose_name=_('Timeout de Sesión (minutos)'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración del Sistema"
        verbose_name_plural = "Configuraciones del Sistema"
    
    def __str__(self):
        return "Configuración del Sistema"
    
    @classmethod
    def get_settings(cls):
        """Obtiene la configuración del sistema, creando una por defecto si no existe"""
        settings, created = cls.objects.get_or_create(
            id=1,
            defaults={
                'ai_model': 'gpt-4o-mini',
                'daily_cost_limit': 10.00,
                'auto_assignment': True,
                'max_response_time': 24,
                'enable_cache': True,
                'cache_ttl': 3600,
                'enable_metrics': True,
                'metrics_retention_days': 90,
                'max_login_attempts': 5,
                'session_timeout': 480,
            }
        )
        return settings


class SupportAttachment(models.Model):
    """Modelo para archivos adjuntos en conversaciones"""
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='support_attachments', verbose_name=_('Conversación'))
    
    file_name = models.CharField(max_length=255, verbose_name=_('Nombre del Archivo'))
    file_path = models.CharField(max_length=500, verbose_name=_('Ruta del Archivo'))
    file_size = models.IntegerField(verbose_name=_('Tamaño del Archivo'))
    file_type = models.CharField(max_length=100, verbose_name=_('Tipo de Archivo'))
    mime_type = models.CharField(max_length=100, verbose_name=_('Tipo MIME'))
    
    # Procesamiento de IA
    ocr_text = models.TextField(blank=True, verbose_name=_('Texto OCR'))
    ai_analysis = models.JSONField(default=dict, blank=True, verbose_name=_('Análisis IA'))
    processed = models.BooleanField(default=False, verbose_name=_('Procesado'))
    
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Subida'))
    
    class Meta:
        verbose_name = _('Adjunto de Soporte')
        verbose_name_plural = _('Adjuntos de Soporte')
    
    def __str__(self):
        return f"{self.file_name} - {self.conversation}"


class SupportMetrics(models.Model):
    """Modelo para métricas y analytics del sistema de soporte"""
    
    date = models.DateField(verbose_name=_('Fecha'))
    
    # Métricas generales
    total_tickets = models.IntegerField(default=0, verbose_name=_('Total Tickets'))
    resolved_tickets = models.IntegerField(default=0, verbose_name=_('Tickets Resueltos'))
    ai_resolved_tickets = models.IntegerField(default=0, verbose_name=_('Tickets Resueltos por IA'))
    escalated_tickets = models.IntegerField(default=0, verbose_name=_('Tickets Escalados'))
    
    # Métricas de tiempo
    avg_resolution_time = models.FloatField(default=0.0, verbose_name=_('Tiempo Resolución Promedio'))
    avg_first_response_time = models.FloatField(default=0.0, verbose_name=_('Tiempo Primera Respuesta Promedio'))
    
    # Métricas de satisfacción
    customer_satisfaction = models.FloatField(default=0.0, verbose_name=_('Satisfacción del Cliente'))
    total_ratings = models.IntegerField(default=0, verbose_name=_('Total Calificaciones'))
    
    # Métricas de IA
    ai_accuracy = models.FloatField(default=0.0, verbose_name=_('Precisión IA'))
    ai_usage_rate = models.FloatField(default=0.0, verbose_name=_('Tasa de Uso IA'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    
    class Meta:
        verbose_name = _('Métrica de Soporte')
        verbose_name_plural = _('Métricas de Soporte')
        unique_together = ['date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Métricas {self.date}"


class KnowledgeBase(models.Model):
    """Base de conocimientos dinámica con IA"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    category = models.CharField(max_length=100, choices=[
        ('facturacion', 'Facturación'),
        ('configuracion', 'Configuración'),
        ('ventas', 'Ventas'),
        ('inventario', 'Inventario'),
        ('general', 'General'),
    ])
    tags = models.JSONField(default=list, blank=True)
    ai_generated = models.BooleanField(default=False)
    usage_count = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Base de Conocimientos"
        verbose_name_plural = "Bases de Conocimientos"
    
    def __str__(self):
        return self.title


class OnboardingFlow(models.Model):
    """Flujos de onboarding inteligente"""
    name = models.CharField(max_length=100)
    description = models.TextField()
    user_type = models.CharField(max_length=50, choices=[
        ('new_customer', 'Cliente Nuevo'),
        ('advanced_customer', 'Cliente Avanzado'),
        ('new_agent', 'Agente Nuevo'),
        ('experienced_agent', 'Agente Experimentado'),
    ])
    steps = models.JSONField(default=list)  # Lista de pasos del onboarding
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Flujo de Onboarding"
        verbose_name_plural = "Flujos de Onboarding"
    
    def __str__(self):
        return self.name


class CustomerProfile(models.Model):
    """Perfil del cliente para personalización"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    experience_level = models.CharField(max_length=50, choices=[
        ('beginner', 'Principiante'),
        ('intermediate', 'Intermedio'),
        ('advanced', 'Avanzado'),
        ('expert', 'Experto'),
    ], default='beginner')
    preferred_channel = models.CharField(max_length=50, choices=[
        ('web', 'Web'),
        ('email', 'Email'),
        ('whatsapp', 'WhatsApp'),
        ('voice', 'Voz'),
    ], default='web')
    communication_style = models.CharField(max_length=50, choices=[
        ('formal', 'Formal'),
        ('casual', 'Casual'),
        ('technical', 'Técnico'),
        ('friendly', 'Amigable'),
    ], default='friendly')
    onboarding_completed = models.BooleanField(default=False)
    last_interaction = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Perfil de Cliente"
        verbose_name_plural = "Perfiles de Clientes"
    
    def __str__(self):
        return f"Perfil de {self.user.get_full_name()}"


class AgentCoaching(models.Model):
    """Sistema de coaching para agentes"""
    agent = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    session_date = models.DateTimeField(auto_now_add=True)
    conversation_id = models.CharField(max_length=100)
    feedback_type = models.CharField(max_length=50, choices=[
        ('tone', 'Tono de Voz'),
        ('speed', 'Velocidad'),
        ('empathy', 'Empatía'),
        ('technical', 'Conocimiento Técnico'),
        ('resolution', 'Resolución'),
    ])
    feedback_message = models.TextField()
    suggested_improvement = models.TextField()
    confidence_score = models.FloatField(default=0.0)
    is_implemented = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Coaching de Agente"
        verbose_name_plural = "Coaching de Agentes"
    
    def __str__(self):
        return f"Coaching {self.agent.get_full_name()} - {self.session_date}"


class ProactiveAlert(models.Model):
    """Alertas proactivas basadas en IA"""
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=50, choices=[
        ('license_expiry', 'Expiración de Licencia'),
        ('usage_drop', 'Caída de Uso'),
        ('error_pattern', 'Patrón de Errores'),
        ('feature_adoption', 'Adopción de Funcionalidad'),
        ('support_needed', 'Soporte Necesario'),
    ])
    title = models.CharField(max_length=200)
    description = models.TextField()
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ], default='medium')
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Alerta Proactiva"
        verbose_name_plural = "Alertas Proactivas"
    
    def __str__(self):
        return f"{self.title} - {self.customer.get_full_name()}"


class ContinuousLearning(models.Model):
    """Sistema de aprendizaje continuo"""
    source_type = models.CharField(max_length=50, choices=[
        ('conversation', 'Conversación'),
        ('ticket', 'Ticket'),
        ('feedback', 'Feedback'),
        ('correction', 'Corrección'),
    ])
    source_id = models.CharField(max_length=100)
    learning_data = models.JSONField()  # Datos de aprendizaje
    agent_used = models.CharField(max_length=100)
    confidence_before = models.FloatField(default=0.0)
    confidence_after = models.FloatField(default=0.0)
    improvement_score = models.FloatField(default=0.0)
    is_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Aprendizaje Continuo"
        verbose_name_plural = "Aprendizaje Continuo"
    
    def __str__(self):
        return f"Aprendizaje {self.source_type} - {self.created_at}"


class BusinessInsight(models.Model):
    """Insights de negocio generados por IA"""
    insight_type = models.CharField(max_length=50, choices=[
        ('frustration_pattern', 'Patrón de Frustración'),
        ('feature_request', 'Solicitud de Funcionalidad'),
        ('usage_trend', 'Tendencia de Uso'),
        ('support_optimization', 'Optimización de Soporte'),
        ('product_improvement', 'Mejora de Producto'),
    ])
    title = models.CharField(max_length=200)
    description = models.TextField()
    data_evidence = models.JSONField()  # Evidencia de datos
    impact_score = models.FloatField(default=0.0)
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ], default='medium')
    is_actioned = models.BooleanField(default=False)
    action_taken = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Insight de Negocio"
        verbose_name_plural = "Insights de Negocio"
    
    def __str__(self):
        return self.title 


class CustomerSatisfaction(models.Model):
    """Sistema de satisfacción del cliente con análisis de sentimientos"""
    
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='satisfaction_ratings', verbose_name=_('Ticket'))
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='satisfaction_ratings', verbose_name=_('Cliente'))
    
    # Calificaciones
    overall_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Calificación General')
    )
    
    response_time_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Calificación Tiempo de Respuesta')
    )
    
    solution_quality_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Calificación Calidad de Solución')
    )
    
    agent_helpfulness_rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name=_('Calificación Utilidad del Agente')
    )
    
    # Análisis de sentimientos
    sentiment_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(-1), MaxValueValidator(1)],
        verbose_name=_('Puntuación de Sentimiento')
    )
    
    sentiment_label = models.CharField(
        max_length=20,
        choices=[
            ('very_negative', 'Muy Negativo'),
            ('negative', 'Negativo'),
            ('neutral', 'Neutral'),
            ('positive', 'Positivo'),
            ('very_positive', 'Muy Positivo'),
        ],
        verbose_name=_('Etiqueta de Sentimiento')
    )
    
    # Comentarios
    comment = models.TextField(blank=True, verbose_name=_('Comentario'))
    ai_analysis = models.JSONField(default=dict, blank=True, verbose_name=_('Análisis IA'))
    
    # Metadatos
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    
    class Meta:
        verbose_name = _('Satisfacción del Cliente')
        verbose_name_plural = _('Satisfacciones de Clientes')
        unique_together = ['ticket', 'customer']
    
    def __str__(self):
        return f"Satisfacción #{self.ticket.ticket_number} - {self.overall_rating}/5"


class EscalationRule(models.Model):
    """Reglas de escalamiento inteligente basadas en IA"""
    
    name = models.CharField(max_length=100, verbose_name=_('Nombre'))
    description = models.TextField(verbose_name=_('Descripción'))
    
    # Condiciones de activación
    priority_threshold = models.CharField(
        max_length=10,
        choices=SupportTicket.PRIORITY_CHOICES,
        verbose_name=_('Umbral de Prioridad')
    )
    
    ai_confidence_threshold = models.FloatField(
        default=0.7,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        verbose_name=_('Umbral Confianza IA')
    )
    
    sentiment_threshold = models.FloatField(
        default=-0.3,
        validators=[MinValueValidator(-1), MaxValueValidator(1)],
        verbose_name=_('Umbral Sentimiento')
    )
    
    response_time_threshold = models.PositiveIntegerField(
        default=60,
        verbose_name=_('Umbral Tiempo Respuesta (minutos)')
    )
    
    # Acciones de escalamiento
    escalation_type = models.CharField(
        max_length=20,
        choices=[
            ('human_agent', 'Agente Humano'),
            ('supervisor', 'Supervisor'),
            ('specialist', 'Especialista'),
            ('emergency', 'Emergencia'),
        ],
        verbose_name=_('Tipo de Escalamiento')
    )
    
    target_department = models.CharField(max_length=100, blank=True, verbose_name=_('Departamento Objetivo'))
    notification_channels = models.JSONField(default=list, verbose_name=_('Canales de Notificación'))
    
    # Configuración
    is_active = models.BooleanField(default=True, verbose_name=_('Activa'))
    auto_trigger = models.BooleanField(default=True, verbose_name=_('Activación Automática'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Fecha Actualización'))
    
    class Meta:
        verbose_name = _('Regla de Escalamiento')
        verbose_name_plural = _('Reglas de Escalamiento')
    
    def __str__(self):
        return self.name


class AutomatedWorkflow(models.Model):
    """Flujos de trabajo automatizados para tickets"""
    
    name = models.CharField(max_length=100, verbose_name=_('Nombre'))
    description = models.TextField(verbose_name=_('Descripción'))
    
    # Triggers
    trigger_type = models.CharField(
        max_length=20,
        choices=[
            ('ticket_created', 'Ticket Creado'),
            ('priority_changed', 'Prioridad Cambiada'),
            ('status_changed', 'Estado Cambiado'),
            ('time_elapsed', 'Tiempo Transcurrido'),
            ('ai_confidence_low', 'Confianza IA Baja'),
            ('sentiment_negative', 'Sentimiento Negativo'),
        ],
        verbose_name=_('Tipo de Trigger')
    )
    
    trigger_conditions = models.JSONField(default=dict, verbose_name=_('Condiciones de Trigger'))
    
    # Acciones
    actions = models.JSONField(default=list, verbose_name=_('Acciones'))
    
    # Configuración
    is_active = models.BooleanField(default=True, verbose_name=_('Activo'))
    execution_order = models.PositiveIntegerField(default=1, verbose_name=_('Orden de Ejecución'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Fecha Actualización'))
    
    class Meta:
        verbose_name = _('Flujo de Trabajo Automatizado')
        verbose_name_plural = _('Flujos de Trabajo Automatizados')
        ordering = ['execution_order', 'name']
    
    def __str__(self):
        return self.name


class IntegrationWebhook(models.Model):
    """Webhooks para integraciones con sistemas externos"""
    
    name = models.CharField(max_length=100, verbose_name=_('Nombre'))
    description = models.TextField(verbose_name=_('Descripción'))
    
    # Configuración del webhook
    url = models.URLField(verbose_name=_('URL del Webhook'))
    method = models.CharField(
        max_length=10,
        choices=[
            ('POST', 'POST'),
            ('PUT', 'PUT'),
            ('PATCH', 'PATCH'),
        ],
        default='POST',
        verbose_name=_('Método HTTP')
    )
    
    headers = models.JSONField(default=dict, verbose_name=_('Headers'))
    payload_template = models.TextField(verbose_name=_('Plantilla de Payload'))
    
    # Eventos que activan el webhook
    events = models.JSONField(default=list, verbose_name=_('Eventos'))
    
    # Configuración de seguridad
    secret_key = models.CharField(max_length=255, blank=True, verbose_name=_('Clave Secreta'))
    is_active = models.BooleanField(default=True, verbose_name=_('Activo'))
    
    # Métricas
    success_count = models.PositiveIntegerField(default=0, verbose_name=_('Éxitos'))
    failure_count = models.PositiveIntegerField(default=0, verbose_name=_('Fallos'))
    last_triggered = models.DateTimeField(null=True, blank=True, verbose_name=_('Último Activado'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Fecha Actualización'))
    
    class Meta:
        verbose_name = _('Webhook de Integración')
        verbose_name_plural = _('Webhooks de Integración')
    
    def __str__(self):
        return self.name


class TicketTemplate(models.Model):
    """Plantillas de tickets para casos comunes"""
    
    name = models.CharField(max_length=100, verbose_name=_('Nombre'))
    description = models.TextField(verbose_name=_('Descripción'))
    
    # Categorización
    category = models.CharField(max_length=100, verbose_name=_('Categoría'))
    tags = models.JSONField(default=list, verbose_name=_('Etiquetas'))
    
    # Contenido de la plantilla
    subject_template = models.CharField(max_length=200, verbose_name=_('Plantilla de Asunto'))
    description_template = models.TextField(verbose_name=_('Plantilla de Descripción'))
    
    # Configuración
    priority = models.CharField(
        max_length=10,
        choices=SupportTicket.PRIORITY_CHOICES,
        default='medium',
        verbose_name=_('Prioridad por Defecto')
    )
    
    sla_hours = models.PositiveIntegerField(default=24, verbose_name=_('SLA Horas'))
    
    # Variables disponibles
    available_variables = models.JSONField(default=list, verbose_name=_('Variables Disponibles'))
    
    # Configuración
    is_active = models.BooleanField(default=True, verbose_name=_('Activa'))
    usage_count = models.PositiveIntegerField(default=0, verbose_name=_('Cantidad de Uso'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Fecha Actualización'))
    
    class Meta:
        verbose_name = _('Plantilla de Ticket')
        verbose_name_plural = _('Plantillas de Tickets')
    
    def __str__(self):
        return self.name


class CustomerJourney(models.Model):
    """Seguimiento del journey del cliente"""
    
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='journey_events', verbose_name=_('Cliente'))
    
    # Evento del journey
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('first_contact', 'Primer Contacto'),
            ('ticket_created', 'Ticket Creado'),
            ('ai_interaction', 'Interacción IA'),
            ('human_escalation', 'Escalamiento Humano'),
            ('resolution', 'Resolución'),
            ('feedback', 'Feedback'),
            ('follow_up', 'Seguimiento'),
        ],
        verbose_name=_('Tipo de Evento')
    )
    
    # Detalles del evento
    event_data = models.JSONField(default=dict, verbose_name=_('Datos del Evento'))
    
    # Relaciones
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, null=True, blank=True, related_name='journey_events', verbose_name=_('Ticket'))
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, null=True, blank=True, related_name='journey_events', verbose_name=_('Conversación'))
    
    # Análisis IA
    ai_insights = models.JSONField(default=dict, blank=True, verbose_name=_('Insights IA'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    
    class Meta:
        verbose_name = _('Evento del Journey del Cliente')
        verbose_name_plural = _('Eventos del Journey del Cliente')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.customer.get_full_name()} - {self.get_event_type_display()}"


class PredictiveAnalytics(models.Model):
    """Analytics predictivos para optimización del soporte"""
    
    date = models.DateField(verbose_name=_('Fecha'))
    
    # Predicciones
    predicted_ticket_volume = models.PositiveIntegerField(verbose_name=_('Volumen Predicho de Tickets'))
    predicted_escalation_rate = models.FloatField(verbose_name=_('Tasa Predicha de Escalamiento'))
    predicted_resolution_time = models.FloatField(verbose_name=_('Tiempo Predicho de Resolución'))
    
    # Factores de predicción
    seasonal_factor = models.FloatField(default=1.0, verbose_name=_('Factor Estacional'))
    trend_factor = models.FloatField(default=1.0, verbose_name=_('Factor de Tendencia'))
    external_factors = models.JSONField(default=dict, verbose_name=_('Factores Externos'))
    
    # Métricas de precisión
    accuracy_score = models.FloatField(default=0.0, verbose_name=_('Puntuación de Precisión'))
    confidence_interval = models.FloatField(default=0.0, verbose_name=_('Intervalo de Confianza'))
    
    # Configuración
    model_version = models.CharField(max_length=20, verbose_name=_('Versión del Modelo'))
    features_used = models.JSONField(default=list, verbose_name=_('Características Utilizadas'))
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Fecha Creación'))
    
    class Meta:
        verbose_name = _('Analytics Predictivo')
        verbose_name_plural = _('Analytics Predictivos')
        unique_together = ['date']
        ordering = ['-date']
    
    def __str__(self):
        return f"Predicciones {self.date}"


class Notification(models.Model):
    """
    Notificaciones push para usuarios
    """
    NOTIFICATION_TYPES = [
        ('ticket_created', 'Ticket Creado'),
        ('ticket_updated', 'Ticket Actualizado'),
        ('ticket_assigned', 'Ticket Asignado'),
        ('message_received', 'Mensaje Recibido'),
        ('ticket_resolved', 'Ticket Resuelto'),
        ('system_alert', 'Alerta del Sistema'),
        ('reminder', 'Recordatorio'),
    ]
    
    PRIORITY_LEVELS = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('urgent', 'Urgente'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    priority = models.CharField(max_length=10, choices=PRIORITY_LEVELS, default='medium')
    is_read = models.BooleanField(default=False)
    is_sent = models.BooleanField(default=False)
    data = models.JSONField(default=dict, blank=True)  # Datos adicionales
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.user.email}"
    
    def mark_as_read(self):
        """Marca la notificación como leída"""
        from django.utils import timezone
        self.is_read = True
        self.read_at = timezone.now()
        self.save()
    
    def mark_as_sent(self):
        """Marca la notificación como enviada"""
        self.is_sent = True
        self.save()


class UserPreference(models.Model):
    """
    Preferencias de notificación del usuario
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notification_preferences')
    
    # Preferencias de notificación
    email_notifications = models.BooleanField(default=True)
    push_notifications = models.BooleanField(default=True)
    sms_notifications = models.BooleanField(default=False)
    
    # Tipos de notificación
    ticket_updates = models.BooleanField(default=True)
    new_messages = models.BooleanField(default=True)
    system_alerts = models.BooleanField(default=True)
    reminders = models.BooleanField(default=True)
    
    # Frecuencia
    notification_frequency = models.CharField(
        max_length=20,
        choices=[
            ('immediate', 'Inmediata'),
            ('hourly', 'Cada hora'),
            ('daily', 'Diaria'),
            ('weekly', 'Semanal'),
        ],
        default='immediate'
    )
    
    # Horario de silencio
    quiet_hours_start = models.TimeField(null=True, blank=True)
    quiet_hours_end = models.TimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Preferencia de Usuario"
        verbose_name_plural = "Preferencias de Usuario"
    
    def __str__(self):
        return f"Preferencias de {self.user.email}"
    
    def is_quiet_hours(self):
        """Verifica si estamos en horario de silencio"""
        from django.utils import timezone
        now = timezone.now().time()
        
        if not self.quiet_hours_start or not self.quiet_hours_end:
            return False
        
        if self.quiet_hours_start <= self.quiet_hours_end:
            return self.quiet_hours_start <= now <= self.quiet_hours_end
        else:  # Horario que cruza la medianoche
            return now >= self.quiet_hours_start or now <= self.quiet_hours_end


class UserSettings(models.Model):
    """
    Configuraciones generales del usuario
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_settings')
    
    # Configuraciones de interfaz
    language = models.CharField(
        max_length=10,
        choices=[
            ('es', 'Español'),
            ('en', 'English'),
            ('fr', 'Français'),
        ],
        default='es',
        verbose_name=_('Idioma')
    )
    
    theme = models.CharField(
        max_length=10,
        choices=[
            ('light', 'Claro'),
            ('dark', 'Oscuro'),
            ('auto', 'Automático'),
        ],
        default='light',
        verbose_name=_('Tema')
    )
    
    # Configuraciones de notificaciones
    notifications_enabled = models.BooleanField(default=True, verbose_name=_('Notificaciones Habilitadas'))
    push_notifications = models.BooleanField(default=True, verbose_name=_('Notificaciones Push'))
    
    # Configuraciones de privacidad
    data_collection = models.BooleanField(default=True, verbose_name=_('Recolección de Datos'))
    analytics_tracking = models.BooleanField(default=True, verbose_name=_('Seguimiento Analítico'))
    
    # Configuraciones de accesibilidad
    font_size = models.CharField(
        max_length=10,
        choices=[
            ('small', 'Pequeña'),
            ('medium', 'Mediana'),
            ('large', 'Grande'),
        ],
        default='medium',
        verbose_name=_('Tamaño de Fuente')
    )
    
    high_contrast = models.BooleanField(default=False, verbose_name=_('Alto Contraste'))
    screen_reader = models.BooleanField(default=False, verbose_name=_('Lector de Pantalla'))
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuración de Usuario"
        verbose_name_plural = "Configuraciones de Usuario"
    
    def __str__(self):
        return f"Configuraciones de {self.user.email}" 