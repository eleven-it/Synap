"""
Comando para inicializar el módulo Reports AI
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from reports_ai.tools.glossary_tool import GlossaryTool


class Command(BaseCommand):
    help = 'Inicializa el módulo Reports AI con datos base'
    
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🚀 Inicializando Reports AI...'))
        
        # 1. Aplicar migraciones
        self.stdout.write('📦 Aplicando migraciones...')
        call_command('migrate', 'reports_ai', verbosity=0)
        self.stdout.write(self.style.SUCCESS('✓ Migraciones aplicadas'))
        
        # 2. Cargar glosario base
        self.stdout.write('📖 Cargando glosario base...')
        glossary = GlossaryTool()
        self.stdout.write(self.style.SUCCESS('✓ Glosario inicializado'))
        
        # 3. Verificar conexión MySQL
        self.stdout.write('🔌 Verificando conexión a administraNET...')
        try:
            from reports_ai.tools.mysql_tool import MySQLTool
            mysql = MySQLTool()
            if mysql.test_connection():
                self.stdout.write(self.style.SUCCESS('✓ Conexión MySQL OK'))
            else:
                self.stdout.write(self.style.WARNING('⚠ Conexión MySQL no disponible'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠ Error verificando MySQL: {e}'))
        
        # 4. Verificar API OpenAI
        self.stdout.write('🤖 Verificando API de OpenAI...')
        import os
        if os.getenv('OPENAI_API_KEY'):
            self.stdout.write(self.style.SUCCESS('✓ OpenAI API Key configurada'))
        else:
            self.stdout.write(self.style.ERROR('✗ OPENAI_API_KEY no configurada'))
        
        self.stdout.write(self.style.SUCCESS('\n✅ Reports AI inicializado correctamente'))

