"""
Filtros de plantilla para el módulo MPR.
Formato de fecha unificado en la UI: dd-MM-yyyy.
"""
from datetime import date, datetime

from django import template

from core.utils.administranet_types import str_codigo_manual_articulo

register = template.Library()


@register.filter
def codigo_mpr(value):
    """
    Código de artículo para UI MPR: articulo.id_manual (nunca CodigoArticuloT).
    Acepta dict con codigo_manual/id_manual o valor escalar.
    """
    if isinstance(value, dict):
        return str_codigo_manual_articulo(value.get("codigo_manual") or value.get("id_manual"))
    return str_codigo_manual_articulo(value)


@register.filter
def fecha_dd_mm_yyyy(value):
    """
    Formatea una fecha para la UI MPR como dd-MM-yyyy.
    Acepta date, datetime, string (yyyy-mm-dd) o None. None/vacío → "—".
    Uso: {{ mov.fecha|fecha_dd_mm_yyyy }}
    """
    if value is None or value == "":
        return "—"
    if isinstance(value, (date, datetime)):
        return value.strftime("%d-%m-%Y")
    if isinstance(value, str) and value.strip():
        s = value.strip()[:10]
        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
            return dt.strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            return "—"
    return "—"


@register.filter
def dict_get(d, key):
    """
    Accede a un dict con clave dinámica en templates.
    Uso: {{ asignaciones|dict_get:operario.id }}
    """
    if d is None:
        return None
    return d.get(key)


@register.filter
def isoformat(value):
    """
    Devuelve la representación ISO (YYYY-MM-DD) de un objeto date/datetime.
    Uso: {{ fecha_lunes|isoformat }}
    """
    if value is None:
        return ""
    if isinstance(value, (date, datetime)):
        return value.strftime("%Y-%m-%d")
    return str(value)
