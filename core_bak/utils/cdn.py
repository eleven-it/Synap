"""
Utilidades para configuración y validación de CDN
"""
import os
import requests
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)

def get_cdn_url(path):
    """
    Obtiene la URL completa del CDN para un archivo
    """
    if hasattr(settings, 'MEDIA_URL') and settings.MEDIA_URL.startswith('http'):
        return f"{settings.MEDIA_URL.rstrip('/')}/{path.lstrip('/')}"
    return None

def test_cdn_accessibility(image_url, timeout=5):
    """
    Prueba si una imagen es accesible desde el CDN
    """
    try:
        response = requests.head(image_url, timeout=timeout)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Error accediendo a imagen CDN: {image_url} - {str(e)}")
        return False

def get_cdn_status():
    """
    Obtiene el estado actual de la configuración del CDN
    """
    status = {
        'enabled': False,
        'provider': None,
        'domain': None,
        'media_url': settings.MEDIA_URL,
        'static_url': settings.STATIC_URL,
    }
    
    if hasattr(settings, 'USE_CLOUDFLARE_CDN') and settings.USE_CLOUDFLARE_CDN:
        status.update({
            'enabled': True,
            'provider': 'Cloudflare',
            'domain': getattr(settings, 'CLOUDFLARE_DOMAIN', 'N/A'),
        })
    elif hasattr(settings, 'USE_AWS_CDN') and settings.USE_AWS_CDN:
        status.update({
            'enabled': True,
            'provider': 'AWS CloudFront',
            'domain': getattr(settings, 'AWS_S3_CUSTOM_DOMAIN', 'N/A'),
        })
    elif hasattr(settings, 'USE_BUNNY_CDN') and settings.USE_BUNNY_CDN:
        status.update({
            'enabled': True,
            'provider': 'Bunny CDN',
            'domain': getattr(settings, 'BUNNY_CDN_DOMAIN', 'N/A'),
        })
    
    return status

def optimize_image_url(image_url, width=None, height=None, quality=None):
    """
    Optimiza una URL de imagen para el CDN (si soporta transformaciones)
    """
    if not image_url:
        return image_url
    
    # Cloudflare Image Resizing
    if hasattr(settings, 'USE_CLOUDFLARE_CDN') and settings.USE_CLOUDFLARE_CDN:
        params = []
        if width:
            params.append(f'w={width}')
        if height:
            params.append(f'h={height}')
        if quality:
            params.append(f'q={quality}')
        
        if params:
            separator = '&' if '?' in image_url else '?'
            return f"{image_url}{separator}{'&'.join(params)}"
    
    # Bunny CDN Image Optimization
    elif hasattr(settings, 'USE_BUNNY_CDN') and settings.USE_BUNNY_CDN:
        if width or height or quality:
            # Bunny CDN usa parámetros en la URL
            params = []
            if width:
                params.append(f'width={width}')
            if height:
                params.append(f'height={height}')
            if quality:
                params.append(f'quality={quality}')
            
            if params:
                separator = '&' if '?' in image_url else '?'
                return f"{image_url}{separator}{'&'.join(params)}"
    
    return image_url

def get_cdn_cache_headers(file_type='media'):
    """
    Obtiene los headers de cache apropiados para el tipo de archivo
    """
    if hasattr(settings, 'CDN_CACHE_HEADERS'):
        return settings.CDN_CACHE_HEADERS.get(file_type, {})
    return {}

def validate_cdn_configuration():
    """
    Valida la configuración actual del CDN
    """
    errors = []
    warnings = []
    
    status = get_cdn_status()
    
    if not status['enabled']:
        warnings.append("CDN no está habilitado")
        return errors, warnings
    
    # Verificar que las URLs usen HTTPS
    if not status['media_url'].startswith('https://'):
        errors.append("MEDIA_URL debe usar HTTPS para CDN")
    
    if not status['static_url'].startswith('https://'):
        errors.append("STATIC_URL debe usar HTTPS para CDN")
    
    # Verificar configuración específica del proveedor
    if status['provider'] == 'Cloudflare':
        if not hasattr(settings, 'CLOUDFLARE_DOMAIN'):
            errors.append("CLOUDFLARE_DOMAIN no está configurado")
    
    elif status['provider'] == 'AWS CloudFront':
        if not hasattr(settings, 'AWS_S3_CUSTOM_DOMAIN'):
            errors.append("AWS_S3_CUSTOM_DOMAIN no está configurado")
    
    elif status['provider'] == 'Bunny CDN':
        if not hasattr(settings, 'BUNNY_CDN_DOMAIN'):
            errors.append("BUNNY_CDN_DOMAIN no está configurado")
    
    return errors, warnings

def test_cdn_performance():
    """
    Prueba el rendimiento del CDN con una imagen de prueba
    """
    if not get_cdn_status()['enabled']:
        return None
    
    # Usar una imagen de prueba pequeña
    test_image = "products/test-image.jpg"
    cdn_url = get_cdn_url(test_image)
    
    if not cdn_url:
        return None
    
    try:
        import time
        start_time = time.time()
        response = requests.get(cdn_url, timeout=10)
        end_time = time.time()
        
        return {
            'url': cdn_url,
            'status_code': response.status_code,
            'response_time': round((end_time - start_time) * 1000, 2),  # ms
            'content_length': len(response.content),
            'headers': dict(response.headers),
        }
    except Exception as e:
        logger.error(f"Error probando rendimiento CDN: {str(e)}")
        return None 