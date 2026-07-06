"""Cuadre pre/post migración."""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand, CommandError

from odoo_migracion.models import OdooConnection
from odoo_migracion.services.validation import run_validation


class Command(BaseCommand):
    help = "Valida cuadre origen MySQL vs mappings Odoo en Synap."

    def add_arguments(self, parser):
        parser.add_argument("--connection-id", type=int, required=True)
        parser.add_argument("--json", action="store_true")

    def handle(self, *args, **options):
        try:
            conexion = OdooConnection.objects.get(pk=options["connection_id"])
        except OdooConnection.DoesNotExist as exc:
            raise CommandError("Conexión no encontrada.") from exc

        report = run_validation(conexion)
        data = report.to_dict()
        if options["json"]:
            self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
            return
        self.stdout.write(self.style.SUCCESS(f"Cuadre — {conexion.nombre} ({conexion.base_empresa})"))
        for line in data["lineas"]:
            self.stdout.write(
                f"  {line['dominio']}: origen={line['origen_count']} "
                f"ok={line['mappings_ok']} pend={line['mappings_pendiente']} "
                f"err={line['mappings_error']} delta={line['delta']}"
            )
