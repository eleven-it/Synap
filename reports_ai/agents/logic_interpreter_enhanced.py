"""
Intérprete de Lógica de Negocio - VERSIÓN ENRIQUECIDA
Analiza formularios VB6/PHP para inferir mapas de persistencia
y entregar sugerencias de tablas/campos al Analista de Datos
"""
import logging
import time
from typing import Dict, List, Any, Optional
from .base import BaseAgent
from reports_ai.tools.vb6_form_analyzer import VB6FormAnalyzer
from reports_ai.models import BusinessRule

logger = logging.getLogger(__name__)


class LogicInterpreterEnhancedAgent(BaseAgent):
    """
    Intérprete de Lógica - VERSIÓN ENRIQUECIDA
    
    Analiza formularios VB6/PHP para crear mapas de persistencia
    y sugerir tablas/campos al Analista de Datos (solo interno)
    
    NUNCA expone nombres técnicos al usuario
    """
    
    def __init__(self, **kwargs):
        super().__init__(
            agent_name="Intérprete de Lógica Enriquecido",
            model="gpt-4",
            temperature=0.1,  # Máximo determinismo
            max_tokens=2000,
            top_p=0.85,
            **kwargs
        )
        
        self.form_analyzer = VB6FormAnalyzer()
        
        # Cache de mapeos de persistencia
        self._persistence_cache = {}
    
    def get_system_prompt(self) -> str:
        return """Eres Intérprete de Lógica de Negocio de Administranet.

RESPONSABILIDADES:
1. Analizar formularios VB6/PHP para inferir entidades funcionales
2. Mapear entidades a tablas de persistencia candidatas
3. Sugerir campos clave y relaciones
4. Extraer reglas funcionales en lenguaje de negocio
5. Calcular scores de confianza para evitar alucinaciones

SALIDA (SOLO para uso interno de otros agentes):
{
  "entidades_funcionales": ["cliente", "pedido", "articulo"],
  "tablas_sugeridas": [
    {"nombre": "Cliente", "rol": "maestro", "confianza": 0.92,
     "campos_clave_sugeridos": ["IdCliente", "RazonSocial", "CUIT"]}
  ],
  "relaciones_candidatas": [...],
  "reglas_funcionales_resumidas": [
    "Un cliente puede tener múltiples pedidos",
    "El stock se valida antes de confirmar un pedido"
  ]
}

ANTI-ALUCINACIÓN:
- Solo sugerir tablas/campos con evidencia del formulario o schema
- Confianza >= 0.80 para incluir en tablas_sugeridas
- Si confianza < 0.80, marcar como "en revisión"
- Nunca inventar nombres sin respaldo

PROHIBIDO EXPONER AL USUARIO:
- Nombres de tablas/campos
- Rutas de archivos
- Código VB6/PHP
- Consultas SQL

Todo lo técnico queda ESTRICTAMENTE INTERNO.
"""
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta análisis de lógica de negocio
        
        Args:
            input_data: {
                'intent': dict con intención y categoría,
                'query': str (opcional),
                'request_id': str (opcional)
            }
            
        Returns:
            Dict con mapa de persistencia (solo para uso interno)
        """
        start_time = time.time()
        
        intent = input_data.get('intent', {})
        category = intent.get('category', 'general')
        intention = intent.get('intencion', input_data.get('query', ''))
        
        logger.info(
            f"\n{'='*70}\n"
            f"[{self.agent_name}] 📖 INICIO DE INTERPRETACIÓN DE LÓGICA\n"
            f"{'='*70}\n"
            f"  🎯 Intención: {intention[:100]}...\n"
            f"  📂 Categoría: {category}\n"
            f"{'='*70}"
        )
        
        try:
            # Paso 1: Analizar formularios VB6 relevantes
            logger.info(f"[{self.agent_name}] 🔧 PASO 1: Analizando formularios VB6")
            form_analysis = self.form_analyzer.analyze_forms_for_intent(intention, category)
            
            # Paso 2: Buscar reglas existentes en BD
            logger.info(f"[{self.agent_name}] 🔧 PASO 2: Consultando reglas en BD")
            db_rules = self._get_business_rules_from_db(category)
            
            # Paso 3: Consolidar mapeo de persistencia
            logger.info(f"[{self.agent_name}] 🔧 PASO 3: Consolidando mapa de persistencia")
            persistence_map = self._build_persistence_map(
                form_analysis,
                db_rules,
                category
            )
            
            # Paso 4: Calcular scores de confianza finales
            logger.info(f"[{self.agent_name}] 🔧 PASO 4: Calculando scores de confianza")
            persistence_map = self._calculate_final_confidence(persistence_map)
            
            duration = time.time() - start_time
            
            logger.info(
                f"[{self.agent_name}] ✅ LÓGICA INTERPRETADA\n"
                f"  ⏱️  Duración: {duration:.2f}s\n"
                f"  🏷️  Entidades: {len(persistence_map['entidades_funcionales'])}\n"
                f"  🗄️  Tablas sugeridas: {len(persistence_map['tablas_sugeridas'])}\n"
                f"  🔗 Relaciones: {len(persistence_map['relaciones_candidatas'])}\n"
                f"  📚 Reglas: {len(persistence_map['reglas_funcionales_resumidas'])}\n"
                f"  📊 Confianza promedio: {self._avg_confidence(persistence_map):.2f}"
            )
            
            # Agregar metadata para el Analista de Datos
            persistence_map['para'] = 'analista_datos'
            persistence_map['categoria'] = category
            persistence_map['intencion'] = intention
            
            return {
                'success': True,
                'persistence_map': persistence_map,
                'agent': 'logic_interpreter_enhanced',
                'duration': duration
            }
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{self.agent_name}] ❌ ERROR EN INTERPRETACIÓN\n"
                f"  ⏱️  Duración: {duration:.2f}s\n"
                f"  🚫 Error: {type(e).__name__}: {str(e)}"
            )
            
            return {
                'success': False,
                'error': str(e),
                'agent': 'logic_interpreter_enhanced'
            }
    
    def _get_business_rules_from_db(self, category: str) -> List[Dict[str, Any]]:
        """
        Obtiene reglas de negocio de la BD
        
        Args:
            category: Categoría funcional
            
        Returns:
            Lista de reglas
        """
        try:
            rules = BusinessRule.objects.filter(
                module__iexact=category,
                is_active=True
            ).values('name', 'description', 'conditions', 'actions', 'category', 'priority')
            
            return list(rules)
        except Exception as e:
            logger.warning(f"[{self.agent_name}] No se pudieron obtener reglas de BD: {e}")
            return []
    
    def _build_persistence_map(
        self,
        form_analysis: Dict[str, Any],
        db_rules: List[Dict[str, Any]],
        category: str
    ) -> Dict[str, Any]:
        """
        Construye el mapa de persistencia consolidado
        
        Args:
            form_analysis: Análisis de formularios VB6
            db_rules: Reglas de BD
            category: Categoría funcional
            
        Returns:
            Mapa de persistencia completo
        """
        # Combinar reglas de formularios con reglas de BD
        all_rules = form_analysis.get('reglas_funcionales_resumidas', [])
        
        for rule in db_rules:
            business_desc = f"{rule.get('name', '')}: {rule.get('description', '')}"
            if business_desc not in all_rules:
                all_rules.append(business_desc)
        
        return {
            'entidades_funcionales': form_analysis.get('entidades_funcionales', []),
            'tablas_sugeridas': form_analysis.get('tablas_sugeridas', []),
            'relaciones_candidatas': form_analysis.get('relaciones_candidatas', []),
            'reglas_funcionales_resumidas': all_rules,
            'vigencia_reglas': form_analysis.get('vigencia_reglas', {}),
            'notas': form_analysis.get('notas', [])
        }
    
    def _calculate_final_confidence(self, persistence_map: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calcula scores de confianza finales para tablas sugeridas
        
        Heurísticas:
        - Coincidencia UI ↔ entidad: +0.25
        - Patrones maestro/detalle: +0.25
        - Eventos de confirmación: +0.15
        - Reutilización en múltiples formularios: +0.15
        - Verificación DDL: +0.20 (pendiente de implementar)
        
        Args:
            persistence_map: Mapa de persistencia
            
        Returns:
            Mapa con confianzas ajustadas
        """
        tables = persistence_map.get('tablas_sugeridas', [])
        
        # Filtrar tablas con confianza >= 0.80
        high_confidence = []
        under_review = []
        
        for table in tables:
            conf = table['confianza']
            
            if conf >= 0.80:
                high_confidence.append(table)
            else:
                table['estado'] = 'en_revision'
                table['razon'] = 'Confianza < 0.80, requiere verificación'
                under_review.append(table)
        
        # Actualizar el mapa
        persistence_map['tablas_sugeridas'] = high_confidence
        persistence_map['tablas_en_revision'] = under_review
        
        # Agregar nota si hay tablas en revisión
        if under_review:
            persistence_map['notas'].append(
                f'{len(under_review)} tabla(s) en revisión por baja confianza'
            )
        
        return persistence_map
    
    def _avg_confidence(self, persistence_map: Dict[str, Any]) -> float:
        """Calcula confianza promedio de las tablas sugeridas"""
        tables = persistence_map.get('tablas_sugeridas', [])
        if not tables:
            return 0.0
        
        return sum(t['confianza'] for t in tables) / len(tables)

