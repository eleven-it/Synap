"""
Filtros de plantilla para el módulo MPR.
Formato de fecha unificado en la UI: dd-MM-yyyy.
"""
import unicodedata
from datetime import date, datetime

from django import template

from core.utils.administranet_types import str_codigo_manual_articulo

register = template.Library()

# Cantidad de colores de la paleta de reserva (fallback por id de turno).
_TURNO_COLOR_PALETA_N = 4


def _normalizar_nombre_turno(texto):
    """Minúsculas sin acentos, para heurística por nombre de turno."""
    s = str(texto or "").strip().lower()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


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
def turno_color(asig):
    """
    Devuelve un slug de color para diferenciar visualmente los turnos en la
    grilla de roster. El slug se usa como sufijo de clase CSS scoped
    (`.mpr-turno-badge--<slug>`) definida en la plantilla.

    Heurística:
    - Por nombre: mañana → "manana", tarde → "tarde", noche/nocturno → "noche".
    - Fallback: rota una paleta fija (`p0`..`p{N-1}`) por id del turno.

    Acepta un dict de asignación ({"id_turno", "nombre_turno"}) o una cadena.
    Uso: {{ asig|turno_color }}
    """
    nombre = ""
    id_turno = 0
    if isinstance(asig, dict):
        nombre = asig.get("nombre_turno") or asig.get("nombre") or ""
        try:
            id_turno = int(asig.get("id_turno") or asig.get("id") or 0)
        except (ValueError, TypeError):
            id_turno = 0
    else:
        nombre = asig
    n = _normalizar_nombre_turno(nombre)
    if "manana" in n:
        return "manana"
    if "tarde" in n:
        return "tarde"
    if "noche" in n or "nocturno" in n:
        return "noche"
    return "p%d" % (id_turno % _TURNO_COLOR_PALETA_N)


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


@register.filter
def roster_ids_turno(asigs):
    """
    Lista de id_turno de una celda multi-turno del roster.
    Uso: {% with ids=asigs|roster_ids_turno %}{% if t.id not in ids %}...
    """
    if not asigs:
        return []
    out = []
    for item in asigs:
        if not isinstance(item, dict):
            continue
        tid = item.get("id_turno")
        if tid is None:
            continue
        try:
            out.append(int(tid))
        except (ValueError, TypeError):
            continue
    return out
