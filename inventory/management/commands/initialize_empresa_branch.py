from django.core.management.base import BaseCommand
from django.db import transaction
from core.models import Empresa, Branch
from inventory.models import (
    Warehouse, Location, Product, StockLot, StockQuant, 
    StockMove, InventoryAdjustment, StockReservation, 
    ReplenishmentRule, InitialStockDraft, InitialStockDraftItem
)


class Command(BaseCommand):
    help = 'Inicializa empresa_id y branch_id en todas las tablas de inventory con los datos existentes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Ejecuta sin hacer cambios reales en la base de datos',
        )
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID específico de la empresa a usar (opcional)',
        )
        parser.add_argument(
            '--branch-id',
            type=int,
            help='ID específico de la sucursal a usar (opcional)',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        empresa_id = options['empresa_id']
        branch_id = options['branch_id']

        self.stdout.write(
            self.style.SUCCESS('🚀 Iniciando inicialización de empresa_id y branch_id...')
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

        # Definir modelos a actualizar
        models_to_update = [
            (Warehouse, 'Warehouse'),
            (Location, 'Location'),
            (Product, 'Product'),
            (StockLot, 'StockLot'),
            (StockQuant, 'StockQuant'),
            (StockMove, 'StockMove'),
            (InventoryAdjustment, 'InventoryAdjustment'),
            (StockReservation, 'StockReservation'),
            (ReplenishmentRule, 'ReplenishmentRule'),
            (InitialStockDraft, 'InitialStockDraft'),
            (InitialStockDraftItem, 'InitialStockDraftItem'),
        ]

        total_updated = 0

        if dry_run:
            self.stdout.write(
                self.style.WARNING('🔍 MODO DRY-RUN: No se harán cambios reales en la base de datos')
            )

        try:
            with transaction.atomic():
                for model, model_name in models_to_update:
                    self.stdout.write(f'\n📊 Procesando {model_name}...')

                    # Contar registros con empresa_id nulo
                    empresa_null_count = model.objects.filter(empresa__isnull=True).count()
                    branch_null_count = model.objects.filter(branch__isnull=True).count()

                    if empresa_null_count == 0 and branch_null_count == 0:
                        self.stdout.write(f'   ✅ {model_name}: No hay registros con valores nulos')
                        continue

                    self.stdout.write(f'   📈 {model_name}: {empresa_null_count} registros con empresa_id nulo, {branch_null_count} con branch_id nulo')

                    if not dry_run:
                        # Actualizar empresa_id
                        if empresa_null_count > 0:
                            updated_empresa = model.objects.filter(empresa__isnull=True).update(empresa=empresa)
                            self.stdout.write(f'   ✅ {model_name}: Actualizados {updated_empresa} registros con empresa_id')

                        # Actualizar branch_id
                        if branch_null_count > 0:
                            updated_branch = model.objects.filter(branch__isnull=True).update(branch=branch)
                            self.stdout.write(f'   ✅ {model_name}: Actualizados {updated_branch} registros con branch_id')

                        total_updated += empresa_null_count + branch_null_count
                    else:
                        self.stdout.write(f'   🔍 DRY-RUN: Se actualizarían {empresa_null_count + branch_null_count} registros')

                # Verificar que no queden registros nulos
                self.stdout.write('\n🔍 Verificando que no queden registros nulos...')
                for model, model_name in models_to_update:
                    empresa_null_count = model.objects.filter(empresa__isnull=True).count()
                    branch_null_count = model.objects.filter(branch__isnull=True).count()
                    
                    if empresa_null_count > 0 or branch_null_count > 0:
                        self.stdout.write(
                            self.style.WARNING(f'   ⚠️  {model_name}: Aún hay {empresa_null_count} empresa_id nulos y {branch_null_count} branch_id nulos')
                        )
                    else:
                        self.stdout.write(f'   ✅ {model_name}: Todos los registros tienen empresa_id y branch_id válidos')

            if dry_run:
                self.stdout.write(
                    self.style.SUCCESS(f'\n🎉 DRY-RUN COMPLETADO: Se actualizarían {total_updated} registros en total')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f'\n🎉 INICIALIZACIÓN COMPLETADA: Se actualizaron {total_updated} registros en total')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error durante la inicialización: {e}')
            )
            if not dry_run:
                self.stdout.write(
                    self.style.ERROR('🔄 Los cambios han sido revertidos debido al error')
                )

        # Mostrar resumen final
        self.stdout.write('\n📋 RESUMEN FINAL:')
        self.stdout.write(f'   🏢 Empresa: {empresa.nombre} (ID: {empresa.id})')
        self.stdout.write(f'   🏪 Sucursal: {branch.name} (ID: {branch.id})')
        self.stdout.write(f'   📊 Total de registros procesados: {len(models_to_update)} modelos')
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS('✅ La base de datos está lista para aplicar la migración 0013_make_empresa_branch_required')
            )
        else:
            self.stdout.write(
                self.style.WARNING('🔍 Ejecuta sin --dry-run para aplicar los cambios reales')
            )
