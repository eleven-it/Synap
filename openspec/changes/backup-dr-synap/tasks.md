# Tasks: Backup y DR Synap

> Orden: settings/modelos → servicios dump → incremental → SFTP → commands → UI → cron/docs → tests.
> Runner: `docker exec Synap_app python manage.py test core.tests.test_backup_*`.

## Fase 1: Fundación (settings, modelos, permisos)

- [x] 1.1 Añadir settings `BACKUP_*` y `BACKUP_SFTP_*`, `BACKUP_PG_WAL_ARCHIVE_DIR` en `synap/settings*.py` (defaults documentados)
- [x] 1.2 Crear modelos `BackupJob` y `BackupArtifact` en `core/backup/models.py` + migración Django
- [x] 1.3 Registrar modelos en admin opcional (solo lectura) o omitir si no aplica
- [x] 1.4 Test: migración aplica; campos `job_type`, `status`, `parent_job_id`, `base_mysql` presentes

## Fase 2: Servicios core — full backup

- [x] 2.1 RED: `core/tests/test_backup_manifest.py` — manifest JSON con SHA256, engines mysql+postgres, tipo full
- [x] 2.2 GREEN: `core/backup/services/manifest.py` — escritura/lectura manifest
- [x] 2.3 GREEN: `core/backup/services/mysql_backup.py` — `mysqldump --single-transaction --routines --triggers`; opción `empresas`; captura binlog marker post-full
- [x] 2.4 GREEN: `core/backup/services/postgres_backup.py` — `pg_dump -Fc` de `POSTGRES_DB`; metadata WAL/base según design
- [x] 2.5 GREEN: `core/backup/services/prechecks.py` — espacio disco, conectividad engines
- [x] 2.6 GREEN: `core/backup/services/orchestrator.py` — pipeline full, estados job, paths bajo `BACKUP_LOCAL_ROOT`

## Fase 3: Incremental (día 1)

- [x] 3.1 RED: `core/tests/test_backup_incremental.py` — exige parent full; manifest incremental encadenado; ambos engines en manifest
- [x] 3.2 RED: `core/tests/test_backup_prechecks.py` — `log_bin=OFF` → error español; WAL dir vacío → fallo Postgres explícito
- [x] 3.3 GREEN: incremental MySQL vía `mysqlbinlog` desde marcador en `BackupJob` parent
- [x] 3.4 GREEN: incremental Postgres — copia WAL desde `BACKUP_PG_WAL_ARCHIVE_DIR`
- [x] 3.5 GREEN: estados `partial_failed` vs `completed`/`failed` en orchestrator

## Fase 4: SFTP y retención

- [x] 4.1 RED: `core/tests/test_backup_sftp.py` — mock upload; `remote_upload_status`; local preservado si SFTP falla
- [x] 4.2 GREEN: `core/backup/services/sftp_upload.py` (paramiko o rclone sftp)
- [x] 4.3 GREEN: flag `BACKUP_SFTP_ENABLED=false` → `skipped`; credenciales solo ENV
- [x] 4.4 Opcional: `backup_run --prune` según `BACKUP_RETENTION_DAYS`

## Fase 5: Management commands

- [x] 5.1 GREEN: `core/management/commands/backup_run.py` — args `--type full|incremental`, `--job-id`, `--scheduled`, `--base-mysql`, `--include-empresas`
- [x] 5.2 GREEN: subprocess/background safe para invocación desde UI (no bloquear)
- [x] 5.3 GREEN: `core/management/commands/backup_restore.py` — restore asistido MVP + mensajes español
- [x] 5.4 Test integración: `backup_run --dry-run` crea estructura tmp sin tocar prod (mock subprocess)

## Fase 6: UI Synap (`/core/backups/`)

- [x] 6.1 Esqueleto rutas en `core/urls.py`: listado, detalle, POST lanzar, API polling `jobs/<id>/`
- [x] 6.2 Templates `core/templates/core/backups/` — canon reports/MPR (listado, detalle, modal confirmación Synap)
- [x] 6.3 Vistas con `@tiene_permiso("administrar.backup")`; selector `base_empresa`; fechas dd/MM/yyyy
- [x] 6.4 POST lanza job async + polling estado; MUST NOT usar alert/confirm nativos
- [x] 6.5 Test: 403 sin permiso; operador crea job con `triggered_by`

## Fase 7: Scheduler cron y documentación

- [x] 7.1 Documentar cron host en `docs/general/BACKUP_DR_SYNAP.md` (full semanal + incremental diario ejemplo)
- [x] 7.2 Documentar requisitos MySQL `log_bin` y Postgres `archive_mode`/WAL dir antes de prod incremental
- [x] 7.3 Documentar restore paso a paso desde manifest local/SFTP
- [x] 7.4 Documentar variables ENV y rollback (desactivar URLs + cron)
- [x] 7.5 Verificación manual MVP: full UI → manifest OK → SFTP (si habilitado) → incremental cron simulado

## Fase 8: Cierre y escenarios spec

- [x] 8.1 Mapear escenarios spec a tests (tabla job_id ↔ escenario en comentario o doc)
- [x] 8.2 Ejecutar suite `docker exec Synap_app python manage.py test core.tests.test_backup_*`
- [x] 8.3 Revisar que no se introducen destinos S3/Azure ni backup multi-empresa en UI
