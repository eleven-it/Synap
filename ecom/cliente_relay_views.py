"""
Relays clientes mayoristapp (``relay-clientes.php``).
"""

from __future__ import annotations

from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ecom.permissions import EcomMayoristappSessionPermission
from ecom.services.cliente_contacto_relay import alta_contacto_relay, lista_contactos_cliente
from ecom.services.cliente_domicilio_relay import (
    alta_domicilio_relay,
    edita_domicilio_relay,
    id_cliente_de_domicilio,
    trae_domicilio_completo,
    trae_opciones_visita,
)
from ecom.services.cliente_geo_relay import (
    list_departamentos,
    list_distritos,
    list_provincias,
    list_zonas_erp,
)
from ecom.services.cliente_rapido_escritura import (
    actualizar_cliente_rapido_json,
    alta_cliente_rapido,
    edita_cliente_rapido,
)
from ecom.services.cliente_rapido_relay import (
    inicio_payload,
    obtiene_cliente_fila,
    tipo_cliente_dict,
    tipo_iva_dict,
)
from ecom.services.cliente_relay import (
    MAYORISTAPP_FORMULARIO_COMPROBANTE,
    buscar_clientes_relay,
    cliente_accesible_por_sesion,
)
from ecom.services.cliente_seleccion_relay import construir_payload_cliente_seleccionado
from ecom.services.mayoristapp_session import (
    guardar_cliente_rapido_lista_sesion,
    guardar_cliente_seleccion_mayoristapp,
    guardar_formulario_comprobante_mayoristapp,
    leer_cliente_seleccionado,
    leer_idcliente_mayoristapp,
)
from ecom.services.mayoristapp_sesion_contexto import asegurar_contexto_mayoristapp
from core.utils.administranet_types import to_int_or_none


def _session_base_empresa(request: Request) -> str | None:
    data = (getattr(request, "session", None) or {}).get("user") or {}
    be = data.get("base_empresa")
    return str(be).strip() if be else None


def _session_user(request: Request) -> dict:
    return asegurar_contexto_mayoristapp(request)


class ClienteBuscarRelayAPIView(APIView):
    """
    GET/POST ``/ecom/api/mayoristapp/clientes/buscar/?ajax=1``

    Paridad POST ``buscarCliente`` (``queCliente``, ``claseBusqueda``, ``codigo``).
    GET: ``modoBus`` / ``modo_busqueda``, ``patron`` / ``queCliente``, ``codigo``, ``limit``.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def _parse(self, request: Request) -> tuple[str, str, str, int]:
        if request.method == "GET":
            modo = request.query_params.get("modoBus") or request.query_params.get("modo_busqueda") or ""
            patron = (
                request.query_params.get("patron")
                or request.query_params.get("queCliente")
                or request.query_params.get("q")
                or ""
            )
            codigo = request.query_params.get("codigo") or ""
            lim = to_int_or_none(request.query_params.get("limit")) or 10
        else:
            data = request.data
            modo = data.get("claseBusqueda") or data.get("modoBus") or ""
            patron = (data.get("queCliente") or data.get("patron") or "") or ""
            codigo = (data.get("codigo") or "") or ""
            lim = to_int_or_none(data.get("limit")) or 10
        return str(modo).strip().lower(), str(patron), str(codigo), max(1, min(int(lim), 50))

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-clientes.php)."},
                status=400,
            )
        modo, patron, codigo, lim = self._parse(request)
        return self._ejecutar_busqueda(request, base, modo, patron, codigo, lim)

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if str(request.data.get("buscarCliente")) != "1":
            return Response(
                {"detail": "Parámetro buscarCliente=1 requerido en el cuerpo (paridad relay-clientes.php)."},
                status=400,
            )
        modo, patron, codigo, lim = self._parse(request)
        return self._ejecutar_busqueda(request, base, modo, patron, codigo, lim)

    @staticmethod
    def _filas_a_results_synap(rows: list) -> list[dict]:
        """Formato autocomplete Synap (`{ id, text }`) para tags_filter / presupuesto."""
        results = []
        for row in rows:
            cod = row.get("Codigo")
            if cod is None:
                cod = row.get("codigo")
            if cod is None:
                continue
            nombre = (row.get("nombre_cliente") or row.get("nombre") or row.get("Nombre") or "").strip()
            try:
                cid = int(cod)
            except (TypeError, ValueError):
                try:
                    cid = int(float(cod))
                except (TypeError, ValueError):
                    continue
            results.append({"id": cid, "text": nombre or str(cid)})
        return results

    def _ejecutar_busqueda(
        self, request: Request, base: str, modo: str, patron: str, codigo: str, lim: int
    ) -> Response:
        if not modo and (patron or codigo):
            modo = "codigo" if codigo and not patron else "texto"
        sess_user = _session_user(request)
        rows, err = buscar_clientes_relay(
            base,
            modo_busqueda=modo,
            patron_texto=patron,
            codigo_cliente=codigo,
            sess_user=sess_user,
            limit=lim,
        )
        msg_map = {
            "ingrese_busqueda": ("Debe ingresar una búsqueda.", 400),
            "codigo_invalido": ("Código de cliente inválido.", 400),
            "patron_vacio": ("Patrón de búsqueda vacío.", 400),
            "modo_invalido": ("modoBus / claseBusqueda debe ser codigo o texto.", 400),
        }
        if err:
            msg, status = msg_map.get(err, ("Error en búsqueda.", 400))
            return Response({"detail": msg, "codigo": err}, status=status)

        return Response(
            {
                "clientes": rows,
                "total": len(rows),
                "results": self._filas_a_results_synap(rows),
            }
        )


class ClienteSeleccionadoRelayAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/clientes/seleccionado/?ajax=1``

    Paridad ``traeDatosClienteSeleccionado`` (JSON desde sesión).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-clientes.php)."},
                status=400,
            )

        data = leer_cliente_seleccionado(request)
        if data is None:
            return Response({})
        if isinstance(data, dict):
            return Response(data)
        return Response({"cliente": data})


class ClienteComprobanteFormularioRelayAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/clientes/comprobante-formulario/?ajax=1&frm=<0-5>``

    Paridad ``seleccionarComprobante`` (guarda en sesión y devuelve JSON con URL).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)

        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay-clientes.php)."},
                status=400,
            )

        frm = to_int_or_none(request.query_params.get("frm"))
        if frm is None or frm not in MAYORISTAPP_FORMULARIO_COMPROBANTE:
            return Response({"detail": "frm debe ser un entero entre 0 y 5."}, status=400)

        formulario, url = MAYORISTAPP_FORMULARIO_COMPROBANTE[frm]
        try:
            guardar_formulario_comprobante_mayoristapp(request, formulario, url)
        except Exception:
            return Response({"detail": "No se pudo guardar el formulario en sesión."}, status=500)

        return Response({"estado": "ok", "url": url, "formulario": formulario})


class ClienteSeleccionarRelayAPIView(APIView):
    """
    POST ``/ecom/api/mayoristapp/clientes/seleccionar/?ajax=1``

    Paridad ``selecciona_cliente`` en ``relay-cliente-rapido.php`` (cuerpo JSON ``codigo`` / ``codCliente``).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response(
                {"detail": "Parámetro ajax requerido (paridad relay PHP)."},
                status=400,
            )
        cod = to_int_or_none(request.data.get("codigo") or request.data.get("codCliente"))
        if cod is None:
            return Response({"detail": "codigo o codCliente requerido."}, status=400)
        sess_user = _session_user(request)
        if not cliente_accesible_por_sesion(base, cod, sess_user):
            return Response({"detail": "Cliente no disponible o sin permiso."}, status=403)
        cv = to_int_or_none(
            sess_user.get("id_vendedor_usr") or sess_user.get("CodViajante") or sess_user.get("cod_viajante")
        )
        cliente_datos, autoriza, domicilios, iva_inc = construir_payload_cliente_seleccionado(base, cod, cv)
        if not cliente_datos:
            return Response({"detail": "No se encontró el cliente."}, status=404)
        guardar_cliente_seleccion_mayoristapp(
            request,
            cliente_datos=cliente_datos,
            autoriza_credito=autoriza,
            idcliente=cod,
            domicilios_cliente=domicilios,
            iva_incluido=iva_inc,
        )
        return Response({"estado": "ok", "idcliente": cod, "ivaIncluido": iva_inc})


class ClienteDomicilioRelayAPIView(APIView):
    """
    GET/POST ``/ecom/api/mayoristapp/clientes/domicilio/?ajax=1``

    Paridad ``relay-cliente-domicilio.php`` (acciones ``traer``, ``provincia``, ``departamento``, ``distrito``, ``zona``, ``alta``, ``editar``).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        accion = (request.query_params.get("accion") or "").strip().lower()
        sess_user = _session_user(request)
        id_pais = to_int_or_none(request.query_params.get("idPais"))
        id_prov = to_int_or_none(request.query_params.get("idProvincia"))
        id_dep = to_int_or_none(request.query_params.get("idDepartamento"))
        id_dist = to_int_or_none(request.query_params.get("idDistrito"))

        if accion == "traer":
            id_dom = to_int_or_none(request.query_params.get("idDomicilio"))
            if id_dom is None:
                return Response({"detail": "idDomicilio requerido."}, status=400)
            id_cli = id_cliente_de_domicilio(base, id_dom)
            if id_cli is None or not cliente_accesible_por_sesion(base, id_cli, sess_user):
                return Response({"detail": "Domicilio no disponible."}, status=403)
            dm, err = trae_domicilio_completo(base, id_dom)
            if err or not dm:
                return Response({"detail": "No se encontró el domicilio."}, status=404)
            cp = dm.get("CodProvincia")
            prov = list_provincias(base, id_pais)
            dep = list_departamentos(base, cp)
            dist = list_distritos(base, dm.get("IDDepartamento"))
            zona = list_zonas_erp(base, cp)
            return Response({"dom": dm, "prov": prov, "dep": dep, "dist": dist, "zona": zona})

        if accion == "provincia":
            return Response(list_provincias(base, id_pais))
        if accion == "departamento":
            return Response(list_departamentos(base, id_prov))
        if accion == "distrito":
            return Response(list_distritos(base, id_dep))
        if accion == "zona":
            return Response(list_zonas_erp(base, id_prov))
        return Response({"detail": "accion inválida (use traer, provincia, departamento, distrito, zona)."}, status=400)

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        accion = (request.data.get("accion") or "").strip().lower()
        sess_user = _session_user(request)
        if accion == "alta":
            id_cli = to_int_or_none(request.data.get("idCliente"))
            if id_cli is None or not cliente_accesible_por_sesion(base, id_cli, sess_user):
                return Response({"detail": "Cliente no disponible para alta de domicilio."}, status=403)
            payload, err = alta_domicilio_relay(base, dict(request.data))
            if err:
                return Response({"detail": err, "estado": "error"}, status=400)
            return Response(payload)
        if accion == "editar":
            id_dom = to_int_or_none(request.data.get("idClienteDom"))
            if id_dom is None:
                return Response({"detail": "idClienteDom requerido."}, status=400)
            id_cli = id_cliente_de_domicilio(base, id_dom)
            if id_cli is None or not cliente_accesible_por_sesion(base, id_cli, sess_user):
                return Response({"detail": "Domicilio no disponible."}, status=403)
            payload, err = edita_domicilio_relay(base, dict(request.data))
            if err:
                return Response({"detail": err, "estado": "error"}, status=400)
            return Response(payload)
        return Response({"detail": "accion inválida (use alta o editar)."}, status=400)


class ClienteDomicilioOpcionesVisitaRelayAPIView(APIView):
    """
    GET ``/ecom/api/mayoristapp/clientes/domicilio-opciones-visita/?traeVisita=1&tipoVisita=…``

    Paridad ``traeVisita`` en ``relay-cliente-domicilio.php``.
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if str(request.query_params.get("traeVisita")) != "1":
            return Response({"detail": "traeVisita=1 requerido."}, status=400)
        tv = request.query_params.get("tipoVisita") or ""
        return Response(trae_opciones_visita(str(tv)))


class ClienteContactoRelayAPIView(APIView):
    """
    GET/POST ``/ecom/api/mayoristapp/clientes/contacto/?ajax=1``

    Paridad ``relay-contacto-cliente.php`` (respuesta JSON en lugar de HTML).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        accion = (request.query_params.get("accion") or "lista").strip().lower()
        if accion != "lista":
            return Response({"detail": "GET solo soporta accion=lista."}, status=400)
        id_cli = leer_idcliente_mayoristapp(request)
        if id_cli is None:
            return Response({"detail": "No hay idcliente en sesión."}, status=400)
        sess_user = _session_user(request)
        if not cliente_accesible_por_sesion(base, id_cli, sess_user):
            return Response({"detail": "Cliente no disponible."}, status=403)
        rows = lista_contactos_cliente(base, id_cli)
        return Response({"contactos": rows, "total": len(rows)})

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        accion = (request.data.get("accion") or "").strip().lower()
        if accion != "alta":
            return Response({"detail": "accion=alta requerido."}, status=400)
        id_cli = leer_idcliente_mayoristapp(request)
        if id_cli is None:
            return Response({"detail": "No hay idcliente en sesión."}, status=400)
        sess_user = _session_user(request)
        if not cliente_accesible_por_sesion(base, id_cli, sess_user):
            return Response({"detail": "Cliente no disponible."}, status=403)
        completo = str(sess_user.get("contacto_completo") or "No")
        ok, err = alta_contacto_relay(
            base,
            id_cliente=id_cli,
            completo=completo,
            nombre_contacto=str(request.data.get("nombreContacto") or ""),
            tipo_doc=str(request.data.get("tipoDocContacto") or ""),
            nro_doc=str(request.data.get("nroDocContacto") or ""),
            telefono_contacto=str(request.data.get("telefonoContacto") or ""),
            email_contacto=str(request.data.get("emailContacto") or ""),
        )
        if not ok:
            return Response({"detail": err or "Error al alta contacto.", "estado": "error"}, status=400)
        rows = lista_contactos_cliente(base, id_cli)
        return Response({"estado": "ok", "contactos": rows, "total": len(rows)})


class ClienteRapidoRelayAPIView(APIView):
    """
    GET/POST ``/ecom/api/mayoristapp/clientes/rapido/?ajax=1&accion=…``

    GET: ``inicio``, ``tipoCliente``, ``ivaCliente``, ``provincia``, ``departamento``, ``distrito``, ``obtieneCliente``.

    POST: ``altaCliente`` / ``editaCliente`` (paridad ``relay-cliente-rapido.php``).
    """

    permission_classes = [EcomMayoristappSessionPermission]

    def post(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        accion = (request.data.get("accion") or "").strip().lower()
        sess_user = _session_user(request)
        if accion == "altacliente":
            resultado = alta_cliente_rapido(base, dict(request.data), sess_user)
            if isinstance(resultado, dict):
                return Response(resultado, status=400)
            cod = resultado
            cv = to_int_or_none(
                sess_user.get("id_vendedor_usr")
                or sess_user.get("CodViajante")
                or sess_user.get("cod_viajante")
            )
            cliente_datos, autoriza, domicilios, iva_inc = construir_payload_cliente_seleccionado(base, cod, cv)
            if cliente_datos:
                guardar_cliente_seleccion_mayoristapp(
                    request,
                    cliente_datos=cliente_datos,
                    autoriza_credito=autoriza,
                    idcliente=cod,
                    domicilios_cliente=domicilios,
                    iva_incluido=iva_inc,
                )
            lista_json = actualizar_cliente_rapido_json(base, sess_user)
            guardar_cliente_rapido_lista_sesion(request, lista_json)
            nombre = str(request.data.get("nombreCliente") or "").strip()
            return Response(
                {
                    "status": "ok",
                    "cartel": f"cliente {nombre} ingresado con exito",
                    "codigo": cod,
                }
            )

        if accion == "editacliente":
            cod_cli = to_int_or_none(request.data.get("codCliente"))
            if cod_cli is None:
                return Response({"detail": "codCliente requerido."}, status=400)
            if not cliente_accesible_por_sesion(base, cod_cli, sess_user):
                return Response({"detail": "Cliente no disponible."}, status=403)
            resultado = edita_cliente_rapido(base, dict(request.data), sess_user)
            if isinstance(resultado, dict):
                return Response(resultado, status=400)
            cod = int(resultado)
            cv = to_int_or_none(
                sess_user.get("id_vendedor_usr")
                or sess_user.get("CodViajante")
                or sess_user.get("cod_viajante")
            )
            cliente_datos, autoriza, domicilios, iva_inc = construir_payload_cliente_seleccionado(base, cod, cv)
            if cliente_datos:
                guardar_cliente_seleccion_mayoristapp(
                    request,
                    cliente_datos=cliente_datos,
                    autoriza_credito=autoriza,
                    idcliente=cod,
                    domicilios_cliente=domicilios,
                    iva_incluido=iva_inc,
                )
            return Response({"status": "ok", "cartel": "cliente editado con exito", "codigo": cod})

        return Response({"detail": "accion inválida (use altaCliente o editaCliente)."}, status=400)

    def get(self, request: Request) -> Response:
        base = _session_base_empresa(request)
        if not base:
            return Response({"detail": "No se encontró base_empresa en la sesión."}, status=400)
        if "ajax" not in request.query_params:
            return Response({"detail": "Parámetro ajax requerido."}, status=400)
        accion = (request.query_params.get("accion") or "").strip().lower()
        id_pais = to_int_or_none(request.query_params.get("idPais"))
        id_prov = to_int_or_none(request.query_params.get("idProvincia"))
        id_dep = to_int_or_none(request.query_params.get("idDepartamento"))
        sess_user = _session_user(request)

        if accion == "inicio":
            return Response(inicio_payload(base))
        if accion == "tipocliente":
            return Response(tipo_cliente_dict(base))
        if accion == "ivacliente":
            return Response(tipo_iva_dict(base))
        if accion == "provincia":
            return Response(list_provincias(base, id_pais))
        if accion == "departamento":
            return Response(list_departamentos(base, id_prov))
        if accion == "distrito":
            return Response(list_distritos(base, id_dep))
        if accion == "obtienecliente":
            cod = to_int_or_none(request.query_params.get("codCliente"))
            if cod is None:
                return Response({"detail": "codCliente requerido."}, status=400)
            if not cliente_accesible_por_sesion(base, cod, sess_user):
                return Response({"detail": "Cliente no disponible."}, status=403)
            fila = obtiene_cliente_fila(base, cod)
            if not fila:
                return Response({"detail": "No se encontró el cliente."}, status=404)
            return Response({"cliente": fila})
        return Response({"detail": "accion inválida."}, status=400)
