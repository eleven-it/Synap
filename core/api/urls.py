from django.urls import path
from . import views

app_name = 'core_api'

urlpatterns = [
    # API para búsqueda de contactos
    path('contacts/search/', views.contact_search_api, name='contact_search'),
    # API para búsqueda de países
    path('countries/search/', views.country_search_api, name='country_search'),
    # API para búsqueda de responsabilidades fiscales
    path('fiscal-responsibilities/search/', views.fiscal_responsibility_search_api, name='fiscal_responsibility_search'),
    # API para búsqueda de estados/provincias
    path('states/search/', views.state_search_api, name='state_search'),
    path('currency/search/', views.currency_search_api, name='currency_search'),
    # APIs para administraNET Gestión
    path('provincias/', views.provincias_api, name='provincias_api'),
    path('departamentos/', views.departamentos_api, name='departamentos_api'),
] 