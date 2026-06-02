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
- `/reports/` — catálogo de reportes.
- `/reports/workspace/` — workspace personal.
- `/reports/dashboard/command-center-gerencial/` — Command Center gerencial.
- `/reports/dashboard/resumen-ejecutivo-ventas/` — Resumen ejecutivo de ventas (panel del día).
- `/reports/dashboard/cash_flow_waterfall/`, `cash_flow_by_account/`, `cash_flow_detailed_movements/` — Flujo de caja (enlace desde Tesorería en Command Center).
- `/mpr/` y rutas hijas — Tablero MPR (enlace desde Manufactura en Command Center).
- APIs: `/api/reports/executive-dashboard/`, `/api/reports/executive-summary/`, `/api/reports/pv-canal-ejecutivo/`, `/api/reports/query/`, `/api/reports/filters/`, `/api/reports/export/`.

### Bloqueadas en móvil (ejemplos)

- Formularios de configuración de kiosco, alta/edición de talonarios y PV: `/self_checkout/config/nuevo/`, `.../editar/`, `talonarios/nuevo-pv/`, `talonarios/agregar/`, `talonarios/.../editar/`
- Detalle de informes individuales (`/reports/dashboard/<slug>/` salvo los listados arriba), stock, compras, e-com, Tienda Nube, etc.

## Manifest PWA

`theme/static/manifest.json` usa `start_url: "/login/"` para que la app instalada abra una entrada válida en móvil.

## Menú y navegación

- **`apps_visibles_para_usuario`** (`core/utils/utils.py`): tras resolver permisos y reglas habituales, se aplica `filtrar_apps_menu_para_pwa_movil` (`core/pwa_nivel_a.py`). En móvil solo permanecen entradas cuyo `id` está en `PWA_MENU_APP_IDS` (actualmente solo **`self_checkout`**). Los permisos del usuario siguen limitando ítems dentro del TPV (p. ej. configuración y talonarios solo con `self_checkout.admin`).
- **`menu_context`**: si `request.is_mobile`, el sidebar contextual solo se rellena para apps Nivel A (`sidebar_visible_en_pwa`); se añadió `current_app_id = 'self_checkout'` cuando la URL es del namespace `self_checkout`.
- En `partials/navbar.html`, el enlace «Mi perfil» usa `login:perfil` cuando `request.is_mobile` (o en el panel móvil), para coincidir con la plantilla móvil Nivel A. Historial y acceso a `/admin/` no se muestran en móvil desde ese menú (evitan 403 innecesarios).
- El logo en móvil apunta al TPV (`self_checkout:index`) si hay sesión, o al login si no.

## Tests

`core/tests/test_mobile_level_a_middleware.py` — ejecutar con:

`docker exec Synap_app python manage.py test core.tests.test_mobile_level_a_middleware`
