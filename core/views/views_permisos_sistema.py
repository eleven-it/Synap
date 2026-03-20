# core/views/views_permisos_sistema.py

from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_POST
from core.decorators import tiene_permiso, solo_usuario_supervisor
from core.services.administranet_permisos_sistema import AdministraNETPermisosSistemaService
import json
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def _usuario_es_supervisor_cod(request) -> bool:
    user = getattr(request, "user", None)
    if not user or not getattr(user, "is_authenticated", False):
        return False
    return (getattr(user, "cod_usuario", None) or "").strip().lower() == "supervisor"


@tiene_permiso("administrar.usuarios")
def listar_puestos_permisos_view(request):
    """
    Vista principal para listar puestos y gestionar sus permisos del sistema
    Similar a ABMPermiso_Sistema.frm
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:dashboard")
    
    # Inicializar servicio
    permisos_service = AdministraNETPermisosSistemaService()
    
    # Búsqueda
    q = request.GET.get("q", "").strip()
    
    # Obtener puestos desde MySQL de administraNET
    puestos = permisos_service.listar_puestos(
        base_empresa=base_empresa,
        busqueda=q if q else None
    )
    
    # Paginación manual
    paginator = Paginator(puestos, 15)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    
    tab = (request.GET.get("tab") or "puestos").strip().lower()
    if tab not in ("puestos", "navbar"):
        tab = "puestos"
    if tab == "navbar" and not _usuario_es_supervisor_cod(request):
        messages.warning(
            request,
            "La pestaña de menú navbar solo está disponible para el usuario supervisor.",
        )
        tab = "puestos"

    navbar_global = None
    navbar_grupos_vis = []
    q_navbar = ""
    total_filas_navbar = 0
    if _usuario_es_supervisor_cod(request):
        try:
            from core.models import NavbarMenuGlobal

            navbar_global = NavbarMenuGlobal.get_solo()
        except Exception as e:
            logger.warning("No se pudo cargar NavbarMenuGlobal: %s", e)
        if tab == "navbar":
            from core.services.navbar_visibilidad import construir_grupos_visibilidad_navbar_ui

            q_navbar = (request.GET.get("q_navbar") or "").strip()
            q_navbar_lower = q_navbar.lower()
            navbar_grupos_vis = construir_grupos_visibilidad_navbar_ui()
            if q_navbar_lower:
                filtrados = []
                for g in navbar_grupos_vis:
                    nombre_l = (g.get("nombre") or "").lower()
                    aid_l = (g.get("app_id") or "").lower()
                    if q_navbar_lower in nombre_l or q_navbar_lower in aid_l:
                        filtrados.append(g)
                        continue
                    filas_f = [
                        r
                        for r in g.get("filas") or []
                        if q_navbar_lower in (r.get("label") or "").lower()
                        or q_navbar_lower in (r.get("menu_item_id") or "").lower()
                        or q_navbar_lower in (r.get("seccion") or "").lower()
                        or q_navbar_lower in (r.get("url_name") or "").lower()
                    ]
                    if filas_f:
                        g2 = {**g, "filas": filas_f}
                        filtrados.append(g2)
                navbar_grupos_vis = filtrados
            total_filas_navbar = sum(len(g.get("filas") or []) for g in navbar_grupos_vis)

    context = {
        "puestos": page_obj,
        "q": q,
        "base_empresa": base_empresa,
        "tab_activa": tab,
        "es_supervisor_cod": _usuario_es_supervisor_cod(request),
        "navbar_global": navbar_global,
        "navbar_grupos_vis": navbar_grupos_vis,
        "q_navbar": q_navbar,
        "total_filas_navbar": total_filas_navbar,
    }
    return render(request, "core/permisos_sistema_list.html", context)


@require_POST
@solo_usuario_supervisor
@csrf_protect
def toggle_navbar_menu_global_view(request):
    """
    Activa o desactiva la ocultación global del menú de la navbar (todos los usuarios).
    Solo usuario cod_usuario supervisor.
    """
    from core.models import NavbarMenuGlobal

    estado = (request.POST.get("estado_navbar") or "").strip().lower()
    row = NavbarMenuGlobal.get_solo()
    if estado == "oculto":
        row.ocultar_todos_items = True
        row.save()
        messages.success(
            request,
            "Menú navbar oculto para todos los usuarios. Usted sigue viendo «Archivo» para revertir.",
        )
    elif estado == "visible":
        row.ocultar_todos_items = False
        row.save()
        messages.success(request, "Menú navbar visible según permisos habituales.")
    else:
        messages.error(request, "Solicitud inválida.")
    return redirect(f"{reverse('core:permisos_sistema')}?tab=navbar")


@require_POST
@solo_usuario_supervisor
@csrf_protect
def toggle_navbar_granular_view(request):
    """
    Actualiza visibilidad granular (módulo o ítem hoja) del menú navbar. JSON POST.
    """
    from core.services.navbar_visibilidad import (
        establecer_item_visible,
        establecer_modulo_visible,
    )

    ct = (request.content_type or "").split(";")[0].strip().lower()
    if ct != "application/json":
        return JsonResponse(
            {"success": False, "error": "Content-Type debe ser application/json"},
            status=415,
        )
    try:
        data = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"success": False, "error": "JSON inválido"}, status=400)

    tipo = (data.get("tipo") or "").strip().lower()
    app_id = (data.get("app_id") or "").strip()
    visible_raw = data.get("visible")

    if visible_raw is True:
        visible_bool = True
    elif visible_raw is False:
        visible_bool = False
    elif isinstance(visible_raw, str):
        visible_bool = visible_raw.strip().lower() in ("true", "1", "si", "yes")
    else:
        return JsonResponse(
            {"success": False, "error": "Campo visible inválido"},
            status=400,
        )

    if tipo == "modulo":
        ok = establecer_modulo_visible(app_id, visible_bool)
    elif tipo == "item":
        menu_item_id = (data.get("menu_item_id") or "").strip()
        ok = establecer_item_visible(app_id, menu_item_id, visible_bool)
    else:
        return JsonResponse({"success": False, "error": "tipo debe ser modulo o item"}, status=400)

    if not ok:
        return JsonResponse(
            {"success": False, "error": "No se pudo actualizar (app o ítem inválido)"},
            status=400,
        )
    return JsonResponse({"success": True})


@tiene_permiso("administrar.usuarios")
@csrf_protect
def editar_permisos_puesto_view(request, id_puesto):
    """
    Vista para editar los permisos del sistema de un puesto
    Similar a CargaPermiso_Sistema_Puesto.frm
    """
    # Obtener datos de la sesión del usuario actual
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    
    if not base_empresa:
        messages.error(request, "No se pudo determinar la empresa activa.")
        return redirect("core:permisos_sistema")
    
    # Inicializar servicio
    permisos_service = AdministraNETPermisosSistemaService()
    
    # Obtener puesto
    puesto = permisos_service.obtener_puesto(base_empresa, id_puesto)
    if not puesto:
        messages.error(request, "Puesto no encontrado.")
        return redirect("core:permisos_sistema")
    
    # Obtener permisos actuales del puesto
    permisos_actuales = permisos_service.obtener_permisos_puesto(base_empresa, id_puesto)
    
    if request.method == "POST":
        # Recopilar todos los permisos del POST
        permisos_nuevos = {}
        
        # Campos booleanos (Si/No)
        campos_booleanos = [
            'Mod_Precio_Fact', 'cambia_cv', 'actualiza_abm_art', 'mod_lista_de_precio',
            'cambia_deposito', 'cambia_caja', 'cambia_sucursal', 'cambia_talonario',
            'mod_descuento_pie', 'mod_descuento_renglon', 'visualizar_comprobantes',
            'anular_comprobantes', 'reimprimir_comprobantes', 'actualiza_lista_compra',
            'lista_compra_venta_defecto', 'imprime_cheques', 'modifica_pedido_presupuesto',
            'modifica_factura_pedido', 'modifica_remito_pedido', 'acceso_pv',
            'acceso_comp_ventas_talonario', 'modifica_oc_presupuesto', 'modifica_factura_oc',
            'modifica_remito_oc', 'modifica_remitoc_facturac', 'ver_cliente_sucursal',
            'ver_proveedor_sucursal', 'genera_fact_rem', 'factura_importe_cero',
            'calcula_precio_oficial', 'autoriza_documentos', 'cont_prev_asiento',
            'cont_acceso_contabilidad', 'pre_ped_otro_cliente', 'login_supervisor_credito',
            'selec_pv', 'cambia_cv_abmcliente', 'cambia_lp_abmcliente',
            'modifica_comp_talonario', 'visualiza_aviso', 'obliga_cambvendedor',
            'caja_opciones_total', 'obliga_selecpv', 'obliga_selecTipoDevol',
            'popup_mensajeria', 'traslada_detalle', 'desc_int_cv', 'secuencia_tpv_cant',
            'selec_item_total_ped_rem', 'modif_prec_remito_fact', 'remite_factura_art',
            'limita_pendientes_ped_max', 'Habilita_selecpv_consultacomp',
            'selec_ejer_per_cont', 'precio_final_fa', 'selec_DatosAdicionales',
            'utiliza_lista_oficial', 'filtra_art_proveedor', 'mov_stock_utiliza_cbarra',
            'plantillas', 'art_precios_negativos', 'recuerda_ruta_zona',
            'visualiza_clientes_todos_web', 'pedido_web', 'remito_web',
            'ver_informes_gerencia_web', 'oe_ultima_etapa', 'impresion_oe',
            'genera_edita_oe', 'serie_cod_barra', 'fiscal_cambio',
            'fiscal_codigo_linea_comp', 'abmcli_mod_desc', 'abmcli_mod_vendedor',
            'bloquea_oc', 'oe_deposito_origenxarticulo', 'ajuste_cta_cte',
            'informes_vendedor', 'nc_ruta_cerrada', 'mod_fecha_venta',
            'mod_item_pre_ped'
        ]
        
        for campo in campos_booleanos:
            valor = request.POST.get(campo, 'No')
            permisos_nuevos[campo] = 'Si' if valor == 'on' or valor == 'Si' else 'No'
        
        # Campos de texto/opciones
        campos_texto = [
            'carga_comp_venta', 'carga_comp_cobranza', 'carga_comp_ped',
            'acceso_ref_movstock', 'acceso_motivo_movstock', 'medio_cobro_pend',
            'reporte_pedido'
        ]
        
        for campo in campos_texto:
            if campo in request.POST:
                permisos_nuevos[campo] = request.POST.get(campo, '')
        
        # Campos numéricos
        campos_numericos = [
            'id_refmovstock', 'lim_desc_renglon', 'lim_desc_pie'
        ]
        
        for campo in campos_numericos:
            if campo in request.POST:
                valor = request.POST.get(campo, '0')
                try:
                    permisos_nuevos[campo] = int(valor) if valor else 0
                except ValueError:
                    permisos_nuevos[campo] = 0
        
        # Guardar permisos
        if permisos_service.guardar_permisos_puesto(base_empresa, id_puesto, permisos_nuevos):
            messages.success(request, f"✅ Permisos del puesto '{puesto['nombre']}' guardados correctamente.")
            return redirect("core:permisos_sistema")
        else:
            messages.error(request, "Error al guardar los permisos.")
    
    # GET - mostrar formulario
    # Agrupar permisos por categoría para mejor organización en el template
    permisos_por_categoria = {
        'Ventas': {
            'Mod_Precio_Fact': 'Modificar precios en factura',
            'mod_lista_de_precio': 'Cambiar lista de precio',
            'mod_descuento_pie': 'Modificar descuento pie',
            'mod_descuento_renglon': 'Modificar descuento renglón',
            'acceso_pv': 'Acceso a puntos de venta',
            'acceso_comp_ventas_talonario': 'Acceso comprobantes por talonario',
            'carga_comp_venta': 'Cargar comprobantes de venta',
            'selec_pv': 'Seleccionar punto de venta',
            'cambia_cv_abmcliente': 'Cambiar CV en ABM cliente',
            'cambia_lp_abmcliente': 'Cambiar LP en ABM cliente',
            'modifica_comp_talonario': 'Modificar comprobante talonario',
            'visualizar_comprobantes': 'Visualizar comprobantes',
            'anular_comprobantes': 'Anular comprobantes',
            'reimprimir_comprobantes': 'Reimprimir comprobantes',
            'factura_importe_cero': 'Facturar importe cero',
            'mod_fecha_venta': 'Modificar fecha de venta',
            'reporte_pedido': 'Reporte de pedido',
        },
        'Compras': {
            'modifica_oc_presupuesto': 'Modificar OC presupuesto',
            'modifica_factura_oc': 'Modificar factura OC',
            'modifica_remito_oc': 'Modificar remito OC',
            'modifica_remitoc_facturac': 'Modificar remito compra facturación',
            'actualiza_lista_compra': 'Actualizar lista de compra',
            'lista_compra_venta_defecto': 'Lista compra/venta por defecto',
            'bloquea_oc': 'Bloquear orden de compra',
        },
        'Stock': {
            'cambia_deposito': 'Cambiar depósito',
            'acceso_ref_movstock': 'Acceso referencia mov. stock',
            'acceso_motivo_movstock': 'Acceso motivo mov. stock',
            'id_refmovstock': 'ID referencia mov. stock',
            'mov_stock_utiliza_cbarra': 'Mov. stock usa código de barras',
        },
        'Articulos': {
            'actualiza_abm_art': 'Actualizar ABM artículos',
            'filtra_art_proveedor': 'Filtrar artículos por proveedor',
            'art_precios_negativos': 'Artículos con precios negativos',
        },
        'Clientes/Proveedores': {
            'ver_cliente_sucursal': 'Ver clientes de sucursal',
            'ver_proveedor_sucursal': 'Ver proveedores de sucursal',
            'actualiza_abm_cliente': 'Actualizar ABM cliente',
            'actualiza_abm_proveedor': 'Actualizar ABM proveedor',
            'modifica_vendedor': 'Modificar vendedor',
        },
        'Caja': {
            'cambia_caja': 'Cambiar caja',
            'caja_opciones_total': 'Caja opciones total',
            'imprime_cheques': 'Imprimir cheques',
            'carga_comp_cobranza': 'Cargar comprobantes de cobranza',
        },
        'Sucursales': {
            'cambia_sucursal': 'Cambiar sucursal',
            'cambia_talonario': 'Cambiar talonario',
        },
        'Pedidos': {
            'modifica_pedido_presupuesto': 'Modificar pedido presupuesto',
            'modifica_factura_pedido': 'Modificar factura pedido',
            'modifica_remito_pedido': 'Modificar remito pedido',
            'carga_comp_ped': 'Cargar comprobantes de pedido',
            'pre_ped_otro_cliente': 'Presupuesto/pedido otro cliente',
            'limita_pendientes_ped_max': 'Limitar pendientes pedido máximo',
            'mod_item_pre_ped': 'Modificar item presupuesto/pedido',
        },
        'Contabilidad': {
            'cont_prev_asiento': 'Previsualizar asiento',
            'cont_acceso_contabilidad': 'Acceso a contabilidad',
            'selec_ejer_per_cont': 'Seleccionar ejercicio/período contable',
        },
        'Otros': {
            'cambia_cv': 'Cambiar CV/CC',
            'calcula_precio_oficial': 'Calcular precio oficial',
            'autoriza_documentos': 'Autorizar documentos',
            'medio_cobro_pend': 'Medio de cobro pendiente',
            'login_supervisor_credito': 'Login supervisor crédito',
            'visualiza_aviso': 'Visualizar avisos',
            'obliga_cambvendedor': 'Obligar cambiar vendedor',
            'obliga_selecpv': 'Obligar seleccionar PV',
            'obliga_selecTipoDevol': 'Obligar seleccionar tipo devolución',
            'popup_mensajeria': 'Popup mensajería',
            'traslada_detalle': 'Trasladar detalle',
            'desc_int_cv': 'Descuento interno CV',
            'secuencia_tpv_cant': 'Secuencia TPV cantidad',
            'selec_item_total_ped_rem': 'Seleccionar item total pedido/remito',
            'modif_prec_remito_fact': 'Modificar precio remito factura',
            'remite_factura_art': 'Remitir factura artículo',
            'Habilita_selecpv_consultacomp': 'Habilitar seleccionar PV consulta comprobantes',
            'precio_final_fa': 'Precio final factura',
            'selec_DatosAdicionales': 'Seleccionar datos adicionales',
            'utiliza_lista_oficial': 'Utilizar lista oficial',
            'lim_desc_renglon': 'Límite descuento renglón (%)',
            'lim_desc_pie': 'Límite descuento pie (%)',
            'plantillas': 'Plantillas',
            'recuerda_ruta_zona': 'Recordar ruta/zona',
            'visualiza_clientes_todos_web': 'Visualizar clientes todos web',
            'pedido_web': 'Pedido web',
            'remito_web': 'Remito web',
            'ver_informes_gerencia_web': 'Ver informes gerencia web',
            'oe_ultima_etapa': 'OE última etapa',
            'impresion_oe': 'Impresión OE',
            'genera_edita_oe': 'Generar/editar OE',
            'serie_cod_barra': 'Serie código de barras',
            'fiscal_cambio': 'Fiscal cambio',
            'fiscal_codigo_linea_comp': 'Fiscal código línea comprobante',
            'abmcli_mod_desc': 'ABM cliente modificar descuento',
            'abmcli_mod_vendedor': 'ABM cliente modificar vendedor',
            'oe_deposito_origenxarticulo': 'OE depósito origen por artículo',
            'ajuste_cta_cte': 'Ajuste cuenta corriente',
            'informes_vendedor': 'Informes vendedor',
            'nc_ruta_cerrada': 'NC ruta cerrada',
            'genera_fact_rem': 'Generar factura remito',
        }
    }
    
    # Asegurar que permisos siempre tenga valores por defecto si no existe registro
    if not permisos_actuales:
        permisos_actuales = permisos_service._get_permisos_por_defecto()
    
    context = {
        'puesto': puesto,
        'permisos': permisos_actuales,
        'permisos_por_categoria': permisos_por_categoria,
        'base_empresa': base_empresa,
    }
    return render(request, "core/permisos_sistema_form.html", context)

