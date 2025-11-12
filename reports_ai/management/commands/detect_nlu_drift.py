"""
Comando para detectar deriva del modelo NLU
"""
from django.core.management.base import BaseCommand
from reports_ai.services.nlu_training_service import NLUTrainingService


class Command(BaseCommand):
    help = 'Detecta deriva del modelo NLU comparando contra ejemplos canónicos'
    
    def handle(self, *args, **options):
        self.stdout.write('🔍 Iniciando detección de deriva del NLU...\n')
        
        service = NLUTrainingService()
        result = service.detect_drift()
        
        if result['drift_detected']:
            self.stdout.write(
                self.style.WARNING(
                    f"\n⚠️  DERIVA DETECTADA:\n"
                    f"  • Ejemplos canónicos: {result['canonical_count']}\n"
                    f"  • Accuracy: {result.get('accuracy_on_canonical', 0):.1f}%\n"
                    f"  • Versión actual: {result['model_version']}\n"
                    f"\n  🔧 Acción requerida: Reentrenar incrementalmente\n"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ No se detectó deriva:\n"
                    f"  • Ejemplos canónicos: {result['canonical_count']}\n"
                    f"  • Accuracy: {result.get('accuracy_on_canonical', 0):.1f}%\n"
                    f"  • Versión actual: {result['model_version']}\n"
                    f"  • Mensaje: {result['message']}\n"
                )
            )

