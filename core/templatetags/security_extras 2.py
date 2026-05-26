"""
Filtros para reducir XSS en fragmentos HTML/SVG mostrados con |safe histórico.
"""
import bleach
from django import template
from django.utils.safestring import mark_safe

register = template.Library()

# SVG de iconos de menú (theme / módulos)
_SVG_TAGS = frozenset({
    'svg', 'path', 'circle', 'rect', 'g', 'line', 'polyline', 'polygon',
    'defs', 'lineargradient', 'radialgradient', 'stop', 'use', 'title', 'desc',
})
_SVG_ATTRS = {
    '*': [
        'class', 'id', 'fill', 'stroke', 'viewbox', 'xmlns', 'width', 'height',
        'stroke-width', 'stroke-linecap', 'stroke-linejoin', 'd', 'cx', 'cy', 'r',
        'x', 'y', 'x1', 'y1', 'x2', 'y2', 'points', 'transform', 'opacity',
        'stroke-miterlimit', 'fill-rule', 'clip-rule', 'gradientunits', 'offset',
        'stop-color', 'stop-opacity',
    ],
}

# Slots de subheader: HTML de UI sin scripts ni handlers
_UI_TAGS = frozenset({
    'div', 'span', 'p', 'br', 'label', 'input', 'select', 'option', 'button',
    'form', 'a', 'i', 'strong', 'em', 'small', 'ul', 'ol', 'li', 'h1', 'h2', 'h3',
    'h4', 'h5', 'h6', 'svg', 'path', 'circle', 'rect', 'g', 'line',
})
_UI_ATTRS = {
    '*': [
        'class', 'id', 'type', 'name', 'value', 'placeholder', 'checked', 'disabled', 'readonly',
        'href', 'role', 'aria-label', 'title', 'for', 'multiple', 'selected', 'style',
    ],
    'svg': _SVG_ATTRS['*'],
    'path': _SVG_ATTRS['*'],
    'circle': _SVG_ATTRS['*'],
    'rect': _SVG_ATTRS['*'],
    'g': _SVG_ATTRS['*'],
    'line': _SVG_ATTRS['*'],
    'a': ['class', 'id', 'href', 'title'],
    'input': ['class', 'id', 'type', 'name', 'value', 'placeholder', 'checked', 'disabled', 'readonly'],
    'select': ['class', 'id', 'name', 'multiple', 'disabled'],
    'option': ['class', 'value', 'selected'],
    'button': ['class', 'id', 'type', 'name', 'value', 'disabled'],
    'form': ['class', 'id', 'action', 'method'],
}


@register.filter(is_safe=True)
def safe_svg_icon(value):
    """Sanitiza SVG de iconos de aplicación/menú antes de renderizar."""
    if value is None or value == '':
        return ''
    cleaned = bleach.clean(
        str(value),
        tags=_SVG_TAGS,
        attributes=_SVG_ATTRS,
        strip=True,
    )
    return mark_safe(cleaned)


@register.filter(is_safe=True)
def safe_ui_slot(value):
    """Sanitiza HTML de slots de interfaz (filtros, chips); elimina script/on*."""
    if value is None or value == '':
        return ''
    cleaned = bleach.clean(
        str(value),
        tags=_UI_TAGS,
        attributes=_UI_ATTRS,
        strip=True,
    )
    return mark_safe(cleaned)
