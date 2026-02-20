"""
Solicita CAEA en los plazos establecidos (5 días previos a cada quincena).
Ejecutar diariamente por cron, ej: 0 8 * * * python manage.py request_caea_auto
Uso: python manage.py request_caea_auto [--base-empresa X] [--dry-run]
"""
import logging

from django.core.management.base import BaseCommand

from fe_afip.models import AFIPConfig
from fe_afip.services.caea_service import periods_to_request_today, run_auto_request_for_base

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Obtiene/renueva CAEA para períodos en ventana de 5 días previos (ejecución diaria)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            type=str,
            help="Solo esta base; si no se indica, todas las configuraciones AFIP activas",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo mostrar qué períodos se solicitarían, sin llamar a AFIP",
        )

    def handle(self, *args, **options):
        base_filter = (options.get("base_empresa") or "").strip()
        dry_run = options.get("dry_run", False)

        configs = AFIPConfig.objects.filter(activo=True)
        if base_filter:
            configs = configs.filter(base_empresa=base_filter)
        configs = list(configs.filter(cert_path__isnull=False).exclude(cert_path="").filter(key_path__isnull=False).exclude(key_path="").filter(cuit__isnull=False).exclude(cuit=""))

        if not configs:
            self.stdout.write("No hay configuraciones AFIP activas con cert/key/cuit.")
            return

        today_periods = periods_to_request_today()
        if not today_periods:
            self.stdout.write("Hoy no corresponde ventana de solicitud (5 días previos a quincena).")
            return

        self.stdout.write("Ventana de hoy: períodos %s" % (today_periods,))

        for cfg in configs:
            base = cfg.base_empresa
            self.stdout.write("Base: %s" % base)
            if dry_run:
                for periodo, orden in today_periods:
                    self.stdout.write("  [dry-run] solicitaría %s orden %s" % (periodo, orden))
                continue
            results = run_auto_request_for_base(base)
            for periodo, orden, ok, msg in results:
                if ok:
                    self.stdout.write(self.style.SUCCESS("  %s ord.%s: %s" % (periodo, orden, msg)))
                else:
                    self.stdout.write(self.style.ERROR("  %s ord.%s: %s" % (periodo, orden, msg)))
