# Módulo Synap: acceso y Module Management

## Registro

| Artefacto | Ubicación |
|-----------|-----------|
| App Django | `odoo_migracion` en `INSTALLED_APPS` |
| Module Management | `core/module_registry.py` → `odoo_migracion` (`is_core: False`) |
| URLs | `/odoo-migracion/` (`url_prefix` en `module_registry`) |
| Menú navbar | `APPS_MENU` id `odoo_migracion` |

## Activación

1. Si el módulo no aparece en la lista, sincronizar el registro:
   ```bash
   docker exec Synap_app python manage.py setup_modules --sync
   ```
2. **Module Management** → activar **Migración Odoo**.
3. El ítem aparece en la barra superior solo si el módulo está activo.

## Quién puede acceder

**Solo el usuario AdministraNET con `cod_usuario == 'supervisor'`.**

- No aplica al puesto/rol "Supervisor".
- `APPS_MENU` usa `superuser_only: True` y la misma regla que Module Management.
- Todas las vistas usan `@solo_usuario_supervisor` ([`core/decorators.py`](../core/decorators.py)).

## Permisos Synap

Registrados en `PERMISOS_POR_MODULO` → grupo **Migración Odoo**:

- `odoo_migracion.ver`
- `odoo_migracion.conexiones`
- `odoo_migracion.jobs`

Sincronizar a MySQL: `docker exec Synap_app python manage.py sync_synap_permissions_to_adminet`

## Rutas principales

| Ruta | Nombre |
|------|--------|
| `/odoo-migracion/` | Panel |
| `/odoo-migracion/conexiones/` | Listado conexiones |
| `/odoo-migracion/inventario/` | Inventario F0 |
| `/odoo-migracion/wizard/` | Wizard migración |
| `/odoo-migracion/validacion/` | Cuadre pre/post |
| `/odoo-migracion/mapeos/` | Correlaciones entidad |
