"""URLs de la API."""
from django.urls import path, include

urlpatterns = [
    path("health", include("apps.api.views_health")),
    path("", include("apps.api.views_auth")),
    path("", include("apps.api.views_dashboard")),
    path("casos/", include("apps.api.views_cases")),
    path("empresas/", include("apps.api.views_companies")),
    path("usuarios-soporte/", include("apps.api.views_support_users")),
    path("agentes/", include("apps.api.views_agents")),
    path("metricas/", include("apps.api.views_metrics")),
    path("copiloto/", include("apps.api.views_copilot")),
    path("knowledge/", include("apps.api.views_knowledge")),
    path("config/", include("apps.system_config.urls")),
    path("", include("apps.api.views_webhooks")),
]
