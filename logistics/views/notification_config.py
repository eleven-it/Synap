from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.contrib import messages
from logistics.models.notification_config import NotificationConfig
from logistics.forms import NotificationConfigForm

class NotificationConfigListView(LoginRequiredMixin, ListView):
    model = NotificationConfig
    template_name = 'logistics/notification_config_list.html'
    context_object_name = 'configs'
    
    def get_queryset(self):
        # Mostrar configuraciones del usuario actual y configuraciones globales
        return NotificationConfig.objects.filter(
            user=self.request.user
        ) | NotificationConfig.objects.filter(
            user__isnull=True
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['available_events'] = [
            ('delayed', 'Entregas Retrasadas'),
            ('out_geofence', 'Fuera de Geocerca'),
            ('incident', 'Incidentes'),
            ('weather_alert', 'Alertas Meteorológicas'),
            ('completed', 'Entregas Completadas'),
        ]
        context['available_channels'] = [
            ('email', 'Email'),
            ('push', 'Notificaciones Push'),
            ('sms', 'SMS'),
        ]
        return context

class NotificationConfigCreateView(LoginRequiredMixin, CreateView):
    model = NotificationConfig
    form_class = NotificationConfigForm
    template_name = 'logistics/notification_config_form.html'
    success_url = reverse_lazy('logistics:notification_config_list')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Configuración de notificaciones creada exitosamente.')
        return super().form_valid(form)

class NotificationConfigUpdateView(LoginRequiredMixin, UpdateView):
    model = NotificationConfig
    form_class = NotificationConfigForm
    template_name = 'logistics/notification_config_form.html'
    success_url = reverse_lazy('logistics:notification_config_list')
    
    def get_queryset(self):
        # Solo permitir editar configuraciones propias
        return NotificationConfig.objects.filter(user=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Configuración de notificaciones actualizada exitosamente.')
        return super().form_valid(form)

class NotificationConfigDeleteView(LoginRequiredMixin, DeleteView):
    model = NotificationConfig
    template_name = 'logistics/notification_config_confirm_delete.html'
    success_url = reverse_lazy('logistics:notification_config_list')
    
    def get_queryset(self):
        # Solo permitir eliminar configuraciones propias
        return NotificationConfig.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Configuración de notificaciones eliminada exitosamente.')
        return super().delete(request, *args, **kwargs)

class NotificationTestView(LoginRequiredMixin, ListView):
    """
    Vista para probar notificaciones
    """
    template_name = 'logistics/notification_test.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['test_events'] = [
            {
                'type': 'delayed',
                'name': 'Entrega Retrasada',
                'description': 'Simula una entrega retrasada',
                'icon': '🚨'
            },
            {
                'type': 'out_geofence',
                'name': 'Fuera de Geocerca',
                'description': 'Simula un vehículo fuera de la geocerca',
                'icon': '📍'
            },
            {
                'type': 'weather_alert',
                'name': 'Alerta Meteorológica',
                'description': 'Simula una alerta meteorológica',
                'icon': '🌦️'
            },
            {
                'type': 'incident',
                'name': 'Incidente',
                'description': 'Simula un incidente durante la entrega',
                'icon': '⚠️'
            },
            {
                'type': 'completed',
                'name': 'Entrega Completada',
                'description': 'Simula una entrega completada exitosamente',
                'icon': '✅'
            }
        ]
        return context 