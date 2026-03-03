"""
Investiga si una factura de compra generó movimientos de stock y si tiene remito asociado.

Una factura SIN remito asociado (Factura OC directa) SÍ mueve stock.
Una factura CON remito asociado (Factura sobre Remito) NO mueve stock (el remito ya lo hizo).

Uso:
  python manage.py investigar_factura_stock --base-empresa administranet89 1200-00068659
  python manage.py investigar_factura_stock --base-empresa administranet89 1200-00068659 --fecha 2025-10-24
"""
from django.core.management.base import BaseCommand
from reports.services.connection_pool import get_mysql_pool


class Command(BaseCommand):
    help = "Investiga si una factura de compra generó movimientos de stock y si tiene remito asociado"

    def add_arguments(self, parser):
        parser.add_argument(
            "nro_comprobante",
            type=str,
            help="Número de comprobante (ej: 1200-00068659)",
        )
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Nombre de la base de datos MySQL",
        )
        parser.add_argument(
            "--fecha",
            type=str,
            default=None,
            help="Fecha opcional para precisar (YYYY-MM-DD)",
        )

    def handle(self, *args, **options):
        nro = options["nro_comprobante"].strip()
        base_empresa = options["base_empresa"]
        fecha = options.get("fecha")

        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            cursor = conn.cursor()

            # 1) Buscar cuentaproveedor por NroComprobante o NroCompBusq
            sql_cp = """
                SELECT CodigoMovimiento, TipoComprobante, Fecha, NroComprobante, NroCompBusq, Anulado, Codigo
                FROM cuentaproveedor
                WHERE (TRIM(NroComprobante) = %s OR NroCompBusq = %s)
            """
            params = [nro, nro]
            if fecha:
                sql_cp += " AND DATE(Fecha) = %s"
                params.append(fecha)
            sql_cp += " ORDER BY Fecha DESC LIMIT 5"
            cursor.execute(sql_cp, params)
            rows_cp = cursor.fetchall()

            if not rows_cp:
                self.stdout.write(self.style.WARNING(f"No se encontró comprobante con Nro '{nro}'"))
                return

            self.stdout.write(self.style.SUCCESS(f"\n=== Comprobante(s) encontrado(s) ==="))
            for r in rows_cp:
                cod_mov, tipo, fec, nro_comp, nro_busq, anulado, cod_prov = r
                self.stdout.write(
                    f"  CodigoMovimiento={cod_mov} TipoComprobante={tipo} Fecha={fec} "
                    f"NroComprobante={nro_comp} NroCompBusq={nro_busq} Anulado={anulado or 'NULL'}"
                )

            cod_mov = rows_cp[0][0]
            tipo_comp = rows_cp[0][1]

            # Solo tiene sentido para facturas (FA, FB, FC, FM)
            if tipo_comp not in ("FA", "FB", "FC", "FM"):
                self.stdout.write(
                    self.style.WARNING(f"\nTipoComprobante '{tipo_comp}' no es una factura. Solo facturas pueden tener remito asociado.")
                )
                return

            # 2) ¿Tiene movimientos en stock?
            cursor.execute(
                """
                SELECT COUNT(*) FROM stock
                WHERE CodigoMovimiento = %s AND (anulado IS NULL OR anulado = 'No')
                """,
                (cod_mov,),
            )
            count_stock = cursor.fetchone()[0] or 0

            self.stdout.write(f"\n=== Stock ===")
            if count_stock > 0:
                self.stdout.write(self.style.SUCCESS(f"  SÍ tiene movimientos de stock: {count_stock} líneas"))
                cursor.execute(
                    """
                    SELECT s.id_stock, s.IDArt, s.Cantidad, s.TipoComp, s.Comprobante, s.anulado
                    FROM stock s
                    WHERE s.CodigoMovimiento = %s AND (s.anulado IS NULL OR s.anulado = 'No')
                    LIMIT 10
                    """,
                    (cod_mov,),
                )
                for row in cursor.fetchall():
                    self.stdout.write(f"    id_stock={row[0]} IDArt={row[1]} Cantidad={row[2]} TipoComp={row[3]} Comprobante={row[4]}")
            else:
                self.stdout.write(self.style.WARNING("  NO tiene movimientos de stock"))

            # 3) ¿Está en oc_factp? (Factura ligada a OC)
            try:
                cursor.execute(
                    """
                    SELECT ocf.id_oc_factp, ocf.codigo_movimientof, ocf.codigo_movimiento_oc, ocf.Anulado
                    FROM oc_factp ocf
                    WHERE ocf.codigo_movimientof = %s AND (ocf.Anulado IS NULL OR ocf.Anulado = 'No')
                    """,
                    (cod_mov,),
                )
                oc_factp_rows = cursor.fetchall()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"\n  oc_factp no disponible: {e}"))
                oc_factp_rows = []

            self.stdout.write(f"\n=== oc_factp (Factura → OC) ===")
            if oc_factp_rows:
                self.stdout.write(self.style.SUCCESS(f"  SÍ está en oc_factp: Factura OC directa (ligada a orden de compra)"))
                for r in oc_factp_rows:
                    self.stdout.write(f"    codigo_movimientof={r[1]} codigo_movimiento_oc={r[2]}")
            else:
                self.stdout.write("  NO está en oc_factp")

            # 4) ¿Está en remp_factp? (Factura ligada a Remito) → Factura sobre Remito
            try:
                cursor.execute(
                    """
                    SELECT rf.id_remp_factp, rf.codigo_movimientof, rf.codigo_movimientor, rf.Anulado
                    FROM remp_factp rf
                    WHERE rf.codigo_movimientof = %s AND (rf.Anulado IS NULL OR rf.Anulado = 'No')
                    """,
                    (cod_mov,),
                )
                remp_factp_rows = cursor.fetchall()
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"\n  remp_factp no disponible: {e}"))
                remp_factp_rows = []

            self.stdout.write(f"\n=== remp_factp (Factura → Remito) ===")
            if remp_factp_rows:
                self.stdout.write(self.style.SUCCESS(f"  SÍ tiene remito asociado: Factura SOBRE REMITO"))
                for r in remp_factp_rows:
                    self.stdout.write(f"    codigo_movimientof={r[1]} codigo_movimientor(remito)={r[2]}")
            else:
                self.stdout.write("  NO tiene remito asociado (no está en remp_factp)")

            # Resumen
            self.stdout.write(f"\n=== Conclusión ===")
            if remp_factp_rows:
                self.stdout.write(
                    self.style.WARNING(
                        "  La factura TIENE remito asociado (remp_factp). "
                        "Factura sobre Remito NO debería mover stock (el remito ya lo hizo)."
                    )
                )
                if count_stock > 0:
                    self.stdout.write(
                        self.style.ERROR(
                            "  INCONSISTENCIA: tiene movimientos de stock y remito asociado. "
                            "Posible duplicación de stock."
                        )
                    )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        "  La factura NO tiene remito asociado. Es Factura OC directa → SÍ mueve stock (correcto)."
                    )
                )
