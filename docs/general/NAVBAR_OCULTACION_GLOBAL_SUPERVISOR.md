# Ocultación global del menú navbar (usuario supervisor)

## Objetivo

Permitir al usuario **administraNET** con `cod_usuario` igual a **`supervisor`** (minúsculas, criterio ya usado en Synap):

1. **Ocultar o mostrar todos** los ítems del menú horizontal para **todos los usuarios** (sin respetar permisos del menú en ese modo).
2. Con el menú global **visible**, **ocultar o mostrar por módulo** (Stock, MPR, etc.) o por **ítem hoja** del submenú, también para todos los usuarios.

Sirve para fases de desarrollo, capacitación o demos.

## Comportamiento

### Prioridad: global antes que granular

1. Si **`ocultar_todos_items`** está activo, el comportamiento es el histórico: resto de usuarios sin navbar; el `supervisor` solo ve **Archivo**. La configuración granular **no altera** ese resultado hasta que se vuelva a mostrar el menú global.
2. Si el menú global está **desactivado**, se aplica la **visibilidad granular**:
   - **`modulos_ocultos`:** lista de `app_id` de [`APPS_MENU`](../../core/utils/utils.py) cuyo módulo **no** aparece en la barra (ni sus subítems).
   - **`items_menu_ocultos`:** diccionario `app_id → [menu_item_id, …]` con enlaces de hoja ocultos; el módulo puede seguir visible con un subconjunto de ítems.
3. **Módulo Archivo (`app_id == archivo`):** siempre permanece **visible** en el menú y **no** se configura en la UI granular (el supervisor no puede quedar sin acceso a Permiso en sistema). Los ítems bajo Archivo tampoco se gestionan por granular.

### Comportamiento del modo “ocultar todos” (global)

- **Menú visible (predeterminado):** el navbar se arma con la lógica habitual en [`core/utils/utils.py`](../../core/utils/utils.py) (`apps_visibles_para_usuario`): permisos, módulos activos, reglas de Archivo / Settings / etc., y luego el filtro granular.
- **Menú oculto:** para cualquier usuario que **no** sea el `supervisor` (por `cod_usuario`), `apps_visibles_para_usuario` devuelve lista **vacía**: no se muestran módulos en la barra superior.
- **Excepción supervisor:** cuando el menú está oculto globalmente, el usuario `supervisor` sigue viendo **solo** el módulo **Archivo** en el navbar, para poder entrar a **Archivo → Permiso en sistema** y reactivar la visibilidad.

No se bloquean URLs por middleware: un usuario con enlace directo a una vista puede seguir accediendo si su sesión y permisos de vista lo permiten; solo se oculta el **menú de navegación superior**.

## UI

- Ruta: **Archivo** (navbar) → **Permiso en sistema** → URL `core:permisos_sistema` (permisos MySQL por puesto).
- En esa pantalla hay dos **pestañas**:
  1. **Permisos por puesto** (comportamiento anterior).
  2. **Menú navbar Synap** (solo visible si el usuario es `supervisor`): botones para **Mostrar** u **Ocultar** el menú para todos; debajo, acordeones por módulo (mismo criterio visual que `/core/permisos/`) con interruptores estilo modo oscuro del navbar para **módulo visible** y **ítem visible**.

## Datos

- Modelo Django [`NavbarMenuGlobal`](../../core/models/navbar_menu_global.py): registro singleton (`pk=1`):
  - `ocultar_todos_items` (boolean): ocultación global.
  - `modulos_ocultos` (JSON, lista de `app_id`).
  - `items_menu_ocultos` (JSON, objeto `app_id` → lista de `menu_item_id`).
- Cada **hoja** del menú en `APPS_MENU` debe llevar **`menu_item_id`** único (convención tipo `stock_mov_ingreso`). Test: `core.tests.test_navbar.MenuItemIdsNavbarTest`.
- Tras desplegar: `python manage.py migrate` (o en contenedor: `docker exec Synap_app python manage.py migrate core`).

## Código relevante

| Pieza | Ubicación |
|-------|-----------|
| Modelo | `core/models/navbar_menu_global.py` |
| Servicio granular | `core/services/navbar_visibilidad.py` — carga/validación y `iter_menu_hojas_apps_menu` en `core/utils/utils.py` |
| Lógica menú | `core/utils/utils.py` — `obtener_submenus_por_app`, `apps_visibles_para_usuario`; al final `_navbar_menu_oculto_global()` |
| Pestañas y listado | `core/templates/core/permisos_sistema_list.html` |
| Vista listado | `core/views/views_permisos_sistema.py` — `listar_puestos_permisos_view` (`?tab=puestos` \| `?tab=navbar`) |
| POST toggle global | `toggle_navbar_menu_global_view` + URL `core:toggle_navbar_menu_global` |
| POST JSON granular | `toggle_navbar_granular_view` + URL `core:toggle_navbar_granular` |
| Restricción supervisor | `core/decorators.py` — `solo_usuario_supervisor` |

## Retomar menú completo

1. Iniciar sesión como usuario **supervisor**.
2. Archivo → **Permiso en sistema** → pestaña **Menú navbar Synap**.
3. Pulsar **Mostrar menú navbar (todos)**.

## Notas

- **Histórico:** existió un flag de entorno `NAVBAR_FASE_DESARROLLO` que ocultaba Compras, Settings, Module Management y dejaba en Stock solo «Ingreso Mov. Stock». Se **eliminó** del código; para demos o fases de desarrollo usar la **ocultación global** de esta pantalla (supervisor).
- No confundir con el **rol** o puesto "Supervisor" en administraNET: aquí solo cuenta `cod_usuario == 'supervisor'`.
- El decorador `solo_usuario_supervisor` **no** concede acceso a `is_superuser` de Django salvo que sea el mismo criterio de negocio que definan en despliegue.
