# -*- coding: utf-8 -*-
"""Vista de la herramienta global de migración de esquema MySQL (AdministraNET legacy)."""

import logging

from django.contrib import messages
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from core.decorators import administranet_login_required, solo_usuario_supervisor
from core.mysql_pool import get_connection
from core.services.legacy_mysql_schema.catalog import (
    PROVIDER_REGISTRY,
    run_all_providers,
    run_provider_by_id,
)

logger = logging.getLogger(__name__)


@require_http_methods(["GET", "POST"])
@administranet_login_required
@solo_usuario_supervisor
def legacy_mysql_schema_tool(request):
    """
    Ejecuta migraciones de esquema MySQL sobre ``base_empresa`` de la sesión.
    Solo ``cod_usuario == supervisor`` (ver decoradores).
    """
    session_user = request.session.get("user") or {}
    base_empresa = (session_user.get("base_empresa") or "").strip()
    last_result = None

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        provider_id = (request.POST.get("provider") or "").strip()
        if not base_empresa:
            messages.error(request, "No hay base de empresa en sesión; no se puede ejecutar.")
        else:
            try:
                with get_connection(base_empresa) as conn:
                    if action == "run_all":
                        last_result = run_all_providers(conn)
                    elif action == "run_one" and provider_id:
                        last_result = run_provider_by_id(provider_id, conn)
                    else:
                        messages.warning(request, "Acción no reconocida.")
                if last_result is not None:
                    if last_result.get("success"):
                        messages.success(request, last_result.get("message") or "Completado.")
                    else:
                        messages.error(request, last_result.get("message") or "Error.")
                    logger.info(
                        "legacy_mysql_schema: cod_usuario=%s base=%s action=%s provider=%s ok=%s",
                        getattr(request.user, "cod_usuario", None),
                        base_empresa,
                        action,
                        provider_id,
                        last_result.get("success"),
                    )
            except Exception as e:
                logger.exception("legacy_mysql_schema: %s", e)
                messages.error(request, f"Error de conexión o ejecución: {e}")

    return render(
        request,
        "core/legacy_mysql_schema.html",
        {
            "base_empresa": base_empresa,
            "providers": PROVIDER_REGISTRY,
            "last_result": last_result,
        },
    )
