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

# URLs base (siempre disponibles)
urlpatterns = [
    path('', lambda request: redirect('/core/dashboard/')),  # Redirección raíz
    path("__/auth/handler", TemplateView.as_view(template_name="login/auth_handler.html")),
    path("admin/", admin.site.urls),
    path("login/", include("login.urls")),  
    path("core/", include("core.urls", namespace="core")),
    path("mercadopago/", include("mercadopago.urls")),
    path("tiendanube-adminet/", include("tiendanube_administranet.urls", namespace="tiendanube_administranet")),
    path("tiendanube/", include("tiendanube.urls", namespace="tiendanube")),
]

# URLs críticas siempre disponibles (workaround para tests y desarrollo)
urlpatterns.extend([
    path('accounting/', include('accounting.urls', namespace='accounting')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('sales/', include('sales.urls', namespace='sales')),
    path('api/sales/', include('sales.api.urls')),
    path('core/api/', include('core.api.urls', namespace='core_api')),
    path('administraNET_integration/', include('administraNET_integration.urls', namespace='administraNET_integration')),
    path('api/tiendanube-adminet/', include('tiendanube_administranet.api.urls', namespace='tiendanube_administranet_api')),
])

# URLs de módulos dinámicos
try:
    from core.url_registry import url_registry
    module_url_patterns = url_registry.get_module_url_patterns()
    urlpatterns.extend(module_url_patterns)
except ImportError:
    # Fallback: URLs estáticas si el sistema de módulos no está disponible
    urlpatterns.extend([
        path("inventory/", include("inventory.urls", namespace="inventory")),    
        path("sales/", include("sales.urls", namespace="sales")),
        path('api/sales/', include('sales.api.urls')),
        path('purchases/', include('purchases.urls', namespace='purchases')),
        path('purchases/api/', include(('purchases.api.urls', 'api'), namespace='purchases-api')),
        path('reports/', include('reports.urls', namespace='reports')),
    ])

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ⛔ Handler global de error 403    
handler403 = "core.views.error_403_view"

# Logistics web
urlpatterns.extend([
    path('logistics/', include('logistics.urls', namespace='logistics')),
])

# Finance web
urlpatterns.extend([
    path('finance/', include('finance.urls', namespace='finance')),
])

# Logistics API
urlpatterns.extend([
    path('api/logistics/', include('logistics.api_urls')),
])

# Finance API
urlpatterns.extend([
    path('api/finance/', include('finance.api_urls')),
])