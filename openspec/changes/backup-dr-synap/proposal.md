# Propuesta: Backup y recuperación ante desastres (DR) Synap

## Intent

Synap concentra datos críticos en **PostgreSQL** (app, sesiones, permisos) y **MySQL AdministraNET** (operación por empresa). Hoy existe el permiso `administrar.backup` (crítico/auditable) **sin UI ni procedimiento operativo**. Se necesita backup **full + incremental desde el día 1**, almacenamiento local y remoto **SFTP**, y una **UI Synap** para operadores autorizados, sin depender de Celery beat (scheduler vía cron del host).

## Scope

### In Scope (MVP)
- Backup **conjunto** Postgres + MySQL de la **base de producción seleccionada** (`base_empresa`); opcional dump tabla `empresas`
- Tipos **full** e **incremental** en el mismo job/manifest (ambos engines o falla parcial explícita)
- Artefactos locales en `BACKUP_LOCAL_ROOT` (default `/var/lib/synap/backups`) con manifest JSON (timestamp, engines, checksums SHA256, tipo, `parent_job_id`)
- Upload remoto **SFTP** tras éxito local (`BACKUP_SFTP_*`)
- Modelos Postgres: `BackupJob`, `BackupArtifact`; servicios en `core/backup/` o `core/services/backup_*`
- Commands: `backup_run`, `backup_restore` (restore MVP: script + docs)
- UI canon reports/MPR en `/core/backups/`: listado, lanzar full/incremental, selector base MySQL, log/estado (polling; no bloquear HTTP)
- Permiso existente `administrar.backup`; auditoría de acciones
- Cron host: `manage.py backup_run --scheduled`

### Out of Scope
- Azure Blob, S3 u otros destinos nativos (solo SFTP remoto)
- Backup de **todas** las empresas en un clic (futuro: selección múltiple)
- Exponer MySQL/Postgres a internet
- Restore automatizado completo en UI (MVP: documentación + script)
- Incremental diferido a fase 2

## Capabilities

### New Capabilities
- `backup-dr-synap`: jobs full/incremental conjuntos, manifest, destinos local/SFTP, UI operativa, permisos y auditoría

### Modified Capabilities
- Ninguna

## Approach

Orquestador en Django invoca subprocess (`mysqldump`, `pg_dump`/`pg_basebackup`, `mysqlbinlog`, copia WAL) desde contenedor/app con credenciales de settings. Tras full MySQL guardar posición binlog; Postgres usar `BACKUP_PG_WAL_ARCHIVE_DIR` o `pg_basebackup` + cadena WAL. Job incremental **siempre** incluye ambos engines en el mismo manifest. Scheduler externo (cron) llama `backup_run`; la UI dispara el mismo pipeline en background (thread/subprocess) y consulta estado por polling. Fechas dd/MM/yyyy; textos en español.

## Affected Areas

| Area | Impact | Descripción |
|------|--------|-------------|
| `core/backup/` o `core/services/backup_*` | New | Orquestación, dump, incremental, SFTP |
| `core/models.py` o app `core` | New | `BackupJob`, `BackupArtifact` |
| `core/management/commands/` | New | `backup_run`, `backup_restore` |
| `core/views.py`, `core/urls.py`, templates | New | `/core/backups/` UI canon |
| `core/constantes_permisos.py` | Sin cambio | Reutilizar `administrar.backup` |
| `docs/general/` | New | Operación DR, restore, cron, requisitos binlog/WAL |
| Settings / `.env` | New | `BACKUP_*`, `BACKUP_SFTP_*`, `BACKUP_PG_WAL_ARCHIVE_DIR` |

## Risks

| Riesgo | Mitigación |
|--------|------------|
| MySQL sin `log_bin=ON` | Pre-check; error claro en UI antes de incremental |
| Postgres sin archive/WAL | Pre-check; documentar configuración; error explícito |
| Job largo bloquea worker | Subprocess + estado persistido; polling UI |
| Credenciales SFTP en settings | Solo ENV; permiso crítico; auditoría |
| Incremental parcial (solo un engine) | Manifest exige ambos o marca falla parcial explícita |
| Disco local lleno | Verificar espacio pre-run; retención configurable |

## Rollback Plan

Desactivar cron y URLs `/core/backups/`. Jobs ya subidos a SFTP permanecen como copia. Revertir migraciones Django de modelos backup si aplica. Documentar desinstalación de settings `BACKUP_*`.

## Dependencies

- Herramientas en imagen/contenedor: `mysqldump`, `mysqlbinlog`, `pg_dump`, `pg_basebackup` (según estrategia), `sha256sum`
- Cliente SFTP: `paramiko` o `rclone` sftp
- MySQL prod accesible desde app (`DB_HOST`/`DB_PORT`, ej. `192.168.0.2:30804`)
- Postgres Synap (`POSTGRES_*`, host interno `db:5432`, publish `5435`)
- Permiso `administrar.backup` en roles operativos DR

## Success Criteria

- [ ] Operador con permiso ejecuta **full** desde UI; job termina con manifest válido y artefactos en local (+ SFTP si configurado)
- [ ] Tras full, **incremental** diario vía cron produce manifest encadenado (`parent_job_id`) con ambos engines
- [ ] Sin binlog/WAL: UI/comando informa error accionable en español (no falla silenciosa)
- [ ] Listado muestra estado, tipo, base MySQL, tamaños, fechas dd/MM/yyyy y enlace a log
- [ ] Acciones de backup quedan auditadas (usuario, tipo, base, resultado)
