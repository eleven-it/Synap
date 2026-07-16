# Restricción móvil: solo Nivel A

**Estado:** vigente  
**Implementación:** `core.middleware.mobile_level_a_middleware.MobileLevelAOnlyMiddleware` (registrado en `django_project/settings.py` después de `DeviceDetectionMiddleware`).

## Objetivo

En dispositivos detectados como móvil (`request.is_mobile`), la aplicación web solo debe exponer las pantallas consideradas **Nivel A** (plantilla móvil dedicada o flujo equivalente documentado). El resto queda reservado para escritorio.

## Comportamiento

- **Sin sesión administraNET:** las rutas no permitidas no se cortan aquí; las vistas siguen redirigiendo a login u otro flujo habitual.
- **Con sesión:** acceder a una ruta no permitida en móvil devuelve **403** (HTML autónomo `core/mobile_desktop_only.html` o JSON si la petición es claramente API/AJAX).
- **`/admin/`:** siempre bloqueado en móvil (403), con o sin sesión.

## Rutas permitidas en móvil

### Infraestructura y PWA

- `/login/` (incluye `logout`, `perfil`, `api/empresas/`)
- `/static/`, `/media/`
- `/offline/`, `/sw.js`, `/manifest.json`, `/set-device-hint/`
- `/mobile/proximamente/`, `/__/auth/handler`
- `/favicon.ico`

### APIs necesarias para el TPV

- Prefijo `/api/self-checkout/`
- Prefijo `/api/mercadopago/` (si el módulo está activo; usado por el kiosco)

### Pantallas HTML `self_checkout`

- `/self_checkout/` (selector)
- `/self_checkout/kiosco/<id>/`
- `/self_checkout/config/`
- `/self_checkout/config/carritos-pendientes/`
- `/self_checkout/talonarios/` (solo lista)
- `/self_checkout/ticket/<id>/` (ventana de impresión post-venta usada por el kiosco; excepción operativa respecto al listado estricto de pantallas con plantilla `mobile/`, para no romper el cierre de venta en móvil)

### Dashboard y reportes (UI responsive)

- `/core/dashboard/` — inicio Synap (hero Command Center + accesos Reports / Workspace).
- `/reports/` y rutas hijas — catálogo, workspace, todos los dashboards (`/reports/dashboard/<slug>/`), builder y data-map.
- `/mpr/` y rutas hijas — Tablero MPR (enlace desde Manufactura en Command Center).
- APIs: prefijo `/api/reports/` (consulta, filtros, exportación, Command Center, etc.).

En pantallas &lt; `lg` (1024px), las tablas de informes muestran **tarjetas** (`reports/static/reports/js/reports_responsive.js`); en escritorio se mantiene la **tabla** existente sin cambios visuales.

### Pedido simple mayorista (acceso móvil habilitado; UI en adaptación)

- `/ecom/mayoristapp/venta/` — pantalla de pedido simple (y alias `/ecom/mayoristapp/compra/`).
- `/ecom/mayoristapp/pedidos/` — hub de pedidos (chips + tarjetas en &lt; `lg`; kanban en escritorio).
- APIs: prefijo `/ecom/api/mayoristapp/` (carrito, catálogo, clientes, checkout, hub, jerarquía comercial, aprobación comercial, etc.).

**Fuera de alcance móvil por ahora** (siguen 403): pedido masivo, configuración VCM, ajustes de ventas, listados de comprobantes, logística y demás pantallas HTML de e-com no listadas arriba.

### Bloqueadas en móvil (ejemplos)

- Formularios de configuración de kiosco, alta/edición de talonarios y PV: `/self_checkout/config/nuevo/`, `.../editar/`, `talonarios/nuevo-pv/`, `talonarios/agregar/`, `talonarios/.../editar/`
- Módulos fuera de Nivel A: compras, e-com (salvo pedido simple / hub / APIs mayoristapp), Tienda Nube, administración Django `/admin/`, etc.

## Manifest PWA

`theme/static/manifest.json` usa `start_url: "/login/"` para que la app instalada abra una entrada válida en móvil.

## Menú y navegación

- **`apps_visibles_para_usuario`** (`core/utils/utils.py`): tras resolver permisos y reglas habituales, se aplica `filtrar_apps_menu_para_pwa_movil` (`core/pwa_nivel_a.py`). En móvil solo permanecen entradas cuyo `id` está en `PWA_MENU_APP_IDS` (**`self_checkout`** y **`ecom`**, cada uno sujeto a permisos de menú de escritorio). TPV requiere `usuario_tiene_tpv_en_menu`; e-com hub+venta requiere `usuario_tiene_ecom_en_menu` y filtra submenús a `ecom_compra` (venta) y `ecom_pedidos` (hub). Deep links: `PWA_ECOM_DEEP_LINKS` en `core/pwa_nivel_a.py` y `deep_link` en `ecom/menu_config.py`.
- **`menu_context`**: si `request.is_mobile`, el sidebar contextual solo se rellena para apps Nivel A (`sidebar_visible_en_pwa`); en e-com se aplica `filtrar_submenus_ecom_para_pwa_movil`. Se añadió `current_app_id = 'self_checkout'` cuando la URL es del namespace `self_checkout`.
- En `partials/navbar.html`, el enlace «Mi perfil» usa `login:perfil` cuando `request.is_mobile` (o en el panel móvil), para coincidir con la plantilla móvil Nivel A. Historial y acceso a `/admin/` no se muestran en móvil desde ese menú (evitan 403 innecesarios).
- El logo en móvil apunta al TPV (`self_checkout:index`) si hay sesión y `tpv_visible_movil`; si no, al dashboard (`core:dashboard`); sin sesión, al login.
- **`MobileLevelAOnlyMiddleware`**: las rutas `/self_checkout/…` y APIs `/api/self-checkout/`, `/api/mercadopago/` devuelven **403** en móvil si el usuario autenticado no tiene TPV en menú.

## Tests

`core/tests/test_mobile_level_a_middleware.py` — ejecutar con:

`docker exec Synap_app python manage.py test core.tests.test_mobile_level_a_middleware`
