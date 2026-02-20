# Limpieza de Módulos - administraNET Analytics

> **Revisar.** En el estado actual, **reports_ai** tampoco está instalado (comentado en INSTALLED_APPS). Los "Mantenidos" son: core, login, dashboard, reports, self_checkout.

## Resumen de Cambios

Se han deshabilitado los siguientes módulos para crear administraNET Analytics:
- `sales`
- `inventory`
- `purchases`
- `mercadopago`
- `tiendanube`
- `tiendanube_administranet`
- `finance`
- `clover`
- `pyafipws` (biblioteca externa, mantener pero no usar directamente)

## Módulos Mantenidos (estado actual)

- `core` - Sistema base
- `login` - Autenticación
- `dashboard` - Panel principal
- `reports` - Sistema de reportes
- `self_checkout` - Self-checkout / TPV

*(reports_ai no está instalado en la instalación mínima actual.)*

**SIA eliminado:** El módulo SIA (Strategic Insights & Alignment) fue removido del proyecto. Si en MySQL de administraNET se ejecutó el sync de permisos SIA, pueden quedar filas en `permiso_sistema` y `permiso_sistema_puesto`. Limpieza opcional: ver [LIMPIEZA_SIA_MYSQL.md](LIMPIEZA_SIA_MYSQL.md).

## Archivos Modificados

### 1. `django_project/settings.py`
- Comentados módulos en `INSTALLED_APPS`
- Comentados context processors de módulos eliminados
- Mantenidas configuraciones de módulos activos

### 2. `django_project/urls.py`
- Removidas rutas de módulos eliminados
- Mantenidas rutas de `reports` y `reports_ai`

### 3. `core/management/commands/load_initial_data.py`
- Comentados imports de módulos eliminados
- Deshabilitadas funciones que dependen de módulos eliminados

### 4. `core/management/commands/initial_setup.py`
- Comentados imports de módulos eliminados
- Deshabilitadas funciones relacionadas

### 5. `core/context_processors.py`
- Comentadas referencias a módulos eliminados en `menu_context`
- Comentadas funciones de contexto de menú de módulos eliminados

### 6. `dashboard/views.py`
- Actualizados `quick_actions` para reflejar módulos disponibles

### 7. `login/templates/login/completar_perfil.html`
- Cambiada redirección de `/sales/` a `/core/dashboard/`

## Comandos de Management Deshabilitados

Los siguientes comandos requieren módulos eliminados y están deshabilitados:
- `load_initial_data` - Funciones de payment methods, categories, taxes, payment terms, price lists
- `initial_setup` - Configuración de payment methods
- `fix_cross_company_stock` - Requiere módulo inventory
- `migrate_products_to_empresa` - Requiere módulos inventory y tiendanube

## Próximos Pasos

1. **Eliminar directorios físicos** (opcional, solo si se desea limpieza completa):
   ```bash
   rm -rf sales inventory purchases mercadopago tiendanube tiendanube_administranet finance clover
   ```

2. **Verificar que el sistema inicie correctamente**:
   ```bash
   docker exec Synap_app python manage.py check
   docker exec Synap_app python manage.py migrate
   ```

3. **Probar funcionalidad básica**:
   - Login
   - Dashboard
   - Reports
   - Reports AI

## Notas Importantes

- Los módulos están **comentados** pero no eliminados físicamente
- Si se necesita restaurar algún módulo, simplemente descomentar en `settings.py` y `urls.py`
- El `module_registry.py` mantiene las configuraciones de todos los módulos (solo metadata)
- Los comandos de management deshabilitados pueden causar errores si se ejecutan directamente

