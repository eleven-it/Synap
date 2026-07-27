"""
Servicio — Informe DABRA consolidado remitos.

Materializa filas línea×remito desde MySQL legacy (base_empresa de sesión),
valida totales Σ vs cabecera FA, alarmas y payload para preview/export.
"""

from __future__ import annotations

import calendar
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.utils.administranet_types import (
    str_or_default,
    to_date_or_none,
    to_decimal_or_none,
    to_int_or_none,
)
from reports.services.connection_pool import get_mysql_pool

logger = logging.getLogger(__name__)

CODIGO_CLIENTE_DABRA = 368
DOC_TYPE = 1

LETRA_POR_TIPO = {
    "FA": "A",
    "FB": "B",
    "FC": "C",
    "FE": "E",
    "FM": "M",
    "REM": "R",
}

_NRO_COMP_RE = re.compile(r"^0*(\d+)-0*(\d+)$")

COLUMNS_PREVIEW: List[Dict[str, str]] = [
    {"title": "Fecha", "data": "fecha"},
    {"title": "PuntoVenta", "data": "punto_venta"},
    {"title": "NumeroLegal", "data": "numero_legal"},
    {"title": "Item", "data": "item"},
    {"title": "NombreArticulo", "data": "nombre_articulo"},
    {"title": "Talle", "data": "talle"},
    {"title": "Cantidad", "data": "cantidad"},
    {"title": "Precio", "data": "precio_unitario"},
    {"title": "Bonificacion", "data": "bonificacion"},
    {"title": "ImporteBonificacion", "data": "importe_bonificacion"},
    {"title": "Importe", "data": "importe"},
    {"title": "Iva", "data": "importe_iva"},
    {"title": "TotalGravado", "data": "total_gravado"},
    {"title": "Total", "data": "total"},
    {"title": "CompRef", "data": "comp_ref"},
    {"title": "NumeroRef", "data": "numero_ref"},
    {"title": "NroCAE", "data": "cae"},
    {"title": "VtoCAE", "data": "vto_cae"},
    {"title": "Categoria", "data": "categoria"},
]


def parse_nro_comprobante(nro: Any) -> Tuple[Optional[int], Optional[int]]:
    """Parsea NroComprobante AdministraNET → (punto_venta, numero_legal)."""
    texto = str_or_default(nro, "").strip()
    if not texto:
        return None, None
    m = _NRO_COMP_RE.match(texto)
    if not m:
        return None, None
    return to_int_or_none(m.group(1)), to_int_or_none(m.group(2))


def format_punto_venta(punto_venta: Optional[int]) -> str:
    """Columna D: zero-pad 5."""
    pv = punto_venta if punto_venta is not None else 0
    return f"{pv:05d}"


def format_numero_legal_mask(numero_legal: Optional[int]) -> str:
    """String embebido TOTAL FACTURAS: máscara 8 dígitos."""
    nl = numero_legal if numero_legal is not None else 0
    return f"{nl:08d}"


def letra_por_tipo(tipo_comprobante: Any) -> str:
    """Letra fiscal por TipoComprobante (FA→A, REM→R, …)."""
    tipo = str_or_default(tipo_comprobante, "").strip().upper()
    return LETRA_POR_TIPO.get(tipo, tipo[:1] if tipo else "")


def format_comprobante_string(
    tipo_comprobante: Any,
    punto_venta: Optional[int],
    numero_legal: Optional[int],
    *,
    pv_width: int = 4,
) -> str:
    """String tipo sample: letra + PV(pad) + legal(8)."""
    letra = letra_por_tipo(tipo_comprobante)
    pv = punto_venta if punto_venta is not None else 0
    nl = numero_legal if numero_legal is not None else 0
    return f"{letra}{pv:0{pv_width}d}{nl:08d}"


def parse_cod_art_prov(cod_art_prov: Any) -> Tuple[str, str]:
    """
    CodArtProv → (item, talle).
    Regla: primeros 9 chars XXXXXX-XX + resto tras espacio; fallback split último espacio.
    """
    cod = str_or_default(cod_art_prov, "").strip()
    if not cod or cod == "-":
        return "", ""
    if len(cod) > 9 and cod[9:10] == " ":
        return cod[:9], cod[10:].strip()
    if " " in cod:
        prefijo, sufijo = cod.rsplit(" ", 1)
        return prefijo.strip(), sufijo.strip()
    return cod, ""


def bonificacion_linea(pordesc_bonif: Any, por_desc: Any) -> Decimal:
    """Bonif % = pordesc_bonif si ≠0 else PorDesc."""
    pb = to_decimal_or_none(pordesc_bonif) or Decimal("0")
    if pb != Decimal("0"):
        return pb
    return to_decimal_or_none(por_desc) or Decimal("0")


def calcular_tolerancia(n_lineas: int) -> Decimal:
    """Tolerancia Σ: max(0.05, 0.01×n_lineas)."""
    n = max(n_lineas, 0)
    return max(Decimal("0.05"), Decimal("0.01") * Decimal(n))


def resolver_categoria(nombre_categoria: Any) -> str:
    """Categoría desde articulo_categoria o ACCESORIOS (upper)."""
    nombre = str_or_default(nombre_categoria, "").strip()
    if not nombre or nombre.lower().startswith("rubro"):
        return "ACCESORIOS"
    return nombre.upper()


def normalizar_cuit(cuit_raw: Any) -> str:
    """CUIT emisor: 11 dígitos sin guiones."""
    digits = re.sub(r"\D", "", str_or_default(cuit_raw, ""))
    return digits[:11] if digits else ""


def _dec(value: Any) -> Decimal:
    d = to_decimal_or_none(value)
    return d if d is not None else Decimal("0")


def _fmt_fecha(value: Any) -> str:
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    iso = to_date_or_none(value)
    if iso:
        try:
            return datetime.strptime(iso, "%Y-%m-%d").strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            pass
    return str_or_default(value, "")


def _rango_mes(mes: int, anio: int) -> Tuple[str, str]:
    ultimo = calendar.monthrange(anio, mes)[1]
    return f"{anio:04d}-{mes:02d}-01", f"{anio:04d}-{mes:02d}-{ultimo:02d}"


def validar_totales_fa(
    lineas: Sequence[Dict[str, Any]],
    subtotal1: Any,
    importe_venta: Any,
) -> List[str]:
    """Valida Σ neto/bruto vs cabecera; devuelve mensajes de error en español."""
    errores: List[str] = []
    if not lineas:
        return errores
    sum_neto = Decimal("0")
    sum_bruto = Decimal("0")
    for ln in lineas:
        cant = _dec(ln.get("cantidad"))
        neto_u = _dec(ln.get("precio_netox_u"))
        iva_u = _dec(ln.get("precio_ivax_u"))
        sum_neto += cant * neto_u
        sum_bruto += cant * (neto_u + iva_u)
    cab_neto = _dec(subtotal1)
    cab_bruto = _dec(importe_venta)
    tol = calcular_tolerancia(len(lineas))
    if abs(sum_neto - cab_neto) > tol:
        errores.append(
            f"FA {lineas[0].get('codigo_movimiento')}: Σ neto líneas ({sum_neto}) "
            f"≠ SubTotal1 ({cab_neto}); tolerancia {tol}."
        )
    if abs(sum_bruto - cab_bruto) > tol:
        errores.append(
            f"FA {lineas[0].get('codigo_movimiento')}: Σ bruto líneas ({sum_bruto}) "
            f"≠ ImporteVenta ({cab_bruto}); tolerancia {tol}."
        )
    return errores


def _sql_lineas_fa() -> str:
    return """
        SELECT
            cc.CodigoMovimiento AS codigo_movimiento_fa,
            cc.NroComprobante AS fa_nro_comprobante,
            cc.TipoComprobante AS fa_tipo,
            cc.Fecha AS fa_fecha,
            cc.fe_cae,
            cc.fe_vto_cae,
            cc.SubTotal1,
            cc.ImporteVenta,
            s.id_stock,
            s.Cantidad,
            s.PrecioVentaxU,
            s.PrecioNetoxU,
            s.PrecioIVAxU,
            s.pordesc_bonif,
            s.PorDesc,
            s.imp_alicuota_iva,
            COALESCE(NULLIF(TRIM(a.NombreArticulo), ''), NULLIF(TRIM(s.Descripcion), ''), '') AS NombreArticulo,
            a.CodArtProv,
            ac.nombre_articulo_categoria AS categoria_nombre
        FROM cuentacliente cc
        INNER JOIN stock s ON s.CodigoMovimiento = cc.CodigoMovimiento
        LEFT JOIN articulo a ON a.IDArt = s.IDArt
        LEFT JOIN articulo_categoria ac ON ac.id_articulo_categoria = a.id_articulo_categoria
            AND (ac.anulado IS NULL OR ac.anulado = 'No')
        WHERE cc.Codigo = %s
          AND cc.TipoComprobante = 'FA'
          AND cc.Anulado = 'No'
          AND cc.Fecha BETWEEN %s AND %s
        ORDER BY cc.Fecha, cc.CodigoMovimiento, s.id_stock
    """


def _sql_remitos_por_fa(n: int) -> str:
    ph = ", ".join(["%s"] * n)
    return f"""
        SELECT
            rf.CodigoMovimientoF,
            rf.CodigoMovimientoR,
            rem.NroComprobante AS rem_nro,
            rem.TipoComprobante AS rem_tipo,
            rem.Fecha AS rem_fecha,
            cd.NroCalle
        FROM rem_fact rf
        INNER JOIN cuentacliente rem ON rem.CodigoMovimiento = rf.CodigoMovimientoR
            AND rem.Anulado = 'No'
        LEFT JOIN cliente_datos_adicionales cda ON cda.CodigoMovimiento = rf.CodigoMovimientoR
        LEFT JOIN cliente_domicilio cd ON cd.id_cliente_domicilio = cda.id_cliente_domicilio
        WHERE rf.Anulado = 'No'
          AND rf.CodigoMovimientoF IN ({ph})
        ORDER BY rf.CodigoMovimientoF, rf.id_rem_fact
    """


def _sql_domicilio_fa(n: int) -> str:
    ph = ", ".join(["%s"] * n)
    return f"""
        SELECT cc.CodigoMovimiento, cd.NroCalle
        FROM cuentacliente cc
        LEFT JOIN cliente_datos_adicionales cda ON cda.CodigoMovimiento = cc.CodigoMovimiento
        LEFT JOIN cliente_domicilio cd ON cd.id_cliente_domicilio = cda.id_cliente_domicilio
        WHERE cc.CodigoMovimiento IN ({ph})
    """


def _fetch_rows(cursor, sql: str, params: Sequence[Any]) -> List[Dict[str, Any]]:
    cursor.execute(sql, params)
    rows = cursor.fetchall()
    cols = [d[0] for d in cursor.description] if cursor.description else []
    return [dict(zip(cols, row)) for row in rows]


def _materializar_fila_export(
    *,
    cuit_emisor: str,
    fa: Dict[str, Any],
    linea: Dict[str, Any],
    remito: Optional[Dict[str, Any]],
    entrega: str,
) -> Dict[str, Any]:
    pv_fa, nl_fa = parse_nro_comprobante(fa.get("fa_nro_comprobante"))
    bonif = bonificacion_linea(linea.get("pordesc_bonif"), linea.get("PorDesc"))
    cant = _dec(linea.get("Cantidad"))
    precio_venta_u = _dec(linea.get("PrecioVentaxU"))
    precio_neto_u = _dec(linea.get("PrecioNetoxU"))
    precio_iva_u = _dec(linea.get("PrecioIVAxU"))
    importe = cant * precio_neto_u
    importe_iva = cant * precio_iva_u
    importe_bonif_u = precio_venta_u * bonif / Decimal("100")

    comp_ref = ""
    numero_ref: Any = ""
    nro_remito_str = ""
    if remito:
        pv_rem, nl_rem = parse_nro_comprobante(remito.get("rem_nro"))
        comp_ref = format_punto_venta(pv_rem)
        numero_ref = nl_rem if nl_rem is not None else ""
        nro_remito_str = format_comprobante_string(
            remito.get("rem_tipo") or "REM",
            pv_rem,
            nl_rem,
        )

    item, talle = parse_cod_art_prov(linea.get("CodArtProv"))
    cae = str_or_default(fa.get("fe_cae"), "").strip()

    return {
        "codigo_movimiento": to_int_or_none(fa.get("codigo_movimiento_fa")),
        "punto_venta": format_punto_venta(pv_fa),
        "numero_legal": nl_fa if nl_fa is not None else 0,
        "comprobante": format_comprobante_string(fa.get("fa_tipo"), pv_fa, nl_fa),
        "fecha": _fmt_fecha(fa.get("fa_fecha")),
        "cae": cae,
        "vto_cae": _fmt_fecha(fa.get("fe_vto_cae")) if cae else "",
        "cuit_emisor": cuit_emisor,
        "doc_type": DOC_TYPE,
        "comp_ref": comp_ref,
        "numero_ref": numero_ref,
        "nro_remito": nro_remito_str,
        "entrega": entrega,
        "suc": entrega,
        "item": item,
        "talle": talle,
        "categoria": resolver_categoria(linea.get("categoria_nombre")),
        "nombre_articulo": str_or_default(linea.get("NombreArticulo"), ""),
        "cantidad": float(cant),
        "precio_unitario": float(precio_venta_u),
        "bonificacion": float(bonif),
        "alicuota_iva": float(_dec(linea.get("imp_alicuota_iva"))),
        "importe_bonificacion": float(importe_bonif_u),
        "importe": float(importe),
        "importe_iva": float(importe_iva),
        "total_gravado": float(_dec(fa.get("SubTotal1"))),
        "total": float(_dec(fa.get("ImporteVenta"))),
    }


def get_dabra_consolidado_remitos(
    base_empresa: str,
    *,
    mes: int,
    anio: int,
) -> Dict[str, Any]:
    """
    Payload único para preview y export.

    Returns: columns, filas, totales_facturas, alarmas, errores, meta.
    """
    if mes < 1 or mes > 12:
        raise ValueError("Mes inválido (debe ser 1–12).")
    if anio < 1900 or anio > 2100:
        raise ValueError("Año inválido.")

    fecha_desde, fecha_hasta = _rango_mes(mes, anio)
    pool = get_mysql_pool()

    with pool.get_connection(base_empresa) as conn:
        cursor = conn.cursor()
        lineas_raw = _fetch_rows(
            cursor,
            _sql_lineas_fa(),
            (CODIGO_CLIENTE_DABRA, fecha_desde, fecha_hasta),
        )
        cuit_rows = _fetch_rows(cursor, "SELECT CUIT FROM datosempresa LIMIT 1", ())
        cuit_emisor = normalizar_cuit(cuit_rows[0].get("CUIT") if cuit_rows else "")

    # Agrupar por FA
    fa_map: Dict[Any, Dict[str, Any]] = {}
    lineas_por_fa: Dict[Any, List[Dict[str, Any]]] = {}
    for row in lineas_raw:
        cod_fa = row.get("codigo_movimiento_fa")
        if cod_fa not in fa_map:
            fa_map[cod_fa] = {
                "codigo_movimiento_fa": cod_fa,
                "fa_nro_comprobante": row.get("fa_nro_comprobante"),
                "fa_tipo": row.get("fa_tipo"),
                "fa_fecha": row.get("fa_fecha"),
                "fe_cae": row.get("fe_cae"),
                "fe_vto_cae": row.get("fe_vto_cae"),
                "SubTotal1": row.get("SubTotal1"),
                "ImporteVenta": row.get("ImporteVenta"),
            }
        lineas_por_fa.setdefault(cod_fa, []).append(row)

    codigos_fa = list(fa_map.keys())
    remitos_por_fa: Dict[Any, List[Dict[str, Any]]] = {c: [] for c in codigos_fa}
    domicilio_fa: Dict[Any, str] = {}

    if codigos_fa:
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()
            rem_rows = _fetch_rows(cursor, _sql_remitos_por_fa(len(codigos_fa)), codigos_fa)
            for rem in rem_rows:
                remitos_por_fa.setdefault(rem.get("CodigoMovimientoF"), []).append(rem)
            dom_rows = _fetch_rows(cursor, _sql_domicilio_fa(len(codigos_fa)), codigos_fa)
            for dom in dom_rows:
                nc = str_or_default(dom.get("NroCalle"), "").strip()
                if nc:
                    domicilio_fa[dom.get("CodigoMovimiento")] = nc

    alarmas: List[str] = []
    errores: List[str] = []
    filas: List[Dict[str, Any]] = []
    totales_facturas: List[Dict[str, Any]] = []

    for cod_fa, fa in fa_map.items():
        raw_lineas = lineas_por_fa.get(cod_fa, [])
        # Validación Σ pre-expansión (líneas únicas)
        lineas_val = [
            {
                "codigo_movimiento": cod_fa,
                "cantidad": ln.get("Cantidad"),
                "precio_netox_u": ln.get("PrecioNetoxU"),
                "precio_ivax_u": ln.get("PrecioIVAxU"),
            }
            for ln in raw_lineas
        ]
        errores.extend(
            validar_totales_fa(lineas_val, fa.get("SubTotal1"), fa.get("ImporteVenta"))
        )

        cae = str_or_default(fa.get("fe_cae"), "").strip()
        if not cae:
            alarmas.append(
                f"FA {cod_fa} ({fa.get('fa_nro_comprobante')}): sin CAE; se incluye con CAE vacío."
            )

        remitos = remitos_por_fa.get(cod_fa, [])
        if not remitos:
            alarmas.append(
                f"FA {cod_fa} ({fa.get('fa_nro_comprobante')}): sin remitos vinculados; "
                "CompRef/NumeroRef vacíos."
            )
        elif len(remitos) > 1:
            alarmas.append(
                f"FA {cod_fa} ({fa.get('fa_nro_comprobante')}): {len(remitos)} remitos; "
                "TOTAL FACTURAS usa el primero."
            )

        fallback_entrega = domicilio_fa.get(cod_fa, "")
        bloques_remito: List[Optional[Dict[str, Any]]]
        if remitos:
            bloques_remito = remitos
        else:
            bloques_remito = [None]

        for ln in raw_lineas:
            for rem in bloques_remito:
                if rem:
                    entrega = str_or_default(rem.get("NroCalle"), "").strip()
                    if not entrega:
                        entrega = fallback_entrega
                        if not entrega:
                            alarmas.append(
                                f"Remito {rem.get('CodigoMovimientoR')}: sin NroCalle; "
                                "Entrega/Suc vacíos."
                            )
                else:
                    entrega = fallback_entrega
                    if not entrega and raw_lineas:
                        alarmas.append(
                            f"FA {cod_fa}: sin remito ni domicilio FA; Entrega/Suc vacíos."
                        )
                filas.append(
                    _materializar_fila_export(
                        cuit_emisor=cuit_emisor,
                        fa=fa,
                        linea=ln,
                        remito=rem,
                        entrega=entrega,
                    )
                )

        pv_fa, nl_fa = parse_nro_comprobante(fa.get("fa_nro_comprobante"))
        primer_remito = remitos[0] if remitos else None
        nro_remito_total = ""
        if primer_remito:
            pv_rem, nl_rem = parse_nro_comprobante(primer_remito.get("rem_nro"))
            nro_remito_total = format_comprobante_string(
                primer_remito.get("rem_tipo") or "REM",
                pv_rem,
                nl_rem,
            )
        totales_facturas.append(
            {
                "fecha": _fmt_fecha(fa.get("fa_fecha")),
                "comprobante": format_comprobante_string(fa.get("fa_tipo"), pv_fa, nl_fa),
                "nro_remito": nro_remito_total,
                "imp_neto": float(_dec(fa.get("SubTotal1"))),
                "imp_bruto": float(_dec(fa.get("ImporteVenta"))),
            }
        )

    # Deduplicar alarmas preservando orden
    alarmas_unicas = list(dict.fromkeys(alarmas))

    return {
        "columns": COLUMNS_PREVIEW,
        "filas": filas,
        "totales_facturas": totales_facturas,
        "alarmas": alarmas_unicas,
        "errores": errores,
        "meta": {
            "mes": mes,
            "anio": anio,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "codigo_cliente": CODIGO_CLIENTE_DABRA,
            "base_empresa": base_empresa,
            "cuit_emisor": cuit_emisor,
        },
    }
