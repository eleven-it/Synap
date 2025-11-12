"""
Comando para eliminar TODAS las Business Rules
Permite recrearlas con el nuevo método de entrenamiento guiado
"""
from django.core.management.base import BaseCommand
from reports_ai.models import BusinessRule


class Command(BaseCommand):
    help = 'Elimina TODAS las Business Rules existentes para recrearlas con el método guiado'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmación explícita para eliminar las reglas',
        )
    
    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(self.style.WARNING('\n⚠️  ADVERTENCIA'))
            self.stdout.write('='*70)
            self.stdout.write('Este comando eliminará TODAS las Business Rules.')
            self.stdout.write('')
            self.stdout.write('Uso: python manage.py clean_all_business_rules --confirm')
            self.stdout.write('='*70 + '\n')
            return
        
        # Contar total
        total_count = BusinessRule.objects.count()
        
        self.stdout.write(self.style.WARNING('\n🗑️  ELIMINANDO TODAS LAS BUSINESS RULES'))
        self.stdout.write('='*70)
        self.stdout.write(f'📊 Total de Business Rules a eliminar: {total_count}\n')
        
        if total_count == 0:
            self.stdout.write(self.style.SUCCESS('✅ No hay Business Rules para eliminar.'))
            return
        
        # Mostrar algunas para confirmación
        sample = BusinessRule.objects.all()[:5]
        self.stdout.write('Algunas reglas a eliminar:')
        for rule in sample:
            self.stdout.write(f'  • {rule.name} ({rule.category})')
        if total_count > 5:
            self.stdout.write(f'  ... y {total_count - 5} más')
        
        # Eliminar
        self.stdout.write('\n🗑️  Eliminando todas las Business Rules...\n')
        
        deleted_count = BusinessRule.objects.all().delete()[0]
        
        self.stdout.write('='*70)
        self.stdout.write(self.style.SUCCESS(f'✅ Business Rules eliminadas: {deleted_count}'))
        self.stdout.write('='*70 + '\n')
        
        # Próximos pasos
        self.stdout.write('🎯 PRÓXIMOS PASOS:')
        self.stdout.write('')
        self.stdout.write('1. Entrenar con método GUIADO usando el catálogo funcional:')
        self.stdout.write('   http://localhost:8002/reports-ai/train/logic-interpreter/')
        self.stdout.write('')
        self.stdout.write('2. Entrenar procedimiento "Crear Pedido" puntualmente:')
        self.stdout.write('   → http://localhost:8002/reports-ai/train/logic-interpreter/')
        self.stdout.write('   → Seleccionar: Modo GUIADO')
        self.stdout.write('   → Analizar: Pedido.frm (2-3 minutos)')
        self.stdout.write('')
        self.stdout.write('3. Probar en el chat:')
        self.stdout.write('   http://localhost:8002/reports-ai/chat/')
        self.stdout.write('   → "Como crear un pedido"')
        self.stdout.write('')
        self.stdout.write('✅ Sistema listo para entrenamiento guiado')
        self.stdout.write('')

