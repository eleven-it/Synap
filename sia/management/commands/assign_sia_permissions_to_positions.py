"""
Comando para asignar permisos SIA a puestos específicos en todas las empresas

Este comando asigna los permisos SIA a puestos como Supervisor, Director, etc.
en todas las empresas o en una empresa específica.
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import MySQLdb
from MySQLdb import IntegrityError, OperationalError
import logging

logger = logging.getLogger(__name__)

# Importar datos de permisos desde el helper centralizado
from core.permissions_utils import get_sia_permissions_data


class Command(BaseCommand):
    help = 'Asigna permisos SIA a puestos específicos en todas las empresas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-empresa',
            type=str,
            help='Nombre de la base de datos de la empresa (si no se especifica, usa todas las empresas)',
        )
        parser.add_argument(
            '--puesto',
            type=str,
            default='Supervisor',
            help='Nombre del puesto al que asignar los permisos (default: Supervisor)',
        )
        parser.add_argument(
            '--valor',
            type=str,
            default='Si',
            choices=['Si', 'No'],
            help='Valor del permiso a asignar (default: Si)',
        )
        parser.add_argument(
            '--all-positions',
            action='store_true',
            help='Asignar a todos los puestos (no solo Supervisor/Director)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin hacer cambios reales',
        )

    def handle(self, *args, **options):
        base_empresa = options.get('base_empresa')
        puesto_nombre = options.get('puesto')
        valor_permiso = options.get('valor')
        all_positions = options.get('all_positions', False)
        dry_run = options.get('dry_run', False)

        # Obtener permisos SIA
        sia_permissions_pg = get_sia_permissions_data()
        sia_permission_keys = [p['codigo'] for p in sia_permissions_pg]

        mysql_config = settings.DATABASES.get('mysql')
        if not mysql_config:
            raise CommandError('Configuración MySQL no encontrada en settings.DATABASES["mysql"]')

        server = mysql_config.get('HOST')
        port = mysql_config.get('PORT', 3306)
        user = mysql_config.get('USER')
        password = mysql_config.get('PASSWORD')

        if not all([server, port, user, password]):
            raise CommandError('Configuración MySQL incompleta. Verificar HOST, PORT, USER, PASSWORD')

        # Conectar a la base de empresas para obtener lista de empresas
        try:
            conn_empresas = MySQLdb.connect(
                host=server,
                port=int(port),
                user=user,
                passwd=password,
                db='empresas',
                charset='latin1'
            )
            cursor_empresas = conn_empresas.cursor()

            if base_empresa:
                empresas = [base_empresa]
            else:
                cursor_empresas.execute('SELECT base_empresa FROM empresas WHERE base_empresa IS NOT NULL')
                empresas = [row[0] for row in cursor_empresas.fetchall()]

            cursor_empresas.close()
            conn_empresas.close()

            self.stdout.write(f'\n📋 Procesando {len(empresas)} empresa(s)')
            if dry_run:
                self.stdout.write(self.style.WARNING('⚠️  MODO DRY-RUN: No se realizarán cambios'))

            total_asignados = 0
            empresas_procesadas = 0

            for empresa in empresas:
                try:
                    conn = MySQLdb.connect(
                        host=server,
                        port=int(port),
                        user=user,
                        passwd=password,
                        db=empresa,
                        charset='latin1'
                    )
                    cursor = conn.cursor()

                    # Obtener ID de los permisos SIA
                    cursor.execute("""
                        SELECT id_permiso_sistema, key_permiso
                        FROM permiso_sistema
                        WHERE grupo_permiso = 'SIA'
                    """)
                    permisos_sia = {row[1]: row[0] for row in cursor.fetchall()}

                    if not permisos_sia:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠️  {empresa}: No se encontraron permisos SIA. Ejecuta primero sync_sia_permissions_to_adminet.')
                        )
                        cursor.close()
                        conn.close()
                        continue

                    # Obtener puestos
                    if all_positions:
                        cursor.execute('SELECT idpuesto, puesto FROM puestos')
                        puestos = cursor.fetchall()
                    else:
                        if puesto_nombre:
                            cursor.execute('SELECT idpuesto, puesto FROM puestos WHERE puesto = %s', [puesto_nombre])
                            puestos = cursor.fetchall()
                        else:
                            # Por defecto: Supervisor y Director
                            cursor.execute('SELECT idpuesto, puesto FROM puestos WHERE puesto IN (%s, %s)', ['Supervisor', 'Director'])
                            puestos = cursor.fetchall()

                    if not puestos:
                        self.stdout.write(
                            self.style.WARNING(f'  ⚠️  {empresa}: No se encontraron puestos')
                        )
                        cursor.close()
                        conn.close()
                        continue

                    self.stdout.write(f'\n  📁 {empresa}:')
                    asignados_empresa = 0

                    for id_puesto, nombre_puesto in puestos:
                        self.stdout.write(f'    🔹 Puesto: {nombre_puesto} (ID: {id_puesto})')

                        for key_permiso, id_permiso_sistema in permisos_sia.items():
                            # Verificar si ya existe
                            cursor.execute("""
                                SELECT id_permiso_sistema_puesto
                                FROM permiso_sistema_puesto
                                WHERE id_permiso_sistema = %s AND id_puesto = %s
                                ORDER BY id_permiso_sistema_puesto DESC
                                LIMIT 1
                            """, [id_permiso_sistema, id_puesto])

                            existe = cursor.fetchone()

                            if existe:
                                # Actualizar valor
                                if not dry_run:
                                    cursor.execute("""
                                        UPDATE permiso_sistema_puesto
                                        SET valor_permiso = %s
                                        WHERE id_permiso_sistema_puesto = %s
                                    """, [valor_permiso, existe[0]])
                                    conn.commit()
                                self.stdout.write(
                                    self.style.SUCCESS(f'      ✅ {key_permiso}: Actualizado a "{valor_permiso}"')
                                )
                            else:
                                # Crear nuevo
                                if not dry_run:
                                    cursor.execute("""
                                        INSERT INTO permiso_sistema_puesto
                                        (id_permiso_sistema, key_permiso, valor_permiso, id_puesto)
                                        VALUES (%s, %s, %s, %s)
                                    """, [id_permiso_sistema, key_permiso, valor_permiso, id_puesto])
                                    conn.commit()
                                self.stdout.write(
                                    self.style.SUCCESS(f'      ✅ {key_permiso}: Creado con valor "{valor_permiso}"')
                                )

                            asignados_empresa += 1
                            total_asignados += 1

                    empresas_procesadas += 1
                    self.stdout.write(f'    📊 Total asignados en {empresa}: {asignados_empresa}')

                    cursor.close()
                    conn.close()

                except MySQLdb.Error as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ Error MySQL en {empresa}: {e}')
                    )
                    continue
                except Exception as e:
                    logger.error(f'Error inesperado en {empresa}: {e}', exc_info=True)
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ Error inesperado en {empresa}: {e}')
                    )
                    continue

            self.stdout.write(
                self.style.SUCCESS(
                    f'\n✅ Proceso completado:\n'
                    f'   - Empresas procesadas: {empresas_procesadas}/{len(empresas)}\n'
                    f'   - Permisos asignados: {total_asignados}'
                )
            )

        except MySQLdb.Error as e:
            raise CommandError(f'Error de conexión MySQL: {e}')
        except Exception as e:
            logger.error(f'Error inesperado: {e}', exc_info=True)
            raise CommandError(f'Error inesperado: {e}')













