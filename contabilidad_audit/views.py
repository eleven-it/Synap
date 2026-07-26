"""Vistas de auditoría contable (UI canon reportes Synap).

Fase 1 (solo lectura): tablero verde/rojo por check, export CSV/Excel y
configuración de políticas. Mantiene intacto el contrato `?format=json`
del runner y los permisos Synap dedicados.
"""
from __future__ import annotations

import json
import logging
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404, HttpResponse, JsonResponse, StreamingHttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.decorators import administranet_login_required, tiene_permiso
from core.utils.administranet_types import to_int_or_none

from contabilidad_audit.models import (
    ALCANCE_RECOMPUTE_CHOICES,
    AprobacionREI,
    CATEGORIAS_PREFIJOS,
    EJERCICIOS_CERRADOS_CHOICES,
    POLITICA_CENTAVO_CHOICES,
    PREFIJOS_CUENTA_DEFAULT,
    PlanCorreccion,
    TRATAMIENTO_ANULADOS_CHOICES,
    PoliticaAuditoriaContable,
)
from contabilidad_audit.services.politicas import (
    calcular_config_hash,
    listar_historial_politica,
    registrar_historial_politica,
    resolver_politica,
    snapshot_desde_politica,
)
from contabilidad_audit.services.registry import CHECKS, CHECK_IDS_DEFAULT
from contabilidad_audit.services.runner import ejecutar_corrida
from core.mysql_pool import get_mysql_pool

logger = logging.getLogger(__name__)

SEVERIDAD_ETIQUETA = {
    "critico": "Crítico",
    "alto": "Alto",
    "medio": "Medio",
}

PERMISO_LEER = "contabilidad.auditoria.leer"
PERMISO_CONFIGURAR = "contabilidad.auditoria.configurar"
PERMISO_CORREGIR = "contabilidad.auditoria.corregir"
PERMISO_REI = "contabilidad.auditoria.rei"


def _usuario_identificador(request) -> str:
    user = getattr(request, "user", None)
    if user and getattr(user, "is_authenticated", False):
        return str(getattr(user, "cod_usuario", None) or getattr(user, "username", "") or "usuario")
    session_user = request.session.get("user", {})
    return str(session_user.get("cod_usuario") or session_user.get("nombre") or "usuario")


def _base_empresa_request(request) -> str | None:
    session_user = request.session.get("user", {})
    return request.GET.get("base_empresa") or session_user.get("base_empresa")


def _base_empresa_sesion(request) -> str | None:
    """Empresa base SIEMPRE desde la sesión (ignora cualquier ?base_empresa).

    Usada por el tablero, el dry-run y el endpoint de ejercicios/períodos para
    que el usuario no pueda cambiar la empresa por querystring.
    """
    session_user = request.session.get("user", {}) or {}
    return session_user.get("base_empresa")


def _tiene_permiso(user, codigo: str) -> bool:
    """Réplica de la lógica de `tiene_permiso` para chequeos en línea."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if hasattr(user, "is_admin") and user.is_admin():
        return True
    if (getattr(user, "cod_usuario", "") or "").lower() == "supervisor":
        return True
    if hasattr(user, "roles"):
        try:
            if any((rol.nombre or "").lower() == "administrador" for rol in user.roles.all()):
                return True
        except Exception:
            pass
    if hasattr(user, "tiene_permiso") and user.tiene_permiso(codigo):
        return True
    return False


def _checks_corregibles() -> list[str]:
    """Checks que el motor de corrección sabe planificar (`CHECKS_INCLUIDOS`).

    Import diferido: el servicio legacy es pesado y sólo hace falta para armar
    el contexto de la UI. Si no se puede importar, la UI degrada a «sin
    corrección automática» en todas las tarjetas.
    """
    try:
        from legacy_db.services.cont_recalculo_service import CHECKS_INCLUIDOS
    except Exception:  # noqa: BLE001 — degradación tolerable en el front
        logger.exception("No se pudo importar CHECKS_INCLUIDOS del motor de corrección")
        return []
    return list(CHECKS_INCLUIDOS)


def _checks_disponibles() -> list[dict]:
    """Metadatos de checks para poblar el selector del tablero."""
    disponibles = []
    for check_id in CHECK_IDS_DEFAULT:
        fn = CHECKS[check_id]
        severidad = getattr(fn, "severidad", "medio")
        disponibles.append(
            {
                "check_id": check_id,
                "titulo": getattr(fn, "titulo", check_id),
                "severidad": severidad,
                "severidad_label": SEVERIDAD_ETIQUETA.get(severidad, severidad),
            }
        )
    return disponibles


def _parse_filtros(request) -> dict:
    base_empresa = _base_empresa_sesion(request)
    id_ejercicio = request.GET.get("id_ejercicio")
    if not base_empresa:
        raise ValueError("No hay empresa base en la sesión.")
    if not id_ejercicio:
        raise ValueError("El parámetro id_ejercicio es obligatorio.")
    filtros = {
        "base_empresa": base_empresa,
        "id_ejercicio": int(id_ejercicio),
    }
    if request.GET.get("id_periodo"):
        filtros["id_periodo"] = int(request.GET["id_periodo"])
    if request.GET.get("fecha_desde"):
        filtros["fecha_desde"] = request.GET["fecha_desde"]
    if request.GET.get("fecha_hasta"):
        filtros["fecha_hasta"] = request.GET["fecha_hasta"]
    check_ids = request.GET.getlist("check_ids") or request.GET.getlist("check_id")
    if check_ids:
        filtros["check_ids"] = check_ids
    return filtros


def _contexto_tablero(request, filtros: dict | None = None) -> dict:
    """Contexto de render del tablero (plantilla canon reportes)."""
    filtros = filtros or {}
    user = getattr(request, "user", None)
    return {
        "titulo_pagina": "Auditoría de imputación contable",
        "base_empresa": filtros.get("base_empresa") or _base_empresa_sesion(request) or "",
        "id_ejercicio": filtros.get("id_ejercicio") or request.GET.get("id_ejercicio") or "",
        "id_periodo": filtros.get("id_periodo") or request.GET.get("id_periodo") or "",
        "check_ids_disponibles": CHECK_IDS_DEFAULT,
        "checks_disponibles": _checks_disponibles(),
        # Checks con corrección automática: habilitan el CTA «Generar
        # diagnóstico» en la tarjeta del kanban de resultados.
        "checks_corregibles": _checks_corregibles(),
        # Selección previa de diagnósticos: sólo la que llega explícita por URL.
        # El tablero arranca sin diagnósticos activos; el runner sigue aceptando
        # ausencia de `check_ids` como "todos" para scripts y tests.
        "checks_seleccionados": (
            filtros.get("check_ids")
            or request.GET.getlist("check_ids")
            or request.GET.getlist("check_id")
        ),
        "permiso_leer": PERMISO_LEER,
        "permiso_configurar": PERMISO_CONFIGURAR,
        "puede_configurar": _tiene_permiso(user, PERMISO_CONFIGURAR),
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
        "configuracion_url": reverse("contabilidad_audit:auditoria_configuracion"),
        "ejercicios_periodos_url": reverse("contabilidad_audit:auditoria_ejercicios_periodos"),
        "dry_run_url": reverse("contabilidad_audit:auditoria_dry_run"),
        "lotes_url": reverse("contabilidad_audit:auditoria_lotes"),
        "asientos_url": reverse("contabilidad_audit:auditoria_asientos"),
        "puede_corregir": _tiene_permiso(user, PERMISO_CORREGIR),
    }


@administranet_login_required
@tiene_permiso(PERMISO_LEER)
@require_GET
def auditoria_tablero(request):
    """
    GET /contabilidad/auditoria/

    - `?format=json`  → ejecuta corrida y devuelve JSON (contrato del runner).
    - `?format=csv|xlsx` → ejecuta corrida y descarga el detalle.
    - Sin `format`   → renderiza el tablero canon reportes (Alpine fetch al JSON).
    """
    formato = request.GET.get("format")

    if formato in ("json", "csv", "xlsx"):
        try:
            filtros = _parse_filtros(request)
        except ValueError as exc:
            if formato == "json":
                return JsonResponse({"error": str(exc)}, status=400)
            return HttpResponse(str(exc), status=400, content_type="text/plain; charset=utf-8")

        payload = ejecutar_corrida(
            base_empresa=filtros["base_empresa"],
            filtros=filtros,
            check_ids=filtros.get("check_ids"),
            usuario=_usuario_identificador(request),
        )

        if formato == "json":
            return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})
        if formato == "csv":
            from contabilidad_audit.services.export import exportar_corrida_csv

            return exportar_corrida_csv(payload)
        from contabilidad_audit.services.export import exportar_corrida_xlsx

        return exportar_corrida_xlsx(payload)

    # Render normal del tablero (sin ejecutar corrida en servidor).
    ctx = _contexto_tablero(request)
    ctx["auto_ejecutar"] = bool(ctx["id_ejercicio"] and ctx["base_empresa"])
    return render(request, "contabilidad_audit/auditoria_tablero.html", ctx)


def _label_ejercicio(id_ejercicio, descripcion: str, desde: str, hasta: str) -> str:
    rango = f"{desde} – {hasta}".strip(" –")
    base = descripcion or f"Ejercicio {id_ejercicio}"
    return f"{base} ({rango})" if rango else base


def _label_periodo(id_periodo, descripcion: str, desde: str, hasta: str) -> str:
    rango = f"{desde} – {hasta}".strip(" –")
    base = descripcion or f"Período {id_periodo}"
    return f"{base} ({rango})" if rango else base


def _es_cerrado(valor) -> bool:
    return str(valor or "").strip().lower() in ("si", "sí", "s", "1", "true")


@administranet_login_required
@tiene_permiso(PERMISO_LEER)
@require_GET
def auditoria_ejercicios_periodos(request):
    """
    GET /contabilidad/auditoria/ejercicios-periodos/

    Devuelve ejercicios y períodos de la empresa base de la SESIÓN (solo lectura
    legacy) para poblar los dropdowns predictivos del tablero. Orden por fecha
    descendente (más reciente arriba). Fechas dd/MM/yyyy.
    """
    base_empresa = _base_empresa_sesion(request)
    if not base_empresa:
        return JsonResponse(
            {
                "error": "No hay empresa base en la sesión.",
                "base_empresa": "",
                "ejercicios": [],
                "periodos": [],
            },
            status=400,
            json_dumps_params={"ensure_ascii": False},
        )

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT id_ejercicio, descripcion_ejercicio, fecdesde_ejercicio, "
                    "fechasta_ejercicio, cerrado FROM cont_ejercicio "
                    "ORDER BY fecdesde_ejercicio DESC, id_ejercicio DESC"
                )
                ejercicios_raw = cursor.fetchall()
                cursor.execute(
                    "SELECT id_periodo, id_ejercicio, descripcion_periodo, fecdesde_periodo, "
                    "fechasta_periodo, cerrado FROM cont_periodo "
                    "ORDER BY fecdesde_periodo DESC, id_periodo DESC"
                )
                periodos_raw = cursor.fetchall()
            finally:
                cursor.close()
    except Exception as exc:  # noqa: BLE001 — degradación tolerable en el front
        logger.exception("Error consultando ejercicios/períodos para %s", base_empresa)
        return JsonResponse(
            {
                "error": f"No se pudieron obtener ejercicios/períodos: {exc}",
                "base_empresa": base_empresa,
                "ejercicios": [],
                "periodos": [],
            },
            status=500,
            json_dumps_params={"ensure_ascii": False},
        )

    ejercicios = []
    for row in ejercicios_raw:
        id_ejercicio = int(row[0]) if row[0] is not None else None
        descripcion = (row[1] or "").strip()
        desde = _fecha_date_ui(row[2])
        hasta = _fecha_date_ui(row[3])
        ejercicios.append(
            {
                "id": id_ejercicio,
                "label": _label_ejercicio(id_ejercicio, descripcion, desde, hasta),
                "descripcion": descripcion,
                "desde": desde,
                "hasta": hasta,
                "cerrado": _es_cerrado(row[4]),
            }
        )

    periodos = []
    for row in periodos_raw:
        id_periodo = int(row[0]) if row[0] is not None else None
        id_ejercicio = int(row[1]) if row[1] is not None else None
        descripcion = (row[2] or "").strip()
        desde = _fecha_date_ui(row[3])
        hasta = _fecha_date_ui(row[4])
        periodos.append(
            {
                "id": id_periodo,
                "id_ejercicio": id_ejercicio,
                "label": _label_periodo(id_periodo, descripcion, desde, hasta),
                "descripcion": descripcion,
                "desde": desde,
                "hasta": hasta,
                "cerrado": _es_cerrado(row[5]),
            }
        )

    return JsonResponse(
        {
            "base_empresa": base_empresa,
            "ejercicios": ejercicios,
            "periodos": periodos,
        },
        json_dumps_params={"ensure_ascii": False},
    )


# ──────────────────────────────────────────────────────────────────────────
# Configuración de políticas
# ──────────────────────────────────────────────────────────────────────────

def _prefijos_desde_post(post) -> dict:
    prefijos: dict[str, list[str]] = {}
    for cat in CATEGORIAS_PREFIJOS:
        crudo = post.get(f"prefijos_{cat}", "")
        valores = [p.strip() for p in crudo.replace(";", ",").split(",") if p.strip()]
        prefijos[cat] = valores
    return prefijos


def _politica_a_form(base_empresa: str) -> dict:
    """Valores para el formulario: fila persistida si existe, sino política efectiva."""
    fila = PoliticaAuditoriaContable.objects.filter(base_empresa=base_empresa).first()
    efectiva = resolver_politica(base_empresa)
    if fila:
        prefijos = fila.prefijos_cuenta or efectiva.get("prefijos_cuenta") or dict(PREFIJOS_CUENTA_DEFAULT)
        datos = {
            "tratamiento_anulados": fila.tratamiento_anulados,
            "politica_centavo": fila.politica_centavo,
            "ejercicios_cerrados": fila.ejercicios_cerrados,
            "alcance_recompute": fila.alcance_recompute,
            "tolerancia_decimal": fila.tolerancia_decimal,
            "actualizado_por": fila.actualizado_por,
            "actualizado_en": fila.actualizado_en,
            "existe": True,
        }
    else:
        prefijos = efectiva.get("prefijos_cuenta") or dict(PREFIJOS_CUENTA_DEFAULT)
        datos = {
            "tratamiento_anulados": efectiva["tratamiento_anulados"],
            "politica_centavo": efectiva["politica_centavo"],
            "ejercicios_cerrados": efectiva["ejercicios_cerrados"],
            "alcance_recompute": efectiva["alcance_recompute"],
            "tolerancia_decimal": efectiva["tolerancia_decimal"],
            "actualizado_por": "",
            "actualizado_en": None,
            "existe": False,
        }
    datos["prefijos_items"] = [
        (cat, ", ".join(prefijos.get(cat) or [])) for cat in CATEGORIAS_PREFIJOS
    ]
    return datos


def _form_data_desde_post(post) -> dict:
    """Reconstruye el formulario desde el POST (para preservar edición ante errores)."""
    prefijos = _prefijos_desde_post(post)
    return {
        "tratamiento_anulados": post.get("tratamiento_anulados", ""),
        "politica_centavo": post.get("politica_centavo", ""),
        "ejercicios_cerrados": post.get("ejercicios_cerrados", ""),
        "alcance_recompute": post.get("alcance_recompute", ""),
        "tolerancia_decimal": post.get("tolerancia_decimal", ""),
        "actualizado_por": "",
        "actualizado_en": None,
        "existe": True,
        "prefijos_items": [(cat, ", ".join(prefijos.get(cat) or [])) for cat in CATEGORIAS_PREFIJOS],
    }


def _historial_ui(base_empresa: str) -> list[dict]:
    """Formatea historial de política para plantilla (fechas dd/MM/yyyy)."""
    return [
        {
            **fila,
            "cambiado_en_ui": _fecha_ui(fila["cambiado_en"]),
        }
        for fila in listar_historial_politica(base_empresa)
    ]


def _contexto_configuracion(request, base_empresa: str, form_data: dict | None = None) -> dict:
    user = getattr(request, "user", None)
    efectiva = resolver_politica(base_empresa)
    datos = form_data or _politica_a_form(base_empresa)
    return {
        "titulo_pagina": "Configuración de auditoría contable",
        "base_empresa": base_empresa,
        "base_default": PoliticaAuditoriaContable.BASE_DEFAULT,
        "es_default": base_empresa == PoliticaAuditoriaContable.BASE_DEFAULT,
        "datos": datos,
        "config_hash": calcular_config_hash(efectiva),
        "choices_anulados": TRATAMIENTO_ANULADOS_CHOICES,
        "choices_centavo": POLITICA_CENTAVO_CHOICES,
        "choices_cerrados": EJERCICIOS_CERRADOS_CHOICES,
        "choices_alcance": ALCANCE_RECOMPUTE_CHOICES,
        "categorias_prefijos": CATEGORIAS_PREFIJOS,
        "puede_configurar": _tiene_permiso(user, PERMISO_CONFIGURAR),
        "permiso_configurar": PERMISO_CONFIGURAR,
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
        "configuracion_url": reverse("contabilidad_audit:auditoria_configuracion"),
        "historial_url": reverse("contabilidad_audit:auditoria_configuracion_historial"),
        "historial": _historial_ui(base_empresa),
    }


@administranet_login_required
@tiene_permiso(PERMISO_LEER)
@require_http_methods(["GET", "POST"])
def auditoria_configuracion(request):
    """
    GET/POST /contabilidad/auditoria/configuracion/

    Lectura para `contabilidad.auditoria.leer`; edición sólo para
    `contabilidad.auditoria.configurar` (POL-12). El guardado valida con
    `PoliticaAuditoriaContable.clean()` y muestra mensajes en español.
    """
    user = getattr(request, "user", None)
    puede_configurar = _tiene_permiso(user, PERMISO_CONFIGURAR)
    base_empresa = (
        request.POST.get("base_empresa")
        if request.method == "POST"
        else request.GET.get("base_empresa")
    ) or PoliticaAuditoriaContable.BASE_DEFAULT

    if request.method == "POST":
        if not puede_configurar:
            raise PermissionDenied("No tiene permiso para configurar políticas de auditoría.")

        tolerancia_raw = (request.POST.get("tolerancia_decimal") or "").replace(",", ".").strip()
        try:
            tolerancia = Decimal(tolerancia_raw) if tolerancia_raw else Decimal("0.005")
        except (InvalidOperation, ValueError):
            messages.error(request, "La tolerancia decimal debe ser un número válido.")
            ctx = _contexto_configuracion(request, base_empresa, _form_data_desde_post(request.POST))
            return render(request, "contabilidad_audit/auditoria_configuracion.html", ctx)

        fila = PoliticaAuditoriaContable.objects.filter(base_empresa=base_empresa).first()
        snapshot_anterior = snapshot_desde_politica(fila)
        if fila is None:
            fila = PoliticaAuditoriaContable(base_empresa=base_empresa)
        fila.tratamiento_anulados = request.POST.get("tratamiento_anulados", fila.tratamiento_anulados)
        fila.politica_centavo = request.POST.get("politica_centavo", fila.politica_centavo)
        fila.ejercicios_cerrados = request.POST.get("ejercicios_cerrados", fila.ejercicios_cerrados)
        fila.alcance_recompute = request.POST.get("alcance_recompute", fila.alcance_recompute)
        fila.tolerancia_decimal = tolerancia
        fila.prefijos_cuenta = _prefijos_desde_post(request.POST)
        fila.actualizado_por = _usuario_identificador(request)

        try:
            fila.full_clean()
            fila.save()
            registrar_historial_politica(
                base_empresa=base_empresa,
                anterior=snapshot_anterior,
                nuevo=fila,
                usuario=fila.actualizado_por,
            )
        except ValidationError as exc:
            for campo, errores in exc.message_dict.items():
                for err in errores:
                    messages.error(request, f"{campo}: {err}")
            ctx = _contexto_configuracion(request, base_empresa, _form_data_desde_post(request.POST))
            return render(request, "contabilidad_audit/auditoria_configuracion.html", ctx)

        messages.success(
            request,
            f"Política de auditoría guardada para «{base_empresa}».",
        )
        return redirect(f"{reverse('contabilidad_audit:auditoria_configuracion')}?base_empresa={base_empresa}")

    ctx = _contexto_configuracion(request, base_empresa)
    return render(request, "contabilidad_audit/auditoria_configuracion.html", ctx)


@administranet_login_required
@tiene_permiso(PERMISO_LEER)
@require_GET
def auditoria_configuracion_historial(request):
    """
    GET /contabilidad/auditoria/configuracion/historial/

    Lista el historial de cambios de política para ``base_empresa``.
    ``?format=json`` devuelve JSON; sin format redirige a la pantalla de configuración.
    """
    base_empresa = request.GET.get("base_empresa") or PoliticaAuditoriaContable.BASE_DEFAULT
    historial = _historial_ui(base_empresa)

    if request.GET.get("format") == "json":
        payload = []
        for fila in historial:
            payload.append(
                {
                    "id": fila["id"],
                    "cambiado_en": fila["cambiado_en_ui"],
                    "cambiado_por": fila["cambiado_por"],
                    "config_hash_anterior": fila["config_hash_anterior"],
                    "config_hash_nuevo": fila["config_hash_nuevo"],
                    "es_alta": fila["es_alta"],
                    "cambios": fila["cambios"],
                }
            )
        return JsonResponse(
            {"base_empresa": base_empresa, "historial": payload},
            json_dumps_params={"ensure_ascii": False},
        )

    return redirect(
        f"{reverse('contabilidad_audit:auditoria_configuracion')}?base_empresa={base_empresa}#historial-politica"
    )


# ──────────────────────────────────────────────────────────────────────────
# Fase 2 — Dry-run de corrección (solo lectura legacy)
# ──────────────────────────────────────────────────────────────────────────

def _parse_alcance_dry_run(request) -> dict:
    base_empresa = _base_empresa_sesion(request)
    id_ejercicio = request.GET.get("id_ejercicio")
    if not base_empresa:
        raise ValueError("No hay empresa base en la sesión.")
    if not id_ejercicio:
        raise ValueError("El parámetro id_ejercicio es obligatorio.")
    check_ids = request.GET.getlist("check_ids") or request.GET.getlist("check_id")
    if not check_ids:
        raise ValueError("Seleccioná al menos un diagnóstico.")
    alcance = {
        "base_empresa": base_empresa,
        "id_ejercicio": int(id_ejercicio),
        "check_ids": check_ids,
    }
    if request.GET.get("id_periodo"):
        alcance["id_periodo"] = int(request.GET["id_periodo"])
    alcance_override = request.GET.get("alcance")
    if alcance_override:
        alcance["alcance_recompute_override"] = alcance_override
    return alcance


def _fecha_ui(dt) -> str:
    if dt is None:
        return ""
    if isinstance(dt, str):
        try:
            from datetime import datetime as dt_cls

            parsed = dt_cls.strptime(dt[:19], "%Y-%m-%d %H:%M:%S")
            return parsed.strftime("%d/%m/%Y %H:%M")
        except ValueError:
            return dt
    try:
        if timezone.is_naive(dt):
            return dt.strftime("%d/%m/%Y %H:%M")
        return timezone.localtime(dt).strftime("%d/%m/%Y %H:%M")
    except (AttributeError, ValueError):
        return str(dt)


def _fecha_date_ui(valor) -> str:
    """Formatea una fecha legacy (DATE) como dd/MM/yyyy. Tolerante a None/str."""
    if valor is None or valor == "":
        return ""
    try:
        return valor.strftime("%d/%m/%Y")
    except AttributeError:
        return str(valor)


def _contexto_dry_run(
    request,
    payload: dict | None = None,
    alcance_recompute: str = "",
    *,
    id_ejercicio: str | int | None = None,
    id_periodo: str | int | None = None,
    checks_seleccionados: list[str] | None = None,
    auto_ejecutar: bool | None = None,
) -> dict:
    user = getattr(request, "user", None)
    base_empresa = _base_empresa_sesion(request) or ""
    check_ids = checks_seleccionados
    if check_ids is None:
        check_ids = request.GET.getlist("check_ids") or request.GET.getlist("check_id")
    ejercicio = id_ejercicio if id_ejercicio is not None else request.GET.get("id_ejercicio") or ""
    periodo = id_periodo if id_periodo is not None else request.GET.get("id_periodo") or ""
    if auto_ejecutar is None:
        auto_ejecutar = bool(
            base_empresa
            and ejercicio
            and check_ids
            and payload is None
        )
    return {
        "titulo_pagina": "Diagnóstico de corrección contable",
        "base_empresa": base_empresa,
        "id_ejercicio": ejercicio,
        "id_periodo": periodo,
        "alcance_recompute": alcance_recompute,
        "checks_disponibles": _checks_disponibles(),
        "checks_seleccionados": check_ids,
        "permiso_leer": PERMISO_LEER,
        "puede_configurar": _tiene_permiso(user, PERMISO_CONFIGURAR),
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
        "configuracion_url": reverse("contabilidad_audit:auditoria_configuracion"),
        "ejercicios_periodos_url": reverse("contabilidad_audit:auditoria_ejercicios_periodos"),
        "dry_run_url": reverse("contabilidad_audit:auditoria_dry_run"),
        "lotes_url": reverse("contabilidad_audit:auditoria_lotes"),
        "asientos_url": reverse("contabilidad_audit:auditoria_asientos"),
        "apply_url": reverse("contabilidad_audit:auditoria_apply"),
        "apply_ejecutar_url": reverse("contabilidad_audit:auditoria_apply_ejecutar"),
        "puede_corregir": _tiene_permiso(user, PERMISO_CORREGIR),
        "check_anulacion_id": "integridad_anulacion_compra_pago",
        "payload": payload,
        "auto_ejecutar": auto_ejecutar,
    }


def _cargar_plan_vigente_sesion(request, dry_run_id):
    """
    Carga un plan de diagnóstico y valida empresa de sesión y vigencia.

    Retorna ``(plan, None)`` si es válido, o ``(None, HttpResponse redirect)``.
    """
    try:
        plan = PlanCorreccion.objects.get(dry_run_id=dry_run_id)
    except PlanCorreccion.DoesNotExist:
        messages.error(request, "No existe un plan de diagnóstico con ese identificador.")
        return None, redirect(reverse("contabilidad_audit:auditoria_lotes"))

    base_sesion = _base_empresa_sesion(request)
    if not base_sesion or plan.base_empresa != base_sesion:
        messages.error(request, "El plan no corresponde a la empresa de su sesión.")
        return None, redirect(reverse("contabilidad_audit:auditoria_lotes"))

    ahora = timezone.now()
    if plan.estado == "propuesto" and plan.expira_en and ahora >= plan.expira_en:
        plan.estado = "expirado"
        plan.save(update_fields=["estado"])
        _purgar_planes_vencidos(base_sesion)
        messages.error(
            request,
            "El plan de diagnóstico expiró. Generá uno nuevo desde el tablero.",
        )
        return None, redirect(reverse("contabilidad_audit:auditoria_lotes"))

    es_vigente = plan.estado == "propuesto" and (
        plan.expira_en is None or plan.expira_en > ahora
    )
    if not es_vigente:
        messages.error(
            request,
            f"El plan está en estado «{plan.estado}» y no puede reabrirse.",
        )
        return None, redirect(reverse("contabilidad_audit:auditoria_lotes"))

    return plan, None


@administranet_login_required
@tiene_permiso(PERMISO_LEER)
@require_GET
def auditoria_dry_run(request):
    """
    GET /contabilidad/auditoria/dry-run/

    Genera plan de corrección (100 % SELECT legacy), persiste PlanCorreccion
    y muestra guards TTL/config_hash/data_fingerprint. No aplica cambios (Fase 3).

    - ``?dry_run_id=&refresh=1`` o ``?dry_run_id=&check_ids=…`` → actualiza in-place
      un plan vigente (mismo ``dry_run_id``).
    - ``?dry_run_id=`` sin ``check_ids`` ni ``refresh`` → reabre un plan vigente.
    - ``?format=json`` → payload JSON
    - ``?format=csv|xlsx`` → export del plan
    - Sin ``format`` → plantilla canon con resumen del plan
    """
    from legacy_db.services.cont_recalculo_service import dry_run

    formato = request.GET.get("format")
    check_ids = request.GET.getlist("check_ids") or request.GET.getlist("check_id")
    dry_run_id = request.GET.get("dry_run_id")
    refresh = request.GET.get("refresh") == "1"
    actualizar = bool(dry_run_id and (refresh or check_ids))

    if actualizar:
        plan, redirect_resp = _cargar_plan_vigente_sesion(request, dry_run_id)
        if redirect_resp is not None:
            return redirect_resp

        if refresh and not check_ids:
            alcance = dict(plan.alcance or {})
            base_sesion = _base_empresa_sesion(request)
            if base_sesion:
                alcance["base_empresa"] = base_sesion
        else:
            try:
                alcance = _parse_alcance_dry_run(request)
            except ValueError as exc:
                if formato == "json":
                    return JsonResponse({"error": str(exc)}, status=400)
                if formato in ("csv", "xlsx"):
                    return HttpResponse(
                        str(exc), status=400, content_type="text/plain; charset=utf-8"
                    )
                ctx = _contexto_dry_run(request)
                ctx["error_parametros"] = str(exc)
                return render(request, "contabilidad_audit/auditoria_dry_run.html", ctx)

        politica = resolver_politica(alcance["base_empresa"])
        override = alcance.pop("alcance_recompute_override", None)
        if override:
            politica = {**politica, "alcance_recompute": override}

        alcance_recompute = politica.get("alcance_recompute", "ejercicio_seleccionado")

        base_sesion = alcance.get("base_empresa")
        if base_sesion:
            _purgar_planes_vencidos(base_sesion)

        try:
            payload = dry_run(
                base_empresa=alcance["base_empresa"],
                alcance=alcance,
                politica=politica,
                usuario=_usuario_identificador(request),
                dry_run_id=plan.dry_run_id,
            )
        except Exception as exc:
            if formato == "json":
                return JsonResponse({"error": str(exc)}, status=500)
            ctx = _contexto_dry_run(request, alcance_recompute=alcance_recompute)
            ctx["error_ejecucion"] = str(exc)
            return render(request, "contabilidad_audit/auditoria_dry_run.html", ctx)

        if formato != "json" and formato not in ("csv", "xlsx"):
            messages.success(request, "Diagnóstico actualizado.")

        if formato == "json":
            return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})
        if formato in ("csv", "xlsx"):
            from contabilidad_audit.services.export import (
                exportar_dry_run_csv,
                exportar_dry_run_xlsx,
            )

            payload_export = {**payload, "checks_disponibles": _checks_disponibles()}
            if formato == "csv":
                return exportar_dry_run_csv(payload_export)
            return exportar_dry_run_xlsx(payload_export)

        ctx = _contexto_dry_run(
            request,
            payload,
            alcance_recompute=alcance_recompute,
            id_ejercicio=alcance.get("id_ejercicio"),
            id_periodo=alcance.get("id_periodo"),
            checks_seleccionados=alcance.get("check_ids") or [],
            auto_ejecutar=False,
        )
        if payload.get("dry_run_id"):
            ctx["rei_url"] = reverse(
                "contabilidad_audit:auditoria_rei_aprobacion",
                kwargs={"dry_run_id": payload["dry_run_id"]},
            )
        return render(request, "contabilidad_audit/auditoria_dry_run.html", ctx)

    if dry_run_id and not check_ids:
        plan, redirect_resp = _cargar_plan_vigente_sesion(request, dry_run_id)
        if redirect_resp is not None:
            return redirect_resp

        payload = _payload_desde_plan(plan)
        alcance = plan.alcance or {}
        politica = resolver_politica(plan.base_empresa)
        alcance_recompute = politica.get("alcance_recompute", "ejercicio_seleccionado")

        if formato == "json":
            return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})
        if formato in ("csv", "xlsx"):
            from contabilidad_audit.services.export import (
                exportar_dry_run_csv,
                exportar_dry_run_xlsx,
            )

            payload_export = {**payload, "checks_disponibles": _checks_disponibles()}
            if formato == "csv":
                return exportar_dry_run_csv(payload_export)
            return exportar_dry_run_xlsx(payload_export)

        ctx = _contexto_dry_run(
            request,
            payload,
            alcance_recompute=alcance_recompute,
            id_ejercicio=alcance.get("id_ejercicio"),
            id_periodo=alcance.get("id_periodo"),
            checks_seleccionados=alcance.get("check_ids") or [],
            auto_ejecutar=False,
        )
        if payload.get("dry_run_id"):
            ctx["rei_url"] = reverse(
                "contabilidad_audit:auditoria_rei_aprobacion",
                kwargs={"dry_run_id": payload["dry_run_id"]},
            )
        return render(request, "contabilidad_audit/auditoria_dry_run.html", ctx)

    if not check_ids:
        if formato == "json":
            return JsonResponse(
                {"error": "Seleccioná al menos un diagnóstico."},
                status=400,
            )
        if formato in ("csv", "xlsx"):
            return HttpResponse(
                "Seleccioná al menos un diagnóstico.",
                status=400,
                content_type="text/plain; charset=utf-8",
            )
        ctx = _contexto_dry_run(request)
        return render(request, "contabilidad_audit/auditoria_dry_run.html", ctx)

    try:
        alcance = _parse_alcance_dry_run(request)
    except ValueError as exc:
        if formato == "json":
            return JsonResponse({"error": str(exc)}, status=400)
        if formato in ("csv", "xlsx"):
            return HttpResponse(str(exc), status=400, content_type="text/plain; charset=utf-8")
        ctx = _contexto_dry_run(request)
        ctx["error_parametros"] = str(exc)
        return render(request, "contabilidad_audit/auditoria_dry_run.html", ctx)

    politica = resolver_politica(alcance["base_empresa"])
    override = alcance.pop("alcance_recompute_override", None)
    if override:
        politica = {**politica, "alcance_recompute": override}

    alcance_recompute = politica.get("alcance_recompute", "ejercicio_seleccionado")

    base_sesion = alcance.get("base_empresa")
    if base_sesion:
        _purgar_planes_vencidos(base_sesion)

    try:
        payload = dry_run(
            base_empresa=alcance["base_empresa"],
            alcance=alcance,
            politica=politica,
            usuario=_usuario_identificador(request),
        )
    except Exception as exc:
        if formato == "json":
            return JsonResponse({"error": str(exc)}, status=500)
        ctx = _contexto_dry_run(request, alcance_recompute=alcance_recompute)
        ctx["error_ejecucion"] = str(exc)
        return render(request, "contabilidad_audit/auditoria_dry_run.html", ctx)

    if formato == "json":
        return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})
    if formato in ("csv", "xlsx"):
        from contabilidad_audit.services.export import (
            exportar_dry_run_csv,
            exportar_dry_run_xlsx,
        )

        payload_export = {**payload, "checks_disponibles": _checks_disponibles()}
        if formato == "csv":
            return exportar_dry_run_csv(payload_export)
        return exportar_dry_run_xlsx(payload_export)

    ctx = _contexto_dry_run(request, payload, alcance_recompute=alcance_recompute)
    if payload and payload.get("dry_run_id"):
        ctx["rei_url"] = reverse(
            "contabilidad_audit:auditoria_rei_aprobacion",
            kwargs={"dry_run_id": payload["dry_run_id"]},
        )
    return render(request, "contabilidad_audit/auditoria_dry_run.html", ctx)


# ──────────────────────────────────────────────────────────────────────────
# Fase 3 — Aprobación REI caso a caso
# ──────────────────────────────────────────────────────────────────────────


def _contexto_rei(request, plan: PlanCorreccion, casos: list[AprobacionREI]) -> dict:
    propuestas = (plan.plan or {}).get("propuestas_rei") or []
    cod_por_cuenta = {
        (p.get("id_pc"), p.get("id_ejercicio")): p.get("cod_pc", "")
        for p in propuestas
    }
    filas = []
    for caso in casos:
        filas.append(
            {
                "id": caso.id,
                "id_pc": caso.id_pc,
                "cod_pc": cod_por_cuenta.get((caso.id_pc, caso.id_ejercicio), ""),
                "id_ejercicio": caso.id_ejercicio,
                "rei_teorico": caso.rei_teorico,
                "rei_actual": caso.rei_actual,
                "delta": caso.rei_teorico - caso.rei_actual,
                "estado": caso.estado,
                "aprobado_por": caso.aprobado_por,
                "aprobado_en": _fecha_ui(caso.aprobado_en),
            }
        )
    user = getattr(request, "user", None)
    return {
        "titulo_pagina": "Aprobación REI caso a caso",
        "plan": plan,
        "filas": filas,
        "dry_run_id": str(plan.dry_run_id),
        "base_empresa": plan.base_empresa,
        "expira_en": _fecha_ui(plan.expira_en),
        "config_hash": plan.config_hash,
        "permiso_rei": PERMISO_REI,
        "puede_corregir": _tiene_permiso(user, PERMISO_CORREGIR),
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
        "dry_run_url": reverse("contabilidad_audit:auditoria_dry_run"),
        "apply_url": reverse("contabilidad_audit:auditoria_apply"),
        "total_pendientes": sum(1 for f in filas if f["estado"] == "pendiente"),
        "total_aprobados": sum(1 for f in filas if f["estado"] == "aprobado"),
    }


@administranet_login_required
@tiene_permiso(PERMISO_REI)
@require_http_methods(["GET", "POST"])
def auditoria_rei_aprobacion(request, dry_run_id):
    """
    GET/POST /contabilidad/auditoria/rei/<dry_run_id>/

    Lista propuestas REI del dry-run y permite aprobar/rechazar individualmente.
    """
    try:
        plan = PlanCorreccion.objects.get(dry_run_id=dry_run_id)
    except PlanCorreccion.DoesNotExist:
        messages.error(request, "No existe un plan dry-run con ese identificador.")
        return redirect(reverse("contabilidad_audit:auditoria_dry_run"))

    casos = list(
        AprobacionREI.objects.filter(dry_run_id=dry_run_id).order_by("id_pc", "id_ejercicio")
    )

    if request.method == "POST":
        caso_id = request.POST.get("caso_id")
        accion = (request.POST.get("accion") or "").strip().lower()
        if not caso_id or accion not in ("aprobar", "rechazar"):
            messages.error(request, "Solicitud inválida: indique caso y acción.")
        else:
            try:
                caso = AprobacionREI.objects.get(id=caso_id, dry_run_id=dry_run_id)
            except AprobacionREI.DoesNotExist:
                messages.error(request, "El caso REI indicado no existe.")
            else:
                usuario = _usuario_identificador(request)
                ahora = timezone.now()
                if accion == "aprobar":
                    caso.estado = "aprobado"
                    messages.success(
                        request,
                        f"Cuenta {caso.id_pc} (ejercicio {caso.id_ejercicio}) aprobada para corrección REI.",
                    )
                else:
                    caso.estado = "rechazado"
                    messages.warning(
                        request,
                        f"Cuenta {caso.id_pc} (ejercicio {caso.id_ejercicio}) rechazada.",
                    )
                caso.aprobado_por = usuario
                caso.aprobado_en = ahora
                caso.save(update_fields=["estado", "aprobado_por", "aprobado_en"])
        return redirect(
            reverse("contabilidad_audit:auditoria_rei_aprobacion", kwargs={"dry_run_id": dry_run_id})
        )

    ctx = _contexto_rei(request, plan, casos)
    return render(request, "contabilidad_audit/auditoria_rei.html", ctx)


# ──────────────────────────────────────────────────────────────────────────
# Fase 3 — Confirmación apply (checkbox + permiso)
# ──────────────────────────────────────────────────────────────────────────


def _contexto_apply(request, plan: PlanCorreccion | None = None, error: str = "") -> dict:
    user = getattr(request, "user", None)
    dry_run_id = request.GET.get("dry_run_id") or request.POST.get("dry_run_id") or ""
    base_empresa = (
        request.GET.get("base_empresa")
        or request.POST.get("base_empresa")
        or _base_empresa_request(request)
        or ""
    )
    modo = request.GET.get("modo") or request.POST.get("modo") or "general"
    return {
        "titulo_pagina": "Confirmar corrección contable",
        "plan": plan,
        "dry_run_id": dry_run_id,
        "base_empresa": base_empresa,
        "modo": modo,
        "error_apply": error,
        "permiso_corregir": PERMISO_CORREGIR,
        "puede_corregir": _tiene_permiso(user, PERMISO_CORREGIR),
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
        "dry_run_url": reverse("contabilidad_audit:auditoria_dry_run"),
        "rei_url": (
            reverse("contabilidad_audit:auditoria_rei_aprobacion", kwargs={"dry_run_id": dry_run_id})
            if dry_run_id
            else ""
        ),
    }


@administranet_login_required
@tiene_permiso(PERMISO_CORREGIR)
@require_GET
def auditoria_apply_confirmacion(request):
    """GET /contabilidad/auditoria/apply/ — formulario de confirmación (solo lectura)."""
    dry_run_id = request.GET.get("dry_run_id")
    if not dry_run_id:
        messages.error(request, "Falta el identificador dry_run_id.")
        return redirect(reverse("contabilidad_audit:auditoria_dry_run"))

    try:
        plan = PlanCorreccion.objects.get(dry_run_id=dry_run_id)
    except PlanCorreccion.DoesNotExist:
        messages.error(request, "No existe un plan dry-run con ese identificador.")
        return redirect(reverse("contabilidad_audit:auditoria_dry_run"))

    ctx = _contexto_apply(request, plan)
    return render(request, "contabilidad_audit/auditoria_apply.html", ctx)


@administranet_login_required
@tiene_permiso(PERMISO_CORREGIR)
@require_POST
def auditoria_apply(request):
    """
    POST /contabilidad/auditoria/apply/ejecutar/

    Ejecuta ``apply()`` con confirmación explícita (checkbox). No disponible por GET.
    """
    from legacy_db.services.cont_recalculo_service import CorreccionContableError, apply

    dry_run_id = request.POST.get("dry_run_id")
    base_empresa = request.POST.get("base_empresa")
    modo = request.POST.get("modo") or "general"
    confirmacion_1 = request.POST.get("confirmacion_entiendo") == "on"
    confirmar_reapertura = request.POST.get("confirmar_reapertura") == "on"

    if not dry_run_id or not base_empresa:
        messages.error(request, "Faltan parámetros obligatorios (dry_run_id, base_empresa).")
        return redirect(reverse("contabilidad_audit:auditoria_dry_run"))

    if not confirmacion_1:
        messages.error(
            request,
            "Debe marcar la confirmación: entiende que se modificarán datos contables.",
        )
        # Confirmación fallida: volver al diagnóstico (modal en dry-run) o a apply REI.
        if modo == "rei":
            return redirect(
                f"{reverse('contabilidad_audit:auditoria_apply')}"
                f"?dry_run_id={dry_run_id}&base_empresa={base_empresa}&modo={modo}"
            )
        return redirect(reverse("contabilidad_audit:auditoria_dry_run"))

    try:
        plan = PlanCorreccion.objects.get(dry_run_id=dry_run_id)
    except PlanCorreccion.DoesNotExist:
        messages.error(request, "No existe un plan dry-run con ese identificador.")
        return redirect(reverse("contabilidad_audit:auditoria_dry_run"))

    usuario = _usuario_identificador(request)
    try:
        resultado = apply(
            base_empresa=base_empresa,
            dry_run_id=str(dry_run_id),
            usuario=usuario,
            tiene_permiso_corregir=True,
            confirmar_reapertura=confirmar_reapertura,
            autorizador=usuario,
            modo=modo,
        )
    except CorreccionContableError as exc:
        messages.error(request, str(exc))
        if modo == "rei":
            ctx = _contexto_apply(request, plan, error=str(exc))
            return render(request, "contabilidad_audit/auditoria_apply.html", ctx, status=409)
        return redirect(reverse("contabilidad_audit:auditoria_dry_run"))
    except Exception as exc:
        messages.error(request, f"Error inesperado: {exc}")
        if modo == "rei":
            ctx = _contexto_apply(request, plan, error=f"Error inesperado: {exc}")
            return render(request, "contabilidad_audit/auditoria_apply.html", ctx, status=500)
        return redirect(reverse("contabilidad_audit:auditoria_dry_run"))

    lote = resultado.get("lote_id") or "—"
    filas = resultado.get("filas_aplicadas", 0)
    messages.success(
        request,
        f"Corrección aplicada. Lote: {lote}. Filas afectadas: {filas}.",
    )
    # Tras apply general: ir a lotes (el diagnóstico ya no es la pantalla de resultado).
    if modo == "rei":
        ctx = _contexto_apply(request, plan)
        ctx["resultado_apply"] = resultado
        return render(request, "contabilidad_audit/auditoria_apply.html", ctx)
    return redirect(reverse("contabilidad_audit:auditoria_lotes"))


# ──────────────────────────────────────────────────────────────────────────
# Historial de planes de diagnóstico (Postgres) + lotes aplicados (legacy)
# ──────────────────────────────────────────────────────────────────────────


def _purgar_planes_vencidos(base_empresa: str) -> int:
    """Marca propuesto vencido → expirado; borra expirado+invalidado y sus AprobacionREI.

    No borra aplicado ni propuesto vigente. Retorna cantidad borrada de PlanCorreccion.
    """
    ahora = timezone.now()
    PlanCorreccion.objects.filter(
        base_empresa=base_empresa,
        estado="propuesto",
        expira_en__lte=ahora,
    ).update(estado="expirado")

    a_borrar = PlanCorreccion.objects.filter(
        base_empresa=base_empresa,
        estado__in=("expirado", "invalidado"),
    )
    dry_run_ids = list(a_borrar.values_list("dry_run_id", flat=True))
    cantidad = a_borrar.count()
    if dry_run_ids:
        AprobacionREI.objects.filter(dry_run_id__in=dry_run_ids).delete()
        a_borrar.delete()
    return cantidad


def _payload_desde_plan(plan_obj: PlanCorreccion) -> dict:
    """Arma el mismo shape de payload que dry_run() del motor, desde PlanCorreccion."""
    from legacy_db.services.cont_recalculo_service import PLAN_TTL_MIN

    plan_json = plan_obj.plan or {}
    impacto = plan_json.get("impacto") or {}
    propuestas_rei = plan_json.get("propuestas_rei") or []
    backups_propuestos = plan_json.get("backups_propuestos") or {}
    alcance = plan_obj.alcance or {}

    return {
        "dry_run_id": str(plan_obj.dry_run_id),
        "base_empresa": plan_obj.base_empresa,
        "alcance": dict(alcance),
        "config_hash": plan_obj.config_hash,
        "data_fingerprint": plan_obj.data_fingerprint,
        "estado": plan_obj.estado,
        "creado_por": plan_obj.creado_por,
        "creado_en": _fecha_ui(plan_obj.creado_en),
        "expira_en": _fecha_ui(plan_obj.expira_en),
        "guards": {
            "ttl_minutos": PLAN_TTL_MIN,
            "config_hash": plan_obj.config_hash,
            "data_fingerprint": plan_obj.data_fingerprint,
            "expira_en": _fecha_ui(plan_obj.expira_en),
        },
        "plan": plan_json,
        "impacto": impacto,
        "backups_propuestos": backups_propuestos,
        "propuestas_rei": propuestas_rei,
        "propuestas_rei_total": impacto.get("propuestas_rei_total", len(propuestas_rei)),
        "rei_aprobacion_url_hint": (
            f"/contabilidad/auditoria/rei/{plan_obj.dry_run_id}/"
            if propuestas_rei
            else None
        ),
    }


def _listar_planes_diagnostico(base_empresa: str, limite: int = 50) -> list[dict]:
    """Lista planes de diagnóstico de la empresa (purge lazy + metadatos para UI)."""
    _purgar_planes_vencidos(base_empresa)

    titulos_por_id = {c["check_id"]: c["titulo"] for c in _checks_disponibles()}
    ahora = timezone.now()
    planes: list[dict] = []

    for plan in PlanCorreccion.objects.filter(base_empresa=base_empresa).order_by("-creado_en")[:limite]:
        alcance = plan.alcance or {}
        check_ids = alcance.get("check_ids") or []
        titulos = [titulos_por_id.get(cid, cid) for cid in check_ids]
        diagnosticos_label = ", ".join(titulos) if titulos else "—"
        if len(diagnosticos_label) > 80:
            diagnosticos_label = diagnosticos_label[:77] + "..."

        plan_json = plan.plan or {}
        impacto = plan_json.get("impacto") or {}
        es_vigente = (
            plan.estado == "propuesto"
            and (plan.expira_en is None or plan.expira_en > ahora)
        )

        planes.append(
            {
                "dry_run_id": str(plan.dry_run_id),
                "creado_en": _fecha_ui(plan.creado_en),
                "expira_en": _fecha_ui(plan.expira_en),
                "estado_ui": "vigente" if es_vigente else "aplicado",
                "estado": plan.estado,
                "id_ejercicio": alcance.get("id_ejercicio"),
                "diagnosticos_label": diagnosticos_label,
                "total_aplicables": impacto.get("total_aplicables", 0),
                "abrir_url": (
                    f"{reverse('contabilidad_audit:auditoria_dry_run')}?dry_run_id={plan.dry_run_id}"
                    if es_vigente
                    else ""
                ),
                "actualizar_url": (
                    f"{reverse('contabilidad_audit:auditoria_dry_run')}"
                    f"?dry_run_id={plan.dry_run_id}&refresh=1"
                    if es_vigente
                    else ""
                ),
            }
        )
    return planes


def _formato_monto_argentino(valor) -> str:
    """Formato contable simple: $ 1.234,56."""
    try:
        n = float(valor)
    except (TypeError, ValueError):
        return str(valor)
    return "$ " + f"{n:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _es_numerico(valor) -> bool:
    if valor is None or valor == "":
        return False
    if isinstance(valor, (int, float, Decimal)):
        return True
    try:
        float(str(valor).replace(",", ".").strip())
        return True
    except (TypeError, ValueError):
        return False


def _parse_json_o_string(valor):
    """Parsea TEXT legacy como JSON si aplica; si no, devuelve string."""
    if valor is None or valor == "":
        return None
    if isinstance(valor, (dict, list)):
        return valor
    if isinstance(valor, str):
        txt = valor.strip()
        if not txt:
            return None
        if txt.startswith(("{", "[")):
            try:
                return json.loads(txt)
            except json.JSONDecodeError:
                return txt
        return txt
    return valor


def _formatear_fecha_resumen(valor) -> str:
    """Convierte fechas ISO o datetime legacy a dd/MM/yyyy para resúmenes."""
    if valor is None or valor == "":
        return ""
    if hasattr(valor, "strftime"):
        try:
            return valor.strftime("%d/%m/%Y")
        except (AttributeError, ValueError):
            pass
    txt = str(valor).strip()
    if len(txt) >= 10 and txt[4:5] == "-" and txt[7:8] == "-":
        try:
            from datetime import datetime as dt_cls

            parsed = dt_cls.strptime(txt[:10], "%Y-%m-%d")
            return parsed.strftime("%d/%m/%Y")
        except ValueError:
            pass
    return txt


def _texto_corto(valor, limite: int = 80) -> str:
    if valor is None or valor == "":
        return "—"
    if isinstance(valor, (dict, list)):
        try:
            texto = json.dumps(valor, ensure_ascii=False, sort_keys=True)
        except TypeError:
            texto = str(valor)
    else:
        texto = str(valor)
    if len(texto) <= limite:
        return texto
    return texto[: limite - 3] + "..."


def _renglones_eliminacion_log(valor_anterior) -> list | None:
    """Lista de renglones guardados en valor_anterior al eliminar un asiento."""
    va = valor_anterior
    if isinstance(va, str):
        txt = va.strip()
        if not txt.startswith("["):
            return None
        try:
            va = json.loads(txt)
        except (TypeError, ValueError, json.JSONDecodeError):
            return None
    if isinstance(va, list) and va and isinstance(va[0], dict):
        if any(k in va[0] for k in ("debe_asiento", "haber_asiento", "id_pc")):
            return va
    return None


def _cambio_resumen(valor_anterior, valor_nuevo, tabla: str = "") -> str:
    """Texto corto contable del cambio (paridad con resumenValor del dry-run)."""
    vn = valor_nuevo
    va = valor_anterior

    renglones_elim = _renglones_eliminacion_log(va)
    if renglones_elim is not None and vn in (None, ""):
        return f"Asiento eliminado · {len(renglones_elim)} renglón(es)"

    if isinstance(vn, dict) and vn.get("nro_asiento") is not None:
        partes = [f"Asiento {vn.get('nro_asiento')}"]
        cm = vn.get("codigo_movimiento")
        if cm not in (None, ""):
            partes.append(f"CM {cm}")
        if vn.get("fecha_asiento"):
            partes.append(_formatear_fecha_resumen(vn["fecha_asiento"]))
        if vn.get("id_pc") is not None:
            partes.append(f"Cta {vn.get('id_pc')}")
        try:
            debe = float(vn.get("debe_asiento") or 0)
            haber = float(vn.get("haber_asiento") or 0)
        except (TypeError, ValueError):
            debe = haber = 0
        if debe != 0:
            partes.append(f"Debe {_formato_monto_argentino(debe)}")
        elif haber != 0:
            partes.append(f"Haber {_formato_monto_argentino(haber)}")
        else:
            partes.append(
                f"D {_formato_monto_argentino(vn.get('debe_asiento'))} / "
                f"H {_formato_monto_argentino(vn.get('haber_asiento'))}"
            )
        if vn.get("desc_asiento"):
            partes.append(str(vn["desc_asiento"])[:60])
        return " · ".join(partes)

    if isinstance(vn, dict):
        if vn.get("TipoComprobante") or vn.get("NroComprobante"):
            tipo = vn.get("TipoComprobante") or ""
            nro = vn.get("NroComprobante") or ""
            return f"{tipo} {nro}".strip() or "Marcador de anulación"
        if isinstance(vn.get("renglones_preview"), list):
            return f"Contra-asiento · {len(vn['renglones_preview'])} renglones"
        if vn.get("codigo_movimiento") is not None and vn.get("nro_asiento") is not None:
            return f"Asiento {vn.get('nro_asiento')} · CM {vn.get('codigo_movimiento')}"
        claves = list(vn.keys())
        if len(claves) <= 3:
            return " · ".join(f"{k}: {_texto_corto(vn[k], 40)}" for k in claves)

    es_saldo = "saldo" in (tabla or "").lower()
    if _es_numerico(va) and _es_numerico(vn):
        if es_saldo or "." in str(va) or "." in str(vn):
            return f"{_formato_monto_argentino(va)} → {_formato_monto_argentino(vn)}"
        return f"{va} → {vn}"

    if va not in (None, "") and vn not in (None, ""):
        return f"{_texto_corto(va, 50)} → {_texto_corto(vn, 50)}"
    return _texto_corto(vn if vn not in (None, "") else va, 120)


def _obtener_lote(base_empresa: str, lote_id: str) -> dict | None:
    """Lee metadatos del lote desde cont_audit_correccion_lote (solo lectura)."""
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT lote_id, base_empresa, dry_run_id, config_hash, usuario, fecha,
                       estado, reapertura_flag, autorizador,
                       (SELECT COUNT(*) FROM cont_audit_correccion c
                        WHERE c.lote_id = l.lote_id) AS filas_correccion
                FROM cont_audit_correccion_lote l
                WHERE l.lote_id = %s AND l.base_empresa = %s
                LIMIT 1
                """,
                (lote_id, base_empresa),
            )
            row = cursor.fetchone()
        finally:
            cursor.close()

    if not row:
        return None

    dry_run_id = str(row[2] or "")
    return {
        "lote_id": str(row[0] or ""),
        "base_empresa": str(row[1] or ""),
        "dry_run_id": dry_run_id,
        "dry_run_id_corto": (dry_run_id[:8] + "…") if len(dry_run_id) > 8 else dry_run_id,
        "config_hash": str(row[3] or ""),
        "usuario": str(row[4] or ""),
        "fecha": _fecha_ui(row[5]),
        "estado": str(row[6] or ""),
        "reapertura_flag": bool(row[7]),
        "autorizador": str(row[8] or "") if row[8] else "",
        "filas_correccion": int(row[9] or 0),
    }


def _listar_detalle_lote(base_empresa: str, lote_id: str, limite: int = 500) -> list[dict]:
    """Filas del log cont_audit_correccion para un lote (solo lectura)."""
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT id, check_id, tabla, clave, valor_anterior, valor_nuevo, usuario, fecha
                FROM cont_audit_correccion
                WHERE lote_id = %s
                ORDER BY id ASC
                LIMIT %s
                """,
                (lote_id, limite),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()

    titulos_por_id = {c["check_id"]: c["titulo"] for c in _checks_disponibles()}
    titulos_por_id.setdefault("eliminacion_asiento", "Eliminación de asiento")
    filas: list[dict] = []
    for row in rows:
        clave = _parse_json_o_string(row[3])
        valor_anterior = _parse_json_o_string(row[4])
        valor_nuevo = _parse_json_o_string(row[5])
        tabla = str(row[2] or "")
        codigo_movimiento = _extraer_codigo_movimiento(clave, valor_nuevo)
        nro_asiento = ""
        if isinstance(valor_nuevo, dict) and valor_nuevo.get("nro_asiento") is not None:
            nro_asiento = valor_nuevo.get("nro_asiento")
        elif isinstance(clave, dict) and clave.get("nro_asiento") is not None:
            nro_asiento = clave.get("nro_asiento")
        renglones_elim = _renglones_eliminacion_log(valor_anterior)
        if renglones_elim is not None:
            cms = sorted(
                {
                    str(r.get("codigo_movimiento"))
                    for r in renglones_elim
                    if r.get("codigo_movimiento") not in (None, "")
                }
            )
            if not codigo_movimiento and len(cms) == 1:
                codigo_movimiento = cms[0]
            valor_anterior_corto = f"{len(renglones_elim)} renglón(es)"
        else:
            valor_anterior_corto = _texto_corto(valor_anterior, 60)

        filas.append(
            {
                "id": int(row[0]),
                "check_id": str(row[1] or ""),
                "titulo_check": titulos_por_id.get(str(row[1] or ""), str(row[1] or "")),
                "tabla": tabla,
                "clave": clave,
                "clave_texto": _texto_corto(clave, 120),
                "nro_asiento": nro_asiento if nro_asiento != "" else "—",
                "codigo_movimiento": codigo_movimiento if codigo_movimiento not in (None, "") else "—",
                "valor_anterior": valor_anterior,
                "valor_anterior_corto": valor_anterior_corto,
                "valor_nuevo": valor_nuevo,
                "cambio_resumen": _cambio_resumen(valor_anterior, valor_nuevo, tabla),
                "usuario": str(row[6] or ""),
                "fecha": _fecha_ui(row[7]),
            }
        )
    return filas


def _extraer_codigo_movimiento(clave, valor_nuevo) -> str:
    """Obtiene CodigoMovimiento desde valor_nuevo o clave del log."""
    if isinstance(valor_nuevo, dict):
        for k in ("codigo_movimiento", "CodigoMovimiento"):
            if valor_nuevo.get(k) not in (None, ""):
                return str(valor_nuevo.get(k))
    if isinstance(clave, dict):
        for k in (
            "codigo_movimiento",
            "CodigoMovimiento",
            "codigo_movimiento_original",
            "codigo_movimiento_anul",
        ):
            if clave.get(k) not in (None, ""):
                return str(clave.get(k))
    return ""


def _listar_lotes_correccion(base_empresa: str) -> list[dict]:
    """Lista lotes desde MySQL legacy (solo lectura) con conteo de filas de detalle."""
    pool = get_mysql_pool()
    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT l.lote_id, l.fecha, l.usuario, l.estado, l.dry_run_id,
                       (SELECT COUNT(*) FROM cont_audit_correccion c
                        WHERE c.lote_id = l.lote_id) AS filas_correccion,
                       l.backups_json
                FROM cont_audit_correccion_lote l
                WHERE l.base_empresa = %s
                ORDER BY l.fecha DESC
                LIMIT 200
                """,
                (base_empresa,),
            )
            rows = cursor.fetchall()
        finally:
            cursor.close()

    lotes: list[dict] = []
    for row in rows:
        dry_run_id = str(row[4] or "")
        backups_raw = row[6]
        tiene_backups = False
        if backups_raw:
            try:
                backups_data = (
                    json.loads(backups_raw)
                    if isinstance(backups_raw, (str, bytes, bytearray))
                    else backups_raw
                )
                tiene_backups = isinstance(backups_data, dict) and bool(backups_data)
            except (TypeError, ValueError, json.JSONDecodeError):
                tiene_backups = False
        # Eliminación usa backup efímero: no es revertible vía rollback_lote.
        puede_revertir = (
            str(row[3] or "") != "revertido"
            and dry_run_id != "eliminacion_asiento"
            and tiene_backups
        )
        lotes.append(
            {
                "lote_id": str(row[0] or ""),
                "fecha": _fecha_ui(row[1]),
                "usuario": str(row[2] or ""),
                "estado": str(row[3] or ""),
                "dry_run_id": dry_run_id,
                "filas_correccion": int(row[5] or 0),
                "puede_revertir": puede_revertir,
            }
        )
    return lotes


def _contexto_lotes(
    request,
    lotes: list[dict] | None = None,
    planes: list[dict] | None = None,
    error: str = "",
) -> dict:
    user = getattr(request, "user", None)
    base_empresa = _base_empresa_sesion(request) or ""
    lotes_ctx = lotes or []
    return {
        "titulo_pagina": "Lotes y planes de diagnóstico",
        "base_empresa": base_empresa,
        "lotes": lotes_ctx,
        "planes": planes or [],
        "error_lotes": error,
        "permiso_corregir": PERMISO_CORREGIR,
        "puede_corregir": _tiene_permiso(user, PERMISO_CORREGIR),
        "hay_lotes_revertibles": any(bool(l.get("puede_revertir")) for l in lotes_ctx),
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
        "dry_run_url": reverse("contabilidad_audit:auditoria_dry_run"),
        "lotes_url": reverse("contabilidad_audit:auditoria_lotes"),
        "asientos_url": reverse("contabilidad_audit:auditoria_asientos"),
    }


@administranet_login_required
@tiene_permiso(PERMISO_LEER)
@require_GET
def auditoria_lotes(request):
    """
    GET /contabilidad/auditoria/lotes/

    Lista planes de diagnóstico (Postgres) y lotes de corrección desde
    ``cont_audit_correccion_lote`` (solo lectura legacy) de la empresa base de sesión.
    """
    base_empresa = _base_empresa_sesion(request)
    planes: list[dict] = []
    if base_empresa:
        try:
            planes = _listar_planes_diagnostico(base_empresa)
        except Exception as exc:  # noqa: BLE001 — degradación tolerable en UI
            logger.exception("Error listando planes de diagnóstico para %s", base_empresa)

    if not base_empresa:
        ctx = _contexto_lotes(request, planes=planes, error="No hay empresa base en la sesión.")
        return render(request, "contabilidad_audit/auditoria_lotes.html", ctx)

    error = ""
    lotes: list[dict] = []
    try:
        lotes = _listar_lotes_correccion(base_empresa)
    except Exception as exc:  # noqa: BLE001 — degradación tolerable en UI
        logger.exception("Error listando lotes de corrección para %s", base_empresa)
        error = f"No se pudieron obtener los lotes: {exc}"

    ctx = _contexto_lotes(request, lotes=lotes, planes=planes, error=error)
    return render(request, "contabilidad_audit/auditoria_lotes.html", ctx)


@administranet_login_required
@tiene_permiso(PERMISO_LEER)
@require_GET
def auditoria_lote_detalle(request, lote_id):
    """
    GET /contabilidad/auditoria/lotes/<lote_id>/

    Detalle de un lote aplicado (log legacy). ``?format=xlsx`` descarga Excel.
    """
    base_empresa = _base_empresa_sesion(request)
    lotes_url = reverse("contabilidad_audit:auditoria_lotes")

    if not base_empresa:
        messages.error(request, "No hay empresa base en la sesión.")
        return redirect(lotes_url)

    lote = None
    filas: list[dict] = []
    try:
        lote = _obtener_lote(base_empresa, lote_id)
        if lote:
            filas = _listar_detalle_lote(base_empresa, lote_id)
    except Exception as exc:  # noqa: BLE001 — degradación tolerable en UI
        logger.exception("Error cargando detalle lote %s base=%s", lote_id, base_empresa)
        messages.error(request, f"No se pudo cargar el detalle del lote: {exc}")
        return redirect(lotes_url)

    if not lote:
        messages.error(request, "No existe un lote de corrección con ese identificador para su empresa.")
        return redirect(lotes_url)

    if request.GET.get("format") == "xlsx":
        from contabilidad_audit.services.export import exportar_lote_xlsx

        return exportar_lote_xlsx(lote, filas)

    detalle_url = reverse(
        "contabilidad_audit:auditoria_lote_detalle",
        kwargs={"lote_id": lote_id},
    )
    ctx = {
        "titulo_pagina": "Detalle del lote de corrección",
        "base_empresa": base_empresa,
        "lote": lote,
        "filas": filas,
        "total_filas": lote.get("filas_correccion", len(filas)),
        "excel_url": f"{detalle_url}?format=xlsx",
        "lotes_url": lotes_url,
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
    }
    return render(request, "contabilidad_audit/auditoria_lote_detalle.html", ctx)


@administranet_login_required
@tiene_permiso(PERMISO_CORREGIR)
@require_POST
def auditoria_lote_rollback(request, lote_id):
    """
    POST /contabilidad/auditoria/lotes/<lote_id>/rollback/

    Revierte un lote aplicado vía ``rollback_lote`` (requiere permiso de corregir).
    Los lotes de eliminación de asientos no son revertibles (backup efímero).
    """
    from legacy_db.services.cont_recalculo_service import CorreccionContableError, rollback_lote

    base_empresa = _base_empresa_sesion(request)
    if not base_empresa:
        messages.error(request, "No hay empresa base en la sesión.")
        return redirect(reverse("contabilidad_audit:auditoria_lotes"))

    usuario = _usuario_identificador(request)
    lote = _obtener_lote(base_empresa, lote_id)
    if lote and str(lote.get("dry_run_id") or "") == "eliminacion_asiento":
        messages.error(
            request,
            "Los lotes de eliminación de asientos no se pueden revertir: "
            "el respaldo solo protege ante fallos durante el proceso.",
        )
        return redirect(reverse("contabilidad_audit:auditoria_lotes"))

    try:
        rollback_lote(
            base_empresa,
            lote_id,
            usuario,
            tiene_permiso_corregir=True,
        )
    except CorreccionContableError as exc:
        messages.error(request, str(exc))
    except Exception as exc:
        logger.exception("Rollback lote %s base=%s", lote_id, base_empresa)
        messages.error(request, f"Error inesperado al revertir el lote: {exc}")
    else:
        messages.success(
            request,
            f"Lote «{lote_id}» revertido correctamente desde los backups registrados.",
        )

    return redirect(reverse("contabilidad_audit:auditoria_lotes"))


# ──────────────────────────────────────────────────────────────────────────
# Eliminación de asientos + recálculo de saldos
# ──────────────────────────────────────────────────────────────────────────


def _parse_nros_asiento(raw: str) -> list[int]:
    """Parsea lista de nros desde textarea (coma o salto de línea)."""
    if not raw:
        return []
    nros: list[int] = []
    for parte in raw.replace(",", "\n").split("\n"):
        txt = parte.strip()
        if not txt:
            continue
        n = to_int_or_none(txt)
        if n is not None:
            nros.append(n)
    return nros


def _parse_filtros_asientos(request, *, exigir_ejercicio: bool = True) -> dict:
    base_empresa = _base_empresa_sesion(request)
    if not base_empresa:
        raise ValueError("No hay empresa base en la sesión.")
    id_ejercicio_raw = request.GET.get("id_ejercicio")
    id_ejercicio = to_int_or_none(id_ejercicio_raw) if id_ejercicio_raw not in (None, "") else None
    if exigir_ejercicio and id_ejercicio is None:
        raise ValueError("El parámetro id_ejercicio es obligatorio.")
    filtros: dict = {
        "base_empresa": base_empresa,
    }
    if id_ejercicio is not None:
        filtros["id_ejercicio"] = id_ejercicio
    if request.GET.get("fecha_desde"):
        filtros["fecha_desde"] = request.GET["fecha_desde"]
    if request.GET.get("fecha_hasta"):
        filtros["fecha_hasta"] = request.GET["fecha_hasta"]
    if request.GET.get("id_concepto_asiento"):
        filtros["id_concepto_asiento"] = int(request.GET["id_concepto_asiento"])
    if request.GET.get("codigo_movimiento"):
        filtros["codigo_movimiento"] = request.GET["codigo_movimiento"]
    if request.GET.get("tipo_comprobante"):
        filtros["tipo_comprobante"] = request.GET["tipo_comprobante"]
    anulado = request.GET.get("anulado")
    if anulado in ("Si", "No"):
        filtros["anulado"] = anulado
    if request.GET.get("q"):
        filtros["q"] = request.GET["q"]
    nros = _parse_nros_asiento(request.GET.get("nros_asiento", ""))
    if nros:
        filtros["nros_asiento"] = nros
    return filtros


def _parse_asientos_eliminar_body(request) -> tuple[list[dict], bool]:
    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("JSON inválido en el cuerpo de la solicitud.") from exc
    asientos = payload.get("asientos")
    if not isinstance(asientos, list):
        raise ValueError("El cuerpo debe incluir una lista «asientos».")
    accept = (request.headers.get("Accept") or "").lower()
    stream = bool(payload.get("stream")) or "application/x-ndjson" in accept
    return asientos, stream


def _parse_asientos_json_body(request) -> list[dict]:
    asientos, _ = _parse_asientos_eliminar_body(request)
    return asientos


def _stream_eliminar_asientos_ndjson(base_empresa: str, asientos: list[dict], usuario: str):
    from legacy_db.services.cont_eliminacion_asientos_service import (
        EliminacionAsientosError,
        _eliminar_asientos_iter,
    )

    try:
        for evento in _eliminar_asientos_iter(
            base_empresa,
            asientos,
            usuario,
            tiene_permiso_corregir=True,
        ):
            if evento.get("type") == "progress":
                yield json.dumps(evento, ensure_ascii=False) + "\n"
            elif evento.get("type") == "result":
                fin = {"type": "done", **evento["payload"]}
                yield json.dumps(fin, ensure_ascii=False) + "\n"
    except EliminacionAsientosError as exc:
        yield json.dumps({"type": "error", "error": str(exc)}, ensure_ascii=False) + "\n"
    except Exception as exc:
        logger.exception("Error eliminando asientos (stream) base=%s", base_empresa)
        yield json.dumps({"type": "error", "error": str(exc)}, ensure_ascii=False) + "\n"


def _contexto_asientos_eliminar(request, filtros: dict | None = None) -> dict:
    user = getattr(request, "user", None)
    base_empresa = _base_empresa_sesion(request) or ""
    filtros = filtros or {}
    return {
        "titulo_pagina": "Eliminar asientos",
        "base_empresa": base_empresa,
        "id_ejercicio": filtros.get("id_ejercicio") or request.GET.get("id_ejercicio") or "",
        "permiso_leer": PERMISO_LEER,
        "permiso_corregir": PERMISO_CORREGIR,
        "puede_corregir": _tiene_permiso(user, PERMISO_CORREGIR),
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
        "lotes_url": reverse("contabilidad_audit:auditoria_lotes"),
        "dry_run_url": reverse("contabilidad_audit:auditoria_dry_run"),
        "ejercicios_periodos_url": reverse("contabilidad_audit:auditoria_ejercicios_periodos"),
        "asientos_url": reverse("contabilidad_audit:auditoria_asientos"),
        "preview_url": reverse("contabilidad_audit:auditoria_asientos_preview"),
        "eliminar_url": reverse("contabilidad_audit:auditoria_asientos_eliminar"),
    }


@administranet_login_required
@tiene_permiso(PERMISO_LEER)
@require_http_methods(["GET"])
def auditoria_asientos_eliminar(request):
    """
    GET /contabilidad/auditoria/asientos/

    Lista asientos filtrados. ``?format=json`` devuelve JSON paginado.
    """
    from legacy_db.services.cont_eliminacion_asientos_service import (
        EliminacionAsientosError,
        listar_asientos,
        listar_conceptos,
    )

    formato = request.GET.get("format")
    # HTML inicial: ejercicio opcional (estado vacío). JSON/buscar: ejercicio obligatorio.
    try:
        filtros = _parse_filtros_asientos(request, exigir_ejercicio=(formato == "json"))
    except ValueError as exc:
        if formato == "json":
            return JsonResponse({"error": str(exc)}, status=400)
        ctx = _contexto_asientos_eliminar(request)
        ctx["error_parametros"] = str(exc)
        return render(request, "contabilidad_audit/auditoria_asientos_eliminar.html", ctx)

    if formato == "json":
        try:
            payload = listar_asientos(filtros["base_empresa"], filtros)
        except EliminacionAsientosError as exc:
            return JsonResponse({"error": str(exc)}, status=400)
        except Exception as exc:
            logger.exception("Error listando asientos base=%s", filtros["base_empresa"])
            return JsonResponse({"error": str(exc)}, status=500)
        return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})

    ctx = _contexto_asientos_eliminar(request, filtros)
    if filtros.get("id_ejercicio"):
        try:
            ctx["conceptos"] = listar_conceptos(
                filtros["base_empresa"], int(filtros["id_ejercicio"])
            )
        except Exception as exc:
            logger.exception("Error listando conceptos asientos")
            ctx["error_conceptos"] = str(exc)
            ctx["conceptos"] = []
    else:
        ctx["conceptos"] = []
    return render(request, "contabilidad_audit/auditoria_asientos_eliminar.html", ctx)


@administranet_login_required
@tiene_permiso(PERMISO_LEER)
@require_POST
def auditoria_asientos_preview(request):
    """POST /contabilidad/auditoria/asientos/preview/ — vista previa JSON."""
    from legacy_db.services.cont_eliminacion_asientos_service import (
        EliminacionAsientosError,
        preview_eliminacion,
    )

    base_empresa = _base_empresa_sesion(request)
    if not base_empresa:
        return JsonResponse({"error": "No hay empresa base en la sesión."}, status=400)

    try:
        asientos = _parse_asientos_json_body(request)
        payload = preview_eliminacion(base_empresa, asientos)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except EliminacionAsientosError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
    except Exception as exc:
        logger.exception("Error preview eliminación asientos base=%s", base_empresa)
        return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse(payload, json_dumps_params={"ensure_ascii": False})


@administranet_login_required
@tiene_permiso(PERMISO_CORREGIR)
@require_POST
def auditoria_asientos_eliminar_ejecutar(request):
    """POST /contabilidad/auditoria/asientos/eliminar/ — elimina asientos seleccionados."""
    from legacy_db.services.cont_eliminacion_asientos_service import (
        EliminacionAsientosError,
        eliminar_asientos,
    )

    base_empresa = _base_empresa_sesion(request)
    if not base_empresa:
        return JsonResponse({"error": "No hay empresa base en la sesión."}, status=400)

    try:
        asientos, stream = _parse_asientos_eliminar_body(request)
    except ValueError as exc:
        return JsonResponse({"error": str(exc)}, status=400)

    usuario = _usuario_identificador(request)

    if stream:
        response = StreamingHttpResponse(
            _stream_eliminar_asientos_ndjson(base_empresa, asientos, usuario),
            content_type="application/x-ndjson; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response

    try:
        resultado = eliminar_asientos(
            base_empresa,
            asientos,
            usuario,
            tiene_permiso_corregir=True,
        )
    except EliminacionAsientosError as exc:
        return JsonResponse({"error": str(exc)}, status=409)
    except Exception as exc:
        logger.exception("Error eliminando asientos base=%s", base_empresa)
        return JsonResponse({"error": str(exc)}, status=500)

    return JsonResponse(resultado, json_dumps_params={"ensure_ascii": False})


def manual_usuario_view(request):
    """Manual de usuario Contabilidad (HTML estático). Solo requiere sesión activa."""
    if "user" not in request.session or not request.session.get("user"):
        return redirect("login:login")
    manual_path = (
        Path(__file__).resolve().parent
        / "static"
        / "contabilidad_audit"
        / "manuales"
        / "manual_usuario_contabilidad.html"
    )
    if not manual_path.is_file():
        raise Http404("Manual de usuario Contabilidad no encontrado.")
    return FileResponse(
        manual_path.open("rb"),
        content_type="text/html; charset=utf-8",
    )
