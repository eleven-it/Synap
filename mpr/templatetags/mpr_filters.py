"""
Filtros de plantilla para el módulo MPR.
Formato de fecha unificado en la UI: dd-MM-yyyy.
"""
from datetime import date, datetime

from django import template

register = template.Library()


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
