from django.urls import path
from . import views

app_name = 'finance'

urlpatterns = [
    # AccountReceivable
    path('accounts-receivable/', views.AccountReceivableListView.as_view(), name='account_receivable_list'),
    path('accounts-receivable/create/', views.AccountReceivableCreateView.as_view(), name='account_receivable_create'),
    path('accounts-receivable/<int:pk>/', views.AccountReceivableDetailView.as_view(), name='account_receivable_detail'),
    path('accounts-receivable/<int:pk>/edit/', views.AccountReceivableUpdateView.as_view(), name='account_receivable_edit'),
    path('accounts-receivable/<int:pk>/delete/', views.AccountReceivableDeleteView.as_view(), name='account_receivable_delete'),

    # CreditLimitLog
    path('credit-limit-logs/', views.CreditLimitLogListView.as_view(), name='creditlimitlog_list'),
    path('credit-limit-logs/create/', views.CreditLimitLogCreateView.as_view(), name='creditlimitlog_create'),
    path('credit-limit-logs/<int:pk>/', views.CreditLimitLogDetailView.as_view(), name='creditlimitlog_detail'),
    path('credit-limit-logs/<int:pk>/edit/', views.CreditLimitLogUpdateView.as_view(), name='creditlimitlog_edit'),
    path('credit-limit-logs/<int:pk>/delete/', views.CreditLimitLogDeleteView.as_view(), name='creditlimitlog_delete'),

    # FinancialReport
    path('financial-reports/', views.FinancialReportListView.as_view(), name='financialreport_list'),
    path('financial-reports/create/', views.FinancialReportCreateView.as_view(), name='financialreport_create'),
    path('financial-reports/<int:pk>/', views.FinancialReportDetailView.as_view(), name='financialreport_detail'),
    path('financial-reports/<int:pk>/edit/', views.FinancialReportUpdateView.as_view(), name='financialreport_edit'),
    path('financial-reports/<int:pk>/delete/', views.FinancialReportDeleteView.as_view(), name='financialreport_delete'),

    # AI SQL Chat UI
    path('ai-sql-chat/', views.SqlChatView.as_view(), name='ai_sql_chat'),

    # API Endpoints
    path('api/finance/ingest', views.ingest, name='finance_ingest'),
    path('api/finance/monthly-report', views.monthly_report, name='finance_monthly_report'),
    path('api/ai/sql-chat', views.sql_chat, name='sql_chat'),
] 