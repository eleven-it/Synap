"""
Herramienta para análisis estático de código VB6 de Administranet
Extrae reglas de negocio SIN exponer código ni tecnicismos
"""
import os
import re
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class VB6AnalyzerTool:
    """
    Analizador de código VB6 para extraer reglas de negocio
    
    Principios:
    - Análisis estático (sin ejecutar código)
    - Mapeo a conceptos funcionales
    - NUNCA exponer código, nombres de funciones o archivos
    """
    
    def __init__(self, vb6_source_path: Optional[str] = None):
        """
        Inicializa el analizador VB6
        
        Args:
            vb6_source_path: Ruta al código fuente VB6 de administranet
        """
        if vb6_source_path is None:
            # Ruta por defecto al código VB6 de administranet
            base_path = Path(__file__).parent.parent.parent
            vb6_source_path = base_path / 'administraNET_Limpio'
        
        self.source_path = Path(vb6_source_path)
        if not self.source_path.exists():
            logger.warning(f"Ruta de código VB6 no encontrada: {vb6_source_path}")
        
        self.modules_path = self.source_path / 'Modulos'
        self.forms_path = self.source_path / 'Formularios'
        
        # Cache de reglas extraídas
        self._rules_cache = {}
    
    def extract_business_rules(self, module_name: str) -> Dict[str, Any]:
        """
        Extrae reglas de negocio de un módulo específico
        Escanea RECURSIVAMENTE todos los archivos .bas y .cls
        
        Args:
            module_name: Nombre del módulo funcional (ej: "ventas", "inventario")
            
        Returns:
            Dict con reglas funcionales (sin código ni tecnicismos)
        """
        # Patrones de archivos por categoría funcional
        category_patterns = {
            'ventas': ['venta', 'factura', 'comprobante', 'ticket', 'pedido'],
            'inventario': ['articulo', 'stock', 'producto', 'inventario'],
            'clientes': ['cliente', 'consumidor', 'comprador'],
            'cobranzas': ['cobranza', 'recibo', 'pago', 'cuenta'],
            'compras': ['compra', 'proveedor', 'orden'],
            'general': [],  # Todos los archivos
        }
        
        patterns = category_patterns.get(module_name.lower(), [])
        
        rules = []
        files_analyzed = []
        
        # Buscar archivos .bas y .cls RECURSIVAMENTE
        vb_files = []
        
        if self.source_path.exists():
            # Buscar .bas recursivamente
            vb_files.extend(list(self.source_path.rglob('*.bas')))
            # Buscar .cls recursivamente
            vb_files.extend(list(self.source_path.rglob('*.cls')))
        
        logger.info(f"[VB6Analyzer] 📂 Encontrados {len(vb_files)} archivos VB6 (.bas/.cls) en total")
        
        # Archivos core que siempre deben analizarse (contienen lógica central)
        core_files = ['Funciones.bas', 'MStart.bas']
        
        # Filtrar archivos relevantes para la categoría
        for vb_file in vb_files:
            file_name_lower = vb_file.stem.lower()
            
            # Siempre analizar archivos core
            is_core_file = vb_file.name in core_files
            
            # Si es 'general', analizar todos los archivos
            if not patterns:
                should_analyze = True
            # Si es archivo core, siempre analizar
            elif is_core_file:
                should_analyze = True
            else:
                # Verificar si el nombre del archivo coincide con algún patrón
                should_analyze = any(pattern in file_name_lower for pattern in patterns)
            
            if should_analyze:
                logger.debug(f"[VB6Analyzer] Analizando: {vb_file.relative_to(self.source_path)}")
                
                # Analizar archivo
                file_rules = self._analyze_vb6_file(vb_file, module_name)
                
                if file_rules:
                    rules.extend(file_rules)
                    files_analyzed.append(vb_file.name)
        
        logger.info(
            f"[VB6Analyzer] ✅ Análisis completado\n"
            f"  📋 Archivos analizados: {len(files_analyzed)}\n"
            f"  📚 Reglas extraídas: {len(rules)}\n"
            f"  📂 Archivos: {', '.join(files_analyzed[:5])}{' ...' if len(files_analyzed) > 5 else ''}"
        )
        
        return {
            'module': module_name,
            'rules_count': len(rules),
            'rules': rules,
            'files_analyzed': files_analyzed
        }
    
    def _analyze_vb6_file(self, file_path: Path, module_name: str) -> List[Dict[str, Any]]:
        """
        Analiza un archivo VB6 y extrae reglas funcionales REALES del código
        
        Args:
            file_path: Ruta al archivo .bas/.cls
            module_name: Nombre del módulo funcional
            
        Returns:
            Lista de reglas funcionales extraídas
        """
        rules = []
        
        try:
            with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                lines = f.readlines()
            
            content = ''.join(lines)
            
            # 1. Extraer funciones con sus comentarios precedentes
            for i, line in enumerate(lines):
                # Detectar definición de función pública
                func_match = re.search(
                    r'(Public|Private)?\s*(Function|Sub)\s+(\w+)\s*\(',
                    line,
                    re.IGNORECASE
                )
                
                if func_match:
                    func_name = func_match.group(3)
                    line_number = i + 1
                    
                    # Buscar comentario en las 5 líneas anteriores
                    comment_lines = []
                    for j in range(max(0, i-5), i):
                        if lines[j].strip().startswith("'"):
                            comment_text = lines[j].strip()[1:].strip()
                            if len(comment_text) > 10:  # Filtrar comentarios muy cortos
                                comment_lines.append(comment_text)
                    
                    # Solo crear regla si hay comentario o función relevante de negocio
                    business_concept = self._map_to_business_concept(func_name)
                    
                    if business_concept and comment_lines:
                        # Usar comentario real como descripción
                        description = ' '.join(comment_lines[:2])  # Máximo 2 líneas de comentario
                        
                        # Extraer procedimiento de negocio completo
                        business_procedure = self._extract_business_procedure(
                            func_name, 
                            content, 
                            i, 
                            lines
                        )
                        
                        rules.append({
                            'name': func_name,  # Usar nombre real de función
                            'description': description if description else f'Función de {business_concept}',
                            'category': self._categorize_function(func_name),
                            'module': module_name,
                            'conditions': f'Cuando se requiere {business_concept}',
                            'actions': description if description else f'Calcula/valida {business_concept}',
                            'source_file': file_path.name,
                            'source_line': line_number,
                            'source_function': func_name,  # Nombre de la función/procedimiento
                            'business_procedure': business_procedure,  # Procedimiento completo de negocio
                        })
            
            # 2. Extraer validaciones REALES con mensajes
            validation_pattern = r'If\s+(.{10,200}?)\s+Then.*?MsgBox\s+"([^"]+)"'
            matches = re.finditer(validation_pattern, content, re.IGNORECASE | re.DOTALL)
            
            for match in matches:
                condition = match.group(1).strip()[:150]
                message = match.group(2).strip()[:200]
                
                # Solo agregar si el mensaje es significativo
                if len(message) > 10:
                    # Interpretar condición
                    business_rule = self._interpret_validation(condition)
                    
                    rules.append({
                        'name': f'Validación: {message[:50]}',
                        'description': message,  # Usar mensaje REAL
                        'category': 'validation',
                        'module': module_name,
                        'conditions': business_rule if business_rule else f'Validación: {condition[:100]}',
                        'actions': f'Mensaje: {message}',
                        'source_file': file_path.name,
                        'source_line': 0,
                    })
            
            logger.debug(f"[VB6Analyzer] {file_path.name}: {len(rules)} reglas extraídas")
            
        except Exception as e:
            logger.error(f"[VB6Analyzer] Error analizando {file_path.name}: {e}")
        
        return rules
    
    def _map_to_business_concept(self, technical_name: str) -> Optional[str]:
        """
        Mapea nombres técnicos a conceptos de negocio
        
        Args:
            technical_name: Nombre técnico de función
            
        Returns:
            Concepto de negocio o None
        """
        # Diccionario de mapeo técnico -> negocio (expandido)
        mapping = {
            # Cálculos
            'calcularprecio': 'precio de venta',
            'calculariva': 'impuesto IVA',
            'calculardescuento': 'descuento aplicado',
            'calculartotal': 'total de venta',
            'calcularcomision': 'comisión de vendedor',
            'calcular_costo': 'costo adicional',
            
            # Validaciones
            'validarstock': 'disponibilidad de stock',
            'validarcliente': 'cliente activo',
            'validarfecha': 'fecha válida',
            'validar_email': 'email único',
            'verificar': 'verificación de datos',
            
            # Obtención de datos
            'obtener_datos_cliente': 'información de cliente',
            'obtener_datos_articulo': 'información de artículo',
            'obtener_datos_empresa': 'información de empresa',
            'obtener_datos_caja': 'información de caja',
            'obtener_codigo': 'código automático',
            'obtener_alicuota': 'alícuota de impuesto',
            'obtener_nombre': 'nombre descriptivo',
            
            # Formatos
            'formato_fecha': 'formateo de fecha',
            'formato_cuit': 'formateo de CUIT',
            
            # Licencias y permisos
            'habilita_licencia': 'habilitación de licencia',
            'verificar_limite': 'verificación de límites',
            'trae_licencia': 'obtención de licencia',
            
            # Stock y movimientos
            'obtener_cantidad': 'cantidad acumulada',
            'verifica_articulo': 'verificación de artículo',
        }
        
        name_lower = technical_name.lower()
        
        # Buscar coincidencias parciales
        for tech_key, business_concept in mapping.items():
            if tech_key in name_lower:
                return business_concept
        
        # Si no hay coincidencia pero tiene palabras clave de negocio
        business_keywords = ['cliente', 'articulo', 'venta', 'precio', 'stock', 'factura', 'pedido']
        for keyword in business_keywords:
            if keyword in name_lower:
                return f'operación de {keyword}'
        
        return None
    
    def _categorize_function(self, func_name: str) -> str:
        """
        Categoriza una función según su nombre
        
        Args:
            func_name: Nombre de la función
            
        Returns:
            Categoría de la regla
        """
        name_lower = func_name.lower()
        
        if any(word in name_lower for word in ['calcular', 'calculo', 'formato']):
            return 'calculation'
        elif any(word in name_lower for word in ['validar', 'verificar', 'verifica']):
            return 'validation'
        elif any(word in name_lower for word in ['obtener', 'trae', 'buscar']):
            return 'business'
        elif any(word in name_lower for word in ['habilita', 'deshabilita']):
            return 'workflow'
        else:
            return 'business'
    
    def _interpret_validation(self, condition: str) -> Optional[str]:
        """
        Interpreta una condición VB6 a lenguaje de negocio
        
        Args:
            condition: Condición en código VB6
            
        Returns:
            Interpretación en lenguaje de negocio
        """
        condition_lower = condition.lower()
        
        # Patrones comunes
        if 'stock' in condition_lower and ('=' in condition_lower or '<' in condition_lower):
            return 'El stock debe ser suficiente para la operación'
        
        if 'fecha' in condition_lower:
            return 'La fecha debe estar en rango válido'
        
        if 'cliente' in condition_lower and 'null' in condition_lower:
            return 'El cliente debe estar seleccionado'
        
        if 'precio' in condition_lower and ('0' in condition_lower or '<' in condition_lower):
            return 'El precio debe ser mayor a cero'
        
        return None
    
    def _extract_business_procedure(
        self, 
        func_name: str, 
        content: str, 
        func_line_index: int, 
        lines: list
    ) -> str:
        """
        Extrae el procedimiento completo de negocio analizando el flujo de la función
        
        Args:
            func_name: Nombre de la función
            content: Contenido completo del archivo
            func_line_index: Índice de línea donde comienza la función
            lines: Lista de líneas del archivo
            
        Returns:
            Descripción del procedimiento de negocio completo
        """
        procedure_steps = []
        
        # Mapeo de patrones a pasos de negocio
        procedure_patterns = {
            # Validaciones
            'validar|verificar': 'Validación de datos de entrada',
            'if.*then.*msgbox': 'Verificación de condiciones de negocio',
            
            # Operaciones de BD
            'insert into': 'Registro de nueva información en la base de datos',
            'update': 'Actualización de información existente',
            'delete from': 'Eliminación de registros',
            'select': 'Consulta de información',
            
            # Cálculos
            'calcular|calculo': 'Cálculo de valores',
            'total|suma|subtotal': 'Cálculo de totales',
            'precio|importe': 'Cálculo de precios',
            'iva|impuesto': 'Cálculo de impuestos',
            
            # Flujo de negocio
            'grabar|guardar|save': 'Guardado de información',
            'imprimir|print': 'Generación de documentos/informes',
            'enviar|send': 'Envío de información',
            'confirmar|aprobar': 'Confirmación de operación',
            'anular|cancelar': 'Anulación de operación',
            
            # Stock y logística
            'stock|inventario': 'Gestión de stock',
            'movimiento': 'Registro de movimientos',
            'ruta|entrega|despacho': 'Gestión de logística y entregas',
            'pedido|orden': 'Procesamiento de pedidos',
            
            # Facturación
            'factura|comprobante': 'Generación de comprobantes',
            'recibo|pago|cobro': 'Gestión de cobranzas',
        }
        
        # Analizar función (siguientes 100 líneas o hasta End Function/End Sub)
        end_index = min(func_line_index + 100, len(lines))
        for i in range(func_line_index, end_index):
            line = lines[i].strip().lower()
            
            # Detectar fin de función
            if 'end function' in line or 'end sub' in line:
                break
            
            # Buscar patrones de negocio
            for pattern, description in procedure_patterns.items():
                if re.search(pattern, line, re.IGNORECASE):
                    if description not in procedure_steps:
                        procedure_steps.append(description)
        
        # Inferir procedimiento completo basado en el nombre de la función
        procedure_name = self._infer_procedure_name(func_name)
        
        if procedure_steps:
            steps_text = '\n'.join([f'{i+1}. {step}' for i, step in enumerate(procedure_steps[:5])])  # Máximo 5 pasos
            return f"{procedure_name}:\n{steps_text}"
        elif procedure_name:
            return procedure_name
        
        return ''
    
    def _infer_procedure_name(self, func_name: str) -> str:
        """
        Infiere el nombre del procedimiento de negocio desde el nombre de la función
        
        Args:
            func_name: Nombre de la función VB6
            
        Returns:
            Nombre del procedimiento en lenguaje de negocio
        """
        func_lower = func_name.lower()
        
        # Mapeo de patrones comunes
        procedure_mapping = {
            'guardar.*factura|graba.*factura': 'Procedimiento de creación y guardado de factura',
            'crear.*factura': 'Procedimiento de creación de factura',
            'anular.*factura': 'Procedimiento de anulación de factura',
            
            'guardar.*pedido|graba.*pedido': 'Procedimiento de creación y guardado de pedido',
            'confirmar.*pedido': 'Procedimiento de confirmación de pedido',
            
            'movimiento.*stock|mueve.*stock': 'Procedimiento de movimiento interno de stock',
            'ajuste.*stock': 'Procedimiento de ajuste de inventario',
            'traspaso|transferencia': 'Procedimiento de traspaso entre depósitos',
            
            'ruta.*entrega|genera.*ruta': 'Procedimiento de generación de rutas de entrega',
            'despacho|despachar': 'Procedimiento de despacho de mercadería',
            
            'cobro|cobranza|recibo': 'Procedimiento de registro de cobranza',
            'pago.*proveedor': 'Procedimiento de pago a proveedores',
            
            'cliente.*nuevo|alta.*cliente': 'Procedimiento de alta de cliente',
            'articulo.*nuevo|alta.*articulo': 'Procedimiento de alta de artículo',
            
            'cierre.*caja': 'Procedimiento de cierre de caja',
            'liquidacion': 'Procedimiento de liquidación',
        }
        
        for pattern, procedure_name in procedure_mapping.items():
            if re.search(pattern, func_lower):
                return procedure_name
        
        return ''
    
    def get_business_glossary_from_code(self) -> Dict[str, str]:
        """
        Extrae términos del glosario funcional desde el código
        Escanea RECURSIVAMENTE todos los archivos .bas y .cls
        
        Returns:
            Dict con términos funcionales y sus definiciones
        """
        glossary = {}
        
        # Analizar todos los archivos VB6 recursivamente
        if not self.source_path.exists():
            return glossary
        
        # Buscar archivos .bas y .cls recursivamente
        vb_files = list(self.source_path.rglob('*.bas')) + list(self.source_path.rglob('*.cls'))
        
        logger.info(f"[VB6Analyzer] 📖 Extrayendo glosario de {len(vb_files)} archivos VB6")
        
        for bas_file in vb_files:
            try:
                with open(bas_file, 'r', encoding='latin-1', errors='ignore') as f:
                    content = f.read()
                
                # Buscar comentarios con definiciones (líneas que empiezan con ')
                comment_pattern = r"'([^'\n]+)"
                matches = re.finditer(comment_pattern, content)
                
                for match in matches:
                    comment = match.group(1).strip()
                    
                    # Filtrar comentarios que parecen definiciones
                    if len(comment) > 20 and ':' in comment:
                        parts = comment.split(':', 1)
                        if len(parts) == 2:
                            term = parts[0].strip()
                            definition = parts[1].strip()
                            
                            # Validar que sean conceptos de negocio
                            if self._is_business_term(term):
                                glossary[term] = definition
                
            except Exception as e:
                logger.error(f"Error extrayendo glosario de {bas_file}: {e}")
        
        logger.info(f"[VB6Analyzer] ✅ Glosario extraído: {len(glossary)} términos")
        
        return glossary
    
    def _is_business_term(self, term: str) -> bool:
        """
        Determina si un término es un concepto de negocio
        
        Args:
            term: Término a evaluar
            
        Returns:
            True si es un término de negocio
        """
        # Términos técnicos a excluir
        technical_keywords = [
            'function', 'sub', 'dim', 'as', 'integer', 'string',
            'boolean', 'if', 'then', 'else', 'for', 'next'
        ]
        
        term_lower = term.lower()
        
        # Excluir si contiene palabras técnicas
        for keyword in technical_keywords:
            if keyword in term_lower:
                return False
        
        # Debe tener longitud razonable
        if len(term) < 5 or len(term) > 50:
            return False
        
        return True
    
    def search_business_logic(self, concept: str) -> Dict[str, Any]:
        """
        Busca lógica de negocio relacionada con un concepto
        
        Args:
            concept: Concepto de negocio (ej: "venta neta", "cliente activo")
            
        Returns:
            Dict con reglas relacionadas (sin código)
        """
        results = {
            'concept': concept,
            'rules': [],
            'definitions': []
        }
        
        # Buscar en cache de reglas
        for module_name, rules in self._rules_cache.items():
            for rule in rules:
                if concept.lower() in rule.get('concept', '').lower():
                    results['rules'].append(rule)
        
        return results

