from django.views.generic import (
    ListView, CreateView, UpdateView, DeleteView, DetailView, TemplateView
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.utils.translation import gettext_lazy as _

from .models import (
    Supplier, PurchaseRequest, PurchaseRequestLine, PurchaseQuotation,
    PurchaseQuotationLine, PurchaseOrder, PurchaseOrderLine, PurchaseReceipt,
    SupplierRating, ApprovalWorkflow, ApprovalLevel
)
from .services import PurchaseService, SupplierService, ApprovalService, QuotationService


class PurchaseDashboardView(LoginRequiredMixin, TemplateView):
    """Vista del dashboard principal de compras"""
    template_name = 'purchases/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        empresa = self.request.user.empresa
        
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
class SupplierListView(LoginRequiredMixin, ListView):
    """Lista de proveedores"""
    model = Supplier
    template_name = 'purchases/suppliers/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 20
    
    def get_queryset(self):
        return Supplier.objects.filter(empresa=self.request.user.empresa)


class SupplierCreateView(LoginRequiredMixin, CreateView):
    """Crear proveedor"""
    model = Supplier
    template_name = 'purchases/suppliers/supplier_form.html'
    fields = [
        'name', 'code', 'tax_id', 'contact_person', 'email', 'phone', 'mobile',
        'address', 'city', 'state', 'postal_code', 'country', 'payment_terms',
        'delivery_terms', 'credit_limit', 'supplier_category', 'notes'
    ]
    success_url = reverse_lazy('purchases:supplier_list')
    
    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa
        form.instance.branch = self.request.user.branch
        messages.success(self.request, _('Supplier created successfully'))
        return super().form_valid(form)


class SupplierDetailView(LoginRequiredMixin, DetailView):
    """Detalle de proveedor"""
    model = Supplier
    template_name = 'purchases/suppliers/supplier_detail.html'
    context_object_name = 'supplier'
    
    def get_queryset(self):
        return Supplier.objects.filter(empresa=self.request.user.empresa)


class SupplierUpdateView(LoginRequiredMixin, UpdateView):
    """Editar proveedor"""
    model = Supplier
    template_name = 'purchases/suppliers/supplier_form.html'
    fields = [
        'name', 'code', 'tax_id', 'contact_person', 'email', 'phone', 'mobile',
        'address', 'city', 'state', 'postal_code', 'country', 'payment_terms',
        'delivery_terms', 'credit_limit', 'supplier_category', 'notes'
    ]
    success_url = reverse_lazy('purchases:supplier_list')
    
    def get_queryset(self):
        return Supplier.objects.filter(empresa=self.request.user.empresa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Supplier updated successfully'))
        return super().form_valid(form)


class SupplierDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar proveedor"""
    model = Supplier
    template_name = 'purchases/suppliers/supplier_confirm_delete.html'
    success_url = reverse_lazy('purchases:supplier_list')
    
    def get_queryset(self):
        return Supplier.objects.filter(empresa=self.request.user.empresa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Supplier deleted successfully'))
        return super().delete(request, *args, **kwargs)


# Vistas para Solicitudes de Compra
class PurchaseRequestListView(LoginRequiredMixin, ListView):
    """Lista de solicitudes de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_list.html'
    context_object_name = 'requests'
    paginate_by = 20
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa)


class PurchaseRequestCreateView(LoginRequiredMixin, CreateView):
    """Crear solicitud de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_form.html'
    fields = [
        'title', 'description', 'priority', 'required_date', 'supplier', 'currency'
    ]
    success_url = reverse_lazy('purchases:request_list')
    
    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa
        form.instance.branch = self.request.user.branch
        form.instance.requested_by = self.request.user
        messages.success(self.request, _('Purchase request created successfully'))
        return super().form_valid(form)


class PurchaseRequestDetailView(LoginRequiredMixin, DetailView):
    """Detalle de solicitud de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_detail.html'
    context_object_name = 'request'
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa)


class PurchaseRequestUpdateView(LoginRequiredMixin, UpdateView):
    """Editar solicitud de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_form.html'
    fields = [
        'title', 'description', 'priority', 'required_date', 'supplier', 'currency'
    ]
    success_url = reverse_lazy('purchases:request_list')
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Purchase request updated successfully'))
        return super().form_valid(form)


class PurchaseRequestDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar solicitud de compra"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_confirm_delete.html'
    success_url = reverse_lazy('purchases:request_list')
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Purchase request deleted successfully'))
        return super().delete(request, *args, **kwargs)


class PurchaseRequestSubmitView(LoginRequiredMixin, DetailView):
    """Enviar solicitud a aprobación"""
    model = PurchaseRequest
    template_name = 'purchases/requests/request_submit.html'
    
    def get_queryset(self):
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseRequest.objects.filter(empresa=self.request.user.empresa)
    
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
            supplier = Supplier.objects.get(id=supplier_id, empresa=request.user.empresa)
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
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa)


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
        form.instance.empresa = self.request.user.empresa
        form.instance.branch = self.request.user.branch
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Quotation created successfully'))
        return super().form_valid(form)


class PurchaseQuotationDetailView(LoginRequiredMixin, DetailView):
    """Detalle de cotización"""
    model = PurchaseQuotation
    template_name = 'purchases/quotations/quotation_detail.html'
    context_object_name = 'quotation'
    
    def get_queryset(self):
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa)


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
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Quotation updated successfully'))
        return super().form_valid(form)


class PurchaseQuotationDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar cotización"""
    model = PurchaseQuotation
    template_name = 'purchases/quotations/quotation_confirm_delete.html'
    success_url = reverse_lazy('purchases:quotation_list')
    
    def get_queryset(self):
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Quotation deleted successfully'))
        return super().delete(request, *args, **kwargs)


class PurchaseQuotationEvaluateView(LoginRequiredMixin, DetailView):
    """Evaluar cotización"""
    model = PurchaseQuotation
    template_name = 'purchases/quotations/quotation_evaluate.html'
    
    def get_queryset(self):
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseQuotation.objects.filter(empresa=self.request.user.empresa)
    
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
                    id=request_id, empresa=self.request.user.empresa
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
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa)


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
        form.instance.empresa = self.request.user.empresa
        form.instance.branch = self.request.user.branch
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Purchase order created successfully'))
        return super().form_valid(form)


class PurchaseOrderDetailView(LoginRequiredMixin, DetailView):
    """Detalle de orden de compra"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_detail.html'
    context_object_name = 'order'
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa)


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
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Purchase order updated successfully'))
        return super().form_valid(form)


class PurchaseOrderDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar orden de compra"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_confirm_delete.html'
    success_url = reverse_lazy('purchases:order_list')
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Purchase order deleted successfully'))
        return super().delete(request, *args, **kwargs)


class PurchaseOrderSendView(LoginRequiredMixin, DetailView):
    """Enviar orden al proveedor"""
    model = PurchaseOrder
    template_name = 'purchases/orders/order_send.html'
    
    def get_queryset(self):
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseOrder.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseReceipt.objects.filter(empresa=self.request.user.empresa)


class PurchaseReceiptDetailView(LoginRequiredMixin, DetailView):
    """Detalle de recepción"""
    model = PurchaseReceipt
    template_name = 'purchases/receipts/receipt_detail.html'
    context_object_name = 'receipt'
    
    def get_queryset(self):
        return PurchaseReceipt.objects.filter(empresa=self.request.user.empresa)


class PurchaseReceiptApproveView(LoginRequiredMixin, DetailView):
    """Aprobar recepción"""
    model = PurchaseReceipt
    template_name = 'purchases/receipts/receipt_approve.html'
    
    def get_queryset(self):
        return PurchaseReceipt.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseReceipt.objects.filter(empresa=self.request.user.empresa)
    
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
        return PurchaseReceipt.objects.filter(empresa=self.request.user.empresa)
    
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
        return SupplierRating.objects.filter(empresa=self.request.user.empresa)


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
        form.instance.empresa = self.request.user.empresa
        form.instance.evaluated_by = self.request.user
        messages.success(self.request, _('Supplier rating created successfully'))
        return super().form_valid(form)


class SupplierRatingDetailView(LoginRequiredMixin, DetailView):
    """Detalle de evaluación de proveedor"""
    model = SupplierRating
    template_name = 'purchases/ratings/rating_detail.html'
    context_object_name = 'rating'
    
    def get_queryset(self):
        return SupplierRating.objects.filter(empresa=self.request.user.empresa)


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
        return SupplierRating.objects.filter(empresa=self.request.user.empresa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Supplier rating updated successfully'))
        return super().form_valid(form)


class SupplierRatingDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar evaluación de proveedor"""
    model = SupplierRating
    template_name = 'purchases/ratings/rating_confirm_delete.html'
    success_url = reverse_lazy('purchases:rating_list')
    
    def get_queryset(self):
        return SupplierRating.objects.filter(empresa=self.request.user.empresa)
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, _('Supplier rating deleted successfully'))
        return super().delete(request, *args, **kwargs)


class SupplierRatingSubmitView(LoginRequiredMixin, DetailView):
    """Enviar evaluación para revisión"""
    model = SupplierRating
    template_name = 'purchases/ratings/rating_submit.html'
    
    def get_queryset(self):
        return SupplierRating.objects.filter(empresa=self.request.user.empresa)
    
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
        return SupplierRating.objects.filter(empresa=self.request.user.empresa)
    
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
        return ApprovalWorkflow.objects.filter(empresa=self.request.user.empresa)


class ApprovalWorkflowCreateView(LoginRequiredMixin, CreateView):
    """Crear flujo de aprobación"""
    model = ApprovalWorkflow
    template_name = 'purchases/approval/workflow_form.html'
    fields = ['name', 'description', 'min_amount', 'max_amount', 'requires_all_approvals']
    success_url = reverse_lazy('purchases:workflow_list')
    
    def form_valid(self, form):
        form.instance.empresa = self.request.user.empresa
        form.instance.branch = self.request.user.branch
        form.instance.created_by = self.request.user
        messages.success(self.request, _('Approval workflow created successfully'))
        return super().form_valid(form)


class ApprovalWorkflowDetailView(LoginRequiredMixin, DetailView):
    """Detalle de flujo de aprobación"""
    model = ApprovalWorkflow
    template_name = 'purchases/approval/workflow_detail.html'
    context_object_name = 'workflow'
    
    def get_queryset(self):
        return ApprovalWorkflow.objects.filter(empresa=self.request.user.empresa)


class ApprovalWorkflowUpdateView(LoginRequiredMixin, UpdateView):
    """Editar flujo de aprobación"""
    model = ApprovalWorkflow
    template_name = 'purchases/approval/workflow_form.html'
    fields = ['name', 'description', 'min_amount', 'max_amount', 'requires_all_approvals']
    success_url = reverse_lazy('purchases:workflow_list')
    
    def get_queryset(self):
        return ApprovalWorkflow.objects.filter(empresa=self.request.user.empresa)
    
    def form_valid(self, form):
        messages.success(self.request, _('Approval workflow updated successfully'))
        return super().form_valid(form)


class ApprovalWorkflowDeleteView(LoginRequiredMixin, DeleteView):
    """Eliminar flujo de aprobación"""
    model = ApprovalWorkflow
    template_name = 'purchases/approval/workflow_confirm_delete.html'
    success_url = reverse_lazy('purchases:workflow_list')
    
    def get_queryset(self):
        return ApprovalWorkflow.objects.filter(empresa=self.request.user.empresa)
    
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
        empresa = self.request.user.empresa
        
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