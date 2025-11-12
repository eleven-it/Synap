"""
Analizador de Menús Dinámicos VB6
Extrae la estructura de menús, rutas y atajos de teclado
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MenuAnalyzerTool:
    """
    Analiza la estructura de menús dinámicos en Principal.frm
    
    Extrae:
    - Jerarquía de menús (Ventas > Pedido)
    - Atajos de teclado (F3, Ctrl+P, etc.)
    - Keys de menú (keyPed, keyFacturacion, etc.)
    - Procedimientos asociados (Menu_Pedido_Venta, etc.)
    """
    
    def __init__(self, vb6_root_path: str = None):
        import os
        if os.path.exists('/app/administraNET_Limpio'):
            self.vb6_root_path = vb6_root_path or '/app/administraNET_Limpio'
        else:
            self.vb6_root_path = vb6_root_path or '/Users/sebastian/Documents/Administranet/Proyectos/Synap/administraNET_Limpio'
    
    def find_menu_path_for_form(self, form_name: str) -> Optional[Dict]:
        """
        Encuentra la ruta de menú para un formulario específico
        
        Args:
            form_name: Nombre del formulario (ej: "Pedido")
        
        Returns:
            Dict con path, shortcut, key, procedure
        """
        logger.info(f"[MenuAnalyzer] Buscando ruta de menú para: {form_name}")
        
        # Leer Principal.frm
        principal_file = Path(self.vb6_root_path) / 'Formularios' / 'Principal.frm'
        
        if not principal_file.exists():
            logger.warning("[MenuAnalyzer] No se encontró Principal.frm")
            return None
        
        try:
            with open(principal_file, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"[MenuAnalyzer] Error leyendo Principal.frm: {e}")
            return None
        
        # 1. Buscar en AltaMenu() la definición del menú
        menu_structure = self._parse_menu_structure(content)
        
        # 2. Buscar el key asociado al formulario
        form_lower = form_name.lower()
        
        for menu_key, menu_info in menu_structure.items():
            if form_lower in menu_info['caption'].lower():
                # 3. Buscar el procedimiento que se llama
                procedure = self._find_procedure_for_key(content, menu_key)
                
                if procedure:
                    # 4. Construir la ruta completa
                    full_path = self._build_menu_path(menu_structure, menu_key)
                    
                    return {
                        'menu_path': full_path,
                        'menu_key': menu_key,
                        'caption': menu_info['caption'],
                        'shortcut': menu_info.get('shortcut'),
                        'procedure': procedure,
                        'parent_key': menu_info.get('parent'),
                        'confidence': 0.95
                    }
        
        logger.warning(f"[MenuAnalyzer] No se encontró entrada de menú para {form_name}")
        return None
    
    def _parse_menu_structure(self, content: str) -> Dict:
        """
        Parsea la estructura de menús desde AltaMenu()
        
        Returns:
            Dict con {key: {caption, parent, shortcut}}
        """
        menu_structure = {}
        
        # Buscar el procedimiento AltaMenu()
        alta_menu_match = re.search(
            r'Private Sub AltaMenu\(\)(.*?)End Sub',
            content,
            re.DOTALL | re.IGNORECASE
        )
        
        if not alta_menu_match:
            return menu_structure
        
        alta_menu_code = alta_menu_match.group(1)
        
        # Parsear líneas .Add
        # Formato: .Add "parent_key", "child_key", , "Caption", icon, shortcut_mask, shortcut_key
        add_pattern = r'\.Add\s+"([^"]*)",\s+"([^"]+)",\s+[^,]*,\s+"([^"]+)"(?:,\s+[^,]+)?(?:,\s+(\w+))?(?:,\s+(\w+))?'
        
        matches = re.finditer(add_pattern, alta_menu_code)
        
        for match in matches:
            parent_key = match.group(1)  # Puede ser "" para root
            child_key = match.group(2)
            caption = match.group(3)
            shortcut_mask = match.group(4)  # vbCtrlMask, vbShiftMask, etc.
            shortcut_key = match.group(5)   # vbKeyF3, vbKeyP, etc.
            
            # Parsear shortcut
            shortcut = None
            if shortcut_key:
                shortcut = self._parse_shortcut(shortcut_mask, shortcut_key)
            
            menu_structure[child_key] = {
                'caption': caption,
                'parent': parent_key if parent_key else None,
                'shortcut': shortcut
            }
        
        return menu_structure
    
    def _parse_shortcut(self, mask: Optional[str], key: Optional[str]) -> Optional[str]:
        """Convierte vbKeyF3, vbCtrlMask+vbKeyP a formato legible"""
        if not key:
            return None
        
        # Mapeo de keys
        key_mapping = {
            'vbKeyF2': 'F2',
            'vbKeyF3': 'F3',
            'vbKeyF4': 'F4',
            'vbKeyF5': 'F5',
            'vbKeyF6': 'F6',
            'vbKeyF8': 'F8',
            'vbKeyF9': 'F9',
            'vbKeyF10': 'F10',
            'vbKeyF11': 'F11',
            'vbKeyP': 'P',
            'vbKeyC': 'C',
            'vbKeyA': 'A',
            'vbKeyV': 'V',
            'vbKeyB': 'B',
            'vbKeyR': 'R',
            'vbKeyS': 'S',
            'vbKeyEscape': 'Esc'
        }
        
        key_str = key_mapping.get(key, key)
        
        # Agregar modificador
        if mask:
            if 'Ctrl' in mask:
                return f'Ctrl+{key_str}'
            elif 'Shift' in mask:
                return f'Shift+{key_str}'
        
        return key_str
    
    def _build_menu_path(self, menu_structure: Dict, target_key: str) -> str:
        """Construye la ruta completa del menú (Ventas → Pedido)"""
        path = []
        current_key = target_key
        
        # Recorrer hacia arriba hasta el root
        while current_key and current_key in menu_structure:
            menu_info = menu_structure[current_key]
            path.insert(0, menu_info['caption'])
            current_key = menu_info.get('parent')
        
        return ' → '.join(path)
    
    def _find_procedure_for_key(self, content: str, menu_key: str) -> Optional[str]:
        """
        Encuentra el procedimiento que se ejecuta al hacer clic en un menú
        
        Args:
            content: Contenido de Principal.frm
            menu_key: Key del menú (ej: "keyPed")
        
        Returns:
            Nombre del procedimiento (ej: "Menu_Pedido_Venta")
        """
        # Buscar en Menu_Click o MenuPrincipal_Click
        # Patrón: Case "keyPed" → Menu_Pedido_Venta
        
        case_pattern = rf'Case\s+"{menu_key}".*?(\w+)\s*(?:\(|$)'
        
        matches = re.finditer(case_pattern, content, re.DOTALL | re.IGNORECASE)
        
        for match in matches:
            # Buscar el procedimiento en las siguientes líneas
            window = content[match.start():match.start()+500]
            
            # Buscar llamadas a procedimientos
            proc_pattern = r'(Menu_\w+|ABM\w+\.Show|\w+\.Show)'
            proc_matches = re.findall(proc_pattern, window)
            
            if proc_matches:
                procedure = proc_matches[0]
                # Limpiar .Show
                procedure = procedure.replace('.Show', '')
                return procedure
        
        return None
    
    def get_all_menu_structure(self) -> Dict:
        """
        Obtiene la estructura completa de menús
        
        Returns:
            Dict con toda la jerarquía de menús
        """
        principal_file = Path(self.vb6_root_path) / 'Formularios' / 'Principal.frm'
        
        if not principal_file.exists():
            return {}
        
        try:
            with open(principal_file, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
        except:
            return {}
        
        return self._parse_menu_structure(content)

