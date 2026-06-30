# Tasks: Armado unificado 1ra/2da e imputación supervisor

## Phase 1: Modelos y migraciones

- [x] 1.1 Crear `MprArmadoLote` y campos `modo`, `id_lote_armado`, `estado_imputacion` en `mpr/models.py`
- [x] 1.2 Crear `MprImputacionArmado` en `mpr/models.py`
- [x] 1.3 Migración Django + data migration `modo='2da'` en movimientos existentes
- [x] 1.4 Registrar modelos en `mpr/admin.py`

## Phase 2: Servicios armado 1ra + orquestador

- [x] 2.1 `listar_packs_armado_1ra` y `calcular_max_packs_armado_1ra` en `mpr/services.py`
- [x] 2.2 `_ejecutar_armado_1ra_tx` (BOM fija, anti-tamper, stock Semi) — vía validación BOM + `_ejecutar_armado_surtido_tx`
- [x] 2.3 Generalizar `ejecutar_lote_armado(modo)` delegando 1ra/2da
- [x] 2.4 `validar_reglas_lote_armado` con `modo` y prohibición mezcla
- [x] 2.5 Persistir `MprArmadoLote` post-ejecución; `estado_imputacion=pendiente` en 1ra

## Phase 3: Vista unificada y deprecación OPT

- [x] 3.1 `ArmadoView` + rutas `/mpr/armado/` en `mpr/urls.py`
- [x] 3.2 Template armado unificado (toggle 1ra/2da, BOM read-only en 1ra) — `armado_surtido.html`
- [x] 3.3 Redirects: `armado-surtido` → `modo=2da`; `armado_opt` → `modo=1ra`
- [x] 3.4 Eliminar gates `opt_puede_armado_surtido` en GET/POST
- [x] 3.5 Quitar CTAs armado en `opt_detail.html`; wizard paso 4 → enlace menú
- [x] 3.6 Ajustar `estado_acciones_opt`: `puede_cerrar` solo pendiente OPP

## Phase 4: Imputación supervisor (Fase B)

- [x] 4.1 Servicios: `listar_mstock_pendientes_imputacion`, `sugerir_imputacion_fifo`, `confirmar_imputacion_armado`
- [x] 4.2 `ImputacionArmado1raView` + template + permiso `mpr.imputar_armado_1ra`
- [x] 4.3 Actualizar `lista_produccion_detalle` y `estado_pedido_opt` al confirmar

## Phase 5: Tests

- [x] 5.1 `test_armado_unificado_modo.py` (redirect, reglas 1ra, sin gate OPT)
- [x] 5.2 `test_armado_unificado_lote_1ra.py` (BOM, parcial stock)
- [x] 5.3 `test_imputacion_armado_1ra.py` (FIFO, 403, límite cantidad)
- [x] 5.4 `test_estado_acciones_opt_cierre.py` (cerrar sin armado)
- [x] 5.5 Suite en contenedor: `docker exec Synap_app python manage.py test mpr.tests.test_armado_unificado ...`

## Phase 6: Documentación

- [x] 6.1 `MANUAL_USUARIO_MPR.md` § Armado 1ra/2da e imputación (§7 unificado + §7.3 imputación supervisor)
- [x] 6.2 `FUENTE_VERDAD_UI_REPORTES_MPR.md` rutas `/mpr/armado/`
- [x] 6.3 Actualizar SDD estado a implementado tras verify — `state.yaml` verify: done; ver `verify-report.md`
