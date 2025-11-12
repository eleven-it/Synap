"""
Comando para generar reporte de calidad del Data Analyst
"""
from django.core.management.base import BaseCommand
from reports_ai.services.quality_metrics import QualityMetricsService


class Command(BaseCommand):
    help = 'Genera reporte de calidad del Data Analyst Agent'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--period',
            type=int,
            default=7,
            help='Días hacia atrás para analizar (default: 7)'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Salida en formato JSON'
        )
    
    def handle(self, *args, **options):
        period_days = options['period']
        json_output = options['json']
        
        service = QualityMetricsService()
        
        if json_output:
            # Salida JSON
            import json
            metrics = service.calculate_all_metrics(period_days=period_days)
            self.stdout.write(json.dumps(metrics, indent=2, default=str))
        else:
            # Salida texto formateado
            report = service.generate_report(period_days=period_days)
            self.stdout.write(report)

