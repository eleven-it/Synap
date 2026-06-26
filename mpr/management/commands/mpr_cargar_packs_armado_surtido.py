"""
Habilita artículos pack para armado surtido (MprArticuloArmadoSurtido).

Uso:
  python manage.py mpr_cargar_packs_armado_surtido --base-empresa MI_EMPRESA --ids 101,102,103
  python manage.py mpr_cargar_packs_armado_surtido --base-empresa MI_EMPRESA --ids 101 --desactivar
"""
from django.core.management.base import BaseCommand, CommandError

from mpr.models import MprArticuloArmadoSurtido


class Command(BaseCommand):
    help = "Carga o actualiza packs habilitados para armado surtido MPR."

    def add_arguments(self, parser):
        parser.add_argument("--base-empresa", required=True, help="Código de base empresa (sesión MPR).")
        parser.add_argument(
            "--ids",
            required=True,
            help="IDs de artículo separados por coma (IDArt).",
        )
        parser.add_argument(
            "--desactivar",
            action="store_true",
            help="Marca los artículos como inactivos en lugar de activarlos.",
        )

    def handle(self, *args, **options):
        base = (options["base_empresa"] or "").strip()
        if not base:
            raise CommandError("Indique --base-empresa.")
        raw_ids = (options["ids"] or "").strip()
        ids = []
        for part in raw_ids.split(","):
            part = part.strip()
            if not part:
                continue
            try:
                ids.append(int(part))
            except ValueError as e:
                raise CommandError(f"ID inválido: {part}") from e
        if not ids:
            raise CommandError("Indique al menos un id en --ids.")
        activo = not options["desactivar"]
        creados = 0
        actualizados = 0
        for id_art in ids:
            obj, created = MprArticuloArmadoSurtido.objects.update_or_create(
                base_empresa=base,
                id_articulo=id_art,
                defaults={"activo": activo},
            )
            if created:
                creados += 1
            elif obj.activo != activo:
                actualizados += 1
        estado = "activos" if activo else "inactivos"
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(ids)} artículo(s) en {base}: {creados} creado(s), "
                f"{actualizados} actualizado(s); estado {estado}."
            )
        )
