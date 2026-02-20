"""API REST para Self-Checkout."""
import logging
from decimal import Decimal

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from .db import get_base_empresa_from_request
from .decorators import require_self_checkout_permission
from .constants import (
    E_NO_EMPRESA,
    E_KIOSK_REQUIRED,
    E_KIOSK_NOT_CONFIGURED,
    E_CART_NOT_FOUND,
    E_ITEM_NOT_FOUND,
    E_ARTICLE_NOT_FOUND,
    E_STOCK_INSUFFICIENT,
    E_EMAIL_REQUIRED,
    E_ARTICLE_REQUIRED,
    E_CONFIRM_FAILED,
    E_AFIP_UNAVAILABLE,
    E_SERVICE_UNAVAILABLE,
    E_KIOSK_IN_USE,
)
from .services import CartService, KioskSessionService, ConfirmationService, InvoiceService
from .services.promotion_service import (
    obtener_promocion_articulo,
    aplicar_precio_promocion,
)
from .services.voucher_service import (
    listar_vouchers_disponibles,
    obtener_voucher_y_descuento,
    marcar_voucher_usado,
)

logger = logging.getLogger(__name__)


def _error_response(error: str, message: str, status: int = 400):
    """Respuesta API consistente con code + error."""
    return JsonResponse({'error': message, 'code': error}, status=status)


def _is_kiosk_session_table_missing(exc: Exception) -> bool:
    """True si el error indica que la tabla self_checkout_kiosk_session no existe."""
    err_msg = str(exc)
    return 'self_checkout_kiosk_session' in err_msg and (
        "doesn't exist" in err_msg or "no existe" in err_msg.lower()
    )


def _tables_missing_response(base: str):
    """Respuesta 503 cuando faltan tablas de self-checkout."""
    return JsonResponse({
        'error': 'Faltan las tablas de self-checkout en la base de datos. Ejecutá en el servidor: python manage.py create_self_checkout_tables --base-empresa ' + (base or 'administranet'),
        'code': E_SERVICE_UNAVAILABLE,
    }, status=503)


def _marcar_cart_error_confirmacion(base_empresa: str, cart_id: int, error_msg: str) -> None:
    """
    Marca el carrito como error_confirmacion para que el supervisor pueda recuperarlo.
    Si las columnas de migración 004 no existen, solo actualiza estado.
    """
    from self_checkout.db import mysql_cursor
    try:
        with mysql_cursor(base_empresa) as c:
            c.execute("""
                UPDATE self_checkout_cart SET
                    estado = 'error_confirmacion',
                    ultimo_error_confirmacion = %s,
                    ultimo_intento_confirmacion = NOW()
                WHERE id = %s
            """, [(error_msg or '')[:512], cart_id])
    except Exception as e:
        if 'Unknown column' in str(e):
            try:
                with mysql_cursor(base_empresa) as c:
                    c.execute(
                        "UPDATE self_checkout_cart SET estado = 'error_confirmacion' WHERE id = %s",
                        [cart_id],
                    )
            except Exception:
                pass
        else:
            logger.warning("_marcar_cart_error_confirmacion: %s", e)


def _mensaje_afip_para_usuario(error_msg: str) -> str:
    """
    Traduce errores técnicos de AFIP (WSAA/WSFE) a un mensaje claro para el usuario.
    El detalle técnico sigue en logs.
    """
    if not error_msg:
        return 'No se pudo emitir la factura electrónica. Revisá la configuración AFIP.'
    err = (error_msg or '').strip().lower()
    if 'cms.cert.untrusted' in err or 'certificado no emitido por ac' in err or 'cert.untrusted' in err:
        return (
            'No se pudo emitir la factura electrónica: el certificado AFIP no es de confianza. '
            'Verificá en Configuración AFIP (FE-AFIP) que el certificado sea el emitido por AFIP ARCA '
            'para el ambiente elegido (Homologación o Producción).'
        )
    if 'certificate' in err or 'certificado' in err or 'expired' in err or 'vencido' in err:
        return (
            'No se pudo emitir la factura electrónica: problema con el certificado AFIP. '
            'Revisá en Configuración AFIP que el certificado sea válido y corresponda al ambiente (Homologación/Producción).'
        )
    if 'coe.notauthorized' in err or 'computador no autorizado' in err or 'no autorizado' in err:
        return (
            'No se pudo emitir la factura electrónica: computador no autorizado en AFIP. '
            'En AFIP (Clave Fiscal) tenés que autorizar el equipo: Facturación Electrónica → Punto de venta / Servicios → Autorizar equipos (agregar la IP o nombre del servidor desde el que se conecta Synap).'
        )
    if 'wsaa' in err or 'wsfe' in err or 'cae' in err or 'caea' in err:
        return 'No se pudo emitir la factura electrónica. Revisá la configuración AFIP y la conectividad.'
    return 'No se pudo emitir la factura electrónica. Revisá la configuración AFIP.'


def _mensaje_padron_afip_para_usuario(error_msg: str) -> str:
    """Mensaje claro cuando falla la consulta al padrón AFIP (p. ej. consultar CUIT)."""
    if not error_msg:
        return 'No se pudo consultar el padrón AFIP.'
    err = (error_msg or '').strip().lower()
    if 'coe.notauthorized' in err or 'computador no autorizado' in err or 'no autorizado' in err:
        return (
            'Computador no autorizado en AFIP. En AFIP (Clave Fiscal), en el ambiente que estés usando '
            '(Homologación o Producción), entrá a Servicios web y dale de alta el servicio "Padrón A5" (o Padrón A4). '
            'Ahí tenés que agregar la IP pública del servidor o PC desde la que se conecta Synap.'
        )
    if 'no existe persona' in err or ('no exist' in err and 'persona' in err):
        return 'El CUIT no está registrado en el padrón AFIP. En homologación solo existen algunos CUITs de prueba.'
    if 'padrón no disponible' in err or 'ws_sr_padron' in err:
        return 'El servicio de padrón AFIP no está disponible. Revisá que pyafipws esté instalado.'
    return (error_msg or 'No se pudo consultar el padrón AFIP.')[:300]


@require_http_methods(['GET'])
def health(request):
    """Health check para smoke tests y monitoreo."""
    return JsonResponse({'status': 'ok', 'module': 'self_checkout'})


# --- AFIP healthcheck y modo CAEA (autoservicio fuera de línea / continuar sin AFIP) ---

SESSION_CAEA_MODE_KEY = 'self_checkout_caea_mode'
SESSION_CAEA_SUPERVISOR_AUTH_KEY = 'self_checkout_caea_supervisor_authorized'


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def afip_health(request):
    """
    Healthcheck de conectividad AFIP (WSAA). Para autoservicio: si falla, se pone fuera de línea.
    Si responde ok, se limpia modo CAEA en sesión (vuelta automática a CAE).
    """
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.fe_config import check_afip_connectivity
    ok, error_msg = check_afip_connectivity(base)
    if ok:
        # Restaurar conexión: salir de modo CAEA para volver a CAE automático
        if SESSION_CAEA_MODE_KEY in request.session:
            del request.session[SESSION_CAEA_MODE_KEY]
            request.session.modified = True
        if SESSION_CAEA_SUPERVISOR_AUTH_KEY in request.session:
            del request.session[SESSION_CAEA_SUPERVISOR_AUTH_KEY]
            request.session.modified = True
        return JsonResponse({'ok': True})
    return JsonResponse({'ok': False, 'error': error_msg or 'Sin conexión con AFIP'})


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def afip_caea_mode(request):
    """
    Activa o desactiva modo CAEA (contingencia cuando conexión AFIP cae). Solo supervisor/admin o tras autorización.
    Body: { "enable": true | false }. Permite seguir operando; en confirmación se intenta CAE y si falla por red, CAEA.
    """
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST or {}
    enable = data.get('enable') in (True, 'true', '1', 1)
    from self_checkout.permissions import has_permission
    user = getattr(request, 'user', None)
    session_user = request.session.get('user') or {}
    is_supervisor = has_permission(user or session_user, 'self_checkout.supervisor', base)
    authorized = request.session.get(SESSION_CAEA_SUPERVISOR_AUTH_KEY, False)
    if not (is_supervisor or authorized):
        return _error_response('FORBIDDEN', 'Solo un supervisor puede habilitar modo CAEA', 403)
    if enable:
        request.session[SESSION_CAEA_MODE_KEY] = True
        if SESSION_CAEA_SUPERVISOR_AUTH_KEY in request.session:
            del request.session[SESSION_CAEA_SUPERVISOR_AUTH_KEY]
            request.session.modified = True
    else:
        if SESSION_CAEA_MODE_KEY in request.session:
            del request.session[SESSION_CAEA_MODE_KEY]
        request.session.modified = True
    return JsonResponse({'ok': True, 'caea_mode': enable})


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def supervisor_authorize_caea(request):
    """
    Autoriza modo CAEA con credenciales de supervisor. No cambia el usuario logueado.
    Body: { "cod_usuario": "...", "password": "..." }. Si el usuario es supervisor, guarda flag en sesión.
    """
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST or {}
    cod_usuario = (data.get('cod_usuario') or '').strip()
    password = (data.get('password') or '')
    if not cod_usuario or not password:
        return _error_response('BAD_REQUEST', 'cod_usuario y password son obligatorios', 400)
    try:
        from login.administranet_auth import AdministraNETAuthService
        from self_checkout.permissions import has_permission
        auth_svc = AdministraNETAuthService()
        user_data = auth_svc.validate_user(cod_usuario, password, base)
        if not user_data:
            return _error_response('UNAUTHORIZED', 'Usuario o contraseña incorrectos', 401)
        if not has_permission(user_data, 'self_checkout.supervisor', base):
            return _error_response('FORBIDDEN', 'El usuario no tiene permiso de supervisor', 403)
        request.session[SESSION_CAEA_SUPERVISOR_AUTH_KEY] = True
        request.session.modified = True
        return JsonResponse({'ok': True})
    except Exception as e:
        logger.exception('supervisor_authorize_caea: %s', e)
        return _error_response('SERVER_ERROR', 'Error al validar credenciales', 500)


def _get_context(request):
    base = get_base_empresa_from_request(request)
    if not base:
        return None, _error_response(E_NO_EMPRESA, 'No hay empresa seleccionada', 400)
    return base, None


@require_http_methods(['GET'])
@require_self_checkout_permission('supervisor')
def audit_list(request):
    """Lista auditoría (solo supervisor/admin). Endpoint protegido por permiso supervisor."""
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    try:
        with mysql_cursor(base, dict_cursor=True) as c:
            c.execute(
                """
                SELECT id, kiosk_id, cart_id, accion, created_at
                FROM self_checkout_audit_log
                ORDER BY created_at DESC LIMIT 100
                """
            )
            rows = c.fetchall()
    except Exception:
        rows = []
    return JsonResponse({'audit': [dict(r) for r in rows]})


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def cart_create(request):
    """Crea carrito nuevo. Usa KioskSessionService.resolve_context."""
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST
    kiosk_id = data.get('kiosk_id')
    if not kiosk_id:
        return _error_response(E_KIOSK_REQUIRED, 'kiosk_id requerido', 400)

    try:
        session_user = request.session.get('user', {})
        kiosk_svc = KioskSessionService(base)
        es_admin = hasattr(request.user, 'is_admin') and request.user.is_admin()
        context, err_msg = kiosk_svc.resolve_context(kiosk_id, session_user, es_admin)
        if err_msg:
            return _error_response(E_KIOSK_NOT_CONFIGURED, err_msg, 400)

        cart_svc = CartService(base)
        cart_id = cart_svc.crear_carrito(
            kiosk_id,
            context['id_sucursal'],
            context['id_punto_venta'],
            context['id_deposito'],
        )
        if cart_id:
            return JsonResponse({'cart_id': cart_id})
        return JsonResponse({'error': 'No se pudo crear carrito', 'code': 'CART_CREATE_FAILED'}, status=500)
    except Exception as e:
        logger.exception('cart_create failed: kiosk_id=%s base=%s', kiosk_id, base)
        msg = str(e) if not _is_sensitive(e) else 'Error al crear carrito. Verifique tablas y kiosco configurado.'
        return _error_response('CART_CREATE_FAILED', msg, 500)


def _is_sensitive(exc: Exception) -> bool:
    """Evita exponer detalles internos en respuestas."""
    s = str(exc).lower()
    return any(x in s for x in ('password', 'credential', 'token', 'connection refused'))


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def cart_detail(request, cart_id):
    """Detalle del carrito con ítems."""
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute("SELECT * FROM self_checkout_cart WHERE id = %s", [cart_id])
        cart = c.fetchone()
    if not cart:
        return _error_response(E_CART_NOT_FOUND, 'Carrito no encontrado', 404)
    cart_svc = CartService(base)
    items = cart_svc.obtener_items(cart_id)
    # Normalizar ítems para grilla extendida (TPV): codigo_barras, alicuota_porcentaje, subtotal, precio con IVA incluido.
    items_normalized = []
    for i in items:
        row = dict(i)
        row['codigo_barras'] = row.get('codigo_barras') or row.get('codigo_articulo') or ''
        alic = float(row.get('alicuota_iva') or 0)
        row['alicuota_porcentaje'] = alic
        row['porcentaje_descuento'] = float(row.get('porcentaje_descuento') or 0)
        row['subtotal'] = float(row.get('importe_total') or 0)  # ya es bruto (con IVA)
        pu_neto = float(row.get('precio_unitario') or 0)
        row['precio_unitario_bruto'] = round(pu_neto * (1 + alic / 100.0), 2)  # precio unitario con IVA incluido
        row['promocion'] = row.get('promocion') or ''
        row['detalle'] = row.get('detalle') or ''
        items_normalized.append(row)
    return JsonResponse({
        'cart': dict(cart),
        'items': items_normalized,
    })


def _parse_json(request):
    if request.content_type and 'application/json' in request.content_type:
        import json
        try:
            return json.loads(request.body)
        except Exception:
            return {}
    return {}


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def cart_add_item(request, cart_id):
    """Agrega ítem por scan (codigo) o datos directos."""
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST
    codigo = data.get('codigo')
    id_lista = data.get('id_lista')
    if id_lista is not None:
        try:
            id_lista = int(id_lista)
        except (TypeError, ValueError):
            id_lista = 1
    else:
        id_lista = 1
    try:
        if codigo:
            articulo = _buscar_articulo(base, codigo, id_lista=id_lista)
            if not articulo:
                return _error_response(E_ARTICLE_NOT_FOUND, f'Artículo no encontrado: {codigo}', 404)
        else:
            articulo = {
                'IDArt': data.get('id_articulo'),
                'id_manual': data.get('codigo_articulo', ''),
                'NombreArticulo': data.get('descripcion', ''),
                'precio': Decimal(str(data.get('precio_unitario', 0))),
                'Alicuota': Decimal(str(data.get('alicuota_iva', 0))),
                'promocion_data': {},
            }
            if not articulo['IDArt']:
                return _error_response(E_ARTICLE_REQUIRED, 'id_articulo o codigo requerido', 400)

        cart_svc = CartService(base)
        cantidad = Decimal(str(data.get('cantidad', 1)))
        precio_base = Decimal(str(articulo.get('precio', 0)))
        alicuota = Decimal(str(articulo.get('Alicuota', 0)))
        promo = articulo.get('promocion_data') or {}
        precio_final, pct_desc, promocion_por, promocion_tipo, promocion_cant = aplicar_precio_promocion(
            precio_base, alicuota, cantidad, promo
        )
        porcentaje_descuento = (
            Decimal(str(data['porcentaje_descuento']))
            if data.get('porcentaje_descuento') is not None
            else (pct_desc if pct_desc else None)
        )
        promocion_val = promo.get('promocion') or data.get('promocion')
        item_id, err_msg = cart_svc.agregar_item(
            cart_id=cart_id,
            id_articulo=int(articulo['IDArt']),
            codigo_articulo=str(articulo.get('id_manual', '')),
            descripcion=str(articulo.get('NombreArticulo', '')),
            cantidad=cantidad,
            precio_unitario=precio_final,
            alicuota_iva=alicuota,
            origen=data.get('origen', 'scan'),
            codigo_barras=articulo.get('codigo_barras') or data.get('codigo_barras'),
            porcentaje_descuento=porcentaje_descuento,
            promocion=promocion_val,
            promocion_por=promocion_por,
            promocion_tipo=promocion_tipo,
            promocion_cant=promocion_cant,
            detalle=data.get('detalle'),
        )
        if err_msg:
            return _error_response(E_STOCK_INSUFFICIENT, err_msg, 400)
        if item_id:
            from .services.serie_service import articulo_es_seriado
            requiere_series = articulo_es_seriado(base, int(articulo['IDArt']))
            return JsonResponse({
                'item_id': item_id,
                'requiere_series': requiere_series,
            })
        return JsonResponse({'error': 'No se pudo agregar', 'code': 'ADD_ITEM_FAILED'}, status=500)
    except Exception as e:
        logger.exception('cart_add_item failed: cart_id=%s codigo=%s base=%s', cart_id, codigo, base)
        msg = str(e) if not _is_sensitive(e) else 'Error al agregar ítem.'
        return _error_response('ADD_ITEM_FAILED', msg, 500)


def _buscar_articulo(base_empresa: str, codigo: str, id_lista: int = 1):
    """
    Busca artículo por código de barras o ID.
    Base: base_empresa (sesión). Tabla: articulo.
    Campos buscados: id_manual, IDArt, NroCodBarra, NroCodBarraF, CodigoArticuloT, CodArtProv (VB6).
    Si NroCodBarra/etc no existen, usa id_manual + IDArt. Precio desde articulo_precio (id_lista).
    """
    from self_checkout.db import mysql_cursor
    import MySQLdb
    cod = str(codigo).strip()
    # articulo.Alicuota = id ref iva.id; el porcentaje está en iva.Alicuota
    sql_ext = """
        SELECT a.IDArt, a.id_manual, a.NombreArticulo,
               COALESCE(iva.Alicuota, a.Alicuota, 0) AS Alicuota,
               a.NroCodBarra
        FROM articulo a
        LEFT JOIN iva ON iva.id = a.Alicuota
        WHERE (a.id_manual = %s OR CAST(a.IDArt AS CHAR) = %s
               OR a.NroCodBarra = %s OR a.NroCodBarraF = %s
               OR a.CodigoArticuloT = %s OR a.CodArtProv = %s)
        LIMIT 1
    """
    sql_basic = """
        SELECT a.IDArt, a.id_manual, a.NombreArticulo,
               COALESCE(iva.Alicuota, a.Alicuota, 0) AS Alicuota
        FROM articulo a
        LEFT JOIN iva ON iva.id = a.Alicuota
        WHERE (a.id_manual = %s OR CAST(a.IDArt AS CHAR) = %s)
        LIMIT 1
    """
    with mysql_cursor(base_empresa, dict_cursor=True) as c:
        try:
            c.execute(sql_ext, [cod] * 6)
        except MySQLdb.ProgrammingError as e:
            if (e.args and e.args[0] == 1054) or 'Unknown column' in str(e):
                c.execute(sql_basic, [cod, cod])
            else:
                raise
        row = c.fetchone()
        if not row:
            return None
        precio = 0
        try:
            c.execute("""
                SELECT PrecioVentaxU FROM articulo_precio
                WHERE IDArt = %s AND id_lista = %s LIMIT 1
            """, [row['IDArt'], id_lista])
            pr = c.fetchone()
            if pr and pr.get('PrecioVentaxU') is not None:
                precio = float(pr['PrecioVentaxU'])
        except Exception:
            pass
        if precio <= 0:
            try:
                c.execute("SELECT COALESCE(Precio1V, Precio1VI, 0) as p FROM articulo WHERE IDArt = %s", [row['IDArt']])
                pr2 = c.fetchone()
                if pr2 and pr2.get('p') is not None:
                    precio = float(pr2['p'])
            except Exception:
                pass
        row['precio'] = precio
        row['Alicuota'] = float(row.get('Alicuota') or 0)
        row['codigo_barras'] = row.get('NroCodBarra') or row.get('id_manual') or (str(row['IDArt']) if row.get('IDArt') is not None else '')
        # Promoción por artículo (vigencia + lista, como TPV VB6)
        try:
            id_lista_int = max(0, min(5, int(id_lista)))
            promo = obtener_promocion_articulo(base_empresa, int(row['IDArt']), id_lista_int)
            row['promocion_data'] = promo
        except Exception:
            row['promocion_data'] = {'aplica': False, 'promocion': 'No', 'promocion_tipo': '', 'promocion_por': Decimal('0'), 'promocion_cant': Decimal('0')}
        return row


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def articulo_por_codigo(request):
    """Busca artículo por código para scan."""
    base, err = _get_context(request)
    if err:
        return err
    codigo = request.GET.get('codigo')
    if not codigo:
        return _error_response(E_ARTICLE_REQUIRED, 'codigo requerido', 400)
    articulo = _buscar_articulo(base, codigo)
    if articulo:
        return JsonResponse({'articulo': dict(articulo)})
    return _error_response(E_ARTICLE_NOT_FOUND, 'No encontrado', 404)


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def articulos_list(request):
    """
    Lista artículos para grilla de productos (modo TPV). Devuelve id, codigo, descripcion, precio, alicuota, imagen_url.
    Query: limit (default 40), search (opcional, por nombre o código).
    """
    base, err = _get_context(request)
    if err:
        return err
    limit = min(int(request.GET.get('limit', 40)), 100)
    search = (request.GET.get('search') or '').strip()
    try:
        id_lista = int(request.GET.get('id_lista', 1))
    except (TypeError, ValueError):
        id_lista = 1
    try:
        id_deposito = int(request.GET.get('id_deposito', 0)) or None
    except (TypeError, ValueError):
        id_deposito = None
    from self_checkout.db import mysql_cursor
    from self_checkout.services.stock_service import StockService
    import MySQLdb
    with mysql_cursor(base, dict_cursor=True) as c:
        try:
            if search:
                term = '%' + search + '%'
                # Búsqueda por nombre, id_manual, IDArt y código de barras (si existe columna)
                try:
                    c.execute("""
                        SELECT a.IDArt AS id_articulo, a.id_manual AS codigo_articulo, a.NombreArticulo AS descripcion,
                               COALESCE(iva.Alicuota, a.Alicuota, 0) AS alicuota_iva
                        FROM articulo a
                        LEFT JOIN iva ON iva.id = a.Alicuota
                        WHERE a.NombreArticulo LIKE %s OR a.id_manual LIKE %s OR CAST(a.IDArt AS CHAR) LIKE %s
                           OR a.NroCodBarra = %s OR a.NroCodBarra LIKE %s
                        ORDER BY a.NombreArticulo
                        LIMIT %s
                    """, [term, term, term, search.strip(), term, limit])
                except MySQLdb.ProgrammingError as e:
                    if e.args and e.args[0] == 1054 or 'Unknown column' in str(e):
                        c.execute("""
                            SELECT a.IDArt AS id_articulo, a.id_manual AS codigo_articulo, a.NombreArticulo AS descripcion,
                                   COALESCE(iva.Alicuota, a.Alicuota, 0) AS alicuota_iva
                            FROM articulo a
                            LEFT JOIN iva ON iva.id = a.Alicuota
                            WHERE a.NombreArticulo LIKE %s OR a.id_manual LIKE %s OR CAST(a.IDArt AS CHAR) LIKE %s
                            ORDER BY a.NombreArticulo
                            LIMIT %s
                        """, [term, term, term, limit])
                    else:
                        raise
            else:
                c.execute("""
                    SELECT a.IDArt AS id_articulo, a.id_manual AS codigo_articulo, a.NombreArticulo AS descripcion,
                           COALESCE(iva.Alicuota, a.Alicuota, 0) AS alicuota_iva
                    FROM articulo a
                    LEFT JOIN iva ON iva.id = a.Alicuota
                    ORDER BY a.NombreArticulo
                    LIMIT %s
                """, [limit])
            rows = c.fetchall()
        except Exception as e:
            logger.warning("articulos_list query failed: %s", e)
            rows = []
        id_lista_int = max(0, min(5, int(id_lista)))
        out = []
        for r in rows:
            id_art = r.get('id_articulo')
            precio = 0
            try:
                c.execute("SELECT PrecioVentaxU FROM articulo_precio WHERE IDArt = %s AND id_lista = %s LIMIT 1", [id_art, id_lista])
                pr = c.fetchone()
                if pr and pr.get('PrecioVentaxU') is not None:
                    precio = float(pr['PrecioVentaxU'])
            except Exception:
                pass
            if precio <= 0:
                try:
                    c.execute("SELECT COALESCE(Precio1V, Precio1VI, 0) AS p FROM articulo WHERE IDArt = %s", [id_art])
                    pr2 = c.fetchone()
                    if pr2 and pr2.get('p') is not None:
                        precio = float(pr2['p'])
                except Exception:
                    pass
            promo = {}
            try:
                promo = obtener_promocion_articulo(base, int(id_art), id_lista_int)
            except Exception:
                pass
            item = {
                'id_articulo': id_art,
                'codigo_articulo': r.get('codigo_articulo') or str(id_art),
                'descripcion': r.get('descripcion') or '',
                'precio': precio,
                'alicuota_iva': float(r.get('alicuota_iva') or 0),
                'imagen_url': None,
                'promocion': promo.get('promocion') or 'No',
                'promocion_tipo': promo.get('promocion_tipo') or '',
                'promocion_por': float(promo.get('promocion_por') or 0),
                'promocion_cant': float(promo.get('promocion_cant') or 0),
            }
            if id_deposito is not None:
                try:
                    stock_svc = StockService(base)
                    disp = stock_svc.get_disponible(int(id_art), id_deposito)
                    item['stock_disponible'] = int(disp) if disp is not None else 0
                except Exception:
                    item['stock_disponible'] = 0
            else:
                item['stock_disponible'] = None
            out.append(item)
    return JsonResponse({'articulos': out})


@require_http_methods(['DELETE', 'POST'])
@require_self_checkout_permission('kiosk')
def cart_remove_item(request, cart_id, item_id):
    """Quita ítem del carrito."""
    base, err = _get_context(request)
    if err:
        return err
    cart_svc = CartService(base)
    if cart_svc.quitar_item(cart_id, item_id):
        return JsonResponse({'ok': True})
    return _error_response(E_ITEM_NOT_FOUND, 'Ítem o carrito no encontrado', 404)


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def cart_item_series_disponibles(request, cart_id, item_id):
    """Lista números de serie disponibles (serie_entrada) para el artículo del ítem y depósito del carrito."""
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    from .services.serie_service import listar_series_disponibles
    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute("""
            SELECT c.id_deposito FROM self_checkout_cart c WHERE c.id = %s
        """, [cart_id])
        cart = c.fetchone()
        if not cart:
            return _error_response(E_CART_NOT_FOUND, 'Carrito no encontrado', 404)
        c.execute("""
            SELECT id_articulo FROM self_checkout_cart_item WHERE id = %s AND cart_id = %s
        """, [item_id, cart_id])
        row = c.fetchone()
        if not row:
            return _error_response(E_ITEM_NOT_FOUND, 'Ítem no encontrado', 404)
    id_deposito = cart['id_deposito']
    id_articulo = row['id_articulo']
    lista = listar_series_disponibles(base, id_articulo, id_deposito)
    return JsonResponse({'series': lista})


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def cart_item_series_asignadas(request, cart_id, item_id):
    """Lista los números de serie asignados a este ítem del carrito."""
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    from .services.serie_service import obtener_series_por_item
    with mysql_cursor(base) as c:
        c.execute("SELECT 1 FROM self_checkout_cart_item WHERE id = %s AND cart_id = %s", [item_id, cart_id])
        if not c.fetchone():
            return _error_response(E_ITEM_NOT_FOUND, 'Ítem no encontrado', 404)
    lista = obtener_series_por_item(base, item_id)
    return JsonResponse({'series': lista})


@require_http_methods(['PUT', 'POST'])
@require_self_checkout_permission('kiosk')
def cart_item_series_asignar(request, cart_id, item_id):
    """Asigna números de serie al ítem. Body: { "id_serie_entrada": [1, 2, ...] } (cantidad = cantidad del ítem)."""
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    from .services.serie_service import asignar_series_a_item
    with mysql_cursor(base) as c:
        c.execute("SELECT id_deposito FROM self_checkout_cart WHERE id = %s", [cart_id])
        row = c.fetchone()
        if not row:
            return _error_response(E_CART_NOT_FOUND, 'Carrito no encontrado', 404)
        id_deposito = row[0]
    data = _parse_json(request) or request.POST
    ids = data.get('id_serie_entrada')
    if ids is None:
        ids = data.get('id_serie_entrada_list', [])
    if not isinstance(ids, (list, tuple)):
        ids = [ids] if ids is not None else []
    try:
        id_list = [int(x) for x in ids]
    except (TypeError, ValueError):
        return _error_response('INVALID_INPUT', 'id_serie_entrada debe ser una lista de números', 400)
    ok, err_msg = asignar_series_a_item(base, cart_id, item_id, id_list, id_deposito)
    if not ok:
        return _error_response('SERIES_INVALID', err_msg or 'Error al asignar series', 400)
    return JsonResponse({'ok': True})


@require_http_methods(['PATCH', 'POST'])
@require_self_checkout_permission('kiosk')
def cart_update_item_descuento(request, cart_id, item_id):
    """Actualiza el porcentaje de descuento de un ítem (descuento por renglón, como TPV VB6)."""
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST
    try:
        pct = Decimal(str(data.get('porcentaje_descuento', 0)))
    except (TypeError, ValueError):
        return _error_response('INVALID_INPUT', 'porcentaje_descuento debe ser un número', 400)
    cart_svc = CartService(base)
    ok, err_msg = cart_svc.actualizar_descuento_item(cart_id, item_id, pct)
    if not ok:
        return _error_response('UPDATE_DESCUENTO_FAILED', err_msg or 'No se pudo actualizar', 400)
    return JsonResponse({'ok': True})


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def cart_vouchers_disponibles(request, cart_id):
    """Lista vouchers disponibles para aplicar al carrito (programa de descuentos, como TPV VB6)."""
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute("SELECT id_cliente FROM self_checkout_cart WHERE id = %s", [cart_id])
        row = c.fetchone()
    if not row:
        return _error_response(E_CART_NOT_FOUND, 'Carrito no encontrado', 404)
    id_cliente = int(row.get('id_cliente') or 1)
    listado = listar_vouchers_disponibles(base, id_cliente=id_cliente)
    return JsonResponse({'vouchers': listado})


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def cart_aplicar_voucher(request, cart_id):
    """Aplica un voucher al carrito (id_sp_cupon). Descuento al pie como TPV VB6."""
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST
    try:
        id_sp_cupon = int(data.get('id_sp_cupon', 0))
    except (TypeError, ValueError):
        return _error_response('INVALID_INPUT', 'id_sp_cupon requerido (entero)', 400)
    if id_sp_cupon <= 0:
        return _error_response('INVALID_INPUT', 'id_sp_cupon inválido', 400)
    resultado = obtener_voucher_y_descuento(base, id_sp_cupon)
    if not resultado:
        return _error_response('VOUCHER_INVALID', 'Voucher no encontrado, ya usado o fuera de vigencia', 400)
    monto_pct, _ = resultado
    cart_svc = CartService(base)
    ok, err_msg = cart_svc.aplicar_voucher(cart_id, id_sp_cupon, monto_pct)
    if not ok:
        return _error_response('APPLY_VOUCHER_FAILED', err_msg or 'No se pudo aplicar', 400)
    return JsonResponse({'ok': True, 'monto_descuento': float(monto_pct)})


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def cart_quitar_voucher(request, cart_id):
    """Quita el voucher aplicado al carrito."""
    base, err = _get_context(request)
    if err:
        return err
    cart_svc = CartService(base)
    cart_svc.quitar_voucher(cart_id)
    return JsonResponse({'ok': True})


@require_http_methods(['POST', 'PATCH'])
@require_self_checkout_permission('kiosk')
def cart_aplicar_descuento_pie(request, cart_id):
    """Aplica descuento masivo al pie (PorDesc1) a toda la factura. Body: { porcentaje_descuento: number }."""
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST
    try:
        pct = Decimal(str(data.get('porcentaje_descuento', 0)))
    except (TypeError, ValueError):
        return _error_response('INVALID_INPUT', 'porcentaje_descuento debe ser un número', 400)
    cart_svc = CartService(base)
    ok, err_msg = cart_svc.aplicar_descuento_pie(cart_id, pct)
    if not ok:
        return _error_response('DESCUENTO_PIE_FAILED', err_msg or 'No se pudo aplicar', 400)
    return JsonResponse({'ok': True, 'porcentaje_descuento': float(pct)})


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def cart_create_payment_intent(request, cart_id):
    """
    Crea un payment_intent para el carrito (para MercadoPago u otro procesador).
    Body: monto (opcional, si no se envía se usa total del carrito), kiosk_id (opcional).
    Retorna: payment_intent_id, id_sucursal, id_punto_venta, monto.
    """
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST
    kiosk_id = (data.get('kiosk_id') or '').strip()

    from self_checkout.db import mysql_cursor
    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute(
            "SELECT id, estado, total, id_sucursal, id_punto_venta FROM self_checkout_cart WHERE id = %s",
            [cart_id],
        )
        cart = c.fetchone()
    if not cart:
        return _error_response(E_CART_NOT_FOUND, 'Carrito no encontrado', 404)
    if cart['estado'] not in ('borrador', 'pago_pendiente'):
        return _error_response('E_CART_STATE', 'El carrito no está en estado para iniciar pago', 400)

    from .services.serie_service import validar_series_carrito
    ok_series, err_series = validar_series_carrito(base, cart_id)
    if not ok_series:
        return _error_response('SERIES_INVALID', err_series or 'Faltan números de serie', 400)

    monto = data.get('monto')
    if monto is not None:
        try:
            monto = float(monto)
        except (TypeError, ValueError):
            monto = float(cart['total'] or 0)
    else:
        monto = float(cart['total'] or 0)
    if monto <= 0:
        return _error_response('E_AMOUNT', 'Monto debe ser mayor a 0', 400)

    id_sucursal = int(cart['id_sucursal'])
    id_punto_venta = int(cart['id_punto_venta'])

    with mysql_cursor(base) as c:
        c.execute(
            """
            INSERT INTO self_checkout_payment_intent
            (cart_id, kiosk_id, id_sucursal, id_punto_venta, monto, estado)
            VALUES (%s, %s, %s, %s, %s, 'pendiente')
            """,
            [cart_id, kiosk_id or None, id_sucursal, id_punto_venta, monto],
        )
        payment_intent_id = c.lastrowid
    return JsonResponse({
        'payment_intent_id': payment_intent_id,
        'id_sucursal': id_sucursal,
        'id_punto_venta': id_punto_venta,
        'monto': monto,
    })


def _normalize_denom(s: str) -> str:
    """Normaliza para comparar razón social / nombre (strip, upper, espacios colapsados)."""
    if not s:
        return ''
    return ' '.join((s or '').strip().upper().split())


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def clientes_buscar(request):
    """
    Búsqueda predictiva de clientes por nombre o CUIT.
    GET ?q=xxx (mín. 2 caracteres). Devuelve { clientes: [{ id_cliente, nombre_cliente, cuit }] }.
    Excluye Consumidor Final (Codigo = 1).
    """
    base, err = _get_context(request)
    if err:
        return err
    q = (request.GET.get('q') or '').strip()
    if len(q) < 2:
        return JsonResponse({'clientes': []})
    from self_checkout.db import mysql_cursor
    term = '%' + q + '%'
    term_digits = ''.join(c for c in q if c.isdigit())
    try:
        with mysql_cursor(base, dict_cursor=True) as c:
            if term_digits:
                c.execute("""
                    SELECT Codigo AS id_cliente, nombre_cliente,
                           COALESCE(TRIM(CUIT), '') AS cuit
                    FROM cliente
                    WHERE (Codigo IS NULL OR Codigo <> 1)
                      AND (nombre_cliente LIKE %s OR TRIM(COALESCE(CUIT,'')) LIKE %s
                           OR REPLACE(REPLACE(TRIM(COALESCE(CUIT,'')), '-', ''), ' ', '') LIKE %s)
                    ORDER BY nombre_cliente
                    LIMIT 25
                """, [term, term, '%' + term_digits + '%'])
            else:
                c.execute("""
                    SELECT Codigo AS id_cliente, nombre_cliente,
                           COALESCE(TRIM(CUIT), '') AS cuit
                    FROM cliente
                    WHERE (Codigo IS NULL OR Codigo <> 1)
                      AND nombre_cliente LIKE %s
                    ORDER BY nombre_cliente
                    LIMIT 25
                """, [term])
            rows = c.fetchall()
        clientes = [
            {
                'id_cliente': r.get('id_cliente'),
                'nombre_cliente': (r.get('nombre_cliente') or '').strip() or 'Sin nombre',
                'cuit': (r.get('cuit') or '').strip(),
            }
            for r in rows
        ]
        return JsonResponse({'clientes': clientes})
    except Exception as e:
        logger.warning("clientes_buscar: %s", e)
        return JsonResponse({'clientes': []})


@require_http_methods(['GET', 'POST'])
@require_self_checkout_permission('kiosk')
def consultar_cuit(request):
    """
    Busca en clientes dados de alta en administraNET por CUIT. Si está dado de alta,
    usamos esos datos y validamos en backend contra el padrón AFIP. En los datos del
    cliente puede venir el email; si no está, el front debe pedirlo. Si el padrón
    arroja datos distintos a administraNET, se devuelve datos_difieren para mostrar
    el error y pedir confirmación para actualizar o no.
    GET: ?cuit=20123456789  |  POST: { "cuit": "20-12345678-9" }
    """
    base, err = _get_context(request)
    if err:
        return err
    if request.method == 'GET':
        cuit = (request.GET.get('cuit') or '').strip()
    else:
        data = _parse_json(request) or request.POST or {}
        cuit = (data.get('cuit') or '').strip()
    if not cuit:
        return JsonResponse({'ok': False, 'error': 'CUIT requerido'}, status=400)

    from self_checkout.services.cliente_administranet_service import buscar_cliente_por_cuit
    from self_checkout.services.padron_afip_service import consultar_condicion_fiscal
    from self_checkout.services.empresa_fiscal_service import emisor_emite_solo_factura_c

    cliente = buscar_cliente_por_cuit(base, cuit)
    solo_factura_c = emisor_emite_solo_factura_c(base)
    if solo_factura_c and cliente:
        # Emisor solo FC y cliente ya está en administraNET: no hace falta consultar padrón.
        tipo = 'FC'
        denominacion_afip = (cliente.get('nombre_cliente') or '').strip()
        error_detail = None
    else:
        # Consultar padrón AFIP: para tipo FA/FB, o para obtener razón social si el cliente no está en administraNET.
        tipo, denominacion_afip, error_detail = consultar_condicion_fiscal(base, cuit)
        if solo_factura_c:
            tipo = 'FC'
            # denominacion_afip ya viene del padrón (o '' si falló)
    padron_no_disponible = False
    if error_detail:
        msg = (error_detail or {}).get('msg', 'Error al consultar AFIP')
        if 'padrón' in msg.lower() and ('no disponible' in msg.lower() or 'no instalado' in msg.lower() or 'ws_sr_padron' in msg.lower()):
            padron_no_disponible = True
            tipo = 'FB'
            denominacion_afip = denominacion_afip or ''
        else:
            return JsonResponse({'ok': False, 'error': _mensaje_padron_afip_para_usuario(msg)})

    payload = {
        'ok': True,
        'denominacion': denominacion_afip or '',
        'tipo_comprobante': tipo or 'FB',
        'solo_factura_c': solo_factura_c,
        'padron_no_disponible': padron_no_disponible,
        'aviso': 'Validación AFIP no disponible. Se usará Factura B.' if padron_no_disponible else None,
        'id_cliente': None,
        'nombre_cliente': None,
        'email': None,
        'datos_difieren': False,
        'denominacion_afip': denominacion_afip or '',
        'denominacion_administranet': None,
    }

    if cliente:
        payload['id_cliente'] = cliente.get('id_cliente')
        payload['nombre_cliente'] = cliente.get('nombre_cliente') or ''
        payload['email'] = cliente.get('email') or None
        if padron_no_disponible and not payload.get('denominacion'):
            payload['denominacion'] = payload['nombre_cliente'] or ''
        nom_admin = (cliente.get('nombre_cliente') or '').strip()
        denom_afip = (denominacion_afip or '').strip()
        if nom_admin and denom_afip and _normalize_denom(nom_admin) != _normalize_denom(denom_afip):
            payload['datos_difieren'] = True
            payload['denominacion_administranet'] = nom_admin
            payload['denominacion_afip'] = denom_afip

    return JsonResponse(payload)


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def cliente_actualizar_desde_afip(request, id_cliente):
    """
    Actualiza el cliente en administraNET con la denominación de AFIP.
    Body: { "denominacion_afip": "RAZÓN SOCIAL AFIP" }.
    Se usa cuando consultar_cuit devuelve datos_difieren y el usuario confirma actualizar.
    """
    base, err = _get_context(request)
    if err:
        return err
    id_cliente = int(id_cliente)
    if id_cliente <= 1:
        return JsonResponse({'ok': False, 'error': 'Cliente no actualizable'}, status=400)
    data = _parse_json(request) or request.POST or {}
    denominacion_afip = (data.get('denominacion_afip') or '').strip()
    if not denominacion_afip:
        return JsonResponse({'ok': False, 'error': 'denominacion_afip requerida'}, status=400)

    from self_checkout.services.cliente_administranet_service import actualizar_cliente_denominacion
    ok = actualizar_cliente_denominacion(base, id_cliente, denominacion_afip)
    if not ok:
        return JsonResponse({'ok': False, 'error': 'No se pudo actualizar el cliente'}, status=500)
    return JsonResponse({'ok': True, 'nombre_cliente': denominacion_afip[:255]})


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def cliente_cuenta_corriente(request, id_cliente):
    """
    Ver cuenta corriente del cliente (como TPV administraNET: Ver cuenta corriente).
    GET cliente/<id_cliente>/cuenta-corriente/?fecha_desde=YYYY-MM-DD&fecha_hasta=YYYY-MM-DD&busqueda=xxx
    Devuelve: nombre_cliente, saldo, movimientos (lista de cuentacliente).
    Solo para clientes distintos de Consumidor Final (id_cliente <> 1).
    """
    base, err = _get_context(request)
    if err:
        return err
    id_cliente = int(id_cliente)
    if id_cliente <= 1:
        return _error_response('E_CF', 'Cuenta corriente no aplica a Consumidor Final', 400)

    from self_checkout.db import mysql_cursor
    fecha_desde = (request.GET.get('fecha_desde') or '').strip()[:10]
    fecha_hasta = (request.GET.get('fecha_hasta') or '').strip()[:10]
    busqueda = (request.GET.get('busqueda') or '').strip()

    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute(
            "SELECT COALESCE(saldo, 0) AS saldo, COALESCE(nombre_cliente, '') AS nombre_cliente FROM cliente WHERE Codigo = %s",
            [id_cliente],
        )
        row = c.fetchone()
        if not row:
            return _error_response(E_ARTICLE_NOT_FOUND, 'Cliente no encontrado', 404)
        saldo = float(row['saldo'] or 0)
        nombre_cliente = (row['nombre_cliente'] or '').strip() or f'Cliente {id_cliente}'

        # Movimientos: cuentacliente para este cliente; opcional filtro por fechas y búsqueda
        sql = """
            SELECT id_cuentacliente, CodigoMovimiento, Fecha, TipoComprobante, NroComprobante,
                   COALESCE(NroCompBusq, NroComprobante, '') AS NroCompBusq,
                   COALESCE(ImporteVenta, 0) AS ImporteVenta, COALESCE(Importecobro, 0) AS Importecobro,
                   COALESCE(Saldo, 0) AS Saldo, COALESCE(Estado, '') AS Estado,
                   COALESCE(anulado, 'No') AS anulado, COALESCE(tpv_comp, 'No') AS tpv_comp
            FROM cuentacliente
            WHERE Codigo = %s
        """
        params = [id_cliente]
        if fecha_desde:
            sql += " AND Fecha >= %s"
            params.append(fecha_desde)
        if fecha_hasta:
            sql += " AND Fecha <= %s"
            params.append(fecha_hasta)
        if busqueda:
            sql += " AND (NroCompBusq LIKE %s OR TipoComprobante LIKE %s OR COALESCE(Estado,'') LIKE %s)"
            term = '%' + busqueda + '%'
            params.extend([term, term, term])
        sql += " ORDER BY id_cuentacliente DESC LIMIT 500"
        try:
            c.execute(sql, params)
            rows = c.fetchall()
        except Exception as e:
            if "doesn't exist" in str(e) or 'Unknown column' in str(e):
                return JsonResponse({
                    'nombre_cliente': nombre_cliente,
                    'saldo': saldo,
                    'movimientos': [],
                    'error': 'Tabla cuentacliente no disponible',
                })
            raise

        movimientos = []
        for r in rows:
            f = r.get('Fecha')
            if f and hasattr(f, 'strftime'):
                f = f.strftime('%Y-%m-%d')
            movimientos.append({
                'id_cuentacliente': r.get('id_cuentacliente'),
                'CodigoMovimiento': r.get('CodigoMovimiento'),
                'Fecha': f,
                'TipoComprobante': (r.get('TipoComprobante') or ''),
                'NroComprobante': (r.get('NroComprobante') or ''),
                'NroCompBusq': (r.get('NroCompBusq') or ''),
                'ImporteVenta': float(r.get('ImporteVenta') or 0),
                'Importecobro': float(r.get('Importecobro') or 0),
                'Saldo': float(r.get('Saldo') or 0),
                'Estado': (r.get('Estado') or ''),
                'anulado': (r.get('anulado') or 'No'),
                'tpv_comp': (r.get('tpv_comp') or 'No'),
            })

    return JsonResponse({
        'nombre_cliente': nombre_cliente,
        'saldo': saldo,
        'movimientos': movimientos,
    })


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def cart_set_email(request, cart_id):
    """Captura email (opcional en Consumidor Final; obligatorio en Ticket Factura si el PV tiene envío habilitado). Pasa a pago_pendiente (valida stock)."""
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST
    email = (data.get('email') or '').strip()
    if email and '@' not in email:
        return _error_response(E_EMAIL_REQUIRED, 'Si ingresás email, debe ser válido', 400)

    from self_checkout.db import mysql_cursor
    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute("SELECT id, estado FROM self_checkout_cart WHERE id = %s", [cart_id])
        cart = c.fetchone()
    if not cart:
        return _error_response(E_CART_NOT_FOUND, 'Carrito no encontrado', 404)

    with mysql_cursor(base) as c:
        c.execute("UPDATE self_checkout_cart SET email = %s WHERE id = %s", [email or None, cart_id])
    cart_svc = CartService(base)
    ok, error_msg = cart_svc.validar_stock_y_preparar_pago(cart_id)
    if not ok:
        return _error_response(E_STOCK_INSUFFICIENT, error_msg, 400)
    return JsonResponse({'ok': True, 'estado': 'pago_pendiente'})


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def cart_confirm(request, cart_id):
    """
    Confirma venta. Requiere carrito en pago_aprobado.
    Por ahora: si está en pago_pendiente, simulamos pago aprobado y confirmamos.
    """
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST
    email = (data.get('email') or '').strip()
    id_cliente = int(data.get('id_cliente', 1))
    payment_method = (data.get('payment_method') or '').strip().lower() or None  # efectivo, tarjeta (TPV)

    from self_checkout.db import mysql_cursor
    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute("SELECT estado, email FROM self_checkout_cart WHERE id = %s", [cart_id])
        row = c.fetchone()
    if not row:
        return _error_response(E_CART_NOT_FOUND, 'Carrito no encontrado', 404)
    estado, email_actual = row['estado'], row['email']
    email_final = (email_actual or '').strip() or (email or '').strip()
    if not email_final or '@' not in email_final:
        return _error_response(E_EMAIL_REQUIRED, 'Email obligatorio antes de confirmar', 400)
    if not email_actual and email:
        with mysql_cursor(base) as c:
            c.execute("UPDATE self_checkout_cart SET email = %s WHERE id = %s", [email, cart_id])

    # Si pago_pendiente: permitir confirmar con payment_method efectivo/tarjeta (TPV) o tras pago MP
    if estado == 'pago_pendiente':
        if payment_method in ('efectivo', 'tarjeta'):
            logger.info("cart_confirm: carrito %s pago_pendiente, confirmando con método %s (TPV)", cart_id, payment_method)
        else:
            logger.info("cart_confirm: carrito %s en pago_pendiente, pasando a pago_aprobado para confirmar", cart_id)
        with mysql_cursor(base) as c:
            c.execute("UPDATE self_checkout_cart SET estado = 'pago_aprobado' WHERE id = %s", [cart_id])

    inv_svc = InvoiceService(base)
    tipo_comp = inv_svc.determinar_tipo_comprobante(id_cliente, data.get('cuit'))

    # Usuario logueado (login guarda id_usuario en session['user'])
    session_user = request.session.get('user') or {}
    id_usuario = session_user.get('id_usuario')

    cod_viajante_req = data.get('cod_viajante')
    if cod_viajante_req is not None:
        try:
            cod_viajante_req = int(cod_viajante_req)
        except (TypeError, ValueError):
            cod_viajante_req = None
    from .services.serie_service import validar_series_carrito
    ok_series, err_series = validar_series_carrito(base, cart_id)
    if not ok_series:
        return _error_response('SERIES_INVALID', err_series or 'Faltan números de serie', 400)

    # Medios de cobro TPV (como administraNET: importe efectivo, recibido, cambio, importe tarjeta + detalle tarjeta)
    tpv_importe_efectivo = None
    tpv_pago_efectivo = None
    tpv_cambio_efectivo = None
    tpv_importe_tarjeta = None
    tpv_tarjeta_nombre = data.get('tpv_tarjeta_nombre') or ''
    tpv_plan_nombre = data.get('tpv_plan_nombre') or ''
    tpv_cuotas = data.get('tpv_cuotas')
    tpv_nro_tarjeta = (data.get('tpv_nro_tarjeta') or '').strip()
    tpv_nro_cupon = (data.get('tpv_nro_cupon') or '').strip()
    tpv_nro_lote = (data.get('tpv_nro_lote') or '').strip()
    tpv_intereses = None
    tpv_valor_cuota = None
    tpv_importe_parcial = None
    if data.get('tpv_importe_efectivo') is not None:
        try:
            tpv_importe_efectivo = float(data.get('tpv_importe_efectivo'))
        except (TypeError, ValueError):
            pass
    if data.get('tpv_pago_efectivo') is not None:
        try:
            tpv_pago_efectivo = float(data.get('tpv_pago_efectivo'))
        except (TypeError, ValueError):
            pass
    if data.get('tpv_cambio_efectivo') is not None:
        try:
            tpv_cambio_efectivo = float(data.get('tpv_cambio_efectivo'))
        except (TypeError, ValueError):
            pass
    if data.get('tpv_importe_tarjeta') is not None:
        try:
            tpv_importe_tarjeta = float(data.get('tpv_importe_tarjeta'))
        except (TypeError, ValueError):
            pass
    if data.get('tpv_cuotas') is not None:
        try:
            tpv_cuotas = int(data.get('tpv_cuotas'))
        except (TypeError, ValueError):
            tpv_cuotas = 1
    if data.get('tpv_intereses') is not None:
        try:
            tpv_intereses = float(data.get('tpv_intereses'))
        except (TypeError, ValueError):
            pass
    if data.get('tpv_valor_cuota') is not None:
        try:
            tpv_valor_cuota = float(data.get('tpv_valor_cuota'))
        except (TypeError, ValueError):
            pass
    if data.get('tpv_importe_parcial') is not None:
        try:
            tpv_importe_parcial = float(data.get('tpv_importe_parcial'))
        except (TypeError, ValueError):
            pass

    conf_svc = ConfirmationService(base)
    ok, error_msg, result = conf_svc.confirmar(
        cart_id=cart_id,
        id_cliente=id_cliente,
        email=email_final,
        tipo_comprobante=tipo_comp,
        cuit=data.get('cuit'),
        id_usuario=id_usuario,
        cod_viajante=cod_viajante_req,
        tpv_importe_efectivo=tpv_importe_efectivo,
        tpv_pago_efectivo=tpv_pago_efectivo,
        tpv_cambio_efectivo=tpv_cambio_efectivo,
        tpv_importe_tarjeta=tpv_importe_tarjeta,
        tpv_tarjeta_nombre=tpv_tarjeta_nombre or None,
        tpv_plan_nombre=tpv_plan_nombre or None,
        tpv_cuotas=tpv_cuotas,
        tpv_nro_tarjeta=tpv_nro_tarjeta or None,
        tpv_nro_cupon=tpv_nro_cupon or None,
        tpv_nro_lote=tpv_nro_lote or None,
        tpv_intereses=tpv_intereses,
        tpv_valor_cuota=tpv_valor_cuota,
        tpv_importe_parcial=tpv_importe_parcial,
    )
    if ok:
        if SESSION_CAEA_MODE_KEY in request.session:
            del request.session[SESSION_CAEA_MODE_KEY]
            request.session.modified = True
        # FE se ejecutó dentro de confirmar (si está configurado). Sin CAE/CAEA no se confirma.
        estado_fe = result.get('estado_fe') or 'pendiente'
        inv_id = inv_svc.guardar_invoice(
            cart_id=cart_id,
            codigo_movimiento=result['codigo_movimiento'],
            id_cuentacliente=result['id_cuentacliente'],
            nro_comprobante=result['nro_comprobante'],
            tipo_comprobante=result['tipo_comprobante'],
            estado=estado_fe,
            cae=result.get('cae'),
            vto_cae=result.get('vto_cae'),
            fe_regimen=result.get('fe_regimen'),
        )
        # Caja: se registra dentro de confirmar (transacción atómica, paridad administraNET)
        logger.info("cart_confirm: carrito %s confirmado ok, cod_mov=%s nro_comp=%s", cart_id, result.get('codigo_movimiento'), result.get('nro_comprobante'))
        return JsonResponse({'ok': True, 'resultado': result, 'fe_estado': estado_fe})
    # Validación de medios de cobro (suma ≠ total): devolver mensaje claro al cliente
    if error_msg and ('no coincide con el total' in error_msg or 'medios de cobro' in error_msg.lower()):
        return _error_response('E_MEDIOS_COBRO', error_msg, 400)
    # Marcar carrito para recuperación por supervisor
    _marcar_cart_error_confirmacion(base, cart_id, error_msg)
    # Kiosco: cualquier otro error → "Fuera de servicio" (sin detalles para el cliente)
    return _error_response(
        E_AFIP_UNAVAILABLE,
        'El autoservicio se encuentra fuera de servicio. Solicitá asistencia.',
        400,
    )


@require_http_methods(['POST'])
@require_self_checkout_permission('supervisor')
def cart_confirm_pending(request, cart_id):
    """
    Emite comprobante para un carrito en pago_aprobado (desde UI de carritos pendientes).
    Usa datos del carrito (email, id_cliente, cuit); si email vacío usa placeholder (CF).
    Solo supervisor o admin.
    """
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute("""
            SELECT id, estado, id_cliente, email, cuit, id_sucursal, kiosk_id
            FROM self_checkout_cart WHERE id = %s
        """, [cart_id])
        row = c.fetchone()
    if not row:
        return _error_response(E_CART_NOT_FOUND, 'Carrito no encontrado', 404)
    if row['estado'] not in ('pago_aprobado', 'error_confirmacion'):
        return _error_response(
            'E_CART_STATE',
            f'El carrito no está en pago aprobado ni en error de confirmación (estado: {row["estado"]})',
            400,
        )
    return _do_confirm_pending(base, request, cart_id, row)


@require_http_methods(['GET'])
@require_self_checkout_permission('supervisor')
def talonarios_consulta_afip(request):
    """
    Consulta numeración AFIP vs AdministraNET para un talonario.
    Query: id_punto_venta, tipo_comprobante.
    Solo supervisor.
    """
    base, err = _get_context(request)
    if err:
        return err
    id_pv = request.GET.get('id_punto_venta')
    tipo = (request.GET.get('tipo_comprobante') or '').strip().upper()
    if not id_pv or not tipo:
        return _error_response('E_PARAMS', 'Faltan id_punto_venta y tipo_comprobante', 400)
    try:
        id_pv = int(id_pv)
    except (TypeError, ValueError):
        return _error_response('E_PARAMS', 'id_punto_venta debe ser numérico', 400)

    from self_checkout.fe_sync import get_ultimo_autorizado_afip
    from self_checkout.services.talonarios_service import obtener_talonario

    ultimo_afip, err_afip = get_ultimo_autorizado_afip(base, id_pv, tipo)
    if err_afip is not None:
        return JsonResponse({
            'ok': False,
            'error': err_afip,
            'id_punto_venta': id_pv,
            'tipo_comprobante': tipo,
        })

    talon = obtener_talonario(base, id_pv, tipo)
    nro_talonario = talon.get('Nro') if talon else None
    proximo_afip = (ultimo_afip or 0) + 1
    sincronizado = nro_talonario is not None and int(nro_talonario) == proximo_afip

    return JsonResponse({
        'id_punto_venta': id_pv,
        'tipo_comprobante': tipo,
        'ultimo_afip': ultimo_afip,
        'proximo_afip': proximo_afip,
        'nro_talonario': int(nro_talonario) if nro_talonario is not None else None,
        'sincronizado': sincronizado,
    })


@require_http_methods(['POST'])
@require_self_checkout_permission('supervisor')
def talonarios_sincronizar(request):
    """
    Sincroniza talonarios.Nro con el valor de AFIP (ARCA próximo).
    Body: { "id_punto_venta": 1, "tipo_comprobante": "FC", "nro": 2 }
    Solo supervisor.
    """
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or {}
    id_pv = data.get('id_punto_venta')
    tipo = (data.get('tipo_comprobante') or '').strip().upper()
    nro = data.get('nro')
    if id_pv is None or not tipo or nro is None:
        return _error_response('E_PARAMS', 'Faltan id_punto_venta, tipo_comprobante o nro', 400)
    try:
        id_pv = int(id_pv)
        nro = int(nro)
    except (TypeError, ValueError):
        return _error_response('E_PARAMS', 'id_punto_venta y nro deben ser numéricos', 400)

    from self_checkout.services.talonarios_service import actualizar_talonario
    ok = actualizar_talonario(base, id_pv, tipo, nro)
    if not ok:
        return _error_response('E_UPDATE', 'No se pudo actualizar el talonario', 400)
    return JsonResponse({
        'ok': True,
        'id_punto_venta': id_pv,
        'tipo_comprobante': tipo,
        'nro_actualizado': nro,
    })


@require_http_methods(['POST'])
@require_self_checkout_permission('supervisor')
def cart_cancel(request, cart_id):
    """
    Cancela/elimina un carrito en pago_aprobado o error_confirmacion.
    Solo supervisor. Para carritos que no se van a recuperar.
    """
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute("SELECT id, estado FROM self_checkout_cart WHERE id = %s", [cart_id])
        row = c.fetchone()
    if not row:
        return _error_response(E_CART_NOT_FOUND, 'Carrito no encontrado', 404)
    if row['estado'] not in ('pago_aprobado', 'error_confirmacion', 'borrador'):
        return _error_response(
            'E_CART_STATE',
            f'Solo se pueden cancelar carritos en pago aprobado, error de confirmación o borrador (estado: {row["estado"]})',
            400,
        )
    with mysql_cursor(base) as c:
        c.execute("UPDATE self_checkout_cart SET estado = 'cancelado' WHERE id = %s", [cart_id])
    return JsonResponse({'ok': True})


@require_http_methods(['POST'])
@require_self_checkout_permission('supervisor')
def cart_buscar_pago_mp(request, cart_id):
    """
    Busca pagos aprobados en Mercado Pago para un carrito en borrador o pago_pendiente.
    Si encuentra pago aprobado en MP con external_reference cart_X_pi_Y, actualiza el carrito
    a pago_aprobado y emite el comprobante. Un solo clic: buscar + emitir.
    """
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute(
            "SELECT id, estado, id_cliente, email, cuit, id_sucursal, kiosk_id FROM self_checkout_cart WHERE id = %s",
            [cart_id],
        )
        row = c.fetchone()
    if not row:
        return _error_response(E_CART_NOT_FOUND, 'Carrito no encontrado', 404)
    if row['estado'] not in ('borrador', 'pago_pendiente'):
        return _error_response(
            'E_CART_STATE',
            f'Buscar pago MP solo aplica a carritos en borrador o pago pendiente (estado: {row["estado"]})',
            400,
        )

    from mercadopago.services.payment_service import sincronizar_pagos_desde_mp
    sync_count, sync_error = sincronizar_pagos_desde_mp(base_empresa=base, dias=30, limit=100)
    if sync_error:
        return _error_response('E_SYNC_MP', f'No se pudo sincronizar con Mercado Pago: {sync_error}', 400)

    with mysql_cursor(base, dict_cursor=True) as c:
        c.execute("""
            SELECT sc.estado, EXISTS(
                SELECT 1 FROM self_checkout_payment_intent pi
                WHERE pi.cart_id = sc.id AND pi.estado = 'aprobado'
            ) AS pi_aprobado
            FROM self_checkout_cart sc WHERE sc.id = %s
        """, [cart_id])
        updated = c.fetchone()

    if not updated or updated['estado'] != 'pago_aprobado' or not updated['pi_aprobado']:
        return _error_response(
            'E_NO_PAGO_MP',
            'No se encontró pago aprobado en Mercado Pago para este carrito. Si el cliente pagó, verificá en MP.',
            400,
        )

    row['estado'] = 'pago_aprobado'
    return _do_confirm_pending(base, request, cart_id, row)


def _do_confirm_pending(base, request, cart_id, row):
    """Ejecuta la confirmación (emitir comprobante) para un carrito en pago_aprobado."""
    from self_checkout.db import mysql_cursor
    from .services.serie_service import validar_series_carrito
    if row.get('estado') == 'error_confirmacion':
        with mysql_cursor(base) as c:
            c.execute("UPDATE self_checkout_cart SET estado = 'pago_aprobado' WHERE id = %s", [cart_id])

    ok_series, err_series = validar_series_carrito(base, cart_id)
    if not ok_series:
        return _error_response('SERIES_INVALID', err_series or 'Faltan números de serie', 400)

    id_cliente = row.get('id_cliente') or 1
    email = (row.get('email') or '').strip() or 'noreply@autoconfirm.local'
    cuit = (row.get('cuit') or '').strip() or None
    inv_svc = InvoiceService(base)
    tipo_comp = inv_svc.determinar_tipo_comprobante(id_cliente, cuit)
    session_user = getattr(request, 'session', {}).get('user') or {}
    id_usuario = session_user.get('id_usuario') if isinstance(session_user, dict) else None

    conf_svc = ConfirmationService(base)
    ok, error_msg, result = conf_svc.confirmar(
        cart_id=cart_id,
        id_cliente=id_cliente,
        email=email,
        tipo_comprobante=tipo_comp,
        cuit=cuit,
        id_usuario=id_usuario,
    )
    if not ok:
        _marcar_cart_error_confirmacion(base, cart_id, error_msg)
        err_lower = (error_msg or '').lower()
        if any(x in err_lower for x in ('cae', 'caea', 'afip', 'no se pudo obtener', 'wsaa', 'wsfe', 'coe.notauthorized', 'computador no autorizado', 'talonario', 'arca')):
            code = E_AFIP_UNAVAILABLE
            msg = _mensaje_afip_para_usuario(error_msg) if 'talonario' not in err_lower and 'arca' not in err_lower else error_msg
        elif 'stock' in err_lower or 'disponible' in err_lower:
            code = E_STOCK_INSUFFICIENT
            msg = error_msg
        else:
            code = E_CONFIRM_FAILED
            msg = error_msg
        return _error_response(code, msg, 400)

    estado_fe = result.get('estado_fe') or 'pendiente'
    inv_svc.guardar_invoice(
        cart_id=cart_id,
        codigo_movimiento=result['codigo_movimiento'],
        id_cuentacliente=result['id_cuentacliente'],
        nro_comprobante=result['nro_comprobante'],
        tipo_comprobante=result['tipo_comprobante'],
        estado=estado_fe,
        cae=result.get('cae'),
        vto_cae=result.get('vto_cae'),
        fe_regimen=result.get('fe_regimen'),
    )
    # Caja: se registra dentro de confirmar (transacción atómica)
    logger.info(
        "cart_buscar_pago_mp: carrito %s confirmado ok, cod_mov=%s nro_comp=%s",
        cart_id, result.get('codigo_movimiento'), result.get('nro_comprobante'),
    )
    return JsonResponse({'ok': True, 'resultado': result, 'fe_estado': estado_fe})


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def cart_ticket(request, cart_id):
    """
    Devuelve los datos del ticket/comprobante en JSON para mostrar en pantalla.
    Incluye todos los datos obligatorios AFIP para FA y FB.
    """
    base, err = _get_context(request)
    if err:
        return err
    
    from self_checkout.views import _get_ticket_data
    ticket_data = _get_ticket_data(base, cart_id)
    if not ticket_data:
        return _error_response('TICKET_NOT_FOUND', 'Comprobante no encontrado', 404)
    
    # Convertir objetos datetime a string para JSON
    import json
    from decimal import Decimal
    from datetime import datetime
    
    def json_serializer(obj):
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return str(obj)
    
    # Serializar items correctamente
    items_json = []
    for item in ticket_data.get('items', []):
        items_json.append({
            'descripcion': item.get('descripcion', ''),
            'cantidad': float(item.get('cantidad') or 0),
            'precio_unitario': float(item.get('precio_unitario') or 0),
            'importe_total': float(item.get('importe_total') or 0),
            'alicuota_iva': float(item.get('alicuota_iva') or 0),
            'importe_iva': float(item.get('importe_iva') or 0),
        })
    
    response_data = {
        'tipo_comprobante': ticket_data.get('tipo_comprobante'),
        'tipo_comprobante_letra': ticket_data.get('tipo_comprobante_letra'),
        'tipo_comprobante_nombre': ticket_data.get('tipo_comprobante_nombre'),
        'nro_comprobante_formateado': ticket_data.get('nro_comprobante_formateado'),
        'fecha_emision': ticket_data.get('fecha_emision'),
        'empresa': ticket_data.get('empresa'),
        'cliente': ticket_data.get('cliente'),
        'items': items_json,
        'subtotal': float(ticket_data.get('subtotal') or 0),
        'total': float(ticket_data.get('total') or 0),
        'ivas': ticket_data.get('ivas', []),
        'cae': ticket_data.get('cae'),
        'vto_cae': ticket_data.get('vto_cae'),
        'fe_regimen': ticket_data.get('fe_regimen'),
        'qr_data': ticket_data.get('qr_data'),
        'importe_letras': ticket_data.get('importe_letras'),
        'ticket_url': f'/self_checkout/ticket/{cart_id}/',
    }
    
    return JsonResponse(response_data)


# --- Sesión kiosco: un kiosco solo puede estar abierto en una máquina a la vez ---
STALE_SESSION_MINUTES = 5


def _ensure_session_key(request):
    """Asegura que la sesión tenga session_key (persistida)."""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def kiosk_list(request):
    """Lista kioscos configurados con estado: disponible / en_uso (para selector)."""
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.db import mysql_cursor
    from datetime import datetime, timedelta
    session_key = _ensure_session_key(request)
    stale = datetime.now() - timedelta(minutes=STALE_SESSION_MINUTES)

    def build_kiosk(r, session_key_opt=None, last_heartbeat_val=None):
        last = last_heartbeat_val or r.get('last_heartbeat')
        if last and getattr(last, 'tzinfo', None):
            last = last.replace(tzinfo=None)
        sk = session_key_opt if session_key_opt is not None else r.get('session_key')
        in_use = bool(last and last > stale and sk != session_key)
        return {
            'kiosk_id': r['kiosk_id'],
            'id_sucursal': r['id_sucursal'],
            'id_punto_venta': r['id_punto_venta'],
            'id_deposito': r['id_deposito'],
            'activo': bool(r['activo']),
            'modo_rfid': r.get('modo_rfid') or 'delta',
            'en_uso': in_use,
            'es_mi_sesion': sk == session_key,
        }

    try:
        with mysql_cursor(base, dict_cursor=True) as c:
            c.execute("""
                SELECT k.kiosk_id, k.id_sucursal, k.id_punto_venta, k.id_deposito, k.activo, k.modo_rfid,
                       s.session_key, s.last_heartbeat
                FROM self_checkout_kiosk k
                LEFT JOIN self_checkout_kiosk_session s ON s.kiosk_id = k.kiosk_id
                WHERE k.activo = 1
                ORDER BY k.kiosk_id
            """)
            rows = c.fetchall()
        kiosks = [build_kiosk(r) for r in rows]
        return JsonResponse({'kiosks': kiosks})
    except Exception as e:
        err_msg = str(e).lower()
        if 'self_checkout_kiosk_session' in err_msg and ("doesn't exist" in err_msg or "no existe" in err_msg):
            logger.warning('kiosk_list: tabla sesión no existe en %s, listando sin estado en_uso', base)
            try:
                with mysql_cursor(base, dict_cursor=True) as c:
                    c.execute("""
                        SELECT kiosk_id, id_sucursal, id_punto_venta, id_deposito, activo, modo_rfid
                        FROM self_checkout_kiosk
                        WHERE activo = 1
                        ORDER BY kiosk_id
                    """)
                    rows = c.fetchall()
                kiosks = [build_kiosk(r, last_heartbeat_val=None) for r in rows]
                return JsonResponse({'kiosks': kiosks})
            except Exception as e2:
                logger.exception('kiosk_list fallback failed: %s', base)
                return _error_response(E_KIOSK_NOT_CONFIGURED, 'Error al listar kioscos', 500)
        logger.exception('kiosk_list failed: %s', base)
        return _error_response(E_KIOSK_NOT_CONFIGURED, 'Error al listar kioscos', 500)


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def payment_methods_list(request):
    """
    Lista medios de pago disponibles. Si kiosk_id tiene modo_tpv=1, incluye Efectivo y Tarjeta
    además de Mercado Pago (QR y dispositivo). Para self-checkout solo MP.
    Query: ?kiosk_id=xxx (opcional; si no se envía, se devuelven solo métodos de autoservicio).
    """
    base, err = _get_context(request)
    if err:
        return err
    kiosk_id = (request.GET.get('kiosk_id') or '').strip()
    modo_tpv = False
    if kiosk_id:
        kiosk_svc = KioskSessionService(base)
        config = kiosk_svc.get_kiosk_config(kiosk_id)
        if config:
            modo_tpv = bool(config.get('modo_tpv', 0))
    # Siempre: Mercado Pago QR y dispositivo (flujo actual)
    methods = [
        {'code': 'mercadopago_qr', 'name': 'Pago con QR (Mercado Pago)', 'type': 'digital'},
        {'code': 'mercadopago_device', 'name': 'Pago en dispositivo (tarjeta/celular)', 'type': 'digital'},
    ]
    if modo_tpv:
        methods = [
            {'code': 'efectivo', 'name': 'Efectivo', 'type': 'cash'},
            {'code': 'tarjeta', 'name': 'Tarjeta', 'type': 'card'},
            {'code': 'mercadopago_qr', 'name': 'Mercado Pago (QR)', 'type': 'digital'},
            {'code': 'mercadopago_device', 'name': 'Mercado Pago (dispositivo)', 'type': 'digital'},
        ]
    return JsonResponse({'modo_tpv': modo_tpv, 'payment_methods': methods})


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def price_lists_list(request):
    """Lista listas de precio para selector TPV (táctil)."""
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.services.config_options_service import listar_listas_precio
    listas = listar_listas_precio(base)
    return JsonResponse({'listas': listas})


@require_http_methods(['GET'])
@require_self_checkout_permission('kiosk')
def vendedores_list(request):
    """Lista vendedores (viajantes) para selector TPV (táctil)."""
    base, err = _get_context(request)
    if err:
        return err
    from self_checkout.services.config_options_service import listar_viajantes
    viajantes = listar_viajantes(base)
    out = [{'cod_viajante': r.get('CodViajante'), 'nombre': (r.get('Nombre') or '').strip() or f"Vendedor {r.get('CodViajante')}"} for r in viajantes]
    return JsonResponse({'vendedores': out})


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def kiosk_session_acquire(request, kiosk_id):
    """
    Reserva el kiosco para esta sesión. Un kiosco solo puede estar abierto en una máquina.
    Si ya está en uso por otra sesión (no stale), retorna 409 KIOSK_IN_USE.
    """
    base, err = _get_context(request)
    if err:
        return err
    data = _parse_json(request) or request.POST or {}
    machine_id = (data.get('machine_id') or '').strip() or None
    session_key = _ensure_session_key(request)

    kiosk_svc = KioskSessionService(base)
    config = kiosk_svc.get_kiosk_config(kiosk_id)
    if not config:
        return _error_response(E_KIOSK_NOT_CONFIGURED, 'Kiosco no configurado o inactivo', 404)

    from self_checkout.db import mysql_cursor
    from datetime import datetime, timedelta
    stale = datetime.now() - timedelta(minutes=STALE_SESSION_MINUTES)
    try:
        with mysql_cursor(base, dict_cursor=True) as c:
            c.execute("""
                SELECT session_key, last_heartbeat FROM self_checkout_kiosk_session
                WHERE kiosk_id = %s
            """, [kiosk_id])
            row = c.fetchone()
        if row:
            last = row['last_heartbeat']
            last_naive = last.replace(tzinfo=None) if hasattr(last, 'replace') and getattr(last, 'tzinfo', None) else last
            if last_naive > stale and row['session_key'] != session_key:
                return JsonResponse({
                    'error': 'Este kiosco está abierto en otra máquina. No se puede abrir el mismo kiosco en dos lugares.',
                    'code': E_KIOSK_IN_USE,
                }, status=409)

        with mysql_cursor(base) as c:
            c.execute("""
                INSERT INTO self_checkout_kiosk_session (kiosk_id, session_key, machine_id, started_at, last_heartbeat)
                VALUES (%s, %s, %s, NOW(), NOW())
                ON DUPLICATE KEY UPDATE
                    session_key = VALUES(session_key),
                    machine_id = VALUES(machine_id),
                    started_at = IF(session_key = VALUES(session_key), started_at, NOW()),
                    last_heartbeat = NOW()
            """, [kiosk_id, session_key, machine_id])
        # Devolver config del kiosco (incl. vendedor, modo_tpv, id_deposito, punto de venta para header TPV)
        cod_viajante = config.get('cod_viajante')
        modo_tpv = bool(config.get('modo_tpv', 0))
        id_deposito = config.get('id_deposito')
        id_pv = config.get('id_punto_venta')
        payload = {'ok': True, 'acquired': True, 'modo_tpv': modo_tpv}
        if cod_viajante is not None:
            payload['cod_viajante'] = int(cod_viajante)
        if id_deposito is not None:
            payload['id_deposito'] = int(id_deposito)
        if id_pv is not None:
            payload['id_punto_venta'] = int(id_pv)
            # nro_punto_venta para mostrar en header TPV
            with mysql_cursor(base, dict_cursor=True) as c:
                c.execute(
                    "SELECT nro_punto_venta FROM punto_venta WHERE id_punto_venta = %s",
                    [id_pv],
                )
                pv_row = c.fetchone()
            payload['nro_punto_venta'] = str(pv_row['nro_punto_venta']) if pv_row and pv_row.get('nro_punto_venta') is not None else str(id_pv)
        return JsonResponse(payload)
    except Exception as e:
        if _is_kiosk_session_table_missing(e):
            logger.warning('kiosk_session_acquire: tabla sesión no existe en %s', base)
            return _tables_missing_response(base)
        logger.exception('kiosk_session_acquire failed: kiosk_id=%s', kiosk_id)
        return _error_response(E_CONFIRM_FAILED, 'Error al reservar kiosco', 500)


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def kiosk_session_heartbeat(request, kiosk_id):
    """Actualiza last_heartbeat para la sesión actual. Llamar periódicamente (ej. cada 1 min)."""
    base, err = _get_context(request)
    if err:
        return err
    session_key = _ensure_session_key(request)
    from self_checkout.db import mysql_cursor
    try:
        with mysql_cursor(base) as c:
            c.execute("""
                UPDATE self_checkout_kiosk_session
                SET last_heartbeat = NOW() WHERE kiosk_id = %s AND session_key = %s
            """, [kiosk_id, session_key])
        return JsonResponse({'ok': True})
    except Exception as e:
        if _is_kiosk_session_table_missing(e):
            return _tables_missing_response(base)
        logger.exception('kiosk_session_heartbeat failed: kiosk_id=%s', kiosk_id)
        return JsonResponse({'ok': False}, status=500)


@require_http_methods(['POST'])
@require_self_checkout_permission('kiosk')
def kiosk_session_release(request, kiosk_id):
    """Libera el kiosco para esta sesión (al cerrar o salir)."""
    base, err = _get_context(request)
    if err:
        return err
    session_key = _ensure_session_key(request)
    from self_checkout.db import mysql_cursor
    try:
        with mysql_cursor(base) as c:
            c.execute("""
                DELETE FROM self_checkout_kiosk_session
                WHERE kiosk_id = %s AND session_key = %s
            """, [kiosk_id, session_key])
        return JsonResponse({'ok': True})
    except Exception as e:
        if _is_kiosk_session_table_missing(e):
            return _tables_missing_response(base)
        logger.exception('kiosk_session_release failed: kiosk_id=%s', kiosk_id)
        return JsonResponse({'ok': False}, status=500)
