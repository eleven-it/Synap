# -*- coding: utf-8 -*-
"""Import one-shot de planillas Monthly Reporting seed."""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from reports.services.monthly_reporting_pack_seed import iter_monthly_reporting_pack_ids
from reports.services.ventas_mensuales_licenciatarios_importer import (
    ImportActor,
    ensure_monthly_reporting_packs,
    import_monthly_reporting_file,
)


class Command(BaseCommand):
    help = "Importa planillas seed Monthly Reporting (xlsx/xlsb) de forma idempotente."

    def add_arguments(self, parser):
        parser.add_argument(
            "--pack",
            required=True,
            choices=list(iter_monthly_reporting_pack_ids()),
            help="Identificador del pack licenciatario.",
        )
        parser.add_argument(
            "--file",
            required=True,
            help="Ruta al archivo .xlsx o .xlsb.",
        )
        parser.add_argument(
            "--replace",
            action="store_true",
            help="Reemplaza filas seed coincidentes y registra auditoría.",
        )
        parser.add_argument(
            "--year",
            type=int,
            default=2026,
            help="Año calendario por defecto para columnas de mes.",
        )
        parser.add_argument(
            "--actor-cod",
            default="system",
            help="Código usuario legacy para auditoría.",
        )
        parser.add_argument(
            "--actor-nombre",
            default="Sistema",
            help="Nombre visible del actor para auditoría.",
        )
        parser.add_argument(
            "--seed-packs",
            action="store_true",
            help="Asegura los 6 packs antes de importar.",
        )

    def handle(self, *args, **options):
        if options["seed_packs"]:
            packs = ensure_monthly_reporting_packs()
            self.stdout.write(self.style.SUCCESS(f"Packs asegurados: {len(packs)}"))

        path = Path(options["file"]).expanduser()
        if not path.exists():
            raise CommandError(f"Archivo no encontrado: {path}")

        actor = ImportActor(
            cod_usuario=options["actor_cod"],
            nombre=options["actor_nombre"],
        )
        result = import_monthly_reporting_file(
            options["pack"],
            path,
            replace_mode=options["replace"],
            actor=actor,
            default_year=options["year"],
        )
        batch = result.batch
        if result.duplicate:
            self.stdout.write(
                self.style.WARNING(
                    f"Duplicado detectado (hash {batch.file_sha256[:12]}…); "
                    f"0 altas. Lote #{batch.id}."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS(
                f"Importación aplicada lote #{batch.id}: "
                f"{batch.rows_created} creadas, {batch.rows_updated} actualizadas, "
                f"{batch.rows_skipped} omitidas."
            )
        )
