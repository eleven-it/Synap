"""Servicios de matriz pedido masivo por sucursales (Phase 4)."""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.db import transaction

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from mpr.services import get_deposito_terminado_mpr
from self_checkout.services.stock_service import StockService
from ecom.models import EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.services.catalogo_producto import resolver_precio_articulo
from ecom.services.price_rules_engine import (
    calcular_precio_articulo_row,
    resolver_reglas_precio_map,
)
from ecom.services.multiplo_empaque import (
    campos_multiplo_articulo,
    cantidad_respeta_multiplo,
    disponible_unidades_a_packs,
    infracciones_multiplo_celdas,
    mensaje_multiplo_invalido,
    multiplo_empaque_venta,
)
from ecom.services.vendedor_operativo import resolver_viajante_operativo

logger = logging.getLogger(__name__)


def _dec(v: Any, default: str = "0") -> Decimal:
    r = to_decimal_or_none(v)
    return r if r is not None else Decimal(default)


def _clamp_pct(v: Any) -> Decimal:
    pct = _dec(v)
    if pct < 0:
        return Decimal("0")
    if pct > 100:
        return Decimal("100")
    return pct


def leer_contexto_cliente_masivo(base_empresa: str, id_cliente: int) -> Dict[str, Any]:
    """Descuentos y lista del cliente legacy (descRenglon, descPie, lista_id)."""
    idc = to_int_or_none(id_cliente)
    if idc is None:
        return {"descRenglon": Decimal("0"), "descPie": Decimal("0"), "lista_id": 1}
    sql = """
        SELECT
            cliente.descuento_por_cli AS descRenglon,
            cliente.Descuento AS descPie,
            SUBSTRING(cliente.ListaPrecio, 6) AS codListaPrecio
        FROM cliente
        WHERE cliente.Codigo = %s
        LIMIT 1
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, [idc])
                row = cursor.fetchone()
                if not row:
                    return {"descRenglon": Decimal("0"), "descPie": Decimal("0"), "lista_id": 1}
                lista_id = to_int_or_none(row[2]) or 1
                return {
                    "descRenglon": _dec(row[0]),
                    "descPie": _dec(row[1]),
                    "lista_id": lista_id,
                }
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("leer_contexto_cliente_masivo: %s", e)
        return {"descRenglon": Decimal("0"), "descPie": Decimal("0"), "lista_id": 1}


def _precio_real_articulo(
    base_empresa: str,
    id_articulo: int,
    *,
    lista_id: int,
    id_cliente: int,
    descuento_cliente: Decimal,
) -> Optional[Decimal]:
    res = resolver_precio_articulo(
        base_empresa,
        id_articulo,
        lista_id=lista_id,
        codigo_cliente=id_cliente,
        descuento_cliente=descuento_cliente,
        iva_incluido=False,
    )
    if res is None:
        return None
    return _dec(res[0])


def descuentos_fila_efectivos(
    draft: EcomPedidoMasivoDraft,
    base_empresa: str,
) -> Dict[int, Decimal]:
    """Mapa id_articulo → % descuento renglón (borrador o descRenglon del cliente)."""
    ctx = leer_contexto_cliente_masivo(base_empresa, draft.id_cliente)
    default = _clamp_pct(ctx.get("descRenglon"))
    stored = draft.descuentos_fila if isinstance(draft.descuentos_fila, dict) else {}
    art_ids = {c.id_articulo for c in draft.celdas.all()}
    out: Dict[int, Decimal] = {}
    for aid in art_ids:
        raw = stored.get(str(aid))
        if raw is not None:
            out[int(aid)] = _clamp_pct(raw)
        else:
            out[int(aid)] = default
    return out


def asegurar_descuento_fila_articulo(
    draft: EcomPedidoMasivoDraft,
    id_articulo: int,
    base_empresa: str,
) -> None:
    """Precarga descRenglon del cliente al registrar un artículo en la matriz."""
    aid = to_int_or_none(id_articulo)
    if aid is None:
        return
    stored = dict(draft.descuentos_fila or {})
    if str(aid) in stored:
        return
    ctx = leer_contexto_cliente_masivo(base_empresa, draft.id_cliente)
    stored[str(aid)] = float(_clamp_pct(ctx.get("descRenglon")))
    draft.descuentos_fila = stored
    draft.save(update_fields=["descuentos_fila", "updated_at"])


def guardar_descuento_fila(
    draft: EcomPedidoMasivoDraft,
    *,
    id_articulo: int,
    porcentaje_descuento: Any,
) -> Tuple[bool, str]:
    if draft.estado not in (
        EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
    ):
        return False, "El borrador no es editable."
    aid = to_int_or_none(id_articulo)
    if aid is None:
        return False, "Artículo inválido."
    stored = dict(draft.descuentos_fila or {})
    stored[str(aid)] = float(_clamp_pct(porcentaje_descuento))
    draft.descuentos_fila = stored
    draft.save(update_fields=["descuentos_fila", "updated_at"])
    return True, "Descuento de fila guardado."


def guardar_descuento_pie(
    draft: EcomPedidoMasivoDraft,
    *,
    desc_pie_pct: Any,
) -> Tuple[bool, str]:
    if draft.estado not in (
        EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
    ):
        return False, "El borrador no es editable."
    draft.descuento_pie_pct = _clamp_pct(desc_pie_pct)
    draft.save(update_fields=["descuento_pie_pct", "updated_at"])
    return True, "Descuento pie guardado."


def _lista_id_efectiva(
    draft: EcomPedidoMasivoDraft,
    base_empresa: str,
    lista_id: Optional[int] = None,
) -> int:
    lid = to_int_or_none(lista_id)
    if lid is not None and 1 <= lid <= 5:
        return int(lid)
    ctx = leer_contexto_cliente_masivo(base_empresa, draft.id_cliente)
    return int(ctx.get("lista_id") or 1)


def precios_fila_efectivos(
    draft: EcomPedidoMasivoDraft,
    base_empresa: str,
    *,
    lista_id: Optional[int] = None,
) -> Dict[int, Decimal]:
    """Mapa id_articulo → precio unitario neto (override de fila o lista)."""
    ctx = leer_contexto_cliente_masivo(base_empresa, draft.id_cliente)
    lista_ef = _lista_id_efectiva(draft, base_empresa, lista_id)
    desc_cli = _clamp_pct(ctx.get("descRenglon"))
    stored = draft.precios_fila if isinstance(draft.precios_fila, dict) else {}
    art_ids = {c.id_articulo for c in draft.celdas.all()}
    out: Dict[int, Decimal] = {}
    for aid in art_ids:
        raw = stored.get(str(aid))
        if raw is not None:
            p = to_decimal_or_none(raw)
            if p is not None:
                out[int(aid)] = p
                continue
        lista = _precio_real_articulo(
            base_empresa,
            int(aid),
            lista_id=lista_ef,
            id_cliente=draft.id_cliente,
            descuento_cliente=desc_cli,
        )
        out[int(aid)] = lista if lista is not None else Decimal("0")
    return out


def asegurar_precio_fila_articulo(
    draft: EcomPedidoMasivoDraft,
    id_articulo: int,
    base_empresa: str,
    *,
    lista_id: Optional[int] = None,
) -> None:
    """Precarga el precio de lista al registrar un artículo, si aún no hay override."""
    aid = to_int_or_none(id_articulo)
    if aid is None:
        return
    stored = dict(draft.precios_fila or {})
    if str(aid) in stored:
        return
    ctx = leer_contexto_cliente_masivo(base_empresa, draft.id_cliente)
    lista_ef = _lista_id_efectiva(draft, base_empresa, lista_id)
    precio = _precio_real_articulo(
        base_empresa,
        int(aid),
        lista_id=lista_ef,
        id_cliente=draft.id_cliente,
        descuento_cliente=_clamp_pct(ctx.get("descRenglon")),
    )
    stored[str(aid)] = float(precio if precio is not None else Decimal("0"))
    draft.precios_fila = stored
    draft.save(update_fields=["precios_fila", "updated_at"])


def guardar_precio_fila(
    draft: EcomPedidoMasivoDraft,
    *,
    id_articulo: int,
    precio_unitario_neto: Any,
) -> Tuple[bool, str]:
    if draft.estado not in (
        EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
    ):
        return False, "El borrador no es editable."
    aid = to_int_or_none(id_articulo)
    if aid is None:
        return False, "Artículo inválido."
    precio = to_decimal_or_none(precio_unitario_neto)
    if precio is None:
        return False, "El precio no es válido."
    if precio < 0:
        return False, "El precio no puede ser negativo."
    stored = dict(draft.precios_fila or {})
    stored[str(aid)] = float(precio)
    draft.precios_fila = stored
    draft.save(update_fields=["precios_fila", "updated_at"])
    return True, "Precio de fila guardado."


def recalcular_precios_fila_desde_lista(
    draft: EcomPedidoMasivoDraft,
    base_empresa: str,
    *,
    lista_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """Reemplaza los precios de línea con los de la lista indicada."""
    if draft.estado not in (
        EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
    ):
        return False, "El borrador no es editable."
    ctx = leer_contexto_cliente_masivo(base_empresa, draft.id_cliente)
    lista_ef = _lista_id_efectiva(draft, base_empresa, lista_id)
    desc_cli = _clamp_pct(ctx.get("descRenglon"))
    stored: Dict[str, float] = {}
    for aid in {c.id_articulo for c in draft.celdas.all()}:
        precio = _precio_real_articulo(
            base_empresa,
            int(aid),
            lista_id=lista_ef,
            id_cliente=draft.id_cliente,
            descuento_cliente=desc_cli,
        )
        stored[str(int(aid))] = float(precio if precio is not None else Decimal("0"))
    draft.precios_fila = stored
    draft.save(update_fields=["precios_fila", "updated_at"])
    return True, "Precios recalculados con la lista seleccionada."


def lineas_con_precio_cero(
    draft: EcomPedidoMasivoDraft,
    base_empresa: str,
    *,
    lista_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Artículos con cantidad > 0 y precio efectivo ≤ 0."""
    precios = precios_fila_efectivos(draft, base_empresa, lista_id=lista_id)
    qty_por_art: Dict[int, Decimal] = {}
    for c in draft.celdas.all():
        aid = to_int_or_none(c.id_articulo)
        if aid is None:
            continue
        qty_por_art[aid] = qty_por_art.get(aid, Decimal("0")) + _dec(c.cantidad_packs)
    out: List[Dict[str, Any]] = []
    for aid, qty in qty_por_art.items():
        if qty <= 0:
            continue
        precio = precios.get(aid, Decimal("0"))
        if precio <= 0:
            out.append(
                {
                    "id_articulo": aid,
                    "cantidad_packs": float(qty),
                    "precio_unitario_neto": float(precio),
                }
            )
    return out


def marcas_asignadas_viajante_cliente(
    base_empresa: str,
    cod_viajante: int,
    id_cliente: int,
    id_cliente_domicilio: Optional[int] = None,
) -> List[int]:
    """
    CodMarca activos de la cuaterna (vendedor, cliente[, sucursal]).

    Si ``id_cliente_domicilio`` es None o 0: unión de marcas en todas las sucursales del par.
    Si > 0: solo marcas de esa sucursal.
    """
    cv = to_int_or_none(cod_viajante)
    idc = to_int_or_none(id_cliente)
    if cv is None or idc is None:
        return []
    idd = to_int_or_none(id_cliente_domicilio)
    where = [
        "CodViajante = %s",
        "id_cliente = %s",
        "COALESCE(anulado, 'No') = 'No'",
    ]
    params: List[Any] = [cv, idc]
    if idd is not None and idd > 0:
        where.append("id_cliente_domicilio = %s")
        params.append(idd)
    sql = f"""
        SELECT DISTINCT CodMarca
        FROM ecom_vendedor_cliente_marca
        WHERE {' AND '.join(where)}
        ORDER BY CodMarca ASC
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                return [int(r[0]) for r in cursor.fetchall() if r and r[0] is not None]
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("marcas_asignadas_viajante_cliente: %s", e)
        return []


def listar_sucursales_cliente(
    base_empresa: str,
    id_cliente: int,
    cod_viajante: Optional[int] = None,
    *,
    ids_domicilio: Optional[List[int]] = None,
    incluir_anulados: bool = False,
) -> List[Dict[str, Any]]:
    """``cliente_domicilio`` → columnas de la matriz.

    Si VCM está activo y hay ``cod_viajante``, solo sucursales con ≥1 cuaterna activa.
    Con ``ids_domicilio`` se fuerza ese conjunto (snapshot histórico) y se omite el
    filtro VCM — útil al reabrir un lote confirmado cuyas celdas apuntan a
    domicilios que ya no están en la asignación VCM vigente.
    """
    from ecom.services.vendedor_asignacion_sql import vcm_ternas_disponible

    idc = to_int_or_none(id_cliente)
    if idc is None:
        return []
    ids_hist = sorted(
        {
            i
            for i in (to_int_or_none(x) for x in (ids_domicilio or []))
            if i is not None
        }
    )
    cv = to_int_or_none(cod_viajante)
    filtrar_vcm = (
        not ids_hist
        and vcm_ternas_disponible(base_empresa)
        and cv is not None
    )
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
    """
    params: List[Any] = [idc]
    if not incluir_anulados:
        sql += " AND COALESCE(cm.anulado, 'No') = 'No'"
    if ids_hist:
        placeholders = ",".join(["%s"] * len(ids_hist))
        sql += f" AND cm.id_cliente_domicilio IN ({placeholders})"
        params.extend(ids_hist)
    if filtrar_vcm:
        sql += """
          AND EXISTS (
              SELECT 1 FROM ecom_vendedor_cliente_marca vcm
              WHERE vcm.id_cliente = cm.id_cliente
                AND vcm.id_cliente_domicilio = cm.id_cliente_domicilio
                AND vcm.CodViajante = %s
                AND COALESCE(vcm.anulado, 'No') = 'No'
          )
        """
        params.append(cv)
    sql += " ORDER BY cm.id_cliente_domicilio ASC"
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params)
                out = []
                for r in cursor.fetchall():
                    calle = (r[1] or "").strip()
                    nro = (r[2] or "").strip()
                    dpto = (r[3] or "").strip()
                    # En AdministraNET la «sucursal» del cliente suele vivir en Calle (+ NroCalle).
                    nombre_parts = [p for p in (calle, nro) if p and p != "-"]
                    nombre = " ".join(nombre_parts).strip()
                    dir_parts = [p for p in (calle, nro, dpto) if p and p != "-"]
                    etiqueta = nombre or " ".join(dir_parts) or f"Sucursal #{int(r[0])}"
                    out.append(
                        {
                            "id_cliente_domicilio": int(r[0]),
                            "nombre": etiqueta,
                            "etiqueta": etiqueta,
                            "calle": calle,
                            "nro": nro,
                            "dpto": dpto,
                            "provincia": (r[4] or "").strip(),
                            "distrito": (r[5] or "").strip(),
                            "zona": (r[6] or "").strip(),
                        }
                    )
                out.sort(key=_clave_orden_nro_sucursal)
                return out
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("listar_sucursales_cliente: %s", e)
        return []


def _clave_orden_nro_sucursal(suc: Dict[str, Any]) -> tuple:
    """Orden ascendente numérico por NroCalle (fallback id_cliente_domicilio)."""
    nro = str(suc.get("nro") or "").strip()
    digitos = "".join(ch for ch in nro if ch.isdigit())
    id_dom = to_int_or_none(suc.get("id_cliente_domicilio")) or 0
    if digitos:
        try:
            return (0, int(digitos), id_dom)
        except ValueError:
            pass
    return (1, id_dom, 0)


def _clave_orden_nombre_articulo(
    nombres: Dict[int, Dict[str, Any]], aid: int
) -> tuple:
    """Orden alfabético por nombre visible en la matriz (descripción / código)."""
    info = nombres.get(aid) or {}
    etiqueta = (
        str_or_default(info.get("descripcion"), "")
        or str_or_default(info.get("codigo"), "")
        or f"art. {aid}"
    ).strip().lower()
    return (etiqueta, aid)


def credito_cliente_masivo(base_empresa: str, id_cliente: int) -> Dict[str, Any]:
    """
    Datos de crédito/cuenta del cliente para el widget hero (REQ-PSU-07).

    Expone por separado cupo monetario (``cliente.Credito``) y límite de mora
    en días (``cliente.credito_limite_dias``). No consulta autorización por pedido.
    """
    idc = to_int_or_none(id_cliente)
    vacio = {"saldo": 0.0, "credito_cupo": 0.0, "credito_limite_dias": 0}
    if idc is None:
        return vacio
    sql = """
        SELECT
            COALESCE(cliente.Saldo, 0) AS saldo,
            COALESCE(cliente.Credito, 0) AS credito_cupo,
            COALESCE(cliente.credito_limite_dias, 0) AS credito_limite_dias
        FROM cliente
        WHERE cliente.Codigo = %s
        LIMIT 1
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, [idc])
                row = cursor.fetchone()
                if not row:
                    return vacio
                return {
                    "saldo": float(_dec(row[0])),
                    "credito_cupo": float(_dec(row[1])),
                    "credito_limite_dias": int(to_int_or_none(row[2]) or 0),
                }
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("credito_cliente_masivo: %s", e)
        return vacio


def _nombre_cliente(base_empresa: str, id_cliente: int) -> str:
    idc = to_int_or_none(id_cliente)
    if idc is None:
        return ""
    sql = """
        SELECT COALESCE(nombre_cliente, '')
        FROM cliente
        WHERE Codigo = %s
        LIMIT 1
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, [idc])
                row = cursor.fetchone()
                return (row[0] or "").strip() if row else ""
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("_nombre_cliente: %s", e)
        return ""


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


def _stock_disponible_packs_map(
    base_empresa: str,
    ids_articulos: Sequence[int],
    multiplos_por_articulo: Optional[Dict[int, Dict[str, Any]]] = None,
) -> Dict[int, float]:
    """
    Stock disponible (saldo − saldo_pedido_cliente) en depósito Terminado MPR,
    expresado en packs según ``multiplo_cantidad_vta``. Una consulta bulk.
    """
    ids_clean = sorted(
        {i for i in (to_int_or_none(x) for x in ids_articulos) if i is not None}
    )
    if not ids_clean:
        return {}

    id_dep = get_deposito_terminado_mpr(base_empresa.strip())
    if id_dep is None:
        logger.warning(
            "_stock_disponible_packs_map: sin depósito Terminado en %s",
            base_empresa,
        )
        return {i: 0.0 for i in ids_clean}

    stock_svc = StockService(base_empresa.strip())
    disp_map = stock_svc.get_disponible_map(ids_clean, int(id_dep))

    if multiplos_por_articulo is None:
        multiplos_por_articulo = _multiplos_articulos(base_empresa, ids_clean)

    out: Dict[int, float] = {}
    for id_art in ids_clean:
        info = multiplos_por_articulo.get(id_art) or {}
        mc = info.get("multiplo_cantidad_vta")
        if mc is None:
            mc = info.get("multiplo_empaque")
        out[id_art] = disponible_unidades_a_packs(disp_map.get(id_art, Decimal("0")), mc)
    return out


def buscar_articulos_filtrados_ternas(
    base_empresa: str,
    *,
    cod_viajante: int,
    id_cliente: int,
    id_cliente_domicilio: Optional[int] = None,
    q: str = "",
    lista_id: int = 1,
    id_deposito: int = 1,
    pagina: int = 1,
    tam: int = 20,
    iva_incluido: bool = True,
    descuento_cliente: Decimal = Decimal("0"),
    listar_todos: bool = False,
) -> Dict[str, Any]:
    """
    Autocomplete liviano para la matriz masiva.

    Solo artículos que el motor de precios/carrito puede resolver: Terminado,
    Discontinuo=No, ecommerce=Si y marcas de terna. Así no se ofrecen
    sugerencias que luego fallarían en preview/confirm con «no encontrado o inactivo».
    Incluye ``stock_disponible_packs`` (depósito Terminado MPR, bulk). Precios/reglas en lote.

    Con ``listar_todos=True`` (flecha abajo en UI) devuelve el catálogo filtrado
    completo sin exigir ``q`` (tope alto de seguridad).
    """
    marcas = marcas_asignadas_viajante_cliente(
        base_empresa, cod_viajante, id_cliente, id_cliente_domicilio
    )
    q = (q or "").strip()
    todos = bool(listar_todos)
    if todos:
        lim = max(1, min(int(tam or 5000), 5000))
    else:
        lim = max(1, min(int(tam or 20), 40))
    if not marcas:
        return {
            "items": [],
            "total": 0,
            "pagina": 1,
            "tam": lim,
            "total_paginas": 0,
            "marcas": [],
            "sin_marcas": True,
        }

    ctx_cli = leer_contexto_cliente_masivo(base_empresa, id_cliente)
    lista_ef = int(lista_id or ctx_cli.get("lista_id") or 1)
    desc_cli = _clamp_pct(descuento_cliente if descuento_cliente else ctx_cli.get("descRenglon"))

    # Paridad con obtener_articulo_row_precio / agregar_item (activo + ecommerce).
    where = [
        "articulo.Discontinuo = 'No'",
        "articulo.ecommerce = 'Si'",
        "COALESCE(TRIM(articulo.tipo_art_fab), '') = 'Terminado'",
    ]
    params: List[Any] = []
    placeholders = ",".join(["%s"] * len(marcas))
    where.append(f"articulo.CodigoMarca IN ({placeholders})")
    params.extend(marcas)

    if not todos and len(q) < 2:
        return {
            "items": [],
            "total": 0,
            "pagina": 1,
            "tam": lim,
            "total_paginas": 0,
            "marcas": marcas,
            "sin_marcas": False,
        }
    if q:
        like = f"%{q}%"
        where.append(
            "(articulo.id_manual LIKE %s OR articulo.NombreArticulo LIKE %s "
            "OR articulo.CodigoArticuloT LIKE %s OR CAST(articulo.IDArt AS CHAR) LIKE %s "
            "OR articulo.NroCodBarra = %s OR articulo.NroCodBarra LIKE %s)"
        )
        params.extend([like, like, like, like, q, like])

    select_cols = """
            articulo.IDArt,
            COALESCE(articulo.id_manual, '') AS id_manual,
            COALESCE(articulo.NombreArticulo, '') AS nombre,
            articulo.Precio1V,
            articulo.Precio2V,
            articulo.Precio3V,
            articulo.Precio4V,
            articulo.Precio5V,
            articulo.PNOficial,
            articulo.impuesto_interno,
            articulo.CodigoProveedor,
            articulo.CodigoRubro,
            articulo.IDSubRubro,
            articulo.promocion,
            articulo.promocion_por,
            articulo.promocion_cant,
            articulo.promocion_tipo,
            articulo.promocion_alcance,
            articulo.promocion_lista1,
            articulo.promocion_lista2,
            articulo.promocion_lista3,
            articulo.promocion_lista4,
            articulo.promocion_lista5,
            articulo.promocion_listaoficial,
            articulo.promocion_vigencia_desde,
            articulo.promocion_vigencia_hasta,
            articulo.multiplo_cantidad_vta,
            iva.Alicuota AS alic_iva
    """
    if q:
        sql = f"""
        SELECT {select_cols}
        FROM articulo
        LEFT JOIN iva ON iva.ID = articulo.Alicuota
        WHERE {' AND '.join(where)}
        ORDER BY
            CASE
                WHEN articulo.id_manual = %s THEN 0
                WHEN articulo.NroCodBarra = %s THEN 1
                WHEN articulo.id_manual LIKE %s THEN 2
                ELSE 3
            END,
            articulo.NombreArticulo
        LIMIT %s
        """
        q_exact = q
        q_prefix = f"{q}%"
        params_order = params + [q_exact, q_exact, q_prefix, lim]
    else:
        sql = f"""
        SELECT {select_cols}
        FROM articulo
        LEFT JOIN iva ON iva.ID = articulo.Alicuota
        WHERE {' AND '.join(where)}
        ORDER BY articulo.NombreArticulo
        LIMIT %s
        """
        params_order = params + [lim]

    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, params_order)
                cols = [d[0] for d in cursor.description] if cursor.description else []
                articulos = [dict(zip(cols, row)) for row in cursor.fetchall()]
                try:
                    reglas = resolver_reglas_precio_map(conn, articulos, id_cliente)
                except Exception:
                    logger.warning(
                        "buscar_articulos_filtrados_ternas: no se pudieron resolver reglas",
                        exc_info=True,
                    )
                    reglas = {}
                items = []
                for articulo in articulos:
                    id_art = int(articulo["IDArt"])
                    precio = calcular_precio_articulo_row(
                        articulo,
                        lista_id=lista_ef,
                        codigo_cliente=id_cliente,
                        descuento_cliente=desc_cli,
                        iva_incluido=False,
                        conn=conn,
                        regla_precio=reglas.get(id_art),
                        resolver_regla=False,
                    )
                    alic = to_decimal_or_none(articulo.get("alic_iva"))
                    mult_campos = campos_multiplo_articulo(
                        articulo.get("multiplo_cantidad_vta"),
                    )
                    items.append(
                        {
                            "id_articulo": id_art,
                            "id_manual": str_or_default(articulo.get("id_manual"), ""),
                            "codigo": str_or_default(articulo.get("id_manual"), ""),
                            "nombre": str_or_default(articulo.get("nombre"), ""),
                            "descripcion": str_or_default(articulo.get("nombre"), ""),
                            "precio_unitario_neto": float(precio or 0),
                            "precio_lista1": float(precio or 0),
                            "alicuota_iva": float(alic if alic is not None else 21),
                            **mult_campos,
                        }
                    )
                if items:
                    multiplos_inline = {
                        int(it["id_articulo"]): {
                            "multiplo_cantidad_vta": it.get("multiplo_cantidad_vta"),
                            "multiplo_empaque": it.get("multiplo_empaque"),
                        }
                        for it in items
                    }
                    stock_map = _stock_disponible_packs_map(
                        base_empresa,
                        [it["id_articulo"] for it in items],
                        multiplos_inline,
                    )
                    for it in items:
                        it["stock_disponible_packs"] = stock_map.get(
                            it["id_articulo"], 0.0
                        )
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("buscar_articulos_filtrados_ternas: %s", e)
        items = []

    return {
        "items": items,
        "total": len(items),
        "pagina": 1,
        "tam": lim,
        "total_paginas": 1 if items else 0,
        "marcas": marcas,
        "sin_marcas": False,
    }


def _nombres_articulos(
    base_empresa: str,
    ids: Sequence[int],
    *,
    id_cliente: int,
    lista_id: int = 1,
    descuento_cliente: Decimal = Decimal("0"),
) -> Dict[int, Dict[str, Any]]:
    ids_clean = [i for i in (to_int_or_none(x) for x in ids) if i is not None]
    if not ids_clean:
        return {}
    placeholders = ",".join(["%s"] * len(ids_clean))
    sql = f"""
        SELECT
            articulo.IDArt,
            COALESCE(articulo.id_manual, ''),
            COALESCE(articulo.NombreArticulo, ''),
            COALESCE(iva.Alicuota, 21) AS alic_iva,
            articulo.multiplo_cantidad_vta
        FROM articulo
        LEFT JOIN iva ON iva.ID = articulo.Alicuota
        WHERE articulo.IDArt IN ({placeholders})
    """
    out: Dict[int, Dict[str, Any]] = {}
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, list(ids_clean))
                for r in cursor.fetchall():
                    id_art = int(r[0])
                    precio = _precio_real_articulo(
                        base_empresa,
                        id_art,
                        lista_id=lista_id,
                        id_cliente=id_cliente,
                        descuento_cliente=descuento_cliente,
                    )
                    alic = to_decimal_or_none(r[3])
                    out[id_art] = {
                        "codigo": str_or_default(r[1], ""),
                        "descripcion": str_or_default(r[2], ""),
                        "precio_unitario_neto": float(precio or 0),
                        "precio_lista1": float(precio or 0),
                        "alicuota_iva": float(alic if alic is not None else 21),
                        **campos_multiplo_articulo(r[4]),
                    }
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("_nombres_articulos: %s", e)
    return out


def sincronizar_cod_viajante_borrador(
    draft: EcomPedidoMasivoDraft,
    cod_viajante: Optional[int],
    base_empresa: str,
) -> bool:
    """
    Actualiza ``draft.cod_viajante`` al viajante operativo y recorta celdas
    cuyo domicilio ya no está en el territorio VCM del nuevo vendedor.

    No toca borradores en solo lectura / confirmados / archivados.
    """
    cv = to_int_or_none(cod_viajante)
    if cv is None or not draft:
        return False
    estado = (draft.estado or "").strip().lower()
    if estado not in (
        EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
    ):
        return False
    actual = to_int_or_none(draft.cod_viajante)
    if actual == cv:
        return False
    draft.cod_viajante = cv
    draft.save(update_fields=["cod_viajante", "updated_at"])
    if not draft.celdas.exists():
        return True
    sucursales = listar_sucursales_cliente(
        base_empresa, draft.id_cliente, cod_viajante=cv
    )
    ids_ok = {
        to_int_or_none(s.get("id_cliente_domicilio"))
        for s in sucursales
        if to_int_or_none(s.get("id_cliente_domicilio")) is not None
    }
    qs = EcomPedidoMasivoDraftCelda.objects.filter(draft=draft)
    if not ids_ok:
        qs.delete()
    else:
        qs.exclude(id_cliente_domicilio__in=list(ids_ok)).delete()
    return True


def obtener_o_crear_draft(
    *,
    base_empresa: str,
    id_usuario: int,
    id_cliente: int,
    cod_viajante: Optional[int],
    draft_id: Optional[int] = None,
    modo: str = EcomPedidoMasivoDraft.MODO_MASIVO,
    id_domicilio_fijo: Optional[int] = None,
    cod_mov_origen: Optional[int] = None,
    solo_lectura: bool = False,
    consulta: bool = False,
) -> Tuple[Optional[EcomPedidoMasivoDraft], str]:
    """
    Si ``draft_id``: valida ownership y cliente.
    Si no: reutiliza borrador activo del mismo usuario+cliente+modo o crea uno nuevo.
    Con ``solo_lectura=True`` permite abrir drafts ``confirmado`` (matriz del resumen).
    """
    id_u = to_int_or_none(id_usuario)
    idc = to_int_or_none(id_cliente)
    if not base_empresa or id_u is None or idc is None:
        return None, "Parámetros inválidos."

    modo_ef = (modo or EcomPedidoMasivoDraft.MODO_MASIVO).strip().lower()
    if modo_ef not in (
        EcomPedidoMasivoDraft.MODO_MASIVO,
        EcomPedidoMasivoDraft.MODO_SIMPLE,
    ):
        modo_ef = EcomPedidoMasivoDraft.MODO_MASIVO
    id_dom_fijo = to_int_or_none(id_domicilio_fijo)
    cod_origen = to_int_or_none(cod_mov_origen)

    if draft_id is not None:
        d = EcomPedidoMasivoDraft.objects.filter(
            pk=draft_id,
            base_empresa=base_empresa,
            id_usuario=id_u,
        ).first()
        if not d:
            return None, "Borrador no encontrado."
        if d.estado == EcomPedidoMasivoDraft.ESTADO_ARCHIVADO:
            # Consulta de PED ya avanzado: el draft se archiva para no ensuciar el hub,
            # pero sigue siendo recuperable por id / cod_mov en solo lectura.
            if solo_lectura or to_int_or_none(d.cod_mov_origen) is not None:
                return d, ""
            return None, "El borrador está archivado."
        if d.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMADO:
            if solo_lectura:
                return d, ""
            return None, "El borrador ya fue confirmado."
        if d.estado == EcomPedidoMasivoDraft.ESTADO_ANULADO:
            reactivar_borrador_masivo(d)
        elif d.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO:
            d.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
            d.save(update_fields=["estado", "updated_at"])
        if not consulta and not solo_lectura:
            sincronizar_cod_viajante_borrador(d, cod_viajante, base_empresa)
        return d, ""

    if cod_origen is not None:
        estados_origen = (
            EcomPedidoMasivoDraft.ESTADO_BORRADOR,
            EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
        )
        if consulta:
            estados_origen = (
                EcomPedidoMasivoDraft.ESTADO_BORRADOR,
                EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
                EcomPedidoMasivoDraft.ESTADO_ARCHIVADO,
            )
        existente_origen = (
            EcomPedidoMasivoDraft.objects.filter(
                base_empresa=base_empresa,
                id_usuario=id_u,
                cod_mov_origen=cod_origen,
                modo=modo_ef,
                estado__in=estados_origen,
            )
            .order_by("-updated_at")
            .first()
        )
        if existente_origen:
            if (
                not consulta
                and existente_origen.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO
            ):
                existente_origen.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
                existente_origen.save(update_fields=["estado", "updated_at"])
            if not consulta and not solo_lectura:
                sincronizar_cod_viajante_borrador(
                    existente_origen, cod_viajante, base_empresa
                )
            return existente_origen, ""

    existente = (
        EcomPedidoMasivoDraft.objects.filter(
            base_empresa=base_empresa,
            id_usuario=id_u,
            id_cliente=idc,
            modo=modo_ef,
            estado__in=(
                EcomPedidoMasivoDraft.ESTADO_BORRADOR,
                EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
            ),
        )
        .order_by("-updated_at")
        .first()
    )
    if existente:
        if (
            modo_ef == EcomPedidoMasivoDraft.MODO_SIMPLE
            and id_dom_fijo is not None
            and existente.id_domicilio_fijo != id_dom_fijo
        ):
            # Un simple solo opera sobre un domicilio. Al cambiarlo desde el
            # selector, conservar sus cantidades y mover sus celdas a la nueva
            # columna antes de devolver el borrador reutilizado.
            with transaction.atomic():
                EcomPedidoMasivoDraftCelda.objects.filter(draft=existente).update(
                    id_cliente_domicilio=id_dom_fijo
                )
                existente.id_domicilio_fijo = id_dom_fijo
                existente.save(update_fields=["id_domicilio_fijo", "updated_at"])
        if existente.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO:
            existente.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
            existente.save(update_fields=["estado", "updated_at"])
        if not consulta and not solo_lectura:
            sincronizar_cod_viajante_borrador(existente, cod_viajante, base_empresa)
        return existente, ""

    estado_inicial = (
        EcomPedidoMasivoDraft.ESTADO_ARCHIVADO
        if consulta
        else EcomPedidoMasivoDraft.ESTADO_BORRADOR
    )
    d = EcomPedidoMasivoDraft.objects.create(
        base_empresa=base_empresa,
        id_usuario=id_u,
        id_cliente=idc,
        cod_viajante=to_int_or_none(cod_viajante),
        estado=estado_inicial,
        modo=modo_ef,
        id_domicilio_fijo=id_dom_fijo,
        cod_mov_origen=cod_origen,
        descuento_pie_pct=_clamp_pct(
            leer_contexto_cliente_masivo(base_empresa, idc).get("descPie")
        ),
        descuentos_fila={},
    )
    return d, ""


def _sucursal_fallback(id_dom: int) -> Dict[str, Any]:
    """Columna mínima cuando el domicilio ya no está en MySQL."""
    etiqueta = f"Sucursal #{int(id_dom)}"
    return {
        "id_cliente_domicilio": int(id_dom),
        "nombre": etiqueta,
        "etiqueta": etiqueta,
        "calle": "",
        "nro": "",
        "dpto": "",
        "provincia": "",
        "distrito": "",
        "zona": "",
    }


def serializar_matriz(
    draft: EcomPedidoMasivoDraft,
    base_empresa: str,
) -> Dict[str, Any]:
    celdas_qs = list(draft.celdas.all())
    doms_celdas = sorted(
        {
            i
            for i in (to_int_or_none(c.id_cliente_domicilio) for c in celdas_qs)
            if i is not None
        }
    )
    # Lote confirmado: columnas = domicilios históricos de las celdas (no VCM vigente).
    es_snapshot = (
        (draft.estado or "") == EcomPedidoMasivoDraft.ESTADO_CONFIRMADO
        and bool(doms_celdas)
    )
    if es_snapshot:
        sucursales = listar_sucursales_cliente(
            base_empresa,
            draft.id_cliente,
            ids_domicilio=doms_celdas,
            incluir_anulados=True,
        )
        presentes = {
            to_int_or_none(s.get("id_cliente_domicilio"))
            for s in sucursales
        }
        for idd in doms_celdas:
            if idd not in presentes:
                sucursales.append(_sucursal_fallback(idd))
        sucursales.sort(key=_clave_orden_nro_sucursal)
    else:
        sucursales = listar_sucursales_cliente(
            base_empresa, draft.id_cliente, cod_viajante=draft.cod_viajante
        )
    modo = (draft.modo or EcomPedidoMasivoDraft.MODO_MASIVO).strip().lower()
    id_dom_fijo = to_int_or_none(draft.id_domicilio_fijo)
    if modo == EcomPedidoMasivoDraft.MODO_SIMPLE and id_dom_fijo is not None:
        sucursales = [
            s for s in sucursales if int(s.get("id_cliente_domicilio") or 0) == id_dom_fijo
        ]
        if not sucursales:
            sucursales = [_sucursal_fallback(id_dom_fijo)]
    art_ids_set = {c.id_articulo for c in celdas_qs}
    ctx_cli = leer_contexto_cliente_masivo(base_empresa, draft.id_cliente)
    lista_id = int(ctx_cli.get("lista_id") or 1)
    desc_cli = _clamp_pct(ctx_cli.get("descRenglon"))
    desc_map = descuentos_fila_efectivos(draft, base_empresa)
    precio_map = precios_fila_efectivos(draft, base_empresa, lista_id=lista_id)
    nombres = _nombres_articulos(
        base_empresa,
        sorted(art_ids_set),
        id_cliente=draft.id_cliente,
        lista_id=lista_id,
        descuento_cliente=desc_cli,
    )
    art_ids = sorted(
        art_ids_set,
        key=lambda aid: _clave_orden_nombre_articulo(nombres, aid),
    )
    stock_packs = _stock_disponible_packs_map(base_empresa, art_ids, nombres)

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
            "id_manual": nombres.get(aid, {}).get("codigo", ""),
            "codigo": nombres.get(aid, {}).get("codigo", ""),
            "nombre": nombres.get(aid, {}).get("descripcion", f"Art. {aid}"),
            "descripcion": nombres.get(aid, {}).get("descripcion", f"Art. {aid}"),
            "precio_unitario_neto": float(
                precio_map.get(aid, nombres.get(aid, {}).get("precio_unitario_neto") or 0)
            ),
            "precio_lista": float(nombres.get(aid, {}).get("precio_unitario_neto") or 0),
            "precio_lista1": float(nombres.get(aid, {}).get("precio_lista1") or 0),
            "alicuota_iva": float(nombres.get(aid, {}).get("alicuota_iva") or 21),
            "porcentaje_descuento": float(desc_map.get(aid, desc_cli)),
            "multiplo_cantidad_vta": int(nombres.get(aid, {}).get("multiplo_cantidad_vta") or 0),
            "multiplo_empaque": int(
                nombres.get(aid, {}).get("multiplo_empaque")
                or multiplo_empaque_venta(
                    nombres.get(aid, {}).get("multiplo_cantidad_vta"),
                )
            ),
            "stock_disponible_packs": stock_packs.get(aid, 0.0),
        }
        for aid in art_ids
    ]

    descuentos_fila_out = {
        str(k): float(v) for k, v in desc_map.items()
    }

    return {
        "draft_id": draft.pk,
        "id_cliente": draft.id_cliente,
        "nombre_cliente": _nombre_cliente(base_empresa, draft.id_cliente),
        "cod_viajante": draft.cod_viajante,
        "estado": draft.estado,
        "modo": modo,
        "cod_mov_origen": draft.cod_mov_origen,
        "id_domicilio_fijo": id_dom_fijo,
        "ultimo_error": draft.ultimo_error or {},
        "codigos_movimiento": draft.codigos_movimiento or [],
        "desc_pie_pct": float(draft.descuento_pie_pct or 0),
        "descuentos_fila": descuentos_fila_out,
        "precios_fila": {str(k): float(v) for k, v in precio_map.items()},
        "lista_id": lista_id,
        "sucursales": sucursales,
        "articulos": articulos,
        "celdas": celdas_map,
        "updated_at": draft.updated_at.isoformat() if draft.updated_at else "",
    }


def eliminar_fila_articulo(
    draft: EcomPedidoMasivoDraft,
    *,
    id_articulo: int,
) -> Tuple[bool, str]:
    """Quita el artículo de la matriz: todas las celdas + descuento de fila."""
    if draft.estado not in (
        EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
    ):
        return False, "El borrador no es editable."
    if draft.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO:
        draft.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
        draft.save(update_fields=["estado", "updated_at"])

    aid = to_int_or_none(id_articulo)
    if aid is None:
        return False, "Artículo inválido."

    with transaction.atomic():
        EcomPedidoMasivoDraftCelda.objects.filter(
            draft=draft, id_articulo=aid
        ).delete()
        stored = dict(draft.descuentos_fila or {})
        stored.pop(str(aid), None)
        draft.descuentos_fila = stored
        precios = dict(draft.precios_fila or {})
        precios.pop(str(aid), None)
        draft.precios_fila = precios
        draft.save(update_fields=["descuentos_fila", "precios_fila", "updated_at"])
    return True, "Artículo quitado de la matriz."


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

    if qty > 0:
        multiplos = _multiplos_articulos(draft.base_empresa, [aid])
        info = multiplos.get(aid) or {}
        multiplo = int(info.get("multiplo_empaque") or 1)
        if not cantidad_respeta_multiplo(qty, multiplo):
            return (
                False,
                mensaje_multiplo_invalido(multiplo),
                {
                    "code": "multiplo_empaque",
                    "multiplo_empaque": multiplo,
                },
            )

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
        asegurar_descuento_fila_articulo(draft, aid, draft.base_empresa)
        asegurar_precio_fila_articulo(draft, aid, draft.base_empresa)
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


def _multiplos_articulos(
    base_empresa: str,
    ids: Sequence[int],
) -> Dict[int, Dict[str, Any]]:
    """Mapa id_articulo → campos de múltiplo de empaquetado."""
    ids_clean = [i for i in (to_int_or_none(x) for x in ids) if i is not None]
    if not ids_clean:
        return {}
    placeholders = ",".join(["%s"] * len(ids_clean))
    sql = f"""
        SELECT
            articulo.IDArt,
            articulo.multiplo_cantidad_vta
        FROM articulo
        WHERE articulo.IDArt IN ({placeholders})
    """
    out: Dict[int, Dict[str, Any]] = {}
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, list(ids_clean))
                for r in cursor.fetchall():
                    id_art = int(r[0])
                    out[id_art] = campos_multiplo_articulo(r[1])
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("_multiplos_articulos: %s", e)
    return out


def validar_multiplos_draft(
    draft: EcomPedidoMasivoDraft,
    base_empresa: str,
) -> Tuple[bool, str, List[Dict[str, Any]]]:
    """Rechaza confirmación si alguna celda con qty>0 viola el múltiplo de empaquetado."""
    celdas_qs = list(draft.celdas.all())
    art_ids = sorted(
        {
            int(c.id_articulo)
            for c in celdas_qs
            if (to_decimal_or_none(c.cantidad_packs) or Decimal("0")) > 0
        }
    )
    if not art_ids:
        return True, "", []
    multiplos = _multiplos_articulos(base_empresa, art_ids)
    nombres = _nombres_articulos(
        base_empresa,
        art_ids,
        id_cliente=draft.id_cliente,
    )
    infracciones = infracciones_multiplo_celdas(
        celdas_qs,
        multiplos,
        nombres=nombres,
    )
    if not infracciones:
        return True, "", []
    primera = infracciones[0]
    multiplo = int(primera.get("multiplo_empaque") or 1)
    msg = (
        f"Hay {len(infracciones)} cantidad(es) que no respetan la unidad de "
        f"empaquetado ({multiplo}). Corregí la matriz antes de confirmar."
    )
    return False, msg, infracciones


def cod_viajante_sesion(sess_user: Dict[str, Any]) -> Optional[int]:
    return resolver_viajante_operativo(sess_user)


def reactivar_borrador_masivo(draft: EcomPedidoMasivoDraft) -> Tuple[bool, str]:
    """Reactiva un borrador anulado (o confirmando) a estado editable."""
    if draft.estado == EcomPedidoMasivoDraft.ESTADO_ANULADO:
        draft.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
        draft.save(update_fields=["estado", "updated_at"])
        return True, "Borrador reactivado."
    if draft.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO:
        draft.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR
        draft.save(update_fields=["estado", "updated_at"])
        return True, "Borrador reactivado."
    if draft.estado == EcomPedidoMasivoDraft.ESTADO_BORRADOR:
        return True, "Borrador activo."
    return False, "El borrador no se puede reactivar."


def anular_borrador_masivo_usuario(
    draft_id: int,
    id_usuario: int,
    base_empresa: str,
) -> Tuple[bool, str]:
    """Anula un borrador masivo en edición (soft-delete recuperable vía hub)."""
    id_u = to_int_or_none(id_usuario)
    did = to_int_or_none(draft_id)
    if id_u is None or did is None or not base_empresa:
        return False, "Parámetros inválidos."
    draft = EcomPedidoMasivoDraft.objects.filter(
        pk=did,
        base_empresa=base_empresa,
        id_usuario=id_u,
    ).first()
    if not draft:
        return False, "Borrador no encontrado."
    if draft.estado not in (
        EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
    ):
        return False, "Solo se pueden anular borradores en edición."
    draft.estado = EcomPedidoMasivoDraft.ESTADO_ANULADO
    draft.save(update_fields=["estado", "updated_at"])
    return True, "Borrador anulado."
