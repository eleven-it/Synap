# Módulo MPR - Vistas
import logging
import traceback
from datetime import date, timedelta

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)

from core.services.administranet_stock import get_depositos
from core.utils.administranet_types import to_int_or_none

from .services import (
    actualizar_componente_bom,
    actualizar_conjunto_bom,
    actualizar_pedidos_produccion,
    actualizar_deposito_suma_stock,
    anular_componente_bom,
    crear_componente_bom,
    crear_conjunto_bom,
    ejecutar_armado,
    ejecutar_liberar_opt,
    ejecutar_opp,
    ejecutar_reclasificacion,
    get_articulo_armado_por_bom,
    get_bom_detalle,
    get_cantidades_armadas_por_opt,
    get_id_en_abm_por_articulo,
    set_articulo_armado_bom,
    crear_op_agrupada,
    crear_opt_multiples_articulos,
    listar_columnas_opcionales_nueva_op,
    cerrar_opt,
    get_op_detalle,
    get_opt_detalle,
    get_op_detalle_by_articulo,
    listar_articulos_para_op,
    listar_bom_conjuntos,
    listar_depositos_config,
    listar_detalle_pedidos_por_articulo,
    listar_lista_produccion_agrupada,
    listar_movimientos_recientes_mpr,
    listar_ventana_pack,
    listar_ventana_pack_unidades,
    listar_unidades_desde_seleccion,
    listar_ops_para_cerrar,
    listar_pedidos_fabrica,
    get_depositos_con_suma_stock,
    get_deposito_produccion_mpr,
    set_deposito_produccion_mpr,
    reporte_mpr_pendiente,
    reporte_mpr_wip,
    reporte_mpr_stock,
    reporte_mpr_bajo_minimo,
)


class MprLoginRequiredMixin(LoginRequiredMixin):
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


class TableroView(MprLoginRequiredMixin, TemplateView):
    """Tablero de control MPR: vista 'control de planta' y entrada rápida a acción."""

    template_name = "mpr/tablero.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        # KPIs y listas desde MySQL si hay empresa; si no, placeholders
        if base_empresa:
            agrupada = listar_lista_produccion_agrupada(base_empresa, limit=50)
            total_pendiente = sum(r["cantidad_pendiente_prod"] for r in agrupada)
            ventana_pack = listar_ventana_pack(base_empresa, limit=15)
            context["kpi_op_in_progress"] = len(agrupada)
            context["kpi_delayed_ops"] = 0
            context["kpi_pending_units"] = total_pendiente
            context["kpi_urgent_items"] = min(15, len(ventana_pack))
            context["top_urgencies"] = []
            for r in ventana_pack[:10]:
                id_art = r.get("id_articulo")
                opt_list_url = (reverse("mpr:opt_list") + "?articulo=" + str(id_art)) if id_art else None
                context["top_urgencies"].append({
                    "id_articulo": id_art,
                    "article_id": r.get("codigo_articulo", "-"),
                    "description": (r.get("descripcion_articulo") or "")[:50],
                    "stock": int(r.get("stock_terminado", 0)),
                    "demand": r.get("cantidad_pendiente_prod", 0),
                    "status": "Warning" if (r.get("cantidad_a_fabricar", 0) or 0) > 0 else "Ok",
                    "status_class": "bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300" if (r.get("cantidad_a_fabricar", 0) or 0) > 0 else "bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300",
                    "detail_url": opt_list_url,
                })
            ops_release = []
            for r in agrupada[:5]:
                id_lista = r.get("id_lista_produccion")
                id_art = r.get("id_articulo")
                if id_lista:
                    detail_url = reverse("mpr:opt_detail", kwargs={"id_lista": id_lista})
                else:
                    detail_url = reverse("mpr:opt_detail", kwargs={"id_lista": 0}) + f"?articulo={id_art}"
                ops_release.append({
                    "numero": id_lista or id_art,
                    "cliente_resumen": (r.get("descripcion_articulo") or "")[:40] or "-",
                    "unidades": r["cantidad_pendiente_prod"],
                    "detail_url": detail_url,
                })
            context["ops_to_release"] = ops_release
            ops_close_raw = listar_ops_para_cerrar(base_empresa, limit=10)
            context["ops_to_close"] = [
                {
                    "numero": op["id_lista_produccion"],
                    "detail_url": reverse("mpr:opt_detail", kwargs={"id_lista": op["id_lista_produccion"]}),
                    "cerrar_url": reverse("mpr:opt_cerrar", kwargs={"id_lista": op["id_lista_produccion"]}),
                    "descripcion": (op.get("descripcion_articulo") or "")[:40] or "-",
                }
                for op in ops_close_raw
            ]
            recent_raw = listar_movimientos_recientes_mpr(base_empresa, limit=10)
            for mov in recent_raw:
                    mov["detail_url"] = reverse("mpr:opt_detail", kwargs={"id_lista": mov["id_lista"]}) if mov.get("id_lista") else None
            context["recent_movements"] = recent_raw
        else:
            context["kpi_op_in_progress"] = 0
            context["kpi_delayed_ops"] = 0
            context["kpi_pending_units"] = 0
            context["kpi_urgent_items"] = 0
            context["ops_to_release"] = []
            context["ops_to_close"] = []
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
        paso = wizard.get("paso", 1)
        # Paso 1 del wizard = pantalla ventana-pack (demanda por artículo)
        if paso == 1:
            request.session[WIZARD_SESSION_KEY] = {"paso": 1}
            request.session.modified = True
            return redirect("mpr:ventana_pack")
        if paso == 4:
            id_articulo = wizard.get("id_articulo")
            id_en_abm = get_id_en_abm_por_articulo(base_empresa, id_articulo) if id_articulo else None
            if not id_en_abm or not get_articulo_armado_por_bom(base_empresa, id_en_abm):
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
            messages.info(request, "Use la pantalla de demanda (Pedido producción trabajo) para crear la OPT.")
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
                    ok, error = cerrar_opt(base_empresa, id_lista)
                    if ok:
                        messages.success(request, f"OPT {id_lista} cerrada correctamente.")
                    else:
                        messages.error(request, error or "Error al cerrar la OPT.")
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
                "Configure el depósito de producción en Config. Depósitos (Producción → Config. Depósitos) para poder confirmar la orden.",
            )
            return redirect("mpr:wizard")
        id_dep = wizard.get("id_deposito_produccion_opcional")
        prioridad = wizard.get("prioridad")
        fecha_raw = wizard.get("fecha_objetivo")
        fecha_objetivo = None
        if fecha_raw:
            try:
                fecha_objetivo = datetime.strptime(fecha_raw, "%Y-%m-%d").date()
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
        ok_opt, codigo_mov, nro_comprobante, error_opt = ejecutar_liberar_opt(
            base_empresa, id_usuario, id_lista, lineas, cantidad_total, deposito_produccion,
        )
        if not ok_opt:
            msg = error_opt or "Error al liberar a producción."
            if msg and ("bytes" in msg.lower() or "formatting" in msg.lower() or "convert" in msg.lower()):
                msg = "Error al confirmar. Verifique la OPT y el depósito de producción en Config. Depósitos."
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
        """Paso 3: Crear OPP. Cantidades por depósito destino (origen = depósito producción)."""
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
            messages.error(request, "Depósito de producción no configurado. Configure en Config. Depósitos.")
            return redirect("mpr:wizard")
        depositos = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(request))
        # Solo aceptar depósitos destino con Suma stock = Sí (igual que en el formulario OPP)
        depositos_opp = [d for d in depositos if (d.get("suma_stock") or "Si").strip().lower() in ("si", "sí")]
        destinos_cantidad = []
        for dep in depositos_opp:
            cod_dep = to_int_or_none(dep.get("CodDeposito"))
            if cod_dep is None or cod_dep == deposito_origen:
                continue
            key = "cantidad_dep_{}".format(cod_dep)
            raw = request.POST.get(key, "").strip()
            try:
                qty = int(raw) if raw else 0
            except ValueError:
                qty = 0
            if qty > 0:
                destinos_cantidad.append((cod_dep, qty))
        if not destinos_cantidad:
            messages.error(request, "Indique al menos un depósito destino con cantidad mayor a 0.")
            return redirect("mpr:wizard")
        lineas = get_opt_detalle(base_empresa, id_lista)
        if not lineas:
            messages.error(request, "No se encontraron líneas para esta OPT.")
            return redirect("mpr:wizard")
        total_pendiente = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
        suma_destinos = sum(q for _, q in destinos_cantidad)
        if suma_destinos > total_pendiente:
            messages.error(request, f"La suma de cantidades ({suma_destinos}) no puede superar el pendiente ({total_pendiente}).")
            return redirect("mpr:wizard")
        if suma_destinos < total_pendiente:
            messages.error(request, f"Quedan {total_pendiente - suma_destinos} unidades sin registrar. Debe distribuir todo el pendiente ({total_pendiente}) para continuar.")
            return redirect("mpr:wizard")
        logger.info(
            "MPR OPP wizard paso 3: base_empresa=%s id_lista=%s id_usuario=%s deposito_origen=%s destinos_cantidad=%s total_pendiente=%s",
            base_empresa, id_lista, id_usuario, deposito_origen, destinos_cantidad, total_pendiente,
        )
        for deposito_destino, cantidad in destinos_cantidad:
            lineas_actual = get_opt_detalle(base_empresa, id_lista)
            if not lineas_actual:
                logger.warning("MPR OPP wizard: sin lineas_actual para id_lista=%s", id_lista)
                break
            try:
                ok, codigo_mov, nro_comp, error = ejecutar_opp(
                    base_empresa, id_usuario, id_lista, lineas_actual,
                    cantidad, deposito_origen, deposito_destino,
                )
            except Exception as e:
                logger.exception(
                    "MPR OPP wizard: excepción en ejecutar_opp base_empresa=%s id_lista=%s deposito_destino=%s cantidad=%s: %s",
                    base_empresa, id_lista, deposito_destino, cantidad, e,
                )
                logger.debug(
                    "MPR OPP wizard: traceback completo:\n%s",
                    traceback.format_exc(),
                )
                messages.error(request, str(e))
                return redirect("mpr:wizard")
            if not ok:
                logger.warning(
                    "MPR OPP wizard: ejecutar_opp devolvió error base_empresa=%s id_lista=%s deposito_destino=%s: %s",
                    base_empresa, id_lista, deposito_destino, error,
                )
                messages.error(request, error or "Error al registrar OPP para un depósito.")
                return redirect("mpr:wizard")
        wizard["paso"] = 4
        request.session[WIZARD_SESSION_KEY] = wizard
        request.session.modified = True
        messages.success(request, "Parte de producción (OPP) registrada por depósito.")
        return redirect("mpr:wizard")

    def _post_paso4(self, request, base_empresa, wizard):
        from django.contrib import messages
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
        try:
            id_en_abm = int((request.POST.get("id_en_abm") or "").strip())
        except (TypeError, ValueError):
            id_en_abm = None
        try:
            cantidad_a_armar = int((request.POST.get("cantidad_a_armar") or "").strip())
        except (TypeError, ValueError):
            cantidad_a_armar = 0
        try:
            deposito_origen = int((request.POST.get("deposito_origen") or "").strip())
        except (TypeError, ValueError):
            deposito_origen = None
        try:
            deposito_destino = int((request.POST.get("deposito_destino") or "").strip())
        except (TypeError, ValueError):
            deposito_destino = None
        if not id_en_abm or cantidad_a_armar <= 0 or not deposito_origen or not deposito_destino:
            messages.error(request, "Complete conjunto, cantidad y ambos depósitos para ejecutar el armado.")
            return redirect("mpr:wizard")
        ok, codigo_mov, nro_comp, error = ejecutar_armado(
            base_empresa, id_usuario, id_en_abm, cantidad_a_armar, deposito_origen, deposito_destino,
        )
        if ok:
            messages.success(request, f"Armado registrado. Comprobante {nro_comp}.")
        else:
            messages.error(request, error or "Error al ejecutar armado.")
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
            lineas = get_opt_detalle(base_empresa, id_lista) if id_lista else []
            context["lineas"] = lineas
            context["total_pendiente"] = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
            depositos = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(self.request))
            # En OPP solo se muestran depósitos con Suma stock = Sí (destino de producción que suma a stock)
            context["depositos"] = [d for d in depositos if (d.get("suma_stock") or "Si").strip().lower() in ("si", "sí")]
            context["id_deposito_produccion"] = get_deposito_produccion_mpr(base_empresa)
        elif paso == 4:
            id_articulo = wizard.get("id_articulo")
            id_en_abm = get_id_en_abm_por_articulo(base_empresa, id_articulo) if id_articulo else None
            context["id_en_abm"] = id_en_abm
            context["mostrar_armado"] = bool(id_en_abm and get_articulo_armado_por_bom(base_empresa, id_en_abm))
            context["conjuntos"] = listar_bom_conjuntos(base_empresa)
            context["bom_seleccionado"] = get_bom_detalle(base_empresa, id_en_abm) if id_en_abm else None
            context["articulo_armado"] = get_articulo_armado_por_bom(base_empresa, id_en_abm) if id_en_abm else None
            context["depositos"] = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(self.request))
            context["cantidad_sugerida"] = wizard.get("cantidad_pedida", 1)
        elif paso == 5:
            id_lista = wizard.get("id_lista")
            lineas = get_op_detalle(base_empresa, id_lista) if id_lista else []
            context["id_lista"] = id_lista
            context["total_pendiente"] = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas)
            context["opt_cerrar_url"] = reverse("mpr:opt_cerrar", kwargs={"id_lista": id_lista}) if id_lista else None
        return context


class OptListView(MprLoginRequiredMixin, TemplateView):
    """Lista de OPT (Pedidos de producción)."""

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
        articulo_filter = self.request.GET.get("articulo", "").strip()
        id_articulo = int(articulo_filter) if articulo_filter.isdigit() else None
        estado_filter = (self.request.GET.get("estado", "") or "todos").strip().lower()
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
            limit=200,
            id_articulo=id_articulo,
            estado_en_proceso=estado_en_proceso,
            solo_atrasadas=solo_atrasadas,
        )
        context["base_empresa"] = base_empresa
        context["ordenes"] = ordenes
        context["filtro_articulo"] = articulo_filter
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
        paso_liberada_opt = en_proceso or (total_pendiente == 0)
        paso_producida_opp = total_pendiente == 0
        paso_pendiente_cero = total_pendiente == 0
        paso_cerrado = not en_proceso

        # Cantidades ya armadas por artículo (solo si OPT con id_lista)
        cantidades_armadas = {}
        if id_lista and id_lista != 0:
            cantidades_armadas = get_cantidades_armadas_por_opt(base_empresa, id_lista)

        lineas_with_armado = []
        for l in lineas:
            id_art = l.get("id_articulo")
            id_en_abm = get_id_en_abm_por_articulo(base_empresa, id_art) if id_art else None
            if id_en_abm:
                cantidad_pedida = l.get("cantidad_pedida") or 0
                cantidad_ya_armada = cantidades_armadas.get(id_art, 0)
                cantidad_restante_armar = max(0, cantidad_pedida - cantidad_ya_armada)
                lineas_with_armado.append({
                    "linea": l,
                    "id_en_abm": id_en_abm,
                    "cantidad_pendiente": l.get("cantidad_pendiente_prod") or 0,
                    "cantidad_pedida": cantidad_pedida,
                    "cantidad_ya_armada": cantidad_ya_armada,
                    "cantidad_restante_armar": cantidad_restante_armar,
                })
        # Armado habilitado solo si Pendiente 0 y hay al menos una línea con restante por armar
        hay_restante_armar = any(item["cantidad_restante_armar"] > 0 for item in lineas_with_armado)
        # Enriquecer cada línea con datos de armado para la tabla (cantidad_ya_armada, cantidad_restante_armar o None)
        armado_por_articulo = {
            item["linea"]["id_articulo"]: {
                "cantidad_ya_armada": item["cantidad_ya_armada"],
                "cantidad_restante_armar": item["cantidad_restante_armar"],
            }
            for item in lineas_with_armado
        }
        for l in lineas:
            d = armado_por_articulo.get(l.get("id_articulo"))
            l["cantidad_ya_armada"] = d["cantidad_ya_armada"] if d else None
            l["cantidad_restante_armar"] = d["cantidad_restante_armar"] if d else None
        if lineas_with_armado:
            for item in lineas_with_armado:
                item["armado_url"] = (
                    reverse("mpr:armado") + f"?id_lista={id_lista}"
                    if total_pendiente == 0 and hay_restante_armar and id_lista
                    else ""
                )
        paso_armado = (
            not lineas_with_armado
            or all(item["cantidad_ya_armada"] >= item["cantidad_pedida"] for item in lineas_with_armado)
        )

        # Porcentaje según 6 pasos: Pedida, En producción, Producida (OPP), Pendiente 0, Armado, Cerrado
        num_pasos = sum([
            paso_pedida,
            paso_liberada_opt,
            paso_producida_opp,
            paso_pendiente_cero,
            paso_armado,
            paso_cerrado,
        ])
        porcentaje_estado = min(100, round(100 * num_pasos / 6)) if num_pasos else 0

        if total_pendiente == 0 and en_proceso:
            estado_actual_texto = "Completada (pendiente 0). Puede cerrar la OPT."
        elif total_pendiente == 0:
            estado_actual_texto = "Producida (OPP). Pendiente: 0 unidades."
        elif en_proceso:
            estado_actual_texto = "En producción. Pendiente: {} unidades.".format(total_pendiente)
        else:
            estado_actual_texto = "En producción (pendiente: {}).".format(total_pendiente)

        context["lineas_with_armado"] = lineas_with_armado
        context["hay_restante_armar"] = hay_restante_armar
        context["base_empresa"] = base_empresa
        context["id_lista"] = id_lista
        context["opt_numero"] = opt_numero
        context["lineas"] = lineas
        context["total_pedida"] = total_pedida
        context["total_pendiente"] = total_pendiente
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
            try:
                from mpr.models import OptLinea

                opt_linea = OptLinea.objects.filter(
                    id_lista_produccion=id_lista
                ).select_related("opt").first()
                if opt_linea and opt_linea.opt.base_empresa == base_empresa and opt_linea.opt.codigo_movimiento:
                    codigo_movimiento = opt_linea.opt.codigo_movimiento
            except Exception:
                pass
        context["codigo_movimiento"] = codigo_movimiento
        return context


class RegistrarOppView(MprLoginRequiredMixin, TemplateView):
    """Pantalla Registrar OPP (Parte de producción): cantidad producida, depósito origen y destino."""

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
        lineas = get_opt_detalle(base_empresa, id_lista)
        if not lineas:
            raise Http404("OPT no encontrada o sin líneas.")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_empresa = _get_base_empresa(self.request)
        id_lista = kwargs.get("id_lista", 0)
        lineas = get_opt_detalle(base_empresa, id_lista)
        total_pendiente = sum(l["cantidad_pendiente_prod"] for l in lineas)
        depositos = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(self.request))
        context["base_empresa"] = base_empresa
        context["id_lista"] = id_lista
        context["opt_numero"] = id_lista
        context["lineas"] = lineas
        context["total_pendiente"] = total_pendiente
        context["depositos"] = depositos
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        id_lista = kwargs.get("id_lista", 0)
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:opt_detail", id_lista=id_lista)
        session_user = request.session.get("user", {})
        id_usuario = session_user.get("id_usuario")
        try:
            id_usuario = int(id_usuario) if id_usuario is not None else None
        except (TypeError, ValueError):
            id_usuario = None
        if not id_usuario:
            messages.error(request, "Sesión sin usuario. Inicie sesión de nuevo.")
            return redirect("mpr:registrar_opp", id_lista=id_lista)
        cantidad_raw = request.POST.get("cantidad", "").strip()
        origen_raw = request.POST.get("deposito_origen", "").strip()
        destino_raw = request.POST.get("deposito_destino", "").strip()
        try:
            cantidad_total = int(cantidad_raw) if cantidad_raw else 0
        except ValueError:
            cantidad_total = 0
        try:
            deposito_origen = int(origen_raw) if origen_raw else None
        except ValueError:
            deposito_origen = None
        try:
            deposito_destino = int(destino_raw) if destino_raw else None
        except ValueError:
            deposito_destino = None
        if cantidad_total <= 0 or not deposito_origen or not deposito_destino:
            messages.error(request, "Indique cantidad positiva, depósito origen y depósito destino.")
            return redirect("mpr:registrar_opp", id_lista=id_lista)
        lineas = get_opt_detalle(base_empresa, id_lista)
        if not lineas:
            messages.error(request, "No se encontraron líneas para esta OPT.")
            return redirect("mpr:opt_detail", id_lista=id_lista)
        ok, codigo_mov, nro_comprobante, error = ejecutar_opp(
            base_empresa, id_usuario, id_lista, lineas,
            cantidad_total, deposito_origen, deposito_destino,
        )
        if ok:
            messages.success(
                request,
                f"Parte de producción (OPP) registrada. Movimiento {codigo_mov} · Comprobante {nro_comprobante}.",
            )
            return redirect("mpr:opt_detail", id_lista=id_lista)
        messages.error(request, error or "Error al registrar la parte de producción (OPP).")
        return redirect("mpr:registrar_opp", id_lista=id_lista)


class CerrarOptView(MprLoginRequiredMixin, TemplateView):
    """Cierra la OPT (en_proceso_produccion='No' en todas sus líneas) cuando el pendiente total es 0. Solo POST."""

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        id_lista = kwargs.get("id_lista", 0)
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:opt_detail", id_lista=id_lista)
        ok, error = cerrar_opt(base_empresa, id_lista)
        if ok:
            messages.success(request, f"OPT {id_lista} cerrada correctamente.")
        else:
            messages.error(request, error or "Error al cerrar la OPT.")
        referer = request.META.get("HTTP_REFERER") or ""
        if "mpr/tablero" in referer or referer.endswith("/mpr/"):
            return redirect("mpr:tablero")
        return redirect("mpr:opt_detail", id_lista=id_lista)


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
        context["conjuntos"] = listar_bom_conjuntos(
            base_empresa,
            limit=100,
            solo_activos=solo_activos,
            solo_en_produccion=solo_en_produccion,
        )
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


class PedidosFabricaListView(MprLoginRequiredMixin, TemplateView):
    """Listado de pedidos con estado de producción (comp_ped tipo_pedido_opt: Pendiente, Produccion, Terminado)."""

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
        context["pedidos"] = listar_pedidos_fabrica(base_empresa, limit=100, estado=estado)
        context["filtro_estado"] = estado or ""
        return context


class ConfigDepositosView(MprLoginRequiredMixin, TemplateView):
    """Configuración MPR: depósitos, suma_stock y depósito de producción (donde se lleva el stock al liberar OPT)."""

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
        context["depositos"] = listar_depositos_config(base)
        context["id_deposito_produccion"] = get_deposito_produccion_mpr(base)
        return context

    def post(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("mpr:config_depositos")
        # Depósito de producción (formulario con select deposito_produccion)
        if "deposito_produccion" in request.POST:
            dep_prod = request.POST.get("deposito_produccion", "").strip()
            id_dep = None
            if dep_prod:
                try:
                    id_dep = int(dep_prod)
                except ValueError:
                    id_dep = None
            if set_deposito_produccion_mpr(base_empresa, id_dep):
                if id_dep:
                    messages.success(request, "Depósito de producción actualizado. Al confirmar la OPT el stock se registrará en este depósito.")
                else:
                    messages.success(request, "Depósito de producción quitado. Configure uno para que el asistente confirme la OPT automáticamente.")
            else:
                messages.error(request, "No se pudo guardar el depósito de producción.")
            return redirect("mpr:config_depositos")
        # Toggle suma_stock
        cod = request.POST.get("cod_deposito", "").strip()
        valor = request.POST.get("valor", "").strip()
        try:
            cod_deposito = int(cod) if cod else None
        except ValueError:
            cod_deposito = None
        if not cod_deposito or valor not in ("Si", "No"):
            messages.error(request, "Datos inválidos para actualizar depósito.")
            return redirect("mpr:config_depositos")
        ok, err = actualizar_deposito_suma_stock(base_empresa, cod_deposito, valor)
        if ok:
            messages.success(request, f"Depósito {cod_deposito} actualizado: Suma stock = {valor}.")
        else:
            messages.error(request, err or "Error al actualizar.")
        return redirect("mpr:config_depositos")


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
            return context
        lineas = get_opt_detalle(base_empresa, id_lista)
        if not lineas:
            context["lineas_armado"] = []
            context["id_lista"] = id_lista
            context["opt_numero"] = id_lista
            context["depositos"] = get_depositos_con_suma_stock(base_empresa, _get_id_puesto(self.request))
            return context
        cantidades_armadas = get_cantidades_armadas_por_opt(base_empresa, id_lista)
        lineas_armado = []
        for l in lineas:
            id_art = l.get("id_articulo")
            id_en_abm = get_id_en_abm_por_articulo(base_empresa, id_art) if id_art else None
            if not id_en_abm:
                continue
            cantidad_pedida = l.get("cantidad_pedida") or 0
            cantidad_ya_armada = cantidades_armadas.get(id_art, 0)
            cantidad_restante_armar = max(0, cantidad_pedida - cantidad_ya_armada)
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
        context["hay_restante_armar"] = any(item["cantidad"] > 0 for item in lineas_armado)
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
        ejecutados = 0
        primer_error = None
        for l in lineas:
            id_art = l.get("id_articulo")
            id_en_abm = get_id_en_abm_por_articulo(base_empresa, id_art) if id_art else None
            if not id_en_abm:
                continue
            cantidad_pedida = l.get("cantidad_pedida") or 0
            cantidad_ya_armada = cantidades_armadas.get(id_art, 0)
            cantidad_restante_armar = max(0, cantidad_pedida - cantidad_ya_armada)
            if cantidad_restante_armar <= 0:
                continue
            ok, codigo_mov, nro_comp, error = ejecutar_armado(
                base_empresa,
                id_usuario,
                id_en_abm,
                cantidad_restante_armar,
                deposito_origen,
                deposito_destino,
                id_lista_produccion=id_lista,
                id_articulo_armado=id_art,
            )
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
        if tipo not in ("pendiente", "wip", "stock", "bajo_minimo"):
            tipo = "pendiente"
        context["base_empresa"] = base_empresa
        context["tipo_reporte"] = tipo
        if tipo == "pendiente":
            context["filas"] = reporte_mpr_pendiente(base_empresa, limit=200)
            context["titulo_reporte"] = "Pendiente por artículo / pedido"
        elif tipo == "wip":
            context["filas"] = reporte_mpr_wip(base_empresa, limit=200)
            context["titulo_reporte"] = "En progreso (WIP)"
        elif tipo == "stock":
            context["filas"] = reporte_mpr_stock(base_empresa, limit=500)
            context["titulo_reporte"] = "Stock por tipo / depósito"
        else:
            context["filas"] = reporte_mpr_bajo_minimo(base_empresa, limit=200)
            context["titulo_reporte"] = "Bajo mínimo"
        return context


class VentanaPackActualizarView(MprLoginRequiredMixin, TemplateView):
    """POST: ejecuta actualizar_pedidos_produccion y redirige a Pedido producción trabajo (OPT) con mensaje."""

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
        ok, msg = actualizar_pedidos_produccion(
            base_empresa,
            id_usuario=id_usuario,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            busqueda=busqueda,
        )
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


class VentanaPackAgruparView(MprLoginRequiredMixin, TemplateView):
    """Pantalla 2: recibe selección desde Pedido producción trabajo (OPT), muestra tabla con cantidades editables y tooltip; POST 'Generar OPT' crea la OPT."""

    template_name = "mpr/ventana_pack_agrupar.html"

    def get(self, request, *args, **kwargs):
        from django.contrib import messages
        base_empresa = _get_base_empresa(request)
        if not base_empresa:
            messages.error(request, "No se pudo determinar la empresa activa.")
            return redirect("core:dashboard")
        seleccion = request.session.get("ventana_pack_seleccion")
        if not seleccion or not seleccion.get("filas"):
            messages.info(request, "No hay selección. Elija artículos en Pedido producción trabajo (OPT) y pulse Continuar.")
            return redirect("mpr:ventana_pack")
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
                messages.error(request, "La selección expiró. Vuelva a Pedido producción trabajo (OPT) y seleccione de nuevo.")
                return redirect("mpr:ventana_pack")
            # OPT se genera desde Unidades (componentes BOM); cant_* vienen del formulario de filas_unidades
            filas_unidades = listar_unidades_desde_seleccion(base_empresa, seleccion["filas"], limit=200)
            lineas = []
            for f in filas_unidades:
                id_art = f.get("id_articulo")
                if not id_art:
                    continue
                qty_str = request.POST.get("cant_" + str(id_art), "0").strip()
                try:
                    qty = int(qty_str) if qty_str else 0
                except ValueError:
                    qty = 0
                if qty > 0:
                    lineas.append((int(id_art), qty))
            if not lineas:
                messages.error(request, "Indique al menos un artículo con cantidad mayor a 0.")
                return self.get(request, *args, **kwargs)
            session_user = request.session.get("user", {})
            try:
                id_usuario = int(session_user.get("id_usuario")) if session_user.get("id_usuario") is not None else None
            except (TypeError, ValueError):
                id_usuario = None
            ok, id_lista_principal, error = crear_opt_multiples_articulos(base_empresa, id_usuario, lineas)
            if ok and id_lista_principal:
                if "ventana_pack_seleccion" in request.session:
                    del request.session["ventana_pack_seleccion"]
                # Si estamos en el asistente (wizard), liberar a producción y pasar al paso 3 (OPP)
                wizard = request.session.get(WIZARD_SESSION_KEY) or {}
                if wizard.get("paso") == 1:
                    deposito_produccion = get_deposito_produccion_mpr(base_empresa)
                    if deposito_produccion:
                        lineas_detalle = get_op_detalle(base_empresa, id_lista_principal)
                        if lineas_detalle:
                            total_liberar = sum(l.get("cantidad_pendiente_prod") or 0 for l in lineas_detalle)
                            ok_opt, _cod, nro_comp, err_opt = ejecutar_liberar_opt(
                                base_empresa, id_usuario, id_lista_principal, lineas_detalle,
                                total_liberar, deposito_produccion,
                            )
                            if ok_opt:
                                primer_art = lineas_detalle[0].get("id_articulo") if lineas_detalle else None
                                request.session[WIZARD_SESSION_KEY] = {
                                    "paso": 3,
                                    "id_lista": id_lista_principal,
                                    "id_articulo": primer_art,
                                    "cantidad_pedida": total_liberar,
                                }
                                request.session.modified = True
                                messages.success(request, f"OPT Nº {id_lista_principal} creada y liberada. Comprobante {nro_comp}. Siguiente: Crear OPP.")
                                return redirect("mpr:wizard")
                            messages.error(request, err_opt or "Error al liberar a producción.")
                        else:
                            messages.error(request, "No se pudieron cargar las líneas de la OPT.")
                    else:
                        messages.error(request, "Configure el depósito de producción en Config. Depósitos para continuar en el asistente.")
                    return redirect("mpr:ventana_pack_agrupar")
                messages.success(request, f"OPT creada con {len(lineas)} artículo(s). Nº {id_lista_principal}.")
                return redirect("mpr:opt_detail", id_lista=id_lista_principal)
            messages.error(request, error or "Error al crear la OPT.")
            return self.get(request, *args, **kwargs)
        # POST desde Pantalla 1: guardar sel y cant_* en sesión y redirigir GET
        selected = request.POST.getlist("sel")
        filas_sesion = []
        ventana_pack_filas = listar_ventana_pack(base_empresa, limit=200)
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
        for f in filas:
            detalle = listar_detalle_pedidos_por_articulo(base_empresa, f.get("id_articulo"), limit=30)
            f["detalle_pedidos"] = detalle
            f["detalle_pedidos_json"] = json.dumps(detalle)
        wizard = self.request.session.get(WIZARD_SESSION_KEY) or {}
        context["base_empresa"] = base_empresa
        context["filas"] = filas
        context["filas_unidades"] = listar_unidades_desde_seleccion(base_empresa, filas, limit=200)
        context["en_wizard"] = wizard.get("paso") == 1
        context["wizard_paso"] = 2
        return context


class VentanaPackView(MprLoginRequiredMixin, TemplateView):
    """Pedido producción trabajo (OPT) Pantalla 1: demanda por artículo; formulario envía a ventana_pack_agrupar (Continuar)."""

    template_name = "mpr/ventana_pack.html"

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
        vista = (self.request.GET.get("vista") or "pack").strip().lower()
        if vista != "unidades":
            vista = "pack"
        wizard = self.request.session.get(WIZARD_SESSION_KEY) or {}
        context["base_empresa"] = base_empresa
        context["vista_unidades"] = vista == "unidades"
        context["filas"] = listar_ventana_pack(base_empresa, limit=200)
        context["filas_unidades"] = listar_ventana_pack_unidades(base_empresa, limit=200)
        filtros = self.request.session.get("ventana_pack_filtros_actualizar") or {}
        # Preset fechas: inicio y fin del mes en curso si están vacías
        hoy = date.today()
        if not filtros.get("fecha_desde"):
            filtros = dict(filtros)
            filtros["fecha_desde"] = hoy.replace(day=1).isoformat()
        if not filtros.get("fecha_hasta"):
            filtros = dict(filtros)
            ultimo_dia = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
            filtros["fecha_hasta"] = ultimo_dia.isoformat()
        context["filtros_actualizar"] = filtros
        context["en_wizard"] = wizard.get("paso") == 1
        context["wizard_paso"] = 1
        return context
