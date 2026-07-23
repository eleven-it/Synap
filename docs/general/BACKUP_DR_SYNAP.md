# Backup y recuperación ante desastres (DR) — Synap

Documentación operativa del módulo `core/backup/` (change SDD `backup-dr-synap`).

## Alcance

- **Full + incremental** conjunto: PostgreSQL Synap (`pg_dump -Fc`) + MySQL AdministraNET (`mysqldump`).
- **Una base MySQL por job** (`base_empresa`), con checkbox opcional para incluir la base `empresas`.
- Almacenamiento **local** (`BACKUP_LOCAL_ROOT`) y réplica remota **SFTP** (paramiko).
- UI operativa: `/core/backups/` (permiso `administrar.backup`).
- Scheduler: **cron del host** (sin Celery beat).

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `BACKUP_LOCAL_ROOT` | `/var/lib/synap/backups` | Raíz local de artefactos |
| `BACKUP_RETENTION_DAYS` | `30` | Retención para `--prune` |
| `BACKUP_SFTP_ENABLED` | `false` | Habilita upload remoto |
| `BACKUP_SFTP_HOST` | — | Host SFTP |
| `BACKUP_SFTP_PORT` | `22` | Puerto SFTP |
| `BACKUP_SFTP_USER` | — | Usuario SFTP |
| `BACKUP_SFTP_PASSWORD` | — | Password (o usar key) |
| `BACKUP_SFTP_KEY_PATH` | — | Ruta a clave privada RSA |
| `BACKUP_SFTP_REMOTE_PATH` | `/synap/backups` | Directorio remoto base |
| `BACKUP_PG_WAL_ARCHIVE_DIR` | — | Directorio de WAL archivados (Postgres) |
| `BACKUP_SCHEDULED_BASE_MYSQL` | — | Base MySQL para jobs `--scheduled` |

Credenciales SFTP **solo en ENV** (no en UI).

## Requisitos MySQL (incremental)

1. `log_bin=ON` en el servidor MySQL de producción.
2. Tras cada **full**, Synap guarda `mysql_binlog_file` + `mysql_binlog_pos` en `BackupJob`.
3. Incremental ejecuta `mysqlbinlog --read-from-remote-server` desde el marcador.

Si `log_bin=OFF`, el job incremental falla con mensaje en español indicando habilitar binary log.

## Requisitos PostgreSQL (incremental)

1. `archive_mode=on` y `archive_command` operativo en Postgres Synap.
2. Segmentos WAL copiados al directorio configurado en `BACKUP_PG_WAL_ARCHIVE_DIR`.
3. Incremental copia segmentos **nuevos** respecto al job padre (full o incremental previo).

Si el directorio está vacío o no configurado, Postgres reporta fallo explícito (`partial_failed` o `failed`).

## Cron (host)

Ejemplo (contenedor Synap):

```bash
# Incremental diario 02:00
0 2 * * * docker exec Synap_app python manage.py backup_run --scheduled --type incremental

# Full semanal domingo 03:00
0 3 * * 0 docker exec Synap_app python manage.py backup_run --scheduled --type full
```

Configure `BACKUP_SCHEDULED_BASE_MYSQL` con la base de producción activa.

## Comandos CLI

```bash
# Full manual
docker exec Synap_app python manage.py backup_run --type full --base-mysql=mi_empresa_prod

# Incremental (requiere full previo completado)
docker exec Synap_app python manage.py backup_run --type incremental --base-mysql=mi_empresa_prod

# Job creado desde UI
docker exec Synap_app python manage.py backup_run --job-id=<uuid>

# Simulación sin dumps reales
docker exec Synap_app python manage.py backup_run --type full --base-mysql=test --dry-run

# Purgar jobs antiguos (metadatos + intento de borrar dirs)
docker exec Synap_app python manage.py backup_run --prune

# Restore asistido (MVP — muestra pasos, no ejecuta)
docker exec Synap_app python manage.py backup_restore --manifest=/ruta/manifest.json
```

## Estructura local

```
BACKUP_LOCAL_ROOT/
  YYYY/
    MM/
      <job_uuid>/
        manifest.json
        mysql/<base>.sql.gz
        postgres/full.dump
        mysql_binlog/...
        postgres_wal/...
        backup.log
```

## Restore (MVP)

1. Obtener manifest + artefactos desde local o SFTP.
2. Verificar SHA256 del manifest contra archivos.
3. **PostgreSQL:** `pg_restore -d $POSTGRES_DB --clean --if-exists postgres/full.dump`
4. **MySQL:** `gunzip -c mysql/<base>.sql.gz | mysql ... <base>`
5. Aplicar binlog/WAL incrementales según procedimiento DBA (PITR).

Use `manage.py backup_restore --manifest=...` para ver comandos sugeridos.

## UI

- Listado: `/core/backups/`
- Detalle + polling: `/core/backups/<uuid>/`
- API JSON: `GET /core/backups/api/jobs/<uuid>/`
- Permiso requerido: `administrar.backup` (crítico/auditable en `core/constantes_permisos.py`).

## Rollback / desactivación

1. Quitar entradas cron.
2. Desactivar `BACKUP_SFTP_ENABLED=false`.
3. Revocar permiso `administrar.backup` a roles operativos.
4. (Opcional) comentar URLs en `core/urls.py` — no recomendado si solo se desactiva cron.

## Tests

```bash
docker exec Synap_app python manage.py test \
  core.tests.test_backup_manifest \
  core.tests.test_backup_incremental \
  core.tests.test_backup_prechecks \
  core.tests.test_backup_sftp \
  core.tests.test_backup_views \
  --keepdb
```

## Escenarios spec ↔ tests

| Escenario spec | Test |
|----------------|------|
| Manifest full SHA256 + engines | `test_backup_manifest.py` |
| Incremental encadenado + ambos engines | `test_backup_incremental.py` |
| log_bin OFF → error español | `test_backup_prechecks.py` |
| WAL dir vacío | `test_backup_prechecks.py` |
| SFTP mock + skipped | `test_backup_sftp.py` |
| Permiso 403 / POST job | `test_backup_views.py` |

## Fuera de alcance

- Destinos S3 / Azure Blob.
- Backup multi-empresa en un clic.
- Wizard completo de restore en UI.
