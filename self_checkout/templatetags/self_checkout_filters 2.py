"""
Filtros de template para el módulo self_checkout.
Formato de moneda: separador de miles (.) y decimales (,) para Argentina.
"""
from django import template

register = template.Library()


@register.filter
def formato_moneda(value):
    """
    Formatea un número como moneda con separador de miles (punto)
    y decimales (coma), ej: 330545.45 -> "330.545,45"
    """
    if value is None:
        return "0,00"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return str(value)
    s = f"{n:.2f}"
    if "." in s:
        parte_entera, parte_decimal = s.split(".")
        if parte_entera.startswith("-"):
            signo = "-"
            parte_entera = parte_entera[1:]
        else:
            signo = ""
        if len(parte_entera) > 3:
            partes = []
            while parte_entera:
                partes.append(parte_entera[-3:])
                parte_entera = parte_entera[:-3]
            parte_entera = ".".join(reversed(partes))
        return signo + parte_entera + "," + parte_decimal
    return s
