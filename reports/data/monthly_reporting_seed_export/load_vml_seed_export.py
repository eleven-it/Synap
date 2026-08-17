# -*- coding: utf-8 -*-
"""
Carga export CSV de Monthly Reporting (VML) en el Postgres Synap actual.

Uso en Server2 (desde /app o con CSVs montados):

  docker exec -i Synap_app python manage.py shell < /app/tmp_exports/load_vml_seed_export.py

O:

  docker exec Synap_app python manage.py shell -c "exec(open('/app/tmp_exports/load_vml_seed_export.py').read())"

Requiere en el mismo dir (o EXPORT_DIR):
  vml_clientmatch.csv, vml_importbatch.csv, vml_seedrow.csv
"""
from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from reports.models import (
    MonthlyReportingClientMatch,
    MonthlyReportingImportBatch,
    MonthlyReportingPack,
    MonthlyReportingSeedRow,
)

EXPORT_DIR = Path(
    os.environ.get(
        "VML_EXPORT_DIR",
        "/app/reports/data/monthly_reporting_seed_export",
    )
)


def _parse_dt(value: str):
    if not value:
        return None
    dt = parse_datetime(value)
    if dt is None:
        # CSV de Postgres a veces sin TZ explícita
        try:
            dt = datetime.fromisoformat(value.replace(" ", "T"))
        except ValueError:
            return None
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def _dec(value: str) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(value)


@transaction.atomic
def load_export(export_dir: Path = EXPORT_DIR) -> dict:
    packs = {p.pack_id: p for p in MonthlyReportingPack.objects.all()}
    if len(packs) < 6:
        raise RuntimeError(f"Se esperaban 6 packs; hay {len(packs)}: {sorted(packs)}")

    # Limpiar datos seed (no toca packs ni SuperArt)
    MonthlyReportingSeedRow.objects.all().delete()
    MonthlyReportingImportBatch.objects.all().delete()
    MonthlyReportingClientMatch.objects.all().delete()

    match_by_key: dict[str, MonthlyReportingClientMatch] = {}
    with (export_dir / "vml_clientmatch.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            m = MonthlyReportingClientMatch(
                seed_key=row["seed_key"],
                seed_customer_code=row.get("seed_customer_code") or "",
                seed_customer_name=row["seed_customer_name"],
                seed_city=row.get("seed_city") or "",
                seed_store_type=row.get("seed_store_type") or "",
                seed_product_group=row.get("seed_product_group") or "",
                seed_uf=row.get("seed_uf") or "",
                base_empresa=row.get("base_empresa") or "",
                anet_cliente_id=int(row["anet_cliente_id"]) if row.get("anet_cliente_id") else None,
                estado=row.get("estado") or MonthlyReportingClientMatch.Estado.PENDING,
                actor_id_usuario=int(row["actor_id_usuario"]) if row.get("actor_id_usuario") else None,
                actor_cod_usuario=row.get("actor_cod_usuario") or "",
                actor_nombre=row.get("actor_nombre") or "",
            )
            # created/updated se setean al save; forzar si vienen
            m.save()
            ca, ua = _parse_dt(row.get("created_at") or ""), _parse_dt(row.get("updated_at") or "")
            updates = []
            if ca:
                m.created_at = ca
                updates.append("created_at")
            if ua:
                m.updated_at = ua
                updates.append("updated_at")
            if updates:
                MonthlyReportingClientMatch.objects.filter(pk=m.pk).update(
                    **{f: getattr(m, f) for f in updates}
                )
            match_by_key[m.seed_key] = m

    batch_by_sha: dict[str, MonthlyReportingImportBatch] = {}
    with (export_dir / "vml_importbatch.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            pack = packs[row["pack_slug"]]
            audit = row.get("audit_json") or "{}"
            try:
                audit_json = json.loads(audit)
            except json.JSONDecodeError:
                audit_json = {}
            b = MonthlyReportingImportBatch.objects.create(
                pack=pack,
                file_name=row["file_name"],
                file_size=int(row.get("file_size") or 0),
                file_format=row.get("file_format") or "xlsx",
                file_sha256=row["file_sha256"],
                replace_mode=str(row.get("replace_mode")).lower() in ("t", "true", "1"),
                estado=row.get("estado") or "applied",
                rows_created=int(row.get("rows_created") or 0),
                rows_updated=int(row.get("rows_updated") or 0),
                rows_skipped=int(row.get("rows_skipped") or 0),
                error_message=row.get("error_message") or "",
                actor_id_usuario=int(row["actor_id_usuario"]) if row.get("actor_id_usuario") else None,
                actor_cod_usuario=row.get("actor_cod_usuario") or "",
                actor_nombre=row.get("actor_nombre") or "",
                audit_json=audit_json,
                applied_at=_parse_dt(row.get("applied_at") or "") or timezone.now(),
            )
            batch_by_sha[row["file_sha256"]] = b

    seed_created = 0
    with (export_dir / "vml_seedrow.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            pack = packs[row["pack_slug"]]
            match = match_by_key[row["seed_key"]]
            batch = batch_by_sha[row["batch_sha"]]
            MonthlyReportingSeedRow.objects.create(
                pack=pack,
                match=match,
                batch=batch,
                month=row["month"],
                units=_dec(row.get("units")),
                amount=_dec(row.get("amount")),
                units_men=_dec(row.get("units_men")),
                units_women=_dec(row.get("units_women")),
                amount_men=_dec(row.get("amount_men")),
                amount_women=_dec(row.get("amount_women")),
                city=row.get("city") or "",
                store_type=row.get("store_type") or "",
                uf=row.get("uf") or "",
            )
            seed_created += 1

    return {
        "matches": len(match_by_key),
        "batches": len(batch_by_sha),
        "seed_rows": seed_created,
        "pending": MonthlyReportingClientMatch.objects.filter(estado="pending").count(),
        "matched": MonthlyReportingClientMatch.objects.filter(estado="matched").count(),
    }


result = load_export()
print("OK VML seed cargado:", result)
