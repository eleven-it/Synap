"""Importación Excel de pedido masivo (matriz artículo × sucursal).

Formato plantilla v2: hoja ``Pedido`` con fila 1 oculta (A1 marker, B1 id_cliente,
C+ = id_cliente_domicilio), fila 2 = rótulos y datos desde fila 3.
Columna A = SuperArt (id_manual), B = nombre, C+ = packs. Sin precios.
Hoja oculta ``_Synap`` identifica cliente y vendedor.

Modo: **reemplazo total** del borrador (se vacían celdas y queda solo el Excel).
Validación de territorio: cuaterna VCM vendedor → cliente → sucursal → marca.
"""

from __future__ import annotations

import io
import logging
import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from django.db import transaction
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill, Protection
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from core.mysql_pool import get_mysql_pool
from core.utils.administranet_types import str_or_default, to_decimal_or_none, to_int_or_none
from ecom.models import EcomPedidoMasivoDraft, EcomPedidoMasivoDraftCelda
from ecom.services.multiplo_empaque import (
    cantidad_respeta_multiplo,
    mensaje_multiplo_invalido,
    multiplo_empaque_venta,
)
from ecom.services.pedido_masivo_matriz import (
    _clamp_pct,
    _clave_orden_nro_sucursal,
    _nombre_cliente,
    asegurar_descuento_fila_articulo,
    leer_contexto_cliente_masivo,
    listar_sucursales_cliente,
    marcas_asignadas_viajante_cliente,
)

logger = logging.getLogger(__name__)

HOJA_PEDIDO = "Pedido"
HOJA_SUCURSALES = "Sucursales"
HOJA_INSTRUCCIONES = "Instrucciones"
HOJA_META = "_Synap"
MARKER_CODIGO = "codigo_articulo"
PLANTILLA_VERSION = 2
MAX_BYTES = 8 * 1024 * 1024
MAX_ERRORES = 200
MAX_ARTICULOS_PLANTILLA = 5000  # red de seguridad; administranet prod 13/08/2026: 310 ecommerce Terminado

_FILL_ID = PatternFill("solid", fgColor="E2E8F0")
_FILL_HDR = PatternFill("solid", fgColor="0F172A")
_FILL_LOCK = PatternFill("solid", fgColor="F1F5F9")
_FILL_QTY = PatternFill("solid", fgColor="FFFBEB")
_FONT_HDR = Font(color="FFFFFF", bold=True, size=10)
_FONT_ID = Font(color="64748B", size=8)
_PROT_LOCK = Protection(locked=True)
_PROT_UNLOCK = Protection(locked=False)


def _err(
    mensaje: str,
    *,
    code: str,
    fila: Optional[int] = None,
    columna: Optional[str] = None,
    codigo_articulo: str = "",
    sucursal: str = "",
) -> Dict[str, Any]:
    return {
        "fila": fila,
        "columna": columna or "",
        "codigo_articulo": codigo_articulo or "",
        "sucursal": sucursal or "",
        "mensaje": mensaje,
        "code": code,
    }


def _celda_str(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, float) and val == int(val):
        return str(int(val))
    return str(val).strip()


def _qty_celda(val: Any) -> Tuple[Optional[Decimal], Optional[str]]:
    """Vacío → (None, None). Inválido → (None, mensaje)."""
    if val is None or val == "":
        return None, None
    if isinstance(val, str) and not val.strip():
        return None, None
    if isinstance(val, str):
        val = val.strip().replace(" ", "").replace(",", ".")
    qty = to_decimal_or_none(val)
    if qty is None:
        return None, "Cantidad inválida."
    if qty < 0:
        return None, "La cantidad no puede ser negativa."
    if qty == 0:
        return None, None
    return qty, None


def consultar_articulos_por_codigos(
    base_empresa: str, codigos: Sequence[str]
) -> Dict[str, List[Dict[str, Any]]]:
    """Resuelve códigos Excel → candidatos de ``articulo`` (exacto)."""
    out: Dict[str, List[Dict[str, Any]]] = {}
    unicos = []
    seen: Set[str] = set()
    for c in codigos:
        k = (c or "").strip()
        if not k or k in seen:
            continue
        seen.add(k)
        unicos.append(k)
    if not unicos:
        return out
    sql = """
        SELECT
            articulo.IDArt,
            COALESCE(articulo.id_manual, '') AS id_manual,
            COALESCE(articulo.NombreArticulo, '') AS nombre,
            articulo.CodigoMarca,
            COALESCE(articulo.CodArtProv, '') AS cod_art_prov,
            COALESCE(articulo.CodigoArticuloT, '') AS codigo_t,
            COALESCE(articulo.Discontinuo, 'No') AS discontinuo,
            COALESCE(articulo.ecommerce, 'No') AS ecommerce,
            COALESCE(TRIM(articulo.tipo_art_fab), '') AS tipo_art_fab,
            articulo.multiplo_cantidad_vta
        FROM articulo
        WHERE articulo.id_manual = %s
           OR CAST(articulo.IDArt AS CHAR) = %s
           OR articulo.CodigoArticuloT = %s
           OR articulo.NroCodBarra = %s
           OR articulo.NroCodBarraF = %s
           OR articulo.CodArtProv = %s
        LIMIT 8
    """
    try:
        pool = get_mysql_pool()
        with pool.get_connection(base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                for codigo in unicos:
                    cursor.execute(sql, [codigo] * 6)
                    cols = [d[0] for d in cursor.description] if cursor.description else []
                    rows = [dict(zip(cols, r)) for r in cursor.fetchall()]
                    seen_ids: Set[int] = set()
                    arts: List[Dict[str, Any]] = []
                    for row in rows:
                        aid = to_int_or_none(row.get("IDArt"))
                        if aid is None or aid in seen_ids:
                            continue
                        seen_ids.add(aid)
                        arts.append(
                            {
                                "id_articulo": aid,
                                "id_manual": str_or_default(row.get("id_manual"), ""),
                                "nombre": str_or_default(row.get("nombre"), ""),
                                "codigo_marca": to_int_or_none(row.get("CodigoMarca")),
                                "cod_art_prov": str_or_default(row.get("cod_art_prov"), ""),
                                "codigo_t": str_or_default(row.get("codigo_t"), ""),
                                "discontinuo": str_or_default(row.get("discontinuo"), "No"),
                                "ecommerce": str_or_default(row.get("ecommerce"), "No"),
                                "tipo_art_fab": str_or_default(row.get("tipo_art_fab"), ""),
                                "multiplo_cantidad_vta": row.get("multiplo_cantidad_vta"),
                            }
                        )
                    out[codigo] = arts
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("consultar_articulos_por_codigos: %s", e)
        for codigo in unicos:
            out.setdefault(codigo, [])
    return out


def _territorio(
    draft: EcomPedidoMasivoDraft,
) -> Tuple[List[Dict[str, Any]], Dict[int, Set[int]]]:
    sucursales = listar_sucursales_cliente(
        draft.base_empresa,
        draft.id_cliente,
        draft.cod_viajante,
    )
    sucursales = sorted(sucursales, key=_clave_orden_nro_sucursal)
    if draft.modo == EcomPedidoMasivoDraft.MODO_SIMPLE:
        fijo = to_int_or_none(draft.id_domicilio_fijo)
        if fijo:
            sucursales = [
                s
                for s in sucursales
                if to_int_or_none(s.get("id_cliente_domicilio")) == fijo
            ]
    marcas_map: Dict[int, Set[int]] = {}
    cv = to_int_or_none(draft.cod_viajante)
    for s in sucursales:
        idd = to_int_or_none(s.get("id_cliente_domicilio"))
        if idd is None:
            continue
        if cv is None:
            marcas_map[idd] = set()
            continue
        marcas_map[idd] = set(
            marcas_asignadas_viajante_cliente(
                draft.base_empresa,
                cv,
                draft.id_cliente,
                id_cliente_domicilio=idd,
            )
        )
    return sucursales, marcas_map


def listar_articulos_plantilla_vcm(draft: EcomPedidoMasivoDraft) -> List[Dict[str, Any]]:
    """Artículos Terminado/ecommerce de la unión de marcas VCM (sin precio ni stock)."""
    _sucursales, marcas_map = _territorio(draft)
    marcas: Set[int] = set()
    for ms in marcas_map.values():
        marcas.update(ms)
    marcas_l = sorted(m for m in marcas if m is not None)
    if not marcas_l:
        return []
    ph = ",".join(["%s"] * len(marcas_l))
    sql = f"""
        SELECT
            articulo.IDArt,
            COALESCE(articulo.id_manual, '') AS id_manual,
            COALESCE(articulo.NombreArticulo, '') AS nombre
        FROM articulo
        WHERE articulo.Discontinuo = 'No'
          AND articulo.ecommerce = 'Si'
          AND COALESCE(TRIM(articulo.tipo_art_fab), '') = 'Terminado'
          AND articulo.CodigoMarca IN ({ph})
        ORDER BY
            CASE WHEN articulo.id_manual IS NULL OR articulo.id_manual = '' THEN 1 ELSE 0 END,
            articulo.id_manual,
            articulo.NombreArticulo
        LIMIT %s
    """
    out: List[Dict[str, Any]] = []
    seen_id: Set[int] = set()
    seen_code: Set[str] = set()
    try:
        pool = get_mysql_pool()
        with pool.get_connection(draft.base_empresa.strip()) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql, [*marcas_l, MAX_ARTICULOS_PLANTILLA])
                for row in cursor.fetchall():
                    aid = to_int_or_none(row[0])
                    if aid is None or aid in seen_id:
                        continue
                    codigo = str_or_default(row[1], "") or str(aid)
                    key = codigo.strip().lower()
                    if not key or key in seen_code:
                        continue
                    seen_id.add(aid)
                    seen_code.add(key)
                    out.append(
                        {
                            "id_articulo": aid,
                            "id_manual": codigo,
                            "nombre": str_or_default(row[2], ""),
                        }
                    )
            finally:
                cursor.close()
    except Exception as e:
        logger.warning("listar_articulos_plantilla_vcm: %s", e)
        return []
    return out


def _etiqueta_suc(s: Dict[str, Any]) -> str:
    return str_or_default(s.get("etiqueta") or s.get("nombre") or s.get("calle"), "")


def generar_plantilla_excel(
    draft: EcomPedidoMasivoDraft,
    *,
    articulos: Optional[Sequence[Dict[str, Any]]] = None,
) -> bytes:
    """Plantilla VCM: SuperArt + nombre + cantidades. Sin precios. Identifica al cliente."""
    sucursales, _marcas = _territorio(draft)
    if articulos is None:
        articulos = listar_articulos_plantilla_vcm(draft)
    nombre_cli = _nombre_cliente(draft.base_empresa, draft.id_cliente)
    id_cli = to_int_or_none(draft.id_cliente) or 0
    cv = to_int_or_none(draft.cod_viajante)

    qty_map: Dict[Tuple[int, int], Decimal] = {}
    for cel in draft.celdas.all():
        aid = to_int_or_none(cel.id_articulo)
        idd = to_int_or_none(cel.id_cliente_domicilio)
        if aid is None or idd is None:
            continue
        qty_map[(aid, idd)] = cel.cantidad_packs

    wb = Workbook()

    ws_i = wb.active
    ws_i.title = HOJA_INSTRUCCIONES
    instrucciones = [
        "Plantilla de pedido masivo Synap — solo completá cantidades (packs).",
        "No agregues columnas, ni precios, ni descuentos: eso sale del cliente.",
        "",
        f"Cliente: {id_cli} — {nombre_cli or '—'}",
        f"Vendedor: {cv if cv is not None else '—'}",
        f"Borrador: #{draft.pk}",
        "",
        "Al importar se reemplaza todo el borrador. Usá la plantilla de este mismo pedido.",
    ]
    for i, texto in enumerate(instrucciones, start=1):
        ws_i.cell(i, 1, texto)
    ws_i.column_dimensions["A"].width = 110
    ws_i.sheet_state = "hidden"

    ws_s = wb.create_sheet(HOJA_SUCURSALES)
    ws_s.append(["id_cliente_domicilio", "nro", "calle", "etiqueta"])
    for col in range(1, 5):
        c = ws_s.cell(1, col)
        c.fill = _FILL_HDR
        c.font = _FONT_HDR
    for s in sucursales:
        ws_s.append(
            [
                int(s["id_cliente_domicilio"]),
                str_or_default(s.get("nro"), ""),
                str_or_default(s.get("calle"), ""),
                _etiqueta_suc(s),
            ]
        )
    for col, w in enumerate((22, 14, 55, 55), start=1):
        ws_s.column_dimensions[get_column_letter(col)].width = w
    ws_s.sheet_state = "hidden"

    ws_m = wb.create_sheet(HOJA_META)
    ws_m.append(["id_cliente", id_cli])
    ws_m.append(["nombre_cliente", nombre_cli])
    ws_m.append(["cod_viajante", cv if cv is not None else ""])
    ws_m.append(["draft_id", draft.pk or 0])
    ws_m.append(["plantilla_version", PLANTILLA_VERSION])
    ws_m.sheet_state = "veryHidden"

    ws = wb.create_sheet(HOJA_PEDIDO, 0)
    n_suc = len(sucursales)
    last_col = 2 + max(n_suc, 1)
    ws.cell(1, 1, MARKER_CODIGO)
    ws.cell(1, 2, id_cli)
    ws.cell(2, 1, "Código")
    ws.cell(2, 2, "Artículo")
    for idx, s in enumerate(sucursales):
        col = 3 + idx
        ws.cell(1, col, int(s["id_cliente_domicilio"]))
        ws.cell(2, col, _etiqueta_suc(s) or f"Suc {s.get('nro') or s['id_cliente_domicilio']}")
    for col in range(1, last_col + 1):
        c1 = ws.cell(1, col)
        c1.fill = _FILL_ID
        c1.font = _FONT_ID
        c1.protection = _PROT_LOCK
        c2 = ws.cell(2, col)
        c2.fill = _FILL_HDR
        c2.font = _FONT_HDR
        c2.alignment = Alignment(wrap_text=True, horizontal="center", vertical="center")
        c2.protection = _PROT_LOCK

    for ridx, art in enumerate(articulos):
        fila = 3 + ridx
        aid = int(art["id_articulo"])
        codigo = str_or_default(art.get("id_manual"), "") or str(aid)
        ca = ws.cell(fila, 1, codigo)
        ca.fill = _FILL_LOCK
        ca.protection = _PROT_LOCK
        cn = ws.cell(fila, 2, str_or_default(art.get("nombre"), ""))
        cn.fill = _FILL_LOCK
        cn.protection = _PROT_LOCK
        for idx, s in enumerate(sucursales):
            col = 3 + idx
            idd = to_int_or_none(s.get("id_cliente_domicilio"))
            qty = qty_map.get((aid, idd)) if idd is not None else None
            cell = ws.cell(fila, col, qty if qty is not None else None)
            cell.fill = _FILL_QTY
            cell.protection = _PROT_UNLOCK
            cell.alignment = Alignment(horizontal="center")
            cell.number_format = "0"

    n_arts = len(articulos)
    last_row = 2 + max(n_arts, 1)
    if n_arts == 0:
        for idx in range(n_suc):
            cell = ws.cell(3, 3 + idx)
            cell.fill = _FILL_QTY
            cell.protection = _PROT_UNLOCK

    ws.row_dimensions[1].hidden = True
    ws.row_dimensions[2].height = 36
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 42
    for idx in range(n_suc):
        ws.column_dimensions[get_column_letter(3 + idx)].width = 14
    ws.freeze_panes = "C3"
    ws.sheet_view.showGridLines = True
    if n_suc:
        ws.auto_filter.ref = f"A2:{get_column_letter(2 + n_suc)}{last_row}"
        dv = DataValidation(
            type="decimal",
            operator="greaterThanOrEqual",
            formula1="0",
            allow_blank=True,
            showErrorMessage=True,
            errorTitle="Cantidad",
            error="Solo números mayores o iguales a 0 (packs).",
        )
        dv.add(f"C3:{get_column_letter(2 + n_suc)}{max(last_row, 3)}")
        ws.add_data_validation(dv)
    ws.protection.sheet = True
    ws.protection.enable()
    ws.protection.autoFilter = True
    ws.protection.sort = True
    ws.protection.selectLockedCells = True
    ws.protection.selectUnlockedCells = True

    bio = io.BytesIO()
    wb.save(bio)
    return bio.getvalue()


def _leer_workbook_import(raw: bytes) -> Tuple[List[Tuple[Any, ...]], Dict[str, Any]]:
    if len(raw) > MAX_BYTES:
        raise ValueError("El archivo supera el tamaño máximo (8 MB).")
    try:
        wb = load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    except Exception as e:
        raise ValueError(f"No se pudo leer el Excel: {e}") from e
    try:
        meta: Dict[str, Any] = {}
        if HOJA_META in wb.sheetnames:
            ws_m = wb[HOJA_META]
            for row in ws_m.iter_rows(min_row=1, max_col=2, values_only=True):
                if not row:
                    continue
                k = _celda_str(row[0]).strip().lower()
                if k:
                    meta[k] = row[1] if len(row) > 1 else None
        if HOJA_PEDIDO not in wb.sheetnames:
            raise ValueError(
                "El Excel no tiene la hoja Pedido. Descargá de nuevo la plantilla."
            )
        ws = wb[HOJA_PEDIDO]
        rows = [tuple(row) for row in ws.iter_rows(values_only=True)]
        return rows, meta
    finally:
        wb.close()


def _mapear_columnas_sucursal(
    headers_id: Sequence[Any],
    headers_nom: Sequence[Any],
    sucursales: Sequence[Dict[str, Any]],
    errores: List[Dict[str, Any]],
) -> List[Tuple[int, Optional[int], str]]:
    """Lista (col_1based, id_domicilio|None, etiqueta_header) para cols ≥ 3."""
    by_id = {
        to_int_or_none(s.get("id_cliente_domicilio")): s
        for s in sucursales
        if to_int_or_none(s.get("id_cliente_domicilio")) is not None
    }
    by_etiq: Dict[str, List[int]] = {}
    for s in sucursales:
        idd = to_int_or_none(s.get("id_cliente_domicilio"))
        if idd is None:
            continue
        keys = {
            _etiqueta_suc(s).strip().lower(),
            str_or_default(s.get("calle"), "").strip().lower(),
            str_or_default(s.get("nro"), "").strip().lower(),
            f"suc {str_or_default(s.get('nro'), '')}".strip().lower(),
        }
        for k in keys:
            if k:
                by_etiq.setdefault(k, []).append(idd)

    n = max(len(headers_id), len(headers_nom))
    out: List[Tuple[int, Optional[int], str]] = []
    for i in range(2, n):  # índice 0-based; col Excel = i+1; saltar A,B
        col = i + 1
        raw_id = headers_id[i] if i < len(headers_id) else None
        raw_nom = headers_nom[i] if i < len(headers_nom) else None
        letra = get_column_letter(col)
        etiqueta = _celda_str(raw_nom) or _celda_str(raw_id)
        idd = to_int_or_none(raw_id)
        if idd is None and _celda_str(raw_id):
            # Header de ids no numérico: intentar etiqueta.
            idd = None
        if idd is not None:
            if idd not in by_id:
                errores.append(
                    _err(
                        "La sucursal no está en el territorio del vendedor para este cliente.",
                        code="sucursal_fuera_territorio",
                        fila=1,
                        columna=letra,
                        sucursal=etiqueta or str(idd),
                    )
                )
                out.append((col, None, etiqueta))
                continue
            out.append((col, idd, etiqueta or _etiqueta_suc(by_id[idd])))
            continue
        key = etiqueta.strip().lower()
        candidatos = by_etiq.get(key) or []
        if not etiqueta:
            continue
        if len(candidatos) == 1:
            out.append((col, candidatos[0], etiqueta))
        elif len(candidatos) > 1:
            errores.append(
                _err(
                    "Sucursal ambigua (mismo nombre en más de un domicilio). Usá la plantilla descargada.",
                    code="sucursal_ambigua",
                    fila=2,
                    columna=letra,
                    sucursal=etiqueta,
                )
            )
            out.append((col, None, etiqueta))
        else:
            errores.append(
                _err(
                    "Sucursal no reconocida para este vendedor y cliente.",
                    code="sucursal_desconocida",
                    fila=2,
                    columna=letra,
                    sucursal=etiqueta,
                )
            )
            out.append((col, None, etiqueta))
    return out


def _elegir_articulo(
    codigo: str,
    candidatos: Sequence[Dict[str, Any]],
    fila: int,
    errores: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not candidatos:
        errores.append(
            _err(
                "Artículo no encontrado.",
                code="articulo_no_encontrado",
                fila=fila,
                columna="A",
                codigo_articulo=codigo,
            )
        )
        return None
    if len(candidatos) > 1:
        errores.append(
            _err(
                "Código de artículo ambiguo: coincide con más de un artículo.",
                code="articulo_ambiguo",
                fila=fila,
                columna="A",
                codigo_articulo=codigo,
            )
        )
        return None
    art = candidatos[0]
    disc = str_or_default(art.get("discontinuo"), "No").strip().lower()
    ecom = str_or_default(art.get("ecommerce"), "No").strip().lower()
    tipo = str_or_default(art.get("tipo_art_fab"), "").strip()
    if disc not in ("no", "") or ecom not in ("si", "sí") or tipo != "Terminado":
        errores.append(
            _err(
                "El artículo no está activo para venta (Terminado / ecommerce).",
                code="articulo_inactivo",
                fila=fila,
                columna="A",
                codigo_articulo=codigo,
            )
        )
        return None
    return art


def importar_matriz_excel(
    draft: EcomPedidoMasivoDraft,
    archivo_bytes: bytes,
    *,
    consultar_arts=None,
) -> Dict[str, Any]:
    """Parsea, valida VCM y reemplaza celdas. All-or-nothing si hay errores."""
    if draft.estado not in (
        EcomPedidoMasivoDraft.ESTADO_BORRADOR,
        EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO,
    ):
        return {
            "ok": False,
            "error": "El borrador no es editable.",
            "code": "draft_no_editable",
            "errores": [
                _err("El borrador no es editable.", code="draft_no_editable")
            ],
        }

    errores: List[Dict[str, Any]] = []
    try:
        rows, meta = _leer_workbook_import(archivo_bytes)
    except ValueError as e:
        return {
            "ok": False,
            "error": str(e),
            "code": "archivo_invalido",
            "errores": [_err(str(e), code="archivo_invalido")],
        }
    if len(rows) < 2:
        return {
            "ok": False,
            "error": "El Excel no tiene el formato de plantilla (faltan encabezados).",
            "code": "archivo_invalido",
            "errores": [
                _err(
                    "El Excel no tiene el formato de plantilla (faltan encabezados).",
                    code="archivo_invalido",
                )
            ],
        }

    sucursales, marcas_map = _territorio(draft)
    a1 = _celda_str(rows[0][0] if rows[0] else "").lower()
    es_plantilla = a1.replace(" ", "_") == MARKER_CODIGO
    if es_plantilla:
        headers_id = list(rows[0])
        headers_nom = list(rows[1]) if len(rows) > 1 else []
        data_rows = rows[2:]
        fila_base = 3
    else:
        headers_id = list(rows[0])
        headers_nom = list(rows[0])
        data_rows = rows[1:]
        fila_base = 2

    id_cli_excel = to_int_or_none(meta.get("id_cliente"))
    if id_cli_excel is None and es_plantilla and rows and len(rows[0]) > 1:
        id_cli_excel = to_int_or_none(rows[0][1])
    id_cli_draft = to_int_or_none(draft.id_cliente)
    if id_cli_excel is None:
        errores.append(
            _err(
                "Falta la identificación del cliente. Descargá de nuevo la plantilla de este pedido.",
                code="plantilla_sin_cliente",
                fila=1,
            )
        )
    elif id_cli_draft is not None and id_cli_excel != id_cli_draft:
        nom = _nombre_cliente(draft.base_empresa, id_cli_draft) or str(id_cli_draft)
        errores.append(
            _err(
                (
                    f"Esta plantilla es del cliente {id_cli_excel} y el pedido abierto "
                    f"es {id_cli_draft} ({nom}). Descargá la plantilla de este cliente."
                ),
                code="cliente_no_coincide",
                fila=1,
            )
        )
    cv_excel = to_int_or_none(meta.get("cod_viajante"))
    cv_draft = to_int_or_none(draft.cod_viajante)
    if (
        cv_excel is not None
        and cv_draft is not None
        and cv_excel != cv_draft
    ):
        errores.append(
            _err(
                "Esta plantilla es de otro vendedor. Descargá la plantilla de este pedido.",
                code="vendedor_no_coincide",
                fila=1,
            )
        )

    cols = _mapear_columnas_sucursal(headers_id, headers_nom, sucursales, errores)
    if not cols:
        errores.append(
            _err(
                "No hay columnas de sucursal. Descargá la plantilla del cliente.",
                code="sin_columnas_sucursal",
                fila=1,
            )
        )

    codigos_filas: List[Tuple[int, str, Any]] = []
    for offset, row in enumerate(data_rows):
        fila = fila_base + offset
        if not row:
            continue
        codigo = _celda_str(row[0] if len(row) > 0 else None)
        if not codigo:
            hay_qty = False
            for col, _idd, _et in cols:
                idx = col - 1
                if idx < len(row):
                    qty, qerr = _qty_celda(row[idx])
                    if qty is not None or qerr:
                        hay_qty = True
                        break
            if hay_qty:
                errores.append(
                    _err(
                        "Falta el código de artículo.",
                        code="articulo_sin_codigo",
                        fila=fila,
                        columna="A",
                    )
                )
            continue
        codigos_filas.append((fila, codigo, row))

    lookup_fn = consultar_arts or consultar_articulos_por_codigos
    catalogo = lookup_fn(draft.base_empresa, [c for _f, c, _r in codigos_filas])

    vistos: Dict[str, int] = {}
    celdas_ok: List[Tuple[int, int, Decimal]] = []
    arts_ok: Dict[int, Dict[str, Any]] = {}

    for fila, codigo, row in codigos_filas:
        prev = vistos.get(codigo.lower())
        if prev:
            hay_qty_dup = False
            for col, _idd, _et in cols:
                idx = col - 1
                if idx < len(row):
                    qty, qerr = _qty_celda(row[idx])
                    if qty is not None or qerr:
                        hay_qty_dup = True
                        break
            if hay_qty_dup:
                errores.append(
                    _err(
                        f"Artículo repetido (ya aparece en la fila {prev}).",
                        code="articulo_duplicado",
                        fila=fila,
                        columna="A",
                        codigo_articulo=codigo,
                    )
                )
            continue
        vistos[codigo.lower()] = fila
        art = _elegir_articulo(codigo, catalogo.get(codigo) or [], fila, errores)
        if not art:
            continue
        aid = int(art["id_articulo"])
        arts_ok[aid] = art
        marca = to_int_or_none(art.get("codigo_marca"))
        multiplo = multiplo_empaque_venta(art.get("multiplo_cantidad_vta"))
        for col, idd, etiqueta in cols:
            letra = get_column_letter(col)
            idx = col - 1
            val = row[idx] if idx < len(row) else None
            qty, qerr = _qty_celda(val)
            if qerr:
                errores.append(
                    _err(
                        qerr,
                        code="cantidad_invalida",
                        fila=fila,
                        columna=letra,
                        codigo_articulo=codigo,
                        sucursal=etiqueta,
                    )
                )
                continue
            if qty is None:
                continue
            if idd is None:
                continue
            if not cantidad_respeta_multiplo(qty, multiplo):
                errores.append(
                    _err(
                        mensaje_multiplo_invalido(multiplo),
                        code="multiplo_empaque",
                        fila=fila,
                        columna=letra,
                        codigo_articulo=codigo,
                        sucursal=etiqueta,
                    )
                )
                continue
            permitidas = marcas_map.get(idd) or set()
            if marca is None or marca not in permitidas:
                errores.append(
                    _err(
                        "La marca del artículo no está asignada a esta sucursal para el vendedor.",
                        code="marca_fuera_territorio",
                        fila=fila,
                        columna=letra,
                        codigo_articulo=codigo,
                        sucursal=etiqueta,
                    )
                )
                continue
            celdas_ok.append((aid, idd, qty))

    if errores:
        return {
            "ok": False,
            "error": f"La importación tiene {len(errores)} error(es). No se modificó el borrador.",
            "code": "validacion",
            "errores": errores[:MAX_ERRORES],
            "errores_total": len(errores),
        }

    if not celdas_ok:
        return {
            "ok": False,
            "error": "No hay cantidades para importar. Completá packs en la plantilla.",
            "code": "sin_cantidades",
            "errores": [
                _err(
                    "No hay cantidades para importar. Completá packs en la plantilla.",
                    code="sin_cantidades",
                )
            ],
        }

    if draft.estado == EcomPedidoMasivoDraft.ESTADO_CONFIRMANDO:
        draft.estado = EcomPedidoMasivoDraft.ESTADO_BORRADOR

    with transaction.atomic():
        EcomPedidoMasivoDraftCelda.objects.filter(draft=draft).delete()
        draft.descuentos_fila = {}
        draft.ultimo_error = {}
        if celdas_ok:
            EcomPedidoMasivoDraftCelda.objects.bulk_create(
                [
                    EcomPedidoMasivoDraftCelda(
                        draft=draft,
                        id_articulo=aid,
                        id_cliente_domicilio=idd,
                        cantidad_packs=qty,
                    )
                    for aid, idd, qty in celdas_ok
                ],
                batch_size=500,
            )
        for aid in arts_ok:
            asegurar_descuento_fila_articulo(draft, aid, draft.base_empresa)
        ctx_cli = leer_contexto_cliente_masivo(draft.base_empresa, draft.id_cliente)
        draft.descuento_pie_pct = _clamp_pct(ctx_cli.get("descPie"))
        draft.save(
            update_fields=[
                "estado",
                "descuentos_fila",
                "descuento_pie_pct",
                "ultimo_error",
                "updated_at",
            ]
        )

    n_suc = len({idd for _a, idd, _q in celdas_ok})
    return {
        "ok": True,
        "message": (
            f"Se importaron {len(celdas_ok)} cantidad(es) "
            f"en {len(arts_ok)} artículo(s) y {n_suc} sucursal(es)."
        ),
        "celdas": len(celdas_ok),
        "articulos": len(arts_ok),
        "sucursales": n_suc,
        "errores": [],
    }


def nombre_archivo_plantilla(draft: EcomPedidoMasivoDraft) -> str:
    cid = to_int_or_none(draft.id_cliente) or 0
    crudo = _nombre_cliente(draft.base_empresa, draft.id_cliente)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "_", (crudo or "").strip())[:40].strip("_")
    if slug:
        return f"pedido_masivo_{cid}_{slug}.xlsx"
    return f"pedido_masivo_cliente_{cid}.xlsx"
