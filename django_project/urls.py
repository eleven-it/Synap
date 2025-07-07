"""
URL configuration for django_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from core.views import error_403_view
from django.shortcuts import redirect

urlpatterns = [
    path('', lambda request: redirect('/core/dashboard/')),  # Redirección raíz
    path("__/auth/handler", TemplateView.as_view(template_name="login/auth_handler.html")),
    path("admin/", admin.site.urls),
    path("login/", include("login.urls")),  
    path("inventory/", include("inventory.urls", namespace="inventory")),    
    path("clientes/", include("clientes.urls", namespace="clientes")),
    path("proveedores/", include("proveedores.urls", namespace="proveedores")),
    path("core/", include("core.urls", namespace="core")),
    path('tiendanube/', include('tiendanube.urls', namespace='tiendanube')),
    path('sales/', include('sales.urls', namespace='sales')),
    path('api/sales/', include('sales.api.urls')),
    path('accounting/', include('accounting.urls', namespace='accounting')),
    path('purchases/', include('purchases.urls', namespace='purchases')),
    path('purchases/api/', include(('purchases.api.urls', 'api'), namespace='purchases-api')),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ⛔ Handler global de error 403    
handler403 = "core.views.error_403_view"