# Tasks: Control de calidad consolidado por artículo

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 2200–3200 |
| 800-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 infra+RED → PR2 TX+confirm → PR3 grilla+lock → PR4 UI → PR5 docs |
| Delivery strategy | exception-ok (cierre PR4+PR5) |
| Chain strategy | stacked-to-main |
| size:exception | Aceptada 20/08/2026 (PR4 1795 vs 800; PR5 docs/verify con tope 3500) |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
800-line budget risk: High
size:exception: Yes — maintainer amplió presupuesto para finalizar correctamente

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Baseline, DDL 007, tests RED S1–S9 | PR1 | `docker exec Synap_app python manage.py test mpr.tests.test_cc_consolidado_articulo` | `apply_mpr_core_tables` idempotente en empresa prueba | Revert `007_*.sql`, `catalog.py`, `test_cc_consolidado_articulo.py` |
| 2 | Cursor TX, confirm atómico, parser | PR2 | `docker exec Synap_app python manage.py test mpr.tests.test_cc_consolidado_articulo.TestConfirmacionSaldo` | N/A — cubierto por fixtures MySQL en tests | Revert `services_cc_consolidado.py`, extract en `services.py`, ledger cursor |
| 3 | Grilla, borrador 007, bloqueo dual | PR3 | `docker exec Synap_app python manage.py test mpr.tests.test_cc_consolidado_articulo.TestGrillaBloqueo` | N/A | Revert repos + delegación en `services.py` |
| 4 | Views POST/GET + UI CC | PR4 | `docker exec Synap_app python manage.py test mpr.tests.test_etapa10_clasificacion_produccion` | Humo manual `/mpr/tablero-produccion/clasificacion-produccion/` | Revert `views.py` + templates CC |
| 5 | Docs, reportes, verify | PR5 | `docker exec Synap_app python manage.py test mpr` | `e2e_mpr_trazabilidad` + checklist §12.3 | Revert solo `docs/mpr/` |

## Phase 1: Baseline e infraestructura

- [x] 1.1 Crear `docs/mpr/AUDITORIA_CC_CONSOLIDADO_BASELINE.sql` (SELECT §12.3 plan; sin UPDATE).
- [x] 1.2 Crear `mpr/sql/007_mpr_cc_borrador_consolidado.sql` (`mpr_cc_borrador` / `mpr_cc_borrador_linea`; UK fecha; centinela 0).
- [x] 1.3 Registrar 007 + `idx_mpr_tl_fecha_art_dest` en `core/services/legacy_mysql_schema/catalog.py`.
- [x] 1.4 Crear esqueleto `mpr/tests/test_cc_consolidado_articulo.py` con fixtures empresa prueba.

## Phase 2: Tests RED — saldos S1–S9 (TDD estricto)

- [x] 2.1 RED S1: Semi 120 → Prod 0, ledger `id_operario NULL`.
- [x] 2.2 RED S2: Semi 100 + 2da Luis 20 → Prod 0; Semi sin op; 2da con op.
- [x] 2.3 RED S3: Semi 100 + 2da 30 sobre Prod 120 → rechazo; cero filas.
- [x] 2.4 RED S4: huérfano Prod 50, Semi 50 → OK sin 2da.
- [x] 2.5 RED S5: huérfano POST 2da 10 → rechazo; Prod 50.
- [x] 2.6 RED S6: parte 100, saldo 150 → tope/mostrar 150.
- [x] 2.7 RED S7: fallo inyectado en 2da tras Semi → rollback; Prod intacto.
- [x] 2.8 RED S8: histórico Semi 60 con operario, Prod 0 → muestra 60; sin INSERT.
- [x] 2.9 RED S9: artículo 1 OK, artículo 2 excede → parcial; borrador 2 intacto.

## Phase 3: Tests RED — comportamiento B1–B8

- [x] 3.1 RED B1–B4: sin turno GET; colapso máquinas; Solo pendiente artículo/op.
- [x] 3.2 RED B5–B6: solo Semi nuevo no bloquea; Semi histórico sí bloquea turno.
- [x] 3.3 RED B7: borrador no toca `stock_deposito`.
- [x] 3.4 RED B8: `sumar_clasificado_rendimiento_operario` ignora Semi NULL; suma 2da.

## Phase 4: Extracción transferencia en cursor

- [x] 4.1 Extraer `_transferir_etapa_en_cursor(cursor, ...)` desde `transferir_stock_entre_etapas` en `mpr/services.py` sin cambiar firma pública ni contrato best-effort de `transferir_stock_lote`.
- [x] 4.2 Añadir `crear_transicion_lote_en_cursor` y `semi_agregado_por_articulo_fecha` en `mpr/repositories/transicion_lote.py`.
- [x] 4.3 GREEN tests unitarios parser C6 y centinela 0→NULL borrador.

## Phase 5: Servicio CC consolidado

- [x] 5.1 Crear `mpr/services_cc_consolidado.py`: `construir_bloques_cc_articulo`, universo parte∪saldo∪roster; sin `_extra_pool`/`_max_clasificable_celda`.
- [x] 5.2 Implementar `parsear_post_cc_consolidado` (claves `semi_{art}`, `seg2da_`, `scrap_`; ignorar `semi_*_op_*`; tipos AdministraNET).
- [x] 5.3 Implementar `confirmar_cc_consolidado`: `FOR UPDATE` C1; validar C2–C7; TX por artículo; ledger `cantidad_extra=0`; borrador C13 solo OK.
- [x] 5.4 Delegar `construir_grilla_clasificacion_produccion` al builder nuevo; `turno_id` ignorado documentado.
- [x] 5.5 GREEN S1–S9 y B7 vía servicio confirmación.

## Phase 6: Repositorio borrador y bloqueo dual

- [x] 6.1 Extender `mpr/repositories/clasificacion_borrador.py` para tablas 007 (upsert por fecha, borrado por artículo, centinela 0↔NULL); conservar funciones viejas.
- [x] 6.2 Implementar query dual `turnos_con_control_calidad` (2da/scrap OR Semi con operario) en `transicion_lote.py`.
- [x] 6.3 GREEN B1–B6, B8 y aviso borrador incompatible en builder.

## Phase 7: Integración views

- [x] 7.1 Modificar GET `RegistrarClasificacionProduccionView`: quitar turno; delegar grilla; aviso borrador viejo.
- [x] 7.2 Modificar POST: `parsear_post_cc_consolidado` + `confirmar_cc_consolidado`; feedback `mprShowAviso`; sin `transferir_stock_lote` directo.
- [x] 7.3 GREEN integración views + adaptar `test_etapa10_clasificacion_produccion.py` y `test_docenas_clasificacion_operario.py`.

## Phase 8: UI (chrome CC existente)

- [x] 8.1 `clasificacion_produccion.html`: bloque artículo rowspan; Semi único; fila huérfana; Alpine por bloque.
- [x] 8.2 Includes encabezado/thead/qty: sin Turno/Máquina; «Saldo producción»; claves POST nuevas; sin `alert`/`confirm`.
- [x] 8.3 Humo template: footer Guardar borrador/CC deshabilitado sin editables.

## Phase 9: Documentación y verify

- [x] 9.1 Actualizar `GLOSARIO_MPR.md`, `MANUAL_USUARIO_MPR.md` §5, `DOCENAS_CLASIFICACION_OPERARIO_MPR.md`, `REPORTES_MPR.md`, plan §estado.
- [x] 9.2 Ejecutar baseline pre/post §12.3 en empresa prueba; registrar resultados en `docs/mpr/`.
- [x] 9.3 Verify: `docker exec Synap_app python manage.py test mpr` + checklist §13 plan.
