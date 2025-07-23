from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from .models import AccountReceivable, CreditLimitLog, FinancialReport
from .forms import AccountReceivableForm, CreditLimitLogForm, FinancialReportForm

# AccountReceivable
class AccountReceivableListView(ListView):
    model = AccountReceivable
    template_name = 'finance/account_receivable_list.html'
    context_object_name = 'accounts_receivable'

class AccountReceivableDetailView(DetailView):
    model = AccountReceivable
    template_name = 'finance/account_receivable_detail.html'
    context_object_name = 'accountreceivable'

class AccountReceivableCreateView(CreateView):
    model = AccountReceivable
    form_class = AccountReceivableForm
    template_name = 'finance/account_receivable_form.html'
    success_url = reverse_lazy('finance:account_receivable_list')

class AccountReceivableUpdateView(UpdateView):
    model = AccountReceivable
    form_class = AccountReceivableForm
    template_name = 'finance/account_receivable_form.html'
    success_url = reverse_lazy('finance:account_receivable_list')

class AccountReceivableDeleteView(DeleteView):
    model = AccountReceivable
    template_name = 'finance/account_receivable_confirm_delete.html'
    success_url = reverse_lazy('finance:account_receivable_list')

# CreditLimitLog
class CreditLimitLogListView(ListView):
    model = CreditLimitLog
    template_name = 'finance/creditlimitlog_list.html'
    context_object_name = 'creditlimitlogs'

class CreditLimitLogDetailView(DetailView):
    model = CreditLimitLog
    template_name = 'finance/creditlimitlog_detail.html'
    context_object_name = 'creditlimitlog'

class CreditLimitLogCreateView(CreateView):
    model = CreditLimitLog
    form_class = CreditLimitLogForm
    template_name = 'finance/creditlimitlog_form.html'
    success_url = reverse_lazy('finance:creditlimitlog_list')

class CreditLimitLogUpdateView(UpdateView):
    model = CreditLimitLog
    form_class = CreditLimitLogForm
    template_name = 'finance/creditlimitlog_form.html'
    success_url = reverse_lazy('finance:creditlimitlog_list')

class CreditLimitLogDeleteView(DeleteView):
    model = CreditLimitLog
    template_name = 'finance/creditlimitlog_confirm_delete.html'
    success_url = reverse_lazy('finance:creditlimitlog_list')

# FinancialReport
class FinancialReportListView(ListView):
    model = FinancialReport
    template_name = 'finance/financialreport_list.html'
    context_object_name = 'financialreports'

class FinancialReportDetailView(DetailView):
    model = FinancialReport
    template_name = 'finance/financialreport_detail.html'
    context_object_name = 'financialreport'

class FinancialReportCreateView(CreateView):
    model = FinancialReport
    form_class = FinancialReportForm
    template_name = 'finance/financialreport_form.html'
    success_url = reverse_lazy('finance:financialreport_list')

class FinancialReportUpdateView(UpdateView):
    model = FinancialReport
    form_class = FinancialReportForm
    template_name = 'finance/financialreport_form.html'
    success_url = reverse_lazy('finance:financialreport_list')

class FinancialReportDeleteView(DeleteView):
    model = FinancialReport
    template_name = 'finance/financialreport_confirm_delete.html'
    success_url = reverse_lazy('finance:financialreport_list') 