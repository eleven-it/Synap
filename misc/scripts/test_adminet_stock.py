#!/usr/bin/env python
"""
Script para inspeccionar la tabla stock_deposito en administraNET y mostrar los primeros registros
"""
import os
import sys
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_project.settings')
django.setup()

from administraNET_integration.models import AdministraNETConfig
from administraNET_integration.services.connection_service import AdministraNETConnectionService

def test_stock_deposito():
    config = AdministraNETConfig.objects.first()
    if not config:
        print("❌ No se encontró configuración de administraNET")
        return
    service = AdministraNETConnectionService(config)
    print("Conexión creada. Consultando stock_deposito...")
    try:
        # Contar registros
        count_result = service.execute_query('SELECT COUNT(*) as total FROM stock_deposito')
        total = count_result[0]['total'] if count_result and 'total' in count_result[0] else 0
        print(f"Total de registros en stock_deposito: {total}")
        if total > 0:
            # Mostrar primeros 5 registros
            sample = service.execute_query('SELECT * FROM stock_deposito LIMIT 5')
            print("Primeros 5 registros:")
            for row in sample:
                print(row)
        else:
            print("No hay registros en stock_deposito.")
    except Exception as e:
        print(f"❌ Error consultando stock_deposito: {e}")

if __name__ == '__main__':
    test_stock_deposito() 