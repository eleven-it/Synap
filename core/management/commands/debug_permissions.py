from django.core.management.base import BaseCommand
from django.conf import settings
from core.middleware.base_middleware import get_usuario_extendiendo_desde_sesion
from core.module_registry import MODULE_CONFIGS
from core.middleware.module_middleware import ModulePermissionMiddleware
import MySQLdb


class Command(BaseCommand):
    help = 'Diagnostica los permisos de un usuario de administraNET'

    def add_arguments(self, parser):
        parser.add_argument('cod_usuario', type=str, help='Código de usuario a diagnosticar')
        parser.add_argument('--base-empresa', type=str, help='Base de datos de la empresa (ej: administranet89). Si no se especifica, busca en todas las empresas.')

    def handle(self, *args, **options):
        cod_usuario = options['cod_usuario']
        base_empresa = options.get('base_empresa')
        
        self.stdout.write(f"🔍 Diagnosticando permisos para usuario: {cod_usuario}\n")
        
        # Obtener configuración de MySQL desde settings
        mysql_config = settings.DATABASES['mysql']
        
        # Conectar directamente a MySQL (evita validación de versión de Django)
        try:
            # Conectar a la base de datos 'empresas' para obtener lista de empresas
            conn_empresas = MySQLdb.connect(
                host=mysql_config['HOST'],
                port=int(mysql_config['PORT']),
                user=mysql_config['USER'],
                passwd=mysql_config['PASSWORD'],
                db='empresas',
                charset='latin1'
            )
            cursor_empresas = conn_empresas.cursor()
            
            # Obtener lista de bases de datos de empresas
            if base_empresa:
                cursor_empresas.execute("SELECT base_empresa FROM empresas WHERE base_empresa = %s", [base_empresa])
            else:
                cursor_empresas.execute("SELECT base_empresa FROM empresas WHERE activa = 'Si'")
            
            empresas = [row[0] for row in cursor_empresas.fetchall()]
            cursor_empresas.close()
            conn_empresas.close()
            
            if not empresas:
                self.stdout.write(self.style.ERROR(f"❌ No se encontraron empresas activas"))
                return
            
            self.stdout.write(f"🔍 Buscando usuario en {len(empresas)} empresa(s)...\n")
            
            # Buscar el usuario en cada base de datos de empresa
            result = None
            empresa_encontrada = None
            
            for empresa_db in empresas:
                try:
                    conn = MySQLdb.connect(
                        host=mysql_config['HOST'],
                        port=int(mysql_config['PORT']),
                        user=mysql_config['USER'],
                        passwd=mysql_config['PASSWORD'],
                        db=empresa_db,
                        charset='latin1'
                    )
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT u.id_usuario, u.cod_usuario, u.nombre_usuario, u.apellido_usuario,
                               u.id_puesto, p.puesto
                        FROM usuarios u
                        LEFT JOIN puestos p ON u.id_puesto = p.idpuesto
                        WHERE u.cod_usuario = %s AND u.baja_usuario <> 'Si'
                    """, [cod_usuario])
                    
                    result = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    
                    if result:
                        empresa_encontrada = empresa_db
                        self.stdout.write(f"✅ Usuario encontrado en empresa: {empresa_db}\n")
                        break
                except Exception as e:
                    # Continuar con la siguiente empresa si hay error
                    continue
            
            if not result:
                self.stdout.write(self.style.ERROR(f"❌ Usuario {cod_usuario} no encontrado en ninguna base de datos de empresa"))
                return
            
            # Reconectar a la base de datos donde se encontró el usuario
            conn = MySQLdb.connect(
                host=mysql_config['HOST'],
                port=int(mysql_config['PORT']),
                user=mysql_config['USER'],
                passwd=mysql_config['PASSWORD'],
                db=empresa_encontrada,
                charset='latin1'
            )
            cursor = conn.cursor()
            
            id_usuario, cod_usuario, nombre_usuario, apellido_usuario, id_puesto, nombre_puesto = result
            
            self.stdout.write(f"📋 Información del usuario:")
            self.stdout.write(f"   ID: {id_usuario}")
            self.stdout.write(f"   Código: {cod_usuario}")
            self.stdout.write(f"   Nombre: {nombre_usuario} {apellido_usuario}")
            self.stdout.write(f"   Puesto ID: {id_puesto}")
            self.stdout.write(f"   Nombre Puesto: {nombre_puesto or 'N/A'}")
            self.stdout.write("")
            
            # Obtener permisos desde MySQL usando la base de datos de la empresa
            # Nota: usuarios.id_puesto (con guion), puestos.idpuesto (sin guion), permiso_sistema_puesto.id_puesto (con guion)
            if id_puesto:
                cursor.execute("""
                    SELECT ps.key_permiso, psp.valor_permiso
                    FROM permiso_sistema ps
                    INNER JOIN (
                        SELECT psp1.id_permiso_sistema, psp1.valor_permiso
                        FROM permiso_sistema_puesto psp1
                        INNER JOIN (
                            SELECT id_permiso_sistema, MAX(id_permiso_sistema_puesto) as max_id
                            FROM permiso_sistema_puesto
                            WHERE id_puesto = %s
                            GROUP BY id_permiso_sistema
                        ) psp2 ON psp1.id_permiso_sistema = psp2.id_permiso_sistema 
                               AND psp1.id_permiso_sistema_puesto = psp2.max_id
                        WHERE psp1.id_puesto = %s
                    ) psp ON ps.id_permiso_sistema = psp.id_permiso_sistema
                    WHERE psp.valor_permiso = 'Si'
                    ORDER BY ps.key_permiso
                """, [id_puesto, id_puesto])
                
                permisos_db = cursor.fetchall()
                
                self.stdout.write(f"🔑 Permisos desde MySQL (puesto {id_puesto}):")
                if permisos_db:
                    for row in permisos_db:
                        key_permiso = row[0]
                        self.stdout.write(f"   ✅ {key_permiso}")
                else:
                    self.stdout.write(self.style.WARNING("   ⚠️  No se encontraron permisos en la base de datos"))
                self.stdout.write("")
            
            # Crear objeto usuario mock
            session_data = {
                'id_usuario': id_usuario,
                'cod_usuario': cod_usuario,
                'nombre_usuario': nombre_usuario,
                'apellido_usuario': apellido_usuario,
                'nombre_completo': f"{nombre_usuario} {apellido_usuario}",
                'id_puesto': id_puesto,
                'nombre_puesto': nombre_puesto,
                'base_empresa': empresa_encontrada,
            }
            
            class MockRequest:
                def __init__(self):
                    self.session = {'user': session_data}
                    self.path_info = '/reports/'
            
            request = MockRequest()
            user = get_usuario_extendiendo_desde_sesion(request)
            
            self.stdout.write(f"👤 Usuario mock creado:")
            self.stdout.write(f"   Tipo: {type(user).__name__}")
            self.stdout.write(f"   cod_usuario: {getattr(user, 'cod_usuario', 'N/A')}")
            self.stdout.write(f"   nombre_puesto: {getattr(user, 'nombre_puesto', 'N/A') or 'N/A'}")
            self.stdout.write(f"   is_admin(): {user.is_admin() if hasattr(user, 'is_admin') else 'N/A'}")
            self.stdout.write("")
            
            # Obtener permisos usando get_permisos_totales
            if hasattr(user, 'get_permisos_totales'):
                permisos = user.get_permisos_totales()
                self.stdout.write(f"🔑 Permisos del usuario (get_permisos_totales):")
                self.stdout.write(f"   Tipo: {type(permisos)}")
                if permisos:
                    for perm in sorted(permisos):
                        self.stdout.write(f"   ✅ {perm}")
                else:
                    self.stdout.write(self.style.WARNING("   ⚠️  Ningún permiso encontrado"))
                self.stdout.write("")
            
            # Verificar configuración del módulo reports
            reports_config = MODULE_CONFIGS.get('reports', {})
            required_permissions = reports_config.get('permissions', [])
            self.stdout.write(f"📦 Configuración del módulo 'reports':")
            self.stdout.write(f"   Permisos requeridos: {required_permissions}")
            self.stdout.write("")
            
            # Verificar acceso usando el middleware
            middleware = ModulePermissionMiddleware(lambda r: None)
            has_access = middleware.user_has_module_access(user, 'reports')
            
            self.stdout.write(f"✅ Verificación de acceso:")
            self.stdout.write(f"   ¿Tiene acceso al módulo 'reports'? {self.style.SUCCESS('SÍ') if has_access else self.style.ERROR('NO')}")
            self.stdout.write("")
            
            # Verificar cada permiso individualmente
            if hasattr(user, 'get_permisos_totales'):
                permisos = user.get_permisos_totales()
                self.stdout.write(f"🔍 Verificación detallada:")
                for perm in required_permissions:
                    has_perm = perm in permisos
                    status = self.style.SUCCESS('✅') if has_perm else self.style.ERROR('❌')
                    self.stdout.write(f"   {status} {perm}")
                
                # Verificar comodín del módulo
                module_wildcard = "reports.*"
                has_wildcard = module_wildcard in permisos
                status = self.style.SUCCESS('✅') if has_wildcard else self.style.ERROR('❌')
                self.stdout.write(f"   {status} {module_wildcard} (comodín)")
                self.stdout.write("")
                
                # Verificar también con tiene_permiso
                if hasattr(user, 'tiene_permiso'):
                    self.stdout.write(f"🔍 Verificación con tiene_permiso():")
                    for perm in required_permissions:
                        has_perm = user.tiene_permiso(perm)
                        status = self.style.SUCCESS('✅') if has_perm else self.style.ERROR('❌')
                        self.stdout.write(f"   {status} {perm}")
                    
                    has_wildcard = user.tiene_permiso(module_wildcard)
                    status = self.style.SUCCESS('✅') if has_wildcard else self.style.ERROR('❌')
                    self.stdout.write(f"   {status} {module_wildcard} (comodín)")
            
            # Cerrar conexión
            cursor.close()
            conn.close()
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error al conectar a MySQL: {e}"))
            import traceback
            self.stdout.write(traceback.format_exc())

