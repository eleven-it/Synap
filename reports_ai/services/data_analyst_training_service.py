"""
Servicio de entrenamiento interactivo del Data Analyst Agent
"""
import uuid
import time
import threading
from datetime import datetime
from typing import Dict, Optional, Callable
from django.utils import timezone

from ..models import AgentMetrics
from .relationship_discovery import RelationshipDiscoveryService
from .synonym_service import SynonymService
from ..models import RelationshipCandidate, SynonymMapping, ColumnStatistics


class DataAnalystTrainingSession:
    """Modelo para tracking de sesión de entrenamiento"""
    def __init__(self, session_id: str, options: Dict):
        self.session_id = session_id
        self.options = options
        self.status = 'pending'  # pending, running, completed, error, cancelled
        self.start_time = None
        self.end_time = None
        self.current_phase = None
        self.progress = 0
        
        # Métricas de progreso
        self.relationships_discovered = 0
        self.relationships_validated = 0
        self.synonyms_created = 0
        self.columns_analyzed = 0
        
        # Resultados
        self.results = {}
        self.error_message = None
        self.log_entries = []
    
    def to_dict(self):
        """Serializa la sesión a dict"""
        return {
            'session_id': self.session_id,
            'status': self.status,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'current_phase': self.current_phase,
            'progress': self.progress,
            'relationships_discovered': self.relationships_discovered,
            'relationships_validated': self.relationships_validated,
            'synonyms_created': self.synonyms_created,
            'columns_analyzed': self.columns_analyzed,
            'results': self.results,
            'error_message': self.error_message,
            'log_entries': self.log_entries[-50:]  # Últimas 50 entradas
        }


class DataAnalystTrainingService:
    """
    Servicio para entrenar el Data Analyst Agent de forma interactiva
    """
    
    def __init__(self):
        self.active_sessions = {}
    
    def train_interactive(
        self,
        options: Dict,
        progress_callback: Optional[Callable] = None
    ) -> str:
        """
        Inicia entrenamiento interactivo con progreso en tiempo real
        
        Args:
            options: Opciones de entrenamiento
                - discover_relationships: bool
                - build_synonyms: bool
                - min_confidence: float
                - clear_existing: bool
            progress_callback: Callback opcional para progreso
        
        Returns:
            session_id
        """
        session_id = str(uuid.uuid4())
        session = DataAnalystTrainingSession(session_id, options)
        self.active_sessions[session_id] = session
        
        # Ejecutar en thread separado
        thread = threading.Thread(
            target=self._run_training,
            args=(session, progress_callback)
        )
        thread.daemon = True
        thread.start()
        
        return session_id
    
    def _run_training(self, session: DataAnalystTrainingSession, callback: Optional[Callable]):
        """Ejecuta el entrenamiento completo"""
        try:
            session.status = 'running'
            session.start_time = timezone.now()
            session.progress = 0
            
            self._log(session, "🚀 Iniciando entrenamiento del Data Analyst Agent...")
            
            # Fase 1: Descubrimiento de relaciones (si está habilitado)
            if session.options.get('discover_relationships', True):
                self._phase_discover_relationships(session, callback)
            
            # Fase 2: Construcción de sinónimos (si está habilitado)
            if session.options.get('build_synonyms', True):
                self._phase_build_synonyms(session, callback)
            
            # Fase 3: Resultados finales
            self._phase_finalize(session, callback)
            
            session.status = 'completed'
            session.end_time = timezone.now()
            session.progress = 100
            
            duration = (session.end_time - session.start_time).total_seconds()
            self._log(session, f"✅ Entrenamiento completado en {duration:.1f}s")
            
            if callback:
                callback(session.to_dict())
        
        except Exception as e:
            session.status = 'error'
            session.error_message = str(e)
            session.end_time = timezone.now()
            self._log(session, f"❌ Error: {str(e)}")
            
            if callback:
                callback(session.to_dict())
    
    def _phase_discover_relationships(self, session: DataAnalystTrainingSession, callback: Optional[Callable]):
        """Fase 1: Descubrir relaciones entre tablas con contexto del Logic Interpreter"""
        session.current_phase = 'discover_relationships'
        self._log(session, "📊 FASE 1: Descubriendo relaciones entre tablas...")
        
        min_confidence = session.options.get('min_confidence', 0.6)
        use_logic_interpreter = session.options.get('use_logic_interpreter', True)
        
        # Limpiar si se solicita
        if session.options.get('clear_existing', False):
            count_before = RelationshipCandidate.objects.count()
            RelationshipCandidate.objects.all().delete()
            self._log(session, f"   🗑️ Eliminadas {count_before} relaciones existentes")
        
        # Descubrir relaciones
        service = RelationshipDiscoveryService()
        
        try:
            # Activar integración con Logic Interpreter
            discovered = service.discover_all_relationships(
                min_confidence=min_confidence,
                use_logic_interpreter=use_logic_interpreter
            )
            
            session.relationships_discovered = discovered
            session.relationships_validated = RelationshipCandidate.objects.filter(
                confidence_score__gte=0.8
            ).count()
            
            # Contar cuántas fueron enriquecidas con Logic Interpreter
            enriched = RelationshipCandidate.objects.filter(
                logic_interpreter_hint=True
            ).count()
            
            self._log(session, f"   ✅ {discovered} relaciones descubiertas")
            self._log(session, f"   ✅ {session.relationships_validated} con alta confianza (≥0.8)")
            if enriched > 0:
                self._log(session, f"   🧠 {enriched} enriquecidas con contexto del Logic Interpreter")
            
            session.progress = 50
            
            if callback:
                callback(session.to_dict())
        
        except Exception as e:
            self._log(session, f"   ⚠️ Error en descubrimiento: {str(e)}")
            raise
    
    def _phase_build_synonyms(self, session: DataAnalystTrainingSession, callback: Optional[Callable]):
        """Fase 2: Construir catálogo de sinónimos"""
        session.current_phase = 'build_synonyms'
        self._log(session, "📚 FASE 2: Construyendo catálogo de sinónimos...")
        
        # Limpiar si se solicita
        if session.options.get('clear_existing', False):
            count_before = SynonymMapping.objects.count()
            SynonymMapping.objects.all().delete()
            self._log(session, f"   🗑️ Eliminados {count_before} sinónimos existentes")
        
        # Construir catálogo
        service = SynonymService()
        
        try:
            service.build_synonym_catalog()
            
            session.synonyms_created = SynonymMapping.objects.count()
            session.columns_analyzed = ColumnStatistics.objects.count()
            
            # Estadísticas por fuente
            by_source = {}
            for mapping in SynonymMapping.objects.all():
                source = mapping.source
                by_source[source] = by_source.get(source, 0) + 1
            
            self._log(session, f"   ✅ {session.synonyms_created} sinónimos creados")
            for source, count in by_source.items():
                self._log(session, f"      • {source}: {count} mapeos")
            
            self._log(session, f"   ✅ {session.columns_analyzed} columnas analizadas")
            
            session.progress = 90
            
            if callback:
                callback(session.to_dict())
        
        except Exception as e:
            self._log(session, f"   ⚠️ Error en construcción de sinónimos: {str(e)}")
            raise
    
    def _phase_finalize(self, session: DataAnalystTrainingSession, callback: Optional[Callable]):
        """Fase 3: Finalizar y generar resultados"""
        session.current_phase = 'finalize'
        self._log(session, "📋 FASE 3: Generando resultados finales...")
        
        # Calcular métricas finales
        high_conf_rels = RelationshipCandidate.objects.filter(
            confidence_score__gte=0.8
        ).count()
        
        avg_conf = 0.0
        if session.relationships_discovered > 0:
            from django.db.models import Avg
            avg_conf = RelationshipCandidate.objects.aggregate(
                avg=Avg('confidence_score')
            )['avg'] or 0.0
        
        # Construir resultados
        session.results = {
            'relationships': {
                'total': session.relationships_discovered,
                'validated': session.relationships_validated,
                'high_confidence': high_conf_rels,
                'avg_confidence': round(avg_conf, 2)
            },
            'synonyms': {
                'total': session.synonyms_created,
                'by_source': self._get_synonyms_by_source()
            },
            'columns': {
                'analyzed': session.columns_analyzed
            }
        }
        
        self._log(session, "   ✅ Resultados generados")
        
        if callback:
            callback(session.to_dict())
    
    def _get_synonyms_by_source(self) -> Dict:
        """Obtiene conteo de sinónimos por fuente"""
        by_source = {}
        for mapping in SynonymMapping.objects.all():
            source = mapping.source
            by_source[source] = by_source.get(source, 0) + 1
        return by_source
    
    def _log(self, session: DataAnalystTrainingSession, message: str):
        """Agrega entrada al log de la sesión"""
        timestamp = timezone.now().strftime('%H:%M:%S')
        entry = f"[{timestamp}] {message}"
        session.log_entries.append(entry)
        print(entry)  # También imprime en consola para debugging
    
    def get_session(self, session_id: str) -> Optional[DataAnalystTrainingSession]:
        """Obtiene una sesión por ID"""
        return self.active_sessions.get(session_id)
    
    def cancel_session(self, session_id: str) -> bool:
        """Cancela una sesión en ejecución"""
        session = self.get_session(session_id)
        if session and session.status == 'running':
            session.status = 'cancelled'
            session.end_time = timezone.now()
            self._log(session, "⚠️ Entrenamiento cancelado por el usuario")
            return True
        return False
    
    def get_session_progress(self, session_id: str) -> Dict:
        """Obtiene el progreso actual de una sesión"""
        session = self.get_session(session_id)
        if session:
            return session.to_dict()
        return {'error': 'Session not found'}

