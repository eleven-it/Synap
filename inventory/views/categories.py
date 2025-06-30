from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.http import JsonResponse, HttpResponseForbidden
from django.core.exceptions import PermissionDenied
from ..models import Category, Subcategory
from django.db.models import Count
from django.views import View

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

class CategorySearchApiView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        if not q:
            top_cats = Category.objects.annotate(num_products=Count('product')).order_by('-num_products', 'name')[:3]
            top_ids = [c.id for c in top_cats]
            other_cats = Category.objects.exclude(id__in=top_ids).order_by('name')[:10]
            return JsonResponse({
                'top': [{'id': c.id, 'name': c.name} for c in top_cats],
                'others': [{'id': c.id, 'name': c.name} for c in other_cats]
            })
        else:
            cats = Category.objects.filter(name__icontains=q).order_by('name')[:10]
            results = [{'id': c.id, 'name': c.name} for c in cats]
            return JsonResponse({'results': results})

class SubcategorySearchApiView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        category_id = request.GET.get('category_id')
        if not category_id:
            return JsonResponse({'results': []})
        if not q:
            top_subcats = Subcategory.objects.filter(category_id=category_id).annotate(num_products=Count('product')).order_by('-num_products', 'name')[:3]
            top_ids = [s.id for s in top_subcats]
            other_subcats = Subcategory.objects.filter(category_id=category_id).exclude(id__in=top_ids).order_by('name')[:10]
            return JsonResponse({
                'top': [{'id': s.id, 'name': s.name} for s in top_subcats],
                'others': [{'id': s.id, 'name': s.name} for s in other_subcats]
            })
        else:
            subcats = Subcategory.objects.filter(category_id=category_id, name__icontains=q).order_by('name')[:10]
            results = [{'id': s.id, 'name': s.name} for s in subcats]
            return JsonResponse({'results': results}) 