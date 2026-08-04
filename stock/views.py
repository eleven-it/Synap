# Vistas del módulo Stock (AdministraNET).
# Permisos validados con decorador; revalidación en servicio para escrituras.
import json

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import FileResponse, Http404, HttpResponse

from core.decorators import tiene_permiso


def manual_usuario_view(request):
    """Manual de usuario Stock (HTML estático). Solo requiere sesión activa."""
    if "user" not in request.session or not request.session.get("user"):
        return redirect("login:login")
    from pathlib import Path

    manual_path = (
        Path(__file__).resolve().parent
        / "static"
        / "stock"
        / "manuales"
        / "manual_usuario_stock.html"
    )
    if not manual_path.is_file():
        raise Http404("Manual de usuario Stock no encontrado.")
    return FileResponse(
        manual_path.open("rb"),
        content_type="text/html; charset=utf-8",
    )


@tiene_permiso("stock.crear_movimiento")
def alta_movimiento_view(request):
    """Alta de movimiento de stock (CargaMovStock)."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    context = {
        "base_empresa": base_empresa,
    }
    return render(request, "stock/alta_movimiento.html", context)


@tiene_permiso("stock.consultas")
def visualiza_movimientos_view(request):
    """Listado de movimientos de stock (Visualiza_CargaMovStock) con filtros."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    id_puesto = session_user.get("id_puesto")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    from core.services.administranet_stock import (
        MOTIVOS_MOVIMIENTO,
        get_depositos,
        get_nombres_depositos,
        listar_movimientos,
    )

    # Filtros desde GET
    fecha_desde = request.GET.get("fecha_desde", "").strip() or None
    fecha_hasta = request.GET.get("fecha_hasta", "").strip() or None
    id_deposito = request.GET.get("deposito", "").strip()
    id_deposito = int(id_deposito) if id_deposito.isdigit() else None
    motivo = request.GET.get("motivo", "").strip() or None
    nro_comprobante = request.GET.get("nro_comprobante", "").strip() or None

    movimientos = listar_movimientos(
        base_empresa,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        id_deposito=id_deposito,
        motivo=motivo,
        nro_comprobante=nro_comprobante,
        limit=200,
    )

    # Nombres de depósitos para la tabla
    cods_dep = set()
    for m in movimientos:
        if m.get("deposito_origen") is not None:
            cods_dep.add(int(m["deposito_origen"]))
        if m.get("deposito_destino") is not None:
            cods_dep.add(int(m["deposito_destino"]))
    nombres_dep = get_nombres_depositos(base_empresa, list(cods_dep)) if cods_dep else {}

    for m in movimientos:
        m["nombre_dep_origen"] = nombres_dep.get(int(m["deposito_origen"]), "-") if m.get("deposito_origen") is not None else "-"
        m["nombre_dep_destino"] = nombres_dep.get(int(m["deposito_destino"]), "-") if m.get("deposito_destino") is not None else "-"

    depositos = get_depositos(base_empresa, id_puesto)

    # Opciones de agrupación (artefacto BO: múltiples campos, orden = niveles). Sin "Sin agrupación" en el multi-select
    OPCIONES_AGRUPAR = [
        ("fecha", "Fecha"),
        ("motivo_movimiento", "Motivo"),
        ("nombre_dep_origen", "Depósito origen"),
        ("nombre_dep_destino", "Depósito destino"),
        ("nombre_usuario", "Usuario"),
    ]

    movimientos_json = json.dumps(movimientos, default=str) if movimientos else "[]"

    context = {
        "base_empresa": base_empresa,
        "movimientos": movimientos,
        "movimientos_json": movimientos_json,
        "depositos": depositos,
        "motivos": MOTIVOS_MOVIMIENTO,
        "opciones_agrupar": OPCIONES_AGRUPAR,
        "filtros": {
            "fecha_desde": fecha_desde or "",
            "fecha_hasta": fecha_hasta or "",
            "deposito": id_deposito,
            "motivo": motivo or "",
            "nro_comprobante": nro_comprobante or "",
        },
    }
    return render(request, "stock/visualiza_movimientos.html", context)


@tiene_permiso("stock.consultas")
def detalle_movimiento_view(request, codigo_movimiento):
    """Detalle de un movimiento de stock (solo lectura) con renglones y enlace a PDF."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    from core.services.administranet_stock import (
        get_nombre_deposito,
        obtener_movimiento,
        obtener_renglones_movimiento,
    )

    mov = obtener_movimiento(base_empresa, codigo_movimiento)
    if not mov:
        messages.error(request, "Movimiento no encontrado.")
        return redirect("stock:visualiza_movimientos")

    renglones = obtener_renglones_movimiento(base_empresa, codigo_movimiento)
    nombre_dep_origen = get_nombre_deposito(base_empresa, mov.get("deposito_origen"))
    nombre_dep_destino = get_nombre_deposito(base_empresa, mov.get("deposito_destino"))

    context = {
        "base_empresa": base_empresa,
        "codigo_movimiento": codigo_movimiento,
        "mov": mov,
        "renglones": renglones,
        "nombre_dep_origen": nombre_dep_origen,
        "nombre_dep_destino": nombre_dep_destino,
    }
    return render(request, "stock/detalle_movimiento.html", context)


@tiene_permiso("stock.ref_movstock")
def ref_movstock_list_view(request):
    """Listado de referencias de movimiento de stock (ABMref_movstock)."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    context = {"base_empresa": base_empresa}
    return render(request, "stock/ref_movstock_list.html", context)


@tiene_permiso("stock.ref_movstock")
def ref_movstock_create_view(request):
    """Alta de referencia de movimiento (CargaRef_movstock)."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    context = {"base_empresa": base_empresa}
    return render(request, "stock/ref_movstock_form.html", context)


@tiene_permiso("stock.ref_movstock")
def ref_movstock_edit_view(request, pk):
    """Edición de referencia de movimiento."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    context = {"base_empresa": base_empresa, "id_ref_movstock": pk}
    return render(request, "stock/ref_movstock_form.html", context)


@tiene_permiso("stock.consultas")
def inventario_view(request):
    """Inventario por etapa MPR: tabla pivote Producción → Terminado + consolidado."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    from dataclasses import replace

    from stock.services.inventario_tabla import (
        build_inventario_query_string,
        consultar_inventario_tabla,
        etapas_para_ambito,
        listar_marcas_catalogo,
        parse_inventario_filtros,
        preparar_filas_inventario_presentacion,
    )

    filtros = parse_inventario_filtros(
        request.GET,
        marcas_getlist=request.GET.getlist("marcas_incluidos"),
    )
    # Texto `q` solo para filtro cliente en la grilla; SQL carga todo el ámbito.
    resultado = consultar_inventario_tabla(
        base_empresa, replace(filtros, busqueda=None)
    )
    filas = preparar_filas_inventario_presentacion(
        resultado.get("filas") or [],
        filtros.presentacion,
        base_empresa=base_empresa,
        ambito=filtros.ambito,
    )
    page = 1
    total_pages = 1
    etapas_columnas = resultado.get("etapas") or etapas_para_ambito(filtros.ambito)

    context = {
        "base_empresa": base_empresa,
        "filas": filas,
        "etapas_columnas": etapas_columnas,
        "filtros": filtros,
        "marcas_catalogo": listar_marcas_catalogo(base_empresa),
        "total_registros": resultado.get("total_registros", 0),
        "filas_cargadas": resultado.get("filas_cargadas", len(filas)),
        "truncado": resultado.get("truncado", False),
        "page": page,
        "page_size": resultado.get("page_size", 5000),
        "total_pages": total_pages,
        "sin_config_mpr": resultado.get("sin_config_mpr", False),
        "modo_presentacion": filtros.presentacion,
        "pagination_prev_qs": "",
        "pagination_next_qs": "",
        "limpiar_qs": build_inventario_query_string(filtros, clear_search=True, page=1),
    }
    return render(request, "stock/inventario.html", context)


@tiene_permiso("stock.consultas")
def consulta_avanzada_view(request):
    """Búsqueda avanzada de stock; permite abrir ajuste desde aquí."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    context = {"base_empresa": base_empresa}
    return render(request, "stock/consulta_avanzada.html", context)


@tiene_permiso("stock.consultas")
def movimiento_pdf_view(request, codigo_movimiento):
    """Descarga del comprobante de movimiento de stock en PDF (ReportLab)."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    from core.services.administranet_stock import (
        get_nombre_deposito,
        obtener_movimiento,
        obtener_renglones_movimiento,
    )

    mov = obtener_movimiento(base_empresa, codigo_movimiento)
    if not mov:
        messages.error(request, "Movimiento no encontrado.")
        return redirect("stock:visualiza_movimientos")

    renglones = obtener_renglones_movimiento(base_empresa, codigo_movimiento)

    try:
        import io

        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
        from reportlab.pdfgen import canvas

        from core.report_pdf import (
            draw_report_footer,
            draw_report_header,
            get_empresa_para_reporte,
        )

        empresa = get_empresa_para_reporte(base_empresa)
        margin = 20 * mm

        nombre_dep_origen = get_nombre_deposito(base_empresa, mov.get("deposito_origen"))
        nombre_dep_destino = get_nombre_deposito(base_empresa, mov.get("deposito_destino"))

        buf = io.BytesIO()
        p = canvas.Canvas(buf, pagesize=landscape(A4))
        # En horizontal la altura de la hoja es 210 mm
        y_content = draw_report_header(
            p, empresa, "Comprobante de Movimiento de Stock", 210 * mm
        )

        p.setFont("Helvetica", 10)
        p.drawString(margin, y_content, f"Nro: {mov.get('nro_comprobante') or '-'}  |  Fecha: {str(mov.get('fecha') or '')}  |  Motivo: {mov.get('motivo_movimiento') or '-'}")
        y_content -= 6 * mm
        p.drawString(margin, y_content, f"Dep. origen: {nombre_dep_origen}  |  Dep. destino: {nombre_dep_destino}")
        y_content -= 6 * mm
        p.drawString(margin, y_content, f"Detalle: {(mov.get('detalle') or '')[:80]}")
        y_content -= 8 * mm

        # Tabla con marcos y encabezados en negrita (más ancho en horizontal), incl. Saldo
        col_articulo = 168 * mm
        col_entrada = 28 * mm
        col_salida = 28 * mm
        col_saldo = 28 * mm
        ancho_tabla = col_articulo + col_entrada + col_salida + col_saldo
        x_fin_tabla = margin + ancho_tabla
        fila_altura = 5 * mm
        cabecera_altura = 6 * mm

        # Línea superior de la tabla
        p.setStrokeColorRGB(0.2, 0.2, 0.2)
        p.setLineWidth(0.5)
        p.line(margin, y_content, x_fin_tabla, y_content)
        y_content -= cabecera_altura

        # Encabezados de columnas (negrita)
        p.setFont("Helvetica-Bold", 10)
        p.setFillColorRGB(0, 0, 0)
        p.drawString(margin + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Artículo / Descripción")
        p.drawString(margin + col_articulo + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Entrada")
        p.drawString(margin + col_articulo + col_entrada + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Salida")
        p.drawString(margin + col_articulo + col_entrada + col_salida + 2 * mm, y_content + (cabecera_altura - 4 * mm), "Saldo")

        # Líneas verticales y línea bajo encabezado
        p.line(margin, y_content + cabecera_altura, margin, y_content)
        p.line(margin + col_articulo, y_content + cabecera_altura, margin + col_articulo, y_content)
        p.line(margin + col_articulo + col_entrada, y_content + cabecera_altura, margin + col_articulo + col_entrada, y_content)
        p.line(margin + col_articulo + col_entrada + col_salida, y_content + cabecera_altura, margin + col_articulo + col_entrada + col_salida, y_content)
        p.line(x_fin_tabla, y_content + cabecera_altura, x_fin_tabla, y_content)
        p.line(margin, y_content, x_fin_tabla, y_content)
        y_content -= fila_altura

        p.setFont("Helvetica", 10)
        for r in renglones[:30]:
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

        # Línea inferior de la tabla
        p.line(margin, y_content, x_fin_tabla, y_content)

        if len(renglones) > 30:
            y_content -= 4 * mm
            p.setFont("Helvetica", 9)
            p.drawString(margin, y_content, f"... y {len(renglones) - 30} renglones más.")

        draw_report_footer(p)
        p.showPage()
        p.save()
        buf.seek(0)
        response = HttpResponse(buf.read(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="movimiento-stock-{codigo_movimiento}.pdf"'
        return response
    except ImportError:
        response = HttpResponse(b"PDF no disponible (ReportLab no instalado).", content_type="text/plain")
        response["Content-Disposition"] = 'attachment; filename="movimiento-stock.txt"'
        return response


@tiene_permiso("stock.inventario_fisico.gestionar")
def inventario_fisico_list_view(request):
    """Listado de campañas de inventario físico."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    from stock.services.inventario_fisico import (
        etiquetar_contadores,
        listar_campanas,
        listar_contadores_candidatos,
        obtener_progreso_campana,
    )

    campanas = listar_campanas(base_empresa)
    candidatos = listar_contadores_candidatos(base_empresa)
    for c in campanas:
        c["progreso"] = obtener_progreso_campana(base_empresa, c["id_campana"])
        c["contadores_detalle"] = etiquetar_contadores(c.get("contadores", []), candidatos)
    context = {
        "base_empresa": base_empresa,
        "campanas": campanas,
    }
    return render(request, "stock/inventario_fisico/listado.html", context)


@tiene_permiso("stock.inventario_fisico.gestionar")
def inventario_fisico_crear_view(request):
    """Alta de campaña de inventario físico."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    id_usuario = session_user.get("id_usuario")
    if not base_empresa or not id_usuario:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    from stock.services.inventario_fisico import (
        ESTADO_EN_CONTEO,
        asignar_contadores,
        crear_campana,
        listar_contadores_candidatos,
        listar_depositos_elegibles,
        parse_ids_contadores,
        transicionar_campana,
    )

    depositos = listar_depositos_elegibles(base_empresa)
    contadores_disponibles = listar_contadores_candidatos(base_empresa)

    if request.method == "POST":
        fecha = request.POST.get("fecha", "").strip()
        seleccionados = []
        for raw in request.POST.getlist("depositos"):
            try:
                seleccionados.append(int(raw))
            except (TypeError, ValueError):
                continue
        contadores_ids = parse_ids_contadores(
            request.POST.getlist("contadores") + [request.POST.get("contadores_texto", "")]
        )
        accion = request.POST.get("accion", "").strip()
        abrir_conteo = accion == "crear_abrir" or request.POST.get("abrir_conteo") == "1"
        ok, result = crear_campana(
            base_empresa,
            fecha=fecha,
            depositos_ids=seleccionados,
            id_usuario_alta=int(id_usuario),
        )
        if not ok:
            messages.error(request, result.get("error", "No se pudo crear la campaña."))
        else:
            id_campana = result["id_campana"]
            if contadores_ids:
                ok_asig, res_asig = asignar_contadores(base_empresa, id_campana, contadores_ids)
                if not ok_asig:
                    messages.warning(
                        request,
                        res_asig.get("error", "No se pudieron asignar los contadores."),
                    )
            if abrir_conteo:
                if contadores_ids:
                    transicionar_campana(base_empresa, id_campana, ESTADO_EN_CONTEO)
                    messages.success(
                        request,
                        "Campaña creada y abierta para conteo (EnConteo).",
                    )
                else:
                    messages.warning(
                        request,
                        "Campaña creada como borrador: asigná contadores antes de abrir el conteo.",
                    )
            else:
                messages.success(request, "Campaña de inventario físico creada como borrador.")
            return redirect("stock:inventario_fisico_monitor", id_campana=id_campana)

    context = {
        "base_empresa": base_empresa,
        "depositos": depositos,
        "contadores_disponibles": contadores_disponibles,
    }
    return render(request, "stock/inventario_fisico/crear.html", context)


@tiene_permiso("stock.inventario_fisico.gestionar")
def inventario_fisico_monitor_view(request, id_campana):
    """Monitor básico de progreso de campaña."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    from stock.services.inventario_fisico import (
        ESTADO_EN_CONTEO,
        ESTADO_EN_REVISION,
        anular_campana,
        asignar_contadores,
        etiquetar_contadores,
        listar_contadores_candidatos,
        obtener_campana,
        obtener_progreso_campana,
        obtener_resumen_monitor,
        parse_ids_contadores,
        transicionar_campana,
    )

    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        messages.error(request, "Campaña no encontrada.")
        return redirect("stock:inventario_fisico_list")

    if request.method == "POST":
        accion = request.POST.get("accion", "").strip()
        if accion == "cerrar_conteo":
            ok, result = transicionar_campana(base_empresa, id_campana, ESTADO_EN_REVISION)
            if ok:
                messages.success(request, "Conteo cerrado. Campaña en revisión.")
                campana = obtener_campana(base_empresa, id_campana)
            else:
                messages.error(request, result.get("error", "No se pudo cerrar el conteo."))
        elif accion == "abrir_conteo" and campana["estado"] != ESTADO_EN_CONTEO:
            ok, result = transicionar_campana(base_empresa, id_campana, ESTADO_EN_CONTEO)
            if ok:
                messages.success(request, "Campaña abierta para conteo.")
                campana = obtener_campana(base_empresa, id_campana)
            else:
                messages.error(request, result.get("error", "No se pudo abrir el conteo."))
        elif accion == "reasignar":
            contadores_ids = parse_ids_contadores(
                request.POST.getlist("contadores") + [request.POST.get("contadores_texto", "")]
            )
            ok, result = asignar_contadores(base_empresa, id_campana, contadores_ids)
            if ok:
                messages.success(request, "Contadores actualizados.")
                campana = obtener_campana(base_empresa, id_campana)
            else:
                messages.error(request, result.get("error", "No se pudieron asignar contadores."))
        elif accion == "anular":
            ok, result = anular_campana(base_empresa, id_campana)
            if ok:
                messages.success(request, "Campaña anulada.")
                return redirect("stock:inventario_fisico_list")
            messages.error(request, result.get("error", "No se pudo anular."))

    progreso = obtener_progreso_campana(base_empresa, id_campana)
    resumen = obtener_resumen_monitor(base_empresa, id_campana)
    contadores_disponibles = listar_contadores_candidatos(base_empresa)
    contadores_detalle = etiquetar_contadores(
        campana.get("contadores", []), contadores_disponibles
    )
    context = {
        "base_empresa": base_empresa,
        "campana": campana,
        "progreso": progreso,
        "resumen": resumen,
        "contadores_disponibles": contadores_disponibles,
        "contadores_detalle": contadores_detalle,
    }
    return render(request, "stock/inventario_fisico/monitor.html", context)


@tiene_permiso("stock.inventario_fisico.gestionar")
def inventario_fisico_analizador_view(request, id_campana):
    """Analizador de diferencias (supervisor)."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    from stock.services.inventario_fisico import (
        ESTADO_BORRADOR,
        ESTADO_EN_CONTEO,
        build_analizador_query_string,
        obtener_campana,
        obtener_resumen_monitor,
        listar_lineas_analizador,
        parse_marcas_incluidos,
    )
    from stock.services.inventario_tabla import listar_marcas_catalogo

    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        messages.error(request, "Campaña no encontrada.")
        return redirect("stock:inventario_fisico_list")

    filtro = request.GET.get("filtro", "").strip().lower()
    if filtro not in ("", "faltante", "sobrante", "con_diferencia"):
        filtro = ""

    marcas_incluidos = parse_marcas_incluidos(request.GET.getlist("marcas_incluidos"))

    lineas = listar_lineas_analizador(
        base_empresa,
        id_campana,
        filtro=filtro or None,
        marcas_incluidos=marcas_incluidos or None,
    )
    resumen = obtener_resumen_monitor(base_empresa, id_campana)
    puede_autorizar = (
        campana["estado"] == "EnRevision"
        and not resumen.get("bloqueo_autorizar")
        and not resumen.get("bloqueo_estado")
    )

    context = {
        "base_empresa": base_empresa,
        "campana": campana,
        "lineas": lineas,
        "resumen": resumen,
        "filtro": filtro,
        "marcas_catalogo": listar_marcas_catalogo(base_empresa),
        "marcas_incluidos": marcas_incluidos,
        "analizador_qs_todas": build_analizador_query_string(marcas_incluidos=marcas_incluidos),
        "analizador_qs_faltante": build_analizador_query_string(
            filtro="faltante", marcas_incluidos=marcas_incluidos
        ),
        "analizador_qs_sobrante": build_analizador_query_string(
            filtro="sobrante", marcas_incluidos=marcas_incluidos
        ),
        "analizador_qs_con_diferencia": build_analizador_query_string(
            filtro="con_diferencia", marcas_incluidos=marcas_incluidos
        ),
        "puede_autorizar": puede_autorizar,
        "puede_anular": campana["estado"] in (ESTADO_BORRADOR, ESTADO_EN_CONTEO),
    }
    return render(request, "stock/inventario_fisico/analizador.html", context)


@tiene_permiso("stock.inventario_fisico.gestionar")
def inventario_fisico_linea_view(request, id_campana, id_linea):
    """Detalle de línea con eventos de conteo."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")

    from stock.services.inventario_fisico import (
        obtener_campana,
        obtener_linea_analizador,
        listar_eventos_linea,
    )

    campana = obtener_campana(base_empresa, id_campana)
    if not campana:
        messages.error(request, "Campaña no encontrada.")
        return redirect("stock:inventario_fisico_list")

    linea = obtener_linea_analizador(base_empresa, id_campana, id_linea)
    if not linea:
        messages.error(request, "Línea no encontrada.")
        return redirect("stock:inventario_fisico_analizador", id_campana=id_campana)

    eventos = listar_eventos_linea(
        base_empresa,
        id_campana,
        linea["id_articulo"],
        linea["id_deposito"],
    )
    context = {
        "campana": campana,
        "linea": linea,
        "eventos": eventos,
    }
    return render(request, "stock/inventario_fisico/linea_detalle.html", context)
