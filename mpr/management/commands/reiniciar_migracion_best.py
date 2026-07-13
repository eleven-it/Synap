"""Reinicia el staging de Migración BEST en PostgreSQL (Synap).

No toca MySQL AdministraNET ni Azure BEST. Borra solo mapas/paridad
de la base_empresa indicada para poder recalcular desde cero tras un
restore de Admin u otro cutover.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from mpr.best_migration.reset import contar_staging_best, reiniciar_staging_best


class Command(BaseCommand):
    help = (
        "Reinicia Migración BEST en Postgres (mapas + gate) para una base_empresa. "
        "Dry-run por defecto; usar --ejecutar para borrar."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Empresa Synap / Admin (ej. administranet1).",
        )
        parser.add_argument(
            "--ejecutar",
            action="store_true",
            help="Confirma el borrado. Sin este flag solo muestra conteos.",
        )

    def handle(self, *args, **options):
        base = (options["base_empresa"] or "").strip()
        if not base:
            raise CommandError("Indicá --base-empresa.")

        conteos = contar_staging_best(base)
        total = sum(conteos.values())
        self.stdout.write(f"Staging Migración BEST · base_empresa={base}")
        for etiqueta, n in conteos.items():
            self.stdout.write(f"  {etiqueta}: {n}")
        self.stdout.write(f"  TOTAL filas: {total}")

        if not options["ejecutar"]:
            self.stdout.write(
                self.style.WARNING(
                    "Dry-run: no se borró nada. Reejecutá con --ejecutar para reiniciar."
                )
            )
            return

        if total == 0:
            self.stdout.write(self.style.SUCCESS("Ya estaba vacío; nada que borrar."))
            return

        prev = reiniciar_staging_best(base)
        self.stdout.write(self.style.SUCCESS("Staging reiniciado:"))
        for etiqueta, n in prev.items():
            self.stdout.write(f"  borrados {etiqueta}: {n}")
        self.stdout.write(
            "Siguiente: en /mpr/migracion-best/ recalculá artículos, sincronizá "
            "clientes/depósitos/stock y confirmá unidades."
        )
