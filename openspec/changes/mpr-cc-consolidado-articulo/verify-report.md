```yaml
schema: gentle-ai.verify-result/v1
evidence_revision: sha256:3d3d38d91ebccb7a14bf04aad5e71450f39aacfecda3a140b0d99d9f57cc01c5
verdict: pass_with_warnings
blockers: 0
critical_findings: 0
requirements: 25/25
scenarios: 45/45
test_command: docker exec Synap_app python manage.py test mpr.tests.test_cc_consolidado_articulo mpr.tests.test_cc_consolidado_views_ui mpr.tests.test_etapa10_clasificacion_produccion mpr.tests.test_docenas_clasificacion_operario --keepdb --noinput
test_exit_code: 0
test_output_hash: sha256:2cc4b933d06245bead4bba4c1b3444423659a970dfbd3b3fdd275020380d0ccf
build_command: docker exec Synap_app python manage.py shell -c "import mpr.services_cc_consolidado; print('OK')"
build_exit_code: 0
build_output_hash: sha256:fafa039ffddd453a7c85d320ab84a0334072f4579b68e270bc14b0c086ca0fc6
```

## Verification Report

**Change**: mpr-cc-consolidado-articulo
**Version**: delta specs 2026-08-20 (3 capabilities)
**Mode**: Strict TDD

### Completeness
| Metric | Value |
|--------|-------|
| Tasks total | 37 |
| Tasks complete | 37 |
| Tasks incomplete | 0 |

### Build & Tests Execution
**Build**: ✅ Passed
```text
docker exec Synap_app python manage.py shell -c "import mpr.services_cc_consolidado; print('OK')"
OK
```

**Tests**: ✅ 100 passed / 0 failed / 0 skipped
```text
docker exec Synap_app python manage.py test mpr.tests.test_cc_consolidado_articulo mpr.tests.test_cc_consolidado_views_ui mpr.tests.test_etapa10_clasificacion_produccion mpr.tests.test_docenas_clasificacion_operario --keepdb --noinput
Found 100 test(s).
Ran 100 tests in 60.580s
OK
```

**Coverage**: ➖ Not available (no coverage tool run on changed files)

### Spec counts (authoritative, delta ADDED+MODIFIED)
| Capability | Requirements | Scenarios |
|------------|-------------|-----------|
| mpr-clasificacion-operario-fabricante | 18 | 31 |
| mpr-transiciones-lote | 4 | 8 |
| mpr-reporte-rendimiento-operario | 3 | 6 |
| **Total** | **25** | **45** |

REMOVED requirements (2): sin escenarios — verificados por ausencia en builder CC.

### Spec Compliance Matrix
| Requirement | Scenario | Test | Result |
|-------------|----------|------|--------|
| Grilla por bloque artículo | Varias máquinas y turnos en un bloque | `test_cc_consolidado_articulo.py > test_b1_b2_ignora_turno_y_colapsa_maquinas` | ✅ COMPLIANT |
| Grilla por bloque artículo | Sin filtro turno en GET | `test_cc_consolidado_views_ui.py > test_get_no_pasa_turno_id_a_grilla` | ✅ COMPLIANT |
| Columna cantidad = saldo Depósito Producción | Parte menor que saldo físico | `test_cc_consolidado_articulo.py > test_s6_parte_100_saldo_150_tope_150` | ✅ COMPLIANT |
| Columna cantidad = saldo Depósito Producción | Saldo como única autoridad | `test_cc_consolidado_articulo.py > test_s3_exceso_sobre_saldo_rechaza_sin_filas` | ✅ COMPLIANT |
| Semi consolidado por artículo | Guardado Semi único | `test_cc_consolidado_articulo.py > test_s1_semi_120_prod_cero_ledger_sin_operario` | ✅ COMPLIANT |
| Semi consolidado por artículo | Lectura Semi agregada del día | `test_cc_consolidado_articulo.py > test_s8_historico_semi_60_prod_cero_muestra_sin_insert` | ✅ COMPLIANT |
| Segunda y desperdicio por operario y turno | Mismo operario en dos máquinas | `test_cc_consolidado_articulo.py > test_b1_b2_ignora_turno_y_colapsa_maquinas` | ✅ COMPLIANT |
| Segunda y desperdicio por operario y turno | POST 2da con operario del parte | `test_cc_consolidado_articulo.py > test_s2_semi_100_2da_luis_20_prod_cero` | ✅ COMPLIANT |
| Artículo huérfano solo Semi | Huérfano con Semi | `test_cc_consolidado_articulo.py > test_s4_huerfano_semi_50_sin_2da` | ✅ COMPLIANT |
| Artículo huérfano solo Semi | POST 2da en huérfano rechazado | `test_cc_consolidado_articulo.py > test_s5_huerfano_post_2da_rechazado` | ✅ COMPLIANT |
| Tope único por artículo con bloqueo de saldo | Exceso sobre saldo | `test_cc_consolidado_articulo.py > test_s3_exceso_sobre_saldo_rechaza_sin_filas` | ✅ COMPLIANT |
| Tope único por artículo con bloqueo de saldo | Cantidad cero no escribe ledger | `test_etapa10_clasificacion_produccion.py > test_cantidades_cero_ignoradas` | ✅ COMPLIANT |
| Parser POST consolidado | Clave Semi legada ignorada | `test_cc_consolidado_articulo.py > test_c6_ignora_semi_legado_y_usa_clave_consolidada` | ✅ COMPLIANT |
| Borrador por fecha | Borrador viejo incompatible | `test_cc_consolidado_articulo.py > test_avisa_borrador_viejo_incompatible` | ✅ COMPLIANT |
| Borrador por fecha | Borrador no mueve stock | `test_cc_consolidado_articulo.py > test_b7_upsert_por_fecha_solo_escribe_tablas_borrador` | ✅ COMPLIANT |
| Filtro Solo pendiente | Ocultar artículo sin saldo | `test_cc_consolidado_articulo.py > test_b3_b4_solo_pendiente_oculta_saldo_cero_y_operario_confirmado` | ✅ COMPLIANT |
| Filtro Solo pendiente | Ocultar operario confirmado en 2da | `test_cc_consolidado_articulo.py > test_b3_b4_solo_pendiente_oculta_saldo_cero_y_operario_confirmado` | ✅ COMPLIANT |
| Bloqueo dual del parte | Solo Semi nuevo no bloquea | `test_cc_consolidado_articulo.py > test_b5_b6_query_dual_semi_nuevo_no_bloquea_e_historico_si` | ✅ COMPLIANT |
| Bloqueo dual del parte | Semi histórico con operario bloquea | `test_cc_consolidado_articulo.py > test_b5_b6_query_dual_semi_nuevo_no_bloquea_e_historico_si` | ✅ COMPLIANT |
| Bloqueo dual del parte | 2da bloquea turno | `test_etapa10_clasificacion_produccion.py > test_registrar_parte_rechaza_si_hay_cc` | ✅ COMPLIANT |
| Histórico de ledger de solo lectura | Histórico intacto tras confirmación nueva | `test_cc_consolidado_articulo.py > test_s8_historico_semi_60_prod_cero_muestra_sin_insert` | ✅ COMPLIANT |
| Dimensión operario fabricante en ledger | Guardado 2da con operario | `test_cc_consolidado_articulo.py > test_s2_semi_100_2da_luis_20_prod_cero` | ✅ COMPLIANT |
| Dimensión operario fabricante en ledger | Semi nuevo sin operario | `test_cc_consolidado_articulo.py > test_s1_semi_120_prod_cero_ledger_sin_operario` | ✅ COMPLIANT |
| Dimensión operario fabricante en ledger | Histórico sin operario | `test_cc_consolidado_articulo.py > test_s8_historico_semi_60_prod_cero_muestra_sin_insert` | ✅ COMPLIANT |
| Grilla por artículo y operario | Dos operarios mismo artículo | `test_docenas_clasificacion_operario.py > test_grilla_filas_por_operario` | ✅ COMPLIANT |
| Grilla por artículo y operario | Sin filas vacías por defecto en Solo pendiente | `test_docenas_clasificacion_operario.py > test_grilla_sin_bloqueo_si_clasificacion_completa` | ✅ COMPLIANT |
| Cálculo de pendiente por operario | Clasificación parcial 2da | `test_cc_consolidado_articulo.py > test_b3_b4_solo_pendiente_oculta_saldo_cero_y_operario_confirmado` | ⚠️ PARTIAL |
| Validación por fila | Exceso 2da por operario | `test_cc_consolidado_articulo.py > test_exceso_2da_por_operario_rechaza_sin_transferir` | ✅ COMPLIANT |
| Validación global por artículo | Desfase con stock físico | `test_etapa10_clasificacion_produccion.py > test_bloqueo_suma_excede_disponible` | ✅ COMPLIANT |
| Presentación docenas en clasificación | POST en docenas | `test_cc_consolidado_articulo.py > test_parser_convierte_docenas_y_descarta_ceros` | ✅ COMPLIANT |
| Auditoría del clasificador | Distinción fabricante vs usuario en 2da | `test_docenas_clasificacion_operario.py > test_crear_transicion_con_operario` | ✅ COMPLIANT |
| Confirmación CC atómica por artículo | Semi y 2da en un solo commit | `test_cc_consolidado_articulo.py > test_s2_semi_100_2da_luis_20_prod_cero` | ✅ COMPLIANT |
| Confirmación CC atómica por artículo | Fallo en 2da tras Semi validado | `test_cc_consolidado_articulo.py > test_s7_fallo_2da_rollback_prod_intacto` | ✅ COMPLIANT |
| Confirmación CC atómica por artículo | Éxito parcial entre artículos | `test_cc_consolidado_articulo.py > test_s9_parcial_articulo_1_ok_2_excede_borrador_2_intacto` | ✅ COMPLIANT |
| Wrapper CC sin alterar transferir_stock_lote genérico | Lote genérico sigue best-effort | `test_etapa10_clasificacion_produccion.py > test_best_effort_un_ok_un_fail` | ✅ COMPLIANT |
| Wrapper CC sin alterar transferir_stock_lote genérico | CC no usa transferir_stock_lote directo | `test_cc_consolidado_views_ui.py > test_post_confirma_via_servicio_consolidado` | ✅ COMPLIANT |
| Borrador CC solo tras éxito del artículo | Borrador preservado en fallo | `test_cc_consolidado_articulo.py > test_s9_parcial_articulo_1_ok_2_excede_borrador_2_intacto` | ✅ COMPLIANT |
| Escritura CC en transicion_lote | Semi CC sin operario en ledger | `test_cc_consolidado_articulo.py > test_s1_semi_120_prod_cero_ledger_sin_operario` | ✅ COMPLIANT |
| Escritura CC en transicion_lote | Suma insertada igual al POST | `test_etapa10_clasificacion_produccion.py > test_reparto_valido_tres_destinos` | ✅ COMPLIANT |
| Semi consolidado excluido de métricas por operario | Día con solo Semi consolidado | `test_cc_consolidado_articulo.py > test_b8_ignora_semi_null_y_suma_segunda` | ⚠️ PARTIAL |
| Semi consolidado excluido de métricas por operario | 2da y scrap siguen atribuidos | `test_cc_consolidado_articulo.py > test_b8_ignora_semi_null_y_suma_segunda` | ✅ COMPLIANT |
| Métricas de calidad por operario fabricante | Operario con fabricado y clasificación mixta | `test_cc_consolidado_articulo.py > test_b8_ignora_semi_null_y_suma_segunda` | ⚠️ PARTIAL |
| Métricas de calidad por operario fabricante | Fabricado sin clasificación atribuible | `test_cc_consolidado_articulo.py > test_fabricado_sin_clasificacion_atribuible_devuelve_mapa_vacio` | ✅ COMPLIANT |
| Histórico sin atribución de operario | Mezcla histórico Semi con operario y Semi NULL | `test_cc_consolidado_articulo.py > test_b8_ignora_semi_null_y_suma_segunda` | ⚠️ PARTIAL |
| Histórico sin atribución de operario | Sin doble conteo | `test_cc_consolidado_articulo.py > test_semi_null_no_se_duplica_entre_operarios` | ✅ COMPLIANT |

**Compliance summary**: 41/45 COMPLIANT, 4/45 PARTIAL, 0/45 UNTESTED

### Correctness (Static Evidence)
| Requirement | Status | Notes |
|------------|--------|-------|
| Servicio CC consolidado | ✅ Implemented | `mpr/services_cc_consolidado.py` con parser, builder, confirmación TX y `_atribuible_2da_scrap` |
| DDL borrador 007 | ✅ Implemented | `mpr/sql/007_mpr_cc_borrador_consolidado.sql` + catalog |
| Views integradas | ✅ Implemented | POST delega `confirmar_cc_consolidado`; GET sin turno |
| UI bloque artículo | ✅ Implemented | templates CC + tests views_ui |
| Bloqueo dual | ✅ Implemented | query `turnos_con_control_calidad` extendida |

### Coherence (Design)
| Decision | Followed? | Notes |
|----------|-----------|-------|
| Wrapper CC atómico sin tocar `transferir_stock_lote` | ✅ Yes | `_transferir_etapa_en_cursor` + TX por artículo |
| Tablas borrador nuevas 007 | ✅ Yes | convive con borrador legado |
| Semi NULL en ledger nuevo | ✅ Yes | S1/S2 confirman |
| Centinela 0 en borrador Semi | ✅ Yes | test_centinela_borrador |
| `turno_id` ignorado en grilla | ✅ Yes | documentado y testeado |

### TDD Compliance
| Check | Result | Details |
|-------|--------|---------|
| TDD Evidence reported | ✅ | `apply-progress` con tabla TDD Cycle Evidence (3 escenarios gap-fill) |
| All tasks have tests | ✅ | 37/37 tasks mapean a tests S1-S9, B1-B8, views_ui, etapa10 |
| RED confirmed (tests exist) | ✅ | 3 tests nuevos verificados en `test_cc_consolidado_articulo.py` |
| GREEN confirmed (tests pass) | ✅ | 100/100 en ejecución verify |
| Triangulation adequate | ✅ | Exceso 2da triangulado con S2; reporte con B8 + 2 tests dedicados |
| Safety Net for modified files | ✅ | apply-progress documenta 35/35 OK antes de gap-fill |

**TDD Compliance**: 6/6 checks passed

### Test Layer Distribution
| Layer | Tests | Files | Tools |
|-------|-------|-------|-------|
| Unit | 71 | 2 | Django SimpleTestCase + mocks |
| Integration | 29 | 2 | Django TestCase + RequestFactory |
| E2E | 0 | 0 | not installed |
| **Total** | **100** | **4** | docker exec Synap_app |

### Changed File Coverage
Coverage analysis skipped — no coverage tool detected

### Assertion Quality
**Assertion quality**: ✅ All assertions verify real behavior (sin tautologías; tests gap-fill assertan rechazo, mapa vacío y no-duplicación)

### Quality Metrics
**Linter**: ➖ Not run on changed files only
**Type Checker**: ➖ Not available

### Issues Found
**CRITICAL**: None

**WARNING**:
- Suite completa `manage.py test mpr` no ejecutada (MySQL 192.168.0.2 inalcanzable + fallos tablero preexistentes) — ambiental, fuera del alcance del change.
- Escenarios reporte «Sin atribución» / Semi NULL / mixta verificados a nivel repositorio (`test_b8`, tests dedicados), no en vista HTML del reporte Por operario.
- Escenario «Clasificación parcial 2da» (pendiente 25 docenas): PARTIAL — filtro solo pendiente cubierto, valor numérico de pendiente no assertado.
- Primera ejecución verify requirió copiar `docs/mpr/AUDITORIA_CC_CONSOLIDADO_BASELINE.sql` al contenedor (worktree→Synap mount); re-run 100/100 OK.

**SUGGESTION**:
- Añadir test de integración del reporte Por operario si producto exige validación UI de % apto y fila «Sin atribución».
- Ejecutar checklist §12.3 baseline en empresa con MySQL accesible antes de producción.

### Verdict
**PASS WITH WARNINGS** — 100/100 tests focalizados verdes; 41/45 escenarios COMPLIANT, 4 PARTIAL (reporte UI), 0 UNTESTED; 37/37 tareas completas; diseño coherente; TDD gap-fill verificado.
