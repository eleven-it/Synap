# -*- coding: utf-8 -*-
"""Etiquetas legibles de filtros para exportación Excel (nombres, no códigos)."""
from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.conf import settings

logger = logging.getLogger(__name__)

# (clave_filtro, etiqueta_español, tipo_resolución)
_FILTER_SPECS: Tuple[Tuple[str, str, str], ...] = (
    ("fecha_inicio", "Período desde", "fecha"),
    ("fecha_fin", "Período hasta", "fecha"),
    ("fecha_inicio_facturacion", "Facturación desde", "fecha"),
    ("fecha_fin_facturacion", "Facturación hasta", "fecha"),
    ("fecha_inicio_bo", "Backorder desde", "fecha"),
    ("fecha_fin_bo", "Backorder hasta", "fecha"),
    ("periodo_tipo_facturacion", "Tipo período facturación", "periodo_tipo"),
    ("dia_actual", "Período", "flag_dia"),
    ("mes_actual", "Período", "flag_mes"),
    ("año_actual", "Período", "flag_anio"),
    ("sucursales", "Sucursales", "sucursales"),
    ("punto_venta", "Puntos de venta", "puntos_venta"),
    ("depositos_incluidos", "Depósitos incluidos", "depositos"),
    ("lista_precio", "Lista de precio", "lista_precio"),
    ("clientes_incluir", "Clientes incluidos", "clientes"),
    ("clientes_excluidos", "Clientes excluidos", "clientes"),
    ("vendedores_incluir", "Vendedores incluidos", "viajantes"),
    ("vendedores_excluidos", "Vendedores excluidos", "viajantes"),
    ("rubros_incluidos", "Rubros incluidos", "rubros"),
    ("rubros_excluidos", "Rubros excluidos", "rubros"),
    ("subrubros_incluidos", "Subrubros incluidos", "subrubros"),
    ("subrubros_excluidos", "Subrubros excluidos", "subrubros"),
    ("marcas_incluidos", "Marcas incluidas", "marcas"),
    ("marcas_excluidos", "Marcas excluidas", "marcas"),
    ("superarts_incluidos", "SuperArt incluidos", "texto_lista"),
    ("incluir_stock_cero", "Incluir stock cero", "si_no"),
    ("logistica_estado_entrega", "Estado entrega", "texto"),
    ("logistica_id_cliente", "Cliente logística", "logistica_cliente"),
    ("busqueda", "Búsqueda", "texto"),
    ("ordenar_por", "Ordenar por", "ordenar_por"),
    ("orden_forma", "Orden", "orden_forma"),
    ("excel_scope", "Alcance exportación", "excel_scope"),
    ("nro_comprobante", "N° comprobante", "texto"),
)

_ORDENAR_POR_LABELS = {
    "objetivo_meta": "Objetivo meta",
    "objetivo_falta": "Objetivo falta",
    "total_ventas_periodo": "Total ventas período",
    "facturacion_periodo": "Facturación período",
    "unidades_periodo": "Unidades período",
    "packs": "Packs",
    "docenas": "Docenas",
}

_ORDEN_FORMA_LABELS = {"asc": "Creciente", "desc": "Decreciente"}

_PERIODO_TIPO_LABELS = {
    "dia_actual": "Día en curso",
    "mes_actual": "Mes en curso",
    "año_actual": "Año en curso",
    "personalizado": "Personalizado",
}

_LISTA_PRECIO_LABELS = (
    "Costo",
    "Lista Oficial",
    "Lista 1",
    "Lista 2",
    "Lista 3",
    "Lista 4",
    "Lista 5",
)

# Informes de ventas que siempre declaran el alcance sucursal / PV en Excel.
_SLUGS_SCOPE_SUCURSAL_PV = frozenset(
    {
        "ventas-objetivos-vs-bo",
        "ventas-por-vendedor",
        "ventas-por-articulo",
        "ventas-marca-superart",
        "ventas-bom-docenas",
        "ventas-marcas-mensual",
        "ventas-mensuales-licenciatarios",
        "ventas-netas",
        "ventas_netas",
        "total-consolidado-operativo",
        "clientes-sin-ventas-vendedor",
    }
)

_SKIP_KEYS = frozenset(
    {
        "base_empresa",
        "performance_phase_ms",
        "performance_total_ms",
        "logistica_cliente_etiquetas",
        "logistica_cliente_label",
        "filter_labels",
    }
)


def _parse_int_list(raw: Any) -> List[int]:
    if isinstance(raw, str):
        raw = [raw] if raw.strip() else []
    elif not isinstance(raw, list):
        raw = []
    out: List[int] = []
    for item in raw:
        try:
            out.append(int(str(item).strip()))
        except (TypeError, ValueError):
            continue
    return out


def _fmt_fecha(value: Any) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        return value.date().strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    s = str(value).strip()
    if not s:
        return ""
    if len(s) >= 10 and s[4:5] == "-":
        try:
            return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
        except ValueError:
            pass
    return s


def _truthy_flag(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "si", "sí")


def _label_lista_precio(cod: Any, meta_label: Optional[str]) -> str:
    if meta_label:
        return str(meta_label).strip()
    try:
        i = int(cod)
    except (TypeError, ValueError):
        return str(cod) if cod is not None else ""
    if 0 <= i < len(_LISTA_PRECIO_LABELS):
        return _LISTA_PRECIO_LABELS[i]
    return f"Lista ({i})"


class _MysqlLabelLookup:
    """Resuelve códigos legacy AdministraNET a etiquetas legibles."""

    def __init__(self, base_empresa: str):
        self.base_empresa = base_empresa
        self._maps: Dict[str, Dict[int, str]] = {}

    def _connect(self):
        import MySQLdb

        mysql_config = settings.DATABASES["mysql"]
        return MySQLdb.connect(
            host=mysql_config["HOST"],
            port=int(mysql_config["PORT"]),
            user=mysql_config["USER"],
            passwd=mysql_config["PASSWORD"],
            db=self.base_empresa,
            charset="latin1",
        )

    def _load_map(self, kind: str, ids: Sequence[int]) -> Dict[int, str]:
        if kind in self._maps:
            base = self._maps[kind]
            return {i: base[i] for i in ids if i in base}
        unique = sorted({int(i) for i in ids if i is not None})
        if not unique:
            self._maps[kind] = {}
            return {}

        queries = {
            "sucursales": (
                "SELECT id_sucursal, nombre_sucursal FROM sucursales "
                "WHERE id_sucursal IN ({ph})",
                "id_sucursal",
                "nombre_sucursal",
            ),
            "puntos_venta": (
                "SELECT id_punto_venta, nro_punto_venta FROM punto_venta "
                "WHERE id_punto_venta IN ({ph})",
                "id_punto_venta",
                "nro_punto_venta",
            ),
            "depositos": (
                "SELECT CodDeposito, NombreDeposito FROM deposito "
                "WHERE CodDeposito IN ({ph})",
                "CodDeposito",
                "NombreDeposito",
            ),
            "clientes": (
                "SELECT Codigo, nombre_cliente FROM cliente WHERE Codigo IN ({ph})",
                "Codigo",
                "nombre_cliente",
            ),
            "viajantes": (
                "SELECT CodViajante, Nombre FROM viajantes WHERE CodViajante IN ({ph})",
                "CodViajante",
                "Nombre",
            ),
            "rubros": (
                "SELECT CodigoRubro, NombreRubro FROM rubro WHERE CodigoRubro IN ({ph})",
                "CodigoRubro",
                "NombreRubro",
            ),
            "subrubros": (
                "SELECT IDSubRubro, NombreSubRubro FROM subrubro WHERE IDSubRubro IN ({ph})",
                "IDSubRubro",
                "NombreSubRubro",
            ),
            "marcas": (
                "SELECT CodMarca, NombreMarca FROM marca WHERE CodMarca IN ({ph})",
                "CodMarca",
                "NombreMarca",
            ),
        }
        spec = queries.get(kind)
        if not spec:
            return {}

        sql_tpl, id_col, name_col = spec
        placeholders = ",".join(["%s"] * len(unique))
        sql = sql_tpl.format(ph=placeholders)
        out: Dict[int, str] = {}
        conn = None
        try:
            conn = self._connect()
            cur = conn.cursor()
            cur.execute(sql, unique)
            cols = [d[0] for d in cur.description]
            id_idx = cols.index(id_col)
            name_idx = cols.index(name_col)
            for row in cur.fetchall():
                try:
                    rid = int(row[id_idx])
                except (TypeError, ValueError):
                    continue
                nombre = row[name_idx]
                if isinstance(nombre, bytes):
                    nombre = nombre.decode("latin1", errors="replace")
                label = (str(nombre or "").strip()) or f"{kind} {rid}"
                if kind == "puntos_venta":
                    label = f"PV {label}"
                out[rid] = label
            cur.close()
        except Exception as exc:
            logger.warning("Export filtros: lookup %s falló: %s", kind, exc)
        finally:
            if conn:
                conn.close()

        self._maps[kind] = out
        return {i: out[i] for i in unique if i in out}

    def labels_for(self, kind: str, ids: Sequence[int]) -> List[str]:
        m = self._load_map(kind, ids)
        labels: List[str] = []
        for i in ids:
            try:
                key = int(i)
            except (TypeError, ValueError):
                continue
            labels.append(m.get(key, f"({key})"))
        return labels


def build_export_filter_lines(
    report_slug: str,
    payload: Dict[str, Any],
    meta_filters_applied: Optional[Dict[str, Any]] = None,
    base_empresa: Optional[str] = None,
) -> List[Tuple[str, str]]:
    """
    Devuelve pares (etiqueta, valor) para escribir antes de los datos en Excel.
    Usa nombres/descripciones cuando hay base_empresa; si no, omite listas de IDs.
    """
    payload_filters = payload.get("filters") if isinstance(payload, dict) else {}
    if not isinstance(payload_filters, dict):
        payload_filters = {}
    merged: Dict[str, Any] = dict(meta_filters_applied or {})
    merged.update(payload_filters)

    extra_labels = merged.get("filter_labels")
    if not isinstance(extra_labels, dict):
        extra_labels = {}

    lookup: Optional[_MysqlLabelLookup] = None
    if base_empresa:
        try:
            lookup = _MysqlLabelLookup(str(base_empresa).strip())
        except Exception as exc:
            logger.warning("Export filtros: sin lookup MySQL: %s", exc)

    lines: List[Tuple[str, str]] = []
    seen_labels: set = set()

    def _append(label: str, value: str) -> None:
        v = (value or "").strip()
        if not v:
            return
        key = (label, v)
        if key in seen_labels:
            return
        seen_labels.add(key)
        lines.append((label, v))

    for key, label, kind in _FILTER_SPECS:
        if key in _SKIP_KEYS or key in extra_labels:
            continue
        # Alcance sucursal/PV: lo declara _append_sucursal_pv_scope (nombres o Todas/Todos).
        if key in ("sucursales", "punto_venta"):
            continue
        raw = merged.get(key)
        if raw is None or raw == "" or raw == []:
            continue

        if kind == "fecha":
            _append(label, _fmt_fecha(raw))
        elif kind == "flag_dia" and _truthy_flag(raw):
            _append(label, "Día en curso")
        elif kind == "flag_mes" and _truthy_flag(raw):
            _append(label, "Mes en curso")
        elif kind == "flag_anio" and _truthy_flag(raw):
            _append(label, "Año en curso")
        elif kind == "periodo_tipo":
            _append(label, _PERIODO_TIPO_LABELS.get(str(raw).strip(), str(raw)))
        elif kind == "lista_precio":
            meta_lbl = merged.get("lista_precio_label")
            _append(label, _label_lista_precio(raw, meta_lbl))
        elif kind == "si_no":
            s = str(raw).strip().lower()
            _append(label, "Sí" if s in ("si", "sí", "1", "true", "yes") else "No")
        elif kind == "ordenar_por":
            _append(label, _ORDENAR_POR_LABELS.get(str(raw).strip(), str(raw)))
        elif kind == "orden_forma":
            _append(label, _ORDEN_FORMA_LABELS.get(str(raw).strip().lower(), str(raw)))
        elif kind == "excel_scope":
            scope = str(raw).strip().lower()
            _append(label, "Detallado" if scope == "detallado" else "Resumen")
        elif kind == "texto":
            _append(label, str(raw).strip())
        elif kind == "texto_lista":
            if isinstance(raw, list):
                parts = [str(x).strip() for x in raw if str(x).strip()]
            else:
                parts = [str(raw).strip()] if str(raw).strip() else []
            if parts:
                _append(label, ", ".join(parts))
        elif kind == "logistica_cliente":
            etiquetas = merged.get("logistica_cliente_etiquetas")
            if isinstance(etiquetas, dict) and etiquetas:
                nombres = [str(v).strip() for v in etiquetas.values() if str(v).strip()]
                if nombres:
                    _append(label, ", ".join(nombres))
                    continue
            lbl = merged.get("logistica_cliente_label")
            if lbl:
                _append(label, str(lbl).strip())
                continue
            ids = _parse_int_list(raw if isinstance(raw, list) else [raw])
            if lookup and ids:
                _append(label, ", ".join(lookup.labels_for("clientes", ids)))
        elif lookup:
            ids = _parse_int_list(raw)
            if not ids:
                continue
            kind_map = {
                "sucursales": "sucursales",
                "puntos_venta": "puntos_venta",
                "depositos": "depositos",
                "clientes": "clientes",
                "viajantes": "viajantes",
                "rubros": "rubros",
                "subrubros": "subrubros",
                "marcas": "marcas",
            }
            lk = kind_map.get(kind)
            if lk:
                _append(label, ", ".join(lookup.labels_for(lk, ids)))

    for ek, ev in extra_labels.items():
        if ek in _SKIP_KEYS:
            continue
        elabel = str(ek).replace("_", " ").strip().capitalize()
        _append(elabel, str(ev).strip())

    _append_sucursal_pv_scope(report_slug, merged, lookup, _append)

    return lines


def _unique_int_ids(*raws: Any) -> List[int]:
    seen: set = set()
    out: List[int] = []
    for raw in raws:
        if raw is None or raw == "":
            continue
        for i in _parse_int_list(raw if isinstance(raw, list) else [raw]):
            if i not in seen:
                seen.add(i)
                out.append(i)
    return out


def _format_scope_list(
    ids: List[int],
    kind: str,
    lookup: Optional[_MysqlLabelLookup],
    empty_label: str,
) -> str:
    if not ids:
        return empty_label
    if lookup:
        labels = lookup.labels_for(kind, ids)
        if labels:
            return ", ".join(labels)
    return ", ".join(str(i) for i in ids)


def _append_sucursal_pv_scope(
    report_slug: str,
    merged: Dict[str, Any],
    lookup: Optional[_MysqlLabelLookup],
    append_fn,
) -> None:
    """En informes de ventas, Excel siempre lista sucursales y PV (nombres o «Todas/Todos»)."""
    suc_ids = _unique_int_ids(merged.get("sucursales"))
    pv_ids = _unique_int_ids(
        merged.get("punto_venta"),
        merged.get("puntos_venta"),
        merged.get("punto_venta_id"),
    )
    force = report_slug in _SLUGS_SCOPE_SUCURSAL_PV
    if force or suc_ids:
        append_fn(
            "Sucursales",
            _format_scope_list(suc_ids, "sucursales", lookup, "Todas"),
        )
    if force or pv_ids:
        append_fn(
            "Puntos de venta",
            _format_scope_list(pv_ids, "puntos_venta", lookup, "Todos"),
        )
