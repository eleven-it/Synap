# Runbook de restauración Synap (DR de datos + bootstrap)

**Fecha:** 25/07/2026  
**Contexto:** Tras el incidente WSL/Docker (24/07), se descarta el VHDX como estrategia primaria (crece y comparte el mismo radio de fallo). La RD se apoya en **tres capas**.

## Estrategia recomendada (3 capas)

| Capa | Qué es | Dónde vive | Frecuencia |
|------|--------|------------|------------|
| **A. Código / receta de despliegue** | Repo Git + `docker-compose.yml` + `Dockerfile` + docs | GitHub (`Desarrollo`/`Staging`) | Continuo |
| **B. Bootstrap / secretos** | `.env`, certs AFIP, inventario de versiones, mapa de puertos | **SFTP offsite** (cifrado), **no** solo en el host | Con cada full + al cambiar config |
| **C. Datos** | Dump Postgres Synap + dump MySQL `base_empresa` (+ opcional `empresas`) + incremental | Local + **SFTP** vía `/core/backups/` | Calendario UI (ej. L–S inc / D full) |

**No respaldar como primario:** discos WSL (`ext4.vhdx`), `docker_data.vhdx`, imágenes Docker completas. Se **reconstruyen** con capa A + B + `docker compose up --build`.

```
Fallo host/WSL
    │
    ├─► Instalar Windows/WSL/Docker (capa A documentada)
    ├─► git clone + checkout rama
    ├─► Restaurar paquete bootstrap (capa B) → .env + AFIP
    ├─► docker compose up -d --build
    ├─► Restaurar Postgres + MySQL (capa C) desde manifest
    └─► migrate / collectstatic / smoke login
```

---

## Inventario: qué hay que tener instalado (host nuevo)

### 1. Sistema / runtime

| Componente | Notas |
|------------|--------|
| Windows 10/11 o Linux servidor | El incidente reciente fue en stack Windows + WSL2 |
| WSL2 + distro (ej. `SynapUbuntu`) | Solo si el despliegue sigue siendo WSL; en bare-metal Linux no aplica |
| Docker Engine **o** Docker Desktop | Misma major que producción si es posible |
| Docker Compose v2 | `docker compose version` |
| Git | Clonar `eleven-it/Synap` |
| Acceso red a MySQL AdministraNET | Hoy tip. `DB_HOST:DB_PORT` (ej. `192.168.0.2:30804`) — **MySQL no va en el compose de prod** |
| Acceso SFTP al servidor de backups | Para bajar capa B + C |

### 2. Contenedores Synap (`docker-compose.yml`)

| Servicio | Imagen / build | Volumen persistente | Puerto host típico |
|----------|----------------|---------------------|--------------------|
| `app` (`Synap_app`) | build `Dockerfile` | bind `.:/app`, `static_volume`, `synap_afip_secrets` | **8000** |
| `db` (`Synap_db`) | `postgres:13` | `postgres_data` | **5435→5432** |
| `redis` (`Synap_redis`) | `redis:6-alpine` | `redis_data` (AOF) | **6381→6379** |

MySQL AdministraNET: servidor **externo** (no volumen Docker Synap). El restore de datos MySQL apunta a ese host con credenciales del `.env`.

### 3. Clientes de backup/restore en imagen app

Tras rebuild con Dockerfile actual: `default-mysql-client`, `postgresql-client`, `paramiko`.

---

## Inventario: mapa de configuración (capa B — bootstrap)

### Obligatorios para levantar y autenticar

| Artefacto | Uso | Notas |
|-----------|-----|--------|
| **`.env`** | Compose + Django | **Crítico.** Incluye `SECRET_KEY`, Postgres, MySQL, AES, hosts |
| `docker-compose.yml` | Orquestación | En Git (capa A); no hace falta offsite salvo pin de versión |
| Certificados **AFIP** (`SYNAP_AFIP_STORAGE`) | FE / pyafipws | Volumen `synap_afip_secrets` → `/var/lib/synap/afip` |
| Clave **`SECRET_KEY`** | Sesiones, firma, **descifrado password SFTP** en `BackupSettings` | Sin ella no se lee la clave SFTP guardada en Postgres |

### Variables `.env` que el restore necesita (checklist)

Copiar de `.env.example` y completar; backup offsite del `.env` real (cifrado):

| Grupo | Variables |
|-------|-----------|
| App | `ENVIRONMENT`, `DEBUG`, `SECRET_KEY`, `ALLOWED_HOSTS`, `SITE_URL` |
| Postgres | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`, `POSTGRES_PORT` |
| MySQL | `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `ADMINISTRANET_MYSQL_AES_KEY` |
| Redis | `REDIS_URL` |
| Permisos | `SYNAP_PERMISOS_SOURCE` (prod: `synap`) |
| Opcionales según módulos | `GOOGLE_*`, `SUPPORT_SYNAP_JWT_SECRET`, `BEST_AZURE_*`, `EMAIL_*`, `SYNAP_AFIP_STORAGE` |

### En Postgres (no en `.env`, pero sí en dump capa C)

- `BackupSettings` (agenda, SFTP cifrado, base MySQL programada)
- `SystemConfiguration` (correo, WebAuthn, etc.)
- Usuarios/reportes/MPR/ecom ledgers Synap

Por eso el restore de **Postgres** debe ir **antes** de depender de la UI de backups.

### Recomendación de paquete bootstrap offsite

Un tarball cifrado (o directorio SFTP `bootstrap/<fecha>/`) con:

```
bootstrap/
  env.enc                 # .env cifrado (Fernet + frase de UI Copias de seguridad)
  env.sha256              # SHA-256 del .env en claro
  afip/                   # cert + key (sin permisos world-readable)
  inventory.json          # versiones docker, compose, git SHA, puertos, DB_HOST
  RESTORE.md              # puntero a este runbook + SHA del commit
```

Generación automática: cada job **full** (`core/backup/services/bootstrap.py`) escribe
este directorio y lo registra en el manifest (`engine=bootstrap`). La frase se configura
en `/core/backups/configuracion/` (campo cifrado en `BackupSettings`); **debe** guardarse
también fuera de Synap (gestor de secretos / password manager / sobre físico). No subir
la frase al mismo SFTP que `env.enc`.

---

## Inventario: datos (capa C)

Por cada job full (manifest):

| Engine | Artefacto | Restore |
|--------|-----------|---------|
| PostgreSQL | `postgres/full.dump` (`pg_dump -Fc`) | `pg_restore -d $POSTGRES_DB --clean --if-exists` |
| MySQL | `mysql/<base>.sql.gz` | `gunzip -c … \| mysql … <base>` |
| MySQL opcional | dump `empresas` | Idem |
| Incremental | `mysql_binlog/…`, `postgres_wal/…` | Solo si binlog/WAL estaban activos; PITR DBA |

Verificar **SHA256** del manifest antes de aplicar.

Orden sugerido:

1. Postgres Synap (app metadata + `BackupSettings`).
2. MySQL `empresas` (si se respaldó).
3. MySQL `base_empresa` de producción.
4. Incrementales en orden temporal (si aplica).
5. `docker exec Synap_app python manage.py migrate` (idempotente).
6. Smoke: login AdministraNET, `/core/dashboard/`, un informe, hub pedidos.

---

## Qué NO hace falta respaldar (se regenera)

| Ítem | Motivo |
|------|--------|
| `staticfiles/` / `static_volume` | `collectstatic` |
| `node_modules` / `__pycache__` | Rebuild imagen / pip |
| Código fuente | `git clone` |
| Imágenes Docker locales | `docker compose build` / pull |
| Redis (salvo colas críticas) | Cache; AOF es nice-to-have, no bloqueante DR |
| VHDX WSL / Docker Desktop | Reinstalar + capas A–C |

---

## Madurez actual vs objetivo

| Pieza | Hoy | Objetivo próximo |
|-------|-----|------------------|
| Full datos UI + SFTP | Código listo; ops a endurecer | Full prod + SFTP verde |
| Incremental | Requiere binlog/WAL | Activar o documentar “solo full” |
| `backup_restore` | Solo imprime comandos | Ejecutar restore asistido a staging + verify |
| Paquete bootstrap `.env`+AFIP | **Automatizado en full** (`bootstrap/` + SFTP si está activo) | Drill trimestral de descifrado |
| Drill trimestral | No | Checklist firmado |

---

## Procedimiento restore (borrador operativo)

### Fase 0 — Precondiciones

- [ ] Host con Docker + Git
- [ ] Credenciales SFTP + passphrase de `env.enc`
- [ ] IP/acceso al MySQL AdministraNET (o instancia restaurada)
- [ ] Elegir manifest full (+ cadena incremental si aplica)

### Fase 1 — Código

```bash
git clone git@github.com:eleven-it/Synap.git
cd Synap
git checkout <SHA del inventory.json>
```

### Fase 2 — Bootstrap

```bash
# Descargar bootstrap/ y artefactos del job desde SFTP (o copiar del local_root)
# Descifrar env.enc → .env (frase offline; no la tome del mismo servidor que el backup)
docker exec Synap_app python manage.py backup_decrypt_env \
  --input=/ruta/al/job/bootstrap/env.enc --output=./.env
# Opcional: verificar sha256sum -c bootstrap/env.sha256 tras descifrar
# Copiar afip/* → volumen o ruta SYNAP_AFIP_STORAGE / FE_AFIP_CERT_STORAGE_DIR
# Ajuste hosts/puertos en .env si el entorno de restore difiere del origen
```

### Fase 3 — Stack vacío

```bash
docker compose up -d --build
# Esperar healthcheck db/redis/app
```

### Fase 4 — Datos

```bash
docker exec Synap_app python manage.py backup_restore --manifest=/ruta/manifest.json
# Ejecutar los comandos pg_restore / mysql indicados (hoy manual; luego automatizar)
docker exec Synap_app python manage.py migrate
docker exec Synap_app python manage.py collectstatic --noinput
```

### Fase 5 — Verificación

- [ ] Login usuario de prueba
- [ ] Empresa / base correcta
- [ ] `/core/backups/` lista jobs (metadatos Postgres)
- [ ] Pedido o informe de humo

---

## Mejoras de producto a iterar (prioridad)

1. ~~**Bundle bootstrap en cada full**~~ — hecho (`bootstrap/` + frase UI + `backup_decrypt_env`).  
2. **Restore ejecutable** (`backup_restore --execute --target=staging`) con confirmación modal / flag.  
3. **Verify job**: restore automático a DB staging + checksum + smoke HTTP.  
4. UI: estado “último bootstrap offsite” y “última prueba de restore”.

El VHDX queda solo como **salvavidas opcional** esporádico, no como plan RD.
