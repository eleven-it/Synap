import MySQLdb
from django.conf import settings
from django.core.management.base import BaseCommand

from core.services.sync_permisos_synap import sincronizar_permisos_synap_para_empresa


class Command(BaseCommand):
    help = 'Sincroniza los permisos de Synap a la tabla permiso_sistema de administraNET (también se ejecuta automáticamente tras login).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-empresa',
            type=str,
            help='Base de datos de la empresa (ej: administranet89). Si no se especifica, sincroniza en todas las empresas activas.'
        )
        parser.add_argument(
            '--grupo',
            type=str,
            default='Synap',
            help='Grupo de permisos en administraNET (default: Synap)'
        )

    def handle(self, *args, **options):
        base_empresa = options.get('base_empresa')
        grupo_permiso = options.get('grupo', 'Synap')
        
        empresas = []
        if base_empresa:
            empresas = [base_empresa]
        else:
            mysql_config = settings.DATABASES['mysql']
            try:
                conn_empresas = MySQLdb.connect(
                    host=mysql_config['HOST'],
                    port=int(mysql_config['PORT']),
                    user=mysql_config['USER'],
                    passwd=mysql_config['PASSWORD'],
                    db='empresas',
                    charset='latin1'
                )
                cursor_empresas = conn_empresas.cursor()
                cursor_empresas.execute("SELECT base_empresa FROM empresas")
                empresas = [row[0] for row in cursor_empresas.fetchall()]
                cursor_empresas.close()
                conn_empresas.close()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error al obtener empresas: {e}"))
                return
        
        self.stdout.write(f"🔄 Sincronizando permisos de Synap a {len(empresas)} empresa(s)...\n")
        
        total_creados = 0
        total_existentes = 0
        for empresa in empresas:
            self.stdout.write(f"\n📦 Procesando empresa: {empresa}")
            try:
                creados, existentes = sincronizar_permisos_synap_para_empresa(empresa, grupo_permiso)
                total_creados += creados
                total_existentes += existentes
                self.stdout.write(f"   📊 {empresa}: {creados} creados, {existentes} existentes")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error en {empresa}: {e}"))
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Sincronización completada: {total_creados} creados, {total_existentes} existentes"))
        self.stdout.write("💡 Asigna permisos a puestos desde /core/permisos-sistema/ (o desactiva auto-sync con SYNAP_AUTO_SYNC_PERMISSIONS=False).")

