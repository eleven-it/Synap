"""
Relay catálogo rubro/subrubro (paridad mayoristapp relay-rubro.php).

GET con query ``ajax`` opcional (el PHP exige ``isset($_GET['ajax'])``; aceptamos
cualquier valor si el parámetro está presente, o omitimos en Synap si se prefiere
solo sesión — ver vistas).
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.catalogo_articulo import search_articulos_autocomplete
from core.utils.administranet_types import to_int_or_none

from ecom.services.catalogo_lotes import list_lotes_por_articulo_deposito
from ecom.services.catalogo_maestros import (
    list_laboratorios_catalogo_ecommerce,
    list_marcas_catalogo_ecommerce,
    list_proveedores_catalogo_ecommerce,
)
from ecom.services.catalogo_mas_vendidos import (
    list_mas_vendidos_ecommerce,
    parse_filtros_mas_vendidos,
    parse_limit_mas_vendidos,
)
from ecom.services.catalogo_tacc import tacc_relay_payload
from ecom.services.catalogo_rubro import (
    list_rubros_por_categoria,
    list_subrubros_maestro_por_rubro,
    list_subrubros_por_rubro,
    list_subrubros_por_rubro_y_tipo_cliente,
)
from ecom.services.mayoristapp_session import guardar_filtro_catalogo_rubro


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


class CatalogoRubrosRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/catalogo/rubros/?idcategoria=<int>&ajax=1
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-rubro.php)."},
                status=400,
            )

        raw_cat = request.query_params.get("idcategoria")
        if raw_cat is None or str(raw_cat).strip() == "":
            return Response({"detail": "idcategoria es obligatorio."}, status=400)
        try:
            id_categoria = int(raw_cat)
        except (TypeError, ValueError):
            return Response({"detail": "idcategoria debe ser entero."}, status=400)

        try:
            data = list_rubros_por_categoria(base, id_categoria)
        except Exception:
            return Response({"detail": "Error al consultar rubros."}, status=500)

        return Response(data)


class CatalogoSubrubrosRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/catalogo/subrubros/?idrubro=<int>&ajax=1
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-rubro.php)."},
                status=400,
            )

        raw_r = request.query_params.get("idrubro")
        if raw_r is None or str(raw_r).strip() == "":
            return Response({"detail": "idrubro es obligatorio."}, status=400)
        try:
            codigo_rubro = int(raw_r)
        except (TypeError, ValueError):
            return Response({"detail": "idrubro debe ser entero."}, status=400)

        try:
            data = list_subrubros_por_rubro(base, codigo_rubro)
        except Exception:
            return Response({"detail": "Error al consultar subrubros."}, status=500)

        return Response(data)


class CatalogoFiltroRubroCatalogoAPIView(APIView):
    """
    POST /ecom/api/mayoristapp/catalogo/filtro-rubro-catalogo/

    Paridad relay-rubro-catalogo.php (sesión ``buscaRubro`` / ``claseLista``).
    Cuerpo JSON o form: ``idr`` (código rubro u opción de filtro).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        if not _session_base_empresa(request):
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        idr = request.data.get("idr")
        if idr is None or str(idr).strip() == "":
            return Response({"detail": "idr es obligatorio."}, status=400)

        try:
            guardar_filtro_catalogo_rubro(request, idr)
        except Exception:
            return Response({"detail": "No se pudo guardar el filtro en sesión."}, status=500)

        return Response({"status": "ok"})


class CatalogoArticulosAutocompleteAPIView(APIView):
    """
    POST /ecom/api/mayoristapp/catalogo/articulos/autocomplete/

    Paridad ``buscarArticulosAutocomplete`` (relay-stock-existencias.php).
    Cuerpo: ``term``; opcional ``autocomplete=1`` (como el PHP).
    Respuesta: lista de ``{id, label, value}``.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        ac = request.data.get("autocomplete")
        if ac is None or str(ac) not in ("1", "true", "True"):
            return Response(
                {"detail": "Parámetro autocomplete=1 requerido (paridad relay-stock-existencias.php)."},
                status=400,
            )

        term = request.data.get("term")
        if term is None:
            term = request.POST.get("term") or ""

        try:
            data = search_articulos_autocomplete(base, str(term).strip())
        except Exception:
            return Response({"detail": "Error al buscar artículos."}, status=500)

        return Response(data)


class CatalogoSubrubrosTipoClienteRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/catalogo/subrubros-tipo-cliente/?idrubro=&ajax=1
    Query opcional ``tipoCliente`` (paridad relay-tipo-cliente.php).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-tipo-cliente.php)."},
                status=400,
            )

        raw_r = request.query_params.get("idrubro")
        if raw_r is None or str(raw_r).strip() == "":
            return Response({"detail": "idrubro es obligatorio."}, status=400)
        try:
            codigo_rubro = int(raw_r)
        except (TypeError, ValueError):
            return Response({"detail": "idrubro debe ser entero."}, status=400)

        raw_tc = request.query_params.get("tipoCliente") or request.query_params.get("tipo_cliente")
        try:
            if raw_tc is not None and str(raw_tc).strip() != "":
                id_tc = int(raw_tc)
                data = list_subrubros_por_rubro_y_tipo_cliente(base, codigo_rubro, id_tc)
            else:
                data = list_subrubros_maestro_por_rubro(base, codigo_rubro)
        except Exception:
            return Response({"detail": "Error al consultar subrubros."}, status=500)

        return Response(data)


class CatalogoMarcasRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/catalogo/marcas/?ajax=1

    Paridad ``relay-marca.php`` (listado para filtros de catálogo ecommerce).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-marca.php)."},
                status=400,
            )

        try:
            data = list_marcas_catalogo_ecommerce(base)
        except Exception:
            return Response({"detail": "Error al consultar marcas."}, status=500)

        return Response(data)


class CatalogoLaboratoriosRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/catalogo/laboratorios/?ajax=1

    Paridad ``relay-laboratorio.php``.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-laboratorio.php)."},
                status=400,
            )

        try:
            data = list_laboratorios_catalogo_ecommerce(base)
        except Exception:
            return Response({"detail": "Error al consultar laboratorios."}, status=500)

        return Response(data)


class CatalogoProveedoresRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/catalogo/proveedores/?ajax=1

    Paridad ``relay-proveedor.php``.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-proveedor.php)."},
                status=400,
            )

        try:
            data = list_proveedores_catalogo_ecommerce(base)
        except Exception:
            return Response({"detail": "Error al consultar proveedores."}, status=500)

        return Response(data)


class CatalogoLotesRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/catalogo/lotes/?ajax=1&idArt=&idDeposito=

    Paridad ``relay-lote.php`` (el PHP devuelve HTML; Synap devuelve JSON).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-lote.php)."},
                status=400,
            )

        id_art = to_int_or_none(
            request.query_params.get("idArt") or request.query_params.get("id_art")
        )
        id_dep = to_int_or_none(
            request.query_params.get("idDeposito") or request.query_params.get("id_deposito")
        )
        if id_art is None or id_dep is None:
            return Response(
                {"detail": "idArt e idDeposito son obligatorios (enteros)."},
                status=400,
            )

        try:
            data = list_lotes_por_articulo_deposito(base, id_art, id_dep)
        except Exception:
            return Response({"detail": "Error al consultar lotes."}, status=500)

        return Response(data)


class CatalogoTaccRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/catalogo/tacc-opciones/?ajax=1

    Paridad ``relay-tacc.php`` (JSON ``mensaje`` + ``valores``).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-tacc.php)."},
                status=400,
            )

        try:
            payload = tacc_relay_payload(base)
        except Exception:
            return Response({"detail": "Error al consultar opciones TACC."}, status=500)

        return Response(payload)


class CatalogoMasVendidosRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/catalogo/mas-vendidos/?ajax=1

    Paridad lógica con ``inventario/includes/mas-vendidos.php`` (top ventas por movimientos ``stock``).

    Query opcionales: ``idcategoria``, ``idrubro``, ``idsubrubro``, ``limit`` (1–50, default 15).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-mas-vendidos.php)."},
                status=400,
            )

        filtros = parse_filtros_mas_vendidos(request.query_params)
        lim = parse_limit_mas_vendidos(request.query_params)

        try:
            data = list_mas_vendidos_ecommerce(
                base,
                limit=lim,
                id_categoria=filtros["id_categoria"],
                id_rubro=filtros["id_rubro"],
                id_subrubro=filtros["id_subrubro"],
            )
        except Exception:
            return Response({"detail": "Error al consultar más vendidos."}, status=500)

        return Response(data)
