# Apps core y permisos compatibles con AdministraNET

Las apps **stock**, **compras** y **self_checkout** son **módulos core**: siempre instaladas y visibles en menú vía `core_modules` en `core/utils/utils.py` (sin fila en `ModuleConfig`). **MPR** está siempre en `INSTALLED_APPS` y en `django_project/urls.py`, pero su visibilidad en menú, URLs (`ModuleMiddleware`) y Command Center depende de **`ModuleConfig`** (`setup_modules --activate mpr`; registro en `core/module_registry.py`, migración `0013_moduleconfig_mpr`).

## Permisos: única fuente AdministraNET

- **Tablas:** `permiso_sistema` y `permiso_sistema_puesto` (MySQL por base empresa).
- **Sincronización:** Tras el login se ejecuta `sync_permisos_synap` (si `SYNAP_AUTO_SYNC_PERMISSIONS` está activo), que crea en `permiso_sistema` los `key_permiso` definidos en **`core/constantes_permisos.py`** → **`PERMISOS_POR_MODULO`**.
- **Comodines:** Para "acceso total" al módulo se sincronizan además `reports.*`, `stock.*`, `self_checkout.*` (véase `MODULOS_CON_COMODIN` en `core/services/sync_permisos_synap.py`).

## Permisos por app (PERMISOS_POR_MODULO)

| Módulo | key_permiso principales | Uso en menú / vistas |
|--------|-------------------------|----------------------|
| **Stock** | stock.ver, stock.crear_movimiento, stock.consultas, stock.ref_movstock, stock.informes | permiso app: stock.ver; vistas con @tiene_permiso |
| **Compras** | compras.ver, compras.crear, compras.editar, … | permiso app: compras.ver |
| **Producción (MPR)** | mpr.ver | permiso app: mpr.ver; visibilidad vía `ModuleConfig` |
| **Self-Checkout / TPV** | self_checkout.ver, … | permiso app: self_checkout.ver; siempre activo en menú (`core_modules`) |
| **Reportes** | reports.ver, … | permiso app: reports.ver; visibilidad vía `ModuleConfig` (bootstrap lo activa) |
| **IA** | ia.ver, … | permiso app: ia.ver; visibilidad vía `ModuleConfig` |
| **Logística** | logistica_editar_entregas, … | visibilidad vía `ModuleConfig` |
| **Facturación AFIP** | fe_afip.view_afipconfig, … | visibilidad vía `ModuleConfig`; URLs dinámicas `/fe_afip/` |

Para que un puesto tenga acceso a una app en Synap, debe tener el valor "Si" en `permiso_sistema_puesto` para el `key_permiso` correspondiente (o el comodín del módulo, o "*" si es supervisor). La verificación se hace con `core.services.administranet_permisos_usuario.get_permisos_totales_administranet` y en el menú con `app["permiso"] in permisos_usuario`.

## Self-Checkout como core

- **URLs:** Incluidas en `urls.py` como `path('self_checkout/', include('self_checkout.urls', namespace='self_checkout'))`.
- **Module Management:** Self-checkout **no** aparece en Module Management (se eliminó de `MODULE_CONFIGS` en `core/module_registry.py`).
- **Jerarquía de permisos:** ver &lt; kiosk &lt; supervisor &lt; admin (definida en `self_checkout/permissions.py` → `SCO_HIERARCHY`).
