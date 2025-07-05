from django import template
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

register = template.Library()

@register.simple_tag(takes_context=True)
def device_template(context, base_template_name, mobile_suffix='_mobile'):
    """
    Template tag para servir templates diferentes según el dispositivo.
    
    Uso:
    {% device_template 'login/login' %}
    {% device_template 'login/register' '_mobile' %}
    
    Si el dispositivo es móvil, buscará 'login/login_mobile.html'
    Si es desktop, buscará 'login/login.html'
    """
    request = context.get('request')
    
    if not request:
        return base_template_name
    
    # Si es móvil, agregar el sufijo
    if hasattr(request, 'is_mobile') and request.is_mobile:
        mobile_template = f"{base_template_name}{mobile_suffix}"
        try:
            # Verificar si existe el template móvil
            get_template(mobile_template)
            return mobile_template
        except TemplateDoesNotExist:
            # Si no existe, usar el template base
            return base_template_name
    
    return base_template_name

@register.simple_tag(takes_context=True)
def is_mobile(context):
    """
    Template tag para verificar si el dispositivo es móvil.
    
    Uso:
    {% is_mobile as mobile %}
    {% if mobile %}
        <!-- Contenido para móvil -->
    {% else %}
        <!-- Contenido para desktop -->
    {% endif %}
    """
    request = context.get('request')
    if request and hasattr(request, 'is_mobile'):
        return request.is_mobile
    return False

@register.simple_tag(takes_context=True)
def device_type(context):
    """
    Template tag para obtener el tipo de dispositivo.
    
    Uso:
    {% device_type as device %}
    {% if device == 'iphone' %}
        <!-- Contenido específico para iPhone -->
    {% endif %}
    """
    request = context.get('request')
    if request and hasattr(request, 'device_type'):
        return request.device_type
    return 'desktop'

@register.filter
def get_item(dictionary, key):
    """Permite acceder a un valor de un diccionario por clave en los templates."""
    try:
        return dictionary.get(key)
    except Exception:
        return None 