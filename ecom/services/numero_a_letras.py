"""Conversión de importe numérico a letras (pesos argentinos)."""

from __future__ import annotations


def numero_a_letras(numero: float) -> str:
    """Convierte un número a letras en español (formato pesos argentinos)."""
    try:
        entero = int(numero)
        centavos = int(round((numero - entero) * 100))

        unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
        decenas = [
            "",
            "DIEZ",
            "VEINTE",
            "TREINTA",
            "CUARENTA",
            "CINCUENTA",
            "SESENTA",
            "SETENTA",
            "OCHENTA",
            "NOVENTA",
        ]
        especiales = {
            11: "ONCE",
            12: "DOCE",
            13: "TRECE",
            14: "CATORCE",
            15: "QUINCE",
            16: "DIECISEIS",
            17: "DIECISIETE",
            18: "DIECIOCHO",
            19: "DIECINUEVE",
            21: "VEINTIUNO",
            22: "VEINTIDOS",
            23: "VEINTITRES",
            24: "VEINTICUATRO",
            25: "VEINTICINCO",
            26: "VEINTISEIS",
            27: "VEINTISIETE",
            28: "VEINTIOCHO",
            29: "VEINTINUEVE",
        }
        centenas = [
            "",
            "CIENTO",
            "DOSCIENTOS",
            "TRESCIENTOS",
            "CUATROCIENTOS",
            "QUINIENTOS",
            "SEISCIENTOS",
            "SETECIENTOS",
            "OCHOCIENTOS",
            "NOVECIENTOS",
        ]

        def convertir_grupo(n: int) -> str:
            if n == 0:
                return ""
            if n == 100:
                return "CIEN"
            if n in especiales:
                return especiales[n]

            resultado = ""
            if n >= 100:
                resultado += centenas[n // 100] + " "
                n %= 100
            if n in especiales:
                resultado += especiales[n]
            elif n >= 10:
                resultado += decenas[n // 10]
                if n % 10:
                    resultado += " Y " + unidades[n % 10]
            else:
                resultado += unidades[n]
            return resultado.strip()

        if entero == 0:
            letras = "CERO"
        elif entero < 1000:
            letras = convertir_grupo(entero)
        elif entero < 1000000:
            miles = entero // 1000
            resto = entero % 1000
            if miles == 1:
                letras = "MIL"
            else:
                letras = convertir_grupo(miles) + " MIL"
            if resto:
                letras += " " + convertir_grupo(resto)
        else:
            millones = entero // 1000000
            resto = entero % 1000000
            if millones == 1:
                letras = "UN MILLON"
            else:
                letras = convertir_grupo(millones) + " MILLONES"
            if resto:
                miles = resto // 1000
                unids = resto % 1000
                if miles:
                    if miles == 1:
                        letras += " MIL"
                    else:
                        letras += " " + convertir_grupo(miles) + " MIL"
                if unids:
                    letras += " " + convertir_grupo(unids)

        if centavos:
            return f"PESOS {letras} CON {centavos:02d}/100"
        return f"PESOS {letras}"
    except Exception:
        return ""
