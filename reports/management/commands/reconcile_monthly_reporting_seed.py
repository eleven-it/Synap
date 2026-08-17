# -*- coding: utf-8 -*-
"""
Conciliación seed Monthly Reporting: planillas fuente vs PostgreSQL.

Compara totales pack×cliente×mes del Excel/xlsb contra filas seed importadas.
No escribe en AdministraNET ni modifica seed (dry-run por defecto).

Uso:
  docker exec Synap_app python manage.py reconcile_monthly_reporting_seed
  docker exec Synap_app python manage.py reconcile_monthly_reporting_seed --pack levis_bw
  docker exec Synap_app python manage.py reconcile_monthly_reporting_seed \\
    --source-dir "/Users/sebastian/Documents/Best Sox/fwdreportesjun" \\
    --limit 10
"""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand

from reports.services.monthly_reporting_pack_seed import iter_monthly_reporting_pack_ids
from reports.services.ventas_mensuales_licenciatarios_reconciliation import (
    DEFAULT_SOURCE_DIR,
    FA_NC_REFERENCE_NOTE,
    reconcile_all_packs,
    reconcile_pack_from_file,
    resolve_pack_source_path,
)


class Command(BaseCommand):
    help = (
        "Concilia planillas Monthly Reporting (fwdreportesjun) vs seed PostgreSQL "
        "por pack×cliente×mes. Solo lectura; dry-run por defecto."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--pack",
            choices=list(iter_monthly_reporting_pack_ids()),
            help="Conciliar un solo pack (default: los 6).",
        )
        parser.add_argument(
            "--source-dir",
            default=str(DEFAULT_SOURCE_DIR),
            help="Carpeta con las 6 planillas origen.",
        )
        parser.add_argument(
            "--file",
            help="Ruta explícita al archivo (requiere --pack).",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=2026,
            help="Año calendario del FY.",
        )
        parser.add_argument(
            "--through-month",
            type=int,
            default=6,
            help="Mes máximo seed a conciliar (default 6 = ene–jun).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=15,
            help="Máximo de discrepancias a listar por pack.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=True,
            help="Solo reporta (default). No importa ni altera datos.",
        )

    def handle(self, *args, **options):
        source_dir = Path(options["source_dir"]).expanduser()
        year = options["year"]
        through_month = options["through_month"]
        limit = options["limit"]
        pack_id = options.get("pack")

        self.stdout.write(
            self.style.NOTICE(
                f"Conciliación seed Monthly Reporting — año {year}, meses 1–{through_month}"
            )
        )
        self.stdout.write(f"Directorio fuente: {source_dir}")
        self.stdout.write(f"Modo: {'dry-run (solo lectura)' if options['dry_run'] else 'reporte'}")
        self.stdout.write("")
        self.stdout.write(self.style.NOTICE("Referencia FA/NC (porción ANET ≥22/07):"))
        self.stdout.write(FA_NC_REFERENCE_NOTE)
        self.stdout.write("")

        if pack_id:
            file_path = Path(options["file"]).expanduser() if options["file"] else resolve_pack_source_path(
                pack_id, source_dir
            )
            packs = [
                reconcile_pack_from_file(
                    pack_id,
                    file_path,
                    year=year,
                    through_month=through_month,
                )
            ]
        else:
            result = reconcile_all_packs(
                source_dir=source_dir,
                year=year,
                through_month=through_month,
                dry_run=options["dry_run"],
            )
            packs = result.packs

        total_coincidencias = 0
        total_discrepancias = 0
        for pack_result in packs:
            total_coincidencias += pack_result.coincidencias
            total_discrepancias += len(pack_result.discrepancias)
            self.stdout.write(self.style.HTTP_INFO(f"=== {pack_result.pack_id} ==="))
            self.stdout.write(f"Archivo: {pack_result.file_path}")
            if not pack_result.file_accessible:
                self.stdout.write(self.style.ERROR("  Archivo no accesible desde el contenedor."))
                self.stdout.write(
                    "  Montar la carpeta fuente o usar --file con ruta visible en Synap_app."
                )
                continue
            self.stdout.write(
                f"  Filas archivo (seed): {pack_result.file_row_count} | "
                f"Filas DB: {pack_result.db_row_count} | "
                f"Coincidencias: {pack_result.coincidencias} | "
                f"Discrepancias: {len(pack_result.discrepancias)}"
            )
            if pack_result.ytd_file:
                ytd_units_file = sum(row.units for row in pack_result.ytd_file)
                ytd_amount_file = sum(row.amount for row in pack_result.ytd_file)
                ytd_units_db = sum(row.units for row in pack_result.ytd_db)
                ytd_amount_db = sum(row.amount for row in pack_result.ytd_db)
                self.stdout.write(
                    f"  YTD FY (clientes {len(pack_result.ytd_file)}): "
                    f"archivo units={ytd_units_file} amount={ytd_amount_file} | "
                    f"DB units={ytd_units_db} amount={ytd_amount_db}"
                )
            for mismatch in pack_result.discrepancias[:limit]:
                self.stdout.write(
                    self.style.WARNING(
                        f"  [{mismatch.kind}] {mismatch.customer_name or mismatch.seed_key} "
                        f"{mismatch.month.strftime('%m/%Y') if mismatch.month else ''} "
                        f"file={mismatch.file_value} db={mismatch.db_value}"
                    )
                )
            if len(pack_result.discrepancias) > limit:
                self.stdout.write(
                    f"  … {len(pack_result.discrepancias) - limit} discrepancias más (ver --limit)"
                )
            self.stdout.write("")

        self.stdout.write(
            self.style.SUCCESS(
                f"Resumen: {total_coincidencias} coincidencias, {total_discrepancias} discrepancias"
            )
        )
        if total_discrepancias and not pack_id:
            self.stdout.write(
                self.style.NOTICE(
                    "Si no hay seed importado, ejecutar primero import_monthly_reporting_seed "
                    "por pack antes de conciliar."
                )
            )
