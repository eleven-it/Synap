"""
Vistas principales para la integración Tiendanube-AdministraNET.
"""

import logging
import requests
import uuid
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
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

logger = logging.getLogger(__name__)


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


class DashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
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


class CustomerMappingListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar mapeos de clientes con datos reales de AdministraNET.
    """
    model = CustomerMapping
    template_name = 'tiendanube_administranet/customer_mapping_list.html'
    context_object_name = 'page_obj'
    permission_required = 'tiendanube_administranet.view_customermapping'
    paginate_by = 20
    
    def get_queryset(self):
        """
        Obtiene solo mapeos reales de clientes que existen tanto en TiendaNube como en AdministraNET.
        """
        try:
            # Solo mostrar mapeos reales que tienen tanto TiendaNube ID como AdministraNET código
            queryset = CustomerMapping.objects.filter(
                tiendanube_id__isnull=False,
                adminet_codigo__isnull=False,
                adminet_codigo__gt=0
            ).order_by('-last_synced', '-created_at')
            
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
            # Fallback a datos existentes
            return CustomerMapping.objects.filter(
                tiendanube_id__isnull=False,
                adminet_codigo__isnull=False,
                adminet_codigo__gt=0
            ).order_by('-last_synced', '-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Parámetros de búsqueda
        context['search'] = self.request.GET.get('search', '')
        context['status'] = self.request.GET.get('status', '')
        context['sync_enabled'] = self.request.GET.get('sync_enabled', '')
        
        # Estadísticas básicas
        queryset = self.get_queryset()
        
        # Manejar tanto QuerySet como lista
        if hasattr(queryset, 'filter') and hasattr(queryset, 'model'):
            # Es un QuerySet
            total = queryset.count()
            synced = queryset.filter(sync_status=CustomerMapping.SyncStatus.SYNCED).count()
            pending = queryset.filter(sync_status=CustomerMapping.SyncStatus.PENDING).count()
            error = queryset.filter(sync_status=CustomerMapping.SyncStatus.ERROR).count()
        else:
            # Es una lista
            total = len(queryset)
            synced = len([c for c in queryset if c.sync_status == CustomerMapping.SyncStatus.SYNCED])
            pending = len([c for c in queryset if c.sync_status == CustomerMapping.SyncStatus.PENDING])
            error = len([c for c in queryset if c.sync_status == CustomerMapping.SyncStatus.ERROR])
        
        context['stats'] = {
            'total': total,
            'synced': synced,
            'pending': pending,
            'error': error,
        }
        
        return context


class SyncCustomersView(LoginRequiredMixin, View):
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
            sync_service = CustomerSyncService(adminet_config)
            
            # Ejecutar sincronización
            result = sync_service.sync_customers_from_adminet(limit=limit, offset=offset)
            
            return JsonResponse(result)
            
        except Exception as e:
            logger.error(f"Error en sincronización de clientes: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error en sincronización: {str(e)}'
            })


class CustomerMappingCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Vista para crear un nuevo mapeo de cliente.
    """
    model = CustomerMapping
    form_class = CustomerMappingForm
    template_name = 'tiendanube_administranet/customer_mapping_form.html'
    permission_required = 'tiendanube_administranet.add_customermapping'
    success_url = reverse_lazy('tiendanube_administranet:customer_mapping_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Mapeo de cliente creado exitosamente.'))
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Error al crear el mapeo de cliente.'))
        return super().form_invalid(form)


class CustomerMappingUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para actualizar un mapeo de cliente.
    """
    model = CustomerMapping
    form_class = CustomerMappingForm
    template_name = 'tiendanube_administranet/customer_mapping_form.html'
    permission_required = 'tiendanube_administranet.change_customermapping'
    success_url = reverse_lazy('tiendanube_administranet:customer_mapping_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Mapeo de cliente actualizado exitosamente.'))
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, _('Error al actualizar el mapeo de cliente.'))
        return super().form_invalid(form)


class CustomerMappingDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
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


class CustomerMappingDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
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


class SyncLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
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


class SyncLogDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
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


class TiendanubeConfigView(LoginRequiredMixin, PermissionRequiredMixin, RedirectView):
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


class AdministraNETConfigView(LoginRequiredMixin, PermissionRequiredMixin, FormView):
    """
    Vista para gestionar configuración de AdministraNET.
    """
    template_name = 'tiendanube_administranet/adminet_config.html'
    form_class = AdministraNETConfigForm
    permission_required = 'tiendanube_administranet.change_administraNETconfig'
    success_url = reverse_lazy('tiendanube_administranet:dashboard')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Obtener configuración existente
        config = AdministraNETConfig.objects.filter(is_active=True).first()
        if config:
            kwargs['instance'] = config
        return kwargs
    
    def form_valid(self, form):
        try:
            # Debug: imprimir datos del formulario
            print(f"Form data: {form.cleaned_data}")
            print(f"Form is valid: {form.is_valid()}")
            print(f"Form errors: {form.errors}")
            
            config = form.save()
            messages.success(self.request, _('Configuración de AdministraNET guardada exitosamente.'))
            
            # Probar conexión
            from .services.adminet_service import AdministraNETService
            service = AdministraNETService(config)
            test_result = service.test_connection()
            
            if test_result['success']:
                messages.success(self.request, _('Conexión con AdministraNET probada exitosamente.'))
            else:
                messages.warning(self.request, f"Configuración guardada pero error de conexión: {test_result['error']}")
                
        except Exception as e:
            print(f"Error saving config: {e}")
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
            
            if direction == 'to_tiendanube':
                success, message = sync_service.sync_customer_to_tiendanube(mapping)
            elif direction == 'to_adminet':
                success, message = sync_service.sync_customer_to_adminet(mapping)
            else:
                # Sincronización automática según dirección del mapeo
                if mapping.sync_direction == 'tiendanube_to_adminet':
                    success, message = sync_service.sync_customer_to_adminet(mapping)
                elif mapping.sync_direction == 'adminet_to_tiendanube':
                    success, message = sync_service.sync_customer_to_tiendanube(mapping)
                else:
                    # Bidireccional
                    success1, message1 = sync_service.sync_customer_to_adminet(mapping)
                    success2, message2 = sync_service.sync_customer_to_tiendanube(mapping)
                    success = success1 and success2
                    message = f"Adminet: {message1}, Tiendanube: {message2}"
            
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
    Vista AJAX para probar conexiones a Tiendanube y AdministraNET.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        config_type = request.POST.get('config_type')
        config_data = request.POST.get('config_data', {})
        
        if config_type == 'tiendanube':
            # Probar conexión a Tiendanube
            from .services.tiendanube_service import TiendanubeService
            
            service = TiendanubeService(
                store_id=config_data.get('store_id'),
                access_token=config_data.get('access_token'),
                api_url=config_data.get('api_url', 'https://api.tiendanube.com/v1')
            )
            
            success, message = service.test_connection()
            
            return JsonResponse({
                'success': success,
                'message': message,
                'platform': 'tiendanube'
            })
            
        elif config_type == 'adminet':
            # Probar conexión a AdministraNET
            from .services.adminet_service import AdministraNETService
            
            service = AdministraNETService(
                host=config_data.get('host'),
                port=config_data.get('port', 3306),
                database=config_data.get('database'),
                user=config_data.get('user'),
                password=config_data.get('password')
            )
            
            success, message = service.test_connection()
            
            return JsonResponse({
                'success': success,
                'message': message,
                'platform': 'adminet'
            })
            
        else:
            return JsonResponse({
                'success': False,
                'error': 'Tipo de configuración no válido'
            })
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': f'Error al probar conexión: {str(e)}'
        })


# Vistas faltantes para completar el menú
class ProductMappingListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
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


class ProductMappingCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
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


class ProductMappingUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
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


class ProductMappingDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
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


class ProductMappingDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
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


class OrderMappingListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
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


class OrderMappingCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
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


class OrderMappingUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
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


class OrderMappingDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
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


class OrderMappingDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
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


class ManualSyncView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
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


class SyncHistoryView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
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


class StatusView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
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
                    from .services.tiendanube_service import TiendanubeService
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
                    from .services.adminet_service import AdministraNETService
                    adminet_service = AdministraNETService(adminet_config)
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
        
        # Estadísticas de sincronización
        context['successful_syncs'] = SyncLog.objects.filter(status='success').count()
        context['failed_syncs'] = SyncLog.objects.filter(status='error').count()
        context['pending_syncs'] = SyncLog.objects.filter(status='pending').count()
        
        # Última sincronización
        last_sync = SyncLog.objects.filter(status='success').order_by('-started_at').first()
        context['last_sync'] = last_sync
        
        # Webhooks
        try:
            from .models import WebhookEvent
            context['total_webhook_events'] = WebhookEvent.objects.count()
            context['recent_webhook_events'] = WebhookEvent.objects.order_by('-received_at')[:5]
        except:
            context['total_webhook_events'] = 0
            context['recent_webhook_events'] = []
        
        return context


@login_required
@permission_required('tiendanube_administranet.change_administraNETconfig')
def test_adminet_connection_ajax(request):
    """
    Vista AJAX para probar conexión específica a AdministraNET.
    """
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': _('Invalid request method')})
    
    try:
        # Obtener datos del formulario
        host = request.POST.get('host', '').strip()
        port = request.POST.get('port', '3306').strip()
        database = request.POST.get('database', '').strip()
        user = request.POST.get('user', '').strip()
        password = request.POST.get('password', '').strip()
        
        # Validar campos requeridos
        if not all([host, database, user, password]):
            return JsonResponse({
                'success': False,
                'message': _('Please fill in all required fields: host, database, user, and password')
            })
        
        # Crear configuración temporal para la prueba
        temp_config = AdministraNETConfig(
            name='Test Connection',
            host=host,
            port=int(port) if port.isdigit() else 3306,
            database=database,
            user=user,
            password=password,
            is_active=False  # No guardar esta configuración
        )
        
        # Probar conexión
        from .services.adminet_service import AdministraNETService
        service = AdministraNETService(temp_config)
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
        api_url = request.POST.get('api_url', 'https://api.tiendanube.com/v1').strip()
        
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
        from .services.tiendanube_service import TiendanubeService
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
        if sync_type not in ['customers', 'products', 'orders']:
            return JsonResponse({
                'success': False,
                'message': _('Invalid sync type. Must be customers, products, or orders')
            })
        
        if direction not in ['tiendanube', 'adminet']:
            return JsonResponse({
                'success': False,
                'message': _('Invalid direction. Must be tiendanube or adminet')
            })
        
        # Validar restricciones de sincronización
        if sync_type == 'products' and direction == 'tiendanube':
            return JsonResponse({
                'success': False,
                'message': _('Product synchronization from Tiendanube to AdministraNET is not allowed')
            })
        
        # Obtener configuraciones activas
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config or not adminet_config:
            return JsonResponse({
                'success': False,
                'message': _('Active configurations not found. Please configure Tiendanube and AdministraNET first.')
            })
        
        # Crear servicio de sincronización
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        # Ejecutar sincronización según el tipo y dirección
        if sync_type == 'customers':
            if direction == 'tiendanube':
                result = sync_service.sync_customers_from_tiendanube()
            else:
                result = sync_service.sync_customers_from_adminet()
        elif sync_type == 'products':
            if direction == 'tiendanube':
                result = sync_service.sync_products_from_tiendanube()
            else:
                result = sync_service.sync_products_from_adminet()
        elif sync_type == 'orders':
            if direction == 'tiendanube':
                result = sync_service.sync_orders_from_tiendanube()
            else:
                result = sync_service.sync_orders_from_adminet()
        
        if result.get('success'):
            return JsonResponse({
                'success': True,
                'message': _('Synchronization completed successfully'),
                'details': result.get('details', {})
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result.get('error', _('Synchronization failed'))
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

class WebhookConfigListView(ListView):
    """
    Vista para listar configuraciones de webhooks.
    """
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


class WebhookConfigCreateView(CreateView):
    """
    Vista para crear nueva configuración de webhook.
    """
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


class WebhookConfigUpdateView(UpdateView):
    """
    Vista para actualizar configuración de webhook.
    """
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


class WebhookConfigDeleteView(DeleteView):
    """
    Vista para eliminar configuración de webhook.
    """
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


class WebhookConfigDetailView(DetailView):
    """
    Vista para mostrar detalles de configuración de webhook.
    """
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


class WebhookEventListView(ListView):
    """
    Vista para listar eventos de webhook.
    """
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


class WebhookEventDetailView(DetailView):
    """
    Vista para mostrar detalles de evento de webhook.
    """
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
                    local_webhook.events = tiendanube_webhook.get('events', [])
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
        # Obtener datos del request
        payload = request.body.decode('utf-8')
        headers = dict(request.headers)
        
        # Buscar configuración de webhook por URL
        webhook_url = request.build_absolute_uri()
        webhook_config = WebhookConfig.objects.filter(
            webhook_url=webhook_url,
            is_active=True
        ).first()
        
        if not webhook_config:
            logger.warning(f"No webhook configuration found for URL: {webhook_url}")
            return JsonResponse({'error': 'Webhook not found'}, status=404)
        
        # Verificar firma si está configurada
        signature = headers.get('X-Tiendanube-Signature', '')
        if webhook_config.webhook_secret:
            from ..services.webhook_service import WebhookProcessor
            if not WebhookProcessor.verify_signature(payload, signature, webhook_config.webhook_secret):
                logger.warning(f"Invalid webhook signature for URL: {webhook_url}")
                return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        # Parsear payload JSON
        try:
            event_data = json.loads(payload)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON payload: {str(e)}")
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        # Procesar evento
        from ..services.webhook_processor import WebhookProcessor
        from ..models import AdministraNETConfig
        
        # Obtener configuración de AdministraNET
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        if not adminet_config:
            return JsonResponse({'error': 'AdministraNET configuration not found'}, status=500)
        
        # Crear procesador de webhook
        processor = WebhookProcessor(webhook_config.tiendanube_config, adminet_config)
        
        # Crear request mock para el procesador
        from django.test import RequestFactory
        factory = RequestFactory()
        mock_request = factory.post('/webhook/', data=json.dumps(event_data), content_type='application/json')
        mock_request.headers = headers
        
        result = processor.process_webhook(mock_request)
        
        if result['success']:
            return JsonResponse({'status': 'success'}, status=200)
        else:
            logger.error(f"Webhook processing failed: {result.get('error')}")
            return JsonResponse({'error': 'Processing failed'}, status=500)
            
    except Exception as e:
        logger.error(f"Error in webhook endpoint: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


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
                'message': 'Query de búsqueda requerida'
            })
        
        # Obtener configuración activa
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'message': 'No hay configuración activa de Tiendanube'
            })
        
        # Buscar clientes
        service = TiendanubeService(tiendanube_config)
        result = service.search_customers(query, limit=20)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'customers': result['customers'],
                'total': result['total'],
                'query': query
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result['message']
            })
            
    except Exception as e:
        logger.error(f"Error searching customers: {e}")
        return JsonResponse({
            'success': False,
            'message': f'Error buscando clientes: {str(e)}'
        })


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

# ============================================================================
# VISTAS DE PRODUCTOS Y VARIANTES
# ============================================================================

@login_required
@permission_required('tiendanube_administranet.view_productmapping')
def product_list(request):
    """Vista para listar productos mapeados."""
    try:
        # Obtener filtros
        search = request.GET.get('search', '')
        status = request.GET.get('status', '')
        sync_enabled = request.GET.get('sync_enabled', '')
        
        # Query base
        products = ProductMapping.objects.all()
        
        # Aplicar filtros
        if search:
            products = products.filter(
                Q(tiendanube_name__icontains=search) |
                Q(adminet_nombre__icontains=search) |
                Q(tiendanube_sku__icontains=search) |
                Q(adminet_codigo_articulo__icontains=search)
            )
        
        if status:
            products = products.filter(sync_status=status)
        
        if sync_enabled:
            products = products.filter(sync_enabled=sync_enabled == 'true')
        
        # Ordenar
        products = products.order_by('-created_at')
        
        # Paginación
        paginator = Paginator(products, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Estadísticas
        stats = {
            'total': ProductMapping.objects.count(),
            'synced': ProductMapping.objects.filter(sync_status=ProductMapping.SyncStatus.SYNCED).count(),
            'pending': ProductMapping.objects.filter(sync_status=ProductMapping.SyncStatus.PENDING).count(),
            'error': ProductMapping.objects.filter(sync_status=ProductMapping.SyncStatus.ERROR).count(),
        }
        
        context = {
            'page_obj': page_obj,
            'stats': stats,
            'search': search,
            'status': status,
            'sync_enabled': sync_enabled,
        }
        
        return render(request, 'tiendanube_administranet/products/product_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in product_list: {e}")
        # Usar contexto para pasar el error en lugar de messages
        context = {
            'error_message': f'Error cargando productos: {str(e)}',
            'page_obj': [],
            'stats': {'total': 0, 'synced': 0, 'pending': 0, 'error': 0},
            'search': '',
            'status': '',
            'sync_enabled': '',
        }
        return render(request, 'tiendanube_administranet/products/product_list.html', context)


@login_required
@permission_required('tiendanube_administranet.add_productmapping')
def product_create(request):
    """Vista para crear nuevo mapeo de producto."""
    if request.method == 'POST':
        form = ProductMappingForm(request.POST)
        if form.is_valid():
            try:
                product = form.save()
                messages.success(request, 'Producto creado exitosamente.')
                return redirect('tiendanube_administranet:product_detail', product_id=product.id)
            except Exception as e:
                logger.error(f"Error creating product: {e}")
                messages.error(request, f'Error creando producto: {str(e)}')
    else:
        form = ProductMappingForm()
    
    context = {
        'form': form,
        'title': 'Crear Producto',
        'action': 'Crear'
    }
    return render(request, 'tiendanube_administranet/products/product_form.html', context)


@login_required
@permission_required('tiendanube_administranet.view_productmapping')
def product_detail(request, product_id):
    """Vista para ver detalles de un producto."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        variants = ProductVariantMapping.objects.filter(product_mapping=product)
        
        context = {
            'product': product,
            'variants': variants,
        }
        return render(request, 'tiendanube_administranet/products/product_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error in product_detail: {e}")
        messages.error(request, f'Error cargando producto: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.change_productmapping')
def product_edit(request, product_id):
    """Vista para editar un producto."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        if request.method == 'POST':
            form = ProductMappingForm(request.POST, instance=product)
            if form.is_valid():
                form.save()
                messages.success(request, 'Producto actualizado exitosamente.')
                return redirect('tiendanube_administranet:product_detail', product_id=product.id)
        else:
            form = ProductMappingForm(instance=product)
        
        context = {
            'form': form,
            'product': product,
            'title': 'Editar Producto',
            'action': 'Actualizar'
        }
        return render(request, 'tiendanube_administranet/products/product_form.html', context)
        
    except Exception as e:
        logger.error(f"Error in product_edit: {e}")
        messages.error(request, f'Error editando producto: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.delete_productmapping')
def product_delete(request, product_id):
    """Vista para eliminar un producto."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        if request.method == 'POST':
            product.delete()
            messages.success(request, 'Producto eliminado exitosamente.')
            return redirect('tiendanube_administranet:product_list')
        
        context = {
            'product': product,
        }
        return render(request, 'tiendanube_administranet/products/product_confirm_delete.html', context)
        
    except Exception as e:
        logger.error(f"Error in product_delete: {e}")
        messages.error(request, f'Error eliminando producto: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.change_productmapping')
def product_sync(request, product_id):
    """Vista AJAX para sincronizar un producto específico."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config or not adminet_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuraciones de Tiendanube o AdministraNET no encontradas'
            })
        
        # Crear servicio de sincronización
        from .services.sync_service import TiendanubeAdministraNETSyncService
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        # Determinar dirección de sincronización
        sync_direction = request.POST.get('direction', 'both')
        
        if sync_direction == 'to_adminet' or sync_direction == 'both':
            # Sincronizar desde Tiendanube hacia AdministraNET
            if product.tiendanube_id:
                result = sync_service.sync_products_from_tiendanube()
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'El producto no tiene ID de Tiendanube para sincronizar'
                })
        
        elif sync_direction == 'from_adminet':
            # Sincronizar desde AdministraNET hacia Tiendanube
            if product.adminet_id:
                result = sync_service.sync_products_from_adminet()
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'El producto no tiene ID de AdministraNET para sincronizar'
                })
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in product_sync: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error en sincronización: {str(e)}'
        })


@login_required
@permission_required('tiendanube_administranet.change_productmapping')
def product_sync_all(request):
    """Vista AJAX para sincronizar todos los productos."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config or not adminet_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuraciones de Tiendanube o AdministraNET no encontradas'
            })
        
        # Crear servicio de sincronización
        from .services.sync_service import TiendanubeAdministraNETSyncService
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        # Determinar dirección de sincronización
        sync_direction = request.POST.get('direction', 'both')
        
        if sync_direction == 'to_adminet' or sync_direction == 'both':
            result = sync_service.sync_products_from_tiendanube()
        elif sync_direction == 'from_adminet':
            result = sync_service.sync_products_from_adminet()
        else:
            return JsonResponse({
                'success': False,
                'error': 'Dirección de sincronización no válida'
            })
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in product_sync_all: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error en sincronización: {str(e)}'
        })


@login_required
@permission_required('tiendanube_administranet.add_productmapping')
def product_import_from_tiendanube(request):
    """Vista AJAX para importar productos desde Tiendanube."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        # Obtener configuración de Tiendanube
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuración de Tiendanube no encontrada'
            })
        
        # Crear servicio de productos
        from .services.product_service import TiendanubeProductService
        product_service = TiendanubeProductService(tiendanube_config)
        
        # Obtener productos de Tiendanube
        result = product_service.get_products(limit=100)
        
        if not result['success']:
            return JsonResponse(result)
        
        products = result['products']
        imported_count = 0
        error_count = 0
        
        for product_data in products:
            try:
                # Verificar si ya existe
                existing = ProductMapping.objects.filter(tiendanube_id=product_data['id']).first()
                if existing:
                    continue
                
                # Crear nuevo mapeo
                ProductMapping.objects.create(
                    tiendanube_id=product_data['id'],
                    tiendanube_name=product_data.get('name', ''),
                    tiendanube_sku=product_data.get('sku', ''),
                    tiendanube_price=float(product_data.get('price', 0)),
                    tiendanube_stock=int(product_data.get('stock', 0)),
                    tiendanube_config=tiendanube_config,
                    sync_status=ProductMapping.SyncStatus.PENDING
                )
                imported_count += 1
                
            except Exception as e:
                logger.error(f"Error importing product {product_data.get('id')}: {e}")
                error_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Importación completada: {imported_count} productos importados, {error_count} errores',
            'imported_count': imported_count,
            'error_count': error_count
        })
        
    except Exception as e:
        logger.error(f"Error in product_import_from_tiendanube: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error en importación: {str(e)}'
        })


# ============================================================================
# VISTAS DE VARIANTES
# ============================================================================

@login_required
@permission_required('tiendanube_administranet.view_productvariantmapping')
def variant_list(request, product_id):
    """Vista para listar variantes de un producto."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        variants = ProductVariantMapping.objects.filter(product_mapping=product).order_by('-created_at')
        
        context = {
            'product': product,
            'variants': variants,
        }
        return render(request, 'tiendanube_administranet/products/variant_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in variant_list: {e}")
        messages.error(request, f'Error cargando variantes: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.add_productvariantmapping')
def variant_create(request, product_id):
    """Vista para crear nueva variante."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        if request.method == 'POST':
            form = ProductVariantMappingForm(request.POST)
            if form.is_valid():
                variant = form.save(commit=False)
                variant.product_mapping = product
                variant.save()
                messages.success(request, 'Variante creada exitosamente.')
                return redirect('tiendanube_administranet:variant_list', product_id=product.id)
        else:
            form = ProductVariantMappingForm()
        
        context = {
            'form': form,
            'product': product,
            'title': 'Crear Variante',
            'action': 'Crear'
        }
        return render(request, 'tiendanube_administranet/products/variant_form.html', context)
        
    except Exception as e:
        logger.error(f"Error in variant_create: {e}")
        messages.error(request, f'Error creando variante: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.change_productvariantmapping')
def variant_edit(request, variant_id):
    """Vista para editar una variante."""
    try:
        variant = get_object_or_404(ProductVariantMapping, id=variant_id)
        
        if request.method == 'POST':
            form = ProductVariantMappingForm(request.POST, instance=variant)
            if form.is_valid():
                form.save()
                messages.success(request, 'Variante actualizada exitosamente.')
                return redirect('tiendanube_administranet:variant_list', product_id=variant.product_mapping.id)
        else:
            form = ProductVariantMappingForm(instance=variant)
        
        context = {
            'form': form,
            'variant': variant,
            'product': variant.product_mapping,
            'title': 'Editar Variante',
            'action': 'Actualizar'
        }
        return render(request, 'tiendanube_administranet/products/variant_form.html', context)
        
    except Exception as e:
        logger.error(f"Error in variant_edit: {e}")
        messages.error(request, f'Error editando variante: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.delete_productvariantmapping')
def variant_delete(request, variant_id):
    """Vista para eliminar una variante."""
    try:
        variant = get_object_or_404(ProductVariantMapping, id=variant_id)
        product_id = variant.product_mapping.id
        
        if request.method == 'POST':
            variant.delete()
            messages.success(request, 'Variante eliminada exitosamente.')
            return redirect('tiendanube_administranet:variant_list', product_id=product_id)
        
        context = {
            'variant': variant,
            'product': variant.product_mapping,
        }
        return render(request, 'tiendanube_administranet/products/variant_confirm_delete.html', context)
        
    except Exception as e:
        logger.error(f"Error in variant_delete: {e}")
        messages.error(request, f'Error eliminando variante: {str(e)}')
        return redirect('tiendanube_administranet:product_list')


@login_required
@permission_required('tiendanube_administranet.change_productvariantmapping')
def variant_sync(request, variant_id):
    """Vista AJAX para sincronizar una variante específica."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        variant = get_object_or_404(ProductVariantMapping, id=variant_id)
        
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config or not adminet_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuraciones de Tiendanube o AdministraNET no encontradas'
            })
        
        # Crear servicio de sincronización
        from .services.sync_service import TiendanubeAdministraNETSyncService
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        # Sincronizar variantes del producto
        result = sync_service.sync_product_variants_from_tiendanube(variant.product_mapping)
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in variant_sync: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error en sincronización: {str(e)}'
        })


# ============================================================================
# VISTAS DE CATEGORÍAS
# ============================================================================

@login_required
@permission_required('tiendanube_administranet.view_productcategorymapping')
def category_list(request):
    """Vista para listar categorías mapeadas."""
    try:
        categories = ProductCategoryMapping.objects.all().order_by('-created_at')
        
        # Paginación
        paginator = Paginator(categories, 20)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context = {
            'page_obj': page_obj,
        }
        return render(request, 'tiendanube_administranet/products/category_list.html', context)
        
    except Exception as e:
        logger.error(f"Error in category_list: {e}")
        messages.error(request, f'Error cargando categorías: {str(e)}')
        return redirect('tiendanube_administranet:dashboard')


@login_required
@permission_required('tiendanube_administranet.add_productcategorymapping')
def category_import_from_tiendanube(request):
    """Vista AJAX para importar categorías desde Tiendanube."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        # Obtener configuración de Tiendanube
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        if not tiendanube_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuración de Tiendanube no encontrada'
            })
        
        # Crear servicio de productos
        from .services.product_service import TiendanubeProductService
        product_service = TiendanubeProductService(tiendanube_config)
        
        # Obtener categorías de Tiendanube
        result = product_service.get_categories()
        
        if not result['success']:
            return JsonResponse(result)
        
        categories = result['categories']
        imported_count = 0
        error_count = 0
        
        for category_data in categories:
            try:
                # Verificar si ya existe
                existing = ProductCategoryMapping.objects.filter(tiendanube_id=category_data['id']).first()
                if existing:
                    continue
                
                # Crear nuevo mapeo
                ProductCategoryMapping.objects.create(
                    tiendanube_id=category_data['id'],
                    tiendanube_name=category_data.get('name', ''),
                    tiendanube_handle=category_data.get('handle', ''),
                    tiendanube_description=category_data.get('description', ''),
                    tiendanube_parent_id=category_data.get('parent_id'),
                    tiendanube_image=category_data.get('image', ''),
                    sync_status=ProductCategoryMapping.SyncStatus.PENDING
                )
                imported_count += 1
                
            except Exception as e:
                logger.error(f"Error importing category {category_data.get('id')}: {e}")
                error_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Importación completada: {imported_count} categorías importadas, {error_count} errores',
            'imported_count': imported_count,
            'error_count': error_count
        })
        
    except Exception as e:
        logger.error(f"Error in category_import_from_tiendanube: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Error en importación: {str(e)}'
        })


# ============================================================================
# APIs
# ============================================================================

@login_required
@permission_required('tiendanube_administranet.view_productmapping')
def api_products(request):
    """API para obtener productos."""
    try:
        products = ProductMapping.objects.all()
        
        # Filtros
        search = request.GET.get('search', '')
        if search:
            products = products.filter(
                Q(tiendanube_name__icontains=search) |
                Q(adminet_nombre__icontains=search)
            )
        
        # Serializar
        data = []
        for product in products[:50]:  # Límite de 50
            data.append({
                'id': product.id,
                'tiendanube_id': product.tiendanube_id,
                'tiendanube_name': product.tiendanube_name,
                'tiendanube_sku': product.tiendanube_sku,
                'tiendanube_price': float(product.tiendanube_price) if product.tiendanube_price else 0,
                'tiendanube_stock': product.tiendanube_stock,
                'adminet_id': product.adminet_id,
                'adminet_nombre': product.adminet_nombre,
                'adminet_codigo_articulo': product.adminet_codigo_articulo,
                'sync_status': product.sync_status,
                'sync_enabled': product.sync_enabled,
                'last_synced': product.last_synced.isoformat() if product.last_synced else None,
            })
        
        return JsonResponse({
            'success': True,
            'products': data,
            'total': len(data)
        })
        
    except Exception as e:
        logger.error(f"Error in api_products: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@permission_required('tiendanube_administranet.view_productmapping')
def api_product_detail(request, product_id):
    """API para obtener detalles de un producto."""
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        data = {
            'id': product.id,
            'tiendanube_id': product.tiendanube_id,
            'tiendanube_name': product.tiendanube_name,
            'tiendanube_handle': product.tiendanube_handle,
            'tiendanube_description': product.tiendanube_description,
            'tiendanube_sku': product.tiendanube_sku,
            'tiendanube_price': float(product.tiendanube_price) if product.tiendanube_price else 0,
            'tiendanube_compare_at_price': float(product.tiendanube_compare_at_price) if product.tiendanube_compare_at_price else 0,
            'tiendanube_cost': float(product.tiendanube_cost) if product.tiendanube_cost else 0,
            'tiendanube_stock': product.tiendanube_stock,
            'tiendanube_weight': float(product.tiendanube_weight) if product.tiendanube_weight else 0,
            'tiendanube_width': float(product.tiendanube_width) if product.tiendanube_width else 0,
            'tiendanube_height': float(product.tiendanube_height) if product.tiendanube_height else 0,
            'tiendanube_depth': float(product.tiendanube_depth) if product.tiendanube_depth else 0,
            'tiendanube_free_shipping': product.tiendanube_free_shipping,
            'tiendanube_published': product.tiendanube_published,
            'tiendanube_featured': product.tiendanube_featured,
            'tiendanube_product_type': product.tiendanube_product_type,
            'tiendanube_categories': product.tiendanube_categories,
            'tiendanube_images': product.tiendanube_images,
            'tiendanube_videos': product.tiendanube_videos,
            'tiendanube_seo_title': product.tiendanube_seo_title,
            'tiendanube_seo_description': product.tiendanube_seo_description,
            'tiendanube_created_at': product.tiendanube_created_at.isoformat() if product.tiendanube_created_at else None,
            'tiendanube_updated_at': product.tiendanube_updated_at.isoformat() if product.tiendanube_updated_at else None,
            'adminet_id': product.adminet_id,
            'adminet_id_manual': product.adminet_id_manual,
            'adminet_codigo_articulo': product.adminet_codigo_articulo,
            'adminet_nombre': product.adminet_nombre,
            'adminet_detalle': product.adminet_detalle,
            'adminet_precio_costo': float(product.adminet_precio_costo) if product.adminet_precio_costo else 0,
            'adminet_precio_1v': float(product.adminet_precio_1v) if product.adminet_precio_1v else 0,
            'adminet_stock': product.adminet_stock,
            'adminet_codigo_barra': product.adminet_codigo_barra,
            'adminet_ecommerce': product.adminet_ecommerce,
            'adminet_disponible_venta': product.adminet_disponible_venta,
            'sync_status': product.sync_status,
            'sync_enabled': product.sync_enabled,
            'sync_price': product.sync_price,
            'sync_stock': product.sync_stock,
            'sync_description': product.sync_description,
            'sync_images': product.sync_images,
            'error_message': product.error_message,
            'last_synced': product.last_synced.isoformat() if product.last_synced else None,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat(),
        }
        
        return JsonResponse({
            'success': True,
            'product': data
        })
        
    except Exception as e:
        logger.error(f"Error in api_product_detail: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
@permission_required('tiendanube_administranet.change_productmapping')
def api_product_sync(request, product_id):
    """API para sincronizar un producto."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Método no permitido'})
    
    try:
        product = get_object_or_404(ProductMapping, id=product_id)
        
        # Obtener configuraciones
        tiendanube_config = TiendanubeConfig.objects.filter(is_active=True).first()
        adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
        
        if not tiendanube_config or not adminet_config:
            return JsonResponse({
                'success': False,
                'error': 'Configuraciones de Tiendanube o AdministraNET no encontradas'
            })
        
        # Crear servicio de sincronización
        from .services.sync_service import TiendanubeAdministraNETSyncService
        sync_service = TiendanubeAdministraNETSyncService(tiendanube_config, adminet_config)
        
        # Sincronizar
        sync_direction = request.POST.get('direction', 'both')
        
        if sync_direction == 'to_adminet' or sync_direction == 'both':
            result = sync_service.sync_products_from_tiendanube()
        elif sync_direction == 'from_adminet':
            result = sync_service.sync_products_from_adminet()
        else:
            return JsonResponse({
                'success': False,
                'error': 'Dirección de sincronización no válida'
            })
        
        return JsonResponse(result)
        
    except Exception as e:
        logger.error(f"Error in api_product_sync: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        })

# =============================================================================
# TIENDANUBE CONFIGURATION VIEWS
# =============================================================================

class TiendanubeConfigListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar configuraciones de Tiendanube.
    """
    model = TiendanubeConfig
    template_name = 'tiendanube_administranet/tiendanube_config_list.html'
    context_object_name = 'configs'
    permission_required = 'tiendanube_administranet.view_tiendanubeconfig'
    paginate_by = 20

    def get_queryset(self):
        return TiendanubeConfig.objects.all().order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Agregar estadísticas de estado de configuración
        config_statuses = {}
        for config in context['configs']:
            # Aquí podrías agregar lógica para verificar el estado de cada configuración
            config_statuses[config.pk] = {
                'active': config.is_active,
                'message': 'Configuration is active' if config.is_active else 'Configuration is inactive'
            }
        context['config_statuses'] = config_statuses
        return context


class TiendanubeConfigCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Vista para crear nueva configuración de Tiendanube.
    """
    model = TiendanubeConfig
    form_class = TiendanubeConfigForm
    template_name = 'tiendanube_administranet/tiendanube_config_form.html'
    permission_required = 'tiendanube_administranet.add_tiendanubeconfig'
    success_url = reverse_lazy('tiendanube_administranet:tiendanube_config_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Tiendanube configuration created successfully.'))
        return response

    def form_invalid(self, form):
        messages.error(self.request, _('Error creating Tiendanube configuration. Please check the form.'))
        return super().form_invalid(form)


class TiendanubeConfigUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Vista para actualizar configuración de Tiendanube.
    """
    model = TiendanubeConfig
    form_class = TiendanubeConfigForm
    template_name = 'tiendanube_administranet/tiendanube_config_form.html'
    permission_required = 'tiendanube_administranet.change_tiendanubeconfig'
    success_url = reverse_lazy('tiendanube_administranet:tiendanube_config_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Tiendanube configuration updated successfully.'))
        return response

    def form_invalid(self, form):
        messages.error(self.request, _('Error updating Tiendanube configuration. Please check the form.'))
        return super().form_invalid(form)


class TiendanubeConfigDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Vista para eliminar configuración de Tiendanube.
    """
    model = TiendanubeConfig
    template_name = 'tiendanube_administranet/tiendanube_config_confirm_delete.html'
    permission_required = 'tiendanube_administranet.delete_tiendanubeconfig'
    success_url = reverse_lazy('tiendanube_administranet:tiendanube_config_list')

    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Tiendanube configuration deleted successfully.'))
        return super().delete(request, *args, **kwargs)


class TiendanubeConfigWizardCallbackView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """
    Vista de callback para el wizard de configuración de Tiendanube.
    """
    permission_required = 'tiendanube_administranet.add_tiendanubeconfig'
    
    def get(self, request, *args, **kwargs):
        session = request.session
        code = request.GET.get('code')
        state = request.GET.get('state')
        
        logger.info(f"Tiendanube ADMINET callback received - Code: {code[:10] if code else 'None'}..., State: {state}")
        logger.info(f"Request path: {request.path}")
        logger.info(f"Request GET params: {dict(request.GET)}")
        
        if code and state:
            session['wizard_code'] = code
            session['wizard_state'] = state
            session['wizard_step'] = 4
            logger.info("Authorization code saved to session successfully")
            # Usar session para mensajes en lugar del framework de mensajes
            session['wizard_message'] = 'Authorization code received successfully!'
            session['wizard_message_type'] = 'success'
        else:
            logger.error(f"Authorization failed - Code: {code}, State: {state}")
            session['wizard_message'] = 'Authorization failed. Please try again.'
            session['wizard_message_type'] = 'error'
        
        redirect_url = f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=4"
        logger.info(f"Redirecting to: {redirect_url}")
        return redirect(redirect_url)


class TiendanubeConfigWizardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista para el wizard de configuración de Tiendanube.
    """
    template_name = 'tiendanube_administranet/tiendanube_config_wizard.html'
    permission_required = 'tiendanube_administranet.add_tiendanubeconfig'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Obtener el paso actual del wizard
        step = int(self.request.GET.get('step', 1))
        context['step'] = step
        
        logger.info(f"Wizard step: {step}, Session data: {dict(self.request.session)}")
        
        # Manejar mensajes desde la sesión
        wizard_message = self.request.session.pop('wizard_message', None)
        wizard_message_type = self.request.session.pop('wizard_message_type', None)
        
        if wizard_message:
            context['wizard_message'] = wizard_message
            context['wizard_message_type'] = wizard_message_type
        
        # Definir los pasos del wizard
        context['wizard_steps'] = [
            _('Credentials'),
            _('Validation'),
            _('Authorization'),
            _('Token'),
            _('Preferences'),
            _('Summary')
        ]
        
        # Configurar datos según el paso
        if step == 1:
            # Paso 1: Credenciales
            context['app_id'] = self.request.session.get('wizard_app_id', '')
            context['client_secret'] = self.request.session.get('wizard_client_secret', '')
            context['redirect_uri'] = self.request.build_absolute_uri(reverse('tiendanube_administranet:tiendanube_config_wizard_callback'))
            
        elif step == 3:
            # Paso 3: Autorización
            app_id = self.request.session.get('wizard_app_id')
            client_secret = self.request.session.get('wizard_client_secret')
            if app_id and client_secret:
                # Generar URL de autorización
                state = self.request.session.get('wizard_state', '')
                redirect_uri = self.request.build_absolute_uri(reverse('tiendanube_administranet:tiendanube_config_wizard_callback'))
                # Asegurar que la URL sea HTTPS
                redirect_uri = redirect_uri.replace('http://', 'https://')
                context['auth_url'] = f"https://www.tiendanube.com/apps/{app_id}/authorize?response_type=code&client_id={app_id}&redirect_uri={redirect_uri}&state={state}"
                context['redirect_uri'] = redirect_uri
                context['state'] = state
                
                logger.info(f"Step 3 - App ID: {app_id}, State: {state}")
                logger.info(f"Step 3 - Auth URL: {context['auth_url']}")
                logger.info(f"Step 3 - Redirect URI: {context['redirect_uri']}")
                
        elif step == 4:
            # Paso 4: Token
            access_token = self.request.session.get('wizard_access_token')
            user_id = self.request.session.get('wizard_user_id')
            wizard_code = self.request.session.get('wizard_code')
            
            # Agregar código de autorización al contexto
            context['wizard_code'] = wizard_code
            
            # Solo mostrar datos si realmente tenemos un token válido
            if access_token and user_id and not access_token.startswith('sample_'):
                context['access_token'] = access_token
                context['user_id'] = user_id
                context['token_obtained'] = True
            else:
                context['access_token'] = None
                context['user_id'] = None
                context['token_obtained'] = False
            
        elif step == 5:
            # Paso 5: Preferencias
            context['auto_sync'] = self.request.session.get('wizard_auto_sync', True)
            context['sync_interval'] = self.request.session.get('wizard_sync_interval', 30)
            context['sync_products'] = self.request.session.get('wizard_sync_products', True)
            context['sync_stock'] = self.request.session.get('wizard_sync_stock', True)
            
            # Verificar que tenemos los datos necesarios para continuar
            access_token = self.request.session.get('wizard_access_token')
            user_id = self.request.session.get('wizard_user_id')
            if not access_token or not user_id:
                context['wizard_error'] = 'No se pudo obtener la autorización de Tiendanube. Por favor, completa el proceso de autorización antes de continuar.'
            
        elif step == 6:
            # Paso 6: Resumen
            access_token = self.request.session.get('wizard_access_token')
            user_id = self.request.session.get('wizard_user_id')
            
            # Verificar que tenemos los datos necesarios
            if not access_token or not user_id:
                context['wizard_error'] = 'No se pudo obtener la autorización de Tiendanube. Por favor, completa el proceso de autorización antes de continuar.'
            else:
                # Verificar si ya existe la tienda en Synap
                if TiendanubeConfig.objects.filter(store_id=user_id).exists():
                    context['wizard_error'] = 'This store is already registered in Synap.'
                else:
                    context['summary'] = {
                        'app_id': self.request.session.get('wizard_app_id'),
                        'user_id': user_id,
                        'access_token': access_token[:20] + '...' + access_token[-10:] if access_token else 'N/A',
                        'scopes': self.request.session.get('wizard_scopes', []),
                        'auto_sync': self.request.session.get('wizard_auto_sync', True),
                        'sync_interval': self.request.session.get('wizard_sync_interval', 30),
                        'sync_products': self.request.session.get('wizard_sync_products', True),
                        'sync_stock': self.request.session.get('wizard_sync_stock', True),
                    }
                    # Obtener datos de la tienda si están disponibles
            context['tienda_data'] = self.request.session.get('wizard_tienda_data')
            
        return context

    def post(self, request, *args, **kwargs):
        step = int(request.GET.get('step', 1))
        
        if step == 1:
            # Procesar credenciales
            app_id = request.POST.get('app_id')
            client_secret = request.POST.get('client_secret')
            
            if app_id and client_secret:
                request.session['wizard_app_id'] = app_id
                request.session['wizard_client_secret'] = client_secret
                request.session['wizard_state'] = str(uuid.uuid4())
                return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=3")
            else:
                messages.error(request, _('Please provide both App ID and Client Secret.'))
                return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=1")
                
        elif step == 4:
            # Obtener token de acceso
            if 'get_token' in request.POST:
                # Intercambiar código de autorización por access token
                app_id = request.session.get('wizard_app_id')
                client_secret = request.session.get('wizard_client_secret')
                code = request.session.get('wizard_code')
                redirect_uri = request.build_absolute_uri(reverse('tiendanube_administranet:tiendanube_config_wizard_callback'))
                redirect_uri = redirect_uri.replace('http://', 'https://')
                
                data = {
                    'client_id': app_id,
                    'client_secret': client_secret,
                    'grant_type': 'authorization_code',
                    'code': code,
                    'redirect_uri': redirect_uri
                }
                
                logger.info(f"Tiendanube token exchange - App ID: {app_id}")
                logger.info(f"Tiendanube token exchange - Code: {code[:10] if code else 'None'}...")
                logger.info(f"Tiendanube token exchange - Redirect URI: {redirect_uri}")
                
                try:
                    response = requests.post(
                        'https://www.tiendanube.com/apps/authorize/token',
                        json=data,
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    )
                    
                    logger.info(f"Tiendanube token exchange - Response status: {response.status_code}")
                    logger.info(f"Tiendanube token exchange - Response text: {response.text}")
                    
                    if response.status_code == 200:
                        token_data = response.json()
                        access_token = token_data.get('access_token')
                        user_id = token_data.get('user_id')
                        
                        if access_token:
                            # El user_id de la respuesta OAuth es el installation_id
                            # Necesitamos usar la API de Partners para obtener el store_id real
                            from ..services.partners_service import TiendaNubePartnersService
                            
                            partners_service = TiendaNubePartnersService()
                            partners_result = partners_service.get_store_id_from_installation(user_id)
                            
                            if partners_result['success']:
                                final_store_id = partners_result['store_id']
                                logger.info(f"Store ID obtenido desde Partners API: {final_store_id}")
                                logger.info(f"Installation ID: {user_id} → Store ID: {final_store_id}")
                            else:
                                # Fallback: usar user_id como store_id (comportamiento anterior)
                                final_store_id = user_id
                                logger.warning(f"Error obteniendo store_id desde Partners API: {partners_result['message']}")
                                logger.warning(f"Usando user_id como fallback: {final_store_id}")
                            
                            request.session['wizard_access_token'] = access_token
                            request.session['wizard_user_id'] = final_store_id
                            request.session['wizard_message'] = 'Access token obtained successfully!'
                            request.session['wizard_message_type'] = 'success'
                            logger.info(f"Tiendanube token exchange - Success! Store ID: {final_store_id}")
                        else:
                            # Verificar si hay error en la respuesta
                            error = token_data.get('error')
                            error_description = token_data.get('error_description', 'Unknown error')
                            
                            if error == 'invalid_client':
                                request.session['wizard_message'] = 'Invalid App ID or Client Secret. Please check your credentials.'
                            elif error == 'invalid_grant':
                                request.session['wizard_message'] = 'Authorization code is invalid or expired. Please try the authorization process again.'
                            elif error == 'invalid_redirect_uri':
                                request.session['wizard_message'] = 'Redirect URI mismatch. Please check your app configuration.'
                            else:
                                request.session['wizard_message'] = f'Error from Tiendanube: {error_description}'
                            
                            request.session['wizard_message_type'] = 'error'
                            logger.error(f"Tiendanube token exchange - Error: {error} - {error_description}")
                    else:
                        # Manejar errores HTTP
                        if response.status_code == 400:
                            try:
                                error_data = response.json()
                                error = error_data.get('error')
                                error_description = error_data.get('error_description', 'Bad request')
                                
                                if error == 'invalid_client':
                                    request.session['wizard_message'] = 'Invalid App ID or Client Secret. Please check your credentials.'
                                elif error == 'invalid_grant':
                                    request.session['wizard_message'] = 'Authorization code is invalid or expired. Please try the authorization process again.'
                                elif error == 'invalid_redirect_uri':
                                    request.session['wizard_message'] = 'Redirect URI mismatch. Please check your app configuration.'
                                else:
                                    request.session['wizard_message'] = f'Error from Tiendanube: {error_description}'
                            except:
                                request.session['wizard_message'] = 'Invalid request to Tiendanube. Please check your configuration.'
                        elif response.status_code == 401:
                            request.session['wizard_message'] = 'Unauthorized. Please check your App ID and Client Secret.'
                        elif response.status_code == 403:
                            request.session['wizard_message'] = 'Access forbidden. Please check your app permissions.'
                        elif response.status_code >= 500:
                            request.session['wizard_message'] = 'Tiendanube service is temporarily unavailable. Please try again later.'
                        else:
                            request.session['wizard_message'] = f'Unexpected error from Tiendanube (HTTP {response.status_code})'
                        
                        request.session['wizard_message_type'] = 'error'
                        logger.error(f"Tiendanube token exchange - HTTP Error {response.status_code}: {response.text}")
                        
                except requests.exceptions.RequestException as e:
                    error_message = f'Network error: {str(e)}'
                    request.session['wizard_message'] = error_message
                    request.session['wizard_message_type'] = 'error'
                    logger.error(f"Tiendanube token exchange - Network error: {e}")
                except Exception as e:
                    error_message = f'Unexpected error: {str(e)}'
                    request.session['wizard_message'] = error_message
                    request.session['wizard_message_type'] = 'error'
                    logger.error(f"Tiendanube token exchange - Unexpected error: {e}")
                
                return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=4")
            elif 'continue_prefs' in request.POST:
                return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=5")
                
        elif step == 5:
            # Procesar preferencias
            request.session['wizard_auto_sync'] = 'auto_sync' in request.POST
            request.session['wizard_sync_interval'] = int(request.POST.get('sync_interval', 30))
            request.session['wizard_sync_products'] = 'sync_products' in request.POST
            request.session['wizard_sync_stock'] = 'sync_stock' in request.POST
            return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=6")
            
        elif step == 6:
            # Guardar configuración
            if 'save_store' in request.POST:
                try:
                    # Verificar que tenemos los datos necesarios
                    store_id = request.session.get('wizard_user_id')
                    access_token = request.session.get('wizard_access_token')
                    
                    if not store_id or not access_token:
                        request.session['wizard_message'] = 'No se pudo obtener la autorización de Tiendanube. Por favor, completa el proceso de autorización antes de continuar.'
                        request.session['wizard_message_type'] = 'error'
                        return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=6")
                    
                    # Verificar si ya existe la tienda en Synap
                    if TiendanubeConfig.objects.filter(store_id=store_id).exists():
                        request.session['wizard_message'] = 'This store is already registered in Synap.'
                        request.session['wizard_message_type'] = 'error'
                        return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=6")
                    
                    # Obtener datos de la tienda desde Tiendanube para el nombre
                    tienda_name = f"Store {store_id}"
                    try:
                        headers = {
                            'Content-Type': 'application/json',
                            'Authentication': f'bearer {access_token}',
                            'User-Agent': 'Synap-Tiendanube-Integration/1.0'
                        }
                        response = requests.get(
                            f'https://api.tiendanube.com/v1/{store_id}/store',
                            headers=headers,
                            timeout=10
                        )
                        if response.status_code == 200:
                            tienda_data = response.json()
                            tienda_name = tienda_data.get('name', f"Store {store_id}")
                            logger.info(f"Tiendanube store data retrieved: {tienda_name}")
                    except Exception as e:
                        logger.warning(f"Could not retrieve store data from Tiendanube: {e}")
                    
                    # Crear la configuración de Tiendanube
                    config = TiendanubeConfig.objects.create(
                        name=tienda_name,
                        store_id=store_id,
                        access_token=access_token,
                        api_url='https://api.tiendanube.com/v1',
                        is_active=request.session.get('wizard_auto_sync', True),
                    )
                    
                    logger.info(f"Tiendanube configuration created successfully: {config.name} (ID: {config.id})")
                    
                    # Limpiar datos de sesión
                    session_keys_to_clean = [
                        'wizard_app_id', 'wizard_client_secret', 'wizard_state', 
                        'wizard_access_token', 'wizard_user_id', 'wizard_auto_sync',
                        'wizard_sync_interval', 'wizard_sync_products', 'wizard_sync_stock',
                        'wizard_scopes', 'wizard_tienda_data',
                        'wizard_message', 'wizard_message_type'
                    ]
                    
                    for key in session_keys_to_clean:
                        request.session.pop(key, None)
                    
                    messages.success(request, _('Tiendanube store configuration completed successfully!'))
                    logger.info(f"Wizard completed successfully for store: {store_id}")
                    return redirect('tiendanube_administranet:tiendanube_config_list')
                    
                except Exception as e:
                    error_msg = f'Error saving configuration: {str(e)}'
                    logger.error(f"Wizard error: {error_msg}")
                    request.session['wizard_message'] = error_msg
                    request.session['wizard_message_type'] = 'error'
                    return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=6")
        
        return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step={step}")


# =============================================================================
# IMPORTS NECESARIOS
# =============================================================================

import uuid
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

# =============================================================================
# IMPORTAR VISTAS DE WEBHOOKS
# =============================================================================

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
class WebhookEventDebugView(LoginRequiredMixin, DetailView):
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
