# Backup y recuperación ante desastres (DR) — Synap

Documentación operativa del módulo `core/backup/` (change SDD `backup-dr-synap`).

## Alcance

- **Full + incremental** conjunto: PostgreSQL Synap (`pg_dump -Fc`) + MySQL AdministraNET (`mysqldump`).
- **Una base MySQL por job** (`base_empresa`), con checkbox opcional para incluir la base `empresas`.
- Almacenamiento **local** y réplica remota **SFTP** (paramiko).
- **Configuración operativa en UI** (`/core/backups/configuracion/`, permiso `administrar.backup`).
- Scheduler: **cron del host** invocando solo `manage.py backup_tick` (sin argumentos ni `BACKUP_*` en ENV).

## Configuración (UI Postgres)

Toda la configuración operativa vive en el singleton **`BackupSettings`** (pk=1), editable en:

**`/core/backups/configuracion/`** (permiso `administrar.backup`)

| Campo | Descripción |
|-------|-------------|
| Programación automática | Activa/desactiva `backup_tick` |
| Base MySQL | Base de producción para jobs programados |
| Incluir empresas | Dump de base `empresas` en full programados |
| Directorio local | Raíz de artefactos (default `/var/lib/synap/backups`) |
| Retención (días) | Para `--prune` |
| Directorio WAL | Segmentos WAL archivados (PostgreSQL incremental) |
| SFTP | Host, puerto, usuario, ruta remota, clave opcional |
| Contraseña SFTP | Cifrada en Postgres (Fernet derivado de `SECRET_KEY`) |
| Programación semanal | JSON `{dow, time, job_type}` — **dow: 0=lunes … 6=domingo** |

**Default programación:** lun–sáb 02:00 incremental, dom 03:00 full.

Las variables `BACKUP_*` en `settings.py` son **fallback inerte** si no hay fila o campos vacíos; no se usan en operación diaria.

## Requisitos MySQL (incremental)

1. `log_bin=ON` en el servidor MySQL de producción.
2. Tras cada **full**, Synap guarda `mysql_binlog_file` + `mysql_binlog_pos` en `BackupJob`.
3. Incremental ejecuta `mysqlbinlog --read-from-remote-server` desde el marcador.

Si `log_bin=OFF`, el job incremental falla con mensaje en español indicando habilitar binary log.

## Requisitos PostgreSQL (incremental)

1. `archive_mode=on` y `archive_command` operativo en Postgres Synap.
2. Segmentos WAL copiados al directorio configurado en la UI (`pg_wal_archive_dir`).
3. Incremental copia segmentos **nuevos** respecto al job padre (full o incremental previo).

Si el directorio está vacío o no configurado, Postgres reporta fallo explícito (`partial_failed` o `failed`).

## Cron (host)

Ejemplo (contenedor Synap, cada minuto):

```bash
* * * * * docker exec Synap_app python manage.py backup_tick
```

Alternativa horaria (coincidencia solo por hora):

```bash
0 * * * * docker exec Synap_app python manage.py backup_tick --match-hour-only
```

Configure base MySQL, programación y SFTP en **`/core/backups/configuracion/`**. No hace falta pasar `--type`, `--base-mysql` ni variables `BACKUP_*` al cron.

## Comandos CLI

```bash
# Tick programado (cron)
docker exec Synap_app python manage.py backup_tick

# Full manual
docker exec Synap_app python manage.py backup_run --type full --base-mysql=mi_empresa_prod

# Incremental (requiere full previo completado)
docker exec Synap_app python manage.py backup_run --type incremental --base-mysql=mi_empresa_prod

# Job programado legacy (usa base de BackupSettings si omite --base-mysql)
docker exec Synap_app python manage.py backup_run --scheduled --type incremental

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
<local_root>/
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
- Configuración: `/core/backups/configuracion/`
- Detalle + polling: `/core/backups/<uuid>/`
- API JSON: `GET /core/backups/api/jobs/<uuid>/`
- Probar SFTP: `POST /core/backups/configuracion/probar-sftp/`
- Permiso requerido: `administrar.backup` (crítico/auditable en `core/constantes_permisos.py`).

## UI para supervisor

Objetivo UX: un **supervisor** (no devops) configura el backup DR sin tocar `.env`
ni `crontab`. Toda la configuración vive en la UI y se persiste en el singleton
`BackupSettings` (`core/backup/models.py`, migración `0016_backupsettings`).

### Fuente de verdad y estilo

Las pantallas siguen `docs/general/FUENTE_VERDAD_UI_REPORTES_MPR.md` (canon
reportes/MPR: hero **slate-800**, Material Icons, Tailwind, sin diálogos nativos).
Acentos en **emerald** para éxito/acciones primarias. Feedback AJAX vía
`SynapMessages.show(...)` (nunca `alert/confirm/prompt`). Fechas en `dd/MM/yyyy`.

### 1. Hub `/core/backups/` (`core/templates/core/backups/list.html`)

- **Hero** con título «Copias de seguridad» y subtítulo orientado a supervisor.
- **Chip de estado** de la programación:
  - Activa → «Programación activa · <resumen>» (ej. `L–S incremental 02:00 · D completo 03:00`)
    con indicador animado y, si aplica, próximo slot (`schedule_hint`).
  - Pausada → «Programación pausada».
  - El resumen lo calcula `_resumen_programacion()` en `core/views/views_backup.py`.
- **Acciones**: «Hacer copia ahora» (modal Synap de confirmación) · «Configuración»
  (enlace a `core:backup_config`).
- **Tarjetas** de destino local, SFTP y base de producción.
- **Historial** (tabla) con badges de estado (icono + color) y origen (Programado / usuario).

### 2. Configuración `/core/backups/configuracion/` (`configuracion.html`)

Página única con secciones (una por área de la job), Alpine para interacción y
**footer sticky** (Guardar / Cancelar). Campos mapeados a `BackupSettings`:

| Sección | Controles | `name` POST |
|---------|-----------|-------------|
| **A. Qué respaldar** | Select base MySQL (context `bases_mysql`); toggle incluir empresas | `base_mysql`, `include_empresas` |
| **B. Calendario semanal** | 7 tarjetas L→D (Lun=0…Dom=6): select Completo/Incremental/No respaldar + hora `HH:MM`; preset «L–S incremental 02:00 · D completo 03:00»; toggle grande «Activar programación automática» | `enabled_auto`; por día `schedule_enabled_{dow}`, `schedule_type_{dow}`, `schedule_time_{dow}` → normalizados a `schedule_json` |
| **C. Destino local** | Ruta en disco; días de retención | `local_root`, `retention_days` |
| **D. Copia remota SFTP** | Toggle habilitar; host/puerto/usuario/ruta remota; password (vacío = no cambiar; casilla «borrar»); ruta clave SSH; botón «Probar conexión» (AJAX) | `sftp_enabled`, `sftp_host`, `sftp_port`, `sftp_user`, `sftp_remote_path`, `sftp_password`, `sftp_clear_password`, `sftp_key_path` |
| **E. Incremental Postgres** | Directorio WAL archivados (ayuda: lo configura el DBA, el supervisor solo indica la carpeta) | `pg_wal_archive_dir` |

Notas de comportamiento:

- El servidor consulta la agenda **cada minuto** vía `manage.py backup_tick`
  (cron del host, sin variables `BACKUP_*`); ver `core/management/commands/backup_tick.py`.
- La **contraseña SFTP** se guarda cifrada (Fernet derivado de `SECRET_KEY`,
  `core/backup/services/secrets.py`). Dejar el campo vacío mantiene la guardada;
  la casilla «Borrar contraseña guardada» (`sftp_clear_password`) la elimina.
- Con SFTP deshabilitado los campos se atenúan pero **conservan** su valor al
  guardar (no se borran).
- «Probar conexión» hace `POST` a `core:backup_test_sftp` (`test_sftp_connection`)
  y muestra el resultado con `SynapMessages` (toast), usando los valores del
  formulario sin necesidad de guardar antes.
- Los ajustes `BackupSettings` **tienen prioridad** sobre las variables de entorno
  legacy (`core/backup/services/config.py`, helpers `effective_*`), que quedan como
  *fallback* para instalaciones que aún no migraron a la UI.

## Rollback / desactivación

1. Quitar entrada cron `backup_tick` o desactivar programación en UI.
2. Desactivar SFTP en configuración UI.
3. Revocar permiso `administrar.backup` a roles operativos.

## Tests

```bash
docker exec Synap_app python manage.py test \
  core.tests.test_backup_manifest \
  core.tests.test_backup_config \
  core.tests.test_backup_tick \
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
| Singleton BackupSettings + schedule | `test_backup_config.py` |
| backup_tick enabled/disabled/duplicado | `test_backup_tick.py` |
| Incremental encadenado + ambos engines | `test_backup_incremental.py` |
| log_bin OFF → error español | `test_backup_prechecks.py` |
| WAL dir vacío | `test_backup_prechecks.py` |
| SFTP mock + skipped | `test_backup_sftp.py` |
| Permiso 403 / POST job | `test_backup_views.py` |

## Fuera de alcance

- Destinos S3 / Azure Blob.
- Backup multi-empresa en un clic.
- Wizard completo de restore en UI.
