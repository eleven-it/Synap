# -*- coding: utf-8 -*-
"""Registra el informe pedidos-pendientes-produccion (idempotente)."""
from django.core.management.base import BaseCommand

from reports.services.pedidos_pendientes_produccion_seed import (
    PEDIDOS_PENDIENTES_PRODUCCION_SLUG,
    ensure_pedidos_pendientes_produccion_report,
)


class Command(BaseCommand):
    help = "Crea o actualiza ReportDefinition pedidos-pendientes-produccion"

    def handle(self, *args, **options):
        report = ensure_pedidos_pendientes_produccion_report()
        if report:
            self.stdout.write(
                self.style.SUCCESS(
                    f"OK: {PEDIDOS_PENDIENTES_PRODUCCION_SLUG} (id={report.pk})"
                )
            )
        else:
            self.stdout.write(self.style.ERROR("No se pudo crear el informe."))
