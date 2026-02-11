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
from core.views.media_views import serve_media_file
from django.shortcuts import redirect

# URLs base (siempre disponibles)
urlpatterns = [
    path('', lambda request: redirect('/core/dashboard/')),  # Redirección raíz
    path("__/auth/handler", TemplateView.as_view(template_name="login/auth_handler.html")),
    path("admin/", admin.site.urls),
    path("login/", include("login.urls")),  
    path("core/", include("core.urls", namespace="core")),
    # Vista alternativa para servir archivos media cuando el servidor web no está configurado
    path("media/<path:path>", serve_media_file, name="serve_media"),
    # Módulos deshabilitados para administraNET Analytics
    # path("mercadopago/", include("mercadopago.urls")),
    # path("tiendanube-adminet/", include("tiendanube_administranet.urls", namespace="tiendanube_administranet")),
    # path("tiendanube/", include("tiendanube.urls", namespace="tiendanube")),
]

# URLs críticas siempre disponibles (workaround para tests y desarrollo)
urlpatterns.extend([
    # Módulos deshabilitados para administraNET Analytics
    # path('accounting/', include('accounting.urls', namespace='accounting')),
    # path('sales/', include('sales.urls', namespace='sales')),
    # path('api/sales/', include('sales.api.urls')),
    path('core/api/', include('core.api.urls', namespace='core_api')),
    # path('administraNET_integration/', include('administraNET_integration.urls', namespace='administraNET_integration')),
    # path('api/tiendanube-adminet/', include('tiendanube_administranet.api.urls', namespace='tiendanube_administranet_api')),
])

# URLs de módulos dinámicos
try:
    from core.url_registry import url_registry
    module_url_patterns = url_registry.get_module_url_patterns()
    urlpatterns.extend(module_url_patterns)
except ImportError:
    # Fallback: URLs estáticas si el sistema de módulos no está disponible
    # Módulos deshabilitados para administraNET Analytics
    # urlpatterns.extend([
    #     path("inventory/", include("inventory.urls", namespace="inventory")),    
    #     path("sales/", include("sales.urls", namespace="sales")),
    #     path('api/sales/', include('sales.api.urls')),
    #     path('purchases/', include('purchases.urls', namespace='purchases')),
    #     path('purchases/api/', include(('purchases.api.urls', 'api'), namespace='purchases-api')),
    # ])
    pass

# Servir archivos estáticos y media
# En desarrollo (DEBUG=True), Django los sirve directamente
# En producción, el servidor web (nginx/apache) debería servir estos archivos,
# pero los mantenemos aquí como fallback para desarrollo y para casos donde
# el servidor web no esté configurado correctamente
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # En producción, también servir media files como fallback
    # Esto es necesario si el servidor web no está configurado para servir /media/
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# ⛔ Handler global de error 403    
handler403 = "core.views.error_403_view"

# Módulos deshabilitados para administraNET Analytics
# Logistics web
# urlpatterns.extend([
#     path('logistics/', include('logistics.urls', namespace='logistics')),
# ])

# Finance web (mantener reports)
urlpatterns.extend([
    # path('finance/', include('finance.urls', namespace='finance')),
    # path('support/', include('support_ai.urls', namespace='support_ai')),
    path('reports/', include('reports.urls', namespace='reports')),
    path('sia/', include('sia.urls', namespace='sia')),
])

# Logistics API
# urlpatterns.extend([
#     path('api/logistics/', include('logistics.api_urls')),
# ])

# Finance API (mantener reports)
urlpatterns.extend([
    # path('api/finance/', include('finance.api_urls')),
    path('api/reports/', include('reports.api_urls', namespace='reports-api')),
    path('api/sia/', include('sia.api.urls', namespace='sia-api')),
    path('api/self-checkout/', include('self_checkout.api_urls')),
])

# Reports AI - ELIMINADO (No necesario para instalación mínima)
# urlpatterns.extend([
#     path('reports-ai/', include('reports_ai.urls', namespace='reports_ai')),
# ])