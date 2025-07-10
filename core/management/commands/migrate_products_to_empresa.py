from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from core.models import Empresa
from inventory.models import Product
from tiendanube.models import TiendaNubeConfig

User = get_user_model()

class Command(BaseCommand):
    help = 'Migrate Tiendanube products to the active user company'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user-email',
            type=str,
            help='Email of the user whose active company will receive the products'
        )
        parser.add_argument(
            '--empresa-id',
            type=int,
            help='ID of the empresa to migrate products to'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        user_email = options['user_email']
        empresa_id = options['empresa_id']

        # Determine target empresa
        target_empresa = None
        if empresa_id:
            try:
                target_empresa = Empresa.objects.get(id=empresa_id)
            except Empresa.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Empresa with ID {empresa_id} does not exist')
                )
                return
        elif user_email:
            try:
                user = User.objects.get(email=user_email)
                target_empresa = user.empresa_activa
                if not target_empresa:
                    self.stdout.write(
                        self.style.ERROR(f'User {user_email} has no active empresa')
                    )
                    return
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User with email {user_email} does not exist')
                )
                return
        else:
            self.stdout.write(
                self.style.ERROR('Please provide either --user-email or --empresa-id')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Target empresa: {target_empresa.nombre} (ID: {target_empresa.id})')
        )

        # Find Tiendanube products (products with tiendanube tag)
        tiendanube_products = Product.objects.filter(tags__icontains='tiendanube')
        
        if not tiendanube_products.exists():
            self.stdout.write(
                self.style.WARNING('No Tiendanube products found')
            )
            return

        self.stdout.write(f'Found {tiendanube_products.count()} Tiendanube products')

        # Show current distribution
        self.stdout.write('\nCurrent product distribution:')
        for empresa in Empresa.objects.all():
            count = Product.objects.filter(empresa=empresa).count()
            self.stdout.write(f'  {empresa.nombre}: {count} products')

        # Migrate products
        migrated_count = 0
        for product in tiendanube_products:
            if product.empresa != target_empresa:
                if dry_run:
                    self.stdout.write(
                        f'Would migrate: {product.name} (SKU: {product.sku}) from {product.empresa.nombre} to {target_empresa.nombre}'
                    )
                else:
                    old_empresa = product.empresa
                    product.empresa = target_empresa
                    product.branch = target_empresa.branches.first()  # Assign to first branch
                    product.save()
                    self.stdout.write(
                        f'Migrated: {product.name} (SKU: {product.sku}) from {old_empresa.nombre} to {target_empresa.nombre}'
                    )
                migrated_count += 1

        if dry_run:
            self.stdout.write(
                self.style.SUCCESS(f'\nDry run complete. Would migrate {migrated_count} products.')
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(f'\nMigration complete. Migrated {migrated_count} products.')
            )

        # Show final distribution
        if not dry_run:
            self.stdout.write('\nFinal product distribution:')
            for empresa in Empresa.objects.all():
                count = Product.objects.filter(empresa=empresa).count()
                self.stdout.write(f'  {empresa.nombre}: {count} products') 