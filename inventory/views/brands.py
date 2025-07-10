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
from django.db.models import Count
from django.http import HttpResponseForbidden

class BrandListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Brand
    template_name = 'inventory/brand_list.html'
    context_object_name = 'brands'
    permission_required = 'inventory.view_brand'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        empresa = self.request.user.empresa_activa
        return Brand.objects.filter(empresa=empresa).order_by('name')

class BrandCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Brand
    template_name = 'inventory/brand_form.html'
    fields = ['name', 'is_active']
    permission_required = 'inventory.add_brand'
    success_url = reverse_lazy('inventory:brand_list')

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Brand"
        return context

    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        return super().form_valid(form)

class BrandUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Brand
    template_name = 'inventory/brand_form.html'
    fields = ['name', 'is_active']
    permission_required = 'inventory.change_brand'
    success_url = reverse_lazy('inventory:brand_list')

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        empresa = self.request.user.empresa_activa
        return Brand.objects.filter(empresa=empresa)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Brand"
        return context

class BrandDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Brand
    template_name = 'inventory/brand_confirm_delete.html'
    success_url = reverse_lazy('inventory:brand_list')
    permission_required = 'inventory.delete_brand'

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        empresa = self.request.user.empresa_activa
        return Brand.objects.filter(empresa=empresa)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Confirm Delete Brand"
        return context

class BrandSearchApiView(LoginRequiredMixin, View):
    def get(self, request):
        empresa = request.user.empresa_activa
        if not empresa:
            return JsonResponse({'results': []}, status=403)
        
        q = request.GET.get('q', '').strip()
        if not q:
            # Top 3 más usadas de la empresa del usuario
            top_brands = Brand.objects.filter(empresa=empresa).annotate(num_products=Count('product')).order_by('-num_products', 'name')[:3]
            top_ids = [b.id for b in top_brands]
            # Otras marcas (sin repetir) de la empresa del usuario
            other_brands = Brand.objects.filter(empresa=empresa).exclude(id__in=top_ids).order_by('name')[:10]
            return JsonResponse({
                'top': [{'id': b.id, 'name': b.name} for b in top_brands],
                'others': [{'id': b.id, 'name': b.name} for b in other_brands]
            })
        else:
            brands = Brand.objects.filter(empresa=empresa, name__icontains=q).order_by('name')[:10]
            results = [{'id': b.id, 'name': b.name} for b in brands]
            return JsonResponse({'results': results})

@method_decorator(csrf_exempt, name='dispatch')
class BrandQuickCreateApiView(LoginRequiredMixin, View):
    def post(self, request):
        empresa = request.user.empresa_activa
        if not empresa:
            return JsonResponse({'success': False, 'error': _('No active company.')}, status=403)
        
        if not request.user.has_perm('inventory.add_brand'):
            return JsonResponse({'success': False, 'error': _('No tienes permisos para crear marcas.')}, status=403)
        
        name = request.POST.get('name', '').strip()
        if not name:
            return JsonResponse({'success': False, 'error': _('El nombre es obligatorio.')}, status=400)
        
        if Brand.objects.filter(empresa=empresa, name__iexact=name).exists():
            return JsonResponse({'success': False, 'error': _('Ya existe una marca con ese nombre.')}, status=400)
        
        brand = Brand.objects.create(name=name, is_active=True, empresa=empresa)
        return JsonResponse({'success': True, 'id': brand.id, 'name': brand.name}) 