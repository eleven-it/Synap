"""
Selector de templates por dispositivo.

Usa request.is_mobile (inyectado por DeviceDetectionMiddleware) para elegir
entre la versión desktop y mobile de un template.

Convención de rutas:
  - Desktop: <app>/templates/<app>/<nombre>.html  (ruta original)
  - Mobile:  <app>/templates/<app>/mobile/<nombre>.html

Si el template mobile no existe, se devuelve el desktop como fallback.
"""
import logging
from django.template.loader import get_template
from django.template import TemplateDoesNotExist

logger = logging.getLogger(__name__)


def get_template_for_device(request, template_name: str) -> str:
    """
    Devuelve la ruta del template correcto según el dispositivo.

    Args:
        request: HttpRequest con atributo is_mobile (inyectado por middleware).
        template_name: Ruta del template desktop, ej. 'self_checkout/kiosco.html'.

    Returns:
        Ruta del template mobile si existe y el dispositivo es mobile;
        caso contrario devuelve el template original.
    """
    is_mobile = getattr(request, 'is_mobile', False)

    if not is_mobile:
        return template_name

    parts = template_name.rsplit('/', 1)
    if len(parts) == 2:
        mobile_template = f"{parts[0]}/mobile/{parts[1]}"
    else:
        mobile_template = f"mobile/{template_name}"

    try:
        get_template(mobile_template)
        logger.debug("Usando template mobile: %s", mobile_template)
        return mobile_template
    except TemplateDoesNotExist:
        logger.debug(
            "Template mobile no encontrado (%s), usando desktop: %s",
            mobile_template, template_name,
        )
        return template_name
