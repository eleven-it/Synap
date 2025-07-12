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
from .views import views_periods

app_name = 'accounting'

urlpatterns = [
    # Dashboard
    path('', views.accounting_dashboard, name='dashboard'),
    
    # Chart of Accounts
    path('accounts/', views.ChartOfAccountsListView.as_view(), name='account_list'),
    path('accounts/create/', views.ChartOfAccountsCreateView.as_view(), name='account_create'),
    path('accounts/<int:pk>/edit/', views.ChartOfAccountsUpdateView.as_view(), name='account_edit'),
    path('accounts/<int:pk>/update/', views.ChartOfAccountsUpdateView.as_view(), name='account_update'),
    path('accounts/<int:pk>/delete/', views.ChartOfAccountsDeleteView.as_view(), name='account_delete'),
    path('accounts/<int:pk>/toggle-status/', views.toggle_account_status, name='account_toggle_status'),
    path('accounts/<int:pk>/detail/', views.ChartOfAccountsDetailView.as_view(), name='account_detail'),
    path('accounts/tree/', views.account_tree_view, name='account_tree'),
    path('accounts/balance-sheet/', views.account_balance_sheet, name='account_balance_sheet'),
    
    # Journals
    path('journals/', views.JournalListView.as_view(), name='journal_list'),
    path('journals/create/', views.JournalCreateView.as_view(), name='journal_create'),
    path('journals/<int:pk>/edit/', views.JournalUpdateView.as_view(), name='journal_edit'),
    path('journals/<int:pk>/update/', views.JournalUpdateView.as_view(), name='journal_update'),
    path('journals/<int:pk>/delete/', views.JournalDeleteView.as_view(), name='journal_delete'),
    path('journals/<int:pk>/toggle-status/', views.toggle_journal_status, name='journal_toggle_status'),
    path('journals/<int:pk>/detail/', views.JournalDetailView.as_view(), name='journal_detail'),
    path('journals/dashboard/', views.journal_dashboard, name='journal_dashboard'),
    
    # Journal Entries
    path('entries/', views.JournalEntryListView.as_view(), name='journal_entry_list'),
    path('entries/create/', views.JournalEntryCreateView.as_view(), name='journal_entry_create'),
    path('entries/<int:pk>/edit/', views.JournalEntryUpdateView.as_view(), name='journal_entry_edit'),
    path('entries/<int:pk>/update/', views.JournalEntryUpdateView.as_view(), name='journal_entry_update'),
    path('entries/<int:pk>/delete/', views.JournalEntryDeleteView.as_view(), name='journal_entry_delete'),
    path('entries/<int:pk>/detail/', views.JournalEntryDetailView.as_view(), name='journal_entry_detail'),
    path('entries/<int:pk>/post/', views.JournalEntryPostView.as_view(), name='journal_entry_post'),
    path('entries/<int:pk>/cancel/', views.JournalEntryCancelView.as_view(), name='journal_entry_cancel'),
    path('entries/dashboard/', views.entry_dashboard, name='journal_entry_dashboard'),
    path('entries/<int:pk>/balance-check/', views.entry_balance_check, name='journal_entry_balance_check'),
    path('entries/quick-create/', views.quick_entry_create, name='journal_entry_quick_create'),
    
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
    
    # Fiscal Positions
    path('fiscal-positions/', views.FiscalPositionListView.as_view(), name='fiscal_position_list'),
    path('fiscal-positions/create/', views.FiscalPositionCreateView.as_view(), name='fiscal_position_create'),
    path('fiscal-positions/<int:pk>/edit/', views.FiscalPositionUpdateView.as_view(), name='fiscal_position_edit'),
    path('fiscal-positions/<int:pk>/update/', views.FiscalPositionUpdateView.as_view(), name='fiscal_position_update'),
    path('fiscal-positions/<int:pk>/delete/', views.FiscalPositionDeleteView.as_view(), name='fiscal_position_delete'),
    path('fiscal-positions/<int:pk>/toggle-status/', views.toggle_fiscal_position_status, name='fiscal_position_toggle_status'),
    path('fiscal-positions/<int:pk>/detail/', views.fiscal_position_detail, name='fiscal_position_detail'),
    
    # Fiscal Position Tax Mappings
    path('fiscal-positions/<int:fiscal_position_pk>/tax-mappings/create/', views.FiscalPositionTaxCreateView.as_view(), name='fiscal_position_tax_create'),
    path('fiscal-positions/tax-mappings/<int:pk>/edit/', views.FiscalPositionTaxUpdateView.as_view(), name='fiscal_position_tax_edit'),
    path('fiscal-positions/tax-mappings/<int:pk>/update/', views.FiscalPositionTaxUpdateView.as_view(), name='fiscal_position_tax_update'),
    path('fiscal-positions/tax-mappings/<int:pk>/delete/', views.FiscalPositionTaxDeleteView.as_view(), name='fiscal_position_tax_delete'),
    
    # Reports Dashboard
    path('reports/dashboard/', views.reports_dashboard, name='reports_dashboard'),
    
    # Basic Reports
    path('reports/balance-sheet/', views.balance_sheet_report, name='balance_sheet_report'),
    path('reports/income-statement/', views.income_statement_report, name='income_statement_report'),
    path('reports/trial-balance/', views.trial_balance_report, name='trial_balance_report'),
    path('reports/general-ledger/', views.general_ledger_report, name='general_ledger_report'),
    path('reports/tax-report/', views.tax_report, name='tax_report'),
    path('reports/account-balance/', views.account_balance_report, name='account_balance_report'),
    path('reports/tax-summary/', views.tax_summary_report, name='tax_summary_report'),
    path('reports/financial-statements/', views.financial_statements, name='financial_statements'),
    
    # Advanced Reports
    path('reports/bank-reconciliation/', views.bank_reconciliation, name='bank_reconciliation_report'),
    path('reports/trend-analysis/', views.trend_analysis, name='trend_analysis_report'),
    path('reports/custom-reports/', views.custom_reports, name='custom_reports'),
    path('reports/financial-ratios/', views.financial_ratios, name='financial_ratios_report'),
    
    # Advanced Reports Dashboard
    path('reports/advanced-dashboard/', views.advanced_dashboard, name='advanced_dashboard'),
    path('reports/bank-reconciliation-advanced/', views.bank_reconciliation_advanced, name='bank_reconciliation_advanced'),
    path('reports/trend-analysis-advanced/', views.trend_analysis_advanced, name='trend_analysis_advanced'),
    path('reports/custom-reports-advanced/', views.custom_reports_advanced, name='custom_reports_advanced'),
    path('reports/financial-ratios-advanced/', views.financial_ratios_advanced, name='financial_ratios_advanced'),
    
    # Configuration
    path('currencies/', views.currency_list, name='currency_list'),
    path('account-types/', views.account_type_list, name='account_type_list'),
    
    # Fiscal Years
    path('fiscal-years/', views_periods.FiscalYearListView.as_view(), name='fiscal_year_list'),
    path('fiscal-years/create/', views_periods.FiscalYearCreateView.as_view(), name='fiscal_year_create'),
    path('fiscal-years/<int:pk>/edit/', views_periods.FiscalYearUpdateView.as_view(), name='fiscal_year_edit'),
    path('fiscal-years/<int:pk>/update/', views_periods.FiscalYearUpdateView.as_view(), name='fiscal_year_update'),
    path('fiscal-years/<int:pk>/delete/', views_periods.FiscalYearDeleteView.as_view(), name='fiscal_year_delete'),
    path('fiscal-years/<int:pk>/detail/', views_periods.FiscalYearDetailView.as_view(), name='fiscal_year_detail'),
    path('fiscal-years/<int:pk>/close/', views_periods.close_fiscal_year, name='fiscal_year_close'),
    path('fiscal-years/<int:pk>/reopen/', views_periods.reopen_fiscal_year, name='fiscal_year_reopen'),
    
    # Accounting Periods
    path('periods/', views_periods.AccountingPeriodListView.as_view(), name='period_list'),
    path('periods/create/', views_periods.AccountingPeriodCreateView.as_view(), name='period_create'),
    path('periods/<int:pk>/edit/', views_periods.AccountingPeriodUpdateView.as_view(), name='period_edit'),
    path('periods/<int:pk>/update/', views_periods.AccountingPeriodUpdateView.as_view(), name='period_update'),
    path('periods/<int:pk>/delete/', views_periods.AccountingPeriodDeleteView.as_view(), name='period_delete'),
    path('periods/<int:pk>/detail/', views_periods.AccountingPeriodDetailView.as_view(), name='period_detail'),
    path('periods/<int:pk>/close/', views_periods.close_accounting_period, name='period_close'),
    path('periods/<int:pk>/reopen/', views_periods.reopen_accounting_period, name='period_reopen'),
    path('periods/dashboard/', views_periods.periods_dashboard, name='periods_dashboard'),
    
    # API endpoints para cálculo de impuestos en órdenes
    path('api/taxes/for-product/', get_taxes_for_product, name='get_taxes_for_product'),
    path('api/fiscal-positions/', get_fiscal_positions, name='get_fiscal_positions'),
    path('api/calculate-line-taxes/', calculate_line_taxes, name='calculate_line_taxes'),
    path('api/apply-automatic-taxes/', apply_automatic_taxes_to_order, name='apply_automatic_taxes_to_order'),
    path('api/tax-summary/', get_tax_summary, name='get_tax_summary'),
    path('api/update-line-taxes/', update_line_taxes, name='update_line_taxes'),
    path('api/validate-tax-config/', validate_tax_configuration, name='validate_tax_configuration'),
] 