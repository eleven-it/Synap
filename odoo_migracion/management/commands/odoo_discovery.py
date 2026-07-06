"""Inventario cuantitativo por base_empresa (F0)."""

from __future__ import annotations

import json

from django.core.management.base import BaseCommand

from odoo_migracion.services.discovery import run_discovery


class Command(BaseCommand):
    help = "Inventario cuantitativo AdministraNET por dominio de migración Odoo (F0)."

    def add_arguments(self, parser):
        parser.add_argument("--base-empresa", required=True, help="Base MySQL origen")
        parser.add_argument("--json", action="store_true", help="Salida JSON")

    def handle(self, *args, **options):
        base = options["base_empresa"].strip()
        report = run_discovery(base)
        data = report.to_dict()
        if options["json"]:
            self.stdout.write(json.dumps(data, indent=2, ensure_ascii=False))
            return
        self.stdout.write(self.style.SUCCESS(f"Inventario — {base}"))
        for dominio, n in sorted(data["conteos"].items()):
            self.stdout.write(f"  {dominio}: {n}")
        if data["anomalias"]:
            self.stdout.write(self.style.WARNING("\nAnomalías:"))
            for a in data["anomalias"]:
                self.stdout.write(f"  [{a['dominio']}] {a['codigo']}: {a['cantidad']} — {a['mensaje']}")
