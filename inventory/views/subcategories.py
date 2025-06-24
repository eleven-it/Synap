from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from ..models import Subcategory

class SubcategoryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Subcategory
    template_name = 'inventory/subcategory_list.html'
    context_object_name = 'subcategories'
    permission_required = 'inventory.view_subcategory'
    paginate_by = 20

    def get_queryset(self):
        return Subcategory.objects.select_related('category').order_by('category__name', 'name')

class SubcategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Subcategory
    template_name = 'inventory/subcategory_form.html'
    fields = ['name', 'category', 'is_active']
    permission_required = 'inventory.add_subcategory'
    success_url = reverse_lazy('inventory:subcategory_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Subcategory"
        return context

class SubcategoryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Subcategory
    template_name = 'inventory/subcategory_form.html'
    fields = ['name', 'category', 'is_active']
    permission_required = 'inventory.change_subcategory'
    success_url = reverse_lazy('inventory:subcategory_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Subcategory"
        return context

class SubcategoryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Subcategory
    template_name = 'inventory/subcategory_confirm_delete.html'
    success_url = reverse_lazy('inventory:subcategory_list')
    permission_required = 'inventory.delete_subcategory'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Confirm Delete Subcategory"
        return context 