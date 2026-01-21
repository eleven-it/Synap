from django.core.management.base import BaseCommand
import pymssql
from datetime import datetime


class Command(BaseCommand):
    help = 'Mostrar información detallada de clientes de Azure SQL Database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=20,
            help='Número de clientes a mostrar (default: 20)',
        )
        parser.add_argument(
            '--client-id',
            type=int,
            help='Mostrar información de un cliente específico por ID',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('👥 Consultando información detallada de clientes')
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
        client_id = options['client_id']

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

            # Explorar estructura de tablas relacionadas con clientes
            self.explore_client_tables(conn)
            
            # Mostrar clientes detallados
            if client_id:
                self.show_specific_client(conn, client_id)
            else:
                self.show_detailed_clients(conn, limit)
            
            conn.close()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al consultar clientes: {e}')
            )

    def explore_client_tables(self, conn):
        """Explorar tablas relacionadas con clientes"""
        try:
            with conn.cursor() as cursor:
                # Listar todas las tablas que podrían contener información de clientes
                client_related_tables = ['CL', 'CU', 'CY', 'DD', 'TG', 'TT']
                
                self.stdout.write('\n🔍 Explorando tablas relacionadas con clientes:')
                self.stdout.write('=' * 50)
                
                for table in client_related_tables:
                    cursor.execute(f"""
                        SELECT COUNT(*) 
                        FROM INFORMATION_SCHEMA.TABLES 
                        WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table}'
                    """)
                    
                    if cursor.fetchone()[0] > 0:
                        cursor.execute(f"SELECT COUNT(*) FROM dbo.{table}")
                        count = cursor.fetchone()[0]
                        self.stdout.write(f'   📋 {table}: {count} registros')
                    else:
                        self.stdout.write(f'   ❌ {table}: No existe')
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f'⚠️  Error al explorar tablas: {e}')
            )

    def show_detailed_clients(self, conn, limit):
        """Mostrar información detallada de clientes"""
        try:
            with conn.cursor() as cursor:
                # Obtener clientes básicos
                cursor.execute(f"""
                    SELECT TOP {limit} 
                        CLCCID,
                        CLLOC,
                        CLSTAT,
                        CLDESC,
                        CLLOCK
                    FROM dbo.CL
                    ORDER BY CLCCID, CLLOC
                """)
                
                clients = cursor.fetchall()
                
                if not clients:
                    self.stdout.write(
                        self.style.WARNING('⚠️  No se encontraron clientes')
                    )
                    return

                self.stdout.write(f'\n👥 Información detallada de {len(clients)} clientes:')
                self.stdout.write('=' * 80)
                
                for i, client in enumerate(clients, 1):
                    client_id = client[0]
                    location = client[1]
                    status = client[2]
                    description = client[3] or "N/A"
                    locked = client[4]
                    
                    self.stdout.write(f'\n🔹 Cliente #{i} - ID: {client_id}')
                    self.stdout.write('   ' + '=' * 40)
                    
                    # Información básica
                    self.stdout.write(f'   📋 Información Básica:')
                    self.stdout.write(f'      ID: {client_id}')
                    self.stdout.write(f'      Localización: {location}')
                    self.stdout.write(f'      Estado: {status}')
                    self.stdout.write(f'      Descripción: {description}')
                    self.stdout.write(f'      Bloqueado: {"Sí" if locked else "No"}')
                    
                    # Información de monedas (CU)
                    self.get_currency_info(cursor, client_id)
                    
                    # Información de condiciones (CY)
                    self.get_conditions_info(cursor, client_id)
                    
                    # Información de documentos (DD)
                    self.get_documents_info(cursor, client_id)
                    
                    # Información bancaria (BA)
                    self.get_banking_info(cursor, client_id)
                    
                    # Información de transacciones (TG)
                    self.get_transactions_info(cursor, client_id)
                    
                    self.stdout.write('   ' + '-' * 40)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al mostrar clientes detallados: {e}')
            )

    def show_specific_client(self, conn, client_id):
        """Mostrar información de un cliente específico"""
        try:
            with conn.cursor() as cursor:
                # Verificar si el cliente existe
                cursor.execute("""
                    SELECT CLCCID, CLLOC, CLSTAT, CLDESC, CLLOCK
                    FROM dbo.CL
                    WHERE CLCCID = %s
                """, (client_id,))
                
                client = cursor.fetchone()
                
                if not client:
                    self.stdout.write(
                        self.style.WARNING(f'⚠️  No se encontró el cliente con ID: {client_id}')
                    )
                    return

                self.stdout.write(f'\n🔍 Cliente específico - ID: {client_id}')
                self.stdout.write('=' * 50)
                
                # Información básica
                self.stdout.write(f'   📋 Información Básica:')
                self.stdout.write(f'      ID: {client[0]}')
                self.stdout.write(f'      Localización: {client[1]}')
                self.stdout.write(f'      Estado: {client[2]}')
                self.stdout.write(f'      Descripción: {client[3] or "N/A"}')
                self.stdout.write(f'      Bloqueado: {"Sí" if client[4] else "No"}')
                
                # Información detallada
                self.get_currency_info(cursor, client_id)
                self.get_conditions_info(cursor, client_id)
                self.get_documents_info(cursor, client_id)
                self.get_banking_info(cursor, client_id)
                self.get_transactions_info(cursor, client_id)
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al mostrar cliente específico: {e}')
            )

    def get_currency_info(self, cursor, client_id):
        """Obtener información de monedas del cliente"""
        try:
            cursor.execute("""
                SELECT CUID, CURATE, CUINV, CUKEY
                FROM dbo.CU
                WHERE CUID IN (
                    SELECT DISTINCT DDCUID 
                    FROM dbo.DD 
                    WHERE DDCCID = %s
                )
            """, (client_id,))
            
            currencies = cursor.fetchall()
            
            if currencies:
                self.stdout.write(f'   💰 Monedas asociadas:')
                for currency in currencies:
                    currency_id = currency[0]
                    rate = currency[1]
                    inv = "Sí" if currency[2] else "No"
                    key = "Sí" if currency[3] else "No"
                    self.stdout.write(f'      {currency_id}: Tasa={rate}, Inv={inv}, Key={key}')
            else:
                self.stdout.write(f'   💰 Monedas: No hay monedas específicas')
                
        except Exception as e:
            self.stdout.write(f'   💰 Monedas: Error al obtener - {e}')

    def get_conditions_info(self, cursor, client_id):
        """Obtener información de condiciones del cliente"""
        try:
            cursor.execute("""
                SELECT CYTYFL, CYTYCO, CYDESC, CYISMY
                FROM dbo.CY
                WHERE CYCCID = %s
            """, (client_id,))
            
            conditions = cursor.fetchall()
            
            if conditions:
                self.stdout.write(f'   📋 Condiciones:')
                for condition in conditions:
                    type_flag = condition[0]
                    type_code = condition[1] or "N/A"
                    description = condition[2] or "N/A"
                    is_my = "Sí" if condition[3] else "No"
                    self.stdout.write(f'      {type_flag}: {type_code} - {description} (Mi empresa: {is_my})')
            else:
                self.stdout.write(f'   📋 Condiciones: No hay condiciones específicas')
                
        except Exception as e:
            self.stdout.write(f'   📋 Condiciones: Error al obtener - {e}')

    def get_documents_info(self, cursor, client_id):
        """Obtener información de documentos del cliente"""
        try:
            cursor.execute("""
                SELECT DDNO, DDPOS, DDTYPE, DDSTAT, DDINNO, DDVAL, DDCUID, DDREF, DDNOTE
                FROM dbo.DD
                WHERE DDCCID = %s
                ORDER BY DDNO, DDPOS
            """, (client_id,))
            
            documents = cursor.fetchall()
            
            if documents:
                self.stdout.write(f'   📄 Documentos ({len(documents)} registros):')
                for doc in documents[:5]:  # Mostrar solo los primeros 5
                    doc_no = doc[0]
                    doc_pos = doc[1]
                    doc_type = doc[2]
                    doc_stat = doc[3]
                    doc_inno = doc[4] or "N/A"
                    doc_val = doc[5]
                    doc_currency = doc[6]
                    doc_ref = doc[7] or "N/A"
                    doc_note = doc[8] or "N/A"
                    
                    self.stdout.write(f'      Doc {doc_no}-{doc_pos}: Tipo={doc_type}, Estado={doc_stat}, Valor={doc_val} {doc_currency}')
                    self.stdout.write(f'         Ref: {doc_ref}, Nota: {doc_note[:50]}...')
                
                if len(documents) > 5:
                    self.stdout.write(f'      ... y {len(documents) - 5} documentos más')
            else:
                self.stdout.write(f'   📄 Documentos: No hay documentos')
                
        except Exception as e:
            self.stdout.write(f'   📄 Documentos: Error al obtener - {e}')

    def get_banking_info(self, cursor, client_id):
        """Obtener información bancaria del cliente"""
        try:
            cursor.execute("""
                SELECT COUNT(*) as total_records,
                       SUM(BAVAL) as total_value,
                       COUNT(DISTINCT BACUID) as currencies,
                       MIN(BACRDT) as first_record,
                       MAX(BACRDT) as last_record
                FROM dbo.BA
                WHERE BACCID = %s
            """, (client_id,))
            
            banking_info = cursor.fetchone()
            
            if banking_info and banking_info[0] > 0:
                total_records = banking_info[0]
                total_value = banking_info[1] or 0
                currencies = banking_info[2] or 0
                first_record = banking_info[3]
                last_record = banking_info[4]
                
                self.stdout.write(f'   🏦 Información Bancaria:')
                self.stdout.write(f'      Total registros: {total_records:,}')
                self.stdout.write(f'      Valor total: {total_value:,.2f}')
                self.stdout.write(f'      Monedas utilizadas: {currencies}')
                self.stdout.write(f'      Primer registro: {first_record}')
                self.stdout.write(f'      Último registro: {last_record}')
            else:
                self.stdout.write(f'   🏦 Información Bancaria: No hay registros bancarios')
                
        except Exception as e:
            self.stdout.write(f'   🏦 Información Bancaria: Error al obtener - {e}')

    def get_transactions_info(self, cursor, client_id):
        """Obtener información de transacciones del cliente"""
        try:
            # Buscar en tabla TG (transacciones generales)
            cursor.execute("""
                SELECT COUNT(*) as total_transactions
                FROM dbo.TG
                WHERE TGCCID = %s
            """, (client_id,))
            
            tg_result = cursor.fetchone()
            
            if tg_result and tg_result[0] > 0:
                self.stdout.write(f'   💳 Transacciones: {tg_result[0]:,} registros')
            else:
                self.stdout.write(f'   💳 Transacciones: No hay transacciones')
                
        except Exception as e:
            self.stdout.write(f'   💳 Transacciones: Error al obtener - {e}')

        self.stdout.write('\n' + '=' * 60)
        self.stdout.write(
            self.style.SUCCESS('✅ Consulta detallada de clientes completada')
        )


