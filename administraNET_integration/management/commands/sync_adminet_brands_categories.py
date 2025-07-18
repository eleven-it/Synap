from django.core.management.base import BaseCommand
from inventory.models import Brand, Category, Subcategory
from administraNET_integration.services.connection_service import AdministraNETConnectionService
from administraNET_integration.models import AdministraNETConfig

class Command(BaseCommand):
    help = 'Sincroniza marcas, categorías y subcategorías desde administraNET a Synap usando adminet_id.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('Iniciando sincronización de marcas, categorías y subcategorías...'))
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not config:
            self.stdout.write(self.style.ERROR('No hay configuración activa de AdministraNET.'))
            return
        connection = AdministraNETConnectionService(config)

        # --- Marcas ---
        brands = connection.execute_query('SELECT CodMarca, NombreMarca, anulado FROM marca')
        for b in brands:
            is_active = (b['anulado'] or '').strip().lower() == 'no'
            obj, created = Brand.objects.update_or_create(
                adminet_id=b['CodMarca'],
                defaults={
                    'name': b['NombreMarca'],
                    'is_active': is_active,
                }
            )
            self.stdout.write(f"{'[CREADO]' if created else '[ACTUALIZADO]'} Marca: {obj.name} (adminet_id={obj.adminet_id})")

        # --- Categorías ---
        categories = connection.execute_query('SELECT CodigoRubro, NombreRubro, anulado FROM rubro')
        for c in categories:
            is_active = (c['anulado'] or '').strip().lower() == 'no'
            obj, created = Category.objects.update_or_create(
                adminet_id=c['CodigoRubro'],
                defaults={
                    'name': c['NombreRubro'],
                    'is_active': is_active,
                }
            )
            self.stdout.write(f"{'[CREADO]' if created else '[ACTUALIZADO]'} Categoría: {obj.name} (adminet_id={obj.adminet_id})")

        # --- Subcategorías ---
        subcategories = connection.execute_query('SELECT IDSubRubro, NombreSubRubro, CodigoRubro, anulado FROM subrubro')
        for s in subcategories:
            is_active = (s['anulado'] or '').strip().lower() == 'no'
            category = Category.objects.filter(adminet_id=s['CodigoRubro']).first()
            obj, created = Subcategory.objects.update_or_create(
                adminet_id=s['IDSubRubro'],
                defaults={
                    'name': s['NombreSubRubro'],
                    'category': category,
                    'is_active': is_active,
                }
            )
            self.stdout.write(f"{'[CREADO]' if created else '[ACTUALIZADO]'} Subcategoría: {obj.name} (adminet_id={obj.adminet_id})")

        self.stdout.write(self.style.SUCCESS('Sincronización completada.')) 