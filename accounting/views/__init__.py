# Vistas del módulo de contabilidad
from .views_dashboard import *
from .views_tax_groups import *
from .views_taxes import *
from .views_fiscal_positions import *
from .views_chart_of_accounts import *
from .views_journals import *
from .views_entries import *
from .views_reports import * 
from .views_configuration import *

# Importar vistas de períodos contables
from .views_periods import (
    FiscalYearListView, FiscalYearCreateView, FiscalYearUpdateView, 
    FiscalYearDetailView, FiscalYearDeleteView, close_fiscal_year, reopen_fiscal_year,
    AccountingPeriodListView, AccountingPeriodCreateView, AccountingPeriodUpdateView,
    AccountingPeriodDetailView, AccountingPeriodDeleteView, close_accounting_period, 
    reopen_accounting_period, periods_dashboard
) 