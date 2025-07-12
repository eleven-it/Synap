from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Empresa, Branch
from sales.models import POSSale, POSSaleLine, POSPayment, POSPromotion


class Command(BaseCommand):
    help = 'Inicializar campos empresa y branch en modelos del TPV'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Mostrar qué se haría sin ejecutar cambios',
        )
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID de empresa específica a usar',
        )
        parser.add_argument(
            '--branch-id',
            type=int,
            help='ID de sucursal específica a usar',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        empresa_id = options['empresa_id']
        branch_id = options['branch_id']

        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando inicialización de empresa y branch en TPV...')
        )

        # Obtener empresa y branch
        try:
            if empresa_id:
                empresa = Empresa.objects.get(id=empresa_id)
                self.stdout.write(f'✅ Usando empresa específica: {empresa.nombre} (ID: {empresa.id})')
            else:
                empresa = Empresa.objects.first()
                if not empresa:
                    self.stdout.write(
                        self.style.ERROR('❌ No se encontró ninguna empresa en la base de datos')
                    )
                    return
                self.stdout.write(f'✅ Usando primera empresa: {empresa.nombre} (ID: {empresa.id})')

            if branch_id:
                branch = Branch.objects.get(id=branch_id)
                self.stdout.write(f'✅ Usando sucursal específica: {branch.name} (ID: {branch.id})')
            else:
                branch = Branch.objects.filter(empresa=empresa).first()
                if not branch:
                    self.stdout.write(
                        self.style.ERROR('❌ No se encontró ninguna sucursal para la empresa')
                    )
                    return
                self.stdout.write(f'✅ Usando primera sucursal: {branch.name} (ID: {branch.id})')

        except (Empresa.DoesNotExist, Branch.DoesNotExist) as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error al obtener empresa o sucursal: {e}')
            )
            return

        # Inicializar POSSale
        self.stdout.write('\n📊 Inicializando POSSale...')
        possales = POSSale.objects.filter(empresa__isnull=True)
        self.stdout.write(f'  - Registros a actualizar: {possales.count()}')
        
        if not dry_run:
            updated = possales.update(empresa=empresa, branch=branch)
            self.stdout.write(f'  - Registros actualizados: {updated}')
        else:
            self.stdout.write(f'  - [DRY RUN] Se actualizarían: {possales.count()} registros')

        # Inicializar POSSaleLine
        self.stdout.write('\n📊 Inicializando POSSaleLine...')
        possalelines = POSSaleLine.objects.filter(empresa__isnull=True)
        self.stdout.write(f'  - Registros a actualizar: {possalelines.count()}')
        
        if not dry_run:
            updated = possalelines.update(empresa=empresa, branch=branch)
            self.stdout.write(f'  - Registros actualizados: {updated}')
        else:
            self.stdout.write(f'  - [DRY RUN] Se actualizarían: {possalelines.count()} registros')

        # Inicializar POSPayment
        self.stdout.write('\n📊 Inicializando POSPayment...')
        pospayments = POSPayment.objects.filter(empresa__isnull=True)
        self.stdout.write(f'  - Registros a actualizar: {pospayments.count()}')
        
        if not dry_run:
            updated = pospayments.update(empresa=empresa, branch=branch)
            self.stdout.write(f'  - Registros actualizados: {updated}')
        else:
            self.stdout.write(f'  - [DRY RUN] Se actualizarían: {pospayments.count()} registros')

        # Inicializar POSPromotion
        self.stdout.write('\n📊 Inicializando POSPromotion...')
        pospromotions = POSPromotion.objects.filter(empresa__isnull=True)
        self.stdout.write(f'  - Registros a actualizar: {pospromotions.count()}')
        
        if not dry_run:
            updated = pospromotions.update(empresa=empresa, branch=branch)
            self.stdout.write(f'  - Registros actualizados: {updated}')
        else:
            self.stdout.write(f'  - [DRY RUN] Se actualizarían: {pospromotions.count()} registros')

        # Mostrar resumen final
        self.stdout.write('\n📋 RESUMEN FINAL:')
        self.stdout.write(f'  - Empresa: {empresa.nombre}')
        self.stdout.write(f'  - Sucursal: {branch.name}')
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('🎉 Inicialización completada exitosamente')
            )
        else:
            self.stdout.write(
                self.style.WARNING('🔍 Modo DRY RUN - No se realizaron cambios')
            ) 