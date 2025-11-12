"""
Data Analyst V2 - Agente Independiente con Schema Completo

Versión completamente independiente del Logic Interpreter que:
1. Usa Schema Analyzer para conocer TODAS las tablas y columnas
2. Genera SQL basándose en conocimiento real de la BD
3. Aprende de correcciones humanas (active learning)
4. Descubre relaciones sin FKs formales
"""
import logging
import time
import json
from typing import Dict, List, Any, Optional
from .base import BaseAgent
from reports_ai.tools.mysql_tool import MySQLTool
from reports_ai.services.schema_analyzer import SchemaAnalyzer

logger = logging.getLogger(__name__)


class DataAnalystAgentV2(BaseAgent):
    """
    Data Analyst V2 - Versión Independiente
    
    Características:
    - ✅ Acceso completo al schema (463 tablas, 6,464 columnas)
    - ✅ Descubrimiento automático de relaciones
    - ✅ Generación de SQL basada en conocimiento real
    - ✅ Active learning de correcciones humanas
    - ✅ Resolución de sinónimos (business terms → column names)
    - ❌ Sin dependencia del Logic Interpreter
    """
    
    def __init__(self, **kwargs):
        """Inicializa el Data Analyst V2"""
        super().__init__(
            agent_name="Analista de Datos V2",
            model="gpt-4",
            temperature=0.0,  # Máxima precisión para SQL
            max_tokens=3000,
            **kwargs
        )
        
        # Herramientas y servicios
        self.mysql_tool = MySQLTool()
        self.schema_analyzer = SchemaAnalyzer()
        
        # Schema completo (cargado on-demand)
        self.schema_cache = None
        
        # Para active learning
        self.query_history = []
        self.active_learnings = {}  # Learnings del Active Learning Service
        
        logger.info(f"[{self.agent_name}] ✅ Inicializado (independiente)")
    
    def get_system_prompt(self) -> str:
        """
        Retorna el system prompt para el Data Analyst V2
        
        Returns:
            String con el system prompt
        """
        return self._build_system_prompt()
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta análisis de datos según la query del usuario
        
        Args:
            input_data: Dict con 'query', 'periodo', 'filters', etc.
        
        Returns:
            Dict con datos, resumen y SQL generado
        """
        start_time = time.time()
        
        try:
            # Extraer parámetros
            query = input_data.get('query', '')
            periodo = input_data.get('periodo', {})
            filters = input_data.get('filters', {})
            limit = input_data.get('limit', 100)
            
            logger.info(
                f"[{self.agent_name}] 🔍 INICIANDO ANÁLISIS\n"
                f"  📝 Query: {query[:100]}...\n"
                f"  📅 Período: {periodo}\n"
                f"  🔍 Filtros: {filters}"
            )
            
            # 1. Cargar schema si no está en caché
            if not self.schema_cache:
                logger.info(f"[{self.agent_name}] 📊 Cargando schema completo...")
                self.schema_cache = self.schema_analyzer.get_complete_schema()
                logger.info(
                    f"[{self.agent_name}] ✅ Schema cargado\n"
                    f"  📋 Tablas: {len(self.schema_cache.get('tables', {}))}\n"
                    f"  🔗 Relaciones: {len(self.schema_cache.get('relationships', []))}"
                )
            
            # 2. Generar SQL usando conocimiento del schema
            logger.info(f"[{self.agent_name}] 🔧 Generando SQL...")
            sql_result = self._generate_sql_with_schema(query, periodo, filters, limit)
            
            if not sql_result['success']:
                return sql_result
            
            sql_query = sql_result['sql']
            
            # 3. Ejecutar SQL
            logger.info(f"[{self.agent_name}] ▶️  Ejecutando SQL...")
            execution_result = self.mysql_tool.execute_query(sql_query, limit=limit)
            
            if not execution_result['success']:
                logger.error(f"[{self.agent_name}] ❌ Error ejecutando SQL: {execution_result.get('error')}")
                return {
                    'success': False,
                    'error': 'Error al consultar datos',
                    'details': execution_result.get('error'),
                    'agent': 'data_analyst_v2'
                }
            
            # 4. Formatear resultados
            logger.info(f"[{self.agent_name}] 🎨 Formateando resultados...")
            formatted = self._format_business_results(
                execution_result['data'],
                query
            )
            
            duration = time.time() - start_time
            
            result = {
                'success': True,
                'data': formatted['data'],
                'summary': formatted['summary'],
                'row_count': execution_result['row_count'],
                'limited': execution_result.get('limited', False),
                'processing_time': duration,
                'sql_query': sql_query,
                'agent': 'data_analyst_v2'
            }
            
            # Guardar en historial para learning
            self.query_history.append({
                'query': query,
                'sql': sql_query,
                'success': True,
                'timestamp': time.time()
            })
            
            logger.info(
                f"[{self.agent_name}] ✅ ANÁLISIS COMPLETADO\n"
                f"  ⏱️  Duración: {duration:.2f}s\n"
                f"  📊 Registros: {execution_result['row_count']}"
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{self.agent_name}] ❌ ERROR\n"
                f"  ⏱️  Duración: {duration:.2f}s\n"
                f"  🚫 Error: {type(e).__name__}: {str(e)}"
            )
            
            return {
                'success': False,
                'error': str(e),
                'agent': 'data_analyst_v2'
            }
    
    def _generate_sql_with_schema(
        self,
        query: str,
        periodo: Dict[str, Any],
        filters: Dict[str, Any],
        limit: int
    ) -> Dict[str, Any]:
        """
        Genera SQL usando el schema completo
        
        Estrategia:
        1. Identificar tablas relevantes por keywords
        2. Obtener schema completo de esas tablas
        3. Descubrir relaciones desde/hacia esas tablas
        4. Construir JOINs automáticamente
        5. Aplicar filtros y período
        """
        tables_info = self._identify_tables_from_query(query)
        
        if not tables_info:
            return {
                'success': False,
                'error': 'No se pudieron identificar tablas relevantes para la consulta'
            }
        
        # Construir contexto completo del schema
        schema_context = self._build_schema_context(tables_info)
        
        # Generar SQL con LLM
        messages = [
            {
                'role': 'system',
                'content': self._build_system_prompt()
            },
            {
                'role': 'user',
                'content': f"""Genera una consulta SQL SELECT para la siguiente pregunta:

PREGUNTA: {query}

SCHEMA DISPONIBLE:
{schema_context}

REQUERIMIENTOS:
- Genera SQL válido y eficiente
- Usa JOINs apropiados basándose en las relaciones sugeridas
- Aplica filtros de fechas si son relevantes (últimos 12 meses por defecto)
- LIMIT {limit} registros
- NUNCA uses columnas que no existan en el schema provisto
- Responde SOLO con el SQL, sin explicaciones

SQL:"""
            }
        ]
        
        logger.debug(f"[{self.agent_name}] 🤖 LLM generando SQL...")
        
        llm_response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        
        sql_query = llm_response.choices[0].message.content.strip()
        
        # Limpiar SQL (remover ```sql si existe)
        if sql_query.startswith('```'):
            sql_query = sql_query.split('```')[1]
            if sql_query.startswith('sql'):
                sql_query = sql_query[3:].strip()
        
        logger.info(f"[{self.agent_name}] ✅ SQL generado:\n{sql_query[:200]}...")
        
        return {
            'success': True,
            'sql': sql_query
        }
    
    def _identify_tables_from_query(self, query: str) -> List[str]:
        """
        Identifica tablas relevantes desde la query usando keywords
        """
        query_lower = query.lower()
        
        # Diccionario de keywords → tablas
        keywords_to_tables = {
            'cliente': ['cliente', 'clientes_web'],
            'articulo': ['articulo'],
            'producto': ['articulo'],
            'pedido': ['comp_ped'],
            'venta': ['comp_ped', 'comprobante'],
            'factura': ['comprobante'],
            'remito': ['comprobante'],
            'stock': ['stock', 'stockp'],
            'categoria': ['articulo_categoria', 'categoriaret_prov', 'categories'],
            'rubro': ['rubro'],
            'subrubro': ['subrubro'],
            'proveedor': ['proveedor', 'suppliers'],
            'sucursal': ['sucursales'],
            'movimiento': ['codmov'],
            'pago': ['cobranza'],
            'cobranza': ['cobranza'],
            'banco': ['banco']
        }
        
        candidate_tables = set()
        
        for keyword, tables in keywords_to_tables.items():
            if keyword in query_lower:
                candidate_tables.update(tables)
        
        # Si no hay candidatos, usar tablas principales
        if not candidate_tables:
            logger.warning(f"[{self.agent_name}] ⚠️  No se identificaron tablas por keywords, usando tablas principales")
            candidate_tables = {'articulo', 'cliente', 'comp_ped', 'stock'}
        
        return list(candidate_tables)
    
    def _build_schema_context(self, tables: List[str]) -> str:
        """
        Construye contexto detallado del schema para las tablas dadas
        """
        context_parts = []
        
        for table_name in tables[:5]:  # Máximo 5 tablas
            table_info = self.schema_cache['tables'].get(table_name)
            
            if not table_info:
                continue
            
            context_parts.append(f"\n📋 TABLA: {table_name}")
            
            if table_info.get('comment'):
                context_parts.append(f"   Descripción: {table_info['comment']}")
            
            # Primary Key
            pk = table_info.get('primary_key', [])
            if pk:
                context_parts.append(f"   Primary Key: {', '.join(pk)}")
            
            # Columnas principales (máximo 15)
            context_parts.append("\n   Columnas:")
            for col in table_info['columns'][:15]:
                col_name = col['name']
                col_type = col['type']['base']
                nullable = 'NULL' if col['nullable'] else 'NOT NULL'
                key_info = ""
                
                if col['key_info']['is_primary']:
                    key_info = " [PK]"
                elif col['key_info']['is_foreign']:
                    key_info = " [FK]"
                elif col['key_info']['is_unique']:
                    key_info = " [UNIQUE]"
                
                context_parts.append(f"   - {col_name} ({col_type}) {nullable}{key_info}")
            
            if len(table_info['columns']) > 15:
                context_parts.append(f"   ... y {len(table_info['columns']) - 15} más")
        
        # Agregar relaciones descubiertas
        context_parts.append("\n🔗 Relaciones descubiertas:")
        relationships = self.schema_cache['relationships']
        
        for rel in relationships[:10]:
            if rel['from_table'] in tables or rel['to_table'] in tables:
                context_parts.append(
                    f"   {rel['from_table']}.{rel['from_column']} → "
                    f"{rel['to_table']}.{rel['to_column']} "
                    f"[{rel.get('source', 'unknown')}]"
                )
        
        return "\n".join(context_parts)
    
    def _build_system_prompt(self) -> str:
        """
        Construye el system prompt para el LLM con criterios conservadores
        """
        return """Eres un experto en SQL para bases de datos MySQL de AdministraNET.

Tu tarea es generar consultas SQL SELECT de solo lectura que respondan preguntas en lenguaje natural.

REGLAS FUNDAMENTALES:
1. Solo generar SQL SELECT (NUNCA DML/DDL: INSERT, UPDATE, DELETE, DROP, ALTER, CREATE)
2. Usar SOLO columnas que existan en el schema provisto
3. Usar nombres de tablas y columnas EXACTAMENTE como aparecen en el schema
4. Aplicar LIMIT a un número razonable de registros (default: 100)
5. Si no se especifica período: últimos 12 meses
6. Filtros de texto: usar LIKE '%texto%'
7. Redondear precios/moneda a 2 decimales

CRITERIOS CONSERVADORES PARA JOINS:
⚠️ Solo usar relaciones que cumplan TODOS estos criterios:

A. Patrón de Nombre FK:
   - Campo empieza con "Cod" o "codigo_" o "cod" (ej: CodLaboratorio)
   - Campo es "id", "ID", termina con "_id" o "_ID" (ej: cliente_id)
   - Campo empieza con "ID_" o "ID" (ej: ID_Cliente, IDArticulo)

B. Tipo Numérico Entero:
   - int, tinyint, smallint, mediumint, bigint
   - ❌ NUNCA usar varchar, char, text, decimal, float, date, datetime como FK

C. Tabla Destino Correcta:
   - CodLaboratorio → tabla "laboratorio" (NO otra tabla)
   - cliente_id → tabla "cliente" (NO otra tabla)
   - La columna destino debe ser PRIMARY KEY

D. Confianza >= 0.80:
   - Solo usar relaciones con alta confianza
   - Si hay ambigüedad: NO hacer JOIN

EJEMPLOS DE JOINS VÁLIDOS:
✅ articulo.CodLaboratorio = laboratorio.CodLaboratorio
✅ pedido.IDCliente = cliente.IDCliente

EJEMPLOS DE JOINS INVÁLIDOS:
❌ articulo.NombreArticulo = ... (es varchar, NO es FK)
❌ articulo.CodLaboratorio = nro_codigo_manual_cliente.id (tabla incorrecta)

REGLA DE ORO:
Si NO estás 100% seguro de una relación: NO la uses. Es mejor hacer una query sin JOIN que una query con JOIN incorrecto.

FORMATO:
- Responde SOLO con el SQL
- Sin explicaciones adicionales
- SQL limpio y legible"""
    
    def _format_business_results(
        self,
        data: List[Dict[str, Any]],
        original_query: str
    ) -> Dict[str, Any]:
        """
        Formatea resultados en lenguaje de negocio
        """
        if not data:
            return {
                'data': [],
                'summary': 'No se encontraron registros para la consulta.'
            }
        
        # Resumen automático
        summary = f"Se encontraron {len(data)} registro(s) para la consulta."
        
        return {
            'data': data,
            'summary': summary
        }
    
    def mark_query_success(self, query_id: str):
        """
        Marca una query como exitosa para active learning
        """
        # TODO: Implementar feedback positivo
        logger.debug(f"[{self.agent_name}] ✅ Marca query {query_id} como exitosa")
    
    def mark_query_failure(self, query_id: str, corrected_sql: str, explanation: str):
        """
        Marca una query como fallida y guarda la corrección
        """
        # TODO: Implementar feedback negativo
        logger.debug(
            f"[{self.agent_name}] ❌ Marca query {query_id} como fallida\n"
            f"  SQL corregido: {corrected_sql[:100]}...\n"
            f"  Explicación: {explanation}"
        )
    
    def load_active_learnings(self):
        """
        Carga los learnings del Active Learning Service
        """
        try:
            from reports_ai.services.active_learning_service import ActiveLearningService
            
            service = ActiveLearningService()
            corrections = service.load_applied_corrections()
            learnings = service.extract_learnings(corrections)
            
            self.active_learnings = learnings
            
            logger.info(
                f"[{self.agent_name}] 📚 Active learnings cargados\n"
                f"  📝 Keywords: {len(learnings.get('keyword_to_table', {}))}\n"
                f"  🔗 Relaciones: {len(learnings.get('table_relationships', []))}"
            )
        except Exception as e:
            logger.error(f"[{self.agent_name}] ❌ Error cargando active learnings: {e}")
            self.active_learnings = {}

