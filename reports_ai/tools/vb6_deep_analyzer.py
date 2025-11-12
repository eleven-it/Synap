"""
Analizador Profundo de Formularios VB6
Extrae procedimientos, tablas, validaciones y reglas de negocio de forma detallada
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class VB6DeepAnalyzer:
    """
    Analizador profundo de archivos VB6
    
    Extrae:
    - Procedimientos paso a paso
    - Tablas con operaciones (INSERT/UPDATE)
    - Validaciones de negocio
    - Relaciones entre tablas
    - Campos utilizados
    """
    
    def __init__(self, vb6_root_path: str = None):
        # Detectar si está en Docker o local
        import os
        if os.path.exists('/app/administraNET_Limpio'):
            self.vb6_root_path = vb6_root_path or '/app/administraNET_Limpio'
        else:
            self.vb6_root_path = vb6_root_path or '/Users/sebastian/Documents/Administranet/Proyectos/Synap/administraNET_Limpio'
        
    def analyze_procedure(self, catalog_entry) -> Dict:
        """
        Analiza un procedimiento usando una entrada del catálogo como guía
        
        Args:
            catalog_entry: Entrada de FunctionalCatalog
        
        Returns:
            Dict con análisis completo del procedimiento
        """
        logger.info(f"[VB6DeepAnalyzer] Analizando procedimiento: {catalog_entry.procedure}")
        
        results = {
            'procedure_name': catalog_entry.procedure,
            'module': catalog_entry.module,
            'steps': [],
            'validations': [],
            'tables_insert': [],
            'tables_update': [],
            'fields_by_table': {},
            'relationships': [],
            'business_rules': [],
            'confidence': catalog_entry.confidence
        }
        
        # Analizar cada formulario especificado
        for form_name in catalog_entry.get_vb6_forms_list():
            form_analysis = self._analyze_form_deep(form_name, catalog_entry)
            
            if form_analysis:
                # Mergear resultados
                results['steps'].extend(form_analysis.get('steps', []))
                results['validations'].extend(form_analysis.get('validations', []))
                results['tables_insert'].extend(form_analysis.get('tables_insert', []))
                results['tables_update'].extend(form_analysis.get('tables_update', []))
                results['business_rules'].extend(form_analysis.get('business_rules', []))
                
                # Mergear fields por tabla
                for table, fields in form_analysis.get('fields_by_table', {}).items():
                    if table not in results['fields_by_table']:
                        results['fields_by_table'][table] = []
                    results['fields_by_table'][table].extend(fields)
                
                # Mergear relaciones
                results['relationships'].extend(form_analysis.get('relationships', []))
        
        # Eliminar duplicados
        results['tables_insert'] = list(set(results['tables_insert']))
        results['tables_update'] = list(set(results['tables_update']))
        results['validations'] = list(set(results['validations']))
        results['business_rules'] = list(set(results['business_rules']))
        
        return results
    
    def _analyze_form_deep(self, form_name: str, catalog_entry) -> Optional[Dict]:
        """
        Análisis profundo de un formulario VB6
        
        Args:
            form_name: Nombre del formulario (ej: Pedido.frm)
            catalog_entry: Entrada del catálogo con contexto
        
        Returns:
            Dict con análisis detallado
        """
        # Buscar archivo
        file_path = self._find_file(form_name)
        
        if not file_path:
            logger.warning(f"[VB6DeepAnalyzer] No se encontró: {form_name}")
            return None
        
        logger.info(f"[VB6DeepAnalyzer] Analizando: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='latin-1', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"[VB6DeepAnalyzer] Error leyendo {file_path}: {e}")
            return None
        
        results = {
            'steps': [],
            'validations': [],
            'tables_insert': [],
            'tables_update': [],
            'fields_by_table': {},
            'relationships': [],
            'business_rules': []
        }
        
        # 1. Extraer validaciones (MsgBox con errores)
        validations = self._extract_validations(content)
        results['validations'] = validations
        
        # 2. Extraer operaciones INSERT
        insert_ops = self._extract_insert_operations(content, catalog_entry)
        results['tables_insert'] = [op['table'] for op in insert_ops]
        
        # 3. Extraer operaciones UPDATE
        update_ops = self._extract_update_operations(content, catalog_entry)
        results['tables_update'] = [op['table'] for op in update_ops]
        
        # 4. Extraer campos por tabla
        for op in insert_ops + update_ops:
            table = op['table']
            if table not in results['fields_by_table']:
                results['fields_by_table'][table] = []
            results['fields_by_table'][table].extend(op.get('fields', []))
        
        # 5. Inferir pasos del procedimiento
        steps = self._infer_procedure_steps(content, catalog_entry, validations, insert_ops, update_ops)
        results['steps'] = steps
        
        # 6. Extraer relaciones entre tablas
        relationships = self._extract_relationships(content, catalog_entry)
        results['relationships'] = relationships
        
        # 7. Extraer reglas de negocio desde comentarios y código
        rules = self._extract_business_rules_from_code(content)
        results['business_rules'] = rules
        
        return results
    
    def _extract_validations(self, content: str) -> List[str]:
        """Extrae validaciones desde MsgBox"""
        validations = []
        
        # Patrón para MsgBox con validaciones
        msgbox_pattern = r'MsgBox\s+"([^"]+)",\s*vb(?:Critical|Information|Exclamation)'
        
        matches = re.finditer(msgbox_pattern, content, re.IGNORECASE)
        
        for match in matches:
            message = match.group(1)
            # Filtrar mensajes informativos, solo validaciones
            if any(keyword in message.lower() for keyword in ['debe', 'no puede', 'limite', 'supera', 'ingrese', 'seleccione', 'completar']):
                validations.append(message)
        
        return validations[:20]  # Máximo 20 validaciones más importantes
    
    def _extract_insert_operations(self, content: str, catalog_entry) -> List[Dict]:
        """Extrae operaciones INSERT/AddNew"""
        operations = []
        
        # Buscar tablas candidatas del catálogo
        candidate_tables = catalog_entry.get_tables_list()
        
        for table in candidate_tables:
            # Patrón: rs_xxx.Open "SELECT * FROM tabla_name
            open_pattern = rf'(rs_\w+)\.Open\s+"SELECT\s+\*\s+FROM\s+{re.escape(table)}\s+'
            
            matches = re.finditer(open_pattern, content, re.IGNORECASE)
            
            for match in matches:
                recordset_name = match.group(1)
                
                # Buscar AddNew después del Open
                addnew_pattern = rf'{re.escape(recordset_name)}\.AddNew'
                if re.search(addnew_pattern, content[match.end():match.end()+5000], re.IGNORECASE):
                    # Extraer campos asignados
                    fields = self._extract_fields_for_recordset(content, recordset_name, match.end())
                    
                    operations.append({
                        'operation': 'INSERT',
                        'table': table,
                        'recordset': recordset_name,
                        'fields': fields
                    })
        
        return operations
    
    def _extract_update_operations(self, content: str, catalog_entry) -> List[Dict]:
        """Extrae operaciones UPDATE"""
        operations = []
        
        candidate_tables = catalog_entry.get_tables_list()
        
        for table in candidate_tables:
            # Patrón: conn.Execute "UPDATE tabla SET ...
            update_pattern = rf'conn\.Execute\s+"UPDATE\s+{re.escape(table)}\s+SET\s+([^"]+)"'
            
            matches = re.finditer(update_pattern, content, re.IGNORECASE)
            
            for match in matches:
                set_clause = match.group(1)
                # Extraer campos del SET clause
                fields = re.findall(r'(\w+)\s*=', set_clause)
                
                operations.append({
                    'operation': 'UPDATE',
                    'table': table,
                    'fields': fields
                })
        
        return operations
    
    def _extract_fields_for_recordset(self, content: str, recordset_name: str, start_pos: int) -> List[str]:
        """Extrae campos asignados a un recordset"""
        fields = []
        
        # Buscar asignaciones de campos en los siguientes 2000 caracteres
        window = content[start_pos:start_pos+2000]
        
        # Patrón: rs_xxx.Fields!FieldName = ...
        field_pattern = rf'{re.escape(recordset_name)}\.Fields!(\w+)\s*='
        
        matches = re.finditer(field_pattern, window, re.IGNORECASE)
        
        for match in matches:
            field_name = match.group(1)
            if field_name not in fields:
                fields.append(field_name)
        
        return fields
    
    def _infer_procedure_steps(
        self, 
        content: str, 
        catalog_entry, 
        validations: List[str], 
        insert_ops: List[Dict],
        update_ops: List[Dict]
    ) -> List[str]:
        """Infiere los pasos del procedimiento desde el código"""
        steps = []
        
        # Paso 1: Validaciones previas
        if validations:
            steps.append(f"Validación previa: {'; '.join(validations[:5])}")
        
        # Paso 2: Inicio de transacción
        if 'BeginTrans' in content:
            steps.append("Iniciar transacción (BeginTrans)")
        
        # Paso 3: Incrementar contadores
        if 'codmov' in [op['table'] for op in update_ops]:
            steps.append("Generar código de movimiento único (incrementar contador)")
        
        if 'talonarios' in [op['table'] for op in update_ops]:
            steps.append("Generar número de comprobante (incrementar numeración)")
        
        # Paso 4: Guardar datos adicionales
        if 'cliente_datos_adicionales' in [op['table'] for op in insert_ops]:
            steps.append("Guardar datos de entrega (fecha, transporte, repartidor, ruta)")
        
        # Paso 5: Guardar cabecera
        master_table = catalog_entry.master_table
        if master_table and master_table in [op['table'] for op in insert_ops]:
            steps.append(f"Guardar cabecera del {catalog_entry.procedure.lower()} en tabla maestra ({master_table})")
        
        # Paso 6: Guardar detalle
        detail_table = catalog_entry.detail_table
        if detail_table and detail_table in [op['table'] for op in insert_ops]:
            steps.append(f"Guardar líneas/ítems del {catalog_entry.procedure.lower()} en tabla detalle ({detail_table})")
        
        # Paso 7: Actualizar stock
        if 'stock_deposito' in [op['table'] for op in update_ops]:
            steps.append("Actualizar stock reservado/comprometido por depósito")
        
        # Paso 8: Percepciones
        if 'percep_cli' in [op['table'] for op in insert_ops]:
            steps.append("Guardar percepciones aplicadas al cliente")
        
        # Paso 9: Relaciones
        if catalog_entry.dependencies:
            deps = [d.strip() for d in catalog_entry.dependencies.split(',') if d.strip()]
            for dep in deps[:3]:
                if dep.lower() in content.lower():
                    steps.append(f"Procesar relación con: {dep}")
        
        # Paso 10: Confirmar transacción
        if 'CommitTrans' in content:
            steps.append("Confirmar transacción (CommitTrans) o hacer rollback si hay error")
        
        return steps
    
    def _extract_relationships(self, content: str, catalog_entry) -> List[Dict]:
        """Extrae relaciones entre tablas desde el código"""
        relationships = []
        
        # Usar relaciones pre-documentadas del catálogo
        for source, target in catalog_entry.table_relationships.items():
            relationships.append({
                'source': source,
                'target': target,
                'type': '1:N' if catalog_entry.detail_table in source else 'N:1',
                'confidence': 0.95  # Alta confianza (viene del catálogo)
            })
        
        return relationships
    
    def _extract_business_rules_from_code(self, content: str) -> List[str]:
        """Extrae reglas de negocio desde comentarios y código"""
        rules = []
        
        # Buscar comentarios con palabras clave de reglas
        comment_pattern = r"'([^'\n]{20,200})"
        
        matches = re.finditer(comment_pattern, content)
        
        for match in matches:
            comment = match.group(1).strip()
            
            # Filtrar comentarios que parecen reglas de negocio
            if any(keyword in comment.lower() for keyword in [
                'validar', 'verificar', 'debe', 'no puede', 'si el cliente',
                'si el', 'regla', 'limite', 'credito', 'stock', 'permiso'
            ]):
                if len(comment) > 15 and comment not in rules:
                    rules.append(comment)
        
        return rules[:15]  # Máximo 15 reglas
    
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
    
    def generate_business_procedure(self, analysis: Dict) -> str:
        """
        Genera descripción textual del procedimiento de negocio
        
        Args:
            analysis: Resultado del análisis profundo
        
        Returns:
            String con procedimiento en lenguaje de negocio
        """
        lines = []
        
        lines.append(f"PROCEDIMIENTO: {analysis['procedure_name'].upper()}")
        lines.append("")
        
        # Pasos
        if analysis['steps']:
            lines.append("PASOS:")
            for i, step in enumerate(analysis['steps'], 1):
                lines.append(f"{i}. {step}")
            lines.append("")
        
        # Validaciones
        if analysis['validations']:
            lines.append("VALIDACIONES:")
            for val in analysis['validations'][:7]:
                lines.append(f"✓ {val}")
            lines.append("")
        
        # Reglas de negocio
        if analysis['business_rules']:
            lines.append("REGLAS DE NEGOCIO:")
            for rule in analysis['business_rules'][:7]:
                lines.append(f"• {rule}")
            lines.append("")
        
        # Datos guardados
        if analysis['tables_insert']:
            lines.append("DATOS CREADOS EN:")
            for table in analysis['tables_insert']:
                fields = analysis['fields_by_table'].get(table, [])
                fields_str = ', '.join(fields[:5])
                if len(fields) > 5:
                    fields_str += f", ... (+{len(fields)-5} más)"
                lines.append(f"  • {table}: {fields_str}")
            lines.append("")
        
        # Datos actualizados
        if analysis['tables_update']:
            lines.append("DATOS ACTUALIZADOS EN:")
            for table in analysis['tables_update']:
                fields = analysis['fields_by_table'].get(table, [])
                if fields:
                    fields_str = ', '.join(fields[:3])
                    lines.append(f"  • {table}: {fields_str}")
                else:
                    lines.append(f"  • {table}")
        
        return "\n".join(lines)

