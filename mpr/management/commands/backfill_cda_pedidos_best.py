"""Comando: remediación CDA para PED BEST ya migrados."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from mpr.best_migration.pedido_cda_backfill import backfill_cda_pedidos_best


class Command(BaseCommand):
    help = (
        "Remedia cliente_datos_adicionales en PED BEST ya sembrados (comp_ped + stockp). "
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
            "--prefijo",
            type=str,
            default="BEST",
            help="Prefijo NroComprobante (default BEST → BEST-<orden>).",
        )

    def handle(self, *args, **options):
        base = (options.get("base_empresa") or "").strip()
        if not base:
            self.stdout.write(self.style.ERROR("Indique --base-empresa."))
            return

        confirmar = bool(options.get("confirmar"))
        dry_run = not confirmar if not options.get("dry_run") else True
        prefijo = (options.get("prefijo") or "BEST").strip() or "BEST"

        try:
            result = backfill_cda_pedidos_best(
                base,
                dry_run=dry_run,
                prefijo=prefijo,
            )
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Error: {exc}"))
            return

        modo = "ENSAYO (dry-run)" if result.get("dry_run") else "CONFIRMADO"
        self.stdout.write(
            self.style.NOTICE(f"=== Backfill CDA pedidos BEST — {modo} ===")
        )
        self.stdout.write(f"Base: {base}")
        self.stdout.write(f"Prefijo: {prefijo}")
        self.stdout.write(
            f"Pedidos revisados: {result.get('pedidos_revisados', 0)} | "
            f"ya OK: {result.get('ya_ok', 0)} | "
            f"insertados: {result.get('insertados', 0)} | "
            f"actualizados: {result.get('actualizados', 0)} | "
            f"sin domicilio: {result.get('omitidos_sin_domicilio', 0)}"
        )

        omitidos = result.get("detalle_omitidos") or []
        if omitidos:
            self.stdout.write(self.style.WARNING("Omitidos sin domicilio (muestra):"))
            for item in omitidos[:10]:
                self.stdout.write(
                    f"  · {item.get('nro_comprobante')} "
                    f"(cliente {item.get('id_cliente')}, cod_mov {item.get('cod_mov')})"
                )

        escritos = result.get("detalle_escritos") or []
        if escritos:
            self.stdout.write("Escrituras previstas/ejecutadas (muestra):")
            for item in escritos[:10]:
                self.stdout.write(
                    f"  · {item.get('accion')} {item.get('nro_comprobante')} "
                    f"(cod_mov {item.get('cod_mov')}, dom {item.get('id_domicilio')})"
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
        elif (result.get("insertados", 0) + result.get("actualizados", 0)) > 0:
            self.stdout.write(self.style.SUCCESS("Remediación confirmada."))
        else:
            self.stdout.write(
                self.style.WARNING("No se escribieron filas en cliente_datos_adicionales.")
            )
