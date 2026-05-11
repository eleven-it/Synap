"""
Diagnóstico y reparación del esquema PostgreSQL para el panel «Resumen ejecutivo (ventas)».

Resuelve el caso típico en servidor remoto: falta la tabla ``reports_puntoventacanalejecutivo``
(modelo ``PuntoVentaCanalEjecutivo``) o existe la tabla pero no está registrada la migración
``reports.0031_add_puntoventacanalejecutivo``.

**Importante:** las migraciones Synap aplican solo a PostgreSQL (``default``). Si la conexión
``mysql`` apunta a MySQL anterior a la 8 y Django 4.2+ rechaza la conexión al ejecutar ``migrate``,
ejecutar con::

    SYNAP_MIGRATIONS_POSTGRES_ONLY=1 docker exec Synap_app python manage.py repair_panel_ejecutivo_postgres --fix

Ejemplos::

    # Solo diagnóstico (sin cambios)
    docker exec -e SYNAP_MIGRATIONS_POSTGRES_ONLY=1 Synap_app python manage.py repair_panel_ejecutivo_postgres

    # Aplicar migrate o --fake según estado
    docker exec -e SYNAP_MIGRATIONS_POSTGRES_ONLY=1 Synap_app python manage.py repair_panel_ejecutivo_postgres --fix
"""

from __future__ import annotations

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import connections
from django.db.utils import ProgrammingError

MIGRATION_APP = "reports"
MIGRATION_NAME = "0031_add_puntoventacanalejecutivo"
TABLE_NAME = "reports_puntoventacanalejecutivo"

EXPECTED_COLUMNS = frozenset({"id", "empresa_id", "id_pv", "canal", "updated_at"})


class Command(BaseCommand):
    help = (
        "Revisa en PostgreSQL la tabla del panel ejecutivo (PV canal) y opcionalmente "
        "aplica migrate o marca la migración 0031 como aplicada (--fake) si la tabla ya existe."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--fix",
            action="store_true",
            help="Ejecuta migrate o migrate --fake según corresponda (sin --fix solo informa).",
        )

    def handle(self, *args, **options):
        do_fix = options["fix"]
        alias = "default"
        conn = connections[alias]

        engine = conn.settings_dict.get("ENGINE", "")
        self.stdout.write(self.style.NOTICE(f"Base de datos: {alias} ({engine})"))

        table_ok = self._table_exists(conn)
        mig_ok = self._migration_applied(conn)

        self.stdout.write(f"  Tabla {TABLE_NAME}: {'existe' if table_ok else 'no existe'}")
        self.stdout.write(
            f"  Migración {MIGRATION_APP}.{MIGRATION_NAME}: "
            f"{'aplicada' if mig_ok else 'no aplicada'}"
        )

        if table_ok and mig_ok:
            self.stdout.write(self.style.SUCCESS("Estado coherente: no se requiere reparación."))
            return

        if not table_ok and mig_ok:
            self.stdout.write(
                self.style.ERROR(
                    "Estado inconsistente: migración aplicada pero tabla ausente. "
                    "Revise backups y django_migrations; no se aplica reparación automática."
                )
            )
            return

        if not do_fix:
            self.stdout.write(
                self.style.WARNING(
                    "Ejecute con --fix para aplicar migrate (tabla ausente) o "
                    "migrate --fake (tabla ya presente y migración pendiente)."
                )
            )
            return

        if not table_ok and not mig_ok:
            self.stdout.write(self.style.WARNING("Aplicando migración reports → creación de tabla…"))
            try:
                call_command(
                    "migrate",
                    MIGRATION_APP,
                    MIGRATION_NAME,
                    database=alias,
                    interactive=False,
                    verbosity=1,
                )
                self.stdout.write(self.style.SUCCESS("migrate completado."))
            except ProgrammingError as exc:
                err = str(exc).lower()
                if "already exists" not in err and "duplicate" not in err:
                    raise
                self.stdout.write(
                    self.style.WARNING(
                        "La tabla apareció durante migrate (p. ej. ya existía). "
                        "Intentando alinear solo el registro en django_migrations…"
                    )
                )
                conn.close_if_unusable_or_obsolete()
                if self._table_exists(conn) and self._columns_match(conn):
                    call_command(
                        "migrate",
                        MIGRATION_APP,
                        MIGRATION_NAME,
                        fake=True,
                        database=alias,
                        interactive=False,
                        verbosity=1,
                    )
                    self.stdout.write(self.style.SUCCESS("Migración marcada como aplicada (--fake)."))
                else:
                    raise
            return

        if not self._columns_match(conn):
            self.stdout.write(
                self.style.ERROR(
                    f"La tabla {TABLE_NAME} existe pero no tiene las columnas esperadas "
                    f"({sorted(EXPECTED_COLUMNS)}). No se usa --fake; revise el esquema a mano."
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                "Tabla presente y migración pendiente: registrando migración con --fake "
                "(sin ejecutar SQL duplicado)."
            )
        )
        call_command(
            "migrate",
            MIGRATION_APP,
            MIGRATION_NAME,
            fake=True,
            database=alias,
            interactive=False,
            verbosity=1,
        )
        self.stdout.write(self.style.SUCCESS("Migración marcada como aplicada (--fake)."))

    def _table_exists(self, conn) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = %s
                );
                """,
                [TABLE_NAME],
            )
            return bool(cursor.fetchone()[0])

    def _migration_applied(self, conn) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM django_migrations
                    WHERE app = %s AND name = %s
                );
                """,
                [MIGRATION_APP, MIGRATION_NAME],
            )
            return bool(cursor.fetchone()[0])

    def _columns_match(self, conn) -> bool:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = %s;
                """,
                [TABLE_NAME],
            )
            cols = {row[0] for row in cursor.fetchall()}
        return EXPECTED_COLUMNS.issubset(cols)
