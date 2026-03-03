# Vistas del módulo Stock (AdministraNET).
# Permisos validados con decorador; revalidación en servicio para escrituras.
import json

from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse

from core.decorators import tiene_permiso


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
def consulta_ficha_stock_view(request):
    """Consulta ficha de stock por artículo/depósito."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    context = {"base_empresa": base_empresa}
    return render(request, "stock/consulta_ficha_stock.html", context)


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
