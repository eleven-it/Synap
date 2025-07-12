from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Reportes
    path('reports/', views.report_list, name='report_list'),
    path('reports/create/', views.report_create, name='report_create'),
    path('reports/<int:pk>/', views.report_detail, name='report_detail'),
    path('reports/<int:pk>/edit/', views.report_edit, name='report_edit'),
    path('reports/<int:pk>/delete/', views.report_delete, name='report_delete'),
    path('reports/<int:pk>/export/', views.report_export, name='report_export'),
    path('reports/<int:pk>/builder/', views.report_builder, name='report_builder'),
    
    # Plantillas
    path('templates/', views.template_list, name='template_list'),
    path('templates/create/', views.template_create, name='template_create'),
    path('templates/<int:pk>/', views.template_detail, name='template_detail'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    
    # Programaciones
    path('schedules/', views.schedule_list, name='schedule_list'),
    path('schedules/create/', views.schedule_create, name='schedule_create'),
    path('schedules/<int:pk>/', views.schedule_detail, name='schedule_detail'),
    path('schedules/<int:pk>/edit/', views.schedule_edit, name='schedule_edit'),
    
    # Biblioteca de componentes
    path('components/', views.component_library, name='component_library'),
    
    # APIs AJAX
    path('schedules/<int:pk>/toggle/', views.schedule_toggle, name='schedule_toggle'),
    
    # Constructor visual APIs
    path('reports/<int:pk>/config/', views.get_report_config, name='get_report_config'),
    path('reports/<int:pk>/config/save/', views.save_report_config, name='save_report_config'),
    path('reports/<int:pk>/preview/', views.report_preview, name='report_preview'),
] 