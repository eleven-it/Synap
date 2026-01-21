"""
Vistas para servir archivos media cuando el servidor web no está configurado
"""
from django.http import FileResponse, Http404
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)

def serve_media_file(request, path):
    """
    Sirve un archivo desde MEDIA_ROOT
    Útil cuando el servidor web (nginx/apache) no está configurado para servir /media/
    """
    # Construir la ruta completa del archivo
    file_path = os.path.join(settings.MEDIA_ROOT, path)
    
    # Normalizar la ruta para prevenir directory traversal
    file_path = os.path.normpath(file_path)
    media_root = os.path.normpath(settings.MEDIA_ROOT)
    
    # Verificar que el archivo esté dentro de MEDIA_ROOT
    if not file_path.startswith(media_root):
        logger.warning(f"Intento de acceso fuera de MEDIA_ROOT: {path}")
        raise Http404("File not found")
    
    # Verificar que el archivo exista
    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        logger.warning(f"Archivo no encontrado: {file_path}")
        raise Http404("File not found")
    
    # Verificar permisos de lectura
    if not os.access(file_path, os.R_OK):
        logger.warning(f"Sin permisos de lectura: {file_path}")
        raise Http404("File not found")
    
    # Determinar el tipo de contenido
    content_type = 'application/octet-stream'
    if file_path.lower().endswith('.png'):
        content_type = 'image/png'
    elif file_path.lower().endswith('.jpg') or file_path.lower().endswith('.jpeg'):
        content_type = 'image/jpeg'
    elif file_path.lower().endswith('.svg'):
        content_type = 'image/svg+xml'
    elif file_path.lower().endswith('.gif'):
        content_type = 'image/gif'
    
    try:
        # Servir el archivo
        response = FileResponse(open(file_path, 'rb'), content_type=content_type)
        response['Content-Disposition'] = f'inline; filename="{os.path.basename(file_path)}"'
        return response
    except Exception as e:
        logger.error(f"Error al servir archivo {file_path}: {e}")
        raise Http404("File not found")

