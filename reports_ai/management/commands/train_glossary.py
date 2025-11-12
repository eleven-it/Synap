"""
Comando para entrenar/actualizar el glosario desde código VB6
"""
from django.core.management.base import BaseCommand
from reports_ai.tools.vb6_analyzer import VB6AnalyzerTool
from reports_ai.tools.glossary_tool import GlossaryTool


class Command(BaseCommand):
    help = 'Extrae términos del glosario desde código VB6'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('📚 Extrayendo términos desde código VB6...'))
        
        vb6_analyzer = VB6AnalyzerTool()
        glossary_tool = GlossaryTool()
        
        # Extraer términos
        terms = vb6_analyzer.get_business_glossary_from_code()
        
        self.stdout.write(f'✓ Encontrados {len(terms)} términos')
        
        # Agregar al glosario
        added = 0
        for term, definition in terms.items():
            if glossary_tool.add_term(
                term=term,
                definition=definition,
                category='Extraído de Código',
                synonyms=[],
                examples=[]
            ):
                added += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Agregados {added} términos al glosario'))

