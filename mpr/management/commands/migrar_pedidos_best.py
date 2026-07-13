"""Comando: siembra pedidos abiertos BEST → PED AdministraNET."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from core.utils.administranet_types import to_int_or_none
from mpr.best_migration.pedido_loader import migrar_pedidos_best


class Command(BaseCommand):
    help = (
        "Siembra pedidos abiertos BEST como PED (comp_ped + stockp) en AdministraNET. "
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
            help="Confirma la siembra en MySQL (requiere gate abierto e id-usuario).",
        )
        parser.add_argument(
            "--id-usuario",
            type=int,
            default=None,
            help="IdUsuario legacy para comp_ped (obligatorio con --confirmar).",
        )
        parser.add_argument(
            "--id-pv",
            type=int,
            default=1,
            help="Punto de venta para talonario PED (default 1).",
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
        id_usuario = to_int_or_none(options.get("id_usuario"))
        id_pv = to_int_or_none(options.get("id_pv")) or 1
        prefijo = (options.get("prefijo") or "BEST").strip() or "BEST"

        if confirmar and not id_usuario:
            self.stdout.write(
                self.style.ERROR(
                    "Con --confirmar debe indicar --id-usuario (usuario legacy AdministraNET)."
                )
            )
            return

        try:
            result = migrar_pedidos_best(
                base,
                dry_run=dry_run,
                id_usuario=id_usuario,
                id_pv=id_pv,
                prefijo=prefijo,
            )
        except ValueError as exc:
            self.stdout.write(self.style.ERROR(str(exc)))
            return
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Error: {exc}"))
            return

        modo = "ENSAYO (dry-run)" if result.get("dry_run") else "CONFIRMADO"
        gate = "abierto" if result.get("gate_ok") else "cerrado"
        self.stdout.write(self.style.NOTICE(f"=== Migración pedidos BEST — {modo} ==="))
        self.stdout.write(f"Base: {base}")
        self.stdout.write(f"Gate: {gate}")
        self.stdout.write(
            f"Órdenes leídas: {result.get('ordenes_leidas', 0)} | "
            f"migrables: {result.get('ordenes_migrables', 0)} | "
            f"omitidas: {result.get('ordenes_omitidas', 0)}"
        )
        self.stdout.write(
            f"Líneas OK: {result.get('lineas_ok', 0)} | "
            f"huérfanas: {result.get('lineas_huerfanas', 0)}"
        )

        if not result.get("dry_run"):
            self.stdout.write(
                f"Pedidos escritos: {result.get('pedidos_escritos', 0)} | "
                f"omitidos (en producción): {result.get('pedidos_omitidos_existentes', 0)}"
            )
            post_ok = result.get("post_actualizar_ok")
            if post_ok is not None:
                estado = "OK" if post_ok else "FALLÓ"
                self.stdout.write(
                    f"Post actualizar_pedidos_produccion: {estado} — "
                    f"{result.get('post_actualizar_mensaje') or '-'}"
                )

        huerfanos = result.get("huerfanos_detalle") or []
        if huerfanos:
            self.stdout.write(self.style.WARNING("Huérfanos (muestra):"))
            for h in huerfanos[:10]:
                self.stdout.write(
                    f"  · orden {h.get('orden')}: [{h.get('tipo')}] {h.get('detalle')}"
                )

        errores = result.get("errores") or []
        if errores:
            self.stdout.write(self.style.WARNING("Errores / avisos:"))
            for err in errores[:10]:
                self.stdout.write(f"  · {err}")

        if result.get("dry_run"):
            self.stdout.write(
                self.style.SUCCESS(
                    "Ensayo completado. Ejecutá con --confirmar --id-usuario=N para grabar."
                )
            )
        elif result.get("pedidos_escritos", 0) > 0:
            self.stdout.write(self.style.SUCCESS("Siembra confirmada."))
        else:
            self.stdout.write(self.style.WARNING("No se escribieron pedidos."))
