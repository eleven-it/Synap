"""
Calidad de cabecera: puntuación documento, faltantes críticos, consistencia legacy vs Stage 2.

Solo lectura / agregado en ``document_engine_v1``; no altera ``campos_cabecera``.
"""

from __future__ import annotations

from typing import Any

from factura_compra_captura.services.confidence_catalog import (
    CAMPOS_CRITICOS_CABECERA,
    PESO_CLASIFICACION_DOC,
    PESO_COMPLETITUD,
    PESO_CONSISTENCIA,
    PESO_PROMEDIO_CAMPOS,
)


def _norm_total(s: str | None) -> str | None:
    if not s:
        return None
    t = str(s).strip().replace(" ", "")
    if "," in t and "." in t:
        if t.rfind(",") > t.rfind("."):
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        partes = t.split(",")
        if len(partes[-1]) in (1, 2):
            t = ",".join(partes[:-1]).replace(".", "") + "." + partes[-1]
        else:
            t = t.replace(",", ".")
    return t


def _nro_desde_cab(cab: dict[str, Any]) -> tuple[str | None, str | None]:
    raw = (cab.get("nro_comprobante_texto") or "").strip()
    if not raw:
        return None, None
    if "-" in raw:
        a, _, b = raw.partition("-")
        if a.strip().isdigit() and b.replace(" ", "").isdigit():
            return a.strip(), b.replace(" ", "").strip()[:20]
    return None, None


def verificar_consistencia_legacy_vs_header(
    header: dict[str, Any],
    campos_cabecera: dict[str, Any],
) -> dict[str, Any]:
    """
    Compara valores del parser legacy (``campos_cabecera``) con ``parsed.header`` Stage 2.
    No modifica datos; solo informa ``ok`` y mensaje corto.
    """
    cab = campos_cabecera or {}
    checks: list[dict[str, Any]] = []

    # Tipo factura
    t_legacy = (cab.get("tipo_factura") or "").strip()
    t_h = (header.get("tipo_factura") or {}).get("valor")
    t_h = (t_h or "").strip() if t_h else ""
    if t_legacy and t_h:
        ok = t_legacy == t_h
        checks.append(
            {
                "codigo": "tipo_factura",
                "ok": ok,
                "legacy": t_legacy,
                "header": t_h,
                "detalle": "Coincide tipo FA/FB/FC" if ok else "Distinto tipo entre legacy y header Stage 2",
            }
        )

    # Fecha
    f_legacy = (cab.get("fecha_comprobante_texto") or "").strip()
    f_h = (header.get("fecha") or {}).get("valor")
    f_h = (f_h or "").strip() if f_h else ""
    if f_legacy and f_h:
        ok = f_legacy.replace(" ", "") == f_h.replace(" ", "")
        checks.append(
            {
                "codigo": "fecha_comprobante",
                "ok": ok,
                "legacy": f_legacy,
                "header": f_h,
                "detalle": "Misma fecha" if ok else "Fecha distinta entre parsers",
            }
        )

    # Número comprobante (PV + número)
    pv_l, n_l = _nro_desde_cab(cab)
    pv_h = (header.get("punto_venta") or {}).get("valor")
    n_h = (header.get("numero") or {}).get("valor")
    pv_hs = str(pv_h).strip() if pv_h else ""
    n_hs = str(n_h).strip() if n_h else ""
    if pv_l and n_l and pv_hs and n_hs:
        ok = pv_l == pv_hs and n_l == n_hs
        checks.append(
            {
                "codigo": "punto_venta_numero",
                "ok": ok,
                "legacy": f"{pv_l}-{n_l}",
                "header": f"{pv_hs}-{n_hs}",
                "detalle": "Mismo PV y número" if ok else "Comprobante distinto entre legacy y header",
            }
        )

    # Total
    tot_l = _norm_total(cab.get("importe_total_texto"))
    tot_h = _norm_total((header.get("total") or {}).get("valor"))
    if tot_l and tot_h:
        try:
            ok = abs(float(tot_l) - float(tot_h)) < 0.02
        except ValueError:
            ok = tot_l == tot_h
        checks.append(
            {
                "codigo": "importe_total",
                "ok": ok,
                "legacy": str(cab.get("importe_total_texto")),
                "header": str((header.get("total") or {}).get("valor")),
                "detalle": "Mismo importe (normalizado)" if ok else "Importe total distinto",
            }
        )

    n_ok = sum(1 for c in checks if c.get("ok"))
    score_cons = 1.0 if not checks else n_ok / len(checks)

    return {
        "checks": checks,
        "score": round(score_cons, 4),
        "pares_comparados": len(checks),
    }


def resumen_campos_criticos_faltantes(header: dict[str, Any]) -> dict[str, Any]:
    """
    Lista campos críticos sin ``valor`` en el modelo Stage 2 y conteo.
    """
    faltantes: list[str] = []
    for clave in CAMPOS_CRITICOS_CABECERA:
        bloque = header.get(clave) or {}
        if not (bloque.get("valor") if isinstance(bloque, dict) else None):
            faltantes.append(clave)
    return {
        "lista": faltantes,
        "cantidad": len(faltantes),
        "total_campos": len(CAMPOS_CRITICOS_CABECERA),
    }


def calcular_document_score(
    classification: dict[str, Any],
    header: dict[str, Any],
    consistencia: dict[str, Any],
) -> dict[str, Any]:
    """
    Puntuación 0..1 a nivel documento (heurística, no probabilidad calibrada).
    """
    conf_clas = float(classification.get("confidence") or 0.0)
    confs: list[float] = []
    for clave in CAMPOS_CRITICOS_CABECERA:
        b = header.get(clave)
        if isinstance(b, dict) and b.get("valor") is not None:
            confs.append(float(b.get("confidence") or 0.0))
    prom_campos = sum(confs) / len(confs) if confs else 0.0

    res = resumen_campos_criticos_faltantes(header)
    completitud = 1.0 - (res["cantidad"] / max(res["total_campos"], 1))

    score_cons = float(consistencia.get("score") or 1.0)
    if not consistencia.get("checks"):
        score_cons = 1.0

    doc = (
        PESO_CLASIFICACION_DOC * conf_clas
        + PESO_PROMEDIO_CAMPOS * prom_campos
        + PESO_COMPLETITUD * completitud
        + PESO_CONSISTENCIA * score_cons
    )
    return {
        "document_score": round(min(1.0, max(0.0, doc)), 4),
        "componentes": {
            "clasificacion": round(conf_clas, 4),
            "promedio_campos_rellenos": round(prom_campos, 4),
            "completitud_campos_criticos": round(completitud, 4),
            "consistencia_legacy": round(score_cons, 4),
        },
        "pesos": {
            "clasificacion": PESO_CLASIFICACION_DOC,
            "promedio_campos": PESO_PROMEDIO_CAMPOS,
            "completitud": PESO_COMPLETITUD,
            "consistencia": PESO_CONSISTENCIA,
        },
    }


def construir_paquete_calidad_cabecera(
    classification: dict[str, Any],
    header: dict[str, Any],
    campos_cabecera: dict[str, Any],
) -> dict[str, Any]:
    """Paquete único para ``parsed.header_quality`` + ``document_score``."""
    consistencia = verificar_consistencia_legacy_vs_header(header, campos_cabecera)
    faltantes = resumen_campos_criticos_faltantes(header)
    score_pkg = calcular_document_score(classification, header, consistencia)
    return {
        "document_score": score_pkg["document_score"],
        "componentes_document_score": score_pkg["componentes"],
        "pesos_document_score": score_pkg["pesos"],
        "campos_criticos": faltantes,
        "consistencia_legacy": consistencia,
    }
