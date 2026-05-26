# Almacenamiento seguro de certificados AFIP (Synap)

## Importar certificado desde la PC (formulario Facturación AFIP)

En **Editar configuración AFIP**, la opción recomendada es **«Importar desde tu equipo»**: el navegador envía el `.crt`/`.pem` y la `.key` al servidor; Synap los guarda en el almacén (`SYNAP_AFIP_STORAGE` / `FE_AFIP_CERT_STORAGE_DIR`) sin que el usuario indique rutas dentro del contenedor. La sección **«Opción avanzada»** sigue disponible para rutas en servidor (Docker/Linux).

## Módulo en Synap (Module Management)

La app **`fe_afip`** está registrada en **`core/module_registry.py`** (`MODULE_CONFIGS`). Las URLs se montan como **`/fe_afip/...`** solo si el módulo figura **activo** en **Core → Module Management** (tabla `core_moduleconfig`). Tras actualizar el código, ejecutá migraciones: `python manage.py migrate core` (aplica `0012_moduleconfig_fe_afip`, que crea el registro y lo deja activo por defecto). En el menú lateral, bajo **Self-Checkout / TPV**, aparece **Facturación AFIP** para quien tenga el permiso `fe_afip.view_afipconfig`.

## Objetivo

Los certificados y claves privadas ARCA/AFIP deben leerse de forma fiable por **pyafipws** (WSAA). En **Docker Desktop para Mac**, montar el repositorio como `.:/app` puede provocar al leer archivos bajo `/app` el error **`[Errno 35] Resource deadlock avoided`**, que impide obtener el ticket de acceso y emitir CAE/operar el self-checkout.

## Implementación

1. **Volumen dedicado** `synap_afip_secrets` en `docker-compose.yml`, montado en el contenedor en `/var/lib/synap/afip` (no forma parte del bind mount del código).

2. Variable de entorno **`SYNAP_AFIP_STORAGE=/var/lib/synap/afip`** (definida en el servicio `app` del compose). Django expone:
   - `FE_AFIP_CERT_STORAGE_DIR` → `<SYNAP_AFIP_STORAGE>/certs`
   - `FE_AFIP_PENDING_DIR` → `<SYNAP_AFIP_STORAGE>/pending`

3. **Asistente ARCA** (`save_certificate_and_apply`) ya escribe en ese árbol cuando están configurados los settings anteriores.

4. **Formulario manual de rutas** (Facturación AFIP): al guardar, se llama a **`ingest_external_cert_pair`**, que copia el `.crt` y la `.key` al almacén canónico y guarda en base esas rutas internas (permisos `644` / `600` sobre cert y clave).

5. **Migración de configs existentes** (tras subir el compose con el volumen):

   ```bash
   docker compose up -d
   docker exec Synap_app python manage.py fe_afip_migrate_certs_to_secure_storage
   ```

   Opcional: `python manage.py fe_afip_migrate_certs_to_secure_storage --dry-run`

## Desarrollo sin Docker

Si no se define `SYNAP_AFIP_STORAGE`, el valor por defecto es **`private/afip/`** bajo la raíz del proyecto (ignorado en `.gitignore` bajo `private/afip/`). Ese directorio sigue estando bajo el bind mount si el proyecto está montado igual que en Docker; para pruebas reales de FE en Mac conviene usar el compose con volumen dedicado.

## Si `fe_afip_migrate_certs_to_secure_storage` falla al leer el origen

Si las rutas guardadas en `AFIPConfig` apuntan a archivos bajo `/app` (bind mount) y el sistema devuelve **`[Errno 35] Resource deadlock avoided`** al leerlos, la migración automática no puede leer el origen.

### Opción recomendada: importar vía `/tmp` y `docker cp`

Desde el **Mac (host)** los archivos suelen leerse bien; copiálos al contenedor fuera del bind mount y ejecutá el comando con rutas internas.

**Importante:** las dos primeras líneas `docker cp` deben usar **rutas reales en tu Mac** (ej. `/Users/tu_usuario/Descargas/certificado.crt`). **No** copies literalmente texto tipo `/ruta/en/tu/mac/...`: no existe y `docker cp` fallará con `lstat ... no such file`; entonces el `manage.py` dirá que no encuentra `/tmp/afip_import.crt`.

```bash
# Reemplazá CERT_MAC y KEY_MAC por rutas absolutas reales en tu equipo.
CERT_MAC="/Users/TU_USUARIO/ruta/real/certificado.crt"
KEY_MAC="/Users/TU_USUARIO/ruta/real/clave.key"

docker cp "$CERT_MAC" Synap_app:/tmp/afip_import.crt
docker cp "$KEY_MAC" Synap_app:/tmp/afip_import.key
docker exec Synap_app ls -la /tmp/afip_import.crt /tmp/afip_import.key

docker exec Synap_app python manage.py fe_afip_migrate_certs_to_secure_storage \
  --base-empresa administranet89 \
  --certificado /tmp/afip_import.crt \
  --clave /tmp/afip_import.key
docker exec Synap_app rm -f /tmp/afip_import.crt /tmp/afip_import.key
```

(Sustituí `administranet89` si tu `base_empresa` es otro.)

### Otras opciones

1. **Volver a guardar** la configuración en **Facturación AFIP** (mismo cert y clave) con el volumen ya montado: el formulario intentará leer y escribir en `/var/lib/synap/afip/...`. Si la lectura desde el explorador sigue fallando, usá la importación vía `/tmp` arriba.

2. **Copiar a mano** al volumen y actualizar la base (ajustá `administranet89` al `base_empresa` real):

   ```bash
   docker exec Synap_app mkdir -p /var/lib/synap/afip/certs/administranet89
   docker cp ./certificado.crt Synap_app:/var/lib/synap/afip/certs/administranet89/certificado.crt
   docker cp ./clave.key Synap_app:/var/lib/synap/afip/certs/administranet89/clave.key
   docker exec Synap_app chmod 644 /var/lib/synap/afip/certs/administranet89/certificado.crt
   docker exec Synap_app chmod 600 /var/lib/synap/afip/certs/administranet89/clave.key
   ```

   Luego en PostgreSQL (o Django admin / shell) actualizá `fe_afip_afipconfig.cert_path` y `key_path` a:

   - `/var/lib/synap/afip/certs/administranet89/certificado.crt`
   - `/var/lib/synap/afip/certs/administranet89/clave.key`

## Logs confusos: `TypeError: 'OSError' object is not subscriptable`

pyafipws antiguos usan `e[0]` tras `except socket.error`; en Python 3 eso puede romper con `OSError`. Synap aplica en arranque (`core.apps.CoreConfig.ready`) el parche **`core/pyafipws_errno_compat.py`**, que sustituye el decorador por uno compatible con `errno`. El error **real** suele ser **Errno 35** al leer el certificado (véase arriba). Además, antes de llamar a WSAA se valida lectura de cert/clave (`validate_fe_certificates_readable` en `self_checkout/fe_config.py`) para devolver un mensaje en español.

## Referencias

- Código: `fe_afip/services/cert_arca.py` (`ingest_external_cert_pair`), `fe_afip/views.py` (guardado de configuración), `django_project/settings.py`.
- Self-checkout y pyafipws consumen las rutas desde `fe_afip.AFIPConfig` vía `self_checkout/fe_config.py`.
- La app **`fe_afip`** debe estar en `INSTALLED_APPS` para comandos como `fe_afip_migrate_certs_to_secure_storage`.
