# Contenedor Docker — administraNET-ecom (PHP)

Entorno local para ejecutar el repositorio **administraNET-ecom** (PHP procedural + mysqli) sin instalar PHP/Apache en el host. Pensado para:

- Desarrollo y comparación con la migración Django en la app **`ecom`** de Synap.
- **Actualizaciones frecuentes** del repo PHP vía `git pull` en la carpeta del clon: el código se monta como volumen; no hace falta reconstruir la imagen salvo que cambien extensiones PHP o el Dockerfile.

## Requisitos

1. **Red Docker `synap_net`** (misma que Synap y `docker-compose.mysql.yml`).
2. **MySQL** en esa red (`Synap_mysql57`, puerto interno **3306**).
3. **Clon de administraNET-ecom** (carpeta hermana recomendada: `../administraNET-ecom` respecto a la raíz de Synap).

## Configuración aplicada en Synap

| Artefacto | Uso |
|-----------|-----|
| `administranet-ecom.docker.env` | `ECOM_PHP_SRC`, `SYNAP_ECOM_DOCKER`, credenciales MySQL locales y `TZ`. Commiteable; solo desarrollo local. |
| `docker/ecom-php/includes.docker-synap.inc.php` | Se monta en el contenedor como `mayoristapp/includes/includes.docker-synap.inc.php` y define `servidor_db`, `usuario_db`, etc. desde variables de entorno. |
| Repo **administraNET-ecom** | En `mayoristapp/includes/includes.inc.php`: hook que, si `SYNAP_ECOM_DOCKER=1`, carga el archivo anterior y termina. En `mayoristapp/conexion.inc.php`: segunda conexión usa `usuario_db` y `password_db` en lugar de contraseña fija. |

**Importante:** esos dos cambios en el repo PHP deben conservarse en tu rama (o cherry-pick) cuando hagas `git pull` del remoto; si chocan, reaplica el hook y la línea de `mysqli_connect` con constantes.

## Base `empresas` en MySQL local

`conexion-general.inc.php` hace `mysqli_select_db(..., "empresas")`. La plantilla `docker-compose.mysql.yml` crea la base `administranet` y el usuario `administranet` con permisos sobre esa base. Para el e-com hace falta también la base **`empresas`** (y el resto del esquema según tu dump). Ejemplo **solo desarrollo**:

```sql
CREATE DATABASE IF NOT EXISTS empresas CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
GRANT ALL PRIVILEGES ON empresas.* TO 'administranet'@'%';
FLUSH PRIVILEGES;
```

Ajusta según tu backup real (tabla `empresas` con filas que apunten a `base_empresa`).

## Puesta en marcha

Desde la **raíz del repo Synap**:

```bash
./scripts/administranet-ecom-docker-up.sh
```

Equivalente:

```bash
docker compose -f docker-compose.administranet-ecom.yml --env-file administranet-ecom.docker.env up -d --build
```

Bajar el servicio:

```bash
./scripts/administranet-ecom-docker-down.sh
```

- **URL:** [http://localhost:8050/](http://localhost:8050/) — redirige a `/mayoristapp/`.
- Otras entradas del repo siguen bajo rutas como `/index.php` respecto al `DocumentRoot` (raíz del clon).

### Otra ruta del clon PHP

Edita `ECOM_PHP_SRC` en `administranet-ecom.docker.env` (ruta absoluta o relativa al directorio desde el que ejecutas `docker compose`).

### Primera vez: Composer en subcarpetas

```bash
RUN_COMPOSER_INSTALL=1 docker compose -f docker-compose.administranet-ecom.yml --env-file administranet-ecom.docker.env up -d
```

(Puedes poner `RUN_COMPOSER_INSTALL=1` temporalmente en `administranet-ecom.docker.env`.)

## Variables de entorno (contenedor)

| Variable | Significado |
|----------|-------------|
| `SYNAP_ECOM_DOCKER` | Debe ser `1` para activar el hook en `includes.inc.php`. |
| `SYNAP_MYSQL_HOST` | Típico: `Synap_mysql57`. |
| `SYNAP_MYSQL_PORT` | Típico: `3306`. |
| `SYNAP_MYSQL_USER` / `SYNAP_MYSQL_PASSWORD` | Deben coincidir con MySQL local (`docker-compose.mysql.yml`). |

## Actualizaciones del repo PHP

1. `git pull` en `administraNET-ecom`.
2. Refrescar el navegador; no hace falta reiniciar el contenedor salvo que cambien dependencias del sistema.
3. Si añadieron dependencias Composer en subcarpetas, usar `RUN_COMPOSER_INSTALL=1` una vez.

## Reconstruir la imagen

Solo cuando cambie `docker/ecom-php/` (Dockerfile, Apache, `conf.d`, etc.).

## Stack del contenedor

- **PHP 5.6** (`php:5.6-apache`, Debian Stretch en archivo), extensiones: mysqli, pdo_mysql, gd, zip, mbstring, intl, opcache.
- **Apache 2.4.25** (paquetes `apache2` de Stretch). La imagen oficial de Docker para PHP 5.6 **no** incluye Apache 2.2; ese stack (2.2 + PHP 5.6) solo sería razonable con una imagen EOL custom (p. ej. Debian Wheezy) y no está soportada aquí.
- En **Apple Silicon** el servicio lleva `platform: linux/amd64` en `docker-compose.administranet-ecom.yml`.
- **Composer 1.10** (Composer 2 exige PHP ≥ 7.2).
- Apache: `mod_rewrite`, `mod_headers`, `mod_access_compat`, `AllowOverride All`.

### Sintaxis tipo Apache 2.2 (`Order` / `Allow`) sobre Apache 2.4

El virtual host por defecto usa `Order allow,deny` y `Allow from all` dentro de `<Directory>`. En Apache 2.4 esas directivas las interpreta **`mod_access_compat`** (equivalente práctico a 2.2 para acceso por IP/host). Sin ese módulo, Apache 2.4 espera `Require all granted`.

Ejemplo mínimo en un **`.htaccess`** del proyecto (solo si `AllowOverride` lo permite y el módulo está cargado):

```apache
# Paridad con reglas antiguas 2.2
Order deny,allow
Deny from all
Allow from 127.0.0.1
```

Para “abrir a todos” (como el `000-default` del contenedor):

```apache
Order allow,deny
Allow from all
```

Si preferís la forma nativa 2.4 en un archivo nuevo, podés usar en su lugar `Require all granted` y no depender de `access_compat` para ese bloque.

## Instalar paquetes dentro del contenedor (p. ej. `nano`)

Stretch en archivo tiene firmas GPG caducadas; hace falta permitir repositorios “inseguros” para `apt update`. La imagen nueva incluye `/etc/apt/apt.conf.d/99synap-ecom-archive` con `Acquire::AllowInsecureRepositories` (tras `--build`). En un contenedor ya levantado **sin** reconstruir:

```bash
docker exec -u root Synap_administranet_ecom_php bash -c \
  'apt-get -o Acquire::AllowInsecureRepositories=true \
           -o Acquire::AllowDowngradeToInsecureRepositories=true \
           -o APT::Get::AllowUnauthenticated=true \
           update && apt-get install -y nano'
```

O añade esas mismas líneas `Acquire::AllowInsecureRepositories` y `Acquire::AllowDowngradeToInsecureRepositories` al `99synap-ecom-archive` del contenedor y luego `apt-get update && apt-get install -y nano`.

**Nota:** lo instalado con `apt` en un contenedor en ejecución se pierde al recrear el contenedor; para algo permanente, añádelo al `Dockerfile` y reconstruye.

## Ver también

- [README_MIGRATION.md](./README_MIGRATION.md)
- [MAYORISTAPP_MIGRATION.md](./MAYORISTAPP_MIGRATION.md)
- `docker-compose.mysql.yml`
