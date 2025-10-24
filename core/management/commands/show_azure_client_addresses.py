from django.core.management.base import BaseCommand
import pymssql
from datetime import datetime


class Command(BaseCommand):
    help = 'Buscar información de direcciones y datos personales de clientes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--client-id',
            type=int,
            help='Buscar información de un cliente específico por ID',
        )
        parser.add_argument(
            '--search-name',
            type=str,
            help='Buscar clientes por nombre o descripción',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('🏠 Buscando información de direcciones y datos personales')
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

        client_id = options['client_id']
        search_name = options['search_name']

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

            # Explorar tablas que puedan contener información personal
            self.explore_personal_data_tables(conn)
            
            # Buscar información específica
            if client_id:
                self.search_client_personal_data(conn, client_id)
            elif search_name:
                self.search_clients_by_name(conn, search_name)
            else:
                self.show_all_clients_personal_data(conn)
            
            conn.close()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al buscar información personal: {e}')
            )

    def explore_personal_data_tables(self, conn):
        """Explorar tablas que puedan contener información personal"""
        try:
            with conn.cursor() as cursor:
                # Tablas que podrían contener información personal
                personal_tables = ['JR', 'MC', 'MM', 'OO', 'UP', 'YY']
                
                self.stdout.write('\n🔍 Explorando tablas con información personal:')
                self.stdout.write('=' * 50)
                
                for table in personal_tables:
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table}'
                    """)
                    
                    if cursor.fetchone()[0] > 0:
                        cursor.execute(f"SELECT COUNT(*) FROM dbo.{table}")
                        count = cursor.fetchone()[0]
                        self.stdout.write(f'   📋 {table}: {count} registros')
                        
                        # Mostrar estructura de la tabla
                        cursor.execute(f"""
                            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
                            FROM INFORMATION_SCHEMA.COLUMNS
                            WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table}'
                            ORDER BY ORDINAL_POSITION
                        """)
                        
                        columns = cursor.fetchall()
                        for col in columns:
                            col_name = col[0]
                            data_type = col[1]
                            max_length = col[2] or ''
                            self.stdout.write(f'      - {col_name}: {data_type} ({max_length})')
                    else:
                        self.stdout.write(f'   ❌ {table}: No existe')
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Error al explorar tablas: {e}')
            )

    def search_client_personal_data(self, conn, client_id):
        """Buscar información personal de un cliente específico"""
        try:
            with conn.cursor() as cursor:
                self.stdout.write(f'\n🔍 Buscando información personal del cliente {client_id}:')
                self.stdout.write('=' * 50)
                
                # Buscar en tabla JR (posiblemente JSON/XML con datos personales)
                cursor.execute("""
                    SELECT JRNAME, JRXML
                    FROM dbo.JR
                    WHERE JRNAME LIKE %s
                """, (f'%{client_id}%',))
                
                jr_records = cursor.fetchall()
                if jr_records:
                    self.stdout.write(f'   📄 Registros JR (XML/JSON):')
                    for record in jr_records:
                        name = record[0]
                        xml_data = record[1]
                        self.stdout.write(f'      Nombre: {name}')
                        self.stdout.write(f'      Datos XML: {str(xml_data)[:200]}...')
                else:
                    self.stdout.write(f'   📄 Registros JR: No se encontraron')
                
                # Buscar en tabla MC (materiales por cliente)
                cursor.execute("""
                    SELECT MCMMID, MCSTAT, MCSTCK, MCAVAL, MCDLOC, MCBAPL, MCBAMA, MCBANL
                    FROM dbo.MC
                    WHERE MCCCID = %s
                """, (client_id,))
                
                mc_records = cursor.fetchall()
                if mc_records:
                    self.stdout.write(f'   📦 Materiales del cliente ({len(mc_records)} registros):')
                    for record in mc_records[:5]:  # Mostrar solo los primeros 5
                        material_id = record[0]
                        status = record[1]
                        stock = record[2]
                        available = record[3]
                        location = record[4]
                        self.stdout.write(f'      Material {material_id}: Stock={stock}, Disponible={available}, Loc={location}')
                    
                    if len(mc_records) > 5:
                        self.stdout.write(f'      ... y {len(mc_records) - 5} materiales más')
                else:
                    self.stdout.write(f'   📦 Materiales: No se encontraron')
                
                # Buscar en tabla OO (posiblemente órdenes o operaciones)
                cursor.execute("""
                    SELECT COUNT(*) as total_orders
                    FROM dbo.OO
                    WHERE OOCCID = %s
                """, (client_id,))
                
                oo_result = cursor.fetchone()
                if oo_result and oo_result[0] > 0:
                    self.stdout.write(f'   📋 Órdenes/Operaciones: {oo_result[0]:,} registros')
                else:
                    self.stdout.write(f'   📋 Órdenes/Operaciones: No se encontraron')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al buscar información personal: {e}')
            )

    def search_clients_by_name(self, conn, search_name):
        """Buscar clientes por nombre o descripción"""
        try:
            with conn.cursor() as cursor:
                self.stdout.write(f'\n🔍 Buscando clientes con "{search_name}":')
                self.stdout.write('=' * 50)
                
                cursor.execute("""
                    SELECT CLCCID, CLLOC, CLSTAT, CLDESC, CLLOCK
                    FROM dbo.CL
                    WHERE CLDESC LIKE %s
                    ORDER BY CLCCID
                """, (f'%{search_name}%',))
                
                clients = cursor.fetchall()
                
                if clients:
                    self.stdout.write(f'   👥 Clientes encontrados ({len(clients)}):')
                    for client in clients:
                        client_id = client[0]
                        location = client[1]
                        status = client[2]
                        description = client[3] or "N/A"
                        locked = "Sí" if client[4] else "No"
                        
                        self.stdout.write(f'      ID: {client_id}, Loc: {location}, Estado: {status}')
                        self.stdout.write(f'      Descripción: {description}, Bloqueado: {locked}')
                        self.stdout.write('      ' + '-' * 30)
                else:
                    self.stdout.write(f'   👥 No se encontraron clientes con "{search_name}"')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al buscar por nombre: {e}')
            )

    def show_all_clients_personal_data(self, conn):
        """Mostrar información personal de todos los clientes"""
        try:
            with conn.cursor() as cursor:
                # Obtener todos los clientes
                cursor.execute("""
                    SELECT CLCCID, CLLOC, CLSTAT, CLDESC, CLLOCK
                    FROM dbo.CL
                    ORDER BY CLCCID
                """)
                
                clients = cursor.fetchall()
                
                self.stdout.write(f'\n👥 Información personal de {len(clients)} clientes:')
                self.stdout.write('=' * 60)
                
                for client in clients:
                    client_id = client[0]
                    location = client[1]
                    status = client[2]
                    description = client[3] or "N/A"
                    locked = client[4]
                    
                    self.stdout.write(f'\n🔹 Cliente ID: {client_id}')
                    self.stdout.write(f'   📋 Datos básicos:')
                    self.stdout.write(f'      Localización: {location}')
                    self.stdout.write(f'      Estado: {status}')
                    self.stdout.write(f'      Descripción: {description}')
                    self.stdout.write(f'      Bloqueado: {"Sí" if locked else "No"}')
                    
                    # Buscar información adicional
                    self.get_client_additional_info(cursor, client_id)
                    
                    self.stdout.write('   ' + '-' * 30)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al mostrar información personal: {e}')
            )

    def get_client_additional_info(self, cursor, client_id):
        """Obtener información adicional del cliente"""
        try:
            # Contar materiales del cliente
            cursor.execute("""
                SELECT COUNT(*) as material_count
                FROM dbo.MC
                WHERE MCCCID = %s
            """, (client_id,))
            
            mc_result = cursor.fetchone()
            if mc_result and mc_result[0] > 0:
                self.stdout.write(f'   📦 Materiales: {mc_result[0]} registros')
            
            # Contar órdenes del cliente
            cursor.execute("""
                SELECT COUNT(*) as order_count
                FROM dbo.OO
                WHERE OOCCID = %s
            """, (client_id,))
            
            oo_result = cursor.fetchone()
            if oo_result and oo_result[0] > 0:
                self.stdout.write(f'   📋 Órdenes: {oo_result[0]} registros')
            
            # Buscar registros XML/JSON
            cursor.execute("""
                SELECT COUNT(*) as xml_count
                FROM dbo.JR
                WHERE JRNAME LIKE %s
            """, (f'%{client_id}%',))
            
            jr_result = cursor.fetchone()
            if jr_result and jr_result[0] > 0:
                self.stdout.write(f'   📄 Datos XML/JSON: {jr_result[0]} registros')
                
        except Exception as e:
            # Ignorar errores en información adicional
            pass

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS('✅ Búsqueda de información personal completada')
        )


