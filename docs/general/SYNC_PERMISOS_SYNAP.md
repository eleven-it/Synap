# Sincronización automática de permisos Synap → AdministraNET

Los permisos que Synap usa para menú y vistas (`usuarios.ver`, `reports.ver`, etc.) deben existir en la tabla `permiso_sistema` de cada base de empresa en MySQL (AdministraNET). Así los puestos pueden tener asignados esos `key_permiso` y el usuario ve las pantallas correctas.

## Cuándo se ejecuta

- **Automático:** Tras un **login exitoso** se llama a `asegurar_permisos_synap_si_procede(base_empresa)`. Solo sincroniza si:
  - La opción está habilitada (`SYNAP_AUTO_SYNC_PERMISSIONS=True`, por defecto).
  - No se ha sincronizado esa empresa recientemente (cache con TTL configurable, por defecto 24 h).

Ese punto (post-login) evita bloquear el arranque del servidor y solo toca la empresa que el usuario está usando. La cache evita repetir el mismo trabajo en cada login.

- **Manual:** Sigue disponible el comando para todas las empresas o una en concreto:

  ```bash
  docker exec Synap_app python manage.py sync_synap_permissions_to_adminet
  docker exec Synap_app python manage.py sync_synap_permissions_to_adminet --base-empresa administranet89
  ```

## Configuración

| Variable | Default | Descripción |
|----------|---------|-------------|
| `SYNAP_AUTO_SYNC_PERMISSIONS` | `True` | Activa o desactiva la sincronización automática tras login. |
| `SYNAP_AUTO_SYNC_PERMISSIONS_TTL` | `86400` (24 h) | TTL en segundos del cache por empresa; mientras no expire no se vuelve a sincronizar esa base. |

Para desactivar la sincronización automática (y usar solo el comando manual):

```env
SYNAP_AUTO_SYNC_PERMISSIONS=False
```

## Implementación

- Servicio: `core/services/sync_permisos_synap.py`  
  - `sincronizar_permisos_synap_para_empresa(base_empresa, grupo_permiso)`  
  - `asegurar_permisos_synap_si_procede(base_empresa)` (usa cache y settings).
- Llamada post-login: `login/views.py` (tras guardar `request.session["user"]`).
- El comando `sync_synap_permissions_to_adminet` reutiliza `sincronizar_permisos_synap_para_empresa`.

Si la sincronización falla (MySQL, cache, etc.), el login **no** falla: el error se registra y se ignora.
