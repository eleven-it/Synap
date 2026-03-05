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
    path('proveedores/search/', views.proveedor_search_api, name='proveedor_search'),
    path('articulos/search/', views.articulo_search_api, name='articulo_search'),
    # APIs para administraNET Gestión
    path('provincias/', views.provincias_api, name='provincias_api'),
    path('departamentos/', views.departamentos_api, name='departamentos_api'),
    # Fecha/hora servidor (barra de estado, Principal)
    path('fecha-servidor/', views.fecha_servidor_api, name='fecha_servidor'),
    # Geolocalización (Google Geocoding; usado en CargaSucursal, Carga_ClienteDomicilio, etc.)
    path('geocode/', views.geocode_api, name='geocode'),
    # Tipos de cobro por envío por sucursal (paridad ABM_Sucursal_Envio / CargaSucursal_Envio)
    path('sucursales/zonas/', views.sucursal_zonas_list_api, name='sucursal_zonas'),
    path('sucursales/<int:id_sucursal>/tipos-envio/', views.sucursal_tipos_envio_list_or_create_api, name='sucursal_tipos_envio_list'),
    path('sucursales/<int:id_sucursal>/tipos-envio/<int:id_tipo_envio>/', views.sucursal_tipo_envio_update_or_delete_api, name='sucursal_tipo_envio_update'),
    # Stock AdministraNET: alta de movimiento (una transacción)
    path('movimiento-stock/', views.movimiento_stock_alta_api, name='movimiento_stock_alta'),
    # Conocimiento para Support RAG (GET items para ingesta)
    path('support/conocimiento/', views.support_conocimiento_api, name='support_conocimiento'),
] 