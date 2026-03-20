# MPR - Inspecciona líneas armado de una OPT: componentes, saldos en Semi Elaborado y máx. armable.
# Uso: python manage.py inspeccionar_armado_opt <id_lista> --base-empresa=administranet92
# Ejemplo: docker exec Synap_app python manage.py inspeccionar_armado_opt 60 --base-empresa=administranet92

from django.core.management.base import BaseCommand

from mpr.services import get_deposito_semi_elaborado_mpr, get_lineas_armado_opt


class Command(BaseCommand):
    help = "Inspecciona líneas armado de una OPT: componentes, saldo en Semi Elaborado y máx. armable (para verificar por qué aparece Sin stock)."

    def add_arguments(self, parser):
        parser.add_argument(
            "id_lista",
            type=int,
            help="id_lista de la OPT (ej. 60 para OPT 60).",
        )
        parser.add_argument(
            "--base-empresa",
            type=str,
            required=True,
            help="Base de datos MySQL (ej. administranet92).",
        )

    def handle(self, *args, **options):
        id_lista = options["id_lista"]
        base_empresa = (options.get("base_empresa") or "").strip()
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique --base-empresa (ej. administranet92)."))
            return

        dep_semi = get_deposito_semi_elaborado_mpr(base_empresa)
        if not dep_semi:
            self.stdout.write(self.style.WARNING("No hay depósito Semi Elaborado configurado (tipo_mpr=SemiElaborado)."))
            return
        self.stdout.write("Depósito Semi Elaborado (id): %s" % dep_semi)

        lineas = get_lineas_armado_opt(base_empresa, id_lista)
        if not lineas:
            self.stdout.write(self.style.WARNING("No hay líneas armables para esta OPT (sin BOM o sin ensamblado='Si')."))
            return

        for linea in lineas:
            self.stdout.write("")
            self.stdout.write(
                "Artículo (pack): id=%s %s - %s"
                % (linea.get("id_articulo"), linea.get("codigo_articulo"), linea.get("descripcion_articulo", "")[:50])
            )
            self.stdout.write("  Receta: %s" % linea.get("nombre_bom"))
            self.stdout.write("  Máx. armable: %s" % (linea.get("max_packs_armable") if linea.get("max_packs_armable", 0) > 0 else "Sin stock (0)"))
            comps = (linea.get("bom") or {}).get("componentes") or []
            if comps:
                self.stdout.write("  Componentes (cantidad por pack / saldo en Semi Elab.):")
                for c in comps:
                    cod = c.get("codigo_articulo") or c.get("id_articulo")
                    qty = c.get("cantidad_articulo") or 0
                    saldo = c.get("saldo_semi_elaborado") or 0
                    self.stdout.write("    - %s: %.4s / %.4s" % (cod, qty, saldo))
            else:
                self.stdout.write("  (Sin componentes en BOM)")

        self.stdout.write(self.style.SUCCESS("\nFin. Revise que los componentes tengan saldo en stock_deposito para id_deposito = %s." % dep_semi))
