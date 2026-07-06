"""Migración por dominio hacia Odoo (lotes reanudables)."""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from odoo_migracion.models import MigrationJob, OdooConnection
from odoo_migracion.services.domains import DOMAIN_BY_KEY, ordered_domain_keys
from odoo_migracion.services.migration_orchestrator import run_domain_batch, run_full_domain


class Command(BaseCommand):
    help = "Migra un dominio AdministraNET → Odoo (JSON-2) en lotes."

    def add_arguments(self, parser):
        parser.add_argument("--connection-id", type=int, required=True)
        parser.add_argument(
            "--dominio",
            choices=list(DOMAIN_BY_KEY.keys()) + ["all"],
            required=True,
            help="Dominio o 'all' en orden DAG",
        )
        parser.add_argument("--batch-size", type=int, default=100)
        parser.add_argument("--offset", type=int, default=None, help="Solo un lote en este offset")
        parser.add_argument("--resume-job-id", type=int, default=None)

    def handle(self, *args, **options):
        try:
            conexion = OdooConnection.objects.get(pk=options["connection_id"], activo=True)
        except OdooConnection.DoesNotExist as exc:
            raise CommandError("Conexión no encontrada o inactiva.") from exc

        dominio = options["dominio"]
        batch = max(1, min(options["batch_size"], 500))

        if dominio == "all":
            for key in ordered_domain_keys():
                self.stdout.write(f"--- Dominio {key} ---")
                job = run_full_domain(conexion, key, batch_size=batch)
                self.stdout.write(self.style.SUCCESS(f"Job {job.pk} — {job.get_estado_display()}: {job.mensaje}"))
            return

        if options["resume_job_id"]:
            job = MigrationJob.objects.get(pk=options["resume_job_id"], conexion=conexion)
            job = run_full_domain(conexion, dominio, batch_size=batch, resume_job=job)
            self.stdout.write(self.style.SUCCESS(f"Job {job.pk} reanudado: {job.mensaje}"))
            return

        if options["offset"] is not None:
            job = MigrationJob.objects.create(
                conexion=conexion,
                dominio=dominio,
                estado=MigrationJob.Estado.EN_CURSO,
            )
            result = run_domain_batch(
                conexion,
                dominio,
                batch_size=batch,
                offset=options["offset"],
                job=job,
            )
            self.stdout.write(
                f"Lote: {result.procesados} proc, {result.creados} creados, "
                f"{result.errores} errores, {result.pendientes} pendientes"
            )
            return

        job = run_full_domain(conexion, dominio, batch_size=batch)
        self.stdout.write(self.style.SUCCESS(f"Job {job.pk} — {job.get_estado_display()}: {job.mensaje}"))
