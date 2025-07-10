#!/usr/bin/env python
"""
Test completo de funcionalidad de Tiendanube con sistema de tags
Crea clientes, productos, stock y ejecuta sincronizaciones
"""

import os
import sys
import django
from decimal import Decimal
import random

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import models
from core.models import Empresa, Branch, Contact, Currency, UnitOfMeasure
from sales.models import Client
from inventory.models import Product, Category, Brand, StockQuant, Location, Warehouse, StockMove
from tiendanube.models import TiendaNubeConfig, TiendaNubeCustomerMapping, TiendaNubeProductMapping
from tiendanube.services import TiendaNubeService

User = get_user_model()

def setup_test_environment():
    """Configurar entorno de prueba con empresa, sucursal y configuraciones básicas"""
    print("🔧 Configurando entorno de prueba...")
    
    # Obtener o crear empresa y sucursal
    empresa, created = Empresa.objects.get_or_create(
        nombre="Empresa Test Tiendanube",
        defaults={
            'activa': True,
            'identificador_fiscal': '20-12345678-9',
            'email': 'test@tiendanube.com',
            'telefono': '+54 11 1234-5678',
            'direccion': 'Calle Test 123',
            'ciudad': 'Buenos Aires',
            'pais': 'Argentina'
        }
    )
    print(f"   Empresa: {empresa.nombre} {'(creada)' if created else '(existente)'}")
    
    branch, created = Branch.objects.get_or_create(
        name="Sucursal Test",
        empresa=empresa,
        defaults={
            'active': True,
            'address': 'Calle Test 123',
            'city': 'Buenos Aires',
            'state': 'Buenos Aires',
            'country': 'Argentina',
            'phone': '+54 11 1234-5678',
            'email': 'sucursal@tiendanube.com'
        }
    )
    print(f"   Sucursal: {branch.name} {'(creada)' if created else '(existente)'}")
    
    # Obtener o crear moneda y unidad de medida
    currency, created = Currency.objects.get_or_create(
        code='ARS',
        defaults={'name': 'Peso Argentino', 'symbol': '$'}
    )
    
    uom, created = UnitOfMeasure.objects.get_or_create(
        name='Unidad',
        defaults={'code': 'U', 'type': 'unit'}
    )
    
    # Obtener o crear categoría y marca
    category, created = Category.objects.get_or_create(
        name='Test Category',
        defaults={'is_active': True}
    )
    
    brand, created = Brand.objects.get_or_create(
        name='Test Brand',
        defaults={'is_active': True}
    )
    
    # Obtener o crear almacén y ubicación
    warehouse, created = Warehouse.objects.get_or_create(
        code='TEST-WH',
        defaults={
            'name': 'Almacén Test',
            'empresa': empresa,
            'branch': branch,
            'is_active': True
        }
    )
    
    location, created = Location.objects.get_or_create(
        name='Ubicación Principal',
        empresa=empresa,
        branch=branch,
        defaults={
            'warehouse': warehouse,
            'is_active': True,
            'allow_operations': True
        }
    )
    
    print("✅ Entorno de prueba configurado")
    return empresa, branch, currency, uom, category, brand, warehouse, location

def create_test_clients(empresa, branch):
    """Crear 5 clientes (3 con tag tiendanube, 2 sin tag)"""
    print("\n👥 Creando clientes de prueba...")
    
    clients_data = [
        # Clientes con tag tiendanube
        {
            'name': 'Cliente Tiendanube 1',
            'email': 'cliente1@tiendanube.com',
            'document_number': 'DNI12345678',
            'tags': 'tiendanube,premium',
            'tiendanube': True
        },
        {
            'name': 'Cliente Tiendanube 2',
            'email': 'cliente2@tiendanube.com',
            'document_number': 'DNI87654321',
            'tags': 'tiendanube,regular',
            'tiendanube': True
        },
        {
            'name': 'Cliente Tiendanube 3',
            'email': 'cliente3@tiendanube.com',
            'document_number': 'DNI11223344',
            'tags': 'tiendanube,nuevo',
            'tiendanube': True
        },
        # Clientes sin tag tiendanube
        {
            'name': 'Cliente Local 1',
            'email': 'cliente1@local.com',
            'document_number': 'DNI55667788',
            'tags': 'local,frecuente',
            'tiendanube': False
        },
        {
            'name': 'Cliente Local 2',
            'email': 'cliente2@local.com',
            'document_number': 'DNI99887766',
            'tags': 'local,ocasional',
            'tiendanube': False
        }
    ]
    
    created_clients = []
    
    for i, client_data in enumerate(clients_data, 1):
        # Crear Contact
        contact, created = Contact.objects.get_or_create(
            email=client_data['email'],
            defaults={
                'name': client_data['name'],
                'phone': f'+54 11 1234-{i:04d}',
                'address': f'Calle Cliente {i} 123',
                'city': 'Buenos Aires',
                'state': 'Buenos Aires',
                'country': 'Argentina',
                'notes': client_data['document_number'],
                'tags': client_data['tags']
            }
        )
        
        # Crear Client
        client, created = Client.objects.get_or_create(
            email=client_data['email'],
            defaults={
                'name': client_data['name'],
                'document_number': client_data['document_number'],
                'type': 'individual',
                'credit_limit': Decimal('10000.00'),
                'empresa': empresa
            }
        )
        
        # Vincular Contact con Client
        if not client.has_contact(contact, relationship_type='primary'):
            client.add_contact_relationship(contact, relationship_type='primary')
        
        created_clients.append({
            'client': client,
            'contact': contact,
            'tiendanube': client_data['tiendanube']
        })
        
        print(f"   Cliente {i}: {client.name} {'(Tiendanube)' if client_data['tiendanube'] else '(Local)'}")
    
    print(f"✅ {len(created_clients)} clientes creados")
    return created_clients

def create_test_products(empresa, branch, currency, uom, category, brand):
    """Crear 5 productos (4 con tag tiendanube, 1 sin tag) con precios aleatorios"""
    print("\n📦 Creando productos de prueba...")
    
    products_data = [
        # Productos con tag tiendanube
        {
            'name': 'Producto Tiendanube 1 - Camiseta Premium',
            'sku': 'TN-CAM-001',
            'description': 'Camiseta de algodón premium para venta online',
            'price': Decimal('2500.00'),
            'tags': 'tiendanube,ropa,camiseta',
            'tiendanube': True
        },
        {
            'name': 'Producto Tiendanube 2 - Taza Personalizada',
            'sku': 'TN-TAZ-001',
            'description': 'Taza de cerámica personalizable',
            'price': Decimal('1800.00'),
            'tags': 'tiendanube,hogar,taza',
            'tiendanube': True
        },
        {
            'name': 'Producto Tiendanube 3 - Libro Digital',
            'sku': 'TN-LIB-001',
            'description': 'Libro digital sobre emprendimiento',
            'price': Decimal('1200.00'),
            'tags': 'tiendanube,digital,libro',
            'tiendanube': True
        },
        {
            'name': 'Producto Tiendanube 4 - Auriculares',
            'sku': 'TN-AUR-001',
            'description': 'Auriculares inalámbricos bluetooth',
            'price': Decimal('4500.00'),
            'tags': 'tiendanube,tecnologia,auriculares',
            'tiendanube': True
        },
        # Producto sin tag tiendanube
        {
            'name': 'Producto Local - Servicio de Consultoría',
            'sku': 'LOC-CON-001',
            'description': 'Servicio de consultoría empresarial local',
            'price': Decimal('8000.00'),
            'tags': 'local,servicio,consultoria',
            'tiendanube': False
        }
    ]
    
    created_products = []
    
    for i, product_data in enumerate(products_data, 1):
        product, created = Product.objects.get_or_create(
            sku=product_data['sku'],
            defaults={
                'name': product_data['name'],
                'description': product_data['description'],
                'price': product_data['price'],
                'price_currency': currency,
                'uom': uom,
                'category': category,
                'brand': brand,
                'is_published': True,
                'tags': product_data['tags'],
                'empresa': empresa,
                'branch': branch,
                'type': 'stockable',
                'product_kind': 'physical' if i < 5 else 'digital'
            }
        )
        
        created_products.append({
            'product': product,
            'tiendanube': product_data['tiendanube']
        })
        
        print(f"   Producto {i}: {product.name} - ${product.price} {'(Tiendanube)' if product_data['tiendanube'] else '(Local)'}")
    
    print(f"✅ {len(created_products)} productos creados")
    return created_products

def create_stock_movements(products, location):
    """Crear movimientos de stock: 5 unidades para productos Tiendanube, 2 para local"""
    print("\n📊 Creando movimientos de stock...")
    
    for product_info in products:
        product = product_info['product']
        is_tiendanube = product_info['tiendanube']
        
        # Cantidad según tipo de producto
        quantity = Decimal('5.0') if is_tiendanube else Decimal('2.0')
        
        # Crear movimiento de stock (entrada)
        stock_move, created = StockMove.objects.get_or_create(
            product=product,
            reference=f'Stock inicial {product.sku}',
            defaults={
                'empresa': product.empresa,
                'branch': product.branch,
                'quantity': quantity,
                'from_location': location,  # Ubicación origen (puede ser proveedor)
                'to_location': location,    # Ubicación destino
                'move_type': 'incoming',
                'state': 'done'
            }
        )
        
        # Crear o actualizar StockQuant
        stock_quant, created = StockQuant.objects.get_or_create(
            product=product,
            location=location,
            defaults={
                'empresa': product.empresa,
                'branch': product.branch,
                'quantity': quantity,
                'reserved_quantity': Decimal('0.0')
            }
        )
        
        if not created:
            stock_quant.quantity = quantity
            stock_quant.save()
        
        print(f"   Stock {product.sku}: {quantity} unidades {'(Tiendanube)' if is_tiendanube else '(Local)'}")
    
    print("✅ Movimientos de stock creados")

def test_synchronization():
    """Ejecutar sincronizaciones completas"""
    print("\n🔄 Ejecutando sincronizaciones...")
    
    # Obtener configuración de Tiendanube
    config = TiendaNubeConfig.objects.first()
    if not config:
        print("❌ No hay configuración de Tiendanube activa")
        return
    
    service = TiendaNubeService(config)
    
    # Test 1: Sincronización de clientes
    print("\n📋 Test 1: Sincronización de clientes")
    try:
        success_count, failed_count = service.sync_all_customers_to_tiendanube()
        print(f"   Clientes sincronizados: {success_count}, Fallidos: {failed_count}")
    except Exception as e:
        print(f"   ❌ Error en sincronización de clientes: {e}")
    
    # Test 2: Sincronización de productos
    print("\n📦 Test 2: Sincronización de productos")
    try:
        success_count, failed_count = service.sync_all_products_to_tiendanube()
        print(f"   Productos sincronizados: {success_count}, Fallidos: {failed_count}")
    except Exception as e:
        print(f"   ❌ Error en sincronización de productos: {e}")
    
    # Test 3: Sincronización de stock
    print("\n📊 Test 3: Sincronización de stock")
    try:
        success_count, failed_count = service.sync_all_stock_to_tiendanube()
        print(f"   Stock sincronizado: {success_count}, Fallidos: {failed_count}")
    except Exception as e:
        print(f"   ❌ Error en sincronización de stock: {e}")

def show_test_results():
    """Mostrar resultados del test"""
    print("\n📈 Resultados del test:")
    
    # Estadísticas de clientes
    total_clients = Client.objects.count()
    clients_with_tiendanube = Client.objects.filter(contact_relationships__contact__tags__icontains='tiendanube').distinct().count()
    
    print(f"   Clientes totales: {total_clients}")
    print(f"   Clientes con tag tiendanube: {clients_with_tiendanube}")
    
    # Estadísticas de productos
    total_products = Product.objects.count()
    products_with_tiendanube = Product.objects.filter(tags__icontains='tiendanube').count()
    
    print(f"   Productos totales: {total_products}")
    print(f"   Productos con tag tiendanube: {products_with_tiendanube}")
    
    # Estadísticas de mappings
    customer_mappings = TiendaNubeCustomerMapping.objects.count()
    product_mappings = TiendaNubeProductMapping.objects.count()
    
    print(f"   Mappings de clientes: {customer_mappings}")
    print(f"   Mappings de productos: {product_mappings}")
    
    # Estadísticas de stock
    total_stock = StockQuant.objects.aggregate(total=models.Sum('quantity'))['total'] or 0
    tiendanube_stock = StockQuant.objects.filter(
        product__tags__icontains='tiendanube'
    ).aggregate(total=models.Sum('quantity'))['total'] or 0
    
    print(f"   Stock total: {total_stock}")
    print(f"   Stock productos Tiendanube: {tiendanube_stock}")

def main():
    """Función principal del test"""
    print("🚀 Iniciando test completo de integración Tiendanube")
    print("=" * 60)
    
    try:
        # 1. Configurar entorno
        empresa, branch, currency, uom, category, brand, warehouse, location = setup_test_environment()
        
        # 2. Crear clientes
        clients = create_test_clients(empresa, branch)
        
        # 3. Crear productos
        products = create_test_products(empresa, branch, currency, uom, category, brand)
        
        # 4. Crear movimientos de stock
        create_stock_movements(products, location)
        
        # 5. Ejecutar sincronizaciones
        test_synchronization()
        
        # 6. Mostrar resultados
        show_test_results()
        
        print("\n✅ Test completado exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error en el test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 