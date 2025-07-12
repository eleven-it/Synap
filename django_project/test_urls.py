"""
URL configuration for testing - only includes apps available in test_settings.py
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.shortcuts import redirect

# URLs base para pruebas (solo apps disponibles en test_settings.py)
urlpatterns = [
    path('', lambda request: redirect('/core/dashboard/')),  # Redirección raíz
    path("__/auth/handler", TemplateView.as_view(template_name="login/auth_handler.html")),
    path("admin/", admin.site.urls),
    path("login/", include("login.urls")),  
    path("core/", include("core.urls", namespace="core")),
    path("mercadopago/", include("mercadopago.urls")),
]

# Solo incluir sales si está disponible
try:
    urlpatterns.append(path('sales/', include('sales.urls', namespace='sales')))
except ImportError:
    pass

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# Handler global de error 403    
handler403 = "core.views.error_403_view" 