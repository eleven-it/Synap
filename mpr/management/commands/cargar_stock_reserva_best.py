"""Comando: carga stock de seguridad BEST (MC.MCSS) → articulo.stock_reserva."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from core.utils.administranet_types import to_int_or_none
from mpr.best_migration.stock_reserva_loader import migrar_stock_reserva_best


class Command(BaseCommand):
    help = (
        "Carga stock de seguridad BEST (MC.MCSS, pares) en articulo.stock_reserva. "
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
            help="Confirma la actualización en MySQL.",
        )
        parser.add_argument(
            "--mcccid",
            type=int,
            default=4003,
            help="Centro de costo BEST (default 4003 = Terminado).",
        )
        parser.add_argument(
            "--incluir-ceros",
            action="store_true",
            help="También escribe stock_reserva=0 en mapeados sin MCSS (puede pisar reservas manuales).",
        )
        parser.add_argument(
            "--id-usuario",
            type=int,
            default=None,
            help="IdUsuario legacy para actualizar_pedidos_produccion post-carga.",
        )

    def handle(self, *args, **options):
        base = (options.get("base_empresa") or "").strip()
        if not base:
            self.stdout.write(self.style.ERROR("Indique --base-empresa."))
            return

        confirmar = bool(options.get("confirmar"))
        dry_run = not confirmar if not options.get("dry_run") else True
        mcccid = to_int_or_none(options.get("mcccid")) or 4003
        incluir_ceros = bool(options.get("incluir_ceros"))
        id_usuario = to_int_or_none(options.get("id_usuario"))

        try:
            result = migrar_stock_reserva_best(
                base,
                dry_run=dry_run,
                mcccid=mcccid,
                incluir_ceros=incluir_ceros,
                id_usuario=id_usuario if confirmar else None,
            )
        except ValueError as exc:
            self.stdout.write(self.style.ERROR(str(exc)))
            return
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Error: {exc}"))
            return

        modo = "ENSAYO (dry-run)" if result.get("dry_run") else "CONFIRMADO"
        self.stdout.write(
            self.style.NOTICE(f"=== Stock de seguridad BEST → stock_reserva — {modo} ===")
        )
        self.stdout.write(f"Base: {base} | MCCCID: {result.get('mcccid', mcccid)}")
        self.stdout.write(
            f"Filas MC leídas: {result.get('leidos', 0)} | "
            f"con MCSS>0: {result.get('con_mcss', 0)} | "
            f"mapeados a actualizar: {result.get('mapeados', 0)}"
        )
        self.stdout.write(
            f"A actualizar (delta): {result.get('actualizados', 0)} | "
            f"sin cambio: {result.get('sin_cambio', 0)} | "
            f"huérfanos MCSS>0: {result.get('huerfanos', 0)}"
        )

        muestra = result.get("muestra") or []
        if muestra:
            self.stdout.write("Muestra (best_id → IDArt, MCSS, actual Admin):")
            for m in muestra[:10]:
                self.stdout.write(
                    f"  · {m.get('best_id')} → {m.get('idart')}: "
                    f"MCSS={m.get('mcss')} (actual={m.get('actual', '—')})"
                )

        huerfanos = result.get("huerfanos_muestra") or []
        if huerfanos:
            self.stdout.write(self.style.WARNING("Huérfanos MCSS>0 sin mapa (muestra):"))
            for h in huerfanos[:10]:
                self.stdout.write(
                    f"  · BEST {h.get('best_id')}: MCSS={h.get('mcss')}"
                )

        if not result.get("dry_run"):
            post_ok = result.get("post_actualizar_ok")
            if post_ok is not None:
                estado = "OK" if post_ok else "FALLÓ"
                self.stdout.write(
                    f"Post actualizar_pedidos_produccion: {estado} — "
                    f"{result.get('post_actualizar_mensaje') or '-'}"
                )

        errores = result.get("errores") or []
        if errores:
            self.stdout.write(self.style.WARNING("Errores:"))
            for err in errores[:10]:
                self.stdout.write(f"  · {err}")

        if result.get("dry_run"):
            self.stdout.write(
                self.style.SUCCESS(
                    "Ensayo completado. Ejecutá con --confirmar para grabar."
                )
            )
        elif result.get("actualizados", 0) > 0:
            self.stdout.write(self.style.SUCCESS("Carga confirmada."))
        else:
            self.stdout.write(self.style.WARNING("No se actualizaron artículos."))
