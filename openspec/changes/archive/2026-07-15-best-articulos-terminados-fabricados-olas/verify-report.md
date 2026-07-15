# Verification Report

**Change**: `best-articulos-terminados-fabricados-olas`  
**Version**: spec híbrida (3 capabilities, 14 reqs, 22 escenarios)  
**Mode**: Standard  
**Fecha verify**: 15/07/2026

---

## Completeness

| Metric | Value |
|--------|-------|
| Tasks total | 26 |
| Tasks complete | 26 |
| Tasks incomplete | 0 |

Todas las tareas en `tasks.md` están marcadas `[x]`. Fases 1–7 completas.

---

## Build & Tests Execution

**Build**: ✅ Passed (`docker exec Synap_app python manage.py check` — 0 issues)

**Tests (scope change)**: ✅ 11 passed / ❌ 0 failed / ⚠️ 0 skipped

```text
docker exec Synap_app python manage.py test \
  mpr.best_migration.tests.test_articulos_fabricados_olas \
  mpr.best_migration.tests.test_cargar_stock_inicial_olas \
  --verbosity=2 --keepdb
Ran 11 tests in 0.133s — OK
```

**Tests (suite completa `mpr.best_migration`)**: ⚠️ 36 passed / ❌ 1 failed / 37 total

- Fallo preexistente (no bloqueante para este change): `test_reset_staging.ReiniciarStagingBestTests.test_reiniciar_borra_todas_las_tablas` — `DatabaseOperationForbidden` en `SimpleTestCase` sin `databases = ['default']`.
- Tests nuevos del change: todos verdes.

**Coverage**: ➖ Not available (sin umbral configurado en `openspec/config.yaml`)

---

## Spec Compliance Matrix

| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| **Colas stock** — Tres colas | Usuario filtra pendientes de mapeo | `test_articulos_fabricados_olas > test_colas_stock_inicial_por_estado` | ⚠️ PARTIAL (contadores servicio; sin test de filtro vista) |
| **Colas stock** — Tres colas | Usuario identifica ola actual | `test_colas_stock_inicial_por_estado` | ✅ COMPLIANT |
| **Colas stock** — Confirmación solo pendientes | Ola posterior no toca cargados | `test_cargar_stock_inicial_olas > test_sync_no_reabre_cargado`, `test_ola2_solo_nueva_linea_candidata` | ✅ COMPLIANT |
| **Colas stock** — Confirmación solo pendientes | Solo listos entran en la ola | `test_ola1_listo_confirmado_cargado_y_alta_movimiento` | ✅ COMPLIANT |
| **Colas stock** — Copy Terminados | Banner o texto orientador visible | (none found) | ❌ UNTESTED (evidencia estática en `stock_inicial.html`) |
| **Colas stock** — Métricas ola | Resultado post-confirmación | `test_ola1_listo_confirmado_cargado_y_alta_movimiento` | ⚠️ PARTIAL (métricas servicio; sin test UI recarga) |
| **Terminados** — Etiqueta visible | Hub muestra «Artículos terminados» | `test_dominio_terminados_rename_y_fabricados_no_gate` | ✅ COMPLIANT |
| **Terminados** — Etiqueta visible | Ruta y código sin ruptura | `test_ruta_articulos_estable` | ✅ COMPLIANT |
| **Terminados** — Matcher sin cambio | Asignación manual terminado (solo Terminado) | (none found) | ❌ UNTESTED (evidencia: `best_asignar_maestro.js`, `articulos.html`) |
| **Terminados** — Gate PED | Gate habilitado sin fabricados mapeados | `test_gate_habilitado_con_fabricados_pendientes` | ✅ COMPLIANT |
| **Terminados** — Gate PED | Fabricados incompletos no bloquean hub PED | `test_dominio_terminados_rename_y_fabricados_no_gate` | ✅ COMPLIANT |
| **Terminados** — Descripción dominio | Texto de ayuda en pantalla terminados | (none found) | ❌ UNTESTED (evidencia: `domains.py`, `articulos.html`) |
| **Fabricados** — Dominio no bloqueante | Tarjeta en hub sin semáforo gate | (none found) | ❌ UNTESTED (evidencia: `hub.html`) |
| **Fabricados** — Dominio no bloqueante | Cutover posible con fabricados pendientes | `test_gate_habilitado_con_fabricados_pendientes` | ✅ COMPLIANT |
| **Fabricados** — Pantalla espejo | Navegación desde hub | `test_ruta_articulos_estable` (URL fabricados) | ✅ COMPLIANT |
| **Fabricados** — BOM Admin única fuente | Explosión BOM desde terminado validado | `test_infiere_desde_bom_admin` | ✅ COMPLIANT |
| **Fabricados** — BOM Admin única fuente | Fuera de alcance REP_RECETAS | (none found) | ⚠️ PARTIAL (código `_fetch_best_catalog_skus` sin REP_RECETAS; sin test explícito) |
| **Fabricados** — Matcher inverso | Inferencia automática con score | `test_infiere_desde_bom_admin` | ✅ COMPLIANT |
| **Fabricados** — Matcher inverso | Asignación manual fabricado | (none found) | ❌ UNTESTED (evidencia: `articulos_fabricados.html` `tipo_art_fab=Fabricado`) |
| **Fabricados** — Stock Semi opcional | Sync stock fabricados post-cutover | `test_sync_solo_deposito_4002_fabricados`, olas `test_ola2` | ✅ COMPLIANT |
| **Fabricados** — Stock Semi opcional | Stock Semi no bloquea PED | `test_dominio_terminados_rename_y_fabricados_no_gate` | ✅ COMPLIANT |
| **Fabricados** — Separación datos | Contadores independientes en hub | `test_gate_habilitado_con_fabricados_pendientes` | ✅ COMPLIANT |

**Compliance summary**: 14/22 escenarios ✅ COMPLIANT · 3 ⚠️ PARTIAL · 5 ❌ UNTESTED

---

## Correctness (Static — Structural Evidence)

| Requirement | Status | Notes |
|------------|--------|-------|
| `BOM_FABRICADO` en modelo + migración | ✅ Implemented | `models.py`, `0023_best_articulo_bom_fabricado.py` |
| Guard gate `refresh_parity_counters` | ✅ Implemented | Excluye `BOM_FABRICADO`; filtra `PEDIDO_ABIERTO` |
| Guard `recalcular_mapeo_articulos` delete | ✅ Implemented | `.exclude(origen_requerimiento=BOM_FABRICADO)` en delete y preservados |
| Dominio `articulos_fabricados` no gate | ✅ Implemented | `obligatorio_para_pedidos=False`; fuera de `domains_required_for_orders()` |
| Rename «Artículos terminados» | ✅ Implemented | `domains.py` `codigo="articulos"` estable |
| Pantalla `/articulos-fabricados/` | ✅ Implemented | `views.py`, `urls.py`, `articulos_fabricados.html` |
| `resolver_fabricados_desde_terminados` | ✅ Implemented | BOM Admin `_fabricado_idarts_desde_bom_terminados` |
| Colas stock UI (tabs) | ✅ Implemented | `stock_inicial.html` + filtro `cola` en vista |
| Hub fabricados informativo | ✅ Implemented | `hub.html` fila + enlace resolver |
| Documentación | ✅ Implemented | `docs/mpr/MODULO_MIGRACION_BEST_MPR.md` actualizado |

---

## Coherence (Design)

| Decision | Followed? | Notes |
|----------|-----------|-------|
| Reusar `BestArticuloMap` + `BOM_FABRICADO` | ✅ Yes | Sin tabla nueva |
| Aislamiento gate PED | ✅ Yes | Guards en parity y recalcular |
| Rename solo display (`codigo` estable) | ✅ Yes | URLs `/articulos/` intactas |
| BOM Admin (`en_abm_formula`), no REP_RECETAS | ✅ Yes | Implementado en servicios |
| Depósito 4002 Semi-Embalado | ✅ Yes | `sincronizar_stock_fabricados_semi` |
| Colas sobre estados existentes | ✅ Yes | Tabs `pendiente_mapeo` / `listos_carga` / `ya_cargados` |
| Migración solo choices | ✅ Yes | `0023_best_articulo_bom_fabricado.py` |

---

## Issues Found

**CRITICAL** (must fix before archive):
- None en el alcance de este change. El fallo `test_reset_staging` es preexistente y ajeno a BOM_FABRICADO/colas.

**WARNING** (should fix):
- 5 escenarios UI/copy sin test de comportamiento (hub tarjeta fabricados, banner cutover, Asignar Terminado/Fabricado, texto ayuda).
- 3 escenarios PARTIAL (filtro cola vista, métricas post-confirm UI, REP_RECETAS sin test explícito).
- Suite completa `mpr.best_migration`: 1 fallo preexistente en `test_reset_staging`.
- `manage.py test` advierte modelos con cambios sin migración reflejada (warning Django global, no específico del change).

**SUGGESTION** (nice to have):
- Tests de integración vista (Client GET) para tabs colas y hub semáforo fabricados.
- Corregir `test_reset_staging` heredando `TestCase` o declarando `databases`.

---

## Verdict

**PASS WITH WARNINGS**

Gates críticos verificados en runtime: `BOM_FABRICADO` excluido del gate PED y del delete en recalcular; resolver fabricados desde BOM Admin; colas stock por estado; rename terminados; pantalla y rutas fabricados. 11/11 tests del scope del change en verde. Residuales: cobertura UI parcial (5 UNTESTED) y fallo heredado `test_reset_staging` en suite amplia.

**Next recommended**: `sdd-archive`
