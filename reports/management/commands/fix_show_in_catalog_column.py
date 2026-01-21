"""
Comando para agregar la columna show_in_catalog si no existe.

Este comando debe ejecutarse en el servidor remoto cuando se obtiene el error:
    django.db.utils.ProgrammingError: column reports_reportdefinition.show_in_catalog does not exist

Uso:
    docker exec Synap_app python manage.py fix_show_in_catalog_column
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = 'Agrega la columna show_in_catalog a reports_reportdefinition si no existe'

    def handle(self, *args, **options):
        """Verifica si la columna existe y la crea si no existe."""
        
        cursor = connection.cursor()
        
        # Verificar si la columna ya existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'reports_reportdefinition'
                AND column_name = 'show_in_catalog'
            );
        """)
        column_exists = cursor.fetchone()[0]
        
        if column_exists:
            self.stdout.write(self.style.SUCCESS('✅ Columna show_in_catalog ya existe'))
        else:
            self.stdout.write(self.style.WARNING('⚠️  Columna show_in_catalog NO existe. Creándola...'))
            try:
                # Agregar la columna
                cursor.execute("""
                    ALTER TABLE reports_reportdefinition 
                    ADD COLUMN show_in_catalog BOOLEAN NOT NULL DEFAULT TRUE;
                """)
                self.stdout.write(self.style.SUCCESS('✅ Columna show_in_catalog creada correctamente'))
                
                # Agregar comentario si es posible
                try:
                    cursor.execute("""
                        COMMENT ON COLUMN reports_reportdefinition.show_in_catalog IS 
                        'If enabled, the report will appear in the catalog. This is independent of visibility to users.';
                    """)
                except Exception:
                    pass  # Ignorar si no se puede agregar el comentario
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ Error al crear la columna: {e}'))
                raise
        
        cursor.close()
        
        self.stdout.write(self.style.SUCCESS('\n✅ Verificación completada'))

