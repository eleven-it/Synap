"""
Comando para corregir el error de migración 0017 cuando las tablas ya existen.

Este comando debe ejecutarse en el servidor remoto cuando se obtiene el error:
    django.db.utils.ProgrammingError: relation "reports_reporttemplate" already exists

Uso:
    docker exec Synap_app python manage.py fix_migration_0017
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Marca la migración 0017 como aplicada (fake) si las tablas ya existen'

    def handle(self, *args, **options):
        """Verifica si las tablas existen y marca la migración como aplicada."""
        
        # Verificar si las tablas ya existen
        cursor = connection.cursor()
        
        tables_to_check = [
            'reports_reporttemplate',
            'reports_learnedrelationship',
            'reports_reportdefinitionversion',
        ]
        
        all_tables_exist = True
        for table_name in tables_to_check:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                );
            """, [table_name])
            exists = cursor.fetchone()[0]
            
            if exists:
                self.stdout.write(self.style.SUCCESS(f'✅ Tabla {table_name} existe'))
            else:
                self.stdout.write(self.style.ERROR(f'❌ Tabla {table_name} NO existe'))
                all_tables_exist = False
        
        cursor.close()
        
        if all_tables_exist:
            self.stdout.write(self.style.SUCCESS('\n✅ Todas las tablas existen. Marcando migración 0017 como aplicada (fake)...'))
            try:
                # Marcar la migración como aplicada sin ejecutarla
                call_command('migrate', 'reports', '0017', '--fake', verbosity=2)
                self.stdout.write(self.style.SUCCESS('✅ Migración 0017 marcada como aplicada correctamente'))
                self.stdout.write(self.style.SUCCESS('\nAhora puedes ejecutar:'))
                self.stdout.write(self.style.WARNING('  docker exec Synap_app python manage.py migrate'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error al marcar la migración: {e}'))
                self.stdout.write(self.style.WARNING('\nIntenta ejecutar manualmente:'))
                self.stdout.write(self.style.WARNING('  docker exec Synap_app python manage.py migrate reports 0017 --fake'))
        else:
            self.stdout.write(self.style.WARNING('\n⚠️  No todas las tablas existen. No se puede marcar la migración como aplicada.'))
            self.stdout.write(self.style.WARNING('   Ejecuta las migraciones normalmente:'))
            self.stdout.write(self.style.WARNING('  docker exec Synap_app python manage.py migrate'))

