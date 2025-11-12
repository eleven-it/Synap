"""
Endpoints de Webhooks para acceso externo
"""
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json
from reports_ai.services.crew_service import CrewService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_report(request):
    """
    POST /reports_ai/webhook/report
    
    Solicita generación de reporte
    
    Body (JSON):
    {
      "intent": "reporte_ventas",
      "periodo": {"desde": "2025-09-01", "hasta": "2025-09-30"},
      "filtros": {"sucursal": ["CABA", "Mendoza"], "linea_producto": ["Electrónica"]},
      "detalle": "resumen|detallado",
      "segmentacion": ["sucursal", "linea_producto"]
    }
    """
    try:
        # Parsear payload
        payload = json.loads(request.body)
        
        # Extraer intención
        intent = payload.get('intent', '')
        if not intent:
            return JsonResponse({
                'error': 'Campo "intent" requerido'
            }, status=400)
        
        # Inicializar servicio
        crew_service = CrewService()
        
        # Construir query desde el payload
        query = _build_query_from_payload(payload)
        
        # Generar reporte
        result = crew_service.generate_report(
            query=query,
            source='webhook'
        )
        
        if not result['success']:
            return JsonResponse({
                'error': result.get('error', 'Error desconocido')
            }, status=500)
        
        # Formatear respuesta según especificación
        response = {
            'resumen': result['report'].get('resumen', []),
            'metricas': result['report'].get('metricas', {}),
            'desglose': result['report'].get('desglose', []),
            'periodo_cubierto': result['report'].get('periodo_cubierto', ''),
            'notas': result['report'].get('notas', [])
        }
        
        return JsonResponse(response)
        
    except json.JSONDecodeError:
        return JsonResponse({'error': 'JSON inválido'}, status=400)
    except Exception as e:
        logger.error(f"Error en webhook_report: {e}")
        return JsonResponse({'error': 'Error interno del servidor'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_validate(request):
    """
    POST /reports_ai/webhook/validate
    
    Valida intención y filtros sin ejecutar consultas
    """
    try:
        payload = json.loads(request.body)
        
        # Validar estructura básica
        if 'intent' not in payload:
            return JsonResponse({
                'valid': False,
                'message': 'Campo "intent" requerido'
            })
        
        # Por ahora, validación simple
        return JsonResponse({
            'valid': True,
            'message': 'Payload válido',
            'intent': payload.get('intent'),
            'periodo': payload.get('periodo', {}),
            'filtros': payload.get('filtros', {})
        })
        
    except json.JSONDecodeError:
        return JsonResponse({'valid': False, 'message': 'JSON inválido'}, status=400)
    except Exception as e:
        logger.error(f"Error en webhook_validate: {e}")
        return JsonResponse({'valid': False, 'message': str(e)}, status=500)


@require_http_methods(["GET"])
def webhook_health(request):
    """
    GET /reports_ai/webhook/health
    
    Verifica estado del sistema
    """
    try:
        # Verificar conexión a MySQL
        from reports_ai.tools.mysql_tool import MySQLTool
        mysql = MySQLTool()
        mysql_ok = mysql.test_connection()
        
        return JsonResponse({
            'estado': 'operativo' if mysql_ok else 'degradado',
            'ambito': 'Administranet Gestión',
            'mysql_connection': 'ok' if mysql_ok else 'error',
            'ult_actualizacion_reglas': '2025-10-24'  # Hardcoded, se puede mejorar
        })
        
    except Exception as e:
        logger.error(f"Error en webhook_health: {e}")
        return JsonResponse({
            'estado': 'error',
            'mensaje': str(e)
        }, status=500)


def _build_query_from_payload(payload: dict) -> str:
    """
    Construye una consulta en lenguaje natural desde el payload
    
    Args:
        payload: Datos del webhook
        
    Returns:
        Query en lenguaje natural
    """
    intent = payload.get('intent', 'consulta general')
    periodo = payload.get('periodo', {})
    filtros = payload.get('filtros', {})
    
    # Construir query básica
    query_parts = [intent]
    
    # Agregar periodo
    if periodo:
        desde = periodo.get('desde', '')
        hasta = periodo.get('hasta', '')
        if desde and hasta:
            query_parts.append(f"del {desde} al {hasta}")
    
    # Agregar filtros
    for key, value in filtros.items():
        if isinstance(value, list):
            query_parts.append(f"{key}: {', '.join(value)}")
        else:
            query_parts.append(f"{key}: {value}")
    
    return ' '.join(query_parts)

