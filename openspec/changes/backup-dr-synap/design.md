# Design: Backup y recuperación ante desastres (DR) Synap

## Enfoque técnico

Implementar un **orquestador de backup conjunto** Postgres Synap + MySQL AdministraNET (una `base_empresa` por job) como servicio Django en `core/backup/`, persistiendo metadatos en Postgres (`BackupJob`, `BackupArtifact`) y artefactos en filesystem local. Cada ejecución genera un **manifest JSON** con checksums SHA256, tipo `full|incremental`, engines incluidos y `parent_job_id` para la cadena incremental. Tras éxito local, upload opcional a **SFTP**. La UI en `/core/backups/` (canon reports/MPR) delega la ejecución a subprocess/background y expone polling de estado. El scheduler es **cron del host** invocando `manage.py backup_run --scheduled` (sin Celery beat). Restore en MVP: command/script documentado, no wizard completo.

## Decisiones de arquitectura (ADRs)

### ADR-1: Destino remoto SFTP únicamente
**Elección**: upload post-local vía SFTP (`BACKUP_SFTP_HOST/PORT/USER/PASSWORD_or_KEY/PATH`) con `paramiko` o `rclone sftp`.
**Alternativas**: S3, Azure Blob, rsync sobre SSH custom.
**Rationale**: decisión de producto; SFTP cubre el remoto corporativo típico sin abrir APIs cloud ni credenciales IAM.

### ADR-2: MySQL — una base por job (selector `base_empresa`)
**Elección**: full con `mysqldump --single-transaction --routines --triggers` sobre la base seleccionada; checkbox opcional para incluir base `empresas`.
**Alternativas**: dump multi-empresa en un clic; todas las bases del servidor.
**Rationale**: operación DR alineada a la empresa en producción activa; evita dumps masivos no solicitados.

### ADR-3: Incremental desde día 1 (MySQL binlog + Postgres WAL)
**Elección MySQL**: requiere `log_bin=ON`; tras full persistir `binlog_file` + `binlog_pos`; incremental = `mysqlbinlog` desde marcador hasta fin disponible.
**Elección Postgres**: preferir cadena física con `pg_basebackup` en full + WAL en `BACKUP_PG_WAL_ARCHIVE_DIR`; alternativa documentada: full lógico `pg_dump -Fc` + copia incremental de segmentos WAL archivados desde ese directorio (requiere `archive_mode` + `archive_command` o slot/archive dir operativo).
**Alternativas**: diferir incremental a fase 2; solo full lógico sin WAL.
**Rationale**: producto exige RPO bajo desde MVP; sin binlog/WAL el sistema MUST fallar con mensaje claro en UI.

### ADR-4: Job incremental conjunto o falla parcial explícita
**Elección**: un `BackupJob` incremental MUST intentar MySQL y Postgres; el manifest lista éxito/fallo por engine; estado job `completed`, `partial_failed` o `failed`.
**Alternativas**: jobs separados por engine; éxito silencioso de un solo engine.
**Rationale**: DR conjunto coherente; operador ve de inmediato si la cadena está rota.

### ADR-5: No bloquear request HTTP
**Elección**: UI POST crea `BackupJob` en estado `queued`, lanza `manage.py backup_run --job-id=<id>` en subprocess o thread daemon; frontend polling `GET /core/backups/api/jobs/<id>/`.
**Alternativas**: request síncrono hasta terminar dump; Celery worker.
**Rationale**: dumps largos; sin Celery beat/worker dedicado en MVP.

### ADR-6: Configuración en settings (+ destino opcional en DB futuro)
**Elección MVP**: `BACKUP_LOCAL_ROOT`, `BACKUP_RETENTION_DAYS`, `BACKUP_SFTP_*`, `BACKUP_PG_WAL_ARCHIVE_DIR`, flags de habilitación remoto.
**Alternativas**: solo DB para destinos; UI de credenciales.
**Rationale**: alinear con secretos ENV; UI solo dispara jobs, no almacena passwords.

## Modelo de datos (Postgres Synap)

```
BackupJob
  id (UUID PK)
  job_type: full | incremental
  status: queued | running | completed | partial_failed | failed | cancelled
  base_mysql: str (base_empresa seleccionada)
  include_empresas_table: bool
  parent_job_id: FK nullable (cadena incremental)
  triggered_by: user_id nullable (null si cron)
  scheduled: bool
  started_at, finished_at
  log_path, manifest_path
  mysql_binlog_file, mysql_binlog_pos  (post-full / post-incremental)
  error_summary: text (español)
  remote_upload_status: pending | success | failed | skipped

BackupArtifact
  id
  job_id FK
  engine: mysql | postgres | mysql_binlog | postgres_wal | manifest
  relative_path, absolute_path
  sha256, size_bytes
  created_at
```

Manifest JSON (ejemplo de campos): `job_id`, `created_at` ISO, `tipo`, `parent_job_id`, `base_mysql`, `engines[]`, `artifacts[{engine, path, sha256, size}]`, `mysql_binlog_marker`, `postgres_wal_range`.

## Flujo de datos

```
Cron / UI ──► backup_run ──► BackupJob (queued→running)
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
   mysqldump   pg_dump/pg_basebackup   pre-checks (binlog, WAL dir)
        │           │
        └─────┬─────┘
              ▼
      checksums + manifest.json
              ▼
      BACKUP_LOCAL_ROOT/<yyyy>/<mm>/<job_id>/
              ▼
      SFTP upload (si configurado)
              ▼
      BackupJob completed | partial_failed | failed
              ▼
      UI polling / listado
```

### Full
1. Validar permiso (UI) o flag `--scheduled` (cron).
2. Crear directorio job; dump MySQL base seleccionada (+ opcional `empresas`).
3. Dump Postgres `pg_dump -Fc $POSTGRES_DB` **o** `pg_basebackup` a subdir `postgres/base/` si se adopta cadena WAL física.
4. Calcular SHA256; escribir manifest; registrar `BackupArtifact`.
5. Capturar posición binlog MySQL (`SHOW MASTER STATUS` o equivalente) y rango WAL/base backup metadata.
6. Upload SFTP; actualizar job.

### Incremental
1. Resolver `parent_job_id` (último full completado de la misma `base_mysql` o explícito).
2. **MySQL**: verificar `log_bin`; aplicar `mysqlbinlog` desde marcador guardado; actualizar marcador.
3. **Postgres**: copiar nuevos WAL desde `BACKUP_PG_WAL_ARCHIVE_DIR` (o delta desde último LSN documentado).
4. Manifest tipo `incremental` referenciando parent; mismo tratamiento SFTP.

## Archivos a crear / modificar

| Archivo | Acción | Descripción |
|---------|--------|-------------|
| `core/backup/__init__.py` | Crear | Paquete |
| `core/backup/models.py` | Crear | `BackupJob`, `BackupArtifact` |
| `core/backup/services/orchestrator.py` | Crear | Pipeline full/incremental |
| `core/backup/services/mysql_backup.py` | Crear | dump, binlog check, incremental |
| `core/backup/services/postgres_backup.py` | Crear | pg_dump/basebackup, WAL incremental |
| `core/backup/services/manifest.py` | Crear | JSON + checksums |
| `core/backup/services/sftp_upload.py` | Crear | Upload remoto |
| `core/backup/services/prechecks.py` | Crear | binlog, WAL dir, espacio disco |
| `core/management/commands/backup_run.py` | Crear | CLI/cron/UI background |
| `core/management/commands/backup_restore.py` | Crear | Restore asistido MVP |
| `core/views_backup.py` o `core/views/backup.py` | Crear | Listado, lanzar, API estado |
| `core/urls.py` | Modificar | `/core/backups/` |
| `core/templates/core/backups/*.html` | Crear | UI canon reports/MPR |
| `core/tests/test_backup_*.py` | Crear | Unit + integración mocks |
| `docs/general/BACKUP_DR_SYNAP.md` | Crear | Operación, cron, restore, requisitos MySQL/Postgres |
| `synap/settings*.py` | Modificar | Variables `BACKUP_*` |

## Interfaces / contratos

Settings (ENV):

```python
BACKUP_LOCAL_ROOT = env("BACKUP_LOCAL_ROOT", default="/var/lib/synap/backups")
BACKUP_RETENTION_DAYS = env.int("BACKUP_RETENTION_DAYS", default=30)
BACKUP_SFTP_ENABLED = env.bool("BACKUP_SFTP_ENABLED", default=False)
BACKUP_SFTP_HOST = env("BACKUP_SFTP_HOST", default="")
BACKUP_SFTP_PORT = env.int("BACKUP_SFTP_PORT", default=22)
BACKUP_SFTP_USER = env("BACKUP_SFTP_USER", default="")
BACKUP_SFTP_PASSWORD = env("BACKUP_SFTP_PASSWORD", default="")  # o key
BACKUP_SFTP_KEY_PATH = env("BACKUP_SFTP_KEY_PATH", default="")
BACKUP_SFTP_REMOTE_PATH = env("BACKUP_SFTP_REMOTE_PATH", default="/synap/backups")
BACKUP_PG_WAL_ARCHIVE_DIR = env("BACKUP_PG_WAL_ARCHIVE_DIR", default="")
```

Decorador permiso: `@tiene_permiso("administrar.backup")` en todas las vistas/API de backup.

UI: modales Synap para confirmar full/incremental; `SynapMessages` / toast para resultado; fechas `dd/MM/yyyy HH:mm`.

Cron ejemplo (host):

```bash
0 2 * * * docker exec Synap_app python manage.py backup_run --scheduled --type incremental
0 3 * * 0 docker exec Synap_app python manage.py backup_run --scheduled --type full
```

## Estrategia de tests

| Capa | Qué | Cómo (`docker exec Synap_app`) |
|------|-----|--------------------------------|
| Unit | Manifest SHA256; encadenamiento `parent_job_id`; parser binlog marker | TestCase con fixtures temporales |
| Unit | Prechecks: binlog off → error español | mock subprocess MySQL |
| Unit | Job incremental exige ambos engines en manifest | assert engines length |
| Integración | `backup_run --dry-run` genera estructura de dirs | tmp path |
| Integración | Permiso: sin `administrar.backup` → 403 | client login |
| Integración | SFTP mock (paramiko patch) upload tras local OK | mock |
| UI smoke | POST lanza job async; polling cambia estado | LiveServer o view test |

## Migración / rollout

1. Migración Django para tablas `BackupJob`/`BackupArtifact`.
2. Crear `BACKUP_LOCAL_ROOT` en volumen host con permisos contenedor.
3. Documentar habilitación `log_bin` MySQL y archive WAL Postgres **antes** de activar incrementales en prod.
4. Asignar `administrar.backup` a rol DR; habilitar cron en staging primero.
5. Staging: merge sin `docs/`/`openspec/` según flujo de ramas.

## Open Questions

- [ ] ¿Full Postgres MVP = solo `pg_dump -Fc` + WAL archive dir, o obligatorio `pg_basebackup` desde día 1? — **Recomendación design**: full lógico + WAL dir en MVP si ops ya tiene archive; documentar upgrade a `pg_basebackup` para PITR estricto.
- [ ] ¿Retención local borra automáticamente o solo documentada? — MVP: command housekeeping `--prune` opcional.
- [ ] ¿Auditoría en tabla existente de logs admin o solo campos job? — Reutilizar mecanismo de permisos críticos existente en core si hay helper.
