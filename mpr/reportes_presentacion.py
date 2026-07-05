"""Presentación unidades vs docenas en reportes MPR."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

from mpr.services import bulk_cantidad_promedio_bulto, descomponer_docenas_unidades, texto_docenas_unidades

MODOS_PRESENTACION = frozenset({"unidades", "docenas"})
DEFAULT_MODO_PRESENTACION = "unidades"
UNIDADES_POR_DOCENA_COMPONENTE = 12

# Campos numéricos de cantidad (no contadores ni porcentajes).
CAMPOS_CANTIDAD: Set[str] = {
    "enviado",
    "parte",
    "clasificado",
    "scrap",
    "gap_envio_parte",
    "unidades",
    "unidades_total",
    "top_unidades",
    "promedio",
    "demanda",
    "pendiente",
    "total",
    "stock_terminado",
    "cantidad_a_fabricar",
    "demanda_pendiente",
    "unidades_faltantes",
    "saldo",
    "saldo_total",
    "stock_minimo",
}


def parse_modo_presentacion(raw: Optional[str]) -> str:
    modo = (raw or DEFAULT_MODO_PRESENTACION).strip().lower()
    return modo if modo in MODOS_PRESENTACION else DEFAULT_MODO_PRESENTACION


def _to_int_cantidad(val: Any) -> int:
    try:
        return int(float(val or 0))
    except (TypeError, ValueError):
        return 0


def formatear_cantidad_reporte(
    cantidad: Any,
    modo: str,
    *,
    cantidad_promedio_bulto: Any = None,
) -> str:
    """Unidades: entero. Docenas: «N docenas · M unidades» (divisor 12 o bulto pack)."""
    n = _to_int_cantidad(cantidad)
    if modo == "docenas":
        if cantidad_promedio_bulto is not None:
            return texto_docenas_unidades(n, cantidad_promedio_bulto)
        return texto_docenas_unidades(n, unidades_por_docena_fijo=UNIDADES_POR_DOCENA_COMPONENTE)
    return str(n)


def enriquecer_fila_cantidades(
    fila: Dict[str, Any],
    modo: str,
    bulto_map: Optional[Dict[int, float]] = None,
) -> Dict[str, Any]:
    if not isinstance(fila, dict):
        return fila
    out = dict(fila)
    aid = out.get("id_articulo")
    bulto = None
    if bulto_map and aid is not None:
        try:
            bulto = bulto_map.get(int(aid))
        except (TypeError, ValueError):
            bulto = None
    for campo in CAMPOS_CANTIDAD:
        if campo in out:
            out[f"{campo}_display"] = formatear_cantidad_reporte(
                out[campo], modo, cantidad_promedio_bulto=bulto
            )
    return out


def _ids_articulo_en_filas(filas: List[Dict[str, Any]]) -> List[int]:
    ids: List[int] = []
    seen: Set[int] = set()
    for fila in filas or []:
        if not isinstance(fila, dict):
            continue
        try:
            aid = int(fila.get("id_articulo"))
        except (TypeError, ValueError):
            continue
        if aid not in seen:
            seen.add(aid)
            ids.append(aid)
    return ids


def aplicar_presentacion_reporte(
    context: Dict[str, Any],
    modo: str,
    base_empresa: Optional[str] = None,
) -> Dict[str, Any]:
    """Añade campos *_display y metadatos de presentación al contexto del reporte."""
    filas = list(context.get("filas") or [])
    bulto_map: Dict[int, float] = {}
    if modo == "docenas" and base_empresa and filas:
        bulto_map = bulk_cantidad_promedio_bulto(base_empresa, _ids_articulo_en_filas(filas))

    meta_id: Optional[int] = None
    meta = context.get("meta")
    if isinstance(meta, dict):
        try:
            meta_id = int(meta["id_articulo"]) if meta.get("id_articulo") is not None else None
        except (TypeError, ValueError):
            meta_id = None

    if modo == "docenas" and base_empresa and meta_id is not None and meta_id not in bulto_map:
        extra = bulk_cantidad_promedio_bulto(base_empresa, [meta_id])
        bulto_map.update(extra)

    def _map_list(items: Any) -> Any:
        if not isinstance(items, list):
            return items
        return [enriquecer_fila_cantidades(x, modo, bulto_map) if isinstance(x, dict) else x for x in items]

    def _map_eventos(items: Any) -> Any:
        if not isinstance(items, list):
            return items
        out: List[Any] = []
        for ev in items:
            if isinstance(ev, dict):
                fila_ev = dict(ev)
                if meta_id is not None and fila_ev.get("id_articulo") is None:
                    fila_ev["id_articulo"] = meta_id
                fila_ev = enriquecer_fila_cantidades(fila_ev, modo, bulto_map)
                if "cantidad" in fila_ev:
                    aid_ev = fila_ev.get("id_articulo")
                    bulto_ev = None
                    if bulto_map and aid_ev is not None:
                        try:
                            bulto_ev = bulto_map.get(int(aid_ev))
                        except (TypeError, ValueError):
                            bulto_ev = None
                    fila_ev["cantidad_display"] = formatear_cantidad_reporte(
                        fila_ev["cantidad"], modo, cantidad_promedio_bulto=bulto_ev
                    )
                out.append(fila_ev)
            else:
                out.append(ev)
        return out

    context["modo_presentacion"] = modo
    context["etiqueta_cantidad"] = (
        "docenas · unidades" if modo == "docenas" else "unidades"
    )
    context["etiqueta_cantidad_corta"] = "doc. · u." if modo == "docenas" else "u."
    context["filas"] = _map_list(context.get("filas"))
    context["dias"] = _map_list(context.get("dias"))
    context["eventos"] = _map_eventos(context.get("eventos"))
    if isinstance(context.get("totales"), dict):
        context["totales"] = enriquecer_fila_cantidades(context["totales"], modo)
    if isinstance(context.get("kpis"), dict):
        context["kpis"] = enriquecer_fila_cantidades(context["kpis"], modo)
    return context


def valor_celda_cantidad(fila: Dict[str, Any], campo: str) -> str:
    """Valor a mostrar: *_display si existe."""
    if not isinstance(fila, dict):
        return str(fila)
    disp = fila.get(f"{campo}_display")
    if disp is not None:
        return str(disp)
    return str(fila.get(campo, ""))


def _celda_stock_deposito(
    saldo: float,
    modo: str,
    *,
    cantidad_promedio_bulto: Any = None,
) -> Dict[str, Any]:
    """Celda pivote: docenas arriba y unidades abajo (modo docenas) o solo unidades."""
    try:
        total = int(float(saldo or 0))
    except (TypeError, ValueError):
        total = 0
    total = max(0, total)
    if modo == "docenas":
        partes = descomponer_docenas_unidades(
            total,
            cantidad_promedio_bulto,
            unidades_por_docena_fijo=UNIDADES_POR_DOCENA_COMPONENTE,
        )
        return {
            "saldo": total,
            "docenas": partes["docenas"],
            "unidades": partes["unidades"],
            "docenas_display": str(partes["docenas"]),
            "unidades_display": str(partes["unidades"]),
        }
    return {
        "saldo": total,
        "docenas": 0,
        "unidades": total,
        "docenas_display": "",
        "unidades_display": str(total),
    }


def preparar_stock_por_deposito(
    filas_raw: List[Dict[str, Any]],
    modo: str,
    base_empresa: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Pivotea filas planas (artículo × depósito) a una fila por artículo con columnas de depósito.
    Cada celda expone docenas/unidades para apilar en la plantilla.
    """
    from mpr.pipeline import ORDEN_ETAPAS_MPR

    dep_info: Dict[int, Dict[str, Any]] = {}
    articulos: Dict[int, Dict[str, Any]] = {}

    for r in filas_raw or []:
        if not isinstance(r, dict):
            continue
        aid = r.get("id_articulo")
        did = r.get("id_deposito")
        try:
            aid_int = int(aid) if aid is not None else None
            did_int = int(did) if did is not None else None
        except (TypeError, ValueError):
            continue
        if aid_int is None or did_int is None:
            continue
        clave = f"dep_{did_int}"
        if did_int not in dep_info:
            dep_info[did_int] = {
                "id_deposito": did_int,
                "nombre_deposito": str(r.get("nombre_deposito") or "-"),
                "tipo_mpr": str(r.get("tipo_mpr") or ""),
                "clave": clave,
            }
        if aid_int not in articulos:
            articulos[aid_int] = {
                "id_articulo": aid_int,
                "codigo_articulo": str(r.get("codigo_articulo") or "-"),
                "descripcion_articulo": str(r.get("descripcion_articulo") or "-"),
                "saldos": {},
            }
        try:
            articulos[aid_int]["saldos"][clave] = float(r.get("saldo") or 0)
        except (TypeError, ValueError):
            articulos[aid_int]["saldos"][clave] = 0.0

    def _orden_deposito(dep: Dict[str, Any]) -> tuple:
        tipo = dep.get("tipo_mpr") or ""
        try:
            idx = ORDEN_ETAPAS_MPR.index(tipo)
        except ValueError:
            idx = 999
        return (idx, dep.get("id_deposito") or 0)

    columnas_deposito = sorted(dep_info.values(), key=_orden_deposito)

    bulto_map: Dict[int, float] = {}
    if modo == "docenas" and base_empresa and articulos:
        bulto_map = bulk_cantidad_promedio_bulto(base_empresa, list(articulos.keys()))

    filas_out: List[Dict[str, Any]] = []
    for aid_int in sorted(
        articulos.keys(),
        key=lambda a: (articulos[a].get("codigo_articulo") or "", a),
    ):
        art = articulos[aid_int]
        bulto = bulto_map.get(aid_int) if modo == "docenas" else None
        depositos_celdas = []
        for col in columnas_deposito:
            saldo = art["saldos"].get(col["clave"], 0.0)
            depositos_celdas.append(
                _celda_stock_deposito(saldo, modo, cantidad_promedio_bulto=bulto)
            )
        filas_out.append({
            "id_articulo": aid_int,
            "codigo_articulo": art["codigo_articulo"],
            "descripcion_articulo": art["descripcion_articulo"],
            "depositos": depositos_celdas,
        })

    return {
        "filas": filas_out,
        "columnas_deposito": columnas_deposito,
    }
