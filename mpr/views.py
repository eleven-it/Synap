# Módulo MPR - Vistas
import json
import logging
import traceback
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import urlencode
from django.views import View
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)

from core.services.administranet_stock import get_depositos, obtener_renglones_movimiento_bulk
from core.utils.administranet_types import str_or_default, str_codigo_manual_articulo, to_decimal_or_none, to_int_or_none

from .exceptions import MprSchemaError
from .services import (
    actualizar_componente_bom,
    actualizar_conjunto_bom,
    actualizar_operario,
    actualizar_pedidos_produccion,
    actualizar_deposito_suma_stock,
    actualizar_deposito_tipo_mpr,
    anular_componente_bom,
    anular_operario,
    crear_componente_bom,
    crear_conjunto_bom,
    crear_operario,
    ejecutar_armado,
    ejecutar_liberar_opt,
    ejecutar_opp,
    ejecutar_opp_por_componentes,
    ejecutar_reclasificacion,
    ejecutar_lote_armado,
    ejecutar_lote_armado_surtido,
    anular_lote_armado,
    listar_articulos_stock_deposito,
    listar_packs_armado_1ra,
    listar_packs_armado_catalogo,
    listar_packs_armado_surtido,
    lineas_bom_pack_1ra,
    calcular_max_packs_armado_1ra,
    confirmar_imputacion_armado,
    listar_mstock_pendientes_imputacion,
    sugerir_imputacion_fifo,
    validar_reglas_lote_armado,
    validar_reglas_lote_armado_surtido,
    validar_reglas_item_candidato_lote,
    normalizar_item_lote_armado_surtido,
    parse_cabecera_lote_armado_surtido,
    parse_lote_armado_surtido_post,
    validar_stock_agregado_lote,
    normalizar_armados_lote_json,
    LOTE_ARMADO_SURTIDO_MAX_ITEMS,
    TIPO_ART_FAB_PACK_ARMADO_SURTIDO,
    get_deposito_2da_seleccion_mpr,
    get_deposito_semi_elaborado_mpr,
    get_articulo_armado_por_bom,
    get_bom_detalle,
    get_cantidades_armadas_por_opt,
    get_cantidad_opp_por_destino_opt,
    opt_puede_armado_surtido,
    componentes_a_equivalentes_pack,
    bulk_componentes_a_equivalentes_pack,
    get_id_en_abm_por_articulo,
    bulk_id_en_abm,
    bulk_bom_detalle,
    get_lineas_armado_opt,
    construir_items_precarga_armado_desde_opt,
    get_lineas_opt_directo,
    get_op_detalle,
    get_opt_detalle,
    get_codigo_movimiento_opt,
    get_opp_componentes_disponibles,
    get_op_detalle_by_articulo,
    obtener_operario,
    set_articulo_armado_bom,
    crear_op_agrupada,
    crear_opt_multiples_articulos,
    listar_columnas_opcionales_nueva_op,
    cerrar_opt,
    listar_articulos_para_op,
    listar_bom_conjuntos,
    listar_depositos_config,
    listar_detalle_pedidos_por_articulo,
    listar_lista_produccion_agrupada,
    listar_opt_listado,
    listar_movimientos_recientes_mpr,
    listar_operarios_crud,
    docenas_desde_unidades_opt,
    bulk_cantidad_promedio_bulto,
    build_grupos_articulo_renglones_movimiento,
    build_resumen_metrica_opt,
    cantidad_opp_presentacion_du,
    lineas_texto_cantidad_opp,
    lineas_texto_cantidad_pack,
    enriquecer_lineas_opt_presentacion_pack,
    enriquecer_componentes_opp_presentacion,
    bulk_origen_demanda_por_articulo,
    aplicar_origen_demanda_a_filas,
    resumen_origen_demanda_opt,
    calcular_porcentaje_progreso_opt,
    bulk_mstock_imputacion_por_articulo,
    bulk_restante_armar_opt_listado,
    agrupar_filas_opt_listado_por_lote,
    texto_docenas_unidades,
    _etiqueta_linea_opt,
    listar_ventana_pack,
    listar_ventana_pack_unidades,
    listar_empleados_operarios,
    listar_unidades_desde_seleccion,
    obtener_pp_ped_y_stock_pack_por_articulos,
    lineas_opt_desde_formulario_unidades,
    listar_ops_para_cerrar,
    listar_opt_en_proceso,
    estado_acciones_opt,
    estado_acciones_opt_bulk,
    listar_opa_por_opt,
    listar_opp_por_opt,
    listar_pedidos_fabrica,
    contar_pedidos_fabrica,
    contar_opt_atrasadas_distintas,
    listar_opt_atrasadas_tablero,
    listar_opts_por_pedido,
    get_depositos_con_suma_stock,
    get_deposito_produccion_mpr,
    get_deposito_semi_elaborado_mpr,
    get_deposito_terminado_mpr,
    get_depositos_opp,
    reactivar_operario,
    reporte_mpr_stock,
    reporte_mpr_bajo_minimo,
    reporte_mpr_resumen_diario,
    reporte_mpr_operario_parte,
    reporte_mpr_cadena_pipeline,
    reporte_mpr_pendiente_componentes,
    reporte_mpr_trazabilidad_componente,
    reporte_mpr_brecha_demanda,
    reporte_mpr_pedidos_por_estado,
    reporte_mpr_movimientos,
    listar_tablero_por_articulo,
    listar_tablero_armado,
    calcular_kpis_tablero_armado,
    listar_armados_realizados_por_fecha,
    construir_armados_desde_post_tablero,
    transferir_stock_entre_etapas,
    TIPO_MPR_2DA_SELECCION,
    TIPO_MPR_PLANCHADO,
    TIPO_MPR_PRODUCCION,
    TIPO_MPR_SCRAP,
    TIPO_MPR_SEMI_ELABORADO,
    TIPO_MPR_TERMINADO,
)


class MprSchemaErrorMixin:
    """Inyecta en el contexto el mensaje de error de esquema (tabla/campo inexistente) para mostrar el modal en MPR."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        modal_msg = self.request.session.pop("mpr_schema_error_modal", None)
        if modal_msg:
            context["mpr_schema_error_modal"] = modal_msg
            # Registrar en log cuando se muestra el modal desde sesión (el error ocurrió en una petición anterior)
            logger.error(
                "MPR: mostrando modal de error de esquema (recuperado de sesión). Mensaje: %s",
                modal_msg,
            )
            logging.getLogger().error(
                "MPR: mostrando modal de error de esquema (recuperado de sesión). Mensaje: %s",
                modal_msg,
            )
        return context


class MprLoginRequiredMixin(LoginRequiredMixin, MprSchemaErrorMixin):
    """Mixin para MPR: exige sesión de administraNET (compatible con AdministraNETUser)."""

    def dispatch(self, request, *args, **kwargs):
        if "user" not in request.session:
            return redirect("login:login")
        if not getattr(request.user, "is_authenticated", False):
            return redirect("login:login")
        return super().dispatch(request, *args, **kwargs)


def _usuario_tiene_permiso_mpr(user, permiso: str) -> bool:
    """Comprueba permiso MPR (admin, supervisor legacy, rol administrador o permiso explícito)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if hasattr(user, "is_admin") and user.is_admin():
        return True
    if hasattr(user, "cod_usuario"):
        if (user.cod_usuario or "").strip().lower() == "supervisor":
            return True
    if hasattr(user, "roles"):
        _roles_supervisores = {"administrador", "supervisor mpr", "supervisor de producción", "supervisor de produccion"}
        if any((rol.nombre or "").strip().lower() in _roles_supervisores for rol in user.roles.all()):
            return True
    if hasattr(user, "tiene_permiso") and permiso:
        return user.tiene_permiso(permiso)
    return False


def _usuario_puede_imputar_pedido(user) -> bool:
    return _usuario_tiene_permiso_mpr(user, "mpr.imputar_armado_1ra")


def _usuario_puede_anular_envios(user) -> bool:
    """Supervisor, administrador o admin MPR."""
    return _usuario_tiene_permiso_mpr(user, "")


PERMISO_TABLERO_VER = "mpr.tablero_ver"
PERMISO_REPORTES = "mpr.reportes"


def _usuario_puede_ver_tablero_produccion(user) -> bool:
    return (
        _usuario_tiene_permiso_mpr(user, "mpr.ver")
        or _usuario_tiene_permiso_mpr(user, PERMISO_TABLERO_VER)
    )


def _usuario_puede_ver_reportes_mpr(user) -> bool:
    """Reportes: mpr.ver (escritorio) o mpr.reportes (solo analítica)."""
    return (
        _usuario_tiene_permiso_mpr(user, "mpr.ver")
        or _usuario_tiene_permiso_mpr(user, PERMISO_REPORTES)
    )


def _usuario_puede_enviar_desde_tablero(user) -> bool:
    return _usuario_tiene_permiso_mpr(user, "mpr.ver")


def _usuario_puede_consultar_partes(user) -> bool:
    return (
        _usuario_tiene_permiso_mpr(user, "mpr.ver")
        or _usuario_tiene_permiso_mpr(user, "mpr.aprobar_parte")
        or _usuario_tiene_permiso_mpr(user, "mpr.parte_operario")
    )


def _usuario_ve_todos_los_partes(user) -> bool:
    return (
        _usuario_tiene_permiso_mpr(user, "mpr.ver")
        or _usuario_tiene_permiso_mpr(user, "mpr.aprobar_parte")
    )


def _abrir_url_parte_consulta(parte: dict, session_id_usuario: int | None) -> str:
    """Destino Abrir: mi-parte si móvil del mismo usuario; si no, parte escritorio."""
    from urllib.parse import urlencode

    origen = (parte.get("origen") or "").strip()
    id_usuario = to_int_or_none(parte.get("id_usuario"))
    if (
        origen == "movil_operario"
        and session_id_usuario is not None
        and id_usuario == session_id_usuario
    ):
        return reverse("mpr:parte_movil_operario")
    fecha_str = (parte.get("fecha_str") or "").strip()
    qs = urlencode({"fecha": fecha_str}) if fecha_str else ""
    base = reverse("mpr:parte_produccion")
    return f"{base}?{qs}" if qs else base


def _context_flags_tablero(user) -> dict:
    puede_enviar = _usuario_puede_enviar_desde_tablero(user)
    # Pack|Par y Docenas|Pares: mismo umbral que envío (mpr.ver). Lectura con
    # solo mpr.tablero_ver no cambia consolidación ni unidad de presentación.
    puede_cambiar_vista = _usuario_tiene_permiso_mpr(user, "mpr.ver")
    return {
        "puede_enviar": puede_enviar,
        "puede_cambiar_vista_tablero": puede_cambiar_vista,
        "solo_lectura_tablero": _usuario_puede_ver_tablero_produccion(user) and not puede_enviar,
        "puede_anular_envios": _usuario_puede_anular_envios(user) and puede_enviar,
    }


class MprPermisoMixin:
    """Exige permiso administraNET en vista basada en clase."""

    permiso_requerido: str = ""

    def _usuario_tiene_permiso(self, user) -> bool:
        return _usuario_tiene_permiso_mpr(user, self.permiso_requerido)

    def dispatch(self, request, *args, **kwargs):
        if self.permiso_requerido and not self._usuario_tiene_permiso(
            getattr(request, "user", None)
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class MprTableroVerMixin:
    """GET tablero / actualizar / manual: exige mpr.ver OR mpr.tablero_ver."""

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_puede_ver_tablero_produccion(getattr(request, "user", None)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class MprEscritorioVerMixin(MprPermisoMixin):
    """Vistas escritorio MPR sin permiso específico: exigen mpr.ver."""

    permiso_requerido = "mpr.ver"


class MprReportesVerMixin:
    """Hub de reportes: exige mpr.ver OR mpr.reportes."""

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_puede_ver_reportes_mpr(getattr(request, "user", None)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def _get_base_empresa(request):
    """Obtiene base_empresa desde la sesión. Devuelve None si no hay empresa activa."""
    session_user = request.session.get("user", {})
    return session_user.get("base_empresa") or None


def _parse_marcas_incluidos(request) -> List[int]:
    """Normaliza marcas_incluidos desde query string (repetido o único)."""
    from stock.services.inventario_tabla import parse_inventario_filtros

    filtros = parse_inventario_filtros(
        request.GET,
        marcas_getlist=request.GET.getlist("marcas_incluidos"),
    )
    return filtros.marcas_incluidos


def _marcas_urlencode_pairs(marcas: List[int]) -> List[Tuple[str, str]]:
    return [("marcas_incluidos", str(m)) for m in marcas]


def _context_filtro_marcas(request, base_empresa: str | None) -> dict:
    """Catálogo y selección actual para el filtro tags de marcas."""
    from stock.services.inventario_tabla import listar_marcas_catalogo

    marcas = _parse_marcas_incluidos(request)
    return {
        "marcas_catalogo": listar_marcas_catalogo(base_empresa) if base_empresa else [],
        "marcas_incluidos": marcas,
    }


def _urlencode_con_marcas(params: dict, marcas: List[int]) -> str:
    from urllib.parse import urlencode

    pairs = [(k, v) for k, v in params.items() if v not in (None, "")]
    pairs.extend(_marcas_urlencode_pairs(marcas))
    return urlencode(pairs)


def _redirect_clasificacion_produccion(
    request,
    *,
    fecha_str: str = "",
    turno_id_raw: str = "",
):
    """Redirige al GET de CC. ``turno_id_raw`` se ignora (día completo)."""
    del turno_id_raw  # compat firma; el consolidado no filtra por turno
    url = reverse("mpr:clasificacion_produccion")
    qs = _urlencode_con_marcas(
        {"fecha": fecha_str},
        _parse_marcas_incluidos(request),
    )
    return redirect(f"{url}?{qs}" if qs else url)


def _lineas_borrador_desde_payload_cc(
    payload: Dict[int, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Convierte el payload del parser consolidado al shape de upsert 007."""
    lineas: List[Dict[str, Any]] = []
    for id_art, datos in (payload or {}).items():
        aid = to_int_or_none(id_art)
        if aid is None:
            continue
        semi = to_decimal_or_none((datos or {}).get("semi")) or Decimal("0")
        if semi > 0:
            lineas.append({
                "id_articulo": aid,
                "id_operario": None,
                "id_mpr_turno": None,
                "cant_semi": semi,
                "cant_2da": Decimal("0"),
                "cant_scrap": Decimal("0"),
            })
        for linea in (datos or {}).get("lineas") or []:
            if len(linea) != 4:
                continue
            oid = to_int_or_none(linea[0])
            tid = to_int_or_none(linea[1])
            destino = str(linea[2])
            cant = to_decimal_or_none(linea[3]) or Decimal("0")
            if oid is None or tid is None or cant <= 0:
                continue
            lineas.append({
                "id_articulo": aid,
                "id_operario": oid,
                "id_mpr_turno": tid,
                "cant_semi": Decimal("0"),
                "cant_2da": cant if destino == "2da" else Decimal("0"),
                "cant_scrap": cant if destino == "scrap" else Decimal("0"),
            })
    return lineas


# En formularios OPP (wizard y registrar), una docena son siempre 12 unidades (no cantidad_promedio_bulto).
UNIDADES_POR_DOCENA_OPP = 12


def _opp_cantidad_unidades_desde_post(post, id_comp: int, cod_dep: int) -> int:
    """Cantidad en unidades por celda componente × depósito: docenas × 12 + unidades sueltas."""
    doc_key = f"opp_comp_{id_comp}_dep_{cod_dep}_docenas"
    uni_key = f"opp_comp_{id_comp}_dep_{cod_dep}_unidades"
    try:
        docenas = int((post.get(doc_key) or "0").strip())
    except (ValueError, TypeError):
        docenas = 0
    try:
        unidades_sueltas = int((post.get(uni_key) or "0").strip())
    except (ValueError, TypeError):
        unidades_sueltas = 0
    docenas = max(0, docenas)
    unidades_sueltas = max(0, unidades_sueltas)
    return docenas * UNIDADES_POR_DOCENA_OPP + unidades_sueltas


def _clasificacion_cantidad_unidades_desde_post(
    post,
    id_art: int,
    prefijo: str,
    id_operario: int | None = None,
    *,
    id_turno: int | None = None,
    id_maquina: int | None = None,
) -> int:
    """Cantidad en unidades por destino de clasificación: docenas × 12 + unidades sueltas."""
    if id_operario is not None and id_turno is not None and id_maquina is not None:
        base = f"{prefijo}_{id_art}_op_{id_operario}_turno_{id_turno}_maq_{id_maquina}"
        doc_key = f"{base}_docenas"
        uni_key = f"{base}_unidades"
        legacy_key = base
    elif id_operario is not None:
        doc_key = f"{prefijo}_{id_art}_op_{id_operario}_docenas"
        uni_key = f"{prefijo}_{id_art}_op_{id_operario}_unidades"
        legacy_key = f"{prefijo}_{id_art}_op_{id_operario}"
    else:
        doc_key = f"{prefijo}_{id_art}_docenas"
        uni_key = f"{prefijo}_{id_art}_unidades"
        legacy_key = f"{prefijo}_{id_art}"
    if doc_key in post or uni_key in post:
        try:
            docenas = int((post.get(doc_key) or "0").strip())
        except (ValueError, TypeError):
            docenas = 0
        try:
            unidades_sueltas = int((post.get(uni_key) or "0").strip())
        except (ValueError, TypeError):
            unidades_sueltas = 0
        docenas = max(0, docenas)
        unidades_sueltas = max(0, unidades_sueltas)
        return docenas * UNIDADES_POR_DOCENA_OPP + unidades_sueltas
    d = to_decimal_or_none(post.get(legacy_key))
    if d is None or d <= 0:
        return 0
    return int(d)


def _clasificacion_tiene_prefijo_en_post(
    post,
    id_art: int,
    prefijo: str,
    id_operario: int | None = None,
    *,
    id_turno: int | None = None,
    id_maquina: int | None = None,
) -> bool:
    """True si el POST incluye claves docenas/unidades/legacy para el prefijo."""
    if id_operario is not None and id_turno is not None and id_maquina is not None:
        base = f"{prefijo}_{id_art}_op_{id_operario}_turno_{id_turno}_maq_{id_maquina}"
        doc_key = f"{base}_docenas"
        uni_key = f"{base}_unidades"
        legacy_key = base
    elif id_operario is not None:
        doc_key = f"{prefijo}_{id_art}_op_{id_operario}_docenas"
        uni_key = f"{prefijo}_{id_art}_op_{id_operario}_unidades"
        legacy_key = f"{prefijo}_{id_art}_op_{id_operario}"
    else:
        doc_key = f"{prefijo}_{id_art}_docenas"
        uni_key = f"{prefijo}_{id_art}_unidades"
        legacy_key = f"{prefijo}_{id_art}"
    return doc_key in post or uni_key in post or legacy_key in post


def _clasificacion_filas_desde_post(post) -> List[tuple]:
    """Tuplas (id_articulo, id_operario, id_turno, id_maquina) en POST de clasificación."""
    import re

    filas: set = set()
    for key in post:
        m = re.match(
            r"^(semi|seg2da|scrap)_(\d+)_op_(\d+)_turno_(\d+)_maq_(\d+)(?:_(docenas|unidades))?$",
            key,
        )
        if m:
            filas.add((int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))))
            continue
        m2 = re.match(
            r"^(semi|seg2da|scrap)_(\d+)_op_(\d+)(?:_(docenas|unidades))?$",
            key,
        )
        if m2:
            filas.add((int(m2.group(2)), int(m2.group(3)), 0, 0))
            continue
        m3 = re.match(r"^(semi|seg2da|scrap)_(\d+)(?:_(docenas|unidades))?$", key)
        if m3:
            filas.add((int(m3.group(2)), 0, 0, 0))
    return sorted(filas)


def _clasificacion_ids_desde_post(post) -> set:
    """Ids de artículo presentes en el POST de clasificación (docenas/unidades o legacy)."""
    import re

    ids: set = set()
    for key in post:
        m = re.match(r"^(semi|seg2da|scrap)_(\d+)(?:_(docenas|unidades))?$", key)
        if m:
            ids.add(int(m.group(2)))
    return ids


def _parte_cantidad_unidades_desde_post(post, id_art: int, id_op: int) -> int:
    """Cantidad en unidades por celda componente × operario: docenas × 12 + unidades sueltas."""
    doc_key = f"parte_art_{id_art}_op_{id_op}_docenas"
    uni_key = f"parte_art_{id_art}_op_{id_op}_unidades"
    try:
        docenas = int((post.get(doc_key) or "0").strip())
    except (ValueError, TypeError):
        docenas = 0
    try:
        unidades_sueltas = int((post.get(uni_key) or "0").strip())
    except (ValueError, TypeError):
        unidades_sueltas = 0
    docenas = max(0, docenas)
    unidades_sueltas = max(0, unidades_sueltas)
    return docenas * UNIDADES_POR_DOCENA_OPP + unidades_sueltas


def _envio_cantidad_unidades_desde_post(post, id_art: int) -> int:
    """Cantidad en pares para envío tablero: docenas enteras × 12 o pares enteros."""
    from mpr.presentacion_operativa import parse_modo_presentacion_operativa

    doc_key = f"envio_{id_art}_docenas"
    uni_key = f"envio_{id_art}_unidades"
    legacy_key = f"envio_{id_art}"
    presentacion = parse_modo_presentacion_operativa(post.get("presentacion"))
    if doc_key in post or uni_key in post:
        try:
            docenas = int((post.get(doc_key) or "0").strip())
        except (ValueError, TypeError):
            docenas = 0
        if presentacion == "docenas":
            return max(0, docenas) * UNIDADES_POR_DOCENA_OPP
        try:
            unidades_sueltas = int((post.get(uni_key) or "0").strip())
        except (ValueError, TypeError):
            unidades_sueltas = 0
        return max(0, docenas) * UNIDADES_POR_DOCENA_OPP + max(0, unidades_sueltas)
    try:
        pares = int(round(float((post.get(legacy_key) or "0").strip())))
    except (ValueError, TypeError):
        pares = 0
    return max(0, pares)


def _parte_cantidad_pares_planilla_desde_post(
    post, id_maq: int, id_art: int, id_turno: int
) -> int:
    """Pares equivalentes docenas×12 + pares sueltos (celda planilla QC)."""
    doc_key = f"parte_maq_{id_maq}_art_{id_art}_turno_{id_turno}_docenas"
    par_key = f"parte_maq_{id_maq}_art_{id_art}_turno_{id_turno}_pares"
    try:
        docenas = int((post.get(doc_key) or "0").strip())
    except (ValueError, TypeError):
        docenas = 0
    try:
        pares = int((post.get(par_key) or "0").strip())
    except (ValueError, TypeError):
        pares = 0
    return max(0, docenas) * UNIDADES_POR_DOCENA_OPP + max(0, pares)


def _parte_lineas_desde_post(post, *, modo_planilla: bool = False) -> List[Dict[str, Any]]:
    """Arma líneas del parte desde POST (E8 operario×componente o planilla QC)."""
    from decimal import Decimal
    import re as _re

    if modo_planilla or any(
        _re.match(r"^parte_maq_\d+_art_\d+_turno_\d+_", k) for k in post.keys()
    ):
        vistos: set = set()
        lineas: List[Dict[str, Any]] = []
        for key in post.keys():
            m = _re.match(
                r"^parte_maq_(\d+)_art_(\d+)_turno_(\d+)_(docenas|pares)$", key
            )
            if not m or m.group(4) != "docenas":
                continue
            id_maq = int(m.group(1))
            id_art = int(m.group(2))
            id_turno = int(m.group(3))
            clave = (id_maq, id_art, id_turno)
            if clave in vistos:
                continue
            vistos.add(clave)
            cantidad = Decimal(
                _parte_cantidad_pares_planilla_desde_post(post, id_maq, id_art, id_turno)
            )
            op_key = f"parte_maq_{id_maq}_art_{id_art}_turno_{id_turno}_op"
            try:
                id_op = int((post.get(op_key) or "0").strip())
            except (ValueError, TypeError):
                id_op = 0
            lineas.append({
                "id_articulo": id_art,
                "id_operario": id_op if id_op > 0 else None,
                "cantidad": cantidad,
                "id_mpr_maquina": id_maq,
                "maquina_nombre": (post.get(f"parte_maq_{id_maq}_nombre") or "").strip() or "-",
                "turno_id": id_turno,
            })
        return lineas

    vistos: set = set()
    lineas: List[Dict[str, Any]] = []
    for key in post.keys():
        m = _re.match(r"^parte_art_(\d+)_op_(\d+)_docenas$", key)
        if not m:
            continue
        id_art = int(m.group(1))
        id_op = int(m.group(2))
        clave = (id_art, id_op)
        if clave in vistos:
            continue
        vistos.add(clave)
        cantidad = Decimal(_parte_cantidad_unidades_desde_post(post, id_art, id_op))
        if cantidad > 0:
            lineas.append({
                "id_articulo": id_art,
                "id_operario": id_op,
                "cantidad": cantidad,
            })
    return lineas


def _texto_resumen_opt_con_desglose(resumen: dict) -> str:
    """Texto para estado o etiquetas: total agregado o packs + desglose C4."""
    if not resumen:
        return "0 docenas · 0 unidades"
    if not resumen.get("mostrar_desglose"):
        return str(resumen.get("texto_principal") or "0 docenas · 0 unidades")
    partes = [
        f"{fila['etiqueta']}: {fila['texto_docenas_unidades']}"
        for fila in (resumen.get("lineas") or [])
        if (fila.get("packs") or 0) > 0
    ]
    base = str(resumen.get("texto_principal") or "")
    if partes:
        return f"{base} ({'; '.join(partes)})"
    return base


def _opp_max_distribuible_unidades(comp: dict) -> float:
    """
    Devuelve el máximo distribuible para OPP sin caer en fallback por falsy.
    Si max_distribuible_unidades existe y vale 0, debe respetarse 0.
    """
    if not isinstance(comp, dict):
        return 0.0
    raw = comp.get("max_distribuible_unidades")
    if raw is None:
        raw = comp.get("disponible_unidades")
    try:
        return float(raw or 0)
    except (TypeError, ValueError):
        return 0.0


def _get_id_puesto(request):
    """Obtiene id_puesto desde la sesión. Devuelve None si no está definido."""
    session_user = request.session.get("user", {})
    val = session_user.get("id_puesto")
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _log_mpr_schema_error(e):
    """
    Registra un fallo de esquema MPR (tabla/columna faltante en AdministraNET).

    Para ``MprSchemaError`` no se usa traceback: es un caso operativo frecuente
    (BD sin tablas MPR o desactualizada) y ya se informa al usuario con modal.
    """
    detalle_tecnico = ""
    if getattr(e, "__cause__", None) is not None:
        detalle_tecnico = str(e.__cause__)
    msg = "MPR: tabla o campo inexistente en la base de datos. Mensaje: %s. Detalle técnico: %s" % (
        str(e),
        detalle_tecnico or "(sin excepción original)",
    )
    if isinstance(e, MprSchemaError):
        logger.warning("%s", msg)
        return
    logger.error(msg, exc_info=True)
    logging.getLogger().error(msg)


def _mpr_schema_error_redirect(request, e):
    """Guarda el error de esquema en sesión y redirige al tablero para mostrar el modal."""
    _log_mpr_schema_error(e)
    request.session["mpr_schema_error_modal"] = str(e)
    return redirect("mpr:tablero")


def _redirect_operarios_list_preserve_filters(request):
    """Tras POST (anular/reactivar), vuelve al listado conservando q y anulados si vinieron en el formulario."""
    params = {}
    q = (request.POST.get("ret_q") or "").strip()
    if q:
        params["q"] = q
    if request.POST.get("ret_anulados") == "1":
        params["anulados"] = "1"
    url = reverse("mpr:operarios_list")
    if params:
        url += "?" + urlencode(params)
    return redirect(url)


def _build_renglones_modal_map(base_empresa, opp_list, opa_list):
    """
    Mapa codigo_movimiento (str) -> { presentacion_opp_du, articulos } para modal comprobante OPT.
    ``articulos``: grupos por artículo con filas por depósito.
    """
    opp_codigos = set()
    codigos = set()
    for row in opp_list or []:
        cm = to_int_or_none(row.get("codigo_movimiento"))
        if cm is not None:
            codigos.add(cm)
            opp_codigos.add(cm)
    for row in opa_list or []:
        cm = to_int_or_none(row.get("codigo_movimiento"))
        if cm is not None:
            codigos.add(cm)
    out = {}
    if not codigos:
        return out
    renglones_por_codigo = obtener_renglones_movimiento_bulk(base_empresa, list(codigos))
    for cm in codigos:
        renglones = renglones_por_codigo.get(cm) or []
        es_opp = cm in opp_codigos
        articulos = build_grupos_articulo_renglones_movimiento(
            renglones, presentacion_opp_du=es_opp
        )
        out[str(cm)] = {
            "presentacion_opp_du": es_opp,
            "articulos": articulos,
        }
    return out


def _context_nav_movil_mpr(request) -> dict:
    """Flags para navegación inferior PWA (Mi parte opcional)."""
    user = getattr(request, "user", None)
    return {
        "mostrar_parte_movil": _usuario_tiene_permiso_mpr(user, "mpr.parte_operario"),
    }


class TableroView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Tablero de control MPR: KPIs del flujo diario y accesos rápidos."""

    template_name = "mpr/tablero.html"

    def get_template_names(self):
        from core.utils.template_selector import get_template_for_device

        return [get_template_for_device(self.request, "mpr/tablero.html")]

    def get_context_data(self, **kwargs):
        from mpr.presentacion_operativa import (
            enriquecer_resumen_tablero_kpi_presentacion,
            resolver_modo_presentacion_operativa,
        )
        from mpr.services import construir_resumen_tablero_kpi, contar_pedidos_fabrica

        context = super().get_context_data(**kwargs)
        context.update(_context_nav_movil_mpr(self.request))
        context["armado_url"] = reverse("mpr:armado") + "?modo=1ra"
        base_empresa = _get_base_empresa(self.request)
        modo_presentacion = resolver_modo_presentacion_operativa(self.request)
        context["modo_presentacion"] = modo_presentacion
        context["presentacion_query_base"] = ""
        context["unidad_cantidad_label"] = (
            "docenas" if modo_presentacion == "docenas" else "pares"
        )
        context["unidad_cantidad_label_titulo"] = (
            "Docenas" if modo_presentacion == "docenas" else "Pares"
        )

        context.setdefault("kpi_pedidos_pendientes", 0)
        context.setdefault("kpi_componentes_pendientes", 0)
        context.setdefault("kpi_pending_units", 0)
        context.setdefault("kpi_pending_units_display", 0)
        context.setdefault("kpi_pending_units_ped", 0)
        context.setdefault("kpi_pending_units_ped_display", 0)
        context.setdefault("kpi_packs_demanda", 0)
        context.setdefault("kpi_urgent_items", 0)
        context.setdefault("componentes_pendientes", [])
        context.setdefault("top_packs_pendientes", [])
        context.setdefault("top_urgencias", [])
        context.setdefault("totales_packs_stock_display", "0")
        context.setdefault("totales_packs_resta_display", "0")
        context.setdefault("totales_packs_ped_display", "0")

        if not base_empresa:
            return context

        try:
            context["kpi_pedidos_pendientes"] = contar_pedidos_fabrica(
                base_empresa, estado="Pendiente"
            )
        except MprSchemaError:
            context["kpi_pedidos_pendientes"] = 0

        try:
            resumen = construir_resumen_tablero_kpi(base_empresa)
            context.update(
                enriquecer_resumen_tablero_kpi_presentacion(resumen, modo_presentacion)
            )
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            context["mpr_schema_error_modal"] = str(e)

        return context


class InventarioMprView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Inventario MPR por etapa (misma fuente que Stock, permiso mpr.ver)."""

    template_name = "mpr/inventario.html"

    def get_template_names(self):
        from core.utils.template_selector import get_template_for_device

        return [get_template_for_device(self.request, "mpr/inventario.html")]

    def get_context_data(self, **kwargs):
        from dataclasses import replace

        from mpr.presentacion_operativa import resolver_modo_presentacion_operativa
        from stock.services.inventario_tabla import (
            build_inventario_query_string,
            build_orden_terminado_toggle_qs,
            consultar_inventario_tabla,
            etapas_para_ambito,
            listar_marcas_catalogo,
            parse_inventario_filtros,
            preparar_filas_inventario_presentacion,
        )

        context = super().get_context_data(**kwargs)
        context.update(_context_nav_movil_mpr(self.request))
        base_empresa = _get_base_empresa(self.request)
        modo_presentacion = resolver_modo_presentacion_operativa(self.request)
        context["modo_presentacion"] = modo_presentacion

        filtros = parse_inventario_filtros(
            self.request.GET,
            marcas_getlist=self.request.GET.getlist("marcas_incluidos"),
        )
        filtros = replace(filtros, presentacion=modo_presentacion, busqueda=None)

        context.update(
            {
                "base_empresa": base_empresa,
                "filas": [],
                "etapas_columnas": etapas_para_ambito(filtros.ambito),
                "filtros": filtros,
                "marcas_catalogo": [],
                "total_registros": 0,
                "filas_cargadas": 0,
                "truncado": False,
                "sin_config_mpr": False,
                "error_inventario": None,
                "inventario_query_base": build_inventario_query_string(
                    filtros, clear_search=True
                ),
                "orden_terminado_toggle_qs": build_orden_terminado_toggle_qs(filtros),
            }
        )

        if not base_empresa:
            return context

        try:
            context["marcas_catalogo"] = listar_marcas_catalogo(base_empresa)
            resultado = consultar_inventario_tabla(base_empresa, filtros)
            filas = preparar_filas_inventario_presentacion(
                resultado.get("filas") or [],
                modo_presentacion,
                base_empresa=base_empresa,
                ambito=filtros.ambito,
            )
            context["filas"] = filas
            context["etapas_columnas"] = (
                resultado.get("etapas") or etapas_para_ambito(filtros.ambito)
            )
            context["total_registros"] = resultado.get("total_registros", 0)
            context["filas_cargadas"] = resultado.get("filas_cargadas", len(filas))
            context["truncado"] = resultado.get("truncado", False)
            context["sin_config_mpr"] = resultado.get("sin_config_mpr", False)
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            context["mpr_schema_error_modal"] = str(e)
        except Exception as e:
            logger.warning("InventarioMprView %s: %s", base_empresa, e, exc_info=True)
            context["error_inventario"] = (
                "No se pudo cargar el inventario. Reintentá más tarde o contactá al administrador."
            )

        return context


# Clave de sesión para el wizard de producción
WIZARD_SESSION_KEY = "mpr_wizard"


def _limpiar_mpr_wizard(request, id_lista=None) -> None:
    """Elimina el estado del asistente. Con id_lista, solo si la sesión apunta a esa OPT."""
    wizard = request.session.get(WIZARD_SESSION_KEY)
    if not wizard:
        return
    if id_lista is not None and wizard.get("id_lista") != id_lista:
        return
    del request.session[WIZARD_SESSION_KEY]
    request.session.modified = True


class WizardProduccionView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """
    Asistente de producción: 1.Crear OPT → 2.Confirmar (crear+liberar) → 3.Crear OPP → 4.Cierre.
    El armado 1ra/2da es independiente (menú Producción → Armado). Depósito de producción (config) al confirmar.
    """

    template_name = "mpr/wizard.html"

    WIZARD_PASO_MAX = 4

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        if request.GET.get("salir"):
            self._limpiar_wizard(request)
            return redirect("mpr:tablero")
        wizard = request.session.get(WIZARD_SESSION_KEY) or {}
        # Ir al paso 3 (OPP) desde "Registrar OPP" (única opción; /opt/<id>/registrar-opp/ está deprecado). Aceptar id_lista por GET para abrir desde detalle OPT.
        id_lista_get = request.GET.get("id_lista")
        if request.GET.get("paso") == "3":
            id_lista = int(id_lista_get) if (id_lista_get and str(id_lista_get).isdigit()) else wizard.get("id_lista")
            if id_lista:
                wizard["id_lista"] = id_lista
                wizard["paso"] = 3
                request.session[WIZARD_SESSION_KEY] = wizard
                request.session.modified = True
        paso = wizard.get("paso", 1)
        # Sesiones legacy: paso 5 (cierre antiguo) o paso 4 (armado deprecado) → paso 4 cierre
        if paso >= self.WIZARD_PASO_MAX:
            wizard["paso"] = self.WIZARD_PASO_MAX
            request.session[WIZARD_SESSION_KEY] = wizard
            request.session.modified = True
            paso = self.WIZARD_PASO_MAX
        # Paso 1 del wizard = pantalla ventana-pack (demanda por artículo)
        if paso == 1:
            request.session[WIZARD_SESSION_KEY] = {"paso": 1}
            request.session.modified = True
            return redirect("mpr:ventana_pack")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        if request.POST.get("accion") == "salir":
            self._limpiar_wizard(request)
            return redirect("mpr:tablero")
        wizard = request.session.get(WIZARD_SESSION_KEY) or {}
        paso = wizard.get("paso", 1)
        if paso == 1:
            messages.info(request, "Use la pantalla de demanda (Orden de Producción de Trabajo) para crear la OPT.")
            return redirect("mpr:ventana_pack")
        if paso == 2:
            return self._post_paso2(request, base_empresa, wizard)
        if paso == 3:
            return self._post_paso3(request, base_empresa, wizard)
        if paso == 4:
            if request.POST.get("accion") == "cerrar_opt":
                id_lista = wizard.get("id_lista")
                ok = False
                if id_lista:
                    try:
                        ok, error = cerrar_opt(base_empresa, id_lista)
                        if ok:
                            messages.success(request, f"OPT {id_lista} cerrada correctamente.")
                        else:
                            messages.error(request, error or "Error al cerrar la OPT.")
                    except MprSchemaError as e:
                        return _mpr_schema_error_redirect(request, e)
                if ok:
                    _limpiar_mpr_wizard(request)
                    return redirect("mpr:opt_detail", id_lista=id_lista) if id_lista else redirect("mpr:tablero")
                return redirect("mpr:wizard")
            if request.POST.get("accion") == "finalizar":
                _limpiar_mpr_wizard(request)
                id_lista = wizard.get("id_lista")
                if id_lista:
                    return redirect("mpr:opt_detail", id_lista=id_lista)
                return redirect("mpr:tablero")
            _limpiar_mpr_wizard(request)
            id_lista = wizard.get("id_lista")
            if id_lista:
                return redirect("mpr:opt_detail", id_lista=id_lista)
            return redirect("mpr:tablero")

    def _limpiar_wizard(self, request):
        _limpiar_mpr_wizard(request)

    def _post_paso1(self, request, base_empresa, wizard):
        """Paso 1: Crear orden (solo sesión). Artículo + cantidad."""
        from django.contrib import messages
        from datetime import datetime
        id_articulo_raw = (request.POST.get("id_articulo") or "").strip()
        cantidad_raw = (request.POST.get("cantidad") or "").strip()
        try:
            id_articulo = int(id_articulo_raw) if id_articulo_raw else None
        except ValueError:
            id_articulo = None
        try:
            cantidad = int(cantidad_raw) if cantidad_raw else 0
        except ValueError:
            cantidad = 0
        if not id_articulo or cantidad <= 0:
            messages.error(request, "Seleccione un artículo e indique una cantidad positiva.")
            return redirect("mpr:wizard")
        opcional = listar_columnas_opcionales_nueva_op(base_empresa)
        id_deposito = prioridad = None
        fecha_objetivo = None
        if opcional.get("has_deposito_produccion"):
            raw = (request.POST.get("id_deposito_produccion") or "").strip()
            if raw and raw.isdigit():
                id_deposito = int(raw)
        if opcional.get("has_prioridad"):
            raw = (request.POST.get("prioridad") or "").strip()
            if raw and raw.lstrip("-").isdigit():
                prioridad = int(raw)
        if opcional.get("has_fecha_objetivo"):
            raw = (request.POST.get("fecha_objetivo") or "").strip()
            if raw:
                try:
                    fecha_objetivo = datetime.strptime(raw, "%Y-%m-%d").date()
                    if fecha_objetivo < date.today():
                        messages.error(request, "La fecha objetivo no puede ser anterior a la fecha de hoy.")
                        return redirect("mpr:wizard")
                except ValueError:
                    pass
        wizard["paso"] = 2
        wizard["id_articulo"] = id_articulo
        wizard["cantidad_pedida"] = cantidad
        wizard["id_deposito_produccion_opcional"] = id_deposito
        wizard["prioridad"] = prioridad
        wizard["fecha_objetivo"] = str(fecha_objetivo) if fecha_objetivo else None
        request.session[WIZARD_SESSION_KEY] = wizard
        request.session.modified = True
        return redirect("mpr:wizard")

    def _post_paso2(self, request, base_empresa, wizard):
        """Paso 2: Confirmar orden = crear OPT en DB + liberar (depósito desde config)."""
        from django.contrib import messages
        from datetime import datetime
        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        if not id_usuario:
            messages.error(request, "Sesión sin usuario. Inicie sesión de nuevo.")
            return redirect("mpr:wizard")
        id_articulo = wizard.get("id_articulo")
        cantidad = wizard.get("cantidad_pedida", 0)
        if not id_articulo or cantidad <= 0:
            messages.error(request, "Datos de la orden incompletos. Comience de nuevo.")
            self._limpiar_wizard(request)
            return redirect("mpr:wizard")
        deposito_produccion = get_deposito_produccion_mpr(base_empresa)
        if not deposito_produccion:
            messages.error(
                request,
                "Asigne el tipo «Producción» a un depósito en Producción → Config. Depósitos para poder confirmar la orden.",
            )
            return redirect("mpr:wizard")
        id_dep = wizard.get("id_deposito_produccion_opcional")
        prioridad = wizard.get("prioridad")
        fecha_raw = wizard.get("fecha_objetivo")
        fecha_objetivo = None
        if fecha_raw:
            try:
                fecha_objetivo = datetime.strptime(fecha_raw, "%Y-%m-%d").date()
                if fecha_objetivo < date.today():
                    messages.error(request, "La fecha objetivo no puede ser anterior a la fecha de hoy.")
                    return redirect("mpr:wizard")
            except (ValueError, TypeError):
                pass
        ok, id_lista, error = crear_op_agrupada(
            base_empresa, id_articulo, cantidad, id_usuario,
            id_deposito_produccion=id_dep, prioridad=prioridad, fecha_objetivo=fecha_objetivo,
        )
        if not ok or not id_lista:
            messages.error(request, error or "Error al crear la orden de producción.")
            return redirect("mpr:wizard")
        lineas = get_op_detalle(base_empresa, id_lista)
        if not lineas:
            messages.error(request, "No se pudieron cargar las líneas de la OPT.")
            return redirect("mpr:wizard")
        cantidad_total = int(cantidad)
        total_pendiente = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
        if cantidad_total > total_pendiente:
            cantidad_total = int(total_pendiente)
        try:
            ok_opt, codigo_mov, nro_comprobante, error_opt = ejecutar_liberar_opt(
                base_empresa, id_usuario, id_lista, lineas, cantidad_total, deposito_produccion,
            )
        except MprSchemaError as e:
            return _mpr_schema_error_redirect(request, e)
        if not ok_opt:
            msg = error_opt or "Error al liberar a producción."
            if msg and ("bytes" in msg.lower() or "formatting" in msg.lower() or "convert" in msg.lower()):
                msg = "Error al confirmar. Verifique la OPT y que exista un depósito con tipo «Producción» en Config. Depósitos."
            messages.error(request, msg)
            return redirect("mpr:wizard")
        wizard["paso"] = 3
        wizard["id_lista"] = id_lista
        wizard["id_articulo"] = id_articulo
        wizard["cantidad_pedida"] = cantidad
        request.session[WIZARD_SESSION_KEY] = wizard
        request.session.modified = True
        messages.success(request, f"OPT Nº {id_lista} creada y liberada a producción. Comprobante {nro_comprobante}.")
        return redirect("mpr:wizard")

    def _post_paso3(self, request, base_empresa, wizard):
        """Paso 3: Crear OPP. Matriz componente x depósito (unidades)."""
        from django.contrib import messages
        id_lista = wizard.get("id_lista")
        if not id_lista:
            messages.error(request, "Falta la OPT. Comience de nuevo el asistente.")
            self._limpiar_wizard(request)
            return redirect("mpr:wizard")
        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        if not id_usuario:
            messages.error(request, "Sesión sin usuario. Inicie sesión de nuevo.")
            return redirect("mpr:wizard")
        deposito_origen = get_deposito_produccion_mpr(base_empresa)
        if not deposito_origen:
            messages.error(
                request,
                "Asigne el tipo «Producción» a un depósito en Producción → Config. Depósitos.",
            )
            return redirect("mpr:wizard")
        try:
            depositos_opp = get_depositos_opp(base_empresa)
            componentes_opp = get_opp_componentes_disponibles(base_empresa, id_lista, deposito_origen)
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            request.session["mpr_schema_error_modal"] = str(e)
            return redirect("mpr:wizard")
        if not componentes_opp:
            messages.error(request, "No hay componentes para distribuir en esta OPT.")
            return redirect("mpr:wizard")
        cods_dep = [to_int_or_none(d.get("CodDeposito")) for d in depositos_opp if to_int_or_none(d.get("CodDeposito")) is not None]
        # Leer matriz: por celda docenas + unidades sueltas (docena = 12 unidades); se registra solo unidades.
        por_deposito = {}  # cod_dep -> [(id_componente, qty), ...]
        for cod_dep in cods_dep:
            if cod_dep == deposito_origen:
                continue
            por_deposito[cod_dep] = []
        comp_por_id = {to_int_or_none(c.get("id_articulo")): c for c in componentes_opp}
        id_operario_por_componente = {}
        for id_comp, comp in comp_por_id.items():
            if id_comp is None:
                continue
            disponible = int(_opp_max_distribuible_unidades(comp))
            suma_comp = 0
            for cod_dep in cods_dep:
                if cod_dep == deposito_origen:
                    continue
                qty = _opp_cantidad_unidades_desde_post(request.POST, id_comp, cod_dep)
                if qty > 0:
                    por_deposito[cod_dep].append((id_comp, qty))
                suma_comp += qty
            if suma_comp > disponible:
                codigo = str_codigo_manual_articulo(comp.get("codigo_manual") or comp.get("id_manual")) or str(id_comp)
                messages.error(request, f"Componente {codigo}: la suma por depósitos ({suma_comp}) no puede superar el disponible ({disponible} unidades).")
                return redirect("mpr:wizard")
            if suma_comp > 0:
                id_operario_raw = (request.POST.get(f"operario_{id_comp}") or "").strip()
                id_operario_comp = to_int_or_none(id_operario_raw)
                if id_operario_comp is None:
                    codigo = str_codigo_manual_articulo(comp.get("codigo_manual") or comp.get("id_manual")) or str(id_comp)
                    messages.error(request, f"Seleccione un operario para el componente {codigo}.")
                    return redirect("mpr:wizard")
                id_operario_por_componente[id_comp] = id_operario_comp
        distribucion_por_deposito = {cod_dep: list(pairs) for cod_dep, pairs in por_deposito.items() if pairs}
        if not distribucion_por_deposito:
            messages.error(request, "Indique al menos una cantidad mayor a 0 en algún depósito.")
            return redirect("mpr:wizard")
        try:
            ok, codigo_mov, nro_comp, error = ejecutar_opp_por_componentes(
                base_empresa,
                id_usuario,
                id_lista,
                deposito_origen,
                distribucion_por_deposito,
                id_operario_por_componente=id_operario_por_componente,
            )
        except MprSchemaError as e:
            return _mpr_schema_error_redirect(request, e)
        except Exception as e:
            logger.exception(
                "MPR OPP wizard: excepción en ejecutar_opp_por_componentes base_empresa=%s id_lista=%s: %s",
                base_empresa, id_lista, e,
            )
            messages.error(request, str(e))
            return redirect("mpr:wizard")
        if not ok:
            messages.error(request, error or "Error al registrar la parte de producción (OPP).")
            return redirect("mpr:wizard")
        queda_disponible = False
        try:
            componentes_despues = get_opp_componentes_disponibles(base_empresa, id_lista, deposito_origen)
            queda_disponible = any(
                int(_opp_max_distribuible_unidades(c)) > 0
                for c in (componentes_despues or [])
            )
        except Exception as e:
            logger.warning(
                "MPR OPP wizard: no se pudo recalcular disponible tras OPP base_empresa=%s id_lista=%s: %s",
                base_empresa,
                id_lista,
                e,
                exc_info=True,
            )
            queda_disponible = False
        if queda_disponible:
            wizard["paso"] = 3
            messages.success(
                request,
                "Parte de producción (OPP) registrada. Aún hay unidades disponibles para distribuir; puede registrar otra OPP con otro operario.",
            )
        else:
            wizard["paso"] = 4
            messages.success(request, "Parte de producción (OPP) registrada por depósito.")
        request.session[WIZARD_SESSION_KEY] = wizard
        request.session.modified = True
        return redirect("mpr:wizard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        wizard = self.request.session.get(WIZARD_SESSION_KEY) or {}
        paso = wizard.get("paso", 1)
        if paso >= WizardProduccionView.WIZARD_PASO_MAX:
            paso = WizardProduccionView.WIZARD_PASO_MAX
        context["wizard_paso"] = paso
        context["wizard_paso_max"] = WizardProduccionView.WIZARD_PASO_MAX
        context["base_empresa"] = base_empresa
        context["wizard"] = wizard
        context["fecha_hoy"] = date.today()
        if paso == 1:
            context["articulos"] = listar_articulos_para_op(base_empresa, limit=300)
            context["depositos"] = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(self.request))
            context["opcional_op"] = listar_columnas_opcionales_nueva_op(base_empresa)
        elif paso == 2:
            id_articulo = wizard.get("id_articulo")
            articulo_nombre = ""
            if id_articulo:
                arts = listar_articulos_para_op(base_empresa, limit=2000)
                for a in arts:
                    if a.get("id_articulo") == id_articulo:
                        articulo_nombre = (a.get("codigo_manual") or "-") + " · " + (a.get("descripcion_articulo") or "")[:50]
                        break
            context["id_articulo"] = id_articulo
            context["articulo_nombre"] = articulo_nombre or str(id_articulo)
            context["cantidad_pedida"] = wizard.get("cantidad_pedida", 0)
            context["deposito_produccion"] = get_deposito_produccion_mpr(base_empresa)
            depositos = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(self.request))
            context["deposito_produccion_nombre"] = next((d.get("NombreDeposito") or str(d.get("CodDeposito")) for d in depositos if d.get("CodDeposito") == context["deposito_produccion"]), "—")
        elif paso == 3:
            id_lista = wizard.get("id_lista")
            context["id_lista"] = id_lista
            try:
                lineas = get_opt_detalle(base_empresa, id_lista) if id_lista else []
                if id_lista and not lineas:
                    lineas = get_op_detalle(base_empresa, id_lista)
                if id_lista and not lineas:
                    lineas = get_lineas_opt_directo(base_empresa, id_lista)
                depositos_opp = get_depositos_opp(base_empresa)
                id_deposito_produccion = get_deposito_produccion_mpr(base_empresa)
                componentes_opp = (
                    get_opp_componentes_disponibles(base_empresa, id_lista, id_deposito_produccion)
                    if id_lista else []
                )
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                context["mpr_schema_error_modal"] = str(e)
                context["lineas"] = []
                context["componentes_opp"] = []
                context["depositos_opp"] = []
                context["total_pendiente"] = 0
                context["cantidad_opp_registradas"] = 0
                context["id_deposito_produccion"] = get_deposito_produccion_mpr(base_empresa)
                return context
            context["lineas"] = lineas or []
            enriquecer_componentes_opp_presentacion(componentes_opp)
            context["componentes_opp"] = componentes_opp
            context["depositos_opp"] = depositos_opp
            context["operarios"] = listar_empleados_operarios(base_empresa, busqueda=None, limit=200)
            context["total_pendiente"] = (
                sum(_opp_max_distribuible_unidades(c) for c in componentes_opp)
                if componentes_opp else sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
            )
            try:
                opp_registradas = listar_opp_por_opt(base_empresa, id_lista) if id_lista else []
                context["cantidad_opp_registradas"] = len(opp_registradas)
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                context["cantidad_opp_registradas"] = 0
            context["id_deposito_produccion"] = get_deposito_produccion_mpr(base_empresa)
        elif paso == 4:
            id_lista = wizard.get("id_lista")
            lineas = get_opt_detalle(base_empresa, id_lista) if id_lista else []
            en_proceso = (lineas[0].get("en_proceso_produccion") or "No").strip().lower() == "si" if lineas else False
            context["id_lista"] = id_lista
            total_pendiente_opp = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
            context["total_pendiente"] = total_pendiente_opp
            context["opt_en_proceso"] = en_proceso
            context["opt_cerrar_url"] = reverse("mpr:opt_cerrar", kwargs={"id_lista": id_lista}) if id_lista else None
            # Restante por armar: solo lo que está en Semi elaborado (no lo enviado a desperdicio/otros)
            hay_restante_armar = False
            if id_lista and lineas:
                cantidades_armadas = get_cantidades_armadas_por_opt(base_empresa, id_lista)
                opp_semi, _, _ = get_cantidad_opp_por_destino_opt(base_empresa, id_lista)
                all_art_ids = [l.get("id_articulo") for l in lineas if l.get("id_articulo")]
                abm_map = bulk_id_en_abm(base_empresa, all_art_ids) if all_art_ids else {}
                for l in lineas:
                    id_art = l.get("id_articulo")
                    if not id_art or not abm_map.get(id_art):
                        continue
                    cantidad_ya_armada = cantidades_armadas.get(id_art, 0)
                    cantidad_disponible_armar = opp_semi.get(id_art, 0)
                    if cantidad_disponible_armar - cantidad_ya_armada > 0:
                        hay_restante_armar = True
                        break
            context["hay_restante_armar"] = hay_restante_armar
        return context


class OpListView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """
    Demanda de producción agrupada por artículo (lista_produccion_agrupada), solo líneas con pendiente > 0.
    Distinto del listado de OPT (OptListView / opt_list.html), que incluye fases del asistente y demanda sin liberar.
    """

    template_name = "mpr/op_list.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages

            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        estado_filter = (self.request.GET.get("estado", "") or "todos").strip().lower()
        filtro_articulo_raw = (self.request.GET.get("articulo", "") or "").strip()
        id_articulo = None
        if filtro_articulo_raw.isdigit():
            id_articulo = to_int_or_none(filtro_articulo_raw)

        estado_en_proceso = None
        solo_atrasadas = False
        if estado_filter == "en_proceso":
            estado_en_proceso = "Si"
        elif estado_filter == "pendiente":
            estado_en_proceso = "No"
        elif estado_filter == "atrasadas":
            solo_atrasadas = True

        ordenes = listar_lista_produccion_agrupada(
            base_empresa,
            limit=500,
            id_articulo=id_articulo,
            estado_en_proceso=estado_en_proceso,
            solo_atrasadas=solo_atrasadas,
            excluir_filas_opt_liberadas_mstock=True,
        )
        context["base_empresa"] = base_empresa
        context["ordenes"] = ordenes
        context["filtro_estado"] = estado_filter
        context["filtro_articulo"] = filtro_articulo_raw
        return context


class OptListView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Órdenes de Producción de Trabajo (OPT). Listado con columna Estado (fase operativa / etiqueta_fase) según flujo del asistente."""

    template_name = "mpr/opt_list.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        estado_filter = (self.request.GET.get("estado", "") or "todos").strip().lower()
        origen_filter = (self.request.GET.get("origen", "") or "todos").strip().lower()
        extra_filter = (self.request.GET.get("extra", "") or "todos").strip().lower()
        vista_agrupada = (self.request.GET.get("vista", "") or "detalle").strip().lower() == "agrupada"
        estado_en_proceso = None
        solo_atrasadas = False
        if estado_filter == "en_proceso":
            estado_en_proceso = "Si"
        elif estado_filter == "pendiente":
            estado_en_proceso = "No"
        elif estado_filter == "atrasadas":
            solo_atrasadas = True
        ordenes = listar_opt_listado(
            base_empresa,
            limit=500,
            estado_en_proceso=estado_en_proceso,
            solo_atrasadas=solo_atrasadas,
        )
        ids_proceso = [
            opt.get("id_lista_produccion")
            for opt in ordenes
            if opt.get("es_opt_creada")
            and (opt.get("en_proceso_produccion") or "No").strip() == "Si"
            and opt.get("id_lista_produccion")
        ]
        estados_opt = estado_acciones_opt_bulk(base_empresa, ids_proceso)
        art_ids = [opt.get("id_articulo") for opt in ordenes if opt.get("id_articulo")]
        abm_map = bulk_id_en_abm(base_empresa, art_ids) if art_ids else {}
        puede_imputar = _usuario_puede_imputar_pedido(self.request.user)
        imputacion_map = (
            bulk_mstock_imputacion_por_articulo(base_empresa, art_ids)
            if puede_imputar and art_ids
            else {}
        )
        kpi_en_proceso = 0
        kpi_lista_cerrar = 0
        kpi_cerradas = 0
        kpi_armado_pendiente = 0
        kpi_imputacion_articulos = len(imputacion_map)
        # Enriquecer cada fila: pendiente del pedido, fase, progreso y acciones
        for opt in ordenes:
            id_lista = opt.get("id_lista_produccion")
            en_proceso = (opt.get("en_proceso_produccion") or "No").strip() == "Si"
            es_opt_creada = opt.get("es_opt_creada", False)
            cantidad_pedida = opt.get("cantidad_pedida") or 0
            cantidad_pendiente_prod = opt.get("cantidad_pendiente_prod") or 0
            cantidad_asignada_opt = opt.get("cantidad_asignada_opt")
            if cantidad_asignada_opt is not None and int(cantidad_asignada_opt or 0) > 0:
                opt["cantidad_pendiente_mostrar"] = max(0, cantidad_pedida - int(cantidad_asignada_opt))
            else:
                opt["cantidad_pendiente_mostrar"] = cantidad_pendiente_prod
            opt["porcentaje_progreso"] = calcular_porcentaje_progreso_opt(
                en_proceso, int(cantidad_pendiente_prod or 0)
            )
            opt["accion_principal"] = None
            opt["puede_crear_opp"] = False
            opt["puede_cerrar"] = False
            opt["mostrar_link_armado"] = False
            opt["tiene_armado_pendiente"] = False
            opt["restante_armar"] = 0
            opt["mostrar_link_imputacion"] = False
            opt["imputacion_url"] = None
            if id_lista:
                opt["detail_url"] = reverse("mpr:opt_detail", kwargs={"id_lista": id_lista})
                opt["crear_opp_url"] = reverse("mpr:parte_produccion")
                opt["cerrar_url"] = reverse("mpr:opt_cerrar", kwargs={"id_lista": id_lista})
            else:
                opt["detail_url"] = (
                    reverse("mpr:opt_detail", kwargs={"id_lista": 0})
                    + f"?articulo={opt.get('id_articulo')}"
                )
                opt["crear_opp_url"] = None
                opt["cerrar_url"] = None
            id_art = opt.get("id_articulo")
            opt["tiene_bom_armable"] = bool(id_art and abm_map.get(id_art))
            opt["armado_url"] = reverse("mpr:armado") + "?modo=1ra"
            if not es_opt_creada:
                opt["etiqueta_fase"] = "Demanda"
                opt["fase_clave"] = "demanda"
            elif not en_proceso:
                if int(cantidad_pendiente_prod or 0) == 0:
                    opt["etiqueta_fase"] = "Cerrada"
                    opt["fase_clave"] = "cerrada"
                    kpi_cerradas += 1
                else:
                    opt["etiqueta_fase"] = "Pendiente"
                    opt["fase_clave"] = "pendiente"
            elif id_lista is None:
                opt["etiqueta_fase"] = "Pendiente"
                opt["fase_clave"] = "pendiente"
            else:
                kpi_en_proceso += 1
                id_lista_int = int(id_lista)
                estado = estados_opt.get(
                    id_lista_int,
                    {"puede_cerrar": False, "puede_crear_opp": False},
                )
                opt["puede_cerrar"] = bool(estado.get("puede_cerrar"))
                opt["puede_crear_opp"] = bool(estado.get("puede_crear_opp"))
                if estado.get("puede_cerrar"):
                    opt["etiqueta_fase"] = "Lista para cerrar"
                    opt["fase_clave"] = "lista_cerrar"
                    opt["accion_principal"] = "cerrar"
                    kpi_lista_cerrar += 1
                elif estado.get("puede_crear_opp"):
                    opt["etiqueta_fase"] = "En producción (OPP pendiente)"
                    opt["fase_clave"] = "en_produccion_opp"
                    opt["accion_principal"] = "crear_opp"
                else:
                    opt["etiqueta_fase"] = "En producción"
                    opt["fase_clave"] = "en_produccion"
        origen_map = bulk_origen_demanda_por_articulo(base_empresa, art_ids)
        aplicar_origen_demanda_a_filas(ordenes, origen_map)
        restante_por_lista = bulk_restante_armar_opt_listado(
            base_empresa, ordenes, abm_map
        )
        for opt in ordenes:
            id_lista = opt.get("id_lista_produccion")
            id_art = opt.get("id_articulo")
            if id_lista and id_art and abm_map.get(id_art):
                rest = int(
                    restante_por_lista.get(f"{int(id_lista)}:{int(id_art)}", 0) or 0
                )
                if int(opt.get("cantidad_pendiente_prod") or 0) <= 0 and rest > 0:
                    opt["tiene_armado_pendiente"] = True
                    opt["restante_armar"] = rest
                    opt["mostrar_link_armado"] = True
                    params_arm = {"modo": "1ra", "id_lista": int(id_lista)}
                    if id_art:
                        params_arm["id_articulo"] = int(id_art)
                    opt["armado_url"] = (
                        reverse("mpr:armado") + "?" + urlencode(params_arm)
                    )
            if puede_imputar and id_art:
                imp = imputacion_map.get(int(id_art))
                if imp:
                    params = {"codigo_movimiento": imp["codigo_movimiento"]}
                    if imp.get("id_lote_armado"):
                        params["id_lote_armado"] = imp["id_lote_armado"]
                    opt["imputacion_url"] = (
                        reverse("mpr:imputacion_armado_1ra")
                        + "?"
                        + urlencode(params)
                    )
                    opt["mostrar_link_imputacion"] = True
                    opt["mstock_pendiente_imputar"] = imp.get("cantidad_pendiente_imputar")
        kpi_armado_pendiente = sum(
            1 for o in ordenes if o.get("tiene_armado_pendiente")
        )
        if origen_filter and origen_filter != "todos":
            filtro_map = {
                "pedido": "Pedido",
                "reserva": "Reserva",
                "pedido_reserva": "Pedido + reserva",
            }
            etiqueta_obj = filtro_map.get(origen_filter)
            if etiqueta_obj:
                ordenes = [
                    o
                    for o in ordenes
                    if (o.get("origen_demanda_etiqueta") or "") == etiqueta_obj
                ]
        if extra_filter == "armado_pendiente":
            ordenes = [o for o in ordenes if o.get("tiene_armado_pendiente")]
        elif extra_filter == "imputacion_pendiente":
            ordenes = [o for o in ordenes if o.get("mostrar_link_imputacion")]
        if vista_agrupada:
            ordenes = agrupar_filas_opt_listado_por_lote(ordenes)
        mstock_pendientes = 0
        if _usuario_puede_imputar_pedido(self.request.user):
            try:
                mstock_pendientes = len(
                    listar_mstock_pendientes_imputacion(base_empresa, filtros=None)
                )
            except Exception:
                mstock_pendientes = 0
        context["base_empresa"] = base_empresa
        context["ordenes"] = ordenes
        context["filtro_estado"] = estado_filter
        context["filtro_origen"] = origen_filter
        context["filtro_extra"] = extra_filter
        context["vista_agrupada"] = vista_agrupada
        context["kpi_en_proceso"] = kpi_en_proceso
        context["kpi_lista_cerrar"] = kpi_lista_cerrar
        context["kpi_cerradas"] = kpi_cerradas
        context["kpi_armado_pendiente"] = kpi_armado_pendiente
        context["kpi_imputacion_articulos"] = kpi_imputacion_articulos
        context["mstock_imputacion_pendientes"] = mstock_pendientes
        context["puede_imputar_pedido"] = _usuario_puede_imputar_pedido(
            self.request.user
        )
        context["armado_url"] = reverse("mpr:armado") + "?modo=1ra"
        context["imputacion_pedido_url"] = reverse("mpr:imputacion_armado_1ra")
        return context


class OptDetailView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Detalle de una OPT por id_lista_produccion (incluye todas las líneas si es OPT agrupada)."""

    template_name = "mpr/opt_detail.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_lista = kwargs.get("id_lista", 0)
        id_articulo_param = self.request.GET.get("articulo", "").strip()
        id_articulo = int(id_articulo_param) if id_articulo_param.isdigit() else None

        if id_lista and id_lista != 0:
            lineas = get_opt_detalle(base_empresa, id_lista)
            if not lineas:
                lineas = get_op_detalle(base_empresa, id_lista)
            opt_numero = id_lista
        elif id_articulo:
            lineas = get_op_detalle_by_articulo(base_empresa, id_articulo)
            opt_numero = f"Art. {id_articulo}"
        else:
            lineas = []
            opt_numero = None

        if not lineas:
            raise Http404("OPT no encontrada o sin líneas.")

        total_pedida = sum(l["cantidad_pedida"] for l in lineas)
        total_pendiente = sum(l["cantidad_pendiente_prod"] for l in lineas)
        hay_disponible_opp = False
        if id_lista and id_lista != 0:
            try:
                deposito_origen = get_deposito_produccion_mpr(base_empresa)
                componentes_opp = get_opp_componentes_disponibles(base_empresa, id_lista, deposito_origen)
                hay_disponible_opp = any(
                    _opp_max_distribuible_unidades(c) > 0 for c in (componentes_opp or [])
                )
            except Exception:
                hay_disponible_opp = False
        # Estado del flujo: Pedida → En producción → Producida (OPP) → Pendiente 0 → Cerrado
        en_proceso = (lineas[0].get("en_proceso_produccion") or "No").strip().lower() == "si"
        paso_pedida = True
        paso_cerrado = not en_proceso
        # Si la OPT está cerrada, mostrar todos los pasos como cumplidos (persistencia del estado al cierre)
        if paso_cerrado:
            paso_liberada_opt = True
            paso_producida_opp = True
            paso_pendiente_cero = True
        else:
            paso_liberada_opt = en_proceso or (not hay_disponible_opp)
            paso_producida_opp = not hay_disponible_opp
            paso_pendiente_cero = not hay_disponible_opp

        # Cantidades ya armadas por artículo (solo si OPT con id_lista)
        cantidades_armadas = {}
        opp_semi_por_articulo = {}
        opp_otros_por_articulo = {}
        if id_lista and id_lista != 0:
            cantidades_armadas = get_cantidades_armadas_por_opt(base_empresa, id_lista)
            opp_semi_por_articulo, opp_otros_por_articulo, opp_desperdicio_por_articulo = get_cantidad_opp_por_destino_opt(base_empresa, id_lista)

        all_art_ids = [l.get("id_articulo") for l in lineas if l.get("id_articulo")]
        bulto_por_articulo = (
            bulk_cantidad_promedio_bulto(base_empresa, all_art_ids) if all_art_ids else {}
        )
        abm_map = bulk_id_en_abm(base_empresa, all_art_ids) if all_art_ids else {}
        pack_ids_armado = [l.get("id_articulo") for l in lineas if l.get("id_articulo")]
        equiv_semi = bulk_componentes_a_equivalentes_pack(
            base_empresa, pack_ids_armado, opp_semi_por_articulo
        )
        equiv_otros = bulk_componentes_a_equivalentes_pack(
            base_empresa, pack_ids_armado, opp_otros_por_articulo
        )
        lineas_with_armado = []
        for l in lineas:
            id_art = l.get("id_articulo")
            cantidad_pendiente_prod = l.get("cantidad_pendiente_prod") or 0
            cantidad_ya_armada = cantidades_armadas.get(id_art, 0) if id_art else 0
            # Cantidad comprometida en esta OPT: si existe cantidad_asignada_opt (guardada al crear la OPT), usarla;
            # si no, usar pendiente + ya armado (para OPTs creadas antes de tener la columna o sin columna).
            cantidad_asignada = l.get("cantidad_asignada_opt")
            if cantidad_asignada is not None and int(cantidad_asignada or 0) > 0:
                cantidad_en_esta_opt = int(cantidad_asignada)
            else:
                cantidad_en_esta_opt = cantidad_pendiente_prod + cantidad_ya_armada
            l["cantidad_en_esta_opt"] = cantidad_en_esta_opt
            # OPP guarda por componente (medias); convertir a equivalente en packs para esta línea (BOM)
            cantidad_disponible_armar = equiv_semi.get(id_art, 0) if id_art else 0
            cantidad_a_otros_dep = equiv_otros.get(id_art, 0) if id_art else 0
            l["cantidad_a_otros_depositos"] = cantidad_a_otros_dep if id_art and abm_map.get(id_art) else None
            l["cantidad_ya_armada"] = cantidad_ya_armada if id_art and abm_map.get(id_art) else None
            cantidad_pedida = l.get("cantidad_pedida") or 0
            # Restante por armar: solo lo que está en Semi elaborado y aún no se armó (no se cuenta lo enviado a desperdicio/otros)
            cantidad_restante_armar = max(0, cantidad_disponible_armar - cantidad_ya_armada)
            l["cantidad_restante_armar"] = cantidad_restante_armar if id_art and abm_map.get(id_art) else None
            id_en_abm = abm_map.get(id_art) if id_art else None
            if id_en_abm:
                lineas_with_armado.append({
                    "linea": l,
                    "id_en_abm": id_en_abm,
                    "cantidad_pendiente": cantidad_pendiente_prod,
                    "cantidad_pedida": cantidad_pedida,
                    "cantidad_ya_armada": cantidad_ya_armada,
                    "cantidad_restante_armar": cantidad_restante_armar,
                    "cantidad_disponible_armar": cantidad_disponible_armar,
                    "cantidad_a_otros_depositos": cantidad_a_otros_dep,
                })
        # Armado habilitado solo si Pendiente 0 y hay al menos una línea con restante por armar (solo Semi elaborado)
        hay_restante_armar = any(item["cantidad_restante_armar"] > 0 for item in lineas_with_armado)
        # Equivalentes en packs para mostrar (OPP está en unidades de componente; 1 pack = N medias)
        primer_pack_id = lineas[0].get("id_articulo") if lineas else None
        total_a_desperdicio_otro = (
            equiv_otros.get(primer_pack_id, 0) if primer_pack_id else 0
        )
        hay_unidades_a_desperdicio_otro = total_a_desperdicio_otro > 0
        # Enriquecer cada línea con datos de armado para la tabla (ya asignados arriba en l)
        armado_por_articulo = {
            item["linea"]["id_articulo"]: {
                "cantidad_ya_armada": item["cantidad_ya_armada"],
                "cantidad_restante_armar": item["cantidad_restante_armar"],
                "cantidad_a_otros_depositos": item["cantidad_a_otros_depositos"],
            }
            for item in lineas_with_armado
        }
        for l in lineas:
            d = armado_por_articulo.get(l.get("id_articulo"))
            if d:
                l["cantidad_ya_armada"] = d["cantidad_ya_armada"]
                l["cantidad_restante_armar"] = d["cantidad_restante_armar"]
                l["cantidad_a_otros_depositos"] = d.get("cantidad_a_otros_depositos")
            if l.get("cantidad_en_esta_opt") is None:
                l["cantidad_en_esta_opt"] = (l.get("cantidad_pendiente_prod") or 0) + (l.get("cantidad_ya_armada") or 0)
        total_en_esta_opt = sum(l.get("cantidad_en_esta_opt") or 0 for l in lineas)
        pendiente_del_pedido = max(0, total_pedida - total_en_esta_opt)
        art_ids = [l.get("id_articulo") for l in lineas if l.get("id_articulo")]
        origen_map = bulk_origen_demanda_por_articulo(base_empresa, art_ids)
        aplicar_origen_demanda_a_filas(lineas, origen_map)
        origen_demanda_opt = resumen_origen_demanda_opt(lineas)
        enriquecer_lineas_opt_presentacion_pack(lineas, bulto_por_articulo)

        def _lineas_metrica(campo: str):
            items = []
            for lin in lineas:
                id_art = lin.get("id_articulo")
                try:
                    packs = max(0, int(lin.get(campo) or 0))
                except (TypeError, ValueError):
                    packs = 0
                if campo == "pendiente_del_pedido_linea":
                    packs = max(
                        0,
                        int(lin.get("cantidad_pedida") or 0) - int(lin.get("cantidad_en_esta_opt") or 0),
                    )
                items.append({
                    "etiqueta": _etiqueta_linea_opt(lin),
                    "packs": packs,
                    "bulto": bulto_por_articulo.get(id_art, 0),
                })
            return items

        resumen_demanda = build_resumen_metrica_opt(total_pedida, _lineas_metrica("cantidad_pedida"))
        resumen_en_opt = build_resumen_metrica_opt(total_en_esta_opt, _lineas_metrica("cantidad_en_esta_opt"))
        resumen_pendiente_opp = build_resumen_metrica_opt(
            total_pendiente, _lineas_metrica("cantidad_pendiente_prod")
        )
        resumen_pendiente_pedido = build_resumen_metrica_opt(
            pendiente_del_pedido,
            _lineas_metrica("pendiente_del_pedido_linea"),
        )

        if lineas_with_armado and id_lista:
            for item in lineas_with_armado:
                id_art_linea = item["linea"].get("id_articulo")
                params_arm = {"modo": "1ra", "id_lista": int(id_lista)}
                if id_art_linea:
                    params_arm["id_articulo"] = int(id_art_linea)
                item["armado_url"] = reverse("mpr:armado") + "?" + urlencode(params_arm)

        # Porcentaje según 5 pasos obligatorios del timeline OPT
        if paso_cerrado:
            porcentaje_estado = 100
        else:
            num_pasos = sum([
                paso_pedida,
                paso_liberada_opt,
                paso_producida_opp,
                paso_pendiente_cero,
                paso_cerrado,
            ])
            porcentaje_estado = min(100, round(100 * num_pasos / 5)) if num_pasos else 0

        if paso_cerrado:
            estado_actual_texto = "OPT cerrada."
        elif (not hay_disponible_opp) and en_proceso:
            estado_actual_texto = "Completada (pendiente OPP 0). Puede cerrar la OPT."
        elif not hay_disponible_opp:
            estado_actual_texto = "Producida (OPP). Pendiente OPP: 0 docenas · 0 unidades."
        else:
            prefijo = (
                "En producción. Pendiente OPP (por producir en esta OPT): "
                if en_proceso
                else "En producción. Pendiente OPP: "
            )
            estado_actual_texto = prefijo + _texto_resumen_opt_con_desglose(resumen_pendiente_opp) + "."

        context["lineas_with_armado"] = lineas_with_armado
        context["hay_restante_armar"] = hay_restante_armar
        context["hay_unidades_a_desperdicio_otro"] = hay_unidades_a_desperdicio_otro
        context["total_a_desperdicio_otro"] = total_a_desperdicio_otro
        context["base_empresa"] = base_empresa
        context["id_lista"] = id_lista
        context["opt_numero"] = opt_numero
        context["lineas"] = lineas
        context["total_pedida"] = total_pedida
        context["total_pendiente"] = total_pendiente
        context["hay_disponible_opp"] = hay_disponible_opp
        context["total_en_esta_opt"] = total_en_esta_opt
        context["pendiente_del_pedido"] = pendiente_del_pedido
        context["resumen_demanda"] = resumen_demanda
        context["resumen_en_opt"] = resumen_en_opt
        context["resumen_pendiente_opp"] = resumen_pendiente_opp
        context["resumen_pendiente_pedido"] = resumen_pendiente_pedido
        context["origen_demanda_opt"] = origen_demanda_opt
        context["porcentaje_completado"] = porcentaje_estado
        context["estado_actual_texto"] = estado_actual_texto
        context["paso_pedida"] = paso_pedida
        context["paso_liberada_opt"] = paso_liberada_opt
        context["paso_producida_opp"] = paso_producida_opp
        context["paso_pendiente_cero"] = paso_pendiente_cero
        context["paso_cerrado"] = paso_cerrado
        context["en_proceso"] = en_proceso
        context["mostrar_tarjeta_armado_surtido"] = False
        context["puede_armado_surtido"] = False
        context["motivo_armado_surtido_bloqueado"] = ""
        context["armado_url"] = (
            reverse("mpr:armado") + f"?modo=1ra&id_lista={id_lista}"
            if id_lista
            else reverse("mpr:armado") + "?modo=1ra"
        )
        # Codigo de movimiento para imprimir comprobante PDF (si la OPT fue liberada)
        codigo_movimiento = None
        if id_lista and id_lista != 0:
            codigo_movimiento = get_codigo_movimiento_opt(base_empresa, id_lista)
        context["codigo_movimiento"] = codigo_movimiento
        # OPP ya registradas para esta OPT (solo si OPT con id_lista)
        opp_registradas = []
        if id_lista and id_lista != 0:
            try:
                opp_registradas = listar_opp_por_opt(base_empresa, id_lista)
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                opp_registradas = []
        context["opp_registradas"] = opp_registradas
        # OPAs (armados) ya registrados para esta OPT
        opas_registradas = []
        if id_lista and id_lista != 0:
            try:
                opas_registradas = listar_opa_por_opt(base_empresa, id_lista)
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                opas_registradas = []
        context["opas_registradas"] = opas_registradas
        context["renglones_por_movimiento"] = _build_renglones_modal_map(
            base_empresa, opp_registradas, opas_registradas
        )
        # Métricas de armado en tabla: solo cuando OPP de esta OPT está completo (evita 0/0 confuso)
        tiene_lineas_armables = bool(lineas_with_armado)
        context["tiene_lineas_armables"] = tiene_lineas_armables
        context["mostrar_metricas_armado_opt"] = (
            tiene_lineas_armables and not hay_disponible_opp
        )
        context["mostrar_aviso_armado_pendiente_opp"] = (
            tiene_lineas_armables and hay_disponible_opp and en_proceso
        )
        return context


class RegistrarOppView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """
    DEPRECATED (E6): pendiente eliminación hasta migrar wizard paso 3.
    Usar RegistrarParteProduccionView / ParteProduccionView en su lugar.

    Pantalla Registrar OPP: matriz artículo x depósito (Semi Elaborado, Scrap, 2da Selección).
    """

    template_name = "mpr/registrar_opp.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        id_lista = kwargs.get("id_lista", 0)
        if id_lista == 0:
            raise Http404("Indique la OPT por id_lista.")
        try:
            lineas = get_opt_detalle(base_empresa, id_lista)
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            request.session["mpr_schema_error_modal"] = str(e)
            return redirect("mpr:opt_detail", id_lista=id_lista)
        if not lineas:
            raise Http404("OPT no encontrada o sin líneas.")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_lista = kwargs.get("id_lista", 0)
        try:
            lineas = get_opt_detalle(base_empresa, id_lista)
            depositos_opp = get_depositos_opp(base_empresa)
            id_deposito_produccion = get_deposito_produccion_mpr(base_empresa)
            componentes_opp = get_opp_componentes_disponibles(base_empresa, id_lista, id_deposito_produccion)
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            context["mpr_schema_error_modal"] = str(e)
            context["lineas"] = []
            context["componentes_opp"] = []
            context["depositos_opp"] = []
            context["total_pendiente"] = 0
            context["cantidad_opp_registradas"] = 0
        else:
            context["lineas"] = lineas
            enriquecer_componentes_opp_presentacion(componentes_opp)
            context["componentes_opp"] = componentes_opp
            context["depositos_opp"] = depositos_opp
            context["total_pendiente"] = (
                sum(_opp_max_distribuible_unidades(c) for c in componentes_opp)
                if componentes_opp else sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
            )
            try:
                opp_registradas = listar_opp_por_opt(base_empresa, id_lista)
                context["cantidad_opp_registradas"] = len(opp_registradas)
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                context["cantidad_opp_registradas"] = 0
        context["base_empresa"] = base_empresa
        context["id_lista"] = id_lista
        context["opt_numero"] = id_lista
        context["id_deposito_produccion"] = get_deposito_produccion_mpr(base_empresa)
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        id_lista = kwargs.get("id_lista", 0)
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:opt_detail", id_lista=id_lista)
        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        if not id_usuario:
            messages.error(request, "Sesión sin usuario. Inicie sesión de nuevo.")
            return redirect("mpr:registrar_opp", id_lista=id_lista)
        deposito_origen = get_deposito_produccion_mpr(base_empresa)
        if not deposito_origen:
            messages.error(
                request,
                "Asigne el tipo «Producción» a un depósito en Producción → Config. Depósitos.",
            )
            return redirect("mpr:registrar_opp", id_lista=id_lista)
        try:
            depositos_opp = get_depositos_opp(base_empresa)
            componentes_opp = get_opp_componentes_disponibles(base_empresa, id_lista, deposito_origen)
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            request.session["mpr_schema_error_modal"] = str(e)
            return redirect("mpr:registrar_opp", id_lista=id_lista)
        if not componentes_opp:
            messages.error(request, "No hay componentes para distribuir en esta OPT.")
            return redirect("mpr:opt_detail", id_lista=id_lista)
        cods_dep = [to_int_or_none(d.get("CodDeposito")) for d in depositos_opp if to_int_or_none(d.get("CodDeposito")) is not None]
        por_deposito = {cod_dep: [] for cod_dep in cods_dep if cod_dep != deposito_origen}
        comp_por_id = {to_int_or_none(c.get("id_articulo")): c for c in componentes_opp}
        for id_comp, comp in comp_por_id.items():
            if id_comp is None:
                continue
            for cod_dep in cods_dep:
                if cod_dep == deposito_origen:
                    continue
                qty = _opp_cantidad_unidades_desde_post(request.POST, id_comp, cod_dep)
                if qty > 0:
                    por_deposito[cod_dep].append((id_comp, qty))
        id_operario_por_componente = {}
        for id_comp, comp in comp_por_id.items():
            if id_comp is None:
                continue
            disponible = int(_opp_max_distribuible_unidades(comp))
            suma_comp = sum(
                q for cod_dep in por_deposito
                for (cid, q) in por_deposito[cod_dep]
                if cid == id_comp
            )
            if suma_comp > disponible:
                codigo = str_codigo_manual_articulo(comp.get("codigo_manual") or comp.get("id_manual")) or str(id_comp)
                messages.error(request, f"Componente {codigo}: la suma por depósitos ({suma_comp}) no puede superar el disponible ({disponible} unidades).")
                return redirect("mpr:registrar_opp", id_lista=id_lista)
            if suma_comp > 0:
                id_operario_raw = (request.POST.get(f"operario_{id_comp}") or "").strip()
                id_operario_comp = to_int_or_none(id_operario_raw)
                if id_operario_comp is None:
                    codigo = str_codigo_manual_articulo(comp.get("codigo_manual") or comp.get("id_manual")) or str(id_comp)
                    messages.error(request, f"Seleccione un operario para el componente {codigo}.")
                    return redirect("mpr:registrar_opp", id_lista=id_lista)
                id_operario_por_componente[id_comp] = id_operario_comp
        distribucion_por_deposito = {cod_dep: list(pairs) for cod_dep, pairs in por_deposito.items() if pairs}
        if not distribucion_por_deposito:
            messages.error(request, "Indique al menos una cantidad mayor a 0 en algún depósito.")
            return redirect("mpr:registrar_opp", id_lista=id_lista)
        try:
            ok, codigo_mov, nro_comp, error = ejecutar_opp_por_componentes(
                base_empresa,
                id_usuario,
                id_lista,
                deposito_origen,
                distribucion_por_deposito,
                id_operario_por_componente=id_operario_por_componente,
            )
        except MprSchemaError as e:
            return _mpr_schema_error_redirect(request, e)
        if not ok:
            messages.error(request, error or "Error al registrar la parte de producción (OPP).")
            return redirect("mpr:registrar_opp", id_lista=id_lista)
        messages.success(request, "Parte de producción (OPP) registrada por depósito.")
        return redirect("mpr:opt_detail", id_lista=id_lista)


class ArmadoOptView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """Deprecado: redirige a Armado 1ra unificado."""

    def get(self, request, *args, **kwargs):
        from django.contrib import messages
        messages.info(request, "Use Armado 1ra desde el menú de Producción.")
        return _redirect_armado("1ra")

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


class _ArmadoOptViewLegacy(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Legacy — armado multi-artículo desde detalle OPT (deprecado)."""

    template_name = "mpr/armado_opt.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:opt_list")
        id_lista = kwargs.get("id_lista")
        if not id_lista:
            raise Http404("OPT no indicada.")
        try:
            lineas_armado = get_lineas_armado_opt(base_empresa, id_lista)
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            request.session["mpr_schema_error_modal"] = str(e)
            return redirect("mpr:opt_detail", id_lista=id_lista)
        if not lineas_armado:
            from django.contrib import messages
            messages.info(request, "No hay artículos armables para esta OPT.")
            return redirect("mpr:opt_detail", id_lista=id_lista)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_lista = self.kwargs.get("id_lista")
        lineas_armado = get_lineas_armado_opt(base_empresa, id_lista)
        context["id_lista"] = id_lista
        context["opt_numero"] = id_lista
        context["lineas_armado"] = lineas_armado
        context["id_deposito_semi"] = get_deposito_semi_elaborado_mpr(base_empresa)
        context["id_deposito_terminado"] = get_deposito_terminado_mpr(base_empresa)
        depositos_config = listar_depositos_config(base_empresa)
        id_semi = context["id_deposito_semi"]
        id_term = context["id_deposito_terminado"]
        context["nombre_deposito_semi"] = next(
            (d.get("NombreDeposito") or str(d.get("CodDeposito")) for d in depositos_config if d.get("CodDeposito") == id_semi),
            "Semi Elaborado",
        )
        context["nombre_deposito_terminado"] = next(
            (d.get("NombreDeposito") or str(d.get("CodDeposito")) for d in depositos_config if d.get("CodDeposito") == id_term),
            "Terminado",
        )
        context["operarios"] = listar_empleados_operarios(base_empresa, busqueda=None, limit=200)
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:opt_list")
        id_lista = kwargs.get("id_lista")
        if not id_lista:
            return redirect("mpr:opt_list")
        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        if not id_usuario:
            messages.error(request, "Usuario no identificado en sesión.")
            return redirect("mpr:armado_opt", id_lista=id_lista)
        lineas_armado = get_lineas_armado_opt(base_empresa, id_lista)
        if not lineas_armado:
            messages.error(request, "No hay artículos armables para esta OPT.")
            return redirect("mpr:opt_detail", id_lista=id_lista)
        deposito_semi = get_deposito_semi_elaborado_mpr(base_empresa)
        deposito_terminado = get_deposito_terminado_mpr(base_empresa)
        if not deposito_semi or not deposito_terminado:
            messages.error(request, "Configure depósitos Semi Elaborado y Terminado en Config. Depósitos.")
            return redirect("mpr:armado_opt", id_lista=id_lista)
        cantidades = []
        for linea in lineas_armado:
            id_art = linea.get("id_articulo")
            key = f"armar_cantidad_{id_art}"
            try:
                qty = int((request.POST.get(key) or "0").strip())
            except (TypeError, ValueError):
                qty = 0
            qty = max(0, qty)
            if qty > 0:
                id_operario_linea = to_int_or_none(request.POST.get(f"operario_armado_{id_art}"))
                cantidades.append((linea, qty, id_operario_linea))
        if not cantidades:
            messages.error(request, "Indique al menos una cantidad mayor a 0 en algún pack para ejecutar el armado.")
            return redirect("mpr:armado_opt", id_lista=id_lista)
        consumo_por_componente = {}
        saldo_por_componente = {}
        for linea, qty, _id_operario_linea in cantidades:
            for comp in linea.get("bom", {}).get("componentes") or []:
                cid = to_int_or_none(comp.get("id_articulo"))
                if cid is None:
                    continue
                cant_por_pack = float(comp.get("cantidad_articulo") or 0)
                consumo_por_componente[cid] = consumo_por_componente.get(cid, 0) + cant_por_pack * qty
                if cid not in saldo_por_componente:
                    saldo_por_componente[cid] = float(comp.get("saldo_semi_elaborado") or 0)
        for cid, necesario in consumo_por_componente.items():
            saldo = saldo_por_componente.get(cid, 0)
            if necesario > saldo:
                codigo_comp = None
                for linea, _qty, _id_operario_linea in cantidades:
                    for comp in linea.get("bom", {}).get("componentes") or []:
                        if to_int_or_none(comp.get("id_articulo")) == cid:
                            codigo_comp = str_codigo_manual_articulo(comp.get("codigo_manual") or comp.get("id_manual")) or str(cid)
                            break
                    if codigo_comp is not None:
                        break
                messages.error(
                    request,
                    f"Stock insuficiente del componente {codigo_comp or cid} en Semi Elaborado: se necesitan {int(necesario)}, hay {int(saldo)}.",
                )
                return redirect("mpr:armado_opt", id_lista=id_lista)
        for linea, qty, id_operario_linea in cantidades:
            id_en_abm = linea.get("id_en_abm")
            articulo_armado = linea.get("articulo_armado") or {}
            id_art_armado = articulo_armado.get("id_articulo")
            try:
                ok, codigo_mov, nro_comp, error = ejecutar_armado(
                    base_empresa,
                    id_usuario,
                    id_en_abm,
                    qty,
                    deposito_semi,
                    deposito_terminado,
                    id_lista_produccion=id_lista,
                    id_articulo_armado=id_art_armado,
                    id_operario=id_operario_linea,
                )
            except MprSchemaError as e:
                return _mpr_schema_error_redirect(request, e)
            if not ok:
                messages.error(request, error or "Error al ejecutar armado.")
                return redirect("mpr:armado_opt", id_lista=id_lista)
        messages.success(request, "Armado registrado por pack.")
        return redirect("mpr:opt_detail", id_lista=id_lista)


class CerrarOptView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Cierra la OPT (en_proceso_produccion='No' en todas sus líneas) cuando el pendiente total es 0. Solo POST."""

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        id_lista = kwargs.get("id_lista", 0)
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:opt_detail", id_lista=id_lista)
        try:
            ok, error = cerrar_opt(base_empresa, id_lista)
        except MprSchemaError as e:
            return _mpr_schema_error_redirect(request, e)
        if ok:
            messages.success(request, f"OPT {id_lista} cerrada correctamente.")
            _limpiar_mpr_wizard(request, id_lista)
        else:
            messages.error(request, error or "Error al cerrar la OPT.")
        referer = request.META.get("HTTP_REFERER") or ""
        if "mpr/tablero" in referer or referer.endswith("/mpr/"):
            return redirect("mpr:tablero")
        return redirect("mpr:opt_detail", id_lista=id_lista)


def _pdf_fila_altura_para_lineas(n_lineas: int, base_mm: float = 5.0, paso_mm: float = 3.2) -> float:
    from reportlab.lib.units import mm
    n = max(1, int(n_lineas or 1))
    return (base_mm + (n - 1) * paso_mm) * mm


def _pdf_draw_cantidad_lineas(p, x: float, y: float, fila_altura: float, lineas: list) -> None:
    """Dibuja cantidad en varias líneas (docenas/unidades o packs/docenas/unidades)."""
    from reportlab.lib.units import mm
    paso = 3.2 * mm
    y_top = y + fila_altura - 3.5 * mm
    for i, texto in enumerate(lineas or ["—"]):
        p.setFont("Helvetica", 10 if i == 0 else 9)
        p.drawString(x, y_top - i * paso, str(texto))


def _pdf_lineas_resumen_metrica(resumen: dict) -> list:
    """Texto multilínea para métricas del encabezado OPT en PDF."""
    if not resumen:
        return ["0 packs", "0 docenas", "0 unidades"]
    if resumen.get("mostrar_desglose"):
        return [str(resumen.get("texto_principal") or "0 packs")]
    return [
        f"{resumen.get('packs', 0)} packs",
        f"{resumen.get('docenas', 0)} docenas",
        f"{resumen.get('unidades', 0)} unidades",
    ]


def _opt_comprobante_pdf(request, id_lista):
    """Genera PDF con detalle completo de la OPT: liberación OPT, OPPs y OPAs. Uso interno desde opt_comprobante_pdf_view."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    from core.report_pdf import draw_report_footer, draw_report_header, get_empresa_para_reporte
    from core.services.administranet_stock import (
        get_nombres_depositos,
        obtener_movimiento,
    )

    base_empresa = _get_base_empresa(request)
    if not base_empresa:
        return None

    codigo_opt = get_codigo_movimiento_opt(base_empresa, id_lista)
    opp_list = listar_opp_por_opt(base_empresa, id_lista)
    opa_list = listar_opa_por_opt(base_empresa, id_lista)

    bloques = []
    if codigo_opt:
        bloques.append({
            "tipo": "opt",
            "titulo": "1. Liberación OPT",
            "subtitulo": "Movimiento a producción",
            "codigo_movimiento": codigo_opt,
        })
    for i, opp in enumerate(opp_list or [], 1):
        bloques.append({
            "tipo": "opp",
            "titulo": f"2.{i}. OPP – Parte de producción",
            "subtitulo": f"Comprobante {opp.get('nro_comprobante', '-')}",
            "codigo_movimiento": opp["codigo_movimiento"],
        })
    for i, opa in enumerate(opa_list or [], 1):
        bloques.append({
            "tipo": "opa",
            "titulo": f"3.{i}. OPA – Armado",
            "subtitulo": f"Comprobante {opa.get('nro_comprobante', '-')}",
            "codigo_movimiento": opa["codigo_movimiento"],
        })

    if not bloques:
        return None

    todos_cod_mov = [b["codigo_movimiento"] for b in bloques]
    mov_cache = {}
    renglones_cache = obtener_renglones_movimiento_bulk(base_empresa, todos_cod_mov)
    dep_ids_set = set()
    all_id_arts = set()
    for cod_mov in todos_cod_mov:
        mov_cache[cod_mov] = obtener_movimiento(base_empresa, cod_mov)
        m = mov_cache[cod_mov]
        if m:
            if m.get("deposito_origen"):
                dep_ids_set.add(m["deposito_origen"])
            if m.get("deposito_destino"):
                dep_ids_set.add(m["deposito_destino"])
        for r in renglones_cache.get(cod_mov) or []:
            aid = to_int_or_none(r.get("IDArt"))
            if aid is not None:
                all_id_arts.add(aid)
    dep_nombres = get_nombres_depositos(base_empresa, list(dep_ids_set)) if dep_ids_set else {}
    bulto_map = bulk_cantidad_promedio_bulto(base_empresa, list(all_id_arts)) if all_id_arts else {}

    # Resumen OPT (demanda, en OPT, pendientes) — mismo criterio pack/docenas/unidades que detalle
    resumenes_pdf = []
    try:
        lineas_opt = get_opt_detalle(base_empresa, id_lista) or []
        if lineas_opt:
            for lin in lineas_opt:
                cantidad_asignada = lin.get("cantidad_asignada_opt")
                if cantidad_asignada is not None and int(cantidad_asignada or 0) > 0:
                    lin["cantidad_en_esta_opt"] = int(cantidad_asignada)
                elif lin.get("cantidad_en_esta_opt") is None:
                    lin["cantidad_en_esta_opt"] = (lin.get("cantidad_pendiente_prod") or 0) + (
                        lin.get("cantidad_ya_armada") or 0
                    )
            total_pedida = sum(l.get("cantidad_pedida") or 0 for l in lineas_opt)
            total_en_esta_opt = sum(l.get("cantidad_en_esta_opt") or 0 for l in lineas_opt)
            total_pendiente = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas_opt)
            pendiente_del_pedido = max(0, total_pedida - total_en_esta_opt)
            bulto_lineas = bulk_cantidad_promedio_bulto(
                base_empresa,
                [l.get("id_articulo") for l in lineas_opt if l.get("id_articulo")],
            )

            def _lineas_metrica(campo: str):
                items = []
                for lin in lineas_opt:
                    id_art = lin.get("id_articulo")
                    try:
                        packs = max(0, int(lin.get(campo) or 0))
                    except (TypeError, ValueError):
                        packs = 0
                    if campo == "pendiente_del_pedido_linea":
                        packs = max(
                            0,
                            int(lin.get("cantidad_pedida") or 0) - int(lin.get("cantidad_en_esta_opt") or 0),
                        )
                    items.append({
                        "etiqueta": _etiqueta_linea_opt(lin),
                        "packs": packs,
                        "bulto": bulto_lineas.get(id_art, 0),
                    })
                return items

            resumenes_pdf = [
                ("Demanda total", build_resumen_metrica_opt(total_pedida, _lineas_metrica("cantidad_pedida"))),
                ("En esta OPT", build_resumen_metrica_opt(total_en_esta_opt, _lineas_metrica("cantidad_en_esta_opt"))),
                ("Pendiente OPP (por producir aquí)", build_resumen_metrica_opt(total_pendiente, _lineas_metrica("cantidad_pendiente_prod"))),
                ("Pendiente del pedido (para otras OPT)", build_resumen_metrica_opt(pendiente_del_pedido, _lineas_metrica("pendiente_del_pedido_linea"))),
            ]
    except Exception as e:
        logger.warning("Resumen OPT PDF %s: %s", id_lista, e, exc_info=True)

    empresa = get_empresa_para_reporte(base_empresa)
    margin = 20 * mm
    col_articulo = 118 * mm
    col_deposito = 36 * mm
    col_entrada = 28 * mm
    col_salida = 28 * mm
    col_saldo = 28 * mm
    ancho_tabla = col_articulo + col_deposito + col_entrada + col_salida + col_saldo
    x_col_deposito = margin + col_articulo
    x_col_entrada = x_col_deposito + col_deposito
    x_col_salida = x_col_entrada + col_entrada
    x_col_saldo = x_col_salida + col_salida
    x_fin_tabla = margin + ancho_tabla
    cabecera_altura = 6 * mm
    y_min = 45 * mm

    import io
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=landscape(A4))
    primera_pagina = True
    y_content = 210 * mm

    def _lineas_cantidad_celda(tipo_bloque: str, valor, id_art) -> list:
        try:
            qty = float(valor or 0)
        except (TypeError, ValueError):
            qty = 0.0
        if qty <= 0:
            return ["0 docenas", "0 unidades"] if tipo_bloque == "opp" else ["0 packs", "0 docenas", "0 unidades"]
        if tipo_bloque == "opp":
            return lineas_texto_cantidad_opp(int(qty))
        bulto = float(bulto_map.get(id_art, 0) if id_art is not None else 0)
        return lineas_texto_cantidad_pack(int(qty), bulto)

    y_content = draw_report_header(
        p, empresa, f"Comprobante completo OPT {id_lista}", 210 * mm
    )
    primera_pagina = False

    if resumenes_pdf:
        p.setFont("Helvetica-Bold", 10)
        p.drawString(margin, y_content, "Resumen de cantidades")
        y_content -= 5 * mm
        p.setFont("Helvetica", 9)
        col_w = ancho_tabla / 2
        for idx, (etiq, res) in enumerate(resumenes_pdf):
            col = idx % 2
            row = idx // 2
            x = margin + col * col_w
            y_block = y_content - row * 14 * mm
            p.setFont("Helvetica-Bold", 9)
            p.drawString(x, y_block, f"{etiq}:")
            lineas_res = _pdf_lineas_resumen_metrica(res)
            for j, ln in enumerate(lineas_res):
                p.setFont("Helvetica", 9 if j else 9)
                p.drawString(x + 2 * mm, y_block - (j + 1) * 3.2 * mm, ln)
            if res.get("mostrar_desglose") and res.get("lineas"):
                extra_y = y_block - (len(lineas_res) + 1) * 3.2 * mm
                for fila in res["lineas"]:
                    if (fila.get("packs") or 0) <= 0:
                        continue
                    p.setFont("Helvetica", 8)
                    p.drawString(
                        x + 4 * mm,
                        extra_y,
                        f"· {fila['etiqueta']}: {fila['texto_docenas_unidades']}",
                    )
                    extra_y -= 3 * mm
        filas_resumen = (len(resumenes_pdf) + 1) // 2
        y_content -= filas_resumen * 14 * mm + 4 * mm

    for bloque in bloques:
        titulo_seccion = bloque["titulo"]
        subtitulo_seccion = bloque["subtitulo"]
        cod_mov = bloque["codigo_movimiento"]
        tipo_bloque = bloque.get("tipo") or "opt"
        mov = mov_cache.get(cod_mov)
        if not mov:
            continue
        renglones = renglones_cache.get(cod_mov, []) or []
        nombre_dep_origen = dep_nombres.get(mov.get("deposito_origen"), "-")
        nombre_dep_destino = dep_nombres.get(mov.get("deposito_destino"), "-")

        if y_content < y_min + 30 * mm:
            draw_report_footer(p)
            p.showPage()
            y_content = 210 * mm - 25 * mm
        else:
            y_content -= 4 * mm
            p.setStrokeColorRGB(0.75, 0.75, 0.75)
            p.setLineWidth(0.3)
            p.line(margin, y_content, x_fin_tabla, y_content)
            y_content -= 6 * mm

        p.setFont("Helvetica-Bold", 11)
        p.drawString(margin, y_content, titulo_seccion)
        y_content -= 5 * mm
        p.setFont("Helvetica", 9)
        p.setFillColorRGB(0.3, 0.3, 0.3)
        p.drawString(margin, y_content, subtitulo_seccion)
        p.setFillColorRGB(0, 0, 0)
        y_content -= 6 * mm

        p.setFont("Helvetica", 10)
        p.drawString(margin, y_content, f"Nro: {mov.get('nro_comprobante') or '-'}  |  Fecha: {str(mov.get('fecha') or '')}  |  Motivo: {mov.get('motivo_movimiento') or '-'}")
        y_content -= 5 * mm
        p.drawString(margin, y_content, f"Dep. origen: {nombre_dep_origen}  |  Dep. destino: {nombre_dep_destino}")
        y_content -= 5 * mm
        detalle_texto = (mov.get("detalle") or "").strip()
        if detalle_texto:
            p.drawString(margin, y_content, f"Detalle: {detalle_texto[:80]}")
            y_content -= 6 * mm
        y_content -= 4 * mm

        if y_content < y_min:
            draw_report_footer(p)
            p.showPage()
            y_content = 210 * mm - 25 * mm

        if not renglones:
            p.setFont("Helvetica", 9)
            p.setFillColorRGB(0.4, 0.4, 0.4)
            p.drawString(margin, y_content, "Sin líneas de movimiento registradas.")
            p.setFillColorRGB(0, 0, 0)
            y_content -= 10 * mm
        else:
            p.setFont("Helvetica", 9)
            p.setFillColorRGB(0.35, 0.35, 0.35)
            p.drawString(margin, y_content, "Detalle de movimientos (artículo, depósito, entrada, salida, saldo):")
            p.setFillColorRGB(0, 0, 0)
            y_content -= 5 * mm

            if y_content < y_min:
                draw_report_footer(p)
                p.showPage()
                y_content = 210 * mm - 25 * mm

            p.setStrokeColorRGB(0.2, 0.2, 0.2)
            p.setLineWidth(0.5)
            p.line(margin, y_content, x_fin_tabla, y_content)
            y_content -= cabecera_altura
            p.setFont("Helvetica-Bold", 10)
            p.drawString(margin + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Artículo / Descripción")
            p.drawString(x_col_deposito + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Depósito")
            p.drawString(x_col_entrada + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Entrada")
            p.drawString(x_col_salida + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Salida")
            p.drawString(x_col_saldo + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Saldo")
            p.line(margin, y_content + cabecera_altura, margin, y_content)
            p.line(x_col_deposito, y_content + cabecera_altura, x_col_deposito, y_content)
            p.line(x_col_entrada, y_content + cabecera_altura, x_col_entrada, y_content)
            p.line(x_col_salida, y_content + cabecera_altura, x_col_salida, y_content)
            p.line(x_col_saldo, y_content + cabecera_altura, x_col_saldo, y_content)
            p.line(x_fin_tabla, y_content + cabecera_altura, x_fin_tabla, y_content)
            y_content -= 2 * mm

            p.setFont("Helvetica", 10)
            grupos = build_grupos_articulo_renglones_movimiento(
                renglones, presentacion_opp_du=(tipo_bloque == "opp")
            )
            filas_impresas = 0
            max_filas = 25
            total_filas = sum(len(g.get("filas") or []) for g in grupos)

            for grupo in grupos:
                if filas_impresas >= max_filas:
                    break
                plan_filas = []
                for fila in grupo.get("filas") or []:
                    if filas_impresas + len(plan_filas) >= max_filas:
                        break
                    id_art = to_int_or_none(fila.get("id_articulo"))
                    try:
                        entrada_qty = float(fila.get("entrada") or 0)
                    except (TypeError, ValueError):
                        entrada_qty = 0.0
                    try:
                        salida_qty = float(fila.get("salida") or 0)
                    except (TypeError, ValueError):
                        salida_qty = 0.0
                    saldo_val = fila.get("saldo")
                    lineas_entrada = (
                        _lineas_cantidad_celda(tipo_bloque, fila.get("entrada"), id_art)
                        if entrada_qty > 0
                        else ["—"]
                    )
                    lineas_salida = (
                        _lineas_cantidad_celda(tipo_bloque, fila.get("salida"), id_art)
                        if salida_qty > 0
                        else ["—"]
                    )
                    lineas_saldo = (
                        _lineas_cantidad_celda(tipo_bloque, saldo_val, id_art)
                        if saldo_val is not None
                        else ["—"]
                    )
                    altura = _pdf_fila_altura_para_lineas(
                        max(len(lineas_entrada), len(lineas_salida), len(lineas_saldo))
                    )
                    plan_filas.append({
                        "nombre_deposito": str_or_default(fila.get("nombre_deposito"), "—"),
                        "lineas_entrada": lineas_entrada,
                        "lineas_salida": lineas_salida,
                        "lineas_saldo": lineas_saldo,
                        "altura": altura,
                    })

                if not plan_filas:
                    continue

                grupo_altura = sum(f["altura"] for f in plan_filas)
                if y_content - grupo_altura < y_min:
                    draw_report_footer(p)
                    p.showPage()
                    y_content = 210 * mm - 25 * mm
                    p.setFont("Helvetica", 10)

                y_top_grupo = y_content
                cod_txt = str_or_default(grupo.get("codigo_manual") or grupo.get("codigo_articulo"), "—")[:28]
                desc_txt = str_or_default(grupo.get("descripcion"), "—")[:52]
                p.setFont("Helvetica", 9)
                p.drawString(margin + 2 * mm, y_top_grupo - 3.5 * mm, cod_txt)
                p.setFont("Helvetica", 8)
                p.drawString(margin + 2 * mm, y_top_grupo - 7 * mm, desc_txt)
                p.setFont("Helvetica", 10)

                for fila_data in plan_filas:
                    fila_altura = fila_data["altura"]
                    if y_content - fila_altura < y_min:
                        draw_report_footer(p)
                        p.showPage()
                        y_content = 210 * mm - 25 * mm
                        p.setFont("Helvetica", 10)
                        y_top_grupo = y_content

                    p.line(margin, y_content, x_fin_tabla, y_content)
                    dep_txt = fila_data["nombre_deposito"][:22]
                    if len(fila_data["nombre_deposito"]) > 22:
                        dep_txt += "..."
                    p.setFont("Helvetica", 9)
                    p.drawString(x_col_deposito + 2 * mm, y_content - 3.5 * mm, dep_txt)
                    p.setFont("Helvetica", 10)
                    y_fila = y_content - fila_altura
                    _pdf_draw_cantidad_lineas(
                        p, x_col_entrada + 2 * mm, y_fila, fila_altura, fila_data["lineas_entrada"]
                    )
                    _pdf_draw_cantidad_lineas(
                        p, x_col_salida + 2 * mm, y_fila, fila_altura, fila_data["lineas_salida"]
                    )
                    _pdf_draw_cantidad_lineas(
                        p, x_col_saldo + 2 * mm, y_fila, fila_altura, fila_data["lineas_saldo"]
                    )
                    p.line(x_col_entrada, y_content, x_col_entrada, y_fila)
                    p.line(x_col_salida, y_content, x_col_salida, y_fila)
                    p.line(x_col_saldo, y_content, x_col_saldo, y_fila)
                    p.line(x_fin_tabla, y_content, x_fin_tabla, y_fila)
                    y_content = y_fila
                    filas_impresas += 1

                p.line(margin, y_content, x_fin_tabla, y_content)
                p.line(margin, y_top_grupo, margin, y_content)
                p.line(x_col_deposito, y_top_grupo, x_col_deposito, y_content)

            if total_filas > max_filas:
                y_content -= 4 * mm
                p.setFont("Helvetica", 9)
                p.drawString(margin, y_content, f"... y {total_filas - max_filas} renglones más.")
                y_content -= 4 * mm
            y_content -= 8 * mm

        y_content -= 6 * mm

    draw_report_footer(p)
    p.showPage()
    p.save()
    buf.seek(0)
    return buf


def opt_comprobante_pdf_view(request, id_lista):
    """Vista que devuelve el PDF del comprobante completo de la OPT (OPT, OPPs, OPAs)."""
    from django.contrib import messages
    if "user" not in request.session or not getattr(request.user, "is_authenticated", False):
        return redirect("login:login")
    if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
        raise PermissionDenied
    base_empresa = _get_base_empresa(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("mpr:opt_detail", id_lista=id_lista)
    try:
        buf = _opt_comprobante_pdf(request, id_lista)
    except MprSchemaError as e:
        return _mpr_schema_error_redirect(request, e)
    except Exception as e:
        logger.warning("Error al generar comprobante OPT %s: %s", id_lista, e, exc_info=True)
        messages.error(request, "No se pudo generar el comprobante.")
        return redirect("mpr:opt_detail", id_lista=id_lista)
    if buf is None:
        messages.error(request, "No hay movimientos para esta OPT o no se pudo determinar la empresa.")
        return redirect("mpr:opt_detail", id_lista=id_lista)
    response = HttpResponse(buf.read(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="opt-{id_lista}-comprobante-completo.pdf"'
    return response


class NuevaOptView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Redirige al asistente de producción. La creación manual de OPT ya no está disponible en MPR."""

    def get(self, request, *args, **kwargs):
        return redirect("mpr:wizard")

    def post(self, request, *args, **kwargs):
        return redirect("mpr:wizard")


class BomListView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Listado de conjuntos de armado (Lista de materiales / en_abm)."""

    template_name = "mpr/bom_list.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        solo_activos = self.request.GET.get("activos", "1") == "1"
        solo_en_produccion = self.request.GET.get("en_produccion", "1") == "1"
        context["base_empresa"] = base_empresa
        try:
            context["conjuntos"] = listar_bom_conjuntos(
                base_empresa,
                limit=100,
                solo_activos=solo_activos,
                solo_en_produccion=solo_en_produccion,
            )
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            context["mpr_schema_error_modal"] = str(e)
            context["conjuntos"] = []
        context["solo_activos"] = solo_activos
        context["solo_en_produccion"] = solo_en_produccion
        return context


class BomDetailView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Detalle de un conjunto de armado (Lista de materiales): cabecera y componentes."""

    template_name = "mpr/bom_detail.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        id_en_abm = kwargs.get("id_en_abm")
        detalle = get_bom_detalle(base_empresa, id_en_abm)
        if not detalle:
            raise Http404("Conjunto de armado no encontrado.")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_en_abm = kwargs.get("id_en_abm")
        context["base_empresa"] = base_empresa
        context["bom"] = get_bom_detalle(base_empresa, id_en_abm)
        context["articulo_armado"] = get_articulo_armado_por_bom(base_empresa, id_en_abm)
        return context


class BomCreateView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Alta de conjunto de armado (en_abm)."""

    template_name = "mpr/bom_form.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_empresa"] = _get_base_empresa(self.request)
        context["es_nuevo"] = True
        context["bom"] = {"cabecera": {"id_en_abm": None, "nombre_en_abm": "", "detalle": "", "anulado": "No"}}
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:bom_list")
        nombre = (request.POST.get("nombre_en_abm") or "").strip()
        detalle = (request.POST.get("detalle") or "").strip() or None
        if not nombre:
            messages.error(request, "El nombre del conjunto es obligatorio.")
            return redirect("mpr:bom_create")
        ok, id_en_abm, error = crear_conjunto_bom(base_empresa, nombre, detalle)
        if ok:
            messages.success(request, f"Conjunto creado (ID {id_en_abm}). Añada componentes.")
            return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
        messages.error(request, error or "Error al crear conjunto.")
        return redirect("mpr:bom_create")


class BomEditView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Edición de conjunto (en_abm) y componentes (en_abm_formula)."""

    template_name = "mpr/bom_edit.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        id_en_abm = kwargs.get("id_en_abm")
        bom = get_bom_detalle(base_empresa, id_en_abm)
        if not bom:
            raise Http404("Conjunto de armado no encontrado.")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_en_abm = kwargs.get("id_en_abm")
        context["base_empresa"] = base_empresa
        context["id_en_abm"] = id_en_abm
        context["bom"] = get_bom_detalle(base_empresa, id_en_abm)
        context["articulos"] = listar_articulos_para_op(base_empresa, limit=500)
        context["articulo_armado"] = get_articulo_armado_por_bom(base_empresa, id_en_abm)
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        id_en_abm = kwargs.get("id_en_abm")
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
        accion = (request.POST.get("accion") or "").strip()
        if accion == "set_articulo_armado":
            raw = (request.POST.get("id_articulo_armado") or "").strip()
            id_articulo = None
            if raw and raw != "0":
                try:
                    id_articulo = int(raw)
                except (TypeError, ValueError):
                    id_articulo = None
            ok, err = set_articulo_armado_bom(base_empresa, id_en_abm, id_articulo)
            if ok:
                messages.success(request, "Artículo armado actualizado." if id_articulo else "Artículo armado desasignado.")
            else:
                messages.error(request, err or "Error al asignar artículo armado.")
            return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
        if accion == "guardar_cabecera":
            nombre = (request.POST.get("nombre_en_abm") or "").strip()
            detalle = (request.POST.get("detalle") or "").strip() or None
            anulado = (request.POST.get("anulado") or "").strip()
            if not nombre:
                messages.error(request, "El nombre del conjunto es obligatorio.")
                return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
            ok, err = actualizar_conjunto_bom(base_empresa, id_en_abm, nombre, detalle, anulado if anulado in ("Si", "No") else None)
            if ok:
                messages.success(request, "Conjunto actualizado.")
            else:
                messages.error(request, err or "Error al actualizar.")
            return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
        if accion == "agregar_componente":
            try:
                id_articulo = int(request.POST.get("id_articulo", "").strip())
            except (TypeError, ValueError):
                id_articulo = None
            try:
                cantidad_articulo = float(request.POST.get("cantidad_articulo", "0").strip().replace(",", "."))
            except (TypeError, ValueError):
                cantidad_articulo = 0
            tipo_unidad = (request.POST.get("tipo_unidad") or "").strip() or None
            if not id_articulo or cantidad_articulo <= 0:
                messages.error(request, "Seleccione artículo y cantidad mayor que cero.")
                return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
            ok, _, err = crear_componente_bom(base_empresa, id_en_abm, id_articulo, cantidad_articulo, tipo_unidad)
            if ok:
                messages.success(request, "Componente añadido.")
            else:
                messages.error(request, err or "Error al añadir componente.")
            return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
        if accion == "editar_componente":
            try:
                id_en_abm_formula = int(request.POST.get("id_en_abm_formula", "").strip())
            except (TypeError, ValueError):
                id_en_abm_formula = None
            try:
                id_articulo = int(request.POST.get("id_articulo", "").strip())
            except (TypeError, ValueError):
                id_articulo = None
            try:
                cantidad_articulo = float(request.POST.get("cantidad_articulo", "0").strip().replace(",", "."))
            except (TypeError, ValueError):
                cantidad_articulo = 0
            tipo_unidad = (request.POST.get("tipo_unidad") or "").strip() or None
            if not id_en_abm_formula or not id_articulo or cantidad_articulo <= 0:
                messages.error(request, "Datos de componente inválidos.")
                return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
            ok, err = actualizar_componente_bom(base_empresa, id_en_abm_formula, id_articulo, cantidad_articulo, tipo_unidad)
            if ok:
                messages.success(request, "Componente actualizado.")
            else:
                messages.error(request, err or "Error al actualizar.")
            return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
        if accion == "anular_componente":
            try:
                id_en_abm_formula = int(request.POST.get("id_en_abm_formula", "").strip())
            except (TypeError, ValueError):
                id_en_abm_formula = None
            if not id_en_abm_formula:
                messages.error(request, "Componente no indicado.")
                return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
            ok, err = anular_componente_bom(base_empresa, id_en_abm_formula)
            if ok:
                messages.success(request, "Componente anulado.")
            else:
                messages.error(request, err or "Error al anular.")
            return redirect("mpr:bom_edit", id_en_abm=id_en_abm)
        return redirect("mpr:bom_edit", id_en_abm=id_en_abm)


# Opciones de estado_pedido_opt para filtro en Pedidos fábrica
ESTADOS_PEDIDO_OPT_CHOICES = [
    ("", "Todos"),
    ("Pendiente", "Pendiente"),
    ("Produccion", "Producción"),
    ("Parcial", "Parcial"),
    ("Terminado", "Terminado"),
]


class PedidosFabricaListView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Listado de pedidos con estado de producción (comp_ped estado_pedido_opt: Pendiente, Produccion, Parcial, Terminado)."""

    template_name = "mpr/pedidos_fabrica_list.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        estado = self.request.GET.get("estado", "").strip() or None
        context["base_empresa"] = base_empresa
        context["opciones_estado"] = ESTADOS_PEDIDO_OPT_CHOICES
        try:
            context["pedidos"] = listar_pedidos_fabrica(base_empresa, limit=100, estado=estado)
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            context["mpr_schema_error_modal"] = str(e)
            context["pedidos"] = []
        context["filtro_estado"] = estado or ""
        return context


class OptsPorPedidoView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Trazabilidad: OPTs vinculadas a un pedido (codigo_movimiento). GET ?codigo=."""

    template_name = "mpr/opts_por_pedido.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:pedidos_fabrica_list")
        codigo = request.GET.get("codigo")
        if not codigo:
            from django.contrib import messages
            messages.warning(request, "Indique el número de movimiento del pedido.")
            return redirect("mpr:pedidos_fabrica_list")
        try:
            codigo = int(codigo)
        except (TypeError, ValueError):
            from django.contrib import messages
            messages.error(request, "Código de movimiento inválido.")
            return redirect("mpr:pedidos_fabrica_list")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        codigo = int(self.request.GET.get("codigo", 0))
        context["codigo_movimiento"] = codigo
        try:
            context["opts"] = listar_opts_por_pedido(base_empresa, codigo)
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            context["mpr_schema_error_modal"] = str(e)
            context["opts"] = []
        return context


# Opciones para dropdown TIPO en Config. Depósitos (valor interno, etiqueta)
TIPOS_MPR_CON_ETIQUETA = [
    ("", "— Sin tipo —"),
    (TIPO_MPR_PRODUCCION, "Producción"),
    (TIPO_MPR_PLANCHADO, "Planchado"),
    (TIPO_MPR_SEMI_ELABORADO, "Semi Elaborado"),
    (TIPO_MPR_TERMINADO, "Terminado"),
    (TIPO_MPR_SCRAP, "Scrap"),
    (TIPO_MPR_2DA_SELECCION, "2da Selección"),
]


class ConfigDepositosView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Configuración MPR: depósitos, suma_stock y tipo (Producción, Semi Elaborado, Terminado, Scrap, 2da Selección)."""

    template_name = "mpr/config_depositos.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base = _get_base_empresa(self.request)
        context["base_empresa"] = base
        context["tipos_mpr_opciones"] = TIPOS_MPR_CON_ETIQUETA
        try:
            depositos = listar_depositos_config(base)
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            context["mpr_schema_error_modal"] = str(e)
            context["depositos"] = []
            return context
        # Tipos ya asignados a otros depósitos (para dropdown exclusivo)
        tipos_usados = {d.get("tipo_mpr") for d in depositos if d.get("tipo_mpr")}
        from mpr.pipeline import TIPOS_QUE_SUMAN_STOCK
        for d in depositos:
            tipo_actual = d.get("tipo_mpr")
            # Opciones: vacío + tipos no usados por otros + tipo actual de este depósito
            opciones = [("", "— Sin tipo —")]
            for val, label in TIPOS_MPR_CON_ETIQUETA[1:]:
                if val == tipo_actual or val not in tipos_usados:
                    opciones.append((val, label))
            d["opciones_tipo"] = opciones
            d["suma_stock_obligatoria"] = tipo_actual in TIPOS_QUE_SUMAN_STOCK
        context["depositos"] = depositos
        from mpr.services import obtener_config_mpr
        config_mpr = obtener_config_mpr(base)
        context["bloquear_parte_supera_fabricando"] = config_mpr.get(
            "bloquear_parte_supera_fabricando", True
        )
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        from mpr.services import actualizar_config_mpr_bloqueo_fabricando
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:config_depositos")
        if "bloquear_parte_supera_fabricando" in request.POST:
            bloquear = request.POST.get("bloquear_parte_supera_fabricando") == "1"
            ok, err = actualizar_config_mpr_bloqueo_fabricando(base_empresa, bloquear)
            if ok:
                if bloquear:
                    messages.success(
                        request,
                        "Bloqueo activado: el parte no podrá superar la columna Fabricando.",
                    )
                else:
                    messages.success(
                        request,
                        "Bloqueo desactivado: se permitirá registrar con aviso si supera Fabricando.",
                    )
            else:
                messages.error(request, err or "Error al guardar configuración.")
            return redirect("mpr:config_depositos")
        # Toggle suma_stock (form envía cod_deposito + valor Si/No)
        valor = request.POST.get("valor", "").strip()
        cod = request.POST.get("cod_deposito", "").strip()
        if valor in ("Si", "No") and cod:
            try:
                cod_deposito = int(cod)
            except ValueError:
                cod_deposito = None
            if cod_deposito is not None:
                try:
                    ok, err = actualizar_deposito_suma_stock(base_empresa, cod_deposito, valor)
                    if ok:
                        messages.success(request, f"Depósito {cod_deposito} actualizado: Suma stock = {valor}.")
                    else:
                        messages.error(request, err or "Error al actualizar.")
                except MprSchemaError as e:
                    _log_mpr_schema_error(e)
                    request.session["mpr_schema_error_modal"] = str(e)
                return redirect("mpr:config_depositos")
        # Actualización de tipo_mpr (form por fila: cod_deposito + tipo_mpr)
        if "tipo_mpr" in request.POST:
            tipo_mpr = request.POST.get("tipo_mpr", "").strip() or None
            cod_tipo = request.POST.get("cod_deposito", "").strip()
            if cod_tipo:
                try:
                    cod_deposito = int(cod_tipo)
                except ValueError:
                    cod_deposito = None
                if cod_deposito is not None:
                    try:
                        ok, err = actualizar_deposito_tipo_mpr(base_empresa, cod_deposito, tipo_mpr)
                        if ok:
                            messages.success(request, "Tipo de depósito actualizado.")
                        else:
                            messages.error(request, err or "Error al actualizar tipo.")
                    except MprSchemaError as e:
                        _log_mpr_schema_error(e)
                        request.session["mpr_schema_error_modal"] = str(e)
                    return redirect("mpr:config_depositos")
        if valor and valor not in ("Si", "No"):
            messages.error(request, "Datos inválidos para actualizar depósito.")
        return redirect("mpr:config_depositos")


class OperariosListView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Listado de operarios (sue_abm_empleado) para CRUD."""

    template_name = "mpr/operarios_list.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from django.contrib import messages
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        incluir_anulados = self.request.GET.get("anulados", "") == "1"
        busqueda = (self.request.GET.get("q") or "").strip() or None
        context["base_empresa"] = base_empresa
        context["operarios"] = listar_operarios_crud(
            base_empresa, incluir_anulados=incluir_anulados, busqueda=busqueda
        )
        context["incluir_anulados"] = incluir_anulados
        context["q"] = busqueda or ""
        return context


class OperarioCreateView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Alta de operario (sue_abm_empleado)."""

    template_name = "mpr/operario_form.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["base_empresa"] = _get_base_empresa(self.request)
        context["operario"] = None
        context["es_edicion"] = False
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:operarios_list")
        nombre = (request.POST.get("nombre_empleado") or "").strip()
        id_cliente_raw = (request.POST.get("id_cliente") or "").strip()
        id_cliente = int(id_cliente_raw) if id_cliente_raw.isdigit() else None
        ok, new_id, err = crear_operario(base_empresa, nombre, id_cliente=id_cliente)
        if ok:
            messages.success(request, "Operario creado correctamente.")
            return redirect("mpr:operarios_list")
        messages.error(request, err or "Error al crear operario.")
        return redirect("mpr:operario_create")


class OperarioUpdateView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Edición de operario (sue_abm_empleado)."""

    template_name = "mpr/operario_form.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        id_operario = kwargs.get("id_operario")
        operario = obtener_operario(base_empresa, id_operario)
        if not operario:
            from django.contrib import messages
            messages.error(request, "Operario no encontrado.")
            return redirect("mpr:operarios_list")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_operario = kwargs.get("id_operario")
        operario = obtener_operario(base_empresa, id_operario)
        context["base_empresa"] = base_empresa
        context["operario"] = operario
        context["es_edicion"] = True
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        id_operario = kwargs.get("id_operario")
        if not base_empresa or not id_operario:
            messages.error(request, "Parámetros inválidos.")
            return redirect("mpr:operarios_list")
        nombre = (request.POST.get("nombre_empleado") or "").strip()
        id_cliente_raw = (request.POST.get("id_cliente") or "").strip()
        id_cliente = int(id_cliente_raw) if id_cliente_raw.isdigit() else None
        ok, err = actualizar_operario(base_empresa, id_operario, nombre, id_cliente=id_cliente)
        if ok:
            messages.success(request, "Operario actualizado correctamente.")
            return redirect("mpr:operarios_list")
        messages.error(request, err or "Error al actualizar operario.")
        return redirect("mpr:operario_edit", id_operario=id_operario)


class OperarioAnularView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """Anula un operario (anulado='Si'). Solo POST."""

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        id_operario = kwargs.get("id_operario")
        if not base_empresa or not id_operario:
            messages.error(request, "Parámetros inválidos.")
            return redirect("mpr:operarios_list")
        ok, err = anular_operario(base_empresa, id_operario)
        if ok:
            messages.success(request, "Operario anulado.")
        else:
            messages.error(request, err or "Error al anular.")
        return _redirect_operarios_list_preserve_filters(request)


class OperarioReactivarView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """Reactiva un operario (anulado='No'). Solo POST."""

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        id_operario = kwargs.get("id_operario")
        if not base_empresa or not id_operario:
            messages.error(request, "Parámetros inválidos.")
            return redirect("mpr:operarios_list")
        ok, err = reactivar_operario(base_empresa, id_operario)
        if ok:
            messages.success(request, "Operario reactivado.")
        else:
            messages.error(request, err or "Error al reactivar.")
        return _redirect_operarios_list_preserve_filters(request)


class ArmadoLegacyView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Legacy — armado por OPT (deprecado; usar Armado 1ra unificado)."""

    template_name = "mpr/armado.html"

    def get(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        id_lista_param = request.GET.get("id_lista", "").strip()
        try:
            id_lista = int(id_lista_param) if id_lista_param else None
        except ValueError:
            id_lista = None
        if not id_lista:
            messages.info(request, "El armado solo está disponible desde una OPT con pendiente 0. Seleccione una OPT desde el listado.")
            return redirect("mpr:opt_list")
        lineas = get_opt_detalle(base_empresa, id_lista)
        if lineas:
            total_pendiente = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
            if total_pendiente != 0:
                messages.error(request, "El armado solo está disponible cuando el pendiente de la OPT es 0 (todo registrado por OPP).")
                return redirect("mpr:opt_detail", id_lista=id_lista)
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from django.contrib import messages
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_lista_param = self.request.GET.get("id_lista", "").strip()
        try:
            id_lista = int(id_lista_param) if id_lista_param else None
        except ValueError:
            id_lista = None
        if not id_lista:
            context["lineas_armado"] = []
            context["id_lista"] = None
            context["opt_numero"] = None
            context["depositos"] = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(self.request))
            context["id_deposito_terminado"] = get_deposito_terminado_mpr(base_empresa)
            context["operarios"] = listar_empleados_operarios(base_empresa, busqueda=None, limit=200)
            return context
        lineas = get_opt_detalle(base_empresa, id_lista)
        if not lineas:
            context["lineas_armado"] = []
            context["id_lista"] = id_lista
            context["opt_numero"] = id_lista
            context["depositos"] = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(self.request))
            context["id_deposito_terminado"] = get_deposito_terminado_mpr(base_empresa)
            context["operarios"] = listar_empleados_operarios(base_empresa, busqueda=None, limit=200)
            return context
        cantidades_armadas = get_cantidades_armadas_por_opt(base_empresa, id_lista)
        opp_semi, _, _ = get_cantidad_opp_por_destino_opt(base_empresa, id_lista)
        art_ids_liberar = [l.get("id_articulo") for l in lineas if l.get("id_articulo")]
        abm_map_liberar = bulk_id_en_abm(base_empresa, art_ids_liberar) if art_ids_liberar else {}
        equiv_semi = bulk_componentes_a_equivalentes_pack(base_empresa, art_ids_liberar, opp_semi)
        lineas_armado = []
        for l in lineas:
            id_art = l.get("id_articulo")
            id_en_abm = abm_map_liberar.get(id_art)
            if not id_en_abm:
                continue
            cantidad_ya_armada = cantidades_armadas.get(id_art, 0)
            cantidad_disponible_armar = equiv_semi.get(id_art, 0)
            cantidad_restante_armar = max(0, cantidad_disponible_armar - cantidad_ya_armada)
            producto_label = f"{l.get('codigo_manual') or '-'} — {l.get('descripcion_articulo') or '-'}"
            lineas_armado.append({
                "producto_label": producto_label,
                "cantidad": cantidad_restante_armar,
                "id_en_abm": id_en_abm,
                "id_articulo": id_art,
                "id_lista_produccion": l.get("id_lista_produccion") or id_lista,
            })
        context["lineas_armado"] = lineas_armado
        context["id_lista"] = id_lista
        context["opt_numero"] = id_lista
        context["depositos"] = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(self.request))
        context["id_deposito_terminado"] = get_deposito_terminado_mpr(base_empresa)
        context["hay_restante_armar"] = any(item["cantidad"] > 0 for item in lineas_armado)
        context["operarios"] = listar_empleados_operarios(base_empresa, busqueda=None, limit=200)
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:opt_list")
        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        if not id_usuario:
            messages.error(request, "Usuario no identificado en sesión.")
            return redirect("mpr:opt_list")
        try:
            id_lista = int(request.POST.get("id_lista", "").strip())
        except (TypeError, ValueError):
            id_lista = None
        try:
            deposito_origen = int(request.POST.get("deposito_origen", "").strip())
        except (TypeError, ValueError):
            deposito_origen = None
        try:
            deposito_destino = int(request.POST.get("deposito_destino", "").strip())
        except (TypeError, ValueError):
            deposito_destino = None
        if not id_lista or not deposito_origen or not deposito_destino:
            messages.error(request, "Faltan OPT o depósitos.")
            return redirect("mpr:opt_list")
        lineas = get_opt_detalle(base_empresa, id_lista)
        if not lineas:
            messages.error(request, "OPT no encontrada.")
            return redirect("mpr:opt_list")
        total_pendiente = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
        if total_pendiente != 0:
            messages.error(request, "El armado solo está disponible cuando el pendiente de la OPT es 0.")
            return redirect("mpr:opt_detail", id_lista=id_lista)
        cantidades_armadas = get_cantidades_armadas_por_opt(base_empresa, id_lista)
        opp_semi, _, _ = get_cantidad_opp_por_destino_opt(base_empresa, id_lista)
        art_ids_post = [l.get("id_articulo") for l in lineas if l.get("id_articulo")]
        abm_map_post = bulk_id_en_abm(base_empresa, art_ids_post) if art_ids_post else {}
        equiv_semi_post = bulk_componentes_a_equivalentes_pack(base_empresa, art_ids_post, opp_semi)
        ejecutados = 0
        primer_error = None
        for l in lineas:
            id_art = l.get("id_articulo")
            id_en_abm = abm_map_post.get(id_art)
            if not id_en_abm:
                continue
            cantidad_ya_armada = cantidades_armadas.get(id_art, 0)
            cantidad_disponible_armar = equiv_semi_post.get(id_art, 0)
            cantidad_restante_armar = max(0, cantidad_disponible_armar - cantidad_ya_armada)
            if cantidad_restante_armar <= 0:
                continue
            id_operario_linea = to_int_or_none(request.POST.get(f"operario_armado_{id_art}"))
            try:
                ok, codigo_mov, nro_comp, error = ejecutar_armado(
                    base_empresa,
                    id_usuario,
                    id_en_abm,
                    cantidad_restante_armar,
                    deposito_origen,
                    deposito_destino,
                    id_lista_produccion=id_lista,
                    id_articulo_armado=id_art,
                    id_operario=id_operario_linea,
                )
            except MprSchemaError as e:
                return _mpr_schema_error_redirect(request, e)
            if ok:
                ejecutados += 1
                cantidades_armadas[id_art] = cantidades_armadas.get(id_art, 0) + cantidad_restante_armar
            else:
                if primer_error is None:
                    primer_error = error
        if ejecutados > 0:
            messages.success(request, f"Armado registrado para {ejecutados} artículo(s).")
        if primer_error:
            messages.error(request, primer_error)
        return redirect("mpr:opt_detail", id_lista=id_lista)


class ReclasificacionView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Reclasificación (2da selección / Scrap): movimiento de artículo entre depósitos."""

    template_name = "mpr/reclasificacion.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        context["base_empresa"] = base_empresa
        context["articulos"] = listar_articulos_para_op(base_empresa, limit=500)
        context["depositos"] = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(self.request))
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:reclasificacion")
        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        if not id_usuario:
            messages.error(request, "Usuario no identificado en sesión.")
            return redirect("mpr:reclasificacion")
        try:
            id_articulo = int(request.POST.get("id_articulo", "").strip())
        except (TypeError, ValueError):
            id_articulo = None
        try:
            cantidad = int(request.POST.get("cantidad", "").strip())
        except (TypeError, ValueError):
            cantidad = 0
        try:
            deposito_origen = int(request.POST.get("deposito_origen", "").strip())
        except (TypeError, ValueError):
            deposito_origen = None
        try:
            deposito_destino = int(request.POST.get("deposito_destino", "").strip())
        except (TypeError, ValueError):
            deposito_destino = None
        detalle = (request.POST.get("detalle") or "").strip() or None
        if not id_articulo or cantidad <= 0 or not deposito_origen or not deposito_destino:
            messages.error(request, "Complete artículo, cantidad y ambos depósitos.")
            return redirect("mpr:reclasificacion")
        ok, codigo_mov, nro_comp, error = ejecutar_reclasificacion(
            base_empresa, id_usuario, id_articulo, cantidad, deposito_origen, deposito_destino, detalle
        )
        if ok:
            messages.success(request, f"Reclasificación registrada. Comprobante {nro_comp} (código {codigo_mov}).")
        else:
            messages.error(request, error or "Error al ejecutar reclasificación.")
        return redirect("mpr:reclasificacion")


def _parse_lineas_composicion_armado_surtido(request) -> list:
    """Extrae líneas {id_articulo, cantidad_por_pack} del POST del formulario armado surtido."""
    ids = request.POST.getlist("comp_id_articulo")
    cants = request.POST.getlist("comp_cantidad_por_pack")
    lineas = []
    for i, id_raw in enumerate(ids):
        try:
            id_a = int(str(id_raw).strip())
        except (TypeError, ValueError):
            continue
        try:
            qty = int(str(cants[i] if i < len(cants) else "0").strip())
        except (TypeError, ValueError):
            qty = 0
        if id_a and qty > 0:
            lineas.append({"id_articulo": id_a, "cantidad_por_pack": qty})
    return lineas


def _fallidos_para_carrito_armado_surtido(fallidos: list) -> list:
    """Ítems fallidos listos para rehidratar el carrito Alpine (Fase 5)."""
    resultado = []
    for item in fallidos or []:
        lineas = []
        for ln in item.get("lineas") or []:
            lineas.append({
                "id_articulo": ln.get("id_articulo"),
                "cantidad_por_pack": ln.get("cantidad_por_pack"),
            })
        resultado.append({
            "id_articulo_pack": item.get("id_articulo_pack"),
            "cantidad_packs": item.get("cantidad_packs"),
            "lineas": lineas,
        })
    return resultado


def _resolver_post_armado_surtido(request):
    """
    Cabecera + armados desde POST.
    Prioriza lote_json; grilla tabla (vista=tablero); o un ítem single-pack MVP.
    Devuelve (cabecera, armados, error).
    """
    modo = _modo_armado_desde_request(request)
    vista = (request.POST.get("vista") or "").strip().lower()
    if vista == "tablero" and modo == "1ra":
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            cabecera = parse_cabecera_lote_armado_surtido(request.POST)
            return cabecera, None, "No se pudo determinar la empresa activa."
        cabecera = parse_cabecera_lote_armado_surtido(request.POST)
        cabecera["modo"] = modo
        armados = construir_armados_desde_post_tablero(
            base_empresa, request.POST, modo=modo
        )
        if not armados:
            return cabecera, None, "Ingrese al menos una cantidad en la columna Armar."
        return cabecera, armados, None

    raw_lote = (request.POST.get("lote_json") or "").strip()
    if raw_lote:
        return parse_lote_armado_surtido_post(request)

    cabecera = parse_cabecera_lote_armado_surtido(request.POST)
    lineas = _parse_lineas_composicion_armado_surtido(request)
    try:
        id_articulo_pack = int(str(request.POST.get("id_articulo_pack", "")).strip())
    except (TypeError, ValueError):
        id_articulo_pack = None
    try:
        cantidad_packs = int(str(request.POST.get("cantidad_packs", "")).strip())
    except (TypeError, ValueError):
        cantidad_packs = 0
    item_raw = {
        "id_articulo_pack": id_articulo_pack,
        "cantidad_packs": cantidad_packs,
        "lineas": lineas,
    }
    item, err_item = normalizar_item_lote_armado_surtido(item_raw)
    if err_item or not item:
        return cabecera, None, err_item or "Agregue al menos un armado al lote."
    return cabecera, [item], None


def _modo_armado_desde_request(request, default="1ra"):
    modo = (request.GET.get("modo") or request.POST.get("modo") or default).strip().lower()
    return modo if modo in ("1ra", "2da") else default


def _vista_armado_desde_request(request, default: str = "tablero") -> str:
    """Armado solo usa vista tablero. ``vista=pos`` queda deprecado de forma permanente."""
    return "tablero"


def _resolver_solo_resta_armado(request) -> bool:
    raw = (request.GET.get("solo_resta") or request.POST.get("solo_resta") or "1").strip().lower()
    return raw not in ("0", "false", "no")


def _redirect_armado(modo="2da", id_lista=None, request=None):
    filtros_qs = ""
    if request is not None:
        filtros_qs = (request.POST.get("filtros_qs") or "").strip()
    if filtros_qs:
        return redirect(f"{reverse('mpr:armado')}?{filtros_qs}")
    params: Dict[str, Any] = {
        "modo": modo,
        "vista": _vista_armado_desde_request(request) if request else "tablero",
    }
    if id_lista:
        params["id_lista"] = id_lista
    if request is not None:
        for key in ("fecha_desde", "fecha_hasta", "presentacion", "solo_resta", "fecha_realizado"):
            val = (request.GET.get(key) or request.POST.get(key) or "").strip()
            if val:
                params[key] = val
    return redirect(f"{reverse('mpr:armado')}?{urlencode(params)}")


def _redirect_armado_surtido(id_lista=None):
    return _redirect_armado("2da", id_lista)


class ArmadoPacksCatalogAPIView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """API: catálogo de packs Armado (lazy). GET ?modo=1ra|2da&q=&limit=25"""

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"packs": []})
        modo = (request.GET.get("modo") or "1ra").strip().lower()
        if modo not in ("1ra", "2da"):
            modo = "1ra"
        q = (request.GET.get("q") or "").strip()
        try:
            limit = int(request.GET.get("limit") or 25)
        except (TypeError, ValueError):
            limit = 25
        deposito = to_int_or_none(request.GET.get("deposito"))
        try:
            packs = listar_packs_armado_catalogo(
                base_empresa,
                modo,
                busqueda=q or None,
                limit=limit,
                deposito_semi=deposito if modo == "1ra" else None,
            )
            return JsonResponse({"packs": packs})
        except Exception as e:
            logger.warning("API catálogo packs armado: %s", e, exc_info=True)
            return JsonResponse({"packs": [], "error": "No se pudo cargar el catálogo."})


class ArmadoBomPackAPIView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """API: líneas BOM para pack Armado 1ra. GET ?id_articulo="""

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"lineas": [], "max_packs": 0})
        id_art = to_int_or_none(request.GET.get("id_articulo"))
        if not id_art:
            return JsonResponse({"lineas": [], "max_packs": 0, "error": "Pack requerido."})
        dep = to_int_or_none(request.GET.get("deposito"))
        lineas = lineas_bom_pack_1ra(base_empresa, int(id_art))
        max_p = calcular_max_packs_armado_1ra(base_empresa, int(id_art), deposito_semi=dep)
        return JsonResponse({"lineas": lineas, "max_packs": max_p})


class ArmadoSurtidoStockOrigenAPIView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """API: artículos con saldo > 0 en depósito origen. GET ?deposito=&q="""

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"articulos": []})
        try:
            deposito = int((request.GET.get("deposito") or "").strip())
        except (TypeError, ValueError):
            return JsonResponse({"articulos": [], "error": "Depósito inválido."})
        q = (request.GET.get("q") or "").strip() or None
        modo_req = (request.GET.get("modo") or "2da").strip().lower()
        tipo_fab = "Fabricado" if modo_req == "2da" else None
        try:
            articulos = listar_articulos_stock_deposito(
                base_empresa, deposito, busqueda=q, limit=50, tipo_art_fab=tipo_fab,
            )
            return JsonResponse({"articulos": articulos})
        except Exception as e:
            logger.warning("API stock origen armado surtido: %s", e, exc_info=True)
            return JsonResponse({"articulos": []})


class ArmadoSurtidoValidarItemLoteAPIView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """
    GET: valida ítem candidato contra lote actual (reglas + stock agregado en origen).
    Query: deposito, lote_json (URL-encoded), item_json (URL-encoded).
    """

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"ok": False, "error": "Empresa no indicada.", "conflictos": []})
        try:
            deposito = int((request.GET.get("deposito") or "").strip())
        except (TypeError, ValueError):
            return JsonResponse({"ok": False, "error": "Depósito inválido.", "conflictos": []})
        raw_item = (request.GET.get("item_json") or "").strip()
        if not raw_item:
            return JsonResponse({"ok": False, "error": "Ítem candidato requerido.", "conflictos": []})
        raw_lote = (request.GET.get("lote_json") or "").strip()
        try:
            item_data = json.loads(raw_item)
        except (TypeError, ValueError, json.JSONDecodeError):
            return JsonResponse({"ok": False, "error": "El ítem candidato no tiene un JSON válido.", "conflictos": []})
        armados: list = []
        if raw_lote:
            try:
                lote_data = json.loads(raw_lote)
            except (TypeError, ValueError, json.JSONDecodeError):
                return JsonResponse({"ok": False, "error": "El lote enviado no tiene un JSON válido.", "conflictos": []})
            if isinstance(lote_data, list):
                lote_payload = {"armados": lote_data}
            elif isinstance(lote_data, dict):
                lote_payload = lote_data
            else:
                return JsonResponse({"ok": False, "error": "Formato de lote inválido.", "conflictos": []})
            armados, err_lote = normalizar_armados_lote_json(lote_payload)
            if err_lote:
                return JsonResponse({"ok": False, "error": err_lote, "conflictos": []})
        item, err_item = normalizar_item_lote_armado_surtido(item_data)
        if err_item or not item:
            return JsonResponse({"ok": False, "error": err_item or "Ítem inválido.", "conflictos": []})
        ok_reg, err_reg = validar_reglas_item_candidato_lote(armados or [], item)
        if not ok_reg:
            return JsonResponse({"ok": False, "error": err_reg, "conflictos": []})
        try:
            ok_stock, conflictos = validar_stock_agregado_lote(
                base_empresa,
                deposito,
                armados or [],
                item_extra=item,
            )
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            return JsonResponse({"ok": False, "error": str(e), "conflictos": []})
        except Exception as e:
            logger.warning("API validar-item-lote armado surtido: %s", e, exc_info=True)
            return JsonResponse({"ok": False, "error": "Error al validar stock del lote.", "conflictos": []})
        return JsonResponse({"ok": bool(ok_stock), "conflictos": conflictos if not ok_stock else []})


class ArmadoSurtidoView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Armado unificado 1ra/2da: solo grilla tabla (?vista=tablero). POS deprecado."""

    template_name = "mpr/armado_tablero.html"

    def get_template_names(self):
        return [self.template_name]

    def get(self, request, *args, **kwargs):
        from django.contrib import messages

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")

        vista_raw = (request.GET.get("vista") or "").strip().lower()
        modo_raw = (request.GET.get("modo") or "").strip()
        # POS deprecado: cualquier vista distinta de tablero (o ausente con modo) → tablero.
        if vista_raw == "pos" or (vista_raw and vista_raw != "tablero") or not modo_raw:
            params = request.GET.copy()
            params["vista"] = "tablero"
            if not (params.get("modo") or "").strip():
                params["modo"] = "1ra"
            return redirect(f"{reverse('mpr:armado')}?{params.urlencode()}")
        return super().get(request, *args, **kwargs)

    def _context_armado_tablero(self, context: Dict[str, Any]) -> Dict[str, Any]:
        from core.utils.administranet_types import to_date_or_none
        from mpr.presentacion_operativa import (
            enriquecer_filas_tablero_armado,
            resolver_modo_presentacion_armado,
        )
        from mpr.services import _fmt_fecha_ddmmaaaa, _parse_fecha_roster_input

        base_empresa = context.get("base_empresa") or _get_base_empresa(self.request)
        modo = context.get("modo") or _modo_armado_desde_request(self.request)
        fecha_desde_str = (self.request.GET.get("fecha_desde") or "").strip()
        fecha_hasta_str = (self.request.GET.get("fecha_hasta") or "").strip()
        solo_resta = _resolver_solo_resta_armado(self.request)
        marcas_incluidos = _parse_marcas_incluidos(self.request)
        modo_presentacion = resolver_modo_presentacion_armado(self.request)

        fecha_realizado_raw = (self.request.GET.get("fecha_realizado") or "").strip()
        fecha_realizado_obj, _err_fecha = _parse_fecha_roster_input(fecha_realizado_raw) if fecha_realizado_raw else (None, None)
        if fecha_realizado_obj is None:
            fecha_realizado_obj = date.today()
        fecha_realizado_ddmm = _fmt_fecha_ddmmaaaa(fecha_realizado_obj)

        try:
            filas = listar_tablero_armado(
                base_empresa,
                modo=modo,
                fecha_desde=to_date_or_none(fecha_desde_str) if fecha_desde_str else None,
                fecha_hasta=to_date_or_none(fecha_hasta_str) if fecha_hasta_str else None,
                solo_resta=solo_resta,
                marcas_incluidos=marcas_incluidos or None,
            )
        except Exception as e:
            logger.warning("listar_tablero_armado: %s", e, exc_info=True)
            filas = []

        try:
            from mpr.services_maquina_linea import enriquecer_filas_tablero_armado_maquina

            filas = enriquecer_filas_tablero_armado_maquina(
                base_empresa,
                filas,
                fecha=fecha_realizado_obj,
            )
        except Exception as e:
            logger.warning("enriquecer_filas_tablero_armado_maquina: %s", e, exc_info=True)

        armados_del_dia: List[Dict[str, Any]] = []
        try:
            armados_del_dia = listar_armados_realizados_por_fecha(
                base_empresa,
                fecha_realizado=fecha_realizado_obj,
                modo=modo,
            )
        except Exception as e:
            logger.warning("listar_armados_realizados_por_fecha: %s", e, exc_info=True)
            armados_del_dia = []

        marcas_catalogo = _context_filtro_marcas(self.request, base_empresa).get(
            "marcas_catalogo", []
        )
        marcas_etiqueta = {
            int(m["value"]): str(m.get("label") or "")
            for m in (marcas_catalogo or [])
            if m.get("value") is not None
        }
        filas = enriquecer_filas_tablero_armado(
            filas, modo_presentacion, marcas_etiqueta=marcas_etiqueta
        )
        kpis_armado = calcular_kpis_tablero_armado(filas)

        dep_origen = (
            get_deposito_semi_elaborado_mpr(base_empresa)
            if modo == "1ra"
            else get_deposito_2da_seleccion_mpr(base_empresa)
        )
        dep_dest = get_deposito_terminado_mpr(base_empresa)
        depositos = get_depositos_con_suma_stock(
            base_empresa, _get_id_puesto(self.request)
        )

        def _nom_dep(cod):
            if cod is None:
                return "—"
            for d in depositos or []:
                if d.get("CodDeposito") == cod:
                    return str_or_default(d.get("NombreDeposito"), str(cod))
            return str(cod)

        qs_params = {
            "vista": "tablero",
            "modo": modo,
            "solo_resta": "1" if solo_resta else "0",
            "presentacion": modo_presentacion,
            "fecha_realizado": fecha_realizado_ddmm,
        }
        if fecha_desde_str:
            qs_params["fecha_desde"] = fecha_desde_str
        if fecha_hasta_str:
            qs_params["fecha_hasta"] = fecha_hasta_str
        presentacion_query_base = _urlencode_con_marcas(qs_params, marcas_incluidos)

        resultado_lote = self.request.session.pop("armado_surtido_resultado_lote", None)
        self.request.session.pop("armado_surtido_lote_fallidos", None)

        context.update({
            "vista": "tablero",
            "filas": filas,
            "fecha_desde": fecha_desde_str,
            "fecha_hasta": fecha_hasta_str,
            "solo_resta": solo_resta,
            "kpis_armado": kpis_armado,
            "modo_presentacion": modo_presentacion,
            "presentacion_query_base": presentacion_query_base,
            "deposito_origen_default": dep_origen,
            "deposito_destino_default": dep_dest,
            "nombre_deposito_origen": _nom_dep(dep_origen),
            "nombre_deposito_destino": _nom_dep(dep_dest),
            "filtros_qs": presentacion_query_base,
            "resultado_lote": resultado_lote,
            "resultado_lote_json": json.dumps(resultado_lote) if resultado_lote else "null",
            "mostrar_modal_resultado_lote": bool(resultado_lote),
            "puede_imputar_pedido": _usuario_puede_imputar_pedido(
                getattr(self.request, "user", None)
            ),
            "fecha_realizado_default": fecha_realizado_ddmm,
            "armados_del_dia": armados_del_dia,
            "armados_del_dia_total_packs": sum(
                int(a.get("cantidad_packs") or 0) for a in armados_del_dia
            ),
            **_context_filtro_marcas(self.request, base_empresa),
        })
        return context

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        modo = _modo_armado_desde_request(self.request)
        context["modo"] = modo
        context["modo_label"] = "Armado 1ra" if modo == "1ra" else "Armado 2da"
        context["base_empresa"] = base_empresa
        context["vista"] = "tablero"
        context["id_lista"] = to_int_or_none(self.request.GET.get("id_lista"))
        return self._context_armado_tablero(context)


    def post(self, request, *args, **kwargs):
        from django.contrib import messages

        base_empresa = _get_base_empresa(request)
        modo = _modo_armado_desde_request(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return _redirect_armado(modo, request=request)
        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        if not id_usuario:
            messages.error(request, "Usuario no identificado en sesión.")
            return _redirect_armado(modo, request=request)

        cabecera, armados, err_parse = _resolver_post_armado_surtido(request)
        cabecera["modo"] = modo
        accion = str_or_default(cabecera.get("accion"), "aprobar").strip().lower()
        id_lista = cabecera.get("id_lista_produccion") or to_int_or_none(
            request.POST.get("id_lista") or request.GET.get("id_lista")
        )

        if accion == "anular":
            id_lote_anular = to_int_or_none(
                request.POST.get("id_mpr_armado_lote") or cabecera.get("id_mpr_armado_lote")
            )
            if not id_lote_anular:
                messages.error(request, "Indique el lote a anular.")
                return _redirect_armado(modo, id_lista, request=request)
            try:
                ok_an, errs_an = anular_lote_armado(base_empresa, id_usuario, id_lote_anular)
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                messages.error(request, str(e))
                return _redirect_armado(modo, id_lista, request=request)
            if ok_an:
                messages.success(request, "Lote de armado anulado correctamente.")
            else:
                messages.error(request, "; ".join(errs_an) if errs_an else "No se pudo anular el lote.")
            return _redirect_armado(modo, id_lista, request=request)

        if err_parse:
            messages.error(request, err_parse)
            return _redirect_armado(modo, id_lista, request=request)

        ok_reg, err_reg = validar_reglas_lote_armado(
            armados,
            modo=modo,
            deposito_origen=cabecera.get("deposito_origen"),
            deposito_destino=cabecera.get("deposito_destino"),
            id_operario=cabecera.get("id_operario"),
            require_non_empty=True,
            base_empresa=base_empresa,
        )
        if not ok_reg:
            messages.error(request, err_reg)
            return _redirect_armado(modo, id_lista, request=request)

        try:
            resultado = ejecutar_lote_armado(
                base_empresa,
                id_usuario,
                cabecera,
                armados,
            )
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            messages.error(request, str(e))
            return _redirect_armado(modo, id_lista, request=request)

        exitosos = resultado.get("exitosos") or []
        fallidos = resultado.get("fallidos") or []
        n_ok = len(exitosos)
        n_fail = len(fallidos)

        if accion == "borrador" and not fallidos:
            messages.success(request, "Borrador de armado guardado correctamente.")
        # aprobar: feedback solo en modal Synap del tablero (sin toast ni detalle de ítems).

        if n_ok or n_fail:
            request.session["armado_surtido_resultado_lote"] = resultado
            request.session["armado_surtido_lote_fallidos"] = _fallidos_para_carrito_armado_surtido(fallidos)

        return _redirect_armado(modo, id_lista, request=request)


# Vista canónica (menú Armado 1ra / 2da)
ArmadoView = ArmadoSurtidoView


class ArmadoSurtidoRedirectView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """Alias legacy /mpr/armado-surtido/ → /mpr/armado/?modo=2da."""

    def get(self, request, *args, **kwargs):
        id_lista = to_int_or_none(request.GET.get("id_lista"))
        return _redirect_armado("2da", id_lista)

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)


def _agrupar_mstock_por_lote(pendientes: list) -> list:
    """Agrupa MSTOCK pendientes por id_lote_armado para la UI."""
    lotes_map: dict = {}
    sin_lote: list = []
    for item in pendientes or []:
        lid = item.get("id_lote_armado")
        if lid:
            if lid not in lotes_map:
                lotes_map[lid] = {
                    "id_lote_armado": lid,
                    "ejecutado_en": item.get("lote_ejecutado_en"),
                    "movimientos": [],
                }
            lotes_map[lid]["movimientos"].append(item)
        else:
            sin_lote.append(item)
    lotes = sorted(
        lotes_map.values(),
        key=lambda x: x.get("ejecutado_en") or datetime.min,
        reverse=True,
    )
    if sin_lote:
        lotes.append({
            "id_lote_armado": None,
            "ejecutado_en": None,
            "movimientos": sin_lote,
        })
    return lotes


def _redirect_imputacion_pedido(request, codigo_movimiento=None, id_lote_armado=None):
    """Redirige a Imputación de pedido conservando MSTOCK/lote en query string."""
    params = {}
    if codigo_movimiento is not None:
        params["codigo_movimiento"] = int(codigo_movimiento)
    lote = (id_lote_armado or request.GET.get("id_lote_armado") or "").strip()
    if not lote and request.method == "POST":
        lote = (request.POST.get("id_lote_armado") or "").strip()
    if lote:
        params["id_lote_armado"] = lote
    url = reverse("mpr:imputacion_armado_1ra")
    if params:
        url = f"{url}?{urlencode(params)}"
    return redirect(url)


class ImputacionArmadoSugerirAPIView(MprLoginRequiredMixin, MprPermisoMixin, View):
    """API: sugerencia FIFO de imputación para un MSTOCK 1ra."""

    permiso_requerido = "mpr.imputar_armado_1ra"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"lineas": [], "error": "Empresa no indicada."})
        cod = to_int_or_none(request.GET.get("codigo_movimiento"))
        if not cod:
            return JsonResponse({"lineas": [], "error": "Movimiento requerido."})
        lineas, err = sugerir_imputacion_fifo(base_empresa, int(cod))
        if err:
            return JsonResponse({"lineas": [], "error": err})
        return JsonResponse({"lineas": lineas})


class ImputacionArmadoConfirmarAPIView(MprLoginRequiredMixin, MprPermisoMixin, View):
    """API POST: confirma imputación FIFO (o líneas explícitas) para un MSTOCK 1ra."""

    permiso_requerido = "mpr.imputar_armado_1ra"

    def post(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"ok": False, "error": "Empresa no indicada."}, status=400)

        session_user = request.session.get("user", {})
        try:
            id_supervisor = int(session_user.get("id_usuario"))
        except (TypeError, ValueError):
            id_supervisor = None
        if not id_supervisor:
            return JsonResponse({"ok": False, "error": "Usuario no identificado."}, status=400)

        try:
            body = json.loads((request.body or b"").decode() or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            body = {}

        cod = to_int_or_none(body.get("codigo_movimiento"))
        if not cod:
            return JsonResponse({"ok": False, "error": "Movimiento requerido."}, status=400)

        lineas = body.get("lineas")
        if not isinstance(lineas, list):
            lineas = []
        if not lineas and body.get("usar_fifo", True):
            lineas, err_fifo = sugerir_imputacion_fifo(base_empresa, int(cod))
            if err_fifo:
                return JsonResponse({"ok": False, "error": err_fifo}, status=400)
            if not lineas:
                return JsonResponse(
                    {"ok": False, "error": "No hay demanda abierta para imputar."},
                    status=400,
                )

        if not lineas:
            return JsonResponse(
                {"ok": False, "error": "Indique al menos una línea de imputación."},
                status=400,
            )

        lineas_norm: list = []
        for ln in lineas:
            if not isinstance(ln, dict):
                continue
            qty = int(to_int_or_none(ln.get("cantidad")) or 0)
            cod_ped = to_int_or_none(ln.get("codigo_movimiento_pedido"))
            if not cod_ped or qty <= 0:
                continue
            lineas_norm.append({
                "codigo_movimiento_pedido": int(cod_ped),
                "cantidad": qty,
                "origen_regla": (ln.get("origen_regla") or "FIFO").strip() or "FIFO",
                "id_lista_detalle": to_int_or_none(ln.get("id_lista_detalle")),
                "id_lista_produccion": to_int_or_none(ln.get("id_lista_produccion")),
                "notas": str_or_default(ln.get("notas"), "").strip(),
            })

        if not lineas_norm:
            return JsonResponse(
                {"ok": False, "error": "Líneas de imputación inválidas."},
                status=400,
            )

        try:
            ok, err = confirmar_imputacion_armado(
                base_empresa,
                int(cod),
                lineas_norm,
                id_supervisor,
            )
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            return JsonResponse({"ok": False, "error": str(e)}, status=400)

        if not ok:
            return JsonResponse(
                {"ok": False, "error": err or "No se pudo confirmar la imputación."},
                status=400,
            )

        total = sum(ln["cantidad"] for ln in lineas_norm)
        return JsonResponse({
            "ok": True,
            "cantidad_imputada": total,
            "mensaje": f"Imputación confirmada ({total} u.).",
        })


class ImputacionArmado1raView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Imputación de pedido: asigna MSTOCK Armado 1ra a pedidos con demanda abierta."""

    template_name = "mpr/imputacion_armado_1ra.html"
    permiso_requerido = "mpr.imputar_armado_1ra"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages

            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        context["base_empresa"] = base_empresa
        lote_sel = (self.request.GET.get("id_lote_armado") or "").strip() or None
        id_art_sel = to_int_or_none(self.request.GET.get("id_articulo"))
        context["lote_armado_sel"] = lote_sel
        context["id_articulo_sel"] = id_art_sel
        context["filtrado_por_lote"] = bool(lote_sel)
        context["filtrado_por_articulo"] = bool(id_art_sel)
        filtros: Dict[str, Any] = {}
        if lote_sel:
            filtros["id_lote_armado"] = lote_sel
        if id_art_sel:
            filtros["id_articulo_pack"] = id_art_sel
        pendientes = listar_mstock_pendientes_imputacion(
            base_empresa, filtros=filtros or None
        )
        context["lotes_pendientes"] = _agrupar_mstock_por_lote(pendientes)
        context["total_pendientes"] = len(pendientes)
        context["sugerir_api_url"] = reverse("mpr:api_imputacion_armado_sugerir")
        cod_sel = to_int_or_none(self.request.GET.get("codigo_movimiento"))
        if not cod_sel and pendientes:
            if lote_sel or id_art_sel:
                cod_sel = pendientes[0].get("codigo_movimiento")
                if not lote_sel and pendientes[0].get("id_lote_armado"):
                    lote_sel = pendientes[0].get("id_lote_armado")
                    context["lote_armado_sel"] = lote_sel
                    context["filtrado_por_lote"] = True
        context["codigo_movimiento_sel"] = cod_sel
        if cod_sel:
            sugerencias, err = sugerir_imputacion_fifo(base_empresa, int(cod_sel))
            context["sugerencias_fifo"] = sugerencias
            context["sugerencias_fifo_json"] = json.dumps(sugerencias or [], ensure_ascii=False)
            context["sugerencias_error"] = err
        else:
            context["sugerencias_fifo"] = []
            context["sugerencias_fifo_json"] = "[]"
            context["sugerencias_error"] = None
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages

        base_empresa = _get_base_empresa(request)
        lote_post = (request.POST.get("id_lote_armado") or "").strip() or None
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return _redirect_imputacion_pedido(
                request,
                codigo_movimiento=to_int_or_none(request.POST.get("codigo_movimiento")),
                id_lote_armado=lote_post,
            )

        session_user = request.session.get("user", {})
        try:
            id_supervisor = int(session_user.get("id_usuario"))
        except (TypeError, ValueError):
            id_supervisor = None
        if not id_supervisor:
            messages.error(request, "Usuario no identificado en sesión.")
            return _redirect_imputacion_pedido(
                request,
                codigo_movimiento=to_int_or_none(request.POST.get("codigo_movimiento")),
                id_lote_armado=lote_post,
            )

        cod = to_int_or_none(request.POST.get("codigo_movimiento"))
        raw_lineas = (request.POST.get("lineas_json") or "").strip()
        lineas: list = []
        if raw_lineas:
            try:
                parsed = json.loads(raw_lineas)
                lineas = parsed if isinstance(parsed, list) else []
            except (TypeError, ValueError, json.JSONDecodeError):
                messages.error(request, "Formato de líneas de imputación inválido.")
                return _redirect_imputacion_pedido(
                    request, codigo_movimiento=cod, id_lote_armado=lote_post
                )

        if not lineas:
            accion = (request.POST.get("accion") or "").strip()
            if accion == "sugerir_fifo" and cod:
                return _redirect_imputacion_pedido(
                    request, codigo_movimiento=cod, id_lote_armado=lote_post
                )
            messages.error(request, "Indique al menos una línea de imputación.")
            return _redirect_imputacion_pedido(
                request, codigo_movimiento=cod, id_lote_armado=lote_post
            )

        try:
            ok, err = confirmar_imputacion_armado(
                base_empresa,
                int(cod or 0),
                lineas,
                id_supervisor,
            )
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            messages.error(request, str(e))
            return _redirect_imputacion_pedido(
                request, codigo_movimiento=cod, id_lote_armado=lote_post
            )

        if ok:
            messages.success(request, "Imputación confirmada correctamente.")
        else:
            messages.error(request, err or "No se pudo confirmar la imputación.")
        return _redirect_imputacion_pedido(
            request,
            codigo_movimiento=None if ok else cod,
            id_lote_armado=lote_post if not ok else None,
        )


_MESES_ES_LARGO = [
    "", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre",
]


def _agrupar_resumen_por_mes(dias: List[Dict[str, Any]], modo: str) -> List[Dict[str, Any]]:
    """Agrupa el resumen diario por Año/Mes con subtotal de producción (parte).

    Réplica del pivote «Produccion Diario» (Origen=Producción): filas por día con
    subtotal por mes y total. Consolida la cantidad registrada (parte) por día.
    """
    from mpr.reportes_presentacion import formatear_cantidad_reporte

    grupos: List[Dict[str, Any]] = []
    actual: Optional[Dict[str, Any]] = None
    for d in dias:
        # Solo días con producción registrada (como el pivote «Produccion Diario»).
        if int(d.get("parte") or 0) <= 0:
            continue
        f = d.get("fecha")
        anio = getattr(f, "year", 0)
        mes = getattr(f, "month", 0)
        if actual is None or actual["anio"] != anio or actual["mes"] != mes:
            etiqueta = f"{_MESES_ES_LARGO[mes]} {anio}" if 1 <= mes <= 12 else str(anio)
            actual = {"anio": anio, "mes": mes, "mes_label": etiqueta, "dias": [], "subtotal": 0}
            grupos.append(actual)
        actual["dias"].append(d)
        actual["subtotal"] += int(d.get("parte") or 0)
    for g in grupos:
        g["subtotal_display"] = formatear_cantidad_reporte(g["subtotal"], modo)
    return grupos


class ReportesMPRView(MprLoginRequiredMixin, MprReportesVerMixin, TemplateView):
    """Hub de reportes MPR: producción, demanda y trazabilidad (flujo MPR diario)."""

    template_name = "mpr/reportes.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        # Inventario por depósito vive en el catálogo Reportes (oleada 1).
        grupo_q = (request.GET.get("grupo") or "").strip()
        reporte_q = (request.GET.get("reporte") or "").strip()
        if grupo_q == "demanda" and reporte_q == "inventario_deposito":
            from django.urls import reverse

            return redirect(
                reverse(
                    "reports:dashboard_detail",
                    kwargs={"slug": "inventario-deposito-articulo"},
                )
            )
        if (request.GET.get("format") or "").strip().lower() == "csv":
            ctx = self.get_context_data(**kwargs)
            return self._respuesta_csv(ctx)
        if (request.GET.get("format") or "").strip().lower() == "xlsx":
            ctx = self.get_context_data(**kwargs)
            return self._respuesta_xlsx(ctx)
        return super().get(request, *args, **kwargs)

    def _respuesta_csv(self, context: Dict[str, Any]) -> HttpResponse:
        from mpr.export import analisis_trazabilidad_a_csv, filas_a_csv
        from mpr.reportes_hub import columnas_csv_para_modo

        grupo = context.get("grupo") or "produccion"
        reporte = context.get("reporte") or "resumen_diario"
        modo = context.get("modo_presentacion") or "docenas"
        titulo = context.get("titulo_reporte") or "reporte_mpr"

        if grupo == "trazabilidad" and reporte == "kardex_articulo":
            analisis = context.get("_analisis_trazabilidad")
            if not analisis:
                meta = context.get("meta") or {}
                analisis = {
                    "articulo": meta.get("articulo"),
                    "demanda_ped": meta.get("demanda_ped") or {"filas": [], "totales": {"p_ped": 0}},
                    "stock": meta.get("stock") or {"terminado": 0, "negativo": False},
                    "brechas": meta.get("brechas") or {},
                    "a_producir": meta.get("a_producir") or {},
                    "saldo_inicial": meta.get("saldo_inicial") or {},
                    "movimientos": context.get("filas") or [],
                    "eventos_mpr": meta.get("eventos_mpr") or [],
                    "kpis": context.get("kpis") or {},
                }
            payload = analisis_trazabilidad_a_csv(
                analisis,
                modo=modo,
                fecha_desde_display=context.get("fecha_desde_display") or "",
                fecha_hasta_display=context.get("fecha_hasta_display") or "",
            )
            nombre = "analisis_trazabilidad.csv"
            resp = HttpResponse(payload, content_type="text/csv; charset=utf-8")
            resp["Content-Disposition"] = f'attachment; filename="{nombre}"'
            return resp

        columnas = columnas_csv_para_modo(grupo, reporte, modo)
        if not columnas:
            return HttpResponse("Exportación no disponible para este reporte.", status=400)
        filas = context.get("filas") or context.get("dias") or []
        nombre = f"{titulo.replace(' ', '_').lower()}.csv"
        payload = filas_a_csv(filas, columnas)
        resp = HttpResponse(payload, content_type="text/csv; charset=utf-8")
        resp["Content-Disposition"] = f'attachment; filename="{nombre}"'
        return resp

    def _respuesta_xlsx(self, context: Dict[str, Any]) -> HttpResponse:
        from mpr.export import exportar_inventario_deposito_xlsx
        from mpr.reportes_hub import reporte_soporta_export_xlsx

        grupo = context.get("grupo") or "produccion"
        reporte = context.get("reporte") or "resumen_diario"
        if not reporte_soporta_export_xlsx(grupo, reporte):
            return HttpResponse("Exportación Excel no disponible para este reporte.", status=400)

        if grupo == "demanda" and reporte == "inventario_deposito":
            fecha_corte = context.get("fecha_corte_iso")
            fecha_obj = None
            if fecha_corte:
                try:
                    from datetime import datetime

                    fecha_obj = datetime.strptime(str(fecha_corte)[:10], "%Y-%m-%d").date()
                except (ValueError, TypeError):
                    fecha_obj = None
            return exportar_inventario_deposito_xlsx(
                context.get("filas") or [],
                total_docenas=float(context.get("total_docenas") or 0),
                fecha_corte=fecha_obj,
                titulo=context.get("titulo_reporte") or "Inventario por depósito",
            )
        return HttpResponse("Exportación Excel no implementada para este reporte.", status=400)

    def get_context_data(self, **kwargs):
        from mpr.reportes_hub import (
            GRUPOS_REPORTES,
            PARTIALS,
            parse_periodo,
            reporte_soporta_export_xlsx,
            resolver_grupo_reporte,
            titulo_reporte,
        )

        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        get_params = {k: self.request.GET.get(k, "") for k in self.request.GET}
        grupo, reporte = resolver_grupo_reporte(get_params)
        periodo = parse_periodo(
            self.request.GET.get("desde") or self.request.GET.get("fecha_desde"),
            self.request.GET.get("hasta") or self.request.GET.get("fecha_hasta"),
        )
        fd_iso = periodo["fecha_desde_iso"]
        fh_iso = periodo["fecha_hasta_iso"]

        context.update({
            "base_empresa": base_empresa,
            "grupo": grupo,
            "reporte": reporte,
            "grupos_reportes": GRUPOS_REPORTES,
            "reportes_nav": GRUPOS_REPORTES.get(grupo, {}).get("reportes", {}),
            "titulo_reporte": titulo_reporte(grupo, reporte),
            "partial_template": PARTIALS.get((grupo, reporte), ""),
            "soporta_export_xlsx": reporte_soporta_export_xlsx(grupo, reporte),
            **periodo,
        })
        context["tipo_reporte"] = f"{grupo}_{reporte}"

        kpis: Dict[str, Any] = {}
        filas: List[Any] = []
        filas_stock_raw: List[Any] = []
        dias: List[Any] = []
        eventos: List[Any] = []
        totales: Dict[str, Any] = {}
        meta: Dict[str, Any] = {}

        if grupo == "produccion" and reporte == "resumen_diario":
            data = reporte_mpr_resumen_diario(base_empresa, fd_iso, fh_iso)
            kpis = data.get("kpis") or {}
            dias = data.get("dias") or []
            totales = data.get("totales") or {}
            filas = dias
        elif grupo == "produccion" and reporte == "operario":
            data = reporte_mpr_operario_parte(base_empresa, fd_iso, fh_iso)
            kpis = data.get("kpis") or {}
            filas = data.get("filas") or []
        elif grupo == "produccion" and reporte == "operario_mensual":
            from mpr.services import reporte_mpr_operario_mensual
            from mpr.reportes_presentacion import resolver_modo_presentacion_reporte

            modo_pivote = resolver_modo_presentacion_reporte(self.request)
            sel_raw = self.request.GET.get("op") or ""
            seleccionados = [
                int(x) for x in sel_raw.split(",")
                if x.strip().lstrip("-").isdigit()
            ][:2]
            data = reporte_mpr_operario_mensual(
                base_empresa, fd_iso, fh_iso,
                seleccionados=seleccionados, modo=modo_pivote,
            )
            kpis = data.get("kpis") or {}
            filas = data.get("filas") or []
            context["pivote_operario"] = data
        elif grupo == "produccion" and reporte == "operario_maquina":
            from mpr.services import reporte_mpr_operario_maquina
            data = reporte_mpr_operario_maquina(base_empresa, fd_iso, fh_iso)
            kpis = data.get("kpis") or {}
            filas = data.get("filas") or []
        elif grupo == "produccion" and reporte == "cadena":
            data = reporte_mpr_cadena_pipeline(base_empresa, fd_iso, fh_iso)
            kpis = data.get("kpis") or {}
            filas = data.get("filas") or []
        elif grupo == "produccion" and reporte == "pendiente":
            data = reporte_mpr_pendiente_componentes(base_empresa)
            kpis = data.get("kpis") or {}
            filas = data.get("filas") or []
        elif grupo == "demanda" and reporte == "brecha_pack":
            filas = reporte_mpr_brecha_demanda(
                base_empresa,
                fecha_desde=periodo["fecha_desde"],
                fecha_hasta=periodo["fecha_hasta"],
            )
            kpis = {
                "packs_brecha": len(filas),
                "unidades_faltantes": int(sum(float(r.get("cantidad_a_fabricar") or 0) for r in filas)),
                "packs_urgentes": sum(1 for r in filas if r.get("urgente")),
            }
        elif grupo == "demanda" and reporte == "pedidos_estado":
            filas = reporte_mpr_pedidos_por_estado(base_empresa)
            kpis = {"pedidos": len(filas)}
        elif grupo == "demanda" and reporte == "stock":
            filas_stock_raw = reporte_mpr_stock(base_empresa, limit=500)
        elif grupo == "demanda" and reporte == "inventario_deposito":
            from mpr.services_inventario_deposito import (
                consultar_inventario_deposito,
                parse_filtros_inventario_deposito,
            )
            from stock.services.inventario_tabla import listar_marcas_catalogo

            try:
                context["depositos"] = listar_depositos_config(base_empresa)
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                context["depositos"] = []
            context["marcas_catalogo"] = listar_marcas_catalogo(base_empresa)
            get_marcas = (
                self.request.GET.getlist("marcas_incluidos")
                if hasattr(self.request.GET, "getlist")
                else []
            )
            filtros_inv = parse_filtros_inventario_deposito(
                self.request.GET,
                marcas_getlist=get_marcas,
            )
            context["filtros_inventario_deposito"] = filtros_inv
            context["fecha_corte_iso"] = filtros_inv.fecha_corte.isoformat()
            context["fecha_corte_display"] = filtros_inv.fecha_corte.strftime("%d/%m/%Y")
            from django.http import QueryDict

            export_q = QueryDict(mutable=True)
            if hasattr(self.request.GET, "lists"):
                for key in self.request.GET:
                    for val in self.request.GET.getlist(key):
                        export_q.appendlist(key, val)
            elif isinstance(self.request.GET, dict):
                for key, val in self.request.GET.items():
                    if isinstance(val, list):
                        for item in val:
                            export_q.appendlist(key, item)
                    else:
                        export_q[key] = val
            export_q.pop("format", None)
            context["inventario_export_query"] = export_q.urlencode()
            inv_raw = consultar_inventario_deposito(base_empresa, filtros_inv)
            meta = {
                "fecha_corte": filtros_inv.fecha_corte,
                "incluir_2da": filtros_inv.incluir_2da,
                "advertencias": [],
            }
            if inv_raw.get("advertencia_fecha"):
                meta["advertencias"].append(inv_raw["advertencia_fecha"])
            kpis = inv_raw.get("kpis") or {}
            filas = inv_raw.get("filas") or []
            totales = {"total_docenas": inv_raw.get("total_docenas") or 0}
            context["_inventario_deposito_raw"] = inv_raw
            context["meta"] = meta
        elif grupo == "demanda" and reporte == "bajo_minimo":
            filas = reporte_mpr_bajo_minimo(base_empresa)
        elif grupo == "trazabilidad" and reporte == "timeline":
            from core.utils.administranet_types import to_int_or_none
            from mpr.services_kardex_articulo import construir_analisis_trazabilidad_articulo

            id_art = to_int_or_none(self.request.GET.get("id_articulo"))
            meta = {
                "id_articulo": id_art,
                "id_deposito": None,
                "codigo_articulo": "",
                "descripcion_articulo": "",
                "eventos_mpr": [],
            }
            eventos = []
            kpis = {"eventos": 0}
            if id_art is not None:
                data = construir_analisis_trazabilidad_articulo(
                    base_empresa,
                    id_art,
                    fecha_desde=fd_iso,
                    fecha_hasta=fh_iso,
                )
                articulo = data.get("articulo") or {}
                meta["articulo"] = articulo
                meta["codigo_articulo"] = articulo.get("codigo") or ""
                meta["descripcion_articulo"] = articulo.get("descripcion") or ""
                meta["eventos_mpr"] = data.get("eventos_mpr") or []
                eventos = meta["eventos_mpr"]
                kpis = data.get("kpis") or {"eventos": len(eventos)}
                kpis.setdefault("eventos", len(eventos))
                context["_analisis_trazabilidad"] = data
        elif grupo == "trazabilidad" and reporte == "movimientos":
            filas = reporte_mpr_movimientos(base_empresa, fd_iso, fh_iso)
            kpis = {"eventos": len(filas)}
        elif grupo == "trazabilidad" and reporte == "conciliacion":
            from mpr.services import reporte_mpr_conciliacion_envios_produccion
            data = reporte_mpr_conciliacion_envios_produccion(base_empresa, fd_iso, fh_iso)
            kpis = data.get("kpis") or {}
            filas = data.get("filas") or []
        elif grupo == "trazabilidad" and reporte == "kardex_articulo":
            from core.utils.administranet_types import to_int_or_none
            from mpr.services_kardex_articulo import construir_analisis_trazabilidad_articulo

            id_art = to_int_or_none(self.request.GET.get("id_articulo"))

            meta = {
                "id_articulo": id_art,
                "id_deposito": None,
                "advertencias": [],
                "demanda_ped": {"filas": [], "totales": {"p_ped": 0}},
                "stock": {"terminado": 0, "semi_componentes": [], "negativo": False},
                "brechas": {
                    "ped_urgente": 0,
                    "tot_urgente": 0,
                    "reserva": 0,
                    "texto_explicativo": "",
                },
                "a_producir": {
                    "cantidad": 0,
                    "capacidad_semi": 0,
                    "alerta_semi_cero": False,
                },
                "saldo_inicial": {"valor": 0, "calculado_ok": False},
                "eventos_mpr": [],
            }
            if id_art is not None:
                data = construir_analisis_trazabilidad_articulo(
                    base_empresa,
                    id_art,
                    fecha_desde=fd_iso,
                    fecha_hasta=fh_iso,
                )
                meta["articulo"] = data.get("articulo")
                meta["bom"] = data.get("bom")
                meta["deposito"] = data.get("deposito")
                if meta["deposito"]:
                    meta["id_deposito"] = meta["deposito"].get("id")
                    meta["ids_deposito"] = meta["deposito"].get("ids") or []
                meta["advertencias"] = data.get("advertencias") or []
                meta["demanda_ped"] = data.get("demanda_ped") or meta["demanda_ped"]
                meta["stock"] = data.get("stock") or meta["stock"]
                meta["brechas"] = data.get("brechas") or meta["brechas"]
                meta["a_producir"] = data.get("a_producir") or meta["a_producir"]
                meta["saldo_inicial"] = data.get("saldo_inicial") or meta["saldo_inicial"]
                meta["eventos_mpr"] = data.get("eventos_mpr") or []
                if data.get("articulo"):
                    kpis = data.get("kpis") or {}
                    filas = data.get("movimientos") or []
                    opp_rows = [
                        m for m in filas if int(m.get("entrada") or 0) > 0
                    ]
                    opa_rows = [
                        m for m in filas if int(m.get("salida") or 0) > 0
                    ]
                    context["renglones_por_movimiento"] = renglones_map = _build_renglones_modal_map(
                        base_empresa, opp_rows, opa_rows
                    )
                    for mov in filas:
                        if mov.get("clase_ui") != "opa":
                            continue
                        cm = mov.get("codigo_movimiento")
                        if cm is None:
                            continue
                        grupo = renglones_map.get(str(cm)) or {}
                        articulos = grupo.get("articulos") or []
                        if articulos:
                            mov["subfilas_opa"] = articulos
                else:
                    filas = []
                    kpis = {}
                context["_analisis_trazabilidad"] = data

        from mpr.reportes_presentacion import (
            aplicar_presentacion_reporte,
            resolver_modo_presentacion_reporte,
        )

        modo_presentacion = resolver_modo_presentacion_reporte(self.request)

        if grupo == "demanda" and reporte == "stock":
            from mpr.reportes_presentacion import preparar_stock_por_deposito

            stock_ctx = preparar_stock_por_deposito(
                filas_stock_raw, modo_presentacion, base_empresa
            )
            filas_stock = stock_ctx["filas"]
            filas_busqueda = [
                {
                    "codigo": str(f.get("codigo_manual") or f.get("codigo_articulo") or ""),
                    "descripcion": str(f.get("descripcion_articulo") or ""),
                }
                for f in filas_stock
            ]
            reporte_ctx = {
                "kpis": kpis,
                "filas": filas_stock,
                "columnas_deposito": stock_ctx["columnas_deposito"],
                "filas_busqueda": filas_busqueda,
                "total_filas_tabla": len(filas_stock),
                "dias": dias,
                "eventos": eventos,
                "totales": totales,
                "meta": meta,
                "modo_presentacion": modo_presentacion,
                "etiqueta_cantidad": (
                    "docenas · unidades" if modo_presentacion == "docenas" else "unidades"
                ),
                "etiqueta_cantidad_corta": (
                    "doc. · u." if modo_presentacion == "docenas" else "u."
                ),
            }
        elif grupo == "demanda" and reporte == "inventario_deposito":
            from mpr.reportes_presentacion import preparar_inventario_deposito_presentacion

            inv_raw = context.pop("_inventario_deposito_raw", {})
            inv_ctx = preparar_inventario_deposito_presentacion(inv_raw, modo_presentacion)
            reporte_ctx = {
                "kpis": kpis,
                "filas": inv_ctx["filas"],
                "depositos_jerarquia": inv_ctx["depositos_jerarquia"],
                "total_docenas": inv_ctx["total_docenas"],
                "total_docenas_display": inv_ctx["total_docenas_display"],
                "fecha_corte_display": inv_ctx["fecha_corte_display"],
                "usa_stock_deposito": inv_ctx["usa_stock_deposito"],
                "advertencia_fecha": inv_ctx.get("advertencia_fecha"),
                "dias": dias,
                "eventos": eventos,
                "totales": totales,
                "meta": meta,
                "modo_presentacion": modo_presentacion,
                "empty_titulo": (
                    "No hay stock para los filtros seleccionados. "
                    "Probá ampliar depósito, marca o activar «Incluir 2da selección»."
                ),
            }
        else:
            reporte_ctx = {
                "kpis": kpis,
                "filas": filas,
                "dias": dias,
                "eventos": eventos,
                "totales": totales,
                "meta": meta,
            }
            reporte_ctx = aplicar_presentacion_reporte(
                reporte_ctx, modo_presentacion, base_empresa
            )
        if grupo == "produccion":
            from mpr.reportes_charts import build_charts_produccion

            charts = build_charts_produccion(reporte, reporte_ctx)
            if charts:
                reporte_ctx["mpr_charts"] = charts
        context.update(reporte_ctx)
        if grupo == "produccion" and reporte == "resumen_diario":
            context["meses_resumen"] = _agrupar_resumen_por_mes(
                context.get("dias") or [], modo_presentacion
            )
        return context


class VentanaPackActualizarView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """POST: ejecuta actualizar_pedidos_produccion y redirige a Orden de Producción de Trabajo (OPT) con mensaje."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:ventana_pack")
        fecha_desde = (request.POST.get("fecha_desde") or "").strip() or None
        fecha_hasta = (request.POST.get("fecha_hasta") or "").strip() or None
        busqueda = (request.POST.get("busqueda") or "").strip() or None
        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        try:
            ok, msg = actualizar_pedidos_produccion(
                base_empresa,
                id_usuario=id_usuario,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                busqueda=busqueda,
            )
        except MprSchemaError as e:
            return _mpr_schema_error_redirect(request, e)
        request.session["ventana_pack_filtros_actualizar"] = {
            "fecha_desde": fecha_desde or "",
            "fecha_hasta": fecha_hasta or "",
            "busqueda": busqueda or "",
        }
        if ok:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect("mpr:ventana_pack")


class EmpleadosOperariosAPIView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """API para búsqueda de operarios (sue_abm_empleado) en Confirmar OPT. GET ?q=busqueda."""

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"empleados": []})
        try:
            q = (request.GET.get("q") or "").strip()
            empleados = listar_empleados_operarios(base_empresa, busqueda=q or None, limit=50)
            return JsonResponse({"empleados": empleados})
        except Exception as e:
            logger.warning("Error API empleados operarios: %s", e, exc_info=True)
            return JsonResponse({"empleados": []})


def _tiene_receta(fila: dict) -> bool:
    """True si el pack tiene BOM (receta_json decodifica a lista no vacía)."""
    raw = fila.get("receta_json")
    if not raw:
        return False
    try:
        receta = json.loads(raw)
    except (ValueError, TypeError):
        return False
    return isinstance(receta, list) and len(receta) > 0


class VentanaPackAgruparView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Pantalla 2: recibe selección desde Orden de Producción de Trabajo (OPT), muestra tabla con cantidades editables y tooltip; POST 'Generar OPT' crea la OPT."""

    template_name = "mpr/ventana_pack_agrupar.html"

    def get(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        seleccion = request.session.get("ventana_pack_seleccion")
        if not seleccion or not seleccion.get("filas"):
            messages.info(request, "No hay selección. Elija artículos en Orden de Producción de Trabajo (OPT) y pulse Continuar.")
            return redirect("mpr:ventana_pack")
        # Solo al cargar la pantalla por GET: descartar mensajes previos (Actualizar, Continuar, etc.).
        # Las validaciones/errores se muestran solo al hacer clic en «Generar OPT» (POST).
        if request.method == "GET":
            list(messages.get_messages(request))
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:ventana_pack")
        # ¿Viene de Pantalla 1 (sel + cant_*) o es "Generar OPT"?
        accion = (request.POST.get("accion") or "").strip()
        if accion == "generar_opt":
            seleccion = request.session.get("ventana_pack_seleccion")
            if not seleccion or not seleccion.get("filas"):
                messages.error(request, "La selección expiró. Vuelva a Orden de Producción de Trabajo (OPT) y seleccione de nuevo.")
                return redirect("mpr:ventana_pack")
            # OPT se genera por pack (lista_produccion_agrupada tiene id_articulo = pack).
            # El formulario muestra unidades (componentes); mapeamos cantidades/operario al pack.
            lineas = lineas_opt_desde_formulario_unidades(base_empresa, seleccion["filas"], request.POST)
            if not lineas:
                messages.error(request, "Indique al menos un artículo con cantidad mayor a 0.")
                return self.get(request, *args, **kwargs)
            session_user = request.session.get("user", {})
            try:
                id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
            except (TypeError, ValueError):
                id_usuario = None
            fecha_objetivo = None
            raw_fecha = (request.POST.get("fecha_objetivo") or "").strip()
            if raw_fecha:
                try:
                    fecha_objetivo = datetime.strptime(raw_fecha, "%Y-%m-%d").date()
                    if fecha_objetivo < date.today():
                        messages.error(request, "La fecha objetivo no puede ser anterior a la fecha de hoy.")
                        return self.get(request, *args, **kwargs)
                except (ValueError, TypeError):
                    pass
            try:
                ok, id_lista_principal, error = crear_opt_multiples_articulos(
                    base_empresa, id_usuario, lineas, fecha_objetivo=fecha_objetivo
                )
            except MprSchemaError as e:
                return _mpr_schema_error_redirect(request, e)
            if ok and id_lista_principal:
                if "ventana_pack_seleccion" in request.session:
                    del request.session["ventana_pack_seleccion"]
                # Inmediatamente después de Crear OPT: ejecutar Liberar OPT (depósito con tipo Producción)
                liberada = False
                nro_comp_liberada = None
                lineas_detalle = []
                deposito_produccion = get_deposito_produccion_mpr(base_empresa)
                if deposito_produccion:
                    lineas_detalle = get_opt_detalle(base_empresa, id_lista_principal)
                    if lineas_detalle:
                        total_liberar = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas_detalle)
                        try:
                            ok_opt, _cod, nro_comp, err_opt = ejecutar_liberar_opt(
                                base_empresa, id_usuario, id_lista_principal, lineas_detalle,
                                total_liberar, deposito_produccion,
                            )
                        except MprSchemaError as e:
                            return _mpr_schema_error_redirect(request, e)
                        if ok_opt:
                            liberada = True
                            nro_comp_liberada = nro_comp
                        else:
                            if request.session.get(WIZARD_SESSION_KEY, {}).get("paso") == 1:
                                messages.error(request, err_opt or "Error al liberar a producción.")
                                return redirect("mpr:ventana_pack_agrupar")
                    elif request.session.get(WIZARD_SESSION_KEY, {}).get("paso") == 1:
                        messages.error(request, "No se pudieron cargar las líneas de la OPT.")
                        return redirect("mpr:ventana_pack_agrupar")
                elif request.session.get(WIZARD_SESSION_KEY, {}).get("paso") == 1:
                    messages.error(
                        request,
                        "Asigne el tipo «Producción» a un depósito en Config. Depósitos para continuar en el asistente.",
                    )
                    return redirect("mpr:ventana_pack_agrupar")
                wizard = request.session.get(WIZARD_SESSION_KEY) or {}
                if wizard.get("paso") == 1 and liberada:
                    request.session.pop(WIZARD_SESSION_KEY, None)
                    request.session.modified = True
                    messages.success(
                        request,
                        f"OPT Nº {id_lista_principal} creada y liberada. Comprobante {nro_comp_liberada}. "
                        "Registrar producción en Parte de producción.",
                    )
                    return redirect("mpr:opt_detail", id_lista=id_lista_principal)
                if liberada:
                    messages.success(request, f"OPT Nº {id_lista_principal} creada y liberada con {len(lineas)} artículo(s). Comprobante {nro_comp_liberada}.")
                else:
                    messages.success(request, f"OPT creada con {len(lineas)} artículo(s). Nº {id_lista_principal}.")
                return redirect("mpr:opt_detail", id_lista=id_lista_principal)
            messages.error(request, error or "Error al crear la OPT.")
            return self.get(request, *args, **kwargs)
        # POST desde Pantalla 1: guardar sel y cant_* en sesión y redirigir GET
        selected = request.POST.getlist("sel")
        filas_sesion = []
        try:
            ventana_pack_filas = listar_ventana_pack(base_empresa, limit=200)
        except MprSchemaError as e:
            return _mpr_schema_error_redirect(request, e)
        lookup = {f["id_articulo"]: f for f in ventana_pack_filas}
        for id_art_str in selected:
            try:
                id_art = int(id_art_str)
            except ValueError:
                continue
            f = lookup.get(id_art)
            if not f:
                continue
            qty_str = (request.POST.get("cant_" + str(id_art), "0") or "").strip().replace(",", ".")
            try:
                qty = int(round(float(qty_str))) if qty_str else 0
            except (ValueError, TypeError):
                qty = 0
            qty = max(0, qty)
            if qty > 0:
                try:
                    p_ped = float(f.get("cantidad_pedida_pedido") or 0)
                except (TypeError, ValueError):
                    p_ped = 0.0
                filas_sesion.append({
                    "id_articulo": id_art,
                    "codigo_articulo": f.get("codigo_articulo", "-"),
                    "codigo_manual": f.get("codigo_manual", "-"),
                    "descripcion_articulo": f.get("descripcion_articulo", "-"),
                    "stock_terminado": f.get("stock_terminado", 0),
                    "cantidad_pedida_pedido": p_ped,
                    "cantidad_urgente": f.get("cantidad_urgente", 0),
                    "cantidad_a_fabricar": qty,
                    "cantidad_promedio_bulto": f.get("cantidad_promedio_bulto", 0),
                })
        if not filas_sesion:
            messages.error(request, "Seleccione al menos un artículo con cantidad a fabricar mayor a 0.")
            return redirect("mpr:ventana_pack")

        # Validación de receta: bloquear si algún pack seleccionado no tiene BOM
        packs_sin_receta = [
            {
                "id_articulo": f["id_articulo"],
                "codigo_manual": f.get("codigo_manual", "-"),
                "descripcion_articulo": f.get("descripcion_articulo", "-"),
            }
            for fila in filas_sesion
            for f in [lookup.get(fila["id_articulo"])]
            if f and not _tiene_receta(f)
        ]
        if packs_sin_receta:
            request.session["ventana_pack_sin_receta"] = packs_sin_receta
            return redirect("mpr:ventana_pack")

        request.session["ventana_pack_seleccion"] = {"filas": filas_sesion}
        return redirect("mpr:ventana_pack_agrupar")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        seleccion = self.request.session.get("ventana_pack_seleccion") or {}
        filas = seleccion.get("filas") or []
        import json
        from .services import bulk_detalle_pedidos_por_articulos
        art_ids_pack = [f.get("id_articulo") for f in filas if f.get("id_articulo")]
        refresco_pack = (
            obtener_pp_ped_y_stock_pack_por_articulos(base_empresa, art_ids_pack)
            if art_ids_pack and base_empresa
            else {}
        )
        for f in filas:
            aid = to_int_or_none(f.get("id_articulo"))
            ref = refresco_pack.get(aid) if aid is not None else None
            if ref:
                f["cantidad_pedida_pedido"] = ref.get("cantidad_pedida_pedido", 0.0)
                f["stock_terminado"] = ref.get("stock_terminado", 0.0)
        detalle_map = bulk_detalle_pedidos_por_articulos(base_empresa, art_ids_pack, limit_por_articulo=30) if art_ids_pack else {}
        for f in filas:
            detalle = detalle_map.get(f.get("id_articulo"), [])
            f["detalle_pedidos"] = detalle
            f["detalle_pedidos_json"] = json.dumps(detalle)
        wizard = self.request.session.get(WIZARD_SESSION_KEY) or {}
        filas_unidades = listar_unidades_desde_seleccion(
            base_empresa, filas, limit=200, refresco_pack=refresco_pack
        )
        for f in filas_unidades:
            f["cantidad_docenas"] = f.get("cantidad_a_fabricar_docenas", 0)
            f["cantidad_urgente_docenas"] = f.get("cantidad_urgente_docenas", 0)
            f["id_operario_opt"] = None
        for f in filas:
            b = f.get("cantidad_promedio_bulto", 0)
            f["cantidad_docenas"] = docenas_desde_unidades_opt(f.get("cantidad_a_fabricar"), b)
        context["base_empresa"] = base_empresa
        context["filas"] = filas
        context["filas_unidades"] = filas_unidades
        context["en_wizard"] = wizard.get("paso") == 1
        context["wizard_paso"] = 2
        context["wizard_paso_max"] = WizardProduccionView.WIZARD_PASO_MAX
        context["fecha_hoy"] = date.today()
        if base_empresa:
            context["opcional_op"] = listar_columnas_opcionales_nueva_op(base_empresa)
        else:
            context["opcional_op"] = {"has_fecha_objetivo": False, "has_deposito_produccion": False, "has_prioridad": False}
        context["mpr_aviso_sin_deposito_semi_bom"] = (
            bool(base_empresa) and get_deposito_semi_elaborado_mpr(base_empresa) is None
        )
        return context


class VentanaPackView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Orden de Producción de Trabajo (OPT) Pantalla 1: demanda por artículo; formulario envía a ventana_pack_agrupar (Continuar)."""

    template_name = "mpr/ventana_pack.html"

    def get(self, request, *args, **kwargs):
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            from django.contrib import messages
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        # Desde Top urgencias del tablero: ?articulo=ID → preseleccionar ese artículo y llevar a agrupar (crear OPT con pedidos pendientes)
        id_art_param = request.GET.get("articulo", "").strip()
        if id_art_param and id_art_param.isdigit():
            id_art = int(id_art_param)
            try:
                ventana_pack_filas = listar_ventana_pack(base_empresa, limit=200)
            except MprSchemaError:
                pass
            else:
                fila = next((f for f in ventana_pack_filas if to_int_or_none(f.get("id_articulo")) == id_art), None)
                if fila and (fila.get("cantidad_a_fabricar") or 0) > 0:
                    filas_sesion = [{
                        "id_articulo": id_art,
                        "codigo_articulo": fila.get("codigo_articulo", "-"),
                        "codigo_manual": fila.get("codigo_manual", "-"),
                        "descripcion_articulo": fila.get("descripcion_articulo", "-"),
                        "stock_terminado": fila.get("stock_terminado", 0),
                        "cantidad_urgente": fila.get("cantidad_urgente", 0),
                        "cantidad_a_fabricar": int(fila.get("cantidad_a_fabricar") or fila.get("cantidad_pendiente_prod") or 0),
                        "cantidad_promedio_bulto": fila.get("cantidad_promedio_bulto", 0),
                    }]
                    request.session["ventana_pack_seleccion"] = {"filas": filas_sesion}
                    request.session.modified = True
                    return redirect("mpr:ventana_pack_agrupar")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from django.contrib import messages

        context = super().get_context_data(**kwargs)

        # Leer y limpiar packs sin receta comunicados desde VentanaPackAgruparView
        packs_sin_receta = self.request.session.pop("ventana_pack_sin_receta", None)
        context["packs_sin_receta"] = packs_sin_receta or []

        base_empresa = _get_base_empresa(self.request)
        vista = (self.request.GET.get("vista") or "pack").strip().lower()
        if vista != "unidades":
            vista = "pack"
        wizard = self.request.session.get(WIZARD_SESSION_KEY) or {}
        context["base_empresa"] = base_empresa
        context["vista_unidades"] = vista == "unidades"

        # Filtros con valores por defecto (mismo criterio que el formulario Actualizar)
        filtros = self.request.session.get("ventana_pack_filtros_actualizar") or {}
        hoy = date.today()
        if not filtros.get("fecha_desde"):
            filtros = dict(filtros)
            filtros["fecha_desde"] = hoy.replace(day=1).isoformat()
        if not filtros.get("fecha_hasta"):
            filtros = dict(filtros)
            ultimo_dia = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            filtros["fecha_hasta"] = ultimo_dia.isoformat()
        context["filtros_actualizar"] = filtros

        # Actualizar lista_produccion_detalle y agrupada con los filtros de sesión (o por defecto).
        fecha_desde = (filtros.get("fecha_desde") or "").strip() or None
        fecha_hasta = (filtros.get("fecha_hasta") or "").strip() or None
        busqueda = (filtros.get("busqueda") or "").strip() or None
        session_user = self.request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        try:
            actualizar_pedidos_produccion(
                base_empresa,
                id_usuario=id_usuario,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                busqueda=busqueda,
            )
        except MprSchemaError:
            pass  # Se muestra tabla vacía o error en contexto
        try:
            context["filas"] = listar_ventana_pack(base_empresa, limit=200)
            context["filas_unidades"] = listar_ventana_pack_unidades(
                base_empresa, limit=200, filas_pack=context["filas"]
            )
            for f in context["filas"]:
                f["pedidos_resumen_json"] = json.dumps(f.get("pedidos_resumen") or [])
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            context["mpr_schema_error_modal"] = str(e)
            context["filas"] = []
            context["filas_unidades"] = []

        context["mpr_aviso_sin_deposito_semi_bom"] = (
            bool(base_empresa) and get_deposito_semi_elaborado_mpr(base_empresa) is None
        )
        context["en_wizard"] = wizard.get("paso") == 1
        context["wizard_paso"] = 1
        context["wizard_paso_max"] = WizardProduccionView.WIZARD_PASO_MAX
        return context


# ---------------------------------------------------------------------------
# ETAPA 2: Tablero de Demanda Consolidado por Artículo
# ---------------------------------------------------------------------------

# =============================================================================
# Tablero de demanda consolidado — preferencias de sesión
# =============================================================================

_TABLERO_SESSION_SOLO_URGENTE = "tablero_produccion_solo_urgente"
_TABLERO_SESSION_SOLO_SIN_RECETA = "tablero_produccion_solo_sin_receta"
_TABLERO_SESSION_SOLO_PENDIENTE_LEGACY = "tablero_produccion_solo_pendiente"
_TABLERO_SESSION_MODO = "tablero_produccion_modo"
_TABLERO_MODOS = frozenset({"par", "pack"})
_TABLERO_MODO_DEFAULT = "par"


def _resolver_solo_urgente_tablero(request) -> bool:
    """Lee solo_urgente (o solo_pendiente legacy) de GET o sesión."""
    raw = request.GET.get("solo_urgente")
    if raw is None:
        raw = request.GET.get("solo_pendiente")
    if raw is not None:
        valor = raw == "1"
        request.session[_TABLERO_SESSION_SOLO_URGENTE] = valor
        return valor
    if _TABLERO_SESSION_SOLO_URGENTE in request.session:
        return bool(request.session.get(_TABLERO_SESSION_SOLO_URGENTE, True))
    return bool(request.session.get(_TABLERO_SESSION_SOLO_PENDIENTE_LEGACY, True))


def _resolver_solo_pendiente_tablero(request) -> bool:
    """Alias legacy — usar ``_resolver_solo_urgente_tablero``."""
    return _resolver_solo_urgente_tablero(request)


def _resolver_solo_sin_receta_tablero(request) -> bool:
    """Lee ``solo_sin_receta`` de GET (persiste en sesión) o sesión/default ``False``."""
    raw = request.GET.get("solo_sin_receta")
    if raw is not None:
        valor = raw == "1"
        request.session[_TABLERO_SESSION_SOLO_SIN_RECETA] = valor
        return valor
    if _TABLERO_SESSION_SOLO_SIN_RECETA in request.session:
        return bool(request.session.get(_TABLERO_SESSION_SOLO_SIN_RECETA, False))
    return False


def _resolver_modo_tablero(request) -> str:
    """Lee ``modo`` (par|pack) de GET (persiste en sesión) o sesión/default ``par``."""
    raw = (request.GET.get("modo") or "").strip().lower()
    if raw in _TABLERO_MODOS:
        request.session[_TABLERO_SESSION_MODO] = raw
        return raw
    saved = (request.session.get(_TABLERO_SESSION_MODO) or "").strip().lower()
    if saved in _TABLERO_MODOS:
        return saved
    return _TABLERO_MODO_DEFAULT


def _redirect_tablero_produccion(request, query_string: str | None = None):
    """Redirect al tablero preservando solo_urgente, solo_sin_receta, modo, presentacion, marcas, q y query."""
    from urllib.parse import parse_qsl, urlencode

    from mpr.presentacion_operativa import resolver_modo_presentacion_operativa

    url = reverse("mpr:tablero_produccion")
    params = dict(parse_qsl(query_string, keep_blank_values=True)) if query_string else {}
    if "solo_urgente" not in params and "solo_pendiente" not in params:
        solo = _resolver_solo_urgente_tablero(request)
        params["solo_urgente"] = "1" if solo else "0"
    if "solo_sin_receta" not in params:
        solo_sr = _resolver_solo_sin_receta_tablero(request)
        params["solo_sin_receta"] = "1" if solo_sr else "0"
    if "modo" not in params:
        params["modo"] = _resolver_modo_tablero(request)
    if "presentacion" not in params:
        params["presentacion"] = resolver_modo_presentacion_operativa(request)
    # q vacío = limpiar búsqueda client-side tras Actualizar / Enviar
    q_busqueda = (params.get("q") or "").strip()
    if q_busqueda:
        params["q"] = q_busqueda
    else:
        params.pop("q", None)
    params.pop("marcas_incluidos", None)
    pairs = [(k, v) for k, v in params.items()]
    pairs.extend(_marcas_urlencode_pairs(_parse_marcas_incluidos(request)))
    if pairs:
        url += "?" + urlencode(pairs)
    return redirect(url)


class TableroProduccionView(MprLoginRequiredMixin, MprTableroVerMixin, TemplateView):
    """Tablero de producción por artículo/componente (PCP). Etapa 2 MPR."""

    template_name = "mpr/tablero_produccion.html"

    def get(self, request, *args, **kwargs):
        from django.contrib import messages
        from core.utils.administranet_types import to_date_or_none
        from mpr.services import (
            calcular_kpis_tablero_produccion,
            listar_tablero_pack,
        )

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        fecha_desde_str = (request.GET.get("fecha_desde") or "").strip() or None
        fecha_hasta_str = (request.GET.get("fecha_hasta") or "").strip() or None
        solo_urgente = _resolver_solo_urgente_tablero(request)
        solo_sin_receta = _resolver_solo_sin_receta_tablero(request)
        marcas_incluidos = _parse_marcas_incluidos(request)
        # modo=par|pack — par (default) explota BOM por componente; pack consolida
        # por artículo pack terminado (paridad BEST PCP Producción) sin explosión BOM.
        # Persiste en sesión (mismo patrón que presentacion y solo_urgente).
        modo_tablero = _resolver_modo_tablero(request)
        # Búsqueda client-side (Alpine): se persiste en ?q= para sobrevivir Actualizar / toggles.
        busqueda_q = (request.GET.get("q") or "").strip()
        listar_fn = listar_tablero_pack if modo_tablero == "pack" else listar_tablero_por_articulo
        listar_kwargs = {
            "fecha_desde": to_date_or_none(fecha_desde_str) if fecha_desde_str else None,
            "fecha_hasta": to_date_or_none(fecha_hasta_str) if fecha_hasta_str else None,
            "solo_urgente": solo_urgente,
            "limit": 500,
            "marcas_incluidos": marcas_incluidos or None,
        }
        if modo_tablero == "pack":
            listar_kwargs["solo_sin_receta"] = solo_sin_receta
        try:
            filas = listar_fn(base_empresa, **listar_kwargs)
        except MprSchemaError as e:
            return _mpr_schema_error_redirect(request, e)
        except Exception as e:
            logger.warning("TableroProduccionView error: %s", e, exc_info=True)
            filas = []
        from mpr.presentacion_operativa import (
            enriquecer_filas_tablero_presentacion,
            resolver_modo_presentacion_operativa,
        )

        modo_presentacion = resolver_modo_presentacion_operativa(request)
        filas = enriquecer_filas_tablero_presentacion(filas, modo_presentacion)
        from datetime import date as _date_tablero

        fecha_tablero = _date_tablero.today()
        if fecha_hasta_str:
            fecha_iso = to_date_or_none(fecha_hasta_str)
            if fecha_iso:
                fecha_tablero = _date_tablero.fromisoformat(fecha_iso)
        if modo_tablero == "par":
            from mpr.services_maquina_linea import enriquecer_filas_tablero_indicadores_fabricando

            filas = enriquecer_filas_tablero_indicadores_fabricando(
                base_empresa, filas, fecha=fecha_tablero
            )
        ctx_marcas = _context_filtro_marcas(request, base_empresa)
        marcas_etiqueta = {
            int(m["value"]): str(m.get("label") or "")
            for m in (ctx_marcas.get("marcas_catalogo") or [])
            if m.get("value") is not None
        }
        for fila in filas:
            cm = to_int_or_none(fila.get("codigo_marca"))
            if cm is not None:
                fila["codigo_marca"] = cm
                fila["marca_nombre"] = marcas_etiqueta.get(cm, fila.get("marca_nombre") or "")
            else:
                fila["marca_nombre"] = fila.get("marca_nombre") or ""
        from mpr.services_maquina_linea import ordenar_filas_tablero_maquina_marca

        filas = ordenar_filas_tablero_maquina_marca(filas)
        kpis_tablero = calcular_kpis_tablero_produccion(filas)
        qs_params = {}
        if fecha_desde_str:
            qs_params["fecha_desde"] = fecha_desde_str
        if fecha_hasta_str:
            qs_params["fecha_hasta"] = fecha_hasta_str
        qs_params["solo_urgente"] = "1" if solo_urgente else "0"
        qs_params["solo_sin_receta"] = "1" if solo_sin_receta else "0"
        if busqueda_q:
            qs_params["q"] = busqueda_q
        # Base para el toggle Pack|Par: preserva filtros + presentación (sin modo).
        modo_query_base = _urlencode_con_marcas(
            {**qs_params, "presentacion": modo_presentacion}, marcas_incluidos
        )
        # Base para el toggle Docenas|Pares: preserva filtros + modo (sin presentacion).
        presentacion_query_base = _urlencode_con_marcas(
            {**qs_params, "modo": modo_tablero}, marcas_incluidos
        )
        ultima_act = request.session.get("tablero_produccion_ultima_actualizacion", None)
        return self.render_to_response({
            "filas": filas,
            "fecha_desde": fecha_desde_str or "",
            "fecha_hasta": fecha_hasta_str or "",
            "solo_urgente": solo_urgente,
            "solo_pendiente": solo_urgente,
            "solo_sin_receta": solo_sin_receta,
            "busqueda_q": busqueda_q,
            "kpis_tablero": kpis_tablero,
            "ultima_actualizacion": ultima_act,
            "tablero_url": reverse("mpr:tablero"),
            "modo_presentacion": modo_presentacion,
            "modo_tablero": modo_tablero,
            "presentacion_query_base": presentacion_query_base,
            "modo_query_base": modo_query_base,
            "unidades_por_docena_tablero": UNIDADES_POR_DOCENA_OPP,
            "fecha_tablero_ddmmyyyy": fecha_tablero.strftime("%d/%m/%Y"),
            **ctx_marcas,
            **_context_flags_tablero(request.user),
        })


class TableroProduccionActualizarView(MprLoginRequiredMixin, MprTableroVerMixin, TemplateView):
    """POST: refresca timestamp de sesión; la demanda se calcula en vivo desde pedidos PED."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        from urllib.parse import urlencode

        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        q_busqueda = (request.POST.get("q") or "").strip()
        filtros_qs = urlencode({"q": q_busqueda}) if q_busqueda else None
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return _redirect_tablero_produccion(request, filtros_qs)
        request.session["tablero_produccion_ultima_actualizacion"] = (
            datetime.now().strftime("%d/%m/%Y %H:%M")
        )
        return _redirect_tablero_produccion(request, filtros_qs)


# =============================================================================
# Etapa 3: Turnos (CRUD) + Roster Rotativo
# =============================================================================

class TurnosListView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """
    Listado de turnos de producción con toggle Activo/Inactivo.
    GET: lista todos los turnos (activos e inactivos).
    POST: toggle activo de un turno.
    """

    template_name = "mpr/turnos_list.html"

    def get_context_data(self, **kwargs):
        from mpr.services import listar_turnos
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        context["turnos"] = listar_turnos(base_empresa, solo_activos=False)
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        from mpr.services import toggle_turno_activo
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:turnos_list")
        id_turno_raw = request.POST.get("id_turno", "")
        activo_str = request.POST.get("activo", "")
        try:
            id_turno = int(id_turno_raw)
            activo = activo_str == "True"
        except (ValueError, TypeError):
            messages.error(request, "Datos inválidos.")
            return redirect("mpr:turnos_list")
        ok, error = toggle_turno_activo(base_empresa, id_turno, activo)
        if ok:
            estado = "activado" if activo else "desactivado"
            messages.success(request, f"Turno {estado} exitosamente.")
        else:
            messages.error(request, error or "Error al cambiar estado del turno.")
        return redirect("mpr:turnos_list")


class TurnoCreateView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """
    Alta de turno de producción.
    GET: muestra formulario.
    POST: crea turno y redirige a listado si OK.
    """

    template_name = "mpr/turno_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Nuevo turno"
        context["accion"] = "Crear"
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        from mpr.services import crear_turno
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:turnos_list")
        nombre = (request.POST.get("nombre") or "").strip()
        hora_inicio = (request.POST.get("hora_inicio") or "").strip()
        hora_fin = (request.POST.get("hora_fin") or "").strip()
        ok, _id, error = crear_turno(base_empresa, nombre, hora_inicio, hora_fin)
        if ok:
            messages.success(request, f"Turno '{nombre}' creado exitosamente.")
            return redirect("mpr:turnos_list")
        messages.error(request, error or "Error al crear turno.")
        context = self.get_context_data()
        context["nombre"] = nombre
        context["hora_inicio"] = hora_inicio
        context["hora_fin"] = hora_fin
        return self.render_to_response(context)


class TurnoUpdateView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """
    Edición de turno de producción.
    GET: muestra formulario con datos actuales.
    POST: actualiza turno y redirige a listado si OK.
    """

    template_name = "mpr/turno_form.html"

    def get_context_data(self, **kwargs):
        from django.contrib import messages
        from mpr.services import obtener_turno
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_turno = kwargs.get("id_turno")
        turno = obtener_turno(base_empresa, id_turno) if id_turno else None
        if not turno:
            context["titulo"] = "Editar turno"
            context["accion"] = "Guardar cambios"
            return context
        context["titulo"] = f"Editar turno: {turno.nombre}"
        context["accion"] = "Guardar cambios"
        context["id_turno"] = turno.id
        context["nombre"] = turno.nombre
        context["hora_inicio"] = turno.hora_inicio.strftime("%H:%M")
        context["hora_fin"] = turno.hora_fin.strftime("%H:%M")
        return context

    def get(self, request, *args, **kwargs):
        from django.contrib import messages
        from mpr.services import obtener_turno
        base_empresa = _get_base_empresa(request)
        id_turno = kwargs.get("id_turno")
        if not base_empresa or not obtener_turno(base_empresa, id_turno):
            messages.error(request, "Turno no encontrado.")
            return redirect("mpr:turnos_list")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        from mpr.services import actualizar_turno
        base_empresa = _get_base_empresa(request)
        id_turno = kwargs.get("id_turno")
        if not base_empresa or not id_turno:
            messages.error(request, "Parámetros inválidos.")
            return redirect("mpr:turnos_list")
        nombre = (request.POST.get("nombre") or "").strip()
        hora_inicio = (request.POST.get("hora_inicio") or "").strip()
        hora_fin = (request.POST.get("hora_fin") or "").strip()
        ok, error = actualizar_turno(base_empresa, id_turno, nombre, hora_inicio, hora_fin)
        if ok:
            messages.success(request, f"Turno '{nombre}' actualizado exitosamente.")
            return redirect("mpr:turnos_list")
        messages.error(request, error or "Error al actualizar turno.")
        context = self.get_context_data(id_turno=id_turno)
        context["nombre"] = nombre
        context["hora_inicio"] = hora_inicio
        context["hora_fin"] = hora_fin
        return self.render_to_response(context)


# ---------------------------------------------------------------------------- #
# Catálogos: Líneas de producción (CRUD + toggle)
# ---------------------------------------------------------------------------- #
class LineasListView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Listado de líneas de producción con toggle Activo/Inactivo."""

    template_name = "mpr/lineas_list.html"
    permiso_requerido = "mpr.maquinas_lineas"

    def get_context_data(self, **kwargs):
        from mpr.services_maquina_linea import listar_lineas
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        context["lineas"] = listar_lineas(base_empresa, solo_activas=False)
        return context

    def post(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import toggle_linea_activa
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:lineas_list")
        try:
            id_linea = int(request.POST.get("id_linea", ""))
            activa = request.POST.get("activo", "") == "True"
        except (ValueError, TypeError):
            messages.error(request, "Datos inválidos.")
            return redirect("mpr:lineas_list")
        ok, error = toggle_linea_activa(base_empresa, id_linea, activa)
        if ok:
            messages.success(request, "Línea " + ("activada" if activa else "desactivada") + " exitosamente.")
        else:
            messages.error(request, error or "Error al cambiar estado de la línea.")
        return redirect("mpr:lineas_list")


class LineaCreateView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Alta de línea de producción."""

    template_name = "mpr/linea_form.html"
    permiso_requerido = "mpr.maquinas_lineas"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Nueva línea"
        context["accion"] = "Crear"
        return context

    def post(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import crear_linea
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:lineas_list")
        nombre = (request.POST.get("nombre") or "").strip()
        ok, _id, error = crear_linea(base_empresa, nombre)
        if ok:
            messages.success(request, f"Línea '{nombre}' creada exitosamente.")
            return redirect("mpr:lineas_list")
        messages.error(request, error or "Error al crear línea.")
        context = self.get_context_data()
        context["nombre"] = nombre
        return self.render_to_response(context)


class LineaUpdateView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Edición de línea de producción."""

    template_name = "mpr/linea_form.html"
    permiso_requerido = "mpr.maquinas_lineas"

    def get_context_data(self, **kwargs):
        from mpr.services_maquina_linea import obtener_linea
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_linea = kwargs.get("id_linea")
        linea = obtener_linea(base_empresa, id_linea) if id_linea else None
        context["accion"] = "Guardar cambios"
        if not linea:
            context["titulo"] = "Editar línea"
            return context
        context["titulo"] = f"Editar línea: {linea['nombre']}"
        context["id_linea"] = linea["id"]
        context["nombre"] = linea["nombre"]
        return context

    def get(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import obtener_linea
        base_empresa = _get_base_empresa(request)
        id_linea = kwargs.get("id_linea")
        if not base_empresa or not obtener_linea(base_empresa, id_linea):
            messages.error(request, "Línea no encontrada.")
            return redirect("mpr:lineas_list")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import actualizar_linea
        base_empresa = _get_base_empresa(request)
        id_linea = kwargs.get("id_linea")
        if not base_empresa or not id_linea:
            messages.error(request, "Parámetros inválidos.")
            return redirect("mpr:lineas_list")
        nombre = (request.POST.get("nombre") or "").strip()
        ok, error = actualizar_linea(base_empresa, id_linea, nombre)
        if ok:
            messages.success(request, f"Línea '{nombre}' actualizada exitosamente.")
            return redirect("mpr:lineas_list")
        messages.error(request, error or "Error al actualizar línea.")
        context = self.get_context_data(id_linea=id_linea)
        context["nombre"] = nombre
        return self.render_to_response(context)


# ---------------------------------------------------------------------------- #
# Catálogos: Máquinas (CRUD + toggle + asignación versionada a línea)
# ---------------------------------------------------------------------------- #
class MaquinasListView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Listado de máquinas con línea vigente, toggle y asignación de línea."""

    template_name = "mpr/maquinas_list.html"
    permiso_requerido = "mpr.maquinas_lineas"

    def get_context_data(self, **kwargs):
        from mpr.services_maquina_linea import listar_maquinas, listar_lineas
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        context["maquinas"] = listar_maquinas(base_empresa, solo_activas=False)
        context["lineas"] = listar_lineas(base_empresa, solo_activas=True)
        return context

    def post(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import toggle_maquina_activa
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:maquinas_list")
        try:
            id_maquina = int(request.POST.get("id_maquina", ""))
            activa = request.POST.get("activo", "") == "True"
        except (ValueError, TypeError):
            messages.error(request, "Datos inválidos.")
            return redirect("mpr:maquinas_list")
        ok, error = toggle_maquina_activa(base_empresa, id_maquina, activa)
        if ok:
            messages.success(request, "Máquina " + ("activada" if activa else "desactivada") + " exitosamente.")
        else:
            messages.error(request, error or "Error al cambiar estado de la máquina.")
        return redirect("mpr:maquinas_list")


class MaquinaCreateView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Alta de máquina."""

    template_name = "mpr/maquina_form.html"
    permiso_requerido = "mpr.maquinas_lineas"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["titulo"] = "Nueva máquina"
        context["accion"] = "Crear"
        return context

    def post(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import crear_maquina
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:maquinas_list")
        codigo = (request.POST.get("codigo") or "").strip()
        nombre = (request.POST.get("nombre") or "").strip()
        ok, _id, error = crear_maquina(base_empresa, codigo, nombre)
        if ok:
            messages.success(request, f"Máquina '{codigo}' creada exitosamente.")
            return redirect("mpr:maquinas_list")
        messages.error(request, error or "Error al crear máquina.")
        context = self.get_context_data()
        context["codigo"] = codigo
        context["nombre"] = nombre
        return self.render_to_response(context)


class MaquinaUpdateView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Edición de máquina + histórico de pertenencia a líneas."""

    template_name = "mpr/maquina_form.html"
    permiso_requerido = "mpr.maquinas_lineas"

    def get_context_data(self, **kwargs):
        from mpr.services_maquina_linea import (
            obtener_maquina,
            listar_historico_maquina_linea,
        )
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_maquina = kwargs.get("id_maquina")
        maquina = obtener_maquina(base_empresa, id_maquina) if id_maquina else None
        context["accion"] = "Guardar cambios"
        if not maquina:
            context["titulo"] = "Editar máquina"
            return context
        context["titulo"] = f"Editar máquina: {maquina['codigo']}"
        context["id_maquina"] = maquina["id"]
        context["codigo"] = maquina["codigo"]
        context["nombre"] = maquina["nombre"]
        context["historico"] = listar_historico_maquina_linea(base_empresa, id_maquina)
        return context

    def get(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import obtener_maquina
        base_empresa = _get_base_empresa(request)
        id_maquina = kwargs.get("id_maquina")
        if not base_empresa or not obtener_maquina(base_empresa, id_maquina):
            messages.error(request, "Máquina no encontrada.")
            return redirect("mpr:maquinas_list")
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import actualizar_maquina
        base_empresa = _get_base_empresa(request)
        id_maquina = kwargs.get("id_maquina")
        if not base_empresa or not id_maquina:
            messages.error(request, "Parámetros inválidos.")
            return redirect("mpr:maquinas_list")
        codigo = (request.POST.get("codigo") or "").strip()
        nombre = (request.POST.get("nombre") or "").strip()
        ok, error = actualizar_maquina(base_empresa, id_maquina, codigo, nombre)
        if ok:
            messages.success(request, f"Máquina '{codigo}' actualizada exitosamente.")
            return redirect("mpr:maquinas_list")
        messages.error(request, error or "Error al actualizar máquina.")
        context = self.get_context_data(id_maquina=id_maquina)
        context["codigo"] = codigo
        context["nombre"] = nombre
        return self.render_to_response(context)


class MaquinaAsignarLineaView(MprLoginRequiredMixin, MprPermisoMixin, View):
    """Asigna (versionadamente) una máquina a una línea desde el listado."""

    permiso_requerido = "mpr.maquinas_lineas"

    def post(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import asignar_maquina_linea
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:maquinas_list")
        try:
            id_maquina = int(request.POST.get("id_maquina", ""))
            id_linea = int(request.POST.get("id_linea", ""))
        except (ValueError, TypeError):
            messages.error(request, "Datos inválidos.")
            return redirect("mpr:maquinas_list")
        desde = None
        desde_str = (request.POST.get("desde") or "").strip()
        if desde_str:
            try:
                desde = date.fromisoformat(desde_str)
            except ValueError:
                messages.error(request, "Fecha de vigencia inválida.")
                return redirect("mpr:maquinas_list")
        ok, error = asignar_maquina_linea(base_empresa, id_maquina, id_linea, desde)
        if ok:
            messages.success(request, "Máquina asignada a la línea exitosamente.")
        else:
            messages.error(request, error or "Error al asignar la máquina a la línea.")
        return redirect("mpr:maquinas_list")


class MaquinaArticulosView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Gestión de artículos habilitados por máquina (varios vigentes + histórico).

    GET  : lista vigentes, histórico y (opcional) resultados de búsqueda (?q=).
    POST : accion=habilitar|deshabilitar sobre un id_articulo.
    """

    template_name = "mpr/maquina_articulos.html"
    permiso_requerido = "mpr.maquinas_lineas"

    def _maquina(self):
        from mpr.services_maquina_linea import obtener_maquina
        base_empresa = _get_base_empresa(self.request)
        id_maquina = self.kwargs.get("id_maquina")
        return base_empresa, id_maquina, obtener_maquina(base_empresa, id_maquina)

    def get(self, request, *args, **kwargs):
        base_empresa, id_maquina, maquina = self._maquina()
        if not base_empresa or not maquina:
            messages.error(request, "Máquina no encontrada.")
            return redirect("mpr:maquinas_list")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from mpr.services_maquina_linea import (
            listar_articulos_vigentes_maquina,
            historico_maquina_articulo,
            buscar_articulos,
        )
        context = super().get_context_data(**kwargs)
        base_empresa, id_maquina, maquina = self._maquina()
        context["maquina"] = maquina
        context["id_maquina"] = id_maquina
        context["vigentes"] = listar_articulos_vigentes_maquina(base_empresa, id_maquina)
        context["historico"] = historico_maquina_articulo(base_empresa, id_maquina)
        q = (self.request.GET.get("q") or "").strip()
        context["q"] = q
        context["resultados"] = (
            buscar_articulos(base_empresa, q, tipo_art_fab="Fabricado") if q else []
        )
        return context

    def post(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import (
            habilitar_articulo_maquina,
            deshabilitar_articulo_maquina,
        )
        base_empresa = _get_base_empresa(request)
        id_maquina = kwargs.get("id_maquina")
        if not base_empresa or not id_maquina:
            messages.error(request, "Parámetros inválidos.")
            return redirect("mpr:maquinas_list")
        accion = (request.POST.get("accion") or "").strip()
        try:
            id_articulo = int(request.POST.get("id_articulo", ""))
        except (ValueError, TypeError):
            messages.error(request, "Artículo inválido.")
            return redirect("mpr:maquina_articulos", id_maquina=id_maquina)
        if accion == "habilitar":
            ok, error = habilitar_articulo_maquina(base_empresa, id_maquina, id_articulo)
            msg_ok = "Artículo habilitado exitosamente."
        elif accion == "deshabilitar":
            ok, error = deshabilitar_articulo_maquina(base_empresa, id_maquina, id_articulo)
            msg_ok = "Artículo deshabilitado exitosamente."
        else:
            messages.error(request, "Acción inválida.")
            return redirect("mpr:maquina_articulos", id_maquina=id_maquina)
        if ok:
            messages.success(request, msg_ok)
        else:
            messages.error(request, error or "No se pudo completar la acción.")
        return redirect("mpr:maquina_articulos", id_maquina=id_maquina)


class MaquinasCargaArticulosView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Grilla de carga de artículos habilitados por máquina (supervisor)."""

    template_name = "mpr/maquinas_carga_articulos.html"
    permiso_requerido = "mpr.maquinas_lineas"

    def get_context_data(self, **kwargs):
        from datetime import date as _date
        from datetime import datetime as _datetime

        from mpr.services_maquina_linea import construir_grilla_carga_articulos

        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_linea_raw = (self.request.GET.get("id_linea") or "").strip()
        id_linea = None
        if id_linea_raw:
            try:
                id_linea = int(id_linea_raw)
            except (ValueError, TypeError):
                id_linea = None
        hoy = _date.today()
        fecha = hoy
        fecha_str = (self.request.GET.get("fecha") or "").strip()
        if fecha_str:
            try:
                fecha = _datetime.strptime(fecha_str, "%d/%m/%Y").date()
            except ValueError:
                fecha = hoy
        if fecha > hoy:
            fecha = hoy
        grilla = construir_grilla_carga_articulos(
            base_empresa, id_linea=id_linea, fecha=fecha
        )
        context.update(grilla)
        context["fecha_str"] = fecha.strftime("%d/%m/%Y")
        # Operarios del roster del día seleccionado, acotados a las líneas de las máquinas
        # disponibles para la planilla CQ.
        from mpr.services import operarios_roster_por_linea

        id_lineas_maquinas = {
            maquina.get("id_linea_actual")
            for maquina in grilla.get("maquinas", [])
            if maquina.get("id_linea_actual") is not None
        }
        context["operadores_por_linea"] = operarios_roster_por_linea(
            base_empresa, fecha, id_lineas_maquinas
        )
        return context


class ReportesArticuloBuscarAPIView(MprLoginRequiredMixin, MprReportesVerMixin, View):
    """API JSON: búsqueda predictiva de artículos para reportes MPR (kardex)."""

    def get(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import buscar_articulos

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"articulos": []})
        q = (request.GET.get("q") or "").strip()
        if len(q) < 1:
            return JsonResponse({"articulos": []})
        try:
            limit = int(request.GET.get("limit") or 25)
        except (ValueError, TypeError):
            limit = 25
        articulos = buscar_articulos(base_empresa, q, limit=limit)
        return JsonResponse({"articulos": articulos})


class MaquinaArticuloBuscarAPIView(MprLoginRequiredMixin, MprPermisoMixin, View):
    """API JSON: búsqueda predictiva de artículos fabricados para habilitar en máquina."""

    permiso_requerido = "mpr.maquinas_lineas"

    def get(self, request, *args, **kwargs):
        from mpr.services_maquina_linea import buscar_articulos

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"articulos": []})
        q = (request.GET.get("q") or "").strip()
        if len(q) < 1:
            return JsonResponse({"articulos": []})
        try:
            limit = int(request.GET.get("limit") or 25)
        except (ValueError, TypeError):
            limit = 25
        articulos = buscar_articulos(
            base_empresa, q, limit=limit, tipo_art_fab="Fabricado"
        )
        return JsonResponse({"articulos": articulos})


class MaquinaArticuloAccionAPIView(MprLoginRequiredMixin, MprPermisoMixin, View):
    """API JSON: habilitar o deshabilitar artículo en máquina (trazabilidad versionada)."""

    permiso_requerido = "mpr.maquinas_lineas"

    def post(self, request, *args, **kwargs):
        import json
        from datetime import date as _date
        from datetime import datetime as _datetime

        from mpr.services_maquina_linea import (
            deshabilitar_articulo_maquina,
            habilitar_articulo_maquina,
            listar_articulos_vigentes_maquina,
        )

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"ok": False, "error": "Empresa inválida."}, status=400)

        content_type = (request.content_type or "").lower()
        if "application/json" in content_type:
            try:
                payload = json.loads(request.body.decode("utf-8") or "{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)
        else:
            payload = request.POST

        accion = (payload.get("accion") or "").strip()
        try:
            id_maquina = int(payload.get("id_maquina", ""))
            id_articulo = int(payload.get("id_articulo", ""))
        except (ValueError, TypeError):
            return JsonResponse({"ok": False, "error": "Parámetros inválidos."}, status=400)

        hoy = _date.today()
        fecha_obj = hoy
        fecha_raw = (payload.get("fecha") or "").strip()
        if fecha_raw:
            try:
                fecha_obj = _datetime.strptime(fecha_raw, "%d/%m/%Y").date()
            except ValueError:
                try:
                    fecha_obj = _date.fromisoformat(fecha_raw[:10])
                except ValueError:
                    return JsonResponse({"ok": False, "error": "Fecha inválida."}, status=400)
        if fecha_obj > hoy:
            return JsonResponse(
                {"ok": False, "error": "No se pueden modificar asignaciones en fechas futuras."},
                status=400,
            )

        if accion == "habilitar":
            ok, error = habilitar_articulo_maquina(
                base_empresa, id_maquina, id_articulo, desde=fecha_obj
            )
            if not ok:
                return JsonResponse({"ok": False, "error": error or "No se pudo habilitar."}, status=400)
            vigentes = listar_articulos_vigentes_maquina(
                base_empresa, id_maquina, fecha=fecha_obj
            )
            articulo = next(
                (a for a in vigentes if a.get("id_articulo") == id_articulo),
                None,
            )
            return JsonResponse({"ok": True, "articulo": articulo or {"id_articulo": id_articulo}})
        if accion == "deshabilitar":
            ok, error = deshabilitar_articulo_maquina(
                base_empresa, id_maquina, id_articulo, fecha=fecha_obj
            )
            if not ok:
                return JsonResponse(
                    {"ok": False, "error": error or "No se pudo deshabilitar."},
                    status=400,
                )
            return JsonResponse({"ok": True})
        return JsonResponse({"ok": False, "error": "Acción inválida."}, status=400)


class MaquinaObservacionPlanillaAPIView(MprLoginRequiredMixin, MprPermisoMixin, View):
    """API JSON: persistir observación de planilla Control de Calidad por máquina."""

    permiso_requerido = "mpr.maquinas_lineas"

    def post(self, request, *args, **kwargs):
        import json

        from mpr.services_maquina_linea import guardar_observacion_planilla_maquina

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"ok": False, "error": "Empresa inválida."}, status=400)

        content_type = (request.content_type or "").lower()
        if "application/json" in content_type:
            try:
                payload = json.loads(request.body.decode("utf-8") or "{}")
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({"ok": False, "error": "JSON inválido."}, status=400)
        else:
            payload = request.POST

        try:
            id_maquina = int(payload.get("id_maquina", ""))
        except (ValueError, TypeError):
            return JsonResponse({"ok": False, "error": "Parámetros inválidos."}, status=400)

        observacion = payload.get("observacion", "")
        ok, error, normalizada = guardar_observacion_planilla_maquina(
            base_empresa, id_maquina, observacion
        )
        if not ok:
            return JsonResponse(
                {"ok": False, "error": error or "No se pudo guardar la observación."},
                status=400,
            )
        return JsonResponse({"ok": True, "observacion_planilla": normalizada})


class MaquinaPlanillaControlCalidadAPIView(MprLoginRequiredMixin, MprPermisoMixin, View):
    """API JSON: datos de planilla Control de Calidad para impresión."""

    permiso_requerido = "mpr.maquinas_lineas"

    def get(self, request, *args, **kwargs):
        from datetime import date as _date

        from mpr.services_maquina_linea import construir_datos_planilla_control_calidad

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"ok": False, "error": "Empresa inválida."}, status=400)

        fecha_str = (request.GET.get("fecha") or "").strip()
        if not fecha_str:
            return JsonResponse({"ok": False, "error": "Fecha requerida."}, status=400)
        try:
            fecha = _date.fromisoformat(fecha_str)
        except ValueError:
            return JsonResponse({"ok": False, "error": "Fecha inválida."}, status=400)

        id_linea_raw = (request.GET.get("id_linea") or "").strip()
        id_linea = None
        if id_linea_raw:
            try:
                id_linea = int(id_linea_raw)
            except (ValueError, TypeError):
                return JsonResponse({"ok": False, "error": "Línea inválida."}, status=400)

        datos = construir_datos_planilla_control_calidad(
            base_empresa, fecha, id_linea=id_linea
        )
        return JsonResponse({"ok": True, **datos})


class OperarioUsuarioMapView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Vincula operarios (legajo) con usuarios de login para la carga móvil."""

    template_name = "mpr/operario_usuario_map.html"
    permiso_requerido = "mpr.maquinas_lineas"

    def get_context_data(self, **kwargs):
        from mpr.services import listar_operarios_crud
        from mpr.services_operario import listar_mapeos, listar_usuarios
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        context["operarios"] = listar_operarios_crud(base_empresa, incluir_anulados=False)
        context["usuarios"] = listar_usuarios(base_empresa)
        context["mapeos"] = listar_mapeos(base_empresa)
        return context

    def post(self, request, *args, **kwargs):
        from mpr.services_operario import map_operario_usuario, desmapear_usuario
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:operario_usuario_map")
        accion = (request.POST.get("accion") or "").strip()
        if accion == "desmapear":
            try:
                id_usuario = int(request.POST.get("id_usuario", ""))
            except (ValueError, TypeError):
                messages.error(request, "Usuario inválido.")
                return redirect("mpr:operario_usuario_map")
            ok, error = desmapear_usuario(base_empresa, id_usuario)
            messages.success(request, "Vínculo eliminado.") if ok else messages.error(request, error or "No se pudo desvincular.")
            return redirect("mpr:operario_usuario_map")
        try:
            id_operario = int(request.POST.get("id_operario", ""))
            id_usuario = int(request.POST.get("id_usuario", ""))
        except (ValueError, TypeError):
            messages.error(request, "Seleccioná un operario y un usuario.")
            return redirect("mpr:operario_usuario_map")
        ok, error = map_operario_usuario(base_empresa, id_operario, id_usuario)
        messages.success(request, "Operario vinculado al usuario.") if ok else messages.error(request, error or "No se pudo vincular.")
        return redirect("mpr:operario_usuario_map")


class OperarioLineaView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Asignación de la línea habitual (versionada) de cada operario."""

    template_name = "mpr/operario_linea.html"
    permiso_requerido = "mpr.maquinas_lineas"

    def get_context_data(self, **kwargs):
        from mpr.services import listar_operarios_crud
        from mpr.services_maquina_linea import listar_lineas
        from mpr.repositories.operario_linea import lineas_habituales_vigentes
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        operarios = listar_operarios_crud(base_empresa, incluir_anulados=False)
        lineas = listar_lineas(base_empresa, solo_activas=True)
        mapa = lineas_habituales_vigentes(base_empresa, date.today()) if base_empresa else {}
        nombre_por_linea = {l["id"]: l["nombre"] for l in lineas}
        for op in operarios:
            lid = mapa.get(op.get("id_sue_abm_empleado"))
            op["id_linea_habitual"] = lid
            op["linea_habitual_nombre"] = nombre_por_linea.get(lid, "")
        context["operarios"] = operarios
        context["lineas"] = lineas
        return context

    def post(self, request, *args, **kwargs):
        from mpr.services_operario import set_linea_habitual_operario
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:operario_linea")
        try:
            id_operario = int(request.POST.get("id_operario", ""))
            id_linea = int(request.POST.get("id_linea", ""))
        except (ValueError, TypeError):
            messages.error(request, "Seleccioná un operario y una línea.")
            return redirect("mpr:operario_linea")
        ok, error = set_linea_habitual_operario(base_empresa, id_operario, id_linea)
        if ok:
            messages.success(request, "Línea habitual actualizada.")
        else:
            messages.error(request, error or "No se pudo actualizar la línea habitual.")
        return redirect("mpr:operario_linea")


class ParteMovilOperarioView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Carga de parte de producción desde el móvil (operario).

    Resuelve automáticamente operario, turno (roster del día) y línea (habitual u
    override) y arma una grilla de máquinas -> artículos vigentes con captura en
    docenas/pares. Guardar deja el parte `pendiente` (o `borrador`) con
    `origen=movil_operario`, sin mover stock. Exige `mpr.parte_operario`.
    """

    permiso_requerido = "mpr.parte_operario"

    def get_template_names(self):
        from core.utils.template_selector import get_template_for_device
        return [get_template_for_device(self.request, "mpr/parte_operario.html")]

    def _resolver_operario(self, base_empresa, session_user):
        from mpr.repositories.operario_usuario import resolver_operario_por_usuario
        id_operario = session_user.get("id_operario")
        if not id_operario and base_empresa:
            id_operario = resolver_operario_por_usuario(
                base_empresa, session_user.get("id_usuario")
            )
            if id_operario:
                session_user["id_operario"] = id_operario
                self.request.session["user"] = session_user
                self.request.session.modified = True
        return id_operario

    def get_context_data(self, **kwargs):
        from mpr.services_parte_movil import construir_grilla_carga_movil
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        session_user = self.request.session.get("user", {}) or {}
        id_operario = self._resolver_operario(base_empresa, session_user)
        id_usuario = session_user.get("id_usuario")
        context["id_operario"] = id_operario
        context["tiene_operario"] = bool(id_operario)
        context["nombre_usuario"] = (
            session_user.get("nombre_completo") or session_user.get("cod_usuario")
        )
        context["ok_msg"] = self.request.session.pop("parte_movil_ok", None)
        context["error_msg"] = self.request.session.pop("parte_movil_error", None)
        if not id_operario:
            context["estado_borde"] = "sin_operario"
            return context
        id_turno = self._parse_id_turno(self.request.GET.get("turno"))
        grilla = construir_grilla_carga_movil(
            base_empresa, id_operario, id_usuario, id_turno=id_turno
        )
        context.update(grilla)
        return context

    @staticmethod
    def _parse_id_turno(raw) -> Optional[int]:
        from core.utils.administranet_types import to_int_or_none
        return to_int_or_none(raw)

    def post(self, request, *args, **kwargs):
        from django.shortcuts import redirect
        from mpr.services import obtener_operario
        from mpr.services_parte_movil import registrar_parte_movil

        base_empresa = _get_base_empresa(request)
        session_user = request.session.get("user", {}) or {}
        id_operario = self._resolver_operario(base_empresa, session_user)
        id_usuario = session_user.get("id_usuario")
        if not id_operario:
            request.session["parte_movil_error"] = (
                "Tu usuario no tiene un operario asociado. Contactá al supervisor."
            )
            return redirect("mpr:parte_movil_operario")

        op = obtener_operario(base_empresa, id_operario) or {}
        operario_nombre = (
            op.get("nombre_empleado")
            or session_user.get("nombre_completo")
            or "-"
        )
        accion = (request.POST.get("accion") or "enviar").strip()
        estado = "borrador" if accion == "borrador" else "pendiente"
        celdas = self._parsear_celdas(request.POST)
        id_turno = self._parse_id_turno(request.POST.get("id_turno"))
        ok, error, _id = registrar_parte_movil(
            base_empresa,
            id_operario,
            operario_nombre,
            id_usuario,
            celdas,
            id_turno=id_turno,
            estado=estado,
        )
        if ok:
            request.session["parte_movil_ok"] = (
                "Parte guardado como borrador."
                if estado == "borrador"
                else "Parte enviado. Queda pendiente de aprobación del supervisor."
            )
        else:
            request.session["parte_movil_error"] = error or "No se pudo guardar el parte."
        redirect_url = reverse("mpr:parte_movil_operario")
        if id_turno is not None:
            redirect_url = f"{redirect_url}?turno={id_turno}"
        return redirect(redirect_url)

    @staticmethod
    def _parsear_celdas(post):
        """Extrae celdas desde inputs doc_<maquina>_<articulo> / par_<maquina>_<articulo>."""
        import re

        nombres = {
            k[len("maqnombre_"):]: v
            for k, v in post.items()
            if k.startswith("maqnombre_")
        }
        patron = re.compile(r"^(doc|par)_(\d+)_(\d+)$")
        celdas: dict = {}
        for key, val in post.items():
            m = patron.match(key)
            if not m:
                continue
            tipo, maq, art = m.group(1), m.group(2), m.group(3)
            cel = celdas.setdefault(
                (maq, art),
                {"id_maquina": int(maq), "id_articulo": int(art), "docenas": 0, "pares": 0},
            )
            try:
                num = int(val or 0)
            except (TypeError, ValueError):
                num = 0
            cel["docenas" if tipo == "doc" else "pares"] = num
        out = []
        for (maq, _art), cel in celdas.items():
            cel["maquina_nombre"] = nombres.get(maq)
            out.append(cel)
        return out


class PartesPendientesView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Bandeja de partes pendientes de aprobación (supervisor)."""

    permiso_requerido = "mpr.aprobar_parte"
    template_name = "mpr/partes_pendientes.html"

    def get_context_data(self, **kwargs):
        from datetime import date as _date
        from mpr.services import listar_turnos
        from mpr.services_parte_movil import listar_partes_pendientes

        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        fecha = None
        fecha_str = (self.request.GET.get("fecha") or "").strip()
        if fecha_str:
            try:
                fecha = _date.fromisoformat(fecha_str)
            except ValueError:
                fecha = None
        id_turno = to_int_or_none(self.request.GET.get("turno"))
        incluir_borrador = self.request.GET.get("borradores") == "1"

        context["partes"] = listar_partes_pendientes(
            base_empresa, fecha=fecha, id_turno=id_turno, incluir_borrador=incluir_borrador
        )
        context["turnos"] = listar_turnos(base_empresa)
        context["f_fecha"] = fecha_str
        context["f_turno"] = id_turno
        context["f_borradores"] = incluir_borrador
        context["ok_msg"] = self.request.session.pop("aprobacion_ok", None)
        context["error_msgs"] = self.request.session.pop("aprobacion_errores", None)
        return context


class PartePendienteDetailView(MprLoginRequiredMixin, MprPermisoMixin, TemplateView):
    """Detalle editable de un parte + acción de aprobación."""

    permiso_requerido = "mpr.aprobar_parte"
    template_name = "mpr/parte_pendiente_detail.html"

    def get_context_data(self, **kwargs):
        from mpr.services_parte_movil import detalle_parte_para_aprobacion

        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_parte = kwargs.get("id_parte")
        detalle = detalle_parte_para_aprobacion(base_empresa, id_parte)
        context["detalle"] = detalle
        context["id_parte"] = id_parte
        context["error_msgs"] = self.request.session.pop("aprobacion_errores", None)
        return context

    def post(self, request, *args, **kwargs):
        from django.shortcuts import redirect
        from mpr.services import aprobar_parte_produccion
        from mpr.repositories import parte_movil as repo_pm

        base_empresa = _get_base_empresa(request)
        id_parte = kwargs.get("id_parte")
        session_user = request.session.get("user", {}) or {}
        id_sup = session_user.get("id_usuario") or 0
        forzar = request.POST.get("forzar_cupo") == "1"

        lineas = repo_pm.listar_lineas_aprobacion(base_empresa, id_parte)
        correcciones = {}
        for ln in lineas:
            lid = ln["id_mpr_parte_linea"]
            apr = request.POST.get(f"apr_{lid}")
            motivo = request.POST.get(f"motivo_{lid}", "")
            correcciones[lid] = {
                "cantidad_aprobada": apr if apr not in (None, "") else None,
                "motivo": motivo,
            }

        ok, errores, _idp = aprobar_parte_produccion(
            base_empresa, id_parte, correcciones, id_sup, forzar_cupo=forzar
        )
        if ok:
            request.session["aprobacion_ok"] = "Parte aprobado. Stock ingresado a Producción."
            return redirect("mpr:partes_pendientes")
        request.session["aprobacion_errores"] = errores
        return redirect("mpr:parte_pendiente_detail", id_parte=id_parte)


def _params_planificacion_turnos(
    request=None,
    *,
    semana=None,
    filtro=None,
    q=None,
    turno=None,
    incluir_semana=True,
):
    """Arma querystring de planificación de turnos preservando filtros activos."""
    if request is not None:
        if semana is None:
            semana = (request.POST.get("semana") or request.GET.get("semana") or "").strip()
        if filtro is None:
            filtro = (request.POST.get("filtro") or request.GET.get("filtro") or "").strip().lower()
        if q is None:
            q = (request.POST.get("q") or request.GET.get("q") or "").strip()
        if turno is None:
            turno = (request.POST.get("turno") or request.GET.get("turno") or "").strip()
    if filtro not in ("todos", "excepciones", "sin_asignar"):
        filtro = "todos"
    params = {}
    if incluir_semana and semana:
        params["semana"] = semana
    if filtro and filtro != "todos":
        params["filtro"] = filtro
    if q:
        params["q"] = q
    if turno:
        try:
            params["turno"] = str(int(turno))
        except (TypeError, ValueError):
            pass
    return params


def _redirect_planificacion_turnos(request=None, semana=None, filtro=None, q=None, turno=None):
    """Redirect a planificación de turnos preservando semana y filtros de grilla."""
    from django.urls import reverse
    from urllib.parse import urlencode

    params = _params_planificacion_turnos(
        request,
        semana=semana,
        filtro=filtro,
        q=q,
        turno=turno,
        incluir_semana=True,
    )
    base_url = reverse("mpr:planificacion_turnos")
    if params:
        return redirect(f"{base_url}?{urlencode(params)}")
    return redirect(base_url)


class PlanificacionTurnosView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """
    Pantalla de planificación semanal (roster): grilla operadores × 7 días.
    GET: muestra grilla de la semana seleccionada (default: semana actual).
    Query param: semana=YYYY-MM-DD (lunes de la semana); filtro=todos|sin_asignar|excepciones;
    q (búsqueda por nombre); turno (id int).
    Multi-turno: cada celda puede tener 0..N turnos; lineas activas para override.
    """

    template_name = "mpr/planificacion_turnos.html"

    def get_context_data(self, **kwargs):
        import json
        from urllib.parse import urlencode

        from mpr.services import (
            aplicar_filtros_roster_grilla,
            listar_roster_semana,
            listar_turnos,
        )
        from mpr.services_maquina_linea import listar_lineas
        from datetime import timedelta
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        filtro = (self.request.GET.get("filtro") or "todos").strip().lower()
        if filtro not in ("todos", "excepciones", "sin_asignar"):
            filtro = "todos"
        q_roster = (self.request.GET.get("q") or "").strip()
        turno_filtro_raw = (self.request.GET.get("turno") or "").strip()
        turno_filtro = None
        if turno_filtro_raw:
            try:
                turno_filtro = int(turno_filtro_raw)
            except (TypeError, ValueError):
                turno_filtro = None
        semana_str = self.request.GET.get("semana")
        if semana_str:
            try:
                from datetime import date as _date
                fecha_lunes = _date.fromisoformat(semana_str)
                fecha_lunes = fecha_lunes - timedelta(days=fecha_lunes.weekday())
            except ValueError:
                from datetime import date as _date
                hoy = _date.today()
                fecha_lunes = hoy - timedelta(days=hoy.weekday())
        else:
            from datetime import date as _date
            hoy = _date.today()
            fecha_lunes = hoy - timedelta(days=hoy.weekday())
        semana_anterior = fecha_lunes - timedelta(days=7)
        semana_siguiente = fecha_lunes + timedelta(days=7)
        fecha_domingo = fecha_lunes + timedelta(days=6)
        fecha_viernes = fecha_lunes + timedelta(days=4)
        turnos_activos = listar_turnos(base_empresa, solo_activos=True)
        roster_data = listar_roster_semana(base_empresa, fecha_lunes)
        lineas_activas = listar_lineas(base_empresa, solo_activas=True) if base_empresa else []
        operarios_todos = roster_data["operarios"]
        operarios = aplicar_filtros_roster_grilla(
            operarios_todos,
            roster_data["asignaciones"],
            roster_data["dias"],
            filtro=filtro,
            id_turno=turno_filtro,
            q=q_roster,
        )
        roster_query_params = _params_planificacion_turnos(
            self.request,
            semana=fecha_lunes.isoformat(),
            filtro=filtro,
            q=q_roster,
            turno=turno_filtro,
            incluir_semana=False,
        )
        roster_query = urlencode(roster_query_params) if roster_query_params else ""
        filtros_roster_activos = bool(
            q_roster
            or turno_filtro is not None
            or filtro != "todos"
        )
        from datetime import date as _date2
        hoy = _date2.today()
        context.update({
            "fecha_lunes": fecha_lunes,
            "fecha_viernes": fecha_viernes,
            "fecha_domingo": fecha_domingo,
            "semana_anterior": semana_anterior,
            "semana_siguiente": semana_siguiente,
            "turnos_activos": turnos_activos,
            "lineas": lineas_activas,
            "operarios": operarios,
            "operarios_todos": operarios_todos,
            "dias": roster_data["dias"],
            "asignaciones": roster_data["asignaciones"],
            "celdas_bloqueadas": roster_data.get("celdas_bloqueadas") or {},
            "hoy": hoy,
            "filtro_roster": filtro,
            "q_roster": q_roster,
            "turno_filtro": turno_filtro,
            "operarios_total_count": len(operarios_todos),
            "operarios_filtrados_count": len(operarios),
            "roster_query": roster_query,
            "filtros_roster_activos": filtros_roster_activos,
            "turnos_activos_json": json.dumps(
                [
                    {"id": t["id"], "nombre": t["nombre"]}
                    for t in (turnos_activos or [])
                ],
                ensure_ascii=False,
            ),
            "semana_iso": fecha_lunes.isoformat(),
        })
        return context


class AsignarTurnoRosterView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """
    POST: asigna (agrega) un turno a un operario en una fecha.
    Params POST: fecha (dd/MM/yyyy), id_operario, id_turno, semana (YYYY-MM-DD para redirect).
    Multi-turno: no reemplaza turnos ya asignados ese día.
    """

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        from mpr.services import asignar_turno_roster
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return _redirect_planificacion_turnos(request)
        fecha_str = (request.POST.get("fecha") or "").strip()
        id_operario_raw = request.POST.get("id_operario", "")
        id_turno_raw = request.POST.get("id_turno", "")
        try:
            id_operario = int(id_operario_raw)
            id_turno = int(id_turno_raw)
        except (ValueError, TypeError):
            messages.error(request, "Datos inválidos.")
            return _redirect_planificacion_turnos(request)
        id_linea_raw = (request.POST.get("id_linea") or "").strip()
        id_linea = None
        if id_linea_raw:
            try:
                id_linea = int(id_linea_raw)
            except (ValueError, TypeError):
                messages.error(request, "Línea de override inválida.")
                return _redirect_planificacion_turnos(request)
        ok, error = asignar_turno_roster(base_empresa, fecha_str, id_operario, id_turno, id_linea=id_linea)
        if ok:
            messages.success(request, "Turno asignado exitosamente.")
        else:
            messages.error(request, error or "Error al asignar turno.")
        return _redirect_planificacion_turnos(request)


class AsignarTurnoRosterMasivoView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """
    POST: asignación masiva de turno a varios operarios en un rango de fechas.
    Params POST: ids_operario (lista), id_turno, fecha_desde/fecha_hasta (YYYY-MM-DD),
    semana, filtro, modo (agregar|solo_vacio|reemplazar), id_linea opcional,
    alcance_dias (todos|lun_vie|personalizado), dias_semana (0-6 si personalizado).
    """

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        from mpr.services import asignar_turno_roster_rango, mensaje_flash_asignacion_masiva

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return _redirect_planificacion_turnos(request)

        ids_operario = request.POST.getlist("ids_operario")
        id_turno_raw = request.POST.get("id_turno", "")
        fecha_desde = (request.POST.get("fecha_desde") or "").strip()
        fecha_hasta = (request.POST.get("fecha_hasta") or "").strip()

        try:
            id_turno = int(id_turno_raw)
        except (ValueError, TypeError):
            messages.error(request, "Turno inválido.")
            return _redirect_planificacion_turnos(request)

        id_linea_raw = (request.POST.get("id_linea") or "").strip()
        id_linea = None
        if id_linea_raw:
            try:
                id_linea = int(id_linea_raw)
            except (ValueError, TypeError):
                messages.error(request, "Línea de override inválida.")
                return _redirect_planificacion_turnos(request)

        modo = (request.POST.get("modo") or "agregar").strip().lower()
        if modo not in ("agregar", "solo_vacio", "reemplazar"):
            modo = "agregar"

        alcance_dias = (request.POST.get("alcance_dias") or "todos").strip().lower()
        dias_semana = None
        if alcance_dias == "lun_vie":
            dias_semana = [0, 1, 2, 3, 4]
        elif alcance_dias == "personalizado":
            dias_semana = request.POST.getlist("dias_semana")
            if not dias_semana:
                messages.error(request, "Seleccioná al menos un día de la semana.")
                return _redirect_planificacion_turnos(request)

        ok, error, resumen = asignar_turno_roster_rango(
            base_empresa,
            ids_operario,
            id_turno,
            fecha_desde,
            fecha_hasta,
            id_linea=id_linea,
            modo=modo,
            dias_semana=dias_semana,
        )
        if ok:
            messages.success(request, mensaje_flash_asignacion_masiva(resumen, modo=modo))
        else:
            messages.error(request, error or "Error al asignar turnos.")

        return _redirect_planificacion_turnos(request)


class SetLineaOverrideRosterView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """
    POST: fija o limpia el override de línea de un turno del roster.
    Params POST: fecha (dd/MM/yyyy), id_operario, id_turno, id_linea (vacío = habitual/NULL),
    semana (YYYY-MM-DD para redirect), filtro.
    """

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        from mpr.services import set_linea_override_roster

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return _redirect_planificacion_turnos(request)
        fecha_str = (request.POST.get("fecha") or "").strip()
        id_operario_raw = request.POST.get("id_operario", "")
        id_turno_raw = request.POST.get("id_turno", "")
        try:
            id_operario = int(id_operario_raw)
            id_turno = int(id_turno_raw)
        except (ValueError, TypeError):
            messages.error(request, "Datos inválidos.")
            return _redirect_planificacion_turnos(request)
        id_linea_raw = (request.POST.get("id_linea") or "").strip()
        id_linea = None
        if id_linea_raw:
            try:
                id_linea = int(id_linea_raw)
            except (ValueError, TypeError):
                messages.error(request, "Línea de override inválida.")
                return _redirect_planificacion_turnos(request)
        ok, error = set_linea_override_roster(
            base_empresa, fecha_str, id_operario, id_turno, id_linea=id_linea
        )
        if ok:
            if id_linea is None:
                messages.success(request, "Línea restaurada a la habitual.")
            else:
                messages.success(request, "Línea de override actualizada.")
        else:
            messages.error(request, error or "Error al actualizar la línea.")
        return _redirect_planificacion_turnos(request)


class EliminarAsignacionRosterView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """
    POST: elimina la asignación de un turno concreto (fecha + operario + turno).
    Params POST: fecha (dd/MM/yyyy), id_operario, id_turno, semana, filtro.
    """

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        from mpr.services import eliminar_asignacion_roster
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return _redirect_planificacion_turnos(request)
        fecha_str = (request.POST.get("fecha") or "").strip()
        id_operario_raw = request.POST.get("id_operario", "")
        id_turno_raw = (request.POST.get("id_turno") or "").strip()
        try:
            id_operario = int(id_operario_raw)
        except (ValueError, TypeError):
            messages.error(request, "Datos inválidos.")
            return _redirect_planificacion_turnos(request)
        id_turno = None
        if id_turno_raw:
            try:
                id_turno = int(id_turno_raw)
            except (ValueError, TypeError):
                messages.error(request, "Turno inválido.")
                return _redirect_planificacion_turnos(request)
        ok, error = eliminar_asignacion_roster(
            base_empresa, fecha_str, id_operario, id_turno=id_turno
        )
        if ok:
            messages.success(request, "Asignación eliminada exitosamente.")
        else:
            messages.error(request, error or "Error al eliminar asignación.")
        return _redirect_planificacion_turnos(request)


class MprConsultaPartesMixin:
    """Consulta de partes: supervisor ve todos; operario solo los suyos."""

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_puede_consultar_partes(getattr(request, "user", None)):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class PartesConsultaView(MprLoginRequiredMixin, MprConsultaPartesMixin, TemplateView):
    """Listado histórico de partes de producción con filtros."""

    template_name = "mpr/partes_consulta.html"

    def get_context_data(self, **kwargs):
        from datetime import date as _date
        from mpr.services import listar_partes_consulta

        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        session_user = self.request.session.get("user", {}) or {}
        session_id_usuario = to_int_or_none(session_user.get("id_usuario"))

        fecha_desde = None
        fecha_hasta = None
        fecha_desde_str = (self.request.GET.get("fecha_desde") or "").strip()
        fecha_hasta_str = (self.request.GET.get("fecha_hasta") or "").strip()
        if fecha_desde_str:
            try:
                fecha_desde = _date.fromisoformat(fecha_desde_str)
            except ValueError:
                fecha_desde = None
        if fecha_hasta_str:
            try:
                fecha_hasta = _date.fromisoformat(fecha_hasta_str)
            except ValueError:
                fecha_hasta = None

        estado_filtro = (self.request.GET.get("estado") or "").strip().lower()
        id_usuario_filtro = None
        if not _usuario_ve_todos_los_partes(self.request.user):
            id_usuario_filtro = session_id_usuario

        partes = []
        if base_empresa:
            partes = listar_partes_consulta(
                base_empresa,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                estado=estado_filtro or None,
                id_usuario=id_usuario_filtro,
            )
            for p in partes:
                p["abrir_url"] = _abrir_url_parte_consulta(p, session_id_usuario)

        context["partes"] = partes
        context["f_fecha_desde"] = fecha_desde_str
        context["f_fecha_hasta"] = fecha_hasta_str
        context["f_estado"] = estado_filtro
        context["es_supervisor_partes"] = _usuario_ve_todos_los_partes(self.request.user)
        context["session_id_usuario"] = session_id_usuario
        return context


class ParteCupoFabricandoView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """GET JSON: cupo Fabricando live por id_articulo."""

    def get(self, request, *args, **kwargs):
        from mpr.services import cupo_fabricando_por_articulo

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            return JsonResponse({"cupos": {}})

        raw_ids = (request.GET.get("ids") or "").strip()
        ids: list[int] = []
        for chunk in raw_ids.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            val = to_int_or_none(chunk)
            if val is not None:
                ids.append(val)

        cupos_map = cupo_fabricando_por_articulo(base_empresa, ids)
        cupos_json = {str(k): float(v or 0) for k, v in cupos_map.items()}
        return JsonResponse({"cupos": cupos_json})


# ---------------------------------------------------------------------------
# ETAPA 4: Parte de Producción (Ledger OPP-parte)
# ---------------------------------------------------------------------------

class ParteProduccionView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Vista de captura de parte de producción (grilla planilla QC analista)."""

    template_name = "mpr/parte_produccion.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from mpr.services import listar_turnos, obtener_config_mpr
        from mpr.services_maquina_linea import (
            construir_grilla_parte_planilla,
            listar_lineas,
            listar_maquinas,
        )

        base_empresa = _get_base_empresa(self.request)
        context.update(_context_filtro_marcas(self.request, base_empresa))
        if not base_empresa:
            return context

        config_mpr = obtener_config_mpr(base_empresa)
        context["bloquear_parte_supera_fabricando"] = config_mpr.get(
            "bloquear_parte_supera_fabricando", True
        )
        context["unidades_por_docena_parte"] = UNIDADES_POR_DOCENA_OPP
        context["turnos_activos"] = listar_turnos(base_empresa, solo_activos=True)
        context["lineas_filtro"] = listar_lineas(base_empresa, solo_activas=True)
        context["maquinas_filtro"] = listar_maquinas(base_empresa, solo_activas=True)
        from mpr.presentacion_operativa import resolver_modo_presentacion_operativa

        context["modo_presentacion"] = resolver_modo_presentacion_operativa(self.request)
        marcas_incluidos = _parse_marcas_incluidos(self.request)

        fecha_str = (self.request.GET.get("fecha") or "").strip()
        id_linea_raw = (self.request.GET.get("id_linea") or "").strip()
        id_maquina_raw = (self.request.GET.get("id_maquina") or "").strip()
        context["fecha_str"] = fecha_str
        context["id_linea"] = id_linea_raw
        context["id_maquina"] = id_maquina_raw

        warnings_opp = self.request.session.pop("parte_warnings", None)
        if warnings_opp:
            context["warnings_opp"] = warnings_opp

        if not fecha_str:
            messages.info(self.request, "Seleccione una fecha para cargar la planilla.")
            return context

        try:
            from datetime import datetime

            fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y").date()
            id_linea = int(id_linea_raw) if id_linea_raw else None
            id_maquina = int(id_maquina_raw) if id_maquina_raw else None
            # La búsqueda de artículo es filtro predictivo en cliente (chrome), no GET.
            grilla_planilla = construir_grilla_parte_planilla(
                base_empresa,
                fecha_obj,
                id_linea=id_linea,
                id_maquina=id_maquina,
                marcas_incluidos=marcas_incluidos or None,
                q=None,
            )
            context["grilla_planilla"] = grilla_planilla
            context["fecha_obj"] = fecha_obj
        except (ValueError, TypeError):
            messages.error(self.request, "Fecha o filtros inválidos.")

        return context


class RegistrarParteProduccionView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """POST: Registra un parte de producción completo (planilla QC multi-turno)."""

    def post(self, request):
        from datetime import datetime
        from mpr.services import registrar_parte_produccion

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:parte_produccion")

        fecha_str = (request.POST.get("fecha") or "").strip()

        if not fecha_str:
            messages.error(request, "La fecha es obligatoria.")
            return redirect("mpr:parte_produccion")

        try:
            fecha_obj = datetime.strptime(fecha_str, "%d/%m/%Y").date()
        except (ValueError, TypeError):
            messages.error(request, "Fecha inválida.")
            return redirect("mpr:parte_produccion")

        lineas = _parte_lineas_desde_post(request.POST)
        modo_planilla = any(ln.get("id_mpr_maquina") for ln in lineas)
        turno_id_raw = (request.POST.get("turno_id") or "").strip()
        accion_raw = (request.POST.get("accion") or "aprobar").strip().lower()
        accion = "borrador" if accion_raw == "borrador" else "aprobar"

        notas = (request.POST.get("notas") or "").strip()
        id_usuario = getattr(request.user, "id", 0) or 0

        try:
            if modo_planilla:
                partes, warnings = registrar_parte_produccion(
                    base_empresa,
                    fecha_obj,
                    None,
                    id_usuario,
                    lineas,
                    notas,
                    modo_planilla=True,
                    accion=accion,
                )
            else:
                if not turno_id_raw:
                    messages.error(request, "Fecha y turno son requeridos.")
                    return redirect("mpr:parte_produccion")
                turno_id = int(turno_id_raw)
                partes, warnings = registrar_parte_produccion(
                    base_empresa, fecha_obj, turno_id, id_usuario, lineas, notas
                )
            if warnings:
                request.session["parte_warnings"] = warnings
            if accion == "borrador" and modo_planilla:
                messages.success(request, "Borrador del parte guardado correctamente.")
            else:
                messages.success(request, "Parte de producción registrado exitosamente.")
        except ValidationError as ve:
            msg = ve.messages[0] if getattr(ve, "messages", None) else str(ve)
            messages.error(request, msg)
        except Exception as e:
            messages.error(request, f"Error al registrar el parte: {e}")

        redirect_url = reverse("mpr:parte_produccion")
        qs_params = {"fecha": fecha_str}
        id_linea_raw = (request.POST.get("id_linea") or request.GET.get("id_linea") or "").strip()
        id_maquina_raw = (request.POST.get("id_maquina") or request.GET.get("id_maquina") or "").strip()
        if id_linea_raw:
            qs_params["id_linea"] = id_linea_raw
        if id_maquina_raw:
            qs_params["id_maquina"] = id_maquina_raw
        qs = _urlencode_con_marcas(qs_params, _parse_marcas_incluidos(request))
        return redirect(f"{redirect_url}?{qs}")


class AjusteParteView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """POST: Registra un ajuste delta sobre una línea de parte de producción."""

    def post(self, request, parte_id):
        from decimal import Decimal, InvalidOperation
        from django.core.exceptions import ValidationError
        from mpr.services import agregar_ajuste_parte

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:parte_produccion")

        try:
            id_articulo = int(request.POST.get("id_articulo", ""))
            id_operario = int(request.POST.get("id_operario", ""))
            delta = Decimal(str(request.POST.get("delta", "")).replace(",", "."))
            motivo = (request.POST.get("motivo") or "").strip()
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, "Datos del ajuste inválidos.")
            return redirect("mpr:parte_produccion")

        id_usuario = getattr(request.user, "id", 0) or 0

        try:
            agregar_ajuste_parte(
                base_empresa, parte_id, id_articulo, id_operario, delta, motivo, id_usuario
            )
            messages.success(request, "Ajuste registrado exitosamente.")
        except ValidationError as ve:
            messages.error(request, str(ve.message if hasattr(ve, "message") else ve))
        except Exception as e:
            messages.error(request, f"Error al registrar ajuste: {e}")

        return redirect("mpr:parte_produccion")


# =============================================================================
# Etapa 5: Transiciones de lote (TransicionLoteView)
# =============================================================================

class TransicionLoteView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """POST: registra una transferencia de stock entre etapas MPR (Producción, Planchado, etc.).

    Parámetros POST esperados:
        id_articulo: int — ID componente (nivel al que opera la transición).
        tipo_origen: str — constante TIPO_MPR_* del depósito de origen.
        tipo_destino: str — constante TIPO_MPR_* del depósito de destino.
        cantidad: Decimal — unidades a transferir.
    """

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        from django.contrib import messages as dj_messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            dj_messages.error(request, "No se pudo determinar la empresa activa.")
            return _redirect_tablero_produccion(request)

        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else 0
        except (TypeError, ValueError):
            id_usuario = 0

        id_articulo = to_int_or_none(request.POST.get("id_articulo"))
        tipo_origen = (request.POST.get("tipo_origen") or "").strip()
        tipo_destino = (request.POST.get("tipo_destino") or "").strip()
        cantidad = to_decimal_or_none(request.POST.get("cantidad"))

        if not id_articulo:
            dj_messages.error(request, "Artículo no indicado.")
            return _redirect_tablero_produccion(request)

        try:
            ok, codigo_mov, nro_comp, msg_error = transferir_stock_entre_etapas(
                base_empresa=base_empresa,
                id_usuario=id_usuario,
                id_articulo=id_articulo,
                tipo_origen=tipo_origen,
                tipo_destino=tipo_destino,
                cantidad=cantidad,
            )
            if ok:
                dj_messages.success(
                    request,
                    f"Transición {tipo_origen} → {tipo_destino} registrada correctamente "
                    f"(comprobante {nro_comp}).",
                )
            else:
                dj_messages.error(request, msg_error or "Error al registrar la transición.")
        except MprSchemaError as e:
            return _mpr_schema_error_redirect(request, e)
        except Exception as e:
            logger.warning("TransicionLoteView error: %s", e, exc_info=True)
            dj_messages.error(request, f"Error inesperado al procesar la transición: {e}")

        return _redirect_tablero_produccion(request)


# =============================================================================
# Etapa 6: Trazabilidad OPT
# =============================================================================


class TrazabilidadOptView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """GET: Trazabilidad detallada de una OPT por id_lista_produccion (E6).

    Integra 6 fuentes de datos para mostrar un timeline cronológico de todos los eventos
    asociados a la OPT: historico, movimiento_stock (OPP), partes E4+, transiciones E5,
    armados y sus imputaciones.

    URL: /mpr/opt/<id_lista>/trazabilidad/
    """

    template_name = "mpr/trazabilidad_opt.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_lista = self.kwargs.get("id_lista", 0)
        if not base_empresa or not id_lista:
            raise Http404("Parámetros insuficientes para trazabilidad.")
        from mpr.services import construir_trazabilidad_opt
        trazabilidad = construir_trazabilidad_opt(base_empresa, id_lista)
        cabecera = trazabilidad.get("cabecera") or {}
        if not cabecera:
            raise Http404("OPT no encontrada para esta empresa.")
        emp_cabecera = cabecera.get("base_empresa", "")
        if emp_cabecera and emp_cabecera != base_empresa:
            raise Http404("OPT no pertenece a esta empresa.")
        context.update({
            "trazabilidad": trazabilidad,
            "cabecera": cabecera,
            "eventos": trazabilidad.get("eventos", []),
            "fuentes_fallidas": trazabilidad.get("fuentes_fallidas", []),
            "id_lista": id_lista,
            "opt_detail_url": reverse("mpr:opt_detail", kwargs={"id_lista": id_lista}),
            "tablero_url": reverse("mpr:tablero"),
            "opt_list_url": reverse("mpr:opt_list"),
        })
        return context


# =============================================================================
# Anulación de envíos tablero (Opción A — por fila, supervisor)
# =============================================================================


class EnviosProduccionListView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """Lista envíos del tablero con saldo anulable (FIFO vs partes)."""

    template_name = "mpr/envios_produccion.html"

    def get(self, request, *args, **kwargs):
        from datetime import date
        from django.contrib import messages
        from core.utils.administranet_types import to_date_or_none
        from mpr.services import listar_lotes_envios_produccion_anulables

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")

        fecha_str = (request.GET.get("fecha") or "").strip()
        fecha_iso = to_date_or_none(fecha_str) if fecha_str else None
        if fecha_iso:
            fecha_obj = date.fromisoformat(fecha_iso)
            fecha_display = fecha_iso
        else:
            fecha_obj = date.today()
            fecha_display = fecha_obj.isoformat()

        incluir_anulados = (request.GET.get("incluir_anulados") or "").strip() == "1"
        lotes = []
        try:
            lotes = listar_lotes_envios_produccion_anulables(
                base_empresa,
                fecha_obj,
                incluir_anulados=incluir_anulados,
            )
        except MprSchemaError as e:
            return _mpr_schema_error_redirect(request, e)
        except Exception as e:
            logger.warning("EnviosProduccionListView error: %s", e, exc_info=True)
            lotes = []

        return self.render_to_response(
            {
                "lotes": lotes,
                "fecha": fecha_display,
                "fecha_etiqueta": fecha_obj.strftime("%d/%m/%Y"),
                "incluir_anulados": incluir_anulados,
                "titulo_pantalla": "Anulación de envíos a producción",
            }
        )


class AnularEnviosProduccionView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """POST: anula envíos seleccionados (ledger-only)."""

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        from django.contrib import messages as dj_messages
        from core.utils.administranet_types import to_int_or_none
        from mpr.services import anular_envios_produccion_seleccionados

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            dj_messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:envios_produccion")

        session_user = request.session.get("user", {})
        try:
            id_usuario = (
                int(session_user.get("id_usuario"))
                if session_user.get("id_usuario") is not None
                else 0
            )
        except (TypeError, ValueError):
            id_usuario = 0

        ids = []
        for raw in request.POST.getlist("envio_ids"):
            eid = to_int_or_none(raw)
            if eid is not None:
                ids.append(eid)

        ok, n, advertencias, error = anular_envios_produccion_seleccionados(
            base_empresa, ids, id_usuario
        )

        qs_parts = []
        fecha = (request.POST.get("fecha") or "").strip()
        if fecha:
            qs_parts.append(f"fecha={fecha}")
        if (request.POST.get("incluir_anulados") or "").strip() == "1":
            qs_parts.append("incluir_anulados=1")
        redirect_url = reverse("mpr:envios_produccion")
        if qs_parts:
            redirect_url += "?" + "&".join(qs_parts)

        if ok and n:
            sufijo = "s" if n != 1 else ""
            dj_messages.success(
                request,
                f"{n} envío{sufijo} anulado{sufijo} correctamente.",
            )
        elif error:
            dj_messages.error(request, error)
        for w in advertencias:
            dj_messages.warning(request, w)

        return redirect(redirect_url)


# =============================================================================
# Etapa 7: Envío directo a producción desde el Tablero (ledger-componente)
# =============================================================================


class EnviarProduccionLoteView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """POST: registra un lote de envíos a producción desde el tablero (E7).

    Parsea inputs con prefijo envio_{id_art} y pendiente_{id_art};
    delega en enviar_a_produccion_lote (ledger-only, no toca MySQL legacy).
    """

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        from decimal import Decimal
        from django.contrib import messages as dj_messages
        from core.utils.administranet_types import to_int_or_none, to_decimal_or_none
        from mpr.services import enviar_a_produccion_lote

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            dj_messages.error(request, "No se pudo determinar la empresa activa.")
            return _redirect_tablero_produccion(request)

        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else 0
        except (TypeError, ValueError):
            id_usuario = 0

        items = []
        pendientes = {}
        id_arts_envio: set = set()
        import re as _re_env

        for key in request.POST:
            m = _re_env.match(r"^envio_(\d+)(?:_(docenas|unidades))?$", key)
            if m:
                id_arts_envio.add(int(m.group(1)))
        for id_art in sorted(id_arts_envio):
            qty_u = _envio_cantidad_unidades_desde_post(request.POST, id_art)
            if qty_u > 0:
                items.append((id_art, Decimal(qty_u)))
        for key, value in request.POST.items():
            if key.startswith("resta_urgente_"):
                id_art = to_int_or_none(key[14:])
                pend = to_decimal_or_none(value)
                if id_art is not None and pend is not None:
                    pendientes[id_art] = pend
            elif key.startswith("pendiente_"):
                id_art = to_int_or_none(key[10:])
                pend = to_decimal_or_none(value)
                if id_art is not None and pend is not None and id_art not in pendientes:
                    pendientes[id_art] = pend

        filtros_qs = (request.POST.get("filtros_qs") or "").strip()
        ok, creados, warnings, error = enviar_a_produccion_lote(
            base_empresa, id_usuario, items, pendientes
        )

        if ok:
            if creados:
                sufijo = "s" if creados != 1 else ""
                dj_messages.success(
                    request,
                    f"{creados} componente{sufijo} enviado{sufijo} a producción.",
                )
            for w in warnings:
                dj_messages.warning(request, w)
        else:
            dj_messages.error(request, error or "Error al registrar envíos.")

        return _redirect_tablero_produccion(request, filtros_qs or None)


# =============================================================================
# Etapa 10: Clasificación de Producción (pantalla única consolidada)
#
# El planchado es un momento dentro de la producción y no deja stock. La
# clasificación sale directo de Producción hacia {Semi | 2da | Descarte}, en
# un único formulario multi-línea con fecha de carga (permite carga diferida).
# Reemplaza las pantallas de Inspección y Clasificación de la Etapa 9.
# =============================================================================


class ClasificacionProduccionView(MprLoginRequiredMixin, MprEscritorioVerMixin, TemplateView):
    """GET: pantalla de Control de calidad consolidado por artículo.

    Universo del día completo (sin filtro Turno). Semi único por artículo;
    2da/scrap por operario+turno del parte.
    """

    template_name = "mpr/clasificacion_produccion.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from datetime import date as _date, datetime as _dt
        from mpr.services import construir_grilla_clasificacion_produccion, TIPO_MPR_PRODUCCION
        from mpr.presentacion_operativa import resolver_modo_presentacion_operativa

        base_empresa = _get_base_empresa(self.request)
        modo_presentacion = resolver_modo_presentacion_operativa(self.request)
        marcas_incluidos = _parse_marcas_incluidos(self.request)
        fecha_str = (self.request.GET.get("fecha") or "").strip()
        # Default: roster completo. «Solo pendiente» = ver_roster=0.
        _vr = (self.request.GET.get("ver_roster") or "").strip().lower()
        if _vr in ("0", "false", "no", "pendiente"):
            ver_roster = False
        else:
            ver_roster = True

        fecha_obj = None
        if fecha_str:
            try:
                fecha_obj = _dt.strptime(fecha_str, "%d/%m/%Y").date()
            except ValueError:
                pass

        grilla_vacia = {
            "bloques": [],
            "filas": [],
            "filas_vacio": True,
            "hay_filas_editables": False,
            "confirmadas_ocultas": 0,
            "bloqueos": [],
            "requiere_fecha": fecha_obj is None,
            "requiere_fecha_turno": False,
            "componentes": [],
            "componentes_vacio": True,
            "tiene_borrador": False,
            "borrador_incompatible": False,
            "aviso_borrador": "",
        }
        try:
            grilla = (
                construir_grilla_clasificacion_produccion(
                    base_empresa,
                    fecha_obj,
                    None,
                    ver_roster_completo=ver_roster,
                    marcas_incluidos=marcas_incluidos or None,
                )
                if base_empresa
                else {
                    **grilla_vacia,
                    "requiere_fecha": True,
                }
            )
        except Exception as e:
            _log_mpr_schema_error(e)
            context["mpr_schema_error_modal"] = (
                f"{e}\n\nSi falta esquema MPR, ejecutá:\n"
                f"docker exec Synap_app python manage.py apply_mpr_core_tables {base_empresa or '<base_empresa>'}"
            )
            grilla = grilla_vacia

        context.update({
            "titulo_pantalla": "Control de calidad",
            "tipo_origen": TIPO_MPR_PRODUCCION,
            "url_registrar": reverse("mpr:clasificacion_produccion_registrar"),
            "fecha_hoy": _date.today().strftime("%d/%m/%Y"),
            "fecha_str": fecha_str,
            "turno_id": "",
            "turno_nombre": "",
            "turnos_activos": [],
            "bloques": grilla.get("bloques", []),
            "filas": grilla.get("filas", []),
            "filas_vacio": grilla.get("filas_vacio", True),
            "hay_filas_editables": grilla.get("hay_filas_editables", False),
            "confirmadas_ocultas": grilla.get("confirmadas_ocultas", 0),
            "bloqueos": grilla.get("bloqueos", []),
            "requiere_fecha": grilla.get("requiere_fecha", fecha_obj is None),
            "requiere_fecha_turno": False,
            "ver_roster": ver_roster,
            "puede_ver_roster_completo": True,
            "componentes": grilla.get("componentes", grilla.get("filas", [])),
            "componentes_vacio": grilla.get("componentes_vacio", grilla.get("filas_vacio", True)),
            "tiene_borrador": grilla.get("tiene_borrador", False),
            "borrador_incompatible": grilla.get("borrador_incompatible", False),
            "aviso_borrador": grilla.get("aviso_borrador", ""),
            "unidades_por_docena_clasificacion": UNIDADES_POR_DOCENA_OPP,
            "modo_presentacion": modo_presentacion,
            "presentacion_query_base": _urlencode_con_marcas(
                {
                    k: v for k, v in (
                        ("fecha", fecha_str),
                        ("ver_roster", "1" if ver_roster else "0"),
                    ) if v
                },
                marcas_incluidos,
            ),
            "clasificacion_feedback": self.request.session.pop(
                "clasificacion_feedback_modal", None
            ),
            **_context_filtro_marcas(self.request, base_empresa),
        })
        return context


class RegistrarClasificacionProduccionView(MprLoginRequiredMixin, MprEscritorioVerMixin, View):
    """POST: confirma o guarda borrador del CC consolidado por artículo.

    Usa ``parsear_post_cc_consolidado`` + ``confirmar_cc_consolidado``.
    MUST NOT llamar ``transferir_stock_lote`` directamente.
    """

    http_method_names = ["post"]

    def post(self, request, *args, **kwargs):
        from django.contrib import messages as dj_messages
        from mpr.services import _parse_fecha_ddmmaaaa
        from mpr.services_cc_consolidado import (
            confirmar_cc_consolidado,
            parsear_post_cc_consolidado,
        )

        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            dj_messages.error(request, "No se pudo determinar la empresa activa.")
            return _redirect_clasificacion_produccion(request)

        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else 0
        except (TypeError, ValueError):
            id_usuario = 0

        fecha_str = (request.POST.get("fecha") or "").strip()
        fecha_obj, err_fecha = _parse_fecha_ddmmaaaa(fecha_str)
        if err_fecha or fecha_obj is None:
            dj_messages.error(request, err_fecha or "Fecha de carga inválida.")
            return _redirect_clasificacion_produccion(request, fecha_str=fecha_str)

        accion_raw = (request.POST.get("accion") or "confirmar").strip().lower()
        accion = "borrador" if accion_raw == "borrador" else "confirmar"

        payload = parsear_post_cc_consolidado(
            request.POST,
            unidades_por_docena=UNIDADES_POR_DOCENA_OPP,
        )
        tiene_cantidad = any(
            (to_decimal_or_none(datos.get("semi")) or Decimal("0")) > 0
            or any(
                (to_decimal_or_none(ln[3]) or Decimal("0")) > 0
                for ln in (datos.get("lineas") or [])
                if len(ln) == 4
            )
            for datos in payload.values()
        )
        if not payload or not tiene_cantidad:
            dj_messages.warning(request, "No se enviaron cantidades.")
            return _redirect_clasificacion_produccion(request, fecha_str=fecha_str)

        if accion == "borrador":
            from mpr.repositories.clasificacion_borrador import upsert_borrador_cc_consolidado

            upsert_borrador_cc_consolidado(
                base_empresa,
                fecha_obj,
                id_usuario,
                _lineas_borrador_desde_payload_cc(payload),
            )
            request.session["clasificacion_feedback_modal"] = {
                "tipo": "success",
                "titulo": "Listo",
                "mensaje": "Borrador de control de calidad guardado.",
            }
            return _redirect_clasificacion_produccion(request, fecha_str=fecha_str)

        resultado = confirmar_cc_consolidado(
            base_empresa, id_usuario, fecha_obj, payload
        )
        ok_ids = resultado.get("ok") or []
        errs = resultado.get("errores") or []
        if ok_ids and not errs:
            request.session["clasificacion_feedback_modal"] = {
                "tipo": "success",
                "titulo": "Listo",
                "mensaje": "Control de calidad guardado correctamente.",
            }
        elif ok_ids and errs:
            detalle = "; ".join(f"Art. {aid}: {msg}" for aid, msg in errs[:3])
            request.session["clasificacion_feedback_modal"] = {
                "tipo": "warning",
                "titulo": "Atención",
                "mensaje": (
                    "Control de calidad parcial: algunas transferencias no se completaron. "
                    + detalle
                ).strip(),
            }
        elif errs:
            detalle = "; ".join(f"Art. {aid}: {msg}" for aid, msg in errs[:3])
            request.session["clasificacion_feedback_modal"] = {
                "tipo": "error",
                "titulo": "Aviso",
                "mensaje": detalle or "No se pudo completar el control de calidad.",
            }
        for id_art_err, msg_err in errs:
            logger.warning("Clasificación artículo %s: %s", id_art_err, msg_err)

        return _redirect_clasificacion_produccion(request, fecha_str=fecha_str)


class ManualUsuarioMprView(MprLoginRequiredMixin, MprTableroVerMixin, View):
    """Sirve el manual de usuario MPR (HTML estático generado desde Markdown)."""

    def get(self, request, *args, **kwargs):
        from pathlib import Path

        manual_path = (
            Path(__file__).resolve().parent
            / "static"
            / "mpr"
            / "manuales"
            / "manual_usuario_mpr.html"
        )
        if not manual_path.is_file():
            raise Http404("Manual de usuario MPR no encontrado.")
        return FileResponse(
            manual_path.open("rb"),
            content_type="text/html; charset=utf-8",
        )
