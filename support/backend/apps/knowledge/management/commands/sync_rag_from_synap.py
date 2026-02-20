"""
Comando para cargar conocimiento desde Synap e ingestar en RAG.
Uso: python manage.py sync_rag_from_synap [--company-id ID]
Test: asegura SUPPORT_SYNAP_API_URL en .env y que Synap esté levantado (GET /core/api/support/conocimiento/).
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.integrations.adapters.synap_client import SynapClient, SynapClientError
from apps.knowledge.services import KnowledgeIngestionService
from apps.system_config.services import invalidate_config_cache


class Command(BaseCommand):
    help = "Obtiene conocimiento desde Synap (GET /core/api/support/conocimiento/) e ingesta en la base RAG."

    def add_arguments(self, parser):
        parser.add_argument(
            "--company-id",
            type=int,
            default=None,
            help="ID de empresa en Support; si no se pasa, ingesta global (company_id null).",
        )

    def handle(self, *args, **options):
        company_id = options.get("company_id")

        base_url = getattr(settings, "SUPPORT_SYNAP_API_URL", "") or ""
        if not base_url.strip():
            raise CommandError(
                "SUPPORT_SYNAP_API_URL no está configurado. "
                "Configuralo en el .env del backend Support (ej. http://localhost:8000)."
            )

        try:
            client = SynapClient()
            items = client.get_conocimiento()
        except SynapClientError as e:
            raise CommandError(f"No se pudo conectar con Synap: {e}")

        if not items:
            raise CommandError(
                "Synap no devolvió ítems. ¿La URL es correcta y Synap está levantado?"
            )

        self.stdout.write(f"Recibidos {len(items)} ítems desde Synap. Ingestando...")
        svc = KnowledgeIngestionService()
        created, updated = svc.create_or_update_chunks(
            items=items,
            company_id=company_id,
            source_type="synap",
        )
        invalidate_config_cache("rag", company_id)
        self.stdout.write(
            self.style.SUCCESS(f"Carga RAG OK: {created} creados, {updated} actualizados.")
        )
