from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ClientViewSet, ContactViewSet, SalesRepresentativeViewSet,
    TPVProductViewSet, TPVPaymentViewSet, ClientTagViewSet, 
    ClientAttachmentViewSet, AutocompleteViewSet
)

# Configurar router para las vistas
router = DefaultRouter()
router.register(r'clients', ClientViewSet, basename='client')
router.register(r'contacts', ContactViewSet, basename='contact')
router.register(r'sales-representatives', SalesRepresentativeViewSet, basename='sales-representative')
router.register(r'client-tags', ClientTagViewSet, basename='client-tag')
router.register(r'client-attachments', ClientAttachmentViewSet, basename='client-attachment')
router.register(r'autocomplete', AutocompleteViewSet, basename='autocomplete')

# TPV endpoints
router.register(r'products', TPVProductViewSet, basename='tpv-product')
router.register(r'tpv', TPVPaymentViewSet, basename='tpv-payment')

# URLs de la API
app_name = 'sales_api'
urlpatterns = [
    # Incluir todas las rutas del router
    path('', include(router.urls)),
]

# Agregar URLs de autenticación si es necesario
# urlpatterns += [
#     path('auth/', include('rest_framework.urls')),
# ] 