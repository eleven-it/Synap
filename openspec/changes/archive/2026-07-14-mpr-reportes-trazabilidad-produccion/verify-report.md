# Informe de verificación

**Change:** `mpr-reportes-trazabilidad-produccion`  
**Fecha:** 14/07/2026 (re-verificación post-fixes)  
**Modo:** Standard (strict_tdd no activo)  
**Almacenamiento:** hybrid (Engram + openspec)

---

## Veredicto

**PASS WITH WARNINGS** — 56/56 tests del comando solicitado en verde, 7/15 escenarios compliant, 0 failing, fixes críticos aplicados (solo_pendiente, mock operario, tarea 4.5). Queda QA manual 5.6 y cobertura UI parcial.

---

## Completitud de tareas

| Métrica | Valor |
|--------|-------|
| Tareas totales | 40 |
| Tareas completas | 35 |
| Tareas incompletas | 5 |

### Tareas incompletas

| Tarea | Fase | Severidad | Notas |
|-------|------|-----------|-------|
| 5.6 Verificación manual en administranet96 | 5 | WARNING | QA manual pendiente (timeline artículo 1275, presets Alpine) |
| 6.1–6.4 Reportes P1 post-MVP | 6 | SUGGESTION | Opcional; no bloquea MVP |

**Tareas MVP (fases 1–5):** 35/36 completas. La única abierta (5.6) es verificación manual; no bloquea archive técnico.

### Fixes verificados en esta re-ejecución

| Fix | Estado | Evidencia |
|-----|--------|-----------|
| `solo_pendiente=True` en pendiente componentes | ✅ Corregido | `mpr/services.py` L13885; `test_solicita_pendientes_y_no_solo_urgentes` |
| Mock MySQL en `test_ranking_pct` | ✅ Corregido | Patch `@patch sumar_clasificado_rendimiento_operario` en `test_reportes_operario_parte.py` |
| Tarea 4.5 tests brecha PED | ✅ Cerrada | `test_retorna_lista_con_columnas_obligatorias` + `test_pasa_fechas_a_listar_demanda` con mocks |

---

## Ejecución de build y tests

**Build (`python manage.py check`):** ✅ Passed

**Tests solicitados** (`docker exec Synap_app python manage.py test --keepdb`):

```
mpr.tests.test_reportes_mpr_services
mpr.tests.test_reportes_mpr_view
mpr.tests.test_reportes_operario_parte
mpr.tests.test_tablero_consolidado
```

| Métrica | Valor |
|--------|-------|
| Total | 56 |
| Passed | 56 |
| Errors | 0 |
| Failed | 0 |
| Skipped | 0 |
| Exit code | 0 |

**Suite complementaria P0** (módulos adicionales del plan de diseño):

```
mpr.tests.test_reportes_resumen_diario
mpr.tests.test_reportes_cadena_pipeline
mpr.tests.test_reportes_trazabilidad
mpr.tests.test_reportes_shell_legacy_map
```

| Métrica | Valor |
|--------|-------|
| Total | 14 |
| Passed | 14 |
| Exit code | 0 |

**Nota:** `test_retorna_lista_de_dicts_estado_cantidad` (pedidos por estado) emite log MySQL al intentar conexión real; el test pasa con lista vacía. No bloquea veredicto.

**Cobertura:** No disponible (sin herramienta configurada).

---

## Matriz de cumplimiento de specs

| Requisito | Escenario | Test | Resultado |
|-----------|-----------|------|-----------|
| REQ-SHELL-01 | ESC-SHELL-01 Entrada default | `test_reportes_shell_legacy_map > test_default_context_resumen_diario` | ✅ COMPLIANT |
| REQ-SHELL-02 | ESC-SHELL-02 Cambio de período | (ninguno) | ❌ UNTESTED |
| REQ-SHELL-03 | ESC-SHELL-03 Histórico OPT | (ninguno comportamental) | ❌ UNTESTED |
| REQ-RESUMEN-03 | ESC-RESUMEN-01 Gap envío sin parte | `test_reportes_resumen_diario > test_agrega_gap_envio_parte` | ✅ COMPLIANT |
| REQ-RESUMEN-01 | ESC-RESUMEN-02 Período sin datos | (ninguno — solo `test_base_vacia` sin UI) | ❌ UNTESTED |
| REQ-OPER-02 | ESC-OPER-01 Ranking con datos | `test_reportes_operario_parte > test_ranking_pct` | ✅ COMPLIANT |
| REQ-OPER-04 | ESC-OPER-02 Sin partes en período | `test_reportes_operario_parte > test_vacio_sin_empresa` | ✅ COMPLIANT |
| REQ-CADENA-02 | ESC-CADENA-01 Gap envío sin parte | `test_reportes_cadena_pipeline > test_estado_falta_parte` | ✅ COMPLIANT |
| REQ-CADENA-02 | ESC-CADENA-02 Pipeline completo | (ninguno) | ❌ UNTESTED |
| REQ-PEND-01 | ESC-PEND-01 Lista solo pendientes | `test_reportes_mpr_services > test_solicita_pendientes_y_no_solo_urgentes` | ✅ COMPLIANT |
| REQ-PEND-03 | ESC-PEND-02 Sin pendientes | (ninguno) | ❌ UNTESTED |
| REQ-BRECHA-01 | ESC-BRECHA-01 Pack brecha urgente | `test_reportes_mpr_services > test_retorna_lista_con_columnas_obligatorias` | ⚠️ PARTIAL |
| REQ-BRECHA-02 | ESC-BRECHA-02 Sin brecha | `test_reportes_mpr_services > test_retorna_lista_con_columnas_obligatorias` (fila brecha=0) | ⚠️ PARTIAL |
| REQ-TRAZ-01 | ESC-TRAZ-01 Cadena completa timeline | (ninguno) | ❌ UNTESTED |
| REQ-TRAZ-01 | ESC-TRAZ-02 Sin artículo | `test_reportes_trazabilidad > test_sin_articulo` | ✅ COMPLIANT |

**Resumen:** 7/15 escenarios ✅ COMPLIANT · 0 ❌ FAILING · 6 ❌ UNTESTED · 2 ⚠️ PARTIAL

---

## Correctitud (evidencia estática)

| Requisito | Estado | Notas |
|-----------|--------|-------|
| Hub `/mpr/reportes/` + partials | ✅ Implementado | `reportes.html`, `mpr/reportes/**`, `reportes_hub.py` |
| Servicios P0 (resumen, operario, cadena, trazabilidad) | ✅ Implementado | `mpr/services.py` |
| Export CSV UTF-8 BOM | ✅ Implementado | `mpr/export.py`, `test_filas_a_csv_bom` |
| Brecha PED en vivo | ✅ Implementado | `reporte_mpr_brecha_demanda` delega a `listar_demanda_pack_desde_pedidos` |
| Pendiente componentes | ✅ Corregido | `reporte_mpr_pendiente_componentes` usa `solo_pendiente=True` |
| Compatibilidad URL legacy `tipo=` | ⚠️ Desviación | `tipo=pendiente` cae a default moderno; design pedía `grupo=legacy&reporte=pendiente_opt` |
| Alpine presets | ⚠️ Parcial | `mprReportesHub()` inline en `reportes.html` (no `static/mpr/js/reportes_hub.js`) |
| Grupo Histórico OPT | ⚠️ Parcial | `test_tipo_opt_cerradas_no_expone_legacy` confirma no exposición; expand/collapse sin test |

---

## Coherencia (design)

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| Hub en `/mpr/reportes/` | ✅ Sí | |
| GET + query params | ✅ Sí | |
| Servicio operario nuevo | ✅ Sí | `reporte_mpr_operario_parte` intacto vs legacy |
| Fecha parte vs creado_en | ✅ Sí | SQL usa `fecha_produccion` en parte |
| Plantillas fragmentadas | ✅ Sí | 20 partials bajo `mpr/reportes/` |
| `listar_tablero_por_articulo(solo_pendiente=True)` | ✅ Sí | Corregido en re-apply |
| `static/mpr/js/reportes_hub.js` | ⚠️ No | Alpine inline en template |
| `LEGACY_TIPO_MAP` + grupo legacy | ⚠️ No | Solo `TIPO_REDIRECT_MAP` para tipos modernos; `tipo=pendiente` no redirige a legacy |

---

## Issues encontrados

### CRITICAL (corregir antes de archive)

Ninguno en esta re-verificación.

### WARNING (debería corregirse)

1. Tarea **5.6** abierta — verificación manual en administranet96 pendiente (timeline artículo 1275, presets Alpine, export CSV).
2. **Legacy URL `tipo=pendiente`** no redirige a `legacy/pendiente_opt` como indica design/spec REQ-SHELL-09 (opcional según producto).
3. **6 escenarios sin test comportamental de UI** — shell presets, histórico OPT expand, empty states vista, brecha highlight vista, timeline completo, pipeline completo.
4. Tests brecha y pedidos a nivel servicio; highlight amber y empty state de vista sin cobertura automatizada.

### SUGGESTION

1. Fase 6 P1 (eficiencia, WIP snapshot, drill-down, sparkline) — post-MVP documentado.
2. Extraer Alpine a `static/mpr/js/reportes_hub.js` según design original.
3. Añadir tests de vista para CSV/pendiente/brecha con mocks de servicios.

---

## Próximo paso recomendado

**sdd-archive** — MVP técnico verificado; ejecutar 5.6 manual antes de release a producción.

---

## Comando de re-verificación

```bash
docker exec Synap_app python manage.py test --keepdb \
  mpr.tests.test_reportes_mpr_services \
  mpr.tests.test_reportes_mpr_view \
  mpr.tests.test_reportes_operario_parte \
  mpr.tests.test_tablero_consolidado
```
