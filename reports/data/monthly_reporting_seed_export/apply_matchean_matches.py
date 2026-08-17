# -*- coding: utf-8 -*-
"""Aplica JSON Matchean a MonthlyReportingClientMatch (idempotente)."""
import json
import re
import unicodedata
from pathlib import Path

from reports.models import MonthlyReportingClientMatch
from reports.services.monthly_reporting_client_match_service import MatchActor, apply_client_match


def norm(s: str) -> str:
    s = (s or "").strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^A-Z0-9&]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def main(path: str = "/app/reports/data/monthly_reporting_client_matches_matchean.json") -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    actor = MatchActor(cod_usuario="system", nombre="Matchean batch 17/08/2026")
    base = payload.get("base_empresa") or "administranet"

    by_norm: dict[str, list] = {}
    for m in MonthlyReportingClientMatch.objects.all():
        by_norm.setdefault(norm(m.seed_customer_name), []).append(m)

    applied = 0
    already = 0
    no_row: list[str] = []
    for item in payload["matches"]:
        key = norm(item["seed_name"])
        rows = by_norm.get(key) or []
        if not rows:
            for k, lst in by_norm.items():
                if not k or not key:
                    continue
                if k == key or k.startswith(key) or key.startswith(k):
                    rows = lst
                    break
        if not rows:
            no_row.append(item["seed_name"])
            continue
        anet_id = int(item["anet_cliente_id"])
        for m in rows:
            if (
                m.estado == MonthlyReportingClientMatch.Estado.MATCHED
                and m.anet_cliente_id == anet_id
            ):
                already += 1
                continue
            apply_client_match(
                m, anet_cliente_id=anet_id, base_empresa=base, actor=actor
            )
            applied += 1

    return {
        "applied": applied,
        "already_ok": already,
        "no_seed_row": len(no_row),
        "no_seed_names": no_row[:40],
        "pending": MonthlyReportingClientMatch.objects.filter(estado="pending").count(),
        "matched": MonthlyReportingClientMatch.objects.filter(estado="matched").count(),
    }


if __name__ == "__main__":
    print(main())
