#!/usr/bin/env python3
"""
Script para agregar variantes a productos existentes
===================================================

Este script busca productos existentes de la empresa y les agrega variantes
para que el test del TPV pueda funcionar correctamente.
"""

import os
import sys
import django
from decimal import Decimal

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone
from core.models import Empresa, Branch, Currency, UnitOfMeasure
from inventory.models import Product, ProductVariant, Category, Brand, Subcategory

User = get_user_model()

def add_variants_to_products():
    """Agregar variantes a productos existentes"""
    print("🔧 Agregando variantes a productos existentes...")
    
    try:
        # Obtener empresa
        empresa = Empresa.objects.first()
        if not empresa:
            print("❌ No se encontró empresa")
            return False
        
        print(f"📋 Empresa: {empresa.nombre}")
        
        # Obtener productos existentes
        products = Product.objects.filter(empresa=empresa)[:2]  # Tomar 2 productos
        
        if not products:
            print("❌ No se encontraron productos en la empresa")
            return False
        
        print(f"📦 Encontrados {products.count()} productos")
        
        # Obtener categoría, marca y subcategoría por defecto
        category = Category.objects.first()
        brand = Brand.objects.first()
        subcategory = Subcategory.objects.first()
        currency = Currency.objects.first()
        uom = UnitOfMeasure.objects.first()
        
        variants_created = 0
        
        for i, product in enumerate(products):
            print(f"\n📋 Procesando producto: {product.name}")
            
            # Verificar si ya tiene variantes
            existing_variants = ProductVariant.objects.filter(product=product)
            if existing_variants.exists():
                print(f"  ℹ️  Producto ya tiene {existing_variants.count()} variantes")
                variants_created += existing_variants.count()
                continue
            
            # Crear variante principal
            variant = ProductVariant.objects.create(
                product=product,
                sku=f"{product.sku}-VAR-001" if product.sku else f"VAR-{product.id}-001",
                barcode=f"123456789012{i+1}",  # Código de barras único
                price=product.price,
                is_active=True
            )
            
            print(f"  ✅ Variante creada: {variant.sku} (Precio: ${variant.price})")
            variants_created += 1
            
            # Crear una segunda variante para algunos productos
            if i == 0:  # Solo para el primer producto
                variant2 = ProductVariant.objects.create(
                    product=product,
                    sku=f"{product.sku}-VAR-002" if product.sku else f"VAR-{product.id}-002",
                    barcode=f"123456789012{i+1}2",
                    price=product.price * Decimal('1.5'),  # 50% más caro
                    is_active=True
                )
                
                print(f"  ✅ Segunda variante creada: {variant2.sku} (Precio: ${variant2.price})")
                variants_created += 1
        
        print(f"\n🎉 Proceso completado:")
        print(f"  - Productos procesados: {products.count()}")
        print(f"  - Variantes totales: {variants_created}")
        
        # Mostrar resumen de variantes por empresa
        total_variants = ProductVariant.objects.filter(product__empresa=empresa).count()
        print(f"  - Variantes totales en {empresa.nombre}: {total_variants}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

def main():
    """Función principal"""
    print("🚀 Agregando variantes a productos existentes")
    print("=" * 50)
    
    success = add_variants_to_products()
    
    if success:
        print("\n✅ Variantes agregadas exitosamente")
        print("Ahora puedes ejecutar el test del TPV nuevamente")
    else:
        print("\n❌ Error al agregar variantes")
    
    return success

if __name__ == "__main__":
    main() 