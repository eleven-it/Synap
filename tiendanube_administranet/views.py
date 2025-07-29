"""
Vistas principales para la integración Tiendanube-AdministraNET.
"""

import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, DetailView, RedirectView
from django.views.generic.edit import FormView
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib import messages
from django.utils.translation import gettext as _
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone

from .models import (
    TiendanubeConfig, AdministraNETConfig, CustomerMapping, 
    SyncLog, ProductMapping, ProductVariantMapping, ProductCategoryMapping,
    OrderMapping, WebhookConfig, WebhookEvent, WebhookDeliveryLog
)
from .services.sync_service import TiendanubeAdministraNETSyncService
from .forms import (
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
            # Crear servicio de sincronización
            sync_service = TiendanubeAdministraNETSyncService()
            
            # Obtener estadísticas
            context['statistics'] = sync_service.get_sync_statistics()
            
            # Probar conexiones
            context['connections'] = sync_service.test_connections()
            
            # Obtener configuraciones activas
            context['tiendanube_config'] = TiendanubeConfig.objects.filter(is_active=True).first()
            context['adminet_config'] = AdministraNETConfig.objects.filter(is_active=True).first()
            
            # Obtener logs recientes
            context['recent_logs'] = SyncLog.objects.order_by('-started_at')[:10]
            
            # Obtener mapeos recientes
            context['recent_mappings'] = CustomerMapping.objects.order_by('-created_at')[:5]
            
        except Exception as e:
            logger.error(f"Error obteniendo datos del dashboard: {str(e)}")
            context['error'] = str(e)
        
        return context


class CustomerMappingListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Vista para listar mapeos de clientes con filtros avanzados.
    """
    model = CustomerMapping
    template_name = 'tiendanube_administranet/customer_mapping_list.html'
    context_object_name = 'mappings'
    permission_required = 'tiendanube_administranet.view_customermapping'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = CustomerMapping.objects.all()
        
        # Aplicar filtros del formulario
        form = CustomerMappingFilterForm(self.request.GET)
        if form.is_valid():
            # Filtro de búsqueda
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
            
            # Filtros de estado
            sync_status = form.cleaned_data.get('sync_status')
            if sync_status:
                queryset = queryset.filter(sync_status=sync_status)
            
            sync_direction = form.cleaned_data.get('sync_direction')
            if sync_direction:
                queryset = queryset.filter(sync_direction=sync_direction)
            
            sync_enabled = form.cleaned_data.get('sync_enabled')
            if sync_enabled:
                enabled = sync_enabled == 'true'
                queryset = queryset.filter(sync_enabled=enabled)
            
            # Filtros de Tiendanube
            verified_email = form.cleaned_data.get('tiendanube_verified_email')
            if verified_email:
                verified = verified_email == 'true'
                queryset = queryset.filter(tiendanube_verified_email=verified)
            
            accepts_marketing = form.cleaned_data.get('tiendanube_accepts_marketing')
            if accepts_marketing:
                marketing = accepts_marketing == 'true'
                queryset = queryset.filter(tiendanube_accepts_marketing=marketing)
            
            has_orders = form.cleaned_data.get('tiendanube_has_orders')
            if has_orders:
                if has_orders == 'true':
                    queryset = queryset.filter(tiendanube_orders_count__gt=0)
                else:
                    queryset = queryset.filter(tiendanube_orders_count=0)
            
            country = form.cleaned_data.get('tiendanube_country')
            if country:
                queryset = queryset.filter(tiendanube_country__icontains=country)
            
            city = form.cleaned_data.get('tiendanube_city')
            if city:
                queryset = queryset.filter(tiendanube_city__icontains=city)
            
            # Filtros de fecha
            created_from = form.cleaned_data.get('created_date_from')
            if created_from:
                queryset = queryset.filter(created_at__date__gte=created_from)
            
            created_to = form.cleaned_data.get('created_date_to')
            if created_to:
                queryset = queryset.filter(created_at__date__lte=created_to)
            
            synced_from = form.cleaned_data.get('last_synced_from')
            if synced_from:
                queryset = queryset.filter(last_synced__date__gte=synced_from)
            
            synced_to = form.cleaned_data.get('last_synced_to')
            if synced_to:
                queryset = queryset.filter(last_synced__date__lte=synced_to)
            
            # Filtros de rango
            spent_min = form.cleaned_data.get('total_spent_min')
            if spent_min is not None:
                queryset = queryset.filter(tiendanube_total_spent__gte=spent_min)
            
            spent_max = form.cleaned_data.get('total_spent_max')
            if spent_max is not None:
                queryset = queryset.filter(tiendanube_total_spent__lte=spent_max)
            
            orders_min = form.cleaned_data.get('orders_count_min')
            if orders_min is not None:
                queryset = queryset.filter(tiendanube_orders_count__gte=orders_min)
            
            orders_max = form.cleaned_data.get('orders_count_max')
            if orders_max is not None:
                queryset = queryset.filter(tiendanube_orders_count__lte=orders_max)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Formulario de filtros
        context['filter_form'] = CustomerMappingFilterForm(self.request.GET)
        
        # Estadísticas
        queryset = self.get_queryset()
        context['total_mappings'] = CustomerMapping.objects.count()
        context['filtered_mappings'] = queryset.count()
        context['synced_mappings'] = CustomerMapping.objects.filter(sync_status='synced').count()
        context['pending_mappings'] = CustomerMapping.objects.filter(sync_status='pending').count()
        context['error_mappings'] = CustomerMapping.objects.filter(sync_status='error').count()
        
        # Estadísticas adicionales
        context['verified_customers'] = CustomerMapping.objects.filter(tiendanube_verified_email=True).count()
        context['marketing_customers'] = CustomerMapping.objects.filter(tiendanube_accepts_marketing=True).count()
        context['customers_with_orders'] = CustomerMapping.objects.filter(tiendanube_orders_count__gt=0).count()
        
        # Top clientes por gasto
        context['top_customers'] = CustomerMapping.objects.filter(
            tiendanube_total_spent__gt=0
        ).order_by('-tiendanube_total_spent')[:5]
        
        # Distribución por país
        context['country_distribution'] = CustomerMapping.objects.exclude(
            tiendanube_country__isnull=True
        ).exclude(
            tiendanube_country=''
        ).values('tiendanube_country').annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        return context


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
        
        # Obtener logs relacionados
        context['related_logs'] = SyncLog.objects.filter(
            mapping=self.object
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
        
        # Obtener estadísticas relacionadas
        context['related_mappings'] = CustomerMapping.objects.filter(
            sync_logs=self.object
        )[:10]
        
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
            mapping=self.object
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
            mapping=self.object
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
        except:
            context['tiendanube_configured'] = False
        
        try:
            adminet_config = AdministraNETConfig.objects.filter(is_active=True).first()
            context['adminet_configured'] = adminet_config is not None
            context['adminet_config'] = adminet_config
        except:
            context['adminet_configured'] = False
        
        # Estadísticas de mapeos
        context['customer_mappings'] = CustomerMapping.objects.count()
        context['product_mappings'] = ProductMapping.objects.count()
        context['order_mappings'] = OrderMapping.objects.count()
        
        # Últimos logs
        context['recent_logs'] = SyncLog.objects.all().order_by('-started_at')[:5]
        
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
                'duration': str(log.duration) if log.duration else None,
                'records_processed': log.records_processed,
                'records_synced': log.records_synced,
                'error_message': log.error_message,
                'get_status_display': log.get_status_display(),
                'get_direction_display': log.get_direction_display(),
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
        context['delivery_logs'] = self.object.webhook_delivery_logs.order_by('-sent_at')
        
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
        from ..services.webhook_service import WebhookProcessor
        result = WebhookProcessor.process_webhook_event(webhook_config, event_data, headers)
        
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
        products = ProductMapping.objects.select_related('tiendanube_config', 'adminet_config')
        
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
        messages.error(request, f'Error cargando productos: {str(e)}')
        return redirect('tiendanube_administranet:dashboard')


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
        # Agregar lista de warehouses disponibles
        from inventory.models import Warehouse
        context['warehouses'] = Warehouse.objects.filter(is_active=True)
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
        # Agregar lista de warehouses disponibles
        from inventory.models import Warehouse
        context['warehouses'] = Warehouse.objects.filter(is_active=True)
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
            context['redirect_uri'] = self.request.build_absolute_uri(reverse('tiendanube_administranet:tiendanube_config_wizard'))
            
        elif step == 3:
            # Paso 3: Autorización
            app_id = self.request.session.get('wizard_app_id')
            client_secret = self.request.session.get('wizard_client_secret')
            if app_id and client_secret:
                # Generar URL de autorización
                state = self.request.session.get('wizard_state', '')
                context['auth_url'] = f"https://www.tiendanube.com/apps/{app_id}/authorize?response_type=code&client_id={app_id}&state={state}"
                context['redirect_uri'] = self.request.build_absolute_uri(reverse('tiendanube_administranet:tiendanube_config_wizard'))
                context['state'] = state
                
        elif step == 4:
            # Paso 4: Token
            context['access_token'] = self.request.session.get('wizard_access_token')
            context['user_id'] = self.request.session.get('wizard_user_id')
            
        elif step == 5:
            # Paso 5: Preferencias
            context['auto_sync'] = self.request.session.get('wizard_auto_sync', True)
            context['sync_interval'] = self.request.session.get('wizard_sync_interval', 30)
            context['sync_products'] = self.request.session.get('wizard_sync_products', True)
            context['sync_stock'] = self.request.session.get('wizard_sync_stock', True)
            context['sync_variants'] = self.request.session.get('wizard_sync_variants', True)
            
        elif step == 6:
            # Paso 6: Resumen
            context['summary'] = {
                'app_id': self.request.session.get('wizard_app_id'),
                'user_id': self.request.session.get('wizard_user_id'),
                'access_token': self.request.session.get('wizard_access_token'),
                'scopes': self.request.session.get('wizard_scopes', []),
                'auto_sync': self.request.session.get('wizard_auto_sync', True),
                'sync_interval': self.request.session.get('wizard_sync_interval', 30),
                'sync_products': self.request.session.get('wizard_sync_products', True),
                'sync_stock': self.request.session.get('wizard_sync_stock', True),
                'sync_variants': self.request.session.get('wizard_sync_variants', True),
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
                # Aquí implementarías la lógica para obtener el token de acceso
                # Por ahora, simulamos el proceso
                request.session['wizard_access_token'] = 'sample_access_token_123'
                request.session['wizard_user_id'] = 'sample_store_id'
                return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=4")
            elif 'continue_prefs' in request.POST:
                return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=5")
                
        elif step == 5:
            # Procesar preferencias
            request.session['wizard_auto_sync'] = 'auto_sync' in request.POST
            request.session['wizard_sync_interval'] = int(request.POST.get('sync_interval', 30))
            request.session['wizard_sync_products'] = 'sync_products' in request.POST
            request.session['wizard_sync_stock'] = 'sync_stock' in request.POST
            request.session['wizard_sync_variants'] = 'sync_variants' in request.POST
            return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=6")
            
        elif step == 6:
            # Guardar configuración
            if 'save_store' in request.POST:
                try:
                    # Crear la configuración de Tiendanube
                    config = TiendanubeConfig.objects.create(
                        store_id=request.session.get('wizard_user_id'),
                        access_token=request.session.get('wizard_access_token'),
                        api_url='https://api.tiendanube.com/v1',
                        is_active=request.session.get('wizard_auto_sync', True),
                        sync_interval=request.session.get('wizard_sync_interval', 30),
                        sync_products=request.session.get('wizard_sync_products', True),
                        sync_stock=request.session.get('wizard_sync_stock', True),
                        sync_variants=request.session.get('wizard_sync_variants', True),
                    )
                    
                    # Limpiar datos de sesión
                    for key in ['wizard_app_id', 'wizard_client_secret', 'wizard_state', 
                               'wizard_access_token', 'wizard_user_id', 'wizard_auto_sync',
                               'wizard_sync_interval', 'wizard_sync_products', 'wizard_sync_stock',
                               'wizard_sync_variants', 'wizard_scopes', 'wizard_tienda_data']:
                        request.session.pop(key, None)
                    
                    messages.success(request, _('Tiendanube store configuration completed successfully!'))
                    return redirect('tiendanube_administranet:tiendanube_config_list')
                    
                except Exception as e:
                    messages.error(request, f'Error saving configuration: {str(e)}')
                    return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step=6")
        
        return redirect(f"{reverse('tiendanube_administranet:tiendanube_config_wizard')}?step={step}")


# =============================================================================
# IMPORTS NECESARIOS
# =============================================================================

import uuid
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
