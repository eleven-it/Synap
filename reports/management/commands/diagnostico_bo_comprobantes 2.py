# reports/management/commands/diagnostico_bo_comprobantes.py
"""
Diagnóstico: por qué comprobantes comp_ped no aparecen en el reporte BO (Backorder).
Ejecuta consultas contra la base MySQL real y muestra estado, renglones y causas probables.
"""
import logging
from django.core.management.base import BaseCommand
from django.conf import settings

logger = logging.getLogger(__name__)

COMPROBANTES = [
    "0001-00010474",
    "0001-00010076",
    "0001-00010603",
    "0001-00010604",
]


class Command(BaseCommand):
    help = "Diagnostica por qué comprobantes no aparecen en el reporte BO (backorder) usando la base MySQL real."

    def add_arguments(self, parser):
        parser.add_argument(
            "--comprobantes",
            nargs="+",
            default=COMPROBANTES,
            help="Lista de NroComprobante a diagnosticar (default: los 4 de ejemplo).",
        )
        parser.add_argument(
            "--database",
            default=None,
            help="Nombre de la base MySQL (ej. administranet92). Si no se pasa, se usa DB_NAME de settings.",
        )

    def handle(self, *args, **options):
        comprobantes = options["comprobantes"]
        mysql_config = settings.DATABASES.get("mysql")
        if not mysql_config:
            self.stderr.write(self.style.ERROR("No hay configuración 'mysql' en DATABASES."))
            return

        try:
            import MySQLdb
        except ImportError:
            self.stderr.write(self.style.ERROR("Falta MySQLdb. Instalar: pip install mysqlclient"))
            return

        db_name = options.get("database") or mysql_config.get("NAME", "administranet")
        self.stdout.write(f"Base MySQL: {db_name}\n")
        try:
            conn = MySQLdb.connect(
                host=mysql_config["HOST"],
                port=int(mysql_config.get("PORT", 3306)),
                user=mysql_config["USER"],
                passwd=mysql_config["PASSWORD"],
                db=db_name,
                charset="latin1",
            )
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error conectando a MySQL ({db_name}): {e}"))
            return

        placeholders = ",".join(["%s"] * len(comprobantes))

        # 0) Comprobar que hay datos y formato de NroComprobante
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM comp_ped")
            total_cp = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM stockp")
            total_sp = cur.fetchone()[0]
            cur.execute(
                "SELECT NroComprobante FROM comp_ped WHERE TipoComprobante = 'PED' ORDER BY id_comp_ped DESC LIMIT 5"
            )
            samples = [r[0] for r in cur.fetchall()]
            cur.close()
            self.stdout.write(f"Total comp_ped: {total_cp}, total stockp: {total_sp}")
            self.stdout.write(f"Muestra NroComprobante (PED recientes): {samples}\n")
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"No se pudo contar tablas: {e}\n"))

        # 1) Cabecera comp_ped
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("1) CABECERA comp_ped (estado, anulado, cantidad de renglones en stockp)")
        self.stdout.write("=" * 80)

        sql_cab = f"""
            SELECT
                cp.NroComprobante,
                cp.CodigoMovimiento,
                cp.Fecha AS cp_fecha,
                cp.TipoComprobante,
                cp.Estado AS cp_estado,
                cp.Anulado AS cp_anulado,
                cp.Codigo AS id_cliente,
                (SELECT COUNT(*) FROM stockp sp WHERE sp.CodigoMovimiento = cp.CodigoMovimiento) AS num_renglones_stockp
            FROM comp_ped cp
            WHERE cp.NroComprobante IN ({placeholders})
            ORDER BY cp.NroComprobante
        """
        try:
            cur = conn.cursor()
            cur.execute(sql_cab, comprobantes)
            rows = cur.fetchall()
            cur.close()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error en consulta cabecera: {e}"))
            conn.close()
            return

        if not rows:
            self.stdout.write(
                self.style.WARNING(
                    f"Ningún comprobante encontrado en comp_ped en la base '{db_name}': {comprobantes}"
                )
            )
            self.stdout.write(
                self.style.NOTICE(
                    "Si el reporte BO lo ejecutás con otra base (selector base empresa), probá: "
                    "--database <nombre_base>"
                )
            )
        else:
            cols = [
                "NroComprobante", "CodigoMovimiento", "cp_fecha", "TipoComprobante",
                "cp_estado", "cp_anulado", "id_cliente", "num_renglones_stockp",
            ]
            for row in rows:
                d = dict(zip(cols, row))
                nro = d["NroComprobante"]
                estado = d["cp_estado"] or ""
                num_r = d["num_renglones_stockp"] or 0
                motivo = []
                if num_r == 0:
                    motivo.append("SIN RENGLONES en stockp → no puede entrar al BO")
                if estado != "Pendiente":
                    motivo.append(f"Estado='{estado}' → BO solo incluye 'Pendiente' (otros van a Reservado)")
                if motivo:
                    self.stdout.write(self.style.WARNING(f"  {nro}: {', '.join(motivo)}"))
                else:
                    self.stdout.write(f"  {nro}: Estado={estado}, renglones_stockp={num_r}")
                self.stdout.write(f"      CodigoMov={d['CodigoMovimiento']}, Fecha={d['cp_fecha']}, Anulado={d['cp_anulado']}")

        # 2) Detalle por renglón (stockp + articulo)
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("2) DETALLE por renglón (stockp.Fecha, tipo_art, condiciones BO)")
        self.stdout.write("=" * 80)

        sql_det = f"""
            SELECT
                cp.NroComprobante,
                cp.Estado AS cp_estado,
                sp.Fecha AS sp_fecha,
                sp.Comprobante AS sp_comprobante,
                sp.anulado AS sp_anulado,
                a.id_manual AS codigo_articulo,
                a.tipo_art AS tipo_art,
                sp.Cantidad,
                CASE WHEN cp.Estado = 'Pendiente' THEN 'Sí' ELSE 'No (BO solo Pendiente)' END AS estado_ok_bo,
                CASE WHEN (a.IDArt IS NULL OR a.tipo_art IS NULL OR a.tipo_art <> 'Gasto') THEN 'Sí' ELSE 'No (excl. Gasto)' END AS articulo_ok_bo
            FROM comp_ped cp
            INNER JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
            LEFT JOIN articulo a ON a.IDArt = sp.IDArt
            WHERE cp.NroComprobante IN ({placeholders})
            ORDER BY cp.NroComprobante, sp.Fecha, sp.id_stock
        """
        try:
            cur = conn.cursor()
            cur.execute(sql_det, comprobantes)
            rows = cur.fetchall()
            cur.close()
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Error en consulta detalle: {e}"))
            conn.close()
            return

        if not rows:
            self.stdout.write(self.style.WARNING("No hay renglones en stockp para estos comprobantes (o no existen en comp_ped)."))
        else:
            cols_det = [
                "NroComprobante", "cp_estado", "sp_fecha", "sp_comprobante", "sp_anulado",
                "codigo_articulo", "tipo_art", "Cantidad", "estado_ok_bo", "articulo_ok_bo",
            ]
            for row in rows:
                d = dict(zip(cols_det, row))
                nro = d["NroComprobante"]
                self.stdout.write(f"  {nro} | sp_fecha={d['sp_fecha']} | art={d['codigo_articulo']} tipo_art={d['tipo_art']} | estado_ok_bo={d['estado_ok_bo']} | articulo_ok_bo={d['articulo_ok_bo']}")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write("Recordatorio: el BO filtra por stockp.Fecha en el rango del reporte. Si sp_fecha está fuera de ese rango, el comprobante no aparece en el BO.")
        self.stdout.write("=" * 80 + "\n")
        conn.close()
