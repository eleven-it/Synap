"""Vistas web Self-Checkout."""
import json
import base64
from django.shortcuts import render, redirect
from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.core.exceptions import PermissionDenied

from .permissions import has_any_self_checkout_permission, has_permission
from .db import get_base_empresa_from_request, mysql_cursor


def has_self_checkout_admin(user, base_empresa: str) -> bool:
    """True si el usuario tiene permiso self_checkout.admin."""
    return has_permission(user, 'self_checkout.admin', base_empresa)


def has_self_checkout_supervisor(user, base_empresa: str) -> bool:
    """True si el usuario tiene permiso self_checkout.supervisor o admin."""
    return has_permission(user, 'self_checkout.supervisor', base_empresa)


from .services.config_options_service import listar_puntos_venta, listar_depositos, listar_kiosks, listar_viajantes
from .services.talonarios_service import (
    listar_talonarios_por_pv,
    obtener_talonario,
    actualizar_talonario,
    tipos_faltantes_para_pv,
    crear_talonario,
    TIPOS_COMPROBANTE,
)
from .services.pv_service import crear_punto_venta as svc_crear_punto_venta


def _require_base_and_permission(request, permission_check=None):
    """
    Exige usuario logueado y sesión (session['user']) con base_empresa; luego verifica permiso.
    Si no hay usuario o sesión, redirige al login. Retorna (base_empresa, None) o (None, response).
    """
    if not request.user.is_authenticated:
        return None, redirect(f'/login/?next={request.get_full_path()}')
    session_user = request.session.get('user') or {}
    if not session_user:
        return None, redirect('/login/')
    base = get_base_empresa_from_request(request)
    if not base:
        return None, redirect('/login/')
    if not has_any_self_checkout_permission(request.user, base):
        raise PermissionDenied('Sin permiso para Self-Checkout')
    if permission_check and not permission_check(request.user, base):
        raise PermissionDenied('Sin permiso para esta acción')
    return base, None


def index_view(request):
    """
    Selector de kiosco (estilo TPV): listar kioscos y abrir uno.
    Un kiosco solo puede estar abierto en una máquina (se valida con acquire).
    """
    base, err = _require_base_and_permission(request)
    if err:
        return err
    return render(request, 'self_checkout/selector_kiosco.html', {
        'base_empresa': base,
    })


def kiosco_view(request, kiosk_id):
    """
    Pantalla principal del autoservicio.
    La sesión del kiosco se adquiere desde el frontend (acquire + heartbeat + release).
    """
    base, err = _require_base_and_permission(request)
    if err:
        return err
    logo_url = getattr(settings, 'SELF_CHECKOUT_LOGO_URL', '') or ''
    # Teclado virtual en pantalla: configurable por URL (?virtual_keyboard=1) o futuro por kiosk
    use_virtual_keyboard = request.GET.get('virtual_keyboard', '').strip().lower() in ('1', 'true', 'yes')
    from self_checkout.fe_config import get_fe_config
    from self_checkout.permissions import has_permission
    from self_checkout.services.kiosk_service import KioskSessionService
    fe_cfg = get_fe_config(base_empresa=base)
    modo_homologacion = fe_cfg.get('homo', False)
    session_user = request.session.get('user') or {}
    is_supervisor = has_permission(request.user, 'self_checkout.supervisor', base) or has_permission(session_user, 'self_checkout.supervisor', base)
    kiosk_svc = KioskSessionService(base)
    kiosk_config = kiosk_svc.get_kiosk_config(kiosk_id)
    enviar_factura_email = bool(kiosk_config.get('enviar_factura_email', 1) if kiosk_config else True)
    from self_checkout.services.empresa_fiscal_service import emisor_emite_solo_factura_c
    solo_factura_c = emisor_emite_solo_factura_c(base)
    return render(request, 'self_checkout/kiosco.html', {
        'kiosk_id': kiosk_id,
        'base_empresa': {'logo': logo_url},
        'use_virtual_keyboard': use_virtual_keyboard,
        'modo_homologacion': modo_homologacion,
        'is_supervisor': is_supervisor,
        'enviar_factura_email': enviar_factura_email,
        'solo_factura_c': solo_factura_c,
    })


# --- Configuración (solo admin) ---


@require_http_methods(['GET'])
def config_list(request):
    """Lista kioscos configurados. Solo self_checkout.admin."""
    base, err = _require_base_and_permission(request, has_self_checkout_admin)
    if err:
        return err
    kiosks = listar_kiosks(base)
    sucursales_svc = __import__('core.services.administranet_sucursales', fromlist=['AdministraNETSucursalesService']).AdministraNETSucursalesService()
    sucursales = sucursales_svc.listar_sucursales(base) if base else []
    sucursales_by_id = {s['id_sucursal']: s.get('nombre_sucursal', s.get('desc_sucursal', str(s['id_sucursal']))) for s in sucursales}
    pvs = listar_puntos_venta(base)
    pv_by_id = {p['id_punto_venta']: p.get('nro_punto_venta', str(p['id_punto_venta'])) for p in pvs}
    for k in kiosks:
        k['nombre_sucursal'] = sucursales_by_id.get(k['id_sucursal'], str(k['id_sucursal']))
        k['nro_pv'] = pv_by_id.get(k['id_punto_venta'], str(k['id_punto_venta']))
    return render(request, 'self_checkout/config_list.html', {
        'kiosks': kiosks,
    })


# --- Puntos de venta y talonarios (fiel a VB6 ABMTalonario / CargaTalonarios) ---


@require_http_methods(['GET'])
def talonarios_list(request):
    """Lista talonarios por punto de venta. Solo self_checkout.admin."""
    base, err = _require_base_and_permission(request, has_self_checkout_admin)
    if err:
        return err
    pvs = listar_puntos_venta(base)
    id_pv = request.GET.get('id_punto_venta')
    id_pv = int(id_pv) if id_pv and str(id_pv).isdigit() else (pvs[0]['id_punto_venta'] if pvs else None)
    talonarios = listar_talonarios_por_pv(base, id_pv) if id_pv else []
    pv_by_id = {p['id_punto_venta']: p.get('nro_punto_venta', str(p['id_punto_venta'])) for p in pvs}
    tipos_faltantes = tipos_faltantes_para_pv(base, id_pv) if id_pv else []
    id_sucursal_pv = None
    if id_pv and pvs:
        for p in pvs:
            if p.get('id_punto_venta') == id_pv:
                id_sucursal_pv = p.get('id_sucursal')
                break
    return render(request, 'self_checkout/talonarios_list.html', {
        'puntos_venta': pvs,
        'id_punto_venta': id_pv,
        'id_sucursal_pv': id_sucursal_pv,
        'talonarios': talonarios,
        'pv_label': pv_by_id.get(id_pv, str(id_pv)) if id_pv else '',
        'tipos_faltantes': tipos_faltantes,
    })


@require_http_methods(['GET', 'POST'])
def talonarios_edit(request, id_punto_venta: int, tipo_comprobante: str):
    """Modificar numeración de un talonario (como CargaTalonarios)."""
    base, err = _require_base_and_permission(request, has_self_checkout_admin)
    if err:
        return err
    talon = obtener_talonario(base, id_punto_venta, tipo_comprobante)
    if not talon:
        raise Http404('Talonario no encontrado')
    if request.method == 'POST':
        nro = request.POST.get('Nro')
        nro_inic = request.POST.get('NroInic')
        nro_final = request.POST.get('NroFinal')
        nro_cai = request.POST.get('NroCAI') or ''
        fecha_cai = request.POST.get('FechaCAI') or None
        nro_credito = request.POST.get('Nro_Credito')
        try:
            nro = int(nro) if nro else talon['Nro']
            nro_inic = int(nro_inic) if nro_inic else talon.get('NroInic', 1)
            nro_final = int(nro_final) if nro_final else talon.get('NroFinal', 5000)
            nro_credito = int(nro_credito) if nro_credito else talon.get('Nro_Credito', 1)
        except (TypeError, ValueError):
            messages.error(request, 'Números inválidos.')
            return render(request, 'self_checkout/talonarios_edit.html', {'talon': talon, 'id_punto_venta': id_punto_venta, 'tipo_comprobante': tipo_comprobante})
        if fecha_cai:
            try:
                from datetime import datetime
                fecha_cai = datetime.strptime(fecha_cai, '%Y-%m-%d').date()
            except ValueError:
                fecha_cai = None
        ok = actualizar_talonario(base, id_punto_venta, tipo_comprobante, nro, nro_inic, nro_final, nro_cai, fecha_cai, nro_credito)
        if ok:
            messages.success(request, f'Talonario {tipo_comprobante} actualizado.')
            from django.urls import reverse
            return redirect(reverse('self_checkout:talonarios_list') + f'?id_punto_venta={id_punto_venta}')
        messages.error(request, 'No se pudo actualizar el talonario.')
    return render(request, 'self_checkout/talonarios_edit.html', {
        'talon': talon,
        'id_punto_venta': id_punto_venta,
        'tipo_comprobante': tipo_comprobante,
    })


@require_http_methods(['GET', 'POST'])
def talonarios_create(request):
    """Agregar talonario para un PV (tipo que aún no tenga)."""
    base, err = _require_base_and_permission(request, has_self_checkout_admin)
    if err:
        return err
    pvs = listar_puntos_venta(base)
    id_pv = request.GET.get('id_punto_venta') or (request.POST.get('id_punto_venta'))
    id_pv = int(id_pv) if id_pv and str(id_pv).isdigit() else (pvs[0]['id_punto_venta'] if pvs else None)
    tipos_faltantes = tipos_faltantes_para_pv(base, id_pv) if id_pv else []
    if request.method == 'POST' and id_pv:
        tipo_comprobante = request.POST.get('TipoComprobante')
        nro_inic = request.POST.get('NroInic', '1')
        nro_final = request.POST.get('NroFinal', '5000')
        nro_cai = request.POST.get('NroCAI') or '00000000000000'
        fecha_cai = request.POST.get('FechaCAI') or None
        if tipo_comprobante not in tipos_faltantes:
            messages.error(request, 'Tipo de comprobante no válido o ya existe para este PV.')
        else:
            try:
                nro_inic = int(nro_inic)
                nro_final = int(nro_final)
            except (TypeError, ValueError):
                nro_inic, nro_final = 1, 5000
            if fecha_cai:
                try:
                    from datetime import datetime
                    fecha_cai = datetime.strptime(fecha_cai, '%Y-%m-%d').date()
                except ValueError:
                    fecha_cai = None
            if crear_talonario(base, id_pv, tipo_comprobante, nro_inic, nro_final, nro_cai, fecha_cai):
                messages.success(request, f'Talonario {tipo_comprobante} creado.')
                return redirect('self_checkout:talonarios_list')
            messages.error(request, 'No se pudo crear el talonario.')
    return render(request, 'self_checkout/talonarios_create.html', {
        'puntos_venta': pvs,
        'id_punto_venta': id_pv,
        'tipos_faltantes': tipos_faltantes,
    })


@require_http_methods(['GET', 'POST'])
def punto_venta_create(request):
    """Crear nuevo punto de venta y sus 38 talonarios (fiel a VB6 CargaPV.frm)."""
    base, err = _require_base_and_permission(request, has_self_checkout_admin)
    if err:
        return err
    sucursales_svc = __import__('core.services.administranet_sucursales', fromlist=['AdministraNETSucursalesService']).AdministraNETSucursalesService()
    sucursales = sucursales_svc.listar_sucursales(base) if base else []
    if request.method == 'POST':
        nro_pv = (request.POST.get('nro_punto_venta') or '').strip()
        id_sucursal = request.POST.get('id_sucursal')
        try:
            id_sucursal = int(id_sucursal) if id_sucursal else None
        except (TypeError, ValueError):
            id_sucursal = None
        id_creado, error_msg = svc_crear_punto_venta(base, nro_pv, id_sucursal)
        if error_msg:
            messages.error(request, error_msg)
            return render(request, 'self_checkout/punto_venta_create.html', {
                'sucursales': sucursales,
                'nro_punto_venta': nro_pv,
                'id_sucursal': id_sucursal,
            })
        messages.success(request, f'Punto de venta PV {nro_pv} creado con sus talonarios.')
        from django.urls import reverse
        return redirect(reverse('self_checkout:talonarios_list') + f'?id_punto_venta={id_creado}')
    return render(request, 'self_checkout/punto_venta_create.html', {
        'sucursales': sucursales,
    })


@require_http_methods(['GET'])
def carritos_pendientes_view(request):
    """
    Lista carritos con pago confirmado en Mercado Pago que aún no tienen comprobante emitido.
    Antes de listar, sincroniza con Mercado Pago: consulta pagos aprobados e imputa a carritos
    abiertos/abandonados que tengan external_reference cart_X_pi_Y, para que no queden pagos
    reales sin reflejar en la pantalla.
    Condiciones para aparecer:
    - estado = 'pago_aprobado'
    - Al menos un self_checkout_payment_intent con estado = 'aprobado' (cobro real en MP).
    - created_at en los últimos 90 días.
    Si MySQL no está accesible, se muestra "Fuera de servicio" con modal y opción de reintentar.
    """
    base, err = _require_base_and_permission(request, has_self_checkout_supervisor)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    from mercadopago.services.payment_service import sincronizar_pagos_desde_mp
    import MySQLdb

    # Sincronizar pagos aprobados desde MP con carritos locales (abiertos/abandonados)
    sync_count, sync_error = sincronizar_pagos_desde_mp(base_empresa=base, dias=30, limit=100)
    if sync_error:
        messages.warning(request, f"No se pudo sincronizar con Mercado Pago: {sync_error}")
    elif sync_count > 0:
        messages.success(request, f"Se actualizaron {sync_count} carrito(s) con pagos aprobados desde Mercado Pago.")

    mysql_connection_error = None
    carritos = []
    try:
        with mysql_cursor(base, dict_cursor=True) as c:
            try:
                c.execute("""
                    SELECT sc.id, sc.kiosk_id, sc.id_sucursal, sc.id_punto_venta, sc.total, sc.id_cliente,
                           sc.email, sc.cuit, sc.tipo_comprobante, sc.created_at, sc.estado,
                           sc.ultimo_error_confirmacion,
                           si.nro_comprobante AS nro_factura,
                           EXISTS(SELECT 1 FROM self_checkout_payment_intent pi WHERE pi.cart_id = sc.id) AS tiene_pi,
                           EXISTS(SELECT 1 FROM self_checkout_payment_intent pi WHERE pi.cart_id = sc.id AND pi.estado = 'aprobado') AS pi_aprobado,
                           EXISTS(SELECT 1 FROM mercadopago_transaction mt WHERE mt.cart_id = sc.id) AS pago_mp
                    FROM self_checkout_cart sc
                    LEFT JOIN self_checkout_invoice si ON si.cart_id = sc.id
                    WHERE sc.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                    AND sc.estado IN ('pago_aprobado', 'error_confirmacion', 'borrador', 'pago_pendiente', 'confirmado')
                    AND (
                        (sc.estado = 'pago_aprobado' AND EXISTS (
                            SELECT 1 FROM self_checkout_payment_intent pi
                            WHERE pi.cart_id = sc.id AND pi.estado = 'aprobado'
                        ))
                        OR sc.estado = 'error_confirmacion'
                        OR (sc.estado = 'borrador')
                        OR (sc.estado = 'pago_pendiente')
                        OR (sc.estado = 'confirmado' AND si.id IS NOT NULL)
                    )
                    ORDER BY sc.created_at DESC
                    LIMIT 200
                """)
            except MySQLdb.OperationalError as col_err:
                err_str = str(col_err)
                if 'ultimo_error_confirmacion' in err_str or 'mercadopago_transaction' in err_str:
                    c.execute("""
                        SELECT sc.id, sc.kiosk_id, sc.id_sucursal, sc.id_punto_venta, sc.total, sc.id_cliente,
                               sc.email, sc.cuit, sc.tipo_comprobante, sc.created_at, sc.estado,
                               NULL AS ultimo_error_confirmacion,
                               si.nro_comprobante AS nro_factura,
                               EXISTS(SELECT 1 FROM self_checkout_payment_intent pi WHERE pi.cart_id = sc.id) AS tiene_pi,
                               EXISTS(SELECT 1 FROM self_checkout_payment_intent pi WHERE pi.cart_id = sc.id AND pi.estado = 'aprobado') AS pi_aprobado,
                               0 AS pago_mp
                        FROM self_checkout_cart sc
                        LEFT JOIN self_checkout_invoice si ON si.cart_id = sc.id
                        WHERE sc.created_at >= DATE_SUB(NOW(), INTERVAL 90 DAY)
                        AND sc.estado IN ('pago_aprobado', 'error_confirmacion', 'borrador', 'pago_pendiente', 'confirmado')
                        AND (
                            (sc.estado = 'pago_aprobado' AND EXISTS (
                                SELECT 1 FROM self_checkout_payment_intent pi
                                WHERE pi.cart_id = sc.id AND pi.estado = 'aprobado'
                            ))
                            OR sc.estado = 'error_confirmacion'
                            OR (sc.estado = 'borrador')
                            OR (sc.estado = 'pago_pendiente')
                            OR (sc.estado = 'confirmado' AND si.id IS NOT NULL)
                        )
                        ORDER BY sc.created_at DESC
                        LIMIT 200
                    """)
                else:
                    raise
            carritos = c.fetchall()
    except MySQLdb.OperationalError as e:
        mysql_connection_error = str(e)
    for c in carritos:
        if c.get('created_at'):
            c['created_at_str'] = c['created_at'].strftime('%d/%m/%Y %H:%M') if hasattr(c['created_at'], 'strftime') else str(c['created_at'])
        else:
            c['created_at_str'] = '—'
    return render(request, 'self_checkout/carritos_pendientes.html', {
        'carritos': carritos,
        'mysql_connection_error': mysql_connection_error,
    })


@require_http_methods(['GET', 'POST'])
def config_create(request):
    """Crear kiosco. Solo self_checkout.admin. GET acepta ?id_punto_venta=&id_sucursal= para prellenar."""
    base, err = _require_base_and_permission(request, has_self_checkout_admin)
    if err:
        return err
    sucursales_svc = __import__('core.services.administranet_sucursales', fromlist=['AdministraNETSucursalesService']).AdministraNETSucursalesService()
    sucursales = sucursales_svc.listar_sucursales(base)
    pvs = listar_puntos_venta(base)
    depositos = listar_depositos(base)
    viajantes = listar_viajantes(base)
    form_data = {}
    if request.method == 'GET':
        id_pv = request.GET.get('id_punto_venta')
        id_suc = request.GET.get('id_sucursal')
        if id_pv and str(id_pv).isdigit():
            form_data['id_punto_venta'] = int(id_pv)
        if id_suc and str(id_suc).isdigit():
            form_data['id_sucursal'] = int(id_suc)
    if request.method == 'POST':
        kiosk_id = (request.POST.get('kiosk_id') or '').strip()
        id_sucursal = request.POST.get('id_sucursal')
        id_punto_venta = request.POST.get('id_punto_venta')
        id_deposito = request.POST.get('id_deposito')
        cod_viajante_raw = request.POST.get('cod_viajante')
        cod_viajante = int(cod_viajante_raw) if cod_viajante_raw and cod_viajante_raw.strip() else None
        modo_rfid = (request.POST.get('modo_rfid') or 'delta').strip()
        enviar_factura_email = 1 if request.POST.get('enviar_factura_email') == '1' else 0
        if not kiosk_id or not id_sucursal or not id_punto_venta or not id_deposito:
            messages.error(request, 'Completá kiosk_id, sucursal, punto de venta y depósito.')
            form_data = dict(request.POST)
            if id_sucursal:
                form_data['id_sucursal'] = id_sucursal
            if id_punto_venta:
                form_data['id_punto_venta'] = id_punto_venta
            return render(request, 'self_checkout/config_form.html', {
                'sucursales': sucursales, 'puntos_venta': pvs, 'depositos': depositos, 'viajantes': viajantes,
                'form_data': form_data,
            })
        from self_checkout.db import mysql_cursor
        try:
            with mysql_cursor(base) as c:
                c.execute("""
                    INSERT INTO self_checkout_kiosk (kiosk_id, id_sucursal, id_punto_venta, id_deposito, cod_viajante, modo_rfid, enviar_factura_email)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, [kiosk_id, int(id_sucursal), int(id_punto_venta), int(id_deposito), cod_viajante, modo_rfid, enviar_factura_email])
            messages.success(request, f'Kiosco "{kiosk_id}" creado. El PV está asociado a AFIP/talonarios.')
            return redirect('self_checkout:config_list')
        except Exception as e:
            messages.error(request, f'Error al guardar: {e}')
            return render(request, 'self_checkout/config_form.html', {
                'sucursales': sucursales, 'puntos_venta': pvs, 'depositos': depositos, 'viajantes': viajantes,
                'form_data': request.POST,
            })
    return render(request, 'self_checkout/config_form.html', {
        'sucursales': sucursales, 'puntos_venta': pvs, 'depositos': depositos, 'viajantes': viajantes,
        'form_data': form_data,
        'editing': False,
    })


def ticket_print_view(request, cart_id):
    """
    Renderiza el ticket para impresión con todos los datos AFIP obligatorios.
    Soporta FA y FB.
    """
    base, err = _require_base_and_permission(request)
    if err:
        return err
    
    ticket_data = _get_ticket_data(base, cart_id)
    if not ticket_data:
        raise Http404('Comprobante no encontrado')
    
    return render(request, 'self_checkout/ticket_print.html', ticket_data)


def _get_ticket_data(base_empresa: str, cart_id: int) -> dict:
    """
    Obtiene todos los datos necesarios para el ticket desde la base de datos.
    Incluye: empresa, comprobante, cliente, items, totales, CAE, QR.
    """
    # 1. Datos del carrito y factura
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        c.execute("""
            SELECT 
                sc.id, sc.kiosk_id, sc.id_sucursal, sc.id_punto_venta, sc.id_deposito,
                sc.estado, sc.id_cliente, sc.email, sc.cuit, sc.tipo_comprobante,
                sc.codigo_movimiento, sc.id_cuentacliente, sc.subtotal, sc.total, sc.confirmed_at,
                si.cae, si.vto_cae, si.nro_comprobante, si.fe_regimen
            FROM self_checkout_cart sc
            LEFT JOIN self_checkout_invoice si ON si.cart_id = sc.id
            WHERE sc.id = %s AND sc.estado = 'confirmado'
        """, [cart_id])
        cart = c.fetchone()
    
    if not cart:
        return None
    
    # 2. Items del carrito
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        c.execute("""
            SELECT descripcion, cantidad, precio_unitario, importe_total, alicuota_iva, importe_iva
            FROM self_checkout_cart_item
            WHERE cart_id = %s
            ORDER BY orden, id
        """, [cart_id])
        items = c.fetchall()
    
    # 3. Datos del cliente (si no es consumidor final)
    cliente = _get_cliente_data(base_empresa, cart)
    
    # 4. Datos de la empresa (emisor)
    empresa = _get_empresa_data(base_empresa, cart.get('id_sucursal'))
    
    # 5. Formatear número de comprobante
    nro_comp = cart.get('nro_comprobante') or ''
    id_pv = cart.get('id_punto_venta') or 1
    nro_formateado = f"{int(id_pv):04d}-{int(nro_comp):08d}" if nro_comp else ""
    
    # 6. Tipo de comprobante (FA, FB, FC según emisor y cliente - AFIP)
    tipo = cart.get('tipo_comprobante') or 'FB'
    tipo_letra = tipo[-1] if tipo and len(tipo) >= 1 else 'B'  # FA->A, FB->B, FC->C
    tipo_nombre = {"FA": "FACTURA A", "FB": "FACTURA B", "FC": "FACTURA C"}.get(tipo, "FACTURA B")
    # 7. Calcular IVAs por alícuota (solo FA discrimina; FB/FC IVA incluido)
    ivas = _calcular_ivas(items) if tipo == 'FA' else []
    
    # 8. Fecha de emisión
    fecha = cart.get('confirmed_at')
    fecha_str = fecha.strftime('%d/%m/%Y %H:%M') if fecha else ''
    
    # 9. Generar URL de QR para verificación AFIP
    qr_data = _generar_qr_afip(empresa, cart, nro_formateado) if cart.get('cae') else None
    
    # 10. Importe en letras (opcional)
    importe_letras = _numero_a_letras(float(cart.get('total') or 0))
    
    return {
        'tipo_comprobante': tipo,
        'tipo_comprobante_letra': tipo_letra,
        'tipo_comprobante_nombre': tipo_nombre,
        'nro_comprobante_formateado': nro_formateado,
        'fecha_emision': fecha_str,
        'empresa': empresa,
        'cliente': cliente,
        'items': items,
        'subtotal': cart.get('subtotal') or 0,
        'total': cart.get('total') or 0,
        'ivas': ivas,
        'otros_impuestos': 0,
        'cae': cart.get('cae'),
        'vto_cae': _formatear_fecha_cae(cart.get('vto_cae')),
        'fe_regimen': cart.get('fe_regimen'),
        'qr_data': qr_data,
        'importe_letras': importe_letras,
    }


def _get_empresa_data(base_empresa: str, id_sucursal: int) -> dict:
    """Obtiene datos del emisor (empresa) desde datosempresa (administraNET) o tabla empresa."""
    # Mapeo IDIva (datosempresa) a texto condición IVA para ticket
    _CONDICION_IVA_LABEL = {
        1: "IVA RESPONSABLE INSCRIPTO",
        2: "IVA RESPONSABLE NO INSCRIPTO",
        3: "IVA NO RESPONSABLE",
        4: "IVA SUJETO EXENTO",
        6: "RESPONSABLE MONOTRIBUTO",
        7: "SUJETO NO CATEGORIZADO",
    }
    empresa = {
        'razon_social': 'EMPRESA NO CONFIGURADA',
        'domicilio': '',
        'cuit': '',
        'cuit_formateado': '',
        'condicion_iva': 'IVA RESPONSABLE INSCRIPTO',
        'id_iva': None,
        'nro_iibb': '',
        'inicio_actividades': '',
        'telefono': '',
        'email': '',
        'web': '',
    }
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            # Primero intentar datosempresa (origen administraNET VB6: Nombre, CUIT, IDIva)
            c.execute("""
                SELECT Nombre, Domicilio, CUIT, IDIva AS id_iva, Telefono, Email, IngBrutos, InicioAct
                FROM DatosEmpresa WHERE id_empresa = 1 LIMIT 1
            """)
            row = c.fetchone()
            if not row:
                c.execute("""
                    SELECT Nombre, Domicilio, CUIT, IDIVA AS id_iva, Telefono, Email, IngBrutos, InicioAct
                    FROM datosempresa WHERE id_empresa = 1 LIMIT 1
                """)
                row = c.fetchone()
            if row:
                empresa['razon_social'] = (row.get('Nombre') or '').strip() or empresa['razon_social']
                empresa['domicilio'] = (row.get('Domicilio') or '').strip()
                cuit = str(row.get('CUIT') or row.get('cuit') or '').replace('-', '').replace(' ', '')
                empresa['cuit'] = cuit
                if len(cuit) == 11:
                    empresa['cuit_formateado'] = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"
                id_iva = row.get('id_iva')
                if id_iva is not None:
                    empresa['id_iva'] = int(id_iva)
                    empresa['condicion_iva'] = _CONDICION_IVA_LABEL.get(int(id_iva), empresa['condicion_iva'])
                empresa['nro_iibb'] = (row.get('IngBrutos') or '').strip()
                empresa['inicio_actividades'] = str(row.get('InicioAct') or '').strip()
                empresa['telefono'] = (row.get('Telefono') or '').strip()
                empresa['email'] = (row.get('Email') or '').strip()
                return empresa
            # Fallback: tabla empresa si existe
            c.execute("""
                SELECT razon_social, domicilio, cuit, condicion_iva, nro_iibb,
                       inicio_actividades, telefono, email, web
                FROM empresa LIMIT 1
            """)
            row = c.fetchone()
            if row:
                empresa['razon_social'] = row.get('razon_social') or empresa['razon_social']
                empresa['domicilio'] = row.get('domicilio') or ''
                cuit = str(row.get('cuit') or '').replace('-', '').replace(' ', '')
                empresa['cuit'] = cuit
                if len(cuit) == 11:
                    empresa['cuit_formateado'] = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"
                empresa['condicion_iva'] = row.get('condicion_iva') or empresa['condicion_iva']
                empresa['nro_iibb'] = row.get('nro_iibb') or ''
                empresa['inicio_actividades'] = row.get('inicio_actividades') or ''
                empresa['telefono'] = row.get('telefono') or ''
                empresa['email'] = row.get('email') or ''
                empresa['web'] = row.get('web') or ''
    except Exception:
        pass
    return empresa


def _get_cliente_data(base_empresa: str, cart: dict) -> dict:
    """Obtiene datos del cliente para el ticket."""
    cliente = {
        'razon_social': '',
        'domicilio': '',
        'cuit': '',
        'cuit_formateado': '',
        'condicion_iva': '',
        'nombre': '',
        'documento': '',
        'tipo_documento': 'DNI',
    }
    
    id_cliente = cart.get('id_cliente') or 1
    cuit = (cart.get('cuit') or '').replace('-', '').replace(' ', '')
    
    if id_cliente == 1:
        # Consumidor Final
        cliente['nombre'] = ''
        if cuit and len(cuit) == 11:
            cliente['documento'] = f"{cuit[:2]}-{cuit[2:10]}-{cuit[10]}"
            cliente['tipo_documento'] = 'CUIT'
        return cliente
    
    # Cliente identificado
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as c:
            c.execute("""
                SELECT nombre_cliente, domicilio, CUIT, telefono, email, condicion_iva
                FROM clientes WHERE id_cliente = %s
            """, [id_cliente])
            row = c.fetchone()
            if row:
                cliente['razon_social'] = row.get('nombre_cliente') or ''
                cliente['domicilio'] = row.get('domicilio') or ''
                cuit_db = str(row.get('CUIT') or cuit or '').replace('-', '').replace(' ', '')
                cliente['cuit'] = cuit_db
                if len(cuit_db) == 11:
                    cliente['cuit_formateado'] = f"{cuit_db[:2]}-{cuit_db[2:10]}-{cuit_db[10]}"
                cliente['condicion_iva'] = row.get('condicion_iva') or 'IVA RESPONSABLE INSCRIPTO'
    except Exception:
        pass
    
    return cliente


def _calcular_ivas(items: list) -> list:
    """Agrupa IVA por alícuota para Factura A."""
    ivas_dict = {}
    for item in items:
        alic = float(item.get('alicuota_iva') or 21)
        importe_iva = float(item.get('importe_iva') or 0)
        if alic not in ivas_dict:
            ivas_dict[alic] = {'alicuota': alic, 'importe': 0}
        ivas_dict[alic]['importe'] += importe_iva
    return list(ivas_dict.values())


def _formatear_fecha_cae(vto_cae) -> str:
    """Formatea fecha de vencimiento CAE."""
    if not vto_cae:
        return ''
    if isinstance(vto_cae, str):
        # Formato YYYYMMDD
        if len(vto_cae) == 8:
            return f"{vto_cae[6:8]}/{vto_cae[4:6]}/{vto_cae[0:4]}"
        return vto_cae
    try:
        return vto_cae.strftime('%d/%m/%Y')
    except Exception:
        return str(vto_cae)


def _generar_qr_afip(empresa: dict, cart: dict, nro_formateado: str) -> str:
    """
    Genera los datos del QR de verificación AFIP según RG 4291.
    URL: https://www.afip.gob.ar/fe/qr/?p=<datos_base64>
    """
    cuit_emisor = (empresa.get('cuit') or '').replace('-', '')
    if not cuit_emisor or not cart.get('cae'):
        return None
    
    # Datos para el QR según AFIP
    qr_obj = {
        "ver": 1,
        "fecha": cart.get('confirmed_at').strftime('%Y-%m-%d') if cart.get('confirmed_at') else '',
        "cuit": int(cuit_emisor) if cuit_emisor.isdigit() else 0,
        "ptoVta": cart.get('id_punto_venta') or 1,
        "tipoCmp": 6 if cart.get('tipo_comprobante') == 'FB' else 1,  # 1=FA, 6=FB
        "nroCmp": int(cart.get('nro_comprobante') or 0),
        "importe": float(cart.get('total') or 0),
        "moneda": "PES",
        "ctz": 1,
        "tipoDocRec": 99 if (cart.get('id_cliente') or 1) == 1 else 80,  # 99=Sin identificar, 80=CUIT
        "nroDocRec": 0 if (cart.get('id_cliente') or 1) == 1 else int((cart.get('cuit') or '0').replace('-', '').replace(' ', '') or 0),
        "tipoCodAut": "E",  # E=CAE
        "codAut": int(cart.get('cae') or 0),
    }
    
    try:
        json_str = json.dumps(qr_obj)
        b64 = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        return f"https://www.afip.gob.ar/fe/qr/?p={b64}"
    except Exception:
        return None


def _numero_a_letras(numero: float) -> str:
    """Convierte número a letras (simplificado para pesos argentinos)."""
    try:
        entero = int(numero)
        centavos = int(round((numero - entero) * 100))
        
        unidades = ['', 'UN', 'DOS', 'TRES', 'CUATRO', 'CINCO', 'SEIS', 'SIETE', 'OCHO', 'NUEVE']
        decenas = ['', 'DIEZ', 'VEINTE', 'TREINTA', 'CUARENTA', 'CINCUENTA', 'SESENTA', 'SETENTA', 'OCHENTA', 'NOVENTA']
        especiales = {11: 'ONCE', 12: 'DOCE', 13: 'TRECE', 14: 'CATORCE', 15: 'QUINCE', 
                      16: 'DIECISEIS', 17: 'DIECISIETE', 18: 'DIECIOCHO', 19: 'DIECINUEVE',
                      21: 'VEINTIUNO', 22: 'VEINTIDOS', 23: 'VEINTITRES', 24: 'VEINTICUATRO',
                      25: 'VEINTICINCO', 26: 'VEINTISEIS', 27: 'VEINTISIETE', 28: 'VEINTIOCHO', 29: 'VEINTINUEVE'}
        centenas = ['', 'CIENTO', 'DOSCIENTOS', 'TRESCIENTOS', 'CUATROCIENTOS', 'QUINIENTOS', 
                    'SEISCIENTOS', 'SETECIENTOS', 'OCHOCIENTOS', 'NOVECIENTOS']
        
        def convertir_grupo(n):
            if n == 0:
                return ''
            if n == 100:
                return 'CIEN'
            if n in especiales:
                return especiales[n]
            
            resultado = ''
            if n >= 100:
                resultado += centenas[n // 100] + ' '
                n %= 100
            if n in especiales:
                resultado += especiales[n]
            elif n >= 10:
                resultado += decenas[n // 10]
                if n % 10:
                    resultado += ' Y ' + unidades[n % 10]
            else:
                resultado += unidades[n]
            return resultado.strip()
        
        if entero == 0:
            letras = 'CERO'
        elif entero < 1000:
            letras = convertir_grupo(entero)
        elif entero < 1000000:
            miles = entero // 1000
            resto = entero % 1000
            if miles == 1:
                letras = 'MIL'
            else:
                letras = convertir_grupo(miles) + ' MIL'
            if resto:
                letras += ' ' + convertir_grupo(resto)
        else:
            millones = entero // 1000000
            resto = entero % 1000000
            if millones == 1:
                letras = 'UN MILLON'
            else:
                letras = convertir_grupo(millones) + ' MILLONES'
            if resto:
                miles = resto // 1000
                unids = resto % 1000
                if miles:
                    if miles == 1:
                        letras += ' MIL'
                    else:
                        letras += ' ' + convertir_grupo(miles) + ' MIL'
                if unids:
                    letras += ' ' + convertir_grupo(unids)
        
        if centavos:
            return f"PESOS {letras} CON {centavos:02d}/100"
        return f"PESOS {letras}"
    except Exception:
        return ''


@require_http_methods(['GET', 'POST'])
def config_edit(request, kiosk_id):
    """Editar kiosco. Solo self_checkout.admin."""
    base, err = _require_base_and_permission(request, has_self_checkout_admin)
    if err:
        return err
    kiosks = listar_kiosks(base)
    k = next((x for x in kiosks if x['kiosk_id'] == kiosk_id), None)
    if not k:
        messages.error(request, 'Kiosco no encontrado.')
        return redirect('self_checkout:config_list')
    sucursales_svc = __import__('core.services.administranet_sucursales', fromlist=['AdministraNETSucursalesService']).AdministraNETSucursalesService()
    sucursales = sucursales_svc.listar_sucursales(base)
    pvs = listar_puntos_venta(base)
    depositos = listar_depositos(base)
    viajantes = listar_viajantes(base)
    if request.method == 'POST':
        id_sucursal = request.POST.get('id_sucursal')
        id_punto_venta = request.POST.get('id_punto_venta')
        id_deposito = request.POST.get('id_deposito')
        cod_viajante_raw = request.POST.get('cod_viajante')
        cod_viajante = int(cod_viajante_raw) if cod_viajante_raw and cod_viajante_raw.strip() else None
        modo_rfid = (request.POST.get('modo_rfid') or 'delta').strip()
        activo = 1 if request.POST.get('activo') == '1' else 0
        enviar_factura_email = 1 if request.POST.get('enviar_factura_email') == '1' else 0
        modo_tpv = 1 if request.POST.get('modo_tpv') == '1' else 0
        if not id_sucursal or not id_punto_venta or not id_deposito:
            messages.error(request, 'Completá sucursal, punto de venta y depósito.')
            return render(request, 'self_checkout/config_form.html', {
                'sucursales': sucursales, 'puntos_venta': pvs, 'depositos': depositos, 'viajantes': viajantes,
                'form_data': request.POST, 'editing': True, 'kiosk_id': kiosk_id,
            })
        from self_checkout.db import mysql_cursor
        try:
            with mysql_cursor(base) as c:
                try:
                    c.execute("""
                        UPDATE self_checkout_kiosk
                        SET id_sucursal = %s, id_punto_venta = %s, id_deposito = %s, cod_viajante = %s, modo_rfid = %s, activo = %s, enviar_factura_email = %s, modo_tpv = %s
                        WHERE kiosk_id = %s
                    """, [int(id_sucursal), int(id_punto_venta), int(id_deposito), cod_viajante, modo_rfid, activo, enviar_factura_email, modo_tpv, kiosk_id])
                except Exception as col_err:
                    if 'Unknown column' in str(col_err):
                        c.execute("""
                            UPDATE self_checkout_kiosk
                            SET id_sucursal = %s, id_punto_venta = %s, id_deposito = %s, cod_viajante = %s, modo_rfid = %s, activo = %s, enviar_factura_email = %s
                            WHERE kiosk_id = %s
                        """, [int(id_sucursal), int(id_punto_venta), int(id_deposito), cod_viajante, modo_rfid, activo, enviar_factura_email, kiosk_id])
                    else:
                        raise
            messages.success(request, f'Kiosco "{kiosk_id}" actualizado. El PV determina la numeración AFIP.')
            return redirect('self_checkout:config_list')
        except Exception as e:
            messages.error(request, f'Error al guardar: {e}')
            return render(request, 'self_checkout/config_form.html', {
                'sucursales': sucursales, 'puntos_venta': pvs, 'depositos': depositos, 'viajantes': viajantes,
                'form_data': request.POST, 'editing': True, 'kiosk_id': kiosk_id,
            })
    return render(request, 'self_checkout/config_form.html', {
        'sucursales': sucursales, 'puntos_venta': pvs, 'depositos': depositos, 'viajantes': viajantes,
        'form_data': k, 'editing': True, 'kiosk_id': kiosk_id,
    })
