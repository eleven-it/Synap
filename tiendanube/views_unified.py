from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse_lazy
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import json
import logging
import requests

from .models_unified import (
    TiendaNubeUnifiedCustomerMapping, 
    TiendaNubeUnifiedSyncLog, 
    TiendaNubeUnifiedConfig
)
from .services.unified_customer_sync_service import UnifiedCustomerSyncService
from .services.connection_service import MySQLConnectionService

logger = logging.getLogger(__name__)

class UnifiedCustomerSyncDashboardView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Dashboard unificado para sincronización de clientes.
    Combina estadísticas y acciones de todas las plataformas.
    """
    template_name = 'tiendanube/unified_customer_sync_dashboard.html'
    permission_required = 'tiendanube.view_tiendanubeunifiedcustomermapping'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Obtener configuración unificada
            config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
            if not config:
                messages.warning(self.request, _("No hay configuración activa para sincronización unificada"))
                context['config'] = None
                context['stats'] = {}
                return context
            
            context['config'] = config
            
            # Obtener estadísticas
            service = UnifiedCustomerSyncService(config)
            stats = service.get_sync_statistics()
            context['stats'] = stats
            
            # Obtener logs recientes
            recent_logs = TiendaNubeUnifiedSyncLog.objects.filter(
                started_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).order_by('-started_at')[:10]
            context['recent_logs'] = recent_logs
            
            # Verificar estado de conexiones
            context['tiendanube_configured'] = bool(config.tiendanube_store_id and config.tiendanube_access_token)
            context['adminet_configured'] = bool(
                config.adminet_host and config.adminet_database and 
                config.adminet_user and config.adminet_password
            )
            
        except Exception as e:
            logger.error(f"Error en dashboard unificado: {str(e)}")
            messages.error(self.request, f"Error cargando dashboard: {str(e)}")
            context['config'] = None
            context['stats'] = {}
        
        return context


class UnifiedCustomerMappingListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Lista unificada de mapeos de clientes con filtros y búsqueda.
    """
    model = TiendaNubeUnifiedCustomerMapping
    template_name = 'tiendanube/unified_customer_mapping_list.html'
    context_object_name = 'mappings'
    permission_required = 'tiendanube.view_tiendanubeunifiedcustomermapping'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        sync_status = self.request.GET.get('sync_status')
        sync_direction = self.request.GET.get('sync_direction')
        platform = self.request.GET.get('platform')
        search = self.request.GET.get('search')
        
        if sync_status:
            queryset = queryset.filter(sync_status=sync_status)
        
        if sync_direction:
            queryset = queryset.filter(sync_direction=sync_direction)
        
        if platform:
            if platform == 'tiendanube':
                queryset = queryset.filter(tiendanube_id__isnull=False)
            elif platform == 'synap':
                queryset = queryset.filter(synap_client__isnull=False)
            elif platform == 'adminet':
                queryset = queryset.filter(adminet_codigo__isnull=False)
        
        if search:
            queryset = queryset.filter(
                Q(tiendanube_email__icontains=search) |
                Q(adminet_nombre__icontains=search) |
                Q(synap_client__name__icontains=search) |
                Q(synap_contact__name__icontains=search)
            )
        
        return queryset.select_related('synap_client', 'synap_contact')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_statuses'] = TiendaNubeUnifiedCustomerMapping.SyncStatus.choices
        context['sync_directions'] = TiendaNubeUnifiedCustomerMapping.SyncDirection.choices
        context['platforms'] = [
            ('tiendanube', _('Tiendanube')),
            ('synap', _('Synap')),
            ('adminet', _('AdministraNET')),
        ]
        return context


class UnifiedCustomerMappingDetailView(LoginRequiredMixin, PermissionRequiredMixin, TemplateView):
    """
    Vista detallada de un mapeo de cliente con información de todas las plataformas.
    """
    template_name = 'tiendanube/unified_customer_mapping_detail.html'
    permission_required = 'tiendanube.view_tiendanubeunifiedcustomermapping'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        mapping_id = self.kwargs.get('pk')
        
        try:
            mapping = get_object_or_404(TiendaNubeUnifiedCustomerMapping, id=mapping_id)
            context['mapping'] = mapping
            
            # Obtener logs relacionados
            logs = TiendaNubeUnifiedSyncLog.objects.filter(mapping=mapping).order_by('-started_at')[:10]
            context['logs'] = logs
            
        except Exception as e:
            logger.error(f"Error obteniendo detalles del mapeo: {str(e)}")
            messages.error(self.request, f"Error cargando detalles: {str(e)}")
        
        return context


class UnifiedCustomerMappingCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    Crear un nuevo mapeo de cliente manualmente.
    """
    model = TiendaNubeUnifiedCustomerMapping
    template_name = 'tiendanube/unified_customer_mapping_form.html'
    permission_required = 'tiendanube.add_tiendanubeunifiedcustomermapping'
    fields = ['tiendanube_email', 'adminet_codigo', 'sync_direction', 'sync_enabled']
    success_url = reverse_lazy('tiendanube:unified_mapping_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_directions'] = TiendaNubeUnifiedCustomerMapping.SyncDirection.choices
        return context
    
    def form_valid(self, form):
        try:
            # Validar que no existan mapeos duplicados
            tiendanube_email = form.cleaned_data['tiendanube_email']
            adminet_codigo = form.cleaned_data['adminet_codigo']
            
            if TiendaNubeUnifiedCustomerMapping.objects.filter(tiendanube_email=tiendanube_email).exists():
                form.add_error('tiendanube_email', _('Ya existe un mapeo para este email'))
                return self.form_invalid(form)
            
            if TiendaNubeUnifiedCustomerMapping.objects.filter(adminet_codigo=adminet_codigo).exists():
                form.add_error('adminet_codigo', _('Ya existe un mapeo para este código de AdministraNET'))
                return self.form_invalid(form)
            
            # Crear el mapeo usando el servicio
            config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
            if config:
                service = UnifiedCustomerSyncService(config)
                mapping = service.create_customer_mapping(
                    tiendanube_email=tiendanube_email,
                    adminet_codigo=adminet_codigo,
                    sync_direction=form.cleaned_data['sync_direction']
                )
                messages.success(self.request, _('Mapeo creado exitosamente'))
                return redirect('tiendanube:unified_mapping_detail', pk=mapping.id)
            
            return super().form_valid(form)
            
        except Exception as e:
            logger.error(f"Error creando mapeo: {str(e)}")
            messages.error(self.request, f"Error creando mapeo: {str(e)}")
            return self.form_invalid(form)


class UnifiedCustomerMappingUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    Actualizar un mapeo de cliente existente.
    """
    model = TiendaNubeUnifiedCustomerMapping
    template_name = 'tiendanube/unified_customer_mapping_form.html'
    permission_required = 'tiendanube.change_tiendanubeunifiedcustomermapping'
    fields = ['sync_direction', 'sync_enabled', 'tiendanube_email']
    success_url = reverse_lazy('tiendanube:unified_mapping_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_directions'] = TiendaNubeUnifiedCustomerMapping.SyncDirection.choices
        return context
    
    def form_valid(self, form):
        try:
            # Actualizar usando el servicio
            config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
            if config:
                service = UnifiedCustomerSyncService(config)
                mapping = service.update_customer_mapping(
                    mapping_id=self.object.id,
                    sync_direction=form.cleaned_data['sync_direction'],
                    sync_enabled=form.cleaned_data['sync_enabled'],
                    tiendanube_email=form.cleaned_data['tiendanube_email']
                )
                messages.success(self.request, _('Mapeo actualizado exitosamente'))
            
            return super().form_valid(form)
            
        except Exception as e:
            logger.error(f"Error actualizando mapeo: {str(e)}")
            messages.error(self.request, f"Error actualizando mapeo: {str(e)}")
            return self.form_invalid(form)


class UnifiedCustomerMappingDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """
    Eliminar un mapeo de cliente.
    """
    model = TiendaNubeUnifiedCustomerMapping
    template_name = 'tiendanube/unified_customer_mapping_confirm_delete.html'
    permission_required = 'tiendanube.delete_tiendanubeunifiedcustomermapping'
    success_url = reverse_lazy('tiendanube:unified_mapping_list')
    
    def delete(self, request, *args, **kwargs):
        try:
            # Eliminar usando el servicio
            config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
            if config:
                service = UnifiedCustomerSyncService(config)
                service.delete_customer_mapping(self.object.id)
                messages.success(request, _('Mapeo eliminado exitosamente'))
            
            return super().delete(request, *args, **kwargs)
            
        except Exception as e:
            logger.error(f"Error eliminando mapeo: {str(e)}")
            messages.error(request, f"Error eliminando mapeo: {str(e)}")
            return redirect('tiendanube:unified_mapping_detail', pk=self.object.id)


class UnifiedSyncLogListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """
    Lista de logs de sincronización unificada.
    """
    model = TiendaNubeUnifiedSyncLog
    template_name = 'tiendanube/unified_sync_log_list.html'
    context_object_name = 'logs'
    permission_required = 'tiendanube.view_tiendanubeunifiedsynclog'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        sync_type = self.request.GET.get('sync_type')
        status = self.request.GET.get('status')
        platform = self.request.GET.get('platform')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)
        
        if status:
            queryset = queryset.filter(status=status)
        
        if platform:
            queryset = queryset.filter(platform=platform)
        
        if date_from:
            queryset = queryset.filter(started_at__gte=date_from)
        
        if date_to:
            queryset = queryset.filter(started_at__lte=date_to)
        
        return queryset.select_related('mapping')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_types'] = TiendaNubeUnifiedSyncLog.SyncType.choices
        context['statuses'] = TiendaNubeUnifiedSyncLog.Status.choices
        context['platforms'] = TiendaNubeUnifiedSyncLog.Platform.choices
        return context


# Vistas AJAX para operaciones dinámicas
@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def unified_sync_customers_from_tiendanube(request):
    """Sincronizar clientes desde Tiendanube."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Método no permitido')})
    
    try:
        config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({'success': False, 'error': _('No hay configuración activa')})
        
        data = json.loads(request.body)
        limit = data.get('limit', 100)
        offset = data.get('offset', 0)
        
        service = UnifiedCustomerSyncService(config)
        success_count, failed_count = service.sync_customers_from_tiendanube(limit, offset)
        
        return JsonResponse({
            'success': True,
            'message': _('Sincronización completada'),
            'success_count': success_count,
            'failed_count': failed_count
        })
        
    except Exception as e:
        logger.error(f"Error en sincronización desde Tiendanube: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def unified_sync_customers_to_tiendanube(request):
    """Sincronizar clientes hacia Tiendanube."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Método no permitido')})
    
    try:
        config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({'success': False, 'error': _('No hay configuración activa')})
        
        data = json.loads(request.body)
        limit = data.get('limit', 100)
        offset = data.get('offset', 0)
        
        service = UnifiedCustomerSyncService(config)
        success_count, failed_count = service.sync_customers_to_tiendanube(limit, offset)
        
        return JsonResponse({
            'success': True,
            'message': _('Sincronización completada'),
            'success_count': success_count,
            'failed_count': failed_count
        })
        
    except Exception as e:
        logger.error(f"Error en sincronización hacia Tiendanube: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def unified_sync_customers_with_adminet(request):
    """Sincronizar clientes con AdministraNET."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Método no permitido')})
    
    try:
        config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({'success': False, 'error': _('No hay configuración activa')})
        
        data = json.loads(request.body)
        limit = data.get('limit', 100)
        offset = data.get('offset', 0)
        
        service = UnifiedCustomerSyncService(config)
        success_count, failed_count = service.sync_customers_with_adminet(limit, offset)
        
        return JsonResponse({
            'success': True,
            'message': _('Sincronización completada'),
            'success_count': success_count,
            'failed_count': failed_count
        })
        
    except Exception as e:
        logger.error(f"Error en sincronización con AdministraNET: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def unified_migrate_from_old_systems(request):
    """Migrar datos desde los sistemas antiguos."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Método no permitido')})
    
    try:
        config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({'success': False, 'error': _('No hay configuración activa')})
        
        service = UnifiedCustomerSyncService(config)
        migrated_count, error_count = service.migrate_from_old_systems()
        
        return JsonResponse({
            'success': True,
            'message': _('Migración completada'),
            'migrated_count': migrated_count,
            'error_count': error_count
        })
        
    except Exception as e:
        logger.error(f"Error en migración: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def unified_create_mapping_ajax(request):
    """Crear mapeo de cliente via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Método no permitido')})
    
    try:
        config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({'success': False, 'error': _('No hay configuración activa')})
        
        data = json.loads(request.body)
        tiendanube_email = data.get('tiendanube_email')
        adminet_codigo = data.get('adminet_codigo')
        sync_direction = data.get('sync_direction', 'bidirectional')
        
        if not tiendanube_email or not adminet_codigo:
            return JsonResponse({'success': False, 'error': _('Email y código son requeridos')})
        
        service = UnifiedCustomerSyncService(config)
        mapping = service.create_customer_mapping(
            tiendanube_email=tiendanube_email,
            adminet_codigo=adminet_codigo,
            sync_direction=sync_direction
        )
        
        return JsonResponse({
            'success': True,
            'message': _('Mapeo creado exitosamente'),
            'mapping_id': mapping.id
        })
        
    except Exception as e:
        logger.error(f"Error creando mapeo: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@csrf_exempt
@user_passes_test(lambda u: u.is_superuser)
def unified_delete_mapping_ajax(request):
    """Eliminar mapeo de cliente via AJAX."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': _('Método no permitido')})
    
    try:
        config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
        if not config:
            return JsonResponse({'success': False, 'error': _('No hay configuración activa')})
        
        data = json.loads(request.body)
        mapping_id = data.get('mapping_id')
        
        if not mapping_id:
            return JsonResponse({'success': False, 'error': _('ID de mapeo es requerido')})
        
        service = UnifiedCustomerSyncService(config)
        service.delete_customer_mapping(mapping_id)
        
        return JsonResponse({
            'success': True,
            'message': _('Mapeo eliminado exitosamente')
        })
        
    except Exception as e:
        logger.error(f"Error eliminando mapeo: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@user_passes_test(lambda u: u.is_superuser)
def unified_get_adminet_customers(request):
    """Obtener lista de clientes de AdministraNET para mapeo."""
    try:
        config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
        if not config or not config.adminet_host:
            return JsonResponse({'success': False, 'error': _('No hay configuración de AdministraNET')})
        
        mysql_config = config.get_adminet_config()
        mysql_service = MySQLConnectionService(mysql_config)
        
        query = """
            SELECT codigo, nombre_cliente, email, cuit
            FROM cliente 
            ORDER BY nombre_cliente
            LIMIT 100
        """
        
        result = mysql_service.execute_query(query)
        
        if not result.get('success'):
            return JsonResponse({'success': False, 'error': result.get('error', 'Error desconocido')})
        
        clientes = result.get('results', [])
        
        return JsonResponse({
            'success': True,
            'clientes': clientes
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo clientes de AdministraNET: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)})


@user_passes_test(lambda u: u.is_superuser)
def unified_get_tiendanube_customers(request):
    """Obtener lista de clientes de Tiendanube para mapeo."""
    try:
        config = TiendaNubeUnifiedConfig.objects.filter(is_active=True).first()
        if not config or not config.tiendanube_store_id:
            return JsonResponse({'success': False, 'error': _('No hay configuración de Tiendanube')})
        
        tiendanube_config = config.get_tiendanube_config()
        headers = {
            'Content-Type': 'application/json',
            'Authentication': f'bearer {tiendanube_config["access_token"]}',
            'User-Agent': 'synap_tiendanube_unified - synap@administranet.com.ar'
        }
        
        response = requests.get(
            f"{tiendanube_config['api_url']}/{tiendanube_config['store_id']}/customers",
            headers=headers,
            params={'limit': 100}
        )
        
        if response.status_code != 200:
            return JsonResponse({'success': False, 'error': f'Error {response.status_code}: {response.text}'})
        
        customers = response.json()
        
        return JsonResponse({
            'success': True,
            'customers': customers
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo clientes de Tiendanube: {str(e)}")
        return JsonResponse({'success': False, 'error': str(e)}) 