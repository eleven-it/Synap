"""
Backfill idempotente: carteras JSON ``ecom_vendedores_a_cargo_*`` → tablas org.

Ejemplo::

  docker exec Synap_app python manage.py migrar_carteras_a_jerarquia administranet1
  docker exec Synap_app python manage.py migrar_carteras_a_jerarquia administranet1 --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from ecom.services.jerarquia_comercial import backfill_carteras_desde_config


class Command(BaseCommand):
    help = (
        "Migra carteras supervisor JSON (ecom_vendedores_a_cargo_*) "
        "a ecom_org_supervisor_vendedor. Idempotente; no borra claves legacy."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "base_empresa",
            help="Nombre de la base MySQL AdministraNET (ej. administranet1).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo simula vínculos sin escribir.",
        )

    def handle(self, *args, **options):
        base = str(options["base_empresa"] or "").strip()
        dry = bool(options["dry_run"])
        if not base:
            raise CommandError("Debe indicar base_empresa.")
        result = backfill_carteras_desde_config(base, dry_run=dry)
        if not result.get("ok"):
            raise CommandError(result.get("error") or "Backfill falló.")
        modo = "simulación" if dry else "aplicado"
        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill {modo}: supervisores={result.get('supervisores', 0)}, "
                f"vínculos SV={result.get('vinculos_sv', 0)}."
            )
        )
