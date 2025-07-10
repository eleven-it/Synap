from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import TemplateView, ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import UserPassesTestMixin
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from .models import (
    TiendaNubeConfig, TiendaNubeSyncLog, TiendaNubeProductMapping,
    TiendaNubeCustomerMapping, TiendaNubeOrderMapping, TiendaNubeRestockRule,
    TiendaNubeRestockLog, TiendaNubeProductRestockPolicy
)
from core.decorators import tiene_permiso
import logging
from .services import TiendaNubeService
from django.http import HttpResponseRedirect
import requests
import json
from django.utils.translation import gettext_lazy as _
from inventory.models import Product, Warehouse

class TiendaNubePermissionMixin(UserPassesTestMixin):
    """Mixin to check TiendaNube access permissions."""
    
    def test_func(self):
        return self.request.user.tiene_permiso("tiendanube.access")

# Create your views here.

class TiendaNubeDashboardView(TiendaNubePermissionMixin, TemplateView):
    """Main dashboard for TiendaNube integration."""
    template_name = 'tiendanube/tiendanube_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        config = TiendaNubeConfig.objects.first()
        if config:
            context['env_configured'] = True
            context['store_id'] = config.store_id
            context['api_url'] = getattr(config, 'api_url', 'https://api.tiendanube.com/v1')
            context['auto_sync'] = getattr(config, 'auto_sync', False)
            context['sync_interval'] = getattr(config, 'sync_interval', 30)
            context['tiendanube_config'] = config
            
            # Obtener estadísticas del servicio
            service = TiendaNubeService(config)
            context['sync_status'] = service.get_sync_status()
            context['recent_logs'] = service.get_recent_logs(limit=10)
            
            logging.info(f"[TiendaNubeDashboard] Usando configuración de BD: store_id={config.store_id}, api_url={getattr(config, 'api_url', 'https://api.tiendanube.com/v1')}, auto_sync={getattr(config, 'auto_sync', False)}, sync_interval={getattr(config, 'sync_interval', 30)}")
        else:
            context['env_configured'] = bool(
                getattr(settings, 'TIENDANUBE_STORE_ID', None) and 
                getattr(settings, 'TIENDANUBE_ACCESS_TOKEN', None)
            )
            context['store_id'] = getattr(settings, 'TIENDANUBE_STORE_ID', 'No configurado')
            context['api_url'] = getattr(settings, 'TIENDANUBE_API_URL', 'https://api.tiendanube.com/v1')
            context['auto_sync'] = getattr(settings, 'TIENDANUBE_AUTO_SYNC', False)
            context['sync_interval'] = getattr(settings, 'TIENDANUBE_SYNC_INTERVAL', 30)
            context['tiendanube_config'] = None
            logging.info(f"[TiendaNubeDashboard] Usando configuración de entorno: store_id={context['store_id']}, api_url={context['api_url']}, auto_sync={context['auto_sync']}, sync_interval={context['sync_interval']}")
        return context

class TiendaNubeConfigListView(TiendaNubePermissionMixin, ListView):
    """List all TiendaNube configurations."""
    model = TiendaNubeConfig
    template_name = 'tiendanube/tiendanube_config_list.html'
    context_object_name = 'configs'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        configs = context['configs']
        config_statuses = {}
        for config in configs:
            service = TiendaNubeService(config)
            ok, msg = service.test_connection()
            config_statuses[config.pk] = {
                'active': ok,
                'message': msg
            }
        context['config_statuses'] = config_statuses
        return context

class TiendaNubeConfigCreateView(TiendaNubePermissionMixin, CreateView):
    """Create a new TiendaNube configuration."""
    model = TiendaNubeConfig
    fields = '__all__'
    template_name = 'tiendanube/tiendanube_config_form.html'
    success_url = reverse_lazy('tiendanube:config_list')

class TiendaNubeConfigUpdateView(TiendaNubePermissionMixin, UpdateView):
    """Edit an existing TiendaNube configuration."""
    model = TiendaNubeConfig
    fields = '__all__'
    template_name = 'tiendanube/tiendanube_config_form.html'
    success_url = reverse_lazy('tiendanube:config_list')

class TiendaNubeConfigDeleteView(TiendaNubePermissionMixin, DeleteView):
    """Delete a TiendaNube configuration."""
    model = TiendaNubeConfig
    template_name = 'tiendanube/tiendanube_config_confirm_delete.html'
    success_url = reverse_lazy('tiendanube:config_list')

class TiendaNubeSyncLogListView(TiendaNubePermissionMixin, ListView):
    """List all TiendaNube sync logs."""
    model = TiendaNubeSyncLog
    template_name = 'tiendanube/tiendanube_logs_list.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        sync_type = self.request.GET.get('sync_type')
        status = self.request.GET.get('status')
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        
        if sync_type:
            queryset = queryset.filter(sync_type=sync_type)
        if status:
            queryset = queryset.filter(status=status)
        if date_from:
            queryset = queryset.filter(started_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(started_at__lte=date_to)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_types'] = TiendaNubeSyncLog.SyncType.choices
        context['statuses'] = TiendaNubeSyncLog.Status.choices
        return context

class TiendaNubeSyncLogDetailView(TiendaNubePermissionMixin, DetailView):
    """Show details of a sync log."""
    model = TiendaNubeSyncLog
    template_name = 'tiendanube/tiendanube_log_detail.html'
    context_object_name = 'log'

class TiendaNubeProductMappingListView(TiendaNubePermissionMixin, ListView):
    """List all product mappings with TiendaNube."""
    model = TiendaNubeProductMapping
    template_name = 'tiendanube/tiendanube_product_mapping_list.html'
    context_object_name = 'mappings'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        sync_status = self.request.GET.get('sync_status')
        search = self.request.GET.get('search')
        
        if sync_status:
            queryset = queryset.filter(sync_status=sync_status)
        if search:
            queryset = queryset.filter(
                Q(product__name__icontains=search) |
                Q(product__sku__icontains=search) |
                Q(tiendanube_handle__icontains=search)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_statuses'] = TiendaNubeProductMapping.SyncStatus.choices
        return context

class TiendaNubeProductMappingDetailView(TiendaNubePermissionMixin, DetailView):
    """Show details of a product mapping."""
    model = TiendaNubeProductMapping
    template_name = 'tiendanube/tiendanube_product_mapping_detail.html'
    context_object_name = 'mapping'

# Nuevas vistas para clientes
class TiendaNubeCustomerMappingListView(TiendaNubePermissionMixin, ListView):
    """List all customer mappings with Tiendanube."""
    model = TiendaNubeCustomerMapping
    template_name = 'tiendanube/tiendanube_customer_mapping_list.html'
    context_object_name = 'mappings'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        sync_status = self.request.GET.get('sync_status')
        search = self.request.GET.get('search')
        
        if sync_status:
            queryset = queryset.filter(sync_status=sync_status)
        if search:
            queryset = queryset.filter(
                Q(client__name__icontains=search) |
                Q(client__email__icontains=search) |
                Q(tiendanube_email__icontains=search)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_statuses'] = TiendaNubeCustomerMapping.SyncStatus.choices
        return context

class TiendaNubeCustomerMappingDetailView(TiendaNubePermissionMixin, DetailView):
    """Show details of a customer mapping."""
    model = TiendaNubeCustomerMapping
    template_name = 'tiendanube/tiendanube_customer_mapping_detail.html'
    context_object_name = 'mapping'

# Nuevas vistas para pedidos
class TiendaNubeOrderMappingListView(TiendaNubePermissionMixin, ListView):
    """List all order mappings with Tiendanube."""
    model = TiendaNubeOrderMapping
    template_name = 'tiendanube/tiendanube_order_mapping_list.html'
    context_object_name = 'mappings'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        sync_status = self.request.GET.get('sync_status')
        search = self.request.GET.get('search')
        
        if sync_status:
            queryset = queryset.filter(sync_status=sync_status)
        if search:
            queryset = queryset.filter(
                Q(sales_order__number__icontains=search) |
                Q(tiendanube_order_number__icontains=search) |
                Q(sales_order__client__name__icontains=search)
            )
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sync_statuses'] = TiendaNubeOrderMapping.SyncStatus.choices
        return context

class TiendaNubeOrderMappingDetailView(TiendaNubePermissionMixin, DetailView):
    """Show details of an order mapping."""
    model = TiendaNubeOrderMapping
    template_name = 'tiendanube/tiendanube_order_mapping_detail.html'
    context_object_name = 'mapping'

# Vistas para reabastecimiento
class TiendaNubeRestockRuleListView(TiendaNubePermissionMixin, ListView):
    """List all restock rules."""
    model = TiendaNubeRestockRule
    template_name = 'tiendanube/tiendanube_restock_rule_list.html'
    context_object_name = 'rules'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        rule_type = self.request.GET.get('rule_type')
        action_type = self.request.GET.get('action_type')
        is_active = self.request.GET.get('is_active')
        
        if rule_type:
            queryset = queryset.filter(rule_type=rule_type)
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == 'true')
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rule_types'] = TiendaNubeRestockRule.RuleType.choices
        context['action_types'] = TiendaNubeRestockRule.ActionType.choices
        return context

class TiendaNubeRestockRuleCreateView(TiendaNubePermissionMixin, CreateView):
    """Create a new restock rule."""
    model = TiendaNubeRestockRule
    fields = '__all__'
    template_name = 'tiendanube/tiendanube_restock_rule_form.html'
    success_url = reverse_lazy('tiendanube:restock_rule_list')

class TiendaNubeRestockRuleUpdateView(TiendaNubePermissionMixin, UpdateView):
    """Edit an existing restock rule."""
    model = TiendaNubeRestockRule
    fields = '__all__'
    template_name = 'tiendanube/tiendanube_restock_rule_form.html'
    success_url = reverse_lazy('tiendanube:restock_rule_list')

class TiendaNubeRestockRuleDeleteView(TiendaNubePermissionMixin, DeleteView):
    """Delete a restock rule."""
    model = TiendaNubeRestockRule
    template_name = 'tiendanube/tiendanube_restock_rule_confirm_delete.html'
    success_url = reverse_lazy('tiendanube:restock_rule_list')


class TiendaNubeRestockRuleDetailView(TiendaNubePermissionMixin, DetailView):
    """View restock rule details."""
    model = TiendaNubeRestockRule
    template_name = 'tiendanube/tiendanube_restock_rule_detail.html'
    context_object_name = 'rule'


class TiendaNubeRestockLogListView(TiendaNubePermissionMixin, ListView):
    """List all restock logs."""
    model = TiendaNubeRestockLog
    template_name = 'tiendanube/tiendanube_restock_log_list.html'
    context_object_name = 'logs'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        product_id = self.request.GET.get('product')
        action_type = self.request.GET.get('action_type')
        status = self.request.GET.get('status')
        
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action_types'] = TiendaNubeRestockLog.ActionType.choices
        context['statuses'] = TiendaNubeRestockLog.Status.choices
        context['products'] = Product.objects.filter(tags__icontains='tiendanube')
        return context


class TiendaNubeRestockLogDetailView(TiendaNubePermissionMixin, DetailView):
    """View restock log details."""
    model = TiendaNubeRestockLog
    template_name = 'tiendanube/tiendanube_restock_log_detail.html'
    context_object_name = 'log'


# Vistas para políticas de reabastecimiento por producto
class TiendaNubeProductRestockPolicyListView(TiendaNubePermissionMixin, ListView):
    """List all product restock policies."""
    model = TiendaNubeProductRestockPolicy
    template_name = 'tiendanube/tiendanube_product_restock_policy_list.html'
    context_object_name = 'policies'
    paginate_by = 50

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtros
        is_active = self.request.GET.get('is_active')
        policy_type = self.request.GET.get('policy_type')
        action_type = self.request.GET.get('action_type')
        product_search = self.request.GET.get('product_search')
        
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active == 'true')
        if policy_type:
            queryset = queryset.filter(policy_type=policy_type)
        if action_type:
            queryset = queryset.filter(action_type=action_type)
        if product_search:
            queryset = queryset.filter(product__name__icontains=product_search)
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['policy_types'] = TiendaNubeProductRestockPolicy.PolicyType.choices
        context['action_types'] = TiendaNubeProductRestockPolicy.ActionType.choices
        return context


class TiendaNubeProductRestockPolicyCreateView(TiendaNubePermissionMixin, CreateView):
    """Create a new product restock policy."""
    model = TiendaNubeProductRestockPolicy
    fields = '__all__'
    template_name = 'tiendanube/tiendanube_product_restock_policy_form.html'
    success_url = reverse_lazy('tiendanube:product_restock_policy_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar productos que tengan tag tiendanube
        form.fields['product'].queryset = Product.objects.filter(tags__icontains='tiendanube')
        return form


class TiendaNubeProductRestockPolicyUpdateView(TiendaNubePermissionMixin, UpdateView):
    """Edit an existing product restock policy."""
    model = TiendaNubeProductRestockPolicy
    fields = '__all__'
    template_name = 'tiendanube/tiendanube_product_restock_policy_form.html'
    success_url = reverse_lazy('tiendanube:product_restock_policy_list')

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        # Filtrar productos que tengan tag tiendanube
        form.fields['product'].queryset = Product.objects.filter(tags__icontains='tiendanube')
        return form


class TiendaNubeProductRestockPolicyDeleteView(TiendaNubePermissionMixin, DeleteView):
    """Delete a product restock policy."""
    model = TiendaNubeProductRestockPolicy
    template_name = 'tiendanube/tiendanube_product_restock_policy_confirm_delete.html'
    success_url = reverse_lazy('tiendanube:product_restock_policy_list')


class TiendaNubeProductRestockPolicyDetailView(TiendaNubePermissionMixin, DetailView):
    """View product restock policy details."""
    model = TiendaNubeProductRestockPolicy
    template_name = 'tiendanube/tiendanube_product_restock_policy_detail.html'
    context_object_name = 'policy'


class TiendaNubeProductRestockPolicyExecuteView(TiendaNubePermissionMixin, View):
    """Execute a product restock policy manually."""
    
    def post(self, request, pk):
        try:
            policy = TiendaNubeProductRestockPolicy.objects.get(pk=pk)
            success, message = policy.execute_restock()
            
            if success:
                messages.success(request, f"Restock executed successfully: {message}")
            else:
                messages.error(request, f"Restock failed: {message}")
                
        except TiendaNubeProductRestockPolicy.DoesNotExist:
            messages.error(request, "Policy not found")
        except Exception as e:
            messages.error(request, f"Error executing restock: {str(e)}")
        
        return redirect('tiendanube:product_restock_policy_detail', pk=pk)


class TiendaNubeProductRestockPolicyBulkCreateView(TiendaNubePermissionMixin, TemplateView):
    """Bulk create restock policies for multiple products."""
    template_name = 'tiendanube/tiendanube_product_restock_policy_bulk_create.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Obtener productos con tag tiendanube que no tengan política
        products_with_policy = TiendaNubeProductRestockPolicy.objects.values_list('product_id', flat=True)
        context['products'] = Product.objects.filter(
            tags__icontains='tiendanube'
        ).exclude(id__in=products_with_policy)
        context['policy_types'] = TiendaNubeProductRestockPolicy.PolicyType.choices
        context['action_types'] = TiendaNubeProductRestockPolicy.ActionType.choices
        context['warehouses'] = Warehouse.objects.all()
        return context
    
    def post(self, request):
        try:
            product_ids = request.POST.getlist('products')
            policy_type = request.POST.get('policy_type')
            action_type = request.POST.get('action_type')
            threshold = request.POST.get('threshold')
            restock_quantity = request.POST.get('restock_quantity')
            source_warehouse_id = request.POST.get('source_warehouse')
            destination_warehouse_id = request.POST.get('destination_warehouse')
            
            created_count = 0
            
            for product_id in product_ids:
                try:
                    product = Product.objects.get(id=product_id)
                    
                    # Verificar que no exista ya una política
                    if not TiendaNubeProductRestockPolicy.objects.filter(product=product).exists():
                        policy = TiendaNubeProductRestockPolicy.objects.create(
                            product=product,
                            policy_type=policy_type,
                            action_type=action_type,
                            threshold=threshold,
                            restock_quantity=restock_quantity,
                            source_warehouse_id=source_warehouse_id if source_warehouse_id else None,
                            destination_warehouse_id=destination_warehouse_id if destination_warehouse_id else None
                        )
                        created_count += 1
                        
                except Product.DoesNotExist:
                    continue
            
            messages.success(request, f"Created {created_count} restock policies successfully")
            
        except Exception as e:
            messages.error(request, f"Error creating policies: {str(e)}")
        
        return redirect('tiendanube:product_restock_policy_list')

# Vistas para reportes
class TiendaNubeReportsView(TiendaNubePermissionMixin, TemplateView):
    """Reports and KPIs dashboard."""
    template_name = 'tiendanube/tiendanube_reports.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # KPIs básicos
        context['total_products'] = TiendaNubeProductMapping.objects.count()
        context['synced_products'] = TiendaNubeProductMapping.objects.filter(sync_status='synced').count()
        context['error_products'] = TiendaNubeProductMapping.objects.filter(sync_status='error').count()
        context['pending_products'] = TiendaNubeProductMapping.objects.filter(sync_status='pending').count()
        
        context['total_customers'] = TiendaNubeCustomerMapping.objects.count()
        context['synced_customers'] = TiendaNubeCustomerMapping.objects.filter(sync_status='synced').count()
        
        context['total_orders'] = TiendaNubeOrderMapping.objects.count()
        context['synced_orders'] = TiendaNubeOrderMapping.objects.filter(sync_status='synced').count()
        
        # Estadísticas de sincronización
        context['recent_syncs'] = TiendaNubeSyncLog.objects.filter(
            started_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
        
        context['failed_syncs'] = TiendaNubeSyncLog.objects.filter(
            status='error',
            started_at__gte=timezone.now() - timezone.timedelta(days=7)
        ).count()
        
        # Estadísticas de reabastecimiento
        context['total_restocks'] = TiendaNubeRestockLog.objects.count()
        context['completed_restocks'] = TiendaNubeRestockLog.objects.filter(status='completed').count()
        context['pending_restocks'] = TiendaNubeRestockLog.objects.filter(status='pending').count()
        
        return context

# Vistas para sincronización manual
class TiendaNubeManualSyncView(TiendaNubePermissionMixin, View):
    """Manual sync operations."""
    
    def post(self, request, *args, **kwargs):
        sync_type = request.POST.get('sync_type')
        config = TiendaNubeConfig.objects.first()
        
        if not config:
            messages.error(request, 'No hay configuración de Tiendanube activa.')
            return JsonResponse({'success': False, 'message': 'No configuration found'})
        
        service = TiendaNubeService(config)
        
        try:
            if sync_type == 'products':
                success_count, failed_count = service.sync_products_from_tiendanube()
                message = f'Sincronización de productos completada. Exitosos: {success_count}, Fallidos: {failed_count}'
            elif sync_type == 'customers':
                success_count, failed_count = service.sync_customers_from_tiendanube()
                message = f'Sincronización de clientes completada. Exitosos: {success_count}, Fallidos: {failed_count}'
            elif sync_type == 'orders':
                success_count, failed_count = service.sync_orders_from_tiendanube()
                message = f'Sincronización de pedidos completada. Exitosos: {success_count}, Fallidos: {failed_count}'
            elif sync_type == 'stock':
                success_count, failed_count = service.sync_stock_to_tiendanube()
                message = f'Sincronización de stock completada. Exitosos: {success_count}, Fallidos: {failed_count}'
            elif sync_type == 'all_stock':
                success_count, failed_count = service.sync_all_stock_to_tiendanube()
                message = f'Sincronización de stock de productos Tiendanube completada. Exitosos: {success_count}, Fallidos: {failed_count}'
            elif sync_type == 'restock':
                success_count, failed_count = service.check_and_restock_products()
                message = f'Verificación de reabastecimiento completada. Exitosos: {success_count}, Fallidos: {failed_count}'
            else:
                return JsonResponse({'success': False, 'message': 'Tipo de sincronización no válido'})
            
            messages.success(request, message)
            return JsonResponse({'success': True, 'message': message})
            
        except Exception as e:
            error_message = f'Error en sincronización: {str(e)}'
            messages.error(request, error_message)
            return JsonResponse({'success': False, 'message': error_message})

# Vistas para webhooks
class TiendaNubeWebhookView(View):
    """Handle incoming webhooks from Tiendanube."""
    
    def post(self, request, *args, **kwargs):
        try:
            # Verificar autenticación del webhook
            webhook_secret = request.headers.get('X-Tiendanube-Webhook-Secret')
            config = TiendaNubeConfig.objects.filter(webhook_secret=webhook_secret).first()
            
            if not config:
                return HttpResponse(status=401)
            
            # Procesar webhook
            webhook_data = json.loads(request.body)
            service = TiendaNubeService(config)
            success = service.handle_webhook(webhook_data)
            
            if success:
                return HttpResponse(status=200)
            else:
                return HttpResponse(status=500)
                
        except Exception as e:
            logging.error(f"Error processing webhook: {str(e)}")
            return HttpResponse(status=500)

class TiendaNubeConfigWizardView(TiendaNubePermissionMixin, TemplateView):
    template_name = 'tiendanube/tiendanube_config_wizard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = self.request.session
        context['app_id'] = session.get('wizard_app_id', '')
        context['client_secret'] = session.get('wizard_client_secret', '')
        context['step'] = session.get('wizard_step', 1)
        context['scopes'] = session.get('wizard_scopes', ['read_products', 'write_products'])
        context['redirect_uri'] = self.request.build_absolute_uri('/tiendanube/config/wizard/callback/')
        context['redirect_uri'] = context['redirect_uri'].replace('http://', 'https://')
        if context['step'] == 4:
            context['code'] = session.get('wizard_code')
            context['state'] = session.get('wizard_state')
            context['access_token'] = session.get('wizard_access_token', '')
            context['user_id'] = session.get('wizard_user_id', '')
        if context['step'] == 5:
            context['auto_sync'] = session.get('wizard_auto_sync', True)
            context['sync_interval'] = session.get('wizard_sync_interval', 30)
            context['sync_products'] = session.get('wizard_sync_products', True)
            context['sync_stock'] = session.get('wizard_sync_stock', True)
            context['sync_variants'] = session.get('wizard_sync_variants', True)
        if context['step'] == 6:
            # Resumen final con datos de la tienda desde Tiendanube
            access_token = session.get('wizard_access_token')
            user_id = session.get('wizard_user_id')
            tienda_data = session.get('wizard_tienda_data')
            if not tienda_data and access_token and user_id:
                # Consultar la API de TiendaNube
                try:
                    resp = requests.get(f'https://api.tiendanube.com/v1/{user_id}/store',
                        headers={
                            'Content-Type': 'application/json',
                            'Authentication': f'bearer {access_token}',
                            'User-Agent': 'administranet_tiendanube - tiendanube@administranet.com.ar'
                        })
                    if resp.status_code == 200:
                        tienda_data = resp.json()
                        session['wizard_tienda_data'] = tienda_data
                    else:
                        tienda_data = None
                except Exception:
                    tienda_data = None
            context['tienda_data'] = tienda_data
            context['summary'] = {
                'app_id': session.get('wizard_app_id'),
                'user_id': user_id,
                'access_token': access_token,
                'scopes': session.get('wizard_scopes'),
                'auto_sync': session.get('wizard_auto_sync'),
                'sync_interval': session.get('wizard_sync_interval'),
                'sync_products': session.get('wizard_sync_products'),
                'sync_stock': session.get('wizard_sync_stock'),
                'sync_variants': session.get('wizard_sync_variants'),
            }
        if context['step'] == 3:
            app_id = context['app_id']
            scopes = context['scopes']
            redirect_uri = self.request.build_absolute_uri('/tiendanube/config/wizard/callback/')
            redirect_uri = redirect_uri.replace('http://', 'https://')
            scope_str = ','.join(scopes)
            state = 'synap-' + self.request.session.session_key
            auth_url = f"https://www.tiendanube.com/apps/{app_id}/authorize?response_type=code&client_id={app_id}&scope={scope_str}&redirect_uri={redirect_uri}&state={state}"
            context['auth_url'] = auth_url
            context['state'] = state
        context['wizard_steps'] = [
            'Credentials',
            'Authorize',
            'Token',
            'Preferences',
            'Summary'
        ]
        return context

    def post(self, request, *args, **kwargs):
        session = request.session
        step = int(session.get('wizard_step', 1))
        if step == 1:
            app_id = request.POST.get('app_id', '').strip()
            client_secret = request.POST.get('client_secret', '').strip()
            session['wizard_app_id'] = app_id
            session['wizard_client_secret'] = client_secret
            session['wizard_step'] = 3
            return self.get(request, *args, **kwargs)
        elif step == 4 and 'get_token' in request.POST:
            # Obtener access_token desde TiendaNube
            app_id = session.get('wizard_app_id')
            client_secret = session.get('wizard_client_secret')
            code = session.get('wizard_code')
            redirect_uri = self.request.build_absolute_uri('/tiendanube/config/wizard/callback/')
            redirect_uri = redirect_uri.replace('http://', 'https://')
            data = {
                'client_id': app_id,
                'client_secret': client_secret,
                'grant_type': 'authorization_code',
                'code': code,
                'redirect_uri': redirect_uri
            }
            # Logging para depuración
            logging.info(f"[TiendaNube Wizard] POST /apps/authorize/token data: {data}")
            resp = requests.post('https://www.tiendanube.com/apps/authorize/token', json=data, headers={'Content-Type': 'application/json'})
            logging.info(f"[TiendaNube Wizard] Response status: {resp.status_code}")
            logging.info(f"[TiendaNube Wizard] Response text: {resp.text}")
            if resp.status_code == 200:
                token_data = resp.json()
                session['wizard_access_token'] = token_data.get('access_token')
                session['wizard_user_id'] = token_data.get('user_id')
                session['wizard_step'] = 5
            else:
                session['wizard_access_token'] = ''
                session['wizard_user_id'] = ''
            return self.get(request, *args, **kwargs)
        elif step == 4 and 'continue_prefs' in request.POST:
            session['wizard_step'] = 5
            return self.get(request, *args, **kwargs)
        elif step == 5:
            session['wizard_auto_sync'] = bool(request.POST.get('auto_sync'))
            session['wizard_sync_interval'] = int(request.POST.get('sync_interval', 30))
            session['wizard_sync_products'] = bool(request.POST.get('sync_products'))
            session['wizard_sync_stock'] = bool(request.POST.get('sync_stock'))
            session['wizard_sync_variants'] = bool(request.POST.get('sync_variants'))
            session['wizard_step'] = 6
            return self.get(request, *args, **kwargs)
        elif step == 6 and 'save_store' in request.POST:
            from .models import TiendaNubeConfig
            # Verificar si ya existe la tienda en Synap
            store_id = session.get('wizard_user_id')
            access_token = session.get('wizard_access_token')
            if not store_id or not access_token:
                context = self.get_context_data()
                context['wizard_error'] = 'No se pudo obtener la autorización de Tiendanube. Por favor, completa el proceso de autorización antes de continuar.'
                return self.render_to_response(context)
            if TiendaNubeConfig.objects.filter(store_id=store_id).exists():
                # Ya existe, mostrar error amigable
                context = self.get_context_data()
                context['wizard_error'] = 'This store is already registered in Synap.'
                return self.render_to_response(context)
            # Crear nueva configuración
            config = TiendaNubeConfig.objects.create(
                store_id=store_id,
                access_token=access_token,
                auto_sync=session.get('wizard_auto_sync', True),
                sync_interval=session.get('wizard_sync_interval', 30),
                sync_products=session.get('wizard_sync_products', True),
                sync_stock=session.get('wizard_sync_stock', True),
                sync_variants=session.get('wizard_sync_variants', True),
            )
            # Limpiar sesión
            session.pop('wizard_app_id', None)
            session.pop('wizard_client_secret', None)
            session.pop('wizard_code', None)
            session.pop('wizard_state', None)
            session.pop('wizard_access_token', None)
            session.pop('wizard_user_id', None)
            session.pop('wizard_tienda_data', None)
            session.pop('wizard_auto_sync', None)
            session.pop('wizard_sync_interval', None)
            session.pop('wizard_sync_products', None)
            session.pop('wizard_sync_stock', None)
            session.pop('wizard_sync_variants', None)
            session.pop('wizard_step', None)
            messages.success(request, 'TiendaNube configuration created successfully!')
            return redirect('tiendanube:dashboard')
        return self.get(request, *args, **kwargs)

class TiendaNubeConfigWizardCallbackView(View):
    def get(self, request, *args, **kwargs):
        session = request.session
        code = request.GET.get('code')
        state = request.GET.get('state')
        session['wizard_code'] = code
        session['wizard_state'] = state
        session['wizard_step'] = 4
        return redirect('tiendanube:config_wizard')

class TiendaNubeSyncAllProductsView(TiendaNubePermissionMixin, View):
    """Sincroniza todos los productos con tag tiendanube hacia Tiendanube."""
    
    def post(self, request):
        try:
            config = TiendaNubeConfig.objects.first()
            if not config:
                messages.error(request, _('TiendaNube configuration not found.'))
                return redirect('tiendanube:dashboard')
            
            service = TiendaNubeService(config)
            limit = int(request.POST.get('limit', 100))
            offset = int(request.POST.get('offset', 0))
            
            success_count, failed_count = service.sync_all_products_to_tiendanube(limit, offset)
            
            if failed_count == 0:
                messages.success(request, _('All Tiendanube products synchronized successfully.'))
            elif success_count > 0:
                messages.warning(request, _('Partial synchronization completed. Some products failed.'))
            else:
                messages.error(request, _('Synchronization failed for all products.'))
            
            return redirect('tiendanube:dashboard')
            
        except Exception as e:
            messages.error(request, f'Error during synchronization: {str(e)}')
            return redirect('tiendanube:dashboard')

class TiendaNubeSyncAllStockView(TiendaNubePermissionMixin, View):
    """Sincroniza stock de todos los productos con tag tiendanube hacia Tiendanube."""
    
    def post(self, request):
        try:
            config = TiendaNubeConfig.objects.first()
            if not config:
                messages.error(request, _('TiendaNube configuration not found.'))
                return redirect('tiendanube:dashboard')
            
            service = TiendaNubeService(config)
            limit = int(request.POST.get('limit', 100))
            offset = int(request.POST.get('offset', 0))
            
            success_count, failed_count = service.sync_all_stock_to_tiendanube(limit, offset)
            
            if failed_count == 0:
                messages.success(request, _('All Tiendanube product stock synchronized successfully.'))
            elif success_count > 0:
                messages.warning(request, _('Partial stock synchronization completed. Some products failed.'))
            else:
                messages.error(request, _('Stock synchronization failed for all products.'))
            
            return redirect('tiendanube:dashboard')
            
        except Exception as e:
            messages.error(request, f'Error during stock synchronization: {str(e)}')
            return redirect('tiendanube:dashboard')

class TiendaNubeSyncProductsView(TiendaNubePermissionMixin, View):
    """Sincroniza productos pendientes hacia Tiendanube."""
    
    def get(self, request):
        """Muestra la página de sincronización de productos."""
        config = TiendaNubeConfig.objects.first()
        if not config:
            messages.error(request, _('TiendaNube configuration not found.'))
            return redirect('tiendanube:dashboard')
        
        # Obtener estadísticas de productos pendientes
        pending_products = Product.objects.filter(
            tags__icontains='tiendanube',
            tiendanubeproductmapping__isnull=True
        ).count()
        
        context = {
            'config': config,
            'pending_products': pending_products,
        }
        return render(request, 'tiendanube/tiendanube_sync_products.html', context)
    
    def post(self, request):
        try:
            config = TiendaNubeConfig.objects.first()
            if not config:
                messages.error(request, _('TiendaNube configuration not found.'))
                return redirect('tiendanube:dashboard')
            
            service = TiendaNubeService(config)
            success_count, failed_count = service.sync_pending_products_to_tiendanube()
            
            if failed_count == 0:
                messages.success(request, _('Pending products synchronized successfully.'))
            elif success_count > 0:
                messages.warning(request, _('Partial synchronization completed. Some products failed.'))
            else:
                messages.error(request, _('Synchronization failed for all products.'))
            
            return redirect('tiendanube:dashboard')
            
        except Exception as e:
            messages.error(request, f'Error during synchronization: {str(e)}')
            return redirect('tiendanube:dashboard')

class TiendaNubeSyncCustomersView(TiendaNubePermissionMixin, View):
    """Sincroniza clientes desde Tiendanube hacia Synap."""
    
    def post(self, request):
        try:
            config = TiendaNubeConfig.objects.first()
            if not config:
                messages.error(request, _('TiendaNube configuration not found.'))
                return redirect('tiendanube:dashboard')
            
            service = TiendaNubeService(config)
            limit = int(request.POST.get('limit', 50))
            offset = int(request.POST.get('offset', 0))
            
            success_count, failed_count = service.sync_orders_from_tiendanube(limit, offset)
            
            if failed_count == 0:
                messages.success(request, _('Customers synchronized successfully.'))
            elif success_count > 0:
                messages.warning(request, _('Partial customer synchronization completed. Some customers failed.'))
            else:
                messages.error(request, _('Customer synchronization failed.'))
            
            return redirect('tiendanube:dashboard')
            
        except Exception as e:
            messages.error(request, f'Error during customer synchronization: {str(e)}')
            return redirect('tiendanube:dashboard')
