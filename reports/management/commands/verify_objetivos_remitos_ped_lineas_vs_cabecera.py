# -*- coding: utf-8 -*-
"""
Verificación en MySQL: totales por cliente de REM / PED «pedidos en armado»
cabecera (comp_ped.SubtotalDesc) vs suma de líneas (stockp.PrecioNetoxR).

Misma lógica base que ventas_objetivos_bo_runner (REM con fecha; PED armado sin fecha).

Uso:
  docker exec Synap_app python manage.py verify_objetivos_remitos_ped_lineas_vs_cabecera \\
    --base-empresa MiBase --fecha-inicio 2026-04-01 --fecha-fin 2026-04-30

Ver docs/reports/ANALISIS_REMITOS_PED_ARMADO_LINEAS_VS_CABECERA_OBJETIVOS.md
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand

from reports.services.articulo_venta_sql import sql_excluir_tipo_art_gasto
from reports.services.connection_pool import get_mysql_pool


def _dec(x) -> Decimal:
    if x is None:
        return Decimal("0")
    return Decimal(str(x))


class Command(BaseCommand):
    help = (
        "Compara cabecera comp_ped vs suma stockp.PrecioNetoxR para REM (con fecha) "
        "y PED en armado (sin fecha), como el informe objetivos vs BO."
    )

    def add_arguments(self, parser):
        parser.add_argument("--base-empresa", type=str, required=True, help="Base MySQL AdministraNET")
        parser.add_argument("--fecha-inicio", type=str, required=True, help="YYYY-MM-DD (solo REM)")
        parser.add_argument("--fecha-fin", type=str, required=True, help="YYYY-MM-DD (solo REM)")
        parser.add_argument(
            "--tol",
            type=float,
            default=1.0,
            help="Tolerancia en pesos por cliente entre cabecera y líneas (default 1.0)",
        )
        parser.add_argument(
            "--sin-excluir-gasto",
            action="store_true",
            help="No calcular la variante de líneas excluyendo articulo.tipo_art = Gasto",
        )

    def handle(self, *args, **options):
        base = options["base_empresa"]
        fi = options["fecha_inicio"]
        ff = options["fecha_fin"]
        tol = Decimal(str(options["tol"]))
        calc_sin_gasto = not options["sin_excluir_gasto"]

        pool = get_mysql_pool()
        self.stdout.write(self.style.SUCCESS(f"Base: {base} | REM período {fi} .. {ff}\n"))

        where_rem = [
            "cp.Fecha >= %s",
            "cp.Fecha <= %s",
            "cp.TipoComprobante = 'REM'",
            "cp.Anulado = 'No'",
            "cp.Estado = 'Pendiente'",
        ]
        params_rem = [fi, ff]

        where_ped = [
            "cp.TipoComprobante = 'PED'",
            "cp.Anulado = 'No'",
            "cp.Estado IN ('En preparación', 'Preparado')",
        ]
        params_ped: list = []

        sp_join_rem = """
            INNER JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
                AND (sp.anulado IS NULL OR sp.anulado = 'No')
                AND (sp.Comprobante = 'REM' OR sp.Comprobante IS NULL OR sp.Comprobante = '')
        """
        sp_join_ped = """
            INNER JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
                AND (sp.anulado IS NULL OR sp.anulado = 'No')
                AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL OR sp.Comprobante = '')
        """

        sql_rem_cli = f"""
            SELECT cp.Codigo AS id_cliente, SUM(COALESCE(cp.SubtotalDesc, 0)) AS cab
            FROM comp_ped cp
            WHERE {' AND '.join(where_rem)}
            GROUP BY cp.Codigo
        """
        sql_rem_lines_all = f"""
            SELECT cp.Codigo AS id_cliente, SUM(COALESCE(sp.PrecioNetoxR, 0)) AS lin
            FROM comp_ped cp
            {sp_join_rem}
            LEFT JOIN articulo a ON a.IDArt = sp.IDArt
            WHERE {' AND '.join(where_rem)}
            GROUP BY cp.Codigo
        """
        sql_rem_lines_no_gasto = f"""
            SELECT cp.Codigo AS id_cliente, SUM(COALESCE(sp.PrecioNetoxR, 0)) AS lin
            FROM comp_ped cp
            {sp_join_rem}
            LEFT JOIN articulo a ON a.IDArt = sp.IDArt
            WHERE {' AND '.join(where_rem)}
              AND {sql_excluir_tipo_art_gasto("a")}
            GROUP BY cp.Codigo
        """

        sql_ped_cli = f"""
            SELECT cp.Codigo AS id_cliente, SUM(COALESCE(cp.SubtotalDesc, 0)) AS cab
            FROM comp_ped cp
            WHERE {' AND '.join(where_ped)}
            GROUP BY cp.Codigo
        """
        sql_ped_lines_all = f"""
            SELECT cp.Codigo AS id_cliente, SUM(COALESCE(sp.PrecioNetoxR, 0)) AS lin
            FROM comp_ped cp
            {sp_join_ped}
            LEFT JOIN articulo a ON a.IDArt = sp.IDArt
            WHERE {' AND '.join(where_ped)}
            GROUP BY cp.Codigo
        """
        sql_ped_lines_no_gasto = f"""
            SELECT cp.Codigo AS id_cliente, SUM(COALESCE(sp.PrecioNetoxR, 0)) AS lin
            FROM comp_ped cp
            {sp_join_ped}
            LEFT JOIN articulo a ON a.IDArt = sp.IDArt
            WHERE {' AND '.join(where_ped)}
              AND {sql_excluir_tipo_art_gasto("a")}
            GROUP BY cp.Codigo
        """

        # Documentos sin líneas (cabecera > 0)
        sql_rem_sin_lineas = f"""
            SELECT COUNT(*) FROM (
                SELECT cp.CodigoMovimiento
                FROM comp_ped cp
                WHERE {' AND '.join(where_rem)}
                  AND COALESCE(cp.SubtotalDesc, 0) <> 0
                  AND NOT EXISTS (
                      SELECT 1 FROM stockp sp
                      WHERE sp.CodigoMovimiento = cp.CodigoMovimiento
                        AND (sp.anulado IS NULL OR sp.anulado = 'No')
                  )
            ) z
        """
        sql_ped_sin_lineas = f"""
            SELECT COUNT(*) FROM (
                SELECT cp.CodigoMovimiento
                FROM comp_ped cp
                WHERE {' AND '.join(where_ped)}
                  AND COALESCE(cp.SubtotalDesc, 0) <> 0
                  AND NOT EXISTS (
                      SELECT 1 FROM stockp sp
                      WHERE sp.CodigoMovimiento = cp.CodigoMovimiento
                        AND (sp.anulado IS NULL OR sp.anulado = 'No')
                  )
            ) z
        """

        # Top deltas por comprobante REM
        sql_rem_doc_delta = f"""
            SELECT cp.CodigoMovimiento, cp.Codigo AS id_cliente, cp.NroComprobante,
                   COALESCE(cp.SubtotalDesc, 0) AS cab,
                   COALESCE(SUM(sp.PrecioNetoxR), 0) AS lin
            FROM comp_ped cp
            LEFT JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
                AND (sp.anulado IS NULL OR sp.anulado = 'No')
                AND (sp.Comprobante = 'REM' OR sp.Comprobante IS NULL OR sp.Comprobante = '')
            WHERE {' AND '.join(where_rem)}
            GROUP BY cp.CodigoMovimiento, cp.Codigo, cp.NroComprobante, cp.SubtotalDesc
            HAVING ABS(COALESCE(cp.SubtotalDesc, 0) - COALESCE(SUM(sp.PrecioNetoxR), 0)) > %s
            ORDER BY ABS(COALESCE(cp.SubtotalDesc, 0) - COALESCE(SUM(sp.PrecioNetoxR), 0)) DESC
            LIMIT 15
        """

        sql_ped_doc_delta = f"""
            SELECT cp.CodigoMovimiento, cp.Codigo AS id_cliente, cp.NroComprobante,
                   COALESCE(cp.SubtotalDesc, 0) AS cab,
                   COALESCE(SUM(sp.PrecioNetoxR), 0) AS lin
            FROM comp_ped cp
            LEFT JOIN stockp sp ON sp.CodigoMovimiento = cp.CodigoMovimiento
                AND (sp.anulado IS NULL OR sp.anulado = 'No')
                AND (sp.Comprobante = 'PED' OR sp.Comprobante IS NULL OR sp.Comprobante = '')
            WHERE {' AND '.join(where_ped)}
            GROUP BY cp.CodigoMovimiento, cp.Codigo, cp.NroComprobante, cp.SubtotalDesc
            HAVING ABS(COALESCE(cp.SubtotalDesc, 0) - COALESCE(SUM(sp.PrecioNetoxR), 0)) > %s
            ORDER BY ABS(COALESCE(cp.SubtotalDesc, 0) - COALESCE(SUM(sp.PrecioNetoxR), 0)) DESC
            LIMIT 15
        """

        def merge_maps(rows_cli, rows_lin):
            cab = {int(r[0]): _dec(r[1]) for r in rows_cli}
            lin = {int(r[0]): _dec(r[1]) for r in rows_lin}
            ids = set(cab.keys()) | set(lin.keys())
            return ids, cab, lin

        def report_block(title: str, ids: set, cab: dict, lin: dict):
            sum_cab = sum(cab.values(), start=Decimal("0"))
            sum_lin = sum(lin.values(), start=Decimal("0"))
            self.stdout.write(self.style.WARNING(f"\n=== {title} ==="))
            self.stdout.write(f"Total cabecera (suma clientes): {sum_cab}")
            self.stdout.write(f"Total líneas PrecioNetoxR:       {sum_lin}")
            self.stdout.write(f"Delta global:                    {sum_cab - sum_lin}")

            bad = []
            for cid in sorted(ids):
                c = cab.get(cid, Decimal("0"))
                l = lin.get(cid, Decimal("0"))
                if abs(c - l) > tol:
                    bad.append((cid, c, l, c - l))
            self.stdout.write(f"Clientes con |cab - lin| > {tol}: {len(bad)}")
            for cid, c, l, d in bad[:20]:
                self.stdout.write(f"   cliente {cid}: cab={c} lin={l} delta={d}")
            if len(bad) > 20:
                self.stdout.write(f"   ... y {len(bad) - 20} más")

        try:
            with pool.get_connection(base) as conn:
                cur = conn.cursor()

                cur.execute(sql_rem_cli, params_rem)
                rem_cli = cur.fetchall()
                cur.execute(sql_rem_lines_all, params_rem)
                rem_lin_all = cur.fetchall()
                rem_lin_ng = rem_lin_all
                if calc_sin_gasto:
                    cur.execute(sql_rem_lines_no_gasto, params_rem)
                    rem_lin_ng = cur.fetchall()

                ids, cab, lin_all = merge_maps(rem_cli, rem_lin_all)
                report_block("REMITOS Pendientes — líneas TODAS (stockp REM/null)", ids, cab, lin_all)
                if calc_sin_gasto:
                    _, _, lin_ng = merge_maps(rem_cli, rem_lin_ng)
                    report_block("REMITOS Pendientes — líneas sin tipo_art Gasto", ids, cab, lin_ng)

                cur.execute(sql_rem_sin_lineas, params_rem)
                n_sl = cur.fetchone()[0]
                self.stdout.write(f"\nREM con SubtotalDesc <> 0 y sin ninguna fila stockp (no anulada): {n_sl}")

                cur.execute(sql_rem_doc_delta, params_rem + [float(tol)])
                docs = cur.fetchall()
                if docs:
                    self.stdout.write("\nREM — muestra comprobantes |cab - Σ líneas| > tol:")
                    for row in docs:
                        self.stdout.write(
                            f"   mov={row[0]} cliente={row[1]} nro={row[2]} cab={row[3]} lin={row[4]} "
                            f"delta={_dec(row[3]) - _dec(row[4])}"
                        )

                cur.execute(sql_ped_cli, params_ped)
                ped_cli = cur.fetchall()
                cur.execute(sql_ped_lines_all, params_ped)
                ped_lin_all = cur.fetchall()
                ped_lin_ng = ped_lin_all
                if calc_sin_gasto:
                    cur.execute(sql_ped_lines_no_gasto, params_ped)
                    ped_lin_ng = cur.fetchall()

                ids_p, cab_p, lin_p_all = merge_maps(ped_cli, ped_lin_all)
                report_block(
                    "PED En preparación/Preparado — líneas TODAS (stockp PED/null) — sin filtro fecha cp.Fecha",
                    ids_p,
                    cab_p,
                    lin_p_all,
                )
                if calc_sin_gasto:
                    _, _, lin_pn = merge_maps(ped_cli, ped_lin_ng)
                    report_block(
                        "PED En preparación/Preparado — líneas sin tipo_art Gasto",
                        ids_p,
                        cab_p,
                        lin_pn,
                    )

                cur.execute(sql_ped_sin_lineas, params_ped)
                n_sp = cur.fetchone()[0]
                self.stdout.write(
                    f"\nPED armado con SubtotalDesc <> 0 y sin ninguna fila stockp (no anulada): {n_sp}"
                )

                cur.execute(sql_ped_doc_delta, params_ped + [float(tol)])
                docs_p = cur.fetchall()
                if docs_p:
                    self.stdout.write("\nPED armado — muestra comprobantes |cab - Σ líneas| > tol:")
                    for row in docs_p:
                        self.stdout.write(
                            f"   mov={row[0]} cliente={row[1]} nro={row[2]} cab={row[3]} lin={row[4]} "
                            f"delta={_dec(row[3]) - _dec(row[4])}"
                        )

                self.stdout.write(
                    self.style.SUCCESS(
                        "\nListo. Interpretación: si delta global y clientes discordantes son ~0 "
                        "dentro de tol, conviene PrecioNetoxR por IDArt para implementación por artículo."
                    )
                )

        except Exception as ex:
            self.stderr.write(self.style.ERROR(f"Error: {ex}"))
            raise
