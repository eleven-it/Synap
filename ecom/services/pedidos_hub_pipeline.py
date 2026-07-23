"""
Pipeline del hub Pedidos Lista|Kanban: unifica borradores Postgres + PED MySQL.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import Count
from django.urls import reverse
from django.utils import timezone

from core.mysql_pool import mysql_cursor
from core.utils.administranet_types import to_int_or_none
from ecom.models import EcomCart, EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.services.alcance_comercial import alcance_viajantes_comercial
from ecom.services.pedido_masivo_matriz import listar_sucursales_cliente, obtener_o_crear_draft
from ecom.services.pedido_plantilla_service import _salida_a_packs_matriz
from ecom.services.pedido_cabecera_relay import puede_anular_pedido_relay
from ecom.services.aprobacion_pedidos import puede_aprobar_lote, puede_aprobar_pedido
from ecom.services.ecom_config_mysql import (
    aprobacion_pedidos_activa,
)
from ecom.services.pedido_permisos import puede_ver_todos_pedidos

logger = logging.getLogger(__name__)

COLUMNAS_SIN_APROBACION = (
    "borrador",
    "enviado",
    "en_curso",
    "cerrado",
    "anulado",
)

COLUMNAS_CON_APROBACION = (
    "borrador",
    "enviado",
    "por_autorizar",
    "aprobado",
    "en_curso",
    "cerrado",
    "anulado",
)

# Compat: callers/tests que esperan el conjunto completo de ids.
COLUMNAS = COLUMNAS_CON_APROBACION

_LABELS = {
    "borrador": "Borrador",
    "enviado": "Pendiente",
    "por_autorizar": "Por autorizar",
    "aprobado": "Aprobado",
    "en_curso": "En preparación",
    "cerrado": "Entregado / Cerrado",
    "anulado": "Anulado",
}

_ESTADOS_CERRADOS = frozenset(
    {
        "cerrado",
        "facturado",
        "entregado",
    }
)

_ESTADOS_EN_CURSO = frozenset(
    {
        "en preparación",
        "en preparacion",
        "preparado",
        "en remito",
        "parcial",
    }
)


def columnas_hub_visibles(*, aprobacion_activa: bool) -> tuple:
    """Columnas Kanban/Lista: sin Por autorizar/Aprobado si la aprobación comercial está off."""
    if aprobacion_activa:
        return COLUMNAS_CON_APROBACION
    return COLUMNAS_SIN_APROBACION


def _tarjeta(
    *,
    tipo: str,
    columna: str,
    titulo: str,
    subtitulo: str = "",
    fecha: str = "",
    url: str = "",
    id_ref: str = "",
    badge_error: bool = False,
    sucursal: str = "",
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "tipo": tipo,
        "columna": columna,
        "titulo": titulo,
        "subtitulo": subtitulo,
        "fecha": fecha,
        "url": url,
        "id_ref": id_ref,
        "badge_error": badge_error,
        "sucursal": sucursal,
        "meta": meta or {},
    }


def _nombres_clientes(base_empresa: str, ids: List[int]) -> Dict[int, str]:
    """Resuelve nombres de cliente en un solo query batch."""
    unicos = sorted({i for i in ids if to_int_or_none(i) is not None})
    if not base_empresa or not unicos:
        return {}
    placeholders = ",".join(["%s"] * len(unicos))
    sql = f"""
        SELECT Codigo, COALESCE(nombre_cliente, '') AS nombre_cliente
        FROM cliente
        WHERE Codigo IN ({placeholders})
    """
    out: Dict[int, str] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, unicos)
            for row in cursor.fetchall() or []:
                cod = to_int_or_none(row.get("Codigo"))
                if cod is not None:
                    out[cod] = (row.get("nombre_cliente") or "").strip()
    except Exception as e:
        logger.warning("_nombres_clientes: %s", e)
    return out


def _etiqueta_cliente(nombre: str, id_cliente: Optional[int]) -> str:
    nombre = (nombre or "").strip()
    if nombre:
        return nombre
    idc = to_int_or_none(id_cliente)
    return f"Cliente {idc}" if idc is not None else "Cliente —"


def es_ped_migracion_best(
    nro_comprobante: Optional[str] = None,
    tipo_pedido: Optional[str] = None,
    detalle: Optional[str] = None,
) -> bool:
    """True si el PED proviene de migración BEST (solo consulta desde el hub)."""
    nro = str(nro_comprobante or "").strip().upper()
    tipo = str(tipo_pedido or "").strip().lower()
    det = str(detalle or "").strip().lower()
    if nro.startswith("BEST-") or tipo == "migracion best":
        return True
    if "cutover best" in det or "best orden" in det:
        return True
    return False


def url_pedido_masivo_modo_simple(
    *,
    cod_mov: Optional[int] = None,
    draft: Optional[int] = None,
    consulta: bool = False,
) -> str:
    """URL canónica de captura pedido simple (matriz 1 columna)."""
    base = reverse("ecom:mayoristapp_pedido_masivo_sucursales")
    params: List[str] = ["modo=simple"]
    if draft is not None:
        params.append(f"draft={int(draft)}")
    if cod_mov is not None:
        params.append(f"cod_mov={int(cod_mov)}")
    if consulta:
        params.append("consulta=1")
    return f"{base}?{'&'.join(params)}"


def url_resumen_lote_masivo(draft_id: int) -> str:
    """URL canónica del resumen de lote masivo confirmado (pantalla dedicada)."""
    return reverse("ecom:mayoristapp_lote_resumen", kwargs={"draft_id": int(draft_id)})


def url_pedido_masivo_readonly(draft_id: int) -> str:
    """Abre la matriz masiva en solo lectura (mismo patrón que consultar un PED)."""
    base = reverse("ecom:mayoristapp_pedido_masivo_sucursales")
    return f"{base}?draft={int(draft_id)}&readonly=1"

def _etiqueta_sucursal(calle: str, nro: str, id_dom: Optional[int]) -> str:
    """Misma convención que ``listar_sucursales_cliente`` en pedido_masivo_matriz."""
    calle = (calle or "").strip()
    nro = (nro or "").strip()
    nombre_parts = [p for p in (calle, nro) if p and p != "-"]
    nombre = " ".join(nombre_parts).strip()
    if nombre:
        return nombre
    idd = to_int_or_none(id_dom)
    return f"Sucursal #{idd}" if idd is not None else ""


def _borradores_carrito_legacy(
    base_empresa: str,
    id_usuario: int,
) -> List[Dict[str, Any]]:
    """Tarjetas legacy `EcomCart` con CTA migrar/archivar (no borrador masivo estándar)."""
    qs = (
        EcomCart.objects.filter(
            base_empresa=base_empresa,
            id_usuario=id_usuario,
            estado=EcomCart.ESTADO_BORRADOR,
            tipo_comprobante=EcomCart.TIPO_PEDIDO,
        )
        .annotate(n_items=Count("items"))
        .filter(n_items__gt=0)
        .order_by("-updated_at")[:20]
    )
    ids_cliente = [c.idcliente for c in qs if c.idcliente]
    nombres = _nombres_clientes(base_empresa, ids_cliente)
    out = []
    for c in qs:
        fecha = c.updated_at.strftime("%d/%m/%Y") if c.updated_at else ""
        idc = to_int_or_none(c.idcliente)
        nombre = _etiqueta_cliente(nombres.get(idc, "") if idc is not None else "", idc)
        out.append(
            _tarjeta(
                tipo="carrito_legacy",
                columna="borrador",
                titulo=f"Carrito legacy · {nombre}",
                subtitulo=f"{c.n_items} ítems · migrar a borrador masivo",
                fecha=fecha,
                url="",
                id_ref=f"cart-legacy-{c.pk}",
                meta={
                    "cart_id": c.pk,
                    "id_cliente": c.idcliente,
                    "nombre_cliente": nombres.get(idc, "") if idc is not None else "",
                    "legacy_carrito": True,
                },
            )
        )
    return out


def _archivar_draft_origen_no_editable(
    draft: EcomPedidoMasivoDraft,
    base_empresa: str,
) -> bool:
    """
    Si el borrador es edición de un PED que ya no está Pendiente (p. ej. En Remito),
    archívalo: no debe aparecer en la columna Borrador del hub.
    Devuelve True si quedó archivado (o ya no es un borrador activo editable).
    """
    cod_origen = to_int_or_none(getattr(draft, "cod_mov_origen", None))
    if cod_origen is None:
        return False
    puede, _msg = puede_anular_pedido_relay(base_empresa, cod_origen)
    if puede:
        return False
    if draft.estado not in (
        EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
    ):
        return True
    draft.estado = EcomPedidoMasivoDraft.ESTADO_ARCHIVADO
    draft.save(update_fields=["estado", "updated_at"])
    return True


def _borradores_masivo(
    base_empresa: str,
    id_usuario: int,
) -> List[Dict[str, Any]]:
    qs = EcomPedidoMasivoDraft.objects.filter(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        estado__in=(
            EcomPedidoMasivoDraft.ESTADO_BORRADOR,
            EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
        ),
    ).order_by("-updated_at")[:50]
    ids_cliente = [d.id_cliente for d in qs if d.id_cliente]
    nombres = _nombres_clientes(base_empresa, ids_cliente)
    out = []
    for d in qs:
        # Edición de PED ya avanzado (En preparación / Remito / …): no es borrador activo.
        if _archivar_draft_origen_no_editable(d, base_empresa):
            continue
        fecha = d.updated_at.strftime("%d/%m/%Y") if d.updated_at else ""
        err = bool(d.ultimo_error)
        idc = to_int_or_none(d.id_cliente)
        nombre = _etiqueta_cliente(nombres.get(idc, "") if idc is not None else "", idc)
        es_simple = (d.modo or "").strip().lower() == EcomPedidoMasivoDraft.MODO_SIMPLE
        if es_simple:
            url = url_pedido_masivo_modo_simple(draft=d.pk)
            titulo = f"Pedido simple · {nombre}"
            subtitulo = "Error al confirmar" if err else "Borrador pedido simple"
        else:
            url = reverse("ecom:mayoristapp_pedido_masivo_sucursales") + f"?draft={d.pk}"
            titulo = f"Masivo · {nombre}"
            subtitulo = "Error al confirmar" if err else "Matriz por sucursales"
        out.append(
            _tarjeta(
                tipo="masivo",
                columna="borrador",
                titulo=titulo,
                subtitulo=subtitulo,
                fecha=fecha,
                url=url,
                id_ref=f"masivo-{d.pk}",
                badge_error=err,
                meta={
                    "draft_id": d.pk,
                    "id_cliente": d.id_cliente,
                    "nombre_cliente": nombres.get(idc, "") if idc is not None else "",
                    "modo": d.modo,
                },
            )
        )
    return out


def _masivos_anulados(
    base_empresa: str,
    id_usuario: int,
) -> List[Dict[str, Any]]:
    qs = EcomPedidoMasivoDraft.objects.filter(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        estado=EcomPedidoMasivoDraft.ESTADO_ANULADO,
    ).order_by("-updated_at")[:50]
    ids_cliente = [d.id_cliente for d in qs if d.id_cliente]
    nombres = _nombres_clientes(base_empresa, ids_cliente)
    out = []
    for d in qs:
        fecha = d.updated_at.strftime("%d/%m/%Y") if d.updated_at else ""
        idc = to_int_or_none(d.id_cliente)
        nombre = _etiqueta_cliente(nombres.get(idc, "") if idc is not None else "", idc)
        es_simple = (d.modo or "").strip().lower() == EcomPedidoMasivoDraft.MODO_SIMPLE
        if es_simple:
            url = url_pedido_masivo_modo_simple(draft=d.pk)
            titulo = f"Pedido simple · {nombre}"
        else:
            url = reverse("ecom:mayoristapp_pedido_masivo_sucursales") + f"?draft={d.pk}"
            titulo = f"Masivo · {nombre}"
        out.append(
            _tarjeta(
                tipo="masivo",
                columna="anulado",
                titulo=titulo,
                subtitulo="Borrador anulado · Recuperable",
                fecha=fecha,
                url=url,
                id_ref=f"masivo-anulado-{d.pk}",
                meta={
                    "draft_id": d.pk,
                    "id_cliente": d.id_cliente,
                    "nombre_cliente": nombres.get(idc, "") if idc is not None else "",
                    "modo": d.modo,
                    "puede_eliminar_definitivo": True,
                },
            )
        )
    return out


def _columna_ped_mysql(
    anulado: str,
    autorizacion: str,
    estado: str,
    *,
    estado_aprobacion_comercial: str = "-",
    aprobacion_activa: bool = False,
) -> str:
    if (anulado or "").strip().lower() in ("si", "sí"):
        return "anulado"
    est = (estado or "").strip().lower()
    if est in _ESTADOS_CERRADOS:
        return "cerrado"

    est_com = (estado_aprobacion_comercial or "-").strip().lower()
    if aprobacion_activa:
        if est_com == "pendiente":
            return "por_autorizar"
        if est_com == "rechazado":
            return "enviado"
        auth = (autorizacion or "").strip()
        if auth == "No Autorizado":
            return "por_autorizar"
        if est in ("pendiente",):
            return "enviado"
        if est in _ESTADOS_EN_CURSO:
            return "en_curso"
        return "aprobado"

    # Sin aprobación comercial: no usar columnas Por autorizar / Aprobado.
    if est in ("pendiente",):
        return "enviado"
    if est in _ESTADOS_EN_CURSO:
        return "en_curso"
    return "enviado"


def _draft_en_alcance_hub(
    draft: EcomPedidoMasivoDraft,
    sess_user: Dict[str, Any],
    base_empresa: str,
) -> bool:
    """Draft confirmado visible en el hub según usuario y alcance comercial."""
    id_u = to_int_or_none(sess_user.get("id_usuario"))
    if id_u is not None and draft.id_usuario == id_u:
        return True
    tipousuario = (sess_user.get("tipousuario") or "").strip().lower()
    if tipousuario == "cliente":
        idc = to_int_or_none(sess_user.get("idcliente") or sess_user.get("Codigo"))
        return idc is not None and draft.id_cliente == idc
    # Puestos gerenciales / permiso ver_todos: sin filtro de viajante.
    if puede_ver_todos_pedidos(sess_user):
        return True
    alcance = alcance_viajantes_comercial(base_empresa, sess_user)
    if not alcance:
        return False
    cv = to_int_or_none(draft.cod_viajante)
    return cv is not None and cv in alcance


def _drafts_lote_confirmados_alcance(
    base_empresa: str,
    id_usuario: int,
    sess_user: Dict[str, Any],
    *,
    dias: Optional[int] = None,
) -> List[EcomPedidoMasivoDraft]:
    """
    Drafts masivos confirmados en alcance del usuario.

    Si ``dias`` es ``None`` o ``<= 0``: sin filtro de fecha (hasta 200 recientes).
    Si ``dias > 0``: solo drafts con ``updated_at`` en esa ventana (hasta 50).
    """
    filtros: Dict[str, Any] = {
        "base_empresa": base_empresa,
        "estado": EcomPedidoMasivoDraft.ESTADO_CONFIRMADO,
    }
    limite = 200
    if dias is not None and int(dias) > 0:
        cutoff = timezone.now() - timedelta(days=max(1, min(int(dias), 365)))
        filtros["updated_at__gte"] = cutoff
        limite = 50
    qs = (
        EcomPedidoMasivoDraft.objects.filter(**filtros)
        .order_by("-updated_at")[:limite]
    )
    out: List[EcomPedidoMasivoDraft] = []
    for draft in qs:
        if not draft.codigos_movimiento:
            continue
        if not _draft_en_alcance_hub(draft, sess_user, base_empresa):
            continue
        out.append(draft)
    return out


def _fetch_estados_pedidos_lote(
    base_empresa: str,
    codigos: List[int],
) -> Dict[int, Dict[str, Any]]:
    """Estados operativos/comerciales batch para rollup de lotes."""
    unicos = sorted({to_int_or_none(c) for c in codigos if to_int_or_none(c) is not None})
    if not base_empresa or not unicos:
        return {}
    placeholders = ",".join(["%s"] * len(unicos))
    sql = f"""
        SELECT
            cp.CodigoMovimiento,
            cp.Anulado,
            cp.Estado,
            TRIM(COALESCE(cp.autorizacion_sistema, '')) AS autorizacion,
            TRIM(COALESCE(cp.estado_aprobacion_comercial, '-')) AS estado_aprobacion_comercial
        FROM comp_ped cp
        WHERE cp.TipoComprobante = 'PED'
          AND cp.CodigoMovimiento IN ({placeholders})
    """
    out: Dict[int, Dict[str, Any]] = {}
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, unicos)
            for row in cursor.fetchall() or []:
                cod = to_int_or_none(row.get("CodigoMovimiento"))
                if cod is not None:
                    out[cod] = row
    except Exception as e:
        logger.warning("_fetch_estados_pedidos_lote: %s", e)
    return out


def _rollup_lote_desde_pedidos(
    codigos: List[int],
    estados: Dict[int, Dict[str, Any]],
    *,
    aprobacion_on: bool,
) -> Tuple[Dict[str, int], int]:
    """Rollup por columna hub y contador k de PED activos (no anulados)."""
    rollup = {
        "por_autorizar": 0,
        "aprobado": 0,
        "en_curso": 0,
        "anulado": 0,
        "enviado": 0,
        "cerrado": 0,
    }
    activos = 0
    for cod in codigos:
        row = estados.get(cod)
        if not row:
            continue
        col = _columna_ped_mysql(
            str(row.get("Anulado") or ""),
            str(row.get("autorizacion") or ""),
            str(row.get("Estado") or ""),
            estado_aprobacion_comercial=str(row.get("estado_aprobacion_comercial") or "-"),
            aprobacion_activa=aprobacion_on,
        )
        if col == "anulado":
            rollup["anulado"] += 1
            continue
        activos += 1
        if col == "por_autorizar":
            rollup["por_autorizar"] += 1
        elif col == "aprobado":
            rollup["aprobado"] += 1
        elif col == "en_curso":
            rollup["en_curso"] += 1
        elif col == "cerrado":
            rollup["cerrado"] += 1
        elif col == "enviado":
            rollup["enviado"] += 1
    return rollup, activos


def _columna_lote_desde_contexto(
    ctx: Dict[str, Any],
    *,
    aprobacion_on: bool,
    ids_visibles: tuple,
) -> str:
    """Determina la columna Kanban para una tarjeta ``tipo=lote_masivo``."""

    def _fallback(col: str) -> str:
        if col in ids_visibles:
            return col
        if col in ("por_autorizar", "aprobado") and "enviado" in ids_visibles:
            return "enviado"
        return "enviado" if "enviado" in ids_visibles else ids_visibles[0]

    estado_lote = str(
        ctx.get("estado_aprobacion_lote")
        or EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_NEUTRO
    ).strip().lower()
    rollup = ctx.get("rollup") or {}
    n_total = int(ctx.get("n_total") or 0)
    k_activos = int(ctx.get("k_activos") or 0)

    if (
        aprobacion_on
        and estado_lote == EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_PENDIENTE
    ):
        return _fallback("por_autorizar")

    if n_total > 0 and k_activos == 0:
        return _fallback("anulado")

    if int(rollup.get("en_curso") or 0) > 0:
        return _fallback("en_curso")

    if int(rollup.get("cerrado") or 0) == k_activos and k_activos > 0:
        return _fallback("cerrado")

    if aprobacion_on and int(rollup.get("por_autorizar") or 0) > 0:
        return _fallback("por_autorizar")

    if int(rollup.get("aprobado") or 0) > 0:
        if "aprobado" in ids_visibles:
            return "aprobado"
        return _fallback("enviado")

    return _fallback("enviado")


def _n_articulos_por_draft(drafts: List[EcomPedidoMasivoDraft]) -> Dict[int, int]:
    ids = [d.pk for d in drafts if d.pk]
    if not ids:
        return {}
    rows = (
        EcomPedidoMasivoDraftCelda.objects.filter(
            draft_id__in=ids,
            cantidad_packs__gt=0,
        )
        .values("draft_id")
        .annotate(n=Count("id_articulo", distinct=True))
    )
    return {int(r["draft_id"]): int(r["n"]) for r in rows}


def _mapa_reverso_lotes(
    base_empresa: str,
    id_usuario: int,
    sess_user: Dict[str, Any],
    *,
    dias: Optional[int] = None,
    aprobacion_on: bool = False,
    drafts: Optional[List[EcomPedidoMasivoDraft]] = None,
) -> Tuple[Dict[int, int], Dict[int, Dict[str, Any]]]:
    """
    Mapa ``cod_mov → draft_id`` y contexto por draft para enriquecer PED hijos.

    Usa la misma ventana temporal que ``_drafts_lote_confirmados_alcance`` (``dias``).
    """
    if drafts is None:
        drafts = _drafts_lote_confirmados_alcance(
            base_empresa,
            id_usuario,
            sess_user,
            dias=dias,
        )
    if not drafts:
        return {}, {}

    todos_codigos: List[int] = []
    for draft in drafts:
        for cod in draft.codigos_movimiento or []:
            c = to_int_or_none(cod)
            if c is not None:
                todos_codigos.append(c)
    estados = _fetch_estados_pedidos_lote(base_empresa, todos_codigos)

    mapa: Dict[int, int] = {}
    contexto: Dict[int, Dict[str, Any]] = {}
    for draft in drafts:
        cods = [to_int_or_none(c) for c in (draft.codigos_movimiento or [])]
        cods = [c for c in cods if c is not None]
        rollup, activos = _rollup_lote_desde_pedidos(
            cods,
            estados,
            aprobacion_on=aprobacion_on,
        )
        indice_por_cod = {cod: idx + 1 for idx, cod in enumerate(cods)}
        for cod in cods:
            mapa[cod] = draft.pk
        contexto[draft.pk] = {
            "draft_id": draft.pk,
            "id_cliente": draft.id_cliente,
            "codigos_movimiento": cods,
            "rollup": rollup,
            "k_activos": activos,
            "n_total": len(cods),
            "indice_por_cod": indice_por_cod,
            "estado_aprobacion_lote": draft.estado_aprobacion_lote
            or EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_NEUTRO,
        }
    return mapa, contexto


def _lotes_masivos_confirmados(
    base_empresa: str,
    sess_user: Dict[str, Any],
    *,
    drafts: List[EcomPedidoMasivoDraft],
    contexto_lotes: Dict[int, Dict[str, Any]],
    nombres: Dict[int, str],
    n_articulos_por_draft: Dict[int, int],
    aprobacion_on: bool,
    ids_visibles: tuple,
) -> List[Dict[str, Any]]:
    """Tarjetas padre ``tipo=lote_masivo`` en la columna Kanban operativa correspondiente."""
    out: List[Dict[str, Any]] = []
    for draft in drafts:
        ctx = contexto_lotes.get(draft.pk) or {}
        idc = to_int_or_none(draft.id_cliente)
        nombre = _etiqueta_cliente(nombres.get(idc, "") if idc is not None else "", idc)
        n_suc = int(ctx.get("n_total") or len(draft.codigos_movimiento or []))
        n_art = int(n_articulos_por_draft.get(draft.pk, 0))
        k_activos = int(ctx.get("k_activos") or 0)
        fecha = draft.updated_at.strftime("%d/%m/%Y") if draft.updated_at else ""
        estado_lote = str(
            ctx.get("estado_aprobacion_lote")
            or EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_NEUTRO
        )
        columna = _columna_lote_desde_contexto(
            ctx,
            aprobacion_on=aprobacion_on,
            ids_visibles=ids_visibles,
        )
        out.append(
            _tarjeta(
                tipo="lote_masivo",
                columna=columna,
                titulo=f"Carga masiva · {nombre}",
                subtitulo=f"{n_suc} sucursales · {n_art} artículos · {k_activos}/{n_suc} activos",
                fecha=fecha,
                url=url_pedido_masivo_readonly(draft.pk),
                id_ref=f"lote-{draft.pk}",
                meta={
                    "draft_id": draft.pk,
                    "id_cliente": draft.id_cliente,
                    "nombre_cliente": nombres.get(idc, "") if idc is not None else "",
                    "n_sucursales": n_suc,
                    "codigos_movimiento": ctx.get("codigos_movimiento") or [],
                    "rollup": ctx.get("rollup") or {},
                    "estado_aprobacion_lote": estado_lote,
                    "puede_aprobar_lote": (
                        aprobacion_on
                        and puede_aprobar_lote(base_empresa, sess_user, draft)
                    ),
                },
            )
        )
    return out


def _pedidos_mysql(
    base_empresa: str,
    sess_user: Dict[str, Any],
    *,
    dias: Optional[int] = None,
    limit: int = 5000,
    aprobacion_on: Optional[bool] = None,
    mapa_lotes: Optional[Dict[int, int]] = None,
    contexto_lotes: Optional[Dict[int, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    PED MySQL del alcance comercial del usuario.

    Si ``dias`` es ``None`` o ``<= 0``: sin filtro ``Fecha`` (todos los PED del alcance,
    hasta ``limit``, default 5000). Si ``dias > 0``: filtra ``Fecha >= DATE_SUB(...)``.
    """
    where = ["cp.TipoComprobante = 'PED'"]
    params: List[Any] = []
    if dias is not None and int(dias) > 0:
        where.append("cp.Fecha >= DATE_SUB(CURDATE(), INTERVAL %s DAY)")
        params.append(max(1, min(int(dias), 365)))

    tipousuario = (sess_user.get("tipousuario") or "").strip().lower()
    if tipousuario == "cliente":
        idc = to_int_or_none(sess_user.get("idcliente") or sess_user.get("Codigo"))
        if idc is not None:
            where.append("cp.Codigo = %s")
            params.append(idc)
    elif puede_ver_todos_pedidos(sess_user):
        # Supervisor / Supervisor venta / Administracion, todos_clientes o
        # ecom.pedidos.ver_todos: sin filtro CodViajante (ven todos los PED).
        pass
    else:
        alcance = alcance_viajantes_comercial(base_empresa, sess_user)
        if not alcance:
            where.append("1 = 0")
        elif len(alcance) == 1:
            where.append("cp.CodViajante = %s")
            params.append(alcance[0])
        else:
            ph = ",".join(["%s"] * len(alcance))
            where.append(f"cp.CodViajante IN ({ph})")
            params.extend(alcance)

    params.append(max(1, min(int(limit), 5000)))
    if aprobacion_on is None:
        aprobacion_on = aprobacion_pedidos_activa(base_empresa)
    mapa_lotes = mapa_lotes or {}
    contexto_lotes = contexto_lotes or {}
    sql = f"""
        SELECT
            cp.CodigoMovimiento,
            cp.NroComprobante,
            TRIM(COALESCE(cp.TipoPedido, '')) AS tipo_pedido,
            TRIM(COALESCE(cp.Detalle, '')) AS detalle,
            DATE_FORMAT(cp.Fecha, '%%d/%%m/%%Y') AS fecha,
            cp.Estado,
            cp.Anulado,
            TRIM(COALESCE(cp.autorizacion_sistema, '')) AS autorizacion,
            TRIM(COALESCE(cp.estado_aprobacion_comercial, '-')) AS estado_aprobacion_comercial,
            cp.CodViajante,
            cp.Codigo AS id_cliente,
            COALESCE(c.nombre_cliente, '') AS nombre_cliente,
            cp.ImporteVenta,
            (cp.SubtotalDesc + cp.IVA1 + cp.IVA2 + COALESCE(cp.total_percep, 0)) AS total_calc,
            cda.id_cliente_domicilio,
            COALESCE(cd.Calle, '') AS calle_domicilio,
            COALESCE(cd.NroCalle, '') AS nro_domicilio
        FROM comp_ped cp
        LEFT JOIN cliente c ON c.Codigo = cp.Codigo
        LEFT JOIN cliente_datos_adicionales cda
          ON cda.CodigoMovimiento = cp.CodigoMovimiento
         AND cda.TipoComprobante = 'PED'
        LEFT JOIN cliente_domicilio cd
          ON cd.id_cliente_domicilio = cda.id_cliente_domicilio
        WHERE {' AND '.join(where)}
        ORDER BY cp.Fecha DESC, cp.CodigoMovimiento DESC
        LIMIT %s
    """
    out: List[Dict[str, Any]] = []
    try:
        with mysql_cursor(base_empresa, dict_cursor=True) as cursor:
            cursor.execute(sql, params)
            for row in cursor.fetchall() or []:
                col = _columna_ped_mysql(
                    str(row.get("Anulado") or ""),
                    str(row.get("autorizacion") or ""),
                    str(row.get("Estado") or ""),
                    estado_aprobacion_comercial=str(
                        row.get("estado_aprobacion_comercial") or "-"
                    ),
                    aprobacion_activa=aprobacion_on,
                )
                cod = int(row["CodigoMovimiento"])
                nro = str(row.get("NroComprobante") or cod)
                id_cliente = to_int_or_none(row.get("id_cliente"))
                nombre_cliente = (row.get("nombre_cliente") or "").strip()
                cliente = _etiqueta_cliente(nombre_cliente, id_cliente)
                importe_venta = row.get("ImporteVenta")
                if importe_venta is not None and float(importe_venta or 0) > 0:
                    total = float(importe_venta)
                else:
                    total = float(row.get("total_calc") or 0)
                id_dom = to_int_or_none(row.get("id_cliente_domicilio"))
                sucursal = _etiqueta_sucursal(
                    str(row.get("calle_domicilio") or ""),
                    str(row.get("nro_domicilio") or ""),
                    id_dom,
                )
                ped_aprob = {
                    "CodigoMovimiento": cod,
                    "CodViajante": to_int_or_none(row.get("CodViajante")),
                    "estado_aprobacion_comercial": row.get("estado_aprobacion_comercial"),
                }
                puede_aprobar = (
                    aprobacion_on
                    and col == "por_autorizar"
                    and puede_aprobar_pedido(base_empresa, sess_user, ped_aprob)
                )
                est_com = str(row.get("estado_aprobacion_comercial") or "-").strip().lower()
                meta: Dict[str, Any] = {
                    "codigo_movimiento": cod,
                    "estado": row.get("Estado"),
                    "autorizacion": row.get("autorizacion"),
                    "estado_aprobacion_comercial": row.get("estado_aprobacion_comercial"),
                    "puede_aprobar": puede_aprobar,
                    "aprobacion_comercial_activa": aprobacion_on,
                    "id_cliente": id_cliente,
                    "nombre_cliente": nombre_cliente,
                    "id_cliente_domicilio": id_dom,
                    "sucursal": sucursal,
                    "rechazado_comercial": est_com == "rechazado",
                }
                draft_lote_id = mapa_lotes.get(cod)
                if draft_lote_id is not None:
                    ctx_lote = contexto_lotes.get(draft_lote_id) or {}
                    n_total = int(ctx_lote.get("n_total") or 0)
                    idx = int((ctx_lote.get("indice_por_cod") or {}).get(cod) or 0)
                    nombre_lote = _etiqueta_cliente(
                        str(ctx_lote.get("nombre_cliente") or nombre_cliente or ""),
                        id_cliente,
                    )
                    meta["lote_draft_id"] = draft_lote_id
                    meta["lote_label"] = f"Lote · {nombre_lote} ({idx}/{n_total})"
                    meta["lote_indice"] = idx
                    meta["lote_total"] = n_total
                    est_lote = str(
                        ctx_lote.get("estado_aprobacion_lote")
                        or EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_NEUTRO
                    ).strip().lower()
                    if est_lote == EcomPedidoMasivoDraft.ESTADO_APROBACION_LOTE_PENDIENTE:
                        meta["puede_aprobar"] = False
                es_best = es_ped_migracion_best(
                    str(row.get("NroComprobante") or nro),
                    str(row.get("tipo_pedido") or ""),
                    str(row.get("detalle") or ""),
                )
                out.append(
                    _tarjeta(
                        tipo="ped",
                        columna=col,
                        titulo=f"PED {nro}",
                        subtitulo=f"{cliente} · ${total:,.2f}",
                        fecha=str(row.get("fecha") or ""),
                        url=url_pedido_masivo_modo_simple(
                            cod_mov=cod,
                            consulta=es_best,
                        ),
                        id_ref=f"ped-{cod}",
                        sucursal=sucursal,
                        meta=meta,
                    )
                )
    except Exception as e:
        logger.warning("pedidos_hub_pipeline MySQL: %s", e)
    return out


def construir_hub_pedidos(
    base_empresa: str,
    sess_user: Dict[str, Any],
    *,
    id_usuario: Optional[int] = None,
    vista: str = "kanban",
    dias: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Devuelve columnas + items planos para Lista|Kanban.

    ``vista``: ``lista`` | ``kanban`` (solo metadato; mismos datos).
    ``dias``: ventana temporal opcional para PED MySQL y lotes confirmados;
    ``None`` (default) incluye todos los PED del alcance (sin ``DATE_SUB``).
    """
    id_u = to_int_or_none(id_usuario if id_usuario is not None else sess_user.get("id_usuario"))
    aprobacion_on = aprobacion_pedidos_activa(base_empresa) if base_empresa else False
    ids_visibles = columnas_hub_visibles(aprobacion_activa=aprobacion_on)
    items: List[Dict[str, Any]] = []
    mapa_lotes: Dict[int, int] = {}
    contexto_lotes: Dict[int, Dict[str, Any]] = {}
    if id_u is not None and base_empresa:
        drafts_lote = _drafts_lote_confirmados_alcance(
            base_empresa,
            id_u,
            sess_user,
            dias=dias,
        )
        if drafts_lote:
            mapa_lotes, contexto_lotes = _mapa_reverso_lotes(
                base_empresa,
                id_u,
                sess_user,
                dias=dias,
                aprobacion_on=aprobacion_on,
                drafts=drafts_lote,
            )
            ids_cliente_lote = [d.id_cliente for d in drafts_lote if d.id_cliente]
            nombres_lote = _nombres_clientes(base_empresa, ids_cliente_lote)
            for draft_id, ctx in contexto_lotes.items():
                idc = to_int_or_none(ctx.get("id_cliente"))
                if idc is not None:
                    ctx["nombre_cliente"] = nombres_lote.get(idc, "")
            n_articulos = _n_articulos_por_draft(drafts_lote)
            items.extend(
                _lotes_masivos_confirmados(
                    base_empresa,
                    sess_user,
                    drafts=drafts_lote,
                    contexto_lotes=contexto_lotes,
                    nombres=nombres_lote,
                    n_articulos_por_draft=n_articulos,
                    aprobacion_on=aprobacion_on,
                    ids_visibles=ids_visibles,
                )
            )
        items.extend(_borradores_masivo(base_empresa, id_u))
        items.extend(_borradores_carrito_legacy(base_empresa, id_u))
        items.extend(_masivos_anulados(base_empresa, id_u))
    if base_empresa:
        ped_items = _pedidos_mysql(
            base_empresa,
            sess_user,
            dias=dias,
            limit=5000,
            aprobacion_on=aprobacion_on,
            mapa_lotes=mapa_lotes,
            contexto_lotes=contexto_lotes,
        )
        items.extend(
            [
                it
                for it in ped_items
                if not (it.get("meta") or {}).get("lote_draft_id")
            ]
        )
    columnas: Dict[str, List[Dict[str, Any]]] = {k: [] for k in ids_visibles}
    for it in items:
        col = it.get("columna") or "enviado"
        if col not in columnas:
            # Pedidos mid-flow sin columna visible (p. ej. aprobación off) → Pendiente (id enviado).
            col = "enviado" if "enviado" in columnas else ids_visibles[0]
            it = {**it, "columna": col}
        columnas[col].append(it)

    items_visibles = [it for col_items in columnas.values() for it in col_items]
    labels_visibles = {cid: _LABELS[cid] for cid in ids_visibles}
    borradores_activos = len(
        [
            it
            for it in (columnas.get("borrador") or [])
            if it.get("tipo") == "masivo"
        ]
    )
    return {
        "vista": vista if vista in ("lista", "kanban") else "kanban",
        "layout_movil": "chips_cards",
        "aprobacion_comercial_activa": aprobacion_on,
        "columnas": [
            {
                "id": cid,
                "label": _LABELS[cid],
                "count": len(columnas[cid]),
                "items": columnas[cid],
            }
            for cid in ids_visibles
        ],
        "items": items_visibles,
        "cargas_masivas": [],
        "borradores_activos": borradores_activos,
        "labels": labels_visibles,
    }


def archivar_borrador_masivo(draft_id: int, id_usuario: int, base_empresa: str) -> bool:
    """Archiva un draft del usuario (para Nuevo → Masivo con confirmación)."""
    n = EcomPedidoMasivoDraft.objects.filter(
        pk=draft_id,
        id_usuario=id_usuario,
        base_empresa=base_empresa,
        estado__in=(
            EcomPedidoMasivoDraft.ESTADO_BORRADOR,
            EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
        ),
    ).update(estado=EcomPedidoMasivoDraft.ESTADO_ARCHIVADO)
    return n > 0


def eliminar_borrador_masivo_definitivo(
    draft_id: int,
    id_usuario: int,
    base_empresa: str,
) -> tuple[bool, str]:
    """Elimina definitivamente un borrador masivo/simple en estado anulado."""
    draft = EcomPedidoMasivoDraft.objects.filter(
        pk=draft_id,
        id_usuario=id_usuario,
        base_empresa=base_empresa,
    ).first()
    if draft is None:
        return False, "Borrador no encontrado."
    if draft.estado != EcomPedidoMasivoDraft.ESTADO_ANULADO:
        return False, "Solo se pueden eliminar definitivamente borradores anulados."
    draft.delete()
    return True, "Borrador eliminado definitivamente."


def archivar_carrito_legacy(cart_id: int, id_usuario: int, base_empresa: str) -> bool:
    """Descarta un borrador `EcomCart` legacy (ítems + carrito)."""
    cart = (
        EcomCart.objects.filter(
            pk=cart_id,
            id_usuario=id_usuario,
            base_empresa=base_empresa,
            estado=EcomCart.ESTADO_BORRADOR,
        )
        .first()
    )
    if not cart:
        return False
    with transaction.atomic():
        cart.items.all().delete()
        cart.delete()
    return True


def migrar_carrito_legacy_a_draft(
    cart_id: int,
    id_usuario: int,
    base_empresa: str,
    *,
    cod_viajante: Optional[int] = None,
) -> Tuple[Optional[int], Optional[str]]:
    """
    Convierte ítems de ``EcomCart`` borrador a celdas de draft masivo ``modo=simple``.
    Devuelve ``(draft_id, error)``.
    """
    cart = (
        EcomCart.objects.filter(
            pk=cart_id,
            id_usuario=id_usuario,
            base_empresa=base_empresa,
            estado=EcomCart.ESTADO_BORRADOR,
        )
        .prefetch_related("items")
        .first()
    )
    if not cart:
        return None, "Carrito no encontrado."
    id_cliente = to_int_or_none(cart.idcliente)
    if id_cliente is None:
        return None, "El carrito no tiene cliente asociado."

    sucursales = listar_sucursales_cliente(
        base_empresa,
        id_cliente,
        to_int_or_none(cod_viajante),
    )
    if not sucursales:
        return None, "El cliente no tiene sucursales activas para migrar el borrador."
    id_domicilio = to_int_or_none(sucursales[0].get("id_cliente_domicilio"))
    if id_domicilio is None:
        return None, "No se pudo resolver el domicilio del cliente."

    draft, err = obtener_o_crear_draft(
        base_empresa=base_empresa,
        id_usuario=id_usuario,
        id_cliente=id_cliente,
        cod_viajante=to_int_or_none(cod_viajante),
        modo=EcomPedidoMasivoDraft.MODO_SIMPLE,
        id_domicilio_fijo=id_domicilio,
    )
    if err or draft is None:
        return None, err or "No se pudo crear el borrador masivo."

    celdas_nuevas: List[EcomPedidoMasivoDraftCelda] = []
    for item in cart.items.all().order_by("orden", "id"):
        salida = item.cantidad or Decimal("0")
        if salida <= 0:
            continue
        packs, _aviso = _salida_a_packs_matriz(
            base_empresa,
            int(item.id_articulo),
            salida,
            tipo_unidad_linea=str(item.tipo_unidad or ""),
            descripcion=str(item.descripcion or ""),
        )
        if packs <= 0:
            continue
        celdas_nuevas.append(
            EcomPedidoMasivoDraftCelda(
                draft=draft,
                id_articulo=int(item.id_articulo),
                id_cliente_domicilio=id_domicilio,
                cantidad_packs=packs,
            )
        )

    with transaction.atomic():
        draft.celdas.all().delete()
        if celdas_nuevas:
            EcomPedidoMasivoDraftCelda.objects.bulk_create(celdas_nuevas)
        draft.modo = EcomPedidoMasivoDraft.MODO_SIMPLE
        draft.id_domicilio_fijo = id_domicilio
        draft.id_cliente = id_cliente
        draft.descuento_pie_pct = cart.descuento_pie_pct
        if cod_viajante is not None:
            draft.cod_viajante = cod_viajante
        draft.save(
            update_fields=[
                "modo",
                "id_domicilio_fijo",
                "id_cliente",
                "cod_viajante",
                "descuento_pie_pct",
                "updated_at",
            ]
        )
        cart.items.all().delete()
        cart.delete()

    return draft.pk, None
