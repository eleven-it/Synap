from django.core.management.base import BaseCommand

from ecom.services.comprobante_mail_async import procesar_mail_queue_batch


class Command(BaseCommand):
    help = "Procesa la cola async de mails e-com."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=50)
        parser.add_argument("--retries", action="store_true", help="Reprocesar también items en error.")
        parser.add_argument("--max-attempts", type=int, default=5, help="Máximo de intentos por item.")

    def handle(self, *args, **options):
        stats = procesar_mail_queue_batch(
            limit=int(options["limit"]),
            include_errors=bool(options.get("retries")),
            max_attempts=int(options["max_attempts"]),
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Procesados={stats['procesados']} enviados={stats['enviados']} errores={stats['errores']}"
            )
        )

