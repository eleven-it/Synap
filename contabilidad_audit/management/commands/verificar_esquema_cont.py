"""Comando smoke read-only: valida tablas/columnas cont_* esperadas."""
from django.conf import settings
from django.core.management.base import BaseCommand

from core.mysql_pool import get_mysql_pool

TABLAS_COLUMNAS = {
    "cont_asiento": [
        "debe_asiento",
        "haber_asiento",
        "anulado",
        "id_concepto_asiento",
        "saldo_asiento",
        "codigo_movimiento",
        "codigo_movimiento_anul",
        "id_ejercicio",
        "id_periodo",
        "fecha_asiento",
        "nro_asiento",
    ],
    "cont_pc": ["saldo_pc", "imp_cont_pc", "cod_pc", "ajuste_infla_pc"],
    "cont_concepto_asiento": ["id_concepto_anul", "tipo_concepto_asiento", "tipo_concepto"],
    "cont_periodo": ["fecdesde_periodo", "fechasta_periodo", "id_ejercicio", "cerrado"],
    "cont_ejercicio": [
        "nro_asiento_ejercicio",
        "fecdesde_ejercicio",
        "fechasta_ejercicio",
        "activo_ejercicio",
        "cerrado",
    ],
    "cont_ejercicio_saldo_cta": ["id_pc", "id_ejercicio", "saldo_ejercicio_cta"],
    "cont_periodo_saldo_cta": ["id_pc", "id_ejercicio", "id_periodo", "saldo_periodo_cta"],
    "cuentaproveedor": [
        "CodigoMovimiento",
        "codigo_movimiento_anul",
        "TipoComprobante",
        "NroComprobante",
        "Fecha",
        "CodSucursal",
        "ImporteCompra",
        "Anulado",
    ],
    "sucursales": ["cont"],
    "cont_cc_asiento": ["codigo_movimiento", "importe_cc", "id_pc"],
    "cont_indiceinfla_periodo": ["importe_indiceinfla_periodo", "fecdesde_indiceinfla_periodo"],
}


class Command(BaseCommand):
    help = "Valida existencia de tablas/columnas cont_* vía pool MySQL (solo lectura)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            type=str,
            default=None,
            help="Base MySQL AdministraNET (default: DEFAULT_BASE_EMPRESA)",
        )

    def handle(self, *args, **options):
        base_empresa = options.get("base_empresa") or getattr(
            settings, "DEFAULT_BASE_EMPRESA", None
        )
        if not base_empresa:
            self.stderr.write(self.style.ERROR("Indique --base-empresa o configure DB_NAME."))
            return

        pool = get_mysql_pool()
        errores = []
        with pool.get_connection(base_empresa) as conn:
            cur = conn.cursor()
            for tabla, columnas in TABLAS_COLUMNAS.items():
                cur.execute(
                    """
                    SELECT COUNT(*) FROM information_schema.TABLES
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    """,
                    (base_empresa, tabla),
                )
                if (cur.fetchone()[0] or 0) == 0:
                    errores.append(f"Falta tabla {tabla}")
                    continue
                cur.execute(
                    """
                    SELECT COLUMN_NAME FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    """,
                    (base_empresa, tabla),
                )
                existentes = {r[0] for r in cur.fetchall()}
                for col in columnas:
                    if col not in existentes:
                        errores.append(f"Falta columna {tabla}.{col}")

        if errores:
            for err in errores:
                self.stderr.write(self.style.ERROR(err))
            raise SystemExit(1)

        self.stdout.write(
            self.style.SUCCESS(
                f"Esquema cont_* OK en {base_empresa} ({len(TABLAS_COLUMNAS)} tablas verificadas)."
            )
        )
