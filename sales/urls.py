from django.urls import path
from . import views

app_name = 'sales'

urlpatterns = [
    # Dashboard principal de ventas
    path('', views.sales_dashboard, name='dashboard'),
    
    # Gestión de clientes
    path('clients/', views.client_list, name='client_list'),
    path('clients/create/', views.client_create, name='client_create'),
    path('clients/<int:pk>/', views.client_detail, name='client_detail'),
    path('clients/<int:pk>/edit/', views.client_edit, name='client_edit'),
    path('clients/<int:pk>/delete/', views.client_delete, name='client_delete'),
    
    # Gestión de pedidos de venta
    path('orders/', views.sales_order_list, name='sales_order_list'),
    path('orders/create/', views.sales_order_create, name='sales_order_create'),
    path('orders/<int:pk>/', views.sales_order_detail, name='sales_order_detail'),
    path('orders/<int:pk>/edit/', views.sales_order_edit, name='sales_order_edit'),
    path('orders/<int:pk>/delete/', views.sales_order_delete, name='sales_order_delete'),
    path('orders/<int:pk>/approve/', views.sales_order_approve, name='sales_order_approve'),
    path('orders/<int:pk>/cancel/', views.sales_order_cancel, name='sales_order_cancel'),
    path('orders/<int:pk>/invoice/', views.sales_order_create_invoice, name='sales_order_create_invoice'),
    
    # Gestión de facturas
    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoices/create/', views.invoice_create, name='invoice_create'),
    path('invoices/<int:pk>/', views.invoice_detail, name='invoice_detail'),
    path('invoices/<int:pk>/edit/', views.invoice_edit, name='invoice_edit'),
    path('invoices/<int:pk>/delete/', views.invoice_delete, name='invoice_delete'),
    path('invoices/<int:pk>/mark-paid/', views.invoice_mark_paid, name='invoice_mark_paid'),
    path('invoices/<int:pk>/payment/', views.invoice_create_payment, name='invoice_create_payment'),
    
    # Gestión de pagos
    path('payments/', views.payment_list, name='payment_list'),
    path('payments/create/', views.payment_create, name='payment_create'),
    path('payments/<int:pk>/', views.payment_detail, name='payment_detail'),
    path('payments/<int:pk>/edit/', views.payment_edit, name='payment_edit'),
    path('payments/<int:pk>/delete/', views.payment_delete, name='payment_delete'),
    
    # Gestión de entregas
    path('deliveries/', views.delivery_order_list, name='delivery_order_list'),
    path('deliveries/create/', views.delivery_order_create, name='delivery_order_create'),
    path('deliveries/<int:pk>/', views.delivery_order_detail, name='delivery_order_detail'),
    path('deliveries/<int:pk>/edit/', views.delivery_order_edit, name='delivery_order_edit'),
    path('deliveries/<int:pk>/delete/', views.delivery_order_delete, name='delivery_order_delete'),
    path('deliveries/<int:pk>/process/', views.delivery_order_process, name='delivery_order_process'),
    
    # Gestión de devoluciones
    path('returns/', views.return_delivery_list, name='return_delivery_list'),
    path('returns/create/', views.return_delivery_create, name='return_delivery_create'),
    path('returns/<int:pk>/', views.return_delivery_detail, name='return_delivery_detail'),
    path('returns/<int:pk>/edit/', views.return_delivery_edit, name='return_delivery_edit'),
    path('returns/<int:pk>/delete/', views.return_delivery_delete, name='return_delivery_delete'),
    path('returns/<int:pk>/approve/', views.return_delivery_approve, name='return_delivery_approve'),
    
    # Gestión de notas de crédito
    path('credit-notes/', views.credit_note_list, name='credit_note_list'),
    path('credit-notes/create/', views.credit_note_create, name='credit_note_create'),
    path('credit-notes/<int:pk>/', views.credit_note_detail, name='credit_note_detail'),
    path('credit-notes/<int:pk>/edit/', views.credit_note_edit, name='credit_note_edit'),
    path('credit-notes/<int:pk>/delete/', views.credit_note_delete, name='credit_note_delete'),
    path('credit-notes/<int:pk>/apply/', views.credit_note_apply, name='credit_note_apply'),
    
    # Configuración
    path('config/price-lists/', views.price_list_list, name='price_list_list'),
    path('config/price-lists/create/', views.price_list_create, name='price_list_create'),
    path('config/price-lists/<int:pk>/', views.price_list_detail, name='price_list_detail'),
    path('config/price-lists/<int:pk>/edit/', views.price_list_edit, name='price_list_edit'),
    path('config/price-lists/<int:pk>/delete/', views.price_list_delete, name='price_list_delete'),
    
    path('config/payment-terms/', views.payment_term_list, name='payment_term_list'),
    path('config/payment-terms/create/', views.payment_term_create, name='payment_term_create'),
    path('config/payment-terms/<int:pk>/', views.payment_term_detail, name='payment_term_detail'),
    path('config/payment-terms/<int:pk>/edit/', views.payment_term_edit, name='payment_term_edit'),
    path('config/payment-terms/<int:pk>/delete/', views.payment_term_delete, name='payment_term_delete'),
    
    # Reportes
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/sales-summary/', views.sales_summary_report, name='sales_summary_report'),
    path('reports/client-analysis/', views.client_analysis_report, name='client_analysis_report'),
    path('reports/product-performance/', views.product_performance_report, name='product_performance_report'),
] 