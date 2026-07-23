# Spec — Backup y DR Synap

**Capability:** `backup-dr-synap`
**Change:** `backup-dr-synap`
**Estado:** Propuesto

---

## Purpose

Proveer backup **full** e **incremental** conjunto de PostgreSQL Synap y MySQL AdministraNET (base de producción seleccionada), con almacenamiento local, réplica remota **SFTP**, manifest auditable y UI operativa bajo permiso `administrar.backup`. MUST soportar scheduler externo (cron) y ejecución manual desde Synap sin bloquear requests HTTP.

---

## Requirements

### Requirement: Permiso y auditoría

Solo usuarios con permiso `administrar.backup` MUST poder acceder a `/core/backups/` y disparar jobs. Toda ejecución manual MUST registrar `triggered_by` (usuario Synap). El permiso MUST permanecer clasificado como crítico/auditable según `core/constantes_permisos.py`.

#### Scenario: Acceso denegado sin permiso

- **GIVEN** un usuario autenticado sin `administrar.backup`
- **WHEN** navega a `/core/backups/` o invoca la API de lanzamiento
- **THEN** el sistema responde con acceso denegado (403 o redirección equivalente)
- **AND** no se crea ningún `BackupJob`

#### Scenario: Operador autorizado lanza backup

- **GIVEN** un usuario con permiso `administrar.backup`
- **WHEN** confirma un backup full desde la UI
- **THEN** se crea un `BackupJob` con `triggered_by` igual al usuario
- **AND** la acción queda trazable en el job (usuario, tipo, base MySQL, timestamps)

---

### Requirement: Selector de base MySQL (una empresa por job)

El sistema MUST permitir seleccionar **exactamente una** base MySQL de producción (`base_empresa`) por job. MUST NOT ejecutar backup de todas las empresas del servidor en un solo clic. MAY ofrecer checkbox opcional para incluir dump de la base `empresas`.

#### Scenario: Full con base seleccionada

- **GIVEN** un operador en `/core/backups/` y bases MySQL disponibles en sesión/contexto prod
- **WHEN** selecciona `base_empresa=mi_empresa_prod` y lanza backup full
- **THEN** el job registra `base_mysql=mi_empresa_prod`
- **AND** el artefacto MySQL corresponde solo a esa base (más `empresas` si se marcó la opción)

#### Scenario: Rechazo sin base seleccionada

- **GIVEN** el formulario de nuevo backup sin `base_empresa`
- **WHEN** el operador intenta lanzar el job
- **THEN** el sistema rechaza la operación con mensaje en español indicando que debe seleccionar una base

---

### Requirement: Backup full conjunto Postgres + MySQL

Un backup **full** MUST generar artefactos para PostgreSQL (`POSTGRES_DB` vía `pg_dump -Fc` o estrategia documentada con `pg_basebackup`) y MySQL (`mysqldump --single-transaction --routines --triggers` de la base seleccionada). MUST calcular SHA256 por artefacto y escribir **manifest JSON** con: timestamp, `tipo=full`, engines, `base_mysql`, checksums, tamaños y `job_id`.

#### Scenario: Full exitoso local

- **GIVEN** credenciales válidas a Postgres y MySQL prod
- **WHEN** se ejecuta `backup_run --type full` para una base MySQL válida
- **THEN** los artefactos se escriben bajo `BACKUP_LOCAL_ROOT`
- **AND** existe `manifest.json` con entradas `mysql` y `postgres` y checksums SHA256
- **AND** el `BackupJob` pasa a estado `completed`

#### Scenario: Fallo en un engine durante full

- **GIVEN** Postgres accesible y MySQL inaccesible (o viceversa)
- **WHEN** se ejecuta backup full
- **THEN** el job MUST NOT quedar `completed` silencioso
- **AND** el estado MUST ser `failed` o `partial_failed` con `error_summary` en español por engine

---

### Requirement: Incremental desde día 1 (cadena encadenada)

El sistema MUST soportar backup **incremental** desde el MVP (no diferido). Un incremental MUST referenciar `parent_job_id` (último full completado de la misma `base_mysql` o parent explícito). MUST capturar tras full la posición binlog MySQL (`binlog_file`, `binlog_pos`). Incremental MySQL MUST usar binlogs nuevos / `mysqlbinlog` desde el marcador. Incremental Postgres MUST copiar segmentos WAL nuevos desde `BACKUP_PG_WAL_ARCHIVE_DIR` (o estrategia WAL documentada). El manifest MUST indicar `tipo=incremental` y `parent_job_id`.

#### Scenario: Incremental MySQL tras full con binlog activo

- **GIVEN** un full completado con `log_bin=ON` y marcador binlog guardado
- **WHEN** se ejecuta backup incremental
- **THEN** se generan artefactos binlog incrementales MySQL
- **AND** el manifest incremental referencia `parent_job_id` del full
- **AND** se actualiza el marcador binlog al final del incremental

#### Scenario: Incremental rechazado sin binlog

- **GIVEN** MySQL con `log_bin=OFF`
- **WHEN** el operador intenta lanzar backup incremental (UI o cron)
- **THEN** el sistema rechaza o marca el job `failed` antes de completar
- **AND** muestra mensaje claro en español indicando que debe habilitar binary log

#### Scenario: Incremental Postgres sin WAL archive configurado

- **GIVEN** `BACKUP_PG_WAL_ARCHIVE_DIR` vacío o sin segmentos WAL archivados
- **WHEN** se ejecuta backup incremental
- **THEN** el engine Postgres MUST reportar fallo explícito
- **AND** el job MUST quedar `partial_failed` o `failed` según resultado MySQL

---

### Requirement: Job incremental conjunto (ambos engines o falla parcial explícita)

Un job incremental MUST intentar **ambos** engines (MySQL y Postgres) en la misma ejecución y manifest DR conjunto. Si un engine falla y el otro succeed, el job MUST quedar `partial_failed` con detalle por engine. MUST NOT marcar `completed` si falta cualquiera de los dos engines en el manifest incremental.

#### Scenario: Incremental conjunto exitoso

- **GIVEN** pre-requisitos MySQL binlog y Postgres WAL cumplidos
- **WHEN** se ejecuta incremental
- **THEN** el manifest lista artefactos incrementales de `mysql` y `postgres`
- **AND** el `BackupJob` queda `completed`

#### Scenario: Falla parcial explícita

- **GIVEN** MySQL incremental OK y Postgres WAL falla
- **WHEN** finaliza la ejecución
- **THEN** el job queda `partial_failed`
- **AND** la UI muestra qué engine falló y el motivo en español

---

### Requirement: Almacenamiento local

Los artefactos MUST persistirse en `BACKUP_LOCAL_ROOT` (default `/var/lib/synap/backups`) con subruta por job (`/<yyyy>/<mm>/<job_id>/`). Cada archivo MUST registrarse en `BackupArtifact` con path, `sha256` y `size_bytes`.

#### Scenario: Estructura local tras job

- **GIVEN** un job completado
- **WHEN** el operador consulta detalle en UI
- **THEN** ve lista de artefactos con tamaño y checksum
- **AND** las rutas corresponden al directorio bajo `BACKUP_LOCAL_ROOT`

---

### Requirement: Destino remoto SFTP

Tras éxito local, si `BACKUP_SFTP_ENABLED=true` y settings válidos, el sistema MUST subir el conjunto del job (manifest + artefactos) al path remoto SFTP configurado. Si el upload falla, MUST registrar `remote_upload_status=failed` sin borrar copia local.

#### Scenario: Upload SFTP exitoso

- **GIVEN** SFTP configurado y reachable
- **WHEN** un job local termina `completed`
- **THEN** los archivos se suben al `BACKUP_SFTP_REMOTE_PATH`
- **AND** `remote_upload_status=success`

#### Scenario: SFTP deshabilitado

- **GIVEN** `BACKUP_SFTP_ENABLED=false`
- **WHEN** un job local termina
- **THEN** `remote_upload_status=skipped`
- **AND** el job puede quedar `completed` solo con copia local

---

### Requirement: UI Synap (canon reports/MPR)

La UI MUST vivir en `/core/backups/` siguiendo patrones canon reports/MPR (NO referencia visual ventas objetivos/presupuestos). MUST mostrar listado de jobs (tipo, estado, base MySQL, fechas **dd/MM/yyyy**, tamaño), detalle con log y artefactos, formulario para lanzar full/incremental con selector de base, y confirmación vía **modal Synap** (MUST NOT usar `alert`/`confirm`/`prompt`).

#### Scenario: Listado de jobs

- **GIVEN** un operador con permiso en `/core/backups/`
- **WHEN** carga la página
- **THEN** ve tabla/listado canon con jobs recientes y fechas en formato dd/MM/yyyy

#### Scenario: Lanzamiento async con polling

- **GIVEN** un operador confirma backup full en modal Synap
- **WHEN** el servidor acepta la solicitud
- **THEN** la respuesta HTTP MUST NOT bloquear hasta terminar el dump
- **AND** la UI muestra estado `queued`/`running` actualizado por polling hasta `completed`/`failed`

---

### Requirement: Scheduler vía cron (sin Celery beat)

El sistema MUST exponer `manage.py backup_run` invocable desde cron del host (ej. `docker exec Synap_app python manage.py backup_run --scheduled --type incremental`). Jobs `--scheduled` MUST NOT requerir usuario UI; MUST registrar `scheduled=true` y `triggered_by=null`.

#### Scenario: Incremental programado

- **GIVEN** cron configurado en el host
- **WHEN** ejecuta `backup_run --scheduled --type incremental`
- **THEN** se crea y procesa un `BackupJob` incremental usando la `base_mysql` configurada para scheduled (settings o última base usada documentada)
- **AND** el resultado queda en listado UI

---

### Requirement: Restore MVP (documentado)

El MVP MUST incluir command `backup_restore` y documentación operativa para restauración (MySQL + Postgres) desde manifest local o SFTP. La UI completa de restore MUST NOT ser requisito del MVP.

#### Scenario: Documentación de restore disponible

- **GIVEN** un operador DR con manifest válido
- **WHEN** consulta `docs/general/BACKUP_DR_SYNAP.md`
- **THEN** encuentra pasos para restore asistido vía `backup_restore` o scripts referenciados

---

### Requirement: Fuera de alcance enforceable

El sistema MUST NOT implementar destinos Azure Blob ni S3 nativos en este change. MUST NOT exponer MySQL ni Postgres a internet como parte del feature. MUST NOT ofrecer acción «backup todas las empresas» en MVP.

#### Scenario: Solo SFTP como remoto

- **GIVEN** configuración de backup remoto
- **WHEN** se revisan opciones de destino en código/settings del change
- **THEN** solo existen local y SFTP (no settings S3/Azure para este módulo)
