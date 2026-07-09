# -*- coding: utf-8 -*-
"""
Limpieza (purge) de los permisos Synap inyectados históricamente en las tablas VB6
compartidas ``permiso_sistema`` / ``permiso_sistema_puesto``.

SEGURIDAD:
- Solo actúa sobre filas con ``grupo_permiso = 'Synap'`` (nunca toca permisos propios
  de AdministraNET).
- Por defecto es DRY-RUN (solo informa cuántas filas se borrarían). Requiere ``--ejecutar``
  para borrar realmente.
- Debe ejecutarse SOLO tras el cutover a ``SYNAP_PERMISOS_SOURCE=synap`` estable y con el
  backfill validado (ver openspec/changes/permisos-roles-synap-independientes/design.md § P3).

Ejemplos:
  purge_synap_legacy_permisos administranet96            # dry-run (no borra)
  purge_synap_legacy_permisos administranet96 --ejecutar # borra grupo_permiso='Synap'
"""
from django.core.management.base import BaseCommand

from core.mysql_pool import get_connection

GRUPO_SYNAP = "Synap"


class Command(BaseCommand):
    help = (
        "Elimina de permiso_sistema/permiso_sistema_puesto SOLO las filas con "
        "grupo_permiso='Synap'. Por defecto dry-run; use --ejecutar para borrar."
    )

    def add_arguments(self, parser):
        parser.add_argument("base_empresa", type=str, help="Base de datos de la empresa.")
        parser.add_argument(
            "--ejecutar",
            action="store_true",
            help="Ejecuta el borrado real. Sin este flag, solo informa (dry-run).",
        )

    def handle(self, *args, **options):
        base_empresa = (options.get("base_empresa") or "").strip()
        ejecutar = bool(options.get("ejecutar"))
        if not base_empresa:
            self.stdout.write(self.style.ERROR("Indique base_empresa (ej: administranet96)."))
            return

        try:
            with get_connection(base_empresa) as conn:
                cur = conn.cursor()

                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM permiso_sistema_puesto psp
                    INNER JOIN permiso_sistema ps
                        ON ps.id_permiso_sistema = psp.id_permiso_sistema
                    WHERE ps.grupo_permiso = %s
                    """,
                    [GRUPO_SYNAP],
                )
                n_psp = cur.fetchone()[0]

                cur.execute(
                    "SELECT COUNT(*) FROM permiso_sistema WHERE grupo_permiso = %s",
                    [GRUPO_SYNAP],
                )
                n_ps = cur.fetchone()[0]

                if not ejecutar:
                    cur.close()
                    self.stdout.write(
                        self.style.WARNING(
                            f"[dry-run] {base_empresa}: se borrarían {n_psp} filas de "
                            f"permiso_sistema_puesto y {n_ps} de permiso_sistema (grupo_permiso='Synap'). "
                            "Use --ejecutar para borrar."
                        )
                    )
                    return

                cur.execute(
                    """
                    DELETE psp
                    FROM permiso_sistema_puesto psp
                    INNER JOIN permiso_sistema ps
                        ON ps.id_permiso_sistema = psp.id_permiso_sistema
                    WHERE ps.grupo_permiso = %s
                    """,
                    [GRUPO_SYNAP],
                )
                borradas_psp = cur.rowcount
                cur.execute(
                    "DELETE FROM permiso_sistema WHERE grupo_permiso = %s",
                    [GRUPO_SYNAP],
                )
                borradas_ps = cur.rowcount
                conn.commit()
                cur.close()

                self.stdout.write(
                    self.style.SUCCESS(
                        f"{base_empresa}: eliminadas {borradas_psp} filas de permiso_sistema_puesto "
                        f"y {borradas_ps} de permiso_sistema (grupo_permiso='Synap')."
                    )
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR("Error en purge Synap legacy en %s: %s" % (base_empresa, e))
            )
