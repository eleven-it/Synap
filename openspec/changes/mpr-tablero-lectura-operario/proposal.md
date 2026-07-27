# Proposal: Tablero de producción — lectura para operarios

**Change:** `mpr-tablero-lectura-operario` · **Fecha:** 27/07/2026

## Intent

Operarios con `mpr.parte_operario` no pueden consultar el Tablero sin `mpr.ver` (escritorio completo). Se requiere **solo lectura** del tablero (filtros, Pack|Par, Actualizar, modales) conservando `/mpr/mi-parte/` y bloqueando Enviar, CC, reportes y config.

## Scope

### In Scope

- `mpr.tablero_ver` en `core/constantes_permisos.py` + siembra `synap_permiso`
- Perfil: `mpr.parte_operario` + `mpr.tablero_ver` (sin `mpr.ver`)
- GET tablero y Actualizar: `mpr.ver` OR `mpr.tablero_ver` (backend)
- POST Enviar/anular: solo `mpr.ver` (403; ocultar UI Enviar/anular)
- Vistas escritorio MPR con solo `MprLoginRequiredMixin` → exigir `mpr.ver`
- Menú: «Tablero de producción» con OR; resto sin cambio
- Landing: puro y operario+tablero (sin `mpr.ver`) → `/mpr/mi-parte/`
- Tests + docs `docs/mpr/`

### Out of Scope

PWA tablero; permisos por línea; quitar `mpr.ver`; cupo/envío; OPT.

## Capabilities

### New Capabilities

Ninguna.

### Modified Capabilities

- `mpr-operario-login`: permiso, perfiles, menú, landing, barreras escritorio
- `mpr-envio-produccion-tablero`: POST/UI Enviar exigen `mpr.ver`

## Approach

Sembrar `mpr.tablero_ver`. Helper `_usuario_puede_ver_tablero_produccion` + guards GET tablero/modales consulta. Enviar/anular solo `mpr.ver`. Auditar `mpr/views.py` con `MprPermisoMixin(mpr.ver)` en escritorio. Menú MPR raíz OR `tablero_ver`; item tablero OR. `es_operario_puro` = solo parte; operario+tablero aterriza en mi-parte. Tests: GET tablero 200, POST enviar 403, CC por URL 403.

## Affected Areas

| Area | Impact |
|------|--------|
| `core/constantes_permisos.py` | Nuevo permiso |
| `mpr/views.py`, `mpr/landing.py` | Guards y landing |
| `core/utils/utils.py` | Menú parcial |
| `mpr/templates/mpr/tablero_produccion.html` | UI solo lectura |
| `docs/mpr/*.md` | Permisos |

## Risks

| Risk | Mitigation |
|------|------------|
| AJAX tablero sin auditar | Inventario en design + tests |
| Modal tablero → CC | Ocultar enlace o 403 destino |
| Mega-menú oculto | OR en nodo raíz `mpr` |

## Rollback Plan

Quitar `mpr.tablero_ver` de puestos y revertir guards/menú. Sin migración de datos.

## Dependencies

Sync `synap_permiso`; delta `mpr-operario-login`.

## Success Criteria

- [ ] Operario+tablero: tablero GET/Actualizar OK; Enviar 403 y UI oculta
- [ ] Sin acceso URL a CC/reportes/armado
- [ ] `mpr.ver` sin regresión; docs actualizados
