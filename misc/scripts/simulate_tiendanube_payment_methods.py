#!/usr/bin/env python
"""
Script que simula los métodos de pago típicos de Tiendanube.
Uso: docker exec Synap_app python misc/scripts/simulate_tiendanube_payment_methods.py
"""

import os
import sys
import django

# Agregar el directorio raíz al path
sys.path.append('/app')

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

def simulate_tiendanube_payment_methods():
    """Simular métodos de pago típicos de Tiendanube"""
    print("🎯 SIMULACIÓN DE MÉTODOS DE PAGO DE TIENDANUBE")
    print("="*60)
    
    # Métodos de pago típicos de Tiendanube (basado en documentación)
    payment_methods = [
        {
            "id": "credit_card",
            "name": "Tarjeta de Crédito",
            "type": "credit_card",
            "description": "Pago con tarjeta de crédito",
            "enabled": True,
            "installments": True,
            "max_installments": 12
        },
        {
            "id": "debit_card",
            "name": "Tarjeta de Débito",
            "type": "debit_card",
            "description": "Pago con tarjeta de débito",
            "enabled": True,
            "installments": False,
            "max_installments": 1
        },
        {
            "id": "bank_transfer",
            "name": "Transferencia Bancaria",
            "type": "bank_transfer",
            "description": "Pago mediante transferencia bancaria",
            "enabled": True,
            "installments": False,
            "max_installments": 1
        },
        {
            "id": "cash_on_delivery",
            "name": "Contra Reembolso",
            "type": "cash_on_delivery",
            "description": "Pago en efectivo al recibir el producto",
            "enabled": True,
            "installments": False,
            "max_installments": 1
        },
        {
            "id": "mercadopago",
            "name": "MercadoPago",
            "type": "digital_wallet",
            "description": "Pago a través de MercadoPago",
            "enabled": True,
            "installments": True,
            "max_installments": 12
        },
        {
            "id": "paypal",
            "name": "PayPal",
            "type": "digital_wallet",
            "description": "Pago a través de PayPal",
            "enabled": True,
            "installments": False,
            "max_installments": 1
        },
        {
            "id": "stripe",
            "name": "Stripe",
            "type": "credit_card",
            "description": "Pago procesado por Stripe",
            "enabled": True,
            "installments": True,
            "max_installments": 12
        },
        {
            "id": "check",
            "name": "Cheque",
            "type": "check",
            "description": "Pago mediante cheque",
            "enabled": True,
            "installments": False,
            "max_installments": 1
        },
        {
            "id": "wire_transfer",
            "name": "Giro Postal",
            "type": "wire_transfer",
            "description": "Pago mediante giro postal",
            "enabled": True,
            "installments": False,
            "max_installments": 1
        },
        {
            "id": "crypto",
            "name": "Criptomonedas",
            "type": "cryptocurrency",
            "description": "Pago con criptomonedas",
            "enabled": False,
            "installments": False,
            "max_installments": 1
        }
    ]
    
    print(f"✅ Simulación completada")
    print(f"📊 Total de métodos de pago: {len(payment_methods)}")
    
    print("\n📋 MÉTODOS DE PAGO DISPONIBLES:")
    print("-" * 60)
    
    for i, method in enumerate(payment_methods, 1):
        status = "✅ Activo" if method["enabled"] else "❌ Inactivo"
        installments = f"({method['max_installments']} cuotas)" if method["installments"] else "(sin cuotas)"
        
        print(f"{i:2d}. {method['name']} ({method['id']})")
        print(f"     Tipo: {method['type']}")
        print(f"     Estado: {status}")
        print(f"     Cuotas: {installments}")
        print(f"     Descripción: {method['description']}")
        print()
    
    # Mostrar métodos activos para mapeo
    active_methods = [m for m in payment_methods if m["enabled"]]
    print(f"💳 MÉTODOS ACTIVOS PARA MAPEO: {len(active_methods)}")
    print("-" * 60)
    
    for method in active_methods:
        print(f"• {method['name']} ({method['id']})")
    
    return payment_methods

def show_mapping_example():
    """Mostrar ejemplo de mapeo con administraNET"""
    print("\n" + "="*60)
    print("🔗 EJEMPLO DE MAPEO CON ADMINISTRANET")
    print("="*60)
    
    # Ejemplo de mapeo
    mapping_example = [
        {"tiendanube": "credit_card", "adminet": 1, "descripcion": "Contado"},
        {"tiendanube": "debit_card", "adminet": 1, "descripcion": "Contado"},
        {"tiendanube": "mercadopago", "adminet": 2, "descripcion": "Tarjeta"},
        {"tiendanube": "stripe", "adminet": 2, "descripcion": "Tarjeta"},
        {"tiendanube": "bank_transfer", "adminet": 3, "descripcion": "Cheque"},
        {"tiendanube": "cash_on_delivery", "adminet": 4, "descripcion": "Contra Reembolso"},
        {"tiendanube": "paypal", "adminet": 5, "descripcion": "PayPal"},
        {"tiendanube": "check", "adminet": 6, "descripcion": "Cheque"},
        {"tiendanube": "wire_transfer", "adminet": 7, "descripcion": "Giro Postal"},
    ]
    
    print("📋 EJEMPLO DE MAPEO:")
    for mapping in mapping_example:
        print(f"   {mapping['tiendanube']} → {mapping['adminet']} ({mapping['descripcion']})")
    
    print("\n💡 INSTRUCCIONES PARA MAPEO:")
    print("1. Acceder a: /tiendanube/adminet/cond_venta_map/")
    print("2. Para cada método de pago de Tiendanube:")
    print("   - Hacer clic en 'Crear'")
    print("   - Ingresar el nombre del método de pago")
    print("   - Seleccionar la condición de venta correspondiente en administraNET")
    print("   - Activar el switch de sincronización")
    print("3. Guardar el mapeo")

def main():
    """Función principal"""
    # Simular métodos de pago
    payment_methods = simulate_tiendanube_payment_methods()
    
    # Mostrar ejemplo de mapeo
    show_mapping_example()
    
    print("\n" + "="*60)
    print(" RESUMEN")
    print("="*60)
    print("✅ Simulación completada exitosamente")
    print(f"📊 Métodos de pago simulados: {len(payment_methods)}")
    print(f"💳 Métodos activos: {len([m for m in payment_methods if m['enabled']])}")
    print("🔗 Mapeo listo para implementar")
    print("🌐 URL de mapeo: /tiendanube/adminet/cond_venta_map/")

if __name__ == "__main__":
    main() 