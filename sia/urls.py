"""
URLs para el módulo Strategic Insights & Alignment (SIA)
"""
from django.urls import path, include
from sia import views

app_name = 'sia'

urlpatterns = [
    # Dashboard principal
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Ciclos de evaluación
    path('cycles/', views.EvaluationCycleListView.as_view(), name='evaluation_cycle_list'),
    path('cycles/create/', views.EvaluationCycleCreateView.as_view(), name='evaluation_cycle_create'),
    path('cycles/<int:pk>/', views.EvaluationCycleDetailView.as_view(), name='evaluation_cycle_detail'),
    path('cycles/<int:pk>/edit/', views.EvaluationCycleUpdateView.as_view(), name='evaluation_cycle_update'),
    path('cycles/<int:pk>/export/pdf/', views.CyclePdfReportView.as_view(), name='cycle_pdf_export'),
    path('cycles/<int:pk>/export/excel/', views.CycleExcelReportView.as_view(), name='cycle_excel_export'),
    
    # Respuestas de encuesta
    path('responses/create/', views.StrategicSurveyResponseCreateView.as_view(), name='survey_response_create'),
    path('responses/<int:pk>/', views.StrategicSurveyResponseDetailView.as_view(), name='survey_response_detail'),
    
    # Departamentos
    path('departments/', views.DepartmentListView.as_view(), name='department_list'),
    path('departments/create/', views.DepartmentCreateView.as_view(), name='department_create'),
    path('departments/<int:pk>/edit/', views.DepartmentUpdateView.as_view(), name='department_update'),
    path('departments/<int:pk>/delete/', views.DepartmentDeleteView.as_view(), name='department_delete'),
    
    # APIs (incluidas desde api/urls.py)
    path('api/', include('sia.api.urls')),
]

