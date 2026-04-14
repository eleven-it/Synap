# MySQL local (Synap_mysql57): importaciones y política de bases

## Principio

Las importaciones de dumps (`.sql` o `.zip` con SQL) **no deben reemplazar** la base `administranet` por defecto sin una decisión explícita. Esa base es la que crea el contenedor al primer arranque y suele usarse como entorno de desarrollo estable.

**Regla operativa:** importar siempre a **una base nueva** (nombre distinto), por ejemplo `administranet_jesels_20260409` o el prefijo automático `administranet_import_YYYYMMDD_HHMMSS`.

Sobrescribir la base `administranet` solo con:

`ALLOW_OVERWRITE_ADMINISTRANET=1` y el script correspondiente (ver scripts).

## Scripts

| Script | Uso |
|--------|-----|
| `scripts/restore-mysql-local.sh` | Backup **.zip** que contiene `.sql`. Segundo argumento opcional: **nombre de base**. Sin nombre, usa `administranet_import_<timestamp>`. |
| `scripts/import-mysql-sql-new-database.sh` | Archivo **.sql** suelto. Segundo argumento opcional: **nombre de base**. Sin nombre, usa `administranet_import_<timestamp>`. |

Ambos **crean** la base si no existe (`CREATE DATABASE`) y **no hacen** `DROP DATABASE` de otras bases. Además hacen `GRANT` al usuario `administranet` sobre esa base. Si creaste la base **a mano** (solo `CREATE DATABASE`), Synap puede fallar con *Access denied … to database 'nombre'* hasta ejecutar:

`GRANT ALL PRIVILEGES ON \`nombre_base\`.* TO 'administranet'@'%'; FLUSH PRIVILEGES;` (como `root` en el contenedor).

## Conexión

- Desde el host: `127.0.0.1:3307`, usuario `administranet` / `administranet_local`.
- Desde contenedores en `synap_net`: host `Synap_mysql57`, puerto `3306`.

Tras importar a un nombre nuevo, para que esa copia sea usable en Synap hace falta que el **nombre de la base MySQL** coincida con un valor de `base_empresa` que el usuario pueda elegir en el login: la lista sale de la base `empresas`, tabla `empresas` (columna `base_empresa`). **`base_empresa` en la sesión no se configura en `.env`:** se fija al iniciar sesión según la empresa seleccionada (ver `login/views.py` y `login/administranet_auth.py`). Si hace falta una fila nueva en `empresas` apuntando a la base importada, cargarla en esa tabla (entorno de desarrollo).

## Referencia

- `docker-compose.mysql.yml` — servicio `mysql_administranet`, contenedor `Synap_mysql57`.
