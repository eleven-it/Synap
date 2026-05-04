# Plan — Módulo Logística · pantalla operativa «Entregas»

**Estado:** plan acordado (iteración 2026-04).  
**Pendiente de negocio:** punto 2 (permiso PHP ↔ Synap) — ver § Permisos.

## Objetivo

Separar la **operación de reparto** (registrar entrega en terreno) del **informe** `comprobantes-rutas`. La pantalla operativa vivirá bajo el módulo **Logística**; el informe puede quedar orientado a consulta y enlace a operar.

## Navbar

- Ítem principal: **Logística** en `APPS_MENU` (`core/utils/utils.py`).
- Submenú: **Entregas** → **`/logistica/entregas/`** (`logistica:entregas`). Las rutas antiguas bajo `/ecom/logistica/…` redirigen 301 al módulo autónomo.

## Alcance del listado (punto 1 — cerrado)

| Modo | Comportamiento |
|------|----------------|
| **Por defecto** | Fecha **hoy** (entregas / remitos del día según criterio de negocio ya usado en listado). |
| **Mi ruta** | Incluir todo lo que corresponda a **la ruta del usuario logueado** (misma intención que legado: chofer / usuario asociado a la hoja de ruta). |

**Implementación de referencia (legado documentado en SPEC):** si el usuario no es «supervisor de ventas», filtrar por `chofer.id_usuario` = usuario de sesión; en Synap mapear desde `request.session['user']` el flag equivalente a `supervisor_venta` y el vínculo chofer↔usuario.

**UI:** conmutador o pestañas claras: «Hoy» (default) vs «Mi ruta» (o un solo listado que combine ambos criterios si negocio lo define así en v1).

## Permisos (punto 2 — auditoría PHP `administraNET-ecom/mayoristapp`)

**Synap (definido):** el acceso al ítem de menú **Logística → Entregas** y a la ruta **`/logistica/entregas/`** exige el `key_permiso` **`logistica_editar_entregas`** en el puesto (tabla `permiso_sistema` / asignación en puesto), o el comodín **`logistica.*`**. Se sincroniza a MySQL con el resto de permisos Synap (`core/services/sync_permisos_synap.py`). Permiso DRF: `logistica.permissions.LogisticaEntregasPermission`.

**Hallazgo (legado PHP):** en el código revisado **no aparece un permiso nominal** (tabla `permiso`, código tipo `logistica_*`) que habilite o bloquee **registrar entrega**.

| Archivo | Qué hace |
|---------|----------|
| `sesion.inc.php` | Exige sesión válida (`id_sesion`) y usuario tipo **vendedor** (conexión `connV`, etc.). Sin sesión → no se carga el relay. |
| `relay-logistica-comprobantes.php` | Incluye `sesion.inc.php`. El `POST` de `guardarDatosEntrega` llama directamente a `guardarDatosEntrega()` **sin** comprobación adicional de permiso por nombre. El `id_usuario` de no entrega sale de `$_SESSION['idusuario']`. |
| `listadoComprobantes()` (mismo relay) | **Ámbito de datos:** si `$_SESSION['supervisor_venta'] == 'No'`, agrega `AND chofer.id_usuario = <idusuario sesión>` (solo ve “su” ruta como chofer). No es un permiso distinto; es filtro SQL. |
| `header-vendedor.inc.php` / `menu-lista-listados.php` | Los enlaces a **Comprobantes en ruta** (`logistica_lista_comprobantes_rutas.php`) están en el menú **sin** `if` de permiso alrededor (a diferencia de, p. ej., bloques que usan `inf_gerenciales` o `modPremios`). Cualquier vendedor con menú estándar ve Logística. |

**Conclusión para Synap:** el equivalente funcional del PHP es:

1. **Acceso al módulo / pantalla Entregas:** usuario autenticado AdministraNET con el mismo criterio que puede usar **mayoristapp** como vendedor (lo que ya defina el login / sesión Synap).
2. **Restricción “mi ruta”:** replicar el flag **`supervisor_venta`** (o nombre equivalente en sesión Synap) + filtro por **`idusuario`** ↔ `chofer.id_usuario` en consultas.
3. **Permiso fino en Synap (opcional):** si en el futuro quieren separar “solo ver informe” vs “operar entregas”, habría que **introducir** un permiso nuevo en el modelo de negocio (no viene de un código PHP explícito en estos archivos).

**Hoy en Synap** las APIs de entrega bajo `reports` usan `OperationalReportsPermission | ManagerialReportsPermission`; se puede mantener esa equivalencia o acotar con un permiso dedicado cuando producto lo defina.

## Enlace desde el informe (punto 3 — sí)

- En el dashboard `comprobantes-rutas`, mantener acción tipo **«Registrar en Logística»** / **«Operar entrega»** que abra la pantalla **Entregas** con **remito (y pedido si aplica) preseleccionados** vía query string o estado en URL (p. ej. `?cod_mov_remito=&cod_mov_pedido=`).

## Responsive

- **Mobile-first:** tarjetas, botones táctiles, confirmación explícita de entrega.
- **Desktop:** mismos datos, layout más denso; heredar **templates base** del shell Synap (`base_app.html` u homólogo del proyecto).

## Fases sugeridas

1. **Hecho (Synap):** app Django **`logistica`**: listado **Hoy** / **Mi ruta**, filtros, tarjetas, detalle y **Registrar entrega**. APIs: **`/logistica/api/entregas/…`**. Dominio MySQL: `logistica.services.lista_comprobantes_rutas` (el informe Reports sigue pudiendo importar vía `reports.services.logistica_lista_comprobantes_rutas` como capa de compatibilidad). Permiso: `logistica_editar_entregas` (`logistica.permissions.LogisticaEntregasPermission`).
2. **Deep link:** `GET /logistica/entregas/?cod_mov_remito=&cod_mov_pedido=&abrir=entrega` (válido también vía redirect desde `/ecom/logistica/entregas/…`).
3. Refactor opcional: más filtros alineados al informe (período arbitrario en Entregas).

## Module Management (Synap)

El módulo aparece en la gestión de módulos cuando está definido en `core/module_registry.py` (`MODULE_CONFIGS['logistica']`) y existe la fila correspondiente en `core_moduleconfig` (creada por migración `0011_moduleconfig_logistica` o por `setup_modules --init` / `--reset` en entornos nuevos). Tras desplegar, activar **Logística** desde Module Management si la ruta `/logistica/…` debe pasar el `ModuleMiddleware` (módulo inactivo → redirección al dashboard).

---

*Última actualización: módulo autónomo `logistica` (URLs `/logistica/…`); redirecciones 301 desde `/ecom/logistica/…`.*
