from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from logistics.models import DeliveryRoute
from django.utils.translation import gettext_lazy as _

class DeliveryRouteListView(ListView):
    model = DeliveryRoute
    template_name = 'logistics/delivery_routes/delivery_route_list.html'
    context_object_name = 'routes'
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.order_by('-updated_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = _('Delivery Routes')
        return context

class DeliveryRouteDetailView(DetailView):
    model = DeliveryRoute
    template_name = 'logistics/delivery_routes/delivery_route_detail.html'
    context_object_name = 'route'

class DeliveryRouteCreateView(CreateView):
    model = DeliveryRoute
    fields = ['date', 'vehicle', 'driver', 'state', 'notes']
    template_name = 'logistics/delivery_routes/delivery_route_form.html'
    success_url = reverse_lazy('logistics:deliveryroute_list')

class DeliveryRouteUpdateView(UpdateView):
    model = DeliveryRoute
    fields = ['date', 'vehicle', 'driver', 'state', 'notes']
    template_name = 'logistics/delivery_routes/delivery_route_form.html'
    success_url = reverse_lazy('logistics:deliveryroute_list')

class DeliveryRouteDeleteView(DeleteView):
    model = DeliveryRoute
    template_name = 'logistics/delivery_routes/delivery_route_confirm_delete.html'
    success_url = reverse_lazy('logistics:deliveryroute_list')

# Vista para planificación de rutas
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from logistics.services.route_planning_service import RoutePlanningService
from logistics.services.ai_route_optimizer import AIRouteOptimizer
from logistics.models import DeliveryStop, Vehicle
from django.utils.translation import gettext as _

class RoutePlanningView(View):
    """
    Vista para planificar rutas de entrega (acción manual del usuario)
    """
    def post(self, request, *args, **kwargs):
        try:
            use_ai = request.POST.get('use_ai') == '1'
            if use_ai:
                optimizer = AIRouteOptimizer()
                planned_routes = optimizer.optimize_routes()
                if planned_routes:
                    messages.success(request, _(f"{len(planned_routes)} routes optimized with AI! 🚀"))
                else:
                    messages.info(request, _("No routes were optimized. Check available vehicles and stops."))
                return redirect('logistics:deliveryroute_list')
            else:
                service = RoutePlanningService()
                planned_routes = service.plan_routes()
                if planned_routes:
                    messages.success(request, _(f"{len(planned_routes)} routes planned successfully."))
                else:
                    messages.info(request, _("No routes were planned. Check available vehicles and stops."))
        except Exception as e:
            messages.error(request, _(f"Error planning routes: {str(e)}"))
        return redirect('logistics:deliveryroute_list') 