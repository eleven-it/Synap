"""Vistas de auditoría contable (UI canon reportes Synap).

Fase 1 (solo lectura): tablero verde/rojo por check, export CSV/Excel y
configuración de políticas. Mantiene intacto el contrato `?format=json`
del runner y los permisos Synap dedicados.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.decorators import administranet_login_required, tiene_permiso

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
        "checks_seleccionados": filtros.get("check_ids") or [],
        "permiso_leer": PERMISO_LEER,
        "permiso_configurar": PERMISO_CONFIGURAR,
        "puede_configurar": _tiene_permiso(user, PERMISO_CONFIGURAR),
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
        "configuracion_url": reverse("contabilidad_audit:auditoria_configuracion"),
        "ejercicios_periodos_url": reverse("contabilidad_audit:auditoria_ejercicios_periodos"),
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
    alcance = {
        "base_empresa": base_empresa,
        "id_ejercicio": int(id_ejercicio),
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
    return timezone.localtime(dt).strftime("%d/%m/%Y %H:%M")


def _fecha_date_ui(valor) -> str:
    """Formatea una fecha legacy (DATE) como dd/MM/yyyy. Tolerante a None/str."""
    if valor is None or valor == "":
        return ""
    try:
        return valor.strftime("%d/%m/%Y")
    except AttributeError:
        return str(valor)


def _contexto_dry_run(request, payload: dict | None = None, alcance_recompute: str = "") -> dict:
    user = getattr(request, "user", None)
    base_empresa = _base_empresa_sesion(request) or ""
    return {
        "titulo_pagina": "Dry-run de corrección contable",
        "base_empresa": base_empresa,
        "id_ejercicio": request.GET.get("id_ejercicio") or "",
        "id_periodo": request.GET.get("id_periodo") or "",
        "alcance_recompute": alcance_recompute,
        "permiso_leer": PERMISO_LEER,
        "puede_configurar": _tiene_permiso(user, PERMISO_CONFIGURAR),
        "tablero_url": reverse("contabilidad_audit:auditoria_tablero"),
        "configuracion_url": reverse("contabilidad_audit:auditoria_configuracion"),
        "dry_run_url": reverse("contabilidad_audit:auditoria_dry_run"),
        "apply_url": reverse("contabilidad_audit:auditoria_apply"),
        "payload": payload,
        "auto_ejecutar": bool(
            base_empresa
            and request.GET.get("id_ejercicio")
            and payload is None
        ),
    }


@administranet_login_required
@tiene_permiso(PERMISO_LEER)
@require_GET
def auditoria_dry_run(request):
    """
    GET /contabilidad/auditoria/dry-run/

    Genera plan de corrección (100 % SELECT legacy), persiste PlanCorreccion
    y muestra guards TTL/config_hash/data_fingerprint. No aplica cambios (Fase 3).

    - ``?format=json`` → payload JSON
    - ``?format=csv|xlsx`` → export del plan
    - Sin ``format`` → plantilla canon con resumen del plan
    """
    from legacy_db.services.cont_recalculo_service import dry_run

    formato = request.GET.get("format")

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
    if formato == "csv":
        from contabilidad_audit.services.export import exportar_dry_run_csv

        return exportar_dry_run_csv(payload)
    if formato == "xlsx":
        from contabilidad_audit.services.export import exportar_dry_run_xlsx

        return exportar_dry_run_xlsx(payload)

    ctx = _contexto_dry_run(request, payload, alcance_recompute=alcance_recompute)
    if payload and payload.get("dry_run_id"):
        ctx["rei_url"] = reverse(
            "contabilidad_audit:auditoria_rei_aprobacion",
            kwargs={"dry_run_id": payload["dry_run_id"]},
        )
        ctx["apply_confirm_url"] = (
            f"{reverse('contabilidad_audit:auditoria_apply')}"
            f"?dry_run_id={payload['dry_run_id']}&base_empresa={payload.get('base_empresa', '')}"
        )
        ctx["puede_corregir"] = _tiene_permiso(getattr(request, "user", None), PERMISO_CORREGIR)
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
# Fase 3 — Confirmación apply (doble confirmación)
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
    """GET /contabilidad/auditoria/apply/ — formulario de doble confirmación (solo lectura)."""
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

    Ejecuta ``apply()`` con doble confirmación explícita. No disponible por GET.
    """
    from legacy_db.services.cont_recalculo_service import CorreccionContableError, apply

    dry_run_id = request.POST.get("dry_run_id")
    base_empresa = request.POST.get("base_empresa")
    modo = request.POST.get("modo") or "general"
    confirmacion_1 = request.POST.get("confirmacion_entiendo") == "on"
    confirmacion_2 = (request.POST.get("confirmacion_final") or "").strip().upper()
    confirmar_reapertura = request.POST.get("confirmar_reapertura") == "on"

    if not dry_run_id or not base_empresa:
        messages.error(request, "Faltan parámetros obligatorios (dry_run_id, base_empresa).")
        return redirect(reverse("contabilidad_audit:auditoria_dry_run"))

    if not confirmacion_1:
        messages.error(
            request,
            "Debe marcar la primera confirmación: entiende que se modificarán datos contables.",
        )
        return redirect(
            f"{reverse('contabilidad_audit:auditoria_apply')}?dry_run_id={dry_run_id}&base_empresa={base_empresa}&modo={modo}"
        )

    token_esperado = f"APLICAR-{dry_run_id}".upper()
    if confirmacion_2 != token_esperado and confirmacion_2 != "APLICAR DEFINITIVAMENTE":
        messages.error(
            request,
            f"Confirmación final incorrecta. Escriba exactamente: {token_esperado}",
        )
        return redirect(
            f"{reverse('contabilidad_audit:auditoria_apply')}?dry_run_id={dry_run_id}&base_empresa={base_empresa}&modo={modo}"
        )

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
        ctx = _contexto_apply(request, plan, error=str(exc))
        return render(request, "contabilidad_audit/auditoria_apply.html", ctx, status=409)
    except Exception as exc:
        ctx = _contexto_apply(request, plan, error=f"Error inesperado: {exc}")
        return render(request, "contabilidad_audit/auditoria_apply.html", ctx, status=500)

    lote = resultado.get("lote_id") or "—"
    filas = resultado.get("filas_aplicadas", 0)
    messages.success(
        request,
        f"Corrección aplicada. Lote: {lote}. Filas afectadas: {filas}.",
    )
    ctx = _contexto_apply(request, plan)
    ctx["resultado_apply"] = resultado
    return render(request, "contabilidad_audit/auditoria_apply.html", ctx)
