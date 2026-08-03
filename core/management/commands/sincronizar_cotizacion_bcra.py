# -*- coding: utf-8 -*-
"""Job opcional: propone o aplica cotización BCRA (--dry-run por defecto)."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from core.services.cotizacion_service import aceptar, obtener_vigente, sugerir
from core.services.cotizacion_config_resolver import resolver_cotizacion_config


class Command(BaseCommand):
    help = (
        "Consulta sugerencia BCRA y propone cambio (--dry-run por defecto). "
        "Con --aplicar escribe cotizacion.ValorPesos solo si auto_aceptar_job está ON "
        "o se fuerza con --aplicar explícito del operador."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "base_empresa",
            type=str,
            help="Base MySQL de la empresa (ej: administranet89).",
        )
        parser.add_argument(
            "--aplicar",
            action="store_true",
            help="Aplicar cambio (requiere auto_aceptar_job=True en CotizacionConfig).",
        )

    def handle(self, *args, **options):
        base_empresa = (options.get("base_empresa") or "").strip()
        aplicar = bool(options.get("aplicar"))
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique base_empresa."))
            return

        cfg = resolver_cotizacion_config(base_empresa)
        vigente = obtener_vigente(base_empresa)
        sug = sugerir(base_empresa)

        vig_val = vigente.get("valor")
        sug_val = sug.get("valor")

        self.stdout.write(f"Empresa: {base_empresa}")
        self.stdout.write(f"Tipo BCRA: {cfg.get('tipo_cotizacion')}")
        self.stdout.write(f"Vigente local: {vig_val}")
        self.stdout.write(f"Sugerido BCRA: {sug_val} ({sug.get('mensaje') or 'OK'})")

        if sug_val is None:
            self.stdout.write(self.style.WARNING("Sin sugerencia BCRA; no hay cambio que proponer."))
            return

        if vig_val is not None and abs(float(sug_val) - float(vig_val)) < 1e-6:
            self.stdout.write(self.style.SUCCESS("Sugerido coincide con vigente; sin cambios."))
            return

        if not aplicar:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY-RUN: se propondría actualizar ValorPesos de {vig_val} → {sug_val}. "
                    "Use --aplicar para escribir (requiere auto_aceptar_job=True)."
                )
            )
            return

        if not cfg.get("auto_aceptar_job"):
            self.stdout.write(
                self.style.ERROR(
                    "auto_aceptar_job está desactivado para esta empresa. "
                    "No se modificó ValorPesos."
                )
            )
            return

        aceptar(
            base_empresa,
            valor=float(sug_val),
            origen="job",
            id_usuario=None,
            observacion="Job sincronizar_cotizacion_bcra",
        )
        self.stdout.write(self.style.SUCCESS(f"Aplicado: ValorPesos = {sug_val}"))
