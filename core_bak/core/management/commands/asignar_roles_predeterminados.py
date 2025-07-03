from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Rol, Permiso
from core.constantes_permisos import ROLES_PREDEFINIDOS

class Command(BaseCommand):
    help = 'Crea o actualiza los roles predeterminados y les asigna sus permisos correspondientes.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando asignación de permisos a roles predeterminados...'))

        todos_los_permisos = list(Permiso.objects.all())
        permisos_por_codigo = {p.codigo: p for p in todos_los_permisos}

        for nombre_rol, data in ROLES_PREDEFINIDOS.items():
            rol, creado = Rol.objects.get_or_create(
                nombre=nombre_rol,
                defaults={'descripcion': data.get('descripcion', '')}
            )

            if creado:
                self.stdout.write(f'  [+] Rol "{nombre_rol}" creado.')
            else:
                # Opcional: actualizar descripción si ya existe
                if rol.descripcion != data.get('descripcion', ''):
                    rol.descripcion = data.get('descripcion', '')
                    rol.save()
                    self.stdout.write(f'  [*] Rol "{nombre_rol}" actualizado.')

            permisos_para_rol = set()
            codigos_permisos_rol = data.get('permisos', [])

            if "*" in codigos_permisos_rol:
                permisos_para_rol.update(todos_los_permisos)
                self.stdout.write(f'  [*] Asignando TODOS los permisos al rol "{nombre_rol}".')
            else:
                for codigo_permiso in codigos_permisos_rol:
                    if codigo_permiso.endswith(".*"):
                        # Permiso de tipo comodín (ej: "inventario.*")
                        modulo_base = codigo_permiso.split('.')[0]
                        for p in todos_los_permisos:
                            if p.codigo.startswith(modulo_base + "."):
                                permisos_para_rol.add(p)
                        self.stdout.write(f'  [*] Asignando permisos del módulo "{modulo_base}" al rol "{nombre_rol}".')
                    else:
                        # Permiso específico
                        if codigo_permiso in permisos_por_codigo:
                            permisos_para_rol.add(permisos_por_codigo[codigo_permiso])
                        else:
                            self.stdout.write(self.style.WARNING(f'    [!] Permiso "{codigo_permiso}" no encontrado en la DB. Omitiendo.'))
            
            permisos_actuales = set(rol.permisos.all())
            
            # Añadir solo los que no tiene
            permisos_a_anadir = permisos_para_rol - permisos_actuales
            if permisos_a_anadir:
                rol.permisos.add(*permisos_a_anadir)
                self.stdout.write(f'    - Se añadieron {len(permisos_a_anadir)} permisos nuevos al rol "{nombre_rol}".')

            # Quitar los que ya no debería tener
            permisos_a_quitar = permisos_actuales - permisos_para_rol
            if permisos_a_quitar:
                rol.permisos.remove(*permisos_a_quitar)
                self.stdout.write(f'    - Se quitaron {len(permisos_a_quitar)} permisos obsoletos del rol "{nombre_rol}".')
        
        self.stdout.write(self.style.SUCCESS('\nAsignación de roles y permisos completada.')) 