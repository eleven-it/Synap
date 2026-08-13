"""
Vistas webhook config views — tiendanube_administranet.
"""

import logging
import requests
import uuid
import json
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import models
from django.db.models import Q, Count
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, RedirectView, View
from django.views.generic.edit import FormView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import gettext as _, gettext_lazy as _
from django.core.paginator import Paginator

from ..models import (
    TiendanubeConfig, AdministraNETConfig, CustomerMapping,
    SyncLog, ProductMapping, ProductVariantMapping, ProductCategoryMapping,
    OrderMapping, WebhookConfig, WebhookEvent, WebhookDeliveryLog
)
from ..services.sync_service import TiendanubeAdministraNETSyncService
from ..forms import (
    TiendanubeConfigForm, AdministraNETConfigForm,
    CustomerMappingForm, CustomerMappingFilterForm,
    ProductMappingForm, ProductVariantMappingForm, ProductCategoryMappingForm,
    OrderMappingForm, WebhookConfigForm, WebhookEventFilterForm
)
from ..mixins import TiendanubeAdministranetLoginMixin
from ..mysql import resolve_mysql_base_empresa
from ..services.tiendanube_service import NUVEMSHOP_API_VERSION
from ..utils.feature_flags import tiendanube_webhooks_disabled_reason

DEFAULT_TIENDANUBE_API_URL = f'https://api.tiendanube.com/{NUVEMSHOP_API_VERSION}'

logger = logging.getLogger(__name__)


class WebhookConfigListView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar configuraciones de webhooks.
    """
    permission_required = 'tiendanube_administranet.view_webhookconfig'
    model = WebhookConfig
    template_name = 'tiendanube_administranet/webhook_config_list.html'
    context_object_name = 'webhook_configs'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = WebhookConfig.objects.select_related('tiendanube_config').all()
        
        # Aplicar filtros
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        is_active = self.request.GET.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == 'true')
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = WebhookEventFilterForm(self.request.GET)
        
        # Estadísticas
        context['statistics'] = {
            'total_webhooks': WebhookConfig.objects.count(),
            'active_webhooks': WebhookConfig.objects.filter(is_active=True).count(),
            'total_events': WebhookEvent.objects.count(),
            'pending_events': WebhookEvent.objects.filter(status='pending').count(),
            'failed_events': WebhookEvent.objects.filter(status='failed').count(),
        }
        
        return context


class WebhookConfigCreateView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, CreateView):
    """
    Vista para crear nueva configuración de webhook.
    """
    permission_required = 'tiendanube_administranet.add_webhookconfig'
    model = WebhookConfig
    form_class = WebhookConfigForm
    template_name = 'tiendanube_administranet/webhook_config_form.html'
    success_url = reverse_lazy('tiendanube_administranet:webhook_config_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Crear webhook en Tiendanube
        if form.instance.is_active:
            from ..services.webhook_service import WebhookService
            webhook_service = WebhookService(form.instance.tiendanube_config)
            
            webhook_data = {
                'webhook_url': form.instance.webhook_url,
                'events': form.instance.events,
                'description': form.instance.description or 'Synap Webhook'
            }
            
            result = webhook_service.create_webhook(webhook_data)
            
            if result['success']:
                form.instance.webhook_id = result['webhook_id']
                form.instance.save()
                messages.success(self.request, _('Webhook configuration created successfully and registered in Tiendanube.'))
            else:
                form.instance.status = WebhookConfig.WebhookStatus.ERROR
                form.instance.save()
                messages.warning(self.request, f"Webhook created locally but failed to register in Tiendanube: {result.get('error', 'Unknown error')}")
        else:
            messages.success(self.request, _('Webhook configuration created successfully (inactive).'))
        
        return response


class WebhookConfigUpdateView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para actualizar configuración de webhook.
    """
    permission_required = 'tiendanube_administranet.change_webhookconfig'
    model = WebhookConfig
    form_class = WebhookConfigForm
    template_name = 'tiendanube_administranet/webhook_config_form.html'
    success_url = reverse_lazy('tiendanube_administranet:webhook_config_list')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Actualizar webhook en Tiendanube si tiene ID
        if form.instance.webhook_id and form.instance.is_active:
            from ..services.webhook_service import WebhookService
            webhook_service = WebhookService(form.instance.tiendanube_config)
            
            webhook_data = {
                'webhook_url': form.instance.webhook_url,
                'events': form.instance.events,
                'description': form.instance.description or 'Synap Webhook'
            }
            
            result = webhook_service.update_webhook(form.instance.webhook_id, webhook_data)
            
            if result['success']:
                messages.success(self.request, _('Webhook configuration updated successfully in Tiendanube.'))
            else:
                form.instance.status = WebhookConfig.WebhookStatus.ERROR
                form.instance.save()
                messages.warning(self.request, f"Webhook updated locally but failed to update in Tiendanube: {result.get('error', 'Unknown error')}")
        else:
            messages.success(self.request, _('Webhook configuration updated successfully.'))
        
        return response


class WebhookConfigDeleteView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DeleteView):
    """
    Vista para eliminar configuración de webhook.
    """
    permission_required = 'tiendanube_administranet.delete_webhookconfig'
    model = WebhookConfig
    template_name = 'tiendanube_administranet/webhook_config_confirm_delete.html'
    success_url = reverse_lazy('tiendanube_administranet:webhook_config_list')
    
    def delete(self, request, *args, **kwargs):
        webhook_config = self.get_object()
        
        # Eliminar webhook de Tiendanube si tiene ID
        if webhook_config.webhook_id:
            from ..services.webhook_service import WebhookService
            webhook_service = WebhookService(webhook_config.tiendanube_config)
            result = webhook_service.delete_webhook(webhook_config.webhook_id)
            
            if not result['success']:
                messages.warning(self.request, f"Webhook deleted locally but failed to delete from Tiendanube: {result.get('error', 'Unknown error')}")
        
        messages.success(self.request, _('Webhook configuration deleted successfully.'))
        return super().delete(request, *args, **kwargs)


class WebhookConfigDetailView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DetailView):
    """
    Vista para mostrar detalles de configuración de webhook.
    """
    permission_required = 'tiendanube_administranet.view_webhookconfig'
    model = WebhookConfig
    template_name = 'tiendanube_administranet/webhook_config_detail.html'
    context_object_name = 'webhook_config'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Eventos recientes del webhook
        context['recent_events'] = self.object.webhook_events.order_by('-received_at')[:10]
        
        # Estadísticas del webhook
        context['webhook_stats'] = {
            'total_events': self.object.webhook_events.count(),
            'completed_events': self.object.webhook_events.filter(status='completed').count(),
            'failed_events': self.object.webhook_events.filter(status='failed').count(),
            'pending_events': self.object.webhook_events.filter(status='pending').count(),
            'retry_events': self.object.webhook_events.filter(status='retry').count(),
        }
        
        return context


class WebhookEventListView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar eventos de webhook.
    """
    permission_required = 'tiendanube_administranet.view_webhookevent'
    model = WebhookEvent
    template_name = 'tiendanube_administranet/webhook_event_list.html'
    context_object_name = 'webhook_events'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = WebhookEvent.objects.select_related('webhook_config', 'webhook_config__tiendanube_config').all()
        
        # Aplicar filtros
        filter_form = WebhookEventFilterForm(self.request.GET)
        if filter_form.is_valid():
            if filter_form.cleaned_data.get('status'):
                queryset = queryset.filter(status=filter_form.cleaned_data['status'])
            
            if filter_form.cleaned_data.get('event_type'):
                event_type = filter_form.cleaned_data['event_type']
                queryset = queryset.filter(event_type__startswith=f'{event_type}/')
            
            if filter_form.cleaned_data.get('resource_id'):
                queryset = queryset.filter(resource_id=filter_form.cleaned_data['resource_id'])
            
            if filter_form.cleaned_data.get('date_from'):
                queryset = queryset.filter(received_at__date__gte=filter_form.cleaned_data['date_from'])
            
            if filter_form.cleaned_data.get('date_to'):
                queryset = queryset.filter(received_at__date__lte=filter_form.cleaned_data['date_to'])
            
            if filter_form.cleaned_data.get('webhook_config'):
                queryset = queryset.filter(webhook_config=filter_form.cleaned_data['webhook_config'])
        
        return queryset.order_by('-received_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = WebhookEventFilterForm(self.request.GET)
        
        # Estadísticas
        context['statistics'] = {
            'total_events': WebhookEvent.objects.count(),
            'completed_events': WebhookEvent.objects.filter(status='completed').count(),
            'failed_events': WebhookEvent.objects.filter(status='failed').count(),
            'pending_events': WebhookEvent.objects.filter(status='pending').count(),
            'retry_events': WebhookEvent.objects.filter(status='retry').count(),
        }
        
        return context


class WebhookEventDetailView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DetailView):
    """
    Vista para mostrar detalles de evento de webhook.
    """
    permission_required = 'tiendanube_administranet.view_webhookevent'
    model = WebhookEvent
    template_name = 'tiendanube_administranet/webhook_event_detail.html'
    context_object_name = 'webhook_event'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Logs de entrega del evento
        context['delivery_logs'] = self.object.delivery_logs.order_by('-sent_at')
        
        return context


# =============================================================================
# WEBHOOK AJAX VIEWS
# =============================================================================

@login_required
@permission_required('tiendanube_administranet.view_webhookconfig')
def test_webhook_ajax(request, webhook_id):
    """
    Vista AJAX para probar webhook.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _('Invalid request method')})
    
    try:
        webhook_config = WebhookConfig.objects.get(id=webhook_id)
        
        if not webhook_config.webhook_id:
            return JsonResponse({
                'success': False,
                'message': _('Webhook not registered in Tiendanube')
            })
        
        from ..services.webhook_service import WebhookService
        webhook_service = WebhookService(webhook_config.tiendanube_config)
        
        result = webhook_service.test_webhook(webhook_config.webhook_id)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': _('Webhook test sent successfully')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result.get('error', _('Webhook test failed'))
            })
            
    except WebhookConfig.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': _('Webhook configuration not found')
        })
    except Exception as e:
        logger.error(f"Error testing webhook: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@permission_required('tiendanube_administranet.view_webhookconfig')
def sync_webhooks_ajax(request):
    """
    Vista AJAX para sincronizar webhooks con Tiendanube.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _('Invalid request method')})
    
    try:
        # Obtener webhooks de Tiendanube
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'message': _('No active Tiendanube configuration found')
            })
        
        from ..services.webhook_service import WebhookService
        webhook_service = WebhookService(tiendanube_config)
        
        result = webhook_service.get_webhooks()
        
        if result['success']:
            # Actualizar webhooks locales
            tiendanube_webhooks = {wh['id']: wh for wh in result['webhooks']}
            local_webhooks = WebhookConfig.objects.filter(tiendanube_config=tiendanube_config)
            
            synced_count = 0
            for local_webhook in local_webhooks:
                if local_webhook.webhook_id in tiendanube_webhooks:
                    tiendanube_webhook = tiendanube_webhooks[local_webhook.webhook_id]
                    local_webhook.status = WebhookConfig.WebhookStatus.ACTIVE
                    ev = tiendanube_webhook.get('event')
                    local_webhook.events = [ev] if ev else []
                    local_webhook.save()
                    synced_count += 1
                else:
                    local_webhook.status = WebhookConfig.WebhookStatus.ERROR
                    local_webhook.save()
            
            return JsonResponse({
                'success': True,
                'message': _('Webhooks synchronized successfully'),
                'synced_count': synced_count,
                'total_webhooks': len(result['webhooks'])
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result.get('error', _('Failed to sync webhooks'))
            })
            
    except Exception as e:
        logger.error(f"Error syncing webhooks: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@permission_required('tiendanube_administranet.view_webhookevent')
def retry_webhook_event_ajax(request, event_id):
    """
    Vista AJAX para reintentar procesamiento de evento de webhook.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _('Invalid request method')})
    
    try:
        webhook_event = WebhookEvent.objects.get(id=event_id)
        
        if webhook_event.status not in ['failed', 'retry']:
            return JsonResponse({
                'success': False,
                'message': _('Event cannot be retried')
            })
        
        # Procesar evento nuevamente
        from ..services.webhook_service import WebhookProcessor
        
        result = WebhookProcessor.process_webhook_event(
            webhook_event.webhook_config,
            webhook_event.payload,
            webhook_event.headers
        )
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': _('Event processed successfully')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result.get('error', _('Event processing failed'))
            })
            
    except WebhookEvent.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': _('Webhook event not found')
        })
    except Exception as e:
        logger.error(f"Error retrying webhook event: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


# =============================================================================
# WEBHOOK ENDPOINT
# =============================================================================

@csrf_exempt
def webhook_endpoint(request):
    """
    Endpoint para recibir webhooks de Tiendanube.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    try:
        payload = request.body.decode('utf-8')
        headers = dict(request.headers)

        webhook_url = request.build_absolute_uri()
        webhook_config = WebhookConfig.objects.filter(
            webhook_url=webhook_url,
            is_active=True,
        ).select_related('tiendanube_config').first()

        if not webhook_config:
            logger.warning("No webhook configuration found for URL: %s", webhook_url)
            return JsonResponse({'error': 'Webhook not found'}, status=404)

        disabled = tiendanube_webhooks_disabled_reason(webhook_config.tiendanube_config)
        if disabled:
            logger.info("Webhook rechazado: %s", disabled)
            return JsonResponse({'error': disabled}, status=503)
    
        # Obtener datos del request
        # Verificar firma HMAC (Nuvemshop: x-linkedstore-hmac-sha256)
        signature = (
            headers.get('x-linkedstore-hmac-sha256')
            or headers.get('X-Linkedstore-Hmac-Sha256')
            or headers.get('X-Tiendanube-Signature')
            or ''
        )
        secret = (webhook_config.webhook_secret or webhook_config.tiendanube_config.webhook_secret or '').strip()
        env = getattr(settings, 'ENVIRONMENT', 'production').strip().lower()
        is_production = env in ('production', 'produccion')

        if secret or is_production:
            from ..services.webhook_service import WebhookProcessor as WebhookSig

            if not secret and is_production:
                logger.warning("Webhook rechazado: sin secret configurado en producción")
                return JsonResponse({'error': 'Webhook secret not configured'}, status=401)
            if secret and not WebhookSig.verify_hmac_signature(payload, signature, secret):
                logger.warning("Firma HMAC inválida para URL: %s", webhook_url)
                return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        # Parsear payload JSON
        try:
            event_data = json.loads(payload)
        except json.JSONDecodeError as e:
            logger.error("Payload JSON inválido: %s", e)
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        # Inbox ACK: persistir pending y responder 2xx sin procesar negocio inline
        event_type = event_data.get('type') or event_data.get('event') or ''
        event_id = str(event_data.get('id', ''))
        data_block = event_data.get('data') if isinstance(event_data.get('data'), dict) else {}
        resource_id = data_block.get('id')
        resource_type = event_type.split('/')[0] if event_type else ''

        WebhookEvent.objects.create(
            webhook_config=webhook_config,
            event_type=event_type,
            event_id=event_id,
            resource_id=resource_id,
            resource_type=resource_type,
            payload=event_data,
            headers=headers,
            status=WebhookEvent.EventStatus.PENDING,
        )

        webhook_config.last_triggered = timezone.now()
        webhook_config.save(update_fields=['last_triggered'])

        return JsonResponse({'status': 'accepted'}, status=200)
            
    except Exception as e:
        logger.error(f"Error in webhook endpoint: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)
