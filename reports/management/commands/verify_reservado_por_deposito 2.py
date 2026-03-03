"""
Comando para verificar en la DB si existe reservado por depósito.
Consultas:
1) stock_deposito.saldo_pedido_cliente por (id_articulo, id_deposito)
2) stockp.CodDeposito para PED En preparación/Preparado
"""
from django.core.management.base import BaseCommand
from reports.services.connection_pool import get_mysql_pool


class Command(BaseCommand):
    help = 'Verifica si existe reservado por depósito en la DB (stock_deposito vs stockp)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--base-empresa',
            type=str,
            required=True,
            help='Nombre de la base de datos MySQL (base_empresa)',
        )

    def handle(self, *args, **options):
        base_empresa = options['base_empresa']
        pool = get_mysql_pool()

        try:
            with pool.get_connection(base_empresa) as conn:
                cursor = conn.cursor()
                self.stdout.write(self.style.SUCCESS(f'Conectado a MySQL: {base_empresa}\n'))

                # 1) stock_deposito: columnas y datos de saldo_pedido_cliente
                self.stdout.write('=' * 70)
                self.stdout.write('1) STOCK_DEPOSITO - saldo_pedido_cliente (reservado por pedidos)')
                self.stdout.write('=' * 70)
                try:
                    cursor.execute("""
                        SELECT COLUMN_NAME, DATA_TYPE
                        FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'stock_deposito'
                        AND COLUMN_NAME IN ('id_articulo', 'id_deposito', 'saldo_pedido_cliente')
                        ORDER BY COLUMN_NAME
                    """, (base_empresa,))
                    cols = cursor.fetchall()
                    if cols:
                        self.stdout.write('   Columnas encontradas: ' + ', '.join(c[0] for c in cols))
                    else:
                        self.stdout.write(self.style.WARNING('   No se encontraron las columnas esperadas'))

                    cursor.execute("""
                        SELECT COUNT(*) as total,
                               SUM(CASE WHEN COALESCE(saldo_pedido_cliente, 0) > 0 THEN 1 ELSE 0 END) as con_reservado
                        FROM stock_deposito
                    """)
                    row = cursor.fetchone()
                    self.stdout.write(f'   Total filas stock_deposito: {row[0]}')
                    self.stdout.write(f'   Filas con saldo_pedido_cliente > 0: {row[1]}')

                    cursor.execute("""
                        SELECT sd.id_articulo, sd.id_deposito, d.NombreDeposito,
                               COALESCE(sd.saldo_pedido_cliente, 0) as reservado
                        FROM stock_deposito sd
                        LEFT JOIN deposito d ON d.CodDeposito = sd.id_deposito
                        WHERE COALESCE(sd.saldo_pedido_cliente, 0) > 0
                        ORDER BY sd.id_articulo, sd.id_deposito
                        LIMIT 10
                    """)
                    rows = cursor.fetchall()
                    if rows:
                        self.stdout.write('   Muestra (id_articulo, id_deposito, depósito, reservado):')
                        for r in rows:
                            self.stdout.write(f'      {r[0]}, {r[1]}, {r[2] or "?"}, {r[3]}')
                    else:
                        self.stdout.write(self.style.WARNING('   No hay filas con saldo_pedido_cliente > 0'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   Error: {e}'))

                # 2) stockp: CodDeposito para PED En preparación/Preparado
                self.stdout.write('')
                self.stdout.write('=' * 70)
                self.stdout.write('2) STOCKP - CodDeposito en PED En preparación/Preparado')
                self.stdout.write('=' * 70)
                try:
                    cursor.execute("""
                        SELECT COLUMN_NAME FROM information_schema.COLUMNS
                        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'stockp'
                        AND COLUMN_NAME = 'CodDeposito'
                    """, (base_empresa,))
                    if cursor.fetchone():
                        self.stdout.write('   Columna CodDeposito: existe')
                    else:
                        self.stdout.write(self.style.WARNING('   Columna CodDeposito: NO existe en stockp'))

                    cursor.execute("""
                        SELECT COUNT(*) as total,
                               SUM(CASE WHEN sp.CodigoMovimiento IS NOT NULL THEN 1 ELSE 0 END) as con_codmov
                        FROM stockp sp
                        INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                        WHERE cp.TipoComprobante = 'PED'
                          AND cp.Anulado = 'No'
                          AND (sp.anulado IS NULL OR sp.anulado = 'No')
                          AND cp.Estado IN ('En preparación', 'Preparado')
                          AND COALESCE(sp.cantidad_pendiente, sp.Cantidad - COALESCE(sp.cantidad_entregada, 0)) > 0
                    """)
                    row = cursor.fetchone()
                    total_reservado = row[0]
                    self.stdout.write(f'   Renglones PED (En prep/Preparado) con qty pendiente > 0: {total_reservado}')

                    if total_reservado and total_reservado > 0:
                        cursor.execute("""
                            SELECT COUNT(*) as con_dep, SUM(CASE WHEN sp.CodDeposito IS NULL OR TRIM(COALESCE(sp.CodDeposito,'')) = '' THEN 1 ELSE 0 END) as sin_dep
                            FROM stockp sp
                            INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                            WHERE cp.TipoComprobante = 'PED'
                              AND cp.Anulado = 'No'
                              AND (sp.anulado IS NULL OR sp.anulado = 'No')
                              AND cp.Estado IN ('En preparación', 'Preparado')
                              AND COALESCE(sp.cantidad_pendiente, sp.Cantidad - COALESCE(sp.cantidad_entregada, 0)) > 0
                        """)
                        row = cursor.fetchone()
                        con_dep = total_reservado - (row[1] or 0)  # los que tienen CodDeposito
                        sin_dep = row[1] or 0
                        self.stdout.write(f'   Con CodDeposito poblado (no null/no vacío): {con_dep}')
                        self.stdout.write(f'   Sin CodDeposito (null o vacío): {sin_dep}')

                        cursor.execute("""
                            SELECT sp.IDArt, sp.CodDeposito, d.NombreDeposito,
                                   COALESCE(sp.cantidad_pendiente, sp.Cantidad - COALESCE(sp.cantidad_entregada, 0)) as qty
                            FROM stockp sp
                            INNER JOIN comp_ped cp ON cp.CodigoMovimiento = sp.CodigoMovimiento
                            LEFT JOIN deposito d ON d.CodDeposito = sp.CodDeposito
                            WHERE cp.TipoComprobante = 'PED'
                              AND cp.Anulado = 'No'
                              AND (sp.anulado IS NULL OR sp.anulado = 'No')
                              AND cp.Estado IN ('En preparación', 'Preparado')
                              AND COALESCE(sp.cantidad_pendiente, sp.Cantidad - COALESCE(sp.cantidad_entregada, 0)) > 0
                            ORDER BY sp.IDArt
                            LIMIT 10
                        """)
                        rows = cursor.fetchall()
                        self.stdout.write('   Muestra (IDArt, CodDeposito, depósito, qty):')
                        for r in rows:
                            self.stdout.write(f'      {r[0]}, {r[1]}, {r[2] or "?"}, {r[3]}')
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'   Error: {e}'))

                self.stdout.write('')
                self.stdout.write('=' * 70)
                self.stdout.write('Fin de verificación')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error de conexión: {e}'))
            import traceback
            self.stdout.write(traceback.format_exc())
