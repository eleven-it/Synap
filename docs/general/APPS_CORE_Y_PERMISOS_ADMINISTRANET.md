# Apps core y permisos compatibles con AdministraNET

Las apps **stock**, **compras** y **self_checkout** son **módulos core**: siempre instaladas y visibles en menú vía `core_modules` en `core/utils/utils.py` (sin fila en `ModuleConfig`). **MPR** está siempre en `INSTALLED_APPS` y en `django_project/urls.py`, pero su visibilidad en menú, URLs (`ModuleMiddleware`) y Command Center depende de **`ModuleConfig`** (`setup_modules --activate mpr`; registro en `core/module_registry.py`, migración `0013_moduleconfig_mpr`).

## Permisos: almacén propio Synap (`synap_*`)

> **Actualización arquitectónica.** Los permisos/roles de Synap viven en tablas propias
> `synap_*` (independientes de VB6). Con cutover (`SYNAP_PERMISOS_SOURCE=synap`) el **menú**
> y el acceso a pantallas Synap se resuelven **solo** desde `synap_*`.
> `permiso_sistema` / `permiso_sistema_puesto` se leen únicamente si hace falta una
> funcionalidad legacy de AdministraNET, o en modos `legacy`/`dual` de migración.
> Detalle: **[PERMISOS_SYNAP_STORE.md](PERMISOS_SYNAP_STORE.md)**.

- **Fachada runtime:** `core/services/administranet_permisos_usuario.py::get_permisos_totales_administranet`
  (firma estable; los consumidores no cambian).
- **Tablas Synap:** `synap_permiso`, `synap_rol`, `synap_rol_permiso`, `synap_puesto_rol`.
- **Tablas legacy:** `permiso_sistema` y `permiso_sistema_puesto` (lectura en `legacy`/`dual`
  o en features AdministraNET que aún las consultan; **no** para armar el menú en modo `synap`).
- **Catálogo:** se siembra desde **`core/constantes_permisos.py` → `PERMISOS_POR_MODULO`** + comodines
  `MODULOS_CON_COMODIN` (centralizados en `core/constantes_permisos.py`).
- **Sync legacy en `permiso_sistema` (`sync_permisos_synap`):** *retirado* (P3). Reemplazado
  por `apply_synap_permisos_tables` (seed) + `backfill_synap_permisos_from_legacy` (migración).

## Permisos por app (PERMISOS_POR_MODULO)

| Módulo | key_permiso principales | Uso en menú / vistas |
|--------|-------------------------|----------------------|
| **Stock** | stock.ver, stock.crear_movimiento, stock.consultas, stock.ref_movstock, stock.informes | permiso app: stock.ver; vistas con @tiene_permiso |
| **Compras** | compras.ver, compras.crear, compras.editar, … | permiso app: compras.ver |
| **Producción (MPR)** | mpr.ver, mpr.reportes, mpr.tablero_ver, … | permiso app: `mpr.ver` **OR** `mpr.tablero_ver` **OR** `mpr.reportes`; visibilidad vía `ModuleConfig`. `mpr.reportes` habilita solo el hub `/mpr/reportes/` |
| **Self-Checkout / TPV** | self_checkout.ver, … | permiso app: self_checkout.ver; siempre activo en menú (`core_modules`) |
| **Reportes** | reports.ver, … | permiso app: reports.ver; visibilidad vía `ModuleConfig` (bootstrap lo activa) |
| **IA** | ia.ver, … | permiso app: ia.ver; visibilidad vía `ModuleConfig` |
| **Logística** | logistica_editar_entregas, … | visibilidad vía `ModuleConfig` |
| **Facturación AFIP** | fe_afip.view_afipconfig, … | visibilidad vía `ModuleConfig`; URLs dinámicas `/fe_afip/` |

Para que un puesto vea una app en el menú Synap, su rol en `synap_*` debe incluir el
`key_permiso` de la app (p. ej. `mpr.ver`) o un comodín aplicable, o `"*"` si es
`cod_usuario=supervisor`. La fachada es `get_permisos_totales_administranet`; el menú
filtra con `app["permiso"] in permisos_usuario`.

**Asignación por puesto (UI):** el usuario `cod_usuario` **supervisor** usa `/core/permisos-puesto/` (menú Archivo → *Asignar permisos por puesto*). Ver [PERMISOS_ASIGNACION_POR_PUESTO_SUPERVISOR.md](PERMISOS_ASIGNACION_POR_PUESTO_SUPERVISOR.md).

## Self-Checkout como core

- **URLs:** Incluidas en `urls.py` como `path('self_checkout/', include('self_checkout.urls', namespace='self_checkout'))`.
- **Module Management:** Self-checkout **no** aparece en Module Management (se eliminó de `MODULE_CONFIGS` en `core/module_registry.py`).
- **Jerarquía de permisos:** ver &lt; kiosk &lt; supervisor &lt; admin (definida en `self_checkout/permissions.py` → `SCO_HIERARCHY`).
