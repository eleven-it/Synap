"""
Comando para corregir el estado de las migraciones de reports
Útil cuando las migraciones están marcadas como aplicadas pero las tablas no existen
o cuando hay migraciones huérfanas que no existen en el código
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from django.db import connection
import os
import re
import sys


class Command(BaseCommand):
    help = 'Corrige el estado de las migraciones de reports eliminando entradas incorrectas'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar corrección sin confirmación',
        )

    def _django_migrations_exists(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = 'django_migrations'
                );
            """)
            return cursor.fetchone()[0]

    def handle(self, *args, **options):
        force = options.get('force', False)

        if not self._django_migrations_exists():
            self.stdout.write(
                self.style.SUCCESS(
                    'ℹ️  Base de datos nueva (sin django_migrations): '
                    'omitiendo corrección de migraciones de reports.'
                )
            )
            return
        
        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(self.style.WARNING("🔧 Corrección de migraciones de Reports"))
        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write("")
        
        # Verificar estado actual
        self.stdout.write("🔍 Verificando estado actual...")
        
        # Verificar si las tablas existen
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename LIKE 'reports_%' 
                ORDER BY tablename;
            """)
            existing_tables = [row[0] for row in cursor.fetchall()]
        
        if existing_tables:
            self.stdout.write(self.style.SUCCESS(f"   ✅ {len(existing_tables)} tablas de reports encontradas"))
            for table in existing_tables:
                self.stdout.write(f"      - {table}")
        else:
            self.stdout.write(self.style.ERROR("   ❌ No se encontraron tablas de reports"))
        
        self.stdout.write("")
        
        # Verificar migraciones aplicadas
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT app, name FROM django_migrations 
                WHERE app = 'reports' 
                ORDER BY applied;
            """)
            applied_migrations = cursor.fetchall()
        
        # Obtener lista de migraciones que realmente existen en el código
        migrations_dir = os.path.join('reports', 'migrations')
        existing_migration_files = set()
        all_migration_files_in_fs = []
        if os.path.exists(migrations_dir):
            for filename in os.listdir(migrations_dir):
                match = re.match(r'(\d{4}_\w+)\.py$', filename)
                if match:
                    mig_name = match.group(1)
                    existing_migration_files.add(mig_name)
                    all_migration_files_in_fs.append((mig_name, filename))
        
        # Prefijos numéricos reconocidos como migraciones oficiales del repo (no temporales del servidor).
        # Debe incluir la última migración publicada en reports (p. ej. 0031 PuntoVentaCanalEjecutivo).
        valid_migration_numbers = set([f"{i:04d}" for i in range(1, 32)])  # 0001 … 0031
        valid_migration_files = set()
        for mig_name, filename in all_migration_files_in_fs:
            mig_num = mig_name.split('_')[0]
            if mig_num in valid_migration_numbers:
                valid_migration_files.add(mig_name)
            else:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Archivo de migración sospechoso encontrado: {filename}"))
        
        if applied_migrations:
            self.stdout.write(f"   📋 {len(applied_migrations)} migraciones de reports marcadas como aplicadas:")
            orphan_migrations = []
            for app, name in applied_migrations:
                if name not in existing_migration_files:
                    self.stdout.write(self.style.WARNING(f"      - {name} (HUÉRFANA - no existe en código)"))
                    orphan_migrations.append(name)
                else:
                    self.stdout.write(f"      - {name}")
            
            if orphan_migrations:
                self.stdout.write("")
                self.stdout.write(self.style.ERROR(f"   ⚠️  Se encontraron {len(orphan_migrations)} migraciones huérfanas"))
        else:
            self.stdout.write("   ℹ️  No hay migraciones de reports marcadas como aplicadas")
        
        self.stdout.write("")
        
        # Verificar si reports_reportdefinition existe específicamente
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'reports_reportdefinition'
                );
            """)
            main_table_exists = cursor.fetchone()[0]
        
        # Si la tabla principal no existe pero hay otras tablas, hay un estado inconsistente
        if not main_table_exists and existing_tables:
            self.stdout.write(self.style.ERROR("   ❌ Estado inconsistente: algunas tablas existen pero reports_reportdefinition no"))
            self.stdout.write(self.style.WARNING("   Esto indica que las migraciones se aplicaron parcialmente."))
            
            if not force:
                self.stdout.write("")
                confirm = input("¿Deseas eliminar TODAS las tablas de reports y empezar desde cero? (s/N): ")
                if confirm.lower() != 's':
                    self.stdout.write("   Operación cancelada")
                    return
            
            self.stdout.write("🗑️  Eliminando todas las tablas de reports...")
            with connection.cursor() as cursor:
                for table in existing_tables:
                    try:
                        cursor.execute(f'DROP TABLE IF EXISTS {table} CASCADE')
                        self.stdout.write(f"   ✅ Tabla {table} eliminada")
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   ❌ Error eliminando {table}: {e}"))
            
            # Eliminar entradas de migraciones
            self.stdout.write("🗑️  Eliminando entradas de migraciones de reports...")
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM django_migrations WHERE app = 'reports'")
                deleted = cursor.rowcount
                self.stdout.write(self.style.SUCCESS(f"   ✅ {deleted} entradas eliminadas"))
        
        # Si las tablas no existen pero hay migraciones aplicadas, limpiar
        elif not existing_tables and applied_migrations:
            if not force:
                self.stdout.write(self.style.WARNING("⚠️  Se detectaron migraciones aplicadas pero las tablas no existen."))
                self.stdout.write(self.style.WARNING("   Esto puede causar problemas al aplicar migraciones."))
                self.stdout.write("")
                confirm = input("¿Deseas eliminar las entradas de migraciones de reports? (s/N): ")
                if confirm.lower() != 's':
                    self.stdout.write("   Operación cancelada")
                    return
            
            self.stdout.write("🗑️  Eliminando entradas de migraciones de reports...")
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM django_migrations WHERE app = 'reports'")
                deleted = cursor.rowcount
                self.stdout.write(self.style.SUCCESS(f"   ✅ {deleted} entradas eliminadas"))
        
        # Detectar y limpiar migraciones huérfanas (aplicadas pero no existen en código)
        orphan_applied_migrations = []
        if applied_migrations:
            for app, name in applied_migrations:
                if name not in existing_migration_files:
                    orphan_applied_migrations.append(name)
        
        # Detectar migraciones que Django intentará aplicar pero no existen en código
        # Esto puede pasar si se ejecutó makemigrations en el servidor y se creó una migración
        # que luego se eliminó del código pero Django aún la intenta aplicar
        orphan_pending_migrations = []
        try:
            from django.core.management import call_command
            from io import StringIO
            import sys
            
            # Usar showmigrations para ver qué migraciones Django detecta como pendientes
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            try:
                call_command('showmigrations', 'reports', verbosity=0, no_color=True)
                output = sys.stdout.getvalue()
            finally:
                sys.stdout = old_stdout
            
            # Parsear la salida de showmigrations
            # Formato: [X] 0001_initial o [ ] 0001_initial
            for line in output.split('\n'):
                line = line.strip()
                if line.startswith('[ ]'):  # Migración pendiente
                    mig_name = line[3:].strip()
                    if mig_name not in existing_migration_files:
                        orphan_pending_migrations.append(mig_name)
                elif line.startswith('[X]'):  # Migración aplicada
                    mig_name = line[3:].strip()
                    if mig_name not in existing_migration_files:
                        # Ya está en orphan_applied_migrations, no duplicar
                        pass
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"   ⚠️  No se pudo verificar migraciones pendientes: {e}"))
            import traceback
            self.stdout.write(self.style.WARNING(f"   Detalles: {traceback.format_exc()}"))
        
        if orphan_applied_migrations:
            self.stdout.write(self.style.WARNING(f"⚠️  Se detectaron {len(orphan_applied_migrations)} migraciones huérfanas (aplicadas pero no existen):"))
            for name in orphan_applied_migrations:
                self.stdout.write(f"      - {name}")
        
        if orphan_pending_migrations:
            self.stdout.write(self.style.ERROR(f"⚠️  Se detectaron {len(orphan_pending_migrations)} migraciones pendientes que no existen en código:"))
            for name in orphan_pending_migrations:
                self.stdout.write(f"      - {name}")
        
        all_orphan_migrations = list(set(orphan_applied_migrations + orphan_pending_migrations))
        
        if all_orphan_migrations:
            if not force:
                self.stdout.write("")
                confirm = input("¿Deseas eliminar estas migraciones huérfanas de la base de datos? (s/N): ")
                if confirm.lower() != 's':
                    self.stdout.write("   Operación cancelada")
                    return
            
            self.stdout.write("🗑️  Eliminando migraciones huérfanas...")
            with connection.cursor() as cursor:
                for name in all_orphan_migrations:
                    # Eliminar de django_migrations si existe
                    cursor.execute("DELETE FROM django_migrations WHERE app = 'reports' AND name = %s", [name])
                    deleted = cursor.rowcount
                    if deleted > 0:
                        self.stdout.write(f"   ✅ Migración {name} eliminada de django_migrations")
                    else:
                        self.stdout.write(f"   ℹ️  Migración {name} no estaba en django_migrations")
            
            # Si hay migraciones huérfanas pendientes, también necesitamos eliminar el archivo físico si existe
            # Buscar archivos que empiecen con el número de migración huérfana
            for name in orphan_pending_migrations:
                mig_num = name.split('_')[0]
                # Buscar cualquier archivo que empiece con ese número
                for mig_name, filename in all_migration_files_in_fs:
                    if filename.startswith(f'{mig_num}_'):
                        mig_file = os.path.join('reports', 'migrations', filename)
                        if os.path.exists(mig_file):
                            try:
                                os.remove(mig_file)
                                self.stdout.write(f"   ✅ Archivo {filename} eliminado")
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(f"   ⚠️  No se pudo eliminar {filename}: {e}"))
        
        # Archivos .py bajo reports/migrations/ con número > LAST_OFFICIAL_REPORTS_MIGRATION se consideran
        # basura autogenerada en servidor (makemigrations accidental). NO borrar 0030 ni 0031 oficiales.
        LAST_OFFICIAL_REPORTS_MIGRATION = 31
        orphan_files = []
        for mig_name, filename in all_migration_files_in_fs:
            mig_num = mig_name.split("_")[0]
            try:
                mig_num_int = int(mig_num)
                if mig_num_int > LAST_OFFICIAL_REPORTS_MIGRATION:
                    orphan_files.append((mig_name, filename))
            except ValueError:
                pass
        
        if orphan_files:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(f"⚠️  Se encontraron {len(orphan_files)} archivos de migración que no deberían existir:"))
            for mig_name, filename in orphan_files:
                self.stdout.write(f"      - {filename}")
            
            if not force:
                self.stdout.write("")
                confirm = input("¿Deseas eliminar estos archivos de migración? (s/N): ")
                if confirm.lower() != 's':
                    self.stdout.write("   Operación cancelada")
                    return
            
            self.stdout.write("🗑️  Eliminando archivos de migración huérfanos...")
            for mig_name, filename in orphan_files:
                mig_file = os.path.join('reports', 'migrations', filename)
                if os.path.exists(mig_file):
                    try:
                        os.remove(mig_file)
                        self.stdout.write(f"   ✅ Archivo {filename} eliminado")
                    except Exception as e:
                        self.stdout.write(self.style.WARNING(f"   ⚠️  No se pudo eliminar {filename}: {e}"))
        
        # Verificar columnas duplicadas (como is_visible que ya existe)
        if main_table_exists:
            self.stdout.write("")
            self.stdout.write("🔍 Verificando columnas duplicadas...")
            with connection.cursor() as cursor:
                # Verificar si is_visible existe
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_schema = 'public' 
                        AND table_name = 'reports_reportdefinition'
                        AND column_name = 'is_visible'
                    );
                """)
                is_visible_exists = cursor.fetchone()[0]
                
                if is_visible_exists:
                    self.stdout.write("   ✅ Columna is_visible existe (correcto)")
                else:
                    self.stdout.write("   ℹ️  Columna is_visible no existe (se agregará en migración 0011)")
        
        self.stdout.write("")
        
        # Verificar una vez más si hay migraciones huérfanas antes de aplicar
        # Esto es importante porque Django puede haber cargado las migraciones en memoria
        self.stdout.write("🔍 Verificación final antes de aplicar migraciones...")
        with connection.cursor() as cursor:
            # Verificar si hay migraciones en la BD que no existen en código
            cursor.execute("""
                SELECT name FROM django_migrations 
                WHERE app = 'reports' 
                ORDER BY applied;
            """)
            db_migrations = {row[0] for row in cursor.fetchall()}
            
            orphan_in_db = db_migrations - existing_migration_files
            if orphan_in_db:
                self.stdout.write(self.style.WARNING(f"   ⚠️  Aún hay {len(orphan_in_db)} migraciones huérfanas en la BD:"))
                for name in orphan_in_db:
                    self.stdout.write(f"      - {name}")
                self.stdout.write("   🗑️  Eliminándolas...")
                for name in orphan_in_db:
                    cursor.execute("DELETE FROM django_migrations WHERE app = 'reports' AND name = %s", [name])
                self.stdout.write(self.style.SUCCESS(f"   ✅ {len(orphan_in_db)} migraciones huérfanas eliminadas"))
        
        self.stdout.write("")
        
        # Aplicar migraciones desde cero (con reintentos si tablas ya existen)
        self.stdout.write("📦 Aplicando migraciones de reports...")
        max_fake_retries = 10
        migrated_ok = False
        for attempt in range(max_fake_retries + 1):
            try:
                call_command('migrate', 'reports', verbosity=1, interactive=False)
                self.stdout.write(self.style.SUCCESS("   ✅ Migraciones aplicadas correctamente"))
                migrated_ok = True
                break
            except Exception as e:
                err_str = str(e)
                # Tabla/relación ya existe: marcar migración pendiente con --fake y reintentar
                if "already exists" in err_str and ("relation" in err_str or "DuplicateTable" in err_str):
                    self.stdout.write("")
                    self.stdout.write(self.style.WARNING("   ⚠️  Error de tabla duplicada detectado (relation already exists)"))
                    self.stdout.write("   🔍 Buscando migración pendiente para marcar como aplicada (--fake)...")
                    # Obtener migraciones pendientes
                    from io import StringIO
                    old_stdout = sys.stdout
                    sys.stdout = StringIO()
                    try:
                        call_command('showmigrations', 'reports', verbosity=0, no_color=True)
                        output = sys.stdout.getvalue()
                    finally:
                        sys.stdout = old_stdout
                    pending = []
                    for line in output.split('\n'):
                        line = line.strip()
                        if line.startswith('[ ]'):
                            mig_name = line[3:].strip()
                            if mig_name in existing_migration_files:
                                pending.append(mig_name)
                    if not pending:
                        self.stdout.write(self.style.ERROR("   ❌ No hay migraciones pendientes para marcar con --fake"))
                        sys.exit(1)
                    mig_name = pending[0]
                    self.stdout.write(f"   📌 Marcando {mig_name} como aplicada (--fake)...")
                    try:
                        call_command('migrate', 'reports', mig_name, '--fake', verbosity=1, interactive=False)
                        self.stdout.write(self.style.SUCCESS(f"   ✅ {mig_name} marcada como aplicada"))
                        self.stdout.write("   🔄 Reintentando aplicar migraciones...")
                        continue  # siguiente iteración del loop
                    except Exception as e_fake:
                        self.stdout.write(self.style.ERROR(f"   ❌ Error al hacer --fake: {e_fake}"))
                        sys.exit(1)
                # Columna duplicada: intentar limpiar huérfanas y reintentar (solo en último intento del loop)
                elif "already exists" in err_str or "DuplicateColumn" in err_str:
                    self.stdout.write("")
                    self.stdout.write(self.style.WARNING("   ⚠️  Error de columna duplicada detectado"))
                    self.stdout.write("   🔍 Verificando migraciones pendientes nuevamente...")
                    with connection.cursor() as cursor:
                        cursor.execute("""
                            SELECT name FROM django_migrations 
                            WHERE app = 'reports' 
                            AND name NOT IN %s
                        """, [tuple(existing_migration_files)])
                        remaining_orphans = [row[0] for row in cursor.fetchall()]
                    if remaining_orphans:
                        self.stdout.write(f"   🗑️  Eliminando {len(remaining_orphans)} migraciones huérfanas restantes...")
                        with connection.cursor() as cursor:
                            for name in remaining_orphans:
                                cursor.execute("DELETE FROM django_migrations WHERE app = 'reports' AND name = %s", [name])
                        self.stdout.write("   🔄 Reintentando aplicar migraciones...")
                        continue
                    else:
                        self.stdout.write(self.style.ERROR(f"   ❌ Error al aplicar migraciones: {e}"))
                        sys.exit(1)
                else:
                    self.stdout.write(self.style.ERROR(f"   ❌ Error al aplicar migraciones: {e}"))
                    sys.exit(1)
        if not migrated_ok:
            sys.exit(1)
        
        self.stdout.write("")
        
        # Verificar estado final
        self.stdout.write("✅ Verificando estado final...")
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public' 
                AND tablename LIKE 'reports_%' 
                ORDER BY tablename;
            """)
            final_tables = [row[0] for row in cursor.fetchall()]
        
        if final_tables:
            self.stdout.write(self.style.SUCCESS(f"   ✅ {len(final_tables)} tablas de reports creadas:"))
            for table in final_tables:
                self.stdout.write(f"      - {table}")
        else:
            self.stdout.write(self.style.ERROR("   ❌ No se pudieron crear las tablas"))
            sys.exit(1)
        
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("🎉 Corrección de migraciones completada"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

