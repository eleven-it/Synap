from django.core.management.base import BaseCommand
from django.db import connections
from django.conf import settings
import sys


class Command(BaseCommand):
    help = 'Verificar conexión y estado de la base de datos administraNET'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Mostrar información detallada de las tablas',
        )
        parser.add_argument(
            '--test-queries',
            action='store_true',
            help='Ejecutar consultas de prueba',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔧 Verificador de Conexión administraNET')
        )
        self.stdout.write('=' * 50)

        # Verificar configuración
        self.check_connection_settings()

        # Probar conexión MySQL
        if not self.test_mysql_connection():
            sys.exit(1)

        # Verificar información de la base de datos
        self.check_database_info()

        # Verificar tablas principales
        if not self.check_administraNET_tables():
            self.stdout.write(
                self.style.WARNING(
                    '\n⚠️  No se encontraron tablas principales de administraNET'
                )
            )
            self.stdout.write(
                self.style.WARNING('   Verifica que la base de datos sea correcta')
            )

        # Información detallada si se solicita
        if options['detailed']:
            self.show_detailed_info()

        # Consultas de prueba si se solicita
        if options['test_queries']:
            self.test_sample_queries()

        self.stdout.write('=' * 50)
        self.stdout.write(
            self.style.SUCCESS('✅ Verificación completada')
        )

    def check_connection_settings(self):
        """Verificar configuración de conexión"""
        self.stdout.write('\n⚙️  Configuración de conexión:')
        
        db_settings = settings.DATABASES.get('mysql', {})
        
        self.stdout.write(f'   Host: {db_settings.get("HOST", "N/A")}')
        self.stdout.write(f'   Puerto: {db_settings.get("PORT", "N/A")}')
        self.stdout.write(f'   Base de datos: {db_settings.get("NAME", "N/A")}')
        self.stdout.write(f'   Usuario: {db_settings.get("USER", "N/A")}')
        self.stdout.write(f'   Motor: {db_settings.get("ENGINE", "N/A")}')

    def test_mysql_connection(self):
        """Verificar conexión básica a MySQL"""
        try:
            with connections['mysql'].cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                version = cursor.fetchone()
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Conexión exitosa a MySQL')
                )
                self.stdout.write(f'   Versión: {version[0]}')
                return True
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error de conexión MySQL: {e}')
            )
            return False

    def check_administraNET_tables(self):
        """Verificar tablas principales de administraNET"""
        tables_to_check = [
            'stock',
            'stock_deposito', 
            'articulos',
            'depositos',
            'clientes',
            'proveedores',
            'lote',
            'lote_stock',
            'pedidos',
            'pedidos_detalle'
        ]
        
        found_tables = []
        missing_tables = []
        
        try:
            with connections['mysql'].cursor() as cursor:
                for table in tables_to_check:
                    cursor.execute("SHOW TABLES LIKE %s", [table])
                    if cursor.fetchone():
                        # Contar registros
                        cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                        count = cursor.fetchone()[0]
                        found_tables.append((table, count))
                    else:
                        missing_tables.append(table)
            
            # Mostrar resultados
            if found_tables:
                self.stdout.write('\n📋 Tablas encontradas:')
                for table, count in found_tables:
                    self.stdout.write(
                        self.style.SUCCESS(f'   ✅ {table}: {count:,} registros')
                    )
            
            if missing_tables:
                self.stdout.write('\n⚠️  Tablas no encontradas:')
                for table in missing_tables:
                    self.stdout.write(
                        self.style.ERROR(f'   ❌ {table}')
                    )
            
            return len(found_tables) > 0
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error verificando tablas: {e}')
            )
            return False

    def check_database_info(self):
        """Obtener información general de la base de datos"""
        try:
            with connections['mysql'].cursor() as cursor:
                # Obtener nombre de la base de datos
                cursor.execute("SELECT DATABASE()")
                db_name = cursor.fetchone()[0]
                self.stdout.write(f'\n🗄️  Base de datos: {db_name}')
                
                # Obtener todas las tablas
                cursor.execute("SHOW TABLES")
                all_tables = [row[0] for row in cursor.fetchall()]
                self.stdout.write(f'   Total de tablas: {len(all_tables)}')
                
                # Obtener tamaño aproximado de la base de datos
                cursor.execute("""
                    SELECT 
                        ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'DB Size in MB'
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                """)
                db_size = cursor.fetchone()[0]
                self.stdout.write(f'   Tamaño aproximado: {db_size} MB')
                
                return True
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error obteniendo información de BD: {e}')
            )
            return False

    def show_detailed_info(self):
        """Mostrar información detallada de las tablas"""
        self.stdout.write('\n📊 Información detallada:')
        
        try:
            with connections['mysql'].cursor() as cursor:
                # Obtener todas las tablas con información
                cursor.execute("""
                    SELECT 
                        table_name,
                        table_rows,
                        ROUND(((data_length + index_length) / 1024 / 1024), 2) AS 'Size_MB'
                    FROM information_schema.tables 
                    WHERE table_schema = DATABASE()
                    ORDER BY (data_length + index_length) DESC
                    LIMIT 20
                """)
                
                tables_info = cursor.fetchall()
                
                for table_name, rows, size in tables_info:
                    self.stdout.write(
                        f'   📋 {table_name}: {rows:,} filas, {size} MB'
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error obteniendo información detallada: {e}')
            )

    def test_sample_queries(self):
        """Probar consultas de ejemplo"""
        self.stdout.write('\n🔍 Probando consultas de ejemplo:')
        
        queries = [
            ("Artículos totales", "SELECT COUNT(*) FROM articulos"),
            ("Depósitos disponibles", "SELECT COUNT(*) FROM depositos"),
            ("Stock total", "SELECT COUNT(*) FROM stock"),
            ("Stock por depósito", "SELECT COUNT(*) FROM stock_deposito"),
            ("Clientes activos", "SELECT COUNT(*) FROM clientes"),
            ("Proveedores", "SELECT COUNT(*) FROM proveedores"),
        ]
        
        try:
            with connections['mysql'].cursor() as cursor:
                for description, query in queries:
                    try:
                        cursor.execute(query)
                        result = cursor.fetchone()[0]
                        self.stdout.write(
                            self.style.SUCCESS(f'   ✅ {description}: {result:,}')
                        )
                    except Exception as e:
                        self.stdout.write(
                            self.style.ERROR(f'   ❌ {description}: Error - {str(e)[:50]}...')
                        )
                        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error en consultas de ejemplo: {e}')
            ) 