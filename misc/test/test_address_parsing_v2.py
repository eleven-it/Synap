#!/usr/bin/env python3
"""
Test del algoritmo mejorado de parsing de direcciones de Tiendanube a AdministraNET.
"""

import re

def parse_tiendanube_address(address_string: str) -> tuple:
    """
    Parsea la dirección de Tiendanube y la separa en campos de AdministraNET.
    Maneja múltiples formatos de direcciones argentinas.
    Retorna: (calle, nro_calle, dpto)
    """
    if not address_string:
        return '', '', ''
    
    # Limpiar la dirección
    address = address_string.strip()
    
    # Primero, extraer información de departamento/piso
    dpto_info = extract_department_info(address)
    address = dpto_info['clean_address']
    dpto = dpto_info['department']
    
    # Luego, extraer calle y número
    street_info = extract_street_and_number(address)
    calle = street_info['street']
    nro_calle = street_info['number']
    
    return calle, nro_calle, dpto

def extract_department_info(address: str) -> dict:
    """Extrae información de departamento/piso de la dirección."""
    # Patrones para departamentos/pisos
    dpto_patterns = [
        r',?\s*(?:piso|p\.|pis\.)\s*(\d+)(?:\s*,?\s*(?:dpto|depto|dpt\.|apto|apt\.)\s*([a-zA-Z0-9]+))?',
        r',?\s*(?:dpto|depto|dpt\.|apto|apt\.)\s*([a-zA-Z0-9]+)',
        r',?\s*(?:local|l\.)\s*(\d+)',
        r',?\s*(\d+)\s*(?:piso|p\.)',
        r',?\s*(\d+)\s*(?:dpto|depto|dpt\.)',
        r',?\s*(\d+)\s*(?:local|l\.)',
        r',?\s*([a-zA-Z0-9]+)\s*(?:dpto|depto|dpt\.)',
        r',?\s*(?:piso|p\.|pis\.)\s*([a-zA-Z0-9]+)(?:\s*,?\s*(?:dpto|depto|dpt\.|apto|apt\.)\s*([a-zA-Z0-9]+))?',
        r',?\s*(?:dpto|depto|dpt\.|apto|apt\.)\s*(\d+)',
    ]
    
    dpto_match = None
    dpto_text = ''
    
    for pattern in dpto_patterns:
        match = re.search(pattern, address, re.IGNORECASE)
        if match:
            dpto_match = match
            dpto_text = match.group(0)
            break
    
    if dpto_match:
        # Remover el texto del departamento
        clean_address = address[:dpto_match.start()] + address[dpto_match.end():]
        clean_address = clean_address.strip()
        
        # Extraer información del departamento
        dpto_parts = []
        for group in dpto_match.groups():
            if group:
                dpto_parts.append(group)
        
        if dpto_parts:
            department = ' '.join(dpto_parts)
        else:
            department = dpto_text.strip(' ,')
    else:
        clean_address = address
        department = ''
    
    return {
        'clean_address': clean_address,
        'department': department
    }

def extract_street_and_number(address: str) -> dict:
    """Extrae calle y número de la dirección."""
    # Patrones para números de calle
    number_patterns = [
        r'\b(\d+)\s*(?:bis|ter|quater)?\b',  # 1234, 1234 bis, 1234 ter
        r'\b(\d+[a-zA-Z])\b',  # 1234A, 1234B
        r'\b(\d+)\s*-\s*(\d+)\b',  # 1234-5678
    ]
    
    # Buscar el número
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
        street = address[:number_match.start()].strip()
        number = number_text
        
        # Limpiar la calle
        street = re.sub(r'[,\s]+$', '', street)
    else:
        street = address
        number = ''
    
    # Lógica especial para calles con números en el nombre
    if street and not number:
        street_parts = street.split()
        if len(street_parts) >= 3:
            # Verificar si el último elemento es un número
            last_part = street_parts[-1]
            if last_part.isdigit():
                # Es un número de dirección
                street = ' '.join(street_parts[:-1])
                number = last_part
            elif len(street_parts) >= 4:
                # Verificar patrones como "Av. 9 de Julio" o "Calle 25 de Mayo"
                # Si hay un número en el medio, es parte del nombre
                for i, part in enumerate(street_parts):
                    if part.isdigit() and i < len(street_parts) - 1:
                        # Es parte del nombre de la calle
                        continue
                    elif part.isdigit() and i == len(street_parts) - 1:
                        # Es un número de dirección al final
                        street = ' '.join(street_parts[:-1])
                        number = part
                        break
    
    return {
        'street': street.strip(),
        'number': number.strip()
    }

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
    
    print("🧪 **Pruebas de Parsing de Direcciones V2**\n")
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

if __name__ == "__main__":
    test_address_parsing() 