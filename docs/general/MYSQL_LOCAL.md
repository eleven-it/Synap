# MySQL 5.7 local (administraNET)

Contenedor persistente para trabajar la conexión a la DB administraNET en local.

## Pool Synap y conexiones Sleep

Synap reutiliza conexiones MySQL vía `core/mysql_pool.py`. Tras cada request/comando la conexión vuelve al pool y aparece como `Sleep` en el servidor **solo un tiempo breve** (`OPTIONS.POOL_IDLE_SECONDS`, default **30 s**); luego se cierra sola. Al salir del proceso (`atexit`) se llama `close_all`.

Antes de un **restore** o mantenimiento exclusivo:

```bash
docker exec Synap_app python manage.py cerrar_pool_mysql
# Si hay varios workers, reiniciar la app o esperar el idle; conexiones ajenas: KILL en MySQL.
docker compose restart Synap_app   # opcional, limpia workers
```

## Levantar el contenedor

```bash
docker compose -f docker-compose.mysql.yml up -d
```

## Traer la base empresas del servidor remoto

Para que el login muestre la misma lista de empresas que en el servidor remoto:

```bash
./scripts/pull-empresas-from-remote.sh
```

El script descarga la base `empresas` de 190.15.214.142 y la restaura en MySQL local. Requiere `mysqldump` en el host (para conectarse al remoto). Puedes ajustar remoto/local con variables de entorno: `REMOTE_DB_HOST`, `REMOTE_DB_PASSWORD`, `DB_PORT`, etc.

## Restaurar el backup (administranet)

1. Coloca el `.zip` del backup en `backups/`, por ejemplo:
   `backup_administranet_Jesels_administranet_lunes_09_feb_2026__11_09.zip`

2. Ejecuta:

```bash
./scripts/restore-mysql-local.sh
# o con ruta explícita:
./scripts/restore-mysql-local.sh backups/backup_administranet_Jesels_administranet_lunes_09_feb_2026__11_09.zip
```

## Conexión en .env (local)

El bloque de MySQL en `.env` debe quedar así para usar el contenedor local:

```
# Base de datos MySQL (administraNET) — LOCAL (contenedor Docker)
DB_NAME=administranet
DB_USER=administranet
DB_PASSWORD=administranet_local
DB_HOST=127.0.0.1
DB_PORT=3307
```

## Volver a la DB remota

Reemplaza el bloque anterior por:

```
# Base de datos MySQL (administraNET) — REMOTO
DB_NAME=administranet
DB_USER=administranet
DB_PASSWORD=a7v8xx0805
DB_HOST=190.15.214.142
DB_PORT=3306
```

## Parar el contenedor

```bash
docker compose -f docker-compose.mysql.yml down
```

Los datos se conservan en el volumen `mysql_administranet_data`. Para borrar todo (contenedor + datos): `docker compose -f docker-compose.mysql.yml down -v`.
