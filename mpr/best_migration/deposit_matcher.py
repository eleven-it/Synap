"""Inferencia depósito BEST (Id Deposito) → deposito.CodDeposito AdministraNET."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

BEST_DEPOSITO_TIPO_MPR: dict[int, str] = {
    4000: "Produccion",
    4002: "SemiElaborado",
    4003: "Terminado",
    4004: "2daSeleccion",
}

# Palabras clave en nombre Admin para fallback por similitud
_NOMBRE_KEYWORDS: list[tuple[str, str]] = [
    ("PRODUCCION", "Produccion"),
    ("PRODUCCI", "Produccion"),
    ("SEMI", "SemiElaborado"),
    ("EMBALADO", "SemiElaborado"),
    ("ELABORADO", "SemiElaborado"),
    ("TERMINADO", "Terminado"),
    ("SEGUNDA", "2daSeleccion"),
    ("2DA", "2daSeleccion"),
    ("SOBRANTE", "2daSeleccion"),
    ("DESPERDICIO", "Scrap"),
    ("SCRAP", "Scrap"),
    ("PLANCHADO", "Planchado"),
]


def norm_text(s: str | None) -> str:
    if not s:
        return ""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class DepositoMatch:
    best_id_deposito: int
    best_nombre: str
    tipo_mpr_esperado: str
    status: str  # INFERIDO | SIN_CANDIDATO | PENDIENTE
    score: int | None = None
    razon: str = ""
    admin_cod_deposito: int | None = None
    admin_nombre: str = ""
    admin_tipo_mpr: str = ""


def _tipo_por_nombre(nombre: str) -> str | None:
    n = norm_text(nombre)
    if not n:
        return None
    for kw, tipo in _NOMBRE_KEYWORDS:
        if kw in n:
            return tipo
    return None


def match_depositos(
    *,
    best_rows: list[dict],
    admin_depositos: list[dict],
) -> list[DepositoMatch]:
    """
    best_rows: id_dep, nombre, stock_pares (opcional), skus (opcional)
    admin_depositos: CodDeposito, NombreDeposito, tipo_mpr
    """
    by_tipo: dict[str, list[dict]] = {}
    by_name: dict[str, list[dict]] = {}

    for d in admin_depositos:
        tipo = (d.get("tipo_mpr") or "").strip()
        if tipo:
            by_tipo.setdefault(tipo, []).append(d)
        nm = norm_text(d.get("NombreDeposito"))
        if nm:
            by_name.setdefault(nm, []).append(d)

    def uniq(rows: list[dict]) -> list[dict]:
        seen: set[int] = set()
        out = []
        for r in rows:
            c = int(r["CodDeposito"])
            if c not in seen:
                seen.add(c)
                out.append(r)
        return out

    results: list[DepositoMatch] = []
    for b in best_rows:
        best_id = int(b["id_dep"])
        nombre = (b.get("nombre") or "").strip() or f"Depósito {best_id}"
        tipo_esperado = BEST_DEPOSITO_TIPO_MPR.get(best_id) or _tipo_por_nombre(nombre) or ""

        scored: list[tuple[int, str, dict]] = []

        if tipo_esperado and by_tipo.get(tipo_esperado):
            for a in uniq(by_tipo[tipo_esperado]):
                scored.append((100, f"tipo_mpr:{tipo_esperado}", a))

        nm_best = norm_text(nombre)
        if nm_best and by_name.get(nm_best):
            for a in uniq(by_name[nm_best]):
                scored.append((95, "nombre_exacto", a))

        if tipo_esperado:
            for key, rows in by_name.items():
                tipo_nombre = _tipo_por_nombre(key)
                if tipo_nombre == tipo_esperado:
                    for a in uniq(rows):
                        scored.append((80, f"nombre_tipo:{tipo_esperado}", a))

        if nm_best:
            for key, rows in by_name.items():
                if not key:
                    continue
                if nm_best in key or key in nm_best:
                    for a in uniq(rows):
                        scored.append((60, "nombre_contiene", a))

        best_by_code: dict[int, tuple[int, str, dict]] = {}
        for score, reason, a in scored:
            code = int(a["CodDeposito"])
            prev = best_by_code.get(code)
            if not prev or score > prev[0]:
                best_by_code[code] = (score, reason, a)
        ranked = sorted(best_by_code.values(), key=lambda x: (-x[0], int(x[2]["CodDeposito"])))

        if not ranked:
            results.append(
                DepositoMatch(
                    best_id_deposito=best_id,
                    best_nombre=nombre,
                    tipo_mpr_esperado=tipo_esperado,
                    status="SIN_CANDIDATO",
                )
            )
            continue

        top_score, top_reason, top_a = ranked[0]
        status = "INFERIDO" if top_score >= 60 else "SIN_CANDIDATO"
        results.append(
            DepositoMatch(
                best_id_deposito=best_id,
                best_nombre=nombre,
                tipo_mpr_esperado=tipo_esperado,
                status=status,
                score=top_score,
                razon=top_reason,
                admin_cod_deposito=int(top_a["CodDeposito"]),
                admin_nombre=(top_a.get("NombreDeposito") or "")[:255],
                admin_tipo_mpr=((top_a.get("tipo_mpr") or "").strip())[:32],
            )
        )
    return results
