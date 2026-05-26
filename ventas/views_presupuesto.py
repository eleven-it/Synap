# -*- coding: utf-8 -*-
"""Vistas Presupuesto de venta (PRE): lista, detalle lectura; alta en evolución."""

from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from core.decorators import administranet_login_required, tiene_permiso
from core.utils.administranet_types import str_or_default, to_int_or_none
from core.services.administranet_permisos_sistema import AdministraNETPermisosSistemaService
from core.services.administranet_stock import (
    get_clientes,
    get_condiciones_venta,
    get_viajantes,
)
from ventas.services.presupuesto_guardado import alta_presupuesto_mvp
from ventas.services.presupuesto_mysql import (
    DEFAULT_PAGE_SIZE,
    listar_lineas_presupuesto_stockp,
    obtener_presupuesto_cabecera,
    listar_presupuestos,
)
from ventas.services.presupuesto_permisos import contexto_ui_presupuesto
from reports.services.export_service import ExportService


def _base_empresa_session(request) -> str:
    session_user = request.session.get("user", {}) or {}
    return (session_user.get("base_empresa") or "").strip()


def _id_sucursal_session(request) -> int | None:
    session_user = request.session.get("user", {}) or {}
    raw = session_user.get("id_sucursal")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _usuario_puede_editar_presupuesto(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "cod_usuario", None) and str(user.cod_usuario).lower() == "supervisor":
        return True
    fn = getattr(user, "tiene_permiso", None)
    if not fn:
        return False
    return bool(fn("ventas.presupuesto.editar") or fn("ventas.editar"))


def _parse_date_param(s: str) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _fmt_date(d: Any) -> str:
    if d is None:
        return "—"
    if isinstance(d, datetime):
        d = d.date()
    if isinstance(d, date):
        return d.strftime("%d/%m/%Y")
    return str(d)


def _fmt_money_ar(val: Any) -> str:
    """Importe para etiquetas UI (coma decimal, sin miles obligatorios)."""
    if val is None:
        return "—"
    try:
        x = Decimal(str(val))
    except Exception:
        return "—"
    x = x.quantize(Decimal("0.01"))
    neg = x < 0
    x = abs(x)
    s = format(x, "f")
    if "." not in s:
        s += ".00"
    a, b = s.split(".", 1)
    b = (b + "00")[:2]
    body = f"{a},{b}"
    return ("-" if neg else "") + body


def _fmt_qty_linea_ar(val: Any) -> str:
    if val is None:
        return ""
    try:
        x = Decimal(str(val))
    except Exception:
        return ""
    if x == x.to_integral():
        return str(int(x))
    q = x.quantize(Decimal("0.0001"))
    s = format(q, "f").rstrip("0").rstrip(".")
    return s.replace(".", ",")


def _sum_neto_lineas_stockp(lineas: list[dict[str, Any]]) -> Decimal:
    t = Decimal("0")
    for ln in lineas:
        n = ln.get("precio_neto_renglon")
        if n is not None:
            t += Decimal(str(n))
    return t.quantize(Decimal("0.01"))


def _lineas_ui_presupuesto_ver(lineas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Campos formateados para filas de solo lectura (misma grilla que alta)."""
    rows: list[dict[str, Any]] = []
    for ln in lineas:
        qty = ln.get("cantidad")
        pu = ln.get("precio_unitario")
        neto = ln.get("precio_neto_renglon")
        venta_r = ln.get("precio_venta_renglon")
        bruto: Decimal | None = None
        if qty is not None and pu is not None:
            try:
                bruto = Decimal(str(qty)) * Decimal(str(pu))
            except Exception:
                bruto = None
        dto_pct = Decimal("0")
        if bruto is not None and bruto > 0 and neto is not None:
            try:
                n = Decimal(str(neto))
                dto_pct = (Decimal("1") - (n / bruto)) * Decimal("100")
                if dto_pct < 0:
                    dto_pct = Decimal("0")
                if dto_pct > 100:
                    dto_pct = Decimal("100")
            except Exception:
                dto_pct = Decimal("0")
        dto_pct_str = ""
        if dto_pct > 0:
            q = dto_pct.quantize(Decimal("0.01"))
            dto_pct_str = format(q, "f").replace(".", ",")

        dep = ln.get("cod_deposito")
        sub_fmt = _fmt_money_ar(venta_r) if venta_r is not None else _fmt_money_ar(neto)

        rows.append(
            {
                "codigo_articulo": ln.get("codigo_articulo") or "",
                "descripcion": ln.get("descripcion") or "",
                "cantidad_str": _fmt_qty_linea_ar(qty),
                "pu_str": _fmt_money_ar(pu) if pu is not None else "",
                "dto_pct_str": dto_pct_str,
                "cod_deposito": dep if dep is not None else 1,
                "iva_pct_txt": "—",
                "iva_importe_txt": "—",
                "subtotal_txt": sub_fmt,
            }
        )
    return rows


def _json_safe(o: Any) -> Any:
    """Serialización para JsonResponse (Decimal, date, datetime, anidados)."""
    if o is None:
        return None
    if isinstance(o, Decimal):
        return float(o)
    if isinstance(o, datetime):
        return o.isoformat(sep=" ", timespec="seconds")
    if isinstance(o, date):
        return o.isoformat()
    if isinstance(o, dict):
        return {k: _json_safe(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_json_safe(x) for x in o]
    return o


def _page_size_api(request) -> int:
    try:
        ps = int(request.GET.get("page_size") or DEFAULT_PAGE_SIZE)
    except (TypeError, ValueError):
        return DEFAULT_PAGE_SIZE
    return min(100, max(5, ps))


def _parametros_listado_presupuesto(request) -> dict:
    """Parámetros GET compartidos entre lista HTML y API JSON."""
    id_suc = _id_sucursal_session(request)
    solo_sucursal = request.GET.get("todas", "").strip().lower() not in ("1", "true", "si")
    try:
        page = max(1, int(request.GET.get("page") or 1))
    except ValueError:
        page = 1
    q = request.GET.get("q") or ""
    fecha_desde = _parse_date_param(request.GET.get("fecha_desde") or "")
    fecha_hasta = _parse_date_param(request.GET.get("fecha_hasta") or "")
    cod_fil = id_suc if solo_sucursal else None
    return {
        "page": page,
        "q": q,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "cod_sucursal": cod_fil,
        "solo_sucursal": solo_sucursal,
    }


def _session_user_dict(request) -> dict:
    return request.session.get("user") or {}


def _id_usuario_session(request) -> int | None:
    raw = _session_user_dict(request).get("id_usuario")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _id_punto_venta_session(request) -> int | None:
    raw = _session_user_dict(request).get("id_punto_venta")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _id_vendedor_session(request) -> int | None:
    raw = _session_user_dict(request).get("id_vendedor_usr")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _usuario_es_supervisor(user) -> bool:
    return bool(
        user and getattr(user, "cod_usuario", None) and str(user.cod_usuario).lower() == "supervisor"
    )


def _puede_emitir_presupuesto(request) -> bool:
    """Permiso legacy `carga_comp_ped` o usuario supervisor."""
    if _usuario_es_supervisor(request.user):
        return True
    return bool(_permisos_presupuesto_desde_sesion(request).get("carga_comp_ped_si"))


def _construir_lineas_desde_post(request) -> list[dict[str, Any]]:
    """
    Agrupa campos repetidos `linea_*` enviados por el formulario multirenglón.
    Omite filas sin código de artículo.
    """
    cods = request.POST.getlist("linea_codigo_articulo")
    if not cods:
        return []

    descs = request.POST.getlist("linea_descripcion")
    cants = request.POST.getlist("linea_cantidad")
    p_units = request.POST.getlist("linea_precio_unitario")
    dto_line = request.POST.getlist("linea_desc_porciento")
    deps = request.POST.getlist("linea_cod_deposito")
    dets = request.POST.getlist("linea_detalle")

    def _at(lst: list, i: int, default: str = "") -> str:
        return lst[i] if i < len(lst) else default

    lineas: list[dict[str, Any]] = []
    for i in range(len(cods)):
        cod = (_at(cods, i) or "").strip()
        if not cod:
            continue
        lineas.append(
            {
                "codigo_articulo": cod,
                "descripcion": (_at(descs, i) or "").strip(),
                "cantidad": _at(cants, i),
                "precio_unitario": _at(p_units, i),
                "por_desc_linea": _at(dto_line, i) or "0",
                "cod_deposito": _at(deps, i) or "1",
                "detalle_renglon": (_at(dets, i) or "").strip() or "-",
            }
        )
    return lineas


def _permisos_presupuesto_desde_sesion(request) -> dict:
    """Fila `permisos_sistema` del puesto en sesión → flags UI PRE."""
    base_empresa = _base_empresa_session(request)
    session_user = request.session.get("user", {}) or {}
    id_puesto = session_user.get("id_puesto")
    if not base_empresa or id_puesto is None:
        return contexto_ui_presupuesto(None)
    try:
        id_puesto_int = int(id_puesto)
    except (TypeError, ValueError):
        return contexto_ui_presupuesto(None)
    svc = AdministraNETPermisosSistemaService()
    raw = svc.obtener_permisos_puesto(base_empresa, id_puesto_int)
    return contexto_ui_presupuesto(raw)


@tiene_permiso("ventas.presupuesto.ver")
def presupuesto_list_view(request):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    p = _parametros_listado_presupuesto(request)

    ok, err, rows, total = listar_presupuestos(
        base_empresa,
        cod_sucursal=p["cod_sucursal"],
        q=p["q"],
        fecha_desde=p["fecha_desde"],
        fecha_hasta=p["fecha_hasta"],
        page=p["page"],
        page_size=DEFAULT_PAGE_SIZE,
    )

    total_pages = max(1, (total + DEFAULT_PAGE_SIZE - 1) // DEFAULT_PAGE_SIZE)

    for row in rows:
        row["fecha_fmt"] = _fmt_date(row.get("fecha"))

    ctx_perm = _permisos_presupuesto_desde_sesion(request)

    return render(
        request,
        "ventas/presupuesto_list.html",
        {
            "base_empresa": base_empresa,
            "presupuestos": rows if ok else [],
            "error_carga": err if not ok else "",
            "total": total,
            "page": p["page"],
            "total_pages": total_pages,
            "page_size": DEFAULT_PAGE_SIZE,
            "q": p["q"],
            "fecha_desde": p["fecha_desde"].isoformat() if p["fecha_desde"] else "",
            "fecha_hasta": p["fecha_hasta"].isoformat() if p["fecha_hasta"] else "",
            "solo_sucursal_actual": p["solo_sucursal"],
            "puede_editar": _usuario_puede_editar_presupuesto(request.user),
            "permisos_pre": ctx_perm,
        },
    )


@tiene_permiso("ventas.presupuesto.ver")
def presupuesto_detalle_view(request, codigo_movimiento: int):
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    ok, err, cab = obtener_presupuesto_cabecera(base_empresa, codigo_movimiento)
    if not ok or not cab:
        messages.error(request, err or "No se encontró el presupuesto.")
        return redirect("ventas:presupuesto_list")

    id_suc = _id_sucursal_session(request)
    if id_suc is not None and cab.get("cod_sucursal") is not None:
        if int(cab["cod_sucursal"] or 0) != int(id_suc):
            messages.warning(
                request,
                "Este presupuesto pertenece a otra sucursal; se muestra solo lectura.",
            )

    cab["fecha_fmt"] = _fmt_date(cab.get("fecha"))
    cab["vencimiento_fmt"] = _fmt_date(cab.get("vencimiento"))

    ok_ln, err_ln, lineas = listar_lineas_presupuesto_stockp(base_empresa, codigo_movimiento)
    if not ok_ln:
        lineas = []
        err_lineas = err_ln
    else:
        err_lineas = ""

    ctx_perm = _permisos_presupuesto_desde_sesion(request)
    puede_editar_items = (
        _usuario_puede_editar_presupuesto(request.user) and ctx_perm["mod_item_pre_ped_si"]
    )

    fecha_iso = ""
    fv = cab.get("fecha")
    if fv:
        if isinstance(fv, datetime):
            fv = fv.date()
        if isinstance(fv, date):
            fecha_iso = fv.isoformat()

    vencimiento_iso = ""
    vv = cab.get("vencimiento")
    if vv:
        if isinstance(vv, datetime):
            vv = vv.date()
        if isinstance(vv, date):
            vencimiento_iso = vv.isoformat()

    lineas_ui = _lineas_ui_presupuesto_ver(lineas)
    sum_neto = _sum_neto_lineas_stockp(lineas)

    return render(
        request,
        "ventas/presupuesto_nuevo.html",
        {
            "base_empresa": base_empresa,
            "solo_lectura": True,
            "cab": cab,
            "lineas": lineas,
            "lineas_ui": lineas_ui,
            "error_lineas": err_lineas,
            "sum_neto_fmt": _fmt_money_ar(sum_neto),
            "importe_cab_fmt": _fmt_money_ar(cab.get("importe_venta")),
            "fecha_presupuesto_iso": fecha_iso,
            "vencimiento_presupuesto_iso": vencimiento_iso,
            "volver_url": reverse("ventas:presupuesto_list"),
            "export_presupuesto_url": reverse(
                "ventas:presupuesto_export_xlsx",
                kwargs={"codigo_movimiento": codigo_movimiento},
            ),
            "permisos_pre": ctx_perm,
            "puede_emitir": False,
            "api_clientes_url": reverse("ventas:api_presupuesto_clientes_buscar"),
            "puede_editar": _usuario_puede_editar_presupuesto(request.user),
            "puede_editar_items": puede_editar_items,
        },
    )


@administranet_login_required
def presupuesto_nuevo_view(request):
    """
    Emisión de PRE: numeración sistema, `comp_ped` + `stockp` (MVP, sin temporales ni percepciones).
    """
    if not _usuario_puede_editar_presupuesto(request.user):
        raise PermissionDenied

    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    ctx_perm = _permisos_presupuesto_desde_sesion(request)
    puede_emitir = _puede_emitir_presupuesto(request)

    if request.method == "POST" and puede_emitir:
        id_usuario = _id_usuario_session(request)
        if not id_usuario:
            messages.error(request, "No se identificó el usuario en sesión.")
            return redirect("ventas:presupuesto_nuevo")

        id_pv = _id_punto_venta_session(request)
        if not id_pv:
            messages.error(request, "No hay punto de venta en sesión.")
            return redirect("ventas:presupuesto_nuevo")

        id_suc = _id_sucursal_session(request)
        if id_suc is None:
            messages.error(request, "No hay sucursal en sesión.")
            return redirect("ventas:presupuesto_nuevo")

        cod_cli = to_int_or_none(request.POST.get("codigo_cliente"))
        fecha_pre = _parse_date_param(request.POST.get("fecha") or "") or date.today()
        detalle = (request.POST.get("detalle") or "").strip()

        cond_rows = get_condiciones_venta(base_empresa)
        cv_by_id: dict[int, str] = {}
        for row in cond_rows:
            cid_cv = to_int_or_none(row.get("Codigo"))
            if cid_cv is None:
                continue
            cv_by_id[cid_cv] = str_or_default(row.get("Descripcion"), "-")

        id_cv = to_int_or_none(request.POST.get("id_condventa"))
        if id_cv is None or id_cv <= 0:
            id_cv = 1
        cv_txt = cv_by_id.get(id_cv) or "Contado"
        if cv_txt == "-":
            cv_txt = "Contado"

        cod_viajante = to_int_or_none(request.POST.get("cod_viajante"))
        if cod_viajante is None:
            cod_viajante = _id_vendedor_session(request)

        vencimiento_pre = _parse_date_param(request.POST.get("vencimiento") or "")

        lineas = _construir_lineas_desde_post(request)

        ok, err, cm, nro = alta_presupuesto_mvp(
            base_empresa,
            id_usuario=id_usuario,
            cod_sucursal=id_suc,
            id_punto_venta=id_pv,
            codigo_cliente=cod_cli or 0,
            fecha=fecha_pre,
            detalle=detalle,
            id_condventa=id_cv,
            cond_venta=cv_txt,
            cod_viajante=cod_viajante,
            vencimiento=vencimiento_pre,
            lineas=lineas,
            desc_global_pct_1=request.POST.get("desc_global_pct_1"),
            desc_global_pct_2=request.POST.get("desc_global_pct_2"),
        )
        if ok and cm is not None:
            messages.success(
                request,
                f"Presupuesto guardado: {nro or ''} (movimiento {cm}).",
            )
            return redirect("ventas:presupuesto_detalle", codigo_movimiento=cm)
        messages.error(request, err or "No se pudo guardar el presupuesto.")
        return redirect("ventas:presupuesto_nuevo")

    viajantes = get_viajantes(base_empresa)
    raw_cond = get_condiciones_venta(base_empresa)
    condiciones_venta: list[dict[str, Any]] = []
    for r in raw_cond:
        cod = to_int_or_none(r.get("Codigo"))
        if cod is None:
            continue
        condiciones_venta.append(
            {"codigo": cod, "descripcion": str_or_default(r.get("Descripcion"), "-")},
        )
    ids_cv = [c["codigo"] for c in condiciones_venta]
    default_id_condventa = 1 if 1 in ids_cv else (ids_cv[0] if ids_cv else 1)
    default_cod_viajante = _id_vendedor_session(request)

    return render(
        request,
        "ventas/presupuesto_nuevo.html",
        {
            "base_empresa": base_empresa,
            "solo_lectura": False,
            "volver_url": reverse("ventas:presupuesto_list"),
            "permisos_pre": ctx_perm,
            "api_clientes_url": reverse("ventas:api_presupuesto_clientes_buscar"),
            "puede_emitir": puede_emitir,
            "viajantes": viajantes,
            "condiciones_venta": condiciones_venta,
            "default_id_condventa": default_id_condventa,
            "default_cod_viajante": default_cod_viajante,
        },
    )


@require_GET
@tiene_permiso("ventas.presupuesto.ver")
def api_presupuesto_clientes_buscar(request):
    """Búsqueda de clientes para emisión de PRE (autocomplete). Mín. 2 caracteres."""
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return JsonResponse({"results": [], "error": "Sin base empresa."}, status=400)

    q = (request.GET.get("q") or "").strip()
    if len(q) < 2:
        return JsonResponse({"results": []})

    rows = get_clientes(base_empresa, q=q, limit=40)
    results = []
    for row in rows:
        cod = row.get("Codigo")
        if cod is None:
            cod = row.get("codigo")
        if cod is None:
            continue
        nombre = (row.get("nombre_cliente") or row.get("Nombre_cliente") or "").strip()
        try:
            cid = int(cod)
        except (TypeError, ValueError):
            try:
                cid = int(float(cod))
            except (TypeError, ValueError):
                continue
        results.append({"id": cid, "text": nombre or str(cid)})

    return JsonResponse({"results": results})


@require_POST
@tiene_permiso("ventas.presupuesto.editar")
def api_presupuesto_crear(request):
    """
    Alta PRE (JSON). Mismo criterio que POST del formulario «Nuevo».
    Cuerpo: codigo_cliente, fecha (opcional), detalle, cond_venta, id_condventa, cod_viajante, lineas[].
    """
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "error": "Sin base empresa."}, status=400)
    if not _puede_emitir_presupuesto(request):
        return JsonResponse(
            {"ok": False, "error": "Sin permiso para cargar presupuestos (carga_comp_ped)."},
            status=403,
        )
    id_usuario = _id_usuario_session(request)
    if not id_usuario:
        return JsonResponse({"ok": False, "error": "Usuario no identificado en sesión."}, status=400)
    id_pv = _id_punto_venta_session(request)
    if not id_pv:
        return JsonResponse({"ok": False, "error": "Sin punto de venta en sesión."}, status=400)
    id_suc = _id_sucursal_session(request)
    if id_suc is None:
        return JsonResponse({"ok": False, "error": "Sin sucursal en sesión."}, status=400)

    try:
        body = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)

    cod_cli = to_int_or_none(body.get("codigo_cliente"))
    fecha_raw = body.get("fecha")
    if fecha_raw:
        fecha_pre = _parse_date_param(str(fecha_raw)[:10]) or date.today()
    else:
        fecha_pre = date.today()
    detalle = str(body.get("detalle") or "").strip()
    id_cv = to_int_or_none(body.get("id_condventa"))
    cond_venta = str(body.get("cond_venta") or "Contado").strip() or "Contado"
    cod_viajante = to_int_or_none(body.get("cod_viajante"))
    if cod_viajante is None:
        cod_viajante = _id_vendedor_session(request)
    ven_raw = body.get("vencimiento")
    vencimiento_pre = (
        _parse_date_param(str(ven_raw)[:10]) if ven_raw else None
    )
    lineas = body.get("lineas")
    if not isinstance(lineas, list):
        lineas = []

    ok, err, cm, nro = alta_presupuesto_mvp(
        base_empresa,
        id_usuario=id_usuario,
        cod_sucursal=id_suc,
        id_punto_venta=id_pv,
        codigo_cliente=cod_cli or 0,
        fecha=fecha_pre,
        detalle=detalle,
        id_condventa=id_cv,
        cond_venta=cond_venta,
        cod_viajante=cod_viajante,
        vencimiento=vencimiento_pre,
        lineas=lineas,
        desc_global_pct_1=body.get("desc_global_pct_1"),
        desc_global_pct_2=body.get("desc_global_pct_2"),
    )
    if ok and cm is not None:
        return JsonResponse(
            {
                "ok": True,
                "codigo_movimiento": cm,
                "nro_comprobante": nro,
                "detalle_url": reverse(
                    "ventas:presupuesto_detalle", kwargs={"codigo_movimiento": cm}
                ),
            }
        )
    return JsonResponse({"ok": False, "error": err or "Error al guardar."}, status=400)


@require_GET
@tiene_permiso("ventas.presupuesto.ver")
def api_presupuesto_list(request):
    """
    Listado de PRE en JSON (mismos criterios que la lista HTML).
    Query: `q`, `fecha_desde`, `fecha_hasta`, `page`, `page_size` (5–100), `todas=1` para ignorar filtro de sucursal.
    """
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return JsonResponse(
            {"ok": False, "error": "Sin base empresa.", "results": [], "total": 0},
            status=400,
        )

    p = _parametros_listado_presupuesto(request)
    page_size = _page_size_api(request)

    ok, err, rows, total = listar_presupuestos(
        base_empresa,
        cod_sucursal=p["cod_sucursal"],
        q=p["q"],
        fecha_desde=p["fecha_desde"],
        fecha_hasta=p["fecha_hasta"],
        page=p["page"],
        page_size=page_size,
    )

    total_pages = max(1, (total + page_size - 1) // page_size) if total else 0

    out = []
    if ok:
        for row in rows:
            item = dict(row)
            item["fecha_fmt"] = _fmt_date(item.get("fecha"))
            out.append(_json_safe(item))

    return JsonResponse(
        {
            "ok": bool(ok),
            "error": err if not ok else "",
            "results": out,
            "total": total,
            "page": p["page"],
            "page_size": page_size,
            "total_pages": total_pages,
            "filtros": {
                "q": p["q"],
                "fecha_desde": p["fecha_desde"].isoformat() if p["fecha_desde"] else "",
                "fecha_hasta": p["fecha_hasta"].isoformat() if p["fecha_hasta"] else "",
                "solo_sucursal_sesion": p["solo_sucursal"],
            },
        }
    )


@require_GET
@tiene_permiso("ventas.presupuesto.ver")
def api_presupuesto_retrieve(request, codigo_movimiento: int):
    """
    Cabecera PRE + renglones `stockp` en JSON.
    Query opcional: `incluir_lineas=0` para omitir `stockp` (solo cabecera).
    """
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "error": "Sin base empresa."}, status=400)

    ok, err, cab = obtener_presupuesto_cabecera(base_empresa, codigo_movimiento)
    if not ok or not cab:
        return JsonResponse(
            {
                "ok": False,
                "error": err or "Presupuesto no encontrado.",
                "cabecera": None,
                "lineas": [],
            },
            status=404,
        )

    incluir = (request.GET.get("incluir_lineas") or "1").strip().lower() not in ("0", "false", "no")
    lineas: list = []
    err_lineas = ""
    if incluir:
        ok_ln, err_ln, lineas_raw = listar_lineas_presupuesto_stockp(base_empresa, codigo_movimiento)
        if ok_ln:
            lineas = [_json_safe(x) for x in lineas_raw]
        else:
            err_lineas = err_ln or ""
            lineas = []

    id_suc = _id_sucursal_session(request)
    aviso_sucursal = ""
    if id_suc is not None and cab.get("cod_sucursal") is not None:
        if int(cab["cod_sucursal"] or 0) != int(id_suc):
            aviso_sucursal = "El presupuesto pertenece a otra sucursal."

    cab_out = _json_safe(dict(cab))
    cab_out["fecha_fmt"] = _fmt_date(cab.get("fecha"))
    cab_out["vencimiento_fmt"] = _fmt_date(cab.get("vencimiento"))

    return JsonResponse(
        {
            "ok": True,
            "cabecera": cab_out,
            "lineas": lineas,
            "error_lineas": err_lineas,
            "aviso_sucursal": aviso_sucursal,
        }
    )


@tiene_permiso("ventas.presupuesto.ver")
def presupuesto_export_xlsx_view(request, codigo_movimiento: int):
    """
    Descarga Excel del documento PRE vía `ReportDefinition` `documento-presupuesto-ventas`
    (misma fuente que lista/detalle: `comp_ped` + `stockp`).
    """
    base_empresa = _base_empresa_session(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    ok, err, cab = obtener_presupuesto_cabecera(base_empresa, codigo_movimiento)
    if not ok or not cab:
        messages.error(request, err or "No se encontró el presupuesto.")
        return redirect("ventas:presupuesto_list")

    id_suc = _id_sucursal_session(request)
    if id_suc is not None and cab.get("cod_sucursal") is not None:
        if int(cab["cod_sucursal"] or 0) != int(id_suc):
            messages.warning(
                request,
                "Este presupuesto pertenece a otra sucursal; no se permite exportar.",
            )
            return redirect("ventas:presupuesto_detalle", codigo_movimiento=codigo_movimiento)

    nro_raw = str(cab.get("nro_comprobante") or "").strip() or "PRE"
    nro_safe = re.sub(r"[^\w\-.]", "_", nro_raw)[:50] or "PRE"

    payload = {
        "filters": {
            "base_empresa": base_empresa,
            "codigo_movimiento": int(codigo_movimiento),
            "nro_comprobante_archivo": nro_safe,
        }
    }

    try:
        export_service = ExportService(request.user)
        export_result = export_service.export("documento-presupuesto-ventas", payload, "xlsx")
        return export_service.get_file_response(export_result)
    except ValueError as e:
        messages.error(request, str(e))
        return redirect("ventas:presupuesto_detalle", codigo_movimiento=codigo_movimiento)
    except Exception as e:
        messages.error(request, f"No se pudo generar el archivo: {e}")
        return redirect("ventas:presupuesto_detalle", codigo_movimiento=codigo_movimiento)
