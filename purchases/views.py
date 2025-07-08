from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
)
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.utils.translation import gettext_lazy as _

from core.models import Currency
from sales.models import PaymentTerm
from inventory.models import ProductVariant

from .models import (
    Supplier, PurchaseRequest, PurchaseRequestLine, PurchaseQuotation,
    PurchaseQuotationLine, PurchaseOrder, PurchaseOrderLine, PurchaseReceipt,
    SupplierRating, ApprovalWorkflow, ApprovalLevel, ApprovalRecord
)
from .services import PurchaseService, SupplierService, ApprovalService, QuotationService
from .forms import SupplierForm


class PurchaseDashboardView(LoginRequiredMixin, TemplateView):
    """Vista del dashboard principal de compras"""
    template_name = 'purchases/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.request.user.empresa_activa
        
        # Métricas principales
        context['total_requests'] = PurchaseRequest.objects.filter(
            empresa=empresa
        ).count()
        
        context['pending_requests'] = PurchaseRequest.objects.filter(
            empresa=empresa,
            status='pending_approval'
        ).count()
        
        context['total_orders'] = PurchaseOrder.objects.filter(
            empresa=empresa
        ).count()
        
        context['overdue_orders'] = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['sent', 'confirmed'],
            expected_delivery_date__lt=timezone.now().date()
        ).count()
        
        # Solicitudes recientes
        context['recent_requests'] = PurchaseRequest.objects.filter(
            empresa=empresa
        ).order_by('-request_date')[:5]
        
        # Órdenes recientes
        context['recent_orders'] = PurchaseOrder.objects.filter(
            empresa=empresa
        ).order_by('-order_date')[:5]
        
        return context


# Vistas para Proveedores
class SupplierListView(LoginRequiredMixin, PermissionRequiredMixin, ListView):
    """Vista para listar proveedores"""
    model = Supplier
    template_name = 'purchases/supplier_list.html'
    context_object_name = 'suppliers'
    permission_required = 'purchases.view_supplier'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Supplier.objects.all().order_by('name')
        
        # Filtros
        search = self.request.GET.get('search', '')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search) |
                Q(tax_id__icontains=search) |
                Q(email__icontains=search)
            )
        
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            if status_filter == 'active':
                queryset = queryset.filter(is_active=True)
            elif status_filter == 'inactive':
                queryset = queryset.filter(is_active=False)
            elif status_filter == 'approved':
                queryset = queryset.filter(is_approved=True)
            elif status_filter == 'pending':
                queryset = queryset.filter(is_approved=False)
        
        category_filter = self.request.GET.get('category', '')
        if category_filter:
            queryset = queryset.filter(supplier_category=category_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['category_filter'] = self.request.GET.get('category', '')
        
        # Estadísticas
        context['total_suppliers'] = Supplier.objects.count()
        context['active_suppliers'] = Supplier.objects.filter(is_active=True).count()
        context['approved_suppliers'] = Supplier.objects.filter(is_approved=True).count()
        context['suppliers_with_contacts'] = Supplier.objects.filter(contact_relationships__isnull=False).distinct().count()
        
        # Categorías disponibles
        context['categories'] = Supplier.objects.values_list('supplier_category', flat=True).distinct().exclude(supplier_category='')
        
        return context


class SupplierDetailView(LoginRequiredMixin, PermissionRequiredMixin, DetailView):
    """Vista para mostrar detalles de proveedor"""
    model = Supplier
    template_name = 'purchases/supplier_detail.html'
    context_object_name = 'supplier'
    permission_required = 'purchases.view_supplier'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier = self.object
        
        # Obtener contactos relacionados
        context['contacts'] = supplier.get_contacts()
        context['primary_contact'] = supplier.get_primary_contact_object()
        
        # Estadísticas del proveedor
        context['total_orders'] = PurchaseOrder.objects.filter(supplier=supplier).count()
        context['total_requests'] = PurchaseRequest.objects.filter(supplier=supplier).count()
        context['total_purchases'] = supplier.get_total_purchases()
        context['average_rating'] = supplier.get_rating_average()
        
        # Órdenes recientes
        context['recent_orders'] = PurchaseOrder.objects.filter(supplier=supplier).order_by('-created_at')[:5]
        
        # Solicitudes recientes
        context['recent_requests'] = PurchaseRequest.objects.filter(supplier=supplier).order_by('-created_at')[:5]
        
        return context


class SupplierCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """Vista para crear proveedor"""
    model = Supplier
    form_class = SupplierForm
    template_name = 'purchases/supplier_form.html'
    permission_required = 'purchases.add_supplier'
    success_url = reverse_lazy('purchases:supplier_list')
    
    def form_valid(self, form):
        # Asignar empresa y sucursal del usuario actual
        form.instance.empresa = self.request.user.empresa
        form.instance.branch = self.request.user.branch
        form.instance.created_by = self.request.user
        
        response = super().form_valid(form)
        messages.success(self.request, _('Supplier "%(name)s" created successfully.') % {'name': self.object.name})
        return response
    
    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, _('Error creating supplier. Please check the data.'))
        return response


class SupplierUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """Vista para editar proveedor"""
    model = Supplier
    form_class = SupplierForm
    template_name = 'purchases/supplier_form.html'
    permission_required = 'purchases.change_supplier'
    
    def get_success_url(self):
        return reverse('purchases:supplier_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, _('Supplier "%(name)s" updated successfully.') % {'name': self.object.name})
        return response
    
    def form_invalid(self, form):
        response = super().form_invalid(form)
        messages.error(self.request, _('Error updating supplier. Please check the data.'))
        return response


class SupplierDeleteView(LoginRequiredMixin, PermissionRequiredMixin, DeleteView):
    """Vista para eliminar proveedor"""
    model = Supplier
    template_name = 'purchases/supplier_confirm_delete.html'
    permission_required = 'purchases.delete_supplier'
    success_url = reverse_lazy('purchases:supplier_list')
    
    def delete(self, request, *args, **kwargs):
        supplier = self.get_object()
        messages.success(request, _('Supplier "%(name)s" deleted successfully.') % {'name': supplier.name})
        return super().delete(request, *args, **kwargs)


# Vistas para Solicitudes de Compra
class PurchaseRequestListView(LoginRequiredMixin, ListView):
    """Lista de solicitudes de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_list.html'
    context_object_name = 'requests'
    paginate_by = 20
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa_activa)


class PurchaseRequestCreateView(LoginRequiredMixin, CreateView):
    """Crear solicitud de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_form.html'
    fields = [
        'title', 'description', 'priority', 'required_date', 'currency', 'budget_amount', 'delivery_location', 'notes'
    ]
    success_url = reverse_lazy('purchases:request_list')
    
    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.branch = self.request.user.branch_activa
        form.instance.requested_by = self.request.user
        messages.success(self.request, _('Purchase request created successfully'))
        return super().form_valid(form)


class PurchaseRequestDetailView(LoginRequiredMixin, DetailView):
    """Detalle de solicitud de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_detail.html'
    context_object_name = 'request'
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa_activa)


class PurchaseRequestUpdateView(LoginRequiredMixin, UpdateView):
    """Editar solicitud de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_form.html'
    fields = [
        'title', 'description', 'priority', 'required_date', 'currency', 'budget_amount', 'delivery_location', 'notes'
    ]
    success_url = reverse_lazy('purchases:request_list')
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa_activa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Purchase request updated successfully'))
        return super().form_valid(form)


class PurchaseRequestDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar solicitud de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_confirm_delete.html'
    success_url = reverse_lazy('purchases:request_list')
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa_activa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Purchase request deleted successfully'))
        return super().delete(request, *args, **kwargs)


class PurchaseRequestSubmitView(LoginRequiredMixin, DetailView):
    """Enviar solicitud a aprobación"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_submit.html'
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        request_obj = self.get_object()
        
        if request_obj.status != 'draft':
            messages.error(request, _('Only draft requests can be submitted'))
            return redirect('purchases:request_detail', pk=request_obj.pk)
        
        approval_service = ApprovalService().set_user(request.user)
        result = approval_service.initiate_approval_process(request_obj)
        
        if result['status'] == 'auto_approved':
            request_obj.status = 'approved'
            request_obj.approved_by = request.user
            request_obj.approved_date = timezone.now().date()
            messages.success(request, _('Request auto-approved'))
        else:
            request_obj.status = 'pending_approval'
            messages.success(request, _('Request submitted for approval'))
        
        request_obj.save()
        return redirect('purchases:request_detail', pk=request_obj.pk)


class PurchaseRequestApproveView(LoginRequiredMixin, DetailView):
    """Aprobar solicitud"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_approve.html'
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        request_obj = self.get_object()
        comments = request.POST.get('comments', '')
        
        approval_service = ApprovalService().set_user(request.user)
        result = approval_service.approve_request(request_obj, request.user, comments)
        
        if result['status'] == 'approved':
            request_obj.status = 'approved'
            request_obj.approved_by = request.user
            request_obj.approved_date = timezone.now().date()
            request_obj.save()
            messages.success(request, _('Request approved'))
        else:
            messages.info(request, _('Approval recorded'))
        
        return redirect('purchases:request_detail', pk=request_obj.pk)


class PurchaseRequestRejectView(LoginRequiredMixin, DetailView):
    """Rechazar solicitud"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_reject.html'
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        request_obj = self.get_object()
        reason = request.POST.get('reason', '')
        
        if not reason:
            messages.error(request, _('Rejection reason is required'))
            return redirect('purchases:request_reject', pk=request_obj.pk)
        
        approval_service = ApprovalService().set_user(request.user)
        result = approval_service.reject_request(request_obj, request.user, reason)
        
        request_obj.status = 'rejected'
        request_obj.rejection_reason = reason
        request_obj.save()
        
        messages.success(request, _('Request rejected'))
        return redirect('purchases:request_detail', pk=request_obj.pk)


class PurchaseRequestConvertView(LoginRequiredMixin, DetailView):
    """Convertir solicitud a orden de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_convert.html'
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        request_obj = self.get_object()
        
        if request_obj.status != 'approved':
            messages.error(request, _('Only approved requests can be converted'))
            return redirect('purchases:request_detail', pk=request_obj.pk)
        
        supplier_id = request.POST.get('supplier_id')
        expected_delivery_date = request.POST.get('expected_delivery_date')
        
        if not supplier_id:
            messages.error(request, _('Supplier is required'))
            return redirect('purchases:request_convert', pk=request_obj.pk)
        
        try:
            supplier = Supplier.objects.get(id=supplier_id, empresa=self.request.user.empresa_activa)
        except Supplier.DoesNotExist:
            messages.error(request, _('Supplier not found'))
            return redirect('purchases:request_convert', pk=request_obj.pk)
        
        purchase_service = PurchaseService().set_user(request.user)
        order = purchase_service.create_purchase_order_from_request(
            request=request_obj,
            supplier=supplier,
            expected_delivery_date=expected_delivery_date
        )
        
        request_obj.status = 'converted'
        request_obj.save()
        
        messages.success(request, _('Request converted to order'))
        return redirect('purchases:order_detail', pk=order.pk)


# Vistas para Cotizaciones
class PurchaseQuotationListView(LoginRequiredMixin, ListView):
    """Lista de cotizaciones"""
    model = PurchaseQuotation
    template_name = 'purchases/quotations/quotation_list.html'
    context_object_name = 'quotations'
    paginate_by = 20
    
    def get_queryset(self):
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa_activa)


class PurchaseQuotationCreateView(LoginRequiredMixin, CreateView):
    """Crear cotización"""
    model = PurchaseQuotation
    template_name = 'purchases/quotations/quotation_form.html'
    fields = [
        'supplier', 'purchase_request', 'valid_until', 'currency', 'payment_terms',
        'delivery_terms', 'delivery_time', 'notes'
    ]
    success_url = reverse_lazy('purchases:quotation_list')
    
    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.branch = self.request.user.branch_activa
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Quotation created successfully'))
        return super().form_valid(form)


class PurchaseQuotationDetailView(LoginRequiredMixin, DetailView):
    """Detalle de cotización"""
    model = PurchaseQuotation
    template_name = 'purchases/quotations/quotation_detail.html'
    context_object_name = 'quotation'
    
    def get_queryset(self):
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa_activa)


class PurchaseQuotationUpdateView(LoginRequiredMixin, UpdateView):
    """Editar cotización"""
    model = PurchaseQuotation
    template_name = 'purchases/quotations/quotation_form.html'
    fields = [
        'supplier', 'purchase_request', 'valid_until', 'currency', 'payment_terms',
        'delivery_terms', 'delivery_time', 'notes'
    ]
    success_url = reverse_lazy('purchases:quotation_list')
    
    def get_queryset(self):
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa_activa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Quotation updated successfully'))
        return super().form_valid(form)


class PurchaseQuotationDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar cotización"""
    model = PurchaseQuotation
    template_name = 'purchases/quotations/quotation_confirm_delete.html'
    success_url = reverse_lazy('purchases:quotation_list')
    
    def get_queryset(self):
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa_activa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Quotation deleted successfully'))
        return super().delete(request, *args, **kwargs)


class PurchaseQuotationEvaluateView(LoginRequiredMixin, DetailView):
    """Evaluar cotización"""
    model = PurchaseQuotation
    template_name = 'purchases/quotations/quotation_evaluate.html'
    
    def get_queryset(self):
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        quotation = self.get_object()
        
        quotation_service = QuotationService().set_user(request.user)
        
        # Obtener datos de evaluación
        quality_score = request.POST.get('quality_score')
        delivery_score = request.POST.get('delivery_score')
        communication_score = request.POST.get('communication_score')
        price_score = request.POST.get('price_score')
        service_score = request.POST.get('service_score')
        
        # Comentarios
        quality_comments = request.POST.get('quality_comments', '')
        delivery_comments = request.POST.get('delivery_comments', '')
        communication_comments = request.POST.get('communication_comments', '')
        price_comments = request.POST.get('price_comments', '')
        service_comments = request.POST.get('service_comments', '')
        general_comments = request.POST.get('general_comments', '')
        recommendations = request.POST.get('recommendations', '')
        would_recommend = request.POST.get('would_recommend') == 'on'
        
        # Crear evaluación
        result = quotation_service.evaluate_quotation(
            quotation=quotation,
            evaluator=request.user,
            quality_score=quality_score,
            delivery_score=delivery_score,
            communication_score=communication_score,
            price_score=price_score,
            service_score=service_score,
            quality_comments=quality_comments,
            delivery_comments=delivery_comments,
            communication_comments=communication_comments,
            price_comments=price_comments,
            service_comments=service_comments,
            general_comments=general_comments,
            recommendations=recommendations,
            would_recommend=would_recommend
        )
        
        messages.success(request, _('Quotation evaluated successfully'))
        return redirect('purchases:quotation_detail', pk=quotation.pk)


class PurchaseQuotationSelectView(LoginRequiredMixin, DetailView):
    """Seleccionar cotización"""
    model = PurchaseQuotation
    template_name = 'purchases/quotations/quotation_select.html'
    
    def get_queryset(self):
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        quotation = self.get_object()
        reason = request.POST.get('reason', '')
        
        quotation_service = QuotationService().set_user(request.user)
        result = quotation_service.select_quotation(quotation, request.user, reason)
        
        messages.success(request, _('Quotation selected'))
        return redirect('purchases:quotation_detail', pk=quotation.pk)


class PurchaseQuotationCompareView(LoginRequiredMixin, TemplateView):
    """Comparar cotizaciones"""
    template_name = 'purchases/quotations/quotation_compare.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request_id = self.request.GET.get('request_id')
        
        if request_id:
            try:
                purchase_request = PurchaseRequest.objects.get(
                    id=request_id, empresa=self.request.user.empresa_activa
                )
                quotation_service = QuotationService().set_user(self.request.user)
                context['comparison'] = quotation_service.compare_quotations(purchase_request)
                context['request'] = purchase_request
            except PurchaseRequest.DoesNotExist:
                messages.error(self.request, _('Purchase request not found'))
        
        return context


# Vistas para Órdenes de Compra
class PurchaseOrderListView(LoginRequiredMixin, ListView):
    """Lista de órdenes de compra"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_list.html'
    context_object_name = 'orders'
    paginate_by = 20
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa_activa)


class PurchaseOrderCreateView(LoginRequiredMixin, CreateView):
    """Crear orden de compra"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_form.html'
    fields = [
        'supplier', 'purchase_request', 'quotation', 'expected_delivery_date',
        'currency', 'payment_terms', 'delivery_terms', 'delivery_address', 'notes'
    ]
    success_url = reverse_lazy('purchases:order_list')
    
    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.branch = self.request.user.branch_activa
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Purchase order created successfully'))
        return super().form_valid(form)


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    """Detalle de orden de compra"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_detail.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa_activa)


class PurchaseOrderUpdateView(LoginRequiredMixin, UpdateView):
    """Editar orden de compra"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_form.html'
    fields = [
        'supplier', 'purchase_request', 'quotation', 'expected_delivery_date',
        'currency', 'payment_terms', 'delivery_terms', 'delivery_address', 'notes'
    ]
    success_url = reverse_lazy('purchases:order_list')
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa_activa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Purchase order updated successfully'))
        return super().form_valid(form)


class PurchaseOrderDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar orden de compra"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_confirm_delete.html'
    success_url = reverse_lazy('purchases:order_list')
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa_activa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Purchase order deleted successfully'))
        return super().delete(request, *args, **kwargs)


class PurchaseOrderSendView(LoginRequiredMixin, DetailView):
    """Enviar orden al proveedor"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_send.html'
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        order = self.get_object()
        order.send_to_supplier()
        messages.success(request, _('Order sent to supplier'))
        return redirect('purchases:order_detail', pk=order.pk)


class PurchaseOrderConfirmView(LoginRequiredMixin, DetailView):
    """Confirmar orden"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_confirm.html'
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        order = self.get_object()
        order.confirm(request.user)
        messages.success(request, _('Order confirmed'))
        return redirect('purchases:order_detail', pk=order.pk)


class PurchaseOrderCancelView(LoginRequiredMixin, DetailView):
    """Cancelar orden"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_cancel.html'
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        order = self.get_object()
        reason = request.POST.get('reason', '')
        
        if not order.can_cancel():
            messages.error(request, _('Order cannot be cancelled in current status'))
            return redirect('purchases:order_detail', pk=order.pk)
        
        order.cancel(request.user, reason)
        messages.success(request, _('Order cancelled'))
        return redirect('purchases:order_detail', pk=order.pk)


class PurchaseOrderDuplicateView(LoginRequiredMixin, DetailView):
    """Duplicar orden"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_duplicate.html'
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        order = self.get_object()
        
        purchase_service = PurchaseService().set_user(request.user)
        new_order = purchase_service.duplicate_order(order, request.user)
        
        messages.success(request, _('Order duplicated successfully'))
        return redirect('purchases:order_detail', pk=new_order.pk)


class PurchaseOrderReceiveView(LoginRequiredMixin, DetailView):
    """Recibir orden"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_receive.html'
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        order = self.get_object()
        
        # Lógica para recibir productos
        # Esta vista manejaría la creación de recepciones
        
        messages.success(request, _('Products received successfully'))
        return redirect('purchases:order_detail', pk=order.pk)


# Vistas para Recepciones
class PurchaseReceiptListView(LoginRequiredMixin, ListView):
    """Lista de recepciones"""
    model = PurchaseReceipt
    template_name = 'purchases/receipts/receipt_list.html'
    context_object_name = 'receipts'
    paginate_by = 20
    
    def get_queryset(self):
        return PurchaseReceipt.objects.filter(empresa=self.request.user.empresa_activa)


class PurchaseReceiptDetailView(LoginRequiredMixin, DetailView):
    """Detalle de recepción"""
    model = PurchaseReceipt
    template_name = 'purchases/receipts/receipt_detail.html'
    context_object_name = 'receipt'
    
    def get_queryset(self):
        return PurchaseReceipt.objects.filter(empresa=self.request.user.empresa_activa)


class PurchaseReceiptApproveView(LoginRequiredMixin, DetailView):
    """Aprobar recepción"""
    model = PurchaseReceipt
    template_name = 'purchases/receipts/receipt_approve.html'
    
    def get_queryset(self):
        return PurchaseReceipt.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        receipt = self.get_object()
        quality_score = request.POST.get('quality_score')
        quality_notes = request.POST.get('quality_notes', '')
        
        receipt.approve(request.user, quality_score, quality_notes)
        messages.success(request, _('Receipt approved'))
        return redirect('purchases:receipt_detail', pk=receipt.pk)


class PurchaseReceiptRejectView(LoginRequiredMixin, DetailView):
    """Rechazar recepción"""
    model = PurchaseReceipt
    template_name = 'purchases/receipts/receipt_reject.html'
    
    def get_queryset(self):
        return PurchaseReceipt.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        receipt = self.get_object()
        reason = request.POST.get('reason', '')
        
        receipt.reject(request.user, reason)
        messages.success(request, _('Receipt rejected'))
        return redirect('purchases:receipt_detail', pk=receipt.pk)


class PurchaseReceiptReturnView(LoginRequiredMixin, DetailView):
    """Devolver recepción al proveedor"""
    model = PurchaseReceipt
    template_name = 'purchases/receipts/receipt_return.html'
    
    def get_queryset(self):
        return PurchaseReceipt.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        receipt = self.get_object()
        reason = request.POST.get('reason', '')
        
        receipt.return_to_supplier(request.user, reason)
        messages.success(request, _('Receipt returned to supplier'))
        return redirect('purchases:receipt_detail', pk=receipt.pk)


# Vistas para Evaluaciones de Proveedores
class SupplierRatingListView(LoginRequiredMixin, ListView):
    """Lista de evaluaciones de proveedores"""
    model = SupplierRating
    template_name = 'purchases/ratings/rating_list.html'
    context_object_name = 'ratings'
    paginate_by = 20
    
    def get_queryset(self):
        return SupplierRating.objects.filter(empresa=self.request.user.empresa_activa)


class SupplierRatingCreateView(LoginRequiredMixin, CreateView):
    """Crear evaluación de proveedor"""
    model = SupplierRating
    template_name = 'purchases/ratings/rating_form.html'
    fields = [
        'supplier', 'purchase_order', 'period_start', 'period_end',
        'quality_score', 'delivery_score', 'communication_score', 'price_score', 'service_score',
        'quality_comments', 'delivery_comments', 'communication_comments', 'price_comments',
        'service_comments', 'general_comments', 'recommendations', 'would_recommend'
    ]
    success_url = reverse_lazy('purchases:rating_list')
    
    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.evaluated_by = self.request.user
        messages.success(self.request, _('Supplier rating created successfully'))
        return super().form_valid(form)


class SupplierRatingDetailView(LoginRequiredMixin, DetailView):
    """Detalle de evaluación de proveedor"""
    model = SupplierRating
    template_name = 'purchases/ratings/rating_detail.html'
    context_object_name = 'rating'
    
    def get_queryset(self):
        return SupplierRating.objects.filter(empresa=self.request.user.empresa_activa)


class SupplierRatingUpdateView(LoginRequiredMixin, UpdateView):
    """Editar evaluación de proveedor"""
    model = SupplierRating
    template_name = 'purchases/ratings/rating_form.html'
    fields = [
        'supplier', 'purchase_order', 'period_start', 'period_end',
        'quality_score', 'delivery_score', 'communication_score', 'price_score', 'service_score',
        'quality_comments', 'delivery_comments', 'communication_comments', 'price_comments',
        'service_comments', 'general_comments', 'recommendations', 'would_recommend'
    ]
    success_url = reverse_lazy('purchases:rating_list')
    
    def get_queryset(self):
        return SupplierRating.objects.filter(empresa=self.request.user.empresa_activa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Supplier rating updated successfully'))
        return super().form_valid(form)


class SupplierRatingDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar evaluación de proveedor"""
    model = SupplierRating
    template_name = 'purchases/ratings/rating_confirm_delete.html'
    success_url = reverse_lazy('purchases:rating_list')
    
    def get_queryset(self):
        return SupplierRating.objects.filter(empresa=self.request.user.empresa_activa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Supplier rating deleted successfully'))
        return super().delete(request, *args, **kwargs)


class SupplierRatingSubmitView(LoginRequiredMixin, DetailView):
    """Enviar evaluación para revisión"""
    model = SupplierRating
    template_name = 'purchases/ratings/rating_submit.html'
    
    def get_queryset(self):
        return SupplierRating.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        rating = self.get_object()
        rating.submit(request.user)
        messages.success(request, _('Rating submitted for review'))
        return redirect('purchases:rating_detail', pk=rating.pk)


class SupplierRatingReviewView(LoginRequiredMixin, DetailView):
    """Revisar evaluación"""
    model = SupplierRating
    template_name = 'purchases/ratings/rating_review.html'
    
    def get_queryset(self):
        return SupplierRating.objects.filter(empresa=self.request.user.empresa_activa)
    
    def post(self, request, *args, **kwargs):
        rating = self.get_object()
        approved = request.POST.get('approved') == 'on'
        
        rating.review(request.user, approved)
        messages.success(request, _('Rating reviewed'))
        return redirect('purchases:rating_detail', pk=rating.pk)


# Vistas para Flujos de Aprobación
class ApprovalWorkflowListView(LoginRequiredMixin, ListView):
    """Lista de flujos de aprobación"""
    model = ApprovalWorkflow
    template_name = 'purchases/approval/workflow_list.html'
    context_object_name = 'workflows'
    paginate_by = 20
    
    def get_queryset(self):
        return ApprovalWorkflow.objects.filter(empresa=self.request.user.empresa_activa)


class ApprovalWorkflowCreateView(LoginRequiredMixin, CreateView):
    """Crear flujo de aprobación"""
    model = ApprovalWorkflow
    template_name = 'purchases/approval/workflow_form.html'
    fields = ['name', 'description', 'min_amount', 'max_amount', 'requires_all_approvals']
    success_url = reverse_lazy('purchases:workflow_list')
    
    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa_activa
        form.instance.branch = self.request.user.branch_activa
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Approval workflow created successfully'))
        return super().form_valid(form)


class ApprovalWorkflowDetailView(LoginRequiredMixin, DetailView):
    """Detalle de flujo de aprobación"""
    model = ApprovalWorkflow
    template_name = 'purchases/approval/workflow_detail.html'
    context_object_name = 'workflow'
    
    def get_queryset(self):
        return ApprovalWorkflow.objects.filter(empresa=self.request.user.empresa_activa)


class ApprovalWorkflowUpdateView(LoginRequiredMixin, UpdateView):
    """Editar flujo de aprobación"""
    model = ApprovalWorkflow
    template_name = 'purchases/approval/workflow_form.html'
    fields = ['name', 'description', 'min_amount', 'max_amount', 'requires_all_approvals']
    success_url = reverse_lazy('purchases:workflow_list')
    
    def get_queryset(self):
        return ApprovalWorkflow.objects.filter(empresa=self.request.user.empresa_activa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Approval workflow updated successfully'))
        return super().form_valid(form)


class ApprovalWorkflowDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar flujo de aprobación"""
    model = ApprovalWorkflow
    template_name = 'purchases/approval/workflow_confirm_delete.html'
    success_url = reverse_lazy('purchases:workflow_list')
    
    def get_queryset(self):
        return ApprovalWorkflow.objects.filter(empresa=self.request.user.empresa_activa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Approval workflow deleted successfully'))
        return super().delete(request, *args, **kwargs)


# Vistas para Niveles de Aprobación
class ApprovalLevelListView(LoginRequiredMixin, ListView):
    """Lista de niveles de aprobación"""
    model = ApprovalLevel
    template_name = 'purchases/approval/level_list.html'
    context_object_name = 'levels'
    paginate_by = 20


class ApprovalLevelCreateView(LoginRequiredMixin, CreateView):
    """Crear nivel de aprobación"""
    model = ApprovalLevel
    template_name = 'purchases/approval/level_form.html'
    fields = [
        'workflow', 'name', 'priority', 'approval_type', 'approvers', 'roles',
        'groups', 'requires_all_approvers', 'max_approval_time'
    ]
    success_url = reverse_lazy('purchases:level_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Approval level created successfully'))
        return super().form_valid(form)


class ApprovalLevelDetailView(LoginRequiredMixin, DetailView):
    """Detalle de nivel de aprobación"""
    model = ApprovalLevel
    template_name = 'purchases/approval/level_detail.html'
    context_object_name = 'level'


class ApprovalLevelUpdateView(LoginRequiredMixin, UpdateView):
    """Editar nivel de aprobación"""
    model = ApprovalLevel
    template_name = 'purchases/approval/level_form.html'
    fields = [
        'workflow', 'name', 'priority', 'approval_type', 'approvers', 'roles',
        'groups', 'requires_all_approvers', 'max_approval_time'
    ]
    success_url = reverse_lazy('purchases:level_list')
    
    def form_valid(self, form):
        messages.success(self.request, _('Approval level updated successfully'))
        return super().form_valid(form)


class ApprovalLevelDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar nivel de aprobación"""
    model = ApprovalLevel
    template_name = 'purchases/approval/level_confirm_delete.html'
    success_url = reverse_lazy('purchases:level_list')
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Approval level deleted successfully'))
        return super().delete(request, *args, **kwargs)


# Vistas para Reportes
class PurchaseReportsView(LoginRequiredMixin, TemplateView):
    """Vista principal de reportes"""
    template_name = 'purchases/reports/reports.html'


class PurchaseSummaryReportView(LoginRequiredMixin, TemplateView):
    """Reporte resumen de compras"""
    template_name = 'purchases/reports/summary_report.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.request.user.empresa_activa
        
        # Obtener período
        start_date = self.request.GET.get('start_date')
        end_date = self.request.GET.get('end_date')
        
        if start_date:
            start_date = timezone.datetime.strptime(start_date, '%Y-%m-%d').date()
        else:
            start_date = timezone.now().date() - timedelta(days=90)
        
        if end_date:
            end_date = timezone.datetime.strptime(end_date, '%Y-%m-%d').date()
        else:
            end_date = timezone.now().date()
        
        # Calcular métricas
        context['start_date'] = start_date
        context['end_date'] = end_date
        
        context['total_requests'] = PurchaseRequest.objects.filter(
            empresa=empresa,
            request_date__range=[start_date, end_date]
        ).count()
        
        context['approved_requests'] = PurchaseRequest.objects.filter(
            empresa=empresa,
            status='approved',
            request_date__range=[start_date, end_date]
        ).count()
        
        context['total_orders'] = PurchaseOrder.objects.filter(
            empresa=empresa,
            order_date__range=[start_date, end_date]
        ).count()
        
        context['total_spent'] = PurchaseOrder.objects.filter(
            empresa=empresa,
            status__in=['confirmed', 'partially_received', 'received'],
            order_date__range=[start_date, end_date]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        return context


class SupplierPerformanceReportView(LoginRequiredMixin, TemplateView):
    """Reporte de rendimiento de proveedores"""
    template_name = 'purchases/reports/supplier_performance_report.html'


class SpendingAnalysisReportView(LoginRequiredMixin, TemplateView):
    """Reporte de análisis de gastos"""
    template_name = 'purchases/reports/spending_analysis_report.html'


class DeliveryPerformanceReportView(LoginRequiredMixin, TemplateView):
    """Reporte de rendimiento de entregas"""
    template_name = 'purchases/reports/delivery_performance_report.html'


# Vistas para Configuración
class PurchaseSettingsView(LoginRequiredMixin, TemplateView):
    """Vista de configuración de compras"""
    template_name = 'purchases/settings.html'


# ============================================================================
# VISTAS UNIFICADAS PARA EL FLUJO DE COMPRAS
# ============================================================================

class PurchaseDocumentListView(LoginRequiredMixin, ListView):
    """Vista unificada para listar solicitudes y órdenes de compra"""
    template_name = 'purchases/orders/purchase_order_list.html'
    context_object_name = 'page_obj'
    paginate_by = 20
    
    def get_queryset(self):
        """Obtener documentos según filtros"""
        queryset = []
        
        # Obtener solicitudes
        requests = PurchaseRequest.objects.filter(
            empresa=self.request.user.empresa_activa
        ).select_related('requested_by', 'currency')
        
        # Obtener órdenes
        orders = PurchaseOrder.objects.filter(
            empresa=self.request.user.empresa_activa
        ).select_related('supplier', 'currency', 'created_by')
        
        # Aplicar filtros
        document_type = self.request.GET.get('document_type')
        status = self.request.GET.get('status')
        supplier = self.request.GET.get('supplier')
        date_range = self.request.GET.get('date_range')
        
        if document_type == 'request':
            queryset = list(requests)
        elif document_type == 'order':
            queryset = list(orders)
        else:
            # Combinar ambos tipos
            for request in requests:
                request.document_type = 'request'
                request.number = request.request_number
                request.title = request.title
                request.document_date = request.request_date
                request.total_amount = request.total_amount or 0
                request.status = request.status
                request.supplier = None
                request.created_by = request.requested_by
                queryset.append(request)
            
            for order in orders:
                order.document_type = 'order'
                order.number = order.order_number
                order.title = order.notes or f"Order {order.order_number}"
                order.document_date = order.order_date
                order.total_amount = order.total_amount or 0
                order.status = order.status
                queryset.append(order)
        
        # Filtrar por estado
        if status:
            queryset = [doc for doc in queryset if doc.status == status]
        
        # Filtrar por proveedor (solo para órdenes)
        if supplier:
            queryset = [doc for doc in queryset if hasattr(doc, 'supplier') and doc.supplier and doc.supplier.id == int(supplier)]
        
        # Filtrar por rango de fechas
        if date_range:
            from django.utils import timezone
            from datetime import timedelta
            
            today = timezone.now().date()
            if date_range == 'today':
                queryset = [doc for doc in queryset if doc.document_date == today]
            elif date_range == 'week':
                week_ago = today - timedelta(days=7)
                queryset = [doc for doc in queryset if doc.document_date >= week_ago]
            elif date_range == 'month':
                month_ago = today - timedelta(days=30)
                queryset = [doc for doc in queryset if doc.document_date >= month_ago]
            elif date_range == 'quarter':
                quarter_ago = today - timedelta(days=90)
                queryset = [doc for doc in queryset if doc.document_date >= quarter_ago]
            elif date_range == 'year':
                year_ago = today - timedelta(days=365)
                queryset = [doc for doc in queryset if doc.document_date >= year_ago]
        
        # Ordenar por fecha de creación (más reciente primero)
        queryset.sort(key=lambda x: x.created_at, reverse=True)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Estadísticas
        requests = PurchaseRequest.objects.filter(empresa=self.request.user.empresa_activa)
        orders = PurchaseOrder.objects.filter(empresa=self.request.user.empresa_activa)
        
        context.update({
            'total_documents': requests.count() + orders.count(),
            'pending_approval': requests.filter(status='submitted').count(),
            'active_orders': orders.filter(status__in=['order_sent', 'order_confirmed', 'partially_received']).count(),
            'total_value': sum([order.total_amount or 0 for order in orders]),
            'suppliers': Supplier.objects.filter(empresa=self.request.user.empresa_activa),
            'payment_terms': PaymentTerm.objects.filter(is_active=True).order_by('name'),
        })
        
        return context


class PurchaseDocumentCreateView(LoginRequiredMixin, TemplateView):
    """Vista unificada para crear solicitudes y órdenes de compra"""
    template_name = 'purchases/orders/purchase_order_form.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Determinar tipo de documento por defecto
        document_type = self.request.GET.get('type', 'request')
        
        context.update({
            'document_type': document_type,
            'document': None,
            'suppliers': Supplier.objects.filter(empresa=self.request.user.empresa_activa),
            'currencies': Currency.objects.all(),
            'products': ProductVariant.objects.filter(empresa=self.request.user.empresa_activa),
            'payment_terms': PaymentTerm.objects.filter(is_active=True).order_by('name'),
            'today': timezone.now().date(),
        })
        
        return context
    
    def post(self, request, *args, **kwargs):
        """Manejar la creación del documento"""
        document_type = self.request.POST.get('document_type', 'request')
        
        if document_type == 'request':
            # Crear solicitud de compra
            request_obj = PurchaseRequest.objects.create(
                empresa=self.request.user.empresa_activa,
                branch=self.request.user.branch_activa,
                title=self.request.POST.get('title'),
                description=self.request.POST.get('notes', ''),
                priority=self.request.POST.get('priority', 'medium'),
                required_date=self.request.POST.get('document_date'),
                currency_id=self.request.POST.get('currency'),
                budget_amount=self.request.POST.get('budget_amount'),
                requested_by=self.request.user,
                status='draft'
            )
            
            # Crear líneas de solicitud
            self._create_request_lines(request_obj)
            
            messages.success(self.request, _('Purchase request created successfully'))
            return redirect('purchases:document_detail', pk=request_obj.pk)
        
        else:
            # Crear orden de compra
            supplier_id = self.request.POST.get('supplier')
            if not supplier_id:
                messages.error(self.request, _('Supplier is required for purchase orders'))
                return self.get(request, *args, **kwargs)
            
            order = PurchaseOrder.objects.create(
                empresa=self.request.user.empresa_activa,
                branch=self.request.user.branch_activa,
                supplier_id=supplier_id,
                expected_delivery_date=self.request.POST.get('document_date'),
                currency_id=self.request.POST.get('currency'),
                payment_terms=self.request.POST.get('payment_terms', ''),
                delivery_terms=self.request.POST.get('delivery_terms', ''),
                delivery_address=self.request.POST.get('delivery_address', ''),
                notes=self.request.POST.get('notes', ''),
                created_by=self.request.user,
                status='draft'
            )
            
            # Crear líneas de orden
            self._create_order_lines(order)
            
            messages.success(self.request, _('Purchase order created successfully'))
            return redirect('purchases:document_detail', pk=order.pk)
    
    def _create_request_lines(self, request_obj):
        """Crear líneas de solicitud desde el formulario"""
        line_counter = 1
        while f'line_{line_counter}_product' in self.request.POST:
            product_id = self.request.POST.get(f'line_{line_counter}_product')
            quantity = self.request.POST.get(f'line_{line_counter}_quantity')
            price = self.request.POST.get(f'line_{line_counter}_price')
            
            if product_id and quantity:
                try:
                    product = ProductVariant.objects.get(id=product_id)
                    PurchaseRequestLine.objects.create(
                        purchase_request=request_obj,
                        product_variant=product,
                        quantity=quantity,
                        unit_of_measure=product.product.unit_of_measure,
                        estimated_unit_price=price or 0,
                        currency=request_obj.currency,
                        status='pending'
                    )
                except ProductVariant.DoesNotExist:
                    pass
            
            line_counter += 1
    
    def _create_order_lines(self, order):
        """Crear líneas de orden desde el formulario"""
        line_counter = 1
        while f'line_{line_counter}_product' in self.request.POST:
            product_id = self.request.POST.get(f'line_{line_counter}_product')
            quantity = self.request.POST.get(f'line_{line_counter}_quantity')
            price = self.request.POST.get(f'line_{line_counter}_price')
            
            if product_id and quantity:
                try:
                    product = ProductVariant.objects.get(id=product_id)
                    PurchaseOrderLine.objects.create(
                        purchase_order=order,
                        product_variant=product,
                        quantity=quantity,
                        unit_of_measure=product.product.unit_of_measure,
                        unit_price=price or 0,
                        status='pending'
                    )
                except ProductVariant.DoesNotExist:
                    pass
            
            line_counter += 1


class PurchaseDocumentUpdateView(LoginRequiredMixin, UpdateView):
    """Vista unificada para editar solicitudes y órdenes de compra"""
    template_name = 'purchases/orders/purchase_order_form.html'
    
    def get_object(self, queryset=None):
        """Obtener objeto (solicitud u orden) según el ID"""
        pk = self.kwargs.get('pk')
        
        # Intentar obtener solicitud
        try:
            return PurchaseRequest.objects.get(
                id=pk, 
                empresa=self.request.user.empresa_activa
            )
        except PurchaseRequest.DoesNotExist:
            pass
        
        # Intentar obtener orden
        try:
            return PurchaseOrder.objects.get(
                id=pk, 
                empresa=self.request.user.empresa_activa
            )
        except PurchaseOrder.DoesNotExist:
            raise Http404(_('Document not found'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Determinar tipo de documento
        if isinstance(self.object, PurchaseRequest):
            document_type = 'request'
        else:
            document_type = 'order'
        
        context.update({
            'document_type': document_type,
            'document': self.object,
            'suppliers': Supplier.objects.filter(empresa=self.request.user.empresa_activa),
            'currencies': Currency.objects.all(),
            'products': ProductVariant.objects.filter(empresa=self.request.user.empresa_activa),
            'payment_terms': PaymentTerm.objects.filter(is_active=True).order_by('name'),
            'today': timezone.now().date(),
        })
        
        return context
    
    def form_valid(self, form):
        document_type = self.request.POST.get('document_type', 'request')
        
        if document_type == 'request' and isinstance(self.object, PurchaseRequest):
            # Actualizar solicitud
            self.object.title = self.request.POST.get('title')
            self.object.description = self.request.POST.get('notes', '')
            self.object.priority = self.request.POST.get('priority', 'medium')
            self.object.required_date = self.request.POST.get('document_date')
            self.object.currency_id = self.request.POST.get('currency')
            self.object.budget_amount = self.request.POST.get('budget_amount')
            self.object.save()
            
            messages.success(self.request, _('Purchase request updated successfully'))
        
        elif document_type == 'order' and isinstance(self.object, PurchaseOrder):
            # Actualizar orden
            supplier_id = self.request.POST.get('supplier')
            if not supplier_id:
                messages.error(self.request, _('Supplier is required for purchase orders'))
                return self.form_invalid(form)
            
            self.object.supplier_id = supplier_id
            self.object.expected_delivery_date = self.request.POST.get('document_date')
            self.object.currency_id = self.request.POST.get('currency')
            self.object.payment_terms = self.request.POST.get('payment_terms', '')
            self.object.delivery_terms = self.request.POST.get('delivery_terms', '')
            self.object.delivery_address = self.request.POST.get('delivery_address', '')
            self.object.notes = self.request.POST.get('notes', '')
            self.object.save()
            
            messages.success(self.request, _('Purchase order updated successfully'))
        
        return redirect('purchases:document_detail', pk=self.object.pk)


class PurchaseDocumentDetailView(LoginRequiredMixin, DetailView):
    """Vista unificada para mostrar detalles de solicitudes y órdenes de compra"""
    template_name = 'purchases/orders/purchase_order_details.html'
    context_object_name = 'document'
    
    def get_object(self, queryset=None):
        """Obtener objeto (solicitud u orden) según el ID"""
        pk = self.kwargs.get('pk')
        
        # Intentar obtener solicitud
        try:
            return PurchaseRequest.objects.select_related(
                'requested_by', 'currency', 'delivery_location'
            ).prefetch_related('lines__product_variant').get(
                id=pk, 
                empresa=self.request.user.empresa_activa
            )
        except PurchaseRequest.DoesNotExist:
            pass
        
        # Intentar obtener orden
        try:
            return PurchaseOrder.objects.select_related(
                'supplier', 'currency', 'created_by', 'purchase_request'
            ).prefetch_related('lines__product_variant').get(
                id=pk, 
                empresa=self.request.user.empresa_activa
            )
        except PurchaseOrder.DoesNotExist:
            raise Http404(_('Document not found'))
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Determinar tipo de documento
        if isinstance(self.object, PurchaseRequest):
            context['document_type'] = 'request'
            # Obtener logs de aprobación para solicitudes
            context['approval_logs'] = ApprovalRecord.objects.filter(
                purchase_request=self.object
            ).order_by('-created_at')
        else:
            context['document_type'] = 'order'
            # Obtener logs de aprobación para órdenes
            context['approval_logs'] = ApprovalRecord.objects.filter(
                purchase_order=self.object
            ).order_by('-created_at')
        
        return context


# ============================================================================
# VISTAS DE ACCIONES PARA EL WORKFLOW
# ============================================================================

class PurchaseDocumentActionView(LoginRequiredMixin, View):
    """Vista para manejar acciones del workflow de documentos de compra"""
    
    def post(self, request, pk, action):
        """Manejar acciones del workflow"""
        # Obtener documento
        try:
            document = PurchaseRequest.objects.get(
                id=pk, 
                empresa=request.user.empresa_activa
            )
            document_type = 'request'
        except PurchaseRequest.DoesNotExist:
            try:
                document = PurchaseOrder.objects.get(
                    id=pk, 
                    empresa=request.user.empresa_activa
                )
                document_type = 'order'
            except PurchaseOrder.DoesNotExist:
                raise Http404(_('Document not found'))
        
        # Ejecutar acción según el tipo
        if action == 'submit':
            return self._submit_document(request, document, document_type)
        elif action == 'approve':
            return self._approve_document(request, document, document_type)
        elif action == 'reject':
            return self._reject_document(request, document, document_type)
        elif action == 'request_quotation':
            return self._request_quotation(request, document, document_type)
        elif action == 'create_order':
            return self._create_order(request, document, document_type)
        elif action == 'send_order':
            return self._send_order(request, document, document_type)
        elif action == 'confirm_order':
            return self._confirm_order(request, document, document_type)
        elif action == 'cancel':
            return self._cancel_document(request, document, document_type)
        else:
            messages.error(request, _('Invalid action'))
            return redirect('purchases:document_detail', pk=pk)
    
    def _submit_document(self, request, document, document_type):
        """Enviar documento para aprobación"""
        if document_type == 'request':
            document.status = 'submitted'
            document.save()
            
            # Crear log de aprobación
            ApprovalRecord.objects.create(
                purchase_request=document,
                user=request.user,
                action='submitted',
                reason=request.POST.get('reason', 'Document submitted for approval')
            )
            
            messages.success(request, _('Request submitted for approval'))
        else:
            messages.error(request, _('Orders cannot be submitted for approval'))
        
        return redirect('purchases:document_detail', pk=document.pk)
    
    def _approve_document(self, request, document, document_type):
        """Aprobar documento"""
        if document_type == 'request':
            document.status = 'approved'
            document.approved_by = request.user
            document.approved_date = timezone.now().date()
            document.save()
            
            # Crear log de aprobación
            ApprovalRecord.objects.create(
                purchase_request=document,
                user=request.user,
                action='approved',
                reason=request.POST.get('reason', 'Document approved')
            )
            
            messages.success(request, _('Request approved'))
        else:
            messages.error(request, _('Orders cannot be approved'))
        
        return redirect('purchases:document_detail', pk=document.pk)
    
    def _reject_document(self, request, document, document_type):
        """Rechazar documento"""
        if document_type == 'request':
            document.status = 'rejected'
            document.approved_by = request.user
            document.rejection_reason = request.POST.get('reason', '')
            document.save()
            
            # Crear log de rechazo
            ApprovalRecord.objects.create(
                purchase_request=document,
                user=request.user,
                action='rejected',
                reason=request.POST.get('reason', 'Document rejected')
            )
            
            messages.success(request, _('Request rejected'))
        else:
            messages.error(request, _('Orders cannot be rejected'))
        
        return redirect('purchases:document_detail', pk=document.pk)
    
    def _request_quotation(self, request, document, document_type):
        """Solicitar cotización"""
        if document_type == 'request' and document.status == 'approved':
            document.status = 'quotation_requested'
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_request=document,
                user=request.user,
                action='quotation_requested',
                reason=request.POST.get('reason', 'Quotation requested')
            )
            
            messages.success(request, _('Quotation requested'))
        else:
            messages.error(request, _('Cannot request quotation for this document'))
        
        return redirect('purchases:document_detail', pk=document.pk)
    
    def _create_order(self, request, document, document_type):
        """Crear orden desde solicitud"""
        if document_type == 'request' and document.status == 'approved':
            # Crear orden de compra
            supplier_id = request.POST.get('supplier_id')
            if not supplier_id:
                messages.error(request, _('Supplier is required'))
                return redirect('purchases:document_detail', pk=document.pk)
            
            try:
                supplier = Supplier.objects.get(id=supplier_id, empresa=request.user.empresa_activa)
            except Supplier.DoesNotExist:
                messages.error(request, _('Supplier not found'))
                return redirect('purchases:document_detail', pk=document.pk)
            
            # Crear orden
            order = PurchaseOrder.objects.create(
                empresa=request.user.empresa_activa,
                branch=request.user.branch_activa,
                supplier=supplier,
                purchase_request=document,
                expected_delivery_date=request.POST.get('expected_delivery_date'),
                currency=document.currency,
                payment_terms=request.POST.get('payment_terms', ''),
                delivery_terms=request.POST.get('delivery_terms', ''),
                notes=request.POST.get('notes', ''),
                created_by=request.user,
                status='draft'
            )
            
            # Crear líneas de orden desde líneas de solicitud
            for request_line in document.lines.all():
                PurchaseOrderLine.objects.create(
                    purchase_order=order,
                    request_line=request_line,
                    product_variant=request_line.product_variant,
                    quantity=request_line.quantity,
                    unit_of_measure=request_line.unit_of_measure,
                    unit_price=request_line.estimated_unit_price or 0,
                    status='pending'
                )
            
            # Marcar solicitud como convertida
            document.status = 'converted'
            document.save()
            
            messages.success(request, _('Purchase order created from request'))
            return redirect('purchases:document_detail', pk=order.pk)
        else:
            messages.error(request, _('Cannot create order from this document'))
            return redirect('purchases:document_detail', pk=document.pk)
    
    def _send_order(self, request, document, document_type):
        """Enviar orden al proveedor"""
        if document_type == 'order' and document.status == 'draft':
            document.status = 'order_sent'
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_order=document,
                user=request.user,
                action='sent',
                reason=request.POST.get('reason', 'Order sent to supplier')
            )
            
            messages.success(request, _('Order sent to supplier'))
        else:
            messages.error(request, _('Cannot send this order'))
        
        return redirect('purchases:document_detail', pk=document.pk)
    
    def _confirm_order(self, request, document, document_type):
        """Confirmar orden por proveedor"""
        if document_type == 'order' and document.status == 'order_sent':
            document.status = 'order_confirmed'
            document.confirmed_by = request.user
            document.confirmed_date = timezone.now().date()
            document.save()
            
            # Crear log
            ApprovalRecord.objects.create(
                purchase_order=document,
                user=request.user,
                action='confirmed',
                reason=request.POST.get('reason', 'Order confirmed by supplier')
            )
            
            messages.success(request, _('Order confirmed'))
        else:
            messages.error(request, _('Cannot confirm this order'))
        
        return redirect('purchases:document_detail', pk=document.pk)
    
    def _cancel_document(self, request, document, document_type):
        """Cancelar documento"""
        if document.status not in ['cancelled', 'completed', 'rejected']:
            document.status = 'cancelled'
            document.save()
            
            # Crear log
            if document_type == 'request':
                ApprovalRecord.objects.create(
                    purchase_request=document,
                    user=request.user,
                    action='cancelled',
                    reason=request.POST.get('reason', 'Document cancelled')
                )
            else:
                ApprovalRecord.objects.create(
                    purchase_order=document,
                    user=request.user,
                    action='cancelled',
                    reason=request.POST.get('reason', 'Document cancelled')
                )
            
            messages.success(request, _('Document cancelled'))
        else:
            messages.error(request, _('Cannot cancel this document'))
        
        return redirect('purchases:document_detail', pk=document.pk)


# Vistas adicionales para gestión de proveedores
@login_required
def supplier_approve(request, pk):
    """Aprobar un proveedor"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier.approve(request.user)
        messages.success(request, _('Supplier "%(name)s" approved successfully.') % {'name': supplier.name})
        return redirect('purchases:supplier_detail', pk=supplier.pk)
    
    return redirect('purchases:supplier_detail', pk=supplier.pk)


@login_required
def supplier_activate(request, pk):
    """Activar un proveedor"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier.activate()
        messages.success(request, _('Supplier "%(name)s" activated successfully.') % {'name': supplier.name})
        return redirect('purchases:supplier_detail', pk=supplier.pk)
    
    return redirect('purchases:supplier_detail', pk=supplier.pk)


@login_required
def supplier_deactivate(request, pk):
    """Desactivar un proveedor"""
    supplier = get_object_or_404(Supplier, pk=pk)
    
    if request.method == 'POST':
        supplier.deactivate()
        messages.success(request, _('Supplier "%(name)s" deactivated successfully.') % {'name': supplier.name})
        return redirect('purchases:supplier_detail', pk=supplier.pk)
    
    return redirect('purchases:supplier_detail', pk=supplier.pk) 