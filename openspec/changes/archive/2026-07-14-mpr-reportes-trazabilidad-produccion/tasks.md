# Tasks: Reportes MPR — trazabilidad y producción visual

**Change:** `mpr-reportes-trazabilidad-produccion`  
**Design:** [design.md](./design.md)

---

## Phase 1: Foundation — Shell y periodo

- [x] 1.1 Crear `mpr/export.py` con `filas_a_csv(filas, columnas) -> bytes` UTF-8 BOM
- [x] 1.2 Añadir en `mpr/views.py` helpers via `mpr/reportes_hub.py`: periodo, grupo, LEGACY_TIPO_MAP
- [x] 1.3 Refactor `ReportesMPRView.get_context_data` — dispatch por `grupo`/`reporte`; default `produccion/resumen_diario`
- [x] 1.4 Implementar respuesta CSV en `ReportesMPRView.get` cuando `format=csv`
- [x] 1.5 Crear templates shell: `_shell_header`, `_filtros`, `_nav_grupos`, `_kpi_strip`
- [x] 1.6 Alpine `mprReportesHub()` inline en `reportes.html`
- [x] 1.7 Actualizar `mpr/templates/mpr/reportes.html` hub completo
- [x] 1.8 Test `mpr/tests/test_reportes_shell_legacy_map.py`

---

## Phase 2: Servicios agregación P0

- [x] 2.1 Implementar `reporte_mpr_resumen_diario` en `mpr/services.py`
- [x] 2.2 Implementar `reporte_mpr_operario_parte` en `mpr/services.py`
- [x] 2.3 Implementar `reporte_mpr_cadena_pipeline` en `mpr/services.py`
- [x] 2.4 Implementar `reporte_mpr_trazabilidad_componente` en `mpr/services.py`
- [x] 2.5 Refactor `reporte_mpr_brecha_demanda` → `listar_demanda_pack_desde_pedidos`
- [x] 2.6 Test `mpr/tests/test_reportes_resumen_diario.py`
- [x] 2.7 Test `mpr/tests/test_reportes_operario_parte.py`
- [x] 2.8 Test `mpr/tests/test_reportes_cadena_pipeline.py`

---

## Phase 3: Partials UI P0

- [x] 3.1 Partial `partials/resumen_diario.html`
- [x] 3.2 Partial `partials/operario.html`
- [x] 3.3 Partial `partials/cadena_pipeline.html`
- [x] 3.4 Partial `partials/pendiente_componentes.html`
- [x] 3.5 Partial `partials/brecha_pack.html`
- [x] 3.6 Partial `partials/trazabilidad_timeline.html`
- [x] 3.7 Partials demanda/trazabilidad (sin legacy OPT)
- [x] 3.8 Partial `partials/empty_state.html`
- [x] 3.9 Wire KPI strip por reporte en view context `kpis` dict

---

## Phase 4: Integración legacy + demanda auxiliar

- [x] 4.1 Partials `stock.html`, `bajo_minimo.html` bajo grupo Demanda
- [x] 4.2 Conectar `reporte_mpr_pedidos_por_estado` UI
- [x] 4.3 Conectar `reporte_mpr_movimientos` UI bajo Trazabilidad
- [x] 4.4 Actualizar `mpr/tests/test_reportes_mpr_view.py`
- [x] 4.5 Actualizar tests brecha PED en `test_reportes_mpr_services.py` (integración MySQL)

---

## Phase 5: Documentación y verificación

- [x] 5.1 Crear `docs/mpr/REPORTES_MPR.md`
- [x] 5.2 Actualizar `docs/mpr/NAVIGACION_MPR_ETAPA11.md`
- [x] 5.3 Actualizar `docs/reports/mpr/ESPEC_MPR_PRODUCCION_OPERARIO.md`
- [x] 5.4 Actualizar `docs/reports/mpr/ESPEC_MPR_BRECHA_DEMANDA.md`
- [x] 5.5 Test integración `mpr/tests/test_reportes_trazabilidad.py`
- [ ] 5.6 Verificación manual en administranet96

---

## Phase 6: P1 (post-MVP, opcional)

- [ ] 6.1 Reporte eficiencia clasificación (scrap % por componente)
- [ ] 6.2 WIP pipeline snapshot sin OPT
- [ ] 6.3 Drill-down operario → componentes
- [ ] 6.4 Sparkline tendencia en resumen diario
