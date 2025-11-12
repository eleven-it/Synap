"""
Django management command para activar Data Analyst V2 en el sistema
"""
from django.core.management.base import BaseCommand
from reports_ai.services.crew_service import CrewService


class Command(BaseCommand):
    help = 'Activa Data Analyst V2 como agente principal del sistema'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🤖 Activando Data Analyst V2'))
        self.stdout.write('=' * 70)
        self.stdout.write('')
        
        try:
            # Crear instancia del crew service
            self.stdout.write(self.style.WARNING('Inicializando CrewService...'))
            crew = CrewService()
            
            # Intentar activar V2
            self.stdout.write(self.style.WARNING('Activando Data Analyst V2...'))
            success = crew.enable_data_analyst_v2()
            
            if success:
                self.stdout.write(self.style.SUCCESS('✅ Data Analyst V2 activado exitosamente'))
                self.stdout.write('')
                self.stdout.write('El sistema ahora usará Data Analyst V2 para:')
                self.stdout.write('  • Acceso completo al schema (463 tablas)')
                self.stdout.write('  • Generación de SQL basada en datos reales')
                self.stdout.write('  • Active learning de correcciones humanas')
                self.stdout.write('')
                self.stdout.write('💡 Para crear correcciones y entrenar:')
                self.stdout.write('   1. Ve a /reports-ai/corrections/create/')
                self.stdout.write('   2. Marca correcciones como "applied"')
                self.stdout.write('   3. Ejecuta: python manage.py train_data_analyst_active')
            else:
                self.stdout.write(self.style.WARNING('⚠️  Data Analyst V2 no pudo activarse'))
                self.stdout.write('')
                self.stdout.write('Razones posibles:')
                self.stdout.write('  • No hay configuración activa de administraNET')
                self.stdout.write('  • Error de conexión a MySQL')
                self.stdout.write('')
                self.stdout.write('El sistema usará Data Analyst original como fallback')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error: {e}'))
            self.stdout.write('')
            self.stdout.write('El sistema usará Data Analyst original')

