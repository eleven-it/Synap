"""
Comando para analizar código VB6 y extraer reglas de negocio
"""
from django.core.management.base import BaseCommand
from reports_ai.tools.vb6_analyzer import VB6AnalyzerTool
from reports_ai.models import BusinessRule


class Command(BaseCommand):
    help = 'Analiza código VB6 y extrae reglas de negocio'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--module',
            type=str,
            default='general',
            help='Módulo a analizar (ventas, inventario, general, etc.)'
        )
    
    def handle(self, *args, **options):
        module = options['module']
        
        self.stdout.write(self.style.SUCCESS(f'🔍 Analizando módulo: {module}'))
        
        analyzer = VB6AnalyzerTool()
        
        # Extraer reglas
        result = analyzer.extract_business_rules(module)
        rules = result.get('rules', [])
        
        self.stdout.write(f'✓ Encontradas {len(rules)} reglas')
        
        # Guardar en BD
        saved = 0
        for rule in rules:
            code = f"{module}_{rule.get('concept', 'rule')}".replace(' ', '_').lower()
            
            BusinessRule.objects.get_or_create(
                code=code,
                defaults={
                    'name': rule.get('concept', 'Regla sin nombre'),
                    'rule_type': rule.get('type', 'calculation'),
                    'description': rule.get('description', ''),
                    'module': module.capitalize(),
                    'is_active': True
                }
            )
            saved += 1
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Guardadas {saved} reglas en la base de datos'))

