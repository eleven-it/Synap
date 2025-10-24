"""
Servicio principal para el sistema de agentes dinámicos
"""

import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from .dynamic_agent_models import (
    DynamicAgent, AgentDataset, AgentTrainingSession, 
    AgentQuery, AgentRoutingRule, UserProductAccess
)

User = get_user_model()
logger = logging.getLogger(__name__)


class DynamicAgentService:
    """
    Servicio principal para gestionar agentes dinámicos y modulares
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    # ==================== GESTIÓN DE AGENTES ====================
    
    def create_agent(self, name: str, module: str, description: str = None, 
                     escalation_level: int = 1, created_by = None, **kwargs) -> DynamicAgent:
        """
        Crea un nuevo agente dinámico
        
        Args:
            name: Nombre del agente
            module: Módulo funcional
            description: Descripción del agente
            escalation_level: Nivel de escalamiento
            created_by: Usuario que crea el agente
            **kwargs: Otros campos del agente
            
        Returns:
            Agente creado
        """
        try:
            with transaction.atomic():
                agent = DynamicAgent.objects.create(
                    name=name,
                    module=module,
                    description=description or f"Agente para módulo {module}",
                    escalation_level=escalation_level,
                    created_by=created_by,
                    **kwargs
                )
                
                self.logger.info(f"Agente dinámico creado: {agent.name} para módulo {module}")
                return agent
                
        except Exception as e:
            self.logger.error(f"Error creando agente {name}: {e}")
            raise
    
    def update_agent(self, agent: DynamicAgent, **kwargs) -> DynamicAgent:
        """
        Actualiza un agente existente
        
        Args:
            agent: Agente a actualizar
            **kwargs: Campos a actualizar
            
        Returns:
            Agente actualizado
        """
        try:
            for field, value in kwargs.items():
                if hasattr(agent, field):
                    setattr(agent, field, value)
            
            agent.save()
            self.logger.info(f"Agente actualizado: {agent.name}")
            return agent
            
        except Exception as e:
            self.logger.error(f"Error actualizando agente {agent.name}: {e}")
            raise
    
    def activate_agent(self, agent: DynamicAgent) -> bool:
        """
        Activa un agente
        
        Args:
            agent: Agente a activar
            
        Returns:
            True si se activó correctamente
        """
        try:
            if agent.status == 'active':
                self.logger.warning(f"Agente {agent.name} ya está activo")
                return True
            
            agent.status = 'active'
            agent.save()
            
            self.logger.info(f"Agente activado: {agent.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error activando agente {agent.name}: {e}")
            raise
    
    def deactivate_agent(self, agent: DynamicAgent) -> bool:
        """
        Desactiva un agente
        
        Args:
            agent: Agente a desactivar
            
        Returns:
            True si se desactivó correctamente
        """
        try:
            if agent.status == 'inactive':
                self.logger.warning(f"Agente {agent.name} ya está inactivo")
                return True
            
            agent.status = 'inactive'
            agent.save()
            
            self.logger.info(f"Agente desactivado: {agent.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error desactivando agente {agent.name}: {e}")
            raise
    
    def get_available_agents(self, user: User = None, module: str = None) -> List[DynamicAgent]:
        """
        Obtiene agentes disponibles
        
        Args:
            user: Usuario para filtrar acceso
            module: Módulo específico
            
        Returns:
            Lista de agentes disponibles
        """
        try:
            queryset = DynamicAgent.objects.filter(status='active', training_enabled=True)
            
            if module:
                queryset = queryset.filter(module__iexact=module)
            
            if user:
                # Filtrar por acceso del usuario
                user_access = UserProductAccess.objects.filter(
                    user=user,
                    is_active=True
                ).first()
                
                if user_access and not user_access.is_expired:
                    if user_access.access_level == 'admin':
                        # Administrador ve todos los agentes
                        pass
                    elif user_access.available_agents.exists():
                        # Usuario tiene agentes específicos asignados
                        queryset = queryset.filter(id__in=user_access.available_agents.values_list('id', flat=True))
                    else:
                        # Usuario tiene acceso por defecto según nivel
                        queryset = queryset.filter(escalation_level__lte=2)
                else:
                    # Usuario sin acceso, solo agentes básicos
                    queryset = queryset.filter(escalation_level=1)
            
            return list(queryset.order_by('module', 'name'))
            
        except Exception as e:
            self.logger.error(f"Error obteniendo agentes disponibles: {e}")
            return []
    
    # ==================== GESTIÓN DE DATASETS ====================
    
    def upload_dataset(self, agent: DynamicAgent, name: str, file, dataset_type: str,
                      description: str = None, version: str = '1.0.0', 
                      uploaded_by = None) -> AgentDataset:
        """
        Sube un dataset de entrenamiento para un agente
        
        Args:
            agent: Agente para el cual subir el dataset
            name: Nombre del dataset
            file: Archivo del dataset
            dataset_type: Tipo de dataset
            description: Descripción del dataset
            version: Versión del dataset
            uploaded_by: Usuario que sube el dataset
            
        Returns:
            Dataset creado
        """
        try:
            with transaction.atomic():
                dataset = AgentDataset.objects.create(
                    agent=agent,
                    name=name,
                    description=description or f"Dataset para {agent.name}",
                    dataset_type=dataset_type,
                    file=file,
                    version=version,
                    uploaded_by=uploaded_by
                )
                
                # Procesar el dataset
                dataset.process_dataset()
                
                self.logger.info(f"Dataset subido: {dataset.name} para agente {agent.name}")
                return dataset
                
        except Exception as e:
            self.logger.error(f"Error subiendo dataset {name}: {e}")
            raise
    
    def bulk_upload_datasets(self, agent: DynamicAgent, files: List, dataset_type: str,
                            description_template: str = None, version: str = '1.0.0',
                            uploaded_by = None) -> List[AgentDataset]:
        """
        Sube múltiples datasets de entrenamiento
        
        Args:
            agent: Agente para el cual subir los datasets
            files: Lista de archivos
            dataset_type: Tipo de dataset
            description_template: Plantilla de descripción
            version: Versión para todos los datasets
            uploaded_by: Usuario que sube los datasets
            
        Returns:
            Lista de datasets creados
        """
        try:
            datasets = []
            
            with transaction.atomic():
                for i, file in enumerate(files):
                    # Generar nombre del dataset
                    base_name = file.name.rsplit('.', 1)[0]
                    name = f"{base_name}_{i+1}" if len(files) > 1 else base_name
                    
                    # Generar descripción
                    if description_template:
                        description = f"{description_template} - {base_name}"
                    else:
                        description = f"Dataset {base_name} para {agent.name}"
                    
                    # Crear dataset
                    dataset = self.upload_dataset(
                        agent=agent,
                        name=name,
                        file=file,
                        dataset_type=dataset_type,
                        description=description,
                        version=version,
                        uploaded_by=uploaded_by
                    )
                    
                    datasets.append(dataset)
                
                self.logger.info(f"Subidos {len(datasets)} datasets para agente {agent.name}")
                return datasets
                
        except Exception as e:
            self.logger.error(f"Error en subida masiva de datasets: {e}")
            raise
    
    def process_dataset(self, dataset: AgentDataset) -> bool:
        """
        Procesa un dataset existente
        
        Args:
            dataset: Dataset a procesar
            
        Returns:
            True si se procesó correctamente
        """
        try:
            dataset.process_dataset()
            self.logger.info(f"Dataset procesado: {dataset.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error procesando dataset {dataset.name}: {e}")
            raise
    
    # ==================== SESIONES DE ENTRENAMIENTO ====================
    
    def create_training_session(self, agent: DynamicAgent, name: str, 
                               description: str = None, scheduled_at = None,
                               created_by = None) -> AgentTrainingSession:
        """
        Crea una nueva sesión de entrenamiento
        
        Args:
            agent: Agente a entrenar
            name: Nombre de la sesión
            description: Descripción de la sesión
            scheduled_at: Fecha programada
            created_by: Usuario que crea la sesión
            
        Returns:
            Sesión de entrenamiento creada
        """
        try:
            with transaction.atomic():
                session = AgentTrainingSession.objects.create(
                    agent=agent,
                    name=name,
                    description=description or f"Sesión de entrenamiento para {agent.name}",
                    scheduled_at=scheduled_at,
                    created_by=created_by
                )
                
                self.logger.info(f"Sesión de entrenamiento creada: {session.name} para {agent.name}")
                return session
                
        except Exception as e:
            self.logger.error(f"Error creando sesión de entrenamiento: {e}")
            raise
    
    def start_training_session(self, session: AgentTrainingSession) -> bool:
        """
        Inicia una sesión de entrenamiento
        
        Args:
            session: Sesión a iniciar
            
        Returns:
            True si se inició correctamente
        """
        try:
            with transaction.atomic():
                if session.status != 'scheduled':
                    raise ValidationError(f"La sesión debe estar programada para iniciarla")
                
                # Cambiar estado a ejecutándose
                session.status = 'running'
                session.started_at = timezone.now()
                session.total_datasets = session.datasets.count()
                session.save()
                
                self.logger.info(f"Sesión de entrenamiento iniciada: {session.name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error iniciando sesión de entrenamiento: {e}")
            raise
    
    def complete_training_session(self, session: AgentTrainingSession) -> bool:
        """
        Marca una sesión de entrenamiento como completada
        
        Args:
            session: Sesión a completar
            
        Returns:
            True si se completó correctamente
        """
        try:
            with transaction.atomic():
                if session.status != 'running':
                    raise ValidationError(f"La sesión debe estar ejecutándose para completarla")
                
                session.status = 'completed'
                session.completed_at = timezone.now()
                session.progress_percentage = 100
                session.save()
                
                # Actualizar agente
                agent = session.agent
                agent.last_training_at = timezone.now()
                agent.save()
                
                self.logger.info(f"Sesión de entrenamiento completada: {session.name}")
                return True
                
        except Exception as e:
            self.logger.error(f"Error completando sesión de entrenamiento: {e}")
            raise
    
    # ==================== ENRUTAMIENTO AUTOMÁTICO ====================
    
    def route_query(self, query_text: str, user: User = None, context: Dict = None) -> Optional[DynamicAgent]:
        """
        Enruta automáticamente una consulta al agente apropiado
        
        Args:
            query_text: Texto de la consulta
            user: Usuario que hace la consulta
            context: Contexto adicional
            
        Returns:
            Agente seleccionado o None si no se encuentra
        """
        try:
            # Obtener reglas de enrutamiento activas
            routing_rules = AgentRoutingRule.objects.filter(
                is_active=True,
                target_agent__status='active'
            ).order_by('-priority')
            
            # Buscar regla que coincida
            for rule in routing_rules:
                if rule.matches_query(query_text, context):
                    # Verificar que el usuario tenga acceso al agente
                    if user and not self._user_can_access_agent(user, rule.target_agent):
                        continue
                    
                    self.logger.info(f"Consulta enrutada a {rule.target_agent.name} por regla {rule.name}")
                    return rule.target_agent
            
            # Si no hay regla específica, usar enrutamiento por módulo
            return self._route_by_module(query_text, user, context)
            
        except Exception as e:
            self.logger.error(f"Error en enrutamiento automático: {e}")
            return None
    
    def _route_by_module(self, query_text: str, user: User = None, context: Dict = None) -> Optional[DynamicAgent]:
        """
        Enruta consulta por módulo detectado
        
        Args:
            query_text: Texto de la consulta
            user: Usuario que hace la consulta
            context: Contexto adicional
            
        Returns:
            Agente del módulo detectado
        """
        try:
            # Detectar módulo por palabras clave
            module_keywords = {
                'ventas': ['venta', 'cliente', 'prospecto', 'oportunidad', 'cotización'],
                'compras': ['compra', 'proveedor', 'pedido', 'factura', 'pago'],
                'inventario': ['stock', 'producto', 'almacén', 'existencia', 'movimiento'],
                'facturación': ['factura', 'afip', 'impuesto', 'iva', 'recibo'],
                'configuración': ['configurar', 'ajustar', 'parámetro', 'preferencia'],
                'reportes': ['reporte', 'estadística', 'métrica', 'dashboard', 'análisis']
            }
            
            query_lower = query_text.lower()
            
            for module, keywords in module_keywords.items():
                if any(keyword in query_lower for keyword in keywords):
                    # Buscar agente activo para este módulo
                    agent = DynamicAgent.objects.filter(
                        module__iexact=module,
                        status='active',
                        training_enabled=True
                    ).first()
                    
                    if agent and (not user or self._user_can_access_agent(user, agent)):
                        self.logger.info(f"Consulta enrutada a {agent.name} por módulo {module}")
                        return agent
            
            # Agente por defecto (nivel 1)
            default_agent = DynamicAgent.objects.filter(
                status='active',
                training_enabled=True,
                escalation_level=1
            ).first()
            
            if default_agent and (not user or self._user_can_access_agent(user, default_agent)):
                self.logger.info(f"Consulta enrutada a agente por defecto: {default_agent.name}")
                return default_agent
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error en enrutamiento por módulo: {e}")
            return None
    
    def _user_can_access_agent(self, user: User, agent: DynamicAgent) -> bool:
        """
        Verifica si un usuario puede acceder a un agente
        
        Args:
            user: Usuario a verificar
            agent: Agente a verificar
            
        Returns:
            True si el usuario puede acceder
        """
        try:
            # Usuarios administradores pueden acceder a todos los agentes
            if user.is_superuser or user.is_staff:
                return True
            
            # Verificar acceso específico del usuario
            user_access = UserProductAccess.objects.filter(
                user=user,
                is_active=True
            ).first()
            
            if not user_access or user_access.is_expired:
                return False
            
            if user_access.access_level == 'admin':
                return True
            
            # Verificar si el agente está en la lista de agentes disponibles
            if user_access.available_agents.filter(id=agent.id).exists():
                return True
            
            # Verificar acceso por nivel de escalamiento
            if user_access.access_level == 'premium':
                return agent.escalation_level <= 3
            elif user_access.access_level == 'standard':
                return agent.escalation_level <= 2
            else:  # basic
                return agent.escalation_level == 1
                
        except Exception as e:
            self.logger.error(f"Error verificando acceso de usuario {user.email} a agente {agent.name}: {e}")
            return False
    
    # ==================== PROCESAMIENTO DE CONSULTAS ====================
    
    def process_query(self, agent: DynamicAgent, query_text: str, user: User,
                     context: Dict = None) -> Dict[str, Any]:
        """
        Procesa una consulta usando un agente específico
        
        Args:
            agent: Agente que procesará la consulta
            query_text: Texto de la consulta
            user: Usuario que hace la consulta
            context: Contexto adicional
            
        Returns:
            Diccionario con la respuesta y metadatos
        """
        try:
            start_time = time.time()
            
            # Crear registro de consulta
            query = AgentQuery.objects.create(
                agent=agent,
                user=user,
                query_text=query_text,
                query_context=context or {},
                escalated=False
            )
            
            # Verificar si el agente puede manejar la consulta
            if not agent.can_handle_query:
                # Escalar consulta
                escalation_result = self._escalate_query(query, "Agente no disponible")
                return escalation_result
            
            # Procesar consulta con el agente
            try:
                response_result = self._generate_agent_response(agent, query_text, context)
                
                # Actualizar consulta
                query.response_text = response_result.get('response', '')
                query.confidence_score = response_result.get('confidence', 0.0)
                query.processing_time_ms = int((time.time() - start_time) * 1000)
                query.processed_at = timezone.now()
                query.save()
                
                # Incrementar contadores del agente
                agent.increment_query_count(success=True, escalated=False)
                
                result = {
                    'success': True,
                    'response': response_result.get('response', ''),
                    'confidence': response_result.get('confidence', 0.0),
                    'agent': agent.name,
                    'module': agent.module,
                    'processing_time': query.processing_time_ms / 1000.0,  # Convertir de ms a segundos
                    'escalated': False
                }
                
                self.logger.info(f"Consulta procesada exitosamente por {agent.name}")
                return result
                
            except Exception as e:
                # Error en procesamiento, escalar consulta
                self.logger.error(f"Error procesando consulta con {agent.name}: {e}")
                escalation_result = self._escalate_query(query, f"Error de procesamiento: {str(e)}")
                return escalation_result
                
        except Exception as e:
            self.logger.error(f"Error procesando consulta: {e}")
            return {
                'success': False,
                'error': str(e),
                'escalated': True
            }
    
    def _generate_agent_response(self, agent: DynamicAgent, query_text: str, 
                                context: Dict = None) -> Dict[str, Any]:
        """
        Genera respuesta del agente usando Ollama
        
        Args:
            agent: Agente que generará la respuesta
            query_text: Texto de la consulta
            context: Contexto adicional
            
        Returns:
            Diccionario con respuesta y confianza
        """
        try:
            # Importar el adaptador de Ollama
            from .ollama_adapter import get_ollama_adapter
            
            # Obtener el adaptador de Ollama
            ollama_adapter = get_ollama_adapter()
            
            if not ollama_adapter.is_available():
                raise Exception("Ollama no está disponible")
            
            # Construir contexto específico del agente
            agent_context = {
                'agent_name': agent.name,
                'agent_module': agent.module,
                'agent_level': agent.escalation_level,
                'agent_description': agent.description,
                'system_prompt': agent.system_prompt or f"Eres {agent.name}, un asistente especializado en {agent.module}.",
                'user_query': query_text
            }
            
            # Agregar contexto adicional si existe
            if context:
                agent_context.update(context)
            
            # Generar respuesta usando Ollama
            result = ollama_adapter.generate_response(query_text, agent_context)
            
            if not result['success']:
                raise Exception(f"Error generando respuesta: {result.get('error', 'Error desconocido')}")
            
            # Calcular confianza basada en el tiempo de respuesta y otros factores
            confidence = self._calculate_confidence(result, agent)
            
            return {
                'response': result['response'],
                'confidence': confidence,
                'model_used': result['model'],
                'processing_time': result['processing_time']
            }
            
        except Exception as e:
            self.logger.error(f"Error generando respuesta del agente {agent.name}: {e}")
            raise
    
    def _calculate_confidence(self, result: Dict[str, Any], agent: DynamicAgent) -> float:
        """
        Calcula la confianza de la respuesta basada en varios factores
        
        Args:
            result: Resultado de Ollama
            agent: Agente que generó la respuesta
            
        Returns:
            Valor de confianza entre 0.0 y 1.0
        """
        try:
            confidence = 0.8  # Confianza base
            
            # Factor de tiempo de respuesta
            processing_time = result.get('processing_time', 0)
            if processing_time < 2.0:
                confidence += 0.1  # Respuesta rápida
            elif processing_time > 10.0:
                confidence -= 0.1  # Respuesta lenta
            
            # Factor de longitud de respuesta
            response_length = len(result.get('response', ''))
            if 50 <= response_length <= 500:
                confidence += 0.05  # Respuesta de longitud apropiada
            elif response_length < 20:
                confidence -= 0.1  # Respuesta muy corta
            
            # Factor del agente
            if agent.escalation_level == 2:
                confidence += 0.05  # Agente especializado
            
            # Asegurar que la confianza esté entre 0.0 y 1.0
            return max(0.0, min(1.0, confidence))
            
        except Exception as e:
            self.logger.error(f"Error calculando confianza: {e}")
            return 0.7  # Confianza por defecto
    
    def _escalate_query(self, query: AgentQuery, reason: str) -> Dict[str, Any]:
        """
        Escala una consulta a un agente humano
        
        Args:
            query: Consulta a escalar
            reason: Razón del escalamiento
            
        Returns:
            Diccionario con información del escalamiento
        """
        try:
            with transaction.atomic():
                query.escalated = True
                query.escalation_reason = reason
                query.escalated_at = timezone.now()
                query.save()
                
                # Incrementar contador de escalamientos del agente
                agent = query.agent
                agent.increment_query_count(success=False, escalated=True)
                
                self.logger.info(f"Consulta escalada: {query.id} - Razón: {reason}")
                
                return {
                    'success': False,
                    'escalated': True,
                    'escalation_reason': reason,
                    'message': 'Tu consulta ha sido escalada a un agente humano. Te contactaremos pronto.'
                }
                
        except Exception as e:
            self.logger.error(f"Error escalando consulta: {e}")
            return {
                'success': False,
                'error': str(e),
                'escalated': True
            }
    
    # ==================== GESTIÓN DE ACCESO A PRODUCTOS ====================
    
    def grant_product_access(self, user: User, product_name: str, access_level: str = 'standard',
                           product_version: str = None, expires_at = None, 
                           granted_by = None) -> UserProductAccess:
        """
        Concede acceso de un usuario a un producto
        
        Args:
            user: Usuario al cual conceder acceso
            product_name: Nombre del producto
            access_level: Nivel de acceso
            product_version: Versión del producto
            expires_at: Fecha de expiración
            granted_by: Usuario que concede el acceso
            
        Returns:
            Acceso concedido
        """
        try:
            with transaction.atomic():
                # Crear o actualizar acceso
                access, created = UserProductAccess.objects.update_or_create(
                    user=user,
                    product_name=product_name,
                    defaults={
                        'product_version': product_version,
                        'access_level': access_level,
                        'expires_at': expires_at,
                        'granted_by': granted_by,
                        'is_active': True
                    }
                )
                
                action = "concedido" if created else "actualizado"
                self.logger.info(f"Acceso a {product_name} {action} para {user.email}")
                
                return access
                
        except Exception as e:
            self.logger.error(f"Error concediendo acceso a {product_name} para {user.email}: {e}")
            raise
    
    def revoke_product_access(self, user: User, product_name: str) -> bool:
        """
        Revoca acceso de un usuario a un producto
        
        Args:
            user: Usuario al cual revocar acceso
            product_name: Nombre del producto
            
        Returns:
            True si se revocó correctamente
        """
        try:
            with transaction.atomic():
                access = UserProductAccess.objects.filter(
                    user=user,
                    product_name=product_name
                ).first()
                
                if access:
                    access.is_active = False
                    access.save()
                    
                    self.logger.info(f"Acceso a {product_name} revocado para {user.email}")
                    return True
                else:
                    self.logger.warning(f"No se encontró acceso a {product_name} para {user.email}")
                    return False
                    
        except Exception as e:
            self.logger.error(f"Error revocando acceso a {product_name} para {user.email}: {e}")
            raise
    
    def get_user_products(self, user: User) -> List[Dict[str, Any]]:
        """
        Obtiene productos a los que tiene acceso un usuario
        
        Args:
            user: Usuario del cual obtener productos
            
        Returns:
            Lista de productos con información de acceso
        """
        try:
            user_access = UserProductAccess.objects.filter(
                user=user,
                is_active=True
            )
            
            products = []
            for access in user_access:
                if access.can_access:
                    products.append({
                        'product_name': access.product_name,
                        'product_version': access.product_version,
                        'access_level': access.access_level,
                        'granted_at': access.granted_at,
                        'expires_at': access.expires_at,
                        'available_agents': list(access.get_available_agents().values('name', 'module', 'escalation_level'))
                    })
            
            return products
            
        except Exception as e:
            self.logger.error(f"Error obteniendo productos para {user.email}: {e}")
            return []
    
    # ==================== MÉTRICAS Y ESTADÍSTICAS ====================
    
    def get_agent_metrics(self, agent: DynamicAgent = None) -> Dict[str, Any]:
        """
        Obtiene métricas de agentes
        
        Args:
            agent: Agente específico o None para todos
            
        Returns:
            Diccionario con métricas
        """
        try:
            if agent:
                # Métricas de un agente específico
                metrics = {
                    'agent_name': agent.name,
                    'module': agent.module,
                    'status': agent.status,
                    'total_queries': agent.total_queries,
                    'successful_responses': agent.successful_responses,
                    'escalation_count': agent.escalation_count,
                    'success_rate': agent.success_rate,
                    'escalation_rate': agent.escalation_rate,
                    'last_training': agent.last_training_at.isoformat() if agent.last_training_at else None,
                    'datasets_count': agent.datasets.filter(is_active=True).count(),
                    'training_sessions_count': agent.training_sessions.count()
                }
            else:
                # Métricas generales
                agents = DynamicAgent.objects.all()
                total_agents = agents.count()
                active_agents = agents.filter(status='active').count()
                
                total_queries = sum(agent.total_queries for agent in agents)
                total_successful = sum(agent.successful_responses for agent in agents)
                total_escalations = sum(agent.escalation_count for agent in agents)
                
                metrics = {
                    'total_agents': total_agents,
                    'active_agents': active_agents,
                    'total_queries': total_queries,
                    'total_successful_responses': total_successful,
                    'total_escalations': total_escalations,
                    'overall_success_rate': (total_successful / total_queries * 100) if total_queries > 0 else 0,
                    'overall_escalation_rate': (total_escalations / total_queries * 100) if total_queries > 0 else 0,
                    'agents_by_module': {},
                    'agents_by_status': {}
                }
                
                # Agrupar por módulo
                for agent in agents:
                    module = agent.module
                    if module not in metrics['agents_by_module']:
                        metrics['agents_by_module'][module] = 0
                    metrics['agents_by_module'][module] += 1
                
                # Agrupar por estado
                for agent in agents:
                    status = agent.status
                    if status not in metrics['agents_by_status']:
                        metrics['agents_by_status'][status] = 0
                    metrics['agents_by_status'][status] += 1
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error obteniendo métricas: {e}")
            return {}


# Instancia global del servicio
dynamic_agent_service = DynamicAgentService()


# Funciones de conveniencia
def get_dynamic_agent_service() -> DynamicAgentService:
    """Obtiene la instancia del servicio de agentes dinámicos"""
    return dynamic_agent_service


def create_agent(name: str, module: str, **kwargs) -> DynamicAgent:
    """Crea un nuevo agente dinámico"""
    return dynamic_agent_service.create_agent(name, module, **kwargs)


def route_query(query_text: str, **kwargs) -> Optional[DynamicAgent]:
    """Enruta automáticamente una consulta"""
    return dynamic_agent_service.route_query(query_text, **kwargs)


def process_query(agent: DynamicAgent, query_text: str, **kwargs) -> Dict[str, Any]:
    """Procesa una consulta usando un agente"""
    return dynamic_agent_service.process_query(agent, query_text, **kwargs)


def get_available_agents(**kwargs) -> List[DynamicAgent]:
    """Obtiene agentes disponibles"""
    return dynamic_agent_service.get_available_agents(**kwargs)


def get_agent_metrics(**kwargs) -> Dict[str, Any]:
    """Obtiene métricas de agentes"""
    return dynamic_agent_service.get_agent_metrics(**kwargs)
