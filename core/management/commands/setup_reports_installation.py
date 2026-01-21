"""
Comando para configurar automáticamente la instalación de Reports
Se ejecuta automáticamente al instalar una nueva instancia
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
from django.utils import timezone
from core.module_manager import module_manager
from core.models import ModuleConfig
from core.module_registry import MODULE_CONFIGS
import sys


class Command(BaseCommand):
    help = 'Configura automáticamente la instalación de Reports (migraciones, módulo activo, etc.)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar ejecución incluso si ya está configurado',
        )
        parser.add_argument(
            '--skip-migrations',
            action='store_true',
            help='Omitir aplicación de migraciones',
        )

    def handle(self, *args, **options):
        force = options.get('force', False)
        skip_migrations = options.get('skip_migrations', False)
        
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("🚀 Configuración automática de Reports"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write("")
        
        # 1. Verificar y aplicar migraciones
        if not skip_migrations:
            self.stdout.write("📦 Paso 1: Verificando y aplicando migraciones...")
            try:
                # Verificar si la tabla reports_reportdefinition existe
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = 'reports_reportdefinition'
                        );
                    """)
                    table_exists = cursor.fetchone()[0]
                
                if not table_exists:
                    self.stdout.write("   ⚠️  Tabla reports_reportdefinition no existe, aplicando migración inicial...")
                    # Aplicar explícitamente la migración inicial
                    call_command('migrate', 'reports', '0001_initial', verbosity=1, interactive=False)
                    self.stdout.write(self.style.SUCCESS("   ✅ Migración inicial aplicada"))
                
                # Aplicar todas las migraciones pendientes
                call_command('migrate', verbosity=1, interactive=False)
                self.stdout.write(self.style.SUCCESS("   ✅ Migraciones aplicadas correctamente"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   ❌ Error al aplicar migraciones: {e}"))
                if not force:
                    sys.exit(1)
        else:
            self.stdout.write(self.style.WARNING("   ⏭️  Omitiendo aplicación de migraciones"))
        
        self.stdout.write("")
        
        # 2. Verificar que las tablas de reports existan
        self.stdout.write("🔍 Paso 2: Verificando tablas de reports...")
        reports_tables = self._check_reports_tables()
        
        if reports_tables:
            self.stdout.write(self.style.SUCCESS(f"   ✅ {len(reports_tables)} tablas de reports encontradas:"))
            for table in reports_tables:
                self.stdout.write(f"      - {table}")
        else:
            self.stdout.write(self.style.ERROR("   ❌ No se encontraron tablas de reports"))
            if not skip_migrations and not force:
                self.stdout.write(self.style.WARNING("   💡 Ejecuta: python manage.py migrate reports"))
                sys.exit(1)
        
        self.stdout.write("")
        
        # 3. Crear y activar módulo reports
        self.stdout.write("📋 Paso 3: Configurando módulo reports...")
        module_created = self._setup_reports_module(force)
        
        if module_created:
            self.stdout.write(self.style.SUCCESS("   ✅ Módulo reports configurado y activado"))
        else:
            self.stdout.write(self.style.WARNING("   ⚠️  Módulo reports ya estaba configurado"))
        
        self.stdout.write("")
        
        # 4. Verificar estado final
        self.stdout.write("✅ Paso 4: Verificando estado final...")
        is_active = module_manager.is_module_active('reports')
        if is_active:
            self.stdout.write(self.style.SUCCESS("   ✅ Módulo reports está ACTIVO"))
        else:
            self.stdout.write(self.style.ERROR("   ❌ Módulo reports NO está activo"))
            if not force:
                sys.exit(1)
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("🎉 Configuración de Reports completada exitosamente"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        
        # Resumen
        self.stdout.write("")
        self.stdout.write("📊 Resumen:")
        self.stdout.write(f"   - Tablas de reports: {len(reports_tables)}")
        self.stdout.write(f"   - Módulo activo: {'Sí' if is_active else 'No'}")
        self.stdout.write("")
        self.stdout.write("💡 Para verificar el acceso, ejecuta:")
        self.stdout.write("   python manage.py debug_permissions <usuario>")

    def _check_reports_tables(self):
        """Verifica que las tablas de reports existan"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT tablename 
                    FROM pg_tables 
                    WHERE schemaname = 'public' 
                    AND tablename LIKE 'reports_%' 
                    ORDER BY tablename;
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error al verificar tablas: {e}"))
            return []

    def _setup_reports_module(self, force=False):
        """Crea y activa el módulo reports si no existe"""
        module_name = 'reports'
        created = False
        
        try:
            # Verificar si el módulo ya existe
            try:
                config = ModuleConfig.objects.get(name=module_name)
                if config.is_active and not force:
                    return False  # Ya está configurado
                
                # Si existe pero no está activo, activarlo
                if not config.is_active:
                    config.is_active = True
                    config.last_activated = timezone.now()
                    config.save()
                    module_manager.load_modules()
                    return True
            except ModuleConfig.DoesNotExist:
                pass
            
            # Crear el módulo si no existe
            config_data = MODULE_CONFIGS.get(module_name, {})
            
            if not config_data:
                self.stdout.write(self.style.ERROR(f"   ❌ No se encontró configuración para '{module_name}' en MODULE_CONFIGS"))
                return False
            
            config, created = ModuleConfig.objects.get_or_create(
                name=module_name,
                defaults={
                    'display_name': config_data.get('display_name', module_name),
                    'description': config_data.get('description', ''),
                    'version': config_data.get('version', '1.0.0'),
                    'author': config_data.get('author', ''),
                    'is_required': config_data.get('is_required', False),
                    'is_core': config_data.get('is_core', False),
                    'dependencies': config_data.get('dependencies', []),
                    'optional_dependencies': config_data.get('optional_dependencies', []),
                    'settings': config_data.get('settings', {}),
                    'permissions': config_data.get('permissions', []),
                    'hooks': config_data.get('hooks', []),
                    'is_active': True,
                    'last_activated': timezone.now(),
                }
            )
            
            if not created:
                # Actualizar si ya existía
                config.is_active = True
                config.last_activated = timezone.now()
                config.save()
            
            # Recargar módulos
            module_manager.load_modules()
            
            return True
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"   ❌ Error al configurar módulo: {e}"))
            return False

