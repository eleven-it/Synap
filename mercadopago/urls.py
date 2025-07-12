from django.urls import path, include

urlpatterns = [
    path('api/', include('mercadopago.api.urls')),
    path('', include('mercadopago.admin_urls')),
] 