# APIs JSON para el formulario de Ingreso Mov. Stock.
# Requieren sesión y permiso stock.crear_movimiento (salvo datos iniciales/consulta).
import json
import logging
from datetime import date
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.decorators import tiene_permiso
from core.services import administranet_stock as svc

logger = logging.getLogger(__name__)


def _session_context(request):
    """Obtiene base_empresa, id_usuario, id_puesto, id_punto_venta desde sesión. Devuelve (ctx, error_response)."""
    session_user = request.session.get("user", {})
    base_empresa = session_user.get("base_empresa")
    id_usuario = session_user.get("id_usuario")
    id_puesto = session_user.get("id_puesto")
    id_punto_venta = session_user.get("id_punto_venta")
    if not base_empresa or not id_usuario:
        return None, JsonResponse({"error": "Sesión inválida o sin empresa."}, status=400)
    return {
        "base_empresa": base_empresa,
        "id_usuario": int(id_usuario),
        "id_puesto": int(id_puesto) if id_puesto else None,
        "id_punto_venta": int(id_punto_venta) if id_punto_venta is not None else None,
    }, None


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["GET"])
def api_ingreso_datos_iniciales(request):
    """GET: depósitos, referencias de movimiento, motivos permitidos, viajantes (Operario)."""
    ctx, err = _session_context(request)
    if err:
        return err
    depositos = svc.get_depositos(ctx["base_empresa"], ctx["id_puesto"])
    ref_movstock = svc.get_ref_movstock(ctx["base_empresa"], ctx["id_puesto"])
    motivos = svc.get_motivos_permitidos(ctx["base_empresa"], ctx["id_puesto"], incluir_pedidos_produccion=True)
    motivos_list = [{"codigo": c, "nombre": n} for c, n in motivos]
    viajantes = svc.get_viajantes(ctx["base_empresa"])
    clientes = svc.get_clientes(ctx["base_empresa"], limit=300)
    activ_proyecto = svc.get_activ_proyecto(ctx["base_empresa"])
    calculo_stock_saldo = svc.get_calculo_stock_saldo(ctx["base_empresa"])
    config_embalaje = svc.get_config_unidad_bulto_display(ctx["base_empresa"])
    config_peso = svc.get_config_peso_balanza(ctx["base_empresa"])
    pedidos_parte_produccion = svc.get_pedidos_parte_produccion(ctx["base_empresa"])
    return JsonResponse({
        "depositos": depositos,
        "ref_movstock": ref_movstock,
        "motivos": motivos_list,
        "viajantes": viajantes,
        "clientes": clientes,
        "activ_proyecto": activ_proyecto,
        "calculo_stock_saldo": calculo_stock_saldo,
        "utiliza_bulto_cerrado": config_embalaje.get("utiliza_bulto_cerrado", "No"),
        "utiliza_display": config_embalaje.get("utiliza_display", "No"),
        "tipo_unidad_defecto": config_embalaje.get("tipo_unidad_defecto", "Unidad"),
        "usa_multiplica_bulto_promedio": config_peso.get("usa_multiplica_bulto_promedio", "No"),
        "tipo_balanza": config_peso.get("tipo_balanza", ""),
        "pedidos_parte_produccion": pedidos_parte_produccion,
    })


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["GET"])
def api_ingreso_articulos(request):
    """GET ?q=: búsqueda de artículos (autocompletado). ?detalle=1: incluye precios, stock. ?solo_ensamblados=1: solo artículos con fórmula (Armado/Desarmado). Si q=* y solo_ensamblados, lista todos los ensamblados. ?id_deposito= opcional."""
    ctx, err = _session_context(request)
    if err:
        return err
    q = request.GET.get("q", "").strip()
    limit = min(int(request.GET.get("limit", 20)), 50)
    detalle = request.GET.get("detalle", "").strip() in ("1", "true", "yes")
    solo_ensamblados = request.GET.get("solo_ensamblados", "").strip() in ("1", "true", "yes")
    id_deposito = None
    if request.GET.get("id_deposito"):
        try:
            id_deposito = int(request.GET.get("id_deposito", 0)) or None
        except (ValueError, TypeError):
            pass
    if solo_ensamblados:
        limit_ens = min(limit, 100)
        try:
            if detalle:
                items = svc.buscar_articulos_ensamblados_para_movimiento(
                    ctx["base_empresa"], q, limit=limit_ens, id_deposito=id_deposito
                )
            else:
                items = svc._buscar_articulos_ensamblados_con_precios(
                    ctx["base_empresa"], q, limit=limit_ens
                )
        except Exception as e:
            logger.warning("Búsqueda ensamblados fallida: %s", e)
            items = []
        return JsonResponse({"articulos": items, "solo_ensamblados": True})
    if detalle:
        limit_detalle = min(limit, 15)
        try:
            items = svc.buscar_articulos_para_movimiento(
                ctx["base_empresa"], q, limit=limit_detalle, id_deposito=id_deposito
            )
        except Exception as e:
            logger.warning("Búsqueda con detalle fallida, usando búsqueda simple: %s", e)
            items = svc.buscar_articulos(ctx["base_empresa"], q, limit=limit)
    else:
        items = svc.buscar_articulos(ctx["base_empresa"], q, limit=limit)
    return JsonResponse({"articulos": items})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["GET"])
def api_ingreso_articulos_por_codigo(request):
    """GET ?codigo=: búsqueda exacta por código de barras / id_manual / IDArt (misma lógica que TPV). Devuelve un único artículo con detalle (stock_depositos, stock_lotes) o articulos: [] si no existe."""
    ctx, err = _session_context(request)
    if err:
        return err
    codigo = request.GET.get("codigo", "").strip()
    if not codigo:
        return JsonResponse({"articulos": []})
    id_deposito = None
    if request.GET.get("id_deposito"):
        try:
            id_deposito = int(request.GET.get("id_deposito", 0)) or None
        except (ValueError, TypeError):
            pass
    item = svc.buscar_articulo_por_codigo_exacto(
        ctx["base_empresa"], codigo, id_deposito=id_deposito
    )
    if not item:
        return JsonResponse({"articulos": []})
    return JsonResponse({"articulos": [item]})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["GET"])
def api_ingreso_lotes_articulo(request):
    """GET ?id_articulo=&id_deposito=: lista de lotes del artículo en el depósito con stock > 0 (id_lote, cod_lote, vto_lote, stock_lote)."""
    ctx, err = _session_context(request)
    if err:
        return err
    try:
        id_articulo = int(request.GET.get("id_articulo", 0))
        id_deposito = int(request.GET.get("id_deposito", 0))
    except (ValueError, TypeError):
        return JsonResponse({"lotes": []})
    if not id_articulo or not id_deposito:
        return JsonResponse({"lotes": []})
    lotes = svc.get_stock_por_lote(
        ctx["base_empresa"], id_articulo, id_deposito=id_deposito
    )
    out = []
    for lt in lotes:
        out.append({
            "id_lote": lt.get("id_lote"),
            "cod_lote": lt.get("cod_lote"),
            "vto_lote": lt.get("vto_lote"),
            "fecha_vto_lote": str(lt.get("fecha_vto_lote")) if lt.get("fecha_vto_lote") else None,
            "stock_lote": str(lt.get("stock_lote")) if lt.get("stock_lote") is not None else "0",
        })
    return JsonResponse({"lotes": out})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["GET"])
def api_ingreso_saldo(request):
    """GET ?id_articulo=&id_deposito=: saldo disponible."""
    ctx, err = _session_context(request)
    if err:
        return err
    try:
        id_articulo = int(request.GET.get("id_articulo", 0))
        id_deposito = int(request.GET.get("id_deposito", 0))
    except (ValueError, TypeError):
        return JsonResponse({"saldo": 0})
    saldo = svc.get_saldo_articulo_deposito(ctx["base_empresa"], id_articulo, id_deposito)
    return JsonResponse({"saldo": str(saldo)})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["GET"])
def api_ingreso_renglones(request):
    """GET: renglones temporales del usuario."""
    ctx, err = _session_context(request)
    if err:
        return err
    renglones = svc.listar_renglones_temporales(ctx["base_empresa"], ctx["id_usuario"])
    return JsonResponse({"renglones": renglones})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["POST"])
def api_ingreso_renglon_add(request):
    """POST: agrega un renglón temporal. Body: IDArt, CodigoArticulo, Descripcion, Cantidad, ES, CodDeposito, cod_deposito_destino (opc)."""
    ctx, err = _session_context(request)
    if err:
        return err
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    es = (data.get("ES") or "E").strip().upper()
    cantidad = float(data.get("Cantidad") or 1)
    datos = {
        "IDArt": data.get("IDArt"),
        "CodigoArticulo": data.get("CodigoArticulo", ""),
        "Descripcion": data.get("Descripcion", ""),
        "Cantidad": cantidad,
        "ES": es,
        "entrada": cantidad if es == "E" else 0,
        "salida": cantidad if es == "S" else 0,
        "CodDeposito": data.get("CodDeposito"),
        "cod_deposito_destino": data.get("cod_deposito_destino"),
        "id_manual": data.get("id_manual"),
        "nro_pedi": data.get("nro_pedi"),
        "codmov_nro_pedi": data.get("codmov_nro_pedi"),
        "id_lote": data.get("id_lote"),
        "cod_lote": data.get("cod_lote"),
        "vto_lote": data.get("vto_lote"),
        "marca": data.get("marca"),
        "multiplicador_vta": data.get("multiplicador_vta"),
        "cantidad_uni": data.get("cantidad_uni"),
        "tipo_unidad": data.get("tipo_unidad"),
        "unidad_art_peso": data.get("unidad_art_peso"),
    }
    if not datos["IDArt"]:
        return JsonResponse({"error": "Artículo obligatorio."}, status=400)
    if not datos["CodDeposito"] and datos["CodDeposito"] != 0:
        return JsonResponse({"error": "Depósito obligatorio."}, status=400)
    resultado = svc.agregar_renglon_temporal(ctx["base_empresa"], ctx["id_usuario"], datos)
    if resultado:
        return JsonResponse({"error": resultado.get("error", "Error al agregar.")}, status=400)
    renglones = svc.listar_renglones_temporales(ctx["base_empresa"], ctx["id_usuario"])
    return JsonResponse({"ok": True, "renglones": renglones})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["POST", "DELETE"])
def api_ingreso_renglon_remove(request, orden):
    """POST/DELETE: quita el renglón con Orden."""
    ctx, err = _session_context(request)
    if err:
        return err
    try:
        orden = int(orden)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Orden inválido."}, status=400)
    resultado = svc.quitar_renglon_temporal(ctx["base_empresa"], ctx["id_usuario"], orden)
    if resultado:
        return JsonResponse({"error": resultado.get("error", "Error al quitar.")}, status=400)
    renglones = svc.listar_renglones_temporales(ctx["base_empresa"], ctx["id_usuario"])
    return JsonResponse({"ok": True, "renglones": renglones})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["PUT", "PATCH"])
def api_ingreso_renglon_update(request, orden):
    """PUT/PATCH: actualiza el renglón con Orden. Body: IDArt, CodigoArticulo, Descripcion, Cantidad, ES, CodDeposito, cod_deposito_destino (opc)."""
    ctx, err = _session_context(request)
    if err:
        return err
    try:
        orden = int(orden)
    except (ValueError, TypeError):
        return JsonResponse({"error": "Orden inválido."}, status=400)
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    es = (data.get("ES") or "E").strip().upper()
    cantidad = float(data.get("Cantidad") or 1)
    datos = {
        "IDArt": data.get("IDArt"),
        "CodigoArticulo": data.get("CodigoArticulo", ""),
        "Descripcion": data.get("Descripcion", ""),
        "Cantidad": cantidad,
        "ES": es,
        "entrada": cantidad if es == "E" else 0,
        "salida": cantidad if es == "S" else 0,
        "CodDeposito": data.get("CodDeposito"),
        "cod_deposito_destino": data.get("cod_deposito_destino"),
        "id_manual": data.get("id_manual"),
        "nro_pedi": data.get("nro_pedi"),
        "codmov_nro_pedi": data.get("codmov_nro_pedi"),
        "marca": data.get("marca"),
        "multiplicador_vta": data.get("multiplicador_vta"),
        "cantidad_uni": data.get("cantidad_uni"),
        "tipo_unidad": data.get("tipo_unidad"),
        "unidad_art_peso": data.get("unidad_art_peso"),
    }
    if not datos["IDArt"]:
        return JsonResponse({"error": "Artículo obligatorio."}, status=400)
    if not datos["CodDeposito"] and datos["CodDeposito"] != 0:
        return JsonResponse({"error": "Depósito obligatorio."}, status=400)
    resultado = svc.actualizar_renglon_temporal(ctx["base_empresa"], ctx["id_usuario"], orden, datos)
    if resultado:
        return JsonResponse({"error": resultado.get("error", "Error al actualizar.")}, status=400)
    renglones = svc.listar_renglones_temporales(ctx["base_empresa"], ctx["id_usuario"])
    return JsonResponse({"ok": True, "renglones": renglones})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["GET"])
def api_ingreso_proyectos(request):
    """GET: lista proyectos (Ninguno + En curso) para el modal Lista_Proyecto."""
    ctx, err = _session_context(request)
    if err:
        return err
    items = svc.listar_proyectos(ctx["base_empresa"])
    out = []
    for it in items:
        row = {}
        for k, v in it.items():
            if hasattr(v, "__float__") and not isinstance(v, (bool, int)):
                try:
                    row[k] = int(v) if float(v) == int(float(v)) else float(v)
                except (ValueError, TypeError):
                    row[k] = str(v) if v is not None else None
            else:
                row[k] = v
        out.append(row)
    return JsonResponse({"proyectos": out})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["GET"])
def api_ingreso_pedidos_pendientes(request):
    """GET ?motivo=6|11|12&deposito_destino= (obligatorio si motivo=6). Lista PEDI o PED pendientes para el modal Busca_PEDI."""
    ctx, err = _session_context(request)
    if err:
        return err
    try:
        motivo = int(request.GET.get("motivo", 0))
    except (ValueError, TypeError):
        return JsonResponse({"error": "Parámetro motivo inválido."}, status=400)
    if motivo not in (6, 11, 12):
        return JsonResponse({"error": "Motivo debe ser 6, 11 o 12."}, status=400)
    deposito_destino = None
    if motivo == 6:
        dep = request.GET.get("deposito_destino", "").strip()
        if not dep:
            return JsonResponse({"error": "Para Transferencia debe indicar depósito destino."}, status=400)
        try:
            deposito_destino = int(dep)
        except (ValueError, TypeError):
            return JsonResponse({"error": "deposito_destino inválido."}, status=400)
    items = svc.listar_pedidos_pendientes(ctx["base_empresa"], motivo, deposito_destino)
    # Normalizar tipos para JSON (Decimal -> int/str)
    out = []
    for it in items:
        row = {}
        for k, v in it.items():
            if hasattr(v, "__float__") and not isinstance(v, (bool, int)):
                try:
                    row[k] = int(v) if float(v) == int(float(v)) else float(v)
                except (ValueError, TypeError):
                    row[k] = str(v) if v is not None else None
            else:
                row[k] = v
        out.append(row)
    return JsonResponse({"pedidos": out})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["GET"])
def api_ingreso_series_renglon(request):
    """GET ?orden=&id_articulo=&es_entrada=0|1: lista números de serie en temp para el renglón."""
    ctx, err = _session_context(request)
    if err:
        return err
    orden = request.GET.get("orden")
    id_articulo = request.GET.get("id_articulo")
    es_entrada = request.GET.get("es_entrada", "1") == "1"
    if not orden or not id_articulo:
        return JsonResponse({"error": "Faltan orden o id_articulo."}, status=400)
    try:
        orden = int(orden)
        id_articulo = int(id_articulo)
    except (ValueError, TypeError):
        return JsonResponse({"error": "orden e id_articulo deben ser numéricos."}, status=400)
    series = svc.listar_series_renglon(
        ctx["base_empresa"],
        ctx["id_usuario"],
        orden,
        id_articulo,
        es_entrada,
    )
    return JsonResponse({"series": series})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["GET"])
def api_ingreso_series_disponibles(request):
    """GET ?id_articulo=&id_deposito=: series disponibles en depósito (para salida)."""
    ctx, err = _session_context(request)
    if err:
        return err
    id_articulo = request.GET.get("id_articulo")
    id_deposito = request.GET.get("id_deposito")
    if not id_articulo or not id_deposito:
        return JsonResponse({"error": "Faltan id_articulo o id_deposito."}, status=400)
    try:
        id_articulo = int(id_articulo)
        id_deposito = int(id_deposito)
    except (ValueError, TypeError):
        return JsonResponse({"error": "id_articulo e id_deposito deben ser numéricos."}, status=400)
    series = svc.listar_series_disponibles_deposito(ctx["base_empresa"], id_articulo, id_deposito)
    return JsonResponse({"series": series})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["POST"])
def api_ingreso_serie_add(request):
    """POST: agrega un número de serie al renglón. Body: orden, id_articulo, id_deposito, es_entrada, nro_serie?, vto_serie? (entrada) o id_serie_entrada (salida)."""
    ctx, err = _session_context(request)
    if err:
        return err
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    orden = data.get("orden")
    id_articulo = data.get("id_articulo")
    id_deposito = data.get("id_deposito")
    es_entrada = data.get("es_entrada") is True or data.get("es_entrada") == "true" or data.get("es_entrada") == 1
    if orden is None or id_articulo is None or id_deposito is None:
        return JsonResponse({"error": "Faltan orden, id_articulo o id_deposito."}, status=400)
    try:
        orden = int(orden)
        id_articulo = int(id_articulo)
        id_deposito = int(id_deposito)
    except (ValueError, TypeError):
        return JsonResponse({"error": "orden, id_articulo e id_deposito deben ser numéricos."}, status=400)
    if es_entrada:
        nro_serie = (data.get("nro_serie") or "").strip()
        if not nro_serie:
            return JsonResponse({"error": "Para entrada debe indicar nro_serie."}, status=400)
        err = svc.agregar_serie_entrada_temp(
            ctx["base_empresa"],
            ctx["id_usuario"],
            orden,
            id_articulo,
            id_deposito,
            nro_serie,
            data.get("vto_serie"),
        )
    else:
        id_serie_entrada = data.get("id_serie_entrada")
        if id_serie_entrada is None:
            return JsonResponse({"error": "Para salida debe indicar id_serie_entrada."}, status=400)
        try:
            id_serie_entrada = int(id_serie_entrada)
        except (ValueError, TypeError):
            return JsonResponse({"error": "id_serie_entrada inválido."}, status=400)
        err = svc.agregar_serie_salida_temp(
            ctx["base_empresa"],
            ctx["id_usuario"],
            orden,
            id_articulo,
            id_deposito,
            id_serie_entrada,
        )
    if err:
        return JsonResponse(err, status=400)
    series = svc.listar_series_renglon(ctx["base_empresa"], ctx["id_usuario"], orden, id_articulo, es_entrada)
    return JsonResponse({"ok": True, "series": series})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["POST"])
def api_ingreso_serie_remove(request):
    """POST: quita un número de serie del renglón. Body: tipo ('entrada'|'salida'), id_temp."""
    ctx, err = _session_context(request)
    if err:
        return err
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    tipo = (data.get("tipo") or "").strip().lower()
    id_temp = data.get("id_temp")
    if tipo not in ("entrada", "salida") or id_temp is None:
        return JsonResponse({"error": "Debe indicar tipo (entrada|salida) e id_temp."}, status=400)
    try:
        id_temp = int(id_temp)
    except (ValueError, TypeError):
        return JsonResponse({"error": "id_temp debe ser numérico."}, status=400)
    if tipo == "entrada":
        err = svc.quitar_serie_entrada_temp(ctx["base_empresa"], ctx["id_usuario"], id_temp)
    else:
        err = svc.quitar_serie_salida_temp(ctx["base_empresa"], ctx["id_usuario"], id_temp)
    if err:
        return JsonResponse(err, status=400)
    return JsonResponse({"ok": True})


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["POST"])
def api_ingreso_confirmar(request):
    """POST: confirma el movimiento. Body: cabecera (motivo_movimiento, fecha, deposito_origen, deposito_destino, detalle, id_ref_movstock, id_pv). Renglones se toman del temporal."""
    ctx, err = _session_context(request)
    if err:
        return err
    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido."}, status=400)
    cabecera = data.get("cabecera") or {}
    fecha = cabecera.get("fecha") or str(date.today())
    cabecera.setdefault("fecha", fecha)
    # Punto de venta: como en AdministraNET, el PV del movimiento es el del usuario logueado (Modificar usuario → Punto de Venta).
    # Si el front no envía id_pv/id_punto_venta, usamos el de la sesión; si no hay, 1.
    if "id_pv" not in cabecera and "id_punto_venta" not in cabecera:
        cabecera["id_pv"] = ctx.get("id_punto_venta") or 1
    renglones = svc.listar_renglones_temporales(ctx["base_empresa"], ctx["id_usuario"])
    # Si el temporal está vacío pero el front envía renglones (p. ej. desincronización por sesión/base), usarlos.
    if not renglones and isinstance(data.get("renglones"), list) and len(data["renglones"]) > 0:
        renglones = data["renglones"]
    if not renglones:
        return JsonResponse({"error": "Debe agregar al menos un ítem a la lista."}, status=400)
    ok, codigo_mov, nro_comp, mensaje = svc.alta_movimiento(
        base_empresa=ctx["base_empresa"],
        id_usuario=ctx["id_usuario"],
        id_puesto=ctx["id_puesto"],
        cabecera=cabecera,
        renglones=renglones,
    )
    if not ok:
        return JsonResponse({"error": mensaje or "Error al grabar el movimiento."}, status=400)
    return JsonResponse({
        "ok": True,
        "codigo_movimiento": int(codigo_mov),
        "nro_comprobante": nro_comp,
        "mensaje": f"Comprobante MSTOCK-{nro_comp} generado.",
    })


@tiene_permiso("stock.crear_movimiento")
@require_http_methods(["POST"])
def api_ingreso_limpiar_temporales(request):
    """POST: limpia renglones temporales y series temp del usuario (Fase 15: Cancelar / salir sin confirmar)."""
    ctx, err = _session_context(request)
    if err:
        return err
    try:
        svc.limpiar_temporales_usuario(ctx["base_empresa"], ctx["id_usuario"])
    except Exception as e:
        logger.warning("Error al limpiar temporales: %s", e)
    return JsonResponse({"ok": True})
