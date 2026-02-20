"""
Vistas para Remito de compra (paridad PRemito.frm VB6).
Eventos: Form_Load → GET con contexto; Aceptar_Click → POST guardar; Eliminar_Click → POST eliminar renglón.
"""
import json
from datetime import date

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.services.administranet_compras import (
    alta_renglon_temporal,
    eliminar_renglon_temporal,
    get_depositos_remito,
    get_id_art_por_codigo,
    get_renglones_temporales,
    guardar_remito_compra,
    importar_comprobante_remito,
    list_comprobantes_remito,
    limpiar_temporales_usuario,
)
from core.services.administranet_permisos_sistema import AdministraNETPermisosSistemaService
from compras.forms import AltaRenglonRemitoForm, RemitoCompraCabeceraForm


def _tipo_comp_choices(base_empresa, id_puesto):
    """
    Opciones del combo tipo_comp (paridad VB6 Inicial: Principal.remite_factura_art).
    Si permiso remite_factura_art = 'Si' → Ord. Compra y Factura; si no, solo Ord. Compra.
    """
    base = [("ord_compra", "Ord. Compra")]
    if not base_empresa or not id_puesto:
        return base
    try:
        svc = AdministraNETPermisosSistemaService()
        permisos = svc.obtener_permisos_puesto(base_empresa, int(id_puesto)) or {}
        valor = (permisos.get("remite_factura_art") or "").strip()
        if str(valor).lower() == "si":
            return base + [("factura", "Factura")]
    except Exception:
        pass
    return base


def _session_base(request):
    """Obtiene base_empresa e id_usuario de sesión (paridad Principal, IngresoUsuario)."""
    user = request.session.get("user") or {}
    base_empresa = user.get("base_empresa")
    id_usuario = user.get("id_usuario")
    cod_sucursal = user.get("id_sucursal")
    if cod_sucursal is None:
        cod_sucursal = 1
    return base_empresa, id_usuario, cod_sucursal


def _permite_cambiar_deposito(base_empresa, id_puesto):
    """
    Equivalente a Principal.cambia_deposito en VB6.
    Si no se puede resolver permisos, mantiene comportamiento permisivo por compatibilidad.
    """
    if not base_empresa or not id_puesto:
        return True
    try:
        svc = AdministraNETPermisosSistemaService()
        permisos = svc.obtener_permisos_puesto(base_empresa, int(id_puesto)) or {}
        valor = permisos.get("cambia_deposito")
        if valor is None:
            # Fallback defensivo por posibles variantes de nombre de columna
            for k, v in permisos.items():
                if str(k).strip().lower() == "cambia_deposito":
                    valor = v
                    break
        return (str(valor or "").strip().lower() == "si")
    except Exception:
        return True


def _modo_deposito_post(request):
    """
    Mapea el selector VB6 Deposito_Seleccion.
    Valores soportados: defecto_usuario, comp_original, seleccionado, por_articulo.
    """
    modo = (request.POST.get("deposito_seleccion") or "defecto_usuario").strip().lower()
    if modo not in {"defecto_usuario", "comp_original", "seleccionado", "por_articulo"}:
        modo = "defecto_usuario"
    return modo


@require_http_methods(["GET", "POST"])
def remito_compra_form(request):
    """
    Formulario Remito de compra (paridad PRemito.frm).
    GET: Form_Load + Inicial — depósitos, renglones temporales (cuerpostockp CodigoMovimiento=0), formulario vacío o con datos.
    POST: Aceptar_Click → Guardar — validaciones y persistencia según contrato.
    """
    base_empresa, id_usuario, cod_sucursal = _session_base(request)
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    if id_usuario is None:
        messages.error(request, "Usuario no identificado.")
        return redirect("core:dashboard")

    user_session = (request.session.get("user") or {})
    id_puesto = user_session.get("id_puesto")
    id_deposito_usuario = user_session.get("id_deposito")
    cambia_deposito = _permite_cambiar_deposito(base_empresa, id_puesto)

    depositos_raw = get_depositos_remito(
        base_empresa,
        id_usuario,
        id_puesto,
        cambia_deposito=cambia_deposito,
        id_deposito_usuario=id_deposito_usuario,
    )
    depositos_choices = [(d["CodDeposito"], d.get("NombreDeposito") or str(d["CodDeposito"])) for d in depositos_raw]
    id_deposito_inicial = depositos_choices[0][0] if depositos_choices else None
    tipo_comp_choices = _tipo_comp_choices(base_empresa, id_puesto)

    renglones = get_renglones_temporales(base_empresa, id_usuario, codigo_movimiento=0, visualiza="No")

    if request.method == "POST":
        form = RemitoCompraCabeceraForm(depositos_choices=depositos_choices, tipo_comp_choices=tipo_comp_choices, data=request.POST)
        if form.is_valid():
            nro = form.cleaned_data.get("nro", "").strip()
            nro_suc = form.cleaned_data.get("nro_suc", "").strip()
            if not nro or not nro_suc:
                messages.error(request, "Debe completar todos los campos")
                return render(request, "compras/remito_compra_form.html", {
                    "form": form,
                    "renglones": renglones,
                    "depositos": depositos_raw,
                    "base_empresa": base_empresa,
                    "form_alta_renglon": AltaRenglonRemitoForm(depositos_choices=depositos_choices),
                })
            if not renglones:
                messages.error(request, "Debe cargar al menos un renglón.")
                return render(request, "compras/remito_compra_form.html", {
                    "form": form,
                    "renglones": renglones,
                    "depositos": depositos_raw,
                    "base_empresa": base_empresa,
                    "form_alta_renglon": AltaRenglonRemitoForm(depositos_choices=depositos_choices),
                })
            cabecera = {
                "nro": nro,
                "nro_suc": nro_suc,
                "fecha": form.cleaned_data.get("fecha"),
                "fecha_registro": form.cleaned_data.get("fecha_registro"),
                "detalle": form.cleaned_data.get("detalle") or "",
                "codigo_proveedor": form.cleaned_data.get("codigo_proveedor"),
                "id_deposito": form.cleaned_data.get("id_deposito"),
                "importe_total": form.cleaned_data.get("importe_total"),
                "exento": form.cleaned_data.get("exento") or 0,
                "subtotal1": form.cleaned_data.get("subtotal1") or 0,
                "subtotal2": form.cleaned_data.get("subtotal2") or 0,
                "imp_desc1_1": form.cleaned_data.get("imp_desc1_1") or 0,
                "sub_total_desc1": form.cleaned_data.get("sub_total_desc1") or 0,
                "sub_total_desc2": form.cleaned_data.get("sub_total_desc2") or 0,
                "iva1": form.cleaned_data.get("iva1") or 0,
                "iva2": form.cleaned_data.get("iva2") or 0,
                "iva3": form.cleaned_data.get("iva3") or 0,
                "alic1": form.cleaned_data.get("alic1") or 0,
                "alic2": form.cleaned_data.get("alic2") or 0,
                "alic3": form.cleaned_data.get("alic3") or 0,
                "percep_ib": form.cleaned_data.get("percep_ib") or 0,
                "percep_ib_prov": form.cleaned_data.get("percep_ib_prov") or 0,
                "percep_gan": form.cleaned_data.get("percep_gan") or 0,
                "percep_iva": form.cleaned_data.get("percep_iva") or 0,
                "otros_imp": form.cleaned_data.get("otros_imp") or 0,
                "impuesto_interno": form.cleaned_data.get("impuesto_interno") or 0,
                "id_condcompra": form.cleaned_data.get("id_condcompra"),
                "cond_compra": form.cleaned_data.get("cond_compra") or "",
                "coti_dolar": form.cleaned_data.get("coti_dolar") or 0,
                "nro_cai": form.cleaned_data.get("nro_cai") or "",
                "fecha_cai": form.cleaned_data.get("fecha_cai"),
            }
            id_deposito_seleccion = form.cleaned_data.get("id_deposito") or 0
            cod_mov, err = guardar_remito_compra(
                base_empresa=base_empresa,
                id_usuario=id_usuario,
                cod_sucursal=cod_sucursal,
                cabecera=cabecera,
                renglones=renglones,
                id_deposito_seleccion=id_deposito_seleccion,
            )
            if err:
                messages.error(request, err)
                return render(request, "compras/remito_compra_form.html", {
                    "form": form,
                    "renglones": renglones,
                    "depositos": depositos_raw,
                    "base_empresa": base_empresa,
                    "form_alta_renglon": AltaRenglonRemitoForm(depositos_choices=depositos_choices),
                })
            limpiar_temporales_usuario(base_empresa, id_usuario)
            messages.success(request, f"Comprobante generado correctamente. Código movimiento: {cod_mov}")
            return redirect("compras:remito_compra_form")
        return render(request, "compras/remito_compra_form.html", {
            "form": form,
            "renglones": renglones,
            "depositos": depositos_raw,
            "base_empresa": base_empresa,
            "form_alta_renglon": AltaRenglonRemitoForm(depositos_choices=depositos_choices),
        })

    hoy = date.today().isoformat()
    form = RemitoCompraCabeceraForm(
        depositos_choices=depositos_choices,
        tipo_comp_choices=tipo_comp_choices,
        initial={
            "fecha": hoy,
            "fecha_registro": hoy,
            "codigo_proveedor": 0,
            "nombre_proveedor": "",
            "importe_total": "0",
            "id_deposito": id_deposito_inicial,
            "deposito_seleccion": "defecto_usuario",
        },
    )
    return render(request, "compras/remito_compra_form.html", {
        "form": form,
        "renglones": renglones,
        "depositos": depositos_raw,
        "base_empresa": base_empresa,
        "form_alta_renglon": AltaRenglonRemitoForm(
            depositos_choices=depositos_choices,
            initial={"id_deposito": id_deposito_inicial} if id_deposito_inicial is not None else None,
        ),
    })


@require_POST
def eliminar_renglon(request):
    """
    Elimina un renglón temporal (paridad Eliminar_Click).
    POST: orden, id_articulo, orden_cuerpo (para serie_entrada_temp).
    """
    base_empresa, id_usuario, _ = _session_base(request)
    if not base_empresa or id_usuario is None:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "error": "Sesión inválida"}, status=401)
        return redirect("login:login")

    orden = request.POST.get("orden")
    id_articulo = request.POST.get("id_articulo")
    orden_cuerpo = request.POST.get("orden")
    if not orden:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "error": "Falta orden"}, status=400)
        messages.error(request, "Falta identificar el renglón.")
        return redirect("compras:remito_compra_form")
    try:
        orden = int(orden)
    except (ValueError, TypeError):
        orden = None
    if orden is None:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "error": "Orden inválido"}, status=400)
        return redirect("compras:remito_compra_form")
    id_art = int(id_articulo) if id_articulo and str(id_articulo).isdigit() else None
    ord_cuerpo = int(orden_cuerpo) if orden_cuerpo and str(orden_cuerpo).isdigit() else orden
    try:
        eliminar_renglon_temporal(base_empresa, orden, id_usuario, id_art, ord_cuerpo)
    except Exception as e:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "error": str(e)}, status=500)
        messages.error(request, str(e))
        return redirect("compras:remito_compra_form")
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"success": True})
    messages.success(request, "Renglón eliminado.")
    return redirect("compras:remito_compra_form")


@require_http_methods(["GET", "POST"])
def añadir_renglon(request):
    """
    Añade un renglón temporal al remito (paridad AceptarStock / CuerpoStock.AddNew).
    POST: valida, resuelve IDArt por código, inserta en cuerpostockp, redirige al remito.
    GET: redirige al formulario principal (el alta se hace desde el formulario).
    """
    base_empresa, id_usuario, cod_sucursal = _session_base(request)
    if not base_empresa or id_usuario is None:
        messages.error(request, "Sesión inválida.")
        return redirect("core:dashboard")

    if request.method == "GET":
        return redirect("compras:remito_compra_form")

    user_session = (request.session.get("user") or {})
    id_puesto = user_session.get("id_puesto")
    id_deposito_usuario = user_session.get("id_deposito")
    cambia_deposito = _permite_cambiar_deposito(base_empresa, id_puesto)
    depositos_raw = get_depositos_remito(
        base_empresa,
        id_usuario,
        id_puesto,
        cambia_deposito=cambia_deposito,
        id_deposito_usuario=id_deposito_usuario,
    )
    depositos_choices = [(d["CodDeposito"], d.get("NombreDeposito") or str(d["CodDeposito"])) for d in depositos_raw]
    id_deposito_inicial = depositos_choices[0][0] if depositos_choices else None
    renglones = get_renglones_temporales(base_empresa, id_usuario, codigo_movimiento=0, visualiza="No")
    modo_deposito = _modo_deposito_post(request)
    id_deposito_global = request.POST.get("id_deposito_global")
    try:
        id_deposito_global = int(id_deposito_global) if id_deposito_global not in (None, "", "None") else None
    except (TypeError, ValueError):
        id_deposito_global = None

    form = AltaRenglonRemitoForm(depositos_choices=depositos_choices, data=request.POST)
    if not form.is_valid():
        hoy = date.today().isoformat()
        form_remito = RemitoCompraCabeceraForm(
            depositos_choices=depositos_choices,
            initial={
                "fecha": hoy,
                "fecha_registro": hoy,
                "codigo_proveedor": 0,
                "nombre_proveedor": "",
                "importe_total": "0",
                "id_deposito": id_deposito_global or id_deposito_inicial,
                "deposito_seleccion": modo_deposito,
            },
        )
        return render(request, "compras/remito_compra_form.html", {
            "form": form_remito,
            "renglones": renglones,
            "depositos": depositos_raw,
            "base_empresa": base_empresa,
            "form_alta_renglon": form,
        })

    codigo_articulo = (form.cleaned_data.get("codigo_articulo") or "").strip()
    descripcion = (form.cleaned_data.get("descripcion") or "").strip()
    cantidad = form.cleaned_data.get("cantidad")
    id_deposito = form.cleaned_data.get("id_deposito")
    precio_costo_u = form.cleaned_data.get("precio_costo_u")
    # Paridad VB6 Deposito_Seleccion:
    # - por_articulo: usa depósito por renglón
    # - seleccionado: usa depósito global seleccionado
    # - defecto_usuario / comp_original: usa depósito por defecto del usuario
    if modo_deposito == "por_articulo":
        deposito_final = id_deposito
    elif modo_deposito == "seleccionado":
        deposito_final = id_deposito_global or id_deposito_inicial
    else:
        try:
            deposito_final = int(id_deposito_usuario) if id_deposito_usuario is not None else id_deposito_inicial
        except (TypeError, ValueError):
            deposito_final = id_deposito_inicial
    art = get_id_art_por_codigo(base_empresa, codigo_articulo)
    if not art:
        messages.error(request, f"No se encontró artículo con código «{codigo_articulo}».")
        hoy = date.today().isoformat()
        form_remito = RemitoCompraCabeceraForm(
            depositos_choices=depositos_choices,
            initial={
                "fecha": hoy,
                "fecha_registro": hoy,
                "codigo_proveedor": 0,
                "nombre_proveedor": "",
                "importe_total": "0",
                "id_deposito": id_deposito_global or id_deposito_inicial,
                "deposito_seleccion": modo_deposito,
            },
        )
        return render(request, "compras/remito_compra_form.html", {
            "form": form_remito,
            "renglones": renglones,
            "depositos": depositos_raw,
            "base_empresa": base_empresa,
            "form_alta_renglon": form,
        })
    id_art = art.get("IDArt")
    if not descripcion and art.get("Descripcion"):
        descripcion = art.get("Descripcion") or ""
    cod_art = art.get("CodigoArticulo") or codigo_articulo
    if deposito_final is None:
        messages.error(request, "Debe seleccionar un depósito.")
        hoy = date.today().isoformat()
        form_remito = RemitoCompraCabeceraForm(
            depositos_choices=depositos_choices,
            initial={
                "fecha": hoy,
                "fecha_registro": hoy,
                "codigo_proveedor": 0,
                "nombre_proveedor": "",
                "importe_total": "0",
                "id_deposito": id_deposito_inicial,
                "deposito_seleccion": modo_deposito,
            },
        )
        return render(request, "compras/remito_compra_form.html", {
            "form": form_remito,
            "renglones": renglones,
            "depositos": depositos_raw,
            "base_empresa": base_empresa,
            "form_alta_renglon": form,
        })
    orden = alta_renglon_temporal(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        id_art=id_art,
        codigo_articulo=cod_art,
        descripcion=descripcion,
        cantidad=cantidad,
        cod_deposito=deposito_final,
        precio_costo_u=precio_costo_u,
    )
    if orden is not None:
        messages.success(request, "Renglón agregado.")
        return redirect("compras:remito_compra_form")
    messages.error(request, "No se pudo agregar el renglón.")
    hoy = date.today().isoformat()
    form_remito = RemitoCompraCabeceraForm(
        depositos_choices=depositos_choices,
        initial={
            "fecha": hoy,
            "fecha_registro": hoy,
            "codigo_proveedor": 0,
            "nombre_proveedor": "",
            "importe_total": "0",
            "id_deposito": id_deposito_inicial,
            "deposito_seleccion": modo_deposito,
        },
    )
    return render(request, "compras/remito_compra_form.html", {
        "form": form_remito,
        "renglones": renglones,
        "depositos": depositos_raw,
        "base_empresa": base_empresa,
        "form_alta_renglon": form,
    })


@require_http_methods(["GET", "POST"])
def lista_comp_remito(request):
    """
    Lista de comprobantes del proveedor para cargar en Remito de compra (paridad Lista_Comp_Gral).
    GET: codigo_proveedor, tipo (oc | factura | importa_rem) → muestra tabla con comprobantes.
    POST: codigo_movimiento, tipo → importa renglones a cuerpostockp y redirige al remito.
    """
    base_empresa, id_usuario, _cod_sucursal = _session_base(request)
    if not base_empresa or id_usuario is None:
        messages.error(request, "Sesión inválida.")
        return redirect("core:dashboard")

    if request.method == "POST":
        codigo_movimiento = request.POST.get("codigo_movimiento")
        tipo = (request.POST.get("tipo") or "").strip().lower()
        if tipo not in ("oc", "factura", "importa_rem"):
            messages.error(request, "Tipo de comprobante inválido.")
            return redirect("compras:remito_compra_form")
        try:
            cod_mov = int(codigo_movimiento)
        except (TypeError, ValueError):
            messages.error(request, "Comprobante inválido.")
            return redirect("compras:remito_compra_form")
        id_deposito_usuario = (request.session.get("user") or {}).get("id_deposito")
        ok, err = importar_comprobante_remito(
            base_empresa=base_empresa,
            id_usuario=id_usuario,
            codigo_movimiento=cod_mov,
            tipo=tipo,
            id_deposito_usuario=id_deposito_usuario,
        )
        if ok:
            messages.success(request, "Comprobante importado. Revise los renglones en Remito de compra.")
            return redirect("compras:remito_compra_form")
        messages.error(request, err or "No se pudo importar el comprobante.")
        return redirect("compras:remito_compra_form")

    codigo_proveedor = request.GET.get("codigo_proveedor")
    tipo = (request.GET.get("tipo") or "oc").strip().lower()
    if tipo not in ("oc", "factura", "importa_rem"):
        tipo = "oc"
    try:
        cod_prov = int(codigo_proveedor) if codigo_proveedor else None
    except (TypeError, ValueError):
        cod_prov = None
    if not cod_prov:
        if request.GET.get("format") == "json":
            return JsonResponse({"comprobantes": [], "titulo": "", "error": "Indique el proveedor."}, status=400)
        messages.error(request, "Indique el proveedor.")
        return redirect("compras:remito_compra_form")

    comprobantes = list_comprobantes_remito(base_empresa, cod_prov, tipo)
    titulos = {
        "oc": "Lista de órdenes de compra",
        "factura": "Lista de facturas de proveedor",
        "importa_rem": "Lista de remitos del proveedor para importar",
    }
    titulo = titulos.get(tipo, "Comprobantes")

    # Respuesta JSON para uso en modal (mejor UX sin cambiar de página)
    if request.GET.get("format") == "json" or request.headers.get("Accept", "").find("application/json") >= 0:
        # Serializar para JSON: Fecha → str, Decimal → str/int
        lista = []
        for c in comprobantes:
            fecha = c.get("Fecha")
            if hasattr(fecha, "isoformat"):
                fecha = fecha.isoformat()
            elif fecha is not None:
                fecha = str(fecha)
            cod_mov = c.get("CodigoMovimiento")
            if cod_mov is not None and hasattr(cod_mov, "__int__"):
                try:
                    cod_mov = int(cod_mov)
                except (TypeError, ValueError):
                    cod_mov = str(cod_mov)
            importe = c.get("ImporteCompra")
            if importe is not None and hasattr(importe, "__float__"):
                importe = str(importe)
            lista.append({
                "CodigoMovimiento": cod_mov,
                "NroComprobante": c.get("NroComprobante") or "",
                "Fecha": fecha or "",
                "ImporteCompra": importe or "0",
            })
        return JsonResponse({"comprobantes": lista, "titulo": titulo})

    return render(request, "compras/lista_comp_remito.html", {
        "comprobantes": comprobantes,
        "tipo": tipo,
        "codigo_proveedor": cod_prov,
        "titulo": titulo,
    })
