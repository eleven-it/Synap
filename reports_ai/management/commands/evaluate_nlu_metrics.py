"""
Comando para evaluar métricas del NLU
"""
from django.core.management.base import BaseCommand
from reports_ai.services.nlu_training_service import NLUTrainingService


class Command(BaseCommand):
    help = 'Evalúa métricas de calidad del NLU'
    
    def handle(self, *args, **options):
        self.stdout.write('📊 Iniciando evaluación del NLU...\n')
        
        service = NLUTrainingService()
        result = service.evaluate_weekly()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Evaluación completada:\n"
                f"  • Periodo: {result['period']}\n"
                f"  • Total consultas: {result['total_queries']}\n"
                f"  • Cobertura: {result['coverage_rate']:.1f}% (target: ≥95%)\n"
                f"  • Error enrutamiento: {result['misroute_rate']:.1f}% (target: ≤3%)\n"
                f"  • Aclaración: {result['clarification_rate']:.1f}% (target: 3-8%)\n"
                f"  • Requiere reentrenamiento: {'SÍ' if result['needs_retraining'] else 'NO'}\n"
            )
        )
        
        if result['needs_retraining']:
            self.stdout.write(
                self.style.WARNING(
                    "\n⚠️  Se recomienda ejecutar reentrenamiento incremental:\n"
                    "   python manage.py train_nlu_incremental\n"
                )
            )

