"""Vistas UI — Migración BEST → MPR (paridad de maestros)."""

from __future__ import annotations

import logging

from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect
from django.views import View
from django.views.generic import TemplateView

from mpr.best_migration.models import (
    BestArticuloMap,
    BestClienteMap,
    BestDepositoMap,
    BestOperarioMap,
    BestStockInicialMap,
)
from mpr.best_migration.pedido_loader import migrar_pedidos_best
from mpr.best_migration.reset import contar_staging_best, reiniciar_staging_best
from mpr.best_migration.stock_reserva_loader import migrar_stock_reserva_best
from mpr.best_migration.services import (
    aceptar_articulos_seleccionados,
    aceptar_clientes_seleccionados,
    aceptar_depositos_seleccionados,
    aceptar_inferido,
    aceptar_inferido_cliente,
    aceptar_inferido_deposito,
    aceptar_inferido_operario,
    aceptar_inferidos_altos_articulos,
    aceptar_inferidos_clientes,
    aceptar_inferidos_depositos,
    aceptar_inferidos_operarios,
    aceptar_operarios_seleccionados,
    alta_articulo_desde_best,
    alta_articulos_seleccionados,
    cargar_stock_inicial_best,
    descartar_articulo,
    descartar_cliente,
    descartar_deposito,
    descartar_operario,
    descartar_stock_linea,
    hub_context,
    marcar_stock_conciliado,
    marcar_unidades_ok,
    recalcular_mapeo_articulos,
    resolver_fabricados_desde_pp_best,
    resolver_fabricados_desde_terminados,
    aceptar_inferidos_altos_fabricados,
    asignar_admin_a_fabricado_pp,
    asignar_best_a_fabricado,
    buscar_fabricados_admin,
    buscar_skus_best_componentes,
    sincronizar_stock_fabricados_semi,
    reabrir_articulo,
    validar_articulo_fabricado,
    reabrir_operario,
    sincronizar_clientes_abiertos,
    sincronizar_depositos_best,
    sincronizar_operarios_best,
    sincronizar_stock_inicial,
    validar_articulo,
    validar_cliente,
    validar_deposito,
    validar_operario,
)
from mpr.views import MprLoginRequiredMixin, _get_base_empresa, _usuario_tiene_permiso_mpr

logger = logging.getLogger(__name__)


def _require_base(request):
    base = _get_base_empresa(request)
    if not base:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return None
    return base


def _usuario_label(request) -> str:
    user = request.session.get("user") or {}
    return (
        (user.get("cod_usuario") or user.get("nombre") or "")
        or getattr(request.user, "username", "")
        or "usuario"
    )


_FILTRO_GET_KEYS = (
    "estado",
    "q",
    "pendientes",
    "necesarios",
    "alcance",
    "todos",
    "incluir_stock",
    "filtrado",
)


def _tiene_filtros_get(request) -> bool:
    """True si el usuario aplicó filtros (hay query de filtro, aunque vacía).

    Los checkboxes destildados no envían parámetro; el form GET manda
    ``filtrado=1`` y/o ``estado=`` / ``q=`` vacíos. Contar solo valores
    truthy hacía que destildar «Solo necesarios…» se reinterpretara como
    primera visita y reactivara la cola por defecto.
    """
    params = request.GET
    if params.get("filtrado") == "1":
        return True
    return any(k in params for k in _FILTRO_GET_KEYS)


def _filtro_necesarios_pendientes(request) -> bool:
    """Default: cola de trabajo (requeridos no resueltos) solo sin query de filtros."""
    if not _tiene_filtros_get(request):
        return True
    if request.GET.get("todos") == "1":
        return False
    if request.GET.get("necesarios") == "1":
        return True
    if request.GET.get("pendientes") == "1":
        return True
    return False


def _aplicar_filtro_alcance(qs, *, cola_trabajo: bool, alcance: str, model_cls):
    """Filtra por alcance: cola de trabajo o solo requeridos."""
    estados_resueltos = [model_cls.Estado.VALIDADO, model_cls.Estado.DESCARTADO]
    if cola_trabajo:
        return qs.filter(requerido_migracion=True).exclude(estado__in=estados_resueltos)
    if alcance == "necesarios":
        return qs.filter(requerido_migracion=True)
    return qs


def _aplicar_filtro_alcance_articulos(
    qs, *, cola_trabajo: bool, alcance: str, incluir_stock: bool
):
    """Cola de migración = pedidos abiertos; stock solo si incluir_stock=True."""
    estados_resueltos = [
        BestArticuloMap.Estado.VALIDADO,
        BestArticuloMap.Estado.DESCARTADO,
    ]
    origenes = [BestArticuloMap.OrigenRequerimiento.PEDIDO_ABIERTO]
    if incluir_stock:
        origenes.append(BestArticuloMap.OrigenRequerimiento.STOCK_DEPOSITO)
    if cola_trabajo:
        return qs.filter(
            requerido_migracion=True,
            origen_requerimiento__in=origenes,
        ).exclude(estado__in=estados_resueltos)
    if alcance == "necesarios":
        return qs.filter(
            requerido_migracion=True,
            origen_requerimiento__in=origenes,
        )
    return qs


class MigracionBestHubView(MprLoginRequiredMixin, TemplateView):
    template_name = "mpr/best_migration/hub.html"

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            messages.error(request, "No tenés permiso para ver Migración BEST.")
            return redirect("mpr:tablero_produccion")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not _require_base(request):
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = _get_base_empresa(self.request)
        ctx["base_empresa"] = base
        ctx.update(hub_context(base))
        staging = contar_staging_best(base)
        ctx["staging_conteos"] = staging
        ctx["staging_total"] = sum(staging.values())
        return ctx


class MigracionBestReiniciarView(MprLoginRequiredMixin, View):
    """POST: borra mapas/paridad BEST en Postgres para la empresa activa."""

    def post(self, request, *args, **kwargs):
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            messages.error(request, "No tenés permiso para reiniciar Migración BEST.")
            return redirect("mpr:tablero_produccion")
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")

        confirmar = (request.POST.get("confirmar") or "").strip()
        base_confirmada = (request.POST.get("base_empresa") or "").strip()
        acepto = request.POST.get("acepto_riesgos") == "1"

        if confirmar != "REINICIAR" or not acepto or base_confirmada != base:
            messages.error(
                request,
                "Reinicio cancelado: faltó la confirmación explícita de riesgos "
                "o no coincide la empresa activa.",
            )
            return redirect("mpr:migracion_best_hub")

        try:
            prev = reiniciar_staging_best(base)
            total = sum(prev.values())
            detalle = ", ".join(f"{k}={v}" for k, v in prev.items())
            messages.success(
                request,
                f"Migración BEST reiniciada en Postgres para {base} "
                f"({total} filas: {detalle}). "
                "Recalculá artículos y sincronizá clientes/depósitos/stock.",
            )
        except Exception as exc:
            logger.exception("Error reiniciando Migración BEST")
            messages.error(request, f"No se pudo reiniciar la migración: {exc}")
        return redirect("mpr:migracion_best_hub")


class MigracionBestArticulosView(MprLoginRequiredMixin, TemplateView):
    template_name = "mpr/best_migration/articulos.html"

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            messages.error(request, "No tenés permiso para ver Migración BEST.")
            return redirect("mpr:tablero_produccion")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not _require_base(request):
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = _get_base_empresa(self.request)
        estado = (self.request.GET.get("estado") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        alcance = (self.request.GET.get("alcance") or "").strip()
        cola_trabajo = _filtro_necesarios_pendientes(self.request)
        incluir_stock = self.request.GET.get("incluir_stock") == "1"
        # Default sin query: solo pedidos. Con "todos" se ve todo (pedido+stock+histórico).
        if not _tiene_filtros_get(self.request):
            incluir_stock = False

        qs = (
            BestArticuloMap.objects.filter(base_empresa=base)
            .exclude(
                origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO
            )
            .order_by("estado", "best_id_articulo")
        )
        if estado:
            qs = qs.filter(estado=estado)
        qs = _aplicar_filtro_alcance_articulos(
            qs,
            cola_trabajo=cola_trabajo,
            alcance=alcance,
            incluir_stock=incluir_stock,
        )
        if q:
            qs = qs.filter(
                Q(best_id_articulo__icontains=q)
                | Q(best_articulo__icontains=q)
                | Q(admin_nombre__icontains=q)
            )

        hub = hub_context(base)
        ctx.update(hub)
        ctx["base_empresa"] = base
        ctx["filas"] = list(qs[:500])
        ctx["filtro_estado"] = estado
        ctx["filtro_q"] = q
        ctx["filtro_alcance"] = alcance
        ctx["cola_trabajo"] = cola_trabajo
        ctx["incluir_stock"] = incluir_stock
        ctx["solo_pendientes"] = cola_trabajo
        ctx["opciones_estado"] = BestArticuloMap.Estado.choices
        return ctx


class MigracionBestClientesView(MprLoginRequiredMixin, TemplateView):
    template_name = "mpr/best_migration/clientes.html"

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            messages.error(request, "No tenés permiso para ver Migración BEST.")
            return redirect("mpr:tablero_produccion")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not _require_base(request):
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = _get_base_empresa(self.request)
        estado = (self.request.GET.get("estado") or "").strip()
        alcance = (self.request.GET.get("alcance") or "").strip()
        cola_trabajo = _filtro_necesarios_pendientes(self.request)

        qs = BestClienteMap.objects.filter(base_empresa=base).order_by("estado", "best_cliente")
        if estado:
            qs = qs.filter(estado=estado)
        qs = _aplicar_filtro_alcance(
            qs, cola_trabajo=cola_trabajo, alcance=alcance, model_cls=BestClienteMap
        )
        hub = hub_context(base)
        ctx.update(hub)
        ctx["base_empresa"] = base
        ctx["filas"] = list(qs)
        ctx["filtro_estado"] = estado
        ctx["filtro_alcance"] = alcance
        ctx["cola_trabajo"] = cola_trabajo
        ctx["solo_pendientes"] = cola_trabajo
        ctx["opciones_estado"] = BestClienteMap.Estado.choices
        return ctx


class MigracionBestDepositosView(MprLoginRequiredMixin, TemplateView):
    template_name = "mpr/best_migration/depositos.html"

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            messages.error(request, "No tenés permiso para ver Migración BEST.")
            return redirect("mpr:tablero_produccion")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not _require_base(request):
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = _get_base_empresa(self.request)
        estado = (self.request.GET.get("estado") or "").strip()
        alcance = (self.request.GET.get("alcance") or "").strip()
        cola_trabajo = _filtro_necesarios_pendientes(self.request)

        qs = BestDepositoMap.objects.filter(base_empresa=base).order_by("estado", "best_id_deposito")
        if estado:
            qs = qs.filter(estado=estado)
        qs = _aplicar_filtro_alcance(
            qs, cola_trabajo=cola_trabajo, alcance=alcance, model_cls=BestDepositoMap
        )
        hub = hub_context(base)
        ctx.update(hub)
        ctx["base_empresa"] = base
        ctx["filas"] = list(qs)
        ctx["filtro_estado"] = estado
        ctx["filtro_alcance"] = alcance
        ctx["cola_trabajo"] = cola_trabajo
        ctx["solo_pendientes"] = cola_trabajo
        ctx["opciones_estado"] = BestDepositoMap.Estado.choices
        return ctx


class MigracionBestStockInicialView(MprLoginRequiredMixin, TemplateView):
    template_name = "mpr/best_migration/stock_inicial.html"

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            messages.error(request, "No tenés permiso para ver Migración BEST.")
            return redirect("mpr:tablero_produccion")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not _require_base(request):
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = _get_base_empresa(self.request)
        estado = (self.request.GET.get("estado") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        solo_delta = self.request.GET.get("solo_delta") == "1"
        cola = (self.request.GET.get("cola") or "listos_carga").strip()
        cola_trabajo = _filtro_necesarios_pendientes(self.request)

        qs = BestStockInicialMap.objects.filter(base_empresa=base).order_by(
            "estado", "best_id_articulo", "best_id_deposito"
        )
        if cola == "pendiente_mapeo":
            qs = qs.filter(
                estado__in=[
                    BestStockInicialMap.Estado.SIN_MAPEO_ARTICULO,
                    BestStockInicialMap.Estado.SIN_MAPEO_DEPOSITO,
                ]
            )
        elif cola == "ya_cargados":
            qs = qs.filter(estado=BestStockInicialMap.Estado.CARGADO)
        else:
            cola = "listos_carga"
            qs = qs.filter(
                estado__in=[
                    BestStockInicialMap.Estado.LISTO,
                    BestStockInicialMap.Estado.CONCILIADO,
                ]
            )
        if estado:
            qs = qs.filter(estado=estado)
        if cola_trabajo and cola == "listos_carga":
            qs = qs.filter(requerido_migracion=True).exclude(
                estado__in=[
                    BestStockInicialMap.Estado.CONCILIADO,
                    BestStockInicialMap.Estado.CARGADO,
                    BestStockInicialMap.Estado.DESCARTADO,
                ]
            )
        if solo_delta:
            qs = qs.filter(delta_pares__isnull=False).exclude(delta_pares=0)
        if q:
            qs = qs.filter(
                Q(best_id_articulo__icontains=q)
                | Q(best_articulo__icontains=q)
                | Q(admin_nombre__icontains=q)
            )
        total_filtrado = qs.count()
        hub = hub_context(base)
        ctx.update(hub)
        ctx["base_empresa"] = base
        ctx["filas"] = list(qs[:500])
        ctx["filtro_estado"] = estado
        ctx["filtro_q"] = q
        ctx["solo_delta"] = solo_delta
        ctx["cola_trabajo"] = cola_trabajo
        ctx["cola_activa"] = cola
        ctx["solo_pendientes"] = cola_trabajo
        ctx["opciones_estado"] = BestStockInicialMap.Estado.choices
        ctx["total_filtrado"] = total_filtrado
        ctx["limite_listado"] = 500
        return ctx


class MigracionBestRecalcularArticulosView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            messages.error(request, "Sin permiso.")
            return redirect("mpr:migracion_best_hub")
        try:
            result = recalcular_mapeo_articulos(base)
            messages.success(
                request,
                (
                    f"Mapeo de artículos recalculado ({result['dict_version']}): "
                    f"{result['total']} SKUs — "
                    f"nuevos {result['created']}, actualizados {result['updated']}, "
                    f"preservados validados {result['preserved']}."
                ),
            )
        except Exception as exc:
            logger.exception("Error recalculando mapeo BEST artículos")
            messages.error(request, f"No se pudo recalcular el mapeo: {exc}")
        return redirect("mpr:migracion_best_articulos")


class MigracionBestAceptarInferidosArticulosView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        try:
            result = aceptar_inferidos_altos_articulos(
                base_empresa=base, usuario=_usuario_label(request)
            )
            messages.success(
                request,
                f"Aceptados en lote {result['aceptados']} artículos con inferencia alta.",
            )
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("mpr:migracion_best_articulos")


class MigracionBestSincronizarClientesView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        try:
            result = sincronizar_clientes_abiertos(base)
            messages.success(
                request,
                f"Clientes sincronizados e inferidos: {result['total']} "
                f"(nuevos {result['created']}, actualizados {result['updated']}, "
                f"preservados {result['preserved']}).",
            )
        except Exception as exc:
            logger.exception("Error sincronizando clientes BEST")
            messages.error(request, f"No se pudieron sincronizar clientes: {exc}")
        return redirect("mpr:migracion_best_clientes")


class MigracionBestSincronizarDepositosView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        try:
            result = sincronizar_depositos_best(base)
            messages.success(
                request,
                f"Depósitos sincronizados e inferidos: {result['total']} "
                f"(nuevos {result['created']}, actualizados {result['updated']}, "
                f"preservados {result['preserved']}).",
            )
        except Exception as exc:
            logger.exception("Error sincronizando depósitos BEST")
            messages.error(request, f"No se pudieron sincronizar depósitos: {exc}")
        return redirect("mpr:migracion_best_depositos")


class MigracionBestValidarDepositoView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        map_id = (request.POST.get("map_id") or "").strip()
        accion = (request.POST.get("accion") or "").strip()
        notas = (request.POST.get("notas") or "").strip()
        usuario = _usuario_label(request)
        try:
            if accion == "aceptar_lote":
                result = aceptar_inferidos_depositos(base_empresa=base, usuario=usuario)
                messages.success(
                    request,
                    f"Aceptados en lote {result['aceptados']} depósitos inferidos.",
                )
                return redirect("mpr:migracion_best_depositos")
            if accion == "aceptar_seleccion":
                ids = []
                for raw in request.POST.getlist("sel"):
                    if str(raw).isdigit():
                        ids.append(int(raw))
                if not ids:
                    raise ValueError("Seleccioná al menos una fila con candidato.")
                result = aceptar_depositos_seleccionados(
                    base_empresa=base, map_ids=ids, usuario=usuario
                )
                messages.success(
                    request,
                    f"Aceptados {result['aceptados']} depósitos seleccionados"
                    f" ({result['omitidos']} omitidos).",
                )
                return redirect("mpr:migracion_best_depositos")
            if not map_id.isdigit():
                raise ValueError("ID de mapeo inválido.")
            mid = int(map_id)
            if accion == "aceptar":
                aceptar_inferido_deposito(base_empresa=base, map_id=mid, usuario=usuario)
                messages.success(request, "Depósito validado con el CodDeposito inferido.")
            elif accion == "descartar":
                descartar_deposito(base_empresa=base, map_id=mid, usuario=usuario, notas=notas)
                messages.success(request, "Depósito descartado.")
            elif accion == "asignar":
                raw = (request.POST.get("admin_cod_deposito") or "").strip()
                if not raw.isdigit():
                    raise ValueError("CodDeposito inválido.")
                validar_deposito(
                    base_empresa=base,
                    map_id=mid,
                    admin_cod_deposito=int(raw),
                    usuario=usuario,
                    notas=notas,
                )
                messages.success(
                    request,
                    f"Asignado → CodDeposito {raw}. Se aplicó tipo_mpr si correspondía.",
                )
            else:
                raise ValueError("Acción no reconocida.")
        except BestDepositoMap.DoesNotExist:
            messages.error(request, "No existe ese mapeo de depósito.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("mpr:migracion_best_depositos")


class MigracionBestOperariosView(MprLoginRequiredMixin, TemplateView):
    template_name = "mpr/best_migration/operarios.html"

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            messages.error(request, "No tenés permiso para ver Migración BEST.")
            return redirect("mpr:tablero_produccion")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not _require_base(request):
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = _get_base_empresa(self.request)
        estado = (self.request.GET.get("estado") or "").strip()
        alcance = (self.request.GET.get("alcance") or "").strip()
        cola_trabajo = _filtro_necesarios_pendientes(self.request)

        qs = BestOperarioMap.objects.filter(base_empresa=base).order_by("estado", "best_codigo")
        if estado:
            qs = qs.filter(estado=estado)
        qs = _aplicar_filtro_alcance(
            qs, cola_trabajo=cola_trabajo, alcance=alcance, model_cls=BestOperarioMap
        )
        hub = hub_context(base)
        ctx.update(hub)
        ctx["base_empresa"] = base
        ctx["filas"] = list(qs)
        ctx["filtro_estado"] = estado
        ctx["filtro_alcance"] = alcance
        ctx["cola_trabajo"] = cola_trabajo
        ctx["solo_pendientes"] = cola_trabajo
        ctx["opciones_estado"] = BestOperarioMap.Estado.choices
        return ctx


class MigracionBestSincronizarOperariosView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        try:
            result = sincronizar_operarios_best(base)
            messages.success(
                request,
                f"Operarios/tejedores sincronizados ({result.get('fuente')}): {result['total']} "
                f"(nuevos {result['created']}, actualizados {result['updated']}, "
                f"preservados {result['preserved']}).",
            )
        except Exception as exc:
            logger.exception("Error sincronizando operarios BEST")
            messages.error(request, f"No se pudieron sincronizar operarios: {exc}")
        return redirect("mpr:migracion_best_operarios")


class MigracionBestValidarOperarioView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        map_id = (request.POST.get("map_id") or "").strip()
        accion = (request.POST.get("accion") or "").strip()
        notas = (request.POST.get("notas") or "").strip()
        usuario = _usuario_label(request)
        try:
            if accion == "aceptar_lote":
                result = aceptar_inferidos_operarios(base_empresa=base, usuario=usuario)
                messages.success(
                    request,
                    f"Aceptados en lote {result['aceptados']} tejedores inferidos.",
                )
                return redirect("mpr:migracion_best_operarios")
            if accion == "aceptar_seleccion":
                ids = []
                for raw in request.POST.getlist("sel"):
                    if str(raw).isdigit():
                        ids.append(int(raw))
                if not ids:
                    raise ValueError("Seleccioná al menos una fila con candidato.")
                result = aceptar_operarios_seleccionados(
                    base_empresa=base, map_ids=ids, usuario=usuario
                )
                messages.success(
                    request,
                    f"Aceptados {result['aceptados']} seleccionados"
                    f" ({result['omitidos']} omitidos).",
                )
                return redirect("mpr:migracion_best_operarios")
            if not map_id.isdigit():
                raise ValueError("ID de mapeo inválido.")
            mid = int(map_id)
            if accion == "aceptar":
                aceptar_inferido_operario(base_empresa=base, map_id=mid, usuario=usuario)
                messages.success(request, "Tejedor validado con el operario inferido.")
            elif accion == "descartar":
                descartar_operario(base_empresa=base, map_id=mid, usuario=usuario, notas=notas)
                messages.success(request, "Código tejedor descartado.")
            elif accion == "reabrir":
                reabrir_operario(base_empresa=base, map_id=mid, usuario=usuario, notas=notas)
                messages.success(request, "Mapeo reabierto: podés asignar otro operario.")
            elif accion == "asignar":
                raw = (request.POST.get("admin_id_operario") or "").strip()
                if not raw.isdigit():
                    raise ValueError("Operario inválido.")
                validar_operario(
                    base_empresa=base,
                    map_id=mid,
                    admin_id_operario=int(raw),
                    usuario=usuario,
                    notas=notas,
                )
                messages.success(request, f"Asignado tejedor → operario {raw}.")
            else:
                raise ValueError("Acción no reconocida.")
        except BestOperarioMap.DoesNotExist:
            messages.error(request, "No existe ese mapeo de operario.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("mpr:migracion_best_operarios")


class MigracionBestSincronizarStockInicialView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        try:
            result = sincronizar_stock_inicial(base)
            messages.success(
                request,
                f"Stock inicial sincronizado: {result['total']} líneas "
                f"(nuevas {result['created']}, actualizadas {result['updated']}, "
                f"preservadas {result['preserved']}).",
            )
        except Exception as exc:
            logger.exception("Error sincronizando stock inicial BEST")
            messages.error(request, f"No se pudo sincronizar stock inicial: {exc}")
        return redirect("mpr:migracion_best_stock_inicial")


class MigracionBestValidarStockInicialView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        map_id = (request.POST.get("map_id") or "").strip()
        accion = (request.POST.get("accion") or "").strip()
        notas = (request.POST.get("notas") or "").strip()
        usuario = _usuario_label(request)
        try:
            if not map_id.isdigit():
                raise ValueError("ID de línea inválido.")
            mid = int(map_id)
            if accion == "conciliar":
                marcar_stock_conciliado(
                    base_empresa=base, map_id=mid, usuario=usuario, notas=notas
                )
                messages.success(request, "Línea marcada como conciliada.")
            elif accion == "descartar":
                descartar_stock_linea(
                    base_empresa=base, map_id=mid, usuario=usuario, notas=notas
                )
                messages.success(request, "Línea descartada.")
            else:
                raise ValueError("Acción no reconocida.")
        except BestStockInicialMap.DoesNotExist:
            messages.error(request, "No existe esa línea de stock.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("mpr:migracion_best_stock_inicial")


class MigracionBestCargarStockInicialView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        confirmar = request.POST.get("confirmar") == "1"
        usuario = _usuario_label(request)
        session_user = request.session.get("user") or {}
        id_usuario = session_user.get("id_usuario")
        id_puesto = session_user.get("id_puesto")
        id_pv = session_user.get("id_punto_venta")
        try:
            result = cargar_stock_inicial_best(
                base,
                dry_run=not confirmar,
                usuario=usuario,
                id_usuario=id_usuario,
                id_puesto=id_puesto,
                id_pv=id_pv,
            )
            if result.get("dry_run"):
                preservados = result.get("ya_cargados_preservados", 0)
                messages.info(
                    request,
                    f"Ensayo de ola (sin escribir MySQL): {result.get('candidatos', 0)} líneas "
                    f"candidatas; {result['escrituras']} con delta>0 "
                    f"→ ~{result.get('movimientos_estimados', 0)} MSTOCK «Stock Inicial». "
                    f"{result.get('omitidos_admin_ge_best', result.get('omitidos', 0))} "
                    f"sin movimiento (Admin ≥ BEST). "
                    f"{preservados} ya CARGADO de olas previas no se reprocesan.",
                )
            else:
                movs = result.get("movimientos") or []
                nros = ", ".join(
                    str(m.get("nro_comprobante") or m.get("codigo_movimiento") or "?")
                    for m in movs[:8]
                )
                extra = f" Comprobantes: {nros}." if nros else ""
                if len(movs) > 8:
                    extra = f" Comprobantes: {nros}… ({len(movs)} en total)."
                preservados = result.get("ya_cargados_preservados", 0)
                msg = (
                    f"Ola confirmada: {result.get('candidatos', 0)} candidatas; "
                    f"{result['escrituras']} renglones con delta>0 en "
                    f"{len(movs)} movimiento(s) MSTOCK; "
                    f"{result.get('omitidos_admin_ge_best', result.get('omitidos', 0))} "
                    f"omitidas (Admin ≥ BEST). "
                    f"{preservados} ya CARGADO de olas previas preservadas.{extra}"
                )
                if result.get("errores"):
                    messages.warning(
                        request,
                        msg + " Errores: " + " | ".join(result["errores"][:3]),
                    )
                else:
                    messages.success(request, msg)
        except Exception as exc:
            logger.exception("Error cargando stock inicial BEST")
            messages.error(request, f"No se pudo cargar stock inicial: {exc}")
        return redirect("mpr:migracion_best_stock_inicial")


class MigracionBestValidarClienteView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        map_id = (request.POST.get("map_id") or "").strip()
        accion = (request.POST.get("accion") or "").strip()
        notas = (request.POST.get("notas") or "").strip()
        usuario = _usuario_label(request)
        try:
            if accion == "aceptar_lote":
                result = aceptar_inferidos_clientes(base_empresa=base, usuario=usuario)
                messages.success(
                    request,
                    f"Aceptados en lote {result['aceptados']} clientes inferidos (score ≥ 85).",
                )
                return redirect("mpr:migracion_best_clientes")
            if accion == "aceptar_seleccion":
                ids = []
                for raw in request.POST.getlist("sel"):
                    if str(raw).isdigit():
                        ids.append(int(raw))
                if not ids:
                    raise ValueError("Seleccioná al menos una fila con candidato.")
                result = aceptar_clientes_seleccionados(
                    base_empresa=base, map_ids=ids, usuario=usuario
                )
                messages.success(
                    request,
                    f"Aceptados {result['aceptados']} clientes seleccionados"
                    f" ({result['omitidos']} omitidos).",
                )
                return redirect("mpr:migracion_best_clientes")
            if not map_id.isdigit():
                raise ValueError("ID de mapeo inválido.")
            mid = int(map_id)
            if accion == "aceptar":
                aceptar_inferido_cliente(base_empresa=base, map_id=mid, usuario=usuario)
                messages.success(request, "Cliente validado con el Código inferido.")
            elif accion == "descartar":
                descartar_cliente(base_empresa=base, map_id=mid, usuario=usuario, notas=notas)
                messages.success(request, "Cliente descartado.")
            elif accion == "asignar":
                raw = (request.POST.get("admin_codigo") or "").strip()
                if not raw.isdigit():
                    raise ValueError("Código de cliente inválido.")
                validar_cliente(
                    base_empresa=base,
                    map_id=mid,
                    admin_codigo=int(raw),
                    usuario=usuario,
                    notas=notas,
                )
                messages.success(request, f"Asignado → Código {raw}.")
            else:
                raise ValueError("Acción no reconocida.")
        except BestClienteMap.DoesNotExist:
            messages.error(request, "No existe ese mapeo de cliente.")
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("mpr:migracion_best_clientes")


class MigracionBestValidarArticuloView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        wants_json = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in (request.headers.get("Accept") or "")
        )
        if not base:
            if wants_json:
                return JsonResponse({"ok": False, "error": "Sin empresa activa."}, status=400)
            return redirect("core:dashboard")
        best_id = (request.POST.get("best_id_articulo") or "").strip()
        accion = (request.POST.get("accion") or "").strip()
        notas = (request.POST.get("notas") or "").strip()
        usuario = _usuario_label(request)

        def _json_ok(payload: dict):
            return JsonResponse({"ok": True, **payload})

        def _json_err(msg: str, status: int = 400):
            return JsonResponse({"ok": False, "error": str(msg)}, status=status)

        try:
            if accion == "aceptar_seleccion":
                ids = [x.strip() for x in request.POST.getlist("sel") if (x or "").strip()]
                if not ids:
                    raise ValueError("Seleccioná al menos una fila con candidato.")
                result = aceptar_articulos_seleccionados(
                    base_empresa=base, best_ids=ids, usuario=usuario
                )
                messages.success(
                    request,
                    f"Aceptados {result['aceptados']} artículos seleccionados"
                    f" ({result['omitidos']} omitidos).",
                )
                return redirect("mpr:migracion_best_articulos")
            if accion == "alta_seleccion":
                ids = [x.strip() for x in request.POST.getlist("sel") if (x or "").strip()]
                if not ids:
                    raise ValueError("Seleccioná al menos un SKU sin candidato para dar de alta.")
                result = alta_articulos_seleccionados(
                    base_empresa=base, best_ids=ids, usuario=usuario
                )
                msg = (
                    f"Alta Admin: {result['creados']} creados"
                    f" ({result['omitidos']} omitidos)."
                )
                if result.get("errores"):
                    messages.warning(
                        request,
                        msg + " Errores: " + "; ".join(result["errores"][:5]),
                    )
                else:
                    messages.success(request, msg)
                return redirect("mpr:migracion_best_articulos")
            if accion == "aceptar":
                aceptar_inferido(base_empresa=base, best_id=best_id, usuario=usuario)
                if wants_json:
                    return _json_ok({"best_id": best_id, "accion": "aceptar"})
                messages.success(request, f"Validado {best_id} con el IDArt inferido.")
            elif accion == "alta":
                det = alta_articulo_desde_best(
                    base_empresa=base, best_id=best_id, usuario=usuario
                )
                if wants_json:
                    return _json_ok(
                        {
                            "best_id": best_id,
                            "accion": "alta",
                            "idart": det.get("idart"),
                            "codigo_articulo_t": det.get("codigo_articulo_t"),
                            "precio1v": str(det["precio1v"]) if det.get("precio1v") else None,
                        }
                    )
                precio_txt = ""
                if det.get("precio1v"):
                    precio_txt = f" · Precio1V {det['precio1v']} ({det.get('precio_fuente')})"
                messages.success(
                    request,
                    f"Alta Admin {best_id} → IDArt {det['idart']}"
                    f" ({det.get('codigo_articulo_t')}){precio_txt}.",
                )
            elif accion == "descartar":
                descartar_articulo(
                    base_empresa=base, best_id=best_id, usuario=usuario, notas=notas
                )
                if wants_json:
                    return _json_ok({"best_id": best_id, "accion": "descartar"})
                messages.success(request, f"Descartado {best_id} (no se migrará).")
            elif accion == "asignar":
                raw = (request.POST.get("admin_idart") or "").strip()
                if not raw.isdigit():
                    raise ValueError("IDArt inválido.")
                validar_articulo(
                    base_empresa=base,
                    best_id=best_id,
                    admin_idart=int(raw),
                    usuario=usuario,
                    notas=notas,
                )
                if wants_json:
                    return _json_ok(
                        {"best_id": best_id, "accion": "asignar", "admin_idart": int(raw)}
                    )
                messages.success(request, f"Asignado {best_id} → IDArt {raw}.")
            elif accion == "reabrir":
                reabrir_articulo(
                    base_empresa=base, best_id=best_id, usuario=usuario, notas=notas
                )
                if wants_json:
                    return _json_ok({"best_id": best_id, "accion": "reabrir"})
                messages.success(
                    request,
                    f"Mapeo de {best_id} reabierto: podés asignar otro IDArt.",
                )
            else:
                raise ValueError("Acción no reconocida.")
        except BestArticuloMap.DoesNotExist:
            if wants_json:
                return _json_err("No existe ese SKU en el mapeo.", 404)
            messages.error(request, "No existe ese SKU en el mapeo.")
        except Exception as exc:
            if wants_json:
                return _json_err(str(exc))
            messages.error(request, str(exc))
        next_url = request.POST.get("next") or "mpr:migracion_best_articulos"
        if next_url.startswith("/"):
            return redirect(next_url)
        return redirect(next_url)


def _aplicar_filtro_alcance_fabricados(qs, *, cola_trabajo: bool, alcance: str):
    estados_resueltos = [
        BestArticuloMap.Estado.VALIDADO,
        BestArticuloMap.Estado.DESCARTADO,
    ]
    if alcance == "stock":
        qs = qs.filter(requerido_migracion=False)
        if cola_trabajo:
            qs = qs.exclude(estado__in=estados_resueltos)
        return qs
    if alcance == "necesarios":
        return qs.filter(requerido_migracion=True)
    if cola_trabajo:
        return qs.filter(requerido_migracion=True).exclude(estado__in=estados_resueltos)
    return qs


class MigracionBestArticulosFabricadosView(MprLoginRequiredMixin, TemplateView):
    template_name = "mpr/best_migration/articulos_fabricados.html"

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            messages.error(request, "No tenés permiso para ver Migración BEST.")
            return redirect("mpr:tablero_produccion")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not _require_base(request):
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = _get_base_empresa(self.request)
        estado = (self.request.GET.get("estado") or "").strip()
        q = (self.request.GET.get("q") or "").strip()
        alcance = (self.request.GET.get("alcance") or "").strip()
        cola_trabajo = _filtro_necesarios_pendientes(self.request)

        qs = (
            BestArticuloMap.objects.filter(
                base_empresa=base,
                origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
            )
            .order_by("estado", "best_id_articulo")
        )
        if estado:
            qs = qs.filter(estado=estado)
        qs = _aplicar_filtro_alcance_fabricados(
            qs, cola_trabajo=cola_trabajo, alcance=alcance
        )
        if q:
            qs = qs.filter(
                Q(best_id_articulo__icontains=q)
                | Q(best_articulo__icontains=q)
                | Q(admin_nombre__icontains=q)
            )

        hub = hub_context(base)
        ctx.update(hub)
        ctx["base_empresa"] = base
        ctx["filas"] = list(qs[:500])
        ctx["filtro_estado"] = estado
        ctx["filtro_q"] = q
        ctx["filtro_alcance"] = alcance
        ctx["cola_trabajo"] = cola_trabajo
        ctx["solo_pendientes"] = cola_trabajo
        ctx["opciones_estado"] = BestArticuloMap.Estado.choices
        ctx["articulos_resumen"] = hub.get("articulos_fabricados_resumen") or {}
        return ctx


class MigracionBestResolverFabricadosView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        try:
            result = resolver_fabricados_desde_pp_best(base)
            messages.success(
                request,
                (
                    f"Fabricados resueltos desde PP BEST: {result['fabricados_bom']} SKUs con stock "
                    f"({result['pp_requeridos_pedido']} requeridos por pedido) — "
                    f"nuevos {result['created']}, actualizados {result['updated']}, "
                    f"preservados {result['preserved']}, sin Admin {result['skipped_sin_admin']}."
                ),
            )
        except Exception as exc:
            logger.exception("Error resolviendo fabricados desde PP BEST")
            messages.error(request, f"No se pudieron resolver fabricados: {exc}")
        return redirect("mpr:migracion_best_articulos_fabricados")


class MigracionBestAceptarInferidosFabricadosView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        try:
            result = aceptar_inferidos_altos_fabricados(
                base_empresa=base, usuario=_usuario_label(request)
            )
            messages.success(
                request,
                f"Aceptados en lote {result['aceptados']} fabricados con inferencia alta.",
            )
        except Exception as exc:
            messages.error(request, str(exc))
        return redirect("mpr:migracion_best_articulos_fabricados")


class MigracionBestSincronizarStockFabricadosSemiView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        try:
            result = sincronizar_stock_fabricados_semi(base)
            messages.success(
                request,
                f"Stock Semi-Embalado (4002) sincronizado para fabricados: {result['total']} líneas "
                f"(nuevas {result['created']}, actualizadas {result['updated']}, "
                f"preservadas {result['preserved']}).",
            )
        except Exception as exc:
            logger.exception("Error sincronizando stock fabricados Semi")
            messages.error(request, f"No se pudo sincronizar stock Semi: {exc}")
        return redirect("mpr:migracion_best_stock_inicial")


class MigracionBestSkuComponentesSearchView(MprLoginRequiredMixin, View):
    """GET JSON: búsqueda de SKUs BEST (inventario 4000/4002) para componentes fabricados."""

    def get(self, request, *args, **kwargs):
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            return JsonResponse({"results": [], "error": "Sin permiso."}, status=403)
        if not _get_base_empresa(request):
            return JsonResponse({"results": [], "error": "Sin empresa activa."}, status=400)
        q = (request.GET.get("q") or "").strip()
        try:
            limit = min(50, max(1, int(request.GET.get("limit") or 15)))
        except ValueError:
            limit = 15
        results = buscar_skus_best_componentes(
            q, limit=limit, base_empresa=_get_base_empresa(request)
        )
        return JsonResponse({"results": results})


class MigracionBestValidarArticuloFabricadoView(MprLoginRequiredMixin, View):
    """POST fabricados: asignar SKU BEST, aceptar sugerencia, descartar, reabrir."""

    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        wants_json = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in (request.headers.get("Accept") or "")
        )
        redirect_to = "mpr:migracion_best_articulos_fabricados"
        if not base:
            if wants_json:
                return JsonResponse({"ok": False, "error": "Sin empresa activa."}, status=400)
            return redirect("core:dashboard")

        best_id = (request.POST.get("best_id_articulo") or "").strip()
        accion = (request.POST.get("accion") or "").strip()
        notas = (request.POST.get("notas") or "").strip()
        usuario = _usuario_label(request)

        def _json_ok(payload: dict):
            return JsonResponse({"ok": True, **payload})

        def _json_err(msg: str, status: int = 400):
            return JsonResponse({"ok": False, "error": str(msg)}, status=status)

        try:
            if accion == "aceptar_seleccion":
                ids = [x.strip() for x in request.POST.getlist("sel") if (x or "").strip()]
                if not ids:
                    raise ValueError("Seleccioná al menos una fila pendiente.")
                aceptados = omitidos = 0
                for clave in ids:
                    try:
                        obj = BestArticuloMap.objects.get(
                            base_empresa=base,
                            best_id_articulo=clave,
                            origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
                        )
                        if obj.estado in (
                            BestArticuloMap.Estado.VALIDADO,
                            BestArticuloMap.Estado.DESCARTADO,
                        ):
                            omitidos += 1
                            continue
                        if not obj.admin_idart:
                            omitidos += 1
                            continue
                        validar_articulo_fabricado(
                            base_empresa=base,
                            best_id=obj.best_id_articulo,
                            admin_idart=obj.admin_idart,
                            usuario=usuario,
                            notas=obj.notas or "",
                        )
                        aceptados += 1
                    except (BestArticuloMap.DoesNotExist, ValueError):
                        omitidos += 1
                messages.success(
                    request,
                    f"Aceptados {aceptados} fabricados seleccionados ({omitidos} omitidos).",
                )
                return redirect(redirect_to)
            if accion == "aceptar":
                obj = BestArticuloMap.objects.get(
                    base_empresa=base,
                    best_id_articulo=best_id,
                    origen_requerimiento=BestArticuloMap.OrigenRequerimiento.BOM_FABRICADO,
                )
                validar_articulo_fabricado(
                    base_empresa=base,
                    best_id=obj.best_id_articulo,
                    admin_idart=obj.admin_idart,
                    usuario=usuario,
                    notas=notas or obj.notas or "",
                )
                if wants_json:
                    return _json_ok({"best_id": best_id, "accion": "aceptar"})
                messages.success(request, f"Validado {obj.best_id_articulo} con componente Admin.")
            elif accion == "asignar":
                raw = (request.POST.get("admin_idart") or "").strip()
                if not raw.isdigit():
                    raise ValueError("IDArt inválido.")
                obj = asignar_admin_a_fabricado_pp(
                    base_empresa=base,
                    best_id=best_id,
                    nuevo_admin_idart=int(raw),
                    usuario=usuario,
                    notas=notas,
                )
                if wants_json:
                    return _json_ok(
                        {
                            "best_id": obj.best_id_articulo,
                            "accion": "asignar",
                            "admin_idart": obj.admin_idart,
                        }
                    )
                messages.success(
                    request,
                    f"Asignado PP BEST {obj.best_id_articulo} → componente IDArt {obj.admin_idart}.",
                )
            elif accion == "descartar":
                descartar_articulo(
                    base_empresa=base, best_id=best_id, usuario=usuario, notas=notas
                )
                if wants_json:
                    return _json_ok({"best_id": best_id, "accion": "descartar"})
                messages.success(request, f"Descartado {best_id} (no se migrará).")
            elif accion == "reabrir":
                reabrir_articulo(
                    base_empresa=base, best_id=best_id, usuario=usuario, notas=notas
                )
                if wants_json:
                    return _json_ok({"best_id": best_id, "accion": "reabrir"})
                messages.success(
                    request,
                    f"Mapeo de {best_id} reabierto: podés asignar otro SKU BEST.",
                )
            else:
                raise ValueError("Acción no reconocida.")
        except BestArticuloMap.DoesNotExist:
            if wants_json:
                return _json_err("No existe ese SKU en el mapeo.", 404)
            messages.error(request, "No existe ese SKU en el mapeo.")
        except Exception as exc:
            if wants_json:
                return _json_err(str(exc))
            messages.error(request, str(exc))
        return redirect(redirect_to)


class MigracionBestConfirmarUnidadesView(MprLoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        ok = request.POST.get("ok") == "1"
        marcar_unidades_ok(base, ok=ok)
        if ok:
            messages.success(
                request,
                "Unidades confirmadas: las cantidades BEST se interpretan en pares.",
            )
        else:
            messages.warning(request, "Se revirtió la confirmación de unidades.")
        return redirect("mpr:migracion_best_hub")


class MigracionBestPedidosGateView(MprLoginRequiredMixin, TemplateView):
    """Pantalla de migración de pedidos: gate de paridad + ensayo/confirmación."""

    template_name = "mpr/best_migration/pedidos_gate.html"

    def dispatch(self, request, *args, **kwargs):
        if not _usuario_tiene_permiso_mpr(request.user, "mpr.ver"):
            messages.error(request, "No tenés permiso.")
            return redirect("mpr:tablero_produccion")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        if not _require_base(request):
            return redirect("core:dashboard")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        base = _get_base_empresa(self.request)
        hub = hub_context(base)
        ctx.update(hub)
        ctx["base_empresa"] = base
        return ctx


class MigracionBestMigrarPedidosView(MprLoginRequiredMixin, View):
    """POST: ensayo o confirmación de siembra PED desde pedidos abiertos BEST."""

    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        confirmar = request.POST.get("confirmar") == "1"
        session_user = request.session.get("user") or {}
        id_usuario = session_user.get("id_usuario")
        id_pv = session_user.get("id_punto_venta") or 1
        try:
            result = migrar_pedidos_best(
                base,
                dry_run=not confirmar,
                id_usuario=id_usuario,
                id_pv=id_pv,
            )
            if result.get("dry_run"):
                gate_txt = (
                    "Gate abierto."
                    if result.get("gate_ok")
                    else "Gate cerrado: la confirmación seguirá bloqueada."
                )
                messages.info(
                    request,
                    f"Ensayo (sin escribir): {result['ordenes_migrables']} órdenes migrables "
                    f"({result['lineas_ok']} líneas), {result['ordenes_omitidas']} omitidas, "
                    f"{result['lineas_huerfanas']} líneas huérfanas. {gate_txt}",
                )
                huerfanos = result.get("huerfanos_detalle") or []
                if huerfanos:
                    muestra = "; ".join(
                        f"{h.get('orden')}: {h.get('detalle')}" for h in huerfanos[:5]
                    )
                    messages.warning(
                        request,
                        f"Huérfanos (muestra): {muestra}"
                        + ("…" if len(huerfanos) > 5 else ""),
                    )
            else:
                msg = (
                    f"Siembra confirmada: {result['pedidos_escritos']} PED escritos; "
                    f"{result['pedidos_omitidos_existentes']} omitidos (en producción); "
                    f"{result['ordenes_omitidas']} órdenes sin mapeo completo."
                )
                post_ok = result.get("post_actualizar_ok")
                if post_ok is True:
                    msg += f" Demanda MPR actualizada: {result.get('post_actualizar_mensaje') or 'OK'}."
                elif post_ok is False:
                    msg += (
                        f" Advertencia post-actualizar: "
                        f"{result.get('post_actualizar_mensaje') or 'error'}."
                    )
                if result.get("errores"):
                    messages.warning(
                        request,
                        msg + " Detalle: " + " | ".join(result["errores"][:3]),
                    )
                else:
                    messages.success(request, msg)
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            logger.exception("Error migrando pedidos BEST")
            messages.error(request, f"No se pudo migrar pedidos BEST: {exc}")
        return redirect("mpr:migracion_best_pedidos")


class MigracionBestCargarStockReservaView(MprLoginRequiredMixin, View):
    """POST: ensayo o confirmación MCSS BEST → articulo.stock_reserva."""

    def post(self, request, *args, **kwargs):
        base = _require_base(request)
        if not base:
            return redirect("core:dashboard")
        confirmar = request.POST.get("confirmar") == "1"
        session_user = request.session.get("user") or {}
        id_usuario = session_user.get("id_usuario")
        try:
            result = migrar_stock_reserva_best(
                base,
                dry_run=not confirmar,
                id_usuario=id_usuario if confirmar else None,
            )
            if result.get("dry_run"):
                messages.info(
                    request,
                    f"Ensayo stock de seguridad: {result.get('con_mcss', 0)} con MCSS>0; "
                    f"{result.get('mapeados', 0)} mapeados; "
                    f"{result.get('actualizados', 0)} a actualizar; "
                    f"{result.get('huerfanos', 0)} huérfanos sin mapa.",
                )
            else:
                msg = (
                    f"Stock de seguridad cargado: {result.get('actualizados', 0)} artículos "
                    f"actualizados ({result.get('sin_cambio', 0)} sin cambio; "
                    f"{result.get('huerfanos', 0)} huérfanos)."
                )
                post_ok = result.get("post_actualizar_ok")
                if post_ok is True:
                    msg += " Demanda MPR actualizada."
                elif post_ok is False:
                    msg += (
                        f" Advertencia post-actualizar: "
                        f"{result.get('post_actualizar_mensaje') or 'error'}."
                    )
                if result.get("errores"):
                    messages.warning(
                        request,
                        msg + " Detalle: " + " | ".join(result["errores"][:3]),
                    )
                else:
                    messages.success(request, msg)
        except ValueError as exc:
            messages.error(request, str(exc))
        except Exception as exc:
            logger.exception("Error cargando stock_reserva BEST")
            messages.error(request, f"No se pudo cargar stock de seguridad: {exc}")
        return redirect("mpr:migracion_best_hub")
