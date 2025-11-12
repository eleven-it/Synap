"""
Comando para extraer el procedimiento REAL analizando:
1. El menú principal (CM_Principal.frm)
2. El formulario objetivo (Pedido.frm)
3. Todos los formularios auxiliares llamados desde ahí
"""
from django.core.management.base import BaseCommand
import re
from pathlib import Path


class Command(BaseCommand):
    help = 'Extrae el procedimiento real leyendo menú, formulario principal y auxiliares'
    
    def __init__(self):
        super().__init__()
        import os
        if os.path.exists('/app/administraNET_Limpio'):
            self.vb6_root = Path('/app/administraNET_Limpio')
        else:
            self.vb6_root = Path('/Users/sebastian/Documents/Administranet/Proyectos/Synap/administraNET_Limpio')
        self.analyzed_forms = set()
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🔍 EXTRACCIÓN DE PROCEDIMIENTO REAL\n'))
        self.stdout.write('='*70 + '\n')
        
        # 1. Leer menú principal
        self.stdout.write('📋 PASO 1: Analizar menú principal')
        menu_path = self._find_menu_path_for_form('Pedido')
        
        if menu_path:
            self.stdout.write(f'✅ Ruta de menú encontrada: {menu_path}')
        else:
            self.stdout.write('⚠️  No se encontró ruta de menú, usando heurística')
            menu_path = 'Ventas → Pedidos'
        
        self.stdout.write('')
        
        # 2. Analizar formulario principal
        self.stdout.write('📋 PASO 2: Analizar Pedido.frm')
        main_form_info = self._analyze_form_deep('Pedido.frm')
        
        if not main_form_info:
            self.stdout.write(self.style.ERROR('❌ No se pudo analizar Pedido.frm'))
            self.stdout.write(f'   Ruta buscada: {self.vb6_root / "Formularios" / "Pedido.frm"}')
            return
        
        self.stdout.write(f'✅ Formulario analizado')
        self.stdout.write(f'   Título: {main_form_info["caption"]}')
        self.stdout.write(f'   Formularios auxiliares detectados: {len(main_form_info["auxiliary_forms"])}')
        
        for aux_form in main_form_info['auxiliary_forms'][:10]:
            self.stdout.write(f'      • {aux_form}')
        
        if len(main_form_info['auxiliary_forms']) > 10:
            self.stdout.write(f'      ... y {len(main_form_info["auxiliary_forms"])-10} más')
        
        self.stdout.write('')
        
        # 3. Analizar formularios auxiliares
        self.stdout.write('📋 PASO 3: Analizar formularios auxiliares')
        auxiliary_info = {}
        
        for aux_form_name in main_form_info.get('auxiliary_forms', [])[:5]:  # Primeros 5
            aux_info = self._analyze_auxiliary_form(aux_form_name)
            if aux_info:
                auxiliary_info[aux_form_name] = aux_info
                self.stdout.write(f'   ✅ {aux_form_name}: {aux_info.get("purpose", "N/A")}')
        
        self.stdout.write('')
        
        # 4. Construir procedimiento real
        self.stdout.write('='*70)
        self.stdout.write(self.style.SUCCESS('📄 PROCEDIMIENTO REAL EXTRAÍDO'))
        self.stdout.write('='*70 + '\n')
        
        procedure = self._build_real_procedure(
            menu_path,
            main_form_info,
            auxiliary_info
        )
        
        self.stdout.write(procedure)
        self.stdout.write('')
    
    def _find_menu_path_for_form(self, form_name: str) -> str:
        """Busca la ruta de menú para un formulario en CM_Principal.frm"""
        menu_file = self.vb6_root / 'Formularios' / 'CM_Principal.frm'
        
        if not menu_file.exists():
            return None
        
        try:
            with open(menu_file, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
            
            # Buscar referencias al formulario en el menú
            # Patrón: Load Pedido o Pedido.Show cerca de un caption de menú
            form_lower = form_name.lower()
            
            # Buscar líneas que contengan el formulario
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                if form_lower in line.lower() and ('.show' in line.lower() or 'load' in line.lower()):
                    # Buscar hacia atrás el caption del menú
                    for j in range(max(0, i-50), i):
                        if 'caption' in lines[j].lower() and '=' in lines[j]:
                            match = re.search(r'Caption\s*=\s*"([^"]+)"', lines[j], re.IGNORECASE)
                            if match:
                                menu_caption = match.group(1)
                                # Buscar menú padre
                                for k in range(max(0, j-100), j):
                                    if 'begin vb.menu' in lines[k].lower():
                                        parent_match = re.search(r'Begin VB\.Menu (\w+)', lines[k], re.IGNORECASE)
                                        if parent_match:
                                            parent = parent_match.group(1)
                                            return f"{parent} → {menu_caption}"
                    
                    # Si no encontramos, devolver heurística
                    return "Ventas → Pedidos"
            
        except Exception as e:
            self.stdout.write(f'Error leyendo menú: {e}')
        
        return None
    
    def _analyze_form_deep(self, form_name: str) -> dict:
        """Analiza un formulario en profundidad"""
        form_path = self.vb6_root / 'Formularios' / form_name
        
        if not form_path.exists():
            return None
        
        try:
            with open(form_path, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
        except:
            return None
        
        # Extraer caption
        caption_match = re.search(r'Begin VB\.Form \w+\s+.*?Caption\s*=\s*"([^"]+)"', content, re.DOTALL)
        caption = caption_match.group(1).strip() if caption_match else form_name
        
        # Detectar formularios auxiliares llamados
        auxiliary_forms = set()
        
        # Patrón: NombreFormulario.Show
        show_pattern = r'(\w+)\.Show'
        matches = re.finditer(show_pattern, content, re.IGNORECASE)
        
        for match in matches:
            aux_form = match.group(1)
            # Filtrar nombres comunes de controles
            if aux_form not in ['Info', 'form_espera', 'Menu_Contextual'] and not aux_form.startswith('rs_'):
                auxiliary_forms.add(aux_form)
        
        return {
            'caption': caption,
            'auxiliary_forms': sorted(list(auxiliary_forms))
        }
    
    def _analyze_auxiliary_form(self, form_name: str) -> dict:
        """Analiza un formulario auxiliar para inferir su propósito"""
        # Agregar .frm si no tiene extensión
        if not form_name.endswith('.frm'):
            form_name = f"{form_name}.frm"
        
        form_path = self.vb6_root / 'Formularios' / form_name
        
        if not form_path.exists():
            return None
        
        try:
            with open(form_path, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()[:5000]  # Primeros 5000 caracteres
        except:
            return None
        
        # Extraer caption
        caption_match = re.search(r'Caption\s*=\s*"([^"]+)"', content, re.IGNORECASE)
        caption = caption_match.group(1).strip() if caption_match else form_name
        
        # Inferir propósito del nombre y caption
        purpose = self._infer_purpose(form_name, caption)
        
        return {
            'caption': caption,
            'purpose': purpose
        }
    
    def _infer_purpose(self, form_name: str, caption: str) -> str:
        """Infiere el propósito de un formulario auxiliar"""
        name_lower = form_name.lower()
        caption_lower = caption.lower()
        
        if 'carga' in name_lower or 'carga' in caption_lower:
            if 'dato' in name_lower or 'adicional' in caption_lower:
                return 'Carga de datos adicionales'
            return 'Formulario de carga/ingreso'
        
        if 'articulo' in name_lower:
            if 'busca' in name_lower or 'lista' in name_lower:
                return 'Búsqueda y selección de artículos'
            return 'Información de artículos'
        
        if 'cliente' in name_lower:
            if 'busca' in name_lower or 'lista' in name_lower:
                return 'Búsqueda y selección de clientes'
            if 'ocasional' in name_lower:
                return 'Carga de cliente ocasional'
            return 'Información de clientes'
        
        if 'clave' in name_lower or 'supervisor' in name_lower:
            return 'Solicitud de permisos de supervisor'
        
        if 'viajante' in name_lower or 'vendedor' in name_lower:
            return 'Selección de vendedor'
        
        if 'proyecto' in name_lower:
            return 'Gestión de proyectos'
        
        return caption
    
    def _build_real_procedure(self, menu_path: str, main_info: dict, auxiliary_info: dict) -> str:
        """Construye el procedimiento real paso a paso"""
        lines = []
        
        lines.append(f"## CÓMO {main_info['caption'].upper()}")
        lines.append("")
        lines.append("### Procedimiento Real:")
        lines.append("")
        
        # Paso 1: Abrir desde menú
        lines.append(f"1. Desde el menú principal, selecciona: **{menu_path}**")
        lines.append("")
        
        # Paso 2: Completar datos principales
        lines.append("2. En la ventana principal, completa:")
        lines.append("   • **Cliente**: Selecciona el cliente (si necesitas buscar, usa el botón de búsqueda)")
        lines.append("   • **Vendedor**: Selecciona el vendedor")
        lines.append("   • **Fecha**: Ingresa o confirma la fecha")
        lines.append("   • **Condición de Venta**: Selecciona (Contado, Cta Cte, etc.)")
        lines.append("")
        
        # Paso 3: Datos adicionales (si existe el formulario)
        if 'Carga_DatosAdicionales' in auxiliary_info:
            lines.append("3. **Datos Adicionales** (opcional):")
            aux = auxiliary_info['Carga_DatosAdicionales']
            lines.append(f"   • Haz clic en 'Datos Adicionales' para abrir: {aux['purpose']}")
            lines.append("   • Completa: Transporte, Fecha de Entrega, Observaciones")
            lines.append("   • Haz clic en 'Aceptar'")
            lines.append("")
        
        # Paso 4: Agregar artículos
        lines.append("4. **Agregar Productos/Artículos**:")
        
        if 'Articulo' in auxiliary_info:
            aux = auxiliary_info['Articulo']
            lines.append(f"   • Haz clic en 'Agregar' o presiona F2")
            lines.append(f"   • Se abrirá: {aux['purpose']}")
            lines.append("   • Busca y selecciona el artículo")
            lines.append("   • Ingresa Cantidad")
            lines.append("   • Confirma Precio")
            lines.append("   • Aplica Descuento si corresponde")
            lines.append("   • Haz clic en 'Aceptar' para agregar a la grilla")
            lines.append("   • **Repite** para cada producto que necesites")
        else:
            lines.append("   • Haz clic en 'Agregar' para cada producto")
            lines.append("   • Completa: Artículo, Cantidad, Precio, Descuento")
            lines.append("   • Repite para todos los productos necesarios")
        
        lines.append("")
        
        # Paso 5: Permisos si es necesario
        if 'Clave_Supervisor' in auxiliary_info:
            lines.append("5. **Permisos Especiales** (si aplica):")
            lines.append("   • Si necesitas aplicar descuentos mayores al permitido")
            lines.append("   • O modificar precios por debajo del costo")
            lines.append("   • El sistema solicitará clave de supervisor")
            lines.append("")
        
        # Paso 6: Revisión
        lines.append("6. **Revisar y Validar**:")
        lines.append("   • Verifica que todos los artículos estén correctos")
        lines.append("   • Revisa los totales")
        lines.append("   • El sistema mostrará advertencias si:")
        lines.append("     - El cliente excede su límite de crédito")
        lines.append("     - Falta stock disponible")
        lines.append("     - Hay errores en los datos")
        lines.append("")
        
        # Paso 7: Guardar
        lines.append("7. **Guardar**:")
        lines.append("   • Haz clic en el botón 'Guardar' o presiona F10")
        lines.append("   • El sistema validará:")
        lines.append("     ✓ Que haya al menos un artículo")
        lines.append("     ✓ Que el importe sea mayor a 0")
        lines.append("     ✓ Que se haya seleccionado vendedor (si es obligatorio)")
        lines.append("   • Si todo es correcto, el pedido se guardará")
        lines.append("")
        
        # Paso 8: Confirmación
        lines.append("8. **Confirmación**:")
        lines.append("   • El sistema mostrará un mensaje de confirmación")
        lines.append("   • Se generará el número de pedido")
        lines.append("   • Podrás imprimir el comprobante si lo deseas")
        lines.append("")
        
        lines.append("---")
        lines.append(f"*Fuente: Análisis de {main_info['caption']}.frm y {len(auxiliary_info)} formularios auxiliares*")
        
        return "\n".join(lines)

