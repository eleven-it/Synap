"""Inferencia 1:1 BEST Id Articulo → articulo.IDArt (solo lectura sobre orígenes)."""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from mpr.best_migration.dictionary import (
    COLOR_WORD_TO_CODE,
    DICT_VERSION,
    KNOWN_COLOR_CODES,
    TALLE_ADMIN_TO_BEST,
)


def norm(s: Any) -> str:
    if s is None:
        return ""
    s = str(s).strip().upper()
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
    s = re.sub(r"[^A-Z0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def tokens(s: Any) -> set[str]:
    return set(norm(s).split()) if s else set()


def parse_mmid(mmid: str | None) -> tuple[str | None, list[str], str | None]:
    m = re.match(r"^[A-Z]{1,4}(\d{3,6})([A-Z0-9]+?)(\d)$", (mmid or "").upper())
    if not m:
        return None, [], None
    model, blob, talle = m.group(1), m.group(2), m.group(3)
    cols: list[str] = []
    i = 0
    while i < len(blob):
        two = blob[i : i + 2]
        if two in KNOWN_COLOR_CODES:
            cols.append(two)
            i += 2
        else:
            i += 1
    return model, cols, talle


def models_from_best(codigo: str | None, mmid: str | None, articulo: str | None) -> list[str]:
    models: list[str] = []

    def add(x: str | None) -> None:
        if x and x not in models:
            models.append(x)

    m = re.search(r"[A-Z]{1,4}(\d{3,6})", str(mmid or "").upper())
    if m:
        add(m.group(1))
    if codigo:
        m = re.search(r"(\d{3,6})", str(codigo))
        if m:
            add(m.group(1))
    text = articulo or ""
    for m in re.finditer(r"(?<![A-Z0-9])(\d{3,6})(?![0-9])", text):
        add(m.group(1))
    for m in re.finditer(r"\((\d{3,6})\)\s*(\d{3,6})", text):
        add(m.group(1))
        add(m.group(2))
    return models


def extract_variant_codes(articulo: str | None, codigo: str | None, mmid: str | None) -> set[str]:
    codes: set[str] = set()
    text = " ".join([str(x or "") for x in (articulo, codigo, mmid)])
    for m in re.finditer(r"\b(\d{3,6})-([A-Z]?\d{2,4})\b", text, flags=re.I):
        base, var = m.group(1), m.group(2).upper()
        codes.add(f"{base}-{var}")
        if len(base) == 4:
            codes.add(f"90{base}-{var}")
        if len(base) == 6 and base.startswith("90"):
            codes.add(f"{base[2:]}-{var}")
    return codes


def parse_admin_talle(nombre: str | None, codprov: str | None) -> str | None:
    s = norm(f"{nombre or ''} {codprov or ''}")
    for tok in ("T130", "T120", "T110", "T6", "T5", "T4", "T3", "T2", "T1", "TL", "TM"):
        if re.search(rf"\b{tok}\b", s):
            return TALLE_ADMIN_TO_BEST.get(tok)
    return None


def parse_admin_pack(nombre: str | None) -> str | None:
    s = norm(nombre)
    if re.search(r"\b1PAR\b", s):
        return "1"
    if re.search(r"\b3P\b", s) or re.search(r"\b3PAR\b", s) or re.search(r"\bX3\b", s):
        return "3"
    if re.search(r"\b2P\b", s) or re.search(r"\b2PAR\b", s) or "BIPACK" in s or re.search(r"\bX2\b", s):
        return "2"
    if re.search(r"\b1P\b", s):
        return "1"
    return None


def parse_admin_color_profile(nombre: str | None) -> dict:
    s = norm(nombre)
    toks = s.split()
    codes: list[str] = []
    for t in toks:
        if t in COLOR_WORD_TO_CODE:
            codes.append(COLOR_WORD_TO_CODE[t])
        elif t in KNOWN_COLOR_CODES:
            codes.append(t)
    has_mix = "MIX" in toks
    has_logo = "LOGO" in toks
    primary = logo = None
    if has_logo and "LOGO" in toks:
        i = toks.index("LOGO")
        before = [COLOR_WORD_TO_CODE[t] for t in toks[:i] if t in COLOR_WORD_TO_CODE]
        after = [COLOR_WORD_TO_CODE[t] for t in toks[i + 1 :] if t in COLOR_WORD_TO_CODE]
        primary = before[-1] if before else (codes[0] if codes else None)
        logo = after[0] if after else None
        mode = "logo"
    elif has_mix:
        mode = "mix"
    elif codes:
        mode = "solid"
        primary = codes[0]
    else:
        mode = "unknown"
    return {"mode": mode, "primary": primary, "logo": logo, "codes": codes}


def best_color_profile(cols: list[str]) -> dict:
    if not cols:
        return {"mode": "unknown", "primary": None, "unique": []}
    uniq: list[str] = []
    for c in cols:
        if c not in uniq:
            uniq.append(c)
    if len(uniq) == 1:
        return {"mode": "solid", "primary": uniq[0], "unique": uniq}
    return {"mode": "mix", "primary": uniq[0], "unique": uniq}


def _score_color(bp: dict, ap: dict) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    if bp["mode"] == "solid":
        if ap["mode"] == "solid" and ap["primary"] == bp["primary"]:
            score += 30
            reasons.append("color_solid")
        elif ap["mode"] == "logo" and ap["primary"] == bp["primary"]:
            score -= 15
            reasons.append("color_logo_vs_solid")
        elif ap["mode"] == "mix":
            score -= 20
            reasons.append("color_mix_vs_solid")
        elif ap["mode"] == "solid" and ap["primary"] != bp["primary"]:
            score -= 25
            reasons.append("color_solid_diff")
    elif bp["mode"] == "mix":
        if ap["mode"] == "mix":
            score += 30
            reasons.append("color_mix")
        elif ap["mode"] == "logo":
            bu = set(bp["unique"])
            aps = {ap["primary"], ap["logo"]} - {None}
            if bu == aps or bu <= aps or aps <= bu:
                score += 10
                reasons.append("color_logo_as_mix_partial")
            else:
                score -= 5
                reasons.append("color_logo_weak")
        elif ap["mode"] == "solid":
            if ap["primary"] in bp["unique"]:
                score -= 10
                reasons.append("color_solid_partial_mix")
            else:
                score -= 20
                reasons.append("color_solid_vs_mix")
    inter = set(bp.get("unique") or []) & set(ap.get("codes") or [])
    if inter and "color_solid" not in reasons and "color_mix" not in reasons:
        score += 3 * len(inter)
        reasons.append(f"color_tok_{len(inter)}")
    return score, reasons


def _score_pack(bp: str | None, ap: str | None) -> tuple[int, list[str]]:
    if not bp or not ap:
        return 0, []
    if str(bp) == str(ap):
        return 25, ["pack"]
    if (str(bp) in ("2", "3") and str(ap) == "1") or (str(bp) == "1" and str(ap) in ("2", "3")):
        return -30, ["pack_mismatch_1par"]
    return -15, ["pack_diff"]


def _score_talle(bt: str | None, at: str | None) -> tuple[int, list[str]]:
    if not bt or not at:
        return 0, []
    if str(bt) == str(at):
        return 25, ["talle"]
    return -20, ["talle_diff"]


@dataclass
class MatchRow:
    best_id_articulo: str
    best_codigo: str = ""
    best_articulo: str = ""
    best_marca: str = ""
    best_modelos: str = ""
    best_colores: str = ""
    best_color_mode: str = ""
    best_talle: str = ""
    best_pack: str = ""
    best_variant_codes: str = ""
    status: str = "SIN_CANDIDATO"
    score: int | None = None
    razon: str = ""
    admin_idart: int | None = None
    admin_id_manual: str = ""
    admin_nombre: str = ""
    admin_cod_art_prov: str = ""
    admin_pack: str = ""
    admin_talle: str = ""
    admin_color_mode: str = ""
    candidatos_n: int = 0
    alt1_idart: int | None = None
    alt1_nombre: str = ""
    alt1_score: int | None = None
    alt2_idart: int | None = None
    alt2_nombre: str = ""
    alt2_score: int | None = None
    dict_version: str = DICT_VERSION
    extras: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("extras", None)
        return d


STATUS_INFERIDO_ALTO = "INFERIDO_ALTO"
STATUS_INFERIDO_MEDIO = "INFERIDO_MEDIO"
STATUS_INFERIDO_BAJO = "INFERIDO_BAJO"
STATUS_AMBIGUO = "AMBIGUO"
STATUS_SIN_CANDIDATO = "SIN_CANDIDATO"
STATUS_SIN_MATCH = "SIN_MATCH"
STATUS_CONFLICTO = "CONFLICTO_1_A_N"


def match_open_order_skus(
    *,
    best_rows: list[dict],
    myl_by_mmid: dict[str, dict],
    admin_arts: list[dict],
) -> list[MatchRow]:
    """
    best_rows: id_articulo, codigo, articulo, marca
    admin_arts: IDArt, id_manual, NombreArticulo, CodArtProv
        (universo tipicamente filtrado a tipo_art_fab=Terminado por el caller)
    """
    by_model: dict[str, list[dict]] = defaultdict(list)
    by_variant: dict[str, list[dict]] = defaultdict(list)

    for a in admin_arts:
        im = (a.get("id_manual") or "").strip()
        nom = a.get("NombreArticulo") or ""
        if re.fullmatch(r"\d{3,6}", im or ""):
            by_model[im].append(a)
        m = re.match(r"^(\d{3,6})\b", nom)
        if m:
            by_model[m.group(1)].append(a)
        if re.fullmatch(r"90\d{4}", im or ""):
            by_model[im[2:]].append(a)
        for m in re.finditer(
            r"\b(\d{3,6})-([A-Z0-9]{2,5})\b",
            f"{nom} {a.get('CodArtProv') or ''}",
            flags=re.I,
        ):
            key = f"{m.group(1)}-{m.group(2).upper()}"
            by_variant[key].append(a)
            if len(m.group(1)) == 6 and m.group(1).startswith("90"):
                by_variant[f"{m.group(1)[2:]}-{m.group(2).upper()}"].append(a)
            if len(m.group(1)) == 4:
                by_variant[f"90{m.group(1)}-{m.group(2).upper()}"].append(a)

    for d in (by_model, by_variant):
        for k in list(d):
            seen: set[int] = set()
            uniq = []
            for a in d[k]:
                aid = int(a["IDArt"])
                if aid not in seen:
                    seen.add(aid)
                    uniq.append(a)
            d[k] = uniq

    results: list[MatchRow] = []
    for b in best_rows:
        mmid = str(b.get("id_articulo") or "").strip()
        if not mmid:
            continue
        attrs = myl_by_mmid.get(mmid) or {}
        codigo = b.get("codigo") or attrs.get("CODIGO")
        articulo = b.get("articulo") or ""
        model_mmid, cols, talle_mmid = parse_mmid(mmid)
        models = models_from_best(codigo, mmid, articulo)
        if model_mmid and model_mmid not in models:
            models.insert(0, model_mmid)
        talle = str(attrs.get("TALLE") or talle_mmid or "").strip()
        pack = str(attrs.get("PACK") or "").strip()
        if not cols:
            for k in ("COLOR", "COLOR1", "COLOR2", "COLOR3"):
                v = attrs.get(k)
                if v and str(v).strip():
                    cols.append(str(v).strip().upper())
        bprof = best_color_profile(cols)
        variants = extract_variant_codes(articulo, codigo, mmid)

        cand: dict[int, dict] = {}
        exact = [a for a in admin_arts if (a.get("id_manual") or "").upper() == mmid.upper()]
        for a in exact:
            cand[int(a["IDArt"])] = a
        for model in models:
            for a in by_model.get(model, []):
                cand[int(a["IDArt"])] = a
            for a in by_model.get("90" + model, []):
                cand[int(a["IDArt"])] = a
        for vc in variants:
            for a in by_variant.get(vc, []):
                cand[int(a["IDArt"])] = a

        scored: list[tuple[int, str, dict]] = []
        if exact:
            for a in exact:
                scored.append((100, "A_exact_id_manual", a))
        for a in cand.values():
            if a in exact:
                continue
            score = 0
            reasons: list[str] = []
            im = (a.get("id_manual") or "").strip()
            nom = a.get("NombreArticulo") or ""
            model_hit = any(
                im in (model, "90" + model) or nom.startswith(model) or nom.startswith("90" + model)
                for model in models
            )
            score += 35 if model_hit else 15
            reasons.append("B_model" if model_hit else "B_model_weak")

            for vc in variants:
                blob = f"{nom} {a.get('CodArtProv') or ''}".upper()
                if vc.upper() in blob or vc.replace("-", "") in norm(blob).replace(" ", ""):
                    score += 35
                    reasons.append("variant_code")
                    break

            at = parse_admin_talle(nom, a.get("CodArtProv"))
            ap = parse_admin_pack(nom)
            aprof = parse_admin_color_profile(nom)
            sc, rs = _score_talle(talle, at)
            score += sc
            reasons += rs
            sc, rs = _score_pack(pack, ap)
            score += sc
            reasons += rs
            sc, rs = _score_color(bprof, aprof)
            score += sc
            reasons += rs
            marca = norm(b.get("marca") or attrs.get("MARCADS") or "")
            if marca and marca in norm(nom):
                score += 5
                reasons.append("marca")
            bt = tokens(articulo)
            atok = tokens(nom)
            if bt and atok:
                j = len(bt & atok) / len(bt | atok)
                score += int(j * 15)
                if j >= 0.4:
                    reasons.append(f"jaccard_{j:.2f}")
            scored.append((score, "+".join(reasons), a))

        scored.sort(key=lambda x: (-x[0], int(x[2]["IDArt"])))

        if not scored:
            row = MatchRow(
                best_id_articulo=mmid,
                best_codigo=str(codigo or ""),
                best_articulo=articulo,
                best_marca=str(b.get("marca") or ""),
                best_modelos="|".join(models),
                best_colores="/".join(cols),
                best_color_mode=bprof["mode"],
                best_talle=talle,
                best_pack=pack,
                best_variant_codes="|".join(sorted(variants)),
                status=STATUS_SIN_CANDIDATO,
            )
            results.append(row)
            continue

        top_score, top_reason, top_a = scored[0]
        amb = False
        if len(scored) > 1 and scored[1][0] >= top_score - 5 and scored[1][0] >= 55:
            if norm(scored[1][2].get("NombreArticulo")) != norm(top_a.get("NombreArticulo")):
                amb = True
        if top_score >= 95 and not amb:
            status = STATUS_INFERIDO_ALTO
        elif top_score >= 75 and not amb:
            status = STATUS_INFERIDO_MEDIO
        elif amb:
            status = STATUS_AMBIGUO
        elif top_score >= 55:
            status = STATUS_INFERIDO_BAJO
        else:
            status = STATUS_SIN_MATCH

        top3 = scored[:3]
        row = MatchRow(
            best_id_articulo=mmid,
            best_codigo=str(codigo or ""),
            best_articulo=articulo,
            best_marca=str(b.get("marca") or ""),
            best_modelos="|".join(models),
            best_colores="/".join(cols),
            best_color_mode=bprof["mode"],
            best_talle=talle,
            best_pack=pack,
            best_variant_codes="|".join(sorted(variants)),
            status=status,
            score=top_score,
            razon=top_reason,
            admin_idart=int(top_a["IDArt"]),
            admin_id_manual=(top_a.get("id_manual") or "").strip(),
            admin_nombre=top_a.get("NombreArticulo") or "",
            admin_cod_art_prov=(top_a.get("CodArtProv") or "").strip(),
            admin_pack=parse_admin_pack(top_a.get("NombreArticulo")) or "",
            admin_talle=parse_admin_talle(top_a.get("NombreArticulo"), top_a.get("CodArtProv")) or "",
            admin_color_mode=parse_admin_color_profile(top_a.get("NombreArticulo"))["mode"],
            candidatos_n=len(scored),
            alt1_idart=int(top3[1][2]["IDArt"]) if len(top3) > 1 else None,
            alt1_nombre=(top3[1][2].get("NombreArticulo") or "") if len(top3) > 1 else "",
            alt1_score=top3[1][0] if len(top3) > 1 else None,
            alt2_idart=int(top3[2][2]["IDArt"]) if len(top3) > 2 else None,
            alt2_nombre=(top3[2][2].get("NombreArticulo") or "") if len(top3) > 2 else "",
            alt2_score=top3[2][0] if len(top3) > 2 else None,
        )
        results.append(row)

    # conflictos 1:N entre inferidos altos/medios
    claimed: dict[int, list[str]] = defaultdict(list)
    for r in results:
        if r.admin_idart and r.status in (STATUS_INFERIDO_ALTO, STATUS_INFERIDO_MEDIO):
            claimed[r.admin_idart].append(r.best_id_articulo)
    for r in results:
        if (
            r.admin_idart
            and len(claimed.get(r.admin_idart, [])) > 1
            and r.status in (STATUS_INFERIDO_ALTO, STATUS_INFERIDO_MEDIO)
        ):
            r.status = STATUS_CONFLICTO
            r.razon = (r.razon or "") + "+conflicto_IDArt"

    return results
