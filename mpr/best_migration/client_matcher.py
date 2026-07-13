"""Inferencia 1:1 cliente BEST → cliente.Codigo AdministraNET."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher

# Sufijos de campaña / temporada frecuentes en nombres BEST
_SEASON_SUFFIX = re.compile(
    r"[\s\-_]*(FEBRERO|MARZO|ABRIL|MAYO|JUNIO|JULIO|AGOSTO|SEPTIEMBRE|OCTUBRE|NOVIEMBRE|DICIEMBRE|"
    r"ENE|FEB|MAR|ABR|MAY|JUN|JUL|AGO|SEP|OCT|NOV|DIC|"
    r"ARGENTINA|URUGUAY|ECOM|FUTBOL|FÚTBOL)$",
    re.I,
)

# Artículos, conjunciones, formas societarias y nombres personales muy genéricos (AR/es).
_NAME_STOPWORDS = frozenset(
    {
        "DE",
        "DEL",
        "LA",
        "LAS",
        "LOS",
        "EL",
        "LO",
        "Y",
        "E",
        "SA",
        "SRL",
        "SSA",
        "SAS",
        "SOC",
        "LTD",
        "LTDA",
        "CIA",
        "HIJOS",
        "ETC",
        "JOSE",
        "JUAN",
        "MARIA",
        "CARLOS",
        "PEDRO",
        "ANA",
        "LUIS",
        "MIGUEL",
        "ANTONIO",
        "FRANCISCO",
        "MANUEL",
        "ROSA",
        "TERESA",
    }
)

_MIN_SIGNIFICANT_TOKEN_LEN = 4
_FUZZY_MIN_TOKEN_LEN = 5
_FUZZY_RATIO = 0.85


def norm_text(s: str | None) -> str:
    if not s:
        return ""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def norm_cuit(s: str | None) -> str:
    digits = re.sub(r"\D", "", str(s or ""))
    return digits if len(digits) >= 8 else ""


def base_campaign_name(nombre: str | None) -> str:
    """ATOMIK-FEBRERO → ATOMIK; PUMA ECOM → PUMA; LEVIS-AGOSTO ARGENTINA → LEVIS."""
    n = norm_text(nombre)
    if not n:
        return ""
    # quitar sufijos repetidos
    prev = None
    while prev != n:
        prev = n
        n = _SEASON_SUFFIX.sub("", n).strip()
    # primera palabra significativa si quedó compuesto
    parts = n.split()
    if len(parts) >= 2 and parts[0] in {"PUMA", "LEVIS", "ATOMIK", "REEF", "KAMP", "HEAD"}:
        return parts[0]
    return n


def significant_tokens(text: str | None) -> list[str]:
    """Tokens ≥ 4 caracteres excluyendo stopwords comerciales/personales."""
    return [
        t
        for t in norm_text(text).split()
        if len(t) >= _MIN_SIGNIFICANT_TOKEN_LEN and t not in _NAME_STOPWORDS
    ]


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        curr = [i]
        for j, cb in enumerate(b, 1):
            curr.append(min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = curr
    return prev[-1]


def tokens_match_fuzzy(t1: str, t2: str) -> bool:
    """Coincidencia exacta o aproximada entre tokens (p. ej. GRECO / GRECCO)."""
    if t1 == t2:
        return True
    if len(t1) < _FUZZY_MIN_TOKEN_LEN or len(t2) < _FUZZY_MIN_TOKEN_LEN:
        return False
    if t1 in t2 or t2 in t1:
        return True
    if SequenceMatcher(None, t1, t2).ratio() >= _FUZZY_RATIO:
        return True
    return _levenshtein(t1, t2) <= 1


def shared_significant_tokens(
    tokens_a: list[str],
    tokens_b: list[str],
) -> list[str]:
    """Lista de etiquetas de tokens compartidos (exactos o fuzzy)."""
    shared: list[str] = []
    used_b: set[int] = set()
    for ta in tokens_a:
        for idx, tb in enumerate(tokens_b):
            if idx in used_b:
                continue
            if tokens_match_fuzzy(ta, tb):
                label = ta if ta == tb else f"{ta}~{tb}"
                shared.append(label)
                used_b.add(idx)
                break
    return shared


def score_shared_tokens(n_shared: int, labels: list[str]) -> tuple[int, str]:
    """Score y razón para coincidencia por tokens significativos."""
    if n_shared <= 0:
        return 0, ""
    if n_shared == 1:
        label = labels[0]
        prefix = "token_fuzzy" if "~" in label else "token_compartido"
        return 60, f"{prefix}:{label}"
    score = min(72, 65 + (n_shared - 2) * 3)
    return score, f"tokens_compartidos:{','.join(labels[:4])}"


@dataclass
class ClientMatch:
    best_cliente: str
    best_cuit: str
    ordenes_abiertas: int
    status: str  # INFERIDO | AMBIGUO | SIN_CANDIDATO | PENDIENTE
    score: int | None = None
    razon: str = ""
    admin_codigo: int | None = None
    admin_nombre: str = ""
    alt1_codigo: int | None = None
    alt1_nombre: str = ""
    alt1_score: int | None = None


def match_clients(
    *,
    best_rows: list[dict],
    admin_clients: list[dict],
) -> list[ClientMatch]:
    """
    best_rows: best_cliente, best_cuit, ordenes_abiertas
    admin_clients: Codigo, nombre_cliente, CUIT, id_manual_cli, nombre_fantasia
    """
    by_cuit: dict[str, list[dict]] = defaultdict(list)
    by_name: dict[str, list[dict]] = defaultdict(list)
    by_manual: dict[str, list[dict]] = defaultdict(list)
    by_base: dict[str, list[dict]] = defaultdict(list)

    for a in admin_clients:
        cu = norm_cuit(a.get("CUIT"))
        if cu:
            by_cuit[cu].append(a)
        for key in (
            norm_text(a.get("nombre_cliente")),
            norm_text(a.get("nombre_fantasia")),
        ):
            if key:
                by_name[key].append(a)
                b = base_campaign_name(key)
                if b:
                    by_base[b].append(a)
        im = norm_text(a.get("id_manual_cli"))
        if im:
            by_manual[im].append(a)

    def uniq(rows: list[dict]) -> list[dict]:
        seen: set[int] = set()
        out = []
        for r in rows:
            c = int(r["Codigo"])
            if c not in seen:
                seen.add(c)
                out.append(r)
        return out

    results: list[ClientMatch] = []
    for b in best_rows:
        nombre = (b.get("best_cliente") or "").strip() or "(sin nombre)"
        cuit_raw = (b.get("best_cuit") or "").strip()
        ordenes = int(b.get("ordenes_abiertas") or 0)
        cu = norm_cuit(cuit_raw)
        nm = norm_text(nombre)
        base = base_campaign_name(nombre)

        scored: list[tuple[int, str, dict]] = []

        if cu and by_cuit.get(cu):
            for a in uniq(by_cuit[cu]):
                scored.append((100, "cuit_exacto", a))

        if nm and by_name.get(nm):
            for a in uniq(by_name[nm]):
                scored.append((90, "nombre_exacto", a))

        if nm and by_manual.get(nm):
            for a in uniq(by_manual[nm]):
                scored.append((85, "id_manual_exacto", a))

        if base and by_base.get(base):
            for a in uniq(by_base[base]):
                scored.append((70, f"base_campana:{base}", a))

        # contains / token overlap (Jaccard)
        if nm:
            for key, rows in by_name.items():
                if not key or key == nm:
                    continue
                if nm in key or key in nm:
                    for a in uniq(rows):
                        scored.append((55, "nombre_contiene", a))
                else:
                    t1, t2 = set(nm.split()), set(key.split())
                    if t1 and t2:
                        j = len(t1 & t2) / len(t1 | t2)
                        if j >= 0.6:
                            for a in uniq(rows):
                                scored.append((50 + int(j * 20), f"jaccard_{j:.2f}", a))

        # tokens significativos compartidos (exacto o fuzzy)
        best_sig = significant_tokens(nm) if nm else []
        if best_sig:
            for key, rows in by_name.items():
                if not key or key == nm:
                    continue
                admin_sig = significant_tokens(key)
                if not admin_sig:
                    continue
                labels = shared_significant_tokens(best_sig, admin_sig)
                score, reason = score_shared_tokens(len(labels), labels)
                if score >= 55:
                    for a in uniq(rows):
                        scored.append((score, reason, a))

        # dedupe by Codigo keeping best score
        best_by_code: dict[int, tuple[int, str, dict]] = {}
        for score, reason, a in scored:
            code = int(a["Codigo"])
            prev = best_by_code.get(code)
            if not prev or score > prev[0]:
                best_by_code[code] = (score, reason, a)
        ranked = sorted(best_by_code.values(), key=lambda x: (-x[0], int(x[2]["Codigo"])))

        if not ranked:
            results.append(
                ClientMatch(
                    best_cliente=nombre,
                    best_cuit=cuit_raw,
                    ordenes_abiertas=ordenes,
                    status="SIN_CANDIDATO",
                )
            )
            continue

        top_score, top_reason, top_a = ranked[0]
        amb = False
        if len(ranked) > 1 and ranked[1][0] >= top_score - 5 and ranked[1][0] >= 55:
            if norm_text(ranked[1][2].get("nombre_cliente")) != norm_text(top_a.get("nombre_cliente")):
                amb = True

        if top_score >= 85 and not amb:
            status = "INFERIDO"
        elif amb:
            status = "AMBIGUO"
        elif top_score >= 55:
            status = "INFERIDO"  # medio: aún aceptable para aceptar/revisar
            if top_score < 70:
                status = "AMBIGUO"
        else:
            status = "SIN_CANDIDATO"

        alt = ranked[1] if len(ranked) > 1 else None
        results.append(
            ClientMatch(
                best_cliente=nombre,
                best_cuit=cuit_raw,
                ordenes_abiertas=ordenes,
                status=status,
                score=top_score,
                razon=top_reason,
                admin_codigo=int(top_a["Codigo"]),
                admin_nombre=(top_a.get("nombre_cliente") or "")[:255],
                alt1_codigo=int(alt[2]["Codigo"]) if alt else None,
                alt1_nombre=(alt[2].get("nombre_cliente") or "")[:255] if alt else "",
                alt1_score=alt[0] if alt else None,
            )
        )
    return results
