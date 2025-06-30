from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from ..models import Category

class CategoryListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Category
    template_name = 'inventory/category_list.html'
    context_object_name = 'categories'
    permission_required = 'inventory.view_category'
    paginate_by = 20

class CategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Category
    fields = ['name', 'is_active']
    permission_required = 'inventory.add_category'
    success_url = reverse_lazy('inventory:category_list')

    def get_template_names(self):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('modal') == '1':
            return ['inventory/category_form_modal.html']
        return ['inventory/category_form.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Category"
        return context

    def dispatch(self, request, *args, **kwargs):
        # Si no está autenticado o no tiene permisos, devolver JSON si es modal
        if (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('modal') == '1') and (not request.user.is_authenticated or not request.user.has_perm('inventory.add_category')):
            return JsonResponse({'success': False, 'error': 'No tienes permisos para crear categorías.'}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('modal') == '1':
            return JsonResponse({'success': True, 'id': self.object.id, 'name': self.object.name})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('modal') == '1':
            from django.template.loader import render_to_string
            html = render_to_string('inventory/category_form_modal.html', {'form': form, 'title': 'Create Category'}, request=self.request)
            return JsonResponse({'success': False, 'html': html})
        return super().form_invalid(form)

class CategoryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Category
    fields = ['name', 'is_active']
    permission_required = 'inventory.change_category'
    success_url = reverse_lazy('inventory:category_list')

    def get_template_names(self):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('modal') == '1':
            return ['inventory/category_form_modal.html']
        return ['inventory/category_form.html']

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Category"
        return context

    def dispatch(self, request, *args, **kwargs):
        if (request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('modal') == '1') and (not request.user.is_authenticated or not request.user.has_perm('inventory.change_category')):
            return JsonResponse({'success': False, 'error': 'No tienes permisos para editar categorías.'}, status=403)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('modal') == '1':
            return JsonResponse({'success': True, 'id': self.object.id, 'name': self.object.name})
        return response

    def form_invalid(self, form):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('modal') == '1':
            from django.template.loader import render_to_string
            html = render_to_string('inventory/category_form_modal.html', {'form': form, 'title': 'Edit Category'}, request=self.request)
            return JsonResponse({'success': False, 'html': html})
        return super().form_invalid(form)

class CategoryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Category
    template_name = 'inventory/category_confirm_delete.html'
    success_url = reverse_lazy('inventory:category_list')
    permission_required = 'inventory.delete_category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Confirm Delete Category"
        return context 