"""
Comando para entrenar el Logic Interpreter en modo GUIADO
desde el catálogo funcional
"""
from django.core.management.base import BaseCommand
from reports_ai.models import FunctionalCatalog
from reports_ai.services.guided_training_service import GuidedTrainingService


class Command(BaseCommand):
    help = 'Entrena el Logic Interpreter en modo GUIADO desde el catálogo funcional'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--module',
            type=str,
            help='Entrenar solo un módulo específico (ej: Ventas)',
        )
        parser.add_argument(
            '--procedure',
            type=str,
            help='Entrenar solo un procedimiento específico (ej: Crear pedido)',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Entrenar desde TODAS las entradas activas del catálogo',
        )
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('\n🎯 ENTRENAMIENTO GUIADO DEL LOGIC INTERPRETER'))
        self.stdout.write('='*70 + '\n')
        
        service = GuidedTrainingService()
        
        # Determinar qué entrenar
        if options['all']:
            # Entrenar todas las entradas activas
            self.stdout.write('📚 Entrenando desde TODAS las entradas activas del catálogo...\n')
            
            summary = service.get_catalog_entries_summary()
            
            self.stdout.write(f'📊 Total de entradas activas: {summary["active_entries"]}')
            self.stdout.write('\nMódulos disponibles:')
            for module, data in summary['entries_by_module'].items():
                self.stdout.write(f'  • {module}: {data["count"]} procedimientos (confianza promedio: {data["avg_confidence"]:.2f})')
            self.stdout.write('')
            
            # Entrenar
            results = service.train_all_active_catalog_entries()
            
            # Resumen final
            self.stdout.write('\n' + '='*70)
            self.stdout.write(self.style.SUCCESS('📊 RESUMEN DEL ENTRENAMIENTO'))
            self.stdout.write('='*70 + '\n')
            
            self.stdout.write(f'✅ Entradas exitosas: {results["successful_entries"]}/{results["total_entries"]}')
            self.stdout.write(f'❌ Entradas fallidas: {results["failed_entries"]}/{results["total_entries"]}')
            self.stdout.write(f'📋 Total de Business Rules creadas: {results["total_business_rules"]}')
            self.stdout.write(f'📈 Tasa de éxito: {results["summary"]["success_rate"]:.1f}%')
            self.stdout.write('')
            
            # Detalle por entrada
            if results['entries_detail']:
                self.stdout.write('Detalle por procedimiento:')
                for entry in results['entries_detail']:
                    status_icon = '✅' if entry['success'] else '❌'
                    self.stdout.write(f'{status_icon} {entry["module"]} - {entry["procedure"]}')
                    self.stdout.write(f'    Rules: {entry["business_rules_created"]} | '
                                    f'Tablas: {entry["tables"]} | '
                                    f'Validaciones: {entry["validations"]} | '
                                    f'Relaciones: {entry["relationships"]}')
                    
                    if entry.get('errors'):
                        for error in entry['errors']:
                            self.stdout.write(self.style.ERROR(f'    Error: {error}'))
                    self.stdout.write('')
        
        elif options['procedure'] and options['module']:
            # Entrenar un procedimiento específico
            try:
                catalog_entry = FunctionalCatalog.objects.get(
                    module=options['module'],
                    procedure=options['procedure'],
                    is_active=True
                )
            except FunctionalCatalog.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'❌ No se encontró: {options["module"]} - {options["procedure"]}'))
                return
            
            self.stdout.write(f'🎯 Entrenando procedimiento específico:')
            self.stdout.write(f'   Módulo: {catalog_entry.module}')
            self.stdout.write(f'   Procedimiento: {catalog_entry.procedure}')
            self.stdout.write(f'   Formularios: {catalog_entry.vb6_forms}')
            self.stdout.write(f'   Confianza inicial: {catalog_entry.confidence}')
            self.stdout.write('')
            
            results = service.train_from_catalog_entry(catalog_entry)
            
            # Resumen
            self.stdout.write('\n' + '='*70)
            self.stdout.write(self.style.SUCCESS('📊 RESULTADOS'))
            self.stdout.write('='*70 + '\n')
            
            if results.get('success', False):
                self.stdout.write(self.style.SUCCESS('✅ Entrenamiento exitoso'))
                self.stdout.write(f'📋 Business Rules creadas: {results["business_rules_created"]}')
                self.stdout.write(f'🗄️  Tablas descubiertas: {len(results["tables_discovered"])}')
                self.stdout.write(f'✓ Validaciones: {len(results["validations_discovered"])}')
                self.stdout.write(f'🔗 Relaciones: {len(results["relationships_discovered"])}')
            else:
                self.stdout.write(self.style.ERROR('❌ Entrenamiento falló'))
                for error in results.get('errors', []):
                    self.stdout.write(self.style.ERROR(f'   Error: {error}'))
        
        else:
            # No se especificó qué entrenar
            self.stdout.write(self.style.WARNING('⚠️  Debes especificar qué entrenar:'))
            self.stdout.write('')
            self.stdout.write('Opciones:')
            self.stdout.write('  1. Entrenar TODO:  python manage.py train_guided --all')
            self.stdout.write('  2. Entrenar uno:   python manage.py train_guided --module "Ventas" --procedure "Crear pedido"')
            self.stdout.write('')
            
            # Mostrar entradas disponibles
            summary = service.get_catalog_entries_summary()
            
            if summary['active_entries'] > 0:
                self.stdout.write('📚 Entradas activas disponibles:')
                for module, data in summary['entries_by_module'].items():
                    self.stdout.write(f'   Módulo: {module} ({data["count"]} procedimientos)')
                    for proc in data['procedures'][:3]:
                        self.stdout.write(f'      • {proc["name"]}')
            else:
                self.stdout.write(self.style.ERROR('❌ No hay entradas activas en el catálogo'))
                self.stdout.write('   Ejecuta primero: python manage.py load_catalog_pedido')
        
        self.stdout.write('='*70 + '\n')

