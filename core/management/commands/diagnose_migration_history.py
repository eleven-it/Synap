"""
Diagnóstico de historial inconsistente de migraciones (Postgres).

Caso conocido: ia.0001_initial aplicada sin core.0011_moduleconfig_logistica.
Solo inspecciona y registra evidencia; no modifica la BD.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.exceptions import InconsistentMigrationHistory
from django.db.migrations.executor import MigrationExecutor


# #region agent log
_DEBUG_LOG_CANDIDATES = (
    Path("/app/.cursor/debug-faad26.log"),
    Path("/Users/sebastian/Documents/Administranet/Proyectos/Synap-v1/Synap/.cursor/debug-faad26.log"),
)


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict, run_id: str = "pre-fix"):
    payload = {
        "sessionId": "faad26",
        "runId": run_id,
        "hypothesisId": hypothesis_id,
        "location": location,
        "message": message,
        "data": data,
        "timestamp": int(time.time() * 1000),
    }
    line = json.dumps(payload, ensure_ascii=False) + "\n"
    for path in _DEBUG_LOG_CANDIDATES:
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(line)
            break
        except OSError:
            continue
# #endregion


class Command(BaseCommand):
    help = "Diagnostica inconsistencias en django_migrations (core/ia) sin modificar datos"

    def handle(self, *args, **options):
        self.stdout.write("🔍 Diagnóstico de historial de migraciones (core/ia)...")

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'django_migrations'
                )
                """
            )
            has_migrations_table = bool(cursor.fetchone()[0])

        if not has_migrations_table:
            # #region agent log
            _agent_log(
                "A",
                "diagnose_migration_history.py:sin_tabla",
                "django_migrations ausente",
                {"has_migrations_table": False},
            )
            # #endregion
            self.stdout.write(self.style.WARNING("Base sin django_migrations (instalación nueva)."))
            return

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT app, name FROM django_migrations
                WHERE app IN ('core', 'ia')
                ORDER BY app, id
                """
            )
            applied = [(r[0], r[1]) for r in cursor.fetchall()]
            applied_set = {f"{a}.{n}" for a, n in applied}

            cursor.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name LIKE 'ia_%'
                ORDER BY table_name
                """
            )
            ia_tables = [r[0] for r in cursor.fetchall()]

            moduleconfigs = []
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'core_moduleconfig'
                )
                """
            )
            if cursor.fetchone()[0]:
                cursor.execute(
                    """
                    SELECT name FROM core_moduleconfig
                    WHERE name IN ('logistica', 'ia', 'mpr', 'fe_afip', 'tiendanube', 'administranet')
                    ORDER BY name
                    """
                )
                moduleconfigs = [r[0] for r in cursor.fetchall()]

        core_applied = [n for a, n in applied if a == "core"]
        ia_applied = [n for a, n in applied if a == "ia"]
        missing_core_0011 = "core.0011_moduleconfig_logistica" not in applied_set
        ia_0001_applied = "ia.0001_initial" in applied_set

        # #region agent log
        _agent_log(
            "A",
            "diagnose_migration_history.py:estado",
            "Estado aplicado core/ia",
            {
                "core_applied": core_applied,
                "ia_applied": ia_applied,
                "missing_core_0011": missing_core_0011,
                "ia_0001_applied": ia_0001_applied,
            },
        )
        _agent_log(
            "D",
            "diagnose_migration_history.py:tablas_ia",
            "Tablas ia_* presentes",
            {"ia_tables": ia_tables, "count": len(ia_tables)},
        )
        _agent_log(
            "E",
            "diagnose_migration_history.py:moduleconfig",
            "ModuleConfig relevantes",
            {"moduleconfigs": moduleconfigs, "has_logistica": "logistica" in moduleconfigs},
        )
        # #endregion

        self.stdout.write(f"   core aplicadas ({len(core_applied)}): {', '.join(core_applied) or '-'}")
        self.stdout.write(f"   ia aplicadas ({len(ia_applied)}): {', '.join(ia_applied) or '-'}")
        self.stdout.write(f"   tablas ia_*: {len(ia_tables)}")
        self.stdout.write(f"   moduleconfigs: {', '.join(moduleconfigs) or '-'}")
        self.stdout.write(
            f"   ia.0001 aplicada={ia_0001_applied} | core.0011 ausente={missing_core_0011}"
        )

        inconsistent = False
        inconsistency_msg = ""
        try:
            executor = MigrationExecutor(connection)
            executor.loader.check_consistent_history(connection)
            # #region agent log
            _agent_log(
                "C",
                "diagnose_migration_history.py:check",
                "check_consistent_history OK",
                {"inconsistent": False},
            )
            # #endregion
            self.stdout.write(self.style.SUCCESS("   ✅ Historial consistente según Django"))
        except InconsistentMigrationHistory as exc:
            inconsistent = True
            inconsistency_msg = str(exc)
            # #region agent log
            _agent_log(
                "C",
                "diagnose_migration_history.py:check",
                "check_consistent_history FAIL",
                {"inconsistent": True, "error": inconsistency_msg},
            )
            # #endregion
            self.stdout.write(self.style.ERROR(f"   ❌ Inconsistente: {inconsistency_msg}"))

        # #region agent log
        _agent_log(
            "B",
            "diagnose_migration_history.py:resumen",
            "Resumen hipótesis",
            {
                "hypothesis_A_ia_without_core_0011": bool(ia_0001_applied and missing_core_0011),
                "hypothesis_B_core_stuck_at_0010": (
                    "0010_alter_navbarmenuglobal_items_menu_ocultos_and_more" in core_applied
                    and missing_core_0011
                ),
                "hypothesis_C_inconsistent": inconsistent,
                "hypothesis_D_ia_tables_exist": bool(ia_tables),
                "hypothesis_E_logistica_missing": "logistica" not in moduleconfigs,
                "error": inconsistency_msg or None,
            },
        )
        # #endregion

        if ia_0001_applied and missing_core_0011:
            self.stdout.write(
                self.style.WARNING(
                    "   ⚠️  Hipótesis A confirmable: ia.0001 sin core.0011 en django_migrations"
                )
            )
