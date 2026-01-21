"""
URLs para las APIs del módulo Strategic Insights & Alignment (SIA)
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from sia.api import views

router = DefaultRouter()
router.register(r'departments', views.DepartmentViewSet, basename='department')
router.register(r'evaluation-cycles', views.EvaluationCycleViewSet, basename='evaluation-cycle')
router.register(r'survey-responses', views.StrategicSurveyResponseViewSet, basename='survey-response')
router.register(r'foda-items', views.FodaItemViewSet, basename='foda-item')
router.register(r'ratings', views.RatingViewSet, basename='rating')
router.register(r'open-answers', views.OpenAnswerViewSet, basename='open-answer')
router.register(r'came-actions', views.CameActionViewSet, basename='came-action')

app_name = 'sia_api'

urlpatterns = [
    path('', include(router.urls)),
    # Endpoint para datos consolidados del dashboard
    path('dashboard-data/', views.DashboardDataAPIView.as_view(), name='dashboard-data'),
]

