"""
Vistas PWA: sirven sw.js y manifest.json desde la raíz del dominio.

El navegador exige que el Service Worker se sirva desde el mismo scope
que controla, por eso /sw.js debe estar en la raíz (no en /static/sw.js).
"""
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse, Http404


def _resolve_static_file(filename):
    """Busca un archivo estático: primero en STATIC_ROOT, luego en STATICFILES_DIRS."""
    if settings.STATIC_ROOT:
        path = Path(settings.STATIC_ROOT) / filename
        if path.is_file():
            return path

    for static_dir in settings.STATICFILES_DIRS:
        path = Path(static_dir) / filename
        if path.is_file():
            return path

    return None


def serve_sw(request):
    """Sirve /sw.js con Cache-Control: no-cache para que el navegador siempre verifique."""
    path = _resolve_static_file('sw.js')
    if path is None:
        raise Http404('sw.js no encontrado')

    content = path.read_text(encoding='utf-8')
    response = HttpResponse(content, content_type='application/javascript')
    response['Cache-Control'] = 'no-cache'
    return response


def serve_manifest(request):
    """Sirve /manifest.json con cache de 24h."""
    path = _resolve_static_file('manifest.json')
    if path is None:
        raise Http404('manifest.json no encontrado')

    content = path.read_text(encoding='utf-8')
    response = HttpResponse(content, content_type='application/manifest+json')
    response['Cache-Control'] = 'public, max-age=86400'
    return response
