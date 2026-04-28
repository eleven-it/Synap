"""
Vistas para gestión de webhooks de Tiendanube.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
import json
import logging
from ..models import TiendanubeConfig, AdministraNETConfig, WebhookEvent, WebhookDeliveryLog
from ..services.webhook_service import WebhookService
from ..services.webhook_processor import WebhookProcessor
from ..services.sync_service import TiendanubeAdministraNETSyncService

logger = logging.getLogger(__name__)


@login_required
def webhook_status(request):
    """
    Vista para mostrar el estado de los webhooks configurados.
    """
    try:
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config:
            messages.error(request, 'No hay configuración activa de Tiendanube')
            return redirect('tiendanube_administranet:dashboard')
        
        # Inicializar servicio de webhooks
        webhook_service = WebhookService(tiendanube_config)
        
        # Obtener webhooks configurados
        webhooks_result = webhook_service.get_webhooks()
        
        # Obtener eventos recientes (WebhookEvent usa received_at)
        recent_events = WebhookEvent.objects.order_by('-received_at')[:10]
        
        # Obtener logs de entrega recientes (WebhookDeliveryLog usa received_at)
        recent_deliveries = WebhookDeliveryLog.objects.order_by('-received_at')[:10]
        
        # Estadísticas adicionales
        total_events = WebhookEvent.objects.count()
        total_deliveries = WebhookDeliveryLog.objects.count()
        
        # Eventos de hoy (usar received_at)
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        events_today = WebhookEvent.objects.filter(received_at__gte=today_start).count()
        
        # Calcular métricas reales
        success_rate = 0
        avg_response_time = 0
        
        if total_deliveries > 0:
            # Calcular tasa de éxito
            successful_deliveries = WebhookDeliveryLog.objects.filter(status='success').count()
            success_rate = round((successful_deliveries / total_deliveries) * 100, 1)
            
            # Calcular tiempo promedio de respuesta
            from django.db.models import Avg
            avg_response_time = WebhookDeliveryLog.objects.filter(
                request_duration__isnull=False
            ).aggregate(avg_time=Avg('request_duration'))['avg_time']
            if avg_response_time:
                avg_response_time = round(avg_response_time * 1000, 0)  # Convertir a ms
        
        # Verificar si hay webhooks configurados
        webhooks_configured = webhooks_result.get('success', False) and webhooks_result.get('count', 0) > 0
        
        # Obtener información de la tienda
        store_info = None
        try:
            from ..services.tiendanube_service import TiendanubeService
            tiendanube_service = TiendanubeService(tiendanube_config)
            store_response = tiendanube_service.get_store_info()
            if store_response.get('success'):
                store_data = store_response.get('store_info', {})
                # Procesar nombre multilenguaje
                name = store_data.get('name', {})
                if isinstance(name, dict):
                    # Obtener nombre en español o primer idioma disponible
                    store_name = name.get('es') or name.get('en') or list(name.values())[0] if name else 'N/A'
                else:
                    store_name = name or 'N/A'
                
                store_info = {
                    'name': store_name,
                    'url': store_data.get('url_with_protocol', 'N/A'),
                    'email': store_data.get('email', 'N/A'),
                    'main_currency': store_data.get('main_currency', 'N/A'),
                    'main_language': store_data.get('main_language', 'N/A'),
                    'original_domain': store_data.get('original_domain', 'N/A')
                }
        except Exception as e:
            logger.warning(f"No se pudo obtener información de la tienda: {e}")
        
        context = {
            'tiendanube_config': tiendanube_config,
            'adminet_config': adminet_config,
            'webhooks_result': webhooks_result,
            'webhooks_configured': webhooks_configured,
            'recent_events': recent_events,
            'recent_deliveries': recent_deliveries,
            'webhook_url': webhook_service._get_webhook_url(),
            'store_info': store_info,
            'statistics': {
                'total_events': total_events,
                'total_deliveries': total_deliveries,
                'events_today': events_today,
                'webhooks_count': webhooks_result.get('count', 0),
                'success_rate': success_rate,
                'avg_response_time': avg_response_time
            }
        }
        
        return render(request, 'tiendanube_administranet/webhooks/webhook_status.html', context)
        
    except Exception as e:
        logger.error(f"Error en webhook_status: {e}")
        messages.error(request, f'Error obteniendo estado de webhooks: {str(e)}')
        return redirect('tiendanube_administranet:dashboard')


@login_required
def configure_webhooks(request):
    """
    Vista para configurar webhooks automáticamente.
    """
    try:
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config:
            messages.error(request, 'No hay configuración activa de Tiendanube')
            return redirect('tiendanube_administranet:dashboard')
        
        # Inicializar servicio de webhooks
        webhook_service = WebhookService(tiendanube_config)
        
        # Configurar webhooks automáticamente
        result = webhook_service.ensure_webhooks_configured()
        
        if result['success']:
            created = result.get('created', [])
            skipped = result.get('skipped', [])
            
            if created:
                messages.success(request, f'Webhooks creados: {", ".join(created)}')
            if skipped:
                messages.info(request, f'Webhooks ya existían: {", ".join(skipped)}')
            
            messages.success(request, f'Configuración completada. URL: {result.get("webhook_url")}')
        else:
            messages.error(request, f'Error configurando webhooks: {result.get("message")}')
        
        return redirect('tiendanube_administranet:webhook_status')
        
    except Exception as e:
        logger.error(f"Error en configure_webhooks: {e}")
        messages.error(request, f'Error configurando webhooks: {str(e)}')
        return redirect('tiendanube_administranet:dashboard')


@csrf_exempt
@require_http_methods(["POST"])
def webhook_receiver(request):
    """
    Endpoint para recibir webhooks de Tiendanube.
    """
    try:
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config or not adminet_config:
            logger.error("No hay configuración activa de Tiendanube o AdministraNET")
            return HttpResponse("Configuration not found", status=500)
        
        # Procesar webhook
        processor = WebhookProcessor(tiendanube_config, adminet_config)
        result = processor.process_webhook(request)
        
        if result['success']:
            logger.info(f"Webhook procesado exitosamente: {result.get('action', 'unknown')}")
            return HttpResponse("OK", status=200)
        else:
            logger.error(f"Error procesando webhook: {result.get('error')}")
            return HttpResponse("Error processing webhook", status=500)
            
    except Exception as e:
        logger.error(f"Exception en webhook_receiver: {e}")
        return HttpResponse("Internal server error", status=500)


@login_required
def webhook_events(request):
    """
    Vista para mostrar eventos de webhooks recibidos.
    """
    try:
        # Obtener eventos con paginación
        events_list = WebhookEvent.objects.all().order_by('-created_at')
        paginator = Paginator(events_list, 25)
        page_number = request.GET.get('page')
        events = paginator.get_page(page_number)
        
        # Filtros
        event_type = request.GET.get('event_type')
        if event_type:
            events = events.filter(event_type=event_type)
        
        status = request.GET.get('status')
        if status:
            events = events.filter(status=status)
        
        context = {
            'events': events,
            'event_types': WebhookEvent.EVENT_TYPE_CHOICES,
            'status_choices': WebhookEvent.STATUS_CHOICES,
            'current_filters': {
                'event_type': event_type,
                'status': status
            }
        }
        
        return render(request, 'tiendanube_administranet/webhook_events.html', context)
        
    except Exception as e:
        logger.error(f"Error en webhook_events: {e}")
        messages.error(request, f'Error obteniendo eventos: {str(e)}')
        return redirect('tiendanube_administranet:dashboard')


@login_required
def webhook_delivery_logs(request):
    """
    Vista para mostrar logs de entrega de webhooks.
    """
    try:
        # Obtener logs con paginación
        logs_list = WebhookDeliveryLog.objects.all().order_by('-created_at')
        paginator = Paginator(logs_list, 25)
        page_number = request.GET.get('page')
        logs = paginator.get_page(page_number)
        
        # Filtros
        status = request.GET.get('status')
        if status:
            logs = logs.filter(status=status)
        
        context = {
            'logs': logs,
            'status_choices': WebhookDeliveryLog.STATUS_CHOICES,
            'current_filters': {
                'status': status
            }
        }
        
        return render(request, 'tiendanube_administranet/webhook_delivery_logs.html', context)
        
    except Exception as e:
        logger.error(f"Error en webhook_delivery_logs: {e}")
        messages.error(request, f'Error obteniendo logs: {str(e)}')
        return redirect('tiendanube_administranet:dashboard')
