"""Servicios de matriz pedido masivo por sucursales (Phase 4)."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.db import transaction

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from ecom.models import EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.services.catalogo_producto import listar_articulos_paginado
from ecom.services.cliente_relay import cod_viajante_desde_sesion_usuario

logger = logging.getLogger(__name__)


def marcas_asignadas_viajante_cliente(
    base_empresa: str,
    cod_viajante: int,
    id_cliente: int,
) -> List[int]:
    """CodMarca activos de la terna (vendedor, cliente)."""
    cv = to_int_or_none(cod_viajante)
    idc = to_int_or_none(id_cliente)
    if cv is None or idc is None:
        return []
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    SELECT CodMarca
                    FROM ecom_vendedor_cliente_marca
                    WHERE CodViajante = %s
                      AND id_cliente = %s
                      AND COALESCE(anulado, 'No') = 'No'
                    """,
                    [cv, idc],
                )
                return [int(r[0]) for r in cursor.fetchall() if r and r[0] is not None]
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("marcas_asignadas_viajante_cliente: %s", e)
        return []


def listar_sucursales_cliente(base_empresa: str, id_cliente: int) -> List[Dict[str, Any]]:
    """``cliente_domicilio`` no anulados → columnas de la matriz."""
    idc = to_int_or_none(id_cliente)
    if idc is None:
        return []
    sql = """
        SELECT
            cm.id_cliente_domicilio AS id_cliente_domicilio,
            COALESCE(cm.Calle, '') AS calle,
            COALESCE(cm.NroCalle, '') AS nro,
            COALESCE(cm.Dpto, '') AS dpto,
            COALESCE(pv.Provincia, '') AS provincia,
            COALESCE(dt.NombreDistrito, '') AS distrito,
            COALESCE(z.nombre_zona, '') AS zona
        FROM cliente_domicilio AS cm
        LEFT JOIN provincia AS pv ON pv.CodProvincia = cm.CodProvincia
        LEFT JOIN distrito AS dt ON dt.IDDistrito = cm.IDDistrito
        LEFT JOIN erp_zona AS z ON z.id_zona = cm.id_zona
        WHERE cm.id_cliente = %s
          AND COALESCE(cm.anulado, 'No') = 'No'
        ORDER BY cm.id_cliente_domicilio ASC
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, [idc])
                out = []
                for r in cursor.fetchall():
                    calle = (r[1] or "").strip()
                    nro = (r[2] or "").strip()
                    dpto = (r[3] or "").strip()
                    dir_parts = [p for p in (calle, nro, dpto) if p and p != "-"]
                    etiqueta = " ".join(dir_parts) or f"Sucursal #{int(r[0])}"
                    out.append(
                        {
                            "id_cliente_domicilio": int(r[0]),
                            "etiqueta": etiqueta,
                            "calle": calle,
                            "nro": nro,
                            "dpto": dpto,
                            "provincia": (r[4] or "").strip(),
                            "distrito": (r[5] or "").strip(),
                            "zona": (r[6] or "").strip(),
                        }
                    )
                return out
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("listar_sucursales_cliente: %s", e)
        return []


def listar_clientes_con_ternas(
    base_empresa: str,
    cod_viajante: int,
    q: str = "",
    limit: int = 40,
) -> List[Dict[str, Any]]:
    """Clientes que tienen al menos una terna activa con el viajante."""
    cv = to_int_or_none(cod_viajante)
    if cv is None:
        return []
    lim = max(1, min(int(limit), 100))
    where = [
        "t.CodViajante = %s",
        "COALESCE(t.anulado, 'No') = 'No'",
        "c.Estado = 'Activo'",
    ]
    params: List[Any] = [cv]
    q = (q or "").strip()
    if q:
        qi = to_int_or_none(q)
        if qi is not None:
            where.append(
                "(c.Codigo = %s OR c.nombre_cliente LIKE %s OR c.id_manual_cli LIKE %s)"
            )
            params.extend([qi, f"%{q}%", f"%{q}%"])
        else:
            where.append("(c.nombre_cliente LIKE %s OR c.id_manual_cli LIKE %s)")
            params.extend([f"%{q}%", f"%{q}%"])
    params.append(lim)
    sql = f"""
        SELECT DISTINCT c.Codigo, COALESCE(c.nombre_cliente, '') AS nombre
        FROM ecom_vendedor_cliente_marca t
        INNER JOIN cliente c ON c.Codigo = t.id_cliente
        WHERE {' AND '.join(where)}
        ORDER BY c.nombre_cliente ASC
        LIMIT %s
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                return [
                    {
                        "id_cliente": int(r[0]),
                        "nombre": (r[1] or "").strip(),
                        "etiqueta": f"{(r[1] or '').strip()} (cod: {int(r[0])})",
                    }
                    for r in cursor.fetchall()
                ]
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("listar_clientes_con_ternas: %s", e)
        return []


def buscar_articulos_filtrados_ternas(
    base_empresa: str,
    *,
    cod_viajante: int,
    id_cliente: int,
    q: str = "",
    lista_id: int = 1,
    id_deposito: int = 1,
    pagina: int = 1,
    tam: int = 30,
    iva_incluido: bool = True,
    descuento_cliente: Decimal = Decimal("0"),
) -> Dict[str, Any]:
    """Catálogo restringido a marcas de la terna (vendedor, cliente)."""
    marcas = marcas_asignadas_viajante_cliente(base_empresa, cod_viajante, id_cliente)
    if not marcas:
        return {
            "items": [],
            "total": 0,
            "pagina": 1,
            "tam": tam,
            "total_paginas": 0,
            "marcas": [],
            "sin_marcas": True,
        }
    result = listar_articulos_paginado(
        base_empresa,
        filtros={"marcas": marcas, "q": q or ""},
        lista_id=lista_id,
        codigo_cliente=to_int_or_none(id_cliente),
        descuento_cliente=descuento_cliente,
        iva_incluido=iva_incluido,
        id_deposito=id_deposito,
        pagina=pagina,
        tam=tam,
    )
    result["marcas"] = marcas
    result["sin_marcas"] = False
    return result


def _nombres_articulos(base_empresa: str, ids: Sequence[int]) -> Dict[int, Dict[str, str]]:
    ids_clean = [i for i in (to_int_or_none(x) for x in ids) if i is not None]
    if not ids_clean:
        return {}
    placeholders = ",".join(["%s"] * len(ids_clean))
    sql = f"""
        SELECT IDArt, COALESCE(id_manual, ''), COALESCE(NombreArticulo, '')
        FROM articulo
        WHERE IDArt IN ({placeholders})
    """
    out: Dict[int, Dict[str, str]] = {}
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, list(ids_clean))
                for r in cursor.fetchall():
                    out[int(r[0])] = {
                        "codigo": str_or_default(r[1], ""),
                        "descripcion": str_or_default(r[2], ""),
                    }
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("_nombres_articulos: %s", e)
    return out


def obtener_o_crear_draft(
    *,
    base_empresa: str,
    id_usuario: int,
    id_cliente: int,
    cod_viajante: Optional[int],
    draft_id: Optional[int] = None,
) -> Tuple[Optional[EcomPedidoMasivoDraft], str]:
    """
    Si ``draft_id``: valida ownership y cliente.
    Si no: reutiliza borrador activo del mismo usuario+cliente o crea uno nuevo.
    """
    id_u = to_int_or_none(id_usuario)
    idc = to_int_or_none(id_cliente)
    if not base_empresa or id_u is None or idc is None:
        return None, "Parámetros inválidos."

    if draft_id is not None:
        d = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id,
            base_empresa=base_empresa,
            id_usuario=id_u,
        ).first()
        if not d:
            return None, "Borrador no encontrado."
        if d.estado == EcomPedidoMasivoDraft.ESTADO_ARCHIVADO:
            return None, "El borrador está archivado."
        if d.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMADO:
            return None, "El borrador ya fue confirmado."
        return d, ""

    existente = (
        EcomPedidoMasivoDraft.objects.filter(
            base_empresa=base_empresa,
            id_usuario=id_u,
            id_cliente=idc,
            estado__in=(
                EcomPedidoMasivoDraft.ESTADO_BORRADOR,
                EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
            ),
        )
        .order_by("-updated_at")
        .first()
    )
    if existente:
        if existente.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO:
            existente.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
            existente.save(update_fields=["estado", "updated_at"])
        return existente, ""

    d = EcomPedidoMasivoDraft.objects.create(
        base_empresa=base_empresa,
        id_usuario=id_u,
        id_cliente=idc,
        cod_viajante=to_int_or_none(cod_viajante),
        estado=EcomPedidoMasivoDraft.ESTADO_BORRADOR,
    )
    return d, ""


def serializar_matriz(
    draft: EcomPedidoMasivoDraft,
    base_empresa: str,
) -> Dict[str, Any]:
    sucursales = listar_sucursales_cliente(base_empresa, draft.id_cliente)
    celdas_qs = list(draft.celdas.all())
    art_ids = sorted({c.id_articulo for c in celdas_qs})
    nombres = _nombres_articulos(base_empresa, art_ids)

    celdas_map: Dict[str, str] = {}
    for c in celdas_qs:
        key = f"{c.id_articulo}:{c.id_cliente_domicilio}"
        qty = c.cantidad_packs
        # Evitar "3.000" ruidoso en UI
        if qty == qty.to_integral_value():
            celdas_map[key] = str(int(qty))
        else:
            celdas_map[key] = format(qty.normalize(), "f")

    articulos = [
        {
            "id_articulo": aid,
            "codigo": nombres.get(aid, {}).get("codigo", ""),
            "descripcion": nombres.get(aid, {}).get("descripcion", f"Art. {aid}"),
        }
        for aid in art_ids
    ]

    return {
        "draft_id": draft.pk,
        "id_cliente": draft.id_cliente,
        "cod_viajante": draft.cod_viajante,
        "estado": draft.estado,
        "ultimo_error": draft.ultimo_error or {},
        "codigos_movimiento": draft.codigos_movimiento or [],
        "sucursales": sucursales,
        "articulos": articulos,
        "celdas": celdas_map,
        "updated_at": draft.updated_at.isoformat() if draft.updated_at else "",
    }


def guardar_celda(
    draft: EcomPedidoMasivoDraft,
    *,
    id_articulo: int,
    id_cliente_domicilio: int,
    cantidad_packs: Any,
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """Autoguarda una celda. Cantidad 0 elimina la fila de esa sucursal."""
    if draft.estado not in (
        EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
    ):
        return False, "El borrador no es editable.", None
    if draft.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO:
        draft.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
        draft.save(update_fields=["estado", "updated_at"])

    aid = to_int_or_none(id_articulo)
    idd = to_int_or_none(id_cliente_domicilio)
    qty = to_decimal_or_none(cantidad_packs) or Decimal("0")
    if aid is None or idd is None:
        return False, "Artículo o sucursal inválidos.", None
    if qty < 0:
        return False, "La cantidad no puede ser negativa.", None

    with transaction.atomic():
        if qty == 0:
            EcomPedidoMasivoDraftCelda.objects.filter(
                draft=draft,
                id_articulo=aid,
                id_cliente_domicilio=idd,
            ).delete()
            draft.save(update_fields=["updated_at"])
            return True, "Celda vaciada.", {"cantidad_packs": "0", "eliminada": True}

        celda, _created = EcomPedidoMasivoDraftCelda.objects.update_or_create(
            draft=draft,
            id_articulo=aid,
            id_cliente_domicilio=idd,
            defaults={"cantidad_packs": qty},
        )
        draft.save(update_fields=["updated_at"])
        if qty == qty.to_integral_value():
            qty_s = str(int(qty))
        else:
            qty_s = format(qty.normalize(), "f")
        return (
            True,
            "Guardado.",
            {
                "id": celda.pk,
                "cantidad_packs": qty_s,
                "eliminada": False,
            },
        )


def cod_viajante_sesion(sess_user: Dict[str, Any]) -> Optional[int]:
    return cod_viajante_desde_sesion_usuario(sess_user)
