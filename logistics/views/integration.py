from django.views.generic import ListView, DetailView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from logistics.models import DeliveryRoute, DeliveryStop
from logistics.services.integration_service import IntegrationService
from logistics.services.tracking_service import TrackingService
from django.utils import timezone
import json

class IntegrationDashboardView(LoginRequiredMixin, ListView):
    """
    Dashboard para gestionar integraciones con otros módulos
    """
    model = DeliveryRoute
    template_name = 'logistics/integration_dashboard.html'
    context_object_name = 'routes'
    
    def get_queryset(self):
        return DeliveryRoute.objects.filter(
            date=timezone.now().date()
        ).prefetch_related('stops', 'driver', 'vehicle')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        integration_service = IntegrationService()
        
        # Estadísticas de integración
        context['integration_stats'] = {
            'total_routes': self.get_queryset().count(),
            'routes_with_cost_calculated': self.get_queryset().filter(logistics_cost__isnull=False).count(),
            'deliveries_with_stock_reserved': DeliveryStop.objects.filter(stock_reserved=True).count(),
            'deliveries_invoiced': DeliveryStop.objects.filter(invoiced=True).count(),
        }
        
        return context

class StockReservationView(LoginRequiredMixin, DetailView):
    """
    Vista para gestionar reservas de stock para entregas
    """
    model = DeliveryStop
    template_name = 'logistics/stock_reservation.html'
    context_object_name = 'delivery_stop'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        integration_service = IntegrationService()
        
        # Obtener información de productos
        products = integration_service._get_delivery_products(self.object)
        context['products'] = products
        
        # Verificar estado de reserva
        context['stock_reserved'] = self.object.stock_reserved
        context['stock_reserved_at'] = self.object.stock_reserved_at
        
        return context

class LogisticsCostsView(LoginRequiredMixin, DetailView):
    """
    Vista para calcular y mostrar costos logísticos
    """
    model = DeliveryRoute
    template_name = 'logistics/logistics_costs.html'
    context_object_name = 'route'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        integration_service = IntegrationService()
        
        # Calcular costos si no están calculados
        if not self.object.logistics_cost:
            cost_result = integration_service.calculate_logistics_costs(self.object)
            if cost_result['success']:
                context['costs'] = cost_result['costs']
            else:
                context['cost_error'] = cost_result['error']
        else:
            context['costs'] = self.object.cost_breakdown or {}
        
        # Información de la ruta
        context['route_info'] = {
            'total_distance': self.object.total_distance or 0,
            'estimated_duration': self.object.estimated_duration or 0,
            'stops_count': self.object.stops.count(),
            'completed_stops': self.object.stops.filter(state='delivered').count(),
        }
        
        return context

class InvoiceManagementView(LoginRequiredMixin, ListView):
    """
    Vista para gestionar facturación automática
    """
    model = DeliveryStop
    template_name = 'logistics/invoice_management.html'
    context_object_name = 'deliveries'
    
    def get_queryset(self):
        return DeliveryStop.objects.filter(
            state='delivered',
            invoiced=False
        ).select_related('route', 'client').order_by('-delivered_time')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas de facturación
        context['invoice_stats'] = {
            'pending_invoices': self.get_queryset().count(),
            'total_invoiced': DeliveryStop.objects.filter(invoiced=True).count(),
            'total_revenue': sum(
                stop.route.logistics_cost or 0 
                for stop in DeliveryStop.objects.filter(invoiced=True)
            )
        }
        
        return context

@method_decorator(csrf_exempt, name='dispatch')
class IntegrationAPIView(LoginRequiredMixin, DetailView):
    """
    Vista API para operaciones de integración
    """
    model = DeliveryStop
    
    def post(self, request, *args, **kwargs):
        delivery_stop = self.get_object()
        action = request.POST.get('action')
        integration_service = IntegrationService()
        
        if action == 'reserve_stock':
            result = integration_service.reserve_stock_for_delivery(delivery_stop)
        elif action == 'calculate_costs':
            result = integration_service.calculate_logistics_costs(delivery_stop.route)
        elif action == 'create_invoice':
            result = integration_service.create_invoice_for_delivery(delivery_stop)
        elif action == 'sync_inventory':
            result = integration_service.sync_with_inventory(delivery_stop)
        else:
            result = {'success': False, 'error': 'Invalid action'}
        
        return JsonResponse(result)

@require_POST
def reserve_stock_ajax(request, delivery_stop_id):
    """
    Endpoint AJAX para reservar stock
    """
    delivery_stop = get_object_or_404(DeliveryStop, id=delivery_stop_id)
    integration_service = IntegrationService()
    
    result = integration_service.reserve_stock_for_delivery(delivery_stop)
    
    if result['success']:
        messages.success(request, result['message'])
    else:
        messages.error(request, f"Error: {result['error']}")
    
    return JsonResponse(result)

@require_POST
def calculate_costs_ajax(request, route_id):
    """
    Endpoint AJAX para calcular costos logísticos
    """
    route = get_object_or_404(DeliveryRoute, id=route_id)
    integration_service = IntegrationService()
    
    result = integration_service.calculate_logistics_costs(route)
    
    if result['success']:
        messages.success(request, f"Costos calculados: ${result['costs']['total_cost']:.2f}")
    else:
        messages.error(request, f"Error: {result['error']}")
    
    return JsonResponse(result)

@require_POST
def create_invoice_ajax(request, delivery_stop_id):
    """
    Endpoint AJAX para crear factura
    """
    delivery_stop = get_object_or_404(DeliveryStop, id=delivery_stop_id)
    integration_service = IntegrationService()
    
    result = integration_service.create_invoice_for_delivery(delivery_stop)
    
    if result['success']:
        messages.success(request, f"Factura creada: {result.get('invoice_number', 'N/A')}")
    else:
        messages.error(request, f"Error: {result['error']}")
    
    return JsonResponse(result)

@require_POST
def sync_inventory_ajax(request, delivery_stop_id):
    """
    Endpoint AJAX para sincronizar con inventario
    """
    delivery_stop = get_object_or_404(DeliveryStop, id=delivery_stop_id)
    integration_service = IntegrationService()
    
    result = integration_service.sync_with_inventory(delivery_stop)
    
    if result['success']:
        messages.success(request, result['message'])
    else:
        messages.error(request, f"Error: {result['error']}")
    
    return JsonResponse(result)

@require_POST
def update_order_status_ajax(request, delivery_stop_id):
    """
    Endpoint AJAX para actualizar estado del pedido
    """
    delivery_stop = get_object_or_404(DeliveryStop, id=delivery_stop_id)
    new_status = request.POST.get('new_status')
    
    if not new_status:
        return JsonResponse({'success': False, 'error': 'New status is required'})
    
    integration_service = IntegrationService()
    result = integration_service.update_order_status(delivery_stop, new_status)
    
    if result['success']:
        messages.success(request, f"Estado del pedido actualizado a: {new_status}")
    else:
        messages.error(request, f"Error: {result['error']}")
    
    return JsonResponse(result)

class IntegrationSettingsView(LoginRequiredMixin, UpdateView):
    """
    Vista para configurar integraciones con otros módulos
    """
    model = DeliveryRoute
    template_name = 'logistics/integration_settings.html'
    fields = []  # No fields to edit, just configuration
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Configuraciones de integración
        context['integration_config'] = {
            'auto_reserve_stock': True,  # TODO: Get from settings
            'auto_calculate_costs': True,
            'auto_create_invoices': False,
            'auto_sync_inventory': True,
            'auto_update_orders': True,
        }
        
        # Módulos disponibles
        context['available_modules'] = [
            {'name': 'inventory', 'status': 'connected', 'description': 'Gestión de inventario'},
            {'name': 'sales', 'status': 'connected', 'description': 'Gestión de ventas'},
            {'name': 'accounting', 'status': 'disconnected', 'description': 'Contabilidad'},
            {'name': 'purchases', 'status': 'disconnected', 'description': 'Compras'},
        ]
        
        return context 