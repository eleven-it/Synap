"""
Vistas principales para la integración Tiendanube-AdministraNET.
"""

import logging
import requests
import uuid
import json
import threading
from django.db import close_old_connections
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import models
from django.db.models import Q
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, RedirectView, View
from django.views.generic.edit import FormView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import gettext as _
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone

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

DEFAULT_TIENDANUBE_API_URL = f'https://api.tiendanube.com/{NUVEMSHOP_API_VERSION}'

logger = logging.getLogger(__name__)


def run_customer_mapping_sync(mapping: CustomerMapping, force: bool = True):
    """Sync inmediato según sync_direction del mapeo."""
    sync_service = TiendanubeAdministraNETSyncService()
    direction = mapping.sync_direction
    if direction == CustomerMapping.SyncDirection.ADMINET_TO_TIENDANUBE:
        return sync_service.sync_customer_to_tiendanube(mapping, force=force)
    if direction == CustomerMapping.SyncDirection.TIENDANUBE_TO_ADMINET:
        return sync_service.sync_customer_to_adminet(mapping, force=force)
    ok1, m1 = sync_service.sync_customer_to_adminet(mapping, force=force)
    ok2, m2 = sync_service.sync_customer_to_tiendanube(mapping, force=force)
    return ok1 and ok2, f'Adminet: {m1}; Tiendanube: {m2}'


from .webhook_config_views import *  # noqa: F401,F403
from .product_views import *  # noqa: F401,F403
from .config_views import *  # noqa: F401,F403


class TestView(TemplateView):
    """
    Vista de prueba sin autenticación para verificar templates.
    """
    template_name = 'tiendanube_administranet/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['test_mode'] = True
        context['statistics'] = {
            'total_mappings': CustomerMapping.objects.count(),
            'synced_mappings': CustomerMapping.objects.filter(sync_status='synced').count(),
            'pending_mappings': CustomerMapping.objects.filter(sync_status='pending').count(),
            'error_mappings': CustomerMapping.objects.filter(sync_status='error').count(),
        }
        context['connections'] = {'tiendanube': False, 'adminet': True}
        context['recent_logs'] = SyncLog.objects.order_by('-started_at')[:5]
        context['recent_mappings'] = CustomerMapping.objects.order_by('-created_at')[:5]
        return context


class DashboardView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista del dashboard principal de la integración.
    """
    template_name = 'tiendanube_administranet/dashboard.html'
    permission_required = 'tiendanube_administranet.view_customermapping'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Obtener configuraciones activas
            tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
            adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
            
            context['tiendanube_config'] = tiendanube_config
            context['adminet_config'] = adminet_config
            
            # Obtener estadísticas directamente
            from ..models import CustomerMapping, ProductMapping, OrderMapping, SyncLog
            
            # Estadísticas de mapeos
            customer_mappings = CustomerMapping.objects.all()
            product_mappings = ProductMapping.objects.all()
            order_mappings = OrderMapping.objects.all()
            
            context['statistics'] = {
                'total_mappings': customer_mappings.count() + product_mappings.count() + order_mappings.count(),
                'synced_mappings': (
                    customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.SYNCED).count() +
                    product_mappings.filter(sync_status=ProductMapping.SyncStatus.SYNCED).count() +
                    order_mappings.filter(sync_status=OrderMapping.SyncStatus.SYNCED).count()
                ),
                'pending_mappings': (
                    customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.PENDING).count() +
                    product_mappings.filter(sync_status=ProductMapping.SyncStatus.PENDING).count() +
                    order_mappings.filter(sync_status=OrderMapping.SyncStatus.PENDING).count()
                ),
                'error_mappings': (
                    customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.ERROR).count() +
                    product_mappings.filter(sync_status=ProductMapping.SyncStatus.ERROR).count() +
                    order_mappings.filter(sync_status=OrderMapping.SyncStatus.ERROR).count()
                ),
            }
            
            # Probar conexiones básicas
            context['connections'] = {
                'tiendanube': tiendanube_config is not None,
                'adminet': adminet_config is not None
            }
            
            # Obtener logs recientes
            context['recent_logs'] = SyncLog.objects.order_by('-started_at')[:10]
            
            # Obtener mapeos recientes
            context['recent_mappings'] = CustomerMapping.objects.order_by('-created_at')[:5]
            
        except Exception as e:
            logger.error(f"Error obteniendo datos del dashboard: {str(e)}")
            context['error'] = str(e)
            # Valores por defecto en caso de error
            context['statistics'] = {
                'total_mappings': 0,
                'synced_mappings': 0,
                'pending_mappings': 0,
                'error_mappings': 0,
            }
            context['connections'] = {'tiendanube': False, 'adminet': False}
            context['recent_logs'] = []
            context['recent_mappings'] = []
        
        return context


class CustomerMappingListView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar mapeos de clientes con datos reales de AdministraNET.
    """
    model = CustomerMapping
    template_name = 'tiendanube_administranet/customer_mapping_list.html'
    context_object_name = 'customers'
    permission_required = 'tiendanube_administranet.view_customermapping'
    paginate_by = 20
    
    def get_queryset(self):
        """
        Lista mapeos de clientes (completos e incompletos) con filtros opcionales.
        """
        try:
            queryset = CustomerMapping.objects.all().order_by('-last_synced', '-created_at')

            link = self.request.GET.get('link', 'all')
            if link == 'complete':
                queryset = queryset.filter(
                    tiendanube_id__isnull=False,
                    adminet_codigo__isnull=False,
                    adminet_codigo__gt=0,
                )
            elif link == 'incomplete':
                queryset = queryset.exclude(
                    tiendanube_id__isnull=False,
                    adminet_codigo__isnull=False,
                    adminet_codigo__gt=0,
                )
            
            # Aplicar filtros de búsqueda
            search = self.request.GET.get('search', '')
            if search:
                queryset = queryset.filter(
                    Q(tiendanube_email__icontains=search) |
                    Q(tiendanube_first_name__icontains=search) |
                    Q(tiendanube_last_name__icontains=search) |
                    Q(adminet_codigo__icontains=search) |
                    Q(adminet_nombre__icontains=search)
                )
            
            # Aplicar filtro de estado
            status = self.request.GET.get('status', '')
            if status:
                queryset = queryset.filter(sync_status=status)
            
            # Aplicar filtro de sincronización
            sync_enabled = self.request.GET.get('sync_enabled', '')
            if sync_enabled:
                queryset = queryset.filter(sync_enabled=sync_enabled == 'true')
            
            return queryset
                
        except Exception as e:
            logger.error(f"Error obteniendo mapeos de clientes: {str(e)}")
            return CustomerMapping.objects.all().order_by('-last_synced', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Parámetros de búsqueda
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        context['sync_enabled'] = self.request.GET.get('sync_enabled', '')
        context['link'] = self.request.GET.get('link', 'all')
        
        # Estadísticas sobre el queryset filtrado (sin paginación de búsqueda duplicada)
        base_qs = CustomerMapping.objects.all()
        if context['search'] or context['status'] or context['sync_enabled']:
            base_qs = self.get_queryset()
        elif context['link'] == 'complete':
            base_qs = base_qs.filter(
                tiendanube_id__isnull=False,
                adminet_codigo__isnull=False,
                adminet_codigo__gt=0,
            )
        elif context['link'] == 'incomplete':
            base_qs = base_qs.exclude(
                tiendanube_id__isnull=False,
                adminet_codigo__isnull=False,
                adminet_codigo__gt=0,
            )

        total = base_qs.count()
        synced = base_qs.filter(sync_status=CustomerMapping.SyncStatus.SYNCED).count()
        pending = base_qs.filter(sync_status=CustomerMapping.SyncStatus.PENDING).count()
        error = base_qs.filter(sync_status=CustomerMapping.SyncStatus.ERROR).count()
        incomplete = base_qs.exclude(
            tiendanube_id__isnull=False,
            adminet_codigo__isnull=False,
            adminet_codigo__gt=0,
        ).count()
        
        context['stats'] = {
            'total': total,
            'synced': synced,
            'pending': pending,
            'error': error,
            'incomplete': incomplete,
        }
        
        return context


class SyncCustomersView(
    TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, View
):
    """
    Vista para sincronizar clientes desde AdministraNET.
    """
    permission_required = 'tiendanube_administranet.add_customermapping'
    
    def post(self, request, *args, **kwargs):
        """
        Ejecuta la sincronización de clientes desde AdministraNET.
        """
        try:
            import json
            from ..services.customer_sync_service import CustomerSyncService
            from ..models import AdministraNETConfig
            
            # Obtener parámetros del request
            data = json.loads(request.body)
            limit = data.get('limit', 100)
            offset = data.get('offset', 0)
            
            # Obtener configuración de AdministraNET
            adminet_config = AdministraNETConfig.objects.first()
            if not adminet_config:
                return JsonResponse({
                    'success': False,
                    'message': 'No hay configuración de AdministraNET'
                })
            
            # Crear servicio de sincronización
            sync_service = CustomerSyncService(
                adminet_config,
                base_empresa=resolve_mysql_base_empresa(request, adminet_config),
            )
            
            # Ejecutar sincronización
            result = sync_service.sync_customers_from_adminet(limit=limit, offset=offset)
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error en sincronización de clientes: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            })


class CustomerMappingCreateView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, CreateView):
    """
    Vista para crear un nuevo mapeo de cliente.
    """
    model = CustomerMapping
    form_class = CustomerMappingForm
    template_name = 'tiendanube_administranet/customer_mapping_form.html'
    permission_required = 'tiendanube_administranet.add_customermapping'
    success_url = reverse_lazy('tiendanube_administranet:customer_mapping_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Mapeo de cliente creado exitosamente.'))
        if self.request.POST.get('save_and_sync') == '1':
            self.object.sync_enabled = True
            self.object.save(update_fields=['sync_enabled'])
            ok, msg = run_customer_mapping_sync(self.object)
            if ok:
                messages.success(self.request, msg)
            else:
                messages.warning(self.request, msg)
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, _('Error al crear el mapeo de cliente.'))
        return super().form_invalid(form)


class CustomerMappingUpdateView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para actualizar un mapeo de cliente.
    """
    model = CustomerMapping
    form_class = CustomerMappingForm
    template_name = 'tiendanube_administranet/customer_mapping_form.html'
    permission_required = 'tiendanube_administranet.change_customermapping'
    success_url = reverse_lazy('tiendanube_administranet:customer_mapping_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Mapeo de cliente actualizado exitosamente.'))
        if self.request.POST.get('save_and_sync') == '1':
            self.object.sync_enabled = True
            self.object.save(update_fields=['sync_enabled'])
            ok, msg = run_customer_mapping_sync(self.object)
            if ok:
                messages.success(self.request, msg)
            else:
                messages.warning(self.request, msg)
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, _('Error al actualizar el mapeo de cliente.'))
        return super().form_invalid(form)


class CustomerMappingDeleteView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DeleteView):
    """
    Vista para eliminar un mapeo de cliente.
    """
    model = CustomerMapping
    template_name = 'tiendanube_administranet/customer_mapping_confirm_delete.html'
    permission_required = 'tiendanube_administranet.delete_customermapping'
    success_url = reverse_lazy('tiendanube_administranet:customer_mapping_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Mapeo de cliente eliminado exitosamente.'))
        return super().delete(request, *args, **kwargs)


class CustomerMappingDetailView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DetailView):
    """
    Vista para mostrar detalles de un mapeo de cliente.
    """
    model = CustomerMapping
    template_name = 'tiendanube_administranet/customer_mapping_detail.html'
    permission_required = 'tiendanube_administranet.view_customermapping'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener logs relacionados de tipo customer
        context['related_logs'] = SyncLog.objects.filter(
            sync_type=SyncLog.SyncType.CUSTOMER
        ).order_by('-started_at')[:10]
        
        return context


class SyncLogListView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar logs de sincronización.
    """
    model = SyncLog
    template_name = 'tiendanube_administranet/sync_log_list.html'
    context_object_name = 'logs'
    permission_required = 'tiendanube_administranet.view_synclog'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = SyncLog.objects.all()
        
        # Aplicar filtros
        sync_type = self.request.GET.get('sync_type')
        status = self.request.GET.get('status')
        platform = self.request.GET.get('platform')
        
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)
        if status:
            queryset = queryset.filter(status=status)
        if platform:
            queryset = queryset.filter(platform=platform)
        
        return queryset.order_by('-started_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas de logs
        context['total_logs'] = SyncLog.objects.count()
        context['success_logs'] = SyncLog.objects.filter(status='success').count()
        context['error_logs'] = SyncLog.objects.filter(status='error').count()
        context['warning_logs'] = SyncLog.objects.filter(status='warning').count()
        
        return context


class SyncLogDetailView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DetailView):
    """
    Vista para mostrar detalles de un log de sincronización.
    """
    model = SyncLog
    template_name = 'tiendanube_administranet/sync_log_detail.html'
    permission_required = 'tiendanube_administranet.view_synclog'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener estadísticas relacionadas basadas en el tipo de sincronización
        if self.object.sync_type == 'customer':
            # Para logs de clientes, obtener mapeos recientes
            context['related_mappings'] = CustomerMapping.objects.filter(
                last_synced__gte=self.object.started_at
            ).order_by('-last_synced')[:10]
        elif self.object.sync_type == 'product':
            # Para logs de productos, obtener mapeos recientes
            from tiendanube_administranet.models import ProductMapping
            context['related_mappings'] = ProductMapping.objects.filter(
                last_synced__gte=self.object.started_at
            ).order_by('-last_synced')[:10]
        else:
            # Para otros tipos, no mostrar mapeos relacionados
            context['related_mappings'] = []
        
        return context


class TiendanubeConfigView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, RedirectView):
    """
    Vista para gestionar configuración de Tiendanube.
    Redirige al wizard de configuración.
    """
    permission_required = 'tiendanube_administranet.view_tiendanubeconfig'
    
    def get_redirect_url(self, *args, **kwargs):
        # Verificar si hay configuraciones existentes
        configs = TiendanubeConfig.objects.all()
        if configs.exists():
            # Si hay configuraciones, redirigir a la lista
            return reverse('tiendanube_administranet:tiendanube_config_list')
        else:
            # Si no hay configuraciones, redirigir al wizard
            return reverse('tiendanube_administranet:tiendanube_config_wizard')


class AdministraNETConfigView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, FormView):
    """
    Vista para gestionar configuración de AdministraNET.
    """
    template_name = 'tiendanube_administranet/adminet_config.html'
    form_class = AdministraNETConfigForm
    permission_required = 'tiendanube_administranet.change_administranetconfig'
    success_url = reverse_lazy('tiendanube_administranet:dashboard')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        # Obtener configuración existente
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        if config:
            kwargs['instance'] = config
        return kwargs
    
    def form_valid(self, form):
        try:
            config = form.save()
            messages.success(self.request, _('Configuración de AdministraNET guardada exitosamente.'))
            
            # Probar conexión
            from ..services.adminet_service import AdministraNETService
            service = AdministraNETService(
                config,
                base_empresa=resolve_mysql_base_empresa(self.request, config),
            )
            test_result = service.test_connection()
            
            if test_result['success']:
                messages.success(self.request, _('Conexión con AdministraNET probada exitosamente.'))
                
                # Verificar y aplicar migraciones necesarias
                migration_result = service.verify_and_migrate_schema()
                
                if migration_result['migrations_applied']:
                    migrations_list = ', '.join(migration_result['migrations_applied'])
                    messages.success(self.request, f"✅ Migraciones aplicadas: {migrations_list}")
                
                if migration_result['migrations_failed']:
                    failures_list = ', '.join(migration_result['migrations_failed'])
                    messages.warning(self.request, f"⚠️ Migraciones fallidas: {failures_list}")
                
                if not migration_result['migrations_applied'] and not migration_result['migrations_failed']:
                    messages.info(self.request, _('La estructura de la base de datos está actualizada.'))
            else:
                messages.warning(self.request, f"Configuración guardada pero error de conexión: {test_result.get('message', 'Unknown error')}")
                
        except Exception as e:
            logger.exception("Error guardando configuración AdministraNET")
            messages.error(self.request, f'Error al guardar configuración: {str(e)}')
            return self.form_invalid(form)
        
        return super().form_valid(form)


# Vistas AJAX para sincronización
@login_required
@permission_required('tiendanube_administranet.add_customermapping')
def sync_customers_from_tiendanube_ajax(request):
    """
    Vista AJAX para sincronizar clientes desde Tiendanube.
    """
    if request.method == 'POST':
        try:
            limit = int(request.POST.get('limit', 100))
            offset = int(request.POST.get('offset', 0))
            
            sync_service = TiendanubeAdministraNETSyncService()
            success_count, failed_count = sync_service.sync_customers_from_tiendanube(limit, offset)
            
            return JsonResponse({
                'success': True,
                'message': f'Sincronizados {success_count} clientes, {failed_count} fallidos',
                'success_count': success_count,
                'failed_count': failed_count
            })
            
        except Exception as e:
            logger.error(f"Error en sincronización desde Tiendanube: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
@permission_required('tiendanube_administranet.add_customermapping')
def sync_customers_from_adminet_ajax(request):
    """
    Vista AJAX para sincronizar clientes desde AdministraNET.
    """
    if request.method == 'POST':
        try:
            limit = int(request.POST.get('limit', 100))
            offset = int(request.POST.get('offset', 0))
            
            sync_service = TiendanubeAdministraNETSyncService()
            success_count, failed_count = sync_service.sync_customers_from_adminet(limit, offset)
            
            return JsonResponse({
                'success': True,
                'message': f'Sincronizados {success_count} clientes, {failed_count} fallidos',
                'success_count': success_count,
                'failed_count': failed_count
            })
            
        except Exception as e:
            logger.error(f"Error en sincronización desde AdministraNET: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
@permission_required('tiendanube_administranet.change_customermapping')
def sync_mapping_ajax(request, mapping_id):
    """
    Vista AJAX para sincronizar un mapeo específico.
    """
    if request.method == 'POST':
        try:
            mapping = get_object_or_404(CustomerMapping, id=mapping_id)
            sync_service = TiendanubeAdministraNETSyncService()
            
            direction = request.POST.get('direction', 'auto')
            force = request.POST.get('force', '1') != '0'
            
            if direction == 'to_tiendanube':
                success, message = sync_service.sync_customer_to_tiendanube(mapping, force=force)
            elif direction == 'to_adminet':
                success, message = sync_service.sync_customer_to_adminet(mapping, force=force)
            else:
                success, message = run_customer_mapping_sync(mapping, force=force)
            
            return JsonResponse({
                'success': success,
                'message': message
            })
            
        except Exception as e:
            logger.error(f"Error en sincronización de mapeo {mapping_id}: {str(e)}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            })
    
    return JsonResponse({'success': False, 'error': 'Método no permitido'})


@login_required
@permission_required('tiendanube_administranet.view_customermapping')
def get_statistics_ajax(request):
    """
    Vista AJAX para obtener estadísticas actualizadas.
    """
    try:
        # Obtener estadísticas directamente sin instanciar el servicio completo
        from ..models import CustomerMapping, ProductMapping, OrderMapping, SyncLog
        from django.utils import timezone
        
        # Estadísticas de mapeos
        customer_mappings = CustomerMapping.objects.all()
        product_mappings = ProductMapping.objects.all()
        order_mappings = OrderMapping.objects.all()
        
        # Logs de sincronización recientes
        recent_logs = SyncLog.objects.filter(
            started_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).order_by('-started_at')[:10]
        
        stats = {
            'customer_mappings': {
                'total': customer_mappings.count(),
                'synced': customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.SYNCED).count(),
                'pending': customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.PENDING).count(),
                'error': customer_mappings.filter(sync_status=CustomerMapping.SyncStatus.ERROR).count()
            },
            'product_mappings': {
                'total': product_mappings.count(),
                'synced': product_mappings.filter(sync_status=ProductMapping.SyncStatus.SYNCED).count(),
                'pending': product_mappings.filter(sync_status=ProductMapping.SyncStatus.PENDING).count(),
                'error': product_mappings.filter(sync_status=ProductMapping.SyncStatus.ERROR).count()
            },
            'order_mappings': {
                'total': order_mappings.count(),
                'synced': order_mappings.filter(sync_status=OrderMapping.SyncStatus.SYNCED).count(),
                'pending': order_mappings.filter(sync_status=OrderMapping.SyncStatus.PENDING).count(),
                'error': order_mappings.filter(sync_status=OrderMapping.SyncStatus.ERROR).count()
            },
            'recent_syncs': [
                {
                    'id': log.id,
                    'type': log.get_sync_type_display(),
                    'direction': log.get_direction_display(),
                    'status': log.get_status_display(),
                    'started_at': log.started_at,
                    'completed_at': log.completed_at,
                    'total_items': log.total_items,
                    'successful_items': log.successful_items,
                    'failed_items': log.failed_items
                }
                for log in recent_logs
            ]
        }
        
        return JsonResponse({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@permission_required('tiendanube_administranet.view_customermapping')
def test_connections_ajax(request):
    """
    Vista AJAX para probar conexiones activas de Tiendanube y AdministraNET.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'})
    
    try:
        results = {
            'tiendanube': {'success': False, 'message': 'Not configured'},
            'adminet': {'success': False, 'message': 'Not configured'}
        }
        
        # Probar conexión a Tiendanube
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if tiendanube_config:
            try:
                from ..services.tiendanube_service import TiendanubeService
                service = TiendanubeService(tiendanube_config)
                test_result = service.test_connection()
                
                results['tiendanube'] = {
                    'success': test_result.get('success', False),
                    'message': test_result.get('message', 'Connection test completed')
                }
            except Exception as e:
                results['tiendanube'] = {
                    'success': False,
                    'message': f'Error: {str(e)}'
                }
        
        # Probar conexión a AdministraNET
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        if adminet_config:
            try:
                from ..services.adminet_service import AdministraNETService
                service = AdministraNETService(
                    adminet_config,
                    base_empresa=resolve_mysql_base_empresa(request, adminet_config),
                )
                test_result = service.test_connection()
                
                results['adminet'] = {
                    'success': test_result.get('success', False),
                    'message': test_result.get('message', 'Connection test completed')
                }
            except Exception as e:
                results['adminet'] = {
                    'success': False,
                    'message': f'Error: {str(e)}'
                }
        
        # Determinar éxito general
        overall_success = results['tiendanube']['success'] and results['adminet']['success']
        
        return JsonResponse({
            'success': overall_success,
            'message': 'Connection tests completed',
            'results': results
        })
            
    except Exception as e:
        logger.error(f"Error testing connections: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error al probar conexiones: {str(e)}'
        })


# Vistas faltantes para completar el menú
class ProductMappingListView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar mapeos de productos.
    """
    model = ProductMapping
    template_name = 'tiendanube_administranet/product_mapping_list.html'
    context_object_name = 'mappings'
    permission_required = 'tiendanube_administranet.view_productmapping'
    paginate_by = 20

    def get_queryset(self):
        queryset = ProductMapping.objects.all().order_by('-created_at')
        
        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(tiendanube_name__icontains=search) |
                Q(adminet_nombre__icontains=search) |
                Q(tiendanube_sku__icontains=search) |
                Q(adminet_codigo__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(sync_status=status)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_mappings'] = ProductMapping.objects.count()
        context['synced_mappings'] = ProductMapping.objects.filter(sync_status='synced').count()
        context['pending_mappings'] = ProductMapping.objects.filter(sync_status='pending').count()
        context['error_mappings'] = ProductMapping.objects.filter(sync_status='error').count()
        return context


class ProductMappingCreateView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, CreateView):
    """
    Vista para crear un nuevo mapeo de producto.
    """
    model = ProductMapping
    form_class = ProductMappingForm
    template_name = 'tiendanube_administranet/product_mapping_form.html'
    permission_required = 'tiendanube_administranet.add_productmapping'
    success_url = reverse_lazy('tiendanube_administranet:product_mapping_list')

    def form_valid(self, form):
        messages.success(self.request, _('Product mapping created successfully.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('Error creating product mapping.'))
        return super().form_invalid(form)


class ProductMappingUpdateView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para actualizar un mapeo de producto.
    """
    model = ProductMapping
    form_class = ProductMappingForm
    template_name = 'tiendanube_administranet/product_mapping_form.html'
    permission_required = 'tiendanube_administranet.change_productmapping'
    success_url = reverse_lazy('tiendanube_administranet:product_mapping_list')

    def form_valid(self, form):
        messages.success(self.request, _('Product mapping updated successfully.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('Error updating product mapping.'))
        return super().form_invalid(form)


class ProductMappingDeleteView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DeleteView):
    """
    Vista para eliminar un mapeo de producto.
    """
    model = ProductMapping
    template_name = 'tiendanube_administranet/product_mapping_confirm_delete.html'
    permission_required = 'tiendanube_administranet.delete_productmapping'
    success_url = reverse_lazy('tiendanube_administranet:product_mapping_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Product mapping deleted successfully.'))
        return super().delete(request, *args, **kwargs)


class ProductMappingDetailView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DetailView):
    """
    Vista para mostrar detalles de un mapeo de producto.
    """
    model = ProductMapping
    template_name = 'tiendanube_administranet/product_mapping_detail.html'
    permission_required = 'tiendanube_administranet.view_productmapping'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_logs'] = SyncLog.objects.filter(
            sync_type='product'
        ).order_by('-started_at')[:10]
        return context


class OrderMappingListView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar mapeos de órdenes.
    """
    model = OrderMapping
    template_name = 'tiendanube_administranet/order_mapping_list.html'
    context_object_name = 'mappings'
    permission_required = 'tiendanube_administranet.view_ordermapping'
    paginate_by = 20

    def get_queryset(self):
        queryset = OrderMapping.objects.all().order_by('-created_at')
        
        # Filtros
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(tiendanube_number__icontains=search) |
                Q(adminet_numero__icontains=search) |
                Q(tiendanube_customer_email__icontains=search)
            )
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(sync_status=status)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['total_mappings'] = OrderMapping.objects.count()
        context['synced_mappings'] = OrderMapping.objects.filter(sync_status='synced').count()
        context['pending_mappings'] = OrderMapping.objects.filter(sync_status='pending').count()
        context['error_mappings'] = OrderMapping.objects.filter(sync_status='error').count()
        return context


class OrderMappingCreateView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, CreateView):
    """
    Vista para crear un nuevo mapeo de orden.
    """
    model = OrderMapping
    form_class = OrderMappingForm
    template_name = 'tiendanube_administranet/order_mapping_form.html'
    permission_required = 'tiendanube_administranet.add_ordermapping'
    success_url = reverse_lazy('tiendanube_administranet:order_mapping_list')

    def form_valid(self, form):
        messages.success(self.request, _('Order mapping created successfully.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('Error creating order mapping.'))
        return super().form_invalid(form)


class OrderMappingUpdateView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para actualizar un mapeo de orden.
    """
    model = OrderMapping
    form_class = OrderMappingForm
    template_name = 'tiendanube_administranet/order_mapping_form.html'
    permission_required = 'tiendanube_administranet.change_ordermapping'
    success_url = reverse_lazy('tiendanube_administranet:order_mapping_list')

    def form_valid(self, form):
        messages.success(self.request, _('Order mapping updated successfully.'))
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, _('Error updating order mapping.'))
        return super().form_invalid(form)


class OrderMappingDeleteView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DeleteView):
    """
    Vista para eliminar un mapeo de orden.
    """
    model = OrderMapping
    template_name = 'tiendanube_administranet/order_mapping_confirm_delete.html'
    permission_required = 'tiendanube_administranet.delete_ordermapping'
    success_url = reverse_lazy('tiendanube_administranet:order_mapping_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Order mapping deleted successfully.'))
        return super().delete(request, *args, **kwargs)


class OrderMappingDetailView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, DetailView):
    """
    Vista para mostrar detalles de un mapeo de orden.
    """
    model = OrderMapping
    template_name = 'tiendanube_administranet/order_mapping_detail.html'
    permission_required = 'tiendanube_administranet.view_ordermapping'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_logs'] = SyncLog.objects.filter(
            sync_type='order'
        ).order_by('-started_at')[:10]
        return context


class ManualSyncView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista para sincronización manual.
    """
    template_name = 'tiendanube_administranet/manual_sync.html'
    permission_required = 'tiendanube_administranet.run_sync'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas de sincronización
        context['total_customers'] = CustomerMapping.objects.count()
        context['total_products'] = ProductMapping.objects.count()
        context['total_orders'] = OrderMapping.objects.count()
        
        context['synced_customers'] = CustomerMapping.objects.filter(sync_status='synced').count()
        context['synced_products'] = ProductMapping.objects.filter(sync_status='synced').count()
        context['synced_orders'] = OrderMapping.objects.filter(sync_status='synced').count()
        
        context['pending_customers'] = CustomerMapping.objects.filter(sync_status='pending').count()
        context['pending_products'] = ProductMapping.objects.filter(sync_status='pending').count()
        context['pending_orders'] = OrderMapping.objects.filter(sync_status='pending').count()
        
        return context


class SyncHistoryView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, ListView):
    """
    Vista para mostrar historial de sincronización.
    """
    model = SyncLog
    template_name = 'tiendanube_administranet/sync_history.html'
    context_object_name = 'logs'
    permission_required = 'tiendanube_administranet.view_synclog'
    paginate_by = 50

    def get_queryset(self):
        queryset = SyncLog.objects.all().order_by('-started_at')
        
        # Filtros
        sync_type = self.request.GET.get('sync_type')
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)
        
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        platform = self.request.GET.get('platform')
        if platform:
            queryset = queryset.filter(platform=platform)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas
        context['total_logs'] = SyncLog.objects.count()
        context['success_logs'] = SyncLog.objects.filter(status='success').count()
        context['error_logs'] = SyncLog.objects.filter(status='error').count()
        context['warning_logs'] = SyncLog.objects.filter(status='warning').count()
        
        return context


class StatusView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista para mostrar el estado del sistema de integración.
    """
    template_name = 'tiendanube_administranet/status.html'
    permission_required = 'tiendanube_administranet.view_tiendanubeconfig'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estado de las configuraciones
        try:
            tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
            context['tiendanube_configured'] = tiendanube_config is not None
            context['tiendanube_config'] = tiendanube_config
            
            # Probar conexión a Tiendanube
            if tiendanube_config:
                try:
                    from ..services.tiendanube_service import TiendanubeService
                    tiendanube_service = TiendanubeService(tiendanube_config)
                    connection_test = tiendanube_service.test_connection()
                    context['tiendanube_connection_status'] = connection_test.get('success', False)
                    context['tiendanube_connection_message'] = connection_test.get('message', '')
                except Exception as e:
                    context['tiendanube_connection_status'] = False
                    context['tiendanube_connection_message'] = str(e)
            else:
                context['tiendanube_connection_status'] = False
                context['tiendanube_connection_message'] = 'No configuration found'
        except Exception as e:
            context['tiendanube_configured'] = False
            context['tiendanube_connection_status'] = False
            context['tiendanube_connection_message'] = str(e)
        
        try:
            adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
            context['adminet_configured'] = adminet_config is not None
            context['adminet_config'] = adminet_config
            
            # Probar conexión a AdministraNET
            if adminet_config:
                try:
                    from ..services.adminet_service import AdministraNETService
                    adminet_service = AdministraNETService(
                        adminet_config,
                        base_empresa=resolve_mysql_base_empresa(self.request, adminet_config),
                    )
                    connection_test = adminet_service.test_connection()
                    context['adminet_connection_status'] = connection_test.get('success', False)
                    context['adminet_connection_message'] = connection_test.get('message', '')
                except Exception as e:
                    context['adminet_connection_status'] = False
                    context['adminet_connection_message'] = str(e)
            else:
                context['adminet_connection_status'] = False
                context['adminet_connection_message'] = 'No configuration found'
        except Exception as e:
            context['adminet_configured'] = False
            context['adminet_connection_status'] = False
            context['adminet_connection_message'] = str(e)
        
        # Estadísticas de mapeos
        context['customer_mappings'] = CustomerMapping.objects.count()
        context['product_mappings'] = ProductMapping.objects.count()
        context['order_mappings'] = OrderMapping.objects.count()
        
        # Estadísticas adicionales
        context['total_products'] = ProductMapping.objects.count()
        context['total_customers'] = CustomerMapping.objects.count()
        context['total_orders'] = OrderMapping.objects.count()
        
        # Últimos logs
        context['recent_logs'] = SyncLog.objects.all().order_by('-started_at')[:5]
        
        # Estadísticas de sincronización (usar valores correctos de Status.choices)
        context['successful_syncs'] = SyncLog.objects.filter(status=SyncLog.Status.COMPLETED).count()
        context['failed_syncs'] = SyncLog.objects.filter(status=SyncLog.Status.FAILED).count()
        context['pending_syncs'] = SyncLog.objects.filter(status=SyncLog.Status.PENDING).count()
        
        # Última sincronización exitosa
        last_sync = SyncLog.objects.filter(status=SyncLog.Status.COMPLETED).order_by('-started_at').first()
        context['last_sync'] = last_sync
        
        # Webhooks
        try:
            context['total_webhook_events'] = WebhookEvent.objects.count()
            context['recent_webhook_events'] = WebhookEvent.objects.order_by('-received_at')[:5]
        except Exception as e:
            logger.warning(f"Error obteniendo eventos de webhook: {e}")
            context['total_webhook_events'] = 0
            context['recent_webhook_events'] = []

        # Pool MySQL Synap (solo informativo; credenciales en .env / DATABASES)
        try:
            from django.conf import settings as dj_settings

            mysql_cfg = dj_settings.DATABASES.get('mysql') or {}
            context['mysql_pool_host'] = mysql_cfg.get('HOST') or ''
            context['mysql_pool_port'] = mysql_cfg.get('PORT') or ''
        except Exception:
            context['mysql_pool_host'] = ''
            context['mysql_pool_port'] = ''

        return context


class AutoSyncConfigView(TiendanubeAdministranetLoginMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista para configuración de sincronización automática.
    """
    template_name = 'tiendanube_administranet/auto_sync_config.html'
    permission_required = 'tiendanube_administranet.change_tiendanubeconfig'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener configuración activa
        config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not config:
            # Crear configuración por defecto si no existe
            config = TiendanubeConfig.objects.create(
                name="Default Configuration",
                store_id="default",
                access_token="",
                auto_sync=False,
                sync_interval=30
            )
        
        context['config'] = config
        
        # Opciones de intervalo
        context['interval_choices'] = [
            (5, _('5 min')),
            (15, _('15 min')),
            (30, _('30 min')),
            (60, _('1 hour')),
            (180, _('3 hours')),
            (360, _('6 hours')),
            (720, _('12 hours')),
            (1440, _('24 hours')),
        ]
        
        # Estadísticas de sincronización
        from ..models import SyncLog
        total_syncs = SyncLog.objects.count()
        successful_syncs = SyncLog.objects.filter(status=SyncLog.Status.COMPLETED).count()
        failed_syncs = SyncLog.objects.filter(status=SyncLog.Status.FAILED).count()
        
        # Duración promedio
        avg_duration = SyncLog.objects.filter(
            status=SyncLog.Status.COMPLETED,
            duration_seconds__isnull=False
        ).aggregate(avg=models.Avg('duration_seconds'))
        
        context['stats'] = {
            'total_syncs': total_syncs,
            'successful_syncs': successful_syncs,
            'failed_syncs': failed_syncs,
            'avg_duration': round(avg_duration['avg'] or 0, 1)
        }
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Guardar configuración de sincronización automática."""
        try:
            # Obtener configuración activa
            config = TiendanubeConfig.objects.filter(is_active=True).first()
            if not config:
                return JsonResponse({
                    'success': False,
                    'message': _('No active configuration found')
                })
            
            # Actualizar configuración
            config.auto_sync = request.POST.get('auto_sync') == 'on'
            
            # Intervalo personalizado o predefinido
            if request.POST.get('custom_sync_interval'):
                config.sync_interval = int(request.POST.get('custom_sync_interval'))
            else:
                config.sync_interval = int(request.POST.get('sync_interval', 30))
            
            # Qué sincronizar
            config.sync_products = request.POST.get('sync_products') == 'on'
            config.sync_customers = request.POST.get('sync_customers') == 'on'
            config.sync_orders = request.POST.get('sync_orders') == 'on'
            config.sync_stock = request.POST.get('sync_stock') == 'on'
            
            config.save()
            
            return JsonResponse({
                'success': True,
                'message': _('Configuration saved successfully')
            })
            
        except Exception as e:
            logger.error(f"Error saving auto sync configuration: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            })


@login_required
@permission_required('tiendanube_administranet.change_administranetconfig')
def migrate_adminet_schema_ajax(request):
    """
    Vista AJAX para aplicar migraciones de schema en AdministraNET.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _('Invalid request method')})
    
    try:
        # Obtener configuración activa
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({
                'success': False,
                'message': _('No active AdministraNET configuration found')
            })
        
        # Crear servicio y aplicar migraciones
        from ..services.adminet_service import AdministraNETService
        service = AdministraNETService(
            config,
            base_empresa=resolve_mysql_base_empresa(request, config),
        )
        
        # Verificar conexión primero
        test_result = service.test_connection()
        if not test_result['success']:
            return JsonResponse({
                'success': False,
                'message': f"Conexión fallida: {test_result['message']}"
            })
        
        # Aplicar migraciones
        migration_result = service.verify_and_migrate_schema()
        
        # Preparar respuesta
        response_data = {
            'success': migration_result['success'],
            'message': migration_result['message'],
            'migrations_applied': migration_result.get('migrations_applied', []),
            'migrations_failed': migration_result.get('migrations_failed', [])
        }
        
        return JsonResponse(response_data)
        
    except Exception as e:
        logger.error(f"Error applying schema migrations: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error aplicando migraciones: {str(e)}'
        })


@login_required
@permission_required('tiendanube_administranet.change_administranetconfig')
def test_adminet_connection_ajax(request):
    """
    Vista AJAX para probar conexión específica a AdministraNET.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _('Invalid request method')})
    
    try:
        from ..mysql import get_session_base_empresa

        database = get_session_base_empresa(request)
        if not database:
            return JsonResponse({
                'success': False,
                'message': _(
                    'No hay empresa en sesión (base_empresa). No se puede probar la conexión a MySQL.'
                ),
            })

        temp_config = AdministraNETConfig(
            name='Prueba de conexión',
            database=database,
            is_active=False,
        )
        
        # Probar conexión (pool Synap: solo se usa el nombre de base alineado a sesión)
        from ..services.adminet_service import AdministraNETService
        service = AdministraNETService(
            temp_config,
            base_empresa=resolve_mysql_base_empresa(request, temp_config),
        )
        test_result = service.test_connection()
        
        if test_result['success']:
            return JsonResponse({
                'success': True,
                'message': test_result['message'],
                'version': test_result.get('version', '')
            })
        else:
            return JsonResponse({
                'success': False,
                'message': test_result['message']
            })
        
    except Exception as e:
        logger.error(f"Error testing AdministraNET connection: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@permission_required('tiendanube_administranet.change_tiendanubeconfig')
def test_tiendanube_connection_ajax(request):
    """
    Vista AJAX para probar conexión específica a Tiendanube.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _('Invalid request method')})
    
    try:
        # Obtener datos del formulario
        store_id = request.POST.get('store_id', '').strip()
        access_token = request.POST.get('access_token', '').strip()
        api_url = request.POST.get('api_url', DEFAULT_TIENDANUBE_API_URL).strip()
        
        # Validar campos requeridos
        if not all([store_id, access_token]):
            return JsonResponse({
                'success': False,
                'message': _('Please fill in all required fields: store ID and access token')
            })
        
        # Crear configuración temporal para la prueba
        temp_config = TiendanubeConfig(
            name='Test Connection',
            store_id=store_id,
            access_token=access_token,
            api_url=api_url,
            is_active=False  # No guardar esta configuración
        )
        
        # Probar conexión
        from ..services.tiendanube_service import TiendanubeService
        service = TiendanubeService(temp_config)
        store_info = service.get_store_info()
        
        return JsonResponse({
            'success': True,
            'message': _('Tiendanube connection successful! Connected to store: {}').format(store_info.get('name', store_id))
        })
        
    except Exception as e:
        logger.error(f"Error testing Tiendanube connection: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@permission_required('tiendanube_administranet.run_sync')
def get_sync_log_status_ajax(request, pk: int):
    """Estado en tiempo real de un SyncLog (polling desde manual sync)."""
    try:
        log = SyncLog.objects.get(pk=pk)
    except SyncLog.DoesNotExist:
        return JsonResponse(
            {'success': False, 'message': _('Log de sincronización no encontrado')},
            status=404,
        )

    total = log.total_items or 0
    processed = log.processed_items or 0
    percent = round((processed / total) * 100) if total > 0 else 0
    is_complete = log.status in (
        SyncLog.Status.COMPLETED,
        SyncLog.Status.FAILED,
        SyncLog.Status.CANCELLED,
    )

    return JsonResponse({
        'success': True,
        'sync_log_id': log.id,
        'status': log.status,
        'status_display': log.get_status_display(),
        'total_items': total,
        'processed_items': processed,
        'successful_items': log.successful_items or 0,
        'failed_items': log.failed_items or 0,
        'percent': percent,
        'is_complete': is_complete,
        'message': log.error_message or '',
    })


def _sync_type_to_log_type(sync_type: str):
    return {
        'customers': SyncLog.SyncType.CUSTOMER,
        'products': SyncLog.SyncType.PRODUCT,
        'orders': SyncLog.SyncType.ORDER,
    }.get(sync_type)


def _direction_to_log_direction(direction: str):
    return {
        'tiendanube': SyncLog.SyncDirection.TO_ADMINET,
        'adminet': SyncLog.SyncDirection.FROM_ADMINET,
        'both': SyncLog.SyncDirection.BIDIRECTIONAL,
    }.get(direction, SyncLog.SyncDirection.TO_ADMINET)


def _dispatch_background_sync(job, sync_log_id: int) -> None:
    """Ejecuta sync en hilo daemon; cierra conexiones DB al terminar."""

    def _runner():
        close_old_connections()
        try:
            job()
        except Exception as exc:
            logger.exception('Error en sync en background (log %s)', sync_log_id)
            try:
                log = SyncLog.objects.get(pk=sync_log_id)
                if log.status == SyncLog.Status.IN_PROGRESS:
                    log.complete_sync(False, str(exc))
            except SyncLog.DoesNotExist:
                pass
        finally:
            close_old_connections()

    threading.Thread(target=_runner, daemon=True).start()


@login_required
@permission_required('tiendanube_administranet.run_sync')
def trigger_sync_ajax(request):
    """
    Vista AJAX para disparar sincronización manual.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _('Invalid request method')})
    
    try:
        import json
        data = json.loads(request.body)
        sync_type = data.get('sync_type', 'customers')
        direction = data.get('direction', 'tiendanube')
        
        # Validar parámetros
        if sync_type not in ['customers', 'products', 'orders', 'full']:
            return JsonResponse({
                'success': False,
                'message': _('Invalid sync type. Must be customers, products, orders, or full')
            })
        
        if direction not in ['tiendanube', 'adminet', 'both']:
            return JsonResponse({
                'success': False,
                'message': _('Invalid direction. Must be tiendanube, adminet, or both')
            })
        
        # Validar restricciones de sincronización
        if sync_type == 'products' and direction == 'tiendanube':
            return JsonResponse({
                'success': False,
                'message': _('Product synchronization from Tiendanube to AdministraNET is not allowed')
            })

        if sync_type == 'orders' and direction == 'adminet':
            return JsonResponse({
                'success': False,
                'message': _(
                    'La sincronización de pedidos desde AdministraNET hacia Tienda Nube '
                    'no está disponible. Los pedidos se crean en Tienda Nube.'
                ),
            })
        
        # Obtener configuraciones activas
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        # Validar configuraciones
        if not tiendanube_config and not adminet_config:
            return JsonResponse({
                'success': False,
                'message': _('No active configurations found. Please configure Tiendanube and AdministraNET first.')
            })
        elif not tiendanube_config:
            return JsonResponse({
                'success': False,
                'message': _('Tiendanube configuration not found. Please configure Tiendanube first.')
            })
        elif not adminet_config:
            return JsonResponse({
                'success': False,
                'message': _('AdministraNET configuration not found. Please configure AdministraNET first.')
            })
        
        # Crear servicio de sincronización
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)

        # Full sync: ejecuta en el request (varios sub-procesos con logs propios)
        if sync_type == 'full':
            results = {
                'customers': sync_service.sync_customers_from_tiendanube(),
                'products': sync_service.sync_products_from_tiendanube(),
                'orders': sync_service.sync_orders_from_tiendanube()
            }

            total_processed = sum(r.get('total_processed', 0) for r in results.values())
            total_successful = sum(r.get('successful', 0) for r in results.values())
            total_failed = sum(r.get('failed', 0) for r in results.values())

            return JsonResponse({
                'success': True,
                'async': False,
                'message': (
                    f'Sincronización completa: {total_successful} exitosas, '
                    f'{total_failed} fallidas'
                ),
                'total_processed': total_processed,
                'successful': total_successful,
                'failed': total_failed,
                'details': results,
            })

        log_type = _sync_type_to_log_type(sync_type)
        if not log_type:
            return JsonResponse({
                'success': False,
                'message': _('Tipo de sync no soportado'),
            })

        sync_log = SyncLog.objects.create(
            sync_type=log_type,
            direction=_direction_to_log_direction(direction),
            status=SyncLog.Status.IN_PROGRESS,
            tiendanube_config=tiendanube_config,
            adminet_config=adminet_config,
        )

        def _run_sync():
            svc = TiendanubeAdministraNETSyncService(
                tiendanube_config, adminet_config
            )
            if sync_type == 'customers':
                if direction == 'tiendanube':
                    svc.sync_customers_from_tiendanube(sync_log=sync_log)
                else:
                    svc.sync_customers_from_adminet(sync_log=sync_log)
            elif sync_type == 'products':
                if direction == 'tiendanube':
                    svc.sync_products_from_tiendanube(sync_log=sync_log)
                else:
                    svc.sync_products_from_adminet(sync_log=sync_log)
            elif sync_type == 'orders':
                if direction == 'tiendanube':
                    svc.sync_orders_from_tiendanube(sync_log=sync_log)

        _dispatch_background_sync(_run_sync, sync_log.id)

        return JsonResponse({
            'success': True,
            'async': True,
            'sync_log_id': sync_log.id,
            'message': _('Sincronización iniciada. Consulte el progreso en pantalla.'),
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': _('Invalid JSON data')
        })
    except Exception as e:
        logger.error(f"Error in trigger_sync_ajax: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        })


@login_required
@permission_required('tiendanube_administranet.view_synclog')
def get_sync_history_ajax(request):
    """
    Vista AJAX para obtener historial de sincronización.
    """
    try:
        # Obtener logs recientes
        logs = SyncLog.objects.order_by('-started_at')[:20]
        
        history = []
        for log in logs:
            history.append({
                'id': log.id,
                'sync_type': log.sync_type,
                'direction': log.direction,
                'status': log.status,
                'started_at': log.started_at.isoformat() if log.started_at else None,
                'completed_at': log.completed_at.isoformat() if log.completed_at else None,
                'duration_seconds': log.duration_seconds,
                'processed_items': log.processed_items,
                'successful_items': log.successful_items,
                'failed_items': log.failed_items,
                'total_items': log.total_items,
                'error_message': log.error_message,
                'get_status_display': log.get_status_display(),
                'get_direction_display': log.get_direction_display(),
                'get_sync_type_display': log.get_sync_type_display(),
            })
        
        return JsonResponse({
            'success': True,
            'history': history
        })
        
    except Exception as e:
        logger.error(f"Error in get_sync_history_ajax: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': str(e)
        })

# =============================================================================
# WEBHOOK VIEWS
# =============================================================================


@login_required
@permission_required('tiendanube_administranet.view_customermapping')
def search_customers_ajax(request):
    """
    Buscar clientes en Tiendanube por query.
    """
    try:
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({
                'success': False,
                'message': 'Ingrese un término de búsqueda (email, nombre o documento).'
            })

        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'message': 'No hay configuración activa de Tiendanube'
            })

        from ..services.tiendanube_service import TiendanubeService
        service = TiendanubeService(tiendanube_config)
        result = service.search_customers(query, limit=20)

        if result['success']:
            from ..services.customer_lookup import tiendanube_customer_preview
            customers = [
                tiendanube_customer_preview(c) for c in result.get('customers', [])
            ]
            return JsonResponse({
                'success': True,
                'customers': customers,
                'total': len(customers),
                'query': query,
                'source': 'tiendanube',
            })
        return JsonResponse({
            'success': False,
            'message': result.get('message', 'Error buscando clientes'),
        })

    except Exception as e:
        logger.error(f"Error searching customers: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error buscando clientes: {str(e)}'
        })


@login_required
@permission_required('tiendanube_administranet.view_customermapping')
def lookup_tiendanube_customer_ajax(request, customer_id):
    """Consultar un cliente Tienda Nube por ID autogenerado."""
    try:
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'message': 'No hay configuración activa de Tiendanube',
            })
        from ..services.tiendanube_service import TiendanubeService
        result = TiendanubeService(tiendanube_config).get_customer(int(customer_id))
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'message': result.get(
                    'message',
                    f'El cliente Tienda Nube {customer_id} no existe o no es accesible.',
                ),
            })
        from ..services.customer_lookup import (
            tiendanube_customer_preview,
            tiendanube_customer_to_form_fields,
        )
        customer = result['customer']
        return JsonResponse({
            'success': True,
            'source': 'tiendanube',
            'customer': tiendanube_customer_preview(customer),
            'form_fields': tiendanube_customer_to_form_fields(customer),
        })
    except Exception as e:
        logger.error('lookup_tiendanube_customer_ajax: %s', e)
        return JsonResponse({'success': False, 'message': str(e)})


def _adminet_service_for_request(request):
    from ..mysql import get_session_base_empresa
    from ..services.adminet_service import AdministraNETService

    adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
    if not adminet_config:
        return None, 'No hay configuración activa de AdministraNET'
    base_empresa = get_session_base_empresa(request)
    if not base_empresa:
        return None, 'No se detectó la empresa en sesión (base_empresa).'
    return AdministraNETService(adminet_config, base_empresa=base_empresa), None


@login_required
@permission_required('tiendanube_administranet.view_customermapping')
def search_adminet_customers_ajax(request):
    """Buscar clientes en AdministraNET (MySQL) por nombre, email, CUIT o teléfono."""
    try:
        query = request.GET.get('q', '').strip()
        if not query:
            return JsonResponse({
                'success': False,
                'message': 'Ingrese un término de búsqueda.',
            })
        service, err = _adminet_service_for_request(request)
        if err:
            return JsonResponse({'success': False, 'message': err})
        result = service.search_customers(query, limit=20)
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'message': result.get('message', 'Error buscando clientes'),
            })
        from ..services.customer_lookup import adminet_customer_preview
        customers = [
            adminet_customer_preview(row) for row in result.get('customers', [])
        ]
        return JsonResponse({
            'success': True,
            'customers': customers,
            'total': len(customers),
            'query': query,
            'source': 'adminet',
        })
    except Exception as e:
        logger.error('search_adminet_customers_ajax: %s', e)
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@permission_required('tiendanube_administranet.view_customermapping')
def lookup_adminet_customer_ajax(request, customer_code):
    """Consultar un cliente AdministraNET por Codigo autogenerado."""
    try:
        service, err = _adminet_service_for_request(request)
        if err:
            return JsonResponse({'success': False, 'message': err})
        result = service.get_customer(int(customer_code))
        if not result.get('success'):
            return JsonResponse({
                'success': False,
                'message': f'El cliente AdministraNET {customer_code} no existe.',
            })
        from ..services.customer_lookup import (
            adminet_customer_preview,
            adminet_customer_to_form_fields,
        )
        customer = result['customer']
        return JsonResponse({
            'success': True,
            'source': 'adminet',
            'customer': adminet_customer_preview(customer),
            'form_fields': adminet_customer_to_form_fields(customer),
        })
    except Exception as e:
        logger.error('lookup_adminet_customer_ajax: %s', e)
        return JsonResponse({'success': False, 'message': str(e)})


@login_required
@permission_required('tiendanube_administranet.view_customermapping')
def get_customer_orders_ajax(request, customer_id):
    """
    Obtener órdenes de un cliente específico.
    """
    try:
        # Obtener configuración activa
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'message': 'No hay configuración activa de Tiendanube'
            })
        
        # Obtener órdenes del cliente
        from ..services.tiendanube_service import TiendanubeService
        service = TiendanubeService(tiendanube_config)
        result = service.get_customer_orders(customer_id, limit=50)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'orders': result['orders'],
                'total': result['total'],
                'customer_id': customer_id
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result['message']
            })
            
    except Exception as e:
        logger.error(f"Error getting customer orders: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error obteniendo órdenes del cliente: {str(e)}'
        })


@login_required
@permission_required('tiendanube_administranet.view_customermapping')
def validate_customer_data_ajax(request):
    """
    Validar datos de cliente según la documentación de Tiendanube.
    """
    try:
        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'message': 'Método no permitido'
            })
        
        customer_data = json.loads(request.body)
        
        # Obtener configuración activa
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'message': 'No hay configuración activa de Tiendanube'
            })
        
        # Validar datos
        from ..services.tiendanube_service import TiendanubeService
        service = TiendanubeService(tiendanube_config)
        result = service.validate_customer_data(customer_data)
        
        return JsonResponse({
            'success': True,
            'valid': result['valid'],
            'errors': result['errors'],
            'warnings': result['warnings']
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Datos JSON inválidos'
        })
    except Exception as e:
        logger.error(f"Error validating customer data: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error validando datos: {str(e)}'
        })


@login_required
@permission_required('tiendanube_administranet.view_customermapping')
def get_customer_statistics_ajax(request):
    """
    Obtener estadísticas detalladas de clientes.
    """
    try:
        # Obtener configuración activa
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'message': 'No hay configuración activa de Tiendanube'
            })
        
        # Obtener estadísticas
        from ..services.tiendanube_service import TiendanubeService
        service = TiendanubeService(tiendanube_config)
        result = service.get_customer_statistics()
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'statistics': result['statistics']
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result['message']
            })
            
    except Exception as e:
        logger.error(f"Error getting customer statistics: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error obteniendo estadísticas: {str(e)}'
        })


@login_required
@permission_required('tiendanube_administranet.change_customermapping')
def bulk_update_customers_ajax(request):
    """
    Actualización masiva de clientes.
    """
    try:
        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'message': 'Método no permitido'
            })
        
        data = json.loads(request.body)
        customer_ids = data.get('customer_ids', [])
        update_data = data.get('update_data', {})
        
        if not customer_ids:
            return JsonResponse({
                'success': False,
                'message': 'No se especificaron clientes para actualizar'
            })
        
        # Actualizar clientes
        updated_count = 0
        errors = []
        
        for customer_id in customer_ids:
            try:
                customer = CustomerMapping.objects.get(id=customer_id)
                for field, value in update_data.items():
                    if hasattr(customer, field):
                        setattr(customer, field, value)
                customer.save()
                updated_count += 1
            except CustomerMapping.DoesNotExist:
                errors.append(f'Cliente {customer_id} no encontrado')
            except Exception as e:
                errors.append(f'Error actualizando cliente {customer_id}: {str(e)}')
        
        return JsonResponse({
            'success': True,
            'updated_count': updated_count,
            'errors': errors,
            'message': f'Se actualizaron {updated_count} clientes exitosamente'
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Datos JSON inválidos'
        })
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error en actualización masiva: {str(e)}'
        })


@login_required
@permission_required('tiendanube_administranet.change_customermapping')
def export_customers_ajax(request):
    """
    Exportar clientes a CSV/Excel.
    """
    try:
        # Obtener filtros aplicados
        form = CustomerMappingFilterForm(request.GET)
        queryset = CustomerMapping.objects.all()
        
        if form.is_valid():
            # Aplicar los mismos filtros que en la vista de lista
            # (código duplicado por simplicidad)
            search = form.cleaned_data.get('search')
            if search:
                queryset = queryset.filter(
                    Q(tiendanube_email__icontains=search) |
                    Q(tiendanube_name__icontains=search) |
                    Q(tiendanube_first_name__icontains=search) |
                    Q(tiendanube_last_name__icontains=search) |
                    Q(tiendanube_document__icontains=search) |
                    Q(adminet_nombre__icontains=search) |
                    Q(adminet_documento__icontains=search)
                )
            
            # Aplicar otros filtros...
            sync_status = form.cleaned_data.get('sync_status')
            if sync_status:
                queryset = queryset.filter(sync_status=sync_status)
        
        # Generar CSV
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Headers
        headers = [
            'ID', 'Email Tiendanube', 'Nombre', 'Nombre Completo', 'Documento',
            'Teléfono', 'Dirección', 'Ciudad', 'Estado', 'País', 'Código Postal',
            'Email Verificado', 'Acepta Marketing', 'Total Gastado', 'Cantidad Órdenes',
            'Estado Sincronización', 'Última Sincronización', 'Creado'
        ]
        writer.writerow(headers)
        
        # Datos
        for customer in queryset:
            writer.writerow([
                customer.id,
                customer.tiendanube_email,
                customer.tiendanube_name,
                f"{customer.tiendanube_first_name or ''} {customer.tiendanube_last_name or ''}".strip(),
                customer.tiendanube_document,
                customer.tiendanube_phone,
                customer.tiendanube_address,
                customer.tiendanube_city,
                customer.tiendanube_state,
                customer.tiendanube_country,
                customer.tiendanube_postal_code,
                'Sí' if customer.tiendanube_verified_email else 'No',
                'Sí' if customer.tiendanube_accepts_marketing else 'No',
                customer.tiendanube_total_spent,
                customer.tiendanube_orders_count,
                customer.get_sync_status_display(),
                customer.last_synced.strftime('%Y-%m-%d %H:%M:%S') if customer.last_synced else '',
                customer.created_at.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        # Crear respuesta
        from django.http import HttpResponse
        response = HttpResponse(
            output.getvalue(),
            content_type='text/csv; charset=utf-8'
        )
        response['Content-Disposition'] = 'attachment; filename="clientes_tiendanube.csv"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting customers: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error exportando clientes: {str(e)}'
        })

from .webhook_views import (
    webhook_status,
    configure_webhooks,
    webhook_receiver,
    webhook_events,
    webhook_delivery_logs
)

from .validation_views import (
    DataValidationView,
    ValidateDataAjaxView,
    FixInconsistenciesAjaxView,
    SyncUpdatesAjaxView
)

# Vista de debug temporal
class WebhookEventDebugView(TiendanubeAdministranetLoginMixin, DetailView):
    model = WebhookEvent
    template_name = 'tiendanube_administranet/webhook_event_debug.html'
    context_object_name = 'event'


# =============================================================================
# FUNCIONES AJAX PARA WEBHOOKS
# =============================================================================

@login_required
@require_http_methods(["POST"])
def toggle_webhook_ajax(request, webhook_id):
    """
    Activar/desactivar webhook en Tiendanube.
    """
    try:
        # Obtener configuración de webhook
        webhook_config = get_object_or_404(WebhookConfig, id=webhook_id)
        
        # Obtener configuración de Tiendanube
        tiendanube_config = webhook_config.tiendanube_config
        
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'message': _('Tiendanube configuration not found')
            })
        
        # Crear servicio de webhooks
        from ..services.webhook_service import WebhookService
        webhook_service = WebhookService(tiendanube_config)
        
        # Obtener estado actual del webhook
        if webhook_config.webhook_id:
            # Determinar el nuevo estado basado en el estado actual
            current_status = webhook_config.status
            new_status = 'inactive' if current_status == 'active' else 'active'
            
            # Por ahora, solo actualizar el estado local
            # TODO: Implementar sincronización real con Tiendanube cuando la API lo permita
            webhook_config.status = new_status
            webhook_config.save()
            
            action = _('activated') if new_status == 'active' else _('deactivated')
            return JsonResponse({
                'success': True,
                'message': _('Webhook {action} successfully (local only)').format(action=action),
                'new_status': new_status
            })
        else:
            return JsonResponse({
                'success': False,
                'message': _('Webhook not configured in Tiendanube')
            })
            
    except Exception as e:
        logger.error(f"Error toggling webhook {webhook_id}: {e}")
        return JsonResponse({
            'success': False,
            'message': _('Error toggling webhook: {error}').format(error=str(e))
        })
