"""
Servicio de entrenamiento interactivo del Logic Interpreter
Compatible con ejecución manual (UI) y automática (Celery)
"""
import logging
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
from reports_ai.tools.vb6_form_analyzer import VB6FormAnalyzer
from reports_ai.tools.vb6_analyzer import VB6AnalyzerTool
from reports_ai.tools.mysql_tool import MySQLTool
from reports_ai.models import LogicTrainingSession, BusinessRule

logger = logging.getLogger(__name__)


class LogicInterpreterTrainingService:
    """
    Servicio de entrenamiento del Logic Interpreter
    
    Soporta:
    - Entrenamiento interactivo con progreso en tiempo real
    - Entrenamiento batch para Celery
    - Callbacks opcionales para updates de UI
    """
    
    # Definición de fases
    PHASES = [
        {'id': 'scan', 'name': 'Escaneo de Formularios', 'icon': '🔍', 'weight': 0.05},
        {'id': 'analyze', 'name': 'Análisis Individual', 'icon': '🔬', 'weight': 0.60},
        {'id': 'infer', 'name': 'Inferencia de Tablas', 'icon': '🗄️', 'weight': 0.10},
        {'id': 'validate', 'name': 'Validación MySQL', 'icon': '✅', 'weight': 0.15},
        {'id': 'extract', 'name': 'Extracción de Reglas', 'icon': '📚', 'weight': 0.05},
        {'id': 'save', 'name': 'Guardado Final', 'icon': '💾', 'weight': 0.05},
    ]
    
    def __init__(self):
        self.form_analyzer = VB6FormAnalyzer()
        self.vb6_analyzer = VB6AnalyzerTool()
        self.mysql_tool = MySQLTool()
    
    def train_interactive(
        self,
        session_id: str,
        categories: Optional[List[str]] = None,
        mode: str = 'full'
    ) -> Dict[str, Any]:
        """
        Entrenamiento interactivo con tracking de progreso
        
        Args:
            session_id: ID único de la sesión
            categories: Lista de categorías a analizar (None = todas)
            mode: 'full' o 'incremental'
            
        Returns:
            Dict con resultados del entrenamiento
        """
        logger.info(
            f"\n{'='*70}\n"
            f"[Logic Training] 🎓 INICIANDO ENTRENAMIENTO INTERACTIVO\n"
            f"{'='*70}\n"
            f"  🆔 Session ID: {session_id}\n"
            f"  📂 Categorías: {categories or 'Todas'}\n"
            f"  🔧 Modo: {mode}\n"
            f"{'='*70}"
        )
        
        # Obtener o crear sesión
        try:
            session = LogicTrainingSession.objects.get(session_id=session_id)
        except LogicTrainingSession.DoesNotExist:
            session = LogicTrainingSession.objects.create(
                session_id=session_id,
                categories=categories or [],
                mode=mode,
                status='running'
            )
        
        start_time = time.time()
        
        try:
            # Fase 1: Escaneo de formularios
            self._phase_scan(session, categories)
            
            # Fase 2: Análisis individual
            all_discoveries = self._phase_analyze(session, categories)
            
            # Fase 3: Inferencia de tablas
            self._phase_infer(session, all_discoveries)
            
            # Fase 4: Validación en MySQL
            self._phase_validate(session)
            
            # Fase 5: Extracción de reglas
            self._phase_extract_rules(session, categories)
            
            # Fase 6: Guardado final
            self._phase_save(session)
            
            # Completar sesión
            from django.utils import timezone as tz
            duration = time.time() - start_time
            session.status = 'completed'
            session.end_time = tz.now()
            session.duration_seconds = duration
            session.progress_percentage = 100.0
            session.add_log('training_completed', f'Entrenamiento completado en {duration:.1f}s', 'success')
            session.save()
            
            logger.info(
                f"[Logic Training] ✅ ENTRENAMIENTO COMPLETADO\n"
                f"  ⏱️  Duración: {duration:.1f}s\n"
                f"  📋 Formularios: {session.analyzed_forms}/{session.total_forms}\n"
                f"  🏷️  Entidades: {len(session.entities_discovered)}\n"
                f"  🗄️  Tablas: {len(session.tables_suggested)}\n"
                f"  📚 Reglas: {len(session.rules_extracted)}"
            )
            
            return {
                'success': True,
                'session_id': session_id,
                'duration': duration,
                'stats': {
                    'forms_analyzed': session.analyzed_forms,
                    'entities': len(session.entities_discovered),
                    'tables': len(session.tables_suggested),
                    'fields': sum(len(f) for f in session.fields_validated.values()),
                    'relations': len(session.relations_found),
                    'rules': len(session.rules_extracted)
                }
            }
            
        except Exception as e:
            from django.utils import timezone as tz
            duration = time.time() - start_time
            session.status = 'error'
            session.end_time = tz.now()
            session.duration_seconds = duration
            session.error_message = str(e)
            session.add_log('training_error', str(e), 'error')
            session.save()
            
            logger.error(f"[Logic Training] ❌ ERROR: {e}")
            
            return {
                'success': False,
                'session_id': session_id,
                'error': str(e)
            }
    
    def _phase_scan(self, session: LogicTrainingSession, categories: Optional[List[str]]):
        """Fase 1: Escaneo de formularios"""
        session.current_phase = 'scan'
        session.add_log('phase_started', '🔍 Iniciando escaneo de formularios VB6', 'info')
        session.save()
        
        logger.info(f"[Logic Training] 🔍 FASE 1: Escaneo de formularios")
        
        # Identificar formularios relevantes
        if not categories:
            categories = ['inventario', 'ventas', 'clientes', 'cobranzas', 'compras', 'general']
        
        total_forms = 0
        forms_by_category = {}
        
        for category in categories:
            forms = self.form_analyzer._get_relevant_forms(category)
            forms_count = min(len(forms), 10)  # Limitar a 10 por categoría
            total_forms += forms_count
            forms_by_category[category] = forms_count
            
            if forms_count > 0:
                session.add_log(
                    'category_scanned',
                    f'📂 {category}: {forms_count} formularios encontrados',
                    'info'
                )
                session.save()
                time.sleep(0.2)  # Pequeña pausa para visualización
        
        session.total_forms = total_forms
        session.progress_percentage = 5.0
        session.add_log('scan_completed', f'✅ Total: {total_forms} formularios identificados para analizar', 'success')
        session.save()
        
        logger.info(
            f"[Logic Training] ✅ Escaneo completado\n"
            f"  📋 Total formularios: {total_forms}\n"
            f"  📂 Por categoría: {forms_by_category}"
        )
    
    def _phase_analyze(self, session: LogicTrainingSession, categories: Optional[List[str]]) -> Dict[str, Any]:
        """Fase 2: Análisis individual de formularios"""
        session.current_phase = 'analyze'
        session.add_log('phase_started', 'Iniciando análisis de formularios', 'info')
        session.save()
        
        logger.info(f"[Logic Training] 🔬 FASE 2: Análisis individual")
        
        if not categories:
            categories = ['inventario', 'ventas', 'clientes', 'cobranzas', 'compras', 'general']
        
        all_entities = []
        all_tables = []
        all_relations = []
        all_rules = []
        forms_analyzed_list = []  # Lista detallada de formularios
        
        forms_analyzed = 0
        forms_with_errors = 0
        
        for category in categories:
            forms = self.form_analyzer._get_relevant_forms(category)
            
            logger.info(f"[Logic Training] Categoría '{category}': {len(forms)} formularios encontrados")
            
            for form_path in forms:  # SIN LÍMITE: analizar TODOS los formularios
                session.current_item = form_path.name
                session.save()
                
                logger.info(f"[Logic Training] 🔍 Analizando {form_path.name}...")
                
                form_start = time.time()
                
                # Analizar formulario
                try:
                    form_analysis = self.form_analyzer._analyze_single_form(form_path)
                    
                    form_duration = time.time() - form_start
                    
                    if form_analysis:
                        entities = form_analysis.get('entidades', [])
                        tables = form_analysis.get('tablas_sugeridas', [])
                        relations = form_analysis.get('relaciones_candidatas', [])
                        rules = form_analysis.get('reglas_funcionales', [])
                        
                        all_entities.extend(entities)
                        all_tables.extend(tables)
                        all_relations.extend(relations)
                        all_rules.extend(rules)
                        
                        forms_analyzed += 1
                        
                        # Guardar detalle del formulario analizado
                        forms_analyzed_list.append({
                            'name': form_path.name,
                            'category': category,
                            'entities': len(entities),
                            'tables': len(tables),
                            'relations': len(relations),
                            'rules': len(rules),
                            'duration': form_duration,
                            'status': 'success'
                        })
                        
                        # Update progreso
                        session.analyzed_forms = forms_analyzed
                        base_progress = 5.0  # De la fase scan
                        analyze_weight = 60.0  # 60% del total
                        session.progress_percentage = base_progress + (
                            (forms_analyzed / max(session.total_forms, 1)) * analyze_weight
                        )
                        
                        # Log detallado
                        log_msg = f'✅ {form_path.name} → {len(entities)} entidades, {len(tables)} tablas, {len(rules)} reglas ({form_duration:.1f}s)'
                        session.add_log('form_analyzed', log_msg, 'success')
                        session.save()
                        
                        logger.info(f"[Logic Training] {log_msg}")
                        
                        # Pequeña pausa para visualización
                        time.sleep(0.3)
                    else:
                        forms_with_errors += 1
                        forms_analyzed_list.append({
                            'name': form_path.name,
                            'category': category,
                            'status': 'no_data'
                        })
                        session.add_log('form_skipped', f'⚠️ {form_path.name} sin datos útiles', 'warning')
                        session.save()
                        
                except Exception as e:
                    forms_with_errors += 1
                    forms_analyzed_list.append({
                        'name': form_path.name,
                        'category': category,
                        'error': str(e),
                        'status': 'error'
                    })
                    logger.warning(f"[Logic Training] ⚠️ Error en {form_path.name}: {e}")
                    session.add_log('form_error', f'❌ {form_path.name}: {str(e)[:100]}', 'error')
                    session.save()
        
        # Guardar lista de formularios analizados en la sesión
        if not hasattr(session, 'forms_analyzed_list') or not isinstance(session.fields_validated, dict):
            session.fields_validated = {}
        
        session.fields_validated['forms_analyzed_list'] = forms_analyzed_list
        session.fields_validated['forms_with_errors'] = forms_with_errors
        session.save()
        
        logger.info(
            f"[Logic Training] ✅ Análisis completado\n"
            f"  📋 Analizados: {forms_analyzed}\n"
            f"  ❌ Con errores: {forms_with_errors}\n"
            f"  📊 Total procesados: {len(forms_analyzed_list)}"
        )
        
        return {
            'entities': all_entities,
            'tables': all_tables,
            'relations': all_relations,
            'rules': all_rules,
            'forms_list': forms_analyzed_list
        }
    
    def _phase_infer(self, session: LogicTrainingSession, discoveries: Dict[str, Any]):
        """Fase 3: Inferencia y consolidación de tablas"""
        session.current_phase = 'infer'
        session.progress_percentage = 65.0
        session.add_log('phase_started', 'Consolidando descubrimientos', 'info')
        session.save()
        
        logger.info(f"[Logic Training] 🗄️  FASE 3: Inferencia de tablas")
        
        # Consolidar usando lógica de VB6FormAnalyzer
        consolidated = self.form_analyzer._consolidate_analysis(
            discoveries['entities'],
            discoveries['tables'],
            discoveries['relations'],
            discoveries['rules']
        )
        
        session.entities_discovered = consolidated['entidades_funcionales']
        session.tables_suggested = consolidated['tablas_sugeridas']
        session.relations_found = consolidated['relaciones_candidatas']
        session.progress_percentage = 75.0
        session.add_log(
            'infer_completed',
            f'{len(consolidated["tablas_sugeridas"])} tablas consolidadas',
            'success'
        )
        session.save()
        
        logger.info(
            f"[Logic Training] ✅ Consolidación completada\n"
            f"  🏷️  Entidades: {len(consolidated['entidades_funcionales'])}\n"
            f"  🗄️  Tablas: {len(consolidated['tablas_sugeridas'])}"
        )
    
    def _phase_validate(self, session: LogicTrainingSession):
        """Fase 4: Validación en MySQL"""
        session.current_phase = 'validate'
        session.progress_percentage = 80.0
        session.add_log('phase_started', 'Validando tablas en MySQL', 'info')
        session.save()
        
        logger.info(f"[Logic Training] ✅ FASE 4: Validación MySQL")
        
        validated_fields = {}
        tables_verified = 0
        total_fields = 0
        matched_fields = 0
        
        for table_info in session.tables_suggested:
            table_name = table_info.get('nombre')
            suggested_fields = table_info.get('campos_clave_sugeridos', [])
            
            session.current_item = f"Validando {table_name}"
            session.save()
            
            # Verificar en MySQL
            schema_info = self.mysql_tool.get_schema_info(table_name)
            
            if schema_info['success'] and len(schema_info['data']) > 0:
                tables_verified += 1
                real_columns = [col['column_name'] for col in schema_info['data']]
                matched = [f for f in suggested_fields if f in real_columns]
                
                validated_fields[table_name] = {
                    'exists': True,
                    'total_columns': len(schema_info['data']),
                    'suggested_fields': suggested_fields,
                    'matched_fields': matched,
                    'match_rate': len(matched) / len(suggested_fields) if suggested_fields else 0
                }
                
                total_fields += len(suggested_fields)
                matched_fields += len(matched)
                
                session.add_log(
                    'table_validated',
                    f'{table_name}: {len(matched)}/{len(suggested_fields)} campos coinciden',
                    'success'
                )
            else:
                validated_fields[table_name] = {
                    'exists': False,
                    'suggested_fields': suggested_fields
                }
                session.add_log('table_not_found', f'{table_name} no existe en MySQL', 'warning')
        
        session.fields_validated = validated_fields
        session.tables_verified = tables_verified
        session.fields_match_rate = (matched_fields / total_fields) if total_fields > 0 else 0
        session.progress_percentage = 90.0
        session.save()
        
        logger.info(
            f"[Logic Training] ✅ Validación completada\n"
            f"  🗄️  Tablas verificadas: {tables_verified}/{len(session.tables_suggested)}\n"
            f"  🔑 Campos coincidentes: {matched_fields}/{total_fields}"
        )
    
    def _phase_extract_rules(self, session: LogicTrainingSession, categories: Optional[List[str]]):
        """Fase 5: Extracción de reglas de negocio"""
        session.current_phase = 'extract'
        session.progress_percentage = 92.0
        session.add_log('phase_started', 'Extrayendo reglas de negocio', 'info')
        session.save()
        
        logger.info(f"[Logic Training] 📚 FASE 5: Extracción de reglas")
        
        all_rules = []
        
        if not categories:
            categories = ['inventario', 'ventas', 'clientes', 'cobranzas', 'general']
        
        for category in categories:
            vb6_rules = self.vb6_analyzer.extract_business_rules(category)
            all_rules.extend(vb6_rules.get('rules', []))
        
        session.rules_extracted = all_rules
        session.progress_percentage = 95.0
        session.add_log('extract_completed', f'{len(all_rules)} reglas extraídas', 'success')
        session.save()
        
        logger.info(f"[Logic Training] ✅ {len(all_rules)} reglas extraídas")
    
    def _phase_save(self, session: LogicTrainingSession):
        """Fase 6: Guardado final de resultados"""
        session.current_phase = 'save'
        session.progress_percentage = 97.0
        session.add_log('phase_started', 'Guardando resultados en BD', 'info')
        session.save()
        
        logger.info(f"[Logic Training] 💾 FASE 6: Guardado final")
        
        # Calcular métricas finales
        if session.total_forms > 0:
            session.success_rate = (session.analyzed_forms / session.total_forms) * 100
        
        if session.tables_suggested:
            confidences = [t.get('confianza', 0) for t in session.tables_suggested]
            session.avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        session.progress_percentage = 100.0
        session.add_log('save_completed', 'Resultados guardados exitosamente', 'success')
        session.save()
        
        logger.info(
            f"[Logic Training] ✅ Guardado completado\n"
            f"  📊 Tasa de éxito: {session.success_rate:.1f}%\n"
            f"  📈 Confianza promedio: {session.avg_confidence:.2f}"
        )
    
    def get_session_progress(self, session_id: str) -> Dict[str, Any]:
        """
        Obtiene el progreso actual de una sesión
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Dict con estado actual
        """
        try:
            session = LogicTrainingSession.objects.get(session_id=session_id)
            
            # Calcular tiempo estimado restante
            from django.utils import timezone
            elapsed = 0
            estimated_remaining = 0
            
            if session.start_time:
                elapsed = (timezone.now() - session.start_time).total_seconds()
                
                if session.progress_percentage > 0:
                    total_estimated = elapsed / (session.progress_percentage / 100)
                    estimated_remaining = max(0, total_estimated - elapsed)
            
            # Calcular campos validados de forma segura
            total_matched_fields = 0
            if isinstance(session.fields_validated, dict):
                for key, value in session.fields_validated.items():
                    if isinstance(value, dict) and 'matched_fields' in value:
                        total_matched_fields += len(value.get('matched_fields', []))
            
            return {
                'session_id': session_id,
                'status': session.status,
                'phase': session.current_phase,
                'current_item': session.current_item,
                'progress_percentage': session.progress_percentage,
                'progress': {
                    'percentage': session.progress_percentage,
                    'current': session.analyzed_forms,
                    'total': session.total_forms
                },
                'stats': {
                    'forms_analyzed': session.analyzed_forms,
                    'entities_discovered': len(session.entities_discovered) if session.entities_discovered else 0,
                    'tables_suggested': len(session.tables_suggested) if session.tables_suggested else 0,
                    'fields_validated': total_matched_fields,
                    'relations_found': len(session.relations_found) if session.relations_found else 0,
                    'rules_extracted': len(session.rules_extracted) if session.rules_extracted else 0,
                    'elapsed_seconds': int(elapsed),
                    'estimated_remaining': int(estimated_remaining)
                },
                'analyzed_forms': session.analyzed_forms,
                'forms_analyzed': session.analyzed_forms,  # Para el summary (alias)
                'tables_discovered': len(session.tables_suggested) if session.tables_suggested else 0,  # Usar tables_suggested
                'fields_validated': total_matched_fields,  # Usar el calculado, no el raw
                'business_rules_created': len(session.rules_extracted) if session.rules_extracted else 0,  # Usar rules_extracted
                'tables_suggested': len(session.tables_suggested) if session.tables_suggested else 0,
                'rules_extracted': len(session.rules_extracted) if session.rules_extracted else 0,
                'recent_logs': session.log_entries[-20:] if session.log_entries else []
            }
            
        except LogicTrainingSession.DoesNotExist:
            return {
                'error': 'Session not found'
            }
    
    def cancel_training(self, session_id: str) -> Dict[str, Any]:
        """
        Cancela una sesión de entrenamiento
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            Dict con resultado
        """
        try:
            session = LogicTrainingSession.objects.get(session_id=session_id)
            
            if session.status == 'running':
                from django.utils import timezone as tz
                session.status = 'cancelled'
                session.end_time = tz.now()
                session.duration_seconds = (tz.now() - session.start_time).total_seconds()
                session.add_log('training_cancelled', 'Entrenamiento cancelado por el usuario', 'warning')
                session.save()
                
                logger.info(f"[Logic Training] ⚠️  Entrenamiento cancelado: {session_id}")
                
                return {'success': True, 'cancelled': True}
            else:
                return {'success': False, 'error': 'Session not running'}
                
        except LogicTrainingSession.DoesNotExist:
            return {'success': False, 'error': 'Session not found'}

