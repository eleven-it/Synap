from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.urls import reverse_lazy
from django.db import transaction
from django.db.models import Q
from ..models import Product, Category, ProductImage
from ..forms import ProductForm
from core.utils.utils import require_empresa_activa
from django.http import HttpResponseForbidden, JsonResponse
from django.views import View

class ProductListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    model = Product
    template_name = 'inventory/product_list.html'
    context_object_name = 'products'
    permission_required = 'inventory.ver_product'
    paginate_by = 50  # Cambiado a 50 por página

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        empresa = self.request.user.empresa_activa
        branch = self.request.user.branch_activa
        queryset = Product.objects.filter(empresa=empresa, branch=branch).prefetch_related('images', 'brand', 'uom')
        search = self.request.GET.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(description__icontains=search)
            )
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['view_mode'] = self.request.GET.get('view', 'list')  # 'list' o 'kanban'
        return context

class ProductCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    permission_required = 'inventory.add_product'
    success_url = reverse_lazy('inventory:product_list')

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Create Product"
        context['categories'] = Category.objects.filter(is_active=True)
        return context

    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.branch = self.request.user.branch_activa
        response = super().form_valid(form)
        # Manejo de imágenes
        with transaction.atomic():
            product = self.object
            images = self.request.FILES.getlist('images')
            for i, image_file in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    order=i
                )
            images_order = self.request.POST.get('images_order', '')
            if images_order:
                order_ids = [id.strip() for id in images_order.split(',') if id.strip()]
                for i, img_id in enumerate(order_ids):
                    if img_id.startswith('new'):
                        continue
                    try:
                        img = ProductImage.objects.get(id=img_id, product=product)
                        img.order = i
                        img.save(update_fields=['order'])
                    except ProductImage.DoesNotExist:
                        pass
        return response

class ProductUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    model = Product
    form_class = ProductForm
    template_name = 'inventory/product_form.html'
    permission_required = 'inventory.change_product'
    success_url = reverse_lazy('inventory:product_list')

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Edit Product"
        context['categories'] = Category.objects.filter(is_active=True)
        return context

    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.branch = self.request.user.branch_activa
        response = super().form_valid(form)
        # Manejo de imágenes
        with transaction.atomic():
            product = self.object
            for key, value in self.request.POST.items():
                if key.startswith('delete_image_') and value == '1':
                    try:
                        img_id = int(key.replace('delete_image_', ''))
                        ProductImage.objects.filter(id=img_id, product=product).delete()
                    except (ValueError, ProductImage.DoesNotExist):
                        pass
            images = self.request.FILES.getlist('images')
            existing_count = product.images.count()
            for i, image_file in enumerate(images):
                ProductImage.objects.create(
                    product=product,
                    image=image_file,
                    order=existing_count + i
                )
            images_order = self.request.POST.get('images_order', '')
            if images_order:
                order_ids = [id.strip() for id in images_order.split(',') if id.strip()]
                for i, img_id in enumerate(order_ids):
                    if img_id.startswith('new'):
                        continue
                    try:
                        img = ProductImage.objects.get(id=img_id, product=product)
                        img.order = i
                        img.save(update_fields=['order'])
                    except ProductImage.DoesNotExist:
                        pass
        return response

class ProductDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    model = Product
    template_name = 'inventory/product_confirm_delete.html'
    success_url = reverse_lazy('inventory:product_list')
    permission_required = 'inventory.delete_product'

    def dispatch(self, request, *args, **kwargs):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return HttpResponseForbidden('Access denied: company is inactive.')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = "Confirm Delete Product"
        return context 

class ProductSearchApiView(LoginRequiredMixin, View):
    """API endpoint para búsqueda predictiva de productos en tiempo real"""
    
    def get(self, request):
        empresa = request.user.empresa_activa
        if not empresa or not empresa.activa:
            return JsonResponse({'error': 'Access denied: company is inactive.'}, status=403)
        
        search = request.GET.get('q', '').strip()
        branch = request.user.branch_activa
        
        # Construir queryset base
        queryset = Product.objects.filter(
            empresa=empresa, 
            branch=branch
        ).prefetch_related('images', 'brand', 'uom')
        
        # Aplicar filtro de búsqueda si se proporciona
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(sku__icontains=search) |
                Q(description__icontains=search)
            )
        
        # Limitar a un máximo razonable para performance
        queryset = queryset[:2000]
        
        # Preparar datos para respuesta JSON
        products_data = []
        for product in queryset:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'sku': product.sku,
                'description': product.description or '',
                'price': float(product.price),
                'price_currency': product.price_currency.code if product.price_currency else '',
                'brand_name': product.brand.name if product.brand else '',
                'uom_name': product.uom.name if product.uom else '',
                'image_url': product.images.first().image.url if product.images.first() else None,
                'type': product.type,
                # 'is_active': product.is_active,  # Eliminado porque no existe ese campo
            })
        
        return JsonResponse({
            'products': products_data,
            'total_count': len(products_data),
            'search_term': search
        }) 