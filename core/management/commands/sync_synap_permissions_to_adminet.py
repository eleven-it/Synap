from django.core.management.base import BaseCommand
from core.services.administranet_permiso_sistema import AdministraNETPermisoSistemaService
from core.constantes_permisos import PERMISOS_POR_MODULO
from django.conf import settings
import MySQLdb


class Command(BaseCommand):
    help = 'Sincroniza los permisos de Synap a la tabla permiso_sistema de administraNET'

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
        
        # Obtener todas las empresas si no se especifica una
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
        
        # Obtener todos los permisos de Synap
        permisos_synap = []
        for modulo, lista_permisos in PERMISOS_POR_MODULO.items():
            for codigo, nombre in lista_permisos:
                permisos_synap.append({
                    'key_permiso': codigo,
                    'nombre_permiso': nombre,
                    'grupo_permiso': grupo_permiso,
                    'tipo_permiso': 'Si-No',
                    'default_permiso': 'No',
                    'detalle_permiso': f'Permiso de Synap - Módulo {modulo}',
                    'detalle_valor_permiso': 'Si-No'
                })
        
        # Agregar permisos con comodín (como reports.*)
        permisos_comodin = []
        modulos_con_comodin = ['reports', 'sales', 'purchases', 'inventory', 'finance']
        for modulo in modulos_con_comodin:
            permisos_comodin.append({
                'key_permiso': f'{modulo}.*',
                'nombre_permiso': f'Acceso total a {modulo}',
                'grupo_permiso': grupo_permiso,
                'tipo_permiso': 'Si-No',
                'default_permiso': 'No',
                'detalle_permiso': f'Permiso comodín para acceso total al módulo {modulo}',
                'detalle_valor_permiso': 'Si-No'
            })
        
        permisos_synap.extend(permisos_comodin)
        
        self.stdout.write(f"📋 Total de permisos a sincronizar: {len(permisos_synap)}\n")
        
        # Sincronizar en cada empresa
        servicio = AdministraNETPermisoSistemaService()
        total_creados = 0
        total_existentes = 0
        
        for empresa in empresas:
            self.stdout.write(f"\n📦 Procesando empresa: {empresa}")
            creados_empresa = 0
            existentes_empresa = 0
            
            for permiso_data in permisos_synap:
                # Verificar si ya existe
                permisos = servicio.listar_permisos(
                    base_empresa=empresa,
                    busqueda=permiso_data['key_permiso']
                )
                
                existe = any(p.get('key_permiso') == permiso_data['key_permiso'] for p in permisos)
                
                if existe:
                    existentes_empresa += 1
                    self.stdout.write(f"   ⏭️  {permiso_data['key_permiso']} ya existe")
                else:
                    nuevo_id = servicio.crear_permiso(empresa, permiso_data)
                    if nuevo_id:
                        creados_empresa += 1
                        self.stdout.write(f"   ✅ {permiso_data['key_permiso']} creado (ID: {nuevo_id})")
                    else:
                        self.stdout.write(self.style.ERROR(f"   ❌ Error al crear {permiso_data['key_permiso']}"))
            
            total_creados += creados_empresa
            total_existentes += existentes_empresa
            self.stdout.write(f"   📊 Empresa {empresa}: {creados_empresa} creados, {existentes_empresa} existentes")
        
        self.stdout.write(self.style.SUCCESS(f"\n✅ Sincronización completada:"))
        self.stdout.write(f"   Total creados: {total_creados}")
        self.stdout.write(f"   Total existentes: {total_existentes}")
        self.stdout.write(f"\n💡 Ahora puedes asignar estos permisos a puestos desde /core/permisos-sistema/")

