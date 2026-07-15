"""
Vistas API relay para catálogo de productos mayorista (listado + detalle).

Fase P0: solo lectura, sin escritura MySQL.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, Optional

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils.administranet_types import to_decimal_or_none, to_int_or_none
from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.catalogo_producto import listar_articulos_paginado, obtener_detalle_articulo
from ecom.services.catalogo_restricciones import aplicar_restricciones_a_filtros
from ecom.services.mayoristapp_session import leer_cliente_seleccionado, leer_idcliente_mayoristapp
from ecom.services.mayoristapp_sesion_contexto import asegurar_contexto_mayoristapp
from ecom.services.pedido_masivo_matriz import marcas_asignadas_viajante_cliente
from ecom.services.precio_relays import lista_precio_relay_json
from ecom.services.vendedor_asignacion_sql import vcm_ternas_disponible
from ecom.services.vendedor_operativo import resolver_viajante_operativo


def _session_base_empresa(request: Request) -> Optional[str]:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


def _session_user(request: Request) -> Dict[str, Any]:
    return asegurar_contexto_mayoristapp(request)


def _cod_lista_desde_cliente_sesion(request: Request) -> Optional[int]:
    """Código numérico de lista desde datos del cliente en sesión."""
    cliente_data = leer_cliente_seleccionado(request)
    if cliente_data is None:
        return None
    cliente_obj: Dict[str, Any] = {}
    if isinstance(cliente_data, list) and cliente_data and isinstance(cliente_data[0], dict):
        cliente_obj = cliente_data[0]
    elif isinstance(cliente_data, dict):
        cliente_obj = cliente_data
    cod = to_int_or_none(cliente_obj.get("codListaPrecio"))
    if cod is not None:
        return cod
    lp = str(cliente_obj.get("listaPrecio") or "").strip().lower().replace("lista", "").strip()
    return to_int_or_none(lp)


def _rechazar_override_lista(request: Request) -> Optional[Response]:
    """REQ-CAT-005: la lista del cliente no admite override en el request."""
    body = request.data if isinstance(request.data, dict) else {}
    for clave in ("lista_id", "cod_lista_precio", "codListaPrecio", "lista_precio"):
        if body.get(clave) is not None:
            return Response(
                {"detail": "La lista de precios del cliente no se puede modificar."},
                status=400,
            )
    for clave in ("lista_id", "cod_lista_precio", "codListaPrecio", "lista_precio"):
        if request.query_params.get(clave) is not None:
            return Response(
                {"detail": "La lista de precios del cliente no se puede modificar."},
                status=400,
            )
    return None


def _resolver_id_cliente_domicilio_catalogo(request: Request) -> Optional[int]:
    """Domicilio operativo: query/body → sesión mayoristapp (fallback None = unión de sucursales)."""
    body = request.data if isinstance(request.data, dict) else {}
    for fuente in (
        request.query_params.get("id_cliente_domicilio"),
        body.get("id_cliente_domicilio"),
    ):
        idd = to_int_or_none(fuente)
        if idd is not None and idd > 0:
            return idd
    sess = getattr(request, "session", None) or {}
    ma = sess.get("mayoristapp") or {}
    for fuente in (
        ma.get("id_cliente_domicilio"),
        sess.get("id_cliente_domicilio"),
    ):
        idd = to_int_or_none(fuente)
        if idd is not None and idd > 0:
            return idd
    return None


def _aplicar_filtro_vcm_catalogo(
    request: Request,
    base_empresa: str,
    filtros: Dict[str, Any],
    codigo_cliente: Optional[int],
) -> Optional[Response]:
    """REQ-CAT-004: marcas de terna; 400 si falta cliente cuando VCM aplica."""
    if not vcm_ternas_disponible(base_empresa):
        return None
    if codigo_cliente is None:
        return Response(
            {
                "detail": "Seleccioná un cliente antes de buscar artículos en el catálogo.",
                "codigo": "cliente_requerido_vcm",
            },
            status=400,
        )
    cv = resolver_viajante_operativo(_session_user(request))
    if cv is None:
        return Response(
            {"detail": "No se resolvió el viajante de sesión."},
            status=400,
        )
    marcas = marcas_asignadas_viajante_cliente(
        base_empresa,
        cv,
        codigo_cliente,
        _resolver_id_cliente_domicilio_catalogo(request),
    )
    if marcas:
        filtros["marcas"] = marcas
    else:
        filtros["marcas"] = [-1]
    return None


def _cod_lista_precio_cliente_desde_sesion(request: Request) -> Optional[int]:
    """Paridad cod_lista_precio_cliente de sesión (reutiliza lógica de precio_relay_views)."""
    sess = getattr(request, "session", None) or {}
    user = sess.get("user") or {}
    ma = sess.get("mayoristapp") or {}
    cliente = ma.get("cliente") if isinstance(ma.get("cliente"), dict) else {}
    cod = to_int_or_none(
        user.get("cliente_cod_lista_precio")
        or ma.get("cliente_cod_lista_precio")
        or cliente.get("codListaPrecio")
    )
    if cod is not None:
        return cod
    return _cod_lista_desde_cliente_sesion(request)


def _obtener_lista_id_y_cliente(request: Request, base_empresa: str) -> tuple[int, Optional[int], Decimal, bool]:
    """
    Obtiene lista_id, codigo_cliente, descuento_cliente, iva_incluido desde sesión.

    Returns:
        (lista_id, codigo_cliente, descuento_cliente, iva_incluido)
    """
    lista_id = _cod_lista_precio_cliente_desde_sesion(request)
    codigo_cliente = leer_idcliente_mayoristapp(request)

    if codigo_cliente is not None:
        if lista_id is None:
            lista_id = 1
    elif lista_id is None:
        listas = lista_precio_relay_json(base_empresa)
        for lst in listas:
            if lst.get("selected"):
                lista_id = to_int_or_none(lst.get("id"))
                break
        if lista_id is None:
            lista_id = 1

    descuento_cliente = Decimal("0")
    iva_incluido = True

    cliente_data = leer_cliente_seleccionado(request)
    if cliente_data is not None:
        if isinstance(cliente_data, list) and len(cliente_data) > 0:
            cliente_obj = cliente_data[0] if isinstance(cliente_data[0], dict) else {}
            descuento_cliente = to_decimal_or_none(cliente_obj.get("descRenglon")) or Decimal("0")
        elif isinstance(cliente_data, dict):
            descuento_cliente = to_decimal_or_none(cliente_data.get("descRenglon")) or Decimal("0")

    ma = (getattr(request, "session", None) or {}).get("mayoristapp") or {}
    iva_incluido_str = ma.get("iva_incluido", "Si")
    iva_incluido = str(iva_incluido_str).strip().lower() == "si"

    return lista_id, codigo_cliente, descuento_cliente, iva_incluido


def _leer_desc_pie_cliente(request: Request) -> Decimal:
    """Descuento al pie del cliente en sesión (columna legacy ``Descuento`` → ``descPie``)."""
    cliente_data = leer_cliente_seleccionado(request)
    if cliente_data is not None:
        if isinstance(cliente_data, list) and len(cliente_data) > 0:
            cliente_obj = cliente_data[0] if isinstance(cliente_data[0], dict) else {}
            return to_decimal_or_none(cliente_obj.get("descPie")) or Decimal("0")
        if isinstance(cliente_data, dict):
            return to_decimal_or_none(cliente_data.get("descPie")) or Decimal("0")
    return Decimal("0")


def _session_pv_activo(request: Request) -> Optional[int]:
    """PV activo de la sesión mayoristapp (id_punto_venta_activo)."""
    sess = getattr(request, "session", None) or {}
    val = sess.get("id_punto_venta_activo")
    if val is None:
        ma = sess.get("mayoristapp") or {}
        val = ma.get("id_punto_venta_activo") or ma.get("id_punto_venta")
    return to_int_or_none(val)


def _obtener_id_deposito(request: Request) -> int:
    """Obtiene id_deposito desde sesión (deposito activo o mayoristapp); default 1."""
    sess = getattr(request, "session", None) or {}
    dep = sess.get("deposito")
    if dep is not None:
        id_dep = to_int_or_none(dep)
        if id_dep is not None:
            return id_dep

    ma = sess.get("mayoristapp") or {}
    dep_ma = ma.get("deposito")
    if dep_ma is not None:
        id_dep = to_int_or_none(dep_ma)
        if id_dep is not None:
            return id_dep

    return 1


class CatalogoArticulosListadoRelayAPIView(APIView):
    """
    POST /ecom/api/mayoristapp/catalogo/articulos/listado/

    Listado paginado de artículos del catálogo con precio calculado y stock disponible.

    Body JSON:
        {
            "filtros": {
                "rubro": int (opcional),
                "subrubro": int (opcional),
                "marca": int (opcional),
                "laboratorio": int (opcional),
                "proveedor": int (opcional),
                "q": str (opcional, búsqueda por texto/código),
                "solo_promocion": bool (opcional)
            },
            "pagina": int (default 1),
            "tam": int (default 20, máx 100)
        }

    Response:
        {
            "items": [...],
            "total": int,
            "pagina": int,
            "tam": int,
            "total_paginas": int
        }
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        err_lista = _rechazar_override_lista(request)
        if err_lista is not None:
            return err_lista

        codigo_cliente = leer_idcliente_mayoristapp(request)
        filtros_previo: Dict[str, Any] = dict((request.data or {}).get("filtros") or {})
        err_vcm = _aplicar_filtro_vcm_catalogo(request, base, filtros_previo, codigo_cliente)
        if err_vcm is not None:
            return err_vcm

        try:
            lista_id, codigo_cliente, descuento_cliente, iva_incluido = _obtener_lista_id_y_cliente(request, base)
        except Exception:
            return Response(
                {"detail": "Error al resolver lista de precio o cliente desde sesión."},
                status=500,
            )

        id_deposito = _obtener_id_deposito(request)

        body = request.data or {}
        filtros = dict(body.get("filtros") or {})
        if filtros_previo.get("marcas"):
            filtros["marcas"] = filtros_previo["marcas"]
        filtros = aplicar_restricciones_a_filtros(filtros, base, _session_pv_activo(request))
        pagina = to_int_or_none(body.get("pagina")) or 1
        tam = to_int_or_none(body.get("tam")) or 20

        try:
            resultado = listar_articulos_paginado(
                base,
                filtros=filtros,
                lista_id=lista_id,
                codigo_cliente=codigo_cliente,
                descuento_cliente=descuento_cliente,
                iva_incluido=iva_incluido,
                id_deposito=id_deposito,
                pagina=pagina,
                tam=tam,
            )
        except Exception:
            return Response(
                {"detail": "Error al consultar el listado de artículos."},
                status=500,
            )

        return Response(resultado)


class CatalogoArticuloDetalleRelayAPIView(APIView):
    """
    GET /ecom/api/mayoristapp/catalogo/articulos/<int:idart>/detalle/

    Ficha de detalle de un artículo.

    Response:
        {
            "id_articulo": int,
            "id_manual": str,
            "codigo": str,
            "nombre": str,
            "descripcion": str,
            "rubro": str,
            "subrubro": str,
            "marca": str,
            "precio": float,
            "precio_neto": float,
            "stock_disponible": float,
            "stock_depositos": [...],
            "tiene_foto": bool,
            "promocion": {...} (si aplica)
        }
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request, idart: int) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        err_lista = _rechazar_override_lista(request)
        if err_lista is not None:
            return err_lista

        try:
            lista_id, codigo_cliente, descuento_cliente, iva_incluido = _obtener_lista_id_y_cliente(request, base)
        except Exception:
            return Response(
                {"detail": "Error al resolver lista de precio o cliente desde sesión."},
                status=500,
            )

        filtros: Dict[str, Any] = {}
        err_vcm = _aplicar_filtro_vcm_catalogo(request, base, filtros, codigo_cliente)
        if err_vcm is not None:
            return err_vcm

        id_deposito = _obtener_id_deposito(request)

        try:
            detalle = obtener_detalle_articulo(
                base,
                idart=idart,
                lista_id=lista_id,
                codigo_cliente=codigo_cliente,
                descuento_cliente=descuento_cliente,
                iva_incluido=iva_incluido,
                id_deposito=id_deposito,
            )
        except Exception:
            return Response(
                {"detail": "Error al consultar el detalle del artículo."},
                status=500,
            )

        if detalle is None:
            return Response({"detail": "Artículo no encontrado o inactivo."}, status=404)

        if vcm_ternas_disponible(base) and codigo_cliente is not None:
            cv = resolver_viajante_operativo(_session_user(request))
            marcas = marcas_asignadas_viajante_cliente(
                base,
                cv or 0,
                codigo_cliente,
                _resolver_id_cliente_domicilio_catalogo(request),
            )
            cod_marca = to_int_or_none(detalle.get("codigo_marca") or detalle.get("CodigoMarca"))
            if marcas and cod_marca is not None and cod_marca not in marcas:
                return Response({"detail": "Artículo no disponible para la terna del cliente."}, status=404)

        return Response(detalle)
