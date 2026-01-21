"""
Servicio para serializar, validar y normalizar configuraciones de reportes declarativos.

Este módulo proporciona funciones para trabajar con ReportConfig de forma segura,
validando estructura y normalizando valores por defecto.
"""
from __future__ import annotations

from typing import Dict, List, Tuple, Any, Optional
import logging

from .metric_graph import MetricGraph
from .sql_validator import get_sql_validator

logger = logging.getLogger(__name__)


def serialize_report_config(report) -> Dict[str, Any]:
    """
    Serializa la configuración de un reporte a un diccionario.
    
    Args:
        report: Instancia de ReportDefinition
        
    Returns:
        Diccionario con la configuración serializada
    """
    config = report.config or {}
    
    # Incluir campos básicos del reporte
    result = {
        "is_new": False,
        "name": report.name,
        "slug": report.slug,
        "category": report.category,
        "description": report.description or "",
        "show_in_catalog": report.show_in_catalog,
        "is_visible": report.is_visible,
        "config": config
    }
    
    return result
    
    # Asegurar que tenga version declarative-v1
    if config.get("version") != "declarative-v1":
        config = {
            "version": "declarative-v1",
            "datasource": "",
            "metrics": {},
            "dimensions": {},
            "filters": [],
            "group_by": [],
            "order_by": None,
            "joins": None,
            "notes": None,
            "options": {}
        }
    
    return {
        "is_new": False,
        "slug": report.slug,
        "name": report.name,
        "category": report.category,
        "description": report.description or "",
        "is_visible": report.is_visible,
        "is_declarative": config.get("version") == "declarative-v1",
        "config": config
    }


def validate_report_config(
    config_dict: Dict[str, Any],
    base_empresa: Optional[str] = None,
    validate_sql: bool = True
) -> Tuple[bool, List[str], List[str]]:
    """
    Valida la estructura de una configuración de reporte declarativo.
    
    Args:
        config_dict: Diccionario con la configuración a validar
        base_empresa: Base de datos MySQL para validación SQL (opcional)
        validate_sql: Si True, valida expresiones SQL contra esquema MySQL
        
    Returns:
        Tupla (es_válido, lista_de_errores, lista_de_warnings)
    """
    errors = []
    warnings = []
    
    # Validar version
    version = config_dict.get("version")
    if version != "declarative-v1":
        errors.append(f"Versión debe ser 'declarative-v1', se recibió: {version}")
    
    # Validar datasource
    datasource = config_dict.get("datasource")
    if not datasource or not isinstance(datasource, str) or not datasource.strip():
        errors.append("datasource es requerido y debe ser un string no vacío")
    
    # Validar metrics
    metrics = config_dict.get("metrics", {})
    if not isinstance(metrics, dict):
        errors.append("metrics debe ser un diccionario")
    elif len(metrics) == 0:
        # Convertir a warning: no siempre es necesario tener métricas
        warnings.append("No se han definido métricas. El reporte puede no mostrar datos hasta que se agreguen métricas.")
    else:
        for metric_name, metric_def in metrics.items():
            if not isinstance(metric_def, dict):
                errors.append(f"Métrica '{metric_name}' debe ser un diccionario")
                continue
            
            if "expression" not in metric_def:
                errors.append(f"Métrica '{metric_name}' debe tener 'expression'")
            
            # Validar depends_on si existe
            if "depends_on" in metric_def and not isinstance(metric_def["depends_on"], list):
                errors.append(f"Métrica '{metric_name}': depends_on debe ser una lista")
    
    # Validar dimensions
    dimensions = config_dict.get("dimensions", {})
    if not isinstance(dimensions, dict):
        errors.append("dimensions debe ser un diccionario")
    elif len(dimensions) == 0:
        # Convertir a warning: no siempre es necesario tener dimensiones
        warnings.append("No se han definido agrupaciones. El reporte puede no mostrar datos hasta que se agreguen agrupaciones.")
    else:
        for dim_name, dim_def in dimensions.items():
            if not isinstance(dim_def, dict):
                errors.append(f"Dimensión '{dim_name}' debe ser un diccionario")
                continue
            
            if "expression" not in dim_def:
                errors.append(f"Dimensión '{dim_name}' debe tener 'expression'")
    
    # Validar filters
    filters = config_dict.get("filters", [])
    if not isinstance(filters, list):
        errors.append("filters debe ser una lista")
    else:
        for i, filter_def in enumerate(filters):
            if not isinstance(filter_def, dict):
                errors.append(f"Filtro en índice {i} debe ser un diccionario")
                continue
            
            required_fields = ["name", "field", "operator", "param"]
            for field in required_fields:
                if field not in filter_def:
                    errors.append(f"Filtro en índice {i} debe tener '{field}'")
    
    # Validar group_by
    group_by = config_dict.get("group_by", [])
    if not isinstance(group_by, list):
        errors.append("group_by debe ser una lista")
    else:
        # Verificar que todas las dimensiones referenciadas existan (solo si hay dimensiones definidas)
        if len(dimensions) > 0:
            dimension_names = set(dimensions.keys())
            for dim_name in group_by:
                if dim_name not in dimension_names:
                    errors.append(f"group_by referencia dimensión inexistente: '{dim_name}'")
        elif len(group_by) > 0:
            # Si hay group_by pero no hay dimensiones, es un warning
            warnings.append("Se ha definido group_by pero no hay dimensiones. group_by será ignorado.")
    
    # Validar order_by
    order_by = config_dict.get("order_by")
    if order_by is not None:
        if not isinstance(order_by, list):
            errors.append("order_by debe ser una lista o None")
        else:
            # Validar que las dimensiones referenciadas existan (solo si hay dimensiones definidas)
            if len(dimensions) > 0:
                dimension_names = set(dimensions.keys())
                for order_field in order_by:
                    # Puede ser "dimension ASC", "dimension DESC" o "dimension".
                    # Soportar nombres de dimensiones con espacios.
                    if not isinstance(order_field, str):
                        continue
                    parts = order_field.strip().split()
                    if not parts:
                        continue
                    # Si el último token es ASC/DESC, el nombre de la dimensión es el resto
                    last = parts[-1].upper()
                    if last in ("ASC", "DESC") and len(parts) > 1:
                        field_name = " ".join(parts[:-1])
                    else:
                        field_name = order_field.strip()
                    if field_name not in dimension_names:
                        errors.append(f"order_by referencia dimensión inexistente: '{field_name}'")
            elif len(order_by) > 0:
                # Si hay order_by pero no hay dimensiones, es un warning
                warnings.append("Se ha definido order_by pero no hay dimensiones. order_by será ignorado.")
    
    # Validar joins (opcional)
    joins = config_dict.get("joins")
    if joins is not None:
        if not isinstance(joins, list):
            errors.append("joins debe ser una lista o None")
        else:
            for i, join_def in enumerate(joins):
                if not isinstance(join_def, dict):
                    errors.append(f"Join en índice {i} debe ser un diccionario")
                    continue
                
                required_fields = ["type", "table", "on"]
                for field in required_fields:
                    if field not in join_def:
                        errors.append(f"Join en índice {i} debe tener '{field}'")
    
    # Validar options (opcional)
    options = config_dict.get("options")
    if options is not None and not isinstance(options, dict):
        errors.append("options debe ser un diccionario o None")
    
    # Validar grafo de dependencias de métricas
    try:
        graph = MetricGraph.build_from_config(config_dict)
        is_valid_graph, graph_errors = graph.validate()
        if not is_valid_graph:
            errors.extend(graph_errors)
    except Exception as e:
        logger.warning(f"Error validando grafo de métricas: {e}")
        errors.append(f"Error validando dependencias de métricas: {str(e)}")
    
    # Validar expresiones SQL contra esquema MySQL
    # Si validate_sql está habilitado, siempre validar palabras peligrosas
    # Si además hay base_empresa, validar columnas (errores críticos)
    # Si no hay base_empresa, validar solo palabras peligrosas (errores críticos) y columnas como warnings
    if validate_sql:
        if base_empresa:
            # Validación completa: errores críticos para todo
            sql_errors, sql_warnings = _validate_sql_expressions(config_dict, base_empresa)
            errors.extend(sql_errors)
            warnings.extend(sql_warnings)
        else:
            # Validación parcial: solo palabras peligrosas (errores críticos)
            # Columnas se validan como warnings
            sql_errors, sql_warnings = _validate_sql_expressions(config_dict, None)
            errors.extend(sql_errors)  # Palabras peligrosas siempre son errores
            warnings.extend(sql_warnings)  # Columnas sin base_empresa son warnings
    
    return len(errors) == 0, errors, warnings


def _validate_sql_expressions(
    config_dict: Dict[str, Any],
    base_empresa: Optional[str]
) -> Tuple[List[str], List[str]]:
    """
    Valida expresiones SQL contra el esquema MySQL.
    
    Args:
        config_dict: Configuración del reporte
        base_empresa: Base de datos MySQL (opcional, None si no está disponible)
        
    Returns:
        Tupla (errores, warnings)
    """
    errors = []
    warnings = []
    
    try:
        validator = get_sql_validator()
        datasource = config_dict.get("datasource", "")
        joins = config_dict.get("joins")
        
        # Validar métricas
        metrics = config_dict.get("metrics", {})
        for metric_name, metric_def in metrics.items():
            if not isinstance(metric_def, dict):
                continue
            
            expression = metric_def.get("expression", "")
            if expression:
                is_valid, validation_errors = validator.validate_expression(
                    expression=expression,
                    datasource=datasource,
                    joins=joins,
                    allowed_tables=None,
                    base_empresa=base_empresa
                )
                if not is_valid:
                    # Si hay base_empresa, los errores son críticos
                    # Si no hay base_empresa, son warnings (no podemos validar completamente)
                    error_list = errors if base_empresa else warnings
                    error_list.extend([
                        f"Métrica '{metric_name}': {err}" for err in validation_errors
                    ])
        
        # Validar dimensiones
        dimensions = config_dict.get("dimensions", {})
        for dim_name, dim_def in dimensions.items():
            if not isinstance(dim_def, dict):
                continue
            
            expression = dim_def.get("expression", "")
            if expression:
                is_valid, validation_errors = validator.validate_expression(
                    expression=expression,
                    datasource=datasource,
                    joins=joins,
                    allowed_tables=None,
                    base_empresa=base_empresa
                )
                if not is_valid:
                    # Si hay base_empresa, los errores son críticos
                    # Si no hay base_empresa, son warnings (no podemos validar completamente)
                    error_list = errors if base_empresa else warnings
                    error_list.extend([
                        f"Dimensión '{dim_name}': {err}" for err in validation_errors
                    ])
        
        # Validar filtros
        filters = config_dict.get("filters", [])
        for i, filter_def in enumerate(filters):
            if not isinstance(filter_def, dict):
                continue
            
            field = filter_def.get("field", "")
            if field:
                is_valid, validation_errors = validator.validate_expression(
                    expression=field,
                    datasource=datasource,
                    joins=joins,
                    allowed_tables=None,
                    base_empresa=base_empresa
                )
                if not is_valid:
                    # Si hay base_empresa, los errores son críticos
                    # Si no hay base_empresa, son warnings (no podemos validar completamente)
                    error_list = errors if base_empresa else warnings
                    error_list.extend([
                        f"Filtro '{filter_def.get('name', f'#{i}')}': {err}" 
                        for err in validation_errors
                    ])
        
        # Validar JOINs
        joins = config_dict.get("joins", [])
        if joins:
            errors.extend(_validate_joins(joins, datasource, base_empresa))
        
    except Exception as e:
        logger.warning(f"Error validando SQL contra esquema: {e}")
        warnings.append(f"No se pudo validar completamente contra esquema MySQL: {str(e)}")
    
    return errors, warnings


def _validate_joins(joins: List[Dict[str, Any]], base_table: str, base_empresa: Optional[str] = None) -> List[str]:
    """
    Valida la estructura y coherencia de los JOINs.
    
    Args:
        joins: Lista de definiciones de JOIN
        base_table: Tabla principal del reporte
        base_empresa: Base de datos MySQL (opcional)
        
    Returns:
        Lista de mensajes de error (vacía si todo está bien)
    """
    errors = []
    aliases_used = set()
    tables_in_graph = {base_table.lower()}
    
    # Alias por defecto de la tabla base
    # IMPORTANTE: Usar la misma lógica que execution_engine.py para consistencia
    # execution_engine.py usa: table_name[0].lower() (primera letra)
    base_alias = base_table[0].lower() if base_table else "c"
    if base_alias:
        aliases_used.add(base_alias)
        # También agregar alias alternativos comunes para compatibilidad
        # Si el alias es 'c', también reconocer 'cc', 'cu', 'cp' como variaciones
        if base_alias == 'c':
            # No agregar directamente, pero reconocer en la validación
            pass
    
    for i, join_def in enumerate(joins):
        if not isinstance(join_def, dict):
            errors.append(f"JOIN #{i}: debe ser un objeto/diccionario")
            continue
        
        join_type = join_def.get("type", "LEFT")
        if join_type not in ["LEFT", "INNER", "RIGHT"]:
            errors.append(f"JOIN #{i}: tipo '{join_type}' no válido (debe ser LEFT, INNER o RIGHT)")
        
        table = join_def.get("table", "")
        if not table:
            errors.append(f"JOIN #{i}: falta el campo 'table'")
            continue
        
        # Extraer nombre de tabla (sin alias si viene en formato "tabla alias")
        table_parts = table.split()
        table_name = table_parts[0].lower()
        
        # Validar alias único
        alias = join_def.get("alias", "")
        if not alias:
            # Generar alias por defecto
            words = table_name.split('_')
            if len(words) > 1:
                alias = ''.join(w[0] for w in words if w)[:3].lower()
            else:
                alias = table_name[:2].lower()
        
        if alias in aliases_used:
            errors.append(f"JOIN #{i}: el alias '{alias}' ya está en uso")
        else:
            aliases_used.add(alias)
        
        # Validar que no se duplique la tabla
        if table_name in tables_in_graph:
            errors.append(f"JOIN #{i}: la tabla '{table_name}' ya está en el grafo")
        else:
            tables_in_graph.add(table_name)
        
        # Validar condición ON
        on = join_def.get("on", "")
        if not on:
            errors.append(f"JOIN #{i}: falta la condición 'on'")
        else:
            # Validar que ON referencia alias existentes
            if isinstance(on, str):
                # Formato string: extraer alias mencionados
                import re
                alias_pattern = r'\b([a-z_][a-z0-9_]*)\\.'
                mentioned_aliases = set(re.findall(alias_pattern, on.lower()))
                # Filtrar alias válidos (en uso o alternativos comunes)
                invalid_aliases = []
                for alias in mentioned_aliases:
                    if alias in aliases_used:
                        continue
                    # Si el alias base es 'c', aceptar también 'cc', 'cu', 'cp' como variaciones
                    if base_alias == 'c' and alias in ['cc', 'cu', 'cp']:
                        continue
                    # Si el alias base es 'cp', aceptar también 'c' como variación
                    if base_alias == 'cp' and alias == 'c':
                        continue
                    invalid_aliases.append(alias)
                if invalid_aliases:
                    errors.append(f"JOIN #{i}: la condición ON referencia alias no definidos: {', '.join(invalid_aliases)}")
            elif isinstance(on, list):
                # Formato estructurado: validar cada condición
                for j, condition in enumerate(on):
                    if isinstance(condition, dict):
                        left = condition.get("left", "")
                        right = condition.get("right", "")
                        for side in [left, right]:
                            if '.' in side:
                                alias_part = side.split('.')[0].lower()
                                # Verificar si el alias está en uso o es un alias alternativo válido
                                alias_valid = alias_part in aliases_used
                                # Si el alias base es 'c', aceptar también 'cc', 'cu', 'cp' como variaciones
                                if not alias_valid and base_alias == 'c' and alias_part in ['cc', 'cu', 'cp']:
                                    alias_valid = True
                                # Si el alias base es 'cp', aceptar también 'c' como variación
                                elif not alias_valid and base_alias == 'cp' and alias_part == 'c':
                                    alias_valid = True
                                if not alias_valid:
                                    errors.append(f"JOIN #{i}, condición #{j}: referencia alias '{alias_part}' no definido")
        
        # Detectar ciclos simples (si una tabla intenta conectarse a sí misma)
        # Esto es una validación básica, ciclos más complejos requerirían análisis de grafo
        if table_name == base_table.lower():
            errors.append(f"JOIN #{i}: no se puede conectar la tabla base a sí misma")
    
    return errors


def normalize_report_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza una configuración de reporte, rellenando valores por defecto.
    
    Args:
        config_dict: Diccionario con la configuración a normalizar
        
    Returns:
        Diccionario normalizado con valores por defecto aplicados
    """
    normalized = config_dict.copy()
    
    # Asegurar version
    normalized["version"] = normalized.get("version", "declarative-v1")
    
    # Asegurar datasource
    normalized["datasource"] = normalized.get("datasource", "").strip()
    
    # Asegurar metrics (debe ser dict)
    if not isinstance(normalized.get("metrics"), dict):
        normalized["metrics"] = {}
    
    # Asegurar dimensions (debe ser dict)
    if not isinstance(normalized.get("dimensions"), dict):
        normalized["dimensions"] = {}
    
    # Normalizar métricas: asegurar depends_on
    for metric_name, metric_def in normalized["metrics"].items():
        if not isinstance(metric_def, dict):
            continue
        if "depends_on" not in metric_def:
            metric_def["depends_on"] = []
        elif not isinstance(metric_def["depends_on"], list):
            metric_def["depends_on"] = []
    
    # Asegurar filters (debe ser lista)
    if not isinstance(normalized.get("filters"), list):
        normalized["filters"] = []
    
    # Asegurar group_by (debe ser lista)
    if "group_by" not in normalized or not isinstance(normalized["group_by"], list):
        normalized["group_by"] = []
    
    # Normalizar order_by
    if "order_by" not in normalized or normalized["order_by"] is None:
        # Por defecto, ordenar por primera dimensión si existe
        if normalized["group_by"]:
            first_dim = normalized["group_by"][0]
            normalized["order_by"] = [f"{first_dim} ASC"]
        else:
            normalized["order_by"] = None
    
    # Asegurar joins (opcional, None por defecto)
    if "joins" not in normalized:
        normalized["joins"] = None
    elif normalized["joins"] is not None and not isinstance(normalized["joins"], list):
        normalized["joins"] = None
    
    # Asegurar notes (opcional, None por defecto)
    if "notes" not in normalized:
        normalized["notes"] = None
    elif normalized["notes"] is not None and not isinstance(normalized["notes"], list):
        normalized["notes"] = None
    
    # Asegurar options (debe ser dict)
    if not isinstance(normalized.get("options"), dict):
        normalized["options"] = {}
    
    # Normalizar options: asegurar fixed_filters y default_filters
    if "fixed_filters" not in normalized["options"]:
        normalized["options"]["fixed_filters"] = []
    elif not isinstance(normalized["options"]["fixed_filters"], list):
        normalized["options"]["fixed_filters"] = []
    
    if "default_filters" not in normalized["options"]:
        normalized["options"]["default_filters"] = {}
    elif not isinstance(normalized["options"]["default_filters"], dict):
        normalized["options"]["default_filters"] = {}
    
    return normalized

