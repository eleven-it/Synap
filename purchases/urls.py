from django.urls import path
from . import views

app_name = 'purchases'

urlpatterns = [
    # Dashboard principal de compras
    path('dashboard/', views.PurchaseDashboardView.as_view(), name='dashboard'),
    
    # Proveedores
    path('suppliers/', views.SupplierListView.as_view(), name='supplier_list'),
    path('suppliers/create/', views.SupplierCreateView.as_view(), name='supplier_create'),
    path('suppliers/<int:pk>/', views.SupplierDetailView.as_view(), name='supplier_detail'),
    path('suppliers/<int:pk>/edit/', views.SupplierUpdateView.as_view(), name='supplier_update'),
    path('suppliers/<int:pk>/delete/', views.SupplierDeleteView.as_view(), name='supplier_delete'),
    
    # Solicitudes de compra
    path('requests/', views.PurchaseRequestListView.as_view(), name='request_list'),
    path('requests/create/', views.PurchaseRequestCreateView.as_view(), name='request_create'),
    path('requests/<int:pk>/', views.PurchaseRequestDetailView.as_view(), name='request_detail'),
    path('requests/<int:pk>/edit/', views.PurchaseRequestUpdateView.as_view(), name='request_update'),
    path('requests/<int:pk>/delete/', views.PurchaseRequestDeleteView.as_view(), name='request_delete'),
    path('requests/<int:pk>/submit/', views.PurchaseRequestSubmitView.as_view(), name='request_submit'),
    path('requests/<int:pk>/approve/', views.PurchaseRequestApproveView.as_view(), name='request_approve'),
    path('requests/<int:pk>/reject/', views.PurchaseRequestRejectView.as_view(), name='request_reject'),
    path('requests/<int:pk>/convert/', views.PurchaseRequestConvertView.as_view(), name='request_convert'),
    
    # Cotizaciones
    path('quotations/', views.PurchaseQuotationListView.as_view(), name='quotation_list'),
    path('quotations/create/', views.PurchaseQuotationCreateView.as_view(), name='quotation_create'),
    path('quotations/<int:pk>/', views.PurchaseQuotationDetailView.as_view(), name='quotation_detail'),
    path('quotations/<int:pk>/edit/', views.PurchaseQuotationUpdateView.as_view(), name='quotation_update'),
    path('quotations/<int:pk>/delete/', views.PurchaseQuotationDeleteView.as_view(), name='quotation_delete'),
    path('quotations/<int:pk>/evaluate/', views.PurchaseQuotationEvaluateView.as_view(), name='quotation_evaluate'),
    path('quotations/<int:pk>/select/', views.PurchaseQuotationSelectView.as_view(), name='quotation_select'),
    path('quotations/compare/', views.PurchaseQuotationCompareView.as_view(), name='quotation_compare'),
    
    # Órdenes de compra
    path('orders/', views.PurchaseOrderListView.as_view(), name='order_list'),
    path('orders/create/', views.PurchaseOrderCreateView.as_view(), name='order_create'),
    path('orders/<int:pk>/', views.PurchaseOrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:pk>/edit/', views.PurchaseOrderUpdateView.as_view(), name='order_update'),
    path('orders/<int:pk>/delete/', views.PurchaseOrderDeleteView.as_view(), name='order_delete'),
    path('orders/<int:pk>/send/', views.PurchaseOrderSendView.as_view(), name='order_send'),
    path('orders/<int:pk>/confirm/', views.PurchaseOrderConfirmView.as_view(), name='order_confirm'),
    path('orders/<int:pk>/cancel/', views.PurchaseOrderCancelView.as_view(), name='order_cancel'),
    path('orders/<int:pk>/duplicate/', views.PurchaseOrderDuplicateView.as_view(), name='order_duplicate'),
    path('orders/<int:pk>/receive/', views.PurchaseOrderReceiveView.as_view(), name='order_receive'),
    
    # Recepciones
    path('receipts/', views.PurchaseReceiptListView.as_view(), name='receipt_list'),
    path('receipts/<int:pk>/', views.PurchaseReceiptDetailView.as_view(), name='receipt_detail'),
    path('receipts/<int:pk>/approve/', views.PurchaseReceiptApproveView.as_view(), name='receipt_approve'),
    path('receipts/<int:pk>/reject/', views.PurchaseReceiptRejectView.as_view(), name='receipt_reject'),
    path('receipts/<int:pk>/return/', views.PurchaseReceiptReturnView.as_view(), name='receipt_return'),
    
    # Evaluaciones de proveedores
    path('ratings/', views.SupplierRatingListView.as_view(), name='rating_list'),
    path('ratings/create/', views.SupplierRatingCreateView.as_view(), name='rating_create'),
    path('ratings/<int:pk>/', views.SupplierRatingDetailView.as_view(), name='rating_detail'),
    path('ratings/<int:pk>/edit/', views.SupplierRatingUpdateView.as_view(), name='rating_update'),
    path('ratings/<int:pk>/delete/', views.SupplierRatingDeleteView.as_view(), name='rating_delete'),
    path('ratings/<int:pk>/submit/', views.SupplierRatingSubmitView.as_view(), name='rating_submit'),
    path('ratings/<int:pk>/review/', views.SupplierRatingReviewView.as_view(), name='rating_review'),
    
    # Flujos de aprobación
    path('approval-workflows/', views.ApprovalWorkflowListView.as_view(), name='workflow_list'),
    path('approval-workflows/create/', views.ApprovalWorkflowCreateView.as_view(), name='workflow_create'),
    path('approval-workflows/<int:pk>/', views.ApprovalWorkflowDetailView.as_view(), name='workflow_detail'),
    path('approval-workflows/<int:pk>/edit/', views.ApprovalWorkflowUpdateView.as_view(), name='workflow_update'),
    path('approval-workflows/<int:pk>/delete/', views.ApprovalWorkflowDeleteView.as_view(), name='workflow_delete'),
    
    # Niveles de aprobación
    path('approval-levels/', views.ApprovalLevelListView.as_view(), name='level_list'),
    path('approval-levels/create/', views.ApprovalLevelCreateView.as_view(), name='level_create'),
    path('approval-levels/<int:pk>/', views.ApprovalLevelDetailView.as_view(), name='level_detail'),
    path('approval-levels/<int:pk>/edit/', views.ApprovalLevelUpdateView.as_view(), name='level_update'),
    path('approval-levels/<int:pk>/delete/', views.ApprovalLevelDeleteView.as_view(), name='level_delete'),
    
    # Reportes
    path('reports/', views.PurchaseReportsView.as_view(), name='reports'),
    path('reports/summary/', views.PurchaseSummaryReportView.as_view(), name='report_summary'),
    path('reports/supplier-performance/', views.SupplierPerformanceReportView.as_view(), name='report_supplier_performance'),
    path('reports/spending-analysis/', views.SpendingAnalysisReportView.as_view(), name='report_spending_analysis'),
    path('reports/delivery-performance/', views.DeliveryPerformanceReportView.as_view(), name='report_delivery_performance'),
    
    # Configuración
    path('settings/', views.PurchaseSettingsView.as_view(), name='settings'),
] 