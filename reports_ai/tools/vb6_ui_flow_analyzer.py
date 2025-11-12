"""
Analizador de Flujo de Interacción de Usuario en Formularios VB6

Extrae el procedimiento desde la perspectiva del USUARIO FINAL,
sin exponer detalles técnicos (tablas, campos, código).
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VB6UIFlowAnalyzer:
    """
    Analiza formularios VB6 para extraer el flujo de interacción del usuario
    
    Genera procedimientos en lenguaje natural tipo:
    - "Abre el formulario desde Ventas -> Pedidos"
    - "Completa el campo Cliente"
    - "Haz clic en Guardar"
    """
    
    def __init__(self, vb6_root_path: str = None):
        # Detectar si está en Docker o local
        import os
        if os.path.exists('/app/administraNET_Limpio'):
            self.vb6_root_path = vb6_root_path or '/app/administraNET_Limpio'
        else:
            self.vb6_root_path = vb6_root_path or '/Users/sebastian/Documents/Administranet/Proyectos/Synap/administraNET_Limpio'
        
        # Importar herramientas adicionales
        from .menu_analyzer import MenuAnalyzerTool
        from .navigation_flow_tool import NavigationFlowTool
        
        self.menu_analyzer = MenuAnalyzerTool(vb6_root_path)
        self.nav_flow = NavigationFlowTool(vb6_root_path)
    
    def extract_user_procedure(self, form_name: str, catalog_entry=None) -> Dict:
        """
        Extrae el procedimiento de usuario desde un formulario VB6
        USANDO ANÁLISIS REAL del código (menú, navegación, auxiliares)
        
        Args:
            form_name: Nombre del formulario (ej: Pedido.frm)
            catalog_entry: Entrada del catálogo (opcional)
        
        Returns:
            Dict con el procedimiento para usuario final
        """
        logger.info(f"[UIFlowAnalyzer] Extrayendo flujo de usuario REAL: {form_name}")
        
        # Limpiar nombre (quitar .frm si existe)
        clean_form_name = form_name.replace('.frm', '')
        
        # 1. BUSCAR RUTA DEL MENÚ REAL
        menu_info = self.menu_analyzer.find_menu_path_for_form(clean_form_name)
        
        if menu_info:
            logger.info(f"[UIFlowAnalyzer] Ruta de menú encontrada: {menu_info['menu_path']}")
            menu_path = menu_info['menu_path']
            shortcut = menu_info.get('shortcut')
            procedure_name = menu_info.get('procedure')
        else:
            logger.warning(f"[UIFlowAnalyzer] No se encontró ruta de menú, usando heurística")
            module = catalog_entry.module if catalog_entry else self._infer_module(form_name)
            menu_path = f"{module} → {clean_form_name}"
            shortcut = None
            procedure_name = None
        
        # 2. TRAZAR FLUJO DE NAVEGACIÓN COMPLETO
        navigation_flow = []
        if procedure_name:
            navigation_flow = self.nav_flow.trace_navigation_flow(procedure_name)
            logger.info(f"[UIFlowAnalyzer] Flujo de navegación: {len(navigation_flow)} pasos")
        
        # 3. ANALIZAR FORMULARIO PRINCIPAL
        file_path = self._find_file(form_name)
        
        if not file_path:
            logger.warning(f"[UIFlowAnalyzer] No se encontró: {form_name}")
            return None
        
        try:
            with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"[UIFlowAnalyzer] Error leyendo {file_path}: {e}")
            return None
        
        # Extraer información del formulario
        form_caption = self._extract_form_caption(content)
        tabs = self._extract_tabs(content)
        input_fields = self._extract_input_fields(content)
        buttons = self._extract_buttons(content)
        grids = self._extract_grids(content)
        
        # Detectar formularios auxiliares llamados
        auxiliary_forms = self._detect_auxiliary_forms(content)
        
        # 4. GENERAR PASOS DEL PROCEDIMIENTO (con info REAL)
        steps = self._generate_user_steps_real(
            form_caption,
            menu_path,
            shortcut,
            navigation_flow,
            tabs,
            input_fields,
            buttons,
            grids,
            auxiliary_forms,
            catalog_entry
        )
        
        result = {
            'form_name': form_name,
            'form_caption': form_caption,
            'module': catalog_entry.module if catalog_entry else self._infer_module(form_name),
            'menu_path': menu_path,
            'shortcut': shortcut,
            'navigation_flow': navigation_flow,
            'steps': steps,
            'tabs': tabs,
            'main_fields': [f['label'] for f in input_fields[:10]],
            'main_buttons': [b['caption'] for b in buttons if b['caption']],
            'auxiliary_forms': auxiliary_forms,
            'has_detail_grid': len(grids) > 0
        }
        
        return result
    
    def _detect_auxiliary_forms(self, content: str) -> List[Dict]:
        """Detecta formularios auxiliares y su propósito"""
        auxiliary = []
        
        # Patrón: FormName.Show
        show_pattern = r'(\w+)\.Show'
        
        matches = re.finditer(show_pattern, content, re.IGNORECASE)
        
        seen_forms = set()
        
        for match in matches:
            form_name = match.group(1)
            
            # Filtrar controles y formularios comunes
            if (form_name not in ['Info', 'form_espera', 'Menu_Contextual', 'Avisos'] and 
                not form_name.startswith('rs_') and
                form_name not in seen_forms):
                
                seen_forms.add(form_name)
                
                # Inferir propósito
                purpose = self._infer_auxiliary_purpose(form_name)
                
                auxiliary.append({
                    'name': form_name,
                    'purpose': purpose
                })
        
        return auxiliary
    
    def _infer_auxiliary_purpose(self, form_name: str) -> str:
        """Infiere el propósito de un formulario auxiliar"""
        name_lower = form_name.lower()
        
        if 'articulo' in name_lower and ('lista' in name_lower or not 'carga' in name_lower):
            return 'Búsqueda y selección de artículos'
        
        if 'carga' in name_lower and 'datos' in name_lower:
            return 'Carga de datos adicionales (entrega, transporte, etc.)'
        
        if 'clave' in name_lower or 'supervisor' in name_lower:
            return 'Solicitud de permisos de supervisor'
        
        if 'viajante' in name_lower or 'vendedor' in name_lower:
            return 'Selección de vendedor'
        
        if 'ctacte' in name_lower or 'cuenta' in name_lower:
            return 'Consulta de cuenta corriente'
        
        if 'stock' in name_lower:
            return 'Consulta de stock disponible'
        
        if 'cliente' in name_lower and 'ocasional' in name_lower:
            return 'Alta rápida de cliente ocasional'
        
        if 'proyecto' in name_lower:
            return 'Selección o gestión de proyectos'
        
        if 'cotiza' in name_lower:
            return 'Cotizador de precios'
        
        return form_name
    
    def _extract_form_caption(self, content: str) -> str:
        """Extrae el caption del formulario"""
        match = re.search(r'Begin VB\.Form \w+\s+.*?Caption\s*=\s*"([^"]+)"', content, re.DOTALL)
        if match:
            return match.group(1).strip()
        return "Formulario"
    
    def _extract_tabs(self, content: str) -> List[Dict]:
        """Extrae las pestañas/tabs del formulario"""
        tabs = []
        
        # Buscar TabStrip o vaTabPro
        tab_pattern = r'Begin\s+(TabproLib\.vaTabPro|SSTabCtlLib\.SSTab|TabDlg\.SSTab)\s+(\w+)'
        
        matches = re.finditer(tab_pattern, content)
        
        for match in matches:
            control_name = match.group(2)
            
            # Buscar TabCount
            tab_count_pattern = rf'{control_name}.*?TabCount\s*=\s*(\d+)'
            tab_count_match = re.search(tab_count_pattern, content[match.start():match.start()+5000], re.DOTALL)
            
            if tab_count_match:
                tab_count = int(tab_count_match.group(1))
                
                # Buscar captions de tabs (pueden estar en TabCaption)
                # Por ahora inferimos nombres comunes
                if tab_count >= 2:
                    tabs.append({'name': 'Datos Generales', 'order': 1})
                    tabs.append({'name': 'Artículos / Detalle', 'order': 2})
                
                if tab_count >= 3:
                    tabs.append({'name': 'Datos Adicionales', 'order': 3})
        
        return tabs
    
    def _extract_input_fields(self, content: str) -> List[Dict]:
        """Extrae campos de entrada y sus etiquetas"""
        fields = []
        
        # Buscar Labels seguidos de TextBox o ComboBox
        label_pattern = r'Begin VB\.Label (\w+)\s+.*?Caption\s*=\s*"([^"]+)"'
        
        label_matches = list(re.finditer(label_pattern, content, re.DOTALL))
        
        for match in label_matches[:30]:  # Máximo 30 labels
            label_name = match.group(1)
            label_caption = match.group(2).strip()
            
            # Filtrar labels que parecen campos de entrada
            if label_caption and len(label_caption) < 50 and ':' in label_caption:
                # Limpiar caption (quitar ":")
                clean_caption = label_caption.replace(':', '').strip()
                
                # Inferir si es obligatorio (heurística)
                is_required = any(keyword in clean_caption.lower() for keyword in ['cliente', 'fecha', 'sucursal', 'vendedor'])
                
                fields.append({
                    'label': clean_caption,
                    'control_name': label_name,
                    'required': is_required,
                    'type': 'input'
                })
        
        return fields
    
    def _extract_buttons(self, content: str) -> List[Dict]:
        """Extrae botones visibles"""
        buttons = []
        
        # Buscar botones OsenXPButton o CommandButton
        button_pattern = r'Begin\s+(OsenXPCntrl\.OsenXPButton|VB\.CommandButton)\s+(\w+)'
        
        matches = re.finditer(button_pattern, content)
        
        for match in matches:
            button_name = match.group(2)
            
            # Buscar ToolTipText o Caption cerca del botón
            window = content[match.start():match.start()+1000]
            
            tooltip_match = re.search(r'ToolTipText\s*=\s*"([^"]+)"', window)
            caption_match = re.search(r'Caption\s*=\s*"([^"]+)"', window)
            
            button_caption = None
            
            if tooltip_match:
                button_caption = tooltip_match.group(1).strip()
            elif caption_match:
                button_caption = caption_match.group(1).strip()
            
            # Mapear nombres técnicos a nombres de usuario
            if not button_caption:
                button_caption = self._button_name_to_caption(button_name)
            
            if button_caption:
                buttons.append({
                    'name': button_name,
                    'caption': button_caption,
                    'order': len(buttons) + 1
                })
        
        return buttons
    
    def _button_name_to_caption(self, button_name: str) -> str:
        """Mapea nombres técnicos de botones a captions para usuario"""
        mappings = {
            'Modificar': 'Modificar',
            'Eliminar': 'Eliminar',
            'ListaArticulos': 'Lista de Artículos',
            'Importar': 'Importar',
            'AceptarStock': 'Aceptar',
            'Lista_Proyecto': 'Seleccionar Proyecto',
            'VisCtaCte': 'Ver Cuenta Corriente',
            'Lista_Informes': 'Informes'
        }
        
        return mappings.get(button_name, button_name)
    
    def _extract_grids(self, content: str) -> List[Dict]:
        """Extrae grillas de detalle"""
        grids = []
        
        # Buscar TrueOleDBGrid o MSFlexGrid
        grid_pattern = r'Begin\s+(TrueOleDBGrid\w+\.TDBGrid|MSDataGridLib\.DataGrid|MSFlexGridLib\.MSFlexGrid)\s+(\w+)'
        
        matches = re.finditer(grid_pattern, content)
        
        for match in matches:
            grid_name = match.group(2)
            
            # Inferir propósito de la grilla
            purpose = "detalle de artículos" if "stock" in grid_name.lower() or "cuerpo" in grid_name.lower() else "listado"
            
            grids.append({
                'name': grid_name,
                'purpose': purpose
            })
        
        return grids
    
    def _infer_module(self, form_name: str) -> str:
        """Infiere el módulo desde el nombre del formulario"""
        mappings = {
            'Pedido': 'Ventas',
            'Factura': 'Ventas',
            'Presupuesto': 'Ventas',
            'Remito': 'Ventas',
            'Cliente': 'Clientes',
            'Articulo': 'Stock',
            'MovStock': 'Stock',
            'Proveedor': 'Compras',
            'Cobro': 'Cobranzas',
            'Pago': 'Pagos'
        }
        
        for key, module in mappings.items():
            if key.lower() in form_name.lower():
                return module
        
        return "Sistema"
    
    def _generate_user_steps(
        self,
        form_caption: str,
        menu_path: str,
        tabs: List[Dict],
        input_fields: List[Dict],
        buttons: List[Dict],
        grids: List[Dict],
        catalog_entry
    ) -> List[str]:
        """Genera los pasos del procedimiento para usuario final"""
        steps = []
        
        # Paso 1: Abrir formulario
        steps.append(f"Desde el menú principal, selecciona: **{menu_path}**")
        
        # Paso 2: Si hay tabs, mencionar la primera pestaña
        if tabs:
            steps.append(f"En la pestaña **'{tabs[0]['name']}'**, completa los siguientes datos:")
        else:
            steps.append("Completa los siguientes datos:")
        
        # Paso 3: Campos obligatorios
        required_fields = [f for f in input_fields if f.get('required')]
        if required_fields:
            for field in required_fields[:5]:
                steps.append(f"   • **{field['label']}**: Selecciona o ingresa el valor correspondiente")
        else:
            # Si no detectamos required, mostrar los primeros campos
            for field in input_fields[:5]:
                steps.append(f"   • **{field['label']}**: Ingresa el valor")
        
        # Paso 4: Si hay más tabs (generalmente para detalle de artículos)
        if len(tabs) >= 2:
            steps.append(f"Dirígete a la pestaña **'{tabs[1]['name']}'** para agregar los productos o ítems")
        elif grids:
            steps.append("En la sección de artículos o detalle:")
        
        # Paso 5: Agregar items (si hay grilla)
        if grids:
            steps.append("   • Haz clic en **'Agregar'** o **'Nuevo'** para cada producto que desees incluir")
            steps.append("   • Completa: Artículo, Cantidad, Precio, Descuento")
            steps.append("   • Repite para cada producto")
        
        # Paso 6: Revisión
        steps.append("Revisa que todos los datos estén correctos")
        
        # Paso 7: Si hay validaciones conocidas (del catálogo)
        if catalog_entry and catalog_entry.validations:
            steps.append(f"**IMPORTANTE**: El sistema validará automáticamente:")
            validations = [v.strip() for v in catalog_entry.validations.split(',')][:3]
            for val in validations:
                steps.append(f"   ✓ {val}")
        
        # Paso 8: Guardar
        save_button = next((b for b in buttons if 'guardar' in b['caption'].lower() or 'aceptar' in b['caption'].lower()), None)
        
        if save_button:
            steps.append(f"Haz clic en el botón **'{save_button['caption']}'** para guardar")
        else:
            steps.append("Haz clic en **'Guardar'** o **'Aceptar'** para confirmar")
        
        # Paso 9: Confirmación
        steps.append("El sistema procesará la información y mostrará un mensaje de confirmación")
        
        return steps
    
    def _generate_user_steps_real(
        self,
        form_caption: str,
        menu_path: str,
        shortcut: Optional[str],
        navigation_flow: List[Dict],
        tabs: List[Dict],
        input_fields: List[Dict],
        buttons: List[Dict],
        grids: List[Dict],
        auxiliary_forms: List[Dict],
        catalog_entry
    ) -> str:
        """
        Genera procedimiento en lenguaje NATURAL con información REAL
        
        Returns:
            String en markdown con lenguaje humano
        """
        lines = []
        
        # Introducción
        lines.append(f"Para crear un nuevo {form_caption.lower()} en administraNET, sigue estos pasos:")
        lines.append("")
        
        # PASO 1: Acceso al módulo
        lines.append("## Acceso al módulo")
        lines.append("")
        
        shortcut_text = f", o simplemente presiona **{shortcut}**" if shortcut else ""
        lines.append(f"Desde el menú principal, dirígete a {menu_path}{shortcut_text}.")
        lines.append("")
        
        # Si hay flujo de navegación intermedia (ej: lista de clientes)
        if navigation_flow:
            intermediate_forms = [f for f in navigation_flow if f['type'] == 'intermediate_form']
            
            if intermediate_forms:
                inter_form = intermediate_forms[0]
                lines.append(f"Esto abrirá una ventana donde verás {inter_form['purpose'].lower()}.")
            else:
                lines.append(f"Se abrirá directamente el formulario de {form_caption.lower()}.")
        
        lines.append("")
        
        # PASO 2: Selección previa (si aplica - ej: seleccionar cliente)
        if navigation_flow and any('lista' in f['purpose'].lower() or 'cliente' in f['purpose'].lower() for f in navigation_flow if f['type'] == 'intermediate_form'):
            lines.append("## Selecciona el cliente")
            lines.append("")
            lines.append(f"Busca el cliente para quien vas a crear el {form_caption.lower()}. Puedes usar la barra de búsqueda o desplazarte por la lista. Una vez lo encuentres, haz clic sobre él para seleccionarlo.")
            lines.append("")
            
            # Si hay que hacer clic en un menú interno
            if navigation_flow:
                lines.append(f"## Inicia el {form_caption.lower()}")
                lines.append("")
                lines.append(f"Con el cliente seleccionado, ve al menú interno del formulario y elige la opción \"{form_caption}\".")
                lines.append("")
                lines.append(f"Se abrirá el formulario de {form_caption.lower()} con la información del cliente y su vendedor asignado ya cargada automáticamente.")
                lines.append("")
        
        # PASO 3: Completar datos básicos
        lines.append("## Completa los datos básicos")
        lines.append("")
        
        if navigation_flow and 'cliente' in str(navigation_flow).lower():
            lines.append("Revisa que el cliente y vendedor sean correctos. Estos datos ya vienen pre-cargados, pero puedes modificarlos si es necesario.")
        else:
            # Listar campos principales
            main_fields = [f for f in input_fields if f.get('required')][:4]
            if main_fields:
                lines.append("Completa los siguientes campos:")
                for field in main_fields:
                    lines.append(f"- **{field['label']}**")
            else:
                lines.append("Completa los datos solicitados en el formulario.")
        
        lines.append("")
        lines.append(f"Verifica la fecha del {form_caption.lower()} (por defecto será la fecha actual).")
        lines.append("")
        
        # PASO 4: Datos adicionales (si existe el formulario auxiliar)
        if any('datos' in aux['purpose'].lower() and 'adicional' in aux['purpose'].lower() for aux in auxiliary_forms):
            lines.append("## Agrega datos de entrega (opcional)")
            lines.append("")
            lines.append("Si necesitas especificar información sobre la entrega, haz clic en el botón \"Datos Adicionales\".")
            lines.append("")
            lines.append("Aquí podrás indicar:")
            lines.append("- El transporte o empresa de logística")
            lines.append("- La fecha de entrega acordada")
            lines.append("- Observaciones o instrucciones especiales")
            lines.append("")
            lines.append("Cuando termines, confirma con \"Aceptar\".")
            lines.append("")
        
        # PASO 5: Agregar artículos/items
        if grids or any('articulo' in aux['name'].lower() for aux in auxiliary_forms):
            lines.append("## Carga los artículos")
            lines.append("")
            lines.append("Ahora viene la parte principal: agregar los productos al pedido.")
            lines.append("")
            
            # Buscar botón de agregar
            add_button = next((b for b in buttons if 'agregar' in b['caption'].lower()), None)
            add_text = f"Haz clic en \"{add_button['caption']}\"" if add_button else "Haz clic en \"Agregar\""
            
            lines.append(f"{add_text} o presiona **F2**. Se abrirá una ventana donde podrás buscar el artículo que necesitas.")
            lines.append("")
            lines.append("Para cada artículo:")
            lines.append("- Búscalo por código o nombre")
            lines.append("- Selecciónalo")
            lines.append("- Indica la cantidad que el cliente solicita")
            lines.append("- Revisa el precio (el sistema lo trae automáticamente según la lista del cliente)")
            lines.append("- Aplica un descuento si corresponde")
            lines.append("")
            lines.append(f"Confirma con \"Aceptar\" y el artículo se agregará a la grilla del {form_caption.lower()}.")
            lines.append("")
            lines.append("Repite este proceso para cada producto que incluyas.")
            lines.append("")
        
        # PASO 6: Permisos especiales (si existe)
        if any('supervisor' in aux['purpose'].lower() or 'permiso' in aux['purpose'].lower() for aux in auxiliary_forms):
            lines.append("## Permisos especiales")
            lines.append("")
            lines.append("Si en algún momento necesitas aplicar un descuento mayor al permitido para tu usuario, o modificar un precio por debajo del costo, el sistema te pedirá que ingreses una clave de supervisor.")
            lines.append("")
        
        # PASO 7: Revisión
        lines.append("## Revisa antes de guardar")
        lines.append("")
        lines.append("Antes de confirmar, tómate un momento para revisar:")
        lines.append("- Que todos los artículos estén correctos")
        lines.append("- Las cantidades y precios")
        lines.append("- Los totales calculados")
        lines.append("")
        lines.append("El sistema te mostrará advertencias automáticamente si detecta algo fuera de lo normal, como por ejemplo:")
        
        # Validaciones del catálogo si existen
        if catalog_entry and catalog_entry.validations:
            validations = [v.strip() for v in catalog_entry.validations.split(',')][:3]
            for val in validations:
                lines.append(f"• {val}")
        else:
            lines.append("• Si el cliente está excediendo su límite de crédito disponible")
            lines.append("• Si no hay stock suficiente para algún artículo")
            lines.append("• Si hay algún error en los datos ingresados")
        
        lines.append("")
        
        # PASO 8: Guardar
        lines.append("## Guarda el pedido")
        lines.append("")
        lines.append("Cuando todo esté listo, haz clic en \"Guardar\" o presiona **F10**.")
        lines.append("")
        lines.append("El sistema realizará las siguientes validaciones finales:")
        lines.append(f"- Que el {form_caption.lower()} incluya al menos un artículo")
        lines.append("- Que el importe total sea mayor a cero")
        
        if catalog_entry and catalog_entry.validations:
            lines.append(f"- Que no se superen los límites establecidos")
        
        lines.append("")
        lines.append(f"Si todo está correcto, el {form_caption.lower()} se guardará.")
        lines.append("")
        
        # PASO 9: Confirmación
        lines.append("## Confirmación")
        lines.append("")
        lines.append("Una vez guardado exitosamente:")
        lines.append(f"- El sistema generará y asignará un número único al {form_caption.lower()}")
        
        if 'pedido' in form_caption.lower():
            lines.append("- Actualizará el stock reservado de los artículos")
        
        lines.append("- Te mostrará un mensaje de confirmación")
        lines.append("- Tendrás la opción de imprimir el comprobante si lo necesitas")
        lines.append("")
        lines.append(f"Y listo, tu {form_caption.lower()} quedó registrado en el sistema.")
        
        # Atajos útiles
        if shortcut or any('F' in b.get('caption', '') for b in buttons):
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append("Atajos de teclado que te pueden ayudar:")
            if shortcut:
                lines.append(f"- **{shortcut}**: Acceder al módulo de {form_caption}")
            lines.append("- **F2**: Agregar un nuevo artículo")
            lines.append("- **F3**: Modificar un artículo ya agregado")
            lines.append("- **F4**: Eliminar un artículo de la lista")
            lines.append("- **F10**: Guardar el pedido")
        
        return '\n'.join(lines)
    
    def generate_user_manual_text(self, ui_flow: Dict) -> str:
        """
        Genera texto en lenguaje natural para manual de usuario
        
        Args:
            ui_flow: Resultado de extract_user_procedure
        
        Returns:
            String formateado para usuario final (ya viene en markdown)
        """
        # El texto ya viene generado en el formato correcto desde extract_user_procedure
        # que usa _generate_user_steps_real()
        
        if isinstance(ui_flow.get('steps'), str):
            # Ya es el texto completo
            return ui_flow['steps']
        else:
            # Fallback: generar formato básico
            lines = []
            lines.append(f"Para {ui_flow['form_caption'].lower()}, sigue estos pasos desde el menú: {ui_flow['menu_path']}")
            return "\n".join(lines)
    
    def _find_file(self, filename: str) -> Optional[Path]:
        """Busca un archivo VB6 en el directorio raíz"""
        root = Path(self.vb6_root_path)
        
        # Buscar en Formularios primero
        formularios_path = root / 'Formularios' / filename
        if formularios_path.exists():
            return formularios_path
        
        # Buscar en Modulos
        modulos_path = root / 'Modulos' / filename
        if modulos_path.exists():
            return modulos_path
        
        # Buscar recursivamente
        for file_path in root.rglob(filename):
            return file_path
        
        return None

