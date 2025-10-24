from django.core.management.base import BaseCommand
import pymssql
from datetime import datetime


class Command(BaseCommand):
    help = 'Mostrar datos de los primeros 20 clientes de la base de datos Azure SQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Número de clientes a mostrar (default: 20)',
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Mostrar información detallada de cada cliente',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('👥 Consultando clientes de Azure SQL Database')
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

        limit = options['limit']
        detailed = options['detailed']

        try:
            # Conectar a la base de datos
            conn = pymssql.connect(
                server=connection_config['SERVER'],
                port=int(connection_config['PORT']),
                database=connection_config['DATABASE'],
                user=connection_config['USER'],
                password=connection_config['PASSWORD'],
                timeout=30
            )

            # Mostrar información de la tabla de clientes
            self.show_clients_table_info(conn)
            
            # Mostrar clientes
            self.show_clients(conn, limit, detailed)
            
            conn.close()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al consultar clientes: {e}')
            )

    def show_clients_table_info(self, conn):
        """Mostrar información de la tabla de clientes"""
        try:
            with conn.cursor() as cursor:
                # Verificar si existe la tabla CL (clientes)
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'CL'
                """)
                
                if cursor.fetchone()[0] == 0:
                    self.stdout.write(
                        self.style.WARNING('⚠️  No se encontró la tabla CL (clientes)')
                    )
                    return

                # Obtener información de la tabla CL
                cursor.execute("""
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        IS_NULLABLE,
                        CHARACTER_MAXIMUM_LENGTH
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = 'CL'
                    ORDER BY ORDINAL_POSITION
                """)
                
                columns = cursor.fetchall()
                
                self.stdout.write('\n📋 Estructura de la tabla CL (Clientes):')
                self.stdout.write('| Columna | Tipo | Nullable | Longitud |')
                self.stdout.write('|---------|------|----------|----------|')
                
                for col in columns:
                    col_name = col[0]
                    data_type = col[1]
                    is_nullable = col[2]
                    max_length = col[3] or ''
                    
                    self.stdout.write(f'| {col_name} | {data_type} | {is_nullable} | {max_length} |')

                # Contar total de clientes
                cursor.execute("SELECT COUNT(*) FROM dbo.CL")
                total_clients = cursor.fetchone()[0]
                self.stdout.write(f'\n📊 Total de clientes en la base de datos: {total_clients}')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al obtener información de la tabla: {e}')
            )

    def show_clients(self, conn, limit, detailed):
        """Mostrar los clientes"""
        try:
            with conn.cursor() as cursor:
                # Consulta básica de clientes
                query = f"""
                    SELECT TOP {limit} 
                        CLCCID,
                        CLLOC,
                        CLSTAT,
                        CLDESC,
                        CLLOCK
                    FROM dbo.CL
                    ORDER BY CLCCID, CLLOC
                """
                
                cursor.execute(query)
                clients = cursor.fetchall()
                
                if not clients:
                    self.stdout.write(
                        self.style.WARNING('⚠️  No se encontraron clientes')
                    )
                    return

                self.stdout.write(f'\n👥 Primeros {len(clients)} clientes:')
                self.stdout.write('=' * 80)
                
                if detailed:
                    # Mostrar información detallada
                    for i, client in enumerate(clients, 1):
                        self.stdout.write(f'\n🔹 Cliente #{i}:')
                        self.stdout.write(f'   ID: {client[0]}')
                        self.stdout.write(f'   Localización: {client[1]}')
                        self.stdout.write(f'   Estado: {client[2]}')
                        self.stdout.write(f'   Descripción: {client[3] or "N/A"}')
                        self.stdout.write(f'   Bloqueado: {"Sí" if client[4] else "No"}')
                        
                        # Obtener información adicional si es necesario
                        self.get_additional_client_info(cursor, client[0], client[1])
                        
                        self.stdout.write('   ' + '-' * 40)
                else:
                    # Mostrar tabla resumida
                    self.stdout.write('| # | ID | Loc | Estado | Descripción | Bloqueado |')
                    self.stdout.write('|---|----|-----|--------|-------------|-----------|')
                    
                    for i, client in enumerate(clients, 1):
                        client_id = client[0]
                        location = client[1]
                        status = client[2]
                        description = client[3] or "N/A"
                        locked = "Sí" if client[4] else "No"
                        
                        # Truncar descripción si es muy larga
                        if len(description) > 20:
                            description = description[:17] + "..."
                        
                        self.stdout.write(f'| {i} | {client_id} | {location} | {status} | {description} | {locked} |')

                # Mostrar estadísticas
                self.show_client_statistics(cursor)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al mostrar clientes: {e}')
            )

    def get_additional_client_info(self, cursor, client_id, location):
        """Obtener información adicional del cliente"""
        try:
            # Buscar información relacionada en otras tablas
            # Por ejemplo, buscar en tablas de transacciones o cuentas
            cursor.execute("""
                SELECT COUNT(*) 
                FROM dbo.BA 
                WHERE BACCID = %s
            """, (client_id,))
            
            bank_records = cursor.fetchone()[0]
            if bank_records > 0:
                self.stdout.write(f'   📊 Registros bancarios: {bank_records}')
            
        except Exception as e:
            # Ignorar errores en información adicional
            pass

    def show_client_statistics(self, cursor):
        """Mostrar estadísticas de clientes"""
        try:
            self.stdout.write('\n📈 Estadísticas de clientes:')
            self.stdout.write('=' * 40)
            
            # Total de clientes
            cursor.execute("SELECT COUNT(*) FROM dbo.CL")
            total = cursor.fetchone()[0]
            self.stdout.write(f'   Total de clientes: {total}')
            
            # Clientes activos (estado = 1)
            cursor.execute("SELECT COUNT(*) FROM dbo.CL WHERE CLSTAT = 1")
            active = cursor.fetchone()[0]
            self.stdout.write(f'   Clientes activos: {active}')
            
            # Clientes bloqueados
            cursor.execute("SELECT COUNT(*) FROM dbo.CL WHERE CLLOCK = 1")
            locked = cursor.fetchone()[0]
            self.stdout.write(f'   Clientes bloqueados: {locked}')
            
            # Estados únicos
            cursor.execute("SELECT CLSTAT, COUNT(*) FROM dbo.CL GROUP BY CLSTAT ORDER BY CLSTAT")
            status_counts = cursor.fetchall()
            self.stdout.write('   Estados:')
            for status, count in status_counts:
                self.stdout.write(f'     - Estado {status}: {count} clientes')
            
            # Localizaciones únicas
            cursor.execute("SELECT CLLOC, COUNT(*) FROM dbo.CL GROUP BY CLLOC ORDER BY CLLOC")
            location_counts = cursor.fetchall()
            self.stdout.write('   Localizaciones:')
            for location, count in location_counts:
                self.stdout.write(f'     - Loc {location}: {count} clientes')
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Error al obtener estadísticas: {e}')
            )

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS('✅ Consulta de clientes completada')
        )


