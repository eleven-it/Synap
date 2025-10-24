from django.core.management.base import BaseCommand
from django.conf import settings
import pymssql
import sys
from datetime import datetime


class Command(BaseCommand):
    help = 'Verificar conexión y estado de la base de datos Azure SQL'

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
        parser.add_argument(
            '--list-tables',
            action='store_true',
            help='Listar todas las tablas disponibles',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🔧 Verificador de Conexión Azure SQL Database')
        )
        self.stdout.write('=' * 60)

        # Configuración de conexión
        connection_config = {
            'SERVER': 'm52q7iitok.database.windows.net',
            'DATABASE': 'BEST',
            'USER': 'interfase$bestsox',
            'PASSWORD': 'Parsimotion2012',
            'PORT': '1433'
        }

        # Mostrar configuración
        self.show_connection_config(connection_config)

        # Probar conexión
        if not self.test_azure_connection(connection_config):
            sys.exit(1)

        # Verificar información de la base de datos
        self.check_database_info(connection_config)

        # Listar tablas si se solicita
        if options['list_tables']:
            self.list_all_tables(connection_config)

        # Información detallada si se solicita
        if options['detailed']:
            self.show_detailed_info(connection_config)

        # Consultas de prueba si se solicita
        if options['test_queries']:
            self.test_sample_queries(connection_config)

        self.stdout.write('=' * 60)
        self.stdout.write(
            self.style.SUCCESS('✅ Verificación completada')
        )

    def show_connection_config(self, config):
        """Mostrar configuración de conexión"""
        self.stdout.write('\n⚙️  Configuración de conexión Azure SQL:')
        self.stdout.write(f'   Servidor: {config["SERVER"]}')
        self.stdout.write(f'   Puerto: {config["PORT"]}')
        self.stdout.write(f'   Base de datos: {config["DATABASE"]}')
        self.stdout.write(f'   Usuario: {config["USER"]}')
        self.stdout.write(f'   Motor: SQL Server (Azure)')

    def test_azure_connection(self, config):
        """Verificar conexión básica a Azure SQL"""
        try:
            self.stdout.write('\n🔌 Probando conexión...')
            
            # Configurar conexión con pymssql
            conn = pymssql.connect(
                server=config['SERVER'],
                port=int(config['PORT']),
                database=config['DATABASE'],
                user=config['USER'],
                password=config['PASSWORD'],
                timeout=30
            )
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT @@VERSION")
                version = cursor.fetchone()
                self.stdout.write(
                    self.style.SUCCESS('✅ Conexión exitosa a Azure SQL Database')
                )
                self.stdout.write(f'   Versión: {version[0][:100]}...')
            
            conn.close()
            return True
            
        except pymssql.Error as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error de conexión Azure SQL: {e}')
            )
            return False
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error inesperado: {e}')
            )
            return False

    def check_database_info(self, config):
        """Verificar información básica de la base de datos"""
        try:
            conn = pymssql.connect(
                server=config['SERVER'],
                port=int(config['PORT']),
                database=config['DATABASE'],
                user=config['USER'],
                password=config['PASSWORD'],
                timeout=30
            )
            
            with conn.cursor() as cursor:
                # Información de la base de datos
                cursor.execute("SELECT DB_NAME(), DATABASEPROPERTYEX(DB_NAME(), 'Status')")
                db_info = cursor.fetchone()
                
                self.stdout.write('\n📊 Información de la base de datos:')
                self.stdout.write(f'   Nombre: {db_info[0]}')
                self.stdout.write(f'   Estado: {db_info[1]}')
                
                # Contar tablas
                cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
                table_count = cursor.fetchone()[0]
                self.stdout.write(f'   Total de tablas: {table_count}')
                
                # Tamaño de la base de datos
                cursor.execute("""
                    SELECT 
                        CAST(ROUND(SUM(size * 8.0 / 1024), 2) AS DECIMAL(10,2)) AS SizeMB
                    FROM sys.database_files
                """)
                size_info = cursor.fetchone()
                if size_info and size_info[0]:
                    self.stdout.write(f'   Tamaño aproximado: {size_info[0]} MB')
            
            conn.close()
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  No se pudo obtener información detallada: {e}')
            )

    def list_all_tables(self, config):
        """Listar todas las tablas disponibles"""
        try:
            conn = pymssql.connect(
                server=config['SERVER'],
                port=int(config['PORT']),
                database=config['DATABASE'],
                user=config['USER'],
                password=config['PASSWORD'],
                timeout=30
            )
            
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT TABLE_NAME, TABLE_SCHEMA
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_TYPE = 'BASE TABLE'
                    ORDER BY TABLE_SCHEMA, TABLE_NAME
                """)
                
                tables = cursor.fetchall()
                
                self.stdout.write('\n📋 Tablas disponibles:')
                if tables:
                    for table in tables:
                        self.stdout.write(f'   {table[1]}.{table[0]}')
                else:
                    self.stdout.write('   No se encontraron tablas')
            
            conn.close()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al listar tablas: {e}')
            )

    def show_detailed_info(self, config):
        """Mostrar información detallada de la base de datos"""
        try:
            conn = pymssql.connect(
                server=config['SERVER'],
                port=int(config['PORT']),
                database=config['DATABASE'],
                user=config['USER'],
                password=config['PASSWORD'],
                timeout=30
            )
            
            with conn.cursor() as cursor:
                # Información de esquemas
                cursor.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA")
                schemas = cursor.fetchall()
                
                self.stdout.write('\n📚 Esquemas disponibles:')
                for schema in schemas:
                    self.stdout.write(f'   {schema[0]}')
                
                # Información de vistas
                cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS")
                view_count = cursor.fetchone()[0]
                self.stdout.write(f'\n👁️  Vistas: {view_count}')
                
                # Información de procedimientos almacenados
                cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'PROCEDURE'")
                proc_count = cursor.fetchone()[0]
                self.stdout.write(f'🔧 Procedimientos almacenados: {proc_count}')
                
                # Información de funciones
                cursor.execute("SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'FUNCTION'")
                func_count = cursor.fetchone()[0]
                self.stdout.write(f'⚙️  Funciones: {func_count}')
            
            conn.close()
            
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Error al obtener información detallada: {e}')
            )

    def test_sample_queries(self, config):
        """Ejecutar consultas de prueba"""
        try:
            conn = pymssql.connect(
                server=config['SERVER'],
                port=int(config['PORT']),
                database=config['DATABASE'],
                user=config['USER'],
                password=config['PASSWORD'],
                timeout=30
            )
            
            self.stdout.write('\n🧪 Ejecutando consultas de prueba:')
            
            with conn.cursor() as cursor:
                # Prueba 1: Obtener fecha y hora del servidor
                cursor.execute("SELECT GETDATE()")
                server_time = cursor.fetchone()[0]
                self.stdout.write(f'   ✅ Hora del servidor: {server_time}')
                
                # Prueba 2: Verificar permisos del usuario
                cursor.execute("SELECT USER_NAME(), IS_MEMBER('db_owner'), IS_MEMBER('db_datareader')")
                user_info = cursor.fetchone()
                self.stdout.write(f'   ✅ Usuario actual: {user_info[0]}')
                self.stdout.write(f'   ✅ Es db_owner: {"Sí" if user_info[1] else "No"}')
                self.stdout.write(f'   ✅ Es db_datareader: {"Sí" if user_info[2] else "No"}')
                
                # Prueba 3: Verificar conexiones activas
                cursor.execute("SELECT COUNT(*) FROM sys.dm_exec_connections")
                active_connections = cursor.fetchone()[0]
                self.stdout.write(f'   ✅ Conexiones activas: {active_connections}')
            
            conn.close()
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error en consultas de prueba: {e}')
            )
