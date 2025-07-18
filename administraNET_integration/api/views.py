from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext as _
import json
import logging
from django.apps import apps
from django.db import connection
from django.core.exceptions import ValidationError

from ..models import AdministraNETConfig, TableMapping
from ..services.connection_service import AdministraNETConnectionService

logger = logging.getLogger(__name__)

@login_required
@require_http_methods(["GET"])
def get_adminet_table_fields(request):
    """
    Obtener campos de una tabla específica de administraNET
    """
    try:
        table_name = request.GET.get('table')
        if not table_name:
            return JsonResponse({
                'success': False,
                'error': _('Table name is required')
            }, status=400)
        
        # Obtener configuración activa
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({
                'success': False,
                'error': _('No active AdministraNET configuration found')
            }, status=400)
        
        # Conectar a administraNET y obtener campos
        connection_service = AdministraNETConnectionService(config)
        fields = connection_service.get_table_fields(table_name)
        
        return JsonResponse({
            'success': True,
            'fields': fields,
            'table': table_name
        })
        
    except Exception as e:
        logger.error(f"Error getting AdministraNET table fields: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_synap_model_fields(request):
    """
    Obtener campos de un modelo específico de Synap usando introspection
    """
    try:
        model_path = request.GET.get('model')
        if not model_path:
            return JsonResponse({
                'success': False,
                'error': _('Model path is required')
            }, status=400)
        
        # Parsear app.model
        try:
            app_label, model_name = model_path.split('.')
        except ValueError:
            return JsonResponse({
                'success': False,
                'error': _('Invalid model path format. Use: app.model')
            }, status=400)
        
        # Obtener modelo usando introspection
        try:
            model = apps.get_model(app_label, model_name)
        except LookupError:
            return JsonResponse({
                'success': False,
                'error': _('Model not found: %(model)s') % {'model': model_path}
            }, status=400)
        
        # Obtener campos del modelo
        fields = []
        for field in model._meta.get_fields():
            # Filtrar solo campos editables y relevantes
            if hasattr(field, 'name') and not field.name.startswith('_'):
                field_info = {
                    'name': field.name,
                    'type': field.get_internal_type() if hasattr(field, 'get_internal_type') else 'Unknown',
                    'verbose_name': getattr(field, 'verbose_name', field.name),
                    'help_text': getattr(field, 'help_text', ''),
                    'null': getattr(field, 'null', False),
                    'blank': getattr(field, 'blank', False),
                }
                fields.append(field_info)
        
        # Ordenar por nombre
        fields.sort(key=lambda x: x['name'])
        
        return JsonResponse({
            'success': True,
            'fields': fields,
            'model': model_path
        })
        
    except Exception as e:
        logger.error(f"Error getting Synap model fields: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_preset_mapping(request):
    """
    Obtener mapeo predefinido por tipo
    """
    try:
        mapping_type = request.GET.get('type')
        if not mapping_type:
            return JsonResponse({
                'success': False,
                'error': _('Mapping type is required')
            }, status=400)
        
        # Obtener preset del modelo
        presets = TableMapping.get_preset_mappings()
        if mapping_type not in presets:
            return JsonResponse({
                'success': False,
                'error': _('Invalid mapping type: %(type)s') % {'type': mapping_type}
            }, status=400)
        
        preset = presets[mapping_type]
        
        return JsonResponse({
            'success': True,
            'preset': preset,
            'type': mapping_type
        })
        
    except Exception as e:
        logger.error(f"Error getting preset mapping: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@login_required
@require_http_methods(["GET"])
def get_available_mapping_types(request):
    """
    Obtener tipos de mapeo disponibles
    """
    try:
        presets = TableMapping.get_preset_mappings()
        types = []
        
        for mapping_type, preset in presets.items():
            types.append({
                'value': mapping_type,
                'label': dict(TableMapping.MAPPING_TYPES)[mapping_type],
                'table': preset['table'],
                'model': preset['model'],
                'field_count': len(preset['fields'])
            })
        
        return JsonResponse({
            'success': True,
            'types': types
        })
        
    except Exception as e:
        logger.error(f"Error getting mapping types: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500) 