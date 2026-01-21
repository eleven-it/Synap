"""
Gestor de dependencias entre módulos del sistema Synap
Maneja la resolución de dependencias y verificación de consistencia
"""

from .module_registry import MODULE_CONFIGS


class DependencyManager:
    """Gestor de dependencias entre módulos"""
    
    def __init__(self):
        self.dependencies = {}
        self.load_dependencies()
    
    def load_dependencies(self):
        """Carga las dependencias de todos los módulos"""
        for module_name, config in MODULE_CONFIGS.items():
            self.dependencies[module_name] = {
                'required': config.get('dependencies', []),
                'optional': config.get('optional_dependencies', [])
            }
    
    def get_dependency_tree(self, module_name, visited=None):
        """Obtiene el árbol de dependencias de un módulo, evitando recursión infinita por ciclos"""
        if visited is None:
            visited = set()
        if module_name in visited:
            return {'module': module_name, 'dependencies': 'circular', 'optional_dependencies': 'circular'}
        visited.add(module_name)
        tree = {
            'module': module_name,
            'dependencies': [],
            'optional_dependencies': []
        }
        if module_name in self.dependencies:
            # Dependencias requeridas
            for dep in self.dependencies[module_name]['required']:
                tree['dependencies'].append(self.get_dependency_tree(dep, visited.copy()))
            # Dependencias opcionales
            for dep in self.dependencies[module_name]['optional']:
                tree['optional_dependencies'].append(self.get_dependency_tree(dep, visited.copy()))
        return tree
    
    def get_all_dependencies(self, module_name):
        """Obtiene todas las dependencias de un módulo (recursivo)"""
        all_deps = set()
        
        def collect_deps(module):
            if module in self.dependencies:
                for dep in self.dependencies[module]['required']:
                    if dep not in all_deps:
                        all_deps.add(dep)
                        collect_deps(dep)
        
        collect_deps(module_name)
        return list(all_deps)
    
    def get_activation_order(self, modules_to_activate):
        """Obtiene el orden correcto para activar módulos"""
        order = []
        visited = set()
        
        def visit(module):
            if module in visited:
                return
            visited.add(module)
            
            if module in self.dependencies:
                for dep in self.dependencies[module]['required']:
                    visit(dep)
            
            order.append(module)
        
        for module in modules_to_activate:
            visit(module)
        
        return order
    
    def get_deactivation_order(self, modules_to_deactivate):
        """Obtiene el orden correcto para desactivar módulos"""
        order = []
        visited = set()
        
        def visit(module):
            if module in visited:
                return
            visited.add(module)
            
            # Primero visitar dependientes
            dependents = self.get_module_dependents(module)
            for dep in dependents:
                if dep in modules_to_deactivate:
                    visit(dep)
            
            order.append(module)
        
        for module in modules_to_deactivate:
            visit(module)
        
        return order
    
    def check_circular_dependencies(self):
        """Verifica dependencias circulares"""
        visited = set()
        rec_stack = set()
        
        def has_cycle(module):
            visited.add(module)
            rec_stack.add(module)
            
            if module in self.dependencies:
                for dep in self.dependencies[module]['required']:
                    if dep not in visited:
                        if has_cycle(dep):
                            return True
                    elif dep in rec_stack:
                        return True
            
            rec_stack.remove(module)
            return False
        
        for module in MODULE_CONFIGS.keys():
            if module not in visited:
                if has_cycle(module):
                    return True
        
        return False
    
    def get_circular_dependencies(self):
        """Obtiene las dependencias circulares específicas"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def find_cycles(module, path):
            if module in rec_stack:
                cycle_start = path.index(module)
                cycles.append(path[cycle_start:] + [module])
                return
            
            if module in visited:
                return
            
            visited.add(module)
            rec_stack.add(module)
            path.append(module)
            
            if module in self.dependencies:
                for dep in self.dependencies[module]['required']:
                    find_cycles(dep, path.copy())
            
            rec_stack.remove(module)
        
        for module in MODULE_CONFIGS.keys():
            if module not in visited:
                find_cycles(module, [])
        
        return cycles
    
    def get_module_dependents(self, module_name):
        """Obtiene los módulos que dependen de este"""
        dependents = []
        
        for module, deps in self.dependencies.items():
            if module_name in deps['required']:
                dependents.append(module)
        
        return dependents
    
    def get_optional_dependents(self, module_name):
        """Obtiene los módulos que tienen este como dependencia opcional"""
        dependents = []
        
        for module, deps in self.dependencies.items():
            if module_name in deps['optional']:
                dependents.append(module)
        
        return dependents
    
    def validate_dependencies(self, module_name):
        """Valida las dependencias de un módulo"""
        if module_name not in self.dependencies:
            return False, f"Módulo {module_name} no encontrado"
        
        deps = self.dependencies[module_name]
        
        # Verificar que las dependencias requeridas existan
        for dep in deps['required']:
            if dep not in MODULE_CONFIGS:
                return False, f"Dependencia requerida {dep} no existe"
        
        # Verificar que las dependencias opcionales existan
        for dep in deps['optional']:
            if dep not in MODULE_CONFIGS:
                return False, f"Dependencia opcional {dep} no existe"
        
        return True, "Dependencias válidas"
    
    def get_missing_dependencies(self, module_name, active_modules):
        """Obtiene las dependencias faltantes de un módulo"""
        if module_name not in self.dependencies:
            return []
        
        required_deps = self.dependencies[module_name]['required']
        missing = []
        
        for dep in required_deps:
            if dep not in active_modules:
                missing.append(dep)
        
        return missing
    
    def get_conflicting_dependencies(self, modules_to_activate):
        """Obtiene conflictos de dependencias entre módulos"""
        conflicts = []
        
        for module in modules_to_activate:
            if module not in self.dependencies:
                continue
            
            deps = self.dependencies[module]['required']
            
            for dep in deps:
                if dep not in modules_to_activate:
                    conflicts.append({
                        'module': module,
                        'missing_dependency': dep,
                        'type': 'missing_required'
                    })
        
        return conflicts
    
    def get_dependency_graph(self):
        """Obtiene el grafo completo de dependencias"""
        graph = {
            'nodes': [],
            'edges': []
        }
        
        # Nodos (módulos)
        for module_name in MODULE_CONFIGS.keys():
            config = MODULE_CONFIGS[module_name]
            graph['nodes'].append({
                'id': module_name,
                'name': config['display_name'],
                'is_core': config.get('is_core', False),
                'is_required': config.get('is_required', False),
            })
        
        # Aristas (dependencias)
        for module_name, deps in self.dependencies.items():
            for dep in deps['required']:
                graph['edges'].append({
                    'from': dep,
                    'to': module_name,
                    'type': 'required'
                })
            
            for dep in deps['optional']:
                graph['edges'].append({
                    'from': dep,
                    'to': module_name,
                    'type': 'optional'
                })
        
        return graph
    
    def get_impact_analysis(self, module_name):
        """Análisis de impacto de activar/desactivar un módulo"""
        impact = {
            'module': module_name,
            'activation_impact': {
                'required_modules': [],
                'optional_modules': [],
                'total_modules': 0
            },
            'deactivation_impact': {
                'affected_modules': [],
                'broken_dependencies': [],
                'total_affected': 0
            }
        }
        
        # Impacto de activación
        all_deps = self.get_all_dependencies(module_name)
        impact['activation_impact']['required_modules'] = all_deps
        impact['activation_impact']['total_modules'] = len(all_deps)
        
        # Impacto de desactivación
        dependents = self.get_module_dependents(module_name)
        impact['deactivation_impact']['affected_modules'] = dependents
        impact['deactivation_impact']['total_affected'] = len(dependents)
        
        return impact
    
    def suggest_activation_order(self, modules_to_activate):
        """Sugiere el orden óptimo para activar módulos"""
        # Obtener orden de dependencias
        activation_order = self.get_activation_order(modules_to_activate)
        
        # Agrupar por prioridad
        core_modules = []
        required_modules = []
        optional_modules = []
        
        for module in activation_order:
            config = MODULE_CONFIGS[module]
            if config.get('is_core', False):
                core_modules.append(module)
            elif config.get('is_required', False):
                required_modules.append(module)
            else:
                optional_modules.append(module)
        
        return {
            'core_modules': core_modules,
            'required_modules': required_modules,
            'optional_modules': optional_modules,
            'full_order': activation_order
        }


# Instancia global del DependencyManager
dependency_manager = DependencyManager() 