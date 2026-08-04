# Vistas móviles de inventario físico (conteo offline-first, conteo ciego).
from __future__ import annotations

from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse

from core.decorators import tiene_permiso
from core.utils.template_selector import get_template_for_device
from stock.services.inventario_fisico import (
    ESTADO_EN_CONTEO,
    listar_campanas_para_contador,
    listar_depositos_elegibles,
    obtener_campana,
    usuario_asignado_a_campana,
)


def _session_user(request):
    return request.session.get("user", {}) or {}


def _session_base_y_usuario(request):
    user = _session_user(request)
    base_empresa = user.get("base_empresa")
    id_usuario = user.get("id_usuario")
    if not base_empresa or not id_usuario:
        return None, None
    return base_empresa, int(id_usuario)


def _depositos_campana(campana, depositos_catalogo):
    ids = set(campana.get("depositos") or [])
    return [d for d in depositos_catalogo if d.get("id_deposito") in ids]


@tiene_permiso("stock.inventario_fisico.contar")
def conteo_mis_view(request):
    """Landing operario: campañas y depósitos asignados."""
    base_empresa, id_usuario = _session_base_y_usuario(request)
    if not base_empresa:
        return redirect("login:login")

    campanas = listar_campanas_para_contador(base_empresa, id_usuario)
    depositos = listar_depositos_elegibles(base_empresa)
    dep_por_id = {d["id_deposito"]: d for d in depositos}

    filas = []
    for campana in campanas:
        deps = _depositos_campana(campana, depositos)
        filas.append(
            {
                "campana": campana,
                "depositos": deps,
                "url_conteo": reverse("stock:conteo_campana", kwargs={"id_campana": campana["id_campana"]}),
            }
        )

    session = _session_user(request)
    puede_gestionar = False
    try:
        from core.services.administranet_permisos_usuario import tiene_permiso_administranet

        puede_gestionar = tiene_permiso_administranet(
            base_empresa,
            session.get("id_puesto"),
            "stock.inventario_fisico.gestionar",
            cod_usuario=session.get("cod_usuario"),
            nombre_puesto=session.get("nombre_puesto") or session.get("puesto"),
        )
    except Exception:
        puede_gestionar = False

    context = {
        "filas": filas,
        "nombre_usuario": session.get("nombre_usuario") or "",
        "dep_por_id": dep_por_id,
        "puede_gestionar": puede_gestionar,
        "url_campanas": reverse("stock:inventario_fisico_list"),
        "url_nueva_campana": reverse("stock:inventario_fisico_crear"),
    }
    template = get_template_for_device(request, "stock/conteo/mis_conteos.html")
    return render(request, template, context)


@tiene_permiso("stock.inventario_fisico.contar")
def conteo_campana_view(request, id_campana: int):
    """Pantalla de conteo: escáner EAN + cantidad ciega + cola offline."""
    base_empresa, id_usuario = _session_base_y_usuario(request)
    if not base_empresa:
        return redirect("login:login")

    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        raise Http404("Campaña no encontrada.")
    if campana.get("estado") != ESTADO_EN_CONTEO:
        return redirect("stock:conteo_mis")
    if not usuario_asignado_a_campana(campana, id_usuario):
        return redirect("stock:conteo_mis")

    depositos = _depositos_campana(campana, listar_depositos_elegibles(base_empresa))
    if not depositos:
        return redirect("stock:conteo_mis")

    id_deposito = request.GET.get("deposito")
    deposito_sel = None
    if id_deposito:
        try:
            did = int(id_deposito)
            deposito_sel = next((d for d in depositos if d["id_deposito"] == did), None)
        except (TypeError, ValueError):
            deposito_sel = None
    if deposito_sel is None and len(depositos) == 1:
        deposito_sel = depositos[0]

    session = _session_user(request)
    context = {
        "campana": campana,
        "depositos": depositos,
        "deposito_sel": deposito_sel,
        "nombre_usuario": session.get("nombre_usuario") or "",
        "url_prefetch": reverse("stock:api_conteo_prefetch"),
        "url_sync": reverse("stock:api_conteo_sync"),
        "url_registrados": reverse("stock:api_conteo_registrados"),
        "url_mis_conteos": reverse("stock:conteo_mis"),
    }
    template = get_template_for_device(request, "stock/conteo/conteo.html")
    return render(request, template, context)
