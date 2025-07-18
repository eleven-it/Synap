from django.urls import path, include
from . import views
from . import tpv_views
from django.views.generic import RedirectView

app_name = 'sales'

urlpatterns = [
    # Dashboard principal de ventas
    path('', views.sales_dashboard, name='dashboard'),
    
    # Gestión de clientes
    path('clients/', views.ClientListView.as_view(), name='client_list'),
    path('clients/create/', views.ClientCreateView.as_view(), name='client_create'),
    path('clients/<int:pk>/', views.ClientDetailView.as_view(), name='client_detail'),
    path('clients/<int:pk>/edit/', views.ClientUpdateView.as_view(), name='client_update'),
    path('clients/<int:pk>/delete/', views.ClientDeleteView.as_view(), name='client_delete'),
    
    # Wizard multi-step de clientes
    path('clients/wizard/', views.client_wizard_view, name='client_wizard'),
    path('clients/wizard/step/<int:step>/', views.wizard_step_navigation, name='wizard_step'),
    
    # Gestión de contactos (comentado - no implementado)
    # path('contacts/', views.ContactListView.as_view(), name='contact_list'),
    # path('contacts/create/', views.ContactCreateView.as_view(), name='contact_create'),
    # path('contacts/<int:pk>/', views.ContactDetailView.as_view(), name='contact_detail'),
    # path('contacts/<int:pk>/edit/', views.ContactUpdateView.as_view(), name='contact_update'),
    # path('contacts/<int:pk>/delete/', views.ContactDeleteView.as_view(), name='contact_delete'),
    
    # Contactos por cliente (comentado - no implementado)
    # path('clients/<int:client_id>/contacts/', views.ContactListView.as_view(), name='client_contacts'),
    # path('clients/<int:client_id>/contacts/add/', views.ContactCreateView.as_view(), name='contact_create_by_client'),
    
    # Gestión de pedidos de venta
    path('orders/', views.sales_order_list, name='sales_order_list'),
    path('orders/create/', views.sales_order_create, name='sales_order_create'),
    path('orders/<int:pk>/', views.sales_order_detail, name='sales_order_detail'),
    path('orders/<int:pk>/edit/', views.sales_order_edit, name='sales_order_edit'),
    path('orders/<int:pk>/delete/', views.sales_order_delete, name='sales_order_delete'),
    path('orders/<int:pk>/approve/', views.sales_order_approve, name='sales_order_approve'),
    path('orders/<int:pk>/cancel/', views.sales_order_cancel, name='sales_order_cancel'),
    
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
    path('config/price-lists/<int:pk>/deactivate/', views.price_list_deactivate, name='price_list_deactivate'),
    path('config/price-lists/<int:pk>/activate/', views.price_list_activate, name='price_list_activate'),
    path('config/price-lists/<int:pk>/items/add/', views.price_list_item_add, name='price_list_item_add'),
    path('config/price-list-items/<int:pk>/edit/', views.price_list_item_edit, name='price_list_item_edit'),
    path('config/price-list-items/<int:pk>/delete/', views.price_list_item_delete, name='price_list_item_delete'),
    
    path('config/payment-terms/', views.payment_term_list, name='payment_term_list'),
    path('config/payment-terms/create/', views.payment_term_create, name='payment_term_create'),
    path('config/payment-terms/<int:pk>/', views.payment_term_detail, name='payment_term_detail'),
    path('config/payment-terms/<int:pk>/edit/', views.payment_term_edit, name='payment_term_edit'),
    path('config/payment-terms/<int:pk>/delete/', views.payment_term_delete, name='payment_term_delete'),
    path('config/payment-terms/<int:pk>/activate/', views.payment_terms_activate, name='payment_terms_activate'),
    path('config/payment-terms/<int:pk>/deactivate/', views.payment_terms_deactivate, name='payment_terms_deactivate'),
    path('config/payment-terms/<int:payment_term_id>/lines/create/', views.payment_term_line_create, name='payment_term_line_create'),
    path('config/payment-terms/lines/<int:pk>/edit/', views.payment_term_line_edit, name='payment_term_line_edit'),
    path('config/payment-terms/lines/<int:pk>/delete/', views.payment_term_line_delete, name='payment_term_line_delete'),
    
    # Reportes
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('reports/sales-summary/', views.sales_summary_report, name='sales_summary_report'),
    path('reports/client-analysis/', views.client_analysis_report, name='client_analysis_report'),
    path('reports/product-performance/', views.product_performance_report, name='product_performance_report'),
    
    # URLs de autocompletado
    # path('autocomplete/country/', views.autocomplete_country, name='autocomplete_country'),
    # path('autocomplete/state/', views.autocomplete_state, name='autocomplete_state'),
    path('autocomplete/city/', views.autocomplete_city, name='autocomplete_city'),
    path('autocomplete/seller/', views.autocomplete_seller, name='autocomplete_seller'),
    
    # APIs para carga dinámica (deben ir ANTES de la API REST)
    path('api/states-by-country/', views.get_states_by_country, name='api_states_by_country'),
    path('api/fiscal-responsibilities-by-country/', views.get_fiscal_responsibilities_by_country, name='api_fiscal_responsibilities_by_country'),
    path('api/countries-autocomplete/', views.countries_autocomplete, name='api_countries_autocomplete'),
    path('api/states-autocomplete/', views.states_autocomplete, name='api_states_autocomplete'),
    path('api/fiscal-responsibilities-autocomplete/', views.fiscal_responsibilities_autocomplete, name='api_fiscal_responsibilities_autocomplete'),
    path('api/payment-terms-autocomplete/', views.payment_terms_autocomplete, name='api_payment_terms_autocomplete'),
    
    # APIs RESTful
    path('api/', include('sales.api.urls')),
    
    # URLs para gestión de contactos en wizard
    path('clients/wizard/step4/<int:client_id>/', views.client_contacts_step, name='client_contacts_step'),
    path('api/contacts/search/', views.search_contacts_api, name='search_contacts_api'),
    path('api/clients/<int:client_id>/contacts/add/', views.add_contact_to_client, name='add_contact_to_client'),
    path('api/clients/<int:client_id>/contacts/<int:relationship_id>/remove/', views.remove_contact_from_client, name='remove_contact_from_client'),
    path('api/clients/<int:client_id>/contacts/create/', views.create_contact_for_client, name='create_contact_for_client'),

    # --- URLs PARA PUNTO DE VENTA (TPV) ---

    # Dashboard y sesiones
    path('pos/', views.pos_dashboard, name='pos_dashboard'),
    path('pos/session/open/', views.pos_session_open, name='pos_session_open'),
    path('pos/session/close/', views.pos_session_close, name='pos_session_close'),
    path('pos/session/<int:session_id>/report/', views.pos_session_report, name='pos_session_report'),
    path('pos/sessions/', views.POSSessionListView.as_view(), name='pos_session_list'),

    # Ventas
    path('pos/sale/new/', views.pos_sale_new, name='pos_sale_new'),
    path('pos/sale/<int:sale_id>/', views.pos_sale_detail, name='pos_sale_detail'),
    path('pos/sales/', views.POSSaleListView.as_view(), name='pos_sale_list'),

    # APIs para TPV
    path('pos/api/product/search/', views.pos_product_search, name='pos_product_search'),
    path('pos/api/sale/<int:sale_id>/add-product/', views.pos_sale_add_product, name='pos_sale_add_product'),
    path('pos/api/sale/<int:sale_id>/remove-product/<int:line_id>/', views.pos_sale_remove_product, name='pos_sale_remove_product'),
    path('pos/api/sale/<int:sale_id>/apply-promotion/', views.pos_sale_apply_promotion, name='pos_sale_apply_promotion'),
    path('pos/api/sale/<int:sale_id>/complete/', views.pos_sale_complete, name='pos_sale_complete'),
    path('pos/api/scale/weight/', views.pos_scale_weight, name='pos_scale_weight'),
    path('pos/api/validate-stock/', views.pos_validate_stock, name='pos_validate_stock'),
    path('pos/api/calculate-totals/', views.pos_calculate_totals, name='pos_calculate_totals'),

    # Búsqueda de clientes
    path('pos/client/search/', views.pos_client_search, name='pos_client_search'),
    
    # Gestión de clientes en TPV
    path('pos/sale/<int:sale_id>/client/selection/', views.pos_client_selection, name='pos_client_selection'),
    path('pos/sale/<int:sale_id>/client/quick-create/', views.pos_quick_client_create, name='pos_quick_client_create'),

    # Configuración
    path('pos/configuration/', views.pos_configuration, name='pos_configuration'),

    # URLs del TPV
    path('tpv/', tpv_views.tpv_main, name='tpv_main'),
    path('tpv/dashboard/', tpv_views.tpv_dashboard, name='tpv_dashboard'),
    path('tpv/sessions/', tpv_views.tpv_session_list, name='tpv_session_list'),
    path('tpv/session/<int:session_id>/', tpv_views.tpv_session_detail, name='tpv_session_detail'),
    path('tpv/open-session/', tpv_views.tpv_open_session, name='tpv_open_session'),
    path('tpv/close-session/<int:session_id>/', tpv_views.tpv_close_session, name='tpv_close_session'),
    path('tpv/session/<int:session_id>/sale/', tpv_views.tpv_sale_create, name='tpv_sale_create'),
    path('tpv/product-search/', tpv_views.tpv_product_search, name='tpv_product_search'),
    path('tpv/session/<int:session_id>/sale/save/', tpv_views.tpv_sale_save, name='tpv_sale_save'),
    path('tpv/reports/', tpv_views.tpv_reports, name='tpv_reports'),
    path('tpv/sale/<int:sale_id>/summary/', tpv_views.TPVSaleSummaryView.as_view(), name='tpv_sale_summary'),
    path('tpv/process-payment/', tpv_views.tpv_process_payment, name='tpv_process_payment'),

    # Vistas de medios de pago
    path('payment-methods/', views.payment_method_list, name='payment_method_list'),
    path('payment-methods/create/', views.payment_method_create, name='payment_method_create'),
    path('payment-methods/<int:pk>/', views.payment_method_detail, name='payment_method_detail'),
    path('payment-methods/<int:pk>/edit/', views.payment_method_edit, name='payment_method_edit'),
    path('payment-methods/<int:pk>/delete/', views.payment_method_delete, name='payment_method_delete'),

    # Vistas de procesadores de pago
    path('payment-processors/', views.payment_processor_list, name='payment_processor_list'),
    path('payment-processors/create/', views.payment_processor_create, name='payment_processor_create'),
    path('payment-processors/<int:pk>/edit/', views.payment_processor_edit, name='payment_processor_edit'),
    path('payment-processors/<int:pk>/delete/', views.payment_processor_delete, name='payment_processor_delete'),
    path('payment-terms/', RedirectView.as_view(url='/sales/config/payment-terms/', permanent=False)),
    
    # Redirecciones para compatibilidad
    path('price-lists/', RedirectView.as_view(url='/sales/config/price-lists/', permanent=False)),
] 