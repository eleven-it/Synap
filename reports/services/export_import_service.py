"""
Servicio para exportar e importar reportes, relaciones aprendidas y schema entre instancias de Synap.

Este servicio permite transferir configuraciones entre diferentes instalaciones de Synap,
facilitando la migración de reportes, conocimiento de relaciones y metadata de schema.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from django.db import transaction
from django.core.exceptions import ValidationError

from ..models import ReportDefinition, ReportWidget, LearnedRelationship

logger = logging.getLogger(__name__)


class ExportImportService:
    """Servicio para exportar e importar datos de reportes entre instancias."""
    
    VERSION = "1.0.0"
    
    @classmethod
    def export_report(cls, report: ReportDefinition, include_widgets: bool = True) -> Dict[str, Any]:
        """
        Exporta un reporte a formato JSON.
        
        Args:
            report: Instancia de ReportDefinition a exportar
            include_widgets: Si True, incluye widgets asociados
            
        Returns:
            Diccionario con los datos del reporte exportado
        """
        data = {
            "version": cls.VERSION,
            "export_type": "report",
            "exported_at": datetime.now().isoformat(),
            "report": {
                "slug": report.slug,
                "name": report.name,
                "description": report.description,
                "category": report.category,
                "version": report.version,
                "config": report.config or {},
                "metadata": report.metadata or {},
                "refresh_interval": report.refresh_interval,
                "is_active": report.is_active,
                "is_visible": report.is_visible,
                "show_in_catalog": report.show_in_catalog,
                # No exportar empresa_id, created_by, updated_by (específicos de instancia)
            }
        }
        
        if include_widgets:
            widgets = ReportWidget.objects.filter(report=report).order_by("order")
            data["report"]["widgets"] = [
                {
                    "name": w.name,
                    "widget_type": w.widget_type,
                    "order": w.order,
                    "layout": w.layout or {},
                    "configuration": w.configuration or {},
                }
                for w in widgets
            ]
        
        return data
    
    @classmethod
    def export_reports(cls, reports: List[ReportDefinition], include_widgets: bool = True) -> Dict[str, Any]:
        """
        Exporta múltiples reportes a formato JSON.
        
        Args:
            reports: Lista de instancias de ReportDefinition
            include_widgets: Si True, incluye widgets asociados
            
        Returns:
            Diccionario con los datos de los reportes exportados
        """
        return {
            "version": cls.VERSION,
            "export_type": "reports_batch",
            "exported_at": datetime.now().isoformat(),
            "reports": [
                cls.export_report(report, include_widgets=False)["report"]
                for report in reports
            ],
            "widgets": {} if not include_widgets else {
                report.slug: [
                    {
                        "name": w.name,
                        "widget_type": w.widget_type,
                        "order": w.order,
                        "layout": w.layout or {},
                        "configuration": w.configuration or {},
                    }
                    for w in ReportWidget.objects.filter(report=report).order_by("order")
                ]
                for report in reports
            }
        }
    
    @classmethod
    def export_learned_relationships(
        cls,
        empresa_id: Optional[int] = None,
        include_global: bool = True
    ) -> Dict[str, Any]:
        """
        Exporta relaciones aprendidas.
        
        Args:
            empresa_id: ID de empresa específica (None para todas)
            include_global: Si True, incluye relaciones globales (empresa=None)
            
        Returns:
            Diccionario con las relaciones aprendidas exportadas
        """
        filters = {}
        if empresa_id is not None:
            if include_global:
                from django.db.models import Q
                filters = Q(empresa_id=empresa_id) | Q(empresa_id__isnull=True)
            else:
                filters = {"empresa_id": empresa_id}
        else:
            if not include_global:
                filters = {"empresa_id__isnull": False}
        
        relationships = LearnedRelationship.objects.filter(**filters) if isinstance(filters, dict) else LearnedRelationship.objects.filter(filters)
        
        return {
            "version": cls.VERSION,
            "export_type": "learned_relationships",
            "exported_at": datetime.now().isoformat(),
            "relationships": [
                {
                    "from_table": rel.from_table,
                    "from_column": rel.from_column,
                    "to_table": rel.to_table,
                    "to_column": rel.to_column,
                    "usage_count": rel.usage_count,
                    "success_count": rel.success_count,
                    "confidence": float(rel.confidence),
                    "source": rel.source,
                    "is_blocked": rel.is_blocked,
                    "last_used_at": rel.last_used_at.isoformat() if rel.last_used_at else None,
                    # Campos nuevos de gobernanza y validación
                    "status": getattr(rel, "status", "proposed"),
                    "match_rule_json": getattr(rel, "match_rule_json", {}),
                    "validation_metrics_json": getattr(rel, "validation_metrics_json", {}),
                    "confidence_calculated": float(getattr(rel, "confidence_calculated", 0)) if getattr(rel, "confidence_calculated", None) is not None else None,
                    "confidence_override": float(getattr(rel, "confidence_override", 0)) if getattr(rel, "confidence_override", None) is not None else None,
                    "deprecated_reason": getattr(rel, "deprecated_reason", None),
                    "version": getattr(rel, "version", 1),
                    # No exportar empresa_id (se asignará en la importación)
                }
                for rel in relationships
            ]
        }
    
    @classmethod
    def export_schema_metadata(
        cls,
        base_empresa: str,
        tables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Exporta metadata del schema (tablas, columnas, tipos).
        
        Args:
            base_empresa: Nombre de la base de datos
            tables: Lista de nombres de tablas (None para todas)
            
        Returns:
            Diccionario con metadata del schema
        """
        from .semantic_service import SemanticService
        
        # Obtener todas las tablas si no se especifican
        if tables is None:
            tables = SemanticService.get_available_tables(base_empresa)
        
        schema_data = {
            "version": cls.VERSION,
            "export_type": "schema_metadata",
            "exported_at": datetime.now().isoformat(),
            "base_empresa": base_empresa,
            "tables": {}
        }
        
        for table_name in tables:
            try:
                fields = SemanticService.get_table_fields(base_empresa, table_name)
                schema_data["tables"][table_name] = {
                    "fields": [
                        {
                            "name": f["name"],
                            "data_type": f["data_type"],
                            "nullable": f.get("nullable", False),
                        }
                        for f in fields
                    ]
                }
            except Exception as e:
                logger.warning(f"Error obteniendo campos de tabla {table_name}: {e}")
                continue
        
        return schema_data
    
    @classmethod
    @transaction.atomic
    def import_report(
        cls,
        data: Dict[str, Any],
        empresa_id: Optional[int] = None,
        overwrite: bool = False
    ) -> ReportDefinition:
        """
        Importa un reporte desde formato JSON.
        
        Args:
            data: Diccionario con los datos del reporte (formato export)
            empresa_id: ID de empresa para asignar al reporte (None para global)
            overwrite: Si True, sobrescribe reporte existente con mismo slug
            
        Returns:
            Instancia de ReportDefinition importada
            
        Raises:
            ValidationError: Si los datos son inválidos o el slug ya existe
        """
        if data.get("export_type") != "report":
            raise ValidationError("Tipo de exportación inválido. Se espera 'report'.")
        
        report_data = data.get("report", {})
        if not report_data:
            raise ValidationError("Datos de reporte no encontrados en el archivo de exportación.")
        
        slug = report_data.get("slug")
        if not slug:
            raise ValidationError("Slug del reporte es requerido.")
        
        # Verificar si ya existe
        existing = ReportDefinition.objects.filter(slug=slug, empresa_id=empresa_id).first()
        if existing and not overwrite:
            raise ValidationError(f"Reporte con slug '{slug}' ya existe. Usa overwrite=True para sobrescribir.")
        
        # Crear o actualizar reporte
        report, created = ReportDefinition.objects.update_or_create(
            slug=slug,
            empresa_id=empresa_id,
            defaults={
                "name": report_data.get("name", slug),
                "description": report_data.get("description", ""),
                "category": report_data.get("category", "operational"),
                "version": report_data.get("version", "1.0.0"),
                "config": report_data.get("config", {}),
                "metadata": report_data.get("metadata", {}),
                "refresh_interval": report_data.get("refresh_interval", "daily"),
                "is_active": report_data.get("is_active", True),
                "is_visible": report_data.get("is_visible", True),
                "show_in_catalog": report_data.get("show_in_catalog", True),
            }
        )
        
        # Importar widgets si existen
        widgets_data = report_data.get("widgets", [])
        if widgets_data:
            # Eliminar widgets existentes
            ReportWidget.objects.filter(report=report).delete()
            
            # Crear nuevos widgets
            for widget_data in widgets_data:
                ReportWidget.objects.create(
                    report=report,
                    name=widget_data.get("name", ""),
                    widget_type=widget_data.get("widget_type", "table"),
                    order=widget_data.get("order", 0),
                    layout=widget_data.get("layout", {}),
                    configuration=widget_data.get("configuration", {}),
                )
        
        action = "Creado" if created else "Actualizado"
        logger.info(f"✅ Reporte {action}: {report.name} ({report.slug})")
        
        return report
    
    @classmethod
    @transaction.atomic
    def import_learned_relationships(
        cls,
        data: Dict[str, Any],
        empresa_id: Optional[int] = None,
        merge_strategy: str = "merge"
    ) -> int:
        """
        Importa relaciones aprendidas desde formato JSON.
        
        Args:
            data: Diccionario con las relaciones (formato export)
            empresa_id: ID de empresa para asignar (None para global)
            merge_strategy: "merge" (combinar estadísticas) o "replace" (reemplazar)
            
        Returns:
            Número de relaciones importadas
        """
        if data.get("export_type") != "learned_relationships":
            raise ValidationError("Tipo de exportación inválido. Se espera 'learned_relationships'.")
        
        relationships_data = data.get("relationships", [])
        if not relationships_data:
            return 0
        
        imported_count = 0
        
        for rel_data in relationships_data:
            try:
                rel, created = LearnedRelationship.objects.get_or_create(
                    empresa_id=empresa_id,
                    from_table=rel_data["from_table"],
                    from_column=rel_data["from_column"],
                    to_table=rel_data["to_table"],
                    to_column=rel_data["to_column"],
                    defaults={
                        "usage_count": rel_data.get("usage_count", 0),
                        "success_count": rel_data.get("success_count", 0),
                        "confidence": rel_data.get("confidence", 0.5),
                        "source": rel_data.get("source", "usage"),
                        "is_blocked": rel_data.get("is_blocked", False),
                        # Campos nuevos de gobernanza y validación
                        "status": rel_data.get("status", "proposed"),
                        "match_rule_json": rel_data.get("match_rule_json", {}),
                        "validation_metrics_json": rel_data.get("validation_metrics_json", {}),
                        "confidence_calculated": rel_data.get("confidence_calculated"),
                        "confidence_override": rel_data.get("confidence_override"),
                        "deprecated_reason": rel_data.get("deprecated_reason"),
                        "version": rel_data.get("version", 1),
                    }
                )
                
                if not created:
                    if merge_strategy == "merge":
                        # Combinar estadísticas
                        rel.usage_count += rel_data.get("usage_count", 0)
                        rel.success_count += rel_data.get("success_count", 0)
                        # Usar mayor confianza
                        rel.confidence = max(rel.confidence, rel_data.get("confidence", 0.5))
                    elif merge_strategy == "replace":
                        # Reemplazar completamente
                        rel.usage_count = rel_data.get("usage_count", 0)
                        rel.success_count = rel_data.get("success_count", 0)
                        rel.confidence = rel_data.get("confidence", 0.5)
                    
                    # Actualizar campos de gobernanza si están presentes
                    if "status" in rel_data:
                        rel.status = rel_data["status"]
                    if "match_rule_json" in rel_data:
                        rel.match_rule_json = rel_data["match_rule_json"]
                    if "validation_metrics_json" in rel_data:
                        rel.validation_metrics_json = rel_data["validation_metrics_json"]
                    if "confidence_calculated" in rel_data:
                        rel.confidence_calculated = rel_data["confidence_calculated"]
                    if "confidence_override" in rel_data:
                        rel.confidence_override = rel_data["confidence_override"]
                    if "deprecated_reason" in rel_data:
                        rel.deprecated_reason = rel_data["deprecated_reason"]
                    if "version" in rel_data:
                        rel.version = rel_data["version"]
                    
                    rel.save()
                
                imported_count += 1
            except Exception as e:
                logger.warning(f"Error importando relación: {e}")
                continue
        
        logger.info(f"✅ {imported_count} relaciones aprendidas importadas")
        return imported_count
    
    @classmethod
    def export_all(
        cls,
        empresa_id: Optional[int] = None,
        include_reports: bool = True,
        include_relationships: bool = True,
        include_schema: bool = False,
        base_empresa: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Exporta todo: reportes, relaciones y schema.
        
        Args:
            empresa_id: ID de empresa (None para todas)
            include_reports: Si True, incluye reportes
            include_relationships: Si True, incluye relaciones aprendidas
            include_schema: Si True, incluye metadata de schema
            base_empresa: Base de datos para exportar schema (requerido si include_schema=True)
            
        Returns:
            Diccionario con todos los datos exportados
        """
        result = {
            "version": cls.VERSION,
            "export_type": "full_export",
            "exported_at": datetime.now().isoformat(),
        }
        
        if include_reports:
            from django.db.models import Q
            filters = Q(is_active=True)
            if empresa_id:
                filters &= Q(empresa_id=empresa_id) | Q(empresa_id__isnull=True)
            else:
                filters &= Q(empresa_id__isnull=True)
            
            reports = ReportDefinition.objects.filter(filters)
            reports_export = cls.export_reports(list(reports), include_widgets=True)
            result["reports"] = reports_export.get("reports", [])
            result["widgets"] = reports_export.get("widgets", {})
        
        if include_relationships:
            rels_export = cls.export_learned_relationships(empresa_id=empresa_id, include_global=True)
            result["learned_relationships"] = rels_export.get("relationships", [])
        
        if include_schema:
            if not base_empresa:
                raise ValueError("base_empresa es requerido cuando include_schema=True")
            schema_export = cls.export_schema_metadata(base_empresa)
            result["schema_metadata"] = schema_export.get("tables", {})
        
        return result

