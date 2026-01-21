"""
Motor de grafo de dependencias para métricas.

Este módulo implementa un sistema de grafo dirigido acíclico (DAG) para
representar y validar dependencias entre métricas en reportes declarativos.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Any, Tuple
import logging
import re

logger = logging.getLogger(__name__)


@dataclass
class MetricNode:
    """Nodo en el grafo de métricas."""
    name: str
    expression: str
    depends_on: List[str] = field(default_factory=list)


class MetricGraph:
    """
    Grafo dirigido acíclico (DAG) de dependencias entre métricas.
    
    Permite detectar ciclos y calcular un orden topológico válido
    para el cálculo de métricas derivadas.
    """
    
    def __init__(self):
        """Inicializa un grafo vacío."""
        self.nodes: Dict[str, MetricNode] = {}
        self._adjacency: Dict[str, Set[str]] = {}  # Grafo de adyacencia
    
    def add_metric(self, node: MetricNode) -> None:
        """
        Agrega una métrica al grafo.
        
        Args:
            node: Nodo de métrica a agregar
        """
        self.nodes[node.name] = node
        self._adjacency[node.name] = set(node.depends_on)
    
    @classmethod
    def build_from_config(cls, config: Any) -> "MetricGraph":
        """
        Construye un MetricGraph desde una configuración de reporte.
        
        Args:
            config: ReportConfig o dict con configuración
            
        Returns:
            MetricGraph construido
        """
        graph = cls()
        
        # Extraer métricas del config
        if hasattr(config, 'metrics'):
            metrics_dict = config.metrics
        elif isinstance(config, dict):
            metrics_dict = config.get("metrics", {})
        else:
            return graph
        
        # Crear nodos para cada métrica
        for metric_name, metric_def in metrics_dict.items():
            if isinstance(metric_def, dict):
                expression = metric_def.get("expression", "")
                depends_on = metric_def.get("depends_on", [])
            elif hasattr(metric_def, 'expression'):
                expression = metric_def.expression
                depends_on = metric_def.depends_on if hasattr(metric_def, 'depends_on') else []
            else:
                continue
            
            # Inferir dependencias adicionales desde la expresión
            inferred_deps = cls._infer_dependencies(expression, list(metrics_dict.keys()))
            all_deps = list(set(depends_on + inferred_deps))
            
            node = MetricNode(
                name=metric_name,
                expression=expression,
                depends_on=all_deps
            )
            graph.add_metric(node)
        
        return graph
    
    @staticmethod
    def _infer_dependencies(expression: str, available_metrics: List[str]) -> List[str]:
        """
        Infiere dependencias de métricas desde una expresión.
        
        Busca referencias a nombres de métricas en la expresión.
        
        Args:
            expression: Expresión SQL o fórmula
            available_metrics: Lista de nombres de métricas disponibles
            
        Returns:
            Lista de nombres de métricas referenciadas
        """
        dependencies = []
        
        # Buscar referencias a métricas en la expresión
        # Patrón: nombre de métrica como palabra completa (no parte de otra palabra)
        for metric_name in available_metrics:
            # Usar regex para encontrar el nombre como palabra completa
            pattern = r'\b' + re.escape(metric_name) + r'\b'
            if re.search(pattern, expression, re.IGNORECASE):
                dependencies.append(metric_name)
        
        return dependencies
    
    def detect_cycles(self) -> List[List[str]]:
        """
        Detecta ciclos en el grafo de dependencias.
        
        Usa DFS (Depth-First Search) con colores para detectar ciclos.
        
        Returns:
            Lista de ciclos encontrados (cada ciclo es una lista de nombres de métricas)
        """
        cycles = []
        color: Dict[str, int] = {}  # 0: blanco, 1: gris (en proceso), 2: negro (completado)
        parent: Dict[str, Optional[str]] = {}
        
        # Inicializar todos los nodos como blancos
        for node_name in self.nodes:
            color[node_name] = 0
            parent[node_name] = None
        
        def dfs_visit(node_name: str, path: List[str]) -> None:
            """DFS recursivo para detectar ciclos."""
            color[node_name] = 1  # Marcar como gris (en proceso)
            path.append(node_name)
            
            # Visitar dependencias
            for dep in self._adjacency.get(node_name, set()):
                if dep not in self.nodes:
                    continue  # Dependencia a métrica inexistente
                
                if color[dep] == 0:  # Blanco: no visitado
                    parent[dep] = node_name
                    dfs_visit(dep, path)
                elif color[dep] == 1:  # Gris: encontramos un ciclo
                    # Construir el ciclo
                    cycle_start = path.index(dep)
                    cycle = path[cycle_start:] + [dep]
                    cycles.append(cycle.copy())
            
            color[node_name] = 2  # Marcar como negro (completado)
            path.pop()
        
        # Visitar todos los nodos blancos
        for node_name in self.nodes:
            if color[node_name] == 0:
                dfs_visit(node_name, [])
        
        return cycles
    
    def topo_sort(self) -> List[str]:
        """
        Calcula un orden topológico válido para el cálculo de métricas.
        
        Returns:
            Lista de nombres de métricas en orden topológico
            
        Raises:
            ValueError: Si el grafo contiene ciclos
        """
        cycles = self.detect_cycles()
        if cycles:
            cycle_str = " -> ".join(cycles[0])
            raise ValueError(f"El grafo contiene ciclos. Ejemplo: {cycle_str}")
        
        # Algoritmo de orden topológico (Kahn)
        in_degree: Dict[str, int] = {}
        for node_name in self.nodes:
            in_degree[node_name] = 0
        
        # Calcular grados de entrada
        for node_name, deps in self._adjacency.items():
            for dep in deps:
                if dep in in_degree:
                    in_degree[dep] += 1
        
        # Cola de nodos con grado de entrada 0
        queue: List[str] = [node for node, degree in in_degree.items() if degree == 0]
        result: List[str] = []
        
        while queue:
            node = queue.pop(0)
            result.append(node)
            
            # Reducir grado de entrada de dependencias
            for dep in self._adjacency.get(node, set()):
                if dep in in_degree:
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        queue.append(dep)
        
        # Verificar que todos los nodos fueron procesados
        if len(result) != len(self.nodes):
            # Esto no debería pasar si no hay ciclos, pero por seguridad
            remaining = set(self.nodes.keys()) - set(result)
            raise ValueError(f"No se pudo calcular orden topológico. Nodos restantes: {remaining}")
        
        return result
    
    def get_metric_order(self) -> List[str]:
        """
        Obtiene el orden recomendado para calcular métricas.
        
        Returns:
            Lista de nombres de métricas en orden de cálculo
        """
        try:
            return self.topo_sort()
        except ValueError as e:
            logger.warning(f"Error calculando orden topológico: {e}")
            # En caso de error, devolver orden alfabético como fallback
            return sorted(self.nodes.keys())
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Valida el grafo de métricas.
        
        Returns:
            Tupla (es_válido, lista_de_errores)
        """
        errors = []
        
        # Detectar ciclos
        cycles = self.detect_cycles()
        if cycles:
            for cycle in cycles:
                cycle_str = " -> ".join(cycle)
                errors.append(f"Ciclo de dependencias en métricas: {cycle_str}")
        
        # Verificar dependencias a métricas inexistentes
        for node_name, deps in self._adjacency.items():
            for dep in deps:
                if dep not in self.nodes:
                    errors.append(f"Métrica '{node_name}' depende de '{dep}' que no existe")
        
        return len(errors) == 0, errors
