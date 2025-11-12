"""
Schema Graph Service
Construye un grafo del schema y encuentra rutas óptimas de joins
"""
from typing import List, Dict, Optional, Set, Tuple
from collections import defaultdict, deque
import heapq

from ..models import RelationshipCandidate


class SchemaGraph:
    """
    Grafo del schema de la BD para encontrar caminos de join óptimos
    """
    
    def __init__(self, min_confidence: float = 0.80):
        """
        Args:
            min_confidence: Score mínimo para considerar una arista válida
            Default: 0.80 (criterio conservador - solo alta confianza)
        """
        self.min_confidence = min_confidence
        self.graph = defaultdict(list)  # tabla -> [(tabla_destino, relación)]
        self._build_graph()
    
    def _build_graph(self):
        """Construye el grafo desde el catálogo de relaciones"""
        relationships = RelationshipCandidate.objects.filter(
            confidence_score__gte=self.min_confidence
        ).order_by('-confidence_score')
        
        for rel in relationships:
            # Agregar arista: source -> target
            self.graph[rel.source_table].append({
                'target': rel.target_table,
                'source_column': rel.source_column,
                'target_column': rel.target_column,
                'confidence': rel.confidence_score,
                'cardinality': rel.cardinality,
                'has_index': rel.has_index,
                'times_used': rel.times_used_successfully,
                'weight': self._calculate_edge_weight(rel)
            })
            
            # Agregar arista inversa: target -> source (bidireccional)
            self.graph[rel.target_table].append({
                'target': rel.source_table,
                'source_column': rel.target_column,
                'target_column': rel.source_column,
                'confidence': rel.confidence_score,
                'cardinality': self._invert_cardinality(rel.cardinality),
                'has_index': rel.has_index,
                'times_used': rel.times_used_successfully,
                'weight': self._calculate_edge_weight(rel)
            })
    
    def _calculate_edge_weight(self, rel: RelationshipCandidate) -> float:
        """
        Calcula peso de la arista (menor = mejor)
        Considera: confianza, índices, historial de uso
        """
        # Base: invertir confianza (mayor confianza = menor peso)
        weight = 1.0 - rel.confidence_score
        
        # Penalización si no tiene índice (+0.3)
        if not rel.has_index:
            weight += 0.3
        
        # Bonificación por historial exitoso (-0.1 por cada 10 usos)
        if rel.times_used_successfully > 0:
            weight -= min(0.3, rel.times_used_successfully / 10 * 0.1)
        
        # Penalización por fallos (+0.05 por cada fallo)
        if rel.times_failed > 0:
            weight += min(0.2, rel.times_failed * 0.05)
        
        return max(0.1, weight)  # Mínimo 0.1
    
    def _invert_cardinality(self, cardinality: str) -> str:
        """Invierte la cardinalidad para arista reversa"""
        inversions = {
            '1:1': '1:1',
            '1:N': 'N:1',
            'N:1': '1:N',
            'N:M': 'N:M'
        }
        return inversions.get(cardinality, 'N:1')
    
    def find_shortest_path(
        self,
        source_table: str,
        target_table: str,
        max_hops: int = 3
    ) -> Optional[List[Dict]]:
        """
        Encuentra el camino MÁS CORTO entre dos tablas usando Dijkstra
        
        Args:
            source_table: Tabla de inicio
            target_table: Tabla de destino
            max_hops: Máximo número de saltos permitidos
        
        Returns:
            Lista de aristas (relaciones) en el camino óptimo, o None
        """
        if source_table == target_table:
            return []
        
        # Dijkstra con heap
        distances = {source_table: 0.0}
        previous = {}
        visited = set()
        
        # Heap: (distancia, tabla_actual, hop_count)
        heap = [(0.0, source_table, 0)]
        
        while heap:
            current_dist, current_table, hop_count = heapq.heappop(heap)
            
            if current_table in visited:
                continue
            
            if hop_count > max_hops:
                continue
            
            visited.add(current_table)
            
            # ¿Llegamos al destino?
            if current_table == target_table:
                return self._reconstruct_path(previous, source_table, target_table)
            
            # Explorar vecinos
            for edge in self.graph.get(current_table, []):
                neighbor = edge['target']
                
                if neighbor in visited:
                    continue
                
                new_dist = current_dist + edge['weight']
                
                if neighbor not in distances or new_dist < distances[neighbor]:
                    distances[neighbor] = new_dist
                    previous[neighbor] = (current_table, edge)
                    heapq.heappush(heap, (new_dist, neighbor, hop_count + 1))
        
        # No se encontró camino
        return None
    
    def _reconstruct_path(
        self,
        previous: Dict,
        source: str,
        target: str
    ) -> List[Dict]:
        """Reconstruye el camino desde el diccionario de predecesores"""
        path = []
        current = target
        
        while current in previous:
            prev_table, edge = previous[current]
            path.append({
                'source_table': prev_table,
                'source_column': edge['source_column'],
                'target_table': edge['target'],
                'target_column': edge['target_column'],
                'confidence': edge['confidence'],
                'cardinality': edge['cardinality'],
                'has_index': edge['has_index'],
                'weight': edge['weight']
            })
            current = prev_table
        
        # Invertir el camino (estaba target->source)
        path.reverse()
        return path
    
    def find_all_paths(
        self,
        source_table: str,
        target_table: str,
        max_hops: int = 3,
        top_k: int = 3
    ) -> List[Tuple[float, List[Dict]]]:
        """
        Encuentra los top-K mejores caminos entre dos tablas
        
        Returns:
            Lista de (score_total, path) ordenados por score
        """
        if source_table == target_table:
            return [(0.0, [])]
        
        all_paths = []
        
        # BFS con tracking de caminos
        queue = deque([(source_table, [], 0.0, 0, set([source_table]))])
        
        while queue:
            current, path, total_weight, hops, visited = queue.popleft()
            
            if hops > max_hops:
                continue
            
            for edge in self.graph.get(current, []):
                neighbor = edge['target']
                
                # Evitar ciclos
                if neighbor in visited:
                    continue
                
                new_path = path + [edge]
                new_weight = total_weight + edge['weight']
                new_visited = visited | {neighbor}
                
                # ¿Llegamos?
                if neighbor == target_table:
                    all_paths.append((new_weight, self._edge_list_to_path(new_path)))
                else:
                    queue.append((
                        neighbor,
                        new_path,
                        new_weight,
                        hops + 1,
                        new_visited
                    ))
        
        # Ordenar por peso (menor = mejor) y retornar top-K
        all_paths.sort(key=lambda x: x[0])
        return all_paths[:top_k]
    
    def _edge_list_to_path(self, edges: List[Dict]) -> List[Dict]:
        """Convierte lista de aristas a formato de path"""
        return [{
            'source_table': e['source_column'].split('.')[0] if '.' in e['source_column'] else '',
            'source_column': e['source_column'],
            'target_table': e['target'],
            'target_column': e['target_column'],
            'confidence': e['confidence'],
            'cardinality': e['cardinality'],
            'has_index': e['has_index']
        } for e in edges]
    
    def get_neighbors(self, table: str, min_confidence: float = None) -> List[Dict]:
        """
        Retorna todas las tablas directamente relacionadas con la dada
        """
        if min_confidence is None:
            min_confidence = self.min_confidence
        
        neighbors = []
        for edge in self.graph.get(table, []):
            if edge['confidence'] >= min_confidence:
                neighbors.append({
                    'table': edge['target'],
                    'source_column': edge['source_column'],
                    'target_column': edge['target_column'],
                    'confidence': edge['confidence'],
                    'cardinality': edge['cardinality']
                })
        
        return neighbors
    
    def find_multi_table_path(
        self,
        tables: List[str],
        strategy: str = 'star'
    ) -> Optional[List[Dict]]:
        """
        Encuentra el camino óptimo que conecte MÚLTIPLES tablas
        
        Args:
            tables: Lista de tablas a conectar
            strategy: 'star' (desde una tabla central) o 'chain' (secuencial)
        
        Returns:
            Lista de joins necesarios
        """
        if len(tables) < 2:
            return []
        
        if strategy == 'star':
            return self._find_star_path(tables)
        elif strategy == 'chain':
            return self._find_chain_path(tables)
        else:
            raise ValueError(f"Estrategia desconocida: {strategy}")
    
    def _find_star_path(self, tables: List[str]) -> Optional[List[Dict]]:
        """
        Conecta todas las tablas a UNA tabla central (estrella)
        Útil cuando una tabla es el "maestro" común
        """
        # Buscar la tabla con más conexiones directas al resto
        best_center = None
        best_score = -1
        
        for candidate in tables:
            score = 0
            for other in tables:
                if candidate != other:
                    path = self.find_shortest_path(candidate, other, max_hops=2)
                    if path:
                        score += 1
            
            if score > best_score:
                best_score = score
                best_center = candidate
        
        if not best_center or best_score == 0:
            return None
        
        # Construir camino desde el centro a todas las demás
        joins = []
        for table in tables:
            if table != best_center:
                path = self.find_shortest_path(best_center, table, max_hops=2)
                if path:
                    joins.extend(path)
        
        return joins if joins else None
    
    def _find_chain_path(self, tables: List[str]) -> Optional[List[Dict]]:
        """
        Conecta tablas secuencialmente (cadena)
        Útil para transacciones: Cliente -> Pedido -> PedidoDetalle -> Articulo
        """
        joins = []
        
        for i in range(len(tables) - 1):
            path = self.find_shortest_path(tables[i], tables[i + 1], max_hops=2)
            if not path:
                return None  # No se puede completar la cadena
            joins.extend(path)
        
        return joins

