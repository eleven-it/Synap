from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'accounts-receivable', api_views.AccountReceivableViewSet, basename='accountreceivable')
router.register(r'credit-limit-logs', api_views.CreditLimitLogViewSet, basename='creditlimitlog')
router.register(r'financial-reports', api_views.FinancialReportViewSet, basename='financialreport')

urlpatterns = router.urls 