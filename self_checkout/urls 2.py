from django.urls import path
from . import views

app_name = 'self_checkout'

urlpatterns = [
    path('', views.index_view, name='index'),
    path('kiosco/<str:kiosk_id>/', views.kiosco_view, name='kiosco'),
    path('ticket/<int:cart_id>/', views.ticket_print_view, name='ticket_print'),
    path('config/', views.config_list, name='config_list'),
    path('config/carritos-pendientes/', views.carritos_pendientes_view, name='carritos_pendientes'),
    path('config/nuevo/', views.config_create, name='config_create'),
    path('config/<str:kiosk_id>/editar/', views.config_edit, name='config_edit'),
    path('talonarios/', views.talonarios_list, name='talonarios_list'),
    path('talonarios/nuevo-pv/', views.punto_venta_create, name='punto_venta_create'),
    path('talonarios/agregar/', views.talonarios_create, name='talonarios_create'),
    path('talonarios/<int:id_punto_venta>/<str:tipo_comprobante>/editar/', views.talonarios_edit, name='talonarios_edit'),
]
