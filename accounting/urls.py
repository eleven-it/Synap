from django.urls import path
from . import views
from .views.api_views import (
    get_taxes_for_product,
    get_fiscal_positions,
    calculate_line_taxes,
    apply_automatic_taxes_to_order,
    get_tax_summary,
    update_line_taxes,
    validate_tax_configuration,
)

app_name = 'accounting'

urlpatterns = [
    # Dashboard
    path('', views.accounting_dashboard, name='dashboard'),
    
    # Tax Groups
    path('tax-groups/', views.TaxGroupListView.as_view(), name='tax_group_list'),
    path('tax-groups/create/', views.TaxGroupCreateView.as_view(), name='tax_group_create'),
    path('tax-groups/<int:pk>/edit/', views.TaxGroupUpdateView.as_view(), name='tax_group_edit'),
    path('tax-groups/<int:pk>/delete/', views.TaxGroupDeleteView.as_view(), name='tax_group_delete'),
    path('tax-groups/<int:pk>/toggle-status/', views.toggle_tax_group_status, name='tax_group_toggle_status'),
    
    # Individual Taxes
    path('taxes/', views.TaxListView.as_view(), name='tax_list'),
    path('taxes/create/', views.TaxCreateView.as_view(), name='tax_create'),
    path('taxes/<int:pk>/edit/', views.TaxUpdateView.as_view(), name='tax_edit'),
    path('taxes/<int:pk>/delete/', views.TaxDeleteView.as_view(), name='tax_delete'),
    path('taxes/<int:pk>/toggle-status/', views.toggle_tax_status, name='tax_toggle_status'),
    path('taxes/<int:pk>/detail/', views.tax_detail, name='tax_detail'),
    # path('taxes/<int:pk>/duplicate/', views.tax_duplicate, name='tax_duplicate'),  # Vista no implementada
    # path('taxes/bulk-actions/', views.tax_bulk_actions, name='tax_bulk_actions'),  # Vista no implementada
    # path('taxes/export/', views.tax_export, name='tax_export'),  # Vista no implementada
    
    # Fiscal Positions
    path('fiscal-positions/', views.FiscalPositionListView.as_view(), name='fiscal_position_list'),
    path('fiscal-positions/create/', views.FiscalPositionCreateView.as_view(), name='fiscal_position_create'),
    path('fiscal-positions/<int:pk>/edit/', views.FiscalPositionUpdateView.as_view(), name='fiscal_position_edit'),
    path('fiscal-positions/<int:pk>/delete/', views.FiscalPositionDeleteView.as_view(), name='fiscal_position_delete'),
    path('fiscal-positions/<int:pk>/toggle-status/', views.toggle_fiscal_position_status, name='fiscal_position_toggle_status'),
    
    # Reports
    # path('reports/', views.reports_dashboard, name='reports_dashboard'),  # Vista no implementada
    # path('reports/tax-summary/', views.tax_summary_report, name='tax_summary_report'),  # Vista no implementada
    # path('reports/tax-detail/', views.tax_detail_report, name='tax_detail_report'),  # Vista no implementada
    
    # API endpoints para cálculo de impuestos en órdenes
    path('api/taxes/for-product/', get_taxes_for_product, name='get_taxes_for_product'),
    path('api/fiscal-positions/', get_fiscal_positions, name='get_fiscal_positions'),
    path('api/calculate-line-taxes/', calculate_line_taxes, name='calculate_line_taxes'),
    path('api/apply-automatic-taxes/', apply_automatic_taxes_to_order, name='apply_automatic_taxes_to_order'),
    path('api/tax-summary/', get_tax_summary, name='get_tax_summary'),
    path('api/update-line-taxes/', update_line_taxes, name='update_line_taxes'),
    path('api/validate-tax-config/', validate_tax_configuration, name='validate_tax_configuration'),
    
    # TODO: Implementar en siguientes fases
    # Chart of Accounts
    # path('accounts/', views.ChartOfAccountsListView.as_view(), name='chart_of_accounts_list'),
    # path('accounts/create/', views.ChartOfAccountsCreateView.as_view(), name='chart_of_accounts_create'),
    # path('accounts/<int:pk>/edit/', views.ChartOfAccountsUpdateView.as_view(), name='chart_of_accounts_edit'),
    # path('accounts/<int:pk>/delete/', views.ChartOfAccountsDeleteView.as_view(), name='chart_of_accounts_delete'),
    # path('accounts/<int:pk>/toggle-status/', views.chart_of_accounts_toggle_status, name='chart_of_accounts_toggle_status'),
    
    # Journals
    # path('journals/', views.JournalListView.as_view(), name='journal_list'),
    # path('journals/create/', views.JournalCreateView.as_view(), name='journal_create'),
    # path('journals/<int:pk>/edit/', views.JournalUpdateView.as_view(), name='journal_edit'),
    # path('journals/<int:pk>/delete/', views.JournalDeleteView.as_view(), name='journal_delete'),
    # path('journals/<int:pk>/toggle-status/', views.journal_toggle_status, name='journal_toggle_status'),
    
    # Journal Entries
    # path('entries/', views.JournalEntryListView.as_view(), name='journal_entry_list'),
    # path('entries/create/', views.JournalEntryCreateView.as_view(), name='journal_entry_create'),
    # path('entries/<int:pk>/edit/', views.JournalEntryUpdateView.as_view(), name='journal_entry_edit'),
    # path('entries/<int:pk>/delete/', views.JournalEntryDeleteView.as_view(), name='journal_entry_delete'),
    # path('entries/<int:pk>/toggle-status/', views.journal_entry_toggle_status, name='journal_entry_toggle_status'),
    # path('entries/<int:pk>/', views.journal_entry_detail, name='journal_entry_detail'),
    
    # Tax Lines
    # path('tax-lines/', views.TaxLineListView.as_view(), name='tax_line_list'),
    # path('tax-lines/create/', views.TaxLineCreateView.as_view(), name='tax_line_create'),
    # path('tax-lines/<int:pk>/edit/', views.TaxLineUpdateView.as_view(), name='tax_line_edit'),
    # path('tax-lines/<int:pk>/delete/', views.TaxLineDeleteView.as_view(), name='tax_line_delete'),
    
    # Additional Reports
    # path('reports/account-balance/', views.account_balance_report, name='account_balance_report'),
    # path('reports/journal-summary/', views.journal_summary_report, name='journal_summary_report'),
    
    # Additional API endpoints
    # path('api/accounts/', views.account_list_api, name='account_list_api'),
] 