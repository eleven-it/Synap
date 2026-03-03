"""
Ejercicio de reconciliación: saldo_pedido_proveedor vs movimientos teóricos (sumando como VB6).

Determina si el saldo_pedido_proveedor en stock_deposito se explica replicando la lógica VB6:
  teórico = +OC + Remitos desde OC + Facturas OC - Anulaciones OC

Uso:
  python manage.py reconcile_saldo_pedido_proveedor --base-empresa administranet89
  python manage.py reconcile_saldo_pedido_proveedor --base-empresa administranet89 --ejercicio 1
  python manage.py reconcile_saldo_pedido_proveedor --base-empresa administranet89 --fecha-desde 2024-01-01 --fecha-hasta 2024-12-31
"""
from django.core.management.base import BaseCommand
from reports.services.connection_pool import get_mysql_pool
from reports.services.reconciliation_saldo_pedido_proveedor import (
    run_reconciliation,
    get_ejercicio,
)


class Command(BaseCommand):
    help = "Reconciliación saldo_pedido_proveedor: verifica si se explica sumando movimientos OC/Remito/Factura OC como hace VB6"

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Nombre de la base de datos MySQL",
        )
        parser.add_argument(
            "--ejercicio",
            type=int,
            default=None,
            help="ID del ejercicio (cont_ejercicio). Si no se indica, usa el ejercicio activo.",
        )
        parser.add_argument(
            "--fecha-desde",
            type=str,
            default=None,
            help="Fecha desde (YYYY-MM-DD) para filtrar movimientos. Opcional.",
        )
        parser.add_argument(
            "--fecha-hasta",
            type=str,
            default=None,
            help="Fecha hasta (YYYY-MM-DD) para filtrar movimientos. Opcional.",
        )
        parser.add_argument(
            "--sin-filtro-fecha",
            action="store_true",
            help="Ejecutar sin filtro de fechas (todo el historial). Por defecto intenta usar ejercicio.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Máximo de artículos con diferencia a mostrar (default 20)",
        )

    def handle(self, *args, **options):
        base_empresa = options["base_empresa"]
        ejercicio_id = options["ejercicio"]
        fecha_desde = options["fecha_desde"]
        fecha_hasta = options["fecha_hasta"]
        sin_filtro = options["sin_filtro_fecha"]
        limit = options["limit"]

        pool = get_mysql_pool()
        with pool.get_connection(base_empresa) as conn:
            conn.ping()
        self.stdout.write(self.style.SUCCESS(f"Conectado a MySQL: {base_empresa}\n"))

        # Determinar rango de fechas
        if sin_filtro:
            fecha_desde = None
            fecha_hasta = None
            self.stdout.write("Modo: TODO el historial (sin filtro de fechas)\n")
        elif fecha_desde and fecha_hasta:
            self.stdout.write(f"Fechas: {fecha_desde} a {fecha_hasta}\n")
        else:
            ej = get_ejercicio(base_empresa, ejercicio_id)
            if ej:
                fecha_desde = ej.fecdesde
                fecha_hasta = ej.fechasta
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Ejercicio: {ej.nombre} (id={ej.id_ejercicio}) | {ej.fecdesde} a {ej.fechasta}\n"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "No se encontró cont_ejercicio. Ejecutando con todo el historial.\n"
                    )
                )
                fecha_desde = None
                fecha_hasta = None

        result = run_reconciliation(
            base_empresa=base_empresa,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )

        if result.get("error"):
            self.stdout.write(self.style.ERROR(f"Error: {result['error']}"))
            return

        resumen = result.get("resumen_movimientos", {})
        self.stdout.write("")
        self.stdout.write("=" * 70)
        self.stdout.write("RESUMEN DE MOVIMIENTOS")
        self.stdout.write("=" * 70)
        self.stdout.write(f"  + OC:                {resumen.get('mov_oc', 0):,.2f}")
        self.stdout.write(f"  ± Remitos:           {resumen.get('mov_remito', 0):,.2f}")
        self.stdout.write(f"  ± Facturas OC:       {resumen.get('mov_factura_oc', 0):,.2f}")
        self.stdout.write(f"  - Anulaciones:       {resumen.get('mov_anulacion', 0):,.2f}")
        self.stdout.write("-" * 70)
        self.stdout.write(f"  Teórico VB6:         {resumen.get('teorico_vb6_total', 0):,.2f} (= +OC + Rem + FactOC - Anul)")
        self.stdout.write(f"  Teórico conceptual:  {resumen.get('teorico_conceptual_total', 0):,.2f} (= +OC - Rem - FactOC - Anul)")
        self.stdout.write(f"  Actual (stock_dep):  {resumen.get('actual_total', 0):,.2f}")
        self.stdout.write(f"  B (stockp pend.):    {resumen.get('calculo_stockp_total', 0):,.2f}")
        self.stdout.write("")

        total = result.get("total_articulos", 0)
        coinc = result.get("total_coincidencias", 0)
        diff = result.get("total_diferencias", 0)
        self.stdout.write("=" * 70)
        self.stdout.write("RESULTADO POR ARTÍCULO")
        self.stdout.write("=" * 70)
        self.stdout.write(f"  Total artículos:     {total}")
        self.stdout.write(self.style.SUCCESS(f"  Coincidencias:       {coinc}"))
        self.stdout.write(self.style.WARNING(f"  Diferencias:         {diff}"))
        self.stdout.write("")

        if diff > 0:
            self.stdout.write("Artículos con diferencia:")
            self.stdout.write("-" * 70)
            for r in result.get("diferencias", [])[:limit]:
                self.stdout.write(
                    f"  {r['id_art']:6} | {r['codigo']:12} | actual={r['saldo_actual']:8.2f} | "
                    f"teórVB6={r['teorico_vb6']:8.2f} | B={r['calculo_stockp']:8.2f} | "
                    f"teórConcept={r['teorico_conceptual']:8.2f} | diffVB6={r['diferencia_vb6']:+.2f} diffConcept={r['diferencia_conceptual']:+.2f}"
                )
            if diff > limit:
                self.stdout.write(f"  ... y {diff - limit} más")

        self.stdout.write("")
        self.stdout.write(
            "Interpretación: Actual≈Teór.VB6 → VB6 consistente. B≈Teór.conceptual → pendiente correcto."
        )
        self.stdout.write("")
