"""
Comando para sincronizar permisos de SIA a la tabla permiso_sistema de administraNET MySQL

Este comando sincroniza los permisos de SIA desde PostgreSQL a MySQL de administraNET,
haciendo que estén disponibles para asignación a puestos en administraNET Gestión.

Modo automático (--auto):
- Logueo resumido
- Tolerante a errores de conexión MySQL (sale con código 0)
- Idempotente y seguro para ejecutar en entrypoints de contenedores
"""
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
import MySQLdb
from MySQLdb import IntegrityError, OperationalError
import logging
import sys

logger = logging.getLogger(__name__)

# Importar datos de permisos desde el helper centralizado
from core.permissions_utils import get_sia_permissions_data


def convert_sia_permission_to_mysql_format(permiso_data):
    """
    Convierte un permiso de SIA del formato PostgreSQL al formato MySQL de administraNET.
    
    Args:
        permiso_data: Diccionario con datos del permiso en formato PostgreSQL
    
    Returns:
        Diccionario con datos del permiso en formato MySQL
    """
    return {
        'key_permiso': permiso_data['codigo'],
        'nombre_permiso': permiso_data['nombre'],
        'detalle_permiso': permiso_data.get('descripcion', ''),
        'grupo_permiso': permiso_data.get('modulo', 'SIA').upper(),
        'tipo_permiso': 'Si-No',
        'default_permiso': 'No',
        'detalle_valor_permiso': 'Si-No',
    }


class Command(BaseCommand):
    help = 'Sincroniza los permisos de SIA a la tabla permiso_sistema de administraNET MySQL'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-empresa',
            type=str,
            help='Nombre de la base de datos de la empresa (si no se especifica, usa todas las empresas)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simular sin hacer cambios reales',
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Modo automático: logueo resumido y tolerante a errores (para entrypoints)',
        )
        parser.add_argument(
            '--exit-on-error',
            action='store_true',
            help='En modo --auto, salir con código de error si hay problemas (default: salir con 0)',
        )

    def handle(self, *args, **options):
        base_empresa = options.get('base_empresa')
        dry_run = options.get('dry_run', False)
        auto_mode = options.get('auto', False)
        exit_on_error = options.get('exit_on_error', False)

        # Obtener permisos desde el helper centralizado
        sia_permissions_pg = get_sia_permissions_data()
        SIA_PERMISSIONS = [convert_sia_permission_to_mysql_format(p) for p in sia_permissions_pg]

        mysql_config = settings.DATABASES.get('mysql')
        if not mysql_config:
            error_msg = 'Configuración MySQL no encontrada en settings.DATABASES["mysql"]'
            if auto_mode:
                logger.warning(f'⚠️  {error_msg}. Saltando sincronización de permisos SIA a MySQL.')
                if exit_on_error:
                    sys.exit(1)
                else:
                    sys.exit(0)
            else:
                raise CommandError(error_msg)

        server = mysql_config.get('HOST')
        port = mysql_config.get('PORT', 3306)
        user = mysql_config.get('USER')
        password = mysql_config.get('PASSWORD')

        if not all([server, port, user, password]):
            error_msg = 'Configuración MySQL incompleta. Verificar HOST, PORT, USER, PASSWORD'
            if auto_mode:
                logger.warning(f'⚠️  {error_msg}. Saltando sincronización de permisos SIA a MySQL.')
                if exit_on_error:
                    sys.exit(1)
                else:
                    sys.exit(0)
            else:
                raise CommandError(error_msg)

        port = int(port)

        if dry_run and not auto_mode:
            self.stdout.write(self.style.WARNING('🔍 MODO DRY-RUN: No se realizarán cambios reales'))

        # Obtener lista de empresas
        empresas = []
        if base_empresa:
            empresas = [base_empresa]
        else:
            # Obtener todas las empresas desde la base 'empresas'
            try:
                conn_empresas = MySQLdb.connect(
                    host=server,
                    port=port,
                    user=user,
                    passwd=password,
                    db='empresas',
                    charset='latin1',
                    connect_timeout=5  # Timeout corto para modo automático
                )
                cursor_empresas = conn_empresas.cursor()
                cursor_empresas.execute("SELECT base_empresa FROM empresas WHERE base_empresa IS NOT NULL")
                empresas = [row[0] for row in cursor_empresas.fetchall()]
                cursor_empresas.close()
                conn_empresas.close()
            except (OperationalError, MySQLdb.Error) as e:
                error_msg = f'No se pudo conectar a MySQL para obtener empresas: {e}'
                if auto_mode:
                    logger.warning(f'⚠️  {error_msg}. Saltando sincronización de permisos SIA a MySQL.')
                    if exit_on_error:
                        sys.exit(1)
                    else:
                        sys.exit(0)
                else:
                    raise CommandError(error_msg)
            except Exception as e:
                error_msg = f'Error inesperado al obtener empresas: {e}'
                if auto_mode:
                    logger.warning(f'⚠️  {error_msg}. Saltando sincronización de permisos SIA a MySQL.')
                    if exit_on_error:
                        sys.exit(1)
                    else:
                        sys.exit(0)
                else:
                    raise CommandError(error_msg)

        if not empresas:
            warning_msg = 'No se encontraron empresas para sincronizar'
            if auto_mode:
                logger.warning(f'⚠️  {warning_msg}')
                sys.exit(0)
            else:
                self.stdout.write(self.style.WARNING(warning_msg))
                return

        total_creados = 0
        total_actualizados = 0
        total_errores = 0
        empresas_procesadas = 0

        for empresa_db in empresas:
            if not auto_mode:
                self.stdout.write(f'\n📦 Procesando empresa: {empresa_db}')
            
            try:
                conn = MySQLdb.connect(
                    host=server,
                    port=port,
                    user=user,
                    passwd=password,
                    db=empresa_db,
                    charset='latin1',
                    connect_timeout=5
                )
                cursor = conn.cursor()

                for permiso_data in SIA_PERMISSIONS:
                    key_permiso = permiso_data['key_permiso']
                    
                    try:
                        # Verificar si el permiso ya existe (idempotente)
                        cursor.execute(
                            "SELECT id_permiso_sistema FROM permiso_sistema WHERE key_permiso = %s",
                            [key_permiso]
                        )
                        existing = cursor.fetchone()

                        if existing:
                            # Actualizar permiso existente si es necesario
                            if not dry_run:
                                cursor.execute("""
                                    UPDATE permiso_sistema SET
                                        nombre_permiso = %s,
                                        detalle_permiso = %s,
                                        grupo_permiso = %s,
                                        tipo_permiso = %s,
                                        default_permiso = %s,
                                        detalle_valor_permiso = %s
                                    WHERE key_permiso = %s
                                """, [
                                    permiso_data['nombre_permiso'],
                                    permiso_data['detalle_permiso'],
                                    permiso_data['grupo_permiso'],
                                    permiso_data['tipo_permiso'],
                                    permiso_data['default_permiso'],
                                    permiso_data['detalle_valor_permiso'],
                                    key_permiso
                                ])
                            if not auto_mode:
                                self.stdout.write(f'  ↻ Actualizado: {key_permiso}')
                            total_actualizados += 1
                        else:
                            # Crear nuevo permiso
                            if not dry_run:
                                cursor.execute("""
                                    INSERT INTO permiso_sistema (
                                        key_permiso, nombre_permiso, detalle_permiso,
                                        grupo_permiso, tipo_permiso, default_permiso, detalle_valor_permiso
                                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                                """, [
                                    permiso_data['key_permiso'],
                                    permiso_data['nombre_permiso'],
                                    permiso_data['detalle_permiso'],
                                    permiso_data['grupo_permiso'],
                                    permiso_data['tipo_permiso'],
                                    permiso_data['default_permiso'],
                                    permiso_data['detalle_valor_permiso'],
                                ])
                            if not auto_mode:
                                self.stdout.write(f'  ✓ Creado: {key_permiso}')
                            total_creados += 1
                    except IntegrityError as e:
                        # Manejar colisiones concurrentes (otro proceso puede haber creado el permiso)
                        if 'Duplicate entry' in str(e) or 'duplicate key' in str(e).lower():
                            # El permiso ya existe (probablemente creado por otro proceso)
                            # Intentar actualizar
                            try:
                                if not dry_run:
                                    cursor.execute("""
                                        UPDATE permiso_sistema SET
                                            nombre_permiso = %s,
                                            detalle_permiso = %s,
                                            grupo_permiso = %s,
                                            tipo_permiso = %s,
                                            default_permiso = %s,
                                            detalle_valor_permiso = %s
                                        WHERE key_permiso = %s
                                    """, [
                                        permiso_data['nombre_permiso'],
                                        permiso_data['detalle_permiso'],
                                        permiso_data['grupo_permiso'],
                                        permiso_data['tipo_permiso'],
                                        permiso_data['default_permiso'],
                                        permiso_data['detalle_valor_permiso'],
                                        key_permiso
                                    ])
                                if not auto_mode:
                                    self.stdout.write(f'  ↻ Actualizado (después de colisión): {key_permiso}')
                                total_actualizados += 1
                            except Exception as update_error:
                                logger.warning(f'Error al actualizar permiso {key_permiso} después de colisión: {update_error}')
                        else:
                            raise

                if not dry_run:
                    conn.commit()
                
                empresas_procesadas += 1
                cursor.close()
                conn.close()

            except (OperationalError, MySQLdb.Error) as e:
                error_msg = f'Error de conexión MySQL en {empresa_db}: {e}'
                if auto_mode:
                    logger.warning(f'⚠️  {error_msg}')
                    total_errores += 1
                    # Continuar con la siguiente empresa en modo auto
                else:
                    self.stdout.write(self.style.ERROR(f'  ❌ {error_msg}'))
                    total_errores += 1
                    logger.error(f'Error al sincronizar permisos SIA en {empresa_db}: {e}', exc_info=True)
            except Exception as e:
                error_msg = f'Error inesperado en {empresa_db}: {e}'
                if auto_mode:
                    logger.warning(f'⚠️  {error_msg}')
                    total_errores += 1
                else:
                    self.stdout.write(self.style.ERROR(f'  ❌ {error_msg}'))
                    total_errores += 1
                    logger.error(f'Error al sincronizar permisos SIA en {empresa_db}: {e}', exc_info=True)

        # Resumen
        if auto_mode:
            # Log resumido para modo automático
            if total_creados > 0 or total_actualizados > 0:
                logger.info(
                    f'SIA permissions sync to MySQL: {empresas_procesadas} companies, '
                    f'{total_creados} created, {total_actualizados} updated'
                )
            if total_errores > 0:
                logger.warning(f'SIA permissions sync: {total_errores} errors occurred')
            # En modo auto, salir con código 0 a menos que exit_on_error esté activado
            if exit_on_error and total_errores > 0:
                sys.exit(1)
            else:
                sys.exit(0)
        else:
            # Output detallado para modo manual
            self.stdout.write(self.style.SUCCESS(
                f'\n✅ Sincronización completada:\n'
                f'   - Empresas procesadas: {empresas_procesadas}/{len(empresas)}\n'
                f'   - Permisos creados: {total_creados}\n'
                f'   - Permisos actualizados: {total_actualizados}\n'
                f'   - Errores: {total_errores}'
            ))

            if dry_run:
                self.stdout.write(self.style.WARNING('\n⚠️  Este fue un DRY-RUN. Ejecuta sin --dry-run para aplicar los cambios.'))

            if total_errores > 0:
                raise CommandError(f'Sincronización completada con {total_errores} errores')

