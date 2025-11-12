"""
Comando para limpiar Business Rules inventadas o todas las existentes
"""
from django.core.management.base import BaseCommand
from reports_ai.models import BusinessRule
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Elimina Business Rules inventadas o todas las existentes antes del entrenamiento real'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Eliminar TODAS las business rules (no solo las inventadas)',
        )
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar la eliminación sin preguntar',
        )

    def handle(self, *args, **options):
        delete_all = options.get('all', False)
        auto_confirm = options.get('confirm', False)
        
        # Contar reglas existentes
        total_rules = BusinessRule.objects.count()
        
        if total_rules == 0:
            self.stdout.write(self.style.SUCCESS('✅ No hay business rules para eliminar'))
            return
        
        # Determinar qué eliminar
        if delete_all:
            rules_to_delete = BusinessRule.objects.all()
            message = f'Se eliminarán TODAS las {total_rules} business rules'
        else:
            # Detectar reglas "inventadas" por patrones genéricos
            rules_to_delete = BusinessRule.objects.filter(
                description__icontains='Regla de negocio para'
            ) | BusinessRule.objects.filter(
                conditions__icontains='Aplica cuando se requiere'
            ) | BusinessRule.objects.filter(
                source_file='Funciones.bas',
                source_line=0
            )
            
            count_to_delete = rules_to_delete.count()
            message = f'Se eliminarán {count_to_delete} business rules inventadas (de {total_rules} totales)'
        
        # Mostrar resumen
        self.stdout.write(self.style.WARNING('\n' + '='*70))
        self.stdout.write(self.style.WARNING('  🗑️  LIMPIEZA DE BUSINESS RULES'))
        self.stdout.write(self.style.WARNING('='*70))
        self.stdout.write(f'\n📊 {message}\n')
        
        # Mostrar ejemplos de lo que se va a eliminar
        sample_rules = list(rules_to_delete[:5])
        if sample_rules:
            self.stdout.write('\n📋 Ejemplos de reglas a eliminar:')
            for rule in sample_rules:
                self.stdout.write(
                    f'  • {rule.name} '
                    f'(Source: {rule.source_file or "N/A"}, '
                    f'Line: {rule.source_line or "N/A"})'
                )
            
            if rules_to_delete.count() > 5:
                self.stdout.write(f'  ... y {rules_to_delete.count() - 5} más')
        
        # Confirmar
        if not auto_confirm:
            self.stdout.write('\n' + '='*70)
            confirm = input('\n❓ ¿Deseas continuar? (yes/no): ')
            
            if confirm.lower() not in ['yes', 'y', 'si', 's']:
                self.stdout.write(self.style.WARNING('\n❌ Operación cancelada\n'))
                return
        
        # Eliminar
        count = rules_to_delete.count()
        rules_to_delete.delete()
        
        self.stdout.write('\n' + '='*70)
        self.stdout.write(self.style.SUCCESS(f'\n✅ {count} business rules eliminadas exitosamente\n'))
        
        remaining = BusinessRule.objects.count()
        self.stdout.write(f'📊 Business rules restantes: {remaining}\n')
        
        if remaining > 0 and not delete_all:
            self.stdout.write(
                self.style.WARNING(
                    f'\n💡 Tip: Si deseas eliminar TODAS las reglas, usa:\n'
                    f'   python manage.py clean_business_rules --all --confirm\n'
                )
            )
        
        self.stdout.write('='*70 + '\n')
        
        logger.info(f"Business Rules eliminadas: {count}, Restantes: {remaining}")

