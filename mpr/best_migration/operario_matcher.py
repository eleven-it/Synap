"""Inferencia letra/código tejedor BEST (TTNOTE) → sue_abm_empleado."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


# Códigos frecuentes documentados (jun 2026) si BEST no responde.
FALLBACK_CODIGOS_TEJEDOR: tuple[str, ...] = (
    "S",
    "R",
    "D",
    "J",
    "L",
    "F",
    "K",
    "M",
    "C",
    "N",
    "V",
    "G",
    "E",
    "T",
    "W",
    "B",
    "P",
)


def norm_text(s: str | None) -> str:
    if not s:
        return ""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def normalizar_codigo_tejedor(codigo: str | None) -> str:
    c = (codigo or "").strip().upper()
    c = re.sub(r"[^A-Z0-9]", "", c)
    return c[:16]


@dataclass
class OperarioMatch:
    best_codigo: str
    best_nombre: str = ""
    movimientos_n: int = 0
    status: str = "SIN_CANDIDATO"  # INFERIDO | AMBIGUO | SIN_CANDIDATO
    score: int | None = None
    razon: str = ""
    admin_id_operario: int | None = None
    admin_nombre: str = ""
    alt1_id_operario: int | None = None
    alt1_nombre: str = ""


def match_operarios(
    *,
    best_rows: list[dict],
    admin_empleados: list[dict],
) -> list[OperarioMatch]:
    """
    best_rows: codigo, nombre?, movimientos_n?
    admin_empleados: id (o id_sue_abm_empleado), label/nombre_empleado
    """
    by_id_manual: dict[str, list[dict]] = {}
    by_inicial: dict[str, list[dict]] = {}
    by_token: dict[str, list[dict]] = {}

    def emp_id(a: dict) -> int | None:
        for k in ("id", "id_sue_abm_empleado", "id_operario"):
            v = a.get(k)
            if v is not None:
                try:
                    return int(v)
                except (TypeError, ValueError):
                    continue
        return None

    def emp_nombre(a: dict) -> str:
        return (a.get("label") or a.get("nombre_empleado") or a.get("nombre") or "").strip()

    for a in admin_empleados:
        aid = emp_id(a)
        if aid is None:
            continue
        nom = emp_nombre(a)
        n = norm_text(nom)
        toks = n.split()
        if toks:
            ini = toks[0][:1]
            if ini:
                by_inicial.setdefault(ini, []).append(a)
            for t in toks:
                if len(t) == 1:
                    by_token.setdefault(t, []).append(a)
                if re.fullmatch(r"[A-Z0-9]{1,4}", t or ""):
                    by_id_manual.setdefault(t, []).append(a)
        # id_manual / código corto en campos opcionales
        for key in ("id_manual", "codigo", "letra", "cod_tejedor"):
            raw = normalizar_codigo_tejedor(str(a.get(key) or ""))
            if raw:
                by_id_manual.setdefault(raw, []).append(a)

    def uniq(rows: list[dict]) -> list[dict]:
        seen: set[int] = set()
        out = []
        for r in rows:
            i = emp_id(r)
            if i is None or i in seen:
                continue
            seen.add(i)
            out.append(r)
        return out

    results: list[OperarioMatch] = []
    for b in best_rows:
        codigo = normalizar_codigo_tejedor(b.get("codigo") or b.get("best_codigo"))
        if not codigo:
            continue
        nombre = (b.get("nombre") or "").strip() or f"Tejedor {codigo}"
        mov_n = int(b.get("movimientos_n") or 0)

        scored: list[tuple[int, str, dict]] = []
        for a in uniq(by_id_manual.get(codigo, [])):
            scored.append((100, "codigo_exacto", a))
        for a in uniq(by_token.get(codigo, [])):
            scored.append((90, "token_nombre", a))
        if len(codigo) == 1:
            for a in uniq(by_inicial.get(codigo, [])):
                scored.append((55, "inicial_nombre", a))

        best_by: dict[int, tuple[int, str, dict]] = {}
        for score, reason, a in scored:
            i = emp_id(a)
            if i is None:
                continue
            prev = best_by.get(i)
            if not prev or score > prev[0]:
                best_by[i] = (score, reason, a)
        ranked = sorted(best_by.values(), key=lambda x: (-x[0], emp_id(x[2]) or 0))

        if not ranked:
            results.append(
                OperarioMatch(
                    best_codigo=codigo,
                    best_nombre=nombre,
                    movimientos_n=mov_n,
                    status="SIN_CANDIDATO",
                )
            )
            continue

        top_score, top_reason, top_a = ranked[0]
        alt = ranked[1] if len(ranked) > 1 else None
        if alt and alt[0] >= top_score - 5 and top_score < 100:
            status = "AMBIGUO"
        elif top_score >= 90:
            status = "INFERIDO"
        elif top_score >= 55 and len(ranked) == 1:
            status = "INFERIDO"
        elif top_score >= 55:
            status = "AMBIGUO"
        else:
            status = "SIN_CANDIDATO"

        results.append(
            OperarioMatch(
                best_codigo=codigo,
                best_nombre=nombre,
                movimientos_n=mov_n,
                status=status,
                score=top_score,
                razon=top_reason,
                admin_id_operario=emp_id(top_a),
                admin_nombre=emp_nombre(top_a)[:255],
                alt1_id_operario=emp_id(alt[2]) if alt else None,
                alt1_nombre=emp_nombre(alt[2])[:255] if alt else "",
            )
        )
    return results
