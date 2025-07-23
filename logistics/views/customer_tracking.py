from django.views.generic import TemplateView
from logistics.models import DeliveryStop, DeliveryRoute
from logistics.services.tracking_service import TrackingService
from django.utils.translation import gettext as _
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail

class CustomerTrackingView(TemplateView):
    template_name = 'logistics/customer_tracking.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tracking_code = self.request.GET.get('code')
        stop = get_object_or_404(DeliveryStop, tracking_code=tracking_code)
        route = stop.route
        service = TrackingService()
        vehicle = route.vehicle if route else None
        location = service.get_vehicle_location(vehicle) if vehicle else None
        context['stop'] = stop
        context['route'] = route
        context['vehicle'] = vehicle
        context['location'] = location
        context['tracking_code'] = tracking_code
        return context

    def post(self, request, *args, **kwargs):
        tracking_code = request.GET.get('code')
        stop = get_object_or_404(DeliveryStop, tracking_code=tracking_code)
        feedback = request.POST.get('feedback', '').strip()
        context = self.get_context_data(**kwargs)
        if feedback:
            stop.feedback = feedback
            stop.save(update_fields=['feedback'])
            # Determinar destinatario: responsable de la ruta, empresa, o fallback
            recipient = None
            if stop.route and hasattr(stop.route, 'responsible') and stop.route.responsible and stop.route.responsible.email:
                recipient = stop.route.responsible.email
            elif hasattr(stop.route, 'empresa') and stop.route.empresa and hasattr(stop.route.empresa, 'email') and stop.route.empresa.email:
                recipient = stop.route.empresa.email
            else:
                recipient = 'logistics@empresa.com'
            send_mail(
                subject=f"[Synap] Nuevo feedback de entrega ({tracking_code})",
                message=f"Feedback del cliente: {feedback}",
                from_email=None,
                recipient_list=[recipient],
                fail_silently=True
            )
            context['feedback_sent'] = True
        return self.render_to_response(context) 