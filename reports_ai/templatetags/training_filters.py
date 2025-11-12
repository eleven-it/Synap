"""
Template tags para vistas de entrenamiento y business rules
"""
from django import template

register = template.Library()


@register.filter
def lookup(dictionary, key):
    """
    Permite acceder a diccionarios en templates
    Uso: {{ dict|lookup:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def split(value, delimiter=','):
    """
    Divide una cadena por un delimitador
    Uso: {{ string|split:"," }}
    """
    if not value:
        return []
    return value.split(delimiter)

