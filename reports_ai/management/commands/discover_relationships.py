"""
Comando para descubrir relaciones automáticamente entre tablas
"""
from django.core.management.base import BaseCommand
from reports_ai.services.relationship_discovery import RelationshipDiscoveryService


class Command(BaseCommand):
    help = 'Descubre relaciones entre tablas automáticamente (sin FKs formales)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.6,
            help='Score mínimo de confianza para guardar relación (default: 0.6)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Fuerza la actualización de estadísticas aunque estén frescas'
        )
        parser.add_argument(
            '--no-logic-interpreter',
            action='store_true',
            help='Deshabilita integración con Logic Interpreter'
        )
    
    def handle(self, *args, **options):
        min_confidence = options['min_confidence']
        use_logic_interpreter = not options['no_logic_interpreter']
        
        self.stdout.write("═" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                "\n🔍 DESCUBRIMIENTO AUTOMÁTICO DE RELACIONES\n"
            )
        )
        self.stdout.write("═" * 80)
        
        if use_logic_interpreter:
            self.stdout.write("\n🧠 Integración con Logic Interpreter: HABILITADA")
        else:
            self.stdout.write("\n⚠️  Integración con Logic Interpreter: DESHABILITADA")
        
        service = RelationshipDiscoveryService()
        
        try:
            # Descubrir relaciones
            count = service.discover_all_relationships(
                min_confidence=min_confidence,
                use_logic_interpreter=use_logic_interpreter
            )
            
            self.stdout.write("\n" + "═" * 80)
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ DESCUBRIMIENTO COMPLETADO\n"
                    f"   Relaciones descubiertas: {count}\n"
                    f"   Umbral de confianza: {min_confidence}\n"
                )
            )
            self.stdout.write("═" * 80 + "\n")
            
        except Exception as e:
            self.stdout.write("\n" + "═" * 80)
            self.stdout.write(
                self.style.ERROR(
                    f"\n❌ ERROR EN DESCUBRIMIENTO\n"
                    f"   {type(e).__name__}: {str(e)}\n"
                )
            )
            self.stdout.write("═" * 80 + "\n")
            raise

