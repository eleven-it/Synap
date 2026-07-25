"""Restore asistido MVP desde manifest local."""

from __future__ import annotations

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Restore asistido MVP: muestra pasos para restaurar MySQL y PostgreSQL "
        "desde un manifest.json local. No ejecuta restore automático en producción."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            required=True,
            help="Ruta al manifest.json del job (local o descargado de SFTP)",
        )
        parser.add_argument(
            "--mysql-target",
            default="",
            help="Base MySQL destino (default: base_mysql del manifest)",
        )
        parser.add_argument(
            "--postgres-db",
            default="",
            help="Base Postgres destino (default: POSTGRES_DB)",
        )

    def handle(self, *args, **options):
        manifest_path = Path(options["manifest"]).expanduser()
        if not manifest_path.is_file():
            raise CommandError(f"No existe el manifest: {manifest_path}")

        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        base_mysql = (options.get("mysql_target") or data.get("base_mysql") or "").strip()
        pg_db = (options.get("postgres_db") or settings.DATABASES["default"].get("NAME") or "").strip()
        job_dir = manifest_path.parent

        self.stdout.write(self.style.MIGRATE_HEADING("Restore asistido Synap DR (MVP)"))
        self.stdout.write(f"Manifest: {manifest_path}")
        self.stdout.write(f"Tipo: {data.get('tipo')}  Job: {data.get('job_id')}")
        self.stdout.write("")

        mysql_arts = [a for a in data.get("artifacts", []) if a.get("engine") == "mysql"]
        pg_arts = [a for a in data.get("artifacts", []) if a.get("engine") == "postgres"]
        wal_arts = [a for a in data.get("artifacts", []) if a.get("engine") == "postgres_wal"]
        binlog_arts = [a for a in data.get("artifacts", []) if a.get("engine") == "mysql_binlog"]
        boot_arts = [a for a in data.get("artifacts", []) if a.get("engine") == "bootstrap"]

        self.stdout.write(self.style.HTTP_INFO("0. Bootstrap (.env / AFIP)"))
        if boot_arts:
            enc = next((a for a in boot_arts if str(a.get("path") or "").endswith("env.enc")), None)
            if enc:
                self.stdout.write(
                    f"   docker exec Synap_app python manage.py backup_decrypt_env "
                    f"--input={job_dir / enc['path']} --output=./.env"
                )
            for art in boot_arts:
                self.stdout.write(f"   - {job_dir / art['path']}")
        else:
            self.stdout.write("   (sin artefactos bootstrap en este manifest)")

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("1. PostgreSQL (full lógico)"))
        for art in pg_arts:
            dump_path = job_dir / art["path"]
            self.stdout.write(f"   pg_restore -d {pg_db} --clean --if-exists {dump_path}")
        if wal_arts:
            self.stdout.write("   WAL incremental (requiere PITR / archive recovery manual):")
            for art in wal_arts:
                self.stdout.write(f"     - {job_dir / art['path']}")

        self.stdout.write("")
        self.stdout.write(self.style.HTTP_INFO("2. MySQL"))
        for art in mysql_arts:
            dump_path = job_dir / art["path"]
            self.stdout.write(
                f"   gunzip -c {dump_path} | mysql -h HOST -u USER -p {base_mysql}"
            )
        if binlog_arts:
            self.stdout.write("   Aplicar binlog incremental:")
            for art in binlog_arts:
                self.stdout.write(f"     mysql -h HOST -u USER -p {base_mysql} < {job_dir / art['path']}")

        self.stdout.write("")
        self.stdout.write(
            "Documentación completa: docs/general/BACKUP_DR_SYNAP.md"
        )
        self.stdout.write(
            self.style.WARNING(
                "Este comando NO ejecuta restore automático. Revise checksums SHA256 del manifest antes de aplicar."
            )
        )
