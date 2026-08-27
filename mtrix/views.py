"""Vistas del módulo Mtrix."""

from __future__ import annotations

import io
import logging
import subprocess
import sys
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from core.decorators import administranet_login_required, tiene_permiso
from core.utils.administranet_types import str_or_default, to_date_or_none, to_int_or_none
from mtrix.extractors import EXTRACTORS
from mtrix.extractors.base import parse_proveedores
from mtrix.models import MtrixJob
from mtrix.services.crypto import encrypt_secret
from mtrix.services.orchestrator import (
    config_to_export,
    crear_job,
    hay_job_activo,
)
from mtrix.services.preview_formatter import format_row
from mtrix.services.schedule import DOW_LABELS, normalize_schedule
from mtrix.services.sftp import enviar_job, test_connection
from mtrix.view_helpers import base_empresa_sesion, get_or_create_config, sftp_masked

logger = logging.getLogger(__name__)

TIPOS_PREVIEW = ("CI", "PD", "ES", "VD", "FV")
COLUMNAS = {
    "CI": [
        ("CNPJ_CLIENTE", "CUIT cliente"),
        ("RAZAO_SOCIAL", "Razón social"),
        ("ENDERECO", "Dirección"),
        ("CIDADE", "Ciudad"),
        ("ESTADO", "Provincia"),
        ("TIPO_LOJ", "Tipo"),
        ("REPRESENTATIVIDADE", "%"),
    ],
    "PD": [
        ("CODIGO_PRODUTO", "Código"),
        ("DESCRICAO", "Descripción"),
        ("EAN", "EAN"),
        ("DIVISAO_MARCA", "Marca"),
        ("DISCONTINUO", "Discontinuo"),
    ],
    "ES": [
        ("EAN", "EAN"),
        ("QTDE_TOTAL", "Cantidad"),
    ],
    "VD": [
        ("COD_CLIENTE", "Cliente"),
        ("DATA", "Fecha"),
        ("NOTA_FISCAL", "Comprobante"),
        ("EAN", "EAN"),
        ("QTDE", "Cantidad"),
        ("PRECO", "Precio"),
        ("VENDEDOR", "Vendedor"),
        ("TIPO_COMP", "Tipo"),
    ],
    "FV": [
        ("CNPJ_CLIENTE", "Cliente"),
        ("COD_VENDEDOR", "Cód. vendedor"),
        ("NOME_VENDEDOR", "Vendedor"),
        ("NOME_SUPERVISOR", "Supervisor"),
        ("NOME_GERENTE", "Gerente"),
    ],
}


def _launch_subprocess(job_id: str) -> None:
    manage_py = Path(settings.BASE_DIR) / "manage.py"
    subprocess.Popen(
        [sys.executable, str(manage_py), "generar_mtrix", f"--job-id={job_id}"],
        cwd=str(settings.BASE_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )


def _require_base(request):
    base = base_empresa_sesion(request)
    if not base:
        messages.error(request, "No hay empresa seleccionada en la sesión.")
        return None
    return base


@administranet_login_required
@tiene_permiso("mtrix.ver")
@require_GET
def hub(request):
    base = _require_base(request)
    if not base:
        return redirect("core:dashboard")
    cfg = get_or_create_config(base)
    ultimo = MtrixJob.objects.filter(base_empresa=base).first()
    return render(
        request,
        "mtrix/hub.html",
        {
            "config": cfg,
            "ultimo_job": ultimo,
            "tipos": TIPOS_PREVIEW,
            "job_activo": hay_job_activo(base),
        },
    )


@administranet_login_required
@tiene_permiso("mtrix.ver")
@require_GET
def preview(request, tipo: str):
    tipo = (tipo or "").upper()
    if tipo not in TIPOS_PREVIEW:
        raise Http404("Tipo de reporte inválido.")
    base = _require_base(request)
    if not base:
        return redirect("mtrix:hub")
    cfg = get_or_create_config(base)
    error = ""
    filas = []
    total = 0
    try:
        export_cfg = config_to_export(cfg)
        extractor = EXTRACTORS[tipo]
        kwargs = {}
        if tipo in {"PD", "ES", "VD"}:
            proveedores = parse_proveedores(cfg.codigo_proveedor_principal)
            kwargs["codigo_prov"] = proveedores[0] if proveedores else "TODOS"
        page_num = to_int_or_none(request.GET.get("page")) or 1
        per_page = 50
        raw = extractor.fetch_rows(None, export_cfg, limit=per_page, offset=(page_num - 1) * per_page, **kwargs)
        total = extractor.count_rows(None, export_cfg, **kwargs) if hasattr(extractor, "count_rows") else len(raw)
        filas = [format_row(tipo, r) for r in raw]
    except Exception as exc:
        logger.exception("Preview Mtrix %s: %s", tipo, exc)
        error = f"No se pudieron leer los datos: {exc}"
        export_cfg = None
        page_num = 1
        per_page = 50
    paginator = Paginator(range(total or 0), 50)
    page = paginator.get_page(page_num)
    return render(
        request,
        "mtrix/preview.html",
        {
            "tipo": tipo,
            "columnas": COLUMNAS[tipo],
            "filas": filas,
            "page_obj": page,
            "error": error,
            "config": cfg,
            "export_cfg": export_cfg,
            "vacio": not filas and not error,
        },
    )


@administranet_login_required
@tiene_permiso("mtrix.configurar")
@require_http_methods(["GET", "POST"])
def configuracion(request):
    base = _require_base(request)
    if not base:
        return redirect("mtrix:hub")
    cfg = get_or_create_config(base)
    if request.method == "POST":
        cfg.fecha_personalizada = request.POST.get("fecha_personalizada") == "1"
        cfg.fecha_inicio = to_date_or_none(request.POST.get("fecha_inicio"))
        cfg.fecha_final = to_date_or_none(request.POST.get("fecha_final"))
        cfg.dias_a_procesar = to_int_or_none(request.POST.get("dias_a_procesar")) or 5
        cfg.codigo_proveedor_principal = str_or_default(request.POST.get("codigo_proveedor_principal"), "")
        cfg.cnpj_fornecedor = str_or_default(request.POST.get("cnpj_fornecedor"), "").replace("-", "")
        cfg.pvnf = request.POST.get("pvnf") == "1"
        cfg.multiplicador_cantidad = to_int_or_none(request.POST.get("multiplicador_cantidad")) or 1
        cfg.multiplicador_precio = to_int_or_none(request.POST.get("multiplicador_precio")) or 1
        cfg.sftp_host = str_or_default(request.POST.get("sftp_host"), "")
        cfg.sftp_port = to_int_or_none(request.POST.get("sftp_port")) or 22
        cfg.sftp_user = str_or_default(request.POST.get("sftp_user"), "")
        cfg.sftp_remote_path = str_or_default(request.POST.get("sftp_remote_path"), "")
        cfg.sftp_key_path = str_or_default(request.POST.get("sftp_key_path"), "")
        nueva_clave = (request.POST.get("sftp_password") or "").strip()
        if nueva_clave:
            cfg.sftp_password_encrypted = encrypt_secret(nueva_clave)
        cfg.sftp_enviar_automatico = request.POST.get("sftp_enviar_automatico") == "1"
        cfg.programador_activo = request.POST.get("programador_activo") == "1"
        rules = []
        for dow in range(7):
            if request.POST.get(f"schedule_enabled_{dow}") == "1":
                rules.append({"dow": dow, "time": str_or_default(request.POST.get(f"schedule_time_{dow}"), "06:00")})
        cfg.schedule_json = rules
        cfg.save()
        messages.success(request, "Configuración Mtrix guardada.")
        return redirect("mtrix:configuracion")
    by_dow = {int(r["dow"]): r for r in normalize_schedule(cfg.schedule_json)}
    schedule_rows = []
    for dow in range(7):
        rule = by_dow.get(dow, {"dow": dow, "time": "06:00"})
        schedule_rows.append(
            {
                "dow": dow,
                "label": DOW_LABELS[dow],
                "time": rule.get("time", "06:00"),
                "enabled": dow in by_dow,
            }
        )
    return render(
        request,
        "mtrix/configuracion.html",
        {"config": cfg, "schedule_rows": schedule_rows, "sftp_masked": sftp_masked(cfg)},
    )


@administranet_login_required
@tiene_permiso("mtrix.ver")
@require_GET
def job_list(request):
    base = _require_base(request)
    if not base:
        return redirect("mtrix:hub")
    jobs = MtrixJob.objects.filter(base_empresa=base)[:100]
    return render(request, "mtrix/job_list.html", {"jobs": jobs})


@administranet_login_required
@tiene_permiso("mtrix.ver")
@require_GET
def job_detail(request, job_id):
    base = _require_base(request)
    job = get_object_or_404(MtrixJob, pk=job_id, base_empresa=base)
    return render(request, "mtrix/job_detail.html", {"job": job, "artifacts": job.artifacts.all()})


@administranet_login_required
@tiene_permiso("mtrix.generar")
@require_http_methods(["POST"])
def generar(request):
    base = _require_base(request)
    if not base:
        return redirect("mtrix:hub")
    if hay_job_activo(base):
        messages.error(request, "Ya hay una corrida Mtrix en curso para esta empresa.")
        return redirect("mtrix:hub")
    triggered = str_or_default((request.session.get("user") or {}).get("cod_usuario"), "")
    try:
        job = crear_job(base_empresa=base, origen=MtrixJob.Origen.UI, triggered_by=triggered)
    except RuntimeError as exc:
        messages.error(request, str(exc))
        return redirect("mtrix:hub")
    _launch_subprocess(str(job.id))
    messages.success(request, "Se inició la generación de archivos MTRIX.")
    return redirect("mtrix:job_detail", job_id=job.id)


@administranet_login_required
@tiene_permiso("mtrix.ver")
@require_GET
def job_download(request, job_id):
    base = _require_base(request)
    job = get_object_or_404(MtrixJob, pk=job_id, base_empresa=base)
    arts = list(job.artifacts.all())
    if not arts:
        messages.error(request, "Este job no tiene archivos para descargar.")
        return redirect("mtrix:job_detail", job_id=job.id)
    media = Path(settings.MEDIA_ROOT)
    if len(arts) == 1:
        path = media / arts[0].relative_path
        if not path.exists():
            raise Http404("Archivo no encontrado.")
        return FileResponse(path.open("rb"), as_attachment=True, filename=arts[0].filename)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for art in arts:
            path = media / art.relative_path
            if path.exists():
                zf.write(path, art.filename)
    buf.seek(0)
    return FileResponse(buf, as_attachment=True, filename=f"mtrix-{job.id}.zip")


@administranet_login_required
@tiene_permiso("mtrix.enviar_sftp")
@require_http_methods(["POST"])
def job_enviar_sftp(request, job_id):
    base = _require_base(request)
    job = get_object_or_404(MtrixJob, pk=job_id, base_empresa=base)
    cfg = get_or_create_config(base)
    result = enviar_job(job, cfg)
    if result.success:
        messages.success(request, result.message)
    else:
        messages.error(request, result.message)
    return redirect("mtrix:job_detail", job_id=job.id)


@administranet_login_required
@tiene_permiso("mtrix.ver")
@require_GET
def api_job(request, job_id):
    base = _require_base(request)
    job = get_object_or_404(MtrixJob, pk=job_id, base_empresa=base)
    return JsonResponse(
        {
            "status": job.status,
            "progreso": job.progreso,
            "error": job.error_summary,
        }
    )


@administranet_login_required
@tiene_permiso("mtrix.configurar")
@require_http_methods(["POST"])
def api_sftp_probar(request):
    base = _require_base(request)
    if not base:
        return JsonResponse({"ok": False, "mensaje": "Sin empresa en sesión."}, status=400)
    cfg = get_or_create_config(base)
    result = test_connection(cfg)
    return JsonResponse({"ok": result.success, "mensaje": result.message})
