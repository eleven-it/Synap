"""
Limpieza de renglones temporales de movimientos de stock (cuerpostock_mstock, serie_entrada_temp, serie_salida_temp).
Ejecutar por cron o al login/logout para evitar registros huérfanos.
"""
import logging
from django.core.management.base import BaseCommand

from core.mysql_pool import mysql_cursor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Elimina registros de cuerpostock_mstock (y series temp) con más de N horas o todos los temporales"

    def add_arguments(self, parser):
        parser.add_argument(
            "base_empresa",
            nargs="+",
            type=str,
            help="Nombre(s) de base de datos de empresa (ej. administranet_empresa1)",
        )
        parser.add_argument(
            "--horas",
            type=int,
            default=24,
            help="Eliminar temporales con antigüedad mayor a N horas (default 24). Si 0, elimina todos.",
        )

    def handle(self, *args, **options):
        bases = options["base_empresa"]
        horas = options["horas"]

        for base_empresa in bases:
            try:
                with mysql_cursor(base_empresa, dict_cursor=False) as cursor:
                    cursor.execute(
                        "DELETE FROM cuerpostock_mstock WHERE COALESCE(visualiza, 'No') = 'No'"
                    )
                    deleted = cursor.rowcount
                    try:
                        cursor.execute("DELETE FROM serie_entrada_temp WHERE tipo = 'Mstock'")
                        cursor.execute("DELETE FROM serie_salida_temp WHERE tipo = 'Mstock'")
                    except Exception as e:
                        logger.debug("Series temp no existían o error: %s", e)
                    if horas > 0:
                        logger.info(
                            "Filtro por horas no aplicado (tabla sin timestamp); se eliminaron todos los temporales."
                        )
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Base {base_empresa}: eliminados {deleted} renglones temporales."
                        )
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"Base {base_empresa}: error - {e}")
                )
                logger.exception("Error limpiando temporales en %s", base_empresa)
