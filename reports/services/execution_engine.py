"""
Motor de ejecución declarativa de reportes.

Este módulo implementa un sistema declarativo para generar y ejecutar reportes
basado en configuración JSON almacenada en ReportDefinition.config.

Fase 1: Implementación básica con soporte para:
- Métricas simples y derivadas
- Dimensiones
- Filtros parametrizados
- Agrupación y ordenamiento
- Integración con caché y connection pool
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
import logging
import hashlib
import json
import re
from datetime import datetime, date
from decimal import Decimal

from django.utils import timezone
from django.conf import settings

from ..models import ReportDefinition, ReportExecutionLog
from ..cache import get_cached_report, set_cached_report, build_cache_key
from .connection_pool import get_mysql_pool
# QueryResult se importa de forma diferida para evitar circular imports

logger = logging.getLogger(__name__)


@dataclass
class MetricDefinition:
    """Definición de una métrica calculable."""
    name: str
    expression: str  # Expresión SQL o referencia a otra métrica
    depends_on: List[str] = field(default_factory=list)  # Para métricas derivadas


@dataclass
class DimensionDefinition:
    """Definición de una dimensión (campo de agrupación)."""
    name: str
    expression: str  # Columna o expresión SQL


@dataclass
class FilterDefinition:
    """Definición de un filtro aplicable."""
    name: str
    field: str  # Columna o expresión SQL
    operator: str  # '=', '>=', '<=', 'IN', 'BETWEEN', 'LIKE', etc.
    param: str  # Nombre del parámetro que se espera en payload (solo para filtros variables)
    is_variable: bool = True  # Si True, es un parámetro variable; si False, es constante
    constant_value: Optional[str] = None  # Valor constante para filtros no variables


@dataclass
class ReportConfig:
    """Configuración completa de un reporte declarativo."""
    version: str  # "declarative-v1"
    datasource: str  # Tabla base o vista, ej: "cuentacliente"
    metrics: Dict[str, MetricDefinition]
    dimensions: Dict[str, DimensionDefinition]
    filters: List[FilterDefinition] = field(default_factory=list)
    group_by: List[str] = field(default_factory=list)  # Nombres de dimensiones
    order_by: Optional[List[str]] = None
    notes: Optional[List[str]] = None
    options: Dict[str, Any] = field(default_factory=dict)
    joins: Optional[List[Dict[str, str]]] = None  # JOINs opcionales: [{"type": "LEFT", "table": "sucursales", "on": "s.id_sucursal = cc.CodSucursal"}]


class SqlQueryBuilder:
    """
    Constructor de consultas SQL parametrizadas a partir de configuración declarativa.
    
    Genera SQL seguro con parámetros para prevenir SQL injection.
    """
    
    def __init__(self, config: ReportConfig):
        """
        Inicializa el builder con una configuración de reporte.
        
        Args:
            config: Configuración del reporte declarativo
        """
        self.config = config
    
    def build(self, payload: Dict[str, Any]) -> Tuple[str, List[Any]]:
        """
        Construye una consulta SQL parametrizada y sus parámetros.
        
        Args:
            payload: Payload con filtros del request
            
        Returns:
            Tupla (sql_query, params) donde params es la lista de valores para los placeholders
        """
        filters_dict = payload.get("filters", {})
        logger.debug(f"🔍 SqlQueryBuilder.build - filters_dict recibido: {json.dumps(filters_dict, default=str)}")
        
        # Construir SELECT: dimensiones + métricas
        select_parts = []
        
        # Helper para escapar % en expresiones SQL (para DATE_FORMAT, etc.)
        def escape_sql_percent(expr: str) -> str:
            """Escapa % en expresiones SQL para evitar conflictos con f-strings."""
            return expr.replace('%', '%%')
        
        def clean_alias(alias: str) -> str:
            """
            Limpia un alias para que sea un identificador SQL válido.
            Remueve puntos y otros caracteres inválidos, reemplazándolos por guiones bajos.
            """
            if not alias:
                return alias
            # Reemplazar puntos y otros caracteres inválidos por guiones bajos
            cleaned = alias.replace('.', '_').replace(' ', '_').replace('-', '_')
            # Remover caracteres especiales que no son válidos en identificadores SQL
            cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', cleaned)
            # Asegurar que no empiece con número
            if cleaned and cleaned[0].isdigit():
                cleaned = '_' + cleaned
            return cleaned
        
        # Construir mapa de alias de tabla -> nombre de tabla para normalizar expresiones
        # Primero obtener alias de tabla base
        datasource_parts = self.config.datasource.split()
        if len(datasource_parts) == 1:
            table_name = datasource_parts[0]
            base_alias = table_name[0].lower() if table_name else "c"
        else:
            table_name = datasource_parts[0]
            base_alias = datasource_parts[1] if len(datasource_parts) > 1 else table_name[0].lower()
        
        alias_to_table = {base_alias: table_name}
        
        # Agregar alias de JOINs
        if self.config.joins:
            for join_def in self.config.joins:
                join_table_raw = join_def.get("table", "")
                # Parsear join_table para extraer nombre de tabla y alias si ya existe
                join_table_clean, join_alias_from_string = self._parse_table_alias(join_table_raw)
                join_alias = join_def.get("alias", "")
                if join_table_clean:
                    if not join_alias:
                        if join_alias_from_string:
                            join_alias = join_alias_from_string
                        else:
                            # Generar alias por defecto
                            words = join_table_clean.split('_')
                            if len(words) > 1:
                                join_alias = ''.join(w[0] for w in words if w)[:3].lower()
                            else:
                                join_alias = join_table_clean[:2].lower()
                    alias_to_table[join_alias] = join_table_clean
        
        # Helper para normalizar expresiones agregando/corrigiendo alias de tabla cuando sea necesario
        def normalize_expression(expr: str, default_alias: str = None) -> str:
            """
            Normaliza una expresión SQL agregando alias de tabla cuando sea necesario.
            
            Si la expresión es un simple nombre de campo (sin punto ni funciones),
            y hay JOINs, intenta agregar el alias de tabla base por defecto.
            """
            expr = expr.strip()
            
            # IMPORTANTE: Si es una expresión CASE, normalizar solo los alias, preservando la estructura
            # Las expresiones CASE son complejas pero necesitan normalización de alias
            expr_upper = expr.upper().strip()
            is_case_expr = (expr_upper.startswith('CASE') or 
                           ' CASE ' in expr_upper or 
                           expr_upper.startswith('CASE ') or
                           any(op in expr_upper for op in [' WHEN ', ' THEN ', ' ELSE ', ' END']))
            if is_case_expr:
                logger.debug(f"🔍 normalize_expression: Detectada expresión CASE, normalizando alias: '{expr[:100]}...'")
                # Normalizar alias dentro de la expresión CASE usando regex
                # Reemplazar patrones como "cc.campo" o "cu.campo" por el alias correcto
                import re
                # Patrón para encontrar alias.columna dentro de la expresión
                pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b'
                def replace_alias(match):
                    alias_part = match.group(1)
                    column_part = match.group(2)
                    # Si el alias está en el mapa, usar el correcto
                    if alias_part.lower() in [k.lower() for k in alias_to_table.keys()]:
                        # Buscar el alias correcto (case-insensitive)
                        for correct_alias in alias_to_table.keys():
                            if correct_alias.lower() == alias_part.lower():
                                return f"{correct_alias}.{column_part}"
                    # Si no está en el mapa pero es un alias común alternativo (cc, cu, c, cp), usar base_alias
                    # cp es común para comp_ped, cc/cu para cuentacliente
                    if alias_part.lower() in ['cc', 'cu', 'c', 'cp'] and default_alias:
                        return f"{default_alias}.{column_part}"
                    # Si no se encuentra, devolver tal cual
                    return match.group(0)
                
                normalized = re.sub(pattern, replace_alias, expr)
                return normalized
            
            # Si es una función SQL (contiene paréntesis), normalizar solo el contenido interno
            # Ejemplo: COUNT(co.Fecha) -> COUNT(c.Fecha), DATE_FORMAT(cc.Fecha, '%%Y-%%m') -> DATE_FORMAT(c.Fecha, '%%Y-%%m')
            import re
            # Detectar funciones SQL: SUM(...), COUNT(...), AVG(...), DATE_FORMAT(...), etc.
            # Mejorar regex para capturar funciones con múltiples parámetros
            # Buscar función al inicio: nombre_funcion(contenido)
            # Mejorar detección de funciones: usar contador de paréntesis para manejar funciones anidadas
            func_start_match = re.match(r'^(\w+)\s*\(', expr, re.IGNORECASE)
            if func_start_match:
                func_name = func_start_match.group(1).upper()
                # Encontrar el cierre del paréntesis principal contando paréntesis
                paren_start = func_start_match.end() - 1  # Posición del '('
                paren_count = 0
                inner_start = paren_start + 1
                inner_end = len(expr)
                
                for i in range(paren_start, len(expr)):
                    if expr[i] == '(':
                        paren_count += 1
                    elif expr[i] == ')':
                        paren_count -= 1
                        if paren_count == 0:
                            # Encontramos el cierre del paréntesis principal
                            inner_end = i
                            break
                
                inner_expr = expr[inner_start:inner_end].strip()
                
                # Para COUNT(DISTINCT ...), manejar de forma especial (antes de otras funciones COUNT)
                if func_name == 'COUNT' and inner_expr.upper().strip().startswith('DISTINCT'):
                    distinct_part = inner_expr[8:].strip()  # Remover "DISTINCT "
                    # Limpiar paréntesis extra si existen
                    distinct_open = distinct_part.count('(')
                    distinct_close = distinct_part.count(')')
                    if distinct_close > distinct_open:
                        extra_closes = distinct_close - distinct_open
                        for _ in range(extra_closes):
                            if distinct_part.endswith(')'):
                                distinct_part = distinct_part[:-1].rstrip()
                    if '.' in distinct_part:
                        normalized_distinct = self._normalize_alias_in_expression(distinct_part, alias_to_table, default_alias or base_alias)
                        return f"COUNT(DISTINCT {normalized_distinct})"
                    else:
                        return expr
                # Si el nombre de la función es una función de agregación conocida
                elif func_name in ('SUM', 'COUNT', 'AVG', 'MAX', 'MIN'):
                    # Normalizar solo el contenido interno
                    if inner_expr:
                        # IMPORTANTE: Si el contenido interno es una expresión CASE, no normalizar (devolver tal cual)
                        inner_upper = inner_expr.upper().strip()
                        if (inner_upper.startswith('CASE') or 
                            ' CASE ' in inner_upper or 
                            any(op in inner_upper for op in [' WHEN ', ' THEN ', ' ELSE ', ' END'])):
                            return expr
                        # Si el contenido interno tiene un punto, normalizar el alias
                        if '.' in inner_expr:
                            normalized_inner = self._normalize_alias_in_expression(inner_expr, alias_to_table, default_alias or base_alias)
                            return f"{func_name}({normalized_inner})"
                        else:
                            # Si no tiene punto, puede ser una expresión compleja o COUNT(*)
                            if inner_expr.strip() == '*':
                                return expr
                            # Verificar si es una expresión compleja (CASE, operadores, etc.) antes de normalizar
                            if any(op in inner_expr.upper() for op in [' CASE ', ' WHEN ', ' THEN ', ' ELSE ', ' END']):
                                return expr
                            # Para otras expresiones, normalizarlas recursivamente
                            normalized_inner = normalize_expression(inner_expr, default_alias)
                            return f"{func_name}({normalized_inner})"
                    else:
                        # Paréntesis vacíos, no modificar
                        return expr
                # Para otras funciones SQL (DATE_FORMAT, COALESCE, etc.), normalizar alias dentro
                else:
                    # Normalizar alias dentro de la función usando regex
                    if '.' in inner_expr:
                        import re
                        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b'
                        def replace_alias(match):
                            alias_part = match.group(1)
                            column_part = match.group(2)
                            # Si el alias está en el mapa, usar el correcto
                            if alias_part.lower() in [k.lower() for k in alias_to_table.keys()]:
                                for correct_alias in alias_to_table.keys():
                                    if correct_alias.lower() == alias_part.lower():
                                        return f"{correct_alias}.{column_part}"
                            # Si no está en el mapa pero es un alias común alternativo (cc, cu, c, cp), usar base_alias
                            # cp es común para comp_ped, cc/cu para cuentacliente
                            if alias_part.lower() in ['cc', 'cu', 'c', 'cp'] and (default_alias or base_alias):
                                return f"{(default_alias or base_alias)}.{column_part}"
                            return match.group(0)
                        
                        normalized_inner = re.sub(pattern, replace_alias, inner_expr)
                        return f"{func_name}({normalized_inner})"
                    else:
                        # Sin puntos, puede ser una función con solo constantes o sin parámetros
                        # Intentar normalizar recursivamente por si acaso
                        normalized_inner = normalize_expression(inner_expr, default_alias)
                        if normalized_inner != inner_expr:
                            return f"{func_name}({normalized_inner})"
                        return expr
            
            # Si es una expresión compleja (contiene operadores, CASE, etc.), no modificar
            # IMPORTANTE: Verificar esto ANTES de normalizar alias con puntos
            expr_upper = expr.upper()
            if any(op in expr_upper for op in [' AS ', ' + ', ' - ', ' * ', ' / ', ' CASE ', 'CASE ', ' WHEN ', ' THEN ', ' ELSE ', ' END']):
                return expr
            
            # Si ya tiene alias de tabla (contiene punto) pero no es función, normalizarlo/corregirlo
            if '.' in expr:
                return self._normalize_alias_in_expression(expr, alias_to_table, default_alias or base_alias)
            
            # Si hay JOINs y la expresión es un simple nombre de campo, agregar alias base
            if self.config.joins and default_alias:
                # Verificar que no sea una palabra clave SQL
                sql_keywords = {'SELECT', 'FROM', 'WHERE', 'GROUP', 'BY', 'ORDER', 'HAVING', 
                              'JOIN', 'INNER', 'LEFT', 'RIGHT', 'ON', 'AND', 'OR', 'NOT', 'NULL'}
                if expr.upper() not in sql_keywords:
                    return f"{default_alias}.{expr}"
            
            return expr
        
        # Agregar dimensiones al SELECT
        for dim_name, dim_def in self.config.dimensions.items():
            # Normalizar expresión para agregar alias si es necesario
            logger.debug(f"🔍 Dimensión {dim_name}: expresión original = '{dim_def.expression}'")
            normalized_expr = normalize_expression(dim_def.expression, base_alias)
            logger.debug(f"🔍 Dimensión {dim_name}: expresión normalizada = '{normalized_expr}'")
            escaped_expr = escape_sql_percent(normalized_expr)
            # Alias entre backticks para permitir nombres con puntos u otros caracteres
            select_parts.append(f"{escaped_expr} AS `{dim_name}`")
        
        # Agregar métricas al SELECT
        # Primero procesar métricas que no dependen de otras
        base_metrics = {name: metric for name, metric in self.config.metrics.items() 
                       if not metric.depends_on}
        
        # Luego procesar métricas derivadas (que dependen de otras)
        derived_metrics = {name: metric for name, metric in self.config.metrics.items() 
                          if metric.depends_on}
        
        # Función auxiliar para limpiar paréntesis extra (si no está definida)
        def clean_expression_local(expr: str) -> str:
            """Limpia paréntesis extra al final de expresiones SQL."""
            if not expr or not isinstance(expr, str):
                return expr
            expr = expr.strip()
            # IMPORTANTE: Si es una expresión CASE, no limpiar (devolver tal cual)
            expr_upper = expr.upper().strip()
            if (expr_upper.startswith('CASE') or 
                ' CASE ' in expr_upper or 
                expr_upper.startswith('CASE ') or
                any(op in expr_upper for op in [' WHEN ', ' THEN ', ' ELSE ', ' END'])):
                return expr
            open_count = expr.count('(')
            close_count = expr.count(')')
            if close_count > open_count:
                extra_closes = close_count - open_count
                expr = expr.rstrip()
                for _ in range(extra_closes):
                    if expr.endswith(')'):
                        expr = expr[:-1].rstrip()
            return expr
        
        # Agregar métricas base (con SUM si hay GROUP BY, o directamente si no)
        for metric_name, metric_def in base_metrics.items():
            # Logging para debug: ver expresión original
            logger.debug(f"🔍 Métrica {metric_name}: expresión original = '{metric_def.expression}'")
            # Limpiar expresión de paréntesis extra antes de procesar
            cleaned_expr = clean_expression_local(metric_def.expression)
            logger.debug(f"🔍 Métrica {metric_name}: expresión limpiada = '{cleaned_expr}'")
            # Normalizar expresión para agregar alias si es necesario
            normalized_expr = normalize_expression(cleaned_expr, base_alias)
            logger.debug(f"🔍 Métrica {metric_name}: expresión normalizada = '{normalized_expr}'")
            escaped_expr = escape_sql_percent(normalized_expr)
            logger.debug(f"🔍 Métrica {metric_name}: expresión escapada = '{escaped_expr}'")
            
            # Verificar si la expresión ya contiene un operador de agregación
            has_aggregation = any(func in normalized_expr.upper() for func in ['SUM', 'COUNT', 'AVG', 'MAX', 'MIN'])
            
            if self.config.group_by:
                # Si hay agrupación y la expresión ya tiene un operador de agregación, usarla tal cual
                # Si no tiene operador, envolver en SUM
                if has_aggregation:
                    select_parts.append(f"{escaped_expr} AS `{metric_name}`")
                else:
                    select_parts.append(f"SUM({escaped_expr}) AS `{metric_name}`")
            else:
                # Sin agrupación, expresión directa (puede ser agregada o no)
                select_parts.append(f"{escaped_expr} AS `{metric_name}`")
        
        # Para métricas derivadas, calcularlas en el SELECT usando las métricas base
        for metric_name, metric_def in derived_metrics.items():
            # Limpiar expresión de paréntesis extra antes de procesar
            expression = clean_expression_local(metric_def.expression)
            # Reemplazar referencias a otras métricas por sus expresiones
            for dep_name in metric_def.depends_on:
                if dep_name in base_metrics:
                    # Reemplazar nombre de métrica por su expresión
                    if self.config.group_by:
                        dep_expression = escape_sql_percent(base_metrics[dep_name].expression)
                        dep_expression = f"SUM({dep_expression})"
                    else:
                        dep_expression = escape_sql_percent(base_metrics[dep_name].expression)
                    # Reemplazar el nombre de la métrica por su expresión
                    expression = expression.replace(dep_name, dep_expression)
            
            escaped_expr = escape_sql_percent(expression)
            if self.config.group_by:
                # Si hay agrupación y la expresión no es ya una agregación, envolver en SUM
                if not any(func in expression.upper() for func in ['SUM', 'COUNT', 'AVG', 'MAX', 'MIN']):
                    select_parts.append(f"SUM({escaped_expr}) AS `{metric_name}`")
                else:
                    select_parts.append(f"{escaped_expr} AS `{metric_name}`")
            else:
                select_parts.append(f"{escaped_expr} AS `{metric_name}`")
        
        select_clause = "SELECT " + ", ".join(select_parts)
        
        # Construir FROM (ya tenemos table_name y base_alias calculados arriba)
        from_clause = f"FROM {table_name} {base_alias}"
        
        # Construir JOINs si existen
        joins_clause = ""
        if self.config.joins:
            for join_def in self.config.joins:
                join_type = join_def.get("type", "LEFT").upper()
                join_table_raw = join_def.get("table", "")
                
                # Parsear join_table para extraer nombre de tabla y alias si ya existe
                join_table_clean, join_alias_from_string = self._parse_table_alias(join_table_raw)
                
                # Obtener alias del campo "alias" o del string, o generar uno
                join_alias = join_def.get("alias", "")
                if not join_alias:
                    if join_alias_from_string:
                        join_alias = join_alias_from_string
                    else:
                        # Generar alias si no existe
                        words = join_table_clean.split('_')
                        if len(words) > 1:
                            join_alias = ''.join(w[0] for w in words if w)[:3].lower()
                        else:
                            join_alias = join_table_clean[:2].lower()
                
                # Construir nombre de tabla con alias (usar tabla limpia, no la raw)
                table_with_alias = f"{join_table_clean} {join_alias}"
                
                # Soporte para formato estructurado de ON (lista) o string simple (compatibilidad)
                join_on = join_def.get("on", "")
                if isinstance(join_on, list):
                    # Formato estructurado: [{"left": "...", "op": "=", "right": "..."}, ...]
                    on_conditions = []
                    for condition in join_on:
                        if isinstance(condition, dict):
                            left = condition.get("left", "")
                            op = condition.get("op", "=")
                            right = condition.get("right", "")
                            if left and right:
                                # Normalizar alias en left y right para usar alias correctos
                                normalized_left = self._normalize_alias_in_expression(left, alias_to_table, base_alias)
                                normalized_right = self._normalize_alias_in_expression(right, alias_to_table, join_alias)
                                on_conditions.append(f"{normalized_left} {op} {normalized_right}")
                    join_on_str = " AND ".join(on_conditions) if on_conditions else ""
                else:
                    # Formato string simple (compatibilidad) - normalizar alias
                    join_on_str = str(join_on) if join_on else ""
                    if join_on_str:
                        # Normalizar alias en el string ON
                        join_on_str = self._normalize_aliases_in_on_string(join_on_str, alias_to_table, base_alias, join_alias)
                
                if table_with_alias and join_on_str:
                    joins_clause += f" {join_type} JOIN {table_with_alias} ON {join_on_str}"
                
                # Agregar join_alias al mapa para siguientes JOINs (usar tabla limpia)
                alias_to_table[join_alias] = join_table_clean
        
        # Construir WHERE
        where_conditions = []
        params = []
        
        # Aplicar filtros fijos primero (si existen en options.fixed_filters)
        # IMPORTANTE: Normalizar alias en filtros fijos también
        fixed_filters = self.config.options.get("fixed_filters", [])
        for fixed_filter in fixed_filters:
            if isinstance(fixed_filter, str):
                # Normalizar alias en el filtro fijo usando regex
                import re
                pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b'
                def replace_alias(match):
                    alias_part = match.group(1)
                    column_part = match.group(2)
                    # Si el alias está en el mapa, usar el correcto
                    if alias_part.lower() in [k.lower() for k in alias_to_table.keys()]:
                        for correct_alias in alias_to_table.keys():
                            if correct_alias.lower() == alias_part.lower():
                                return f"{correct_alias}.{column_part}"
                    # Si no está en el mapa pero es un alias común alternativo (cc, cu, c, cp), usar base_alias
                    # cp es común para comp_ped, cc/cu para cuentacliente
                    if alias_part.lower() in ['cc', 'cu', 'c', 'cp'] and base_alias:
                        return f"{base_alias}.{column_part}"
                    return match.group(0)
                
                normalized_filter = re.sub(pattern, replace_alias, fixed_filter)
                where_conditions.append(normalized_filter)
            else:
                where_conditions.append(fixed_filter)
        
        # Construir un diccionario con valores finales de filtros
        # (defaults sobrescritos por payload)
        default_filters = self.config.options.get("default_filters", {})
        logger.debug(f"🔍 SqlQueryBuilder - default_filters: {json.dumps(default_filters, default=str)}")
        
        final_filter_values = default_filters.copy()
        # Actualizar con valores del payload, pero solo si tienen valor válido
        # Para listas, considerar válido si no está vacía
        for k, v in filters_dict.items():
            if v is None:
                continue
            # Si es string, debe ser no vacío
            if isinstance(v, str) and v == "":
                continue
            # Si es lista, debe tener al menos un elemento
            if isinstance(v, list) and len(v) == 0:
                continue
            # Si es dict, debe tener al menos una clave
            if isinstance(v, dict) and len(v) == 0:
                continue
            final_filter_values[k] = v
        logger.debug(f"🔍 SqlQueryBuilder - final_filter_values: {json.dumps(final_filter_values, default=str)}")
        
        # Agrupar filtros constantes por campo para combinarlos con OR/IN cuando sea necesario
        constant_filters_by_field = {}
        variable_filters = []
        
        # Helper para escapar % en expresiones SQL (excepto %s que son placeholders)
        def escape_percent_in_sql(expr: str) -> str:
            """
            Escapa % en expresiones SQL para evitar conflictos con placeholders de Python.
            Preserva %s que son placeholders de parámetros.
            """
            if not expr:
                return expr
            # Reemplazar %s temporalmente con un marcador único
            import uuid
            marker = f"__PLACEHOLDER_{uuid.uuid4().hex[:8]}__"
            expr_with_marker = expr.replace('%s', marker)
            # Escapar todos los % restantes
            expr_escaped = expr_with_marker.replace('%', '%%')
            # Restaurar %s
            return expr_escaped.replace(marker, '%s')
        
        for filter_def in self.config.filters:
            # Normalizar el campo del filtro para usar el alias correcto
            normalized_field = normalize_expression(filter_def.field, base_alias)
            
            # Escapar % en expresiones DATE_FORMAT u otras funciones SQL que usen %
            # Esto previene que Python interprete %m, %Y, etc. como placeholders de formato
            normalized_field = escape_percent_in_sql(normalized_field)
            
            # Determinar si el filtro es constante o variable
            if not filter_def.is_variable:
                # Agrupar filtros constantes por campo
                if normalized_field not in constant_filters_by_field:
                    constant_filters_by_field[normalized_field] = []
                constant_filters_by_field[normalized_field].append((filter_def, normalized_field))
            else:
                variable_filters.append((filter_def, normalized_field))
        
        # Aplicar filtros constantes agrupados (combinar con OR/IN si hay múltiples valores para el mismo campo)
        for normalized_field, filter_list in constant_filters_by_field.items():
            # Filtrar solo los que tienen valor
            valid_filters = [(f, field) for f, field in filter_list 
                            if f.constant_value is not None and f.constant_value != ""]
            
            if not valid_filters:
                continue
            
            if len(valid_filters) == 1:
                # Un solo filtro constante, aplicar normalmente
                filter_def, _ = valid_filters[0]
                param_value = filter_def.constant_value
                operator = filter_def.operator.upper()
                
                if operator in ("=", ">=", "<=", ">", "<", "!=", "<>"):
                    where_conditions.append(f"{normalized_field} {filter_def.operator} %s")
                    params.append(param_value)
                    logger.debug(f"🔍 SqlQueryBuilder - Filtro constante único {filter_def.name}: {normalized_field} {filter_def.operator} {param_value}")
                elif operator == "LIKE":
                    where_conditions.append(f"{normalized_field} LIKE %s")
                    params.append(param_value)
                    logger.debug(f"🔍 SqlQueryBuilder - Filtro constante LIKE {filter_def.name}: {normalized_field} LIKE {param_value}")
                else:
                    logger.warning(f"Operador no soportado para filtro constante: {operator}")
            else:
                # Múltiples filtros constantes para el mismo campo, combinarlos con OR o IN
                # Si todos usan el operador =, usar IN
                all_equals = all(f.operator.upper() == "=" for f, _ in valid_filters)
                if all_equals:
                    # Usar IN para múltiples valores iguales
                    values = [f.constant_value for f, _ in valid_filters]
                    placeholders = ",".join(["%s"] * len(values))
                    where_conditions.append(f"{normalized_field} IN ({placeholders})")
                    params.extend(values)
                    logger.debug(f"🔍 SqlQueryBuilder - Filtros constantes combinados (IN): {normalized_field} IN ({placeholders}) con valores: {values}")
                else:
                    # Si hay diferentes operadores, usar OR
                    or_conditions = []
                    for filter_def, _ in valid_filters:
                        param_value = filter_def.constant_value
                        operator = filter_def.operator.upper()
                        if operator in ("=", ">=", "<=", ">", "<", "!=", "<>"):
                            or_conditions.append(f"{normalized_field} {filter_def.operator} %s")
                            params.append(param_value)
                        elif operator == "LIKE":
                            or_conditions.append(f"{normalized_field} LIKE %s")
                            params.append(param_value)
                    if or_conditions:
                        where_conditions.append("(" + " OR ".join(or_conditions) + ")")
                        logger.debug(f"🔍 SqlQueryBuilder - Filtros constantes combinados (OR): {len(or_conditions)} condiciones para {normalized_field}")
        
        # Aplicar filtros variables
        for filter_def, normalized_field in variable_filters:
            # Filtro variable: obtener valor del payload
            # Asegurar que param sea un string (no una lista) para usarlo como clave
            param_key = filter_def.param
            if isinstance(param_key, list):
                # Si param es una lista, usar el primer elemento o saltar este filtro
                if len(param_key) > 0:
                    param_key = str(param_key[0])
                else:
                    logger.warning(f"🔍 SqlQueryBuilder - Filtro {filter_def.name} tiene param como lista vacía, omitiendo")
                    continue
            elif not isinstance(param_key, str):
                param_key = str(param_key)
            
            # Manejar filtros BETWEEN con parámetros separados por comas (ej: "fecha_inicio, fecha_fin")
            if filter_def.operator.upper() == "BETWEEN" and ',' in param_key:
                # Si el param contiene comas, buscar los parámetros individuales
                param_parts = [p.strip() for p in param_key.split(',') if p.strip()]
                if len(param_parts) == 2:
                    # Buscar ambos parámetros en el payload
                    value1 = final_filter_values.get(param_parts[0])
                    value2 = final_filter_values.get(param_parts[1])
                    # Si ambos valores existen, construir la lista
                    if value1 is not None and value2 is not None:
                        if isinstance(value1, str) and value1 != "" and isinstance(value2, str) and value2 != "":
                            param_value = [value1, value2]
                        else:
                            param_value = None
                    else:
                        param_value = None
                    logger.debug(f"🔍 SqlQueryBuilder - Filtro BETWEEN {filter_def.name} (params={param_parts}): valor1={value1}, valor2={value2}, resultado={param_value}")
                else:
                    logger.warning(f"🔍 SqlQueryBuilder - Filtro BETWEEN {filter_def.name} tiene param con formato inválido: '{param_key}'. Se esperan exactamente 2 parámetros separados por coma.")
                    param_value = None
            else:
                # Para otros operadores, buscar el parámetro directamente
                param_value = final_filter_values.get(param_key)
            
            logger.debug(f"🔍 SqlQueryBuilder - Filtro variable {filter_def.name} (param={filter_def.param}): valor={param_value}, tipo={type(param_value).__name__}, operador={filter_def.operator}")
            
            # Verificar si el valor es válido (solo para filtros variables)
            if param_value is None:
                logger.debug(f"🔍 SqlQueryBuilder - Omitiendo filtro variable {filter_def.name} (valor None)")
                continue
            if isinstance(param_value, str) and param_value == "":
                logger.debug(f"🔍 SqlQueryBuilder - Omitiendo filtro variable {filter_def.name} (string vacío)")
                continue
            if isinstance(param_value, list) and len(param_value) == 0:
                logger.debug(f"🔍 SqlQueryBuilder - Omitiendo filtro variable {filter_def.name} (lista vacía)")
                continue
            
            # Manejar diferentes operadores para filtros variables
            
            # Manejar diferentes operadores
            if filter_def.operator.upper() == "IN":
                # Para IN, esperamos una lista
                if isinstance(param_value, list) and param_value:
                    # Convertir valores a enteros si el campo es numérico (id_pv, CodSucursal, etc.)
                    # Esto es necesario porque los valores pueden llegar como strings desde el frontend
                    converted_values = []
                    for val in param_value:
                        try:
                            # Intentar convertir a int si es posible
                            if isinstance(val, str) and val.isdigit():
                                converted_values.append(int(val))
                            else:
                                converted_values.append(val)
                        except (ValueError, AttributeError):
                            converted_values.append(val)
                    
                    placeholders = ",".join(["%s"] * len(converted_values))
                    where_conditions.append(f"{normalized_field} IN ({placeholders})")
                    params.extend(converted_values)
                    logger.debug(f"🔍 SqlQueryBuilder - Aplicando filtro IN: {normalized_field} IN ({placeholders}) con valores: {converted_values}")
                elif isinstance(param_value, str) and param_value:
                    # Si es string, tratarlo como lista de un elemento
                    # Intentar convertir a int si es posible
                    try:
                        if param_value.isdigit():
                            param_value = int(param_value)
                    except (ValueError, AttributeError):
                        pass
                    where_conditions.append(f"{normalized_field} = %s")
                    params.append(param_value)
                    logger.debug(f"🔍 SqlQueryBuilder - Aplicando filtro IN (string único): {normalized_field} = %s con valor: {param_value}")
            elif filter_def.operator.upper() == "BETWEEN":
                # Para BETWEEN, esperamos una tupla o lista de 2 elementos
                # MySQL 5.7 compatible: campo BETWEEN valor1 AND valor2
                if isinstance(param_value, (list, tuple)) and len(param_value) == 2:
                    where_conditions.append(f"{normalized_field} BETWEEN %s AND %s")
                    params.extend(param_value)
                elif isinstance(param_value, str) and param_value:
                    # Si viene como string con comas, convertir a lista
                    # Formato esperado: "valor1, valor2"
                    values = [v.strip() for v in param_value.split(',') if v.strip()]
                    if len(values) == 2:
                        where_conditions.append(f"{normalized_field} BETWEEN %s AND %s")
                        params.extend(values)
                    else:
                        logger.warning(f"Filtro BETWEEN '{filter_def.name}' requiere exactamente 2 valores separados por coma. Valor recibido: '{param_value}'")
            elif filter_def.operator.upper() in ("=", ">=", "<=", ">", "<", "!=", "<>"):
                where_conditions.append(f"{normalized_field} {filter_def.operator} %s")
                params.append(param_value)
            elif filter_def.operator.upper() == "LIKE":
                where_conditions.append(f"{normalized_field} LIKE %s")
                params.append(param_value)
            else:
                logger.warning(f"Operador no soportado: {filter_def.operator}, omitiendo filtro {filter_def.name}")
        
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)
        
        # Construir GROUP BY
        group_by_clause = ""
        if self.config.group_by:
            group_by_expressions = []
            for dim_name in self.config.group_by:
                if dim_name in self.config.dimensions:
                    # Normalizar también las expresiones de GROUP BY para corregir alias (cl. -> c.)
                    normalized_group_expr = normalize_expression(self.config.dimensions[dim_name].expression, base_alias)
                    escaped_expr = escape_sql_percent(normalized_group_expr)
                    group_by_expressions.append(escaped_expr)
                else:
                    # Si no está en dimensiones, usar el nombre directamente
                    group_by_expressions.append(dim_name)
            group_by_clause = "GROUP BY " + ", ".join(group_by_expressions)
        
        # Construir ORDER BY
        order_by_clause = ""
        if self.config.order_by:
            order_by_expressions = []
            for order_field in self.config.order_by:
                if not isinstance(order_field, str):
                    continue
                # Soportar dimensiones con espacios: "Nombre de cliente ASC".
                parts = order_field.strip().split()
                if not parts:
                    continue
                direction = "ASC"
                # Si el último token es ASC/DESC, usarlo como dirección
                last = parts[-1].upper()
                if last in ("ASC", "DESC") and len(parts) > 1:
                    direction = last
                    field_name = " ".join(parts[:-1])
                else:
                    field_name = order_field.strip()
                if field_name in self.config.dimensions:
                    # Normalizar expresión para corregir alias (cl. -> c., etc.)
                    normalized_expr = normalize_expression(self.config.dimensions[field_name].expression, base_alias)
                    escaped_expr = escape_sql_percent(normalized_expr)
                    order_by_expressions.append(f"{escaped_expr} {direction}")
                else:
                    # Si no está en dimensiones, usar el alias limpio (debe coincidir con el SELECT)
                    clean_field_name = clean_alias(field_name)
                    order_by_expressions.append(f"{clean_field_name} {direction}")
            order_by_clause = "ORDER BY " + ", ".join(order_by_expressions)
        elif self.config.group_by:
            # Por defecto, ordenar por la primera dimensión
            first_dim = self.config.group_by[0]
            if first_dim in self.config.dimensions:
                escaped_expr = escape_sql_percent(self.config.dimensions[first_dim].expression)
                order_by_clause = f"ORDER BY {escaped_expr} ASC"
        
        # Construir SQL completo
        sql_parts = [select_clause, from_clause]
        if joins_clause:
            sql_parts.append(joins_clause.strip())
        if where_clause:
            sql_parts.append(where_clause)
        if group_by_clause:
            sql_parts.append(group_by_clause)
        if order_by_clause:
            sql_parts.append(order_by_clause)
        
        sql = " ".join(sql_parts)
        
        logger.debug(f"SQL generado: {sql}")
        logger.debug(f"Parámetros: {params}")
        
        return sql, params
    
    def _parse_table_alias(self, table_spec: str) -> Tuple[str, Optional[str]]:
        """
        Parsea una especificación de tabla que puede incluir alias.
        
        Ejemplos:
            "cuentacliente" -> ("cuentacliente", None)
            "cuentacliente cc" -> ("cuentacliente", "cc")
            "cuentacliente AS cc" -> ("cuentacliente", "cc")
        
        Args:
            table_spec: Especificación de tabla
            
        Returns:
            Tupla (nombre_tabla, alias)
        """
        table_spec = table_spec.strip()
        
        # Buscar "AS" o espacio como separador
        if ' AS ' in table_spec.upper():
            parts = re.split(r'\s+AS\s+', table_spec, flags=re.IGNORECASE)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        elif ' ' in table_spec:
            parts = table_spec.split(None, 1)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
        
        return table_spec, None
    
    def _normalize_alias_in_expression(self, expr: str, alias_to_table: Dict[str, str], default_alias: str) -> str:
        """
        Normaliza un alias en una expresión SQL.
        
        Si la expresión tiene formato "alias.campo", verifica que el alias exista en alias_to_table.
        Si no existe, intenta encontrar el alias correcto o usa default_alias.
        """
        if not expr or '.' not in expr:
            return expr
        
        # IMPORTANTE: Si es una expresión CASE o compleja, no procesar
        # Verificar esto ANTES de hacer split, porque split puede romper expresiones CASE
        expr_upper = expr.upper().strip()
        if (expr_upper.startswith('CASE') or 
            ' CASE ' in expr_upper or 
            expr_upper.startswith('CASE ') or
            any(op in expr_upper for op in [' WHEN ', ' THEN ', ' ELSE ', ' END'])):
            return expr
        
        # Solo procesar expresiones simples con formato "alias.campo"
        # Si la expresión contiene múltiples puntos o estructuras complejas, no procesar
        if expr.count('.') > 1:
            # Puede ser una expresión compleja con múltiples referencias a tablas
            return expr
        
        parts = expr.split('.', 1)
        if len(parts) != 2:
            return expr
        
        alias_part = parts[0].strip().lower()
        field_part = parts[1].strip()
        
        # Si el alias está en el mapa (case-insensitive), está correcto
        alias_lower_map = {k.lower(): k for k in alias_to_table.keys()}
        if alias_part in alias_lower_map:
            correct_alias = alias_lower_map[alias_part]
            return f"{correct_alias}.{field_part}"
        
        # Buscar alias correcto por similitud
        # Si el alias no está en el mapa, puede ser un alias incorrecto
        # Intentar encontrar el alias correcto buscando por tabla
        for correct_alias, table_name in alias_to_table.items():
            correct_alias_lower = correct_alias.lower()
            # Si el alias incorrecto parece ser una variación del correcto, usar el correcto
            # Ejemplo: "cl" -> "c" (ambos empiezan con 'c')
            if (alias_part.startswith(correct_alias_lower[0]) or 
                correct_alias_lower.startswith(alias_part[0]) or
                len(alias_part) == len(correct_alias_lower) and alias_part[0] == correct_alias_lower[0]):
                return f"{correct_alias}.{field_part}"
        
        # Si no se encuentra, usar default_alias
        return f"{default_alias}.{field_part}"
    
    def _normalize_aliases_in_on_string(self, on_string: str, alias_to_table: Dict[str, str], base_alias: str, join_alias: str) -> str:
        """
        Normaliza alias en un string de condición ON.
        
        Reemplaza alias incorrectos por los correctos del mapa alias_to_table.
        """
        import re
        
        # Patrón para encontrar "alias.campo"
        pattern = r'\b([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z_][a-zA-Z0-9_]*)\b'
        
        # Crear mapa case-insensitive
        alias_lower_map = {k.lower(): k for k in alias_to_table.keys()}
        
        def replace_alias(match):
            alias_part = match.group(1)
            alias_part_lower = alias_part.lower()
            field_part = match.group(2)
            
            # Si el alias está en el mapa (case-insensitive), está correcto
            if alias_part_lower in alias_lower_map:
                correct_alias = alias_lower_map[alias_part_lower]
                return f"{correct_alias}.{field_part}"
            
            # Buscar alias correcto por similitud
            for correct_alias, table_name in alias_to_table.items():
                correct_alias_lower = correct_alias.lower()
                # Si el alias incorrecto parece ser una variación del correcto, usar el correcto
                if (alias_part_lower.startswith(correct_alias_lower[0]) or 
                    correct_alias_lower.startswith(alias_part_lower[0]) or
                    (len(alias_part_lower) == len(correct_alias_lower) and alias_part_lower[0] == correct_alias_lower[0])):
                    return f"{correct_alias}.{field_part}"
            
            # Si no se encuentra y parece ser de la tabla base, usar base_alias
            # Si parece ser del join, usar join_alias
            # Por defecto, asumir que es de la tabla base
            return f"{base_alias}.{field_part}"
        
        return re.sub(pattern, replace_alias, on_string)


class ReportExecutionEngine:
    """
    Motor de ejecución de reportes declarativos.
    
    Ejecuta reportes basados en configuración JSON, generando SQL dinámicamente
    y utilizando el sistema de caché y connection pool existente.
    """
    
    def __init__(self, connection_pool, cache_backend=None):
        """
        Inicializa el motor de ejecución.
        
        Args:
            connection_pool: Instancia de MySQLConnectionPool
            cache_backend: Backend de caché (opcional, usa el default si None)
        """
        self.connection_pool = connection_pool
        self.cache_backend = cache_backend
    
    def _parse_config(self, config_dict: Dict[str, Any]) -> ReportConfig:
        """
        Parsea un diccionario de configuración a ReportConfig.
        
        Args:
            config_dict: Diccionario con la configuración del reporte
            
        Returns:
            Instancia de ReportConfig
            
        Raises:
            ValueError: Si la configuración es inválida
        """
        if config_dict.get("version") != "declarative-v1":
            raise ValueError(f"Versión de configuración no soportada: {config_dict.get('version')}")
        
        # Función auxiliar para limpiar paréntesis extra en expresiones SQL
        def clean_expression(expr: str) -> str:
            """Limpia paréntesis extra al final de expresiones SQL."""
            if not expr or not isinstance(expr, str):
                return expr
            expr = expr.strip()
            # Contar paréntesis de apertura y cierre
            open_count = expr.count('(')
            close_count = expr.count(')')
            # Si hay más paréntesis de cierre que de apertura, remover los extra del final
            if close_count > open_count:
                # Remover solo los paréntesis de cierre extra del final
                extra_closes = close_count - open_count
                # Remover espacios al final primero
                expr = expr.rstrip()
                # Remover los paréntesis extra del final
                for _ in range(extra_closes):
                    if expr.endswith(')'):
                        expr = expr[:-1].rstrip()
            return expr
        
        # Parsear métricas
        metrics = {}
        # Asegurar que options existe para guardar formatos
        if 'options' not in config_dict:
            config_dict['options'] = {}
        if 'custom_metrics_format' not in config_dict['options']:
            config_dict['options']['custom_metrics_format'] = {}
        
        for name, metric_data in config_dict.get("metrics", {}).items():
            # Logging para debug: ver qué llega desde la configuración
            if isinstance(metric_data, dict):
                original_expr = metric_data.get("expression", "")
                logger.debug(f"🔍 Parseando métrica {name}: expresión original desde dict = '{original_expr}'")
            elif isinstance(metric_data, MetricDefinition):
                original_expr = metric_data.expression
                logger.debug(f"🔍 Parseando métrica {name}: expresión original desde MetricDefinition = '{original_expr}'")
            else:
                original_expr = str(metric_data)
                logger.debug(f"🔍 Parseando métrica {name}: expresión original desde string = '{original_expr}'")
            
            # Extraer formato si existe
            format_type = None
            decimals = None
            if isinstance(metric_data, dict):
                format_type = metric_data.get('format_type')
                decimals = metric_data.get('decimals')
            
            # Si metric_data ya es un MetricDefinition, limpiar su expresión
            if isinstance(metric_data, MetricDefinition):
                cleaned = clean_expression(metric_data.expression)
                logger.debug(f"🔍 Parseando métrica {name}: expresión limpiada = '{cleaned}'")
                metric_data.expression = cleaned
                metrics[name] = metric_data
            elif isinstance(metric_data, dict):
                expression = clean_expression(metric_data.get("expression", ""))
                logger.debug(f"🔍 Parseando métrica {name}: expresión limpiada = '{expression}'")
                metrics[name] = MetricDefinition(
                    name=name,
                    expression=expression,
                    depends_on=metric_data.get("depends_on", [])
                )
                # Guardar formato si existe
                if format_type is not None:
                    config_dict['options']['custom_metrics_format'][name] = {
                        'format_type': format_type,
                        'decimals': decimals if decimals is not None else 2
                    }
            else:
                # Si es string, limpiarlo y usarlo como expresión
                expression = clean_expression(str(metric_data))
                logger.debug(f"🔍 Parseando métrica {name}: expresión limpiada = '{expression}'")
                metrics[name] = MetricDefinition(
                    name=name,
                    expression=expression,
                    depends_on=[]
                )
        
        # Parsear dimensiones
        dimensions = {}
        # Asegurar que options existe para guardar formatos de dimensiones numéricas
        if 'options' not in config_dict:
            config_dict['options'] = {}
        if 'custom_dimensions_format' not in config_dict['options']:
            config_dict['options']['custom_dimensions_format'] = {}
        
        for name, dim_data in config_dict.get("dimensions", {}).items():
            # Extraer formato si existe
            format_type = None
            decimals = None
            if isinstance(dim_data, dict):
                format_type = dim_data.get('format_type')
                decimals = dim_data.get('decimals')
                dimensions[name] = DimensionDefinition(
                    name=name,
                    expression=dim_data.get("expression", "")
                )
                # Guardar formato si existe (incluso si es None, para mantener consistencia)
                if format_type is not None:
                    config_dict['options']['custom_dimensions_format'][name] = {
                        'format_type': format_type,
                        'decimals': decimals if decimals is not None else 2
                    }
                    logger.debug(f"Dimension '{name}': formato guardado - tipo: {format_type}, decimales: {decimals if decimals is not None else 2}")
            else:
                # Si es string directo, usarlo como expresión
                dimensions[name] = DimensionDefinition(
                    name=name,
                    expression=dim_data
                )
        
        # Parsear filtros
        filters = []
        for filter_data in config_dict.get("filters", []):
            # Asegurar que param sea siempre un string (no una lista)
            param_value = filter_data.get("param", "")
            if isinstance(param_value, list):
                # Si param es una lista, usar el primer elemento o convertir a string
                param_value = param_value[0] if param_value else ""
            elif not isinstance(param_value, str):
                # Si no es string ni lista, convertir a string
                param_value = str(param_value) if param_value else ""
            
            # Determinar si es variable o constante (por defecto, variable para compatibilidad)
            is_variable = filter_data.get("is_variable")
            if is_variable is None:
                # Si no está definido, asumir que es variable (compatibilidad hacia atrás)
                is_variable = True
            
            filters.append(FilterDefinition(
                name=filter_data.get("name", ""),
                field=filter_data.get("field", ""),
                operator=filter_data.get("operator", "="),
                param=param_value if is_variable else "",  # Solo requerido para variables
                is_variable=is_variable,
                constant_value=filter_data.get("constant_value", None) if not is_variable else None
            ))
        
        # Parsear JOINs opcionales
        joins = config_dict.get("joins", None)
        
        return ReportConfig(
            version=config_dict.get("version", "declarative-v1"),
            datasource=config_dict.get("datasource", ""),
            metrics=metrics,
            dimensions=dimensions,
            filters=filters,
            group_by=config_dict.get("group_by", []),
            order_by=config_dict.get("order_by"),
            notes=config_dict.get("notes"),
            options=config_dict.get("options", {}),
            joins=joins
        )
    
    def _calculate_ttl(self, filters: Dict[str, Any]) -> int:
        """
        Calcula TTL para el caché según el rango de fechas del payload.
        
        Reutiliza la estrategia existente:
        - Datos recientes (últimos 7 días): 60s
        - Datos del mes (8-30 días): 300s
        - Datos históricos (>30 días): 900s
        
        Args:
            filters: Diccionario con filtros del payload
            
        Returns:
            TTL en segundos
        """
        fecha_fin = filters.get("fecha_fin") or filters.get("fecha_hasta")
        if fecha_fin:
            try:
                fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
                dias_desde_fin = (date.today() - fecha_fin_obj).days
                
                if dias_desde_fin <= 7:
                    return 60  # 1 minuto
                elif dias_desde_fin <= 30:
                    return 300  # 5 minutos
                else:
                    return 900  # 15 minutos
            except (ValueError, TypeError):
                pass
        
        # Default: 15 minutos
        return 900
    
    def _calculate_totals(self, data: List[Dict[str, Any]], metrics: Dict[str, MetricDefinition]) -> Dict[str, float]:
        """
        Calcula totales sumando cada métrica numérica sobre todos los registros.
        
        Args:
            data: Lista de diccionarios con los resultados
            metrics: Diccionario de métricas definidas
            
        Returns:
            Diccionario con totales por métrica
        """
        totals = {}
        
        # Inicializar totales para todas las métricas
        for metric_name in metrics.keys():
            totals[metric_name] = 0.0
        
        # Sumar valores de cada métrica
        for row in data:
            for metric_name in metrics.keys():
                value = row.get(metric_name, 0)
                # Convertir Decimal a float si es necesario
                if isinstance(value, Decimal):
                    value = float(value)
                elif value is None:
                    value = 0.0
                else:
                    try:
                        value = float(value)
                    except (ValueError, TypeError):
                        value = 0.0
                
                totals[metric_name] += value
        
        return totals
    
    def _normalize_date_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliza filtros de fecha (dia_actual, mes_actual, año_actual) a fecha_inicio/fecha_fin.
        
        Args:
            filters: Diccionario de filtros
            
        Returns:
            Diccionario de filtros normalizado
        """
        from calendar import monthrange
        
        normalized = filters.copy()
        
        # Si ya hay fechas manuales establecidas, NO normalizar (respetar las fechas del usuario)
        has_manual_dates = normalized.get("fecha_inicio") and normalized.get("fecha_fin")
        
        if not has_manual_dates:
            # Si está marcado "día en curso"
            if normalized.get("dia_actual", False):
                today = date.today()
                normalized["fecha_inicio"] = today.strftime("%Y-%m-%d")
                normalized["fecha_fin"] = today.strftime("%Y-%m-%d")
                # Eliminar flags de período para evitar confusión
                normalized.pop("dia_actual", None)
            # Si está marcado "año en curso"
            elif normalized.get("año_actual", False):
                today = date.today()
                normalized["fecha_inicio"] = date(today.year, 1, 1).strftime("%Y-%m-%d")
                normalized["fecha_fin"] = date(today.year, 12, 31).strftime("%Y-%m-%d")
                # Eliminar flags de período para evitar confusión
                normalized.pop("año_actual", None)
            # Si está marcado "mes en curso"
            elif normalized.get("mes_actual", False):
                today = date.today()
                normalized["fecha_inicio"] = date(today.year, today.month, 1).strftime("%Y-%m-%d")
                last_day = monthrange(today.year, today.month)[1]
                normalized["fecha_fin"] = date(today.year, today.month, last_day).strftime("%Y-%m-%d")
                # Eliminar flags de período para evitar confusión
                normalized.pop("mes_actual", None)
            # Si hay periodo_tipo pero no los flags, procesarlo también
            elif normalized.get("periodo_tipo"):
                periodo_tipo = normalized.get("periodo_tipo")
                if periodo_tipo == "dia_actual":
                    today = date.today()
                    normalized["fecha_inicio"] = today.strftime("%Y-%m-%d")
                    normalized["fecha_fin"] = today.strftime("%Y-%m-%d")
                elif periodo_tipo == "mes_actual":
                    today = date.today()
                    normalized["fecha_inicio"] = date(today.year, today.month, 1).strftime("%Y-%m-%d")
                    last_day = monthrange(today.year, today.month)[1]
                    normalized["fecha_fin"] = date(today.year, today.month, last_day).strftime("%Y-%m-%d")
                elif periodo_tipo == "año_actual":
                    today = date.today()
                    normalized["fecha_inicio"] = date(today.year, 1, 1).strftime("%Y-%m-%d")
                    normalized["fecha_fin"] = date(today.year, 12, 31).strftime("%Y-%m-%d")
                # Para "personalizado", mantener las fechas que vengan en el payload (si existen)
        
        # Limpiar flags de período y periodo_tipo del diccionario final para que no afecten el hash
        normalized.pop("dia_actual", None)
        normalized.pop("mes_actual", None)
        normalized.pop("año_actual", None)
        normalized.pop("periodo_tipo", None)
        
        return normalized
    
    def _get_base_empresa(self, payload: Dict[str, Any], user: Any) -> Optional[str]:
        """
        Obtiene la base de datos de la empresa desde el payload o usuario.
        
        Args:
            payload: Payload del request
            user: Usuario actual
            
        Returns:
            Nombre de la base de datos o None
        """
        filters = payload.get("filters", {})
        base_empresa = filters.get("base_empresa")
        
        if not base_empresa and hasattr(user, 'base_empresa'):
            base_empresa = user.base_empresa
        
        if not base_empresa:
            base_empresa = getattr(settings, 'DEFAULT_BASE_EMPRESA', None)
        
        return base_empresa
    
    def run_from_config(self, report: ReportDefinition, config: ReportConfig, payload: Dict[str, Any], user: Any = None, bypass_cache: bool = False) -> QueryResult:
        """
        Ejecuta un reporte usando una configuración temporal (para preview).
        
        Args:
            report: Instancia de ReportDefinition
            config: Instancia de ReportConfig (puede ser diferente a report.config)
            payload: Payload con filtros del request
            user: Usuario que ejecuta el reporte (opcional)
            bypass_cache: Si True, no usa caché
            
        Returns:
            QueryResult con los datos del reporte
        """
        from .query_runner import QueryResult
        
        started_at = timezone.now()
        
        try:
            # Obtener base_empresa
            base_empresa = self._get_base_empresa(payload, user)
            if not base_empresa:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se pudo determinar la base de datos de la empresa."],
                )
            
            # Normalizar filtros de fecha ANTES de calcular hash para consistencia del caché
            filters = payload.get("filters", {})
            normalized_filters = self._normalize_date_filters(filters)
            normalized_payload = payload.copy()
            normalized_payload["filters"] = normalized_filters
            
            # Construir clave de caché con filtros normalizados (solo si no se bypass)
            sorted_normalized_filters = json.dumps(normalized_filters, sort_keys=True, default=str)
            payload_hash = hashlib.md5(sorted_normalized_filters.encode()).hexdigest()
            
            tenant_id = None
            if user and hasattr(user, 'id'):
                tenant_id = user.id
            
            # Intentar obtener del caché solo si está habilitado y no se bypass
            if not bypass_cache and getattr(settings, 'REPORTS_CACHE_ENABLED', False):
                cached_result = get_cached_report(tenant_id, report.slug, payload_hash)
                if cached_result:
                    logger.info(f"✅ Cache HIT para {report.slug} (preview)")
                    return cached_result
            logger.info(f"❌ Cache MISS, bypass o cache desactivado para {report.slug} (preview), ejecutando consulta...")
            
            # Construir SQL usando el config temporal
            builder = SqlQueryBuilder(config)
            sql, params = builder.build(normalized_payload)
            
            # Ejecutar consulta
            with self.connection_pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                
                try:
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                except Exception as sql_error:
                    logger.error(f"❌ Error SQL ejecutando consulta preview: {sql_error}")
                    logger.error(f"SQL: {sql}")
                    logger.error(f"Params: {params}")
                    raise
            
            # Obtener nombres de columnas
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Convertir resultados a formato de diccionario
            data = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                # Convertir Decimal a float para JSON
                for key, value in row_dict.items():
                    if isinstance(value, Decimal):
                        row_dict[key] = float(value)
                    elif value is None:
                        row_dict[key] = 0.0 if key in config.metrics else None
                data.append(row_dict)
            
            # Calcular totales
            totals = self._calculate_totals(data, config.metrics)
            
            # Construir meta
            meta = {
                "slug": report.slug,
                "name": report.name,
                "category": report.category,
                "version": report.version,
                "datasource": config.datasource,
                "applied_filters": filters,
                "tz": "America/Argentina/Buenos_Aires",
                "preview": True,  # Marcar como preview
            }
            
            # Construir notes
            notes = config.notes or []
            if normalized_filters.get("fecha_inicio") and normalized_filters.get("fecha_fin"):
                fecha_inicio = normalized_filters.get("fecha_inicio")
                fecha_fin = normalized_filters.get("fecha_fin")
                try:
                    fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                    fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
                    notes.append(f"Período: {fecha_inicio_obj.strftime('%d/%m/%Y')} a {fecha_fin_obj.strftime('%d/%m/%Y')}")
                except (ValueError, TypeError):
                    pass
            notes.append(f"Total registros: {len(data)}")
            notes.append("Modo preview - cambios no guardados")
            
            # Crear QueryResult
            result = QueryResult(
                meta=meta,
                data=data,
                totals=totals,
                notes=notes
            )
            
            # Guardar en caché para preview solo si está habilitado y no se bypass
            if not bypass_cache and getattr(settings, 'REPORTS_CACHE_ENABLED', False):
                ttl = 10  # 10 segundos para preview
                set_cached_report(tenant_id, report.slug, payload_hash, result, ttl=ttl)
                logger.info(f"💾 Resultado preview cacheado con TTL: {ttl}s")
            
            return result
            
        except Exception as e:
            logger.error(f"Error ejecutando preview para {report.slug}: {e}", exc_info=True)
            raise
    
    def run(self, report: ReportDefinition, payload: Dict[str, Any], user: Any = None):
        """
        Ejecuta un reporte declarativo.
        
        Args:
            report: Instancia de ReportDefinition con config declarativa
            payload: Payload con filtros del request
            user: Usuario que ejecuta el reporte (opcional)
            
        Returns:
            QueryResult con los datos del reporte
            
        Raises:
            ValueError: Si la configuración es inválida
        """
        # Importación diferida para evitar circular imports
        from .query_runner import QueryResult
        
        started_at = timezone.now()
        
        try:
            # Validar que el reporte tenga configuración declarativa
            if not report.config or report.config.get("version") != "declarative-v1":
                raise ValueError(f"Reporte {report.slug} no tiene configuración declarativa válida")
            
            # Parsear configuración
            config = self._parse_config(report.config)
            
            # Obtener base_empresa
            base_empresa = self._get_base_empresa(payload, user)
            if not base_empresa:
                return QueryResult(
                    meta={
                        "slug": report.slug,
                        "name": report.name,
                        "category": report.category,
                        "version": report.version,
                    },
                    data=[],
                    totals={},
                    notes=["No se pudo determinar la base de datos de la empresa."],
                )
            
            # Normalizar filtros de fecha ANTES de calcular hash para consistencia del caché
            filters = payload.get("filters", {})
            logger.info(f"🔍 Filtros recibidos en ReportExecutionEngine: {json.dumps(filters, default=str, indent=2)}")
            logger.info(f"🔍 Tipo de filters: {type(filters).__name__}")
            if "punto_venta" in filters:
                logger.info(f"🔍 punto_venta en filters: {filters.get('punto_venta')}, tipo: {type(filters.get('punto_venta')).__name__}")
            if "sucursales" in filters:
                logger.info(f"🔍 sucursales en filters: {filters.get('sucursales')}, tipo: {type(filters.get('sucursales')).__name__}")
            
            normalized_filters = self._normalize_date_filters(filters)
            logger.info(f"🔍 Filtros normalizados: {json.dumps(normalized_filters, default=str, indent=2)}")
            
            normalized_payload = payload.copy()
            normalized_payload["filters"] = normalized_filters
            
            # Construir clave de caché con filtros normalizados
            sorted_normalized_filters = json.dumps(normalized_filters, sort_keys=True, default=str)
            payload_hash = hashlib.md5(sorted_normalized_filters.encode()).hexdigest()
            logger.info(f"🔍 Hash del payload (normalizado): {payload_hash[:16]}...")
            
            tenant_id = None
            if user and hasattr(user, 'id'):
                tenant_id = user.id
            
            # Intentar obtener del caché (solo si está habilitado)
            if getattr(settings, 'REPORTS_CACHE_ENABLED', False):
                cached_result = get_cached_report(tenant_id, report.slug, payload_hash)
                if cached_result:
                    logger.info(f"✅ Cache HIT para {report.slug} (declarativo)")
                    return cached_result
            logger.info(f"❌ Cache MISS o cache desactivado para {report.slug} (declarativo), ejecutando consulta...")
            
            # Construir SQL
            builder = SqlQueryBuilder(config)
            sql, params = builder.build(normalized_payload)
            logger.info(f"🔍 SQL generado: {sql[:200]}...")
            logger.info(f"🔍 Parámetros SQL: {params}")
            
            # Ejecutar consulta
            with self.connection_pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                
                try:
                    cursor.execute(sql, params)
                    rows = cursor.fetchall()
                except Exception as sql_error:
                    logger.error(f"❌ Error SQL ejecutando consulta declarativa: {sql_error}")
                    logger.error(f"SQL: {sql}")
                    logger.error(f"Params: {params}")
                    raise
            
            # Obtener nombres de columnas
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Convertir resultados a formato de diccionario
            data = []
            for row in rows:
                row_dict = dict(zip(columns, row))
                # Convertir Decimal a float para JSON
                for key, value in row_dict.items():
                    if isinstance(value, Decimal):
                        row_dict[key] = float(value)
                    elif value is None:
                        row_dict[key] = 0.0 if key in config.metrics else None
                data.append(row_dict)
            
            # Calcular totales
            totals = self._calculate_totals(data, config.metrics)
            
            # Construir meta
            meta = {
                "slug": report.slug,
                "name": report.name,
                "category": report.category,
                "version": report.version,
                "datasource": config.datasource,
                "applied_filters": filters,
                "tz": "America/Argentina/Buenos_Aires",
            }
            
            # Construir notes
            notes = config.notes or []
            if normalized_filters.get("fecha_inicio") and normalized_filters.get("fecha_fin"):
                fecha_inicio = normalized_filters.get("fecha_inicio")
                fecha_fin = normalized_filters.get("fecha_fin")
                try:
                    fecha_inicio_obj = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
                    fecha_fin_obj = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
                    notes.append(f"Período: {fecha_inicio_obj.strftime('%d/%m/%Y')} a {fecha_fin_obj.strftime('%d/%m/%Y')}")
                except (ValueError, TypeError):
                    pass
            notes.append(f"Total registros: {len(data)}")
            
            # Crear QueryResult
            result = QueryResult(
                meta=meta,
                data=data,
                totals=totals,
                notes=notes
            )
            
            # Guardar en caché con hash de filtros normalizados (solo si está habilitado)
            if getattr(settings, 'REPORTS_CACHE_ENABLED', False):
                ttl = self._calculate_ttl(normalized_filters)
                set_cached_report(tenant_id, report.slug, payload_hash, result, ttl=ttl)
                logger.info(f"💾 Resultado cacheado para {report.slug} (declarativo) con TTL de {ttl}s")
            
            # Registrar log de ejecución
            duration = (timezone.now() - started_at).total_seconds() * 1000
            from core.models import UsuarioExtendido
            executed_by_user = None
            if user and isinstance(user, UsuarioExtendido) and getattr(user, "is_authenticated", False):
                executed_by_user = user
            
            ReportExecutionLog.objects.create(
                report=report,
                executed_by=executed_by_user,
                status="success",
                filters_snapshot=filters,
                duration_ms=int(duration),
                notes=f"Consulta ejecutada exitosamente (declarativo). {len(data)} registros obtenidos.",
            )
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error ejecutando reporte declarativo {report.slug}: {e}", exc_info=True)
            
            # Registrar log de error
            duration = (timezone.now() - started_at).total_seconds() * 1000
            from core.models import UsuarioExtendido
            executed_by_user = None
            if user and isinstance(user, UsuarioExtendido) and getattr(user, "is_authenticated", False):
                executed_by_user = user
            
            ReportExecutionLog.objects.create(
                report=report,
                executed_by=executed_by_user,
                status="error",
                filters_snapshot=payload.get("filters", {}),
                duration_ms=int(duration),
                notes=f"Error: {str(e)}",
            )
            
            # Retornar resultado de error
            return QueryResult(
                meta={
                    "slug": report.slug,
                    "name": report.name,
                    "category": report.category,
                    "version": report.version,
                },
                data=[],
                totals={},
                notes=[f"Error ejecutando reporte: {str(e)}"],
            )

