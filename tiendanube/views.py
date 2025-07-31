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
from .models_synap import (
    TiendaNubeConfig, TiendaNubeSyncLog, TiendaNubeProductMapping,
    TiendaNubeCustomerMapping, TiendaNubeOrderMapping, TiendaNubeRestockRule,
    TiendaNubeRestockLog, TiendaNubeProductRestockPolicy
)
from core.decorators import tiene_permiso
import logging
from .services_main import TiendaNubeService
from django.http import HttpResponseRedirect
import requests
import json
from django.utils.translation import gettext_lazy as _
from inventory.models import Product, Warehouse

# Import enhanced views
from .views_enhanced import (
    TiendaNubeConfigWizardView,
    TiendaNubeConfigWizardCallbackView,
    TiendaNubeDashboardView,
    TiendaNubeManualSyncView,
)

class TiendaNubePermissionMixin(UserPassesTestMixin):
    """Mixin to check TiendaNube access permissions."""
    
    def test_func(self):
        return self.request.user.tiene_permiso("tiendanube.access")

# Vistas generales para TiendaNube <-> Synap integration

# Create your views here.

# Dashboard view is now in views_enhanced.py

class TiendaNubeConfigListView(TiendaNubePermissionMixin, ListView):
    """List all TiendaNube configurations."""
    model = TiendaNubeConfig
    template_name = 'tiendanube/tiendanube_config_list.html'
    context_object_name = 'configs'

    def get_tiendanube_service(self, config=None):
        if config is None:
            config = TiendaNubeConfig.objects.first()
        from .services_main import TiendaNubeService
        return TiendaNubeService(config)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        configs = context['configs']
        config_statuses = {}
        for config in configs:
            service = self.get_tiendanube_service(config)
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

# Manual sync view is now in views_enhanced.py

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

# Wizard views are now in views_enhanced.py

class TiendaNubeSyncAllProductsView(TiendaNubePermissionMixin, View):
    """Sincroniza todos los productos con tag tiendanube hacia Tiendanube."""
    
    def get_tiendanube_service(self, config=None):
        if config is None:
            config = TiendaNubeConfig.objects.first()
        from .services_main import TiendaNubeService
        return TiendaNubeService(config)
    
    def post(self, request):
        try:
            config = TiendaNubeConfig.objects.first()
            if not config:
                messages.error(request, _('TiendaNube configuration not found.'))
                return redirect('tiendanube:dashboard')
            
            service = self.get_tiendanube_service(config)
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
    
    def get_tiendanube_service(self, config=None):
        if config is None:
            config = TiendaNubeConfig.objects.first()
        from .services_main import TiendaNubeService
        return TiendaNubeService(config)
    
    def post(self, request):
        try:
            config = TiendaNubeConfig.objects.first()
            if not config:
                messages.error(request, _('TiendaNube configuration not found.'))
                return redirect('tiendanube:dashboard')
            
            service = self.get_tiendanube_service(config)
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
    def get_tiendanube_service(self, config=None):
        if config is None:
            config = TiendaNubeConfig.objects.first()
        from .services_main import TiendaNubeService
        return TiendaNubeService(config)

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
            
            service = self.get_tiendanube_service(config)
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
    
    def get_tiendanube_service(self, config=None):
        if config is None:
            config = TiendaNubeConfig.objects.first()
        from .services_main import TiendaNubeService
        return TiendaNubeService(config)
    
    def get(self, request):
        """Muestra la página de sincronización de clientes."""
        config = TiendaNubeConfig.objects.first()
        if not config:
            messages.error(request, _('TiendaNube configuration not found.'))
            return redirect('tiendanube:dashboard')
        
        # Obtener estadísticas de clientes sincronizados
        from core.models import Contact
        synced_customers = Contact.objects.filter(
            tags__icontains='tiendanube'
        ).count()
        
        # Obtener clientes con tag tiendanube que no están sincronizados
        # Simplificar la consulta para evitar errores de lookup
        total_tiendanube_contacts = Contact.objects.filter(
            tags__icontains='tiendanube'
        ).count()
        
        # Contar mappings existentes
        from .models import TiendaNubeCustomerMapping
        existing_mappings = TiendaNubeCustomerMapping.objects.count()
        
        # Calcular clientes pendientes (aproximado)
        unsynced_customers = max(0, total_tiendanube_contacts - existing_mappings)
        
        context = {
            'config': config,
            'synced_customers': synced_customers,
            'unsynced_customers': unsynced_customers,
        }
        return render(request, 'tiendanube/tiendanube_sync_customers.html', context)
    
    def post(self, request):
        try:
            config = TiendaNubeConfig.objects.first()
            if not config:
                messages.error(request, _('TiendaNube configuration not found.'))
                return redirect('tiendanube:dashboard')
            
            service = self.get_tiendanube_service(config)
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


class TiendaNubeSyncCustomersToTiendanubeView(TiendaNubePermissionMixin, View):
    """Sincroniza clientes desde Synap hacia Tiendanube."""
    
    def get_tiendanube_service(self, config=None):
        if config is None:
            config = TiendaNubeConfig.objects.first()
        from .services_main import TiendaNubeService
        return TiendaNubeService(config)
    
    def post(self, request):
        try:
            config = TiendaNubeConfig.objects.first()
            if not config:
                messages.error(request, _('TiendaNube configuration not found.'))
                return redirect('tiendanube:dashboard')
            
            service = self.get_tiendanube_service(config)
            limit = int(request.POST.get('limit', 100))
            offset = int(request.POST.get('offset', 0))
            
            success_count, failed_count = service.sync_all_customers_to_tiendanube(limit, offset)
            
            if failed_count == 0:
                messages.success(request, _('All customers synchronized to Tiendanube successfully.'))
            elif success_count > 0:
                messages.warning(request, _('Partial customer synchronization completed. Some customers failed.'))
            else:
                messages.error(request, _('Customer synchronization to Tiendanube failed.'))
            
            return redirect('tiendanube:dashboard')
            
        except Exception as e:
            messages.error(request, f'Error during customer synchronization to Tiendanube: {str(e)}')
            return redirect('tiendanube:dashboard')
