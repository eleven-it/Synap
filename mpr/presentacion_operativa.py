"""Presentación docenas/unidades en pantallas operativas MPR."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from mpr.services import descomponer_docenas_unidades, texto_docenas_unidades

SESSION_KEY = "mpr_presentacion_cantidad"
MODOS = frozenset({"docenas", "unidades"})
DEFAULT_MODO = "docenas"
UNIDADES_POR_DOCENA = 12

CAMPOS_TABLERO_CANTIDAD = (
    "pendiente",
    "enviado",
    "produccion",
    "segunda_seleccion",
    "semi_elaborado",
    "desperdicio",
    "terminado",
    "total",
)


def parse_modo_presentacion_operativa(raw: Optional[str]) -> str:
    modo = (raw or "").strip().lower()
    return modo if modo in MODOS else DEFAULT_MODO


def resolver_modo_presentacion_operativa(request) -> str:
    """Lee ?presentacion= de GET (persiste en sesión) o devuelve sesión/default."""
    raw = (request.GET.get("presentacion") or "").strip().lower()
    if raw in MODOS:
        request.session[SESSION_KEY] = raw
        return raw
    return parse_modo_presentacion_operativa(request.session.get(SESSION_KEY))


def _display_cantidad(val: Any, modo: str) -> str:
    try:
        n = int(round(float(val or 0)))
    except (TypeError, ValueError):
        n = 0
    if modo == "docenas":
        return texto_docenas_unidades(n, unidades_por_docena_fijo=UNIDADES_POR_DOCENA)
    return str(n)


def enriquecer_fila_tablero_presentacion(
    fila: Dict[str, Any],
    modo: str,
) -> Dict[str, Any]:
    out = dict(fila)
    out["presentacion_modo"] = modo
    for campo in CAMPOS_TABLERO_CANTIDAD:
        if campo in out:
            out[f"{campo}_display"] = _display_cantidad(out[campo], modo)
    try:
        pend = int(round(float(out.get("pendiente") or 0)))
    except (TypeError, ValueError):
        pend = 0
    du = descomponer_docenas_unidades(pend, unidades_por_docena_fijo=UNIDADES_POR_DOCENA)
    out["pendiente_docenas"] = du["docenas"]
    out["pendiente_unidades_sueltas"] = du["unidades"]
    return out


def enriquecer_filas_tablero_presentacion(
    filas: List[Dict[str, Any]],
    modo: str,
) -> List[Dict[str, Any]]:
    return [enriquecer_fila_tablero_presentacion(f, modo) for f in (filas or [])]
