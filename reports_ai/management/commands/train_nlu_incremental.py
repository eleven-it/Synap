"""
Comando para entrenamiento incremental del NLU
"""
from django.core.management.base import BaseCommand
from reports_ai.services.nlu_training_service import NLUTrainingService


class Command(BaseCommand):
    help = 'Entrena el NLU de forma incremental con nuevos ejemplos'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--max-examples',
            type=int,
            default=100,
            help='Máximo de ejemplos nuevos a usar'
        )
    
    def handle(self, *args, **options):
        max_examples = options['max_examples']
        
        self.stdout.write('🎓 Iniciando entrenamiento incremental del NLU...\n')
        
        service = NLUTrainingService()
        result = service.train_incremental(max_examples=max_examples)
        
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Entrenamiento completado:\n"
                    f"  • Ejemplos agregados: {result['examples_added']}\n"
                    f"  • Total ejemplos: {result['total_examples']}\n"
                    f"  • Ejemplos canónicos: {result['canonical_examples']}\n"
                )
            )
        else:
            self.stdout.write(self.style.ERROR(f"\n❌ Error: {result.get('error')}"))

