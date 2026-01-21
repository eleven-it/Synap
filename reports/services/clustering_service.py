"""
Servicio de clustering para agrupar tablas en dominios/clusters lógicos.
Implementa clustering por prefijos y conectividad.
"""
import logging
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict
from django.utils import timezone

from .semantic_service import SemanticService
from ..models import LearnedRelationship, TableClusterAssignment

logger = logging.getLogger(__name__)


class ClusteringService:
    """Servicio para agrupar tablas en clusters lógicos."""
    
    @classmethod
    def get_overview(cls, base_empresa: str, empresa_id: Optional[int] = None, filters: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Obtiene la vista overview con clusters y estadísticas.
        
        Args:
            base_empresa: Base de datos MySQL
            empresa_id: ID de empresa (para filtrar learned relationships)
            filters: Filtros opcionales (no usado aún en overview)
            
        Returns:
            Dict con clusters, stats y metadata
        """
        try:
            # Obtener todas las tablas
            datasources = SemanticService.list_datasources(base_empresa=base_empresa)
            table_names = {ds.name for ds in datasources}
            
            # Obtener todas las FK
            fk_edges = SemanticService.get_all_foreign_keys(base_empresa)
            
            # Obtener learned relationships activas
            learned_edges = cls._get_active_learned_relationships(empresa_id)
            
            # Clustering: primero intentar usar clusters personalizados, sino usar heurísticas
            clusters = cls._get_custom_clusters(base_empresa, empresa_id, table_names, fk_edges, learned_edges)
            if not clusters:
                # Si no hay clusters personalizados, usar heurísticas
                clusters = cls._cluster_by_prefix(table_names, fk_edges, learned_edges)
            
            # Calcular estadísticas
            stats = cls._calculate_stats(table_names, fk_edges, learned_edges)
            
            return {
                "view": "overview",
                "base_empresa": base_empresa,
                "clusters": clusters,
                "stats": stats,
                "timestamp": timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo overview para {base_empresa}: {e}", exc_info=True)
            raise
    
    @classmethod
    def get_cluster_graph(cls, base_empresa: str, empresa_id: Optional[int], cluster_id: str, filters: Dict) -> Dict[str, Any]:
        """
        Obtiene el grafo de un cluster específico.
        
        Args:
            base_empresa: Base de datos MySQL
            empresa_id: ID de empresa
            cluster_id: ID del cluster
            filters: Filtros de visualización
            
        Returns:
            Dict con nodes, edges y external_links del cluster
        """
        try:
            # Obtener todas las tablas
            datasources = SemanticService.list_datasources(base_empresa=base_empresa)
            all_tables = {ds.name: ds for ds in datasources}
            
            # Obtener clusters
            table_names = {ds.name for ds in datasources}
            fk_edges = SemanticService.get_all_foreign_keys(base_empresa)
            learned_edges = cls._get_active_learned_relationships(empresa_id)
            # Clustering: primero intentar usar clusters personalizados, sino usar heurísticas
            clusters = cls._get_custom_clusters(base_empresa, empresa_id, table_names, fk_edges, learned_edges)
            if not clusters:
                # Si no hay clusters personalizados, usar heurísticas
                clusters = cls._cluster_by_prefix(table_names, fk_edges, learned_edges)
            
            # Encontrar el cluster solicitado
            cluster = next((c for c in clusters if c["id"] == cluster_id), None)
            if not cluster:
                raise ValueError(f"Cluster '{cluster_id}' no encontrado")
            
            cluster_tables = set(cluster["table_names"])
            
            # Filtrar edges: solo internas del cluster
            internal_fk_edges = [
                edge for edge in fk_edges
                if edge["tabla_origen"] in cluster_tables and edge["tabla_destino"] in cluster_tables
            ]
            
            internal_learned_edges = [
                edge for edge in learned_edges
                if edge["from_table"] in cluster_tables and edge["to_table"] in cluster_tables
            ]
            
            # Construir nodes del cluster
            nodes = []
            for table_name in cluster_tables:
                ds = all_tables.get(table_name)
                nodes.append({
                    "id": table_name,
                    "label": table_name,
                    "title": ds.description if ds else f"Tabla {table_name}",
                    "group": "table",
                    "shape": "box",
                    "cluster_id": cluster_id,
                    "color": {
                        "background": "#3b82f6",
                        "border": "#1e40af",
                        "highlight": {
                            "background": "#60a5fa",
                            "border": "#3b82f6"
                        }
                    }
                })
            
            # Construir edges internas
            edges = []
            for fk in internal_fk_edges:
                edges.append(cls._build_fk_edge(fk))
            
            for learned in internal_learned_edges:
                edges.append(cls._build_learned_edge(learned))
            
            # Calcular conexiones externas
            external_links = cls._calculate_external_links(
                cluster_tables, fk_edges, learned_edges, clusters
            )
            
            return {
                "view": "cluster",
                "cluster_id": cluster_id,
                "base_empresa": base_empresa,
                "nodes": nodes,
                "edges": edges,
                "external_links": external_links,
                "stats": {
                    "nodes": len(nodes),
                    "edges": len(edges),
                    "external_inbound": sum(link["count"] for link in external_links if link["direction"] == "inbound"),
                    "external_outbound": sum(link["count"] for link in external_links if link["direction"] == "outbound")
                },
                "timestamp": timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo cluster graph para {cluster_id}: {e}", exc_info=True)
            raise
    
    @classmethod
    def _get_custom_clusters(cls, base_empresa: str, empresa_id: Optional[int], table_names: Set[str], fk_edges: List[Dict], learned_edges: List[Dict]) -> List[Dict]:
        """
        Obtiene clusters personalizados desde la base de datos.
        Si no existen, retorna lista vacía para usar heurísticas.
        
        Returns:
            Lista de clusters o lista vacía si no hay clusters personalizados
        """
        from django.db.models import Q
        
        # Buscar asignaciones personalizadas
        filters = Q(base_empresa=base_empresa)
        if empresa_id:
            filters = Q(base_empresa=base_empresa, empresa_id=empresa_id) | Q(base_empresa=base_empresa, empresa_id__isnull=True)
        else:
            filters = Q(base_empresa=base_empresa, empresa_id__isnull=True)
        
        assignments = TableClusterAssignment.objects.filter(filters).order_by('cluster_id', 'order', 'table_name')
        
        if not assignments.exists():
            return []  # No hay clusters personalizados, usar heurísticas
        
        # Agrupar por cluster_id
        cluster_dict = {}
        for assignment in assignments:
            cluster_id = assignment.cluster_id
            if cluster_id not in cluster_dict:
                cluster_dict[cluster_id] = {
                    "id": cluster_id,
                    "label": assignment.cluster_label,
                    "table_names": [],
                    "tables_count": 0
                }
            cluster_dict[cluster_id]["table_names"].append(assignment.table_name)
            cluster_dict[cluster_id]["tables_count"] += 1
        
        clusters = list(cluster_dict.values())
        
        # Calcular estadísticas por cluster (igual que en _cluster_by_prefix)
        for cluster in clusters:
            cluster_tables = set(cluster["table_names"])
            
            # Contar FK edges internas
            fk_count = sum(
                1 for edge in fk_edges
                if edge["tabla_origen"] in cluster_tables and edge["tabla_destino"] in cluster_tables
            )
            
            # Contar learned edges internas
            learned_count = sum(
                1 for edge in learned_edges
                if edge["from_table"] in cluster_tables and edge["to_table"] in cluster_tables
            )
            
            # Calcular densidad
            n = len(cluster_tables)
            max_edges = n * (n - 1) if n > 1 else 0
            density = (fk_count + learned_count) / max_edges if max_edges > 0 else 0.0
            
            cluster["fk_edges"] = fk_count
            cluster["learned_edges"] = learned_count
            cluster["density"] = round(density, 4)
        
        logger.info(f"📊 Clustering personalizado: {len(clusters)} clusters encontrados")
        return clusters
    
    @classmethod
    def _cluster_by_prefix(cls, table_names: Set[str], fk_edges: List[Dict], learned_edges: List[Dict]) -> List[Dict]:
        """
        Agrupa tablas por prefijo (substring antes del primer _).
        
        Reglas:
        - Prefijo = substring antes del primer _
        - Si no tiene _, cluster = "otros"
        - Si el prefijo aparece en < 3 tablas, mandarlo a "otros"
        """
        # Agrupar por prefijo
        prefix_groups = defaultdict(list)
        
        for table_name in table_names:
            if '_' in table_name:
                prefix = table_name.split('_')[0]
            else:
                prefix = "otros"
            
            prefix_groups[prefix].append(table_name)
        
        # Filtrar prefijos con < 3 tablas -> "otros"
        clusters = []
        otros_tables = []
        
        for prefix, tables in prefix_groups.items():
            if len(tables) < 3:
                otros_tables.extend(tables)
            else:
                clusters.append({
                    "id": prefix,
                    "label": prefix.capitalize(),
                    "table_names": tables,
                    "tables_count": len(tables)
                })
        
        # Agregar cluster "otros" si tiene tablas
        if otros_tables:
            clusters.append({
                "id": "otros",
                "label": "Otros",
                "table_names": otros_tables,
                "tables_count": len(otros_tables)
            })
        
        # Calcular estadísticas por cluster
        for cluster in clusters:
            cluster_tables = set(cluster["table_names"])
            
            # Contar FK edges internas
            fk_count = sum(
                1 for edge in fk_edges
                if edge["tabla_origen"] in cluster_tables and edge["tabla_destino"] in cluster_tables
            )
            
            # Contar learned edges internas
            learned_count = sum(
                1 for edge in learned_edges
                if edge["from_table"] in cluster_tables and edge["to_table"] in cluster_tables
            )
            
            # Calcular densidad (edges posibles vs edges reales)
            n = len(cluster_tables)
            max_edges = n * (n - 1) if n > 1 else 0
            density = (fk_count + learned_count) / max_edges if max_edges > 0 else 0.0
            
            cluster["fk_edges"] = fk_count
            cluster["learned_edges"] = learned_count
            cluster["density"] = round(density, 4)
        
        logger.info(f"📊 Clustering: {len(clusters)} clusters creados")
        return clusters
    
    @classmethod
    def _get_active_learned_relationships(cls, empresa_id: Optional[int]) -> List[Dict]:
        """
        Obtiene relaciones aprendidas activas (approved y no bloqueadas).
        
        Returns:
            Lista de dicts con estructura similar a FK edges
        """
        from django.db.models import Q
        
        filters = Q(is_blocked=False)
        if empresa_id:
            filters = Q(empresa_id=empresa_id, is_blocked=False) | Q(empresa_id__isnull=True, is_blocked=False)
        
        # Filtrar por status: solo approved (o proposed con alta confianza si se permite)
        # Por ahora solo mostramos approved para overview
        learned_rels = LearnedRelationship.objects.filter(filters).filter(
            status=LearnedRelationship.RelationshipStatus.APPROVED
        ).order_by('-confidence')
        
        result = []
        for rel in learned_rels:
            result.append({
                "from_table": rel.from_table,
                "from_column": rel.from_column,
                "to_table": rel.to_table,
                "to_column": rel.to_column,
                "confidence": float(rel.effective_confidence),
                "status": rel.status,
                "source": rel.source,
                "usage_count": rel.usage_count,
                "success_count": rel.success_count,
                "match_rule_json": rel.match_rule_json,
                "validation_metrics_json": rel.validation_metrics_json,
                "version": rel.version
            })
        
        return result
    
    @classmethod
    def _calculate_stats(cls, table_names: Set[str], fk_edges: List[Dict], learned_edges: List[Dict]) -> Dict[str, Any]:
        """Calcula estadísticas agregadas."""
        return {
            "total_tables": len(table_names),
            "fk_edges": len(fk_edges),
            "learned_edges": len(learned_edges),
            "total_edges": len(fk_edges) + len(learned_edges)
        }
    
    @classmethod
    def _build_fk_edge(cls, fk: Dict) -> Dict:
        """Construye un edge de FK para vis.js."""
        is_self_ref = fk["tabla_origen"] == fk["tabla_destino"]
        
        title_parts = [f"{fk['tabla_origen']}.{fk['campo_origen']} → {fk['tabla_destino']}.{fk['campo_destino']}"]
        if is_self_ref:
            title_parts.append("(Auto-referencial)")
        if fk.get("update_rule") and fk["update_rule"] != 'RESTRICT':
            title_parts.append(f"UPDATE: {fk['update_rule']}")
        if fk.get("delete_rule") and fk["delete_rule"] != 'RESTRICT':
            title_parts.append(f"DELETE: {fk['delete_rule']}")
        
        edge = {
            "from": fk["tabla_origen"],
            "to": fk["tabla_destino"],
            "label": f"{fk['campo_origen']} → {fk['campo_destino']}",
            "title": " | ".join(title_parts),
            "arrows": "to",
            "color": {"color": "#10b981", "highlight": "#34d399"},
            "width": 2,
            "type": "foreign_key",
            "source": "foreign_key",
            "confidence": 1.0,
            "self_reference": is_self_ref,
            "constraint_name": fk.get("constraint_name"),
            "update_rule": fk.get("update_rule"),
            "delete_rule": fk.get("delete_rule")
        }
        
        if is_self_ref:
            edge["smooth"] = {"type": "curvedCCW", "roundness": 0.2}
            edge["selfReferenceSize"] = 30
        
        return edge
    
    @classmethod
    def _build_learned_edge(cls, learned: Dict) -> Dict:
        """Construye un edge de learned relationship para vis.js."""
        title_parts = [
            f"{learned['from_table']}.{learned['from_column']} → {learned['to_table']}.{learned['to_column']}"
        ]
        title_parts.append(f"(Aprendida, confianza: {learned['confidence']:.2f})")
        
        # Color según status (en PR2 se mejorará)
        color = "#f59e0b"  # Ámbar por defecto
        if learned.get("status") == "approved":
            color = "#f59e0b"
        elif learned.get("status") == "proposed":
            color = "#fbbf24"  # Ámbar más claro
        
        edge = {
            "from": learned["from_table"],
            "to": learned["to_table"],
            "label": f"{learned['from_column']} → {learned['to_column']}",
            "title": " | ".join(title_parts),
            "arrows": "to",
            "color": {"color": color, "highlight": "#fbbf24"},
            "width": 1.5,
            "dashes": [5, 5],
            "type": "learned",
            "source": learned.get("source", "manual"),
            "confidence": learned["confidence"],
            "status": learned.get("status", "proposed"),
            "usage_count": learned.get("usage_count", 0),
            "success_count": learned.get("success_count", 0),
            "match_rule_json": learned.get("match_rule_json", {}),
            "validation_metrics_json": learned.get("validation_metrics_json", {}),
            "version": learned.get("version", 1)
        }
        
        return edge
    
    @classmethod
    def _calculate_external_links(cls, cluster_tables: Set[str], fk_edges: List[Dict], 
                                  learned_edges: List[Dict], clusters: List[Dict]) -> List[Dict]:
        """
        Calcula conexiones externas del cluster hacia otros clusters.
        
        Returns:
            Lista de dicts con: to_cluster, direction, count
        """
        # Crear mapa de tabla -> cluster
        table_to_cluster = {}
        for cluster in clusters:
            for table in cluster["table_names"]:
                table_to_cluster[table] = cluster["id"]
        
        external_links = defaultdict(lambda: {"inbound": 0, "outbound": 0})
        
        # Procesar FK edges
        for fk in fk_edges:
            from_table = fk["tabla_origen"]
            to_table = fk["tabla_destino"]
            
            from_cluster = table_to_cluster.get(from_table)
            to_cluster = table_to_cluster.get(to_table)
            
            if from_table in cluster_tables and to_table not in cluster_tables:
                # Saliente
                if to_cluster:
                    external_links[to_cluster]["outbound"] += 1
            elif from_table not in cluster_tables and to_table in cluster_tables:
                # Entrante
                if from_cluster:
                    external_links[from_cluster]["inbound"] += 1
        
        # Procesar learned edges
        for learned in learned_edges:
            from_table = learned["from_table"]
            to_table = learned["to_table"]
            
            from_cluster = table_to_cluster.get(from_table)
            to_cluster = table_to_cluster.get(to_table)
            
            if from_table in cluster_tables and to_table not in cluster_tables:
                if to_cluster:
                    external_links[to_cluster]["outbound"] += 1
            elif from_table not in cluster_tables and to_table in cluster_tables:
                if from_cluster:
                    external_links[from_cluster]["inbound"] += 1
        
        # Convertir a lista
        result = []
        for cluster_id, counts in external_links.items():
            if counts["inbound"] > 0:
                result.append({
                    "to_cluster": cluster_id,
                    "direction": "inbound",
                    "count": counts["inbound"]
                })
            if counts["outbound"] > 0:
                result.append({
                    "to_cluster": cluster_id,
                    "direction": "outbound",
                    "count": counts["outbound"]
                })
        
        return result

