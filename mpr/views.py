# Módulo MPR - Vistas
import json
import logging
import traceback
from datetime import date, datetime, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from urllib.parse import urlencode
from django.views import View
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)

from core.services.administranet_stock import get_depositos, obtener_renglones_movimiento
from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none

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
    get_articulo_armado_por_bom,
    get_bom_detalle,
    get_cantidades_armadas_por_opt,
    get_cantidad_opp_por_destino_opt,
    componentes_a_equivalentes_pack,
    get_id_en_abm_por_articulo,
    bulk_id_en_abm,
    bulk_bom_detalle,
    get_lineas_armado_opt,
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
    listar_ventana_pack,
    listar_ventana_pack_unidades,
    listar_empleados_operarios,
    listar_unidades_desde_seleccion,
    lineas_opt_desde_formulario_unidades,
    listar_ops_para_cerrar,
    listar_opt_en_proceso,
    estado_acciones_opt,
    listar_opa_por_opt,
    listar_opp_por_opt,
    listar_pedidos_fabrica,
    listar_opts_por_pedido,
    get_depositos_con_suma_stock,
    get_deposito_produccion_mpr,
    get_deposito_semi_elaborado_mpr,
    get_deposito_terminado_mpr,
    get_depositos_opp,
    reactivar_operario,
    reporte_mpr_pendiente,
    reporte_mpr_wip,
    reporte_mpr_stock,
    reporte_mpr_bajo_minimo,
    reporte_mpr_desperdicio,
    reporte_mpr_produccion_por_operario,
    reporte_mpr_opt_cerradas,
    TIPO_MPR_2DA_SELECCION,
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


def _get_base_empresa(request):
    """Obtiene base_empresa desde la sesión. Devuelve None si no hay empresa activa."""
    session_user = request.session.get("user", {})
    return session_user.get("base_empresa") or None


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
    Mapa codigo_movimiento (str) -> renglones para el modal de comprobante en detalle OPT.
    Misma fuente que stock (tabla stock por CodigoMovimiento).
    """
    codigos = set()
    for row in opp_list or []:
        cm = to_int_or_none(row.get("codigo_movimiento"))
        if cm is not None:
            codigos.add(cm)
    for row in opa_list or []:
        cm = to_int_or_none(row.get("codigo_movimiento"))
        if cm is not None:
            codigos.add(cm)
    out = {}
    for cm in codigos:
        renglones = obtener_renglones_movimiento(base_empresa, cm)
        rows = []
        for r in renglones:
            entrada = r.get("Entrada")
            salida = r.get("Salida")
            saldo = r.get("saldo")
            rows.append({
                "codigo_articulo": str_or_default(r.get("CodigoArticulo"), "—"),
                "descripcion": str_or_default(r.get("Descripcion"), "—"),
                "entrada": float(to_decimal_or_none(entrada) or 0),
                "salida": float(to_decimal_or_none(salida) or 0),
                "saldo": float(to_decimal_or_none(saldo) if saldo is not None else 0),
            })
        out[str(cm)] = rows
    return out


class TableroView(MprLoginRequiredMixin, TemplateView):
    """Tablero de control MPR: vista 'control de planta' y entrada rápida a acción."""

    template_name = "mpr/tablero.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        # KPIs y listas desde MySQL si hay empresa; si no, placeholders
        if base_empresa:
            try:
                agrupada = listar_lista_produccion_agrupada(
                    base_empresa, limit=50, excluir_filas_opt_liberadas_mstock=True
                )
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                context["mpr_schema_error_modal"] = str(e)
                context["kpi_pedidos_pendientes"] = 0
                context["kpi_delayed_ops"] = 0
                context["kpi_pending_units"] = 0
                context["kpi_urgent_items"] = 0
                context["ops_to_release"] = []
                context["ops_to_close"] = []
                context["ops_en_proceso"] = []
                context["recent_movements"] = []
                context["top_urgencies"] = []
                return context
            total_pendiente = sum(r["cantidad_pendiente_prod"] for r in agrupada)
            try:
                pedidos_pendientes = listar_pedidos_fabrica(base_empresa, limit=500, estado="Pendiente")
                context["kpi_pedidos_pendientes"] = len(pedidos_pendientes)
            except MprSchemaError:
                context["kpi_pedidos_pendientes"] = 0
            try:
                ventana_pack = listar_ventana_pack(base_empresa, limit=15)
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                context["mpr_schema_error_modal"] = str(e)
                context["kpi_delayed_ops"] = 0
                context["kpi_pending_units"] = total_pendiente
                context["kpi_urgent_items"] = 0
                context["ops_to_release"] = []
                context["ops_to_close"] = []
                context["ops_en_proceso"] = []
                context["recent_movements"] = []
                context["top_urgencies"] = []
                return context
            atrasadas = []
            try:
                atrasadas = listar_opt_listado(base_empresa, limit=500, solo_atrasadas=True)
            except MprSchemaError:
                pass
            kpi_delayed_ops = len(set(r["id_lista_produccion"] for r in atrasadas if r.get("id_lista_produccion")))
            context["kpi_delayed_ops"] = kpi_delayed_ops
            context["kpi_pending_units"] = total_pendiente
            context["kpi_urgent_items"] = min(15, len(ventana_pack) + kpi_delayed_ops)
            top_urgencies = []
            seen_id_lista = set()
            for r in atrasadas:
                id_lista = r.get("id_lista_produccion")
                if id_lista is None or id_lista in seen_id_lista:
                    continue
                seen_id_lista.add(id_lista)
                detail_url = reverse("mpr:opt_detail", kwargs={"id_lista": id_lista})
                top_urgencies.append({
                    "id_articulo": None,
                    "article_id": f"OPT Nº {id_lista}",
                    "description": (r.get("descripcion_articulo") or "-")[:50],
                    "stock": "—",
                    "demand": r.get("cantidad_pendiente_prod") if r.get("cantidad_pendiente_prod") is not None else "—",
                    "status": "Vencida",
                    "status_class": "bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300",
                    "detail_url": detail_url,
                })
                if len(top_urgencies) >= 10:
                    break
            max_demanda = 10 - len(top_urgencies)
            for r in ventana_pack[:max_demanda]:
                id_art = r.get("id_articulo")
                detail_url = (reverse("mpr:ventana_pack") + "?articulo=" + str(id_art)) if id_art else None
                top_urgencies.append({
                    "id_articulo": id_art,
                    "article_id": r.get("codigo_articulo", "-"),
                    "description": (r.get("descripcion_articulo") or "")[:50],
                    "stock": int(r.get("stock_terminado", 0)),
                    "demand": r.get("cantidad_pendiente_prod", 0),
                    "status": "Warning" if (r.get("cantidad_a_fabricar", 0) or 0) > 0 else "Ok",
                    "status_class": "bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300" if (r.get("cantidad_a_fabricar", 0) or 0) > 0 else "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300",
                    "detail_url": detail_url,
                })
            context["top_urgencies"] = top_urgencies
            context["ops_to_release"] = []
            context["ops_to_close"] = []
            try:
                ops_en_proceso_raw = listar_opt_en_proceso(base_empresa, limit=15)
                ops_en_proceso = []
                for op in ops_en_proceso_raw:
                    id_lista = op.get("id_lista_produccion")
                    if not id_lista:
                        continue
                    estado = estado_acciones_opt(base_empresa, id_lista)
                    if estado["puede_cerrar"]:
                        accion_principal = "cerrar"
                    elif estado["puede_crear_opa"]:
                        accion_principal = "crear_opa"
                    elif estado["puede_crear_opp"]:
                        accion_principal = "crear_opp"
                    else:
                        accion_principal = None
                    detail_url = reverse("mpr:opt_detail", kwargs={"id_lista": id_lista})
                    ops_en_proceso.append({
                        "numero": id_lista,
                        "descripcion": op.get("descripcion_articulo") or "-",
                        "unidades": op.get("cantidad_pedida") or 0,
                        "detail_url": detail_url,
                        "crear_opp_url": reverse("mpr:wizard") + f"?paso=3&id_lista={id_lista}",
                        "crear_opa_url": reverse("mpr:armado_opt", kwargs={"id_lista": id_lista}),
                        "cerrar_url": reverse("mpr:opt_cerrar", kwargs={"id_lista": id_lista}),
                        "accion_principal": accion_principal,
                    })
                context["ops_en_proceso"] = ops_en_proceso
                recent_raw = listar_movimientos_recientes_mpr(base_empresa, limit=10)
                for mov in recent_raw:
                    mov["detail_url"] = reverse("mpr:opt_detail", kwargs={"id_lista": mov["id_lista"]}) if mov.get("id_lista") else None
                context["recent_movements"] = recent_raw
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                context["mpr_schema_error_modal"] = str(e)
                context["ops_en_proceso"] = []
                context["ops_to_close"] = []
                context["recent_movements"] = []
        else:
            context["kpi_pedidos_pendientes"] = 0
            context["kpi_delayed_ops"] = 0
            context["kpi_pending_units"] = 0
            context["kpi_urgent_items"] = 0
            context["ops_to_release"] = []
            context["ops_to_close"] = []
            context["ops_en_proceso"] = []
            context["recent_movements"] = []
            context["top_urgencies"] = []
        return context


# Clave de sesión para el wizard de producción
WIZARD_SESSION_KEY = "mpr_wizard"


class WizardProduccionView(MprLoginRequiredMixin, TemplateView):
    """
    Asistente de producción: 1.Crear OPT → 2.Confirmar (crear+liberar) → 3.Crear OPP → 4.Armado → 5.Cierre.
    Depósito de producción (config) se usa al confirmar; no se pide en pantalla.
    """

    template_name = "mpr/wizard.html"

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
        # Paso 1 del wizard = pantalla ventana-pack (demanda por artículo)
        if paso == 1:
            request.session[WIZARD_SESSION_KEY] = {"paso": 1}
            request.session.modified = True
            return redirect("mpr:ventana_pack")
        if paso == 4:
            id_lista = wizard.get("id_lista")
            lineas_armado = get_lineas_armado_opt(base_empresa, id_lista) if id_lista else []
            if not lineas_armado:
                wizard["paso"] = 5
                request.session[WIZARD_SESSION_KEY] = wizard
                request.session.modified = True
                return redirect("mpr:wizard")
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
            return self._post_paso4(request, base_empresa, wizard)
        if paso == 5:
            if request.POST.get("accion") == "cerrar_opt":
                id_lista = wizard.get("id_lista")
                if id_lista:
                    try:
                        ok, error = cerrar_opt(base_empresa, id_lista)
                        if ok:
                            messages.success(request, f"OPT {id_lista} cerrada correctamente.")
                        else:
                            messages.error(request, error or "Error al cerrar la OPT.")
                    except MprSchemaError as e:
                        return _mpr_schema_error_redirect(request, e)
                return redirect("mpr:wizard")
            if request.POST.get("accion") == "finalizar":
                self._limpiar_wizard(request)
                id_lista = wizard.get("id_lista")
                if id_lista:
                    return redirect("mpr:opt_detail", id_lista=id_lista)
                return redirect("mpr:tablero")
            self._limpiar_wizard(request)
            id_lista = wizard.get("id_lista")
            if id_lista:
                return redirect("mpr:opt_detail", id_lista=id_lista)
            return redirect("mpr:tablero")

    def _limpiar_wizard(self, request):
        if WIZARD_SESSION_KEY in request.session:
            del request.session[WIZARD_SESSION_KEY]

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
            componentes_opp = get_opp_componentes_disponibles(base_empresa, id_lista)
        except MprSchemaError as e:
            _log_mpr_schema_error(e)
            request.session["mpr_schema_error_modal"] = str(e)
            return redirect("mpr:wizard")
        if not componentes_opp:
            messages.error(request, "No hay componentes para distribuir en esta OPT.")
            return redirect("mpr:wizard")
        cods_dep = [to_int_or_none(d.get("CodDeposito")) for d in depositos_opp if to_int_or_none(d.get("CodDeposito")) is not None]
        # Leer matriz: opp_comp_<id_componente>_dep_<cod_deposito> (unidades)
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
            disponible = int(comp.get("disponible_unidades") or 0)
            suma_comp = 0
            for cod_dep in cods_dep:
                if cod_dep == deposito_origen:
                    continue
                key = f"opp_comp_{id_comp}_dep_{cod_dep}"
                try:
                    qty = int((request.POST.get(key) or "0").strip())
                except (ValueError, TypeError):
                    qty = 0
                qty = max(0, qty)
                if qty > 0:
                    por_deposito[cod_dep].append((id_comp, qty))
                suma_comp += qty
            if suma_comp > disponible:
                codigo = comp.get("codigo_articulo") or id_comp
                messages.error(request, f"Componente {codigo}: la suma por depósitos ({suma_comp}) no puede superar el disponible ({disponible} unidades).")
                return redirect("mpr:wizard")
            if suma_comp > 0:
                id_operario_raw = (request.POST.get(f"operario_{id_comp}") or "").strip()
                id_operario_comp = to_int_or_none(id_operario_raw)
                if id_operario_comp is None:
                    codigo = comp.get("codigo_articulo") or id_comp
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
        wizard["paso"] = 4
        request.session[WIZARD_SESSION_KEY] = wizard
        request.session.modified = True
        messages.success(request, "Parte de producción (OPP) registrada por depósito.")
        return redirect("mpr:wizard")

    def _post_paso4(self, request, base_empresa, wizard):
        from django.contrib import messages
        from core.utils.administranet_types import to_int_or_none
        if request.POST.get("omitir_armado") == "1":
            wizard["paso"] = 5
            request.session[WIZARD_SESSION_KEY] = wizard
            request.session.modified = True
            return redirect("mpr:wizard")
        session_user = request.session.get("user", {})
        try:
            id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        if not id_usuario:
            messages.error(request, "Usuario no identificado en sesión.")
            return redirect("mpr:wizard")
        id_lista = wizard.get("id_lista")
        if not id_lista:
            messages.error(request, "Falta la OPT. Vuelva al asistente desde la pantalla de demanda.")
            return redirect("mpr:wizard")
        lineas_armado = get_lineas_armado_opt(base_empresa, id_lista)
        if not lineas_armado:
            messages.error(request, "No hay artículos armables para esta OPT.")
            wizard["paso"] = 5
            request.session[WIZARD_SESSION_KEY] = wizard
            request.session.modified = True
            return redirect("mpr:wizard")
        deposito_semi = get_deposito_semi_elaborado_mpr(base_empresa)
        deposito_terminado = get_deposito_terminado_mpr(base_empresa)
        if not deposito_semi or not deposito_terminado:
            messages.error(request, "Configure depósitos Semi Elaborado y Terminado en Config. Depósitos.")
            return redirect("mpr:wizard")
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
                if id_operario_linea is None:
                    messages.error(request, f"Seleccione operario para el pack {linea.get('codigo_articulo') or id_art}.")
                    return redirect("mpr:wizard")
                cantidades.append((linea, qty, id_operario_linea))
        if not cantidades:
            messages.error(request, "Indique al menos una cantidad mayor a 0 en algún pack para ejecutar el armado.")
            return redirect("mpr:wizard")
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
                            codigo_comp = comp.get("codigo_articulo") or cid
                            break
                    if codigo_comp is not None:
                        break
                messages.error(
                    request,
                    f"Stock insuficiente del componente {codigo_comp or cid} en Semi Elaborado: se necesitan {int(necesario)}, hay {int(saldo)}.",
                )
                return redirect("mpr:wizard")
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
                return redirect("mpr:wizard")
        messages.success(request, "Armado registrado por pack.")
        wizard["paso"] = 5
        request.session[WIZARD_SESSION_KEY] = wizard
        request.session.modified = True
        return redirect("mpr:wizard")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        wizard = self.request.session.get(WIZARD_SESSION_KEY) or {}
        paso = wizard.get("paso", 1)
        context["wizard_paso"] = paso
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
                        articulo_nombre = (a.get("codigo_articulo") or "") + " · " + (a.get("descripcion_articulo") or "")[:50]
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
                componentes_opp = get_opp_componentes_disponibles(base_empresa, id_lista) if id_lista else []
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
            context["componentes_opp"] = componentes_opp
            context["depositos_opp"] = depositos_opp
            context["operarios"] = listar_empleados_operarios(base_empresa, busqueda=None, limit=200)
            context["total_pendiente"] = sum(c.get("disponible_unidades") or 0 for c in componentes_opp) if componentes_opp else sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
            try:
                opp_registradas = listar_opp_por_opt(base_empresa, id_lista) if id_lista else []
                context["cantidad_opp_registradas"] = len(opp_registradas)
            except MprSchemaError as e:
                _log_mpr_schema_error(e)
                context["cantidad_opp_registradas"] = 0
            context["id_deposito_produccion"] = get_deposito_produccion_mpr(base_empresa)
        elif paso == 4:
            id_lista = wizard.get("id_lista")
            lineas_armado = get_lineas_armado_opt(base_empresa, id_lista) if id_lista else []
            context["id_lista"] = id_lista
            context["lineas_armado"] = lineas_armado
            context["mostrar_armado"] = bool(lineas_armado)
            context["operarios"] = listar_empleados_operarios(base_empresa, busqueda=None, limit=200)
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
            import json
            data_by_art = {}
            for linea in lineas_armado:
                id_art = linea.get("id_articulo")
                if id_art is not None:
                    comps = []
                    for c in linea.get("bom", {}).get("componentes") or []:
                        comps.append({
                            "codigo_articulo": c.get("codigo_articulo") or "-",
                            "cantidad_articulo": float(c.get("cantidad_articulo") or 0),
                            "saldo_semi_elaborado": float(c.get("saldo_semi_elaborado") or 0),
                        })
                    data_by_art[str(id_art)] = comps
            context["lineas_armado_json"] = json.dumps(data_by_art)
        elif paso == 5:
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


class OpListView(MprLoginRequiredMixin, TemplateView):
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


class OptListView(MprLoginRequiredMixin, TemplateView):
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
        # Enriquecer cada fila: pendiente del pedido y fase (OPTs creadas) o "Demanda" (aún no liberada)
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
            if not es_opt_creada:
                opt["etiqueta_fase"] = "Demanda"
                opt["fase_clave"] = "demanda"
            elif not en_proceso:
                # Cerrada = esta OPT no tiene más pendiente de producir (cantidad_pendiente_prod),
                # no el "pend. del pedido" (cantidad_pendiente_mostrar) que puede ser > 0 para otras OPT.
                if int(cantidad_pendiente_prod or 0) == 0:
                    opt["etiqueta_fase"] = "Cerrada"
                    opt["fase_clave"] = "cerrada"
                else:
                    opt["etiqueta_fase"] = "Pendiente"
                    opt["fase_clave"] = "pendiente"
            elif id_lista is None:
                opt["etiqueta_fase"] = "Pendiente"
                opt["fase_clave"] = "pendiente"
            else:
                estado = estado_acciones_opt(base_empresa, id_lista)
                if estado.get("puede_cerrar"):
                    opt["etiqueta_fase"] = "Lista para cerrar"
                    opt["fase_clave"] = "lista_cerrar"
                elif estado.get("puede_crear_opa"):
                    opt["etiqueta_fase"] = "Lista para armado (OPA)"
                    opt["fase_clave"] = "lista_opa"
                elif estado.get("puede_crear_opp"):
                    opt["etiqueta_fase"] = "En producción (OPP pendiente)"
                    opt["fase_clave"] = "en_produccion_opp"
                else:
                    opt["etiqueta_fase"] = "En producción"
                    opt["fase_clave"] = "en_produccion"
        context["base_empresa"] = base_empresa
        context["ordenes"] = ordenes
        context["filtro_estado"] = estado_filter
        return context


class OptDetailView(MprLoginRequiredMixin, TemplateView):
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
        # Estado del flujo: Pedida → En producción → Producida (OPP) → Pendiente 0 → Armado → Cerrado
        en_proceso = (lineas[0].get("en_proceso_produccion") or "No").strip().lower() == "si"
        paso_pedida = True
        paso_cerrado = not en_proceso
        # Si la OPT está cerrada, mostrar todos los pasos como cumplidos (persistencia del estado al cierre)
        if paso_cerrado:
            paso_liberada_opt = True
            paso_producida_opp = True
            paso_pendiente_cero = True
            paso_armado = True
        else:
            paso_liberada_opt = en_proceso or (total_pendiente == 0)
            paso_producida_opp = total_pendiente == 0
            paso_pendiente_cero = total_pendiente == 0
            paso_armado = None  # se calcula más abajo

        # Cantidades ya armadas por artículo (solo si OPT con id_lista)
        cantidades_armadas = {}
        opp_semi_por_articulo = {}
        opp_otros_por_articulo = {}
        if id_lista and id_lista != 0:
            cantidades_armadas = get_cantidades_armadas_por_opt(base_empresa, id_lista)
            opp_semi_por_articulo, opp_otros_por_articulo, opp_desperdicio_por_articulo = get_cantidad_opp_por_destino_opt(base_empresa, id_lista)

        all_art_ids = [l.get("id_articulo") for l in lineas if l.get("id_articulo")]
        abm_map = bulk_id_en_abm(base_empresa, all_art_ids) if all_art_ids else {}
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
            cantidad_disponible_armar = componentes_a_equivalentes_pack(base_empresa, id_art, opp_semi_por_articulo) if id_art else 0
            cantidad_a_otros_dep = componentes_a_equivalentes_pack(base_empresa, id_art, opp_otros_por_articulo) if id_art else 0
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
        total_a_desperdicio_otro = componentes_a_equivalentes_pack(base_empresa, primer_pack_id, opp_otros_por_articulo) if primer_pack_id else 0
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
        if lineas_with_armado and id_lista:
            armado_opt_url = reverse("mpr:armado_opt", kwargs={"id_lista": id_lista})
            for item in lineas_with_armado:
                item["armado_url"] = armado_opt_url
        if not paso_cerrado:
            # Armado no puede figurar cumplido antes que OPP pendiente = 0 (evita marcar True si no hay
            # líneas en ABM/conjunto: antes `not lineas_with_armado` activaba el paso con OPP aún pendiente).
            if not paso_pendiente_cero:
                paso_armado = False
            elif not lineas_with_armado:
                # Pendiente OPP 0 y sin artículos armables (sin BOM/conjunto en ABM): paso N/A → cumplido
                paso_armado = True
            else:
                # Todo lo disponible en Semi elaborado ya armado (no se exige lo enviado a otros depósitos)
                paso_armado = all(
                    item["cantidad_ya_armada"] >= item.get("cantidad_disponible_armar", 0)
                    for item in lineas_with_armado
                )
        # si paso_cerrado, paso_armado ya quedó True arriba

        # Porcentaje según 6 pasos: Pedida, En producción, Producida (OPP), Pendiente 0, Armado, Cerrado
        # OPT cerrada: 100 % (todos los pasos cumplidos de forma persistente)
        if paso_cerrado:
            porcentaje_estado = 100
        else:
            num_pasos = sum([
                paso_pedida,
                paso_liberada_opt,
                paso_producida_opp,
                paso_pendiente_cero,
                paso_armado,
                paso_cerrado,
            ])
            porcentaje_estado = min(100, round(100 * num_pasos / 6)) if num_pasos else 0

        if paso_cerrado:
            estado_actual_texto = "OPT cerrada."
        elif total_pendiente == 0 and en_proceso:
            estado_actual_texto = "Completada (pendiente OPP 0). Puede cerrar la OPT."
        elif total_pendiente == 0:
            estado_actual_texto = "Producida (OPP). Pendiente OPP: 0 Packs."
        elif en_proceso:
            estado_actual_texto = "En producción. Pendiente OPP (por producir en esta OPT): {} Packs.".format(total_pendiente)
        else:
            estado_actual_texto = "En producción. Pendiente OPP: {} Packs.".format(total_pendiente)

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
        context["total_en_esta_opt"] = total_en_esta_opt
        context["pendiente_del_pedido"] = pendiente_del_pedido
        context["porcentaje_completado"] = porcentaje_estado
        context["estado_actual_texto"] = estado_actual_texto
        context["paso_pedida"] = paso_pedida
        context["paso_liberada_opt"] = paso_liberada_opt
        context["paso_producida_opp"] = paso_producida_opp
        context["paso_pendiente_cero"] = paso_pendiente_cero
        context["paso_armado"] = paso_armado
        context["paso_cerrado"] = paso_cerrado
        context["en_proceso"] = en_proceso
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
        return context


class RegistrarOppView(MprLoginRequiredMixin, TemplateView):
    """Pantalla Registrar OPP: matriz artículo x depósito (Semi Elaborado, Scrap, 2da Selección)."""

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
            componentes_opp = get_opp_componentes_disponibles(base_empresa, id_lista)
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
            context["componentes_opp"] = componentes_opp
            context["depositos_opp"] = depositos_opp
            context["total_pendiente"] = sum(c.get("disponible_unidades") or 0 for c in componentes_opp) if componentes_opp else sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
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
            componentes_opp = get_opp_componentes_disponibles(base_empresa, id_lista)
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
                key = f"opp_comp_{id_comp}_dep_{cod_dep}"
                try:
                    qty = int((request.POST.get(key) or "0").strip())
                except (ValueError, TypeError):
                    qty = 0
                qty = max(0, qty)
                if qty > 0:
                    por_deposito[cod_dep].append((id_comp, qty))
        id_operario_por_componente = {}
        for id_comp, comp in comp_por_id.items():
            if id_comp is None:
                continue
            disponible = int(comp.get("disponible_unidades") or 0)
            suma_comp = sum(
                q for cod_dep in por_deposito
                for (cid, q) in por_deposito[cod_dep]
                if cid == id_comp
            )
            if suma_comp > disponible:
                codigo = comp.get("codigo_articulo") or id_comp
                messages.error(request, f"Componente {codigo}: la suma por depósitos ({suma_comp}) no puede superar el disponible ({disponible} unidades).")
                return redirect("mpr:registrar_opp", id_lista=id_lista)
            if suma_comp > 0:
                id_operario_raw = (request.POST.get(f"operario_{id_comp}") or "").strip()
                id_operario_comp = to_int_or_none(id_operario_raw)
                if id_operario_comp is None:
                    codigo = comp.get("codigo_articulo") or id_comp
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


class ArmadoOptView(MprLoginRequiredMixin, TemplateView):
    """Armado multi-artículo desde detalle OPT: tabla por pack, depósitos fijos Semi Elaborado → Terminado."""

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
        import json
        data_by_art = {}
        for linea in lineas_armado:
            id_art = linea.get("id_articulo")
            if id_art is not None:
                comps = []
                for c in linea.get("bom", {}).get("componentes") or []:
                    comps.append({
                        "codigo_articulo": c.get("codigo_articulo") or "-",
                        "cantidad_articulo": float(c.get("cantidad_articulo") or 0),
                        "saldo_semi_elaborado": float(c.get("saldo_semi_elaborado") or 0),
                    })
                    data_by_art[str(id_art)] = comps
        context["lineas_armado_json"] = json.dumps(data_by_art)
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
                if id_operario_linea is None:
                    messages.error(
                        request,
                        f"Seleccione operario para el pack {linea.get('codigo_articulo') or id_art}.",
                    )
                    return redirect("mpr:armado_opt", id_lista=id_lista)
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
                            codigo_comp = comp.get("codigo_articulo") or cid
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


class CerrarOptView(MprLoginRequiredMixin, TemplateView):
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
        else:
            messages.error(request, error or "Error al cerrar la OPT.")
        referer = request.META.get("HTTP_REFERER") or ""
        if "mpr/tablero" in referer or referer.endswith("/mpr/"):
            return redirect("mpr:tablero")
        return redirect("mpr:opt_detail", id_lista=id_lista)


def _opt_comprobante_pdf(request, id_lista):
    """Genera PDF con detalle completo de la OPT: liberación OPT, OPPs y OPAs. Uso interno desde opt_comprobante_pdf_view."""
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    from core.report_pdf import draw_report_footer, draw_report_header, get_empresa_para_reporte
    from core.services.administranet_stock import (
        get_nombre_deposito,
        obtener_movimiento,
        obtener_renglones_movimiento,
    )

    base_empresa = _get_base_empresa(request)
    if not base_empresa:
        return None

    codigo_opt = get_codigo_movimiento_opt(base_empresa, id_lista)
    opp_list = listar_opp_por_opt(base_empresa, id_lista)
    opa_list = listar_opa_por_opt(base_empresa, id_lista)

    # Bloques a imprimir: (título sección, subtítulo contexto, codigo_movimiento)
    bloques = []
    if codigo_opt:
        bloques.append(("1. Liberación OPT", "Movimiento a producción", codigo_opt))
    for i, opp in enumerate(opp_list or [], 1):
        bloques.append((f"2.{i}. OPP – Parte de producción", f"Comprobante {opp.get('nro_comprobante', '-')}", opp["codigo_movimiento"]))
    for i, opa in enumerate(opa_list or [], 1):
        bloques.append((f"3.{i}. OPA – Armado", f"Comprobante {opa.get('nro_comprobante', '-')}", opa["codigo_movimiento"]))

    if not bloques:
        return None

    todos_cod_mov = [cod for _, __, cod in bloques]
    mov_cache = {}
    renglones_cache = {}
    dep_ids_set = set()
    for cod_mov in todos_cod_mov:
        mov_cache[cod_mov] = obtener_movimiento(base_empresa, cod_mov)
        renglones_cache[cod_mov] = obtener_renglones_movimiento(base_empresa, cod_mov)
        m = mov_cache[cod_mov]
        if m:
            if m.get("deposito_origen"):
                dep_ids_set.add(m["deposito_origen"])
            if m.get("deposito_destino"):
                dep_ids_set.add(m["deposito_destino"])
    dep_nombres = {}
    if dep_ids_set:
        from core.services.administranet_stock import get_nombres_depositos
        dep_nombres = get_nombres_depositos(base_empresa, list(dep_ids_set))

    empresa = get_empresa_para_reporte(base_empresa)
    margin = 20 * mm
    col_articulo = 168 * mm
    col_entrada = 28 * mm
    col_salida = 28 * mm
    col_saldo = 28 * mm
    ancho_tabla = col_articulo + col_entrada + col_salida + col_saldo
    x_fin_tabla = margin + ancho_tabla
    fila_altura = 5 * mm
    cabecera_altura = 6 * mm
    y_min = 45 * mm

    import io
    buf = io.BytesIO()
    p = canvas.Canvas(buf, pagesize=landscape(A4))
    primera_pagina = True
    y_content = 210 * mm

    for titulo_seccion, subtitulo_seccion, cod_mov in bloques:
        mov = mov_cache.get(cod_mov)
        if not mov:
            continue
        renglones = renglones_cache.get(cod_mov, []) or []
        nombre_dep_origen = dep_nombres.get(mov.get("deposito_origen"), "-")
        nombre_dep_destino = dep_nombres.get(mov.get("deposito_destino"), "-")

        if primera_pagina:
            y_content = draw_report_header(
                p, empresa, f"Comprobante completo OPT {id_lista}", 210 * mm
            )
            primera_pagina = False
        else:
            if y_content < y_min:
                draw_report_footer(p)
                p.showPage()
                y_content = 210 * mm - 25 * mm
            # Separador visual entre secciones
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
            p.drawString(margin, y_content, "Detalle de movimientos (Artículo, Entrada, Salida, Saldo):")
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
            p.drawString(margin + col_articulo + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Entrada")
            p.drawString(margin + col_articulo + col_entrada + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Salida")
            p.drawString(margin + col_articulo + col_entrada + col_salida + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Saldo")
            p.line(margin, y_content + cabecera_altura, margin, y_content)
            p.line(margin + col_articulo, y_content + cabecera_altura, margin + col_articulo, y_content)
            p.line(margin + col_articulo + col_entrada, y_content + cabecera_altura, margin + col_articulo + col_entrada, y_content)
            p.line(margin + col_articulo + col_entrada + col_salida, y_content + cabecera_altura, margin + col_articulo + col_entrada + col_salida, y_content)
            p.line(x_fin_tabla, y_content + cabecera_altura, x_fin_tabla, y_content)
            y_content -= fila_altura

            p.setFont("Helvetica", 10)
            for r in renglones[:25]:
                if y_content < y_min:
                    draw_report_footer(p)
                    p.showPage()
                    y_content = 210 * mm - 25 * mm
                    p.setFont("Helvetica", 10)
                p.line(margin, y_content + fila_altura, x_fin_tabla, y_content + fila_altura)
                art_desc = f"{r.get('CodigoArticulo') or ''} {str(r.get('Descripcion') or '')[:70]}".strip()
                if len(art_desc) > 73:
                    art_desc = art_desc[:70] + "..."
                p.drawString(margin + 2 * mm, y_content + (fila_altura - 3.5 * mm), art_desc)
                p.drawString(margin + col_articulo + 2 * mm, y_content + (fila_altura - 3.5 * mm), str(r.get("Entrada") or "0"))
                p.drawString(margin + col_articulo + col_entrada + 2 * mm, y_content + (fila_altura - 3.5 * mm), str(r.get("Salida") or "0"))
                saldo_val = r.get("saldo", r.get("Saldo"))
                saldo_str = str(saldo_val) if saldo_val is not None else "-"
                p.drawString(margin + col_articulo + col_entrada + col_salida + 2 * mm, y_content + (fila_altura - 3.5 * mm), saldo_str)
                p.line(margin, y_content + fila_altura, margin, y_content)
                p.line(margin + col_articulo, y_content + fila_altura, margin + col_articulo, y_content)
                p.line(margin + col_articulo + col_entrada, y_content + fila_altura, margin + col_articulo + col_entrada, y_content)
                p.line(margin + col_articulo + col_entrada + col_salida, y_content + fila_altura, margin + col_articulo + col_entrada + col_salida, y_content)
                p.line(x_fin_tabla, y_content + fila_altura, x_fin_tabla, y_content)
                y_content -= fila_altura

            p.line(margin, y_content, x_fin_tabla, y_content)
            if len(renglones) > 25:
                y_content -= 4 * mm
                p.setFont("Helvetica", 9)
                p.drawString(margin, y_content, f"... y {len(renglones) - 25} renglones más.")
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


class NuevaOptView(MprLoginRequiredMixin, TemplateView):
    """Redirige al asistente de producción. La creación manual de OPT ya no está disponible en MPR."""

    def get(self, request, *args, **kwargs):
        return redirect("mpr:wizard")

    def post(self, request, *args, **kwargs):
        return redirect("mpr:wizard")


class BomListView(MprLoginRequiredMixin, TemplateView):
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


class BomDetailView(MprLoginRequiredMixin, TemplateView):
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


class BomCreateView(MprLoginRequiredMixin, TemplateView):
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


class BomEditView(MprLoginRequiredMixin, TemplateView):
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


class PedidosFabricaListView(MprLoginRequiredMixin, TemplateView):
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


class OptsPorPedidoView(MprLoginRequiredMixin, TemplateView):
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
    (TIPO_MPR_SEMI_ELABORADO, "Semi Elaborado"),
    (TIPO_MPR_TERMINADO, "Terminado"),
    (TIPO_MPR_SCRAP, "Scrap"),
    (TIPO_MPR_2DA_SELECCION, "2da Selección"),
]


class ConfigDepositosView(MprLoginRequiredMixin, TemplateView):
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
        for d in depositos:
            tipo_actual = d.get("tipo_mpr")
            # Opciones: vacío + tipos no usados por otros + tipo actual de este depósito
            opciones = [("", "— Sin tipo —")]
            for val, label in TIPOS_MPR_CON_ETIQUETA[1:]:
                if val == tipo_actual or val not in tipos_usados:
                    opciones.append((val, label))
            d["opciones_tipo"] = opciones
        context["depositos"] = depositos
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
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


class OperariosListView(MprLoginRequiredMixin, TemplateView):
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


class OperarioCreateView(MprLoginRequiredMixin, TemplateView):
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


class OperarioUpdateView(MprLoginRequiredMixin, TemplateView):
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


class OperarioAnularView(MprLoginRequiredMixin, View):
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


class OperarioReactivarView(MprLoginRequiredMixin, View):
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


class ArmadoView(MprLoginRequiredMixin, TemplateView):
    """Armado solo por OPT: salida componentes desde depósito origen, entrada producto armado en depósito destino. Requiere id_lista (OPT con pendiente 0)."""

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
        lineas_armado = []
        for l in lineas:
            id_art = l.get("id_articulo")
            id_en_abm = abm_map_liberar.get(id_art)
            if not id_en_abm:
                continue
            cantidad_ya_armada = cantidades_armadas.get(id_art, 0)
            cantidad_disponible_armar = componentes_a_equivalentes_pack(base_empresa, id_art, opp_semi)
            cantidad_restante_armar = max(0, cantidad_disponible_armar - cantidad_ya_armada)
            producto_label = f"{l.get('codigo_articulo') or '-'} — {l.get('descripcion_articulo') or '-'}"
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
        ejecutados = 0
        primer_error = None
        for l in lineas:
            id_art = l.get("id_articulo")
            id_en_abm = abm_map_post.get(id_art)
            if not id_en_abm:
                continue
            cantidad_ya_armada = cantidades_armadas.get(id_art, 0)
            cantidad_disponible_armar = componentes_a_equivalentes_pack(base_empresa, id_art, opp_semi)
            cantidad_restante_armar = max(0, cantidad_disponible_armar - cantidad_ya_armada)
            if cantidad_restante_armar <= 0:
                continue
            id_operario_linea = to_int_or_none(request.POST.get(f"operario_armado_{id_art}"))
            if id_operario_linea is None:
                messages.error(request, f"Seleccione operario para el pack {l.get('codigo_articulo') or id_art}.")
                return redirect(f"{reverse('mpr:armado')}?id_lista={id_lista}")
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


class ReclasificacionView(MprLoginRequiredMixin, TemplateView):
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


class ReportesMPRView(MprLoginRequiredMixin, TemplateView):
    """Reportes MPR: pendiente, WIP, stock por depósito, bajo mínimo."""

    template_name = "mpr/reportes.html"

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
        tipo = (self.request.GET.get("tipo") or "pendiente").strip().lower()
        tipos_validos = ("pendiente", "wip", "stock", "bajo_minimo", "desperdicio", "produccion_operario", "opt_cerradas")
        if tipo not in tipos_validos:
            tipo = "pendiente"
        context["base_empresa"] = base_empresa
        context["tipo_reporte"] = tipo
        fecha_desde = (self.request.GET.get("fecha_desde") or "").strip() or None
        fecha_hasta = (self.request.GET.get("fecha_hasta") or "").strip() or None
        if tipo == "pendiente":
            context["filas"] = reporte_mpr_pendiente(base_empresa, limit=200)
            context["titulo_reporte"] = "Pendiente por artículo / pedido"
        elif tipo == "wip":
            context["filas"] = reporte_mpr_wip(base_empresa, limit=200)
            context["titulo_reporte"] = "En progreso (WIP)"
        elif tipo == "stock":
            context["filas"] = reporte_mpr_stock(base_empresa, limit=500)
            context["titulo_reporte"] = "Stock por tipo / depósito"
        elif tipo == "bajo_minimo":
            context["filas"] = reporte_mpr_bajo_minimo(base_empresa, limit=200)
            context["titulo_reporte"] = "Bajo mínimo"
        elif tipo == "desperdicio":
            context["filas"] = reporte_mpr_desperdicio(base_empresa, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, limit=200)
            context["titulo_reporte"] = "Desperdicio / Scrap"
        elif tipo == "produccion_operario":
            context["filas"] = reporte_mpr_produccion_por_operario(base_empresa, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, limit=200)
            context["titulo_reporte"] = "Producción por operario"
        else:  # opt_cerradas
            context["filas"] = reporte_mpr_opt_cerradas(base_empresa, fecha_desde=fecha_desde, fecha_hasta=fecha_hasta, limit=200)
            context["titulo_reporte"] = "OPT cerradas"
        return context


class VentanaPackActualizarView(MprLoginRequiredMixin, TemplateView):
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


class EmpleadosOperariosAPIView(MprLoginRequiredMixin, View):
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


class VentanaPackAgruparView(MprLoginRequiredMixin, TemplateView):
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
                    primer_art = lineas_detalle[0].get("id_articulo") if lineas_detalle else None
                    total_liberar = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas_detalle)
                    request.session[WIZARD_SESSION_KEY] = {
                        "paso": 3,
                        "id_lista": id_lista_principal,
                        "id_articulo": primer_art,
                        "cantidad_pedida": total_liberar,
                    }
                    request.session.modified = True
                    messages.success(request, f"OPT Nº {id_lista_principal} creada y liberada. Comprobante {nro_comp_liberada}. Siguiente: Crear OPP.")
                    url_wizard = reverse("mpr:wizard")
                    return redirect(f"{url_wizard}?paso=3&id_lista={id_lista_principal}")
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
            qty_str = request.POST.get("cant_" + str(id_art), "0").strip()
            try:
                qty = int(qty_str) if qty_str else 0
            except ValueError:
                qty = 0
            if qty > 0:
                filas_sesion.append({
                    "id_articulo": id_art,
                    "codigo_articulo": f.get("codigo_articulo", "-"),
                    "codigo_manual": f.get("codigo_manual", "-"),
                    "descripcion_articulo": f.get("descripcion_articulo", "-"),
                    "stock_terminado": f.get("stock_terminado", 0),
                    "cantidad_urgente": f.get("cantidad_urgente", 0),
                    "cantidad_a_fabricar": qty,
                    "cantidad_promedio_bulto": f.get("cantidad_promedio_bulto", 0),
                })
        if not filas_sesion:
            messages.error(request, "Seleccione al menos un artículo con cantidad a fabricar mayor a 0.")
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
        detalle_map = bulk_detalle_pedidos_por_articulos(base_empresa, art_ids_pack, limit_por_articulo=30) if art_ids_pack else {}
        for f in filas:
            detalle = detalle_map.get(f.get("id_articulo"), [])
            f["detalle_pedidos"] = detalle
            f["detalle_pedidos_json"] = json.dumps(detalle)
        wizard = self.request.session.get(WIZARD_SESSION_KEY) or {}
        filas_unidades = listar_unidades_desde_seleccion(base_empresa, filas, limit=200)
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
        context["fecha_hoy"] = date.today()
        if base_empresa:
            context["opcional_op"] = listar_columnas_opcionales_nueva_op(base_empresa)
        else:
            context["opcional_op"] = {"has_fecha_objetivo": False, "has_deposito_produccion": False, "has_prioridad": False}
        context["mpr_aviso_sin_deposito_semi_bom"] = (
            bool(base_empresa) and get_deposito_semi_elaborado_mpr(base_empresa) is None
        )
        return context


class VentanaPackView(MprLoginRequiredMixin, TemplateView):
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
        return context
