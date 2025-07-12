"""
Configuración de menú para el módulo de contabilidad
"""

MENU_CONFIG = [
    {
        'name': 'accounting',
        'label': 'Accounting',
        'icon': 'fas fa-calculator',
        'permission': 'accounting.view_account',
        'order': 40,
        'children': [
            # Dashboard
            {
                'name': 'dashboard',
                'label': 'Dashboard',
                'url': 'accounting:dashboard',
                'permission': 'accounting.view_account',
                'icon': 'fas fa-tachometer-alt',
                'order': 1
            },
            
            # Plan de Cuentas
            {
                'name': 'chart_of_accounts',
                'label': 'Chart of Accounts',
                'url': 'accounting:account_list',
                'permission': 'accounting.view_account',
                'icon': 'fas fa-sitemap',
                'order': 2
            },
            
            # Diarios Contables
            {
                'name': 'journals',
                'label': 'Journals',
                'url': 'accounting:journal_list',
                'permission': 'accounting.view_journal',
                'icon': 'fas fa-book',
                'order': 3
            },
            
            # Asientos Contables
            {
                'name': 'journal_entries',
                'label': 'Journal Entries',
                'url': 'accounting:journal_entry_list',
                'permission': 'accounting.view_journal_entry',
                'icon': 'fas fa-file-invoice',
                'order': 4
            },
            
            # Impuestos
            {
                'name': 'taxes',
                'label': 'Taxes',
                'url': 'accounting:tax_list',
                'permission': 'accounting.view_tax',
                'icon': 'fas fa-percentage',
                'order': 5
            },
            
            # Posiciones Fiscales
            {
                'name': 'fiscal_positions',
                'label': 'Fiscal Positions',
                'url': 'accounting:fiscal_position_list',
                'permission': 'accounting.view_fiscal_position',
                'icon': 'fas fa-globe',
                'order': 6
            },
            
            # Reportes
            {
                'name': 'reports',
                'label': 'Reports',
                'icon': 'fas fa-chart-bar',
                'permission': 'accounting.view_report',
                'order': 7,
                'children': [
                    {
                        'name': 'reports_dashboard',
                        'label': 'Reports Dashboard',
                        'url': 'accounting:reports_dashboard',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-tachometer-alt'
                    },
                    {
                        'name': 'balance_sheet',
                        'label': 'Balance Sheet',
                        'url': 'accounting:balance_sheet_report',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-balance-scale'
                    },
                    {
                        'name': 'income_statement',
                        'label': 'Income Statement',
                        'url': 'accounting:income_statement_report',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-chart-line'
                    },
                    {
                        'name': 'trial_balance',
                        'label': 'Trial Balance',
                        'url': 'accounting:trial_balance_report',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-table'
                    },
                    {
                        'name': 'general_ledger',
                        'label': 'General Ledger',
                        'url': 'accounting:general_ledger_report',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-book-open'
                    },
                    {
                        'name': 'tax_report',
                        'label': 'Tax Report',
                        'url': 'accounting:tax_report',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-file-invoice-dollar'
                    },
                    {
                        'name': 'bank_reconciliation',
                        'label': 'Bank Reconciliation',
                        'url': 'accounting:bank_reconciliation_report',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-university'
                    },
                    {
                        'name': 'trend_analysis',
                        'label': 'Trend Analysis',
                        'url': 'accounting:trend_analysis_report',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-chart-area'
                    },
                    {
                        'name': 'custom_reports',
                        'label': 'Custom Reports',
                        'url': 'accounting:custom_reports',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-file-alt'
                    },
                    {
                        'name': 'financial_ratios',
                        'label': 'Financial Ratios',
                        'url': 'accounting:financial_ratios_report',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-calculator'
                    }
                ]
            },
            
            # Reportes Avanzados
            {
                'name': 'advanced_reports',
                'label': 'Advanced Reports',
                'icon': 'fas fa-chart-pie',
                'permission': 'accounting.view_report',
                'order': 8,
                'children': [
                    {
                        'name': 'advanced_dashboard',
                        'label': 'Advanced Dashboard',
                        'url': 'accounting:advanced_dashboard',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-tachometer-alt'
                    },
                    {
                        'name': 'bank_reconciliation_advanced',
                        'label': 'Bank Reconciliation',
                        'url': 'accounting:bank_reconciliation_advanced',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-university'
                    },
                    {
                        'name': 'trend_analysis_advanced',
                        'label': 'Trend Analysis',
                        'url': 'accounting:trend_analysis_advanced',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-chart-area'
                    },
                    {
                        'name': 'custom_reports_advanced',
                        'label': 'Custom Reports',
                        'url': 'accounting:custom_reports_advanced',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-file-alt'
                    },
                    {
                        'name': 'financial_ratios_advanced',
                        'label': 'Financial Ratios',
                        'url': 'accounting:financial_ratios_advanced',
                        'permission': 'accounting.view_report',
                        'icon': 'fas fa-calculator'
                    }
                ]
            },
            
            # Configuración
            {
                'name': 'configuration',
                'label': 'Configuration',
                'icon': 'fas fa-cog',
                'permission': 'accounting.view_config',
                'order': 9,
                'children': [
                    {
                        'name': 'fiscal_years',
                        'label': 'Fiscal Years',
                        'url': 'accounting:fiscal_year_list',
                        'permission': 'accounting.view_fiscal_year',
                        'icon': 'fas fa-calendar-alt'
                    },
                    {
                        'name': 'accounting_periods',
                        'label': 'Accounting Periods',
                        'url': 'accounting:period_list',
                        'permission': 'accounting.view_period',
                        'icon': 'fas fa-calendar-week'
                    },
                    {
                        'name': 'currencies',
                        'label': 'Currencies',
                        'url': 'accounting:currency_list',
                        'permission': 'accounting.view_currency',
                        'icon': 'fas fa-coins'
                    },
                    {
                        'name': 'account_types',
                        'label': 'Account Types',
                        'url': 'accounting:account_type_list',
                        'permission': 'accounting.view_account_type',
                        'icon': 'fas fa-list'
                    },
                    {
                        'name': 'tax_groups',
                        'label': 'Tax Groups',
                        'url': 'accounting:tax_group_list',
                        'permission': 'accounting.view_tax_group',
                        'icon': 'fas fa-layer-group'
                    }
                ]
            }
        ]
    }
] 