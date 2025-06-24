from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from ..models import Brand

class BrandListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Brand
    template_name = 'inventory/brand_list.html'
    context_object_name = 'brands'
    permission_required = 'inventory.view_brand'
    paginate_by = 20

class BrandCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Brand
    template_name = 'inventory/brand_form.html'
    fields = ['name', 'is_active']
    permission_required = 'inventory.add_brand'
    success_url = reverse_lazy('inventory:brand_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Brand"
        return context

class BrandUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Brand
    template_name = 'inventory/brand_form.html'
    fields = ['name', 'is_active']
    permission_required = 'inventory.change_brand'
    success_url = reverse_lazy('inventory:brand_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Brand"
        return context

class BrandDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Brand
    template_name = 'inventory/brand_confirm_delete.html'
    success_url = reverse_lazy('inventory:brand_list')
    permission_required = 'inventory.delete_brand'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Confirm Delete Brand"
        return context 