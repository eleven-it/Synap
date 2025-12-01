"""
Template tags personalizados para core
"""
from django import template

register = template.Library()


@register.filter
def dict_get(dictionary, key):
    """
    Obtiene un valor de un diccionario usando una clave dinámica
    Uso: {{ permisos|dict_get:'campo' }}
    """
    if dictionary and isinstance(dictionary, dict):
        return dictionary.get(key, '')
    return ''

