from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from ..models import SystemConfiguration
from ..forms import SystemConfigurationForm

class SystemConfigurationListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = SystemConfiguration
    template_name = 'core/system_config/system_config_list.html'
    context_object_name = 'configs'
    permission_required = 'configuracion.sistema'
    paginate_by = 20

class SystemConfigurationCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = SystemConfiguration
    form_class = SystemConfigurationForm
    template_name = 'core/system_config/system_config_form.html'
    permission_required = 'configuracion.sistema'
    success_url = reverse_lazy('core:system_config_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Crear Configuración"
        return context

class SystemConfigurationUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = SystemConfiguration
    form_class = SystemConfigurationForm
    template_name = 'core/system_config/system_config_form.html'
    permission_required = 'configuracion.sistema'
    success_url = reverse_lazy('core:system_config_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Editar Configuración"
        return context

class SystemConfigurationDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = SystemConfiguration
    template_name = 'core/system_config/system_config_confirm_delete.html'
    success_url = reverse_lazy('core:system_config_list')
    permission_required = 'configuracion.sistema'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Confirmar Eliminación de Configuración"
        return context 