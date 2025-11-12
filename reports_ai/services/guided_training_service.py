"""
Servicio para Entrenamiento GUIADO del Logic Interpreter

Utiliza el catálogo funcional para entrenar de forma precisa y rápida,
en lugar de escanear todo el proyecto.
"""
import logging
from typing import Dict, Optional, Callable
from django.utils import timezone

from reports_ai.models import FunctionalCatalog, BusinessRule
from reports_ai.tools.vb6_deep_analyzer import VB6DeepAnalyzer

logger = logging.getLogger(__name__)


class GuidedTrainingService:
    """
    Servicio para entrenamiento guiado desde el catálogo funcional
    """
    
    def __init__(self):
        self.analyzer = VB6DeepAnalyzer()
        
        # Importar analizador de flujo UI
        from reports_ai.tools.vb6_ui_flow_analyzer import VB6UIFlowAnalyzer
        self.ui_analyzer = VB6UIFlowAnalyzer()
    
    def train_from_catalog_entry(
        self, 
        catalog_entry: FunctionalCatalog,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Entrena el Logic Interpreter desde una entrada del catálogo
        
        Args:
            catalog_entry: Entrada del FunctionalCatalog
            progress_callback: Función para reportar progreso
        
        Returns:
            Dict con resultados del entrenamiento
        """
        logger.info(f"[GuidedTraining] Iniciando entrenamiento guiado: {catalog_entry}")
        
        results = {
            'procedure': catalog_entry.procedure,
            'module': catalog_entry.module,
            'business_rules_created': 0,
            'tables_discovered': [],
            'validations_discovered': [],
            'relationships_discovered': [],
            'confidence': catalog_entry.confidence,
            'steps': [],
            'warnings': [],
            'errors': []
        }
        
        try:
            # PASO 1: Análisis profundo
            if progress_callback:
                progress_callback({
                    'phase': 'analyzing',
                    'message': f'Analizando {catalog_entry.vb6_forms}...',
                    'progress': 20
                })
            
            analysis = self.analyzer.analyze_procedure(catalog_entry)
            
            if not analysis:
                results['warnings'].append(f'No se pudo analizar {catalog_entry.vb6_forms}')
                return results
            
            results['tables_discovered'] = list(set(analysis['tables_insert'] + analysis['tables_update']))
            results['validations_discovered'] = analysis['validations']
            results['relationships_discovered'] = analysis['relationships']
            results['steps'] = analysis['steps']
            
            # PASO 2: Generar Business Rule TÉCNICA (para Data Analyst)
            if progress_callback:
                progress_callback({
                    'phase': 'creating_rules',
                    'message': 'Creando Business Rules técnicas...',
                    'progress': 50
                })
            
            procedure_text = self.analyzer.generate_business_procedure(analysis)
            
            # Crear Business Rule TÉCNICA del procedimiento
            technical_rule = BusinessRule.objects.update_or_create(
                module=catalog_entry.module,
                name=f"Procedimiento: {catalog_entry.procedure.title()}",
                defaults={
                    'description': f'Procedimiento TÉCNICO para {catalog_entry.procedure} con validaciones y persistencia. Para uso del Data Analyst.',
                    'category': catalog_entry.module.lower(),
                    'source_file': catalog_entry.vb6_forms,
                    'source_function': 'Guardar()',
                    'source_line': None,
                    'business_procedure': procedure_text,
                    'priority': catalog_entry.priority,
                    'is_active': True,
                    'tags': f'{catalog_entry.module.lower()},{catalog_entry.procedure.lower()},procedimiento,tecnico',
                    'conditions': catalog_entry.validations,
                    'actions': '\n'.join(analysis['steps']) if analysis['steps'] else catalog_entry.business_rules
                }
            )[0]
            
            results['business_rules_created'] += 1
            logger.info(f"[GuidedTraining] Business Rule TÉCNICA creada: {technical_rule.name}")
            
            # PASO 2.5: Generar Business Rule de USUARIO (Manual de Usuario)
            if progress_callback:
                progress_callback({
                    'phase': 'creating_user_manual',
                    'message': 'Generando Manual de Usuario...',
                    'progress': 70
                })
            
            # Analizar flujo de UI para generar manual de usuario
            ui_flow = self.ui_analyzer.extract_user_procedure(catalog_entry.vb6_forms, catalog_entry)
            
            if ui_flow:
                user_manual_text = ui_flow['steps']  # Ya viene en formato markdown natural
                
                # Extraer información de navegación real
                menu_path = ui_flow.get('menu_path', f"{catalog_entry.module} → {catalog_entry.procedure}")
                shortcut = ui_flow.get('shortcut', '')
                nav_flow = ui_flow.get('navigation_flow', [])
                
                # Construir source_file con todos los formularios involucrados
                all_forms = [catalog_entry.vb6_forms]
                if nav_flow:
                    all_forms.extend([f['name'] for f in nav_flow if f.get('name')])
                
                source_files = ', '.join(list(set(all_forms))[:3])  # Máximo 3
                
                # Construir source_function con los procedimientos reales
                source_functions = []
                if nav_flow:
                    for step in nav_flow:
                        if step.get('name') and step.get('type') == 'procedure':
                            source_functions.append(f"{step['name']}()")
                
                if not source_functions:
                    source_functions = ['Menu → Formulario → Guardar()']
                
                # Crear Business Rule de USUARIO
                user_manual_rule = BusinessRule.objects.update_or_create(
                    module=catalog_entry.module,
                    name=f"Manual de Usuario: {ui_flow['form_caption']}",
                    defaults={
                        'description': f'Procedimiento REAL paso a paso para {catalog_entry.procedure.lower()}, extraído del código fuente VB6',
                        'category': catalog_entry.module.lower(),
                        'source_file': source_files,
                        'source_function': ', '.join(source_functions[:3]),
                        'source_line': None,
                        'business_procedure': user_manual_text,
                        'priority': 10,  # MÁXIMA prioridad (se usa para responder al usuario)
                        'is_active': True,
                        'tags': f'{catalog_entry.module.lower()},manual,usuario,{ui_flow["form_caption"].lower()},{catalog_entry.procedure.lower()}',
                        'conditions': catalog_entry.validations,
                        'actions': f"Ruta: {menu_path}" + (f" ({shortcut})" if shortcut else "")
                    }
                )[0]
                
                results['business_rules_created'] += 1
                logger.info(f"[GuidedTraining] Business Rule de USUARIO creada: {user_manual_rule.name}")
            else:
                logger.warning("[GuidedTraining] No se pudo generar Manual de Usuario")
            
            # PASO 3: Crear Business Rules adicionales por validación
            if analysis['validations']:
                for val in analysis['validations'][:10]:  # Máximo 10 validaciones
                    validation_rule = BusinessRule.objects.update_or_create(
                        module=catalog_entry.module,
                        name=f"Validación: {val[:60]}",
                        defaults={
                            'description': f'Validación del procedimiento {catalog_entry.procedure}',
                            'category': catalog_entry.module.lower(),
                            'source_file': catalog_entry.vb6_forms,
                            'source_function': 'MsgBox',
                            'business_procedure': val,
                            'priority': 5,
                            'is_active': True,
                            'tags': f'validacion,{catalog_entry.module.lower()},{catalog_entry.procedure.lower()}',
                            'conditions': val,
                            'actions': f'Aplicar validación: {val}'
                        }
                    )[0]
                    
                    results['business_rules_created'] += 1
            
            # PASO 4: Crear Business Rules por regla de negocio
            if analysis['business_rules']:
                for rule in analysis['business_rules'][:10]:  # Máximo 10 reglas
                    business_rule_obj = BusinessRule.objects.update_or_create(
                        module=catalog_entry.module,
                        name=f"Regla: {rule[:60]}",
                        defaults={
                            'description': f'Regla de negocio extraída de {catalog_entry.vb6_forms}',
                            'category': catalog_entry.module.lower(),
                            'source_file': catalog_entry.vb6_forms,
                            'source_function': 'Comentario',
                            'business_procedure': rule,
                            'priority': 5,
                            'is_active': True,
                            'tags': f'regla,{catalog_entry.module.lower()},{catalog_entry.procedure.lower()}',
                            'conditions': '',
                            'actions': rule
                        }
                    )[0]
                    
                    results['business_rules_created'] += 1
            
            # PASO 5: Actualizar el catálogo con datos descubiertos
            if progress_callback:
                progress_callback({
                    'phase': 'updating_catalog',
                    'message': 'Actualizando catálogo con datos descubiertos...',
                    'progress': 95
                })
            
            # Actualizar campos de lógica del catálogo con lo descubierto
            catalog_entry.business_rules = '\n'.join(analysis.get('business_rules', [])[:10]) if analysis.get('business_rules') else catalog_entry.business_rules
            catalog_entry.validations = '\n'.join(analysis.get('validations', [])[:10]) if analysis.get('validations') else catalog_entry.validations
            
            # Eventos relevantes: extraer de los steps
            events_found = []
            for step in analysis.get('steps', []):
                if 'Guardar' in step or 'Save' in step or 'BeginTrans' in step or 'Commit' in step:
                    # Extraer nombre de función/evento
                    if '()' in step:
                        event = step.split('(')[0].split()[-1]
                        events_found.append(event + '()')
            
            if events_found:
                catalog_entry.relevant_events = ', '.join(list(set(events_found))[:5])
            
            # Actualizar tablas descubiertas
            if results['tables_discovered']:
                discovered_tables = ', '.join(list(set(results['tables_discovered']))[:10])
                if not catalog_entry.candidate_tables or catalog_entry.candidate_tables == '':
                    catalog_entry.candidate_tables = discovered_tables
                else:
                    # Combinar con las existentes (sin duplicados)
                    existing = set(catalog_entry.candidate_tables.split(', '))
                    new_tables = set(results['tables_discovered'])
                    catalog_entry.candidate_tables = ', '.join(list(existing.union(new_tables))[:10])
            
            # Actualizar timestamp
            catalog_entry.last_trained = timezone.now()
            catalog_entry.save()
            
            logger.info(f"[GuidedTraining] Catálogo actualizado con datos descubiertos")
            
            if progress_callback:
                progress_callback({
                    'phase': 'completed',
                    'message': f'Entrenamiento completado: {results["business_rules_created"]} reglas creadas y catálogo actualizado',
                    'progress': 100
                })
            
            results['success'] = True
            results['catalog_updated'] = True
            
        except Exception as e:
            logger.error(f"[GuidedTraining] Error durante entrenamiento: {e}", exc_info=True)
            results['errors'].append(str(e))
            results['success'] = False
            results['catalog_updated'] = False
        
        return results
    
    def train_all_active_catalog_entries(
        self,
        progress_callback: Optional[Callable] = None
    ) -> Dict:
        """
        Entrena desde TODAS las entradas activas del catálogo
        
        Args:
            progress_callback: Función para reportar progreso
        
        Returns:
            Dict con resultados de todos los entrenamientos
        """
        logger.info("[GuidedTraining] Iniciando entrenamiento desde todos los catálogos activos")
        
        # Obtener todas las entradas activas ordenadas por prioridad
        catalog_entries = FunctionalCatalog.objects.filter(is_active=True).order_by('-priority')
        
        total = catalog_entries.count()
        
        results = {
            'total_entries': total,
            'successful_entries': 0,
            'failed_entries': 0,
            'total_business_rules': 0,
            'entries_detail': [],
            'summary': {}
        }
        
        if total == 0:
            results['errors'] = ['No hay entradas activas en el catálogo funcional']
            return results
        
        # Entrenar cada entrada
        for idx, entry in enumerate(catalog_entries):
            if progress_callback:
                progress_callback({
                    'phase': 'training_entry',
                    'message': f'Entrenando: {entry.procedure} ({idx+1}/{total})',
                    'progress': int((idx / total) * 90)
                })
            
            entry_results = self.train_from_catalog_entry(entry, progress_callback)
            
            entry_detail = {
                'module': entry.module,
                'procedure': entry.procedure,
                'business_rules_created': entry_results['business_rules_created'],
                'tables': len(entry_results['tables_discovered']),
                'validations': len(entry_results['validations_discovered']),
                'relationships': len(entry_results['relationships_discovered']),
                'confidence': entry_results['confidence'],
                'success': entry_results.get('success', False),
                'errors': entry_results.get('errors', [])
            }
            
            results['entries_detail'].append(entry_detail)
            
            if entry_results.get('success', False):
                results['successful_entries'] += 1
                results['total_business_rules'] += entry_results['business_rules_created']
            else:
                results['failed_entries'] += 1
        
        # Resumen
        results['summary'] = {
            'total_entries': total,
            'successful': results['successful_entries'],
            'failed': results['failed_entries'],
            'total_business_rules': results['total_business_rules'],
            'success_rate': (results['successful_entries'] / total * 100) if total > 0 else 0
        }
        
        if progress_callback:
            progress_callback({
                'phase': 'completed',
                'message': f'Entrenamiento completado: {results["total_business_rules"]} Business Rules creadas',
                'progress': 100
            })
        
        return results
    
    def get_catalog_entries_summary(self) -> Dict:
        """
        Obtiene resumen de entradas del catálogo
        
        Returns:
            Dict con información del catálogo
        """
        total = FunctionalCatalog.objects.count()
        active = FunctionalCatalog.objects.filter(is_active=True).count()
        
        entries_by_module = {}
        
        for entry in FunctionalCatalog.objects.filter(is_active=True):
            module = entry.module
            if module not in entries_by_module:
                entries_by_module[module] = {
                    'count': 0,
                    'procedures': [],
                    'avg_confidence': 0
                }
            
            entries_by_module[module]['count'] += 1
            entries_by_module[module]['procedures'].append({
                'name': entry.procedure,
                'priority': entry.priority,
                'confidence': entry.confidence
            })
        
        # Calcular confianza promedio por módulo
        for module, data in entries_by_module.items():
            entries = FunctionalCatalog.objects.filter(module=module, is_active=True)
            if entries:
                data['avg_confidence'] = sum(e.confidence for e in entries) / entries.count()
        
        return {
            'total_entries': total,
            'active_entries': active,
            'entries_by_module': entries_by_module
        }

