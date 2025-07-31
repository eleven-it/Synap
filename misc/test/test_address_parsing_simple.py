#!/usr/bin/env python3
"""
Test simplificado del algoritmo de parsing de direcciones.
"""

import re

def parse_tiendanube_address(address_string: str) -> tuple:
    """
    Parsea la dirección de Tiendanube y la separa en campos de AdministraNET.
    Maneja múltiples formatos de direcciones argentinas.
    Retorna: (calle, nro_calle, dpto)
    
    Ejemplos soportados:
    - "Av. Corrientes 1234"
    - "Calle de la Plata 500, Piso 3, Dpto A"
    - "San Martín 1234 bis"
    - "Belgrano 567, 2do piso"
    - "Rivadavia 890, Local 15"
    """
    if not address_string:
        return '', '', ''
    
    # Limpiar la dirección
    address = address_string.strip()
    
    # Patrones comunes para departamentos/pisos
    dpto_patterns = [
        r',?\s*(?:piso|p\.|pis\.)\s*(\d+)(?:\s*,?\s*(?:dpto|depto|dpt\.|apto|apt\.)\s*([a-zA-Z0-9]+))?',
        r',?\s*(?:dpto|depto|dpt\.|apto|apt\.)\s*([a-zA-Z0-9]+)',
        r',?\s*(?:local|l\.)\s*(\d+)',
        r',?\s*(\d+)\s*(?:piso|p\.)',
        r',?\s*(\d+)\s*(?:dpto|depto|dpt\.)',
        r',?\s*(\d+)\s*(?:local|l\.)',
        r',?\s*([a-zA-Z0-9]+)\s*(?:dpto|depto|dpt\.)',
    ]
    
    # Buscar patrones de departamento/piso
    dpto_match = None
    dpto_text = ''
    for pattern in dpto_patterns:
        match = re.search(pattern, address, re.IGNORECASE)
        if match:
            dpto_match = match
            dpto_text = match.group(0)
            break
    
    # Remover el texto del departamento de la dirección
    if dpto_match:
        address = address[:dpto_match.start()] + address[dpto_match.end():]
        address = address.strip()
    
    # Buscar el número de calle
    # Patrones para números
    number_patterns = [
        r'\b(\d+)\s*(?:bis|ter|quater)?\b',  # 1234, 1234 bis, 1234 ter
        r'\b(\d+[a-zA-Z])\b',  # 1234A, 1234B
        r'\b(\d+)\s*-\s*(\d+)\b',  # 1234-5678
    ]
    
    number_match = None
    number_text = ''
    
    for pattern in number_patterns:
        match = re.search(pattern, address)
        if match:
            number_match = match
            number_text = match.group(0)
            break
    
    if number_match:
        # Separar calle y número
        calle = address[:number_match.start()].strip()
        nro_calle = number_text
        
        # Limpiar la calle de caracteres extra
        calle = re.sub(r'[,\s]+$', '', calle)  # Remover comas y espacios al final
        
    else:
        # No se encontró número
        calle = address
        nro_calle = ''
    
    # Procesar el departamento
    if dpto_match:
        # Extraer solo la información relevante del departamento
        dpto_parts = []
        for group in dpto_match.groups():
            if group:
                dpto_parts.append(group)
        
        if dpto_parts:
            dpto = ' '.join(dpto_parts)
        else:
            # Si no hay grupos capturados, usar el texto completo
            dpto = dpto_text.strip(' ,')
    else:
        dpto = ''
    
    # Limpiar y validar resultados
    calle = calle.strip()
    nro_calle = nro_calle.strip()
    dpto = dpto.strip()
    
    # Si la calle está vacía pero hay número, mover el número a calle
    if not calle and nro_calle:
        calle = nro_calle
        nro_calle = ''
    
    return calle, nro_calle, dpto

def test_address_parsing():
    """Prueba el algoritmo de parsing con diferentes formatos de direcciones."""
    
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
        
        # Direcciones complejas con números en el nombre
        ("Av. 9 de Julio 1234, Piso 5, Dpto C", ("Av. 9 de Julio", "1234", "5 C")),
        ("Calle 25 de Mayo 890, 1er piso, Local 3", ("Calle 25 de Mayo", "890", "1er piso 3")),
        
        # Casos especiales
        ("Av. 9 de Julio 1234", ("Av. 9 de Julio", "1234", "")),
        ("Calle 25 de Mayo 890", ("Calle 25 de Mayo", "890", "")),
    ]
    
    print("🧪 **Pruebas de Parsing de Direcciones**\n")
    print("=" * 80)
    
    passed = 0
    failed = 0
    
    for i, (input_address, expected) in enumerate(test_cases, 1):
        try:
            result = parse_tiendanube_address(input_address)
            
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
        result = parse_tiendanube_address(input_address)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{input_address}' → {result}")

if __name__ == "__main__":
    test_address_parsing()
    test_edge_cases() 