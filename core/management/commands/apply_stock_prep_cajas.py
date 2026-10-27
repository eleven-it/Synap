"""Aplica el esquema MySQL de cajas de preparación a una empresa."""

import re

from django.core.management.base import BaseCommand, CommandError

from core.mysql_pool import get_connection
from core.services.legacy_mysql_schema.catalog import run_stock_prep_cajas_mysql


class Command(BaseCommand):
    help = "Crea o actualiza las tablas de cajas de preparación en una base MySQL legacy."

    def add_arguments(self, parser):
        parser.add_argument("base_empresa", help="Base de la empresa, por ejemplo administranet1.")

    def handle(self, *args, **options):
        base_empresa = options["base_empresa"].strip()
        if not re.fullmatch(r"[A-Za-z0-9_]+", base_empresa):
            raise CommandError("Nombre de base de empresa inválido.")

        try:
            with get_connection(base_empresa) as conn:
                result = run_stock_prep_cajas_mysql(conn)
        except Exception as exc:
            raise CommandError(f"No se pudo actualizar {base_empresa}: {exc}") from exc

        if not result.get("success"):
            raise CommandError(result.get("message") or "Falló la migración de cajas.")
        self.stdout.write(self.style.SUCCESS(f"{base_empresa}: {result.get('message', 'OK')}"))
