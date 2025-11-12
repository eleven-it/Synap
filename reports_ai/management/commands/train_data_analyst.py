"""
Comando maestro para entrenar el Data Analyst Agent
Ejecuta todos los pasos de descubrimiento y entrenamiento
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from reports_ai.models import RelationshipCandidate, SynonymMapping, ColumnStatistics
import time


class Command(BaseCommand):
    help = 'Entrena el Data Analyst Agent (descubrimiento + sinónimos + métricas)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--min-confidence',
            type=float,
            default=0.6,
            help='Score mínimo para relaciones (default: 0.6)'
        )
        parser.add_argument(
            '--skip-relationships',
            action='store_true',
            help='Saltar descubrimiento de relaciones'
        )
        parser.add_argument(
            '--skip-synonyms',
            action='store_true',
            help='Saltar construcción de sinónimos'
        )
        parser.add_argument(
            '--clear-synonyms',
            action='store_true',
            help='Limpiar sinónimos existentes'
        )
    
    def handle(self, *args, **options):
        start_time = time.time()
        
        self.stdout.write("\n" + "═" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                "\n🚀 ENTRENAMIENTO DEL DATA ANALYST AGENT\n"
            )
        )
        self.stdout.write("═" * 80 + "\n")
        
        # Paso 1: Descubrir relaciones
        if not options['skip_relationships']:
            self.stdout.write(
                self.style.WARNING(
                    "\n📍 PASO 1: Descubriendo relaciones entre tablas...\n"
                )
            )
            call_command('discover_relationships', min_confidence=options['min_confidence'])
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\n⏭️  PASO 1: Descubrimiento de relaciones OMITIDO\n"
                )
            )
        
        # Paso 2: Construir catálogo de sinónimos
        if not options['skip_synonyms']:
            self.stdout.write(
                self.style.WARNING(
                    "\n📍 PASO 2: Construyendo catálogo de sinónimos...\n"
                )
            )
            call_command('build_synonym_catalog', clear=options['clear_synonyms'])
        else:
            self.stdout.write(
                self.style.WARNING(
                    "\n⏭️  PASO 2: Construcción de sinónimos OMITIDA\n"
                )
            )
        
        # Paso 3: Mostrar resumen
        duration = time.time() - start_time
        
        relationships = RelationshipCandidate.objects.count()
        high_conf_rels = RelationshipCandidate.objects.filter(confidence_score__gte=0.8).count()
        synonyms = SynonymMapping.objects.count()
        column_stats = ColumnStatistics.objects.count()
        
        self.stdout.write("\n" + "═" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ ENTRENAMIENTO COMPLETADO\n"
                f"\n📊 ESTADÍSTICAS FINALES:\n"
                f"   • Relaciones descubiertas: {relationships}\n"
                f"   • Relaciones alta confianza (≥0.8): {high_conf_rels}\n"
                f"   • Mapeos de sinónimos: {synonyms}\n"
                f"   • Estadísticas de columnas: {column_stats}\n"
                f"\n⏱️  Duración total: {duration:.2f}s\n"
            )
        )
        self.stdout.write("═" * 80 + "\n")
        
        # Recomendaciones
        self.stdout.write(
            self.style.WARNING(
                "\n💡 PRÓXIMOS PASOS:\n"
                "   1. Revisar relaciones con baja confianza\n"
                "   2. Validar manualmente relaciones críticas\n"
                "   3. Probar consultas de negocio\n"
                "   4. Monitorear métricas de calidad\n"
            )
        )
        self.stdout.write("\n")

