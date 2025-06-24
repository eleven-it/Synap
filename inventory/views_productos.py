from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from .models import Product

class ProductListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Product
    template_name = 'inventario/producto_list.html'
    context_object_name = 'productos'
    permission_required = 'inventario.ver_producto'
    paginate_by = 20

class ProductCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Product
    template_name = 'inventario/producto_form.html'
    fields = ['name', 'sku', 'description', 'brand', 'handle', 'price', 'price_currency', 'uom', 'tracking', 'is_published']
    permission_required = 'inventario.crear_producto'
    success_url = reverse_lazy('inventario:producto_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Crear Producto"
        return context

class ProductUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Product
    template_name = 'inventario/producto_form.html'
    fields = ['name', 'sku', 'description', 'brand', 'handle', 'price', 'price_currency', 'uom', 'tracking', 'is_published']
    permission_required = 'inventario.editar_producto'
    success_url = reverse_lazy('inventario:producto_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Editar Producto"
        return context 