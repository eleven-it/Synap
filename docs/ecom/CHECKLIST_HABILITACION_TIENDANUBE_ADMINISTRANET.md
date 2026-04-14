# Checklist de habilitación — `tiendanube_administranet`

Documento para ejecutar **antes** y **después** de activar el módulo en un entorno (desarrollo, staging, producción).

## Previo a los cambios (infraestructura y datos)

1. **PostgreSQL**: las migraciones del módulo viven en la BD `default` (Synap). Confirmar espacio y backup de `default`.
2. **MySQL AdministraNET**: el usuario de `settings.DATABASES['mysql']` debe poder conectarse al **nombre de base** que coincida con `session['user']['base_empresa']` y con `AdministraNETConfig.database` (misma cadena).
3. **Permisos en AdministraNET**: sincronizar roles/puestos con las claves de `core/constantes_permisos.py` bajo el bloque «Tiendanube-AdministraNET» (incl. `tiendanube_administranet.change_administranetconfig`, etc.).
4. **Module Management**: activar el módulo `tiendanube_administranet` en BD (`ModuleConfig`) o vía `setup_modules` / panel de módulos, coherente con `core/module_registry.py`.
5. **Celery (opcional pero recomendado)**: para sincronización en segundo plano hace falta broker (p. ej. Redis) y worker; sin Celery, las señales no encolan tareas (se registran en log).
6. **Credenciales Tienda Nube**: `access_token`, `store_id` y URL de API (por defecto `https://api.tiendanube.com/...`); revisar OAuth/scopes en el partner portal.
7. **Git**: el módulo deja de estar en `.gitignore` y pasa a versionarse con el resto del repo.

## Tras desplegar código

1. `pip install -r requirements.txt` (incluye `celery`).
2. En contenedor: `docker exec Synap_app python manage.py migrate`.
3. Comprobar rutas: interfaz bajo `/tiendanube_administranet/`, API bajo `/api/tiendanube_administranet/`.
4. Login Synap → elegir empresa → verificar que `base_empresa` coincide con la base configurada en `AdministraNETConfig`.
5. Probar «Test connection» Tienda Nube y AdministraNET desde la UI.
6. **Barra superior (navbar)**: además de `ModuleConfig.is_active`, el módulo debe estar declarado en `APPS_MENU` (`core/utils/utils.py`, id `tiendanube_administranet`) para que aparezca el menú desplegable. El usuario con `cod_usuario` = `supervisor` recibe permisos `*` y ve las entradas permitidas; el **puesto** «Supervisor» en AdministraNET no equivale a ese usuario técnico (solo los permisos asignados al rol).

## Webhooks (API 2025-03)

Detalle de rutas, cuerpos JSON y receptor Synap: **`docs/ecom/TIENDANUBE_WEBHOOKS_API_2025-03.md`**.

## FASE 2 — API Nuvemshop / Tienda Nube (referencia actual)

- Documentación oficial versionada: **2025-03** — [Getting Started](https://tiendanube.github.io/api-documentation/intro).
- URLs base: `https://api.tiendanube.com/2025-03/{store_id}` (AR/MX/…) o `https://api.nuvemshop.com.br/2025-03/{store_id}` (BR).
- Autenticación: OAuth 2, cabecera `Authentication: bearer {token}`, **User-Agent** obligatorio (la app ya envía uno de contacto).
- El código usa la constante `NUVEMSHOP_API_VERSION` en `tiendanube_administranet/services/tiendanube_service.py`. Ante nuevas versiones mayores, validar changelog oficial y ajustar la constante y pruebas de humo (productos, variantes, pedidos, clientes).

### Notas de compatibilidad

- La documentación en DevHub puede mostrar ejemplos con `/v1/`; la versión soportada actual de referencia es **2025-03** (no sustituir por `v1` en integraciones nuevas sin revisión).
- Productos: existe despliegue gradual de API de productos con multi-inventario; conviene revisar el aviso en la documentación de *Product* si se amplía el alcance.

## Arquitectura Synap aplicada al módulo

- **MySQL**: `AdministraNETService` usa `core.mysql_pool.get_connection(base_empresa)`, misma política que Reportes/logística (no `mysql.connector` ni credenciales por fila para conectar).
- **Config. AdministraNET en UI**: el modelo persiste el esquema (`database`) y los IDs operativos; en la **pantalla web** el esquema **no se edita**: se rellena al guardar con `base_empresa` de la sesión. Host y credenciales: pool Synap (`DATABASES` / `.env`).
- **Permisos UI**: `PermissionRequiredMixin` + `request.user.has_perm` delegan en `tiene_permiso` (AdministraNET); acceso al módulo por `ModulePermissionMiddleware` y lista en `module_registry`.
- **API REST**: `TiendanubeAdministranetSessionPermission` exige sesión con `base_empresa`.
