from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from ..models import Brand
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.utils.translation import gettext as _
from django.contrib.auth.decorators import login_required, permission_required

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

class BrandSearchApiView(LoginRequiredMixin, View):
    def get(self, request):
        q = request.GET.get('q', '').strip()
        results = []
        if q:
            brands = Brand.objects.filter(name__icontains=q)[:10]
            results = [{'id': b.id, 'name': b.name} for b in brands]
        return JsonResponse({'results': results})

@method_decorator(csrf_exempt, name='dispatch')
class BrandQuickCreateApiView(LoginRequiredMixin, View):
    def post(self, request):
        if not request.user.has_perm('inventory.add_brand'):
            return JsonResponse({'success': False, 'error': _('No tienes permisos para crear marcas.')}, status=403)
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': _('El nombre es obligatorio.')}, status=400)
        if Brand.objects.filter(name__iexact=name).exists():
            return JsonResponse({'success': False, 'error': _('Ya existe una marca con ese nombre.')}, status=400)
        brand = Brand.objects.create(name=name, is_active=True)
        return JsonResponse({'success': True, 'id': brand.id, 'name': brand.name}) 