from django.core.management.base import BaseCommand
from inventory.models import StockQuant, Product
from core.models import Empresa

class Command(BaseCommand):
    help = 'Fix cross-company stock issues by removing stock records that cross company boundaries'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be fixed without actually doing it'
        )
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='Fix stock for specific empresa only'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        empresa_id = options['empresa_id']

        self.stdout.write('=== FIXING CROSS-COMPANY STOCK ISSUES ===')

        if empresa_id:
            try:
                empresas = [Empresa.objects.get(id=empresa_id)]
                self.stdout.write(f'Processing only empresa ID: {empresa_id}')
            except Empresa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Empresa with ID {empresa_id} does not exist')
                )
                return
        else:
            empresas = Empresa.objects.all()

        total_fixed = 0

        for empresa in empresas:
            self.stdout.write(f'\n--- Processing {empresa.nombre} ---')
            
            # Find products that belong to this empresa
            empresa_products = Product.objects.filter(empresa=empresa)
            self.stdout.write(f'Products in {empresa.nombre}: {empresa_products.count()}')
            
            # Find stock records where product belongs to this empresa but location belongs to different empresa
            cross_company_stock = StockQuant.objects.filter(
                product__empresa=empresa
            ).exclude(
                location__warehouse__empresa=empresa
            )
            
            if cross_company_stock.exists():
                self.stdout.write(
                    self.style.WARNING(f'Found {cross_company_stock.count()} cross-company stock records')
                )
                
                for stock in cross_company_stock:
                    self.stdout.write(
                        f'  - {stock.product.name}: {stock.available_quantity} in {stock.location.name} '
                        f'(Product empresa: {stock.product.empresa.nombre}, '
                        f'Location empresa: {stock.location.warehouse.empresa.nombre})'
                    )
                    
                    if not dry_run:
                        stock.delete()
                        self.stdout.write(f'    ✓ Deleted cross-company stock record')
                    
                    total_fixed += 1
            else:
                self.stdout.write('  ✓ No cross-company stock found')

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\nDry run complete. Would fix {total_fixed} cross-company stock records.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nFixed {total_fixed} cross-company stock records.')
            )

        # Show final status
        self.stdout.write('\n=== FINAL STATUS ===')
        for empresa in empresas:
            empresa_stock = StockQuant.objects.filter(product__empresa=empresa)
            self.stdout.write(f'{empresa.nombre}: {empresa_stock.count()} stock records')
            
            # Verify no cross-company stock remains
            cross_company = StockQuant.objects.filter(
                product__empresa=empresa
            ).exclude(
                location__warehouse__empresa=empresa
            )
            
            if cross_company.exists():
                self.stdout.write(
                    self.style.ERROR(f'  ⚠️  {cross_company.count()} cross-company records still exist!')
                )
            else:
                self.stdout.write('  ✓ No cross-company stock remaining') 