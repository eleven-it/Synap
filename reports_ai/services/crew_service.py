"""
Servicio de orquestación CrewAI
Coordina todos los agentes y el flujo completo
"""
import logging
import uuid
from typing import Dict, Any, Optional
from django.utils import timezone
from reports_ai.agents.orchestrator import OrchestratorAgent
from reports_ai.agents.query_interpreter import QueryInterpreterAgent
from reports_ai.agents.data_analyst import DataAnalystAgent
from reports_ai.agents.data_analyst_v2 import DataAnalystAgentV2
from reports_ai.agents.logic_interpreter import LogicInterpreterAgent
from reports_ai.agents.report_generator import ReportGeneratorAgent
from reports_ai.agents.validator_agent import ValidatorAgent
from reports_ai.models import ReportRequest, AgentMetrics

logger = logging.getLogger(__name__)


class CrewService:
    """
    Servicio principal de orquestación de agentes
    Implementa el flujo completo del sistema multiagente
    """
    
    def __init__(self):
        """Inicializa todos los agentes"""
        logger.info("[CrewService] Inicializando agentes...")
        
        # Crear agentes
        self.orchestrator = OrchestratorAgent()
        self.query_interpreter = QueryInterpreterAgent()
        self.data_analyst = DataAnalystAgent()
        self.data_analyst_v2 = None  # NUEVO: Se inicializa lazy (requiere config de administraNET)
        self.logic_interpreter = LogicInterpreterAgent()
        self.report_generator = ReportGeneratorAgent()
        self.validator = ValidatorAgent()
        
        # Inyectar referencias al orquestador
        self.orchestrator.set_agents(
            query_interpreter=self.query_interpreter,
            data_analyst=self.data_analyst,
            data_analyst_v2=None,  # Se inicializará on-demand
            logic_interpreter=self.logic_interpreter,
            report_generator=self.report_generator,
            validator=self.validator,
            use_data_analyst_v2=False  # Por defecto usar original (V2 requiere config)
        )
        
        logger.info("[CrewService] Agentes inicializados correctamente")
    
    def _ensure_data_analyst_v2(self):
        """
        Inicializa Data Analyst V2 lazy (solo cuando se necesita)
        """
        if self.data_analyst_v2 is None:
            try:
                logger.info("[CrewService] Inicializando Data Analyst V2...")
                self.data_analyst_v2 = DataAnalystAgentV2()
                self.orchestrator.data_analyst_v2 = self.data_analyst_v2
                self.orchestrator.use_data_analyst_v2 = True
                logger.info("[CrewService] ✅ Data Analyst V2 inicializado")
            except Exception as e:
                logger.warning(f"[CrewService] ⚠️  No se pudo inicializar Data Analyst V2: {e}")
                logger.warning("[CrewService] Usando Data Analyst original como fallback")
                self.orchestrator.use_data_analyst_v2 = False
    
    def enable_data_analyst_v2(self):
        """
        Activa Data Analyst V2 manualmente
        
        Returns:
            bool: True si se activó correctamente, False si falló
        """
        self._ensure_data_analyst_v2()
        return self.orchestrator.use_data_analyst_v2
    
    def generate_report(
        self,
        query: str,
        user=None,
        empresa=None,
        source: str = 'web'
    ) -> Dict[str, Any]:
        """
        Genera un reporte completo ejecutando el flujo de agentes
        
        Args:
            query: Consulta del usuario
            user: Usuario que solicita (opcional)
            empresa: Empresa asociada (opcional)
            source: Origen de la solicitud (web, webhook, api)
            
        Returns:
            Dict con reporte generado y metadatos
        """
        # Generar ID único para esta solicitud
        request_id = f"REQ-{uuid.uuid4().hex[:12].upper()}"
        
        logger.info(f"[CrewService] Iniciando generación de reporte {request_id}")
        
        # Crear registro en BD
        report_request = ReportRequest.objects.create(
            request_id=request_id,
            user=user,
            empresa=empresa,
            intent='',  # Se completará después
            query_text=query,
            status='processing',
            source=source
        )
        
        try:
            # Paso 1: Intérprete de Consulta (NLU)
            logger.info(f"[{request_id}] Paso 1: Interpretando consulta")
            nlu_result = self.query_interpreter.execute({'query': query})
            
            if not nlu_result.get('success'):
                report_request.status = 'error'
                report_request.error_message = 'Error en interpretación de consulta'
                report_request.save()
                return {
                    'success': False,
                    'request_id': request_id,
                    'error': 'No se pudo interpretar la consulta'
                }
            
            brief = nlu_result.get('brief', {})
            report_request.intent = brief.get('intencion', '')
            report_request.parameters = brief
            report_request.save()
            
            # Paso 2: Intérprete de Lógica (reglas de negocio)
            logger.info(f"[{request_id}] Paso 2: Obteniendo reglas de negocio")
            logic_result = self.logic_interpreter.execute({
                'intent': {'category': brief.get('categoria', 'general')}
            })
            
            business_rules = logic_result.get('rules', [])
            
            # Paso 3: Analista de Datos (MySQL)
            logger.info(f"[{request_id}] Paso 3: Consultando datos")
            data_result = self.data_analyst.execute({
                'query': query,
                'periodo': brief.get('periodo', {}),
                'filters': brief.get('filtros', {}),
                'limit': brief.get('limites', {}).get('top_n', 100)
            })
            
            if not data_result.get('success'):
                report_request.status = 'error'
                report_request.error_message = 'Error consultando datos'
                report_request.save()
                return {
                    'success': False,
                    'request_id': request_id,
                    'error': 'Error al consultar datos de Administranet'
                }
            
            # Paso 4: Generador de Reportes
            logger.info(f"[{request_id}] Paso 4: Generando reporte")
            report_result = self.report_generator.execute({
                'data': data_result,
                'business_rules': business_rules,
                'intent': brief,
                'periodo': brief.get('periodo', {})
            })
            
            if not report_result.get('success'):
                report_request.status = 'error'
                report_request.error_message = 'Error generando reporte'
                report_request.save()
                return {
                    'success': False,
                    'request_id': request_id,
                    'error': 'Error al generar el reporte'
                }
            
            report = report_result.get('report', {})
            
            # Paso 5: Validador (control final)
            logger.info(f"[{request_id}] Paso 5: Validando reporte")
            validation_result = self.validator.execute({
                'report': report,
                'data_sources': [data_result]
            })
            
            if not validation_result.get('approved'):
                logger.warning(f"[{request_id}] Reporte no aprobado por validador")
                # Aquí se podría regenerar o aplicar correcciones
            
            # Actualizar registro
            report_request.status = 'completed'
            report_request.completed_at = timezone.now()
            report_request.response_data = report
            report_request.sql_query = data_result.get('sql_query', '')  # Guardar SQL generada
            report_request.confidence_score = report_result.get('validation', {}).get('factual_confidence', 0.95)
            
            # Calcular tokens totales
            total_tokens = sum([
                nlu_result.get('tokens_used', 0),
                data_result.get('tokens_used', 0),
                report_result.get('tokens_used', 0)
            ])
            report_request.tokens_used = total_tokens
            
            report_request.save()
            
            # Actualizar métricas de agentes
            self._update_agent_metrics()
            
            logger.info(f"[CrewService] Reporte {request_id} generado exitosamente")
            
            return {
                'success': True,
                'request_id': request_id,
                'report': report,
                'validation': validation_result.get('validation', {}),
                'tokens_used': total_tokens
            }
            
        except Exception as e:
            logger.error(f"[CrewService] Error generando reporte {request_id}: {e}")
            
            report_request.status = 'error'
            report_request.error_message = str(e)
            report_request.save()
            
            return {
                'success': False,
                'request_id': request_id,
                'error': str(e)
            }
    
    def _update_agent_metrics(self):
        """Actualiza métricas de los agentes en la BD"""
        try:
            from datetime import date
            today = date.today()
            
            agents = [
                ('orchestrator', self.orchestrator),
                ('query_interpreter', self.query_interpreter),
                ('data_analyst', self.data_analyst),
                ('logic_interpreter', self.logic_interpreter),
                ('report_generator', self.report_generator),
                ('validator', self.validator),
            ]
            
            for agent_name, agent_obj in agents:
                metrics = agent_obj.get_metrics()
                
                # Obtener o crear registro de métricas de hoy
                agent_metrics, created = AgentMetrics.objects.get_or_create(
                    agent_name=agent_name,
                    date=today
                )
                
                agent_metrics.total_invocations = metrics['total_invocations']
                agent_metrics.successful_invocations = metrics['successful_invocations']
                agent_metrics.failed_invocations = metrics['failed_invocations']
                agent_metrics.total_tokens_used = metrics['total_tokens_used']
                
                agent_metrics.save()
                
        except Exception as e:
            logger.error(f"Error actualizando métricas de agentes: {e}")
    
    def get_agent_status(self) -> Dict[str, Any]:
        """
        Obtiene el estado de todos los agentes
        
        Returns:
            Dict con métricas de cada agente
        """
        return {
            'orchestrator': self.orchestrator.get_metrics(),
            'query_interpreter': self.query_interpreter.get_metrics(),
            'data_analyst': self.data_analyst.get_metrics(),
            'logic_interpreter': self.logic_interpreter.get_metrics(),
            'report_generator': self.report_generator.get_metrics(),
            'validator': self.validator.get_metrics(),
        }

