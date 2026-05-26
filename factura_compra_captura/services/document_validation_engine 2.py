"""
Motor de validación interna (Stage 4): coherencia cabecera / líneas sin bloquear workflows.

Solo lectura sobre ``document_engine_v1`` ya armado; no modifica ``parsed.*`` ni campos legacy.
"""

from __future__ import annotations

from typing import Any

VALIDATION_EVIDENCE_SCHEMA_VERSION = 1
VALIDATION_SUMMARY_SCHEMA_VERSION = 1

# Umbral relativo suma líneas vs total cabecera
UMBRAL_SUMA_WARNING = 0.02
UMBRAL_SUMA_ERROR = 0.15


def _norm_monto_str(s: str | None) -> str | None:
    if not s:
        return None
    t = str(s).strip().replace(" ", "")
    if not t:
        return None
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


def _to_float(s: str | None) -> float | None:
    n = _norm_monto_str(s)
    if not n:
        return None
    try:
        return float(n)
    except ValueError:
        return None


def _evidencia(
    *,
    raw_text: str = "",
    referencias: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": VALIDATION_EVIDENCE_SCHEMA_VERSION,
        "raw_text": (raw_text or "")[:800],
        "referencias": referencias or {},
    }


def ejecutar_validaciones_documento(document_engine_v1: dict[str, Any]) -> dict[str, Any]:
    """
    Devuelve ``validations`` (lista) y ``validation_summary`` (dict).

    No muta ``document_engine_v1``.
    """
    validations: list[dict[str, Any]] = []
    parsed = document_engine_v1.get("parsed") or {}
    header = parsed.get("header") or {}
    hq = parsed.get("header_quality") or {}
    items: list[dict[str, Any]] = list(parsed.get("line_items") or [])
    liq = document_engine_v1.get("line_items_quality") or {}

    cc = hq.get("campos_criticos") or {}
    lista_faltantes = list(cc.get("lista") or [])
    if lista_faltantes:
        validations.append(
            {
                "codigo": "header.campos_criticos_faltantes",
                "severidad": "warning",
                "mensaje": (
                    "Faltan valores en campos críticos de cabecera: "
                    + ", ".join(lista_faltantes)
                ),
                "evidencia": _evidencia(
                    raw_text=",".join(lista_faltantes),
                    referencias={"campos": lista_faltantes},
                ),
            }
        )

    total_h = (header.get("total") or {}).get("valor")
    if not total_h:
        validations.append(
            {
                "codigo": "header.total_sin_valor",
                "severidad": "warning",
                "mensaje": "No hay importe total en la cabecera analizada.",
                "evidencia": _evidencia(referencias={"campo": "total"}),
            }
        )

    prov = (header.get("proveedor") or {}).get("valor")
    if not prov:
        validations.append(
            {
                "codigo": "header.proveedor_sin_valor",
                "severidad": "info",
                "mensaje": "No se identificó razón social / proveedor en cabecera.",
                "evidencia": _evidencia(referencias={"campo": "proveedor"}),
            }
        )

    clas = document_engine_v1.get("classification") or {}
    if (clas.get("tipo_documento") or "") == "unknown":
        validations.append(
            {
                "codigo": "clasificacion.documento_no_clasificado",
                "severidad": "info",
                "mensaje": "El clasificador no catalogó el documento como factura probable.",
                "evidencia": _evidencia(
                    raw_text=str(clas.get("confidence", "")),
                    referencias={"tipo_documento": "unknown"},
                ),
            }
        )

    item_count = int(liq.get("item_count") or 0)
    if item_count == 0:
        validations.append(
            {
                "codigo": "lineas.sin_items",
                "severidad": "info",
                "mensaje": "No hay ítems de línea en el modelo enriquecido.",
                "evidencia": _evidencia(
                    referencias={"item_count": 0, "heuristic_line_count": liq.get("heuristic_line_count")},
                ),
            }
        )

    for idx, it in enumerate(items):
        campos = it.get("campos") or {}
        cant_s = (campos.get("cantidad") or {}).get("valor")
        precio_s = (campos.get("precio_unitario") or {}).get("valor")
        cant = _to_float(str(cant_s) if cant_s is not None else None)
        precio = _to_float(str(precio_s) if precio_s is not None else None)

        if cant is not None and cant <= 0:
            validations.append(
                {
                    "codigo": "lineas.cantidad_no_positiva",
                    "severidad": "warning",
                    "mensaje": f"Ítem {idx}: cantidad no positiva.",
                    "evidencia": _evidencia(
                        raw_text=str(cant_s),
                        referencias={"item_index": idx, "cantidad": cant_s},
                    ),
                }
            )
        if precio is not None and precio < 0:
            validations.append(
                {
                    "codigo": "lineas.precio_negativo",
                    "severidad": "warning",
                    "mensaje": f"Ítem {idx}: precio unitario negativo.",
                    "evidencia": _evidencia(
                        raw_text=str(precio_s),
                        referencias={"item_index": idx},
                    ),
                }
            )
        if cant is None or precio is None:
            if cant_s or precio_s:
                validations.append(
                    {
                        "codigo": "lineas.subtotal_no_calculable",
                        "severidad": "info",
                        "mensaje": f"Ítem {idx}: cantidad o precio no numéricos; no se verifica subtotal.",
                        "evidencia": _evidencia(
                            referencias={
                                "item_index": idx,
                                "cantidad": cant_s,
                                "precio_unitario": precio_s,
                            },
                        ),
                    }
                )

    total_f = _to_float(str(total_h) if total_h else None)
    suma = 0.0
    n_sumables = 0
    for it in items:
        campos = it.get("campos") or {}
        cant = _to_float(str((campos.get("cantidad") or {}).get("valor") or ""))
        precio = _to_float(str((campos.get("precio_unitario") or {}).get("valor") or ""))
        if cant is not None and precio is not None and cant > 0:
            suma += cant * precio
            n_sumables += 1

    if total_f is not None and n_sumables > 0 and suma > 0:
        diff_rel = abs(suma - total_f) / max(total_f, 1e-9)
        if diff_rel > UMBRAL_SUMA_ERROR:
            validations.append(
                {
                    "codigo": "cross.suma_lineas_vs_total_grave",
                    "severidad": "error",
                    "mensaje": (
                        "La suma de subtotales de línea difiere fuertemente del total de cabecera."
                    ),
                    "evidencia": _evidencia(
                        raw_text=f"suma={suma:.4f},total={total_f:.4f}",
                        referencias={
                            "suma_lineas": round(suma, 4),
                            "total_cabecera": round(total_f, 4),
                            "diferencia_relativa": round(diff_rel, 4),
                        },
                    ),
                }
            )
        elif diff_rel > UMBRAL_SUMA_WARNING:
            validations.append(
                {
                    "codigo": "cross.suma_lineas_vs_total",
                    "severidad": "warning",
                    "mensaje": "La suma de líneas no coincide con el total de cabecera (tolerancia 2%).",
                    "evidencia": _evidencia(
                        raw_text=f"suma={suma:.4f},total={total_f:.4f}",
                        referencias={
                            "suma_lineas": round(suma, 4),
                            "total_cabecera": round(total_f, 4),
                            "diferencia_relativa": round(diff_rel, 4),
                        },
                    ),
                }
            )

    cons = hq.get("consistencia_legacy") or {}
    for chk in cons.get("checks") or []:
        if chk.get("ok") is False:
            validations.append(
                {
                    "codigo": "cross.consistencia_legacy_fallida",
                    "severidad": "warning",
                    "mensaje": (
                        f"Inconsistencia entre parser legacy y cabecera enriquecida: "
                        f"{chk.get('codigo', 'campo')}."
                    ),
                    "evidencia": _evidencia(
                        raw_text=str(chk.get("detalle", "")),
                        referencias={"check": chk},
                    ),
                }
            )

    counts = {"info": 0, "warning": 0, "error": 0}
    for v in validations:
        sev = (v.get("severidad") or "info").lower()
        if sev in counts:
            counts[sev] += 1

    if not validations:
        health = 1.0
    else:
        n = len(validations)
        health = (
            1.0
            - 0.08 * (counts["info"] / n)
            - 0.25 * (counts["warning"] / n)
            - 0.5 * (counts["error"] / n)
        )
        health = max(0.0, min(1.0, round(health, 4)))

    summary = {
        "schema_version": VALIDATION_SUMMARY_SCHEMA_VERSION,
        "counts": counts,
        "has_errors": counts["error"] > 0,
        "has_warnings": counts["warning"] > 0,
        "health_score": health,
    }

    return {"validations": validations, "validation_summary": summary}
