# Apps core y permisos compatibles con AdministraNET

Las apps **stock**, **compras**, **mpr** y **self_checkout** son **módulos core**: siempre instaladas, no se activan/desactivan desde Module Management. Sus URLs están en `django_project/urls.py` y el menú las considera siempre activas (junto con reports) en `core/utils/utils.py` → `core_modules`.

## Permisos: única fuente AdministraNET

- **Tablas:** `permiso_sistema` y `permiso_sistema_puesto` (MySQL por base empresa).
- **Sincronización:** Tras el login se ejecuta `sync_permisos_synap` (si `SYNAP_AUTO_SYNC_PERMISSIONS` está activo), que crea en `permiso_sistema` los `key_permiso` definidos en **`core/constantes_permisos.py`** → **`PERMISOS_POR_MODULO`**.
- **Comodines:** Para "acceso total" al módulo se sincronizan además `reports.*`, `stock.*`, `self_checkout.*` (véase `MODULOS_CON_COMODIN` en `core/services/sync_permisos_synap.py`).

## Permisos por app (PERMISOS_POR_MODULO)

| Módulo | key_permiso principales | Uso en menú / vistas |
|--------|-------------------------|----------------------|
| **Stock** | stock.ver, stock.crear_movimiento, stock.consultas, stock.ref_movstock, stock.informes | permiso app: stock.ver; vistas con @tiene_permiso |
| **Compras** | compras.ver, compras.crear, compras.editar, … | permiso app: compras.ver |
| **Producción (MPR)** | mpr.ver | permiso app: mpr.ver |
| **Self-Checkout / TPV** | self_checkout.ver, self_checkout.kiosk, self_checkout.supervisor, self_checkout.admin | permiso app: self_checkout.ver; vistas con has_self_checkout_admin / has_any_self_checkout_permission |
| **Reportes** | reports.ver, reports.view_operational, reports.dashboard, … | permiso app: reports.ver |

Para que un puesto tenga acceso a una app en Synap, debe tener el valor "Si" en `permiso_sistema_puesto` para el `key_permiso` correspondiente (o el comodín del módulo, o "*" si es supervisor). La verificación se hace con `core.services.administranet_permisos_usuario.get_permisos_totales_administranet` y en el menú con `app["permiso"] in permisos_usuario`.

## Self-Checkout como core

- **URLs:** Incluidas en `urls.py` como `path('self_checkout/', include('self_checkout.urls', namespace='self_checkout'))`.
- **Module Management:** Self-checkout **no** aparece en Module Management (se eliminó de `MODULE_CONFIGS` en `core/module_registry.py`).
- **Jerarquía de permisos:** ver &lt; kiosk &lt; supervisor &lt; admin (definida en `self_checkout/permissions.py` → `SCO_HIERARCHY`).
