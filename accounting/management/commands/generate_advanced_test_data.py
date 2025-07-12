from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import random

from accounting.models import (
    ChartOfAccounts, Journal, JournalEntry, JournalEntryLine, 
    Tax, TaxGroup, FiscalPosition, TaxLine, JournalTypes, EntryStates
)
from core.models import Empresa

User = get_user_model()

class Command(BaseCommand):
    help = 'Generate advanced test data for accounting reports with historical data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--company',
            type=str,
            help='Company name to create data for',
            default='Test Company'
        )
        parser.add_argument(
            '--entries',
            type=int,
            default=50,
            help='Number of entries to create per period'
        )

    def handle(self, *args, **options):
        company_name = options['company']
        entries_per_period = options['entries']
        
        # Get or create company
        empresa, created = Empresa.objects.get_or_create(
            nombre=company_name
        )
        
        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created company: {company_name}')
            )
        
        # Get active user
        user = User.objects.filter(is_active=True).first()
        if not user:
            self.stdout.write(
                self.style.ERROR('No active user found. Please create a user first.')
            )
            return
        
        # Get or create accounts
        accounts = self._get_or_create_accounts(empresa)
        
        # Get or create journals
        journals = self._get_or_create_journals(empresa)
        
        # Generate data for current period (last 30 days)
        current_start = timezone.now().date() - timedelta(days=30)
        current_end = timezone.now().date()
        
        self.stdout.write(f'Generating {entries_per_period} entries for current period...')
        self._generate_period_entries(
            empresa, user, accounts, journals, 
            current_start, current_end, entries_per_period
        )
        
        # Generate data for previous period (30 days before)
        previous_start = current_start - timedelta(days=30)
        previous_end = current_start - timedelta(days=1)
        
        self.stdout.write(f'Generating {entries_per_period} entries for previous period...')
        self._generate_period_entries(
            empresa, user, accounts, journals, 
            previous_start, previous_end, entries_per_period
        )
        
        # Generate some entries with issues to trigger alerts
        self._generate_problematic_entries(empresa, user, accounts, journals)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated advanced test data for {company_name}'
            )
        )

    def _get_or_create_accounts(self, empresa):
        """Get or create basic accounts"""
        accounts = []
        
        # Asset accounts
        cash_account, _ = ChartOfAccounts.objects.get_or_create(
            code='1001',
            empresa=empresa,
            defaults={
                'name': 'Cash',
                'account_type': 'assets',
                'is_active': True
            }
        )
        accounts.append(cash_account)
        
        bank_account, _ = ChartOfAccounts.objects.get_or_create(
            code='1002',
            empresa=empresa,
            defaults={
                'name': 'Bank Account',
                'account_type': 'assets',
                'is_active': True
            }
        )
        accounts.append(bank_account)
        
        # Liability accounts
        accounts_payable, _ = ChartOfAccounts.objects.get_or_create(
            code='2001',
            empresa=empresa,
            defaults={
                'name': 'Accounts Payable',
                'account_type': 'liabilities',
                'is_active': True
            }
        )
        accounts.append(accounts_payable)
        
        # Equity accounts
        equity_account, _ = ChartOfAccounts.objects.get_or_create(
            code='3001',
            empresa=empresa,
            defaults={
                'name': 'Owner Equity',
                'account_type': 'equity',
                'is_active': True
            }
        )
        accounts.append(equity_account)
        
        # Revenue accounts
        sales_revenue, _ = ChartOfAccounts.objects.get_or_create(
            code='4001',
            empresa=empresa,
            defaults={
                'name': 'Sales Revenue',
                'account_type': 'income',
                'is_active': True
            }
        )
        accounts.append(sales_revenue)
        
        # Expense accounts
        operating_expenses, _ = ChartOfAccounts.objects.get_or_create(
            code='5001',
            empresa=empresa,
            defaults={
                'name': 'Operating Expenses',
                'account_type': 'expenses',
                'is_active': True
            }
        )
        accounts.append(operating_expenses)
        
        return accounts

    def _get_or_create_journals(self, empresa):
        """Get or create basic journals"""
        journals = []
        
        # Sales journal
        sales_journal, _ = Journal.objects.get_or_create(
            code='SALES',
            empresa=empresa,
            defaults={
                'name': 'Sales Journal',
                'journal_type': JournalTypes.SALE,
                'is_active': True
            }
        )
        journals.append(sales_journal)
        
        # Purchase journal
        purchase_journal, _ = Journal.objects.get_or_create(
            code='PURCH',
            empresa=empresa,
            defaults={
                'name': 'Purchase Journal',
                'journal_type': JournalTypes.PURCHASE,
                'is_active': True
            }
        )
        journals.append(purchase_journal)
        
        # General journal
        general_journal, _ = Journal.objects.get_or_create(
            code='GENERAL',
            empresa=empresa,
            defaults={
                'name': 'General Journal',
                'journal_type': JournalTypes.MISCELLANEOUS,
                'is_active': True
            }
        )
        journals.append(general_journal)
        
        return journals

    def _generate_period_entries(self, empresa, user, accounts, journals, start_date, end_date, count):
        """Generate entries for a specific period"""
        days_range = (end_date - start_date).days
        
        for i in range(count):
            # Random date within period
            random_days = random.randint(0, days_range)
            entry_date = start_date + timedelta(days=random_days)
            
            # Random journal
            journal = random.choice(journals)
            
            # Generate unique number
            entry_number = f'JE-{entry_date.strftime("%Y%m%d")}-{i+1:03d}'
            
            # Create entry
            entry = JournalEntry.objects.create(
                empresa=empresa,
                journal=journal,
                number=entry_number,
                date=entry_date,
                reference=f'TEST-{entry_date.strftime("%Y%m%d")}-{i+1:03d}',
                narration=f'Test entry {i+1} for {entry_date}',
                state=EntryStates.DRAFT if random.random() < 0.2 else EntryStates.POSTED,
                created_by=user
            )
            
            # Create lines (2-4 lines per entry)
            num_lines = random.randint(2, 4)
            total_debit = Decimal('0')
            total_credit = Decimal('0')
            
            for j in range(num_lines):
                account = random.choice(accounts)
                amount = Decimal(str(random.randint(100, 5000)))
                
                # Alternate debit/credit
                if j % 2 == 0:
                    debit = amount
                    credit = Decimal('0')
                    total_debit += debit
                else:
                    debit = Decimal('0')
                    credit = amount
                    total_credit += credit
                
                JournalEntryLine.objects.create(
                    entry=entry,
                    account=account,
                    name=f'Line {j+1} for {account.name}',
                    debit=debit,
                    credit=credit
                )
            
            # Ensure balance (add balancing line if needed)
            if total_debit != total_credit:
                balancing_account = random.choice(accounts)
                if total_debit > total_credit:
                    JournalEntryLine.objects.create(
                        entry=entry,
                        account=balancing_account,
                        name='Balancing line',
                        debit=Decimal('0'),
                        credit=total_debit - total_credit
                    )
                else:
                    JournalEntryLine.objects.create(
                        entry=entry,
                        account=balancing_account,
                        name='Balancing line',
                        debit=total_credit - total_debit,
                        credit=Decimal('0')
                    )

    def _generate_problematic_entries(self, empresa, user, accounts, journals):
        """Generate entries with issues to trigger alerts"""
        # Entry with significant imbalance
        unbalanced_entry = JournalEntry.objects.create(
            empresa=empresa,
            journal=random.choice(journals),
            number='UNBALANCED-001',
            date=timezone.now().date(),
            reference='UNBALANCED-001',
            narration='Entry with significant imbalance',
            state=EntryStates.POSTED,
            created_by=user
        )
        
        JournalEntryLine.objects.create(
            entry=unbalanced_entry,
            account=accounts[0],
            name='Large debit',
            debit=Decimal('10000'),
            credit=Decimal('0')
        )
        
        JournalEntryLine.objects.create(
            entry=unbalanced_entry,
            account=accounts[1],
            name='Small credit',
            debit=Decimal('0'),
            credit=Decimal('1000')
        )
        
        # Several draft entries (low posting efficiency)
        for i in range(10):
            draft_entry = JournalEntry.objects.create(
                empresa=empresa,
                journal=random.choice(journals),
                number=f'DRAFT-{i+1:03d}',
                date=timezone.now().date() - timedelta(days=random.randint(1, 7)),
                reference=f'DRAFT-{i+1:03d}',
                narration=f'Draft entry {i+1}',
                state=EntryStates.DRAFT,
                created_by=user
            )
            
            # Add balanced lines
            JournalEntryLine.objects.create(
                entry=draft_entry,
                account=accounts[0],
                name='Draft line 1',
                debit=Decimal('1000'),
                credit=Decimal('0')
            )
            
            JournalEntryLine.objects.create(
                entry=draft_entry,
                account=accounts[1],
                name='Draft line 2',
                debit=Decimal('0'),
                credit=Decimal('1000')
            ) 