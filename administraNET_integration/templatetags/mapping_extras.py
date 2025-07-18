from django import template

register = template.Library()

@register.filter
def get_preset(presets, mapping_type):
    """Devuelve el preset de mapeo para el tipo dado"""
    if not presets or not mapping_type:
        return {}
    return presets.get(mapping_type, {}) 