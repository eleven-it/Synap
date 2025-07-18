#!/usr/bin/env python
"""
Script para generar datos de ejemplo para el dashboard de inventario
"""
import os
import sys
import django
import random
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from inventory.models import StockQuant, Product, Location, Warehouse
from core.models import Empresa, Branch

def generate_inventory_data():
    """Generar datos de ejemplo para el dashboard de inventario"""
    
    # Obtener empresa y branch
    empresa = Empresa.objects.first()
    branch = Branch.objects.first()
    
    if not empresa or not branch:
        print("❌ No se encontró empresa o branch")
        return
    
    print(f"🏢 Empresa: {empresa}")
    print(f"🏪 Branch: {branch}")
    
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
        print(f"✅ Warehouse creado: {warehouse}")
    else:
        print(f"📦 Warehouse existente: {warehouse}")
    
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
            print(f"✅ Location creada: {location}")
    
    print(f"📍 Total locations: {len(locations)}")
    
    # Obtener productos
    products = list(Product.objects.filter(empresa=empresa)[:20])
    print(f"📦 Productos disponibles: {len(products)}")
    
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
                reserved_quantity = Decimal(random.randint(0, int(quantity * 0.1)))  # Máximo 10% reservado
                
                StockQuant.objects.create(
                    empresa=empresa,
                    branch=branch,
                    product=product,
                    location=location,
                    quantity=quantity,
                    reserved_quantity=reserved_quantity
                )
                created_count += 1
    
    print(f"✅ StockQuants creados: {created_count}")
    
    # Mostrar estadísticas finales
    total_quants = StockQuant.objects.filter(empresa=empresa).count()
    total_products = Product.objects.filter(empresa=empresa).count()
    total_locations = Location.objects.filter(empresa=empresa).count()
    
    print("\n📊 Estadísticas finales:")
    print(f"   • StockQuants: {total_quants}")
    print(f"   • Productos: {total_products}")
    print(f"   • Locations: {total_locations}")
    print(f"   • Warehouses: {Warehouse.objects.filter(empresa=empresa).count()}")
    
    # Calcular stock total
    stock_stats = StockQuant.objects.filter(empresa=empresa).aggregate(
        total_quantity=Sum('quantity'),
        total_reserved=Sum('reserved_quantity')
    )
    
    total_quantity = stock_stats['total_quantity'] or Decimal('0')
    total_reserved = stock_stats['total_reserved'] or Decimal('0')
    total_available = total_quantity - total_reserved
    
    print(f"   • Stock total: {total_quantity}")
    print(f"   • Stock reservado: {total_reserved}")
    print(f"   • Stock disponible: {total_available}")

if __name__ == '__main__':
    from django.db.models import Sum
    generate_inventory_data() 