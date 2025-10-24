"""
Modelos para el sistema de agentes dinámicos y modulares
"""

import os
import uuid
import json
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from django.core.validators import FileExtensionValidator
from django.utils import timezone
from django.core.exceptions import ValidationError

User = get_user_model()


class DynamicAgent(models.Model):
    """
    Modelo para agentes dinámicos y modulares
    """
    
    AGENT_STATUS_CHOICES = [
        ('active', _('Activo')),
        ('inactive', _('Inactivo')),
        ('training', _('En Entrenamiento')),
        ('maintenance', _('En Mantenimiento')),
        ('deprecated', _('Deprecado')),
    ]
    
    ESCALATION_LEVEL_CHOICES = [
        (1, _('Nivel 1 - Respuesta Directa')),
        (2, _('Nivel 2 - Respuesta Especializada')),
        (3, _('Nivel 3 - Escalamiento Humano')),
    ]
    
    TONE_CHOICES = [
        ('formal', _('Formal - Profesional y serio')),
        ('friendly', _('Amigable - Profesional pero cercano')),
        ('casual', _('Casual - Relajado y descontracturado')),
        ('enthusiastic', _('Entusiasta - Energético y motivador')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Información básica del agente
    name = models.CharField(_('Nombre del Agente'), max_length=200, unique=True)
    description = models.TextField(_('Descripción'), blank=True)
    module = models.CharField(_('Módulo'), max_length=100, 
                            help_text=_('Módulo funcional: Ventas, Compras, Inventario, etc.'))
    
    # Configuración del agente
    status = models.CharField(_('Estado'), max_length=20, choices=AGENT_STATUS_CHOICES, default='inactive')
    escalation_level = models.IntegerField(_('Nivel de Escalamiento'), choices=ESCALATION_LEVEL_CHOICES, default=1)
    
    # Configuración de entrenamiento
    training_enabled = models.BooleanField(_('Entrenamiento Habilitado'), default=True)
    auto_retrain = models.BooleanField(_('Re-entrenamiento Automático'), default=True)
    confidence_threshold = models.DecimalField(_('Umbral de Confianza'), max_digits=3, decimal_places=2, 
                                            default=0.7, help_text=_('0.00 a 1.00'))
    
    # Configuración de respuestas
    system_prompt = models.TextField(_('Prompt del Sistema'), blank=True,
                                   help_text=_('Prompt base del agente'))
    response_template = models.TextField(_('Plantilla de Respuesta'), blank=True,
                                       help_text=_('Plantilla base para respuestas'))
    safety_guidelines = models.TextField(_('Directrices de Seguridad'), blank=True,
                                       help_text=_('Directrices para evitar respuestas sensibles'))
    
    # Configuración de personalidad
    tone = models.CharField(_('Tono de Comunicación'), max_length=20, choices=TONE_CHOICES, 
                           default='friendly', help_text=_('Tono de comunicación del agente'))
    
    # Metadatos
    version = models.CharField(_('Versión'), max_length=20, default='1.0.0')
    created_at = models.DateTimeField(_('Fecha de Creación'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Fecha de Actualización'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Creado por'))
    
    # Estadísticas
    total_queries = models.PositiveIntegerField(_('Total de Consultas'), default=0)
    successful_responses = models.PositiveIntegerField(_('Respuestas Exitosas'), default=0)
    escalation_count = models.PositiveIntegerField(_('Total de Escalamientos'), default=0)
    last_training_at = models.DateTimeField(_('Último Entrenamiento'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('Agente Dinámico')
        verbose_name_plural = _('Agentes Dinámicos')
        ordering = ['module', 'name']
        indexes = [
            models.Index(fields=['module', 'status']),
            models.Index(fields=['escalation_level', 'status']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.module} (v{self.version})"
    
    @property
    def is_active(self):
        """Verifica si el agente está activo"""
        return self.status == 'active'
    
    @property
    def success_rate(self):
        """Calcula la tasa de éxito del agente"""
        if self.total_queries > 0:
            return (self.successful_responses / self.total_queries) * 100
        return 0.0
    
    @property
    def escalation_rate(self):
        """Calcula la tasa de escalamiento del agente"""
        if self.total_queries > 0:
            return (self.escalation_count / self.total_queries) * 100
        return 0.0
    
    @property
    def can_handle_query(self):
        """Verifica si el agente puede manejar consultas"""
        return (self.is_active and 
                self.training_enabled and 
                self.total_queries < 10000)  # Límite de consultas
    
    def increment_query_count(self, success: bool = True, escalated: bool = False):
        """Incrementa contadores de consultas"""
        self.total_queries += 1
        if success:
            self.successful_responses += 1
        if escalated:
            self.escalation_count += 1
        self.save(update_fields=['total_queries', 'successful_responses', 'escalation_count'])


class AgentDataset(models.Model):
    """
    Modelo para datasets de entrenamiento de agentes
    """
    
    DATASET_TYPE_CHOICES = [
        ('json', _('JSON')),
        ('csv', _('CSV')),
        ('text', _('Texto Plano')),
        ('structured', _('Estructurado')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(DynamicAgent, on_delete=models.CASCADE, related_name='datasets', verbose_name=_('Agente'))
    
    # Información del dataset
    name = models.CharField(_('Nombre del Dataset'), max_length=200)
    description = models.TextField(_('Descripción'), blank=True)
    dataset_type = models.CharField(_('Tipo de Dataset'), max_length=20, choices=DATASET_TYPE_CHOICES)
    
    # Archivo del dataset
    file = models.FileField(_('Archivo del Dataset'), upload_to='agent_datasets/%Y/%m/%d/',
                           validators=[FileExtensionValidator(allowed_extensions=['json', 'csv', 'txt'])],
                           null=True, blank=True)
    
    # Contenido procesado
    content = models.JSONField(_('Contenido Procesado'), default=dict, blank=True,
                              help_text=_('Contenido del dataset procesado'))
    
    # Metadatos
    file_size_mb = models.DecimalField(_('Tamaño del Archivo (MB)'), max_digits=8, decimal_places=2, blank=True, null=True)
    uploaded_at = models.DateTimeField(_('Fecha de Subida'), auto_now_add=True)
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Subido por'))
    
    # Estado de procesamiento
    is_processed = models.BooleanField(_('Procesado'), default=False)
    processing_errors = models.TextField(_('Errores de Procesamiento'), blank=True)
    
    # Versión del dataset
    version = models.CharField(_('Versión'), max_length=20, default='1.0.0')
    is_active = models.BooleanField(_('Activo'), default=True)
    
    class Meta:
        verbose_name = _('Dataset de Agente')
        verbose_name_plural = _('Datasets de Agentes')
        ordering = ['-uploaded_at']
        unique_together = ['agent', 'name', 'version']
    
    def __str__(self):
        return f"{self.name} v{self.version} - {self.agent.name}"
    
    def save(self, *args, **kwargs):
        """Calcula el tamaño del archivo antes de guardar"""
        if self.file and not self.file_size_mb:
            self.file_size_mb = self.file.size / (1024 * 1024)
        super().save(*args, **kwargs)
    
    def process_dataset(self):
        """Procesa el dataset según su tipo"""
        try:
            if self.dataset_type == 'json':
                self._process_json_dataset()
            elif self.dataset_type == 'csv':
                self._process_csv_dataset()
            elif self.dataset_type == 'text':
                self._process_text_dataset()
            else:
                self._process_structured_dataset()
            
            self.is_processed = True
            self.save(update_fields=['content', 'is_processed'])
            
        except Exception as e:
            self.processing_errors = str(e)
            self.save(update_fields=['processing_errors'])
            raise
    
    def _process_json_dataset(self):
        """Procesa dataset JSON"""
        import json
        with open(self.file.path, 'r', encoding='utf-8') as f:
            self.content = json.load(f)
    
    def _process_csv_dataset(self):
        """Procesa dataset CSV"""
        import csv
        content = []
        with open(self.file.path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                content.append(row)
        self.content = {'rows': content, 'columns': list(content[0].keys()) if content else []}
    
    def _process_text_dataset(self):
        """Procesa dataset de texto plano"""
        with open(self.file.path, 'r', encoding='utf-8') as f:
            text_content = f.read()
        self.content = {'text': text_content, 'lines': text_content.split('\n')}
    
    def _process_structured_dataset(self):
        """Procesa dataset estructurado"""
        # Implementar procesamiento personalizado según necesidades
        self.content = {'type': 'structured', 'processed': True}


class AgentTrainingSession(models.Model):
    """
    Modelo para sesiones de entrenamiento de agentes
    """
    
    SESSION_STATUS_CHOICES = [
        ('scheduled', _('Programada')),
        ('running', _('Ejecutándose')),
        ('completed', _('Completada')),
        ('failed', _('Falló')),
        ('cancelled', _('Cancelada')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(DynamicAgent, on_delete=models.CASCADE, related_name='training_sessions', verbose_name=_('Agente'))
    
    # Configuración de la sesión
    name = models.CharField(_('Nombre de la Sesión'), max_length=200, default='')
    description = models.TextField(_('Descripción'), blank=True)
    
    # Datasets a procesar
    datasets = models.ManyToManyField(AgentDataset, verbose_name=_('Datasets'))
    
    # Estado y progreso
    status = models.CharField(_('Estado'), max_length=20, choices=SESSION_STATUS_CHOICES, default='scheduled')
    progress_percentage = models.PositiveIntegerField(_('Progreso (%)'), default=0)
    
    # Fechas
    scheduled_at = models.DateTimeField(_('Programado para'), blank=True, null=True)
    started_at = models.DateTimeField(_('Iniciado en'), blank=True, null=True)
    completed_at = models.DateTimeField(_('Completado en'), blank=True, null=True)
    
    # Resultados
    total_datasets = models.PositiveIntegerField(_('Total de Datasets'), default=0)
    processed_datasets = models.PositiveIntegerField(_('Datasets Procesados'), default=0)
    successful_datasets = models.PositiveIntegerField(_('Datasets Exitosos'), default=0)
    failed_datasets = models.PositiveIntegerField(_('Datasets Fallidos'), default=0)
    
    # Metadatos
    created_at = models.DateTimeField(_('Fecha de Creación'), auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Creado por'))
    notes = models.TextField(_('Notas'), blank=True)
    
    class Meta:
        verbose_name = _('Sesión de Entrenamiento de Agente')
        verbose_name_plural = _('Sesiones de Entrenamiento de Agentes')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.agent.name}"
    
    @property
    def duration(self):
        """Calcula la duración de la sesión"""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def success_rate(self):
        """Calcula la tasa de éxito"""
        if self.total_datasets > 0:
            return (self.successful_datasets / self.total_datasets) * 100
        return 0


class AgentQuery(models.Model):
    """
    Modelo para consultas realizadas a agentes
    """
    
    QUERY_STATUS_CHOICES = [
        ('pending', _('Pendiente')),
        ('processing', _('Procesando')),
        ('completed', _('Completada')),
        ('failed', _('Falló')),
        ('escalated', _('Escalada')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agent = models.ForeignKey(DynamicAgent, on_delete=models.CASCADE, related_name='queries', verbose_name=_('Agente'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='agent_queries', verbose_name=_('Usuario'))
    
    # Contenido de la consulta
    query_text = models.TextField(_('Texto de la Consulta'))
    query_context = models.JSONField(_('Contexto de la Consulta'), default=dict, blank=True)
    
    # Respuesta del agente
    response_text = models.TextField(_('Respuesta del Agente'), blank=True)
    confidence_score = models.FloatField(_('Puntuación de Confianza'), default=0.0)
    
    # Estado y metadatos
    escalated = models.BooleanField(_('Escalado'), default=False)
    escalation_reason = models.TextField(_('Razón de Escalamiento'), blank=True)
    escalated_to = models.ForeignKey(DynamicAgent, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='escalated_queries', verbose_name=_('Escalado a'))
    
    # Tiempo de procesamiento
    processing_time_ms = models.PositiveIntegerField(_('Tiempo de Procesamiento (ms)'), default=0)
    
    # Timestamps
    created_at = models.DateTimeField(_('Fecha de Creación'), auto_now_add=True)
    processed_at = models.DateTimeField(_('Fecha de Procesamiento'), blank=True, null=True)
    escalated_at = models.DateTimeField(_('Fecha de Escalamiento'), blank=True, null=True)
    
    class Meta:
        verbose_name = _('Consulta de Agente')
        verbose_name_plural = _('Consultas de Agentes')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['agent', 'escalated']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self):
        user_email = self.user.email if self.user else 'Usuario Anónimo'
        return f"Consulta de {user_email} a {self.agent.name} - {self.created_at.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def is_escalated(self):
        """Verifica si la consulta fue escalada"""
        return self.escalated


class AgentRoutingRule(models.Model):
    """
    Modelo para reglas de enrutamiento automático de consultas
    """
    
    RULE_TYPE_CHOICES = [
        ('keyword', _('Palabra Clave')),
        ('context', _('Contexto')),
        ('module', _('Módulo')),
        ('pattern', _('Patrón')),
        ('fallback', _('Fallback')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Configuración de la regla
    name = models.CharField(_('Nombre de la Regla'), max_length=200)
    rule_type = models.CharField(_('Tipo de Regla'), max_length=20, choices=RULE_TYPE_CHOICES)
    priority = models.PositiveIntegerField(_('Prioridad'), default=1, 
                                         help_text=_('Mayor número = mayor prioridad'))
    
    # Condiciones de activación
    keywords = models.JSONField(_('Palabras Clave'), default=list, blank=True,
                               help_text=_('Lista de palabras clave para activar la regla'))
    context_patterns = models.JSONField(_('Patrones de Contexto'), default=dict, blank=True)
    module_match = models.CharField(_('Módulo Objetivo'), max_length=100, blank=True)
    
    # Agente objetivo
    target_agent = models.ForeignKey(DynamicAgent, on_delete=models.CASCADE, 
                                   related_name='routing_rules', verbose_name=_('Agente Objetivo'))
    
    # Configuración
    is_active = models.BooleanField(_('Activa'), default=True)
    auto_escalate = models.BooleanField(_('Escalamiento Automático'), default=False)
    escalation_threshold = models.DecimalField(_('Umbral de Escalamiento'), max_digits=3, decimal_places=2, 
                                            default=0.5, help_text=_('Confianza mínima para escalar'))
    
    # Metadatos
    created_at = models.DateTimeField(_('Fecha de Creación'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Fecha de Actualización'), auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Creado por'))
    
    class Meta:
        verbose_name = _('Regla de Enrutamiento')
        verbose_name_plural = _('Reglas de Enrutamiento')
        ordering = ['-priority', 'name']
    
    def __str__(self):
        return f"{self.name} -> {self.target_agent.name}"
    
    def matches_query(self, query_text: str, context: dict = None) -> bool:
        """
        Verifica si la regla coincide con una consulta
        
        Args:
            query_text: Texto de la consulta
            context: Contexto adicional
            
        Returns:
            True si la regla coincide
        """
        if not self.is_active:
            return False
        
        query_lower = query_text.lower()
        
        # Verificar palabras clave
        if self.keywords:
            if not any(keyword.lower() in query_lower for keyword in self.keywords):
                return False
        
        # Verificar contexto
        if self.context_patterns and context:
            for key, value in self.context_patterns.items():
                if key not in context or context[key] != value:
                    return False
        
        # Verificar módulo
        if self.module_match:
            if self.module_match.lower() not in query_lower:
                return False
        
        return True


class UserProductAccess(models.Model):
    """
    Modelo para controlar acceso de usuarios a productos
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='product_access', verbose_name=_('Usuario'))
    
    # Producto al que tiene acceso
    product_name = models.CharField(_('Nombre del Producto'), max_length=200, default='')
    product_version = models.CharField(_('Versión del Producto'), max_length=50, blank=True)
    
    # Configuración de acceso
    access_level = models.CharField(_('Nivel de Acceso'), max_length=50, 
                                  choices=[
                                      ('basic', _('Básico')),
                                      ('standard', _('Estándar')),
                                      ('premium', _('Premium')),
                                      ('admin', _('Administrador')),
                                  ], default='standard')
    
    # Agentes disponibles para este usuario
    available_agents = models.ManyToManyField(DynamicAgent, blank=True, verbose_name=_('Agentes Disponibles'))
    
    # Estado
    is_active = models.BooleanField(_('Activo'), default=True)
    granted_at = models.DateTimeField(_('Fecha de Concesión'), auto_now_add=True)
    expires_at = models.DateTimeField(_('Fecha de Expiración'), blank=True, null=True)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, 
                                 related_name='granted_access', verbose_name=_('Concedido por'))
    
    class Meta:
        verbose_name = _('Acceso de Usuario a Producto')
        verbose_name_plural = _('Accesos de Usuarios a Productos')
        unique_together = ['user', 'product_name']
        ordering = ['-granted_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.product_name} ({self.access_level})"
    
    @property
    def is_expired(self):
        """Verifica si el acceso ha expirado"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def can_access(self):
        """Verifica si el usuario puede acceder al producto"""
        return self.is_active and not self.is_expired
    
    def get_available_agents(self):
        """Obtiene los agentes disponibles para el usuario"""
        if self.access_level == 'admin':
            return DynamicAgent.objects.filter(status='active')
        elif self.available_agents.exists():
            return self.available_agents.filter(status='active')
        else:
            # Agentes por defecto según nivel de acceso
            return DynamicAgent.objects.filter(status='active', escalation_level__lte=2)
