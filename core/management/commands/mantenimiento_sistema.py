from django.core.management.base import BaseCommand
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from datetime import timedelta
import logging
import os

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Realiza tareas de mantenimiento del sistema Synap"

    def add_arguments(self, parser):
        parser.add_argument(
            '--limpiar-cache',
            action='store_true',
            help='Limpiar cache del sistema',
        )
        parser.add_argument(
            '--limpiar-logs',
            action='store_true',
            help='Limpiar logs antiguos',
        )
        parser.add_argument(
            '--optimizar-db',
            action='store_true',
            help='Optimizar base de datos',
        )
        parser.add_argument(
            '--verificar-integridad',
            action='store_true',
            help='Verificar integridad de datos',
        )
        parser.add_argument(
            '--todo',
            action='store_true',
            help='Ejecutar todas las tareas de mantenimiento',
        )
        parser.add_argument(
            '--dias-logs',
            type=int,
            default=30,
            help='Días a mantener en logs (default: 30)',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔧 Iniciando mantenimiento del sistema Synap...\n")

        if options['todo']:
            self.ejecutar_todas_tareas(options)
        else:
            if options['limpiar_cache']:
                self.limpiar_cache()
            if options['limpiar_logs']:
                self.limpiar_logs(options['dias_logs'])
            if options['optimizar_db']:
                self.optimizar_base_datos()
            if options['verificar_integridad']:
                self.verificar_integridad()

        self.stdout.write(self.style.SUCCESS("\n✅ Mantenimiento completado!"))

    def ejecutar_todas_tareas(self, options):
        """Ejecuta todas las tareas de mantenimiento"""
        self.stdout.write("🔄 Ejecutando todas las tareas de mantenimiento...\n")
        
        self.limpiar_cache()
        self.limpiar_logs(options['dias_logs'])
        self.optimizar_base_datos()
        self.verificar_integridad()
        self.actualizar_estadisticas()

    def limpiar_cache(self):
        """Limpia el cache del sistema"""
        self.stdout.write("🧹 Limpiando cache del sistema...")
        
        try:
            # Limpiar cache específico del sistema
            cache_keys_to_clear = [
                'system_config',
                'currency_config', 
                'uom_config',
                'user_permissions_*',
                'user_session_*',
                'rate_limit_*'
            ]
            
            # Limpiar por patrones
            for pattern in cache_keys_to_clear:
                if pattern.endswith('*'):
                    # Para patrones con wildcard, necesitarías implementar
                    # una función específica según tu backend de cache
                    pass
                else:
                    cache.delete(pattern)
            
            # Limpiar todo el cache (cuidado en producción)
            cache.clear()
            
            self.stdout.write(self.style.SUCCESS("  ✅ Cache limpiado exitosamente"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Error limpiando cache: {e}"))

    def limpiar_logs(self, dias_a_mantener):
        """Limpia logs antiguos"""
        self.stdout.write(f"📁 Limpiando logs más antiguos de {dias_a_mantener} días...")
        
        try:
            from core.logging_config import cleanup_old_logs
            
            log_dir = 'logs'
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                self.stdout.write(f"  📂 Directorio de logs creado: {log_dir}")
                return
            
            archivos_antes = len(os.listdir(log_dir))
            cleanup_old_logs(log_dir, dias_a_mantener)
            archivos_despues = len(os.listdir(log_dir))
            
            eliminados = archivos_antes - archivos_despues
            self.stdout.write(self.style.SUCCESS(f"  ✅ {eliminados} archivos de log eliminados"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Error limpiando logs: {e}"))

    def optimizar_base_datos(self):
        """Optimiza la base de datos"""
        self.stdout.write("🗄️ Optimizando base de datos...")
        
        try:
            with connection.cursor() as cursor:
                # Analizar tablas
                cursor.execute("ANALYZE;")
                
                # Vacuum (solo PostgreSQL)
                if connection.vendor == 'postgresql':
                    cursor.execute("VACUUM ANALYZE;")
                    self.stdout.write(self.style.SUCCESS("  ✅ VACUUM ANALYZE completado"))
                
                # Para MySQL
                elif connection.vendor == 'mysql':
                    cursor.execute("OPTIMIZE TABLE;")
                    self.stdout.write(self.style.SUCCESS("  ✅ OPTIMIZE TABLE completado"))
                
                self.stdout.write(self.style.SUCCESS("  ✅ Base de datos optimizada"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Error optimizando BD: {e}"))

    def verificar_integridad(self):
        """Verifica la integridad de los datos"""
        self.stdout.write("🔍 Verificando integridad de datos...")
        
        try:
            from core.models import UsuarioExtendido, Rol, Permiso
            
            problemas = []
            
            # Verificar usuarios sin roles
            usuarios_sin_roles = UsuarioExtendido.objects.filter(roles__isnull=True)
            if usuarios_sin_roles.exists():
                problemas.append(f"  ⚠️ {usuarios_sin_roles.count()} usuarios sin roles")
            
            # Verificar roles sin permisos
            roles_sin_permisos = Rol.objects.filter(permisos__isnull=True)
            if roles_sin_permisos.exists():
                problemas.append(f"  ⚠️ {roles_sin_permisos.count()} roles sin permisos")
            
            # Verificar permisos huérfanos
            permisos_huérfanos = Permiso.objects.filter(
                roles__isnull=True, 
                usuarios_con_permiso_directo__isnull=True
            )
            if permisos_huérfanos.exists():
                problemas.append(f"  ⚠️ {permisos_huérfanos.count()} permisos no asignados")
            
            # Verificar usuarios inactivos con roles activos
            usuarios_inactivos_con_roles = UsuarioExtendido.objects.filter(
                is_active=False,
                roles__activo=True
            ).distinct()
            if usuarios_inactivos_con_roles.exists():
                problemas.append(f"  ⚠️ {usuarios_inactivos_con_roles.count()} usuarios inactivos con roles activos")
            
            if problemas:
                self.stdout.write(self.style.WARNING("  Problemas encontrados:"))
                for problema in problemas:
                    self.stdout.write(self.style.WARNING(problema))
            else:
                self.stdout.write(self.style.SUCCESS("  ✅ No se encontraron problemas de integridad"))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Error verificando integridad: {e}"))

    def actualizar_estadisticas(self):
        """Actualiza estadísticas del sistema"""
        self.stdout.write("📊 Actualizando estadísticas del sistema...")
        
        try:
            from core.utils import obtener_estadisticas_sistema
            
            stats = obtener_estadisticas_sistema()
            
            # Guardar estadísticas en cache
            cache.set('system_stats', stats, 3600)  # 1 hora
            
            self.stdout.write(self.style.SUCCESS("  ✅ Estadísticas actualizadas"))
            self.stdout.write(f"  📈 Usuarios totales: {stats.get('usuarios', {}).get('total', 0)}")
            self.stdout.write(f"  📈 Roles activos: {stats.get('roles', {}).get('activos', 0)}")
            self.stdout.write(f"  📈 Permisos activos: {stats.get('permisos', {}).get('activos', 0)}")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Error actualizando estadísticas: {e}"))

    def generar_reporte_mantenimiento(self):
        """Genera un reporte de mantenimiento"""
        self.stdout.write("📋 Generando reporte de mantenimiento...")
        
        try:
            from core.models import UsuarioExtendido, Rol, Permiso
            from django.db.models import Count
            
            reporte = {
                'fecha': timezone.now().isoformat(),
                'usuarios': {
                    'total': UsuarioExtendido.objects.count(),
                    'activos': UsuarioExtendido.objects.filter(is_active=True).count(),
                    'nuevos_30_dias': UsuarioExtendido.objects.filter(
                        fecha_creacion__gte=timezone.now() - timedelta(days=30)
                    ).count(),
                },
                'roles': {
                    'total': Rol.objects.count(),
                    'activos': Rol.objects.filter(activo=True).count(),
                },
                'permisos': {
                    'total': Permiso.objects.count(),
                    'activos': Permiso.objects.filter(activo=True).count(),
                },
                'cache': {
                    'keys_activas': len(cache._cache) if hasattr(cache, '_cache') else 'N/A',
                }
            }
            
            # Guardar reporte
            cache.set('maintenance_report', reporte, 86400)  # 24 horas
            
            self.stdout.write(self.style.SUCCESS("  ✅ Reporte generado y guardado"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"  ❌ Error generando reporte: {e}")) 