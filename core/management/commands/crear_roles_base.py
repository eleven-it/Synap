# core/management/commands/crear_roles_base.py

from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Permiso, Rol
from core.constantes_permisos import PERMISOS_POR_MODULO, ROLES_PREDEFINIDOS
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Crea permisos y roles base desde core/constantes_permisos.py organizados por módulo"

    def add_arguments(self, parser):
        parser.add_argument(
            '--solo-permisos',
            action='store_true',
            help='Crear solo permisos, no roles',
        )
        parser.add_argument(
            '--solo-roles',
            action='store_true',
            help='Crear solo roles, no permisos',
        )
        parser.add_argument(
            '--forzar',
            action='store_true',
            help='Forzar recreación de roles existentes',
        )

    def handle(self, *args, **options):
        self.stdout.write("🔧 Iniciando creación de permisos y roles base...\n")

        with transaction.atomic():
            if not options['solo_roles']:
                self.crear_permisos()
            
            if not options['solo_permisos']:
                self.crear_roles(options['forzar'])

        self.stdout.write(self.style.SUCCESS("\n✅ Proceso completado exitosamente!"))

    def crear_permisos(self):
        """Crea permisos base organizados por módulo"""
        self.stdout.write(self.style.NOTICE("\n📂 Creando permisos por módulo..."))
        
        total_creados = 0
        total_existentes = 0
        total_actualizados = 0

        for modulo, permisos in PERMISOS_POR_MODULO.items():
            self.stdout.write(f"\n  📁 Módulo: {modulo}")
            
            for codigo, nombre in permisos:
                permiso, creado = Permiso.objects.get_or_create(
                    codigo=codigo,
                    defaults={
                        "nombre": nombre,
                        "modulo": modulo,
                        "activo": True
                    }
                )

                if creado:
                    total_creados += 1
                    self.stdout.write(self.style.SUCCESS(f"    ✅ {codigo} - {nombre}"))
                else:
                    # Actualizar si el nombre cambió
                    if permiso.nombre != nombre or permiso.modulo != modulo:
                        permiso.nombre = nombre
                        permiso.modulo = modulo
                        permiso.save()
                        total_actualizados += 1
                        self.stdout.write(self.style.WARNING(f"    🔄 Actualizado: {codigo}"))
                    else:
                        total_existentes += 1
                        self.stdout.write(self.style.WARNING(f"    ⚠️ Ya existía: {codigo}"))

        self.stdout.write("\n📊 Resumen de Permisos:")
        self.stdout.write(self.style.SUCCESS(f"  🎯 Permisos creados: {total_creados}"))
        self.stdout.write(self.style.WARNING(f"  🔄 Permisos actualizados: {total_actualizados}"))
        self.stdout.write(self.style.WARNING(f"  ↪️ Permisos ya existentes: {total_existentes}"))

    def crear_roles(self, forzar=False):
        """Crea roles predeterminados con sus permisos"""
        self.stdout.write(self.style.NOTICE("\n👥 Creando roles predeterminados..."))
        
        total_creados = 0
        total_existentes = 0
        total_actualizados = 0

        for nombre_rol, config in ROLES_PREDEFINIDOS.items():
            self.stdout.write(f"\n  👤 Rol: {nombre_rol}")
            
            # Verificar si el rol existe
            try:
                rol = Rol.objects.get(nombre__iexact=nombre_rol)
                if forzar:
                    # Eliminar rol existente y recrear
                    rol.delete()
                    rol = None
                    self.stdout.write(self.style.WARNING(f"    🔄 Rol eliminado y será recreado"))
                else:
                    total_existentes += 1
                    self.stdout.write(self.style.WARNING(f"    ⚠️ Ya existía: {nombre_rol}"))
                    continue
            except Rol.DoesNotExist:
                rol = None

            if rol is None:
                # Crear nuevo rol
                rol = Rol.objects.create(
                    nombre=nombre_rol,
                    descripcion=config["descripcion"],
                    activo=True
                )
                total_creados += 1
                self.stdout.write(self.style.SUCCESS(f"    ✅ Rol creado: {nombre_rol}"))

            # Asignar permisos
            if config["permisos"] != ["*"]:
                permisos_objs = []
                for perm_codigo in config["permisos"]:
                    if perm_codigo.endswith(".*"):
                        # Permisos de módulo completo
                        modulo = perm_codigo[:-2]
                        permisos_modulo = Permiso.objects.filter(
                            codigo__startswith=f"{modulo}.",
                            activo=True
                        )
                        permisos_objs.extend(permisos_modulo)
                        self.stdout.write(f"      📋 Módulo {modulo}: {permisos_modulo.count()} permisos")
                    else:
                        # Permiso específico
                        try:
                            permiso = Permiso.objects.get(codigo=perm_codigo, activo=True)
                            permisos_objs.append(permiso)
                            self.stdout.write(f"      📋 Permiso: {perm_codigo}")
                        except Permiso.DoesNotExist:
                            self.stdout.write(self.style.ERROR(f"      ❌ Permiso no encontrado: {perm_codigo}"))
                
                rol.permisos.set(permisos_objs)
                self.stdout.write(f"      📊 Total permisos asignados: {len(permisos_objs)}")
            else:
                # Rol con todos los permisos (administrador)
                todos_permisos = Permiso.objects.filter(activo=True)
                rol.permisos.set(todos_permisos)
                self.stdout.write(f"      📊 Todos los permisos asignados: {todos_permisos.count()}")

        self.stdout.write("\n📊 Resumen de Roles:")
        self.stdout.write(self.style.SUCCESS(f"  🎯 Roles creados: {total_creados}"))
        self.stdout.write(self.style.WARNING(f"  ↪️ Roles ya existentes: {total_existentes}"))

    def verificar_integridad(self):
        """Verifica la integridad de permisos y roles"""
        self.stdout.write(self.style.NOTICE("\n🔍 Verificando integridad..."))
        
        # Verificar permisos sin módulo
        permisos_sin_modulo = Permiso.objects.filter(modulo='')
        if permisos_sin_modulo.exists():
            self.stdout.write(self.style.WARNING(f"  ⚠️ {permisos_sin_modulo.count()} permisos sin módulo asignado"))
        
        # Verificar roles sin permisos
        roles_sin_permisos = Rol.objects.filter(permisos__isnull=True)
        if roles_sin_permisos.exists():
            self.stdout.write(self.style.WARNING(f"  ⚠️ {roles_sin_permisos.count()} roles sin permisos"))
        
        # Verificar permisos huérfanos
        permisos_huérfanos = Permiso.objects.filter(roles__isnull=True, usuarios_con_permiso_directo__isnull=True)
        if permisos_huérfanos.exists():
            self.stdout.write(self.style.WARNING(f"  ⚠️ {permisos_huérfanos.count()} permisos no asignados a ningún rol"))
        
        self.stdout.write(self.style.SUCCESS("  ✅ Verificación completada"))
