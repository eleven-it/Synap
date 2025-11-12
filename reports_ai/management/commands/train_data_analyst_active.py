"""
Django management command para entrenar Data Analyst V2 con active learning
"""
from django.core.management.base import BaseCommand
from reports_ai.agents.data_analyst_v2 import DataAnalystAgentV2
from reports_ai.services.active_learning_service import ActiveLearningService
import json


class Command(BaseCommand):
    help = 'Entrena el Data Analyst V2 con active learning basado en correcciones humanas'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--report',
            action='store_true',
            help='Generar reporte de training'
        )
        parser.add_argument(
            '--test',
            type=str,
            help='Probar con una query específica después del training'
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 Active Learning Training para Data Analyst V2'))
        self.stdout.write('=' * 70)
        self.stdout.write('')
        
        # Servicio de active learning
        learning_service = ActiveLearningService()
        
        # Cargar correcciones aplicadas
        self.stdout.write(self.style.WARNING('📚 Cargando correcciones aplicadas...'))
        corrections = learning_service.load_applied_corrections()
        
        if not corrections:
            self.stdout.write(self.style.ERROR('❌ No hay correcciones aplicadas para entrenar'))
            self.stdout.write('   Crea correcciones en /reports-ai/corrections/ y márcalas como "applied"')
            return
        
        self.stdout.write(self.style.SUCCESS(f'✅ {len(corrections)} correcciones encontradas'))
        self.stdout.write('')
        
        # Extraer learnings
        self.stdout.write(self.style.WARNING('🔍 Extrayendo patrones de aprendizaje...'))
        learnings = learning_service.extract_learnings(corrections)
        
        # Mostrar learnings
        self.stdout.write(self.style.SUCCESS('✅ Learnings extraídos:'))
        self.stdout.write(f'   📝 Keywords → Tabla: {len(learnings["keyword_to_table"])}')
        self.stdout.write(f'   🔗 Relaciones: {len(learnings["table_relationships"])}')
        self.stdout.write(f'   ❌ Columnas a evitar: {len(learnings["column_avoid"])}')
        self.stdout.write(f'   ✓ Columnas preferidas: {len(learnings["column_prefer"])}')
        self.stdout.write(f'   🔗 Patrones de JOIN: {len(learnings["join_patterns"])}')
        self.stdout.write('')
        
        # Si solo queremos el reporte
        if options['report']:
            self.stdout.write(self.style.SUCCESS('📊 Reporte de Training:'))
            report = learning_service.generate_training_report()
            
            self.stdout.write('')
            self.stdout.write('Estadísticas:')
            self.stdout.write(f'  - Total de correcciones: {report["total_corrections"]}')
            self.stdout.write(f'  - Keywords aprendidas: {report["total_keywords_learned"]}')
            self.stdout.write(f'  - Relaciones aprendidas: {report["total_relationships_learned"]}')
            
            if report['corrections_by_type']:
                self.stdout.write('')
                self.stdout.write('Por tipo de corrección:')
                for corr_type, count in report['corrections_by_type'].items():
                    self.stdout.write(f'  - {corr_type}: {count}')
            
            return
        
        # Inicializar agente
        self.stdout.write(self.style.WARNING('🤖 Inicializando Data Analyst V2...'))
        agent = DataAnalystAgentV2()
        
        # Aplicar learnings al agente
        self.stdout.write(self.style.WARNING('📚 Aplicando learnings al agente...'))
        learning_service.apply_learnings_to_agent(agent, learnings)
        
        self.stdout.write(self.style.SUCCESS('✅ Training completado'))
        self.stdout.write('')
        
        # Marcar training como completo
        learning_service.mark_training_complete()
        
        # Probar con query específica si se proporciona
        if options['test']:
            test_query = options['test']
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS(f'🧪 Probando con query: {test_query}'))
            self.stdout.write('-' * 70)
            
            input_data = {
                'query': test_query,
                'periodo': {},
                'filters': {},
                'limit': 5
            }
            
            result = agent.execute(input_data)
            
            if result['success']:
                self.stdout.write(self.style.SUCCESS('✅ Query ejecutada exitosamente'))
                self.stdout.write(f'   Registros: {result["row_count"]}')
                self.stdout.write('')
                self.stdout.write('SQL generado:')
                self.stdout.write(self.style.SUCCESS(result['sql_query'][:200]))
            else:
                self.stdout.write(self.style.ERROR(f'❌ Error: {result.get("error")}'))
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✅ Proceso completado'))

