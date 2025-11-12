"""
Comando para eliminar todas las relaciones descubiertas
Útil para comenzar con un catálogo limpio después de ajustar los criterios
"""
from django.core.management.base import BaseCommand
from reports_ai.models import RelationshipCandidate


class Command(BaseCommand):
    help = 'Elimina todas las relaciones descubiertas del catálogo'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirmar la eliminación sin interacción',
        )

    def handle(self, *args, **options):
        self.stdout.write("\n🗑️  Eliminación de Relaciones Descubiertas")
        self.stdout.write("=" * 60)
        
        # Contar relaciones actuales
        total_relationships = RelationshipCandidate.objects.count()
        
        if total_relationships == 0:
            self.stdout.write(self.style.SUCCESS("\n✅ No hay relaciones en el catálogo."))
            return
        
        self.stdout.write(f"\n📊 Relaciones encontradas: {total_relationships}")
        
        # Estadísticas adicionales
        validated = RelationshipCandidate.objects.filter(validated_by_human=True).count()
        high_confidence = RelationshipCandidate.objects.filter(confidence_score__gte=0.80).count()
        with_logic_hint = RelationshipCandidate.objects.filter(logic_interpreter_hint=True).count()
        
        self.stdout.write(f"   • Validadas por humano: {validated}")
        self.stdout.write(f"   • Alta confianza (≥0.80): {high_confidence}")
        self.stdout.write(f"   • Con hint del Logic Interpreter: {with_logic_hint}")
        
        # Confirmación
        if not options['confirm']:
            self.stdout.write(self.style.WARNING(
                "\n⚠️  Esta acción eliminará TODAS las relaciones descubiertas."
            ))
            response = input("¿Deseas continuar? (sí/no): ")
            
            if response.lower() not in ['sí', 'si', 'yes', 's', 'y']:
                self.stdout.write(self.style.WARNING("\n❌ Operación cancelada."))
                return
        
        # Eliminar todas las relaciones
        self.stdout.write("\n🔥 Eliminando relaciones...")
        
        deleted_count, _ = RelationshipCandidate.objects.all().delete()
        
        self.stdout.write(self.style.SUCCESS(
            f"\n✅ Eliminadas {deleted_count} relaciones del catálogo."
        ))
        self.stdout.write(self.style.SUCCESS(
            "\n💡 Ahora puedes ejecutar 'docker exec Synap_app python manage.py discover_relationships' "
            "para generar nuevas relaciones con los criterios actualizados."
        ))




