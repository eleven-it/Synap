#!/usr/bin/env python
"""
Script para verificar la conexión con administraNET y los datos disponibles
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from administraNET_integration.models import AdministraNETConfig
from administraNET_integration.services.connection_service import AdministraNETConnectionService

def test_connection():
    """Probar conexión con administraNET"""
    
    # Obtener configuración
    config = AdministraNETConfig.objects.first()
    if not config:
        print("❌ No se encontró configuración de administraNET")
        return
    
    print(f"✅ Configuración encontrada: {config}")
    
    # Crear servicio de conexión
    try:
        service = AdministraNETConnectionService(config)
        print("✅ Servicio de conexión creado")
        
        # Probar conexión
        connection_params = service.get_connection_params()
        print(f"📡 Parámetros de conexión: {connection_params['host']}:{connection_params['port']}/{connection_params['database']}")
        
        # Verificar productos
        try:
            productos = service.get_table_data('articulo')
            print(f"📦 Productos en administraNET: {len(productos)}")
            if productos:
                print(f"   Ejemplo: {productos[0]}")
        except Exception as e:
            print(f"❌ Error obteniendo productos: {e}")
        
        # Verificar stock
        try:
            stock_query = "SELECT COUNT(*) as total FROM stock_deposito"
            stock_result = service.execute_query(stock_query)
            print(f"📊 Stock en administraNET: {stock_result[0]['total'] if stock_result else 0}")
            
            if stock_result and stock_result[0]['total'] > 0:
                # Obtener ejemplo de stock
                sample_query = """
                    SELECT 
                        sd.articulo_id,
                        sd.deposito_id,
                        sd.cantidad,
                        sd.cantidad_reservada,
                        a.codigo as producto_codigo,
                        d.nombre as deposito_nombre
                    FROM stock_deposito sd
                    JOIN articulos a ON sd.articulo_id = a.id
                    JOIN depositos d ON sd.deposito_id = d.id
                    LIMIT 1
                """
                sample = service.execute_query(sample_query)
                if sample:
                    print(f"   Ejemplo de stock: {sample[0]}")
        except Exception as e:
            print(f"❌ Error obteniendo stock: {e}")
        
        # Verificar depósitos
        try:
            depositos = service.get_table_data('depositos')
            print(f"🏪 Depósitos en administraNET: {len(depositos)}")
            if depositos:
                print(f"   Ejemplo: {depositos[0]}")
        except Exception as e:
            print(f"❌ Error obteniendo depósitos: {e}")
        
    except Exception as e:
        print(f"❌ Error creando servicio: {e}")

if __name__ == '__main__':
    test_connection() 