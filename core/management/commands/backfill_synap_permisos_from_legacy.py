# -*- coding: utf-8 -*-
"""
Backfill de permisos Synap desde las tablas legacy hacia las tablas ``synap_*``.

Estrategia (rol dedicado por puesto): por cada puesto con permisos Synap 'Si' en
permiso_sistema_puesto (limitado a los key_permiso del catálogo synap_permiso), se
crea/reutiliza un rol (``es_sistema=1``), se mapea el puesto a ese rol y se asignan
los permisos. Idempotente.

Lógica: core.services.synap_permisos.backfill_synap_permisos_desde_legacy
Referencia: openspec/changes/permisos-roles-synap-independientes/design.md
"""
from django.core.management.base import BaseCommand

from core.services.synap_permisos import backfill_synap_permisos_desde_legacy


class Command(BaseCommand):
    help = (
        "Importa las asignaciones de permisos Synap desde las tablas legacy "
        "(permiso_sistema_puesto) hacia synap_* (rol por puesto). "
        "Ejemplo: backfill_synap_permisos_from_legacy administranet96 --dry-run"
    )

    def add_arguments(self, parser):
        parser.add_argument("base_empresa", type=str, help="Base de datos de la empresa.")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Calcula y muestra el backfill sin escribir en synap_*.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-sincroniza: reemplaza los permisos del rol de cada puesto según el legacy.",
        )

    def handle(self, *args, **options):
        base_empresa = (options.get("base_empresa") or "").strip()
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique base_empresa (ej: administranet96)."))
            return

        resultado = backfill_synap_permisos_desde_legacy(
            base_empresa,
            dry_run=bool(options.get("dry_run")),
            force=bool(options.get("force")),
        )

        for detalle in resultado.get("detalles") or []:
            self.stdout.write(f"  · {detalle}")

        if resultado.get("success"):
            self.stdout.write(self.style.SUCCESS(resultado.get("message", "OK")))
        else:
            self.stdout.write(self.style.ERROR(resultado.get("message", "Error")))
