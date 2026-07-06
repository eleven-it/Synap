from django.core.management.base import BaseCommand

from odoo_migracion.models import OdooConnection
from odoo_migracion.services.api_key_rotation import rotate_api_key, test_connection
from odoo_migracion.services.odoo_client import OdooApiError


class Command(BaseCommand):
    help = "Rota la API key Odoo de una conexión (JSON-2 generate/revoke)."

    def add_arguments(self, parser):
        parser.add_argument("--connection-id", type=int, required=True, help="PK de OdooConnection")
        parser.add_argument(
            "--no-revoke",
            action="store_true",
            help="No revocar la API key anterior tras generar la nueva",
        )

    def handle(self, *args, **options):
        pk = options["connection_id"]
        conexion = OdooConnection.objects.filter(pk=pk).first()
        if not conexion:
            self.stderr.write(self.style.ERROR(f"No existe OdooConnection id={pk}"))
            return

        try:
            result = rotate_api_key(conexion, revoke_previous=not options["no_revoke"])
            self.stdout.write(
                self.style.SUCCESS(
                    f"API key rotada para '{conexion.nombre}'. Vence: {result.get('expires_at')}"
                )
            )
            if result.get("warning"):
                self.stdout.write(self.style.WARNING(result["warning"]))
        except OdooApiError as exc:
            self.stderr.write(self.style.ERROR(str(exc)))
