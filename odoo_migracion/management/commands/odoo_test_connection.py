from django.core.management.base import BaseCommand

from odoo_migracion.models import OdooConnection
from odoo_migracion.services.api_key_rotation import test_connection


class Command(BaseCommand):
    help = "Prueba conectividad JSON-2 contra Odoo para una OdooConnection."

    def add_arguments(self, parser):
        parser.add_argument("--connection-id", type=int, required=True)

    def handle(self, *args, **options):
        conexion = OdooConnection.objects.filter(pk=options["connection_id"]).first()
        if not conexion:
            self.stderr.write(self.style.ERROR("Conexión no encontrada."))
            return
        result = test_connection(conexion)
        if result.get("success"):
            self.stdout.write(self.style.SUCCESS(f"OK: {conexion.nombre} → {conexion.base_url}"))
        else:
            self.stderr.write(self.style.ERROR(result.get("error", "Error desconocido")))
