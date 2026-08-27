from django.core.management.base import BaseCommand, CommandError

from mtrix.models import MtrixJob
from mtrix.services.orchestrator import ejecutar_job
from mtrix.services.schedule import jobs_a_lanzar


class Command(BaseCommand):
    help = "Genera archivos MTRIX (job existente o programados)."

    def add_arguments(self, parser):
        parser.add_argument("--job-id", dest="job_id", default="")
        parser.add_argument("--scheduled", action="store_true")
        parser.add_argument("--base-empresa", dest="base_empresa", default="")
        parser.add_argument(
            "--match-hour-only",
            action="store_true",
            help="Coincidir solo la hora (cron horario).",
        )

    def handle(self, *args, **options):
        if options.get("scheduled"):
            jobs = jobs_a_lanzar(match_minute=not options.get("match_hour_only"))
            if not jobs:
                self.stdout.write("Sin jobs programados en esta ventana.")
                return
            for job in jobs:
                self.stdout.write(f"Ejecutando job programado {job.id} ({job.base_empresa})")
                ejecutar_job(job.id)
            return
        job_id = (options.get("job_id") or "").strip()
        if not job_id:
            raise CommandError("Indique --job-id o --scheduled.")
        try:
            job = MtrixJob.objects.get(pk=job_id)
        except MtrixJob.DoesNotExist as exc:
            raise CommandError(f"Job no encontrado: {job_id}") from exc
        if options.get("base_empresa") and job.base_empresa != options["base_empresa"]:
            raise CommandError("El job no pertenece a esa base_empresa.")
        ejecutar_job(job.id)
        self.stdout.write(self.style.SUCCESS(f"Job {job.id} {job.status}"))
