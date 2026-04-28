from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from ia.models import AgentDefinition, AgentLearningExample, LearningExampleStatus
from ia.services.learning_capture_service import LearningExportService


class Command(BaseCommand):
    help = (
        "Exporta ejemplos de aprendizaje a JSONL (un objeto JSON por línea, clave «messages», "
        "compatible con fine-tuning de chat en proveedores tipo OpenAI)."
    )

    def add_arguments(self, parser):
        parser.add_argument("--agent-slug", type=str, required=True, help="Slug del AgentDefinition.")
        parser.add_argument(
            "--status",
            type=str,
            default="approved",
            choices=[
                LearningExampleStatus.PENDING,
                LearningExampleStatus.APPROVED,
                LearningExampleStatus.EXPORTED,
                LearningExampleStatus.REJECTED,
            ],
            help="Filtrar por estado (por defecto solo aprobados).",
        )
        parser.add_argument(
            "--output",
            type=str,
            required=True,
            help="Ruta del archivo de salida (.jsonl).",
        )
        parser.add_argument(
            "--mark-exported",
            action="store_true",
            help="Tras escribir el archivo, marcar los ejemplos exportados como EXPORTED.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Máximo de filas (0 = sin límite).",
        )

    def handle(self, *args, **options):
        slug = options["agent_slug"]
        status = options["status"]
        output_path = options["output"]
        mark_exported = options["mark_exported"]
        limit = int(options["limit"] or 0)

        agent = AgentDefinition.objects.filter(slug=slug).first()
        if not agent:
            self.stderr.write(self.style.ERROR(f"No existe agente con slug «{slug}»."))
            return

        qs = AgentLearningExample.objects.filter(agent=agent, status=status).order_by("id")
        if limit > 0:
            qs = qs[:limit]
        ids = []
        lines = []
        for ex in qs:
            lines.append(LearningExportService.render_jsonl_line(ex))
            ids.append(ex.id)

        with open(output_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
            if lines:
                fh.write("\n")

        self.stdout.write(self.style.SUCCESS(f"Escritas {len(lines)} líneas en {output_path}"))

        if mark_exported and ids and status != LearningExampleStatus.EXPORTED:
            with transaction.atomic():
                AgentLearningExample.objects.filter(id__in=ids).update(status=LearningExampleStatus.EXPORTED)
            self.stdout.write(self.style.SUCCESS(f"Marcados como exportados: {len(ids)} ejemplos."))
