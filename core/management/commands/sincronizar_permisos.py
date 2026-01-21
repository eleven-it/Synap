from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Permiso
from core.constantes_permisos import PERMISOS_POR_MODULO

class Command(BaseCommand):
    help = 'Sincroniza los permisos definidos en constantes con la base de datos.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Iniciando sincronización de permisos...'))

        permisos_en_codigo = set()
        for modulo, lista_permisos in PERMISOS_POR_MODULO.items():
            for codigo, nombre in lista_permisos:
                permisos_en_codigo.add((codigo, nombre))

        permisos_en_db = set(Permiso.objects.values_list('codigo', 'nombre'))
        
        # Permisos a crear
        permisos_a_crear_tuplas = permisos_en_codigo - permisos_en_db
        
        if not permisos_a_crear_tuplas:
            self.stdout.write(self.style.SUCCESS('La base de datos ya está sincronizada. No hay nuevos permisos que agregar.'))
            return

        permisos_a_crear_objs = []
        for codigo, nombre in permisos_a_crear_tuplas:
            # Chequeo adicional por si solo el nombre cambió
            if not Permiso.objects.filter(codigo=codigo).exists():
                permisos_a_crear_objs.append(Permiso(codigo=codigo, nombre=nombre))
                self.stdout.write(f'  [+] Agregando permiso: {codigo} ({nombre})')
            else:
                 # Opcional: Actualizar el nombre si el código ya existe
                permiso_existente = Permiso.objects.get(codigo=codigo)
                if permiso_existente.nombre != nombre:
                    self.stdout.write(f'  [*] Actualizando nombre para {codigo}: "{permiso_existente.nombre}" -> "{nombre}"')
                    permiso_existente.nombre = nombre
                    permiso_existente.save()

        Permiso.objects.bulk_create(permisos_a_crear_objs)

        self.stdout.write(self.style.SUCCESS(f'\nSincronización completada. Se agregaron {len(permisos_a_crear_objs)} nuevos permisos.')) 