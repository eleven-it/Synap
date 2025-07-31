#!/usr/bin/env python3
"""
Test del algoritmo de parsing de direcciones de Tiendanube a AdministraNET.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from tiendanube_administranet.services.automatic_mapping_service import AutomaticMappingService

def test_address_parsing():
    """Prueba el algoritmo de parsing con diferentes formatos de direcciones."""
    
    service = AutomaticMappingService()
    
    # Casos de prueba
    test_cases = [
        # Formato básico
        ("Av. Corrientes 1234", ("Av. Corrientes", "1234", "")),
        ("San Martín 567", ("San Martín", "567", "")),
        
        # Con departamento
        ("Calle de la Plata 500, Piso 3, Dpto A", ("Calle de la Plata", "500", "3 A")),
        ("Belgrano 1234, 2do piso", ("Belgrano", "1234", "2do piso")),
        ("Rivadavia 890, Local 15", ("Rivadavia", "890", "15")),
        
        # Con bis/ter
        ("San Martín 1234 bis", ("San Martín", "1234 bis", "")),
        ("Corrientes 567 ter", ("Corrientes", "567 ter", "")),
        
        # Con letras en el número
        ("Belgrano 1234A", ("Belgrano", "1234A", "")),
        ("Rivadavia 567B", ("Rivadavia", "567B", "")),
        
        # Con rangos
        ("San Martín 1234-5678", ("San Martín", "1234-5678", "")),
        
        # Solo calle sin número
        ("Calle sin número", ("Calle sin número", "", "")),
        ("Av. Siempreviva", ("Av. Siempreviva", "", "")),
        
        # Solo número (caso edge)
        ("1234", ("1234", "", "")),
        
        # Con múltiples departamentos
        ("Corrientes 500, Piso 2, Dpto B, Local 5", ("Corrientes", "500", "2 B 5")),
        
        # Con espacios extra
        ("  San Martín   1234  ,  Piso 3  ", ("San Martín", "1234", "3")),
        
        # Con comas múltiples
        ("Belgrano, 567, Local, 10", ("Belgrano", "567", "10")),
        
        # Direcciones complejas
        ("Av. 9 de Julio 1234, Piso 5, Dpto C", ("Av. 9 de Julio", "1234", "5 C")),
        ("Calle 25 de Mayo 890, 1er piso, Local 3", ("Calle 25 de Mayo", "890", "1er piso 3")),
    ]
    
    print("🧪 **Pruebas de Parsing de Direcciones**\n")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, (input_address, expected) in enumerate(test_cases, 1):
        try:
            result = service._parse_tiendanube_address(input_address)
            
            if result == expected:
                status = "✅ PASÓ"
                passed += 1
            else:
                status = "❌ FALLÓ"
                failed += 1
            
            print(f"{i:2d}. {status}")
            print(f"    Entrada:  '{input_address}'")
            print(f"    Esperado: {expected}")
            print(f"    Obtenido: {result}")
            
            if result != expected:
                print(f"    ❌ DIFERENCIA DETECTADA!")
            
            print()
            
        except Exception as e:
            print(f"{i:2d}. ❌ ERROR: {e}")
            print(f"    Entrada: '{input_address}'")
            print()
            failed += 1
    
    print("=" * 80)
    print(f"📊 **RESULTADOS:**")
    print(f"   ✅ Pasaron: {passed}")
    print(f"   ❌ Fallaron: {failed}")
    print(f"   📈 Total: {passed + failed}")
    print(f"   🎯 Porcentaje éxito: {(passed / (passed + failed) * 100):.1f}%")
    
    if failed == 0:
        print("\n🎉 ¡TODAS LAS PRUEBAS PASARON!")
    else:
        print(f"\n⚠️  {failed} pruebas fallaron. Revisar el algoritmo.")

def test_edge_cases():
    """Prueba casos edge y límite."""
    
    service = AutomaticMappingService()
    
    edge_cases = [
        ("", ("", "", "")),  # String vacío
        ("   ", ("", "", "")),  # Solo espacios
        ("123", ("123", "", "")),  # Solo números
        ("abc", ("abc", "", "")),  # Solo letras
        ("123 abc", ("abc", "123", "")),  # Número al inicio
        ("abc 123 def", ("abc", "123", "def")),  # Número en medio
        ("abc def 123", ("abc def", "123", "")),  # Número al final
    ]
    
    print("\n🔍 **Casos Edge y Límite**\n")
    print("=" * 50)
    
    for input_address, expected in edge_cases:
        result = service._parse_tiendanube_address(input_address)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{input_address}' → {result}")

if __name__ == "__main__":
    test_address_parsing()
    test_edge_cases() 