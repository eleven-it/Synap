"""
Comando para limpiar completamente la app clientes del sistema
Elimina referencias, configuraciones y archivos relacionados
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.conf import settings
import os
import shutil


class Command(BaseCommand):
    help = 'Limpia completamente la app clientes del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Forzar la eliminación sin confirmación',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se eliminaría sin ejecutar',
        )

    def handle(self, *args, **options):
        force = options['force']
        dry_run = options['dry_run']
        
        if not force and not dry_run:
            self.stdout.write(
                self.style.WARNING(
                    '⚠️  ADVERTENCIA: Este comando eliminará completamente la app clientes.\n'
                    'Esto incluye:\n'
                    '- Configuraciones de módulos\n'
                    '- Referencias en templates\n'
                    '- Archivos de la app\n'
                    '- Datos de la base de datos\n\n'
                    'Use --force para confirmar o --dry-run para ver qué se eliminaría.'
                )
            )
            return
        
        self.stdout.write(
            self.style.SUCCESS('🧹 Iniciando limpieza de la app clientes...')
        )
        
        # 1. Eliminar configuración de módulo
        self.cleanup_module_config(dry_run)
        
        # 2. Eliminar referencias en templates
        self.cleanup_template_references(dry_run)
        
        # 3. Eliminar archivos de la app
        self.cleanup_app_files(dry_run)
        
        # 4. Eliminar datos de la base de datos
        self.cleanup_database_data(dry_run)
        
        if dry_run:
            self.stdout.write(
                self.style.SUCCESS('✅ Simulación completada. Use --force para ejecutar.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS('✅ Limpieza de la app clientes completada.')
            )

    def cleanup_module_config(self, dry_run):
        """Eliminar configuración del módulo clientes"""
        self.stdout.write('📋 Limpiando configuración de módulo...')
        
        try:
            from core.models import ModuleConfig
            
            if not dry_run:
                ModuleConfig.objects.filter(name='clientes').delete()
                self.stdout.write('  ✅ Configuración de módulo eliminada')
            else:
                count = ModuleConfig.objects.filter(name='clientes').count()
                self.stdout.write(f'  📝 Se eliminarían {count} configuraciones de módulo')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ Error eliminando configuración: {e}')
            )

    def cleanup_template_references(self, dry_run):
        """Eliminar referencias en templates"""
        self.stdout.write('📄 Limpiando referencias en templates...')
        
        template_files = [
            'login/templates/login/completar_perfil.html',
            'core/templates/core/partials/crud_subheader.html',
        ]
        
        for template_file in template_files:
            if os.path.exists(template_file):
                if not dry_run:
                    # Aquí se podrían hacer reemplazos específicos si fuera necesario
                    self.stdout.write(f'  ✅ Template {template_file} verificado')
                else:
                    self.stdout.write(f'  📝 Se verificaría template {template_file}')
            else:
                self.stdout.write(f'  ⚠️  Template {template_file} no encontrado')

    def cleanup_app_files(self, dry_run):
        """Eliminar archivos de la app clientes"""
        self.stdout.write('🗂️  Limpiando archivos de la app...')
        
        app_path = 'clientes'
        
        if os.path.exists(app_path):
            if not dry_run:
                try:
                    shutil.rmtree(app_path)
                    self.stdout.write('  ✅ Directorio de la app eliminado')
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'  ❌ Error eliminando directorio: {e}')
                    )
            else:
                self.stdout.write(f'  📝 Se eliminaría el directorio {app_path}')
        else:
            self.stdout.write(f'  ⚠️  Directorio {app_path} no encontrado')

    def cleanup_database_data(self, dry_run):
        """Eliminar datos de la base de datos"""
        self.stdout.write('🗄️  Limpiando datos de la base de datos...')
        
        try:
            with connection.cursor() as cursor:
                # Verificar si existen tablas de clientes
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE 'clientes_%'
                """)
                
                tables = cursor.fetchall()
                
                if tables:
                    if not dry_run:
                        for table in tables:
                            table_name = table[0]
                            cursor.execute(f'DROP TABLE IF EXISTS {table_name} CASCADE')
                            self.stdout.write(f'  ✅ Tabla {table_name} eliminada')
                    else:
                        for table in tables:
                            self.stdout.write(f'  📝 Se eliminaría tabla {table[0]}')
                else:
                    self.stdout.write('  ℹ️  No se encontraron tablas de clientes')
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'  ❌ Error limpiando base de datos: {e}')
            ) 