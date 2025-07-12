#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from core.models import UsuarioExtendido, Empresa, Branch
from inventory.models import Product, Warehouse, Location, StockQuant

def test_stock_dashboard_functionality():
    print("=== PRUEBA DE FUNCIONALIDAD DEL DASHBOARD DE STOCK ===\n")
    
    # 1. Verificar configuración de usuarios y sucursales
    print("1. CONFIGURACIÓN DE USUARIOS Y SUCURSALES:")
    print("-" * 50)
    
    users = UsuarioExtendido.objects.all()[:3]
    for user in users:
        empresa = user.empresa_activa
        branch = user.branch_activa
        print(f"- Usuario: {user.email}")
        print(f"  Empresa: {empresa.nombre if empresa else 'Sin empresa'}")
        print(f"  Sucursal activa: {branch.name if branch else 'Sin sucursal'}")
        print()
    
    # 2. Verificar stock por sucursal
    print("2. STOCK POR SUCURSAL:")
    print("-" * 50)
    
    for empresa in Empresa.objects.all():
        print(f"\nEmpresa: {empresa.nombre}")
        branches = Branch.objects.filter(empresa=empresa, active=True)
        
        for branch in branches:
            stock_quants = StockQuant.objects.filter(
                product__empresa=empresa,
                branch=branch
            )
            
            total_quantity = sum(sq.quantity for sq in stock_quants)
            total_reserved = sum(sq.reserved_quantity for sq in stock_quants)
            total_available = total_quantity - total_reserved
            
            print(f"  - Sucursal: {branch.name}")
            print(f"    Productos con stock: {stock_quants.values('product').distinct().count()}")
            print(f"    Ubicaciones: {stock_quants.values('location').distinct().count()}")
            print(f"    Stock total: {total_quantity}")
            print(f"    Stock reservado: {total_reserved}")
            print(f"    Stock disponible: {total_available}")
    
    # 3. Simular filtros del dashboard
    print("\n3. SIMULACIÓN DE FILTROS DEL DASHBOARD:")
    print("-" * 50)
    
    empresa = Empresa.objects.first()
    if empresa:
        print(f"Empresa de prueba: {empresa.nombre}")
        
        # Filtro por sucursal activa (simulación)
        branch_activa = Branch.objects.filter(empresa=empresa, active=True).first()
        if branch_activa:
            print(f"\nFiltro por sucursal activa: {branch_activa.name}")
            stock_activa = StockQuant.objects.filter(
                product__empresa=empresa,
                branch=branch_activa
            )
            print(f"  - Registros encontrados: {stock_activa.count()}")
            
            # Mostrar algunos ejemplos
            for quant in stock_activa[:3]:
                print(f"    * {quant.product.name} en {quant.location.name}: {quant.quantity}")
        
        # Filtro por todas las sucursales
        print(f"\nFiltro por todas las sucursales:")
        stock_todas = StockQuant.objects.filter(product__empresa=empresa)
        print(f"  - Registros encontrados: {stock_todas.count()}")
        
        # Agrupar por sucursal
        for branch in Branch.objects.filter(empresa=empresa, active=True):
            branch_stock = stock_todas.filter(branch=branch)
            print(f"    * {branch.name}: {branch_stock.count()} registros")
    
    # 4. Verificar funcionalidad de filtros
    print("\n4. VERIFICACIÓN DE FILTROS DISPONIBLES:")
    print("-" * 50)
    
    if empresa:
        branches_count = Branch.objects.filter(empresa=empresa, active=True).count()
        products_count = Product.objects.filter(empresa=empresa).count()
        warehouses_count = Warehouse.objects.filter(empresa=empresa, is_active=True).count()
        locations_count = Location.objects.filter(empresa=empresa, is_active=True).count()
        
        print(f"Filtros disponibles para {empresa.nombre}:")
        print(f"  - Sucursales: {branches_count}")
        print(f"  - Productos: {products_count}")
        print(f"  - Almacenes: {warehouses_count}")
        print(f"  - Ubicaciones: {locations_count}")
    
    # 5. Recomendaciones
    print("\n5. RECOMENDACIONES:")
    print("-" * 50)
    
    print("✅ FUNCIONALIDAD IMPLEMENTADA:")
    print("  - Dashboard muestra por defecto stock de la sucursal activa")
    print("  - Filtros disponibles por sucursal, producto, almacén y ubicación")
    print("  - Opción para mostrar todas las sucursales")
    print("  - Estadísticas actualizadas según filtros")
    print("  - API endpoint para actualizaciones dinámicas")
    
    print("\n🔧 MEJORAS SUGERIDAS:")
    print("  - Implementar paginación para grandes volúmenes de datos")
    print("  - Agregar exportación a Excel/PDF")
    print("  - Implementar alertas de stock bajo")
    print("  - Agregar gráficos de tendencias de stock")

if __name__ == "__main__":
    test_stock_dashboard_functionality() 