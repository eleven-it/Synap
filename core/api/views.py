from pathlib import Path
from typing import Optional

import jwt
from django.conf import settings
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone

from core.models import Contact, Country, FiscalResponsibility, State, Currency
from core.services.support_conocimiento import build_conocimiento_items_from_docs


def _json_session_required(request):
    """
    Sesión administraNET (login Synap). Devuelve JsonResponse 401 si no hay usuario en sesión.
    """
    if not request.session.get('user'):
        return JsonResponse({'error': 'No autenticado.'}, status=401)
    return None


def _support_rag_auth_error_response(request) -> Optional[JsonResponse]:
    """
    GET conocimiento RAG: en producción exige SUPPORT_SYNAP_JWT_SECRET y Bearer JWT (HS256, con exp).
    Fuera de producción: si el secret está vacío se permite sin token (desarrollo); si está definido, misma validación que producción.
    """
    env = (getattr(settings, 'ENVIRONMENT', '') or '').strip().lower()
    is_prod = env in ('production', 'produccion')
    secret = (getattr(settings, 'SUPPORT_SYNAP_JWT_SECRET', None) or '').strip()

    if is_prod and not secret:
        return JsonResponse(
            {
                'error': (
                    'Servicio no configurado: defina SUPPORT_SYNAP_JWT_SECRET en Synap y en Support '
                    '(mismo valor) para acceder al conocimiento RAG.'
                )
            },
            status=503,
        )

    if not is_prod and not secret:
        if getattr(settings, 'DEBUG', False):
            return None
        return JsonResponse(
            {
                'error': (
                    'Conocimiento RAG: defina SUPPORT_SYNAP_JWT_SECRET y use Bearer JWT cuando DEBUG=False '
                    '(p. ej. staging), o active DEBUG solo en desarrollo local.'
                )
            },
            status=503,
        )

    auth = (request.headers.get('Authorization') or '').strip()
    if not auth.lower().startswith('bearer '):
        return JsonResponse({'error': 'No autorizado.'}, status=401)
    token = auth[7:].strip()
    if not token:
        return JsonResponse({'error': 'No autorizado.'}, status=401)
    try:
        jwt.decode(
            token,
            secret,
            algorithms=['HS256'],
            options={'require': ['exp']},
        )
    except jwt.PyJWTError:
        return JsonResponse({'error': 'Token inválido o expirado.'}, status=401)
    return None


def fecha_servidor_api(request):
    """
    GET /core/api/fecha-servidor/
    Devuelve fecha y hora del servidor (para barra de estado, paridad con Principal VB6 Control_Fecha).
    """
    deny = _json_session_required(request)
    if deny is not None:
        return deny
    now = timezone.now()
    return JsonResponse({
        "fecha": now.strftime("%Y-%m-%d"),
        "hora": now.strftime("%H:%M:%S"),
        "iso": now.isoformat(),
    })


def contact_search_api(request):
    """API para buscar contactos existentes"""
    deny = _json_session_required(request)
    if deny is not None:
        return deny
    query = request.GET.get('q', '')
    if not query or len(query) < 2:
        return JsonResponse({'results': []})
    
    contacts = Contact.objects.filter(
        Q(name__icontains=query) |
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query) |
        Q(company_name__icontains=query)
    ).filter(is_active=True)[:10]
    
    results = []
    for contact in contacts:
        results.append({
            'id': contact.id,
            'text': contact.display_name,
            'name': contact.display_name,
            'email': contact.email,
            'phone': contact.phone,
            'position': contact.position,
            'company_name': contact.company_name,
        })
    
    return JsonResponse({'results': results}) 

def country_search_api(request):
    """API para buscar países por nombre o código"""
    deny = _json_session_required(request)
    if deny is not None:
        return deny
    query = request.GET.get('q', '').strip()
    if not query:
        countries = Country.objects.filter(is_active=True)[:10]
    else:
        countries = Country.objects.filter(
            Q(name__icontains=query) |
            Q(name_es__icontains=query) |
            Q(name_en__icontains=query) |
            Q(name_pt__icontains=query) |
            Q(code__icontains=query) |
            Q(code_2__icontains=query)
        ).filter(is_active=True)[:10]
    results = [
        {
            'id': c.id,
            'text': c.name,
            'name': c.name,
            'code': c.code,
            'code_2': c.code_2,
            'name_es': c.name_es,
            'name_en': c.name_en,
            'name_pt': c.name_pt,
        } for c in countries
    ]
    return JsonResponse({'results': results})

def fiscal_responsibility_search_api(request):
    """API para buscar responsabilidades fiscales por nombre o código y país"""
    deny = _json_session_required(request)
    if deny is not None:
        return deny
    query = request.GET.get('q', '').strip()
    country_name = request.GET.get('country_name', '').strip()
    country_code = request.GET.get('country_code', '').strip()
    respons = FiscalResponsibility.objects.all()
    if country_name:
        respons = respons.filter(
            Q(country__name__icontains=country_name) |
            Q(country__name_es__icontains=country_name) |
            Q(country__name_en__icontains=country_name) |
            Q(country__name_pt__icontains=country_name)
        )
    if country_code:
        respons = respons.filter(country__code__iexact=country_code)
    if query:
        respons = respons.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query)
        )
    respons = respons[:10]
    results = [
        {
            'id': r.id,
            'text': f"{r.name} ({r.code})",
            'name': r.name,
            'code': r.code,
        } for r in respons
    ]
    return JsonResponse({'results': results}) 

def state_search_api(request):
    """API para buscar estados/provincias por nombre/código y país"""
    deny = _json_session_required(request)
    if deny is not None:
        return deny
    query = request.GET.get('q', '').strip()
    country_id = request.GET.get('country_id')
    country_name = request.GET.get('country_name', '').strip()
    country_code = request.GET.get('country_code', '').strip()
    qs = State.objects.all()
    if country_id:
        qs = qs.filter(country_id=country_id)
    elif country_code:
        qs = qs.filter(country__code__iexact=country_code)
    elif country_name:
        qs = qs.filter(
            Q(country__name__icontains=country_name) |
            Q(country__name_es__icontains=country_name) |
            Q(country__name_en__icontains=country_name) |
            Q(country__name_pt__icontains=country_name)
        )
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(name_es__icontains=query) | Q(name_en__icontains=query) | Q(name_pt__icontains=query) | Q(code__icontains=query))
    qs = qs[:10]
    results = [
        {
            'id': s.id,
            'text': f"{s.name} ({s.code})" if s.code else s.name,
            'name': s.name,
            'code': s.code,
            'country_id': s.country_id,
        } for s in qs
    ]
    return JsonResponse({'results': results}) 

def currency_search_api(request):
    """API para buscar monedas por nombre o código"""
    deny = _json_session_required(request)
    if deny is not None:
        return deny
    query = request.GET.get('q', '').strip()
    if not query:
        currencies = Currency.objects.filter(is_active=True)[:10]
    else:
        currencies = Currency.objects.filter(
            Q(name__icontains=query) |
            Q(code__icontains=query) |
            Q(symbol__icontains=query)
        ).filter(is_active=True)[:10]
    results = [
        {
            'id': c.id,
            'text': f"{c.name} ({c.code})",
            'name': c.name,
            'code': c.code,
            'symbol': c.symbol,
        } for c in currencies
    ]
    return JsonResponse({'results': results})


def proveedor_search_api(request):
    """
    GET /core/api/proveedores/search/?q=...
    Búsqueda predictiva de proveedores por CUIT, nombre/razón social o código.
    Requiere sesión con base_empresa. Devuelve { results: [ { Codigo, Nombre, CUIT, responsabilidad_iva, Tipo, saldo }, ... ] }.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        return JsonResponse({'error': 'Sin empresa activa.', 'results': []}, status=400)
    q = (request.GET.get('q') or '').strip()
    from core.services.administranet_compras import buscar_proveedores
    results = buscar_proveedores(base_empresa, q, limite=15)
    return JsonResponse({'results': results})


def cliente_search_api(request):
    """
    GET /core/api/clientes/search/?q=...&limit=15
    Búsqueda predictiva de clientes por nombre, fantasia, código, CUIT o id_manual_cli.
    Requiere sesión con base_empresa.
    Devuelve { results: [ { Codigo, Nombre, CUIT, id_manual_cli, nombre_fantasia }, ... ] }.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        return JsonResponse({'error': 'Sin empresa activa.', 'results': []}, status=400)
    q = (request.GET.get('q') or '').strip()
    try:
        limit = min(int(request.GET.get('limit', 15)), 30)
    except (TypeError, ValueError):
        limit = 15
    from core.services.administranet_stock import buscar_clientes_predictivo
    try:
        results = buscar_clientes_predictivo(base_empresa, q, limit=limit)
    except Exception:
        results = []
    return JsonResponse({'results': results})


def deposito_search_api(request):
    """
    GET /core/api/depositos/search/?q=...&limit=15
    Búsqueda predictiva de depósitos por nombre o código.
    Requiere sesión con base_empresa.
    Devuelve { results: [ { CodDeposito, NombreDeposito, tipo_mpr }, ... ] }.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        return JsonResponse({'error': 'Sin empresa activa.', 'results': []}, status=400)
    q = (request.GET.get('q') or '').strip().lower()
    try:
        limit = min(int(request.GET.get('limit', 15)), 30)
    except (TypeError, ValueError):
        limit = 15
    from mpr.services import listar_depositos_config
    try:
        deps = listar_depositos_config(base_empresa)
    except Exception:
        deps = []
    results = []
    for d in deps:
        cod = d.get("CodDeposito")
        nombre = (d.get("NombreDeposito") or "").strip()
        tipo = d.get("tipo_mpr") or ""
        hay = not q
        if q:
            hay = (
                q in str(cod).lower()
                or q in nombre.lower()
                or q in tipo.lower()
            )
        if hay:
            results.append({
                "CodDeposito": cod,
                "NombreDeposito": nombre,
                "tipo_mpr": tipo,
            })
        if len(results) >= limit:
            break
    return JsonResponse({'results': results})


def articulo_search_api(request):
    """
    GET /core/api/articulos/search/?q=...
    Query opcional: lista_precio (0–6) para elegir el precio devuelto en PrecioLista (costo, oficial, listas 1–5).
    Búsqueda predictiva de artículos por código, nombre o código de barras.
    Requiere sesión con base_empresa. Devuelve { results: [ { IDArt, CodigoArticulo, Descripcion, Alicuota, ImpuestoInterno, PrecioLista, ... }, ... ] }.
    Usado en Factura de Compra (tab Líneas) y otros formularios que necesiten autocompletado de artículo.
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        return JsonResponse({'error': 'Sin empresa activa.', 'results': []}, status=400)
    q = (request.GET.get('q') or '').strip()
    limit = min(int(request.GET.get('limit', 20)), 30)
    try:
        lista_precio = int(request.GET.get('lista_precio', '2'))
    except (TypeError, ValueError):
        lista_precio = 2
    lista_precio = max(0, min(6, lista_precio))
    from core.services.administranet_stock import _buscar_articulos_con_precios
    try:
        items = _buscar_articulos_con_precios(
            base_empresa, q, limit=limit, lista_precio=lista_precio,
        )
    except Exception:
        items = []
    return JsonResponse({'results': items})


def provincias_api(request):
    """
    API para obtener provincias desde la base de la empresa (administraNET).
    Cascada como Empresa.frm: país → Provincia. Parámetro id_pais opcional.
    """
    from core.services.administranet_empresas import AdministraNETEmpresaService

    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")

    if not base_empresa:
        return JsonResponse({'provincias': []}, status=400)

    id_pais = request.GET.get('id_pais')
    empresa_service = AdministraNETEmpresaService()

    if id_pais:
        provincias = empresa_service.obtener_provincias(base_empresa, int(id_pais))
    else:
        provincias = empresa_service.obtener_provincias(base_empresa)

    return JsonResponse({'provincias': provincias})


def departamentos_api(request):
    """
    API para obtener departamentos desde la base de la empresa (administraNET).
    Cascada como Empresa.frm: Provincia → Departamento. Parámetro cod_provincia opcional.
    """
    from core.services.administranet_empresas import AdministraNETEmpresaService
    
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        return JsonResponse({'departamentos': []}, status=400)
    
    cod_provincia = request.GET.get('cod_provincia')
    empresa_service = AdministraNETEmpresaService()
    
    if cod_provincia:
        departamentos = empresa_service.obtener_departamentos(base_empresa, int(cod_provincia))
    else:
        departamentos = empresa_service.obtener_departamentos(base_empresa)
    
    return JsonResponse({'departamentos': departamentos})


def geocode_api(request):
    """
    GET: Geocodificación con Google Maps API (paridad con CargaSucursal.frm).
    Parámetros: address (obligatorio). La clave API solo se toma de GOOGLE_GEOCODING_API_KEY (settings / .env).
    Devuelve { "lat": str, "lng": str } o { "error": "..." }.
    """
    import json
    import logging
    import urllib.parse
    import urllib.request

    deny = _json_session_required(request)
    if deny is not None:
        return deny

    address = request.GET.get('address', '').strip()
    if not address:
        return JsonResponse({'error': 'Falta el parámetro address.'}, status=400)

    api_key = (getattr(settings, 'GOOGLE_GEOCODING_API_KEY', None) or '').strip()
    if not api_key:
        return JsonResponse(
            {'error': 'Geocodificación no configurada en el servidor (GOOGLE_GEOCODING_API_KEY).'},
            status=503,
        )

    url = (
        'https://maps.googleapis.com/maps/api/geocode/json?address='
        + urllib.parse.quote(address)
        + '&key='
        + urllib.parse.quote(api_key)
    )

    logger_geo = logging.getLogger(__name__)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Synap/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        logger_geo.warning('Geocoding request failed: %s', e, exc_info=True)
        return JsonResponse(
            {'error': 'No se pudo contactar el servicio de geocodificación. Intente más tarde.'},
            status=502,
        )

    if data.get('status') != 'OK' or not data.get('results'):
        return JsonResponse(
            {
                'error': (
                    data.get('error_message')
                    or data.get('status')
                    or 'Sin resultados para la dirección.'
                )
            },
            status=404,
        )

    loc = data['results'][0].get('geometry', {}).get('location', {})
    lat = loc.get('lat')
    lng = loc.get('lng')
    if lat is None or lng is None:
        return JsonResponse({'error': 'Coordenadas no encontradas en la respuesta.'}, status=404)
    return JsonResponse({'lat': str(lat), 'lng': str(lng)})


# --- Tipos de envío por sucursal (paridad ABM_Sucursal_Envio / CargaSucursal_Envio VB6) ---

def _session_user_can_access_sucursal(request, id_sucursal: int) -> bool:
    """
    Admin (usuario supervisor administraNET) puede cualquier sucursal; el resto solo su id_sucursal de sesión.
    """
    user = getattr(request, 'user', None)
    if user and getattr(user, 'is_authenticated', False):
        if hasattr(user, 'is_admin') and callable(getattr(user, 'is_admin', None)):
            try:
                if user.is_admin():
                    return True
            except Exception:
                pass
    su = request.session.get('user') or {}
    sid = su.get('id_sucursal')
    if sid is None:
        return False
    try:
        return int(sid) == int(id_sucursal)
    except (TypeError, ValueError):
        return False


def _base_empresa_from_request(request):
    """Obtiene base_empresa de la sesión; devuelve (base_empresa, error_response)."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    if not base_empresa:
        return None, JsonResponse({'error': 'Sin empresa activa.'}, status=400)
    return base_empresa, None


def sucursal_tipos_envio_list_or_create_api(request, id_sucursal):
    """
    GET: Lista tipos de cobro por envío de la sucursal que se está editando.
    POST: Crea un tipo de envío para esa misma sucursal.
    id_sucursal viene de la URL (branch_id del formulario de edición). Paridad AdministraNET:
    CargaSucursal_Envio.id_sucursales_envios = ABMSucursal.DataSucursal.Recordset.Fields!id_sucursal.
    """
    base_empresa, err = _base_empresa_from_request(request)
    if err:
        return err
    from core.services.administranet_sucursales import AdministraNETSucursalesService
    try:
        id_suc = int(id_sucursal)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'id_sucursal inválido.'}, status=400)
    if not _session_user_can_access_sucursal(request, id_suc):
        return JsonResponse({'error': 'No tiene permiso para operar sobre esta sucursal.'}, status=403)
    svc = AdministraNETSucursalesService()
    if request.method == 'GET':
        lista = svc.listar_tipos_envio_sucursal(base_empresa, id_suc)
        return JsonResponse({'tipos_envio': lista})
    if request.method == 'POST':
        import json
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Cuerpo JSON inválido.'}, status=400)
        created = svc.crear_tipo_envio_sucursal(base_empresa, id_suc, data)
        if created is None:
            return JsonResponse({'error': 'No se pudo crear el tipo de envío.'}, status=500)
        return JsonResponse({'ok': True, 'item': created})
    return JsonResponse({'error': 'Método no permitido.'}, status=405)


def sucursal_zonas_list_api(request):
    """
    GET: Lista zonas (erp_zona) para desplegable en el modal de tipo de envío.
    Respuesta: { "zonas": [ { "id_zona": int, "nombre_zona": str }, ... ] }
    """
    base_empresa, err = _base_empresa_from_request(request)
    if err:
        return err
    from core.services.administranet_sucursales import AdministraNETSucursalesService
    svc = AdministraNETSucursalesService()
    zonas = svc.listar_zonas(base_empresa)
    return JsonResponse({'zonas': zonas})


def sucursal_tipo_envio_update_or_delete_api(request, id_sucursal, id_tipo_envio):
    """
    PUT: Actualiza un tipo de envío. DELETE: Elimina un tipo de envío.
    """
    base_empresa, err = _base_empresa_from_request(request)
    if err:
        return err
    try:
        id_suc_url = int(id_sucursal)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'id_sucursal inválido.'}, status=400)
    if not _session_user_can_access_sucursal(request, id_suc_url):
        return JsonResponse({'error': 'No tiene permiso para operar sobre esta sucursal.'}, status=403)
    try:
        id_te = int(id_tipo_envio)
    except (ValueError, TypeError):
        return JsonResponse({'error': 'id_tipo_envio inválido.'}, status=400)
    from core.services.administranet_sucursales import AdministraNETSucursalesService
    svc = AdministraNETSucursalesService()
    if not svc.tipo_envio_pertenece_a_sucursal(base_empresa, id_te, id_suc_url):
        return JsonResponse({'error': 'Tipo de envío no encontrado.'}, status=404)
    if request.method == 'PUT':
        import json
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Cuerpo JSON inválido.'}, status=400)
        ok = svc.actualizar_tipo_envio_sucursal(base_empresa, id_te, data)
        if not ok:
            return JsonResponse({'error': 'No se pudo actualizar.'}, status=500)
        return JsonResponse({'ok': True})
    if request.method == 'DELETE':
        ok = svc.eliminar_tipo_envio_sucursal(base_empresa, id_te)
        if not ok:
            return JsonResponse({'error': 'No se pudo eliminar.'}, status=500)
        return JsonResponse({'ok': True})
    return JsonResponse({'error': 'Método no permitido.'}, status=405)


def movimiento_stock_alta_api(request):
    """
    POST /core/api/movimiento-stock/
    Alta de movimiento de stock en una transacción.
    Body: { "cabecera": { motivo_movimiento, fecha, deposito_origen, deposito_destino, detalle, id_ref_movstock, id_pv, ... }, "renglones": [ { IDArt, CodigoArticulo, Descripcion, Cantidad, entrada, salida, ES, CodDeposito }, ... ] }
    Respuesta: { "ok": true, "codigo_movimiento": ..., "nro_comprobante": "...", "mensaje": "..." } o { "error": "..." }
    Permisos: stock.crear_movimiento; el servicio revalida permisos de puesto en backend.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)

    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return JsonResponse({'error': 'No autenticado.'}, status=401)

    session_user = request.session.get('user', {})
    base_empresa = session_user.get('base_empresa')
    id_usuario = session_user.get('id_usuario')
    id_puesto = session_user.get('id_puesto')

    if not base_empresa:
        return JsonResponse({'error': 'No se pudo determinar la empresa activa.'}, status=400)
    if not id_usuario:
        return JsonResponse({'error': 'Sesión sin id_usuario.'}, status=400)

    if hasattr(user, 'tiene_permiso') and not user.tiene_permiso('stock.crear_movimiento'):
        if not (hasattr(user, 'is_admin') and user.is_admin()):
            return JsonResponse({'error': 'Sin permiso para crear movimiento de stock.'}, status=403)

    import json
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Cuerpo JSON inválido.'}, status=400)

    cabecera = data.get('cabecera') or {}
    renglones = data.get('renglones') or []
    if not renglones:
        return JsonResponse({'error': 'Debe enviar al menos un renglón en renglones.'}, status=400)

    from core.services.administranet_stock import alta_movimiento
    ok, codigo_mov, nro_comp, mensaje, schema_errores = alta_movimiento(
        base_empresa=base_empresa,
        id_usuario=int(id_usuario),
        id_puesto=int(id_puesto) if id_puesto else None,
        cabecera=cabecera,
        renglones=renglones,
    )
    if not ok:
        payload = {'error': mensaje or 'Error al grabar el movimiento.'}
        if schema_errores is not None:
            payload['schema_error'] = True
            payload['detalle'] = [
                {'tabla': e.get('tabla'), 'campo': e.get('campo'), 'mensaje': e.get('mensaje', '')}
                for e in schema_errores
            ]
        return JsonResponse(payload, status=400)
    return JsonResponse({
        'ok': True,
        'codigo_movimiento': str(codigo_mov),
        'nro_comprobante': nro_comp,
        'mensaje': f'Comprobante MSTOCK-{nro_comp} generado.',
    })


def support_conocimiento_api(request):
    """
    GET /core/api/support/conocimiento/
    Conocimiento funcional para RAG del módulo Support.
    Lee docs/ desde disco (chunking por ## y tamaño), asigna sistema por carpeta
    (docs/administranet_vb6/ → administranet, resto → synap). Incluye ítems intro fijos.
    Autenticación: Bearer JWT firmado con SUPPORT_SYNAP_JWT_SECRET (mismo valor que en Support).
    """
    if request.method != 'GET':
        return JsonResponse({'error': 'Método no permitido.'}, status=405)
    auth_err = _support_rag_auth_error_response(request)
    if auth_err is not None:
        return auth_err
    # Ítems intro fijos (siempre presentes)
    items = [
        {
            'text': (
                'AdministraNET es el ERP de Estrategias de Negocios. '
                'Synap es la evolución web del ERP: reportes, stock, compras, self-checkout, integraciones.'
            ),
            'source_id': 'synap-intro',
            'metadata': {'sistema': 'synap', 'file': 'intro', 'tipo': 'producto'},
        },
        {
            'text': (
                'Módulos principales en Synap: Core (empresas, sucursales, usuarios), '
                'Reportes, Stock, Compras, Self-checkout (TPV/caja). '
                'La configuración de empresas y permisos se gestiona desde el backoffice.'
            ),
            'source_id': 'synap-modulos',
            'metadata': {'sistema': 'synap', 'file': 'intro', 'tipo': 'modulos'},
        },
        {
            'text': (
                'Para soporte técnico de AdministraNET o Synap contactar a Estrategias de Negocios. '
                'El asistente de Support puede usar esta base de conocimiento para sugerir respuestas.'
            ),
            'source_id': 'synap-soporte',
            'metadata': {'sistema': 'synap', 'file': 'intro', 'tipo': 'soporte'},
        },
    ]
    docs_dir = Path(settings.BASE_DIR) / "docs"
    items.extend(build_conocimiento_items_from_docs(docs_dir))
    return JsonResponse({'items': items}) 