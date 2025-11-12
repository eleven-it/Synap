"""
Herramienta para analizar formularios VB6 y extraer mapas de persistencia
Infiere tablas, campos y relaciones basándose en controles UI y código de eventos
"""
import logging
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class VB6FormAnalyzer:
    """
    Analizador de formularios VB6 para inferir mapas de persistencia
    
    Responsabilidades:
    - Identificar formularios y sus entidades funcionales
    - Extraer controles UI y mapearlos a campos de BD candidatos
    - Detectar patrones maestro/detalle
    - Inferir relaciones entre tablas
    - Calcular scores de confianza
    """
    
    def __init__(self, vb6_path: Optional[Path] = None):
        """
        Inicializa el analizador
        
        Args:
            vb6_path: Ruta al directorio de código VB6
        """
        if vb6_path and isinstance(vb6_path, str):
            self.vb6_path = Path(vb6_path)
        elif vb6_path:
            self.vb6_path = vb6_path
        else:
            # Default: administraNET_Limpio
            project_root = Path(__file__).parent.parent.parent
            self.vb6_path = project_root / 'administraNET_Limpio'
        
        self.formularios_path = self.vb6_path / 'Formularios'
        self.modulos_path = self.vb6_path / 'Modulos'
        
        # Cache de análisis
        self._form_cache = {}
        self._persistence_map = {}
    
    def analyze_forms_for_intent(self, intent: str, category: str) -> Dict[str, Any]:
        """
        Analiza formularios VB6 relevantes para una intención de negocio
        
        Args:
            intent: Intención del usuario (ej: "consultar pedidos pendientes")
            category: Categoría funcional (ventas, inventario, clientes, etc.)
            
        Returns:
            Dict con mapa de persistencia y sugerencias de tablas/campos
        """
        logger.info(
            f"\n{'='*70}\n"
            f"[VB6FormAnalyzer] 🔍 ANÁLISIS DE FORMULARIOS\n"
            f"{'='*70}\n"
            f"  🎯 Intención: {intent}\n"
            f"  📂 Categoría: {category}\n"
            f"{'='*70}"
        )
        
        # Mapeo de categorías a formularios VB6 relevantes
        category_forms = self._get_relevant_forms(category)
        
        if not category_forms:
            logger.warning(f"[VB6FormAnalyzer] No se encontraron formularios para categoría: {category}")
            return self._empty_result()
        
        # Analizar cada formulario
        all_entities = []
        all_tables = []
        all_relations = []
        all_rules = []
        
        for form_file in category_forms:
            form_analysis = self._analyze_single_form(form_file)
            
            if form_analysis:
                all_entities.extend(form_analysis.get('entidades', []))
                all_tables.extend(form_analysis.get('tablas_sugeridas', []))
                all_relations.extend(form_analysis.get('relaciones_candidatas', []))
                all_rules.extend(form_analysis.get('reglas_funcionales', []))
        
        # Consolidar y eliminar duplicados
        result = self._consolidate_analysis(all_entities, all_tables, all_relations, all_rules)
        
        logger.info(
            f"[VB6FormAnalyzer] ✅ ANÁLISIS COMPLETADO\n"
            f"  📋 Formularios analizados: {len(category_forms)}\n"
            f"  🏷️  Entidades detectadas: {len(result['entidades_funcionales'])}\n"
            f"  🗄️  Tablas sugeridas: {len(result['tablas_sugeridas'])}\n"
            f"  🔗 Relaciones candidatas: {len(result['relaciones_candidatas'])}\n"
            f"  📚 Reglas funcionales: {len(result['reglas_funcionales_resumidas'])}"
        )
        
        return result
    
    def _get_relevant_forms(self, category: str) -> List[Path]:
        """
        Obtiene lista de formularios relevantes según la categoría funcional
        Escanea RECURSIVAMENTE todos los subdirectorios
        
        Args:
            category: Categoría funcional
            
        Returns:
            Lista de rutas a archivos .frm
        """
        # Mapeo de categorías a patrones de formularios
        category_patterns = {
            'ventas': ['venta', 'factura', 'comprobante', 'ticket', 'pedido'],
            'inventario': ['articulo', 'stock', 'producto', 'inventario'],
            'clientes': ['cliente', 'consumidor', 'comprador'],
            'cobranzas': ['cobranza', 'recibo', 'pago', 'cuenta_corriente'],
            'compras': ['compra', 'proveedor', 'orden'],
            'general': ['principal', 'menu', 'articulo', 'cliente'],
        }
        
        patterns = category_patterns.get(category.lower(), ['articulo'])
        
        # Buscar en directorio Formularios/ y también en raíz del proyecto
        search_paths = []
        
        # 1. Subdirectorio Formularios/
        if self.formularios_path.exists():
            search_paths.append(self.formularios_path)
        
        # 2. Directorio raíz de administraNET_Limpio
        if self.vb6_path.exists():
            search_paths.append(self.vb6_path)
        
        if not search_paths:
            logger.warning(f"[VB6FormAnalyzer] No existen directorios para escanear")
            return []
        
        # Buscar archivos .frm RECURSIVAMENTE que coincidan con los patrones
        relevant_forms = []
        
        for search_path in search_paths:
            # rglob busca recursivamente en subdirectorios
            for frm_file in search_path.rglob('*.frm'):
                # Verificar si coincide con algún patrón
                for pattern in patterns:
                    if pattern.lower() in frm_file.stem.lower():
                        relevant_forms.append(frm_file)
                        logger.debug(f"[VB6FormAnalyzer] Encontrado: {frm_file.relative_to(self.vb6_path)}")
                        break
        
        # Eliminar duplicados
        relevant_forms = list(set(relevant_forms))
        
        logger.info(
            f"[VB6FormAnalyzer] ✅ Encontrados {len(relevant_forms)} formularios para '{category}'\n"
            f"  📂 Escaneados: {len(search_paths)} directorios (recursivo)"
        )
        
        return relevant_forms  # SIN LÍMITE: analizar TODOS los formularios encontrados
    
    def _analyze_single_form(self, form_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analiza un formulario VB6 individual
        
        Args:
            form_path: Ruta al archivo .frm
            
        Returns:
            Dict con análisis del formulario
        """
        try:
            with open(form_path, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
            
            logger.debug(f"[VB6FormAnalyzer] Analizando: {form_path.name}")
            
            # Extraer nombre del formulario
            form_name = form_path.stem
            
            # 1. Detectar entidades de negocio (por caption del form)
            entity = self._infer_entity_from_form_name(form_name)
            
            # 2. Detectar tablas candidatas (por RecordSource, SQL en DataEnvironment)
            tables = self._extract_table_references(content, form_name)
            
            # 3. Detectar controles y mapearlos a campos
            controls = self._extract_controls(content)
            
            # 4. Enriquecer tablas con campos sugeridos
            enriched_tables = self._enrich_tables_with_controls(tables, controls)
            
            # 5. Detectar relaciones maestro/detalle
            relations = self._detect_master_detail_relations(content, enriched_tables)
            
            # 6. Extraer reglas funcionales de validaciones
            rules = self._extract_validation_rules(content, entity)
            
            return {
                'form_name': form_name,
                'entidades': [entity] if entity else [],
                'tablas_sugeridas': enriched_tables,
                'relaciones_candidatas': relations,
                'reglas_funcionales': rules
            }
            
        except Exception as e:
            logger.error(f"[VB6FormAnalyzer] Error analizando {form_path.name}: {e}")
            return None
    
    def _infer_entity_from_form_name(self, form_name: str) -> Optional[str]:
        """
        Infiere la entidad funcional del nombre del formulario
        
        Args:
            form_name: Nombre del formulario
            
        Returns:
            Entidad funcional (ej: "cliente", "articulo", "pedido")
        """
        form_lower = form_name.lower()
        
        # Mapeo de patrones a entidades
        entity_patterns = {
            'cliente': ['cliente', 'clientes', 'consumidor'],
            'articulo': ['articulo', 'producto', 'item'],
            'pedido': ['pedido', 'pedidos', 'orden'],
            'factura': ['factura', 'comprobante', 'venta'],
            'proveedor': ['proveedor', 'proveedores'],
            'stock': ['stock', 'movimiento', 'inventario'],
            'cobranza': ['cobranza', 'recibo', 'pago'],
        }
        
        for entity, patterns in entity_patterns.items():
            if any(p in form_lower for p in patterns):
                return entity
        
        return None
    
    def _extract_table_references(self, content: str, form_name: str) -> List[Dict[str, Any]]:
        """
        Extrae referencias a tablas del código VB6
        
        Args:
            content: Contenido del archivo .frm
            form_name: Nombre del formulario
            
        Returns:
            Lista de tablas candidatas con confianza
        """
        tables = []
        
        # Patrones para detectar tablas en VB6
        patterns = [
            r'RecordSource\s*=\s*"([^"]+)"',  # RecordSource en DataEnvironment
            r'FROM\s+(\w+)',  # FROM en SQL embebido
            r'INSERT\s+INTO\s+(\w+)',  # INSERT en código
            r'UPDATE\s+(\w+)',  # UPDATE en código
            r'\.Open\s+"SELECT\s+.*FROM\s+(\w+)',  # Recordset.Open con SELECT
        ]
        
        found_tables = set()
        
        for pattern in patterns:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                table_name = match.group(1).strip()
                # Filtrar palabras SQL y caracteres extraños
                if table_name and len(table_name) > 2 and not any(kw in table_name.upper() for kw in ['SELECT', 'WHERE', 'ORDER', '*']):
                    found_tables.add(table_name)
        
        # Calcular confianza inicial
        for table in found_tables:
            confidence = 0.5  # Base
            
            # +0.2 si el nombre de la tabla coincide con el formulario
            if table.lower() in form_name.lower() or form_name.lower() in table.lower():
                confidence += 0.2
            
            # +0.1 si aparece múltiples veces
            occurrences = len(re.findall(rf'\b{table}\b', content, re.IGNORECASE))
            if occurrences >= 3:
                confidence += 0.1
            elif occurrences >= 2:
                confidence += 0.05
            
            # Inferir rol funcional
            role = self._infer_table_role(table, form_name)
            
            tables.append({
                'nombre': table,
                'rol': role,
                'confianza': min(confidence, 1.0),
                'campos_clave_sugeridos': [],
                'origen': f'form_{form_name}'
            })
        
        return tables
    
    def _infer_table_role(self, table_name: str, form_name: str) -> str:
        """
        Infiere el rol funcional de una tabla
        
        Args:
            table_name: Nombre de la tabla
            form_name: Nombre del formulario
            
        Returns:
            Rol: maestro, detalle, catalogo, transaccional
        """
        table_lower = table_name.lower()
        
        if 'detalle' in table_lower or 'cuerpo' in table_lower or 'linea' in table_lower:
            return 'transaccional_detalle'
        elif any(word in table_lower for word in ['articulo', 'cliente', 'proveedor', 'marca', 'rubro']):
            return 'catalogo'
        elif any(word in table_lower for word in ['factura', 'pedido', 'venta', 'compra', 'movim']):
            return 'transaccional_maestro'
        else:
            return 'maestro'
    
    def _extract_controls(self, content: str) -> List[Dict[str, str]]:
        """
        Extrae controles del formulario (TextBox, ComboBox, etc.)
        CON propósito funcional de cada campo
        
        Args:
            content: Contenido del .frm
            
        Returns:
            Lista de controles con nombre, caption y propósito funcional
        """
        controls = []
        
        # Patrón para controles VB6
        # Begin VB.TextBox txtNombreCliente
        #    Caption = "Nombre Cliente"
        control_pattern = r'Begin\s+VB\.(\w+)\s+(\w+)'
        caption_pattern = r'Caption\s*=\s*"([^"]+)"'
        
        # Convertir a lista para evitar 'callable_iterator' error
        matches = list(re.finditer(control_pattern, content, re.IGNORECASE))
        for match in matches:
            control_type = match.group(1)
            control_name = match.group(2)
            
            # Buscar caption cercano (siguientes 10 líneas)
            start_pos = match.end()
            next_chunk = content[start_pos:start_pos+500]
            caption_match = re.search(caption_pattern, next_chunk)
            caption = caption_match.group(1) if caption_match else ""
            
            # Inferir campo y propósito funcional
            field_candidate = self._infer_field_name(control_name, caption)
            field_purpose = self._infer_field_purpose(control_name, control_type, caption)
            
            controls.append({
                'type': control_type,
                'name': control_name,
                'caption': caption,
                'field_candidate': field_candidate,
                'field_purpose': field_purpose  # NUEVO: propósito funcional
            })
        
        return controls
    
    def _infer_field_name(self, control_name: str, caption: str) -> Optional[str]:
        """
        Infiere el nombre del campo de BD a partir del control
        
        Args:
            control_name: Nombre del control (ej: txtNombreCliente)
            caption: Caption del control (ej: "Nombre Cliente")
            
        Returns:
            Nombre de campo candidato
        """
        # Remover prefijos comunes de VB6
        clean_name = control_name
        for prefix in ['txt', 'cbo', 'cmb', 'lst', 'chk', 'opt', 'lbl', 'cmd']:
            if clean_name.lower().startswith(prefix):
                clean_name = clean_name[len(prefix):]
                break
        
        # Si el nombre limpio es significativo, usarlo
        if len(clean_name) > 2:
            return clean_name
        
        # Si no, intentar con el caption
        if caption:
            # Remover espacios y caracteres especiales
            field_from_caption = re.sub(r'[^a-zA-Z0-9]', '', caption)
            if len(field_from_caption) > 2:
                return field_from_caption
        
        return None
    
    def _infer_field_purpose(self, control_name: str, control_type: str, caption: str) -> str:
        """
        Infiere el propósito funcional de un campo en el contexto de negocio
        
        Args:
            control_name: Nombre del control VB6
            control_type: Tipo de control (TextBox, ComboBox, etc.)
            caption: Caption del control
            
        Returns:
            Propósito funcional del campo:
            - 'primary_search': Campo principal de búsqueda (nombre, código)
            - 'identifier': Identificador único
            - 'description': Descripción o detalle adicional
            - 'filter': Campo de filtrado
            - 'display': Solo visualización
            - 'calculation': Campo calculado
        """
        name_lower = control_name.lower()
        caption_lower = caption.lower() if caption else ''
        
        # 1. Identificadores únicos (ID, Código)
        if any(word in name_lower for word in ['id', 'codigo', 'cod', 'nro', 'numero']):
            return 'identifier'
        
        # 2. Campos de búsqueda principal (Nombre, Descripción principal)
        # Estos son los que el usuario típicamente usa para buscar
        if any(word in name_lower for word in ['nombre', 'articulo', 'cliente', 'razon']):
            return 'primary_search'
        
        if any(word in caption_lower for word in ['nombre', 'artículo', 'razón social']):
            return 'primary_search'
        
        # 3. Campos de búsqueda (combos de búsqueda)
        if 'busqueda' in name_lower or 'buscar' in name_lower:
            return 'primary_search'
        
        # 4. Campos de detalle/descripción adicional
        if any(word in name_lower for word in ['detalle', 'obs', 'observ', 'nota', 'comentario']):
            return 'description'
        
        if any(word in caption_lower for word in ['detalle', 'observ', 'comentario', 'nota']):
            return 'description'
        
        # 5. Campos calculados
        if any(word in name_lower for word in ['total', 'suma', 'calc', 'saldo', 'stock']):
            return 'calculation'
        
        # 6. Filtros (checkboxes, opciones)
        if control_type in ['CheckBox', 'OptionButton']:
            return 'filter'
        
        # 7. ComboBox típicamente para filtrar
        if control_type == 'ComboBox':
            return 'filter'
        
        # 8. Por defecto: display
        return 'display'
    
    def _enrich_tables_with_controls(
        self,
        tables: List[Dict[str, Any]],
        controls: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Enriquece las tablas sugeridas con campos inferidos de los controles
        Y su propósito funcional (Field Usage Map)
        
        Args:
            tables: Tablas detectadas
            controls: Controles del formulario
            
        Returns:
            Tablas enriquecidas con campos_clave_sugeridos y field_usage_map
        """
        for table in tables:
            # Agregar campos comunes que siempre deberían estar
            common_fields = self._get_common_fields_for_role(table['rol'])
            
            # Agregar campos inferidos de controles CON su propósito
            control_fields = []
            field_usage_map = {}  # NUEVO: Mapeo de propósito de campos
            
            for ctrl in controls:
                field_candidate = ctrl.get('field_candidate')
                if field_candidate and len(field_candidate) > 2:
                    control_fields.append(field_candidate)
                    
                    # Guardar propósito funcional
                    field_purpose = ctrl.get('field_purpose', 'display')
                    if field_candidate not in field_usage_map:
                        field_usage_map[field_candidate] = {
                            'purpose': field_purpose,
                            'ui_control': ctrl.get('type'),
                            'ui_caption': ctrl.get('caption', '')
                        }
            
            # Combinar y eliminar duplicados
            all_fields = list(set(common_fields + control_fields))  # SIN LÍMITE: todos los campos inferidos
            
            table['campos_clave_sugeridos'] = all_fields
            table['field_usage_map'] = field_usage_map  # NUEVO: Mapa de uso de campos
            
            # Ajustar confianza si hay campos
            if len(all_fields) > 0:
                table['confianza'] = min(table['confianza'] + 0.1, 1.0)
        
        return tables
    
    def _get_common_fields_for_role(self, role: str) -> List[str]:
        """
        Retorna campos comunes esperados según el rol de la tabla
        
        Args:
            role: Rol de la tabla (maestro, detalle, catalogo, transaccional)
            
        Returns:
            Lista de campos candidatos
        """
        common_fields = {
            'maestro': ['Codigo', 'Nombre', 'Descripcion', 'Activo', 'FechaAlta'],
            'catalogo': ['Codigo', 'Nombre', 'Descripcion'],
            'transaccional_maestro': ['Numero', 'Fecha', 'Cliente', 'Total', 'Estado'],
            'transaccional_detalle': ['Numero', 'Item', 'Articulo', 'Cantidad', 'Precio'],
        }
        
        return common_fields.get(role, ['Id', 'Nombre'])
    
    def _detect_master_detail_relations(
        self,
        content: str,
        tables: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Detecta relaciones maestro/detalle entre tablas
        
        Args:
            content: Contenido del formulario
            tables: Tablas detectadas
            
        Returns:
            Lista de relaciones candidatas
        """
        relations = []
        
        # Buscar tablas maestro y detalle
        master_tables = [t for t in tables if 'maestro' in t['rol']]
        detail_tables = [t for t in tables if 'detalle' in t['rol']]
        
        # Crear relaciones candidatas
        for master in master_tables:
            for detail in detail_tables:
                # Verificar si hay coincidencia en nombres
                master_name = master['nombre'].lower()
                detail_name = detail['nombre'].lower()
                
                # Si el detalle contiene el nombre del maestro, probable relación
                if master_name in detail_name or detail_name.replace('detalle', '') in master_name:
                    # Inferir campos de relación
                    master_key = self._infer_primary_key(master['nombre'])
                    foreign_key = master_key  # Usualmente el mismo nombre
                    
                    relations.append({
                        'origen': f"{detail['nombre']}.{foreign_key}",
                        'destino': f"{master['nombre']}.{master_key}",
                        'tipo': '1..N',
                        'confianza': 0.85
                    })
        
        return relations
    
    def _infer_primary_key(self, table_name: str) -> str:
        """
        Infiere el nombre de la clave primaria de una tabla
        
        Args:
            table_name: Nombre de la tabla
            
        Returns:
            Nombre del campo PK candidato
        """
        # Patrones comunes en AdministraNET
        patterns = [
            f'ID{table_name}',  # IDCliente, IDArticulo
            f'Id{table_name}',  # IdCliente, IdArticulo
            f'Codigo{table_name}',  # CodigoCliente
            'Numero',  # Para comprobantes
        ]
        
        return patterns[0]
    
    def _extract_validation_rules(self, content: str, entity: Optional[str]) -> List[str]:
        """
        Extrae reglas funcionales de validaciones en el código
        
        Args:
            content: Contenido del formulario
            entity: Entidad funcional
            
        Returns:
            Lista de reglas en lenguaje de negocio
        """
        rules = []
        
        # Buscar validaciones (If ... Then MsgBox)
        validation_pattern = r'If\s+(.{10,150})\s+Then.*?MsgBox\s+"([^"]+)"'
        matches = list(re.finditer(validation_pattern, content, re.IGNORECASE | re.DOTALL))
        
        for match in matches:  # SIN LÍMITE: extraer TODAS las reglas de validación
            condition = match.group(1)[:100]
            message = match.group(2)[:100]
            
            # Convertir a lenguaje de negocio
            business_rule = self._translate_validation_to_business(condition, message, entity)
            if business_rule:
                rules.append(business_rule)
        
        return rules
    
    def _translate_validation_to_business(
        self,
        condition: str,
        message: str,
        entity: Optional[str]
    ) -> Optional[str]:
        """
        Traduce una validación técnica a lenguaje de negocio
        
        Args:
            condition: Condición del If
            message: Mensaje de validación
            entity: Entidad funcional
            
        Returns:
            Regla en lenguaje de negocio
        """
        # Simplificación: usar el mensaje como regla
        # En una implementación más sofisticada, se analizaría la condición
        if entity and message:
            return f"{entity.capitalize()}: {message}"
        elif message:
            return f"Validación: {message}"
        
        return None
    
    def _consolidate_analysis(
        self,
        entities: List[str],
        tables: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        rules: List[str]
    ) -> Dict[str, Any]:
        """
        Consolida análisis de múltiples formularios
        
        Args:
            entities: Lista de entidades detectadas
            tables: Lista de tablas detectadas
            relations: Lista de relaciones detectadas
            rules: Lista de reglas funcionales
            
        Returns:
            Objeto consolidado
        """
        # Eliminar duplicados de entidades
        unique_entities = list(set(entities))
        
        # Consolidar tablas (agrupar por nombre y promediar confianza)
        table_map = {}
        for table in tables:
            name = table['nombre']
            if name not in table_map:
                table_map[name] = table
            else:
                # Promediar confianza
                existing = table_map[name]
                existing['confianza'] = (existing['confianza'] + table['confianza']) / 2
                # Combinar campos
                existing['campos_clave_sugeridos'] = list(set(
                    existing['campos_clave_sugeridos'] + table['campos_clave_sugeridos']
                ))
        
        # Filtrar tablas con confianza >= 0.6
        filtered_tables = [
            t for t in table_map.values()
            if t['confianza'] >= 0.6
        ]
        
        # Ordenar por confianza descendente
        filtered_tables.sort(key=lambda x: x['confianza'], reverse=True)
        
        # Eliminar duplicados de reglas
        unique_rules = list(set(rules))
        
        return {
            'entidades_funcionales': unique_entities,
            'tablas_sugeridas': filtered_tables,
            'relaciones_candidatas': relations,
            'reglas_funcionales_resumidas': unique_rules,
            'vigencia_reglas': {'desde': '2024-01-01', 'hasta': None},
            'notas': [
                'Mapeo obtenido de análisis de formularios VB6',
                'Requiere verificación de existencia en schema MySQL',
                f'Confianza mínima aplicada: 0.60'
            ]
        }
    
    def _empty_result(self) -> Dict[str, Any]:
        """Retorna resultado vacío"""
        return {
            'entidades_funcionales': [],
            'tablas_sugeridas': [],
            'relaciones_candidatas': [],
            'reglas_funcionales_resumidas': [],
            'vigencia_reglas': {'desde': None, 'hasta': None},
            'notas': ['No se encontraron formularios relevantes']
        }

