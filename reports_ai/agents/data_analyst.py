"""
Agente Analista de Datos (MySQL Reader)
Ejecuta consultas SELECT de solo lectura y retorna resultados en formato de negocio
"""
import logging
import time
import json
from typing import Dict, List, Any, Optional
from .base import BaseAgent
from reports_ai.tools.mysql_tool import MySQLTool
from reports_ai.tools.validation_tool import ValidationTool

logger = logging.getLogger(__name__)


class DataAnalystAgent(BaseAgent):
    """
    Agente Analista de Datos - Acceso a MySQL de Administranet
    
    Responsabilidades según documento:
    1. Recibir pregunta sobre datos de administraNET
    2. Convertirla en instrucción SQL SELECT válida
    3. Prohibido DML/DDL estrictamente
    4. Usar filtros con LIKE '%texto%', ABS(), ORDER BY para rankings
    5. SIEMPRE usar la herramienta MySQL (nunca inventar resultados)
    6. Presentar resultados como lista para mejor comprensión
    7. Si no se especifica periodo: últimos 12 meses
    8. Aplicar LIMIT si el resultado puede ser grande
    9. Redondear precios/moneda a 2 decimales
    10. Buscar nombres/descripciones en tablas relacionadas (FK)
    11. NUNCA mostrar SQL ni nombres de tablas en la respuesta
    """
    
    def __init__(self, **kwargs):
        """Inicializa el Analista de Datos con temperature=0.0 (máximo determinismo)"""
        super().__init__(
            agent_name="Analista de Datos",
            model="gpt-4",
            temperature=0.0,  # Cero creatividad, máxima precisión
            max_tokens=2000,
            **kwargs
        )
        
        self.mysql_tool = MySQLTool()
        self.validation_tool = ValidationTool()
        
        # Servicios de descubrimiento y resolución
        from reports_ai.services.schema_graph import SchemaGraph
        from reports_ai.services.synonym_service import SynonymService
        
        self.schema_graph = None  # Se inicializa lazy
        self.synonym_service = SynonymService()
        self.message_history = []
        
        # Obtener schema de la base de datos
        self._load_schema()
    
    def _load_schema(self):
        """Carga el schema de la base de datos para conocer tablas y columnas"""
        try:
            schema_info = self.mysql_tool.get_schema_info()
            
            if schema_info['success']:
                self.available_tables = [
                    table['table_name'] 
                    for table in schema_info['data']
                ]
                logger.info(f"[Analista de Datos] Schema cargado: {len(self.available_tables)} tablas")
            else:
                self.available_tables = []
                logger.warning("[Analista de Datos] No se pudo cargar schema")
                
        except Exception as e:
            logger.error(f"[Analista de Datos] Error cargando schema: {e}")
            self.available_tables = []
    
    def _build_messages_with_history(self, current_messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Construye mensajes incluyendo historial de conversación"""
        if not self.message_history:
            return current_messages
        
        # Separar system prompt
        system_prompt = None
        other_messages = []
        
        for msg in current_messages:
            if msg['role'] == 'system':
                system_prompt = msg
            else:
                other_messages.append(msg)
        
        # Construir lista final
        final_messages = []
        if system_prompt:
            final_messages.append(system_prompt)
        
        # Agregar historial (últimos 3 mensajes - menos que otros agentes por el contexto SQL)
        for hist_msg in self.message_history[-3:]:
            final_messages.append({
                'role': hist_msg['role'],
                'content': hist_msg['content']
            })
        
        final_messages.extend(other_messages)
        return final_messages
    
    def _call_llm(self, messages: List[Dict[str, str]], **override_params) -> Dict[str, Any]:
        """Sobrescribe _call_llm para incluir historial"""
        messages_with_history = self._build_messages_with_history(messages)
        return super()._call_llm(messages_with_history, **override_params)
    
    def get_system_prompt(self) -> str:
        """System prompt del Analista de Datos según el documento"""
        return """Tu objetivo es:
1. Recibir una pregunta sobre los datos de la base de datos de administraNET
2. Convertirla ÚNICA Y EXCLUSIVAMENTE en una instrucción SQL SELECT válida
3. Prohibido DML/DDL (INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, GRANT, REVOKE)
4. Al ejecutar la consulta SELECT, siempre usa:
   - Filtros con LIKE '%texto%' para búsquedas de texto
   - Distancias numéricas con ABS() cuando corresponda
   - Rankings simples con ORDER BY ABS(valor - referencia)
5. Usa SIEMPRE la herramienta "MySQL" para ejecutar consultas, NUNCA inventes resultados
6. Si hay una lista de resultados, preséntala como lista para mejor comprensión
7. Si el usuario no especifica periodo, asume últimos 12 meses
8. Aplica LIMIT si el resultado puede ser grande (máximo 1000)
9. Los números de precios o moneda, siempre redondéalos a 2 decimales
10. En caso que tengas campos con relaciones (marca, rubro, subrubro en artículo), busca su nombre/descripción en su tabla específica

Debes obtener la estructura completa de la base de datos (schema DDL).
Debes analizar mediante los campos si existen referencias entre tablas ya que no se encuentran todas normalizadas y faltan FK.

IMPORTANTE:
- Nunca respondas con una consulta SELECT ni nada de SQL en tu respuesta final
- El SQL solo lo generas para enviarlo a tu herramienta MySQL
- NUNCA des nombres de tablas en tus respuestas
- Recuerda que el usuario NO es técnico, usa lenguaje de negocio

Ejemplo interno (NO mostrar al usuario):
Entrada: Dame todos los articulos de anchoas
SQL generado (solo para tool): SELECT * FROM articulo WHERE NombreArticulo LIKE '%anchoas%' ORDER BY NombreArticulo;
Respuesta al usuario: "Encontré X artículos de anchoas: [lista de nombres]"
"""
    
    def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta análisis de datos según la consulta
        
        Args:
            input_data: {
                'query': str,  # Pregunta sobre datos
                'periodo': dict (opcional),  # {'desde': '...', 'hasta': '...'}
                'filters': dict (opcional),  # Filtros adicionales
                'limit': int (opcional)  # Límite de resultados
            }
            
        Returns:
            Dict con datos y presentación en lenguaje de negocio
        """
        start_time = time.time()
        
        query = input_data.get('query', '')
        periodo = input_data.get('periodo', {})
        filters = input_data.get('filters', {})
        limit = input_data.get('limit') or 100  # Si es None, usar 100 por defecto
        persistence_map = input_data.get('persistence_map', {})  # NUEVO: Mapa de persistencia
        
        logger.info(
            f"\n{'='*70}\n"
            f"[{self.agent_name}] 📊 INICIO DE ANÁLISIS DE DATOS\n"
            f"{'='*70}\n"
            f"  📝 Query: {query[:100]}...\n"
            f"  📅 Periodo: {periodo}\n"
            f"  🔍 Filtros: {len(filters)} filtro(s)\n"
            f"  ⏱️  Límite: {limit} registros\n"
            f"  🗄️  Tablas disponibles: {len(self.available_tables)}\n"
            f"  🗺️  Mapa de persistencia: {'Sí (' + str(len(persistence_map.get('tablas_sugeridas', []))) + ' tablas)' if persistence_map else 'No'}\n"
            f"{'='*70}"
        )
        
        try:
            # Paso 1: Generar SQL a partir de la pregunta (con mapa de persistencia si está disponible)
            logger.info(f"[{self.agent_name}] 🔧 PASO 1: Generando consulta SQL")
            sql_generation = self._generate_sql(query, periodo, filters, limit, persistence_map)
            
            if not sql_generation['success']:
                logger.error(f"[{self.agent_name}] ❌ No se pudo generar SQL")
                return {
                    'success': False,
                    'error': 'No se pudo generar consulta de datos',
                    'agent': 'data_analyst'
                }
            
            sql_query = sql_generation['sql']
            logger.info(
                f"[{self.agent_name}] ✅ SQL generado exitosamente\n"
                f"  📝 SQL: {sql_query[:150]}..."
            )
            
            # Paso 2: Ejecutar SQL con la herramienta MySQL
            logger.info(f"[{self.agent_name}] 🔧 PASO 2: Ejecutando query en MySQL")
            execution_result = self.mysql_tool.execute_query(sql_query, limit=limit)
            
            if not execution_result['success']:
                logger.error(
                    f"[{self.agent_name}] ❌ Error ejecutando SQL\n"
                    f"  🚫 Error: {execution_result.get('error', 'Desconocido')}"
                )
                return {
                    'success': False,
                    'error': 'Error al consultar datos de Administranet',
                    'details': execution_result.get('error'),
                    'agent': 'data_analyst'
                }
            
            logger.info(
                f"[{self.agent_name}] ✅ Query ejecutado exitosamente\n"
                f"  📊 Registros obtenidos: {execution_result['row_count']}\n"
                f"  ⚠️  Limitado: {'Sí' if execution_result.get('limited') else 'No'}"
            )
            
            # Paso 3: Formatear resultados en lenguaje de negocio
            logger.info(f"[{self.agent_name}] 🔧 PASO 3: Formateando resultados")
            formatted_results = self._format_results_for_business(
                execution_result['data'],
                query
            )
            
            duration = time.time() - start_time
            
            result = {
                'success': True,
                'data': formatted_results['data'],
                'summary': formatted_results['summary'],
                'row_count': execution_result['row_count'],
                'limited': execution_result.get('limited', False),
                'processing_time': duration,
                'sql_query': sql_query,  # SQL generada para auditoría
                'agent': 'data_analyst'
            }
            
            # Registrar ejecución
            logger.info(
                f"[{self.agent_name}] ✅ ANÁLISIS COMPLETADO\n"
                f"  ⏱️  Duración Total: {duration:.2f}s\n"
                f"  📊 Registros: {execution_result['row_count']}\n"
                f"  📝 SQL Query: {sql_query[:100]}...\n"
                f"  📝 Resumen: {formatted_results['summary'][:100]}..."
            )
            
            self.log_execution(
                input_summary=query[:100],
                output_summary=f"{execution_result['row_count']} registros",
                success=True,
                duration=duration
            )
            
            return result
            
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"[{self.agent_name}] ❌ ERROR EN ANÁLISIS\n"
                f"  ⏱️  Duración: {duration:.2f}s\n"
                f"  🚫 Error: {type(e).__name__}: {str(e)}"
            )
            
            self.log_execution(
                input_summary=query[:100],
                output_summary=f"Error: {str(e)}",
                success=False,
                duration=time.time() - start_time
            )
            
            return {
                'success': False,
                'error': str(e),
                'agent': 'data_analyst'
            }
    
    def _generate_sql(
        self,
        query: str,
        periodo: Dict[str, Any],
        filters: Dict[str, Any],
        limit: int,
        persistence_map: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Genera una consulta SQL a partir de la pregunta en lenguaje natural
        
        Args:
            query: Pregunta del usuario
            periodo: Periodo solicitado
            filters: Filtros adicionales
            limit: Límite de resultados
            persistence_map: Mapa de persistencia del LogicInterpreter (opcional)
            
        Returns:
            Dict con SQL generado
        """
        # NUEVO: Si tenemos mapa de persistencia, usarlo prioritariamente
        field_usage_maps = {}
        if persistence_map and persistence_map.get('tablas_sugeridas'):
            logger.info(
                f"[{self.agent_name}] 🗺️  Usando mapa de persistencia\n"
                f"  📋 Tablas sugeridas: {[t['nombre'] for t in persistence_map['tablas_sugeridas'][:5]]}\n"
                f"  🔗 Relaciones: {len(persistence_map.get('relaciones_candidatas', []))}"
            )
            schema_result = self._get_schemas_from_persistence_map(persistence_map)
            schema_details = schema_result.get('schemas', {})
            field_usage_maps = schema_result.get('field_usage_maps', {})  # NUEVO
        else:
            # Fallback: identificar tablas por keywords en la query
            schema_details = self._get_relevant_schemas(query)
        
        # Construir contexto para el LLM con TODAS las columnas importantes
        # Y el propósito funcional de cada campo
        schema_context = ""
        if schema_details:
            schema_context = "SCHEMA REAL DE MYSQL (USA SOLO ESTAS COLUMNAS):\n\n"
            for table, columns in schema_details.items():
                schema_context += f"Tabla {table}:\n"
                
                # Obtener field usage map de esta tabla
                table_usage_map = field_usage_maps.get(table, {})
                
                # Mostrar TODAS las columnas con sus comentarios Y PROPÓSITO
                for col in columns:
                    col_name = col['column_name']
                    comment = f" -- {col['column_comment']}" if col.get('column_comment') else ""
                    
                    # Agregar propósito funcional si está disponible
                    purpose_info = ""
                    if col_name in table_usage_map:
                        purpose = table_usage_map[col_name].get('purpose', '')
                        ui_caption = table_usage_map[col_name].get('ui_caption', '')
                        
                        if purpose == 'primary_search':
                            purpose_info = " [BUSCAR AQUÍ: usa este campo para búsquedas por texto]"
                        elif purpose == 'identifier':
                            purpose_info = " [ID: identificador único]"
                        elif purpose == 'description':
                            purpose_info = " [DETALLE: descripción adicional, NO usar para búsquedas principales]"
                        elif purpose == 'filter':
                            purpose_info = " [FILTRO: para filtrar por categorías/opciones]"
                        
                        if ui_caption:
                            purpose_info += f" (UI: '{ui_caption}')"
                    
                    schema_context += f"  • {col_name} ({col['data_type']}){comment}{purpose_info}\n"
                schema_context += "\n"
            
            # Agregar ejemplos de uso común
            schema_context += "\n⚠️ REGLAS CRÍTICAS DE BÚSQUEDA:\n"
            schema_context += "- Para buscar por NOMBRE/DESCRIPCIÓN: usa campos marcados [BUSCAR AQUÍ] (ej: NombreArticulo)\n"
            schema_context += "- Los campos [DETALLE] son solo para info adicional, NO para búsquedas principales\n"
            schema_context += "- Ejemplo CORRECTO: WHERE NombreArticulo LIKE '%texto%'\n"
            schema_context += "- Ejemplo INCORRECTO: WHERE Detalle LIKE '%texto%'\n\n"
            schema_context += "EJEMPLOS DE USO:\n"
            schema_context += "- Para 'stock actual' usa: saldo_articulo\n"
            schema_context += "- Para 'sin stock' usa: WHERE saldo_articulo = 0\n"
            schema_context += "- Para 'nombre producto' usa: NombreArticulo [BUSCAR AQUÍ]\n"
            schema_context += "- Para 'precio' usa: Precio1V (precio de venta lista 1)\n"
            schema_context += "- Para 'solo artículos' usa: WHERE tipo_art = 'Articulo'\n"
            schema_context += "- Para 'activos' usa: WHERE Discontinuo = 'No'\n\n"
        elif self.available_tables:
            schema_context = f"Tablas disponibles: {', '.join(self.available_tables[:20])}"
        
        periodo_context = ""
        if periodo:
            periodo_context = f"Periodo: desde {periodo.get('desde')} hasta {periodo.get('hasta')}"
        elif 'ultimo' in query.lower() or 'últim' in query.lower():
            periodo_context = "Periodo: últimos 12 meses (usar fechas relativas)"
        
        messages = [
            {
                'role': 'system',
                'content': self.get_system_prompt()
            },
            {
                'role': 'user',
                'content': f"""Genera SOLO la consulta SQL SELECT (sin explicaciones) para:

Pregunta: {query}
{schema_context}
{periodo_context}

Reglas:
- Solo SELECT, sin DML/DDL
- Usar LIKE '%texto%' para búsquedas
- Aplicar LIMIT {limit}
- Redondear ROUND(columna, 2) para precios
- Nombres descriptivos en SELECT

Responde SOLO con el SQL, nada más."""
            }
        ]
        
        response = self._call_llm(messages, max_tokens=500)
        
        if not response['success']:
            return {'success': False}
        
        # Extraer SQL del contenido
        sql = response['content'].strip()
        
        # Limpiar markdown si existe
        sql = sql.replace('```sql', '').replace('```', '').strip()
        
        # Validar que sea SELECT
        if not sql.upper().startswith('SELECT'):
            logger.warning(f"[Analista de Datos] SQL generado no válido: {sql[:100]}")
            return {'success': False}
        
        logger.info(f"[Analista de Datos] SQL generado exitosamente")
        
        return {
            'success': True,
            'sql': sql
        }
    
    def _get_relevant_schemas(self, query: str) -> Dict[str, List[Dict]]:
        """
        Identifica tablas relevantes basándose en la query
        y obtiene su schema completo
        
        Args:
            query: Pregunta del usuario
            
        Returns:
            Dict con {nombre_tabla: [columnas con metadata]}
        """
        query_lower = query.lower()
        
        # Mapeo de términos de negocio → tablas
        # IMPORTANTE: Solo incluir tablas que EXISTEN en la DB
        table_keywords = {
            'articulo': ['producto', 'articulo', 'item', 'mercadería', 'stock', 'precio', 'inventario', 'sin stock'],
            'cliente': ['cliente', 'comprador', 'consumidor'],
            'proveedor': ['proveedor', 'proveedores'],
            'comprobante': ['factura', 'venta', 'comprobante', 'ticket', 'recibo'],
            'datosempresa': ['empresa', 'compañía', 'negocio'],
            'viajante': ['vendedor', 'viajante', 'representante'],
            'sucursal': ['sucursal', 'branch', 'local'],
            'rubro': ['rubro', 'categoría', 'categoria'],
            'marca': ['marca', 'brand'],
        }
        
        # Identificar tablas relevantes
        relevant_tables = []
        for table, keywords in table_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                relevant_tables.append(table)
        
        # Si no se identificó ninguna, usar 'articulo' como default
        if not relevant_tables:
            relevant_tables = ['articulo']
        
        # Obtener schema de cada tabla
        schemas = {}
        for table in relevant_tables[:2]:  # Máximo 2 tablas para no exceder tokens (con todas las columnas)
            schema_info = self.mysql_tool.get_schema_info(table)
            if schema_info['success'] and len(schema_info['data']) > 0:
                schemas[table] = schema_info['data']
                logger.info(f"[{self.agent_name}] ✅ Schema obtenido para tabla '{table}': {len(schema_info['data'])} columnas")
            else:
                logger.warning(f"[{self.agent_name}] ⚠️ Tabla '{table}' no existe o está vacía, se omite")
        
        return schemas
    
    def _get_schemas_from_persistence_map(self, persistence_map: Dict[str, Any]) -> Dict[str, Any]:
        """
        Obtiene schemas basándose en el mapa de persistencia del LogicInterpreter
        CON información de propósito funcional de cada campo
        
        Args:
            persistence_map: Mapa de persistencia con tablas sugeridas y field_usage_map
            
        Returns:
            Dict con {nombre_tabla: [columnas con metadata]} y field_usage_maps
        """
        schemas = {}
        field_usage_maps = {}  # NUEVO: Mapeos de propósito de campos
        
        tablas_sugeridas = persistence_map.get('tablas_sugeridas', [])
        
        logger.info(
            f"[{self.agent_name}] 🔍 Procesando mapa de persistencia\n"
            f"  📋 Tablas en mapa: {len(tablas_sugeridas)}"
        )
        
        for table_info in tablas_sugeridas[:3]:  # Máximo 3 tablas
            table_name = table_info.get('nombre')
            confidence = table_info.get('confianza', 0.0)
            suggested_fields = table_info.get('campos_clave_sugeridos', [])
            field_usage_map = table_info.get('field_usage_map', {})  # NUEVO
            
            logger.info(
                f"[{self.agent_name}] Verificando tabla '{table_name}'\n"
                f"  📊 Confianza: {confidence:.2f}\n"
                f"  🔑 Campos sugeridos: {suggested_fields[:5]}\n"
                f"  🎯 Field usage map: {len(field_usage_map)} campos con propósito"
            )
            
            # Verificar si la tabla existe en MySQL
            schema_info = self.mysql_tool.get_schema_info(table_name)
            
            if schema_info['success'] and len(schema_info['data']) > 0:
                schemas[table_name] = schema_info['data']
                
                # Guardar field usage map para esta tabla
                if field_usage_map:
                    field_usage_maps[table_name] = field_usage_map
                    
                    # Log de campos por propósito
                    search_fields = [f for f, info in field_usage_map.items() if info.get('purpose') == 'primary_search']
                    if search_fields:
                        logger.info(
                            f"[{self.agent_name}] 🔍 Campos de búsqueda principal: {search_fields}"
                        )
                
                logger.info(
                    f"[{self.agent_name}] ✅ Tabla '{table_name}' VERIFICADA\n"
                    f"  📊 Columnas reales: {len(schema_info['data'])}"
                )
                
                # Validar campos sugeridos contra schema real
                real_columns = [col['column_name'] for col in schema_info['data']]
                matched_fields = [f for f in suggested_fields if f in real_columns]
                
                if matched_fields:
                    logger.info(
                        f"[{self.agent_name}] ✅ Campos coincidentes: {matched_fields[:5]}"
                    )
                else:
                    logger.warning(
                        f"[{self.agent_name}] ⚠️  Ningún campo sugerido coincide con schema real"
                    )
            else:
                logger.warning(
                    f"[{self.agent_name}] ❌ Tabla '{table_name}' NO EXISTE en MySQL\n"
                    f"  🔄 Intentando con fallback..."
                )
                # Fallback: buscar tabla similar
                similar_table = self._find_similar_table(table_name)
                if similar_table:
                    schema_info = self.mysql_tool.get_schema_info(similar_table)
                    if schema_info['success']:
                        schemas[similar_table] = schema_info['data']
                        logger.info(f"[{self.agent_name}] ✅ Usando tabla similar: '{similar_table}'")
        
        return {
            'schemas': schemas,
            'field_usage_maps': field_usage_maps  # NUEVO: Devolver mapas de propósito
        }
    
    def _find_similar_table(self, table_name: str) -> Optional[str]:
        """
        Busca una tabla similar en el schema
        
        Args:
            table_name: Nombre de tabla que no existe
            
        Returns:
            Nombre de tabla similar o None
        """
        table_lower = table_name.lower()
        
        # Buscar en tablas disponibles
        for available_table in self.available_tables:
            available_lower = available_table.lower()
            
            # Coincidencia parcial
            if table_lower in available_lower or available_lower in table_lower:
                return available_table
            
            # Coincidencia por palabras clave
            table_words = table_lower.split('_')
            available_words = available_lower.split('_')
            
            common_words = set(table_words) & set(available_words)
            if len(common_words) > 0:
                return available_table
        
        return None
    
    def _format_results_for_business(
        self,
        data: List[Dict[str, Any]],
        original_query: str
    ) -> Dict[str, Any]:
        """
        Formatea resultados de SQL en lenguaje de negocio
        
        Args:
            data: Datos raw de MySQL
            original_query: Consulta original del usuario
            
        Returns:
            Dict con datos formateados y resumen
        """
        if not data or len(data) == 0:
            return {
                'data': [],
                'summary': 'No se encontraron registros que coincidan con la consulta.'
            }
        
        # Redondear valores numéricos (precios, moneda)
        formatted_data = []
        for row in data:
            formatted_row = {}
            for key, value in row.items():
                if isinstance(value, float):
                    # Redondear a 2 decimales
                    formatted_row[key] = round(value, 2)
                else:
                    formatted_row[key] = value
            formatted_data.append(formatted_row)
        
        # Generar resumen
        count = len(formatted_data)
        summary = f"Se encontraron {count} registro(s)."
        
        # Identificar columnas principales para el resumen
        first_row = formatted_data[0]
        name_columns = [k for k in first_row.keys() if 'nombre' in k.lower() or 'descripcion' in k.lower()]
        
        if name_columns and count <= 10:
            # Listar nombres si hay pocos resultados
            names = [str(row.get(name_columns[0], '')) for row in formatted_data[:10]]
            summary += f" Ejemplos: {', '.join(names[:5])}"
            if count > 5:
                summary += f" y {count - 5} más."
        
        return {
            'data': formatted_data,
            'summary': summary
        }
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Obtiene el schema de una tabla específica
        
        Args:
            table_name: Nombre de la tabla
            
        Returns:
            Dict con columnas y tipos
        """
        try:
            schema = self.mysql_tool.get_schema_info(table_name)
            return schema
        except Exception as e:
            logger.error(f"Error obteniendo schema de {table_name}: {e}")
            return {'success': False, 'data': []}
    
    # ========================================================================
    # NUEVOS MÉTODOS: Integración con SchemaGraph y SynonymService
    # ========================================================================
    
    def _initialize_schema_graph(self):
        """Inicializa el SchemaGraph si no está creado"""
        if self.schema_graph is None:
            from reports_ai.services.schema_graph import SchemaGraph
            self.schema_graph = SchemaGraph(min_confidence=0.7)
            logger.info(f"[{self.agent_name}] 🗺️  SchemaGraph inicializado")
    
    def find_join_path(
        self,
        tables: List[str],
        strategy: str = 'star'
    ) -> Optional[List[Dict]]:
        """
        Encuentra el camino óptimo de joins para conectar múltiples tablas
        
        Args:
            tables: Lista de tablas a conectar
            strategy: 'star' (desde tabla central) o 'chain' (secuencial)
        
        Returns:
            Lista de relaciones/joins necesarios
        """
        self._initialize_schema_graph()
        
        if len(tables) == 2:
            # Dos tablas: buscar camino directo
            return self.schema_graph.find_shortest_path(tables[0], tables[1])
        elif len(tables) > 2:
            # Múltiples tablas: usar estrategia
            return self.schema_graph.find_multi_table_path(tables, strategy=strategy)
        
        return []
    
    def resolve_business_term(
        self,
        term: str,
        context_table: Optional[str] = None
    ) -> List[Dict]:
        """
        Resuelve un término de negocio a columnas técnicas
        
        Args:
            term: Término de negocio (ej: 'provincia', 'cliente', 'total')
            context_table: Tabla de contexto para priorizar
        
        Returns:
            Lista de posibles columnas ordenadas por confianza
        """
        return self.synonym_service.resolve_business_term(
            term,
            context_table=context_table,
            min_confidence=0.5
        )
    
    def generate_sql_with_joins(
        self,
        query: str,
        tables: List[str],
        filters: Dict[str, Any] = None,
        limit: int = 1000
    ) -> str:
        """
        Genera SQL automáticamente con los joins necesarios
        
        Args:
            query: Pregunta del usuario
            tables: Tablas identificadas para la consulta
            filters: Filtros adicionales
            limit: Límite de resultados
        
        Returns:
            SQL query completo con joins
        """
        self._initialize_schema_graph()
        
        # 1. Encontrar camino de joins
        join_path = self.find_join_path(tables, strategy='star')
        
        if not join_path:
            logger.warning(
                f"[{self.agent_name}] ⚠️  No se encontró camino de join entre {tables}"
            )
            # Fallback: query sin joins (solo tabla principal)
            return self._generate_simple_sql(query, tables[0], filters, limit)
        
        # 2. Construir SQL con joins
        main_table = tables[0]
        sql_parts = [f"SELECT * FROM {main_table}"]
        
        for join in join_path:
            sql_parts.append(
                f"JOIN {join['target_table']} ON "
                f"{join['source_table']}.{join['source_column']} = "
                f"{join['target_table']}.{join['target_column']}"
            )
        
        # 3. Agregar filtros
        where_clauses = []
        if filters:
            for key, value in filters.items():
                if isinstance(value, str):
                    where_clauses.append(f"{key} LIKE '%{value}%'")
                else:
                    where_clauses.append(f"{key} = {value}")
        
        if where_clauses:
            sql_parts.append(f"WHERE {' AND '.join(where_clauses)}")
        
        # 4. Agregar limit
        sql_parts.append(f"LIMIT {limit}")
        
        return " ".join(sql_parts)
    
    def _generate_simple_sql(
        self,
        query: str,
        table: str,
        filters: Dict[str, Any],
        limit: int
    ) -> str:
        """Genera SQL simple sin joins (fallback)"""
        sql = f"SELECT * FROM {table}"
        
        if filters:
            where_clauses = []
            for key, value in filters.items():
                if isinstance(value, str):
                    where_clauses.append(f"{key} LIKE '%{value}%'")
                else:
                    where_clauses.append(f"{key} = {value}")
            
            if where_clauses:
                sql += f" WHERE {' AND '.join(where_clauses)}"
        
        sql += f" LIMIT {limit}"
        return sql
    
    def mark_query_success(
        self,
        query: str,
        tables_used: List[str],
        columns_used: Dict[str, List[str]]
    ):
        """
        Marca una query como exitosa para active learning
        Actualiza las confianzas de sinónimos y relaciones
        
        Args:
            query: Query original del usuario
            tables_used: Tablas usadas en el SQL
            columns_used: Dict {tabla: [columnas]}
        """
        # Extraer términos de negocio de la query
        business_terms = self._extract_business_terms(query)
        
        # Actualizar sinónimos exitosos
        for term in business_terms:
            for table, columns in columns_used.items():
                for column in columns:
                    self.synonym_service.update_success(term, table, column)
        
        # Actualizar relaciones exitosas (si se usaron joins)
        if len(tables_used) > 1:
            self._update_relationship_success(tables_used)
    
    def mark_query_failure(
        self,
        query: str,
        reason: str,
        attempted_tables: List[str] = None,
        attempted_columns: Dict[str, List[str]] = None
    ):
        """
        Marca una query como fallida para active learning
        
        Args:
            query: Query original
            reason: Razón del fallo
            attempted_tables: Tablas intentadas
            attempted_columns: Columnas intentadas
        """
        logger.warning(
            f"[{self.agent_name}] ❌ Query fallida\n"
            f"  📝 Query: {query[:100]}\n"
            f"  🚫 Razón: {reason}\n"
            f"  📊 Tablas: {attempted_tables}\n"
            f"  📋 Columnas: {attempted_columns}"
        )
        
        # Actualizar sinónimos fallidos
        if attempted_columns:
            business_terms = self._extract_business_terms(query)
            for term in business_terms:
                for table, columns in attempted_columns.items():
                    for column in columns:
                        self.synonym_service.update_failure(term, table, column)
    
    def _extract_business_terms(self, query: str) -> List[str]:
        """
        Extrae términos de negocio de una query en lenguaje natural
        
        Args:
            query: Query del usuario
        
        Returns:
            Lista de términos de negocio
        """
        # Stopwords simples
        stopwords = {
            'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'que',
            'en', 'con', 'por', 'para', 'y', 'o', 'a', 'dame', 'muestra',
            'quiero', 'necesito', 'ver', 'todos', 'todas'
        }
        
        # Tokenizar y filtrar
        words = query.lower().split()
        terms = [w for w in words if w not in stopwords and len(w) > 2]
        
        return terms
    
    def _update_relationship_success(self, tables: List[str]):
        """Actualiza el score de relaciones usadas exitosamente"""
        from reports_ai.models import RelationshipCandidate
        from django.utils import timezone
        
        # Actualizar cada par de tablas
        for i in range(len(tables) - 1):
            relationships = RelationshipCandidate.objects.filter(
                source_table=tables[i],
                target_table=tables[i + 1]
            )
            
            for rel in relationships:
                rel.times_used_successfully += 1
                rel.last_used_at = timezone.now()
                rel.update_confidence()
                rel.save()

