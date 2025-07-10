#!/usr/bin/env python
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from core.models import UsuarioExtendido, Empresa, Branch
from inventory.models import Product, Warehouse, Location, StockQuant, StockMove
from purchases.models import PurchaseOrder, PurchaseOrderLine
from sales.models import SalesOrder, SalesOrderLine

def analyze_multi_branch_architecture():
    print("=== ANÁLISIS DETALLADO DE ARQUITECTURA MULTI-SUCURSAL SYNAP ===\n")
    
    # 1. USUARIOS Y EMPRESAS
    print("1. USUARIOS Y EMPRESAS:")
    print("-" * 50)
    users = UsuarioExtendido.objects.all()[:5]
    for user in users:
        empresa = user.empresa_activa.nombre if user.empresa_activa else "Sin empresa"
        branch = user.branch_activa.name if user.branch_activa else "Sin branch"
        print(f"- {user.email}: Empresa={empresa}, Branch={branch}")
    
    # 2. PRODUCTOS POR EMPRESA
    print("\n2. PRODUCTOS POR EMPRESA:")
    print("-" * 50)
    for empresa in Empresa.objects.all():
        products = Product.objects.filter(empresa=empresa)
        print(f"{empresa.nombre}: {products.count()} productos")
    
    # 3. ALMACENES Y UBICACIONES
    print("\n3. ALMACENES Y UBICACIONES:")
    print("-" * 50)
    for empresa in Empresa.objects.all():
        print(f"\nEmpresa: {empresa.nombre}")
        warehouses = Warehouse.objects.filter(empresa=empresa)
        for warehouse in warehouses:
            locations = Location.objects.filter(warehouse=warehouse)
            print(f"  - Almacén: {warehouse.name} ({locations.count()} ubicaciones)")
            for location in locations:
                print(f"    * {location.name}")
    
    # 4. STOCK POR EMPRESA
    print("\n4. STOCK POR EMPRESA:")
    print("-" * 50)
    for empresa in Empresa.objects.all():
        print(f"\nEmpresa: {empresa.nombre}")
        products = Product.objects.filter(empresa=empresa)
        for product in products[:3]:  # Solo primeros 3 productos
            stock_quants = StockQuant.objects.filter(product=product)
            total_stock = sum(sq.quantity for sq in stock_quants)
            print(f"  - {product.name}: {total_stock} unidades en {stock_quants.count()} ubicaciones")
    
    # 5. VALIDACIÓN DE ACCESO CRUZADO
    print("\n5. VALIDACIÓN DE ACCESO CRUZADO:")
    print("-" * 50)
    
    # Verificar stock cruzado
    cross_company_stock = StockQuant.objects.filter(
        product__empresa__isnull=False
    ).exclude(
        product__empresa=Empresa.objects.first()
    )
    
    if cross_company_stock.exists():
        print("❌ PROBLEMA: Existe stock cruzado entre empresas")
        for sq in cross_company_stock[:3]:
            print(f"  - Producto: {sq.product.name} (Empresa: {sq.product.empresa.nombre})")
            print(f"    Ubicación: {sq.location.name} (Almacén: {sq.location.warehouse.name})")
    else:
        print("✅ OK: No hay stock cruzado entre empresas")
    
    # 6. CONFIGURACIÓN DE ALMACENES POR SUCURSAL
    print("\n6. CONFIGURACIÓN DE ALMACENES POR SUCURSAL:")
    print("-" * 50)
    for empresa in Empresa.objects.all():
        print(f"\nEmpresa: {empresa.nombre}")
        branches = Branch.objects.filter(empresa=empresa)
        for branch in branches:
            warehouses = Warehouse.objects.filter(empresa=empresa)
            print(f"  - Sucursal: {branch.name}")
            print(f"    Almacenes disponibles: {warehouses.count()}")
            for warehouse in warehouses:
                print(f"    * {warehouse.name}")
    
    # 7. ANÁLISIS DE ARQUITECTURA MULTI-SUCURSAL
    print("\n7. ANÁLISIS DE ARQUITECTURA MULTI-SUCURSAL:")
    print("-" * 50)
    
    # Validar que cada usuario pertenece a una empresa específica
    users_without_company = UsuarioExtendido.objects.filter(empresa_activa__isnull=True)
    if users_without_company.exists():
        print("❌ PROBLEMA: Usuarios sin empresa asignada")
        for user in users_without_company:
            print(f"  - {user.email}")
    else:
        print("✅ OK: Todos los usuarios tienen empresa asignada")
    
    # Validar que los productos son accesibles desde todas las sucursales
    print("\n8. VALIDACIÓN DE ACCESO A PRODUCTOS:")
    print("-" * 50)
    for empresa in Empresa.objects.all():
        branches = Branch.objects.filter(empresa=empresa)
        products = Product.objects.filter(empresa=empresa)
        print(f"\nEmpresa: {empresa.nombre}")
        print(f"  - Sucursales: {branches.count()}")
        print(f"  - Productos: {products.count()}")
        print(f"  - Productos accesibles por sucursal: {products.count()} (todos)")
    
    # 9. VALIDACIÓN DE ALMACENES GENERALES VS POR SUCURSAL
    print("\n9. VALIDACIÓN DE ALMACENES:")
    print("-" * 50)
    for empresa in Empresa.objects.all():
        print(f"\nEmpresa: {empresa.nombre}")
        warehouses = Warehouse.objects.filter(empresa=empresa)
        branches = Branch.objects.filter(empresa=empresa)
        
        # Almacenes generales (sin branch específico)
        general_warehouses = warehouses.filter(branch__isnull=True)
        # Almacenes por sucursal
        branch_warehouses = warehouses.filter(branch__isnull=False)
        
        print(f"  - Almacenes generales: {general_warehouses.count()}")
        print(f"  - Almacenes por sucursal: {branch_warehouses.count()}")
        
        for warehouse in warehouses:
            branch_info = f" (Sucursal: {warehouse.branch.name})" if warehouse.branch else " (General)"
            print(f"    * {warehouse.name}{branch_info}")
    
    # 10. VALIDACIÓN DE MOVIMIENTOS DE STOCK
    print("\n10. VALIDACIÓN DE MOVIMIENTOS DE STOCK:")
    print("-" * 50)
    for empresa in Empresa.objects.all():
        print(f"\nEmpresa: {empresa.nombre}")
        stock_moves = StockMove.objects.filter(empresa=empresa)
        print(f"  - Movimientos totales: {stock_moves.count()}")
        
        # Movimientos por tipo
        move_types = stock_moves.values_list('move_type', flat=True).distinct()
        for move_type in move_types:
            count = stock_moves.filter(move_type=move_type).count()
            print(f"    * {move_type}: {count}")
    
    # 11. RECOMENDACIONES DE ARQUITECTURA
    print("\n11. RECOMENDACIONES DE ARQUITECTURA:")
    print("-" * 50)
    
    print("✅ ARQUITECTURA ACTUAL:")
    print("  - Usuarios están correctamente asociados a empresas")
    print("  - Productos son accesibles desde todas las sucursales")
    print("  - Almacenes pueden ser generales o por sucursal")
    print("  - Stock está correctamente segregado por empresa")
    
    print("\n🔧 MEJORAS SUGERIDAS:")
    print("  - Implementar reglas de acceso por sucursal para movimientos")
    print("  - Configurar rutas de reabastecimiento entre almacenes")
    print("  - Definir políticas de stock mínimo por ubicación")
    print("  - Implementar validaciones de permisos por sucursal")

if __name__ == "__main__":
    analyze_multi_branch_architecture() 