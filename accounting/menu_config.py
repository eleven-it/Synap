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
            {
                'name': 'chart_of_accounts',
                'label': 'Chart of Accounts',
                'url': 'accounting:account_list',
                'permission': 'accounting.view_account',
                'icon': 'fas fa-sitemap',
                'order': 1
            },
            {
                'name': 'journal_entries',
                'label': 'Journal Entries',
                'url': 'accounting:entry_list',
                'permission': 'accounting.view_entry',
                'icon': 'fas fa-book',
                'order': 2
            },
            {
                'name': 'taxes',
                'label': 'Taxes',
                'url': 'accounting:tax_list',
                'permission': 'accounting.view_tax',
                'icon': 'fas fa-percentage',
                'order': 3
            },
            {
                'name': 'fiscal_positions',
                'label': 'Fiscal Positions',
                'url': 'accounting:fiscal_position_list',
                'permission': 'accounting.view_fiscal_position',
                'icon': 'fas fa-globe',
                'order': 4
            },
            {
                'name': 'periods',
                'label': 'Accounting Periods',
                'url': 'accounting:period_list',
                'permission': 'accounting.view_period',
                'icon': 'fas fa-calendar',
                'order': 5
            },
            {
                'name': 'reports',
                'label': 'Reports',
                'icon': 'fas fa-chart-bar',
                'permission': 'accounting.view_report',
                'order': 6,
                'children': [
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
                    }
                ]
            },
            {
                'name': 'configuration',
                'label': 'Configuration',
                'icon': 'fas fa-cog',
                'permission': 'accounting.view_config',
                'order': 7,
                'children': [
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
                        'name': 'fiscal_years',
                        'label': 'Fiscal Years',
                        'url': 'accounting:fiscal_year_list',
                        'permission': 'accounting.view_fiscal_year',
                        'icon': 'fas fa-calendar-alt'
                    }
                ]
            }
        ]
    }
] 