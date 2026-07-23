"""Comando: remediación cabecera/stockp para PED BEST ya migrados."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from mpr.best_migration.pedido_best_remediar import remediar_pedidos_best


class Command(BaseCommand):
    help = (
        "Remedia PED BEST ya sembrados: renumeración Synap (0001-########), "
        "condición Cta/Cte 30, IVA P2 y campos de paridad. "
        "Por defecto ensayo (dry-run); usar --confirmar para escribir."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Base MySQL AdministraNET (ej. administranet1).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Ensayo sin escribir (default si no se pasa --confirmar).",
        )
        parser.add_argument(
            "--confirmar",
            action="store_true",
            help="Confirma la remediación en MySQL.",
        )
        parser.add_argument(
            "--id-pv",
            type=int,
            default=1,
            help="Punto de venta para numeración (default 1 → 0001-########).",
        )

    def handle(self, *args, **options):
        base = (options.get("base_empresa") or "").strip()
        if not base:
            self.stdout.write(self.style.ERROR("Indique --base-empresa."))
            return

        confirmar = bool(options.get("confirmar"))
        dry_run = not confirmar if not options.get("dry_run") else True
        id_pv = int(options.get("id_pv") or 1)

        try:
            result = remediar_pedidos_best(
                base,
                dry_run=dry_run,
                id_pv=id_pv,
            )
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Error: {exc}"))
            return

        modo = "ENSAYO (dry-run)" if result.get("dry_run") else "CONFIRMADO"
        self.stdout.write(
            self.style.NOTICE(f"=== Remediación PED BEST — {modo} ===")
        )
        self.stdout.write(f"Base: {base}")
        self.stdout.write(f"Punto de venta: {id_pv:04d}")
        self.stdout.write(
            f"Revisados: {result.get('revisados', 0)} | "
            f"remediados: {result.get('remediados', 0)} | "
            f"omitidos: {result.get('omitidos', 0)}"
        )

        mapeo = result.get("mapeo_nro") or {}
        if mapeo:
            self.stdout.write("Renumeración (muestra):")
            for old, new in list(mapeo.items())[:10]:
                self.stdout.write(f"  · {old} → {new}")

        muestra = result.get("detalle_muestra") or []
        if muestra:
            self.stdout.write("Detalle (muestra):")
            for item in muestra[:10]:
                self.stdout.write(
                    f"  · cod_mov {item.get('cod_mov')}: "
                    f"{item.get('nro_anterior')} → {item.get('nro_nuevo')} "
                    f"({item.get('lineas_stockp', 0)} renglones)"
                )

        errores = result.get("errores") or []
        if errores:
            self.stdout.write(self.style.WARNING("Errores / avisos:"))
            for err in errores[:10]:
                self.stdout.write(f"  · {err}")

        if result.get("dry_run"):
            self.stdout.write(
                self.style.SUCCESS(
                    "Ensayo completado. Ejecutá con --confirmar para grabar."
                )
            )
        elif result.get("remediados", 0) > 0:
            self.stdout.write(self.style.SUCCESS("Remediación confirmada."))
        else:
            self.stdout.write(
                self.style.WARNING("No se remediaron pedidos BEST pendientes.")
            )
