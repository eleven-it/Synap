"""
Herramienta para Análisis de Flujo de Navegación VB6
Sigue la cadena de llamadas entre formularios y procedimientos
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class NavigationFlowTool:
    """
    Analiza el flujo de navegación entre formularios VB6
    
    Construye el camino desde:
    Menu → Procedimiento → Formulario Lista → Formulario Final
    """
    
    def __init__(self, vb6_root_path: str = None):
        import os
        if os.path.exists('/app/administraNET_Limpio'):
            self.vb6_root_path = vb6_root_path or '/app/administraNET_Limpio'
        else:
            self.vb6_root_path = vb6_root_path or '/Users/sebastian/Documents/Administranet/Proyectos/Synap/administraNET_Limpio'
        
        self.analyzed_procedures = set()
    
    def trace_navigation_flow(self, procedure_name: str, max_depth: int = 5) -> List[Dict]:
        """
        Traza el flujo de navegación desde un procedimiento
        
        Args:
            procedure_name: Nombre del procedimiento (ej: "Menu_Pedido_Venta")
            max_depth: Profundidad máxima del trace
        
        Returns:
            Lista de pasos del flujo con detalles
        """
        logger.info(f"[NavigationFlow] Trazando flujo desde: {procedure_name}")
        
        flow = []
        self.analyzed_procedures.clear()
        
        # Buscar el procedimiento en Principal.frm
        principal_file = Path(self.vb6_root_path) / 'Formularios' / 'Principal.frm'
        
        if not principal_file.exists():
            return flow
        
        try:
            with open(principal_file, 'r', encoding='latin-1', errors='ignore') as f:
                principal_content = f.read()
        except:
            return flow
        
        # Analizar el procedimiento inicial
        proc_info = self._analyze_procedure(principal_content, procedure_name, 'Principal.frm')
        
        if proc_info:
            flow.append(proc_info)
            
            # Seguir las llamadas a formularios
            for form_call in proc_info.get('forms_called', []):
                if len(flow) < max_depth:
                    form_info = self._analyze_form_call(form_call, max_depth - len(flow))
                    if form_info:
                        flow.extend(form_info)
        
        return flow
    
    def _analyze_procedure(self, content: str, proc_name: str, source_file: str) -> Optional[Dict]:
        """Analiza un procedimiento y extrae qué hace"""
        if proc_name in self.analyzed_procedures:
            return None
        
        self.analyzed_procedures.add(proc_name)
        
        # Buscar la definición del procedimiento
        proc_pattern = rf'(?:Private |Public )?Sub {re.escape(proc_name)}\(\)(.*?)End Sub'
        
        proc_match = re.search(proc_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if not proc_match:
            return None
        
        proc_code = proc_match.group(1)
        
        # Extraer:
        # 1. Formularios llamados (.Show)
        forms_called = self._extract_form_calls(proc_code)
        
        # 2. Configuraciones (Caption = ...)
        configurations = self._extract_configurations(proc_code)
        
        # 3. Validaciones (MsgBox)
        validations = self._extract_validations(proc_code)
        
        return {
            'type': 'procedure',
            'name': proc_name,
            'source_file': source_file,
            'forms_called': forms_called,
            'configurations': configurations,
            'validations': validations,
            'description': self._infer_procedure_description(proc_name, forms_called, configurations)
        }
    
    def _extract_form_calls(self, code: str) -> List[str]:
        """Extrae formularios que se llaman (.Show, Load)"""
        forms = []
        
        # Patrón: FormularioNombre.Show
        show_pattern = r'(\w+)\.Show'
        
        matches = re.finditer(show_pattern, code, re.IGNORECASE)
        
        for match in matches:
            form_name = match.group(1)
            # Filtrar controles comunes
            if form_name not in ['Info', 'form_espera', 'Avisos'] and not form_name.startswith('rs_'):
                forms.append(form_name)
        
        return list(set(forms))  # Eliminar duplicados
    
    def _extract_configurations(self, code: str) -> List[str]:
        """Extrae configuraciones que se setean antes de mostrar un formulario"""
        configs = []
        
        # Patrón: Formulario.Property = "Value" o Value
        config_pattern = r'(\w+)\.(\w+)\s*=\s*"([^"]+)"'
        
        matches = re.finditer(config_pattern, code)
        
        for match in matches:
            form = match.group(1)
            prop = match.group(2)
            value = match.group(3)
            
            # Solo Caption y propiedades relevantes
            if prop in ['Caption', 'Inicial', 'Accion']:
                configs.append(f'{form}.{prop} = "{value}"')
        
        return configs[:10]  # Máximo 10 configuraciones
    
    def _extract_validations(self, code: str) -> List[str]:
        """Extrae validaciones (MsgBox con mensajes)"""
        validations = []
        
        msgbox_pattern = r'MsgBox\s+"([^"]+)"'
        
        matches = re.finditer(msgbox_pattern, code, re.IGNORECASE)
        
        for match in matches:
            message = match.group(1)
            if len(message) > 10:  # Filtrar mensajes muy cortos
                validations.append(message)
        
        return validations[:5]  # Máximo 5 validaciones
    
    def _infer_procedure_description(
        self, 
        proc_name: str, 
        forms_called: List[str],
        configurations: List[str]
    ) -> str:
        """Infiere qué hace el procedimiento"""
        # Heurísticas basadas en el nombre
        name_lower = proc_name.lower()
        
        if 'menu_' in name_lower:
            # Es un procedimiento de menú
            if 'pedido' in name_lower:
                return 'Abre la lista de pedidos para seleccionar cliente'
            elif 'factura' in name_lower:
                return 'Abre el módulo de facturación'
            elif 'cliente' in name_lower:
                return 'Abre el ABM de clientes'
            else:
                return f'Abre el módulo de {proc_name.replace("Menu_", "")}'
        
        # Basado en formularios llamados
        if forms_called:
            first_form = forms_called[0]
            return f'Abre y configura {first_form}'
        
        return 'Procedimiento de navegación'
    
    def _analyze_form_call(self, form_name: str, max_depth: int) -> List[Dict]:
        """Analiza qué hace un formulario cuando se abre"""
        flow = []
        
        # Buscar el archivo del formulario
        form_file = self._find_form_file(form_name)
        
        if not form_file:
            return flow
        
        try:
            with open(form_file, 'r', encoding='latin-1', errors='ignore') as f:
                form_content = f.read()
        except:
            return flow
        
        # Detectar si es un formulario de lista/ABM
        if 'CargaComprobantes' in form_name or 'ABM' in form_name or 'Lista' in form_name:
            # Buscar qué formularios se abren desde sus eventos
            sub_forms = self._extract_form_calls(form_content[:50000])  # Primeros 50k
            
            flow.append({
                'type': 'intermediate_form',
                'name': form_name,
                'purpose': self._infer_form_purpose(form_name, form_content),
                'forms_called': sub_forms[:5]  # Máximo 5 sub-formularios
            })
            
            # Si hay sub-formularios, analizar el primero (generalmente el principal)
            if sub_forms and max_depth > 1:
                main_form = sub_forms[0]
                flow.append({
                    'type': 'target_form',
                    'name': main_form,
                    'purpose': self._infer_form_purpose(main_form, ''),
                    'is_final': True
                })
        else:
            # Es un formulario final
            flow.append({
                'type': 'target_form',
                'name': form_name,
                'purpose': self._infer_form_purpose(form_name, form_content),
                'is_final': True
            })
        
        return flow
    
    def _infer_form_purpose(self, form_name: str, form_content: str) -> str:
        """Infiere el propósito de un formulario"""
        name_lower = form_name.lower()
        
        # Heurísticas por nombre
        if 'cargacomprobantes' in name_lower:
            if 'ped' in name_lower:
                return 'Lista de clientes para crear presupuestos, pedidos o remitos'
            return 'Lista de comprobantes'
        
        if 'abm' in name_lower:
            return f'Alta/Baja/Modificación de {form_name.replace("ABM", "")}'
        
        if 'lista' in name_lower:
            return f'Lista de {form_name.replace("Lista", "")}'
        
        if 'carga' in name_lower:
            return f'Carga de {form_name.replace("Carga", "")}'
        
        if 'pedido' in name_lower:
            return 'Creación y edición de pedidos'
        
        if 'factura' in name_lower:
            return 'Facturación'
        
        return form_name
    
    def _find_form_file(self, form_name: str) -> Optional[Path]:
        """Busca el archivo .frm de un formulario"""
        if not form_name.endswith('.frm'):
            form_name = f'{form_name}.frm'
        
        root = Path(self.vb6_root_path)
        
        # Buscar en Formularios
        form_path = root / 'Formularios' / form_name
        if form_path.exists():
            return form_path
        
        # Buscar recursivamente
        for file_path in root.rglob(form_name):
            return file_path
        
        return None

