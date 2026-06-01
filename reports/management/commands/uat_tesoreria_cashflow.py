"""UAT: comparar tesoreria Command Center vs cash_flow_waterfall."""
from __future__ import annotations

import json
from datetime import date

from django.core.management.base import BaseCommand

from reports.models import ReportDefinition
from reports.services.executive_dashboard.base import DashboardFilters, legacy_cursor
from reports.services.executive_dashboard.tesoreria_metrics import fetch_tesoreria_resumen
from reports.services.executive_dashboard.ventas_cobros_metrics import fetch_ventas_cobros_resumen
from reports.services.query_runner import QueryRunnerService


class Command(BaseCommand):
    help = "UAT tesorería vs cash_flow_waterfall (misma base y período)."

    def add_arguments(self, parser):
        parser.add_argument("--base", default="administranet")
        parser.add_argument("--fecha-inicio", default="2026-05-01")
        parser.add_argument("--fecha-fin", default="2026-05-19")

    def handle(self, *args, **options):
        base = options["base"]
        fi = date.fromisoformat(options["fecha_inicio"])
        ff = date.fromisoformat(options["fecha_fin"])
        filters = DashboardFilters(
            base_empresa=base,
            fecha_referencia=ff,
            fecha_inicio=fi,
            fecha_fin=ff,
            cod_sucursal=None,
        )

        with legacy_cursor(base) as cursor:
            tes = fetch_tesoreria_resumen(cursor, filters)
            cob = fetch_ventas_cobros_resumen(cursor, filters)

        report = ReportDefinition.objects.filter(slug="cash_flow_waterfall").first()
        wf = None
        if report:
            runner = QueryRunnerService(user=None)
            wf = runner._run_cash_flow_waterfall(
                report,
                {
                    "filters": {
                        "base_empresa": base,
                        "fecha_inicio": filters.fecha_inicio_str,
                        "fecha_fin": filters.fecha_fin_str,
                    }
                },
            )

        self.stdout.write(f"=== UAT {fi} -> {ff} | {base} ===\n")
        self.stdout.write("--- TESORERIA ---\n")
        for k in (
            "saldo_inicial",
            "saldo_final",
            "saldo_final_coherente",
            "saldo_final_sistema",
            "drift_sistema",
            "ingresos_operativos",
            "egresos_operativos",
            "variacion_neta",
            "ingresos_ventas",
            "ingresos_cobranzas",
            "egresos_proveedores",
        ):
            self.stdout.write(f"  {k}: {tes[k]}\n")

        self.stdout.write("--- VENTAS COBROS ---\n")
        self.stdout.write(f"  facturado total: {cob['facturado_por_medio']['total']}\n")
        self.stdout.write(f"  cobrado total: {cob['cobrado_caja_por_medio']['total']}\n")

        if not wf:
            self.stdout.write(self.style.WARNING("cash_flow_waterfall no configurado\n"))
            return

        t = wf.totals or {}
        data = wf.data or []
        self.stdout.write("--- WATERFALL totals ---\n")
        self.stdout.write(json.dumps(t, default=str, indent=2) + "\n")

        sum_ing = sum(float(r.get("operating_ingresos") or 0) for r in data if isinstance(r, dict))
        sum_egr = sum(float(r.get("operating_egresos") or 0) for r in data if isinstance(r, dict))

        def cmp_line(name, cc_val, wf_val, tol=1.0):
            diff = abs(float(cc_val or 0) - float(wf_val or 0))
            ok = diff <= tol
            style = self.style.SUCCESS if ok else self.style.WARNING
            self.stdout.write(
                style(f"  {name}: CC={cc_val} WF={wf_val} diff={round(diff, 2)} {'OK' if ok else 'REVISAR'}\n")
            )

        self.stdout.write("--- COMPARACION (tol 1.00) ---\n")
        cmp_line("saldo_inicial", tes["saldo_inicial"], t.get("saldo_inicial"))
        cmp_line(
            "saldo_final_coherente",
            tes["saldo_final_coherente"],
            t.get("saldo_final_coherente") or t.get("saldo_final"),
        )
        cmp_line(
            "saldo_final_sistema",
            tes["saldo_final_sistema"],
            t.get("saldo_final_sistema"),
        )
        wf_ing = t.get("total_operating_ingresos") or t.get("operating_ingresos") or sum_ing
        wf_egr = t.get("total_operating_egresos") or t.get("operating_egresos") or sum_egr
        cmp_line("ingresos_operativos", tes["ingresos_operativos"], wf_ing)
        cmp_line("egresos_operativos", tes["egresos_operativos"], wf_egr)
        cmp_line("variacion_neta", tes["variacion_neta"], t.get("cash_variation") or t.get("operating_flow"))
