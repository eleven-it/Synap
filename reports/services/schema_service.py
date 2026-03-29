"""
Servicio para generar schemas de reportes declarativos.

Este módulo expone la estructura de reportes (métricas, dimensiones, widgets)
en un formato que el frontend puede usar para construir widgets automáticamente.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Dict, List, Optional, Literal, Any, Tuple
import logging
import re

from ..models import ReportDefinition, ReportWidget
from .execution_engine import ReportConfig, MetricDefinition, DimensionDefinition

logger = logging.getLogger(__name__)


@dataclass
class MetricSchema:
    """Schema de una métrica para el frontend."""
    name: str
    label: str
    expression: str
    data_type: Literal["number", "currency", "percentage", "integer"]
    role: Optional[Literal["value", "aux"]] = "value"  # value = métrica principal, aux = de apoyo
    format: Optional[str] = None  # ej: "currency:ARS", "percent:2", "number:0"
    show_in_kpi: bool = True  # Si se muestra en las tarjetas KPI del resumen


@dataclass
class DimensionSchema:
    """Schema de una dimensión para el frontend."""
    name: str
    label: str
    expression: str
    data_type: Literal["date", "datetime", "string", "category", "integer", "number"]
    role: Optional[Literal["time", "category", "series"]] = None
    format: Optional[str] = None  # ej: "currency:ARS:2", "percent:2", "number:0"


@dataclass
class DefaultWidgetSchema:
    """Schema de un widget por defecto generado automáticamente."""
    id: str
    kind: Literal["bar", "line", "area", "pie", "table", "kpi"]
    title: str
    description: Optional[str] = None
    x_dimension: Optional[str] = None  # nombre de dimensión
    y_metrics: List[str] = field(default_factory=list)  # nombres de métricas
    series_dimension: Optional[str] = None  # para stacked / multi-series
    options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportSchema:
    """Schema completo de un reporte para el frontend."""
    slug: str
    name: str
    category: str
    is_declarative: bool
    metrics: List[MetricSchema]
    dimensions: List[DimensionSchema]
    default_widgets: List[DefaultWidgetSchema]
    options: Dict[str, Any] = field(default_factory=dict)


_PEDIDOS_PENDIENTES_OCULTAR_DIMENSIONES = frozenset({"tipo_comprobante", "estado"})


class ReportSchemaService:
    """Servicio que construye schemas de reportes para el frontend."""
    
    def __init__(self):
        pass

    def _pedidos_pendientes_sin_columnas_tipo_y_estado(
        self,
        slug: str,
        dimensions: List[DimensionSchema],
        widgets: List[DefaultWidgetSchema],
    ) -> Tuple[List[DimensionSchema], List[DefaultWidgetSchema]]:
        """
        Pedidos pendientes: no mostrar TipoComprobante ni Estado (redundantes; el listado ya filtra PED y estados de preparación).
        """
        if slug != "pedidos-pendientes":
            return dimensions, widgets
        new_dims = [d for d in dimensions if d.name not in _PEDIDOS_PENDIENTES_OCULTAR_DIMENSIONES]
        new_widgets: List[DefaultWidgetSchema] = []
        for w in widgets:
            if w.kind != "table":
                new_widgets.append(w)
                continue
            opts = dict(w.options) if w.options else {}
            lc = dict(opts.get("legacy_config") or {})
            rows = lc.get("rows")
            if isinstance(rows, list):
                lc["rows"] = [r for r in rows if r not in _PEDIDOS_PENDIENTES_OCULTAR_DIMENSIONES]
                opts["legacy_config"] = lc
            # El Builder puede guardar table_dimensions explícitas: el motor de tabla las respeta
            # y no aplica exclusiones por slug; hay que alinearlas aquí.
            td = opts.get("table_dimensions")
            if isinstance(td, list):
                opts["table_dimensions"] = [
                    x for x in td if x not in _PEDIDOS_PENDIENTES_OCULTAR_DIMENSIONES
                ]
            new_widgets.append(replace(w, options=opts))
        return new_dims, new_widgets

    def _pedidos_pendientes_sin_agrupacion_inicial(
        self, slug: str, widgets: List[DefaultWidgetSchema]
    ) -> List[DefaultWidgetSchema]:
        """
        Pedidos pendientes: no activar agrupación al cargar (evita chips precargados al actualizar).
        Se conserva grouping.fields tal como lo guardó el Builder: define qué dimensiones puede
        elegir el usuario en "Agrupar por" en el dashboard (lista blanca).
        """
        if slug != "pedidos-pendientes":
            return widgets
        out: List[DefaultWidgetSchema] = []
        for w in widgets:
            if w.kind != "table":
                out.append(w)
                continue
            opts = dict(w.options) if w.options else {}
            prev = opts.get("grouping")
            if isinstance(prev, dict):
                opts["grouping"] = {**prev, "enabled": False}
            else:
                opts["grouping"] = {
                    "enabled": False,
                    "fields": [],
                    "collapsed_by_default": True,
                    "show_totals": True,
                    "total_columns": [],
                }
            out.append(replace(w, options=opts))
        return out
    
    def _infer_metric_type(self, metric_name: str, expression: str) -> Literal["number", "currency", "percentage", "integer"]:
        """Infiere el tipo de dato de una métrica basándose en su nombre y expresión."""
        name_lower = metric_name.lower()
        expr_upper = expression.upper().strip() if expression else ""
        
        # Enteros (conteos) - verificar primero en la expresión SQL
        if "COUNT" in expr_upper:
            return "integer"
        
        # Enteros (conteos) - verificar en el nombre
        if any(keyword in name_lower for keyword in ["count", "cantidad", "unidades", "items", "conteo", "pedidos"]):
            return "integer"
        
        # Porcentajes
        if "porcentaje" in name_lower or "_pct" in name_lower or "%" in name_lower or "rate" in name_lower:
            return "percentage"
        
        # Moneda/Importes
        if any(keyword in name_lower for keyword in ["importe", "total", "ventas", "saldo", "monto", "precio", "costo", "ingreso", "egreso"]):
            return "currency"
        
        # Default: número
        return "number"
    
    def _infer_dimension_type(self, dim_name: str, expression: str) -> Literal["date", "datetime", "string", "category", "integer", "number"]:
        """Infiere el tipo de dato de una dimensión basándose en su nombre y expresión."""
        name_lower = dim_name.lower()
        expr_upper = expression.upper()
        
        # Fechas
        if "DATE" in expr_upper or "DATE_FORMAT" in expr_upper or "fecha" in name_lower or "date" in name_lower:
            if "TIME" in expr_upper or "datetime" in name_lower:
                return "datetime"
            return "date"
        
        # Enteros
        if "id_" in name_lower or name_lower.endswith("_id") or "CAST" in expr_upper:
            return "integer"
        
        # Números (DECIMAL, FLOAT, etc. en la expresión o nombre del campo)
        # Verificar si la expresión contiene tipos numéricos comunes
        if any(num_type in expr_upper for num_type in ["DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL", "MONEY"]):
            return "number"
        
        # Categorías (strings con valores limitados)
        if any(keyword in name_lower for keyword in ["tipo", "estado", "categoria", "status", "type"]):
            return "category"
        
        # Default: string
        return "string"
    
    def _infer_dimension_role(self, dim_name: str, expression: str, data_type: str) -> Optional[Literal["time", "category", "series"]]:
        """Infiere el rol de una dimensión."""
        name_lower = dim_name.lower()
        expr_upper = expression.upper()
        
        # Time: fechas/meses/años
        if data_type in ("date", "datetime") or "mes" in name_lower or "año" in name_lower or "year" in name_lower or "month" in name_lower:
            return "time"
        
        # Category: valores categóricos
        if data_type == "category" or any(keyword in name_lower for keyword in ["sucursal", "punto_venta", "categoria", "tipo"]):
            return "category"
        
        # Series: para gráficos multi-series
        if any(keyword in name_lower for keyword in ["serie", "series", "grupo"]):
            return "series"
        
        return None
    
    def _generate_metric_format(self, metric: MetricSchema) -> Optional[str]:
        """Genera el formato de visualización para una métrica."""
        if metric.data_type == "currency":
            return "currency:ARS"
        elif metric.data_type == "percentage":
            return "percent:2"
        elif metric.data_type == "integer":
            return "number:0"
        elif metric.data_type == "number":
            return "number:2"
        return None
    
    def _get_metric_custom_format(self, report: ReportDefinition, name: str, report_config) -> Optional[Dict[str, Any]]:
        """Obtiene el formato personalizado de una métrica desde options o desde la configuración original."""
        # Primero intentar desde options.custom_metrics_format
        custom_format = report_config.options.get('custom_metrics_format', {}).get(name)
        if custom_format:
            return custom_format
        
        # Si no está en options, intentar leer format_type directamente de la configuración original
        original_config = report.config or {}
        metric_config = original_config.get('metrics', {}).get(name, {})
        if isinstance(metric_config, dict) and metric_config.get('format_type'):
            return {
                'format_type': metric_config.get('format_type'),
                'decimals': metric_config.get('decimals', 2)
            }
        
        return None
    
    def _build_metric_schema(self, name: str, metric_def: MetricDefinition, custom_format_info: Dict[str, Any] = None, show_in_kpi: bool = True) -> MetricSchema:
        """Construye un MetricSchema desde una MetricDefinition."""
        # Si hay formato personalizado, usarlo; si no, verificar si está en la definición de la métrica
        format_type = None
        decimals = 2
        
        if custom_format_info:
            format_type = custom_format_info.get('format_type')
            decimals = custom_format_info.get('decimals', 2)
        elif hasattr(metric_def, 'format_type') and metric_def.format_type:
            # Si no hay custom_format_info, verificar si format_type está directamente en la métrica
            format_type = metric_def.format_type
            decimals = getattr(metric_def, 'decimals', 2)
        elif isinstance(metric_def, dict):
            # Si metric_def es un diccionario, verificar format_type directamente
            format_type = metric_def.get('format_type')
            decimals = metric_def.get('decimals', 2)
        
        if format_type:
            # Mapear format_type a data_type
            type_mapping = {
                'integer': 'integer',
                'number': 'number',
                'currency': 'currency',
                'percentage': 'percentage'
            }
            data_type = type_mapping.get(format_type, 'number')
            
            # Generar formato según el tipo
            if format_type == 'currency':
                format_str = f"currency:ARS:{decimals}"
            elif format_type == 'percentage':
                format_str = f"percent:{decimals}"
            elif format_type == 'integer':
                format_str = "number:0"
            else:  # number
                format_str = f"number:{decimals}"
        else:
            # Inferir tipo si no hay formato personalizado
            data_type = self._infer_metric_type(name, metric_def.expression)
            format_str = None
        
        # Generar label (capitalizar y reemplazar guiones bajos)
        label = name.replace("_", " ").title()
        
        # Determinar rol (métricas principales vs auxiliares)
        role = "aux" if "aux" in name.lower() or "temp" in name.lower() else "value"
        
        # Crear schema
        schema = MetricSchema(
            name=name,
            label=label,
            expression=metric_def.expression,
            data_type=data_type,
            role=role,
            show_in_kpi=show_in_kpi
        )
        
        # Generar formato (usar el personalizado si existe, si no generar automáticamente)
        if format_str:
            schema.format = format_str
        else:
            schema.format = self._generate_metric_format(schema)
        
        return schema
    
    def _build_dimension_schema(self, name: str, dim_def: DimensionDefinition, custom_format_info: Dict[str, Any] = None) -> DimensionSchema:
        """Construye un DimensionSchema desde una DimensionDefinition."""
        # Inferir tipo
        data_type = self._infer_dimension_type(name, dim_def.expression)
        
        # Si tiene formato personalizado, actualizar data_type y generar formato
        # También verificar si el campo es numérico aunque el tipo inferido sea string
        format_str = None
        if custom_format_info:
            format_type = custom_format_info.get('format_type', 'number')
            decimals = custom_format_info.get('decimals', 2)
            
            # Si el tipo inferido no es numérico pero tiene formato, cambiar a number
            if data_type not in ("integer", "number"):
                # Verificar si la expresión sugiere un campo numérico (DECIMAL, etc.)
                expr_upper = dim_def.expression.upper()
                if any(num_type in expr_upper for num_type in ["DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL", "MONEY"]):
                    data_type = 'number'
            
            # Mapear format_type a data_type y generar formato
            if format_type == 'integer':
                data_type = 'integer'
                format_str = "number:0"
            elif format_type == 'currency':
                data_type = 'number'  # Mantener como number pero con formato currency
                format_str = f"currency:ARS:{decimals}"
            elif format_type == 'percentage':
                data_type = 'number'
                format_str = f"percent:{decimals}"
            else:  # number
                data_type = 'number'
                format_str = f"number:{decimals}"
        
        # Generar label
        label = name.replace("_", " ").title()
        
        # Inferir rol
        role = self._infer_dimension_role(name, dim_def.expression, data_type)
        
        schema = DimensionSchema(
            name=name,
            label=label,
            expression=dim_def.expression,
            data_type=data_type,
            role=role
        )
        
        # Agregar formato si existe
        if format_str:
            schema.format = format_str
        
        return schema
    
    def _generate_default_widgets(self, config: ReportConfig, metrics: List[MetricSchema], dimensions: List[DimensionSchema]) -> List[DefaultWidgetSchema]:
        """
        Genera widgets por defecto basándose en las métricas y dimensiones.
        
        IMPORTANTE: Solo genera widgets para métricas que están explícitamente definidas
        en la configuración del reporte. No genera widgets para métricas que puedan
        haber sido inferidas o agregadas automáticamente.
        """
        widgets = []
        
        # Filtrar métricas: solo usar las que están explícitamente en config.metrics
        # Esto evita generar widgets para métricas que no fueron definidas por el usuario
        explicit_metric_names = set(config.metrics.keys()) if hasattr(config, 'metrics') and config.metrics else set()
        filtered_metrics = [m for m in metrics if m.name in explicit_metric_names]
        
        # Si no hay métricas explícitas, no generar widgets
        if not filtered_metrics:
            logger.debug("No hay métricas explícitas definidas, no se generarán widgets por defecto")
            return widgets
        
        # Encontrar dimensión de tiempo y categoría
        time_dim = next((d for d in dimensions if d.role == "time"), None)
        category_dim = next((d for d in dimensions if d.role == "category"), None)
        first_dim = dimensions[0] if dimensions else None
        
        # Encontrar métricas principales (solo de las filtradas)
        main_metrics = [m for m in filtered_metrics if m.role == "value"]
        if not main_metrics:
            main_metrics = filtered_metrics[:3]  # Tomar las primeras 3 si no hay marcadas como principales
        
        # Widget KPI: totales de métricas principales
        if main_metrics:
            for metric in main_metrics[:4]:  # Máximo 4 KPIs
                widgets.append(DefaultWidgetSchema(
                    id=f"kpi_{metric.name}",
                    kind="kpi",
                    title=metric.label,
                    description=f"Total de {metric.label.lower()}",
                    y_metrics=[metric.name],
                    options={"metric": metric.name}
                ))
        
        # Widget de gráfico: barras o líneas
        if time_dim and main_metrics:
            # Gráfico de barras por tiempo
            widgets.append(DefaultWidgetSchema(
                id="chart_time_series",
                kind="bar",
                title=f"{main_metrics[0].label} por {time_dim.label}",
                description=f"Evolución de {main_metrics[0].label.lower()} en el tiempo",
                x_dimension=time_dim.name,
                y_metrics=[m.name for m in main_metrics[:3]],  # Máximo 3 métricas
                series_dimension=category_dim.name if category_dim else None,
                options={"stacked": bool(category_dim)}
            ))
        elif first_dim and main_metrics:
            # Gráfico de barras por primera dimensión
            widgets.append(DefaultWidgetSchema(
                id="chart_by_dimension",
                kind="bar",
                title=f"{main_metrics[0].label} por {first_dim.label}",
                description=f"Distribución de {main_metrics[0].label.lower()}",
                x_dimension=first_dim.name,
                y_metrics=[m.name for m in main_metrics[:2]],
                options={}
            ))
        
        # NO agregar widget de tabla por defecto - la tabla se muestra mediante
        # el botón "Ver tabla" en los gráficos, no como un widget separado
        
        return widgets
    
    def _convert_report_widgets_to_schema(self, report_widgets: List[ReportWidget], available_dimensions: List['DimensionSchema'] = None, include_table_widgets: bool = False) -> List[DefaultWidgetSchema]:
        """
        Convierte ReportWidget (modelo de DB) a DefaultWidgetSchema.
        
        Args:
            report_widgets: Lista de instancias de ReportWidget
            available_dimensions: Lista de dimensiones disponibles (opcional)
            include_table_widgets: Si True, incluye widgets de tipo "table" (útil para preview)
            
        Returns:
            Lista de DefaultWidgetSchema
        """
        schema_widgets = []
        
        for widget in report_widgets:
            # Filtrar widgets de tipo "table" o "pivot-table" solo si include_table_widgets es False
            # Cuando include_table_widgets es True (preview), incluir widgets de tabla
            if not include_table_widgets and widget.widget_type in ['table', 'pivot-table']:
                logger.debug(f"Omitiendo widget de tabla '{widget.name}' - se muestra mediante botón 'Ver tabla'")
                continue
            # Obtener configuración del widget
            config = widget.configuration or {}
            
            # Mapear widget_type a kind (soporta formatos legacy y nuevos)
            widget_type_map = {
                'kpi': 'kpi',
                'bar': 'bar',
                'line': 'line',
                'area': 'area',
                'pie': 'pie',
                'table': 'table',
                'd3-bar-grouped': 'bar',
                'd3-line': 'line',
                'd3-area': 'area',
                'd3-pie': 'pie',
                'pivot-table': 'table',
            }
            kind = widget_type_map.get(widget.widget_type, 'table')
            
            # Extraer dimensiones y métricas de la configuración
            # Soporta múltiples formatos:
            # 1. Formato nuevo: x_dimension, y_metrics, series_dimension
            # 2. Formato legacy: x_field, y_field, group_field
            # 3. Formato pivot-table: rows, values, columns
            
            x_dimension = config.get('x_dimension') or config.get('x_field')
            y_metrics = config.get('y_metrics', [])
            if not y_metrics:
                # Intentar formato legacy
                y_field = config.get('y_field')
                if y_field:
                    y_metrics = [y_field]
                # Intentar formato pivot-table
                values = config.get('values', [])
                if values:
                    y_metrics = values if isinstance(values, list) else [values]
            
            if not isinstance(y_metrics, list):
                y_metrics = [y_metrics] if y_metrics else []
            
            series_dimension = config.get('series_dimension') or config.get('group_field')
            
            # Mapear campos legacy a nombres reales de dimensiones
            if series_dimension and available_dimensions:
                original_series_dim = series_dimension
                # Si group_field/serie es "sucursal" o "Sucursal", mapear a "nombre_sucursal" si existe
                if str(series_dimension).lower() == "sucursal":
                    sucursal_dim = next((d for d in available_dimensions if 'sucursal' in d.name.lower() and 'nombre' in d.name.lower()), None)
                    if sucursal_dim:
                        series_dimension = sucursal_dim.name
                        logger.debug(f"Mapeado series_dimension 'sucursal' a '{sucursal_dim.name}' en widget {widget.id}")
                # Si group_field es "punto_venta" o "pv", mapear a campo real
                elif series_dimension in ["punto_venta", "pv"]:
                    pv_dim = next((d for d in available_dimensions if 'punto' in d.name.lower() and 'venta' in d.name.lower()), None)
                    if pv_dim:
                        group_field_val = config.get('group_field', series_dimension)
                        series_dimension = pv_dim.name
                        logger.debug(f"Mapeado series_dimension '{group_field_val}' a '{pv_dim.name}' en widget {widget.id}")
            
            # Para pivot-table, usar rows como x_dimension si no hay x_dimension
            if not x_dimension and config.get('rows'):
                rows = config.get('rows', [])
                if rows:
                    x_dimension = rows[0] if isinstance(rows, list) else rows
            
            # Si hay series_dimension y es un gráfico de barras, asegurar que sea apilado
            widget_options = {
                **{k: v for k, v in config.items() if k not in ['x_dimension', 'y_metrics', 'series_dimension', 'x_field', 'y_field', 'group_field', 'rows', 'values', 'columns', 'description']},
                'widget_id': widget.id,
                'order': widget.order,
                'layout': widget.layout or {},
                # Preservar configuración legacy para compatibilidad
                'legacy_config': config
            }
            
            # Incluir columnas personalizadas para tablas (table_dimensions y table_metrics)
            if config.get('table_dimensions'):
                widget_options['table_dimensions'] = config.get('table_dimensions')
            if config.get('table_metrics'):
                widget_options['table_metrics'] = config.get('table_metrics')
            
            # Si hay series_dimension y es un gráfico de barras, usar formato apilado por defecto
            if series_dimension and kind == 'bar' and 'stacked' not in widget_options:
                widget_options['stacked'] = True
                logger.debug(f"Widget {widget.id} tiene series_dimension '{series_dimension}', activando formato apilado")
            
            # Asegurar que y_metrics no esté vacío si hay y_field (formato legacy)
            if not y_metrics and config.get('y_field'):
                y_metrics = [config.get('y_field')]
                logger.debug(f"Widget {widget.id}: mapeado y_field '{config.get('y_field')}' a y_metrics")
            
            # Si el widget tiene campos personalizados activados, usar métricas personalizadas
            use_custom_fields = config.get('use_custom_fields', False)
            if use_custom_fields:
                custom_metrics = config.get('custom_metrics', [])
                if custom_metrics and isinstance(custom_metrics, list):
                    # Usar las métricas personalizadas en lugar de las globales
                    y_metrics = [metric.get('name') for metric in custom_metrics if metric.get('name')]
                    # Guardar las métricas personalizadas en las opciones para referencia
                    widget_options['custom_metrics'] = custom_metrics
                    logger.debug(f"Widget {widget.id} usando {len(y_metrics)} métricas personalizadas: {y_metrics}")
                
                custom_dimensions = config.get('custom_dimensions', [])
                if custom_dimensions and isinstance(custom_dimensions, list):
                    # Guardar las dimensiones personalizadas en las opciones para referencia
                    widget_options['custom_dimensions'] = custom_dimensions
                    # Si hay una dimensión personalizada y no hay x_dimension, usar la primera
                    if not x_dimension and custom_dimensions:
                        x_dimension = custom_dimensions[0].get('name')
                        logger.debug(f"Widget {widget.id} usando dimensión personalizada '{x_dimension}'")
            
            # Crear DefaultWidgetSchema
            schema_widget = DefaultWidgetSchema(
                id=f"widget_{widget.id}",
                kind=kind,
                title=widget.name,
                description=config.get('description', ''),
                x_dimension=x_dimension,
                y_metrics=y_metrics if y_metrics else [],
                series_dimension=series_dimension,
                options=widget_options
            )
            schema_widgets.append(schema_widget)
        
        return schema_widgets
    
    def build_schema(self, report: ReportDefinition) -> ReportSchema:
        """
        Construye el schema de un reporte.
        
        Args:
            report: Instancia de ReportDefinition
            
        Returns:
            ReportSchema con la estructura del reporte
        """
        config = report.config or {}
        is_declarative = config.get("version") == "declarative-v1"
        
        if not is_declarative:
            # Reporte legacy: schema mínimo
            return ReportSchema(
                slug=report.slug,
                name=report.name,
                category=report.category,
                is_declarative=False,
                metrics=[],
                dimensions=[],
                default_widgets=[],
                options={}
            )
        
        # Reporte declarativo: construir schema completo
        try:
            from .execution_engine import ReportExecutionEngine, get_mysql_pool
            
            # Parsear configuración usando el engine (que convierte dicts a MetricDefinition/DimensionDefinition)
            pool = get_mysql_pool()
            engine = ReportExecutionEngine(connection_pool=pool)
            report_config = engine._parse_config(config)
            
            # Recolectar métricas y dimensiones personalizadas de widgets
            manual_widgets = list(report.widgets.all().order_by("order", "id"))
            custom_metrics_to_add = {}
            custom_dimensions_to_add = {}
            
            for widget in manual_widgets:
                widget_config = widget.configuration or {}
                if widget_config.get('use_custom_fields', False):
                    # Agregar métricas personalizadas
                    custom_metrics = widget_config.get('custom_metrics', [])
                    if custom_metrics and isinstance(custom_metrics, list):
                        for metric in custom_metrics:
                            metric_name = metric.get('name')
                            metric_expression = metric.get('expression')
                            if metric_name and metric_expression:
                                # Crear MetricDefinition para la métrica personalizada
                                from .execution_engine import MetricDefinition
                                metric_def = MetricDefinition(
                                    name=metric_name,
                                    expression=metric_expression,
                                    depends_on=[]
                                )
                                # Guardar información de formato personalizada en las opciones del report_config
                                # para que se use al construir el schema
                                if 'custom_metrics_format' not in report_config.options:
                                    report_config.options['custom_metrics_format'] = {}
                                report_config.options['custom_metrics_format'][metric_name] = {
                                    'format_type': metric.get('format_type', 'number'),
                                    'decimals': metric.get('decimals', 2)
                                }
                                custom_metrics_to_add[metric_name] = metric_def
                                format_type = metric.get('format_type', 'number')
                                decimals = metric.get('decimals', 2)
                                logger.debug(f"Agregando métrica personalizada '{metric_name}' con expresión '{metric_expression}' y formato '{format_type}' ({decimals} decimales) del widget '{widget.name}'")
                    
                    # Agregar dimensiones personalizadas
                    custom_dimensions = widget_config.get('custom_dimensions', [])
                    if custom_dimensions and isinstance(custom_dimensions, list):
                        for dimension in custom_dimensions:
                            dim_name = dimension.get('name')
                            dim_expression = dimension.get('expression')
                            if dim_name and dim_expression:
                                # Crear DimensionDefinition para la dimensión personalizada
                                from .execution_engine import DimensionDefinition
                                custom_dimensions_to_add[dim_name] = DimensionDefinition(
                                    name=dim_name,
                                    expression=dim_expression
                                )
                                logger.debug(f"Agregando dimensión personalizada '{dim_name}' con expresión '{dim_expression}' del widget '{widget.name}'")
            
            # Agregar métricas y dimensiones personalizadas al report_config
            custom_metric_names = set()
            if custom_metrics_to_add:
                report_config.metrics.update(custom_metrics_to_add)
                custom_metric_names = set(custom_metrics_to_add.keys())
                logger.info(f"Agregadas {len(custom_metrics_to_add)} métricas personalizadas al schema del reporte: {custom_metric_names}")
            if custom_dimensions_to_add:
                report_config.dimensions.update(custom_dimensions_to_add)
                logger.info(f"Agregadas {len(custom_dimensions_to_add)} dimensiones personalizadas al schema del reporte")
            
            # Guardar lista de métricas personalizadas en las opciones del schema para que el frontend las pueda filtrar
            if custom_metric_names:
                if 'custom_widget_metrics' not in report_config.options:
                    report_config.options['custom_widget_metrics'] = []
                report_config.options['custom_widget_metrics'] = list(custom_metric_names)
            
            # Construir schemas de métricas y dimensiones respetando el orden guardado
            metrics = []
            dimensions = []
            
            # Obtener el orden guardado de los campos visuales
            visual_fields_order = report_config.options.get("visual_fields_order", [])
            
            if visual_fields_order and isinstance(visual_fields_order, list):
                # Usar el orden guardado
                processed_names = set()
                for field_name in visual_fields_order:
                    # Buscar en dimensiones primero
                    if field_name in report_config.dimensions:
                        dim_def = report_config.dimensions[field_name]
                        # Obtener información de formato personalizada si existe
                        custom_format = report_config.options.get('custom_dimensions_format', {}).get(field_name)
                        dimensions.append(self._build_dimension_schema(field_name, dim_def, custom_format))
                        processed_names.add(field_name)
                    # Luego buscar en métricas
                    elif field_name in report_config.metrics:
                        metric_def = report_config.metrics[field_name]
                        # Obtener información de formato personalizada si existe
                        custom_format = self._get_metric_custom_format(report, field_name, report_config)
                        # Leer show_in_kpi del config original (default True para retrocompatibilidad)
                        show_in_kpi = config.get('metrics', {}).get(field_name, {}).get('show_in_kpi', True)
                        metrics.append(self._build_metric_schema(field_name, metric_def, custom_format, show_in_kpi))
                        processed_names.add(field_name)
                
                # Agregar campos que no están en el orden guardado (nuevos campos)
                for name, dim_def in report_config.dimensions.items():
                    if name not in processed_names:
                        # Obtener información de formato personalizada si existe
                        custom_format = report_config.options.get('custom_dimensions_format', {}).get(name)
                        dimensions.append(self._build_dimension_schema(name, dim_def, custom_format))
                for name, metric_def in report_config.metrics.items():
                    if name not in processed_names:
                        # Obtener información de formato personalizada si existe
                        custom_format = self._get_metric_custom_format(report, name, report_config)
                        # Leer show_in_kpi del config original (default True para retrocompatibilidad)
                        show_in_kpi = config.get('metrics', {}).get(name, {}).get('show_in_kpi', True)
                        metrics.append(self._build_metric_schema(name, metric_def, custom_format, show_in_kpi))
            else:
                # Si no hay orden guardado, usar el orden por defecto (dimensiones primero, luego métricas)
                for name, dim_def in report_config.dimensions.items():
                    # Obtener información de formato personalizada si existe
                    custom_format = report_config.options.get('custom_dimensions_format', {}).get(name)
                    dimensions.append(self._build_dimension_schema(name, dim_def, custom_format))
                for name, metric_def in report_config.metrics.items():
                    # Obtener información de formato personalizada si existe
                    custom_format = self._get_metric_custom_format(report, name, report_config)
                    # Leer show_in_kpi del config original (default True para retrocompatibilidad)
                    show_in_kpi = config.get('metrics', {}).get(name, {}).get('show_in_kpi', True)
                    metrics.append(self._build_metric_schema(name, metric_def, custom_format, show_in_kpi))
            
            # IMPORTANTE: Solo generar widgets por defecto si NO hay widgets manuales guardados
            # Si el usuario ya tiene widgets guardados, NO generar nuevos automáticamente
            # (manual_widgets ya fue obtenido arriba para recolectar métricas personalizadas)
            
            if manual_widgets:
                # Si hay widgets manuales, usar esos y NO generar defaults
                logger.info(f"Reporte {report.slug} tiene {len(manual_widgets)} widgets manuales, usando esos en lugar de defaults")
                # Convertir ReportWidget a DefaultWidgetSchema
                # IMPORTANTE: Para el dashboard, incluir widgets de tabla (include_table_widgets=True)
                # porque son parte de la visualización del reporte
                default_widgets = self._convert_report_widgets_to_schema(manual_widgets, available_dimensions=dimensions, include_table_widgets=True)
            else:
                # Solo generar widgets por defecto si NO hay widgets manuales
                default_widgets = self._generate_default_widgets(report_config, metrics, dimensions)

            dimensions, default_widgets = self._pedidos_pendientes_sin_columnas_tipo_y_estado(
                report.slug, dimensions, default_widgets
            )
            default_widgets = self._pedidos_pendientes_sin_agrupacion_inicial(report.slug, default_widgets)

            return ReportSchema(
                slug=report.slug,
                name=report.name,
                category=report.category,
                is_declarative=True,
                metrics=metrics,
                dimensions=dimensions,
                default_widgets=default_widgets,
                options=report_config.options
            )
            
        except Exception as e:
            logger.error(f"Error construyendo schema para {report.slug}: {e}", exc_info=True)
            # Fallback: schema mínimo con error
            return ReportSchema(
                slug=report.slug,
                name=report.name,
                category=report.category,
                is_declarative=True,
                metrics=[],
                dimensions=[],
                default_widgets=[],
                options={"error": str(e)}
            )
    
    def build_schema_from_config(self, report: ReportDefinition, config_dict: Dict[str, Any]) -> ReportSchema:
        """
        Construye un schema desde un diccionario de configuración temporal (para preview).
        
        Args:
            report: Instancia de ReportDefinition
            config_dict: Diccionario con configuración temporal
            
        Returns:
            ReportSchema generado desde el config temporal
        """
        try:
            from .execution_engine import ReportExecutionEngine, get_mysql_pool
            
            # Parsear configuración temporal usando el engine (que convierte dicts a MetricDefinition/DimensionDefinition)
            pool = get_mysql_pool()
            engine = ReportExecutionEngine(connection_pool=pool)
            report_config = engine._parse_config(config_dict)
            
            # IMPORTANTE: Agregar métricas y dimensiones personalizadas de widgets
            # Esto es necesario para que las métricas personalizadas aparezcan en el schema del preview
            manual_widgets = list(report.widgets.all().order_by("order", "id"))
            for widget in manual_widgets:
                widget_config = widget.configuration or {}
                if widget_config.get('use_custom_fields', False):
                    # Agregar métricas personalizadas
                    custom_metrics = widget_config.get('custom_metrics', [])
                    if custom_metrics and isinstance(custom_metrics, list):
                        for metric in custom_metrics:
                            metric_name = metric.get('name')
                            metric_expression = metric.get('expression')
                            if metric_name and metric_expression:
                                # Agregar métrica personalizada al config
                                from .execution_engine import MetricDefinition
                                report_config.metrics[metric_name] = MetricDefinition(
                                    name=metric_name,
                                    expression=metric_expression,
                                    depends_on=[]
                                )
                                # Guardar información de formato personalizada en las opciones del report_config
                                if 'custom_metrics_format' not in report_config.options:
                                    report_config.options['custom_metrics_format'] = {}
                                report_config.options['custom_metrics_format'][metric_name] = {
                                    'format_type': metric.get('format_type', 'number'),
                                    'decimals': metric.get('decimals', 2)
                                }
                                logger.debug(f"Schema preview: Agregando métrica personalizada '{metric_name}' con expresión '{metric_expression}' y formato '{metric.get('format_type', 'number')}' del widget '{widget.name}'")
                    
                    # Agregar dimensiones personalizadas
                    custom_dimensions = widget_config.get('custom_dimensions', [])
                    if custom_dimensions and isinstance(custom_dimensions, list):
                        for dimension in custom_dimensions:
                            dim_name = dimension.get('name')
                            dim_expression = dimension.get('expression')
                            if dim_name and dim_expression:
                                # Agregar dimensión personalizada al config
                                from .execution_engine import DimensionDefinition
                                report_config.dimensions[dim_name] = DimensionDefinition(
                                    name=dim_name,
                                    expression=dim_expression
                                )
                                logger.debug(f"Schema preview: Agregando dimensión personalizada '{dim_name}' con expresión '{dim_expression}' del widget '{widget.name}'")
            
            # Recolectar nombres de métricas personalizadas para filtrarlas en widgets que no las usan
            custom_metric_names = set()
            if manual_widgets:
                for widget in manual_widgets:
                    widget_config = widget.configuration or {}
                    if widget_config.get('use_custom_fields', False):
                        custom_metrics = widget_config.get('custom_metrics', [])
                        if custom_metrics and isinstance(custom_metrics, list):
                            for metric in custom_metrics:
                                metric_name = metric.get('name')
                                if metric_name:
                                    custom_metric_names.add(metric_name)
                
                custom_metrics_count = sum(1 for w in manual_widgets if w.configuration and w.configuration.get('use_custom_fields') and w.configuration.get('custom_metrics'))
                if custom_metrics_count > 0:
                    logger.info(f"Schema preview: Agregadas métricas personalizadas de {custom_metrics_count} widget(s) al schema: {custom_metric_names}")
            
            # Guardar lista de métricas personalizadas en las opciones del schema para que el frontend las pueda filtrar
            if custom_metric_names:
                if 'custom_widget_metrics' not in report_config.options:
                    report_config.options['custom_widget_metrics'] = []
                report_config.options['custom_widget_metrics'] = list(custom_metric_names)
            
            # Construir schemas de métricas y dimensiones respetando el orden guardado
            metrics = []
            dimensions = []
            
            # Obtener el orden guardado de los campos visuales
            visual_fields_order = report_config.options.get("visual_fields_order", [])
            
            if visual_fields_order and isinstance(visual_fields_order, list):
                # Usar el orden guardado
                processed_names = set()
                for field_name in visual_fields_order:
                    # Buscar en dimensiones primero
                    if field_name in report_config.dimensions:
                        dim_def = report_config.dimensions[field_name]
                        # Obtener información de formato personalizada si existe
                        custom_format = report_config.options.get('custom_dimensions_format', {}).get(field_name)
                        dimensions.append(self._build_dimension_schema(field_name, dim_def, custom_format))
                        processed_names.add(field_name)
                    # Luego buscar en métricas
                    elif field_name in report_config.metrics:
                        metric_def = report_config.metrics[field_name]
                        # Obtener información de formato personalizada si existe
                        custom_format = self._get_metric_custom_format(report, field_name, report_config)
                        # Leer show_in_kpi del config original (default True para retrocompatibilidad)
                        show_in_kpi = config_dict.get('metrics', {}).get(field_name, {}).get('show_in_kpi', True)
                        metrics.append(self._build_metric_schema(field_name, metric_def, custom_format, show_in_kpi))
                        processed_names.add(field_name)
                
                # Agregar campos que no están en el orden guardado (nuevos campos)
                for name, dim_def in report_config.dimensions.items():
                    if name not in processed_names:
                        # Obtener información de formato personalizada si existe
                        custom_format = report_config.options.get('custom_dimensions_format', {}).get(name)
                        dimensions.append(self._build_dimension_schema(name, dim_def, custom_format))
                for name, metric_def in report_config.metrics.items():
                    if name not in processed_names:
                        # Obtener información de formato personalizada si existe
                        custom_format = self._get_metric_custom_format(report, name, report_config)
                        # Leer show_in_kpi del config original (default True para retrocompatibilidad)
                        show_in_kpi = config_dict.get('metrics', {}).get(name, {}).get('show_in_kpi', True)
                        metrics.append(self._build_metric_schema(name, metric_def, custom_format, show_in_kpi))
            else:
                # Si no hay orden guardado, usar el orden por defecto (dimensiones primero, luego métricas)
                for name, dim_def in report_config.dimensions.items():
                    # Obtener información de formato personalizada si existe
                    custom_format = report_config.options.get('custom_dimensions_format', {}).get(name)
                    dimensions.append(self._build_dimension_schema(name, dim_def, custom_format))
                for name, metric_def in report_config.metrics.items():
                    # Obtener información de formato personalizada si existe
                    custom_format = self._get_metric_custom_format(report, name, report_config)
                    # Leer show_in_kpi del config original (default True para retrocompatibilidad)
                    show_in_kpi = config_dict.get('metrics', {}).get(name, {}).get('show_in_kpi', True)
                    metrics.append(self._build_metric_schema(name, metric_def, custom_format, show_in_kpi))
            
            # Para preview: incluir widgets guardados del reporte si existen
            # Esto permite que el preview muestre los widgets configurados por el usuario
            manual_widgets = list(report.widgets.all().order_by("order", "id"))
            logger.info(f"Preview para {report.slug}: encontró {len(manual_widgets)} widgets guardados en BD")
            
            if manual_widgets:
                # Si hay widgets manuales guardados, usarlos para el preview
                logger.info(f"Preview para {report.slug}: usando {len(manual_widgets)} widgets guardados")
                try:
                    default_widgets = self._convert_report_widgets_to_schema(manual_widgets, available_dimensions=dimensions, include_table_widgets=True)
                    logger.info(f"Preview para {report.slug}: convertidos {len(default_widgets)} widgets a schema")
                except Exception as e:
                    logger.error(f"Error convirtiendo widgets a schema para {report.slug}: {e}", exc_info=True)
                    default_widgets = []
            else:
                # Si no hay widgets guardados, no generar widgets automáticamente para preview
                # Los widgets solo se generan cuando el usuario explícitamente hace clic en "Usar widgets generados automáticamente"
                logger.info(f"Preview para {report.slug}: no hay widgets guardados, default_widgets = []")
                default_widgets = []

            dimensions, default_widgets = self._pedidos_pendientes_sin_columnas_tipo_y_estado(
                report.slug, dimensions, default_widgets
            )
            default_widgets = self._pedidos_pendientes_sin_agrupacion_inicial(report.slug, default_widgets)

            return ReportSchema(
                slug=report.slug,
                name=report.name,
                category=report.category,
                is_declarative=True,
                metrics=metrics,
                dimensions=dimensions,
                default_widgets=default_widgets,
                options=report_config.options
            )
            
        except Exception as e:
            logger.error(f"Error construyendo schema desde config temporal para {report.slug}: {e}", exc_info=True)
            return ReportSchema(
                slug=report.slug,
                name=report.name,
                category=report.category,
                is_declarative=True,
                metrics=[],
                dimensions=[],
                default_widgets=[],
                options={"error": str(e)}
            )

