"""
Vistas API para el hub de compras (FORM-001): proveedores, sucursales, prechecks, lock OP.
Todas las lecturas pasan por legacy_db.repositories (parametrizadas).
"""
import logging
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.views.decorators.http import require_http_methods

from legacy_db.repositories import (
    PROVEEDOR_ORDER_COLUMNS,
    listar_sucursales,
    buscar_proveedores_paginado,
    count_proveedores,
    check_lock_op_proveedor,
    hay_facturas_para_op_por_imputacion,
    hay_descuentos_para_nc_descuento,
)
from legacy_db.validators import (
    PrecheckError,
    validar_cai_vigente,
    validar_obliga_oc_para_factura,
)
from legacy_db.mappers import proveedor_row_to_dto, sucursal_row_to_dto

logger = logging.getLogger(__name__)


def _base_empresa_and_user(request):
    """Obtiene base_empresa e id_usuario de sesión (paridad con compras.views)."""
    user = request.session.get("user") or {}
    base_empresa = user.get("base_empresa")
    id_usuario = user.get("id_usuario")
    return base_empresa, id_usuario


def _get_ver_proveedor_todas_sucursales(request):
    """Equivalente a Principal.ver_proveedor_sucursal = 'Si' (ve todas las sucursales)."""
    user = request.session.get("user") or {}
    valor = (user.get("ver_proveedor_sucursal") or "").strip()
    return str(valor).lower() == "si"


@require_GET
def api_proveedores_list(request):
    """
    GET: listado/búsqueda de proveedores con paginación y orden.
    Query params: q, tipo_busqueda (Comienza con|Finaliza con|Incluye texto), id_sucursal,
                  page, page_size, order_by (Nombre|Codigo|CUIT|IVA|saldo), orden (asc|desc).
    """
    base_empresa, _ = _base_empresa_and_user(request)
    if not base_empresa:
        return JsonResponse({"error": "No hay sesión o base_empresa"}, status=401)

    q = (request.GET.get("q") or "").strip()
    tipo_busqueda = request.GET.get("tipo_busqueda") or "Incluye texto"
    if tipo_busqueda not in ("Comienza con", "Finaliza con", "Incluye texto"):
        tipo_busqueda = "Incluye texto"
    id_sucursal = request.GET.get("id_sucursal")
    if id_sucursal is not None and id_sucursal != "":
        try:
            id_sucursal = int(id_sucursal)
        except (ValueError, TypeError):
            id_sucursal = None
    else:
        id_sucursal = None
    ver_todas = _get_ver_proveedor_todas_sucursales(request)
    page_size = min(int(request.GET.get("page_size") or 50), 500)
    page = max(1, int(request.GET.get("page") or 1))
    offset = (page - 1) * page_size
    order_by = request.GET.get("order_by") or "Nombre"
    if order_by not in PROVEEDOR_ORDER_COLUMNS:
        order_by = "Nombre"
    orden = (request.GET.get("orden") or "asc").lower()
    if orden not in ("asc", "desc"):
        orden = "asc"

    rows = buscar_proveedores_paginado(
        base_empresa=base_empresa,
        q=q,
        tipo_busqueda=tipo_busqueda,
        id_sucursal=id_sucursal,
        ver_proveedor_todas_sucursales=ver_todas,
        limit=page_size,
        offset=offset,
        order_by=order_by,
        orden=orden,
    )
    total = count_proveedores(
        base_empresa=base_empresa,
        q=q,
        tipo_busqueda=tipo_busqueda,
        id_sucursal=id_sucursal,
        ver_proveedor_todas_sucursales=ver_todas,
    )
    data = [proveedor_row_to_dto(r) for r in rows]
    return JsonResponse({
        "results": data,
        "total": total,
        "page": page,
        "page_size": page_size,
    })


@require_GET
def api_sucursales_list(request):
    """GET: listado de sucursales (todas o filtrado por id_sucursal)."""
    base_empresa, _ = _base_empresa_and_user(request)
    if not base_empresa:
        return JsonResponse({"error": "No hay sesión o base_empresa"}, status=401)
    id_sucursal = request.GET.get("id_sucursal")
    if id_sucursal is not None and id_sucursal != "":
        try:
            id_sucursal = int(id_sucursal)
        except (ValueError, TypeError):
            id_sucursal = None
    else:
        id_sucursal = None
    rows = listar_sucursales(base_empresa, solo_id_sucursal=id_sucursal)
    data = [sucursal_row_to_dto(r) for r in rows]
    return JsonResponse({"results": data})


@require_GET
def api_precheck(request):
    """
    GET: precheck antes de abrir una acción del hub.
    Query params: accion (keyFact|keyPorimp|keyAcuenta|keyNCDesR|keyAsignaPag), codigo_proveedor.
    Devuelve { "ok": true } o { "ok": false, "codigo": "CAI_VENCIDO"|"REQUIERE_OC"|"OP_BLOQUEADA"|"SIN_FACTURAS_IMPUTAR"|"SIN_DESCUENTOS_NC"|"SIN_PROVEEDOR" }.
    """
    base_empresa, id_usuario = _base_empresa_and_user(request)
    if not base_empresa:
        return JsonResponse({"ok": False, "codigo": "SIN_SESION"}, status=401)

    accion = (request.GET.get("accion") or "").strip()
    try:
        codigo_proveedor = int(request.GET.get("codigo_proveedor") or 0)
    except (ValueError, TypeError):
        codigo_proveedor = 0

    if accion in ("keyFact", "keyPorimp", "keyAcuenta", "keyNCDesR", "keyAsignaPag") and not codigo_proveedor:
        return JsonResponse({"ok": False, "codigo": PrecheckError.SIN_PROVEEDOR})

    if accion == "keyPorimp" or accion == "keyAcuenta":
        lock = check_lock_op_proveedor(base_empresa, codigo_proveedor, id_usuario or 0)
        if lock:
            return JsonResponse({
                "ok": False,
                "codigo": PrecheckError.OP_BLOQUEADA,
                "codigo_usuario": lock.get("codigo_usuario"),
            })
        if accion == "keyPorimp":
            if not hay_facturas_para_op_por_imputacion(base_empresa, codigo_proveedor):
                return JsonResponse({"ok": False, "codigo": PrecheckError.SIN_FACTURAS_IMPUTAR})

    if accion == "keyNCDesR":
        if not hay_descuentos_para_nc_descuento(base_empresa, codigo_proveedor):
            return JsonResponse({"ok": False, "codigo": PrecheckError.SIN_DESCUENTOS_NC})

    # Para keyFact y otras que requieren proveedor, validar CAI y obliga_oc si tenemos datos del proveedor
    if accion == "keyFact" and codigo_proveedor:
        rows = buscar_proveedores_paginado(
            base_empresa=base_empresa,
            q=str(codigo_proveedor),
            tipo_busqueda="Incluye texto",
            id_sucursal=None,
            ver_proveedor_todas_sucursales=True,
            limit=1,
            offset=0,
        )
        if rows:
            prov = rows[0]
            ok_cai, err_cai = validar_cai_vigente(prov.get("FechaCAI"))
            if not ok_cai:
                return JsonResponse({"ok": False, "codigo": err_cai})
            ok_oc, err_oc = validar_obliga_oc_para_factura(prov.get("obliga_oc_carga_comp"))
            if not ok_oc:
                return JsonResponse({"ok": False, "codigo": err_oc})

    return JsonResponse({"ok": True})


@require_GET
def api_op_lock_info(request):
    """
    GET: información de bloqueo OP para un proveedor.
    Query params: codigo_proveedor.
    Devuelve { "bloqueado": true/false, "codigo_usuario": "..." } si otro usuario tiene el lock.
    """
    base_empresa, id_usuario = _base_empresa_and_user(request)
    if not base_empresa:
        return JsonResponse({"error": "No hay sesión"}, status=401)
    try:
        codigo_proveedor = int(request.GET.get("codigo_proveedor") or 0)
    except (ValueError, TypeError):
        return JsonResponse({"bloqueado": False})
    lock = check_lock_op_proveedor(base_empresa, codigo_proveedor, id_usuario or 0)
    if lock:
        return JsonResponse({
            "bloqueado": True,
            "codigo_usuario": lock.get("codigo_usuario") or "",
        })
    return JsonResponse({"bloqueado": False})
