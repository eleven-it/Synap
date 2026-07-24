"""
Repara historial inconsistente: ia.0001 aplicada sin core.0011_moduleconfig_logistica.

Django aborta migrate con InconsistentMigrationHistory hasta que la dependencia
conste en django_migrations. core.0011 solo registra ModuleConfig 'logistica'
(RunPython); es seguro aplicar el efecto y marcar la migración como aplicada.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.migrations.exceptions import InconsistentMigrationHistory
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

from core.module_registry import MODULE_CONFIGS


# #region agent log
_DEBUG_LOG_CANDIDATES = (
    Path("/app/.cursor/debug-faad26.log"),
    Path("/Users/sebastian/Documents/Administranet/Proyectos/Synap-v1/Synap/.cursor/debug-faad26.log"),
)


def _agent_log(hypothesis_id: str, location: str, message: str, data: dict, run_id: str = "post-fix"):
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


CORE_0011 = "0011_moduleconfig_logistica"
IA_0001 = "0001_initial"


class Command(BaseCommand):
    help = (
        "Repara ia.0001 aplicada sin core.0011 (historial inconsistente) "
        "para permitir migrate en bases existentes"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Aplicar reparación sin confirmación interactiva",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo informar qué se haría, sin modificar la BD",
        )

    def _applied(self, app: str, name: str) -> bool:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM django_migrations WHERE app = %s AND name = %s LIMIT 1",
                [app, name],
            )
            return cursor.fetchone() is not None

    def _ensure_moduleconfig_logistica(self) -> bool:
        """Crea/actualiza ModuleConfig logistica. Retorna True si la tabla existe."""
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'core_moduleconfig'
                )
                """
            )
            if not cursor.fetchone()[0]:
                return False

        from core.models import ModuleConfig

        cfg = MODULE_CONFIGS["logistica"]
        ModuleConfig.objects.update_or_create(
            name="logistica",
            defaults={
                "display_name": cfg["display_name"],
                "description": cfg["description"],
                "version": cfg["version"],
                "author": cfg.get("author", ""),
                "is_required": cfg.get("is_required", False),
                "is_core": cfg.get("is_core", False),
                "dependencies": cfg.get("dependencies", []),
                "optional_dependencies": cfg.get("optional_dependencies", []),
                "settings": cfg.get("settings", {}),
                "permissions": cfg.get("permissions", []),
                "hooks": cfg.get("hooks", []),
            },
        )
        return True

    def _insert_core_0011(self) -> None:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO django_migrations (app, name, applied)
                VALUES (%s, %s, %s)
                """,
                ["core", CORE_0011, timezone.now()],
            )

    def handle(self, *args, **options):
        force = options.get("force", False)
        dry_run = options.get("dry_run", False)
        run_id = "dry-run" if dry_run else "post-fix"

        self.stdout.write(self.style.WARNING("🔧 Reparación historial core.0011 / ia.0001"))

        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'django_migrations'
                )
                """
            )
            if not cursor.fetchone()[0]:
                self.stdout.write("Base nueva sin django_migrations: nada que reparar.")
                return

        ia_applied = self._applied("ia", IA_0001)
        core_0011_applied = self._applied("core", CORE_0011)

        # #region agent log
        _agent_log(
            "A",
            "fix_inconsistent_migration_history.py:entrada",
            "Estado antes de reparar",
            {
                "ia_0001_applied": ia_applied,
                "core_0011_applied": core_0011_applied,
                "dry_run": dry_run,
                "force": force,
            },
            run_id=run_id,
        )
        # #endregion

        if not ia_applied:
            self.stdout.write(self.style.SUCCESS("ia.0001 no aplicada: no aplica esta reparación."))
            return

        if core_0011_applied:
            self.stdout.write(self.style.SUCCESS("core.0011 ya está en el historial: nada que reparar."))
            # #region agent log
            _agent_log(
                "A",
                "fix_inconsistent_migration_history.py:skip",
                "core.0011 ya presente",
                {"repaired": False},
                run_id=run_id,
            )
            # #endregion
            return

        self.stdout.write(
            self.style.ERROR(
                f"Inconsistencia detectada: ia.{IA_0001} aplicada sin core.{CORE_0011}"
            )
        )

        if dry_run:
            self.stdout.write("DRY-RUN: se insertaría core.0011 y se aseguraría ModuleConfig logistica.")
            # #region agent log
            _agent_log(
                "A",
                "fix_inconsistent_migration_history.py:dry_run",
                "Reparación omitida (dry-run)",
                {"would_repair": True},
                run_id=run_id,
            )
            # #endregion
            return

        if not force:
            self.stdout.write("Usá --force para aplicar la reparación.")
            return

        with transaction.atomic():
            ensured = self._ensure_moduleconfig_logistica()
            self._insert_core_0011()

        # #region agent log
        _agent_log(
            "A",
            "fix_inconsistent_migration_history.py:reparado",
            "core.0011 insertada en historial",
            {
                "repaired": True,
                "moduleconfig_logistica_ensured": ensured,
                "core_0011_now_applied": self._applied("core", CORE_0011),
            },
            run_id=run_id,
        )
        # #endregion

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Marcada core.{CORE_0011} como aplicada"
                + (" y ModuleConfig logistica asegurado" if ensured else " (sin tabla core_moduleconfig)")
            )
        )

        try:
            MigrationExecutor(connection).loader.check_consistent_history(connection)
            consistent = True
            err = None
            self.stdout.write(self.style.SUCCESS("✅ Historial consistente tras reparación"))
        except InconsistentMigrationHistory as exc:
            consistent = False
            err = str(exc)
            self.stdout.write(self.style.ERROR(f"❌ Aún inconsistente: {err}"))

        # #region agent log
        _agent_log(
            "C",
            "fix_inconsistent_migration_history.py:check",
            "check_consistent_history post-repair",
            {"consistent": consistent, "error": err},
            run_id=run_id,
        )
        # #endregion
