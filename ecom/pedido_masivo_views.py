"""Vista HTML + APIs — pedido masivo por sucursales (Phase 4)."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterator

from django.http import HttpResponse, StreamingHttpResponse
from django.urls import reverse
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.request import Request
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_int_or_none
from ecom.catalogo_producto_relay_views import _session_base_empresa
from ecom.models import EcomPedidoMasivoDraft
from ecom.pedido_masivo_stub_views import _StubMayoristappPermisoView
from ecom.permissions import (
    EcomPedidoCapturaPermission,
    usuario_puede_matriz_multi_columna,
)

from ecom.services.pedido_masivo_matriz import (
    anular_borrador_masivo_usuario,
    buscar_articulos_filtrados_ternas,
    cod_viajante_sesion,
    credito_cliente_masivo,
    eliminar_fila_articulo,
    guardar_celda,
    guardar_descuento_fila,
    guardar_descuento_pie,
    guardar_precio_fila,
    recalcular_precios_fila_desde_lista,
    listar_clientes_con_ternas,
    listar_sucursales_cliente,
    obtener_o_crear_draft,
    serializar_matriz,
)
from ecom.services.pedido_masivo_import import (
    generar_plantilla_excel,
    importar_matriz_excel,
    nombre_archivo_plantilla,
)
from ecom.services.pedido_cabecera_relay import (
    cabecera_pedido_relay,
    puede_anular_pedido_relay,
)
from ecom.services.pedidos_hub_pipeline import url_pedido_masivo_modo_simple
from ecom.services.pedido_plantilla_service import cargar_pedido_en_draft_masivo
from ecom.services.batch_checkout_masivo import (
    calcular_totales_lote_masivo,
    confirmar_lote_masivo,
    confirmar_lote_masivo_stream,
)
from ecom.checkout_relay_views import (
    _session_agente_percep,
    _session_dias_no_laborables,
    _session_pv,
)
from ecom.services.pedido_cabecera_comercial import (
    cabecera_defaults_json,
    flags_edicion_desde_sesion,
    parsear_cabecera_desde_body,
    resolver_cabecera_comercial,
)
from ecom.services.ecom_config_mysql import aprobacion_pedidos_activa
from ecom.services.vendedor_operativo import ctx_desde_request


def _sess_user(request) -> Dict[str, Any]:
    return (getattr(request, "session", None) or {}).get("user") or {}


def _err(msg: str, code: str = "error", status: int = 400) -> Response:
    return Response({"ok": False, "error": msg, "code": code}, status=status)


def _flags_cabecera_masivo(request) -> Dict[str, bool]:
    ctx = ctx_desde_request(request)
    sess = _sess_user(request)
    base = _session_base_empresa(request) or ""
    return flags_edicion_desde_sesion(
        ctx,
        base_empresa=base,
        id_puesto=to_int_or_none(sess.get("id_puesto")),
    )


def _cabecera_json_masivo(request, id_cliente: int, fecha_entrega=None) -> Dict[str, Any]:
    flags = _flags_cabecera_masivo(request)
    bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
    dias_ent = to_int_or_none(bag.get("cant_dias_entrega")) or 0
    return cabecera_defaults_json(
        _session_base_empresa(request) or "",
        id_cliente,
        es_supervisor=flags["es_supervisor"],
        dias_entrega=int(dias_ent),
        dias_no_laborables=_session_dias_no_laborables(request),
        fecha_entrega=fecha_entrega,
        prellenar_entrega_desde_vencimiento=fecha_entrega is None,
        flags=flags,
    )


class _NdjsonAcceptRenderer(BaseRenderer):
    """Declara NDJSON para que DRF negocie la respuesta streaming correctamente."""

    media_type = "application/x-ndjson"
    format = "ndjson"
    charset = "utf-8"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b""
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
        return json.dumps(data, ensure_ascii=False).encode("utf-8")


def _serializar_matriz_ui(draft: EcomPedidoMasivoDraft, base: str) -> Dict[str, Any]:
    """Matriz serializada + widget de crédito del cliente en modo simple.

    Si hay ``cod_mov_origen``, adjunta estado actual del PED y si aún se puede
    anular (solo Pendiente). Evita ofrecer «Anular y crear nuevo» cuando el
    origen ya avanzó (p. ej. En preparación).
    """
    from ecom.services.pedido_cabecera_relay import (
        cabecera_pedido_relay,
        puede_anular_pedido_relay,
    )

    matriz = serializar_matriz(draft, base)
    if matriz.get("modo") == EcomPedidoMasivoDraft.MODO_SIMPLE:
        matriz["credito"] = credito_cliente_masivo(base, draft.id_cliente)

    cod_origen = to_int_or_none(getattr(draft, "cod_mov_origen", None))
    origen: Dict[str, Any] = {
        "cod_mov": cod_origen,
        "nro_comprobante": "",
        "estado": "",
        "anulado": "",
        "puede_anular": False,
        "editable": False,
    }
    if cod_origen is not None:
        cab = cabecera_pedido_relay(base, cod_origen) or {}
        puede_anular, _msg = puede_anular_pedido_relay(base, cod_origen)
        estado = str(cab.get("estado") or "").strip()
        anulado = str(cab.get("anulado") or "").strip()
        origen.update(
            {
                "nro_comprobante": str(cab.get("nro_comprobante") or "").strip(),
                "estado": estado,
                "anulado": anulado,
                "puede_anular": bool(puede_anular),
                # Paridad con _pedido_origen_editable: solo Pendiente no anulado.
                "editable": bool(puede_anular),
            }
        )
        # No dejar basura en columna Borrador del hub si el PED ya avanzó.
        if not puede_anular and draft.estado in (
            EcomPedidoMasivoDraft.ESTADO_BORRADOR,
            EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
        ):
            draft.estado = EcomPedidoMasivoDraft.ESTADO_ARCHIVADO
            draft.save(update_fields=["estado", "updated_at"])
            matriz["estado"] = draft.estado
    matriz["origen_pedido"] = origen

    return matriz


def _resolver_cabecera_masivo(
    request,
    draft: EcomPedidoMasivoDraft,
    data: Dict[str, Any],
) -> tuple:
    """Resuelve cabecera comercial del body para preview/confirmar masivo."""
    flags = _flags_cabecera_masivo(request)
    bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
    dias_ent = to_int_or_none(data.get("dias_entrega")) or to_int_or_none(
        bag.get("cant_dias_entrega")
    ) or 0
    parsed = parsear_cabecera_desde_body(data)
    return resolver_cabecera_comercial(
        draft.base_empresa,
        draft.id_cliente,
        es_supervisor=flags["es_supervisor"],
        fecha_pedido=parsed.get("fecha_pedido"),
        fecha_entrega=parsed.get("fecha_entrega"),
        vencimiento=parsed.get("vencimiento"),
        id_condventa=parsed.get("id_condventa"),
        lista_id=parsed.get("lista_id"),
        dias_entrega=int(dias_ent),
        dias_no_laborables=_session_dias_no_laborables(request),
        tipo_comprobante="PED",
        puede_editar_lista=flags["puede_editar_lista"],
        puede_editar_condicion=flags["puede_editar_condicion"],
    )


class PedidoMasivoSucursalesView(_StubMayoristappPermisoView):
    """Matriz packs × sucursales — ``/ecom/mayoristapp/pedido-masivo-sucursales/``."""

    template_name = "ecom/pedido_masivo_sucursales.html"
    # Captura de pedidos: simple (``ecom.pedidos.crear``) o masivo
    # (``ecom.pedido_masivo.usar``). La matriz multi-columna se restringe en el
    # backend a ``ecom.pedido_masivo.usar`` (ver ``PedidoMasivoAbrirAPIView``).
    permiso_requerido = ""
    permisos_or = ("ecom.pedidos.crear", "ecom.pedido_masivo.usar")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        draft_q = to_int_or_none(self.request.GET.get("draft"))
        modo_q = (self.request.GET.get("modo") or "").strip().lower()
        if modo_q not in (
            EcomPedidoMasivoDraft.MODO_SIMPLE,
            EcomPedidoMasivoDraft.MODO_MASIVO,
        ):
            modo_q = ""
        cod_mov_q = to_int_or_none(self.request.GET.get("cod_mov"))
        id_domicilio_q = to_int_or_none(self.request.GET.get("id_domicilio"))
        repetir_q = (self.request.GET.get("repetir") or "").strip().lower() in (
            "1",
            "true",
            "si",
            "sí",
        )
        readonly_q = (self.request.GET.get("readonly") or "").strip().lower() in (
            "1",
            "true",
            "si",
            "sí",
        )
        consulta_q = (self.request.GET.get("consulta") or "").strip().lower() in (
            "1",
            "true",
            "si",
            "sí",
        )
        # Solo el iframe del resumen de lote pide marco embebido (sin navbar/pie).
        # ``readonly=1`` desde el hub abre consulta a pantalla completa como un PED.
        embed_q = (self.request.GET.get("embed") or "").strip().lower() in (
            "1",
            "true",
            "si",
            "sí",
        )
        base_sess = str((self.request.session.get("user") or {}).get("base_empresa") or "")
        # PDF de pedido: plantilla con ``/0/`` para reemplazar el cod_mov en el FE.
        pdf_tpl = reverse("ecom:mayoristapp_pedido_pdf", args=[0])
        ctx.update(
            {
                "draft_id_inicial": draft_q,
                # Embebido en iframe del resumen de lote: sin navbar/footer de base_app.
                "pm_embed": embed_q,
                "bootstrap": {
                    "draft_id": draft_q,
                    "modo": modo_q or None,
                    "cod_mov": cod_mov_q,
                    "id_domicilio": id_domicilio_q,
                    "repetir": repetir_q,
                    "readonly": readonly_q,
                    "consulta": consulta_q,
                    "aprobacion_pedidos_activa": aprobacion_pedidos_activa(base_sess),
                    "urls": {
                        "hub": reverse("ecom:mayoristapp_pedidos_hub"),
                        "nuevo_simple": url_pedido_masivo_modo_simple(),
                        "resumen_lote_tpl": reverse(
                            "ecom:mayoristapp_lote_resumen", kwargs={"draft_id": 0}
                        ).replace("/0/", "/{draft_id}/"),
                        "nuevo_masivo": reverse(
                            "ecom:mayoristapp_pedido_masivo_sucursales"
                        ),
                        "clientes": reverse("ecom:api_pedido_masivo_clientes"),
                        "abrir": reverse("ecom:api_pedido_masivo_abrir"),
                        "abrir_pedido": reverse("ecom:api_pedido_masivo_abrir_pedido"),
                        "matriz": reverse("ecom:api_pedido_masivo_matriz"),
                        "celda": reverse("ecom:api_pedido_masivo_celda"),
                        "eliminar_fila": reverse("ecom:api_pedido_masivo_eliminar_fila"),
                        "articulos": reverse("ecom:api_pedido_masivo_articulos"),
                        "sucursales": reverse("ecom:api_pedido_masivo_sucursales"),
                        "preview": reverse("ecom:api_pedido_masivo_preview"),
                        "descuento_fila": reverse("ecom:api_pedido_masivo_descuento_fila"),
                        "descuento_pie": reverse("ecom:api_pedido_masivo_descuento_pie"),
                        "precio_fila": reverse("ecom:api_pedido_masivo_precio_fila"),
                        "recalcular_precios": reverse(
                            "ecom:api_pedido_masivo_recalcular_precios"
                        ),
                        "confirmar": reverse("ecom:api_pedido_masivo_confirmar"),
                        "anular": reverse("ecom:api_pedido_masivo_anular"),
                        "importar": reverse("ecom:api_pedido_masivo_importar"),
                        "plantilla_excel": reverse(
                            "ecom:api_pedido_masivo_plantilla_excel"
                        ),
                        # Acciones hero PED (reutilizan APIs mayoristas existentes).
                        "mail_enqueue": reverse(
                            "ecom:mayoristapp_comprobantes_comprobante_a_mail_enqueue"
                        )
                        + "?ajax=1",
                        "anular_pedido": reverse(
                            "ecom:mayoristapp_comprobantes_anular_pedido"
                        ),
                        "pdf_tpl": pdf_tpl,
                        "vendedores_cartera": reverse("ecom:mayoristapp_vendedores_cartera"),
                        "vendedor_operativo": reverse("ecom:mayoristapp_vendedor_operativo"),
                        "carrito_vaciar": reverse("ecom:mayoristapp_carrito_vaciar"),
                        "lista_precio": reverse("ecom:mayoristapp_precios_lista_precio"),
                        "condiciones_venta": reverse("ecom:mayoristapp_precios_condiciones_venta"),
                    },
                },
            }
        )
        return ctx


class PedidoMasivoConfirmarAPIView(APIView):
    """POST confirma el lote (1 PED por sucursal) con compensación ante fallo."""

    permission_classes = [EcomPedidoCapturaPermission]
    renderer_classes = [JSONRenderer, _NdjsonAcceptRenderer]

    def _params_confirmar(
        self, request: Request, draft: EcomPedidoMasivoDraft, data: Dict[str, Any]
    ) -> tuple:
        """Resuelve kwargs comunes para confirmación sync o stream."""
        sess = _sess_user(request)
        try:
            pv = to_int_or_none(data.get("id_punto_venta")) or _session_pv(request)
        except Exception:
            return None, _err(
                "No se pudo resolver el punto de venta para confirmar el pedido.",
                "error_resolucion_pv",
            )
        if pv is None:
            return None, _err(
                "No hay punto de venta configurado para la empresa o el usuario.",
                "sin_pv",
            )

        id_dep = to_int_or_none(data.get("id_deposito")) or to_int_or_none(
            sess.get("id_deposito")
        ) or 1
        cv = cod_viajante_sesion(sess)

        flags = _flags_cabecera_masivo(request)
        desc_pie = data.get("desc_pie_pct")
        if desc_pie is not None and flags["puede_editar_descuento_pie"]:
            guardar_descuento_pie(draft, desc_pie_pct=desc_pie)

        cabecera, err_cab = _resolver_cabecera_masivo(request, draft, data)
        if not cabecera:
            return None, _err(err_cab or "Cabecera comercial inválida.")

        es_sup = flags["es_supervisor"]
        bag = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
        dias_ent = to_int_or_none(data.get("dias_entrega")) or to_int_or_none(
            bag.get("cant_dias_entrega")
        ) or 0

        kwargs = dict(
            id_usuario=to_int_or_none(sess.get("id_usuario")),
            id_punto_venta=int(pv),
            cod_viajante=cv,
            lista_id=int(cabecera.lista_id),
            id_deposito=int(id_dep),
            desc_pie_pct=desc_pie,
            forma_entrega=str(data.get("forma_entrega") or ""),
            observaciones=str(data.get("observaciones") or ""),
            agente_percep=_session_agente_percep(request),
            sess_user=sess,
            cabecera=cabecera,
            es_supervisor=es_sup,
            dias_entrega=int(dias_ent),
            dias_no_laborables=_session_dias_no_laborables(request),
        )
        return kwargs, None

    def _stream_ndjson(
        self,
        draft: EcomPedidoMasivoDraft,
        base: str,
        kwargs: Dict[str, Any],
    ) -> Iterator[str]:
        try:
            for ev in confirmar_lote_masivo_stream(draft, **kwargs):
                if ev.get("event") == "fin":
                    draft.refresh_from_db()
                    ev = dict(ev)
                    ev["matriz"] = _serializar_matriz_ui(draft, base)
                    ev["draft_id"] = draft.pk
                    ev["estado_aprobacion_lote"] = draft.estado_aprobacion_lote
                yield json.dumps(ev, ensure_ascii=False) + "\n"
        except Exception as exc:
            draft.refresh_from_db()
            fin = {
                "event": "fin",
                "ok": False,
                "message": str(exc),
                "errores": {"_lote": str(exc)},
                "codigos_movimiento": [],
                "compensacion": [],
                "matriz": _serializar_matriz_ui(draft, base),
            }
            yield json.dumps(fin, ensure_ascii=False) + "\n"

    def post(self, request: Request):
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id o usuario.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)

        kwargs, err_resp = self._params_confirmar(request, draft, data)
        if err_resp is not None:
            return err_resp

        if data.get("stream"):
            response = StreamingHttpResponse(
                self._stream_ndjson(draft, base, kwargs),
                content_type="application/x-ndjson; charset=utf-8",
            )
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"
            return response

        ok, msg, payload = confirmar_lote_masivo(draft, **kwargs)
        draft.refresh_from_db()
        body = {
            "ok": ok,
            "message": msg,
            "matriz": _serializar_matriz_ui(draft, base),
            "draft_id": draft.pk,
            "estado_aprobacion_lote": draft.estado_aprobacion_lote,
            **(payload or {}),
        }
        if not ok:
            return Response(body, status=409)
        return Response(body)


class PedidoMasivoClientesAPIView(APIView):
    permission_classes = [EcomPedidoCapturaPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        cv = cod_viajante_sesion(sess)
        if cv is None:
            return _err("No se resolvió el viajante de sesión.", "sin_viajante")
        rows = listar_clientes_con_ternas(
            base,
            cv,
            q=str(request.query_params.get("q") or ""),
            limit=to_int_or_none(request.query_params.get("limit")) or 40,
        )
        return Response({"ok": True, "items": rows, "CodViajante": cv})


class PedidoMasivoSucursalesAPIView(APIView):
    permission_classes = [EcomPedidoCapturaPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        idc = to_int_or_none(request.query_params.get("id_cliente"))
        if idc is None:
            return _err("Falta id_cliente.")
        cv = cod_viajante_sesion(sess)
        return Response(
            {
                "ok": True,
                "sucursales": listar_sucursales_cliente(base, idc, cod_viajante=cv),
            }
        )


class PedidoMasivoAbrirAPIView(APIView):
    """POST crea/recupera borrador y devuelve matriz serializada."""

    permission_classes = [EcomPedidoCapturaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        id_u = to_int_or_none(sess.get("id_usuario"))
        data = request.data if isinstance(request.data, dict) else {}
        idc = to_int_or_none(data.get("id_cliente"))
        draft_id = to_int_or_none(data.get("draft_id"))
        cv = cod_viajante_sesion(sess)
        modo = (str(data.get("modo") or "")).strip().lower()
        if modo not in (
            EcomPedidoMasivoDraft.MODO_SIMPLE,
            EcomPedidoMasivoDraft.MODO_MASIVO,
        ):
            modo = EcomPedidoMasivoDraft.MODO_MASIVO
        id_domicilio = to_int_or_none(data.get("id_domicilio"))
        solo_lectura = bool(data.get("readonly") or data.get("solo_lectura"))
        if id_u is None:
            return _err("Sin usuario en sesión.")
        if draft_id is None and idc is None:
            return _err("Indicá id_cliente o draft_id.")

        # La matriz multi-columna (modo masivo) exige ``ecom.pedido_masivo.usar``.
        if modo != EcomPedidoMasivoDraft.MODO_SIMPLE and not usuario_puede_matriz_multi_columna(
            request
        ):
            return _err(
                "Se requiere permiso ecom.pedido_masivo.usar para el pedido masivo "
                "multi-sucursal.",
                "sin_permiso_masivo",
                403,
            )

        if draft_id is not None and idc is None:
            d0 = EcomPedidoMasivoDraft.objects.filter(
                pk=draft_id, base_empresa=base, id_usuario=id_u
            ).first()
            if not d0:
                return _err("Borrador no encontrado.", "no_encontrado", 404)
            idc = d0.id_cliente
            # Si el draft es masivo, respetar su modo (evita forzar masivo por default).
            if (d0.modo or "").strip().lower() in (
                EcomPedidoMasivoDraft.MODO_SIMPLE,
                EcomPedidoMasivoDraft.MODO_MASIVO,
            ):
                modo = (d0.modo or "").strip().lower()

        # Modo simple sin domicilio explícito: solo se infiere cuando el cliente
        # tiene un único domicilio operativo. Con varios, la UI debe pedirlo.
        if (
            modo == EcomPedidoMasivoDraft.MODO_SIMPLE
            and id_domicilio is None
            and draft_id is None
            and idc is not None
        ):
            sucs = listar_sucursales_cliente(base, idc, cod_viajante=cv)
            if not sucs:
                return _err(
                    "Este cliente no tiene sucursales activas.",
                    "sin_sucursales",
                    400,
                )
            if len(sucs) == 1:
                id_domicilio = to_int_or_none(sucs[0].get("id_cliente_domicilio"))
            else:
                return Response(
                    {
                        "ok": False,
                        "error": "Elegí la sucursal del pedido.",
                        "code": "requiere_sucursal",
                        "sucursales": sucs,
                    },
                    status=400,
                )

        draft, err = obtener_o_crear_draft(
            base_empresa=base,
            id_usuario=id_u,
            id_cliente=idc,
            cod_viajante=cv,
            draft_id=draft_id,
            modo=modo,
            id_domicilio_fijo=id_domicilio,
            solo_lectura=solo_lectura,
        )
        if not draft:
            return _err(err or "No se pudo abrir el borrador.")
        matriz = _serializar_matriz_ui(draft, base)
        matriz["cabecera"] = _cabecera_json_masivo(request, draft.id_cliente)
        return Response({"ok": True, "matriz": matriz})


class PedidoMasivoAbrirPedidoAPIView(APIView):
    """POST carga un PED (``cod_mov``) en un borrador simple, o lo repite.

    - ``repetir=false`` (default): mantiene ``cod_mov_origen`` → al confirmar se
      anula el origen y se crea un PED nuevo (paridad REQ-VTA-04 / REQ-PSU-06).
    - ``repetir=true``: copia las celdas a un borrador nuevo SIN ``cod_mov_origen``
      (no toca EcomCart) → al confirmar se genera un PED nuevo (REQ-PSU-07/CAR-008).
    """

    permission_classes = [EcomPedidoCapturaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        id_u = to_int_or_none(sess.get("id_usuario"))
        if id_u is None:
            return _err("Sin usuario en sesión.")
        data = request.data if isinstance(request.data, dict) else {}
        cod_mov = to_int_or_none(data.get("cod_mov"))
        if cod_mov is None:
            return _err("Falta cod_mov del pedido.")
        repetir = bool(data.get("repetir"))
        consulta = bool(data.get("consulta"))
        draft_id = to_int_or_none(data.get("draft_id"))

        draft, err, meta = cargar_pedido_en_draft_masivo(
            base,
            cod_mov,
            sess,
            id_usuario=id_u,
            draft_id=None if repetir else draft_id,
            consulta=consulta,
        )
        if err or draft is None:
            return _err(err or "No se pudo cargar el pedido.")

        # Repetir: borrador nuevo sin vínculo al PED origen (crea, no anula+crea).
        if repetir and draft.cod_mov_origen is not None:
            draft.cod_mov_origen = None
            draft.save(update_fields=["cod_mov_origen", "updated_at"])
            meta = dict(meta or {})
            meta["cod_mov_origen"] = None
            meta["editable"] = True

        cab = cabecera_pedido_relay(base, cod_mov) or {}
        puede_anular = False
        if not repetir and not consulta:
            puede_anular, _msg_anular = puede_anular_pedido_relay(base, cod_mov)

        matriz = _serializar_matriz_ui(draft, base)
        fecha_ent_existente = None if repetir else cab.get("fecha_entrega_iso")
        matriz["cabecera"] = _cabecera_json_masivo(
            request, draft.id_cliente, fecha_entrega=fecha_ent_existente
        )
        pedido_info = {
            "cod_mov": None if repetir else cod_mov,
            "nro_comprobante": str(cab.get("nro_comprobante") or "").strip(),
            "estado": str(cab.get("estado") or "").strip(),
            "anulado": str(cab.get("anulado") or "").strip(),
            "email_cliente": str(cab.get("email_cliente") or "").strip(),
            "editable": False if consulta else bool(meta.get("editable")),
            "puede_anular": False if consulta else bool(puede_anular),
            "repetido": repetir,
            "consulta": consulta,
        }
        return Response(
            {
                "ok": True,
                "matriz": matriz,
                "pedido": pedido_info,
                "advertencias": list(meta.get("advertencias") or []),
            }
        )


class PedidoMasivoMatrizAPIView(APIView):
    permission_classes = [EcomPedidoCapturaPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        draft_id = to_int_or_none(request.query_params.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        return Response({"ok": True, "matriz": _serializar_matriz_ui(draft, base)})


class PedidoMasivoCeldaAPIView(APIView):
    """POST autoguardado de una celda."""

    permission_classes = [EcomPedidoCapturaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id,
            base_empresa=base,
            id_usuario=id_u,
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        ok, msg, payload = guardar_celda(
            draft,
            id_articulo=to_int_or_none(data.get("id_articulo")),
            id_cliente_domicilio=to_int_or_none(data.get("id_cliente_domicilio")),
            cantidad_packs=data.get("cantidad_packs"),
        )
        if not ok:
            resp: Dict[str, Any] = {
                "ok": False,
                "error": msg,
                "code": (payload or {}).get("code", "error"),
            }
            if payload and payload.get("multiplo_empaque") is not None:
                resp["multiplo_empaque"] = payload["multiplo_empaque"]
            return Response(resp, status=400)
        return Response({"ok": True, "message": msg, "celda": payload})


class PedidoMasivoEliminarFilaAPIView(APIView):
    """POST quita un artículo (todas las celdas + desc. fila) del borrador."""

    permission_classes = [EcomPedidoCapturaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id,
            base_empresa=base,
            id_usuario=id_u,
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        ok, msg = eliminar_fila_articulo(
            draft, id_articulo=to_int_or_none(data.get("id_articulo"))
        )
        if not ok:
            return _err(msg)
        return Response(
            {
                "ok": True,
                "message": msg,
                "matriz": _serializar_matriz_ui(draft, base),
            }
        )


class PedidoMasivoArticulosAPIView(APIView):
    permission_classes = [EcomPedidoCapturaPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        cv = cod_viajante_sesion(sess)
        idc = to_int_or_none(request.query_params.get("id_cliente"))
        if cv is None or idc is None:
            return _err("Se requieren viajante e id_cliente.")
        lista_id = to_int_or_none(request.query_params.get("lista_id")) or 1
        id_dep = to_int_or_none(request.query_params.get("id_deposito")) or 1
        todos_raw = str(request.query_params.get("todos") or "").strip().lower()
        listar_todos = todos_raw in ("1", "true", "si", "sí", "yes")
        tam_default = 5000 if listar_todos else 20
        result = buscar_articulos_filtrados_ternas(
            base,
            cod_viajante=cv,
            id_cliente=idc,
            id_cliente_domicilio=to_int_or_none(request.query_params.get("id_cliente_domicilio")),
            q=str(request.query_params.get("q") or ""),
            lista_id=lista_id,
            id_deposito=id_dep,
            pagina=to_int_or_none(request.query_params.get("pagina")) or 1,
            tam=to_int_or_none(request.query_params.get("tam")) or tam_default,
            listar_todos=listar_todos,
        )
        return Response({"ok": True, **result})


class PedidoMasivoPreviewAPIView(APIView):
    """POST preview agregado de totales del lote (REQ-MAS-10)."""

    permission_classes = [EcomPedidoCapturaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id o usuario.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)

        flags = _flags_cabecera_masivo(request)
        desc_pie = data.get("desc_pie_pct")
        if desc_pie is not None and flags["puede_editar_descuento_pie"]:
            guardar_descuento_pie(draft, desc_pie_pct=desc_pie)

        cabecera, err_cab = _resolver_cabecera_masivo(request, draft, data)
        if not cabecera:
            return _err(err_cab or "Cabecera comercial inválida.")

        id_dep = to_int_or_none(data.get("id_deposito")) or to_int_or_none(
            sess.get("id_deposito")
        ) or 1

        preview = calcular_totales_lote_masivo(
            draft,
            id_usuario=id_u,
            desc_pie_pct=desc_pie,
            lista_id=cabecera.lista_id,
            id_deposito=int(id_dep),
            cabecera=cabecera,
        )
        body = {
            "ok": bool(preview.get("ok", True)),
            "matriz": _serializar_matriz_ui(draft, base),
            **preview,
        }
        if preview.get("warning"):
            body["warning"] = preview["warning"]
        if not body["ok"]:
            return Response(body, status=409)
        return Response(body)


class PedidoMasivoDescuentoFilaAPIView(APIView):
    """POST persiste % descuento por fila (artículo) en el borrador."""

    permission_classes = [EcomPedidoCapturaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        flags = _flags_cabecera_masivo(request)
        if not flags["puede_editar_descuento_renglon"]:
            return _err(
                "No tiene permiso para modificar el descuento de renglón.",
                "sin_permiso",
                403,
            )
        ok, msg = guardar_descuento_fila(
            draft,
            id_articulo=to_int_or_none(data.get("id_articulo")),
            porcentaje_descuento=data.get("porcentaje_descuento"),
        )
        if not ok:
            return _err(msg)
        return Response(
            {
                "ok": True,
                "message": msg,
                "matriz": _serializar_matriz_ui(draft, base),
            }
        )


class PedidoMasivoPrecioFilaAPIView(APIView):
    """POST persiste precio unitario neto por artículo en el borrador."""

    permission_classes = [EcomPedidoCapturaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        flags = _flags_cabecera_masivo(request)
        if not flags["puede_editar_precio_linea"]:
            return _err(
                "No tiene permiso para modificar el precio de la línea.",
                "sin_permiso",
                403,
            )
        ok, msg = guardar_precio_fila(
            draft,
            id_articulo=to_int_or_none(data.get("id_articulo")),
            precio_unitario_neto=data.get("precio_unitario_neto"),
        )
        if not ok:
            return _err(msg)
        return Response(
            {
                "ok": True,
                "message": msg,
                "matriz": _serializar_matriz_ui(draft, base),
            }
        )


class PedidoMasivoRecalcularPreciosAPIView(APIView):
    """POST reemplaza precios de línea con la lista de cabecera."""

    permission_classes = [EcomPedidoCapturaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        flags = _flags_cabecera_masivo(request)
        if not flags["puede_editar_lista"]:
            return _err(
                "No tiene permiso para cambiar la lista de precio.",
                "sin_permiso",
                403,
            )
        lista_id = to_int_or_none(data.get("lista_id"))
        ok, msg = recalcular_precios_fila_desde_lista(
            draft, base, lista_id=lista_id
        )
        if not ok:
            return _err(msg)
        return Response(
            {
                "ok": True,
                "message": msg,
                "matriz": _serializar_matriz_ui(draft, base),
            }
        )


class PedidoMasivoDescuentoPieAPIView(APIView):
    """POST persiste descuento pie de lote en el borrador."""

    permission_classes = [EcomPedidoCapturaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id.")
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        flags = _flags_cabecera_masivo(request)
        if not flags["puede_editar_descuento_pie"]:
            return _err(
                "No tiene permiso para modificar el descuento de pie.",
                "sin_permiso",
                403,
            )
        ok, msg = guardar_descuento_pie(
            draft,
            desc_pie_pct=data.get("desc_pie_pct"),
        )
        if not ok:
            return _err(msg)
        return Response(
            {
                "ok": True,
                "message": msg,
                "matriz": _serializar_matriz_ui(draft, base),
            }
        )


def _draft_usuario(request, draft_id: Any) -> Any:
    base = _session_base_empresa(request)
    sess = _sess_user(request)
    id_u = to_int_or_none(sess.get("id_usuario"))
    did = to_int_or_none(draft_id)
    if not base or did is None or id_u is None:
        return None, base
    draft = EcomPedidoMasivoDraft.objects.filter(
        pk=did, base_empresa=base, id_usuario=id_u
    ).first()
    return draft, base


class PedidoMasivoPlantillaExcelAPIView(APIView):
    """GET descarga la plantilla matriz del borrador (sucursales VCM)."""

    permission_classes = [EcomPedidoCapturaPermission]

    def get(self, request: Request):
        draft, _base = _draft_usuario(request, request.query_params.get("draft_id"))
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        raw = generar_plantilla_excel(draft)
        nombre = nombre_archivo_plantilla(draft)
        resp = HttpResponse(
            raw,
            content_type=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
        )
        resp["Content-Disposition"] = f'attachment; filename="{nombre}"'
        return resp


class PedidoMasivoImportarAPIView(APIView):
    """POST multipart: reemplaza el borrador con la matriz Excel (validación VCM)."""

    permission_classes = [EcomPedidoCapturaPermission]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if hasattr(request, "data") else {}
        draft, _b = _draft_usuario(request, data.get("draft_id"))
        if not draft:
            return _err("Borrador no encontrado.", "no_encontrado", 404)
        upload = request.FILES.get("archivo")
        if not upload:
            return _err("Falta el archivo Excel.", "sin_archivo")
        nombre = str(getattr(upload, "name", "") or "").lower()
        if not nombre.endswith((".xlsx", ".xlsm")):
            return _err("El archivo debe ser .xlsx.", "archivo_invalido")
        raw = upload.read()
        flags = _flags_cabecera_masivo(request)
        result = importar_matriz_excel(
            draft,
            raw,
            aplicar_precios=bool(flags.get("puede_editar_precio_linea")),
        )
        if not result.get("ok"):
            status = 409 if result.get("code") == "validacion" else 400
            return Response(
                {
                    "ok": False,
                    "error": result.get("error") or "No se pudo importar.",
                    "code": result.get("code") or "error",
                    "errores": result.get("errores") or [],
                    "errores_total": result.get("errores_total")
                    or len(result.get("errores") or []),
                },
                status=status,
            )
        draft.refresh_from_db()
        return Response(
            {
                "ok": True,
                "message": result.get("message"),
                "celdas": result.get("celdas"),
                "articulos": result.get("articulos"),
                "sucursales": result.get("sucursales"),
                "avisos": result.get("avisos") or [],
                "matriz": _serializar_matriz_ui(draft, base),
            }
        )


class PedidoMasivoAnularAPIView(APIView):
    """POST anula un borrador masivo en edición (recuperable desde hub)."""

    permission_classes = [EcomPedidoCapturaPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        sess = _sess_user(request)
        if not base:
            return _err("Sin base_empresa.", "sin_base_empresa")
        data = request.data if isinstance(request.data, dict) else {}
        draft_id = to_int_or_none(data.get("draft_id"))
        id_u = to_int_or_none(sess.get("id_usuario"))
        if draft_id is None or id_u is None:
            return _err("Falta draft_id o usuario.")
        ok, msg = anular_borrador_masivo_usuario(draft_id, id_u, base)
        if not ok:
            return _err(msg)
        draft = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id, base_empresa=base, id_usuario=id_u
        ).first()
        body: Dict[str, Any] = {"ok": True, "message": msg}
        if draft:
            body["matriz"] = _serializar_matriz_ui(draft, base)
        return Response(body)
