# Tasks: Artículos terminados/fabricados y olas stock inicial

**Change:** `best-articulos-terminados-fabricados-olas` · **Modo:** hybrid

> **Ya implementado (no rehacer):** `cargar_stock_inicial_best` (olas anti-duplicado), banner olas, `test_cargar_stock_inicial_olas.py`. Solo UI de colas en stock inicial.

## Phase 1: Modelo y origen

- [x] 1.1 Añadir `BOM_FABRICADO = "BOM_FABRICADO", "BOM fabricado"` a `BestArticuloMap.OrigenRequerimiento` en `mpr/best_migration/models.py`
- [x] 1.2 Crear migración Django `mpr/migrations/00XX_*.py` solo de `choices` (sin DDL MySQL legacy)
- [x] 1.3 Renombrar display `nombre="Artículos terminados"` y actualizar `descripcion` en dominio `codigo="articulos"` en `mpr/best_migration/domains.py`
- [x] 1.4 Registrar `MigrationDomain(codigo="articulos_fabricados", obligatorio_para_pedidos=False, …)` con copy Semi-Embalado↔Semi-elaborado opcional post-cutover

## Phase 2: Servicios — guards gate y matcher BOM

- [x] 2.1 **Guard:** en `refresh_parity_counters` (`services.py`), excluir `.exclude(origen_requerimiento=BOM_FABRICADO)` de conteos que alimentan gate PED
- [x] 2.2 **Guard:** en `recalcular_mapeo_articulos`, excluir `BOM_FABRICADO` del `delete()` masivo (no borrar mapeos fabricados al recalcular terminados)
- [x] 2.3 Implementar `_load_admin_fabricados(base_empresa)` — query Admin `tipo_art_fab='Fabricado'` para matcher inverso
- [x] 2.4 Implementar `resolver_fabricados_desde_terminados(base_empresa)` — terminados VALIDADO → explosión `en_abm_formula` → fabricados únicos → inferir SKU BEST → upsert `origen_requerimiento=BOM_FABRICADO` (sin tocar parity/gate)
- [x] 2.5 Extender `hub_context` con contadores separados de fabricados; confirmar que `domains_required_for_orders()` no incluye `articulos_fabricados`
- [x] 2.6 Branch opcional stock Semi: filtrar sync/carga fabricados por depósito BEST 4002 vía `BestDepositoMap` → Admin SemiElaborado (reusar olas existentes; `CARGADO` inmutable)

## Phase 3: Vistas, URLs y pantalla fabricados

- [x] 3.1 Filtrar vista Terminados (`MigracionBestArticulosView`) para excluir filas `origen_requerimiento=BOM_FABRICADO`; mantener Asignar solo candidatos Admin Terminado
- [x] 3.2 Crear `MigracionBestArticulosFabricadosView` + acciones POST (resolver/validar/aceptar-inferidos) espejo de terminados en `views.py`
- [x] 3.3 Registrar rutas en `mpr/urls.py`: `/migracion-best/articulos-fabricados/` y sub-rutas espejo de `/articulos/`
- [x] 3.4 Crear `mpr/templates/mpr/best_migration/articulos_fabricados.html` (canon UI MPR/reportes; textos español; acción «Resolver fabricados»)

## Phase 4: Stock inicial — colas UI (backend olas ya hecho)

- [x] 4.1 Añadir tabs/colas en `stock_inicial.html`: Pendiente mapeo (`SIN_MAPEO_*`) / Listos carga (`LISTO`,`CONCILIADO`) / Ya cargados (`CARGADO`)
- [x] 4.2 En `MigracionBestStockInicialView`, filtrar queryset por cola activa y exponer contadores alineados con métricas de `cargar_stock_inicial_best`
- [x] 4.3 Copy orientador: cutover prioriza Terminados (dep. Terminado); fabricados/Semi opcional post-cutover — no reimplementar lógica de carga

## Phase 5: Hub — rename y tarjeta fabricados

- [x] 5.1 Actualizar `hub.html`: label «Artículos terminados»; nueva fila «Artículos fabricados» con semáforo informativo (no requisito Gate PED)
- [x] 5.2 Verificar checklist hub: stock Semi fabricados y dominio fabricados no bloquean `migracion_habilitada`

## Phase 6: Documentación

- [x] 6.1 Actualizar `docs/mpr/MODULO_MIGRACION_BEST_MPR.md`: terminados vs fabricados; BOM solo Admin (`en_abm`/`en_abm_formula`); olas stock; Semi-Embalado↔Semi-elaborado opcional; guards `BOM_FABRICADO`

## Phase 7: Tests

- [x] 7.1 Test: `refresh_gate`/`migracion_habilitada` ignora filas `BOM_FABRICADO` con fabricados pendientes
- [x] 7.2 Test: `recalcular_mapeo_articulos` preserva filas `BOM_FABRICADO` existentes
- [x] 7.3 Test: `resolver_fabricados_desde_terminados` infiere desde BOM Admin (sin `REP_RECETAS`); Asignar acepta candidatos Fabricado
- [x] 7.4 Test: sync stock fabricados usa depósito 4002→SemiElaborado; líneas `CARGADO` no reprocesadas (regresión sobre `test_cargar_stock_inicial_olas.py`)
- [x] 7.5 Test: hub/display «Artículos terminados»; rutas `/articulos/` estables; colas stock filtran estados correctamente
- [x] 7.6 Ejecutar suite: `docker exec Synap_app python manage.py test mpr.best_migration`
