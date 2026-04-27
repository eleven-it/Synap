# -*- coding: utf-8 -*-
"""Vista de la herramienta global de migración de esquema MySQL (AdministraNET legacy)."""

import logging
import time

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

# Candado por conexión MySQL: evita dos migraciones Synap a la vez sobre la misma base (colas de ALTER duplicadas).
# GET_LOCK admite nombres de hasta 64 caracteres.
def _mysql_schema_advisory_lock_name(base_empresa: str) -> str:
    key = f"synap_mysql_schema:{(base_empresa or '').strip()}"
    return key[:64]


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
            t_req = time.monotonic()
            try:
                logger.info(
                    "legacy_mysql_schema: POST inicio base=%s action=%s provider=%s",
                    base_empresa,
                    action,
                    provider_id or "-",
                )
                with get_connection(base_empresa) as conn:
                    lock_name = _mysql_schema_advisory_lock_name(base_empresa)
                    cur_lock = conn.cursor()
                    cur_lock.execute("SELECT GET_LOCK(%s, 30)", (lock_name,))
                    lock_row = cur_lock.fetchone()
                    lock_ok = lock_row is not None and lock_row[0] == 1
                    if not lock_ok:
                        cur_lock.close()
                        messages.error(
                            request,
                            "No se pudo iniciar la migración: otra operación de Synap ya tiene reservada "
                            "esta base (o agotó los 30 s de espera). Cierre otras pestañas que estén migrando "
                            "la misma empresa e inténtelo de nuevo.",
                        )
                        logger.warning(
                            "legacy_mysql_schema: GET_LOCK no adquirido base=%s action=%s retorno=%s",
                            base_empresa,
                            action,
                            lock_row[0] if lock_row else None,
                        )
                    else:
                        try:
                            if action == "run_all":
                                last_result = run_all_providers(conn)
                            elif action == "run_one" and provider_id:
                                last_result = run_provider_by_id(provider_id, conn)
                            else:
                                messages.warning(request, "Acción no reconocida.")
                        finally:
                            try:
                                cur_lock.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                            except Exception as rel_err:
                                logger.debug("legacy_mysql_schema: RELEASE_LOCK: %s", rel_err)
                            try:
                                cur_lock.close()
                            except Exception:
                                pass
                logger.info(
                    "legacy_mysql_schema: POST fin base=%s action=%s duracion_s=%.2f",
                    base_empresa,
                    action,
                    time.monotonic() - t_req,
                )
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
                logger.exception(
                    "legacy_mysql_schema: error tras %.2fs base=%s action=%s: %s",
                    time.monotonic() - t_req,
                    base_empresa,
                    action,
                    e,
                )
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
