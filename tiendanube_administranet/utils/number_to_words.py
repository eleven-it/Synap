#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Utilidad para convertir números a palabras en español.
Basado en la función ESCRITO del formulario Pedido.frm de AdministraNET.
"""

def number_to_words(number):
    """
    Convertir un número a palabras en español.
    
    Args:
        number: Número decimal (float o Decimal)
        
    Returns:
        str: Número en palabras
    """
    try:
        # Convertir a string y separar parte entera y decimal
        number_str = str(number)
        
        if '.' in number_str:
            integer_part, decimal_part = number_str.split('.')
        else:
            integer_part = number_str
            decimal_part = '00'
        
        # Asegurar que la parte decimal tenga 2 dígitos
        decimal_part = decimal_part.ljust(2, '0')[:2]
        
        # Convertir parte entera
        integer_words = _convert_integer_to_words(int(integer_part))
        
        # Convertir centavos
        cents = int(decimal_part)
        if cents > 0:
            cents_words = _convert_integer_to_words(cents)
            if cents == 1:
                result = f"{integer_words} con {cents_words} centavo"
            else:
                result = f"{integer_words} con {cents_words} centavos"
        else:
            result = integer_words
            
        return result.capitalize()
        
    except Exception as e:
        return f"Error convirtiendo número: {e}"


def _convert_integer_to_words(number):
    """
    Convertir número entero a palabras.
    """
    if number == 0:
        return "cero"
    
    # Nombres de números
    units = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve"]
    teens = ["diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", 
             "diecisiete", "dieciocho", "diecinueve"]
    tens = ["", "", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", 
            "setenta", "ochenta", "noventa"]
    hundreds = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", 
                "quinientos", "seiscientos", "setecientos", "ochocientos", "novecientos"]
    
    # Nombres de potencias de 1000
    thousands = ["", "mil", "millón", "mil millones", "billón"]
    
    if number < 0:
        return "menos " + _convert_integer_to_words(-number)
    
    if number < 10:
        return units[number]
    
    if number < 20:
        return teens[number - 10]
    
    if number < 100:
        if number % 10 == 0:
            return tens[number // 10]
        else:
            return tens[number // 10] + " y " + units[number % 10]
    
    if number < 1000:
        if number == 100:
            return "cien"
        elif number % 100 == 0:
            return hundreds[number // 100]
        else:
            return hundreds[number // 100] + " " + _convert_integer_to_words(number % 100)
    
    # Para números mayores a 1000
    result = ""
    power = 0
    
    while number > 0:
        if number % 1000 != 0:
            part = _convert_integer_to_words(number % 1000)
            if power > 0:
                if power == 1 and number % 1000 == 1:
                    part = "mil"
                else:
                    part += " " + thousands[power]
            result = part + (" " + result if result else "")
        
        number //= 1000
        power += 1
    
    return result


def test_number_to_words():
    """
    Función de prueba para verificar la conversión.
    """
    test_cases = [
        0, 1, 10, 15, 20, 25, 100, 101, 150, 200, 1000, 1001, 1500, 10000, 
        10500.02, 123456.78, 1000000, 1000001
    ]
    
    print("🧪 Probando conversión de números a palabras:")
    for number in test_cases:
        words = number_to_words(number)
        print(f"  {number:>10} → {words}")


if __name__ == "__main__":
    test_number_to_words()
