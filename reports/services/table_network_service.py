"""
Servicio para obtener ego networks (redes centradas en una tabla) usando BFS.
Permite expandir relaciones hasta una profundidad específica con filtros.
"""
import logging
from typing import Dict, List, Optional, Set, Any
from collections import defaultdict, deque
from django.utils import timezone

from .semantic_service import SemanticService
from ..models import LearnedRelationship

logger = logging.getLogger(__name__)


class TableNetworkService:
    """Servicio para obtener ego networks de tablas."""
    
    @classmethod
    def get_table_network(cls, base_empresa: str, empresa_id: Optional[int], table: str, 
                         depth: int, filters: Dict) -> Dict[str, Any]:
        """
        Obtiene el ego network de una tabla usando BFS.
        
        Args:
            base_empresa: Base de datos MySQL
            empresa_id: ID de empresa
            table: Tabla central
            depth: Profundidad de expansión (1, 2, 3)
            filters: Dict con type, direction, min_conf, status, hide_temp
            
        Returns:
            Dict con nodes, edges y stats del ego network
        """
        try:
            # Validar que la tabla existe
            datasources = SemanticService.list_datasources(base_empresa=base_empresa)
            all_tables = {ds.name: ds for ds in datasources}
            
            if table not in all_tables:
                raise ValueError(f"Tabla '{table}' no existe en {base_empresa}")
            
            # Obtener todas las relaciones
            fk_edges = SemanticService.get_all_foreign_keys(base_empresa)
            learned_edges = cls._get_filtered_learned_relationships(empresa_id, filters)
            
            # Construir índices de adyacencia
            adj_out, adj_in = cls._build_adjacency_indexes(fk_edges, learned_edges, filters, all_tables.keys())
            
            # BFS desde tabla central
            nodes, edges = cls._bfs_expand(table, depth, adj_out, adj_in, filters, all_tables)
            
            return {
                "view": "table",
                "center": table,
                "base_empresa": base_empresa,
                "depth": depth,
                "nodes": nodes,
                "edges": edges,
                "stats": {
                    "nodes": len(nodes),
                    "edges": len(edges),
                    "direct_neighbors": len([n for n in nodes if n.get("distance") == 1])
                },
                "timestamp": timezone.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error obteniendo table network para {table}: {e}", exc_info=True)
            raise
    
    @classmethod
    def _build_adjacency_indexes(cls, fk_edges: List[Dict], learned_edges: List[Dict], 
                                 filters: Dict, valid_tables: Set[str]) -> tuple[Dict, Dict]:
        """
        Construye índices de adyacencia para BFS.
        
        Returns:
            (adj_out, adj_in) donde:
            - adj_out[table] = lista de edges salientes
            - adj_in[table] = lista de edges entrantes
        """
        adj_out = defaultdict(list)
        adj_in = defaultdict(list)
        
        # Procesar FK edges
        if filters.get("type") in ("both", "fk"):
            for fk in fk_edges:
                from_table = fk["tabla_origen"]
                to_table = fk["tabla_destino"]
                
                # Filtrar por tablas válidas y hide_temp
                if not cls._should_include_table(from_table, valid_tables, filters):
                    continue
                if not cls._should_include_table(to_table, valid_tables, filters):
                    continue
                
                edge_data = {
                    "type": "foreign_key",
                    "from": from_table,
                    "to": to_table,
                    "data": fk
                }
                
                adj_out[from_table].append(edge_data)
                adj_in[to_table].append(edge_data)
        
        # Procesar learned edges
        if filters.get("type") in ("both", "learned"):
            min_conf = filters.get("min_conf", 0.8)
            
            for learned in learned_edges:
                from_table = learned["from_table"]
                to_table = learned["to_table"]
                confidence = learned.get("confidence", 0.5)
                
                # Filtrar por confianza mínima
                if confidence < min_conf:
                    continue
                
                # Filtrar por status
                status_filter = filters.get("status", "approved")
                learned_status = learned.get("status", "proposed")
                if status_filter == "approved" and learned_status != "approved":
                    continue
                if status_filter == "proposed" and learned_status not in ("approved", "proposed"):
                    continue
                
                # Filtrar por tablas válidas y hide_temp
                if not cls._should_include_table(from_table, valid_tables, filters):
                    continue
                if not cls._should_include_table(to_table, valid_tables, filters):
                    continue
                
                edge_data = {
                    "type": "learned",
                    "from": from_table,
                    "to": to_table,
                    "data": learned
                }
                
                adj_out[from_table].append(edge_data)
                adj_in[to_table].append(edge_data)
        
        return adj_out, adj_in
    
    @classmethod
    def _should_include_table(cls, table: str, valid_tables: Set[str], filters: Dict) -> bool:
        """Verifica si una tabla debe incluirse según filtros."""
        # Verificar que existe
        if table not in valid_tables:
            return False
        
        # Verificar hide_temp
        if filters.get("hide_temp", True):
            if table.startswith("temp_") or table.endswith("_temp") or table.startswith("staging_"):
                return False
        
        return True
    
    @classmethod
    def _bfs_expand(cls, start_table: str, depth: int, adj_out: Dict, adj_in: Dict, 
                   filters: Dict, all_tables: Dict[str, Any]) -> tuple[List[Dict], List[Dict]]:
        """
        Expande el grafo usando BFS desde start_table hasta depth.
        
        Returns:
            (nodes, edges) donde nodes incluye distancia desde el centro
        """
        direction = filters.get("direction", "both")
        visited = {start_table}
        nodes = []
        edges = []
        queue = deque([(start_table, 0)])  # (table, current_depth)
        
        # Agregar nodo central
        ds = all_tables.get(start_table)
        nodes.append({
            "id": start_table,
            "label": start_table,
            "title": ds.description if ds else f"Tabla {start_table}",
            "group": "table",
            "shape": "box",
            "distance": 0,
            "color": {
                "background": "#3b82f6",
                "border": "#1e40af",
                "highlight": {"background": "#60a5fa", "border": "#3b82f6"}
            }
        })
        
        while queue:
            current_table, current_depth = queue.popleft()
            
            if current_depth >= depth:
                continue
            
            # Obtener vecinos según dirección
            neighbors = []
            
            if direction in ("both", "out"):
                neighbors.extend(adj_out.get(current_table, []))
            
            if direction in ("both", "in"):
                neighbors.extend(adj_in.get(current_table, []))
            
            for edge_data in neighbors:
                neighbor_table = edge_data["to"] if edge_data["from"] == current_table else edge_data["from"]
                
                # Evitar ciclos y ya visitados
                if neighbor_table in visited:
                    # Pero agregar el edge si conecta nodos ya incluidos
                    if neighbor_table in {n["id"] for n in nodes}:
                        edge = cls._build_edge(edge_data, current_table, neighbor_table)
                        if edge and not any(e["from"] == edge["from"] and e["to"] == edge["to"] for e in edges):
                            edges.append(edge)
                    continue
                
                visited.add(neighbor_table)
                
                # Agregar nodo
                ds = all_tables.get(neighbor_table)
                nodes.append({
                    "id": neighbor_table,
                    "label": neighbor_table,
                    "title": ds.description if ds else f"Tabla {neighbor_table}",
                    "group": "table",
                    "shape": "box",
                    "distance": current_depth + 1,
                    "color": {
                        "background": "#3b82f6",
                        "border": "#1e40af",
                        "highlight": {"background": "#60a5fa", "border": "#3b82f6"}
                    }
                })
                
                # Agregar edge
                edge = cls._build_edge(edge_data, current_table, neighbor_table)
                if edge:
                    edges.append(edge)
                
                # Agregar a cola para siguiente nivel
                queue.append((neighbor_table, current_depth + 1))
        
        logger.debug(f"🔍 BFS desde {start_table} (depth={depth}): {len(nodes)} nodos, {len(edges)} edges")
        return nodes, edges
    
    @classmethod
    def _build_edge(cls, edge_data: Dict, from_table: str, to_table: str) -> Optional[Dict]:
        """Construye un edge para vis.js desde edge_data."""
        data = edge_data["data"]
        
        if edge_data["type"] == "foreign_key":
            return cls._build_fk_edge(data, from_table, to_table)
        else:
            return cls._build_learned_edge(data, from_table, to_table)
    
    @classmethod
    def _build_fk_edge(cls, fk: Dict, from_table: str, to_table: str) -> Dict:
        """Construye edge de FK."""
        is_self_ref = from_table == to_table
        
        title_parts = [f"{from_table}.{fk['campo_origen']} → {to_table}.{fk['campo_destino']}"]
        if is_self_ref:
            title_parts.append("(Auto-referencial)")
        if fk.get("update_rule") and fk["update_rule"] != 'RESTRICT':
            title_parts.append(f"UPDATE: {fk['update_rule']}")
        if fk.get("delete_rule") and fk["delete_rule"] != 'RESTRICT':
            title_parts.append(f"DELETE: {fk['delete_rule']}")
        
        edge = {
            "from": from_table,
            "to": to_table,
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
    def _build_learned_edge(cls, learned: Dict, from_table: str, to_table: str) -> Dict:
        """Construye edge de learned relationship."""
        title_parts = [
            f"{from_table}.{learned['from_column']} → {to_table}.{learned['to_column']}"
        ]
        title_parts.append(f"(Aprendida, confianza: {learned.get('confidence', 0.5):.2f})")
        
        color = "#f59e0b"
        status = learned.get("status", "proposed")
        if status == "approved":
            color = "#f59e0b"
        elif status == "proposed":
            color = "#fbbf24"
        elif status == "deprecated":
            color = "#9ca3af"  # Gris
        
        edge = {
            "from": from_table,
            "to": to_table,
            "label": f"{learned['from_column']} → {learned['to_column']}",
            "title": " | ".join(title_parts),
            "arrows": "to",
            "color": {"color": color, "highlight": "#fbbf24"},
            "width": 1.5,
            "dashes": [5, 5],
            "type": "learned",
            "source": learned.get("source", "manual"),
            "confidence": learned.get("confidence", 0.5),
            "status": status,
            "usage_count": learned.get("usage_count", 0),
            "success_count": learned.get("success_count", 0),
            "match_rule_json": learned.get("match_rule_json", {}),
            "validation_metrics_json": learned.get("validation_metrics_json", {}),
            "version": learned.get("version", 1)
        }
        
        return edge
    
    @classmethod
    def _get_filtered_learned_relationships(cls, empresa_id: Optional[int], filters: Dict) -> List[Dict]:
        """Obtiene learned relationships filtradas."""
        from django.db.models import Q
        
        filter_q = Q(is_blocked=False)
        if empresa_id:
            filter_q = Q(empresa_id=empresa_id, is_blocked=False) | Q(empresa_id__isnull=True, is_blocked=False)
        
        # Filtrar por status
        status_filter = filters.get("status", "approved")
        if status_filter == "approved":
            filter_q &= Q(status=LearnedRelationship.RelationshipStatus.APPROVED)
        elif status_filter == "proposed":
            filter_q &= Q(status__in=[
                LearnedRelationship.RelationshipStatus.APPROVED,
                LearnedRelationship.RelationshipStatus.PROPOSED
            ])
        # "all" no filtra por status
        
        learned_rels = LearnedRelationship.objects.filter(filter_q).order_by('-confidence')
        
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

