"""
Comando para construir el catálogo de sinónimos (negocio ↔ columnas)
"""
from django.core.management.base import BaseCommand
from reports_ai.services.synonym_service import SynonymService
from reports_ai.models import SynonymMapping


class Command(BaseCommand):
    help = 'Construye el catálogo de sinónimos desde Glosario, Business Rules y Schema'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Elimina sinónimos existentes antes de construir'
        )
    
    def handle(self, *args, **options):
        clear = options['clear']
        
        self.stdout.write("═" * 80)
        self.stdout.write(
            self.style.SUCCESS(
                "\n📚 CONSTRUCCIÓN DE CATÁLOGO DE SINÓNIMOS\n"
            )
        )
        self.stdout.write("═" * 80 + "\n")
        
        # Limpiar si se solicita
        if clear:
            count_before = SynonymMapping.objects.count()
            SynonymMapping.objects.all().delete()
            self.stdout.write(
                self.style.WARNING(
                    f"   ⚠️  {count_before} sinónimos eliminados\n"
                )
            )
        
        # Construir catálogo
        service = SynonymService()
        
        try:
            service.build_synonym_catalog()
            
            # Estadísticas finales
            total = SynonymMapping.objects.count()
            by_source = {}
            for mapping in SynonymMapping.objects.all():
                source = mapping.source
                by_source[source] = by_source.get(source, 0) + 1
            
            self.stdout.write("\n" + "═" * 80)
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ CATÁLOGO CONSTRUIDO\n"
                    f"   Total de mapeos: {total}\n"
                )
            )
            
            for source, count in by_source.items():
                self.stdout.write(f"   • {source}: {count} mapeos")
            
            self.stdout.write("\n" + "═" * 80 + "\n")
            
        except Exception as e:
            self.stdout.write("\n" + "═" * 80)
            self.stdout.write(
                self.style.ERROR(
                    f"\n❌ ERROR EN CONSTRUCCIÓN\n"
                    f"   {type(e).__name__}: {str(e)}\n"
                )
            )
            self.stdout.write("═" * 80 + "\n")
            raise

