from django.core.management.base import BaseCommand
from django.db.models import Sum
from decimal import Decimal
import random
from inventory.models import StockQuant, Product, Location, Warehouse
from core.models import Empresa, Branch


class Command(BaseCommand):
    help = 'Generar datos de ejemplo para el dashboard de inventario'

    def handle(self, *args, **options):
        # Obtener empresa y branch
        empresa = Empresa.objects.first()
        branch = Branch.objects.first()
        
        if not empresa or not branch:
            self.stdout.write(
                self.style.ERROR('❌ No se encontró empresa o branch')
            )
            return
        
        self.stdout.write(f"🏢 Empresa: {empresa}")
        self.stdout.write(f"🏪 Branch: {branch}")
        
        # Crear warehouse si no existe
        warehouse, created = Warehouse.objects.get_or_create(
            empresa=empresa,
            branch=branch,
            code='ALM-001',
            defaults={
                'name': 'Almacén Principal',
                'address': 'Av. Principal 123',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Warehouse creado: {warehouse}")
            )
        else:
            self.stdout.write(f"📦 Warehouse existente: {warehouse}")
        
        # Crear locations si no existen
        locations_data = [
            {'name': 'Estante A1', 'warehouse': warehouse},
            {'name': 'Estante A2', 'warehouse': warehouse},
            {'name': 'Estante B1', 'warehouse': warehouse},
            {'name': 'Estante B2', 'warehouse': warehouse},
            {'name': 'Estante C1', 'warehouse': warehouse},
            {'name': 'Zona de Recepción', 'warehouse': warehouse},
            {'name': 'Zona de Despacho', 'warehouse': warehouse},
        ]
        
        locations = []
        for loc_data in locations_data:
            location, created = Location.objects.get_or_create(
                empresa=empresa,
                branch=branch,
                name=loc_data['name'],
                defaults={
                    'warehouse': loc_data['warehouse'],
                    'is_active': True,
                    'allow_operations': True
                }
            )
            locations.append(location)
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Location creada: {location}")
                )
        
        self.stdout.write(f"📍 Total locations: {len(locations)}")
        
        # Obtener productos
        products = list(Product.objects.filter(empresa=empresa)[:20])
        self.stdout.write(f"📦 Productos disponibles: {len(products)}")
        
        # Crear StockQuants
        created_count = 0
        for product in products:
            # Crear stock en 2-3 locations por producto
            num_locations = random.randint(2, 3)
            selected_locations = random.sample(locations, num_locations)
            
            for location in selected_locations:
                # Evitar duplicados
                if not StockQuant.objects.filter(
                    empresa=empresa,
                    branch=branch,
                    product=product,
                    location=location
                ).exists():
                    
                    quantity = Decimal(random.randint(10, 200))
                    max_reserved = int(quantity * Decimal('0.1'))  # Máximo 10% reservado
                    reserved_quantity = Decimal(random.randint(0, max_reserved))
                    
                    StockQuant.objects.create(
                        empresa=empresa,
                        branch=branch,
                        product=product,
                        location=location,
                        quantity=quantity,
                        reserved_quantity=reserved_quantity
                    )
                    created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ StockQuants creados: {created_count}")
        )
        
        # Mostrar estadísticas finales
        total_quants = StockQuant.objects.filter(empresa=empresa).count()
        total_products = Product.objects.filter(empresa=empresa).count()
        total_locations = Location.objects.filter(empresa=empresa).count()
        
        self.stdout.write("\n📊 Estadísticas finales:")
        self.stdout.write(f"   • StockQuants: {total_quants}")
        self.stdout.write(f"   • Productos: {total_products}")
        self.stdout.write(f"   • Locations: {total_locations}")
        self.stdout.write(f"   • Warehouses: {Warehouse.objects.filter(empresa=empresa).count()}")
        
        # Calcular stock total
        stock_stats = StockQuant.objects.filter(empresa=empresa).aggregate(
            total_quantity=Sum('quantity'),
            total_reserved=Sum('reserved_quantity')
        )
        
        total_quantity = stock_stats['total_quantity'] or Decimal('0')
        total_reserved = stock_stats['total_reserved'] or Decimal('0')
        total_available = total_quantity - total_reserved
        
        self.stdout.write(f"   • Stock total: {total_quantity}")
        self.stdout.write(f"   • Stock reservado: {total_reserved}")
        self.stdout.write(f"   • Stock disponible: {total_available}")
        
        self.stdout.write(
            self.style.SUCCESS("\n🎉 Datos de inventario generados exitosamente!")
        ) 