"""
Template tags personalizados para core
"""
from __future__ import annotations

from typing import Union

from django import template

register = template.Library()


def _entero_miles_es_ar(n: int) -> str:
    """Agrupa dígitos de tres en tres con punto (convención es-AR para miles)."""
    neg = n < 0
    s = str(abs(int(n)))
    bloques: list[str] = []
    while len(s) > 3:
        bloques.append(s[-3:])
        s = s[:-3]
    if s:
        bloques.append(s)
    cuerpo = ".".join(reversed(bloques)) if bloques else "0"
    return f"-{cuerpo}" if neg else cuerpo


@register.filter
def formato_entero_miles(value: Union[int, float, str, None]) -> str:
    """
    Entero con separador de miles en convención es-AR (punto), sin símbolo de moneda.
    Ej.: ``2.833.102``.
    """
    if value is None or value == "":
        return "—"
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return "—"
    return _entero_miles_es_ar(n)


@register.filter
def formato_ars_entero(value: Union[int, float, str, None]) -> str:
    """
    Moneda ARS en entero para pantalla (es-AR): ``$ 2.833.102``.
    Evita el agrupamiento con espacio que puede dar ``intcomma`` según locale del proceso.
    """
    if value is None or value == "":
        return "—"
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        return "—"
    prefijo = "-$ " if n < 0 else "$ "
    return prefijo + _entero_miles_es_ar(abs(n))


@register.filter
def dict_get(dictionary, key):
    """
    Obtiene un valor de un diccionario usando una clave dinámica
    Uso: {{ permisos|dict_get:'campo' }}
    """
    if dictionary and isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''

