# Tasks: Filtros Punto de venta y Sucursal en informes de ventas

## Review Workload Forecast

| Campo | Valor |
|-------|-------|
| Líneas estimadas cambiadas | 550–650 |
| Riesgo presupuesto 400 líneas | High |
| PRs encadenados recomendados | Yes |
| Split sugerido | PR 1 (O1) → PR 2 (O2.A + O2.B) → PR 3 (O3) → PR 4 (O4) |
| Estrategia de entrega | auto-chain |
| Estrategia de cadena | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Unidades de trabajo sugeridas

| Unidad | Objetivo | PR probable | Comando de test enfocado | Harness runtime | Límite de rollback |
|--------|----------|-------------|--------------------------|-----------------|---------------------|
| 1 | Whitelist PV visible en familia BO (VO/VPV/VPA/VMSA/BOM/VMM): UI + gate JS | PR 1 | `docker exec Synap_app python manage.py test reports.tests.test_filtros_pv_sucursal_ventas.TestOleada1Whitelist` | Abrir `/reports/dashboard/ventas-por-vendedor/` y verificar `id="punto_venta"` presente; `/reports/dashboard/bo-stock-facturacion/` no muestra PV | Revertir templates BO, views.py, dashboard.js; no afecta datos ni otros informes |
| 2 | Filtros en licenciatarios (solo tramo ANET) + clientes sin ventas (UI + SQL) | PR 2 | `docker exec Synap_app python manage.py test reports.tests.test_ventas_mensuales_licenciatarios reports.tests.test_clientes_sin_ventas_relay` | Cargar licenciatarios con `sucursales=[2]`, verificar seed sin filtrar; clientes sin ventas con filtro PV en relay | Revertir servicios y templates; seed y SQL vuelven a comportamiento sin filtro |
| 3 | Relay ventas-netas con listas sucursales/punto_venta + compat escalar | PR 3 | `docker exec Synap_app python manage.py test reports.tests.test_ventas_netas_relay` | Llamar relay con `punto_venta=[10,11]` y verificar SQL IN | Revertir `ventas_netas.py`; relay vuelve a aceptar solo escalar |
| 4 | Ejecutivo + Command Center: PV en KPIs, UI multi-select | PR 4 | `docker exec Synap_app python manage.py test reports.tests.test_executive_summary_contract reports.tests.test_executive_dashboard_contract` | Cargar `/reports/dashboard/command-center-gerencial/` con `punto_venta=[10]`, verificar meta y KPIs | Revertir servicios dashboard, templates ejecutivo/CC, APIs; métricas vuelven a no filtrar PV |

---

## Fase 1: Oleada 1 — Whitelist PV visible en familia BO

- [x] 1.1 **RED**: Test `SLUGS_VENTAS_CON_PUNTO_VENTA` existe en `reports/views.py` y contiene slugs BO de ventas (VO, VPV, VPA, VMSA, BOM, VMM) sin `bo-stock-facturacion` → `reports/tests/test_filtros_pv_sucursal_ventas.py::TestOleada1Whitelist::test_whitelist_slugs_ventas_con_pv_exists`
- [x] 1.2 **GREEN**: Crear `SLUGS_VENTAS_CON_PUNTO_VENTA: frozenset` en `reports/views.py` (línea ~26, patrón `BUILDER_HYBRID_SLUGS`) con slugs de la whitelist diseño (tabla D1)
- [x] 1.3 **RED**: Test `DashboardDetailView` agrega `mostrar_filtro_punto_venta=True` al contexto para slugs en whitelist → `test_dashboard_detail_context_mostrar_pv_true_for_ventas_slugs`
- [x] 1.4 **GREEN**: Extender `DashboardDetailView.get_context_data` (línea ~219) con flag `mostrar_filtro_punto_venta = slug in SLUGS_VENTAS_CON_PUNTO_VENTA`
- [x] 1.5 **RED**: Test template `filters_bo_punto_venta_sucursales_depositos_clientes.html` renderiza `id="punto_venta"` cuando `mostrar_filtro_punto_venta=True` y slug en whitelist → `test_template_bo_muestra_punto_venta_para_ventas_slugs`
- [x] 1.6 **GREEN**: Modificar `reports/templates/reports/includes/filters_bo_punto_venta_sucursales_depositos_clientes.html`: reemplazar condición `{% if report.slug == 'ventas-marcas-mensual' %}` del bloque PV por `{% if mostrar_filtro_punto_venta %}`; agregar hint español "Vacío = todos los puntos de venta"
- [x] 1.7 **RED**: Test negativo `bo-stock-facturacion` no renderiza `id="punto_venta"` → `test_bo_stock_facturacion_no_muestra_punto_venta`
- [x] 1.8 **GREEN**: Verificar que `bo-stock-facturacion` **no** está en `SLUGS_VENTAS_CON_PUNTO_VENTA` (por omisión, no por negación explícita)
- [x] 1.9 **RED**: Test gate JS `loadPuntoVentaOptions` carga PV para slugs de la whitelist sin romper gate `isBoReport` → `test_dashboard_js_gate_punto_venta_ventas_slugs`
- [x] 1.10 **GREEN**: Modificar `reports/static/reports/js/dashboard.js` (línea ~6685): crear `SLUGS_VENTAS_PV` (Set JS con los mismos slugs de la whitelist Python) y gate `loadPuntoVentaOptions = !isBoReport || isVentasMarcasMensualSlug(slug) || SLUGS_VENTAS_PV.has(slug)`
- [x] 1.11 **REFACTOR**: Docs — actualizar `docs/reports/PLAN_FILTROS_PV_SUCURSAL_VENTAS.md` §8.1 (Oleada 1 completa) y `docs/reports/MANUAL_USUARIO_REPORTES.md` con nuevos filtros PV visibles

---

## Fase 2: Oleada 2.A — Ventas mensuales licenciatarios (filtros solo tramo ANET)

- [x] 2.1 **RED**: Test `ventas_mensuales_licenciatarios_query.build_anet_sales_sql` acepta `sucursales` y `puntos_venta` (listas) y genera cláusulas `IN (%s)` con placeholders → `reports/tests/test_ventas_mensuales_licenciatarios.py::test_build_anet_sql_with_sucursales_pv_filters`
- [x] 2.2 **GREEN**: Extender `build_anet_sales_sql(desde, hasta, clientes_excluir, pack_year, sucursales=None, puntos_venta=None)` en `reports/services/ventas_mensuales_licenciatarios_query.py` con cláusulas `cc.CodSucursal IN (%s)` y `cc.id_pv IN (%s)` cuando listas no vacías
- [x] 2.3 **RED**: Test `merge_pack_year` pasa `sucursales` y `puntos_venta` a `fetch_anet_fn` sin filtrar seed → `test_merge_pack_year_filters_only_anet_tramo`
- [x] 2.4 **GREEN**: Modificar `merge_pack_year(..., sucursales, puntos_venta)` en `reports/services/ventas_mensuales_licenciatarios_merger.py` para propagar filtros solo al callback `fetch_anet_fn`, no al seed
- [x] 2.5 **RED**: Test runner parsea `filters.sucursales` / `filters.punto_venta` y agrega `meta.filtros_aplicados_solo_tramo_anet=True` cuando hay selección → `test_runner_licenciatarios_meta_filtros_solo_anet`
- [x] 2.6 **GREEN**: Extender `VentasMensualesLicenciatariosRunner` en `reports/services/ventas_mensuales_licenciatarios_runner.py` con parseo de filtros (normalización `core.utils.administranet_types`), propagación a `merge_pack_year` y meta `filtros_aplicados_solo_tramo_anet`
- [x] 2.7 **RED**: Test template `dashboard_detail.html` incluye `filters_sucursal_punto_venta.html` para slug licenciatarios con flag `ocultar_clientes_excluidos=True` → `test_template_licenciatarios_incluye_filtros_sucursal_pv_sin_duplicar_clientes_excluidos`
- [x] 2.8 **GREEN**: Modificar `reports/templates/reports/dashboard_detail.html` (línea ~393): incluir `filters_sucursal_punto_venta.html` con `{% with ocultar_clientes_excluidos=True %}` tras el bloque pack/período para slug `ventas-mensuales-licenciatarios`
- [x] 2.9 **GREEN**: Modificar `reports/templates/reports/includes/filters_sucursal_punto_venta.html`: envolver bloque "Clientes a excluir" en `{% if not ocultar_clientes_excluidos %}`
- [x] 2.10 **RED**: Test gate JS incluye slug licenciatarios en carga PV y en `collectFilters` → `test_dashboard_js_licenciatarios_envia_filtros_pv`
- [x] 2.11 **GREEN**: Agregar slug `ventas-mensuales-licenciatarios` al gate de `loadPuntoVentaOptions` y a `collectFilters` en `dashboard.js` (línea O2.A del diseño)
- [x] 2.12 **REFACTOR**: Docs — actualizar plan §8.2.A y manual con filtros licenciatarios (solo tramo ANET)

---

## Fase 3: Oleada 2.B — Clientes sin ventas con filtros sucursal/PV

- [x] 3.1 **RED**: Test `get_clientes_sin_ventas` aplica filtros en el `ON` de `LEFT JOIN cc_periodo` y en subconsulta `UltimaCompra` → `reports/tests/test_clientes_sin_ventas_relay.py::test_filtros_en_on_clause_anti_join`
- [x] 3.2 **GREEN**: Extender `get_clientes_sin_ventas(codigo_vendedor, desde, hasta, sucursales=None, puntos_venta=None)` en `reports/services/clientes_sin_ventas.py` con cláusulas en `ON` de `cc_periodo`, en `UltimaCompra` y en `_resumen_por_vendedor` (placeholders `%s`)
- [x] 3.3 **RED**: Test relay acepta query params `sucursales` / `puntoVenta` (repetibles o CSV) y normaliza a listas → `test_relay_clientes_sin_ventas_query_params_normalization`
- [x] 3.4 **GREEN**: Modificar `ClientesSinVentasRelayView` en `reports/clientes_sin_ventas_relay_views.py` para parsear `sucursales` / `puntoVenta` y pasar al servicio
- [x] 3.5 **RED**: Test template `dashboard_clientes_sin_ventas_vendedor.html` muestra tags sucursal/PV junto a período y vendedor → `test_template_clientes_sin_ventas_tags_sucursal_pv`
- [x] 3.6 **GREEN**: Modificar `reports/templates/reports/dashboard_clientes_sin_ventas_vendedor.html` para incluir tags sucursal/PV y envío al relay con los filtros
- [x] 3.7 **RED**: Test cliente con venta en otra sucursal aparece como "sin ventas" al filtrar → `test_cliente_venta_otra_sucursal_sin_ventas_en_filtrada`
- [x] 3.8 **REFACTOR**: Docs — actualizar plan §8.2.B y manual con filtros clientes sin ventas

---

## Fase 4: Oleada 3 — Relay ventas-netas con listas sucursales/punto_venta

- [x] 4.1 **RED**: Test relay acepta `sucursales` y `punto_venta` (listas) en payload → `reports/tests/test_ventas_netas_relay.py::test_relay_acepta_listas_sucursales_pv`
- [x] 4.2 **GREEN**: Extender `get_ventas_netas(..., sucursales=None, punto_venta=None)` en `reports/services/ventas_netas.py` con parámetros explícitos y cláusulas SQL con placeholders
- [x] 4.3 **RED**: Test compat escalar `punto_venta_id` se normaliza a lista `[id]` y se une a `punto_venta` sin duplicar cláusula → `test_relay_compat_escalar_punto_venta_id_to_list`
- [x] 4.4 **GREEN**: Normalizar `punto_venta_id` escalar a lista `[punto_venta_id]` y unir con `punto_venta` en el servicio (deprecado pero aceptado)
- [x] 4.5 **REFACTOR**: Docs — actualizar plan §8.3 con relay ventas-netas y compat escalar

---

## Fase 5: Oleada 4.A — Ejecutivo ventas con filtro PV

- [x] 5.1 **RED**: Test `_cc_scope_sql` acepta `puntos_venta` y genera cláusula `id_pv IN (%s)` → `reports/tests/test_executive_summary_contract.py::test_cc_scope_sql_punto_venta`
- [x] 5.2 **GREEN**: Extender `_cc_scope_sql(scope, puntos_venta=None)` en `reports/services/executive_sales_summary.py` con cláusula PV cuando lista no vacía
- [x] 5.3 **RED**: Test `run_executive_summary` acepta `puntos_venta_filtro` y agrega `meta.punto_venta_filtrados` → `test_executive_summary_meta_punto_venta_filtrados`
- [x] 5.4 **GREEN**: Modificar `run_executive_summary(..., puntos_venta_filtro=None)` para propagar `puntos_venta` a `_cc_scope_sql` y a todos los helpers de series/KPIs/margen; agregar meta
- [x] 5.5 **RED**: Test API parsea query param `punto_venta` (repetible) → `test_executive_summary_api_parse_puntos_venta`
- [x] 5.6 **GREEN**: Crear `_parse_puntos_venta_filtro(qp)` espejo de `_parse_sucursales_filtro` (línea 76) en `reports/executive_summary_api_views.py`
- [x] 5.7 **RED**: Test template ejecutivo muestra tags `punto_venta` junto a `exec_sucursales` → `test_template_executive_summary_tags_punto_venta`
- [x] 5.8 **GREEN**: Modificar `reports/templates/reports/executive_summary.html` (línea ~133) para agregar tags `punto_venta`
- [x] 5.9 **RED**: Test JS carga opciones PV y construye querystring `punto_venta` → `test_executive_summary_js_punto_venta_qs`
- [x] 5.10 **GREEN**: Modificar `reports/static/reports/js/executive_summary.js` (línea ~1099) para carga de opciones PV y `qs.append("punto_venta", id)`
- [x] 5.11 **REFACTOR**: Docs — actualizar plan §8.4.A con ejecutivo ventas + PV

---

## Fase 6: Oleada 4.B — Command Center con multi-select sucursales/PV

- [x] 6.1 **RED**: Test `DashboardFilters` tiene `sucursales_filtro` / `puntos_venta` (tuplas) y `cod_sucursal` es propiedad derivada → `reports/tests/test_executive_dashboard_contract.py::test_dashboard_filters_sucursales_puntos_venta_tuplas`
- [x] 6.2 **GREEN**: Modificar `DashboardFilters` en `reports/services/executive_dashboard/base.py`: agregar `sucursales_filtro` / `puntos_venta` (tuplas); convertir `cod_sucursal` en propiedad derivada (`sucursales_filtro[0]` si exactamente una)
- [x] 6.3 **RED**: Test `resolve_filters_from_query_params` parsea `sucursales` / `puntos_venta` con compat `?sucursal=` → `test_resolve_filters_multi_sucursales_pv_compat_sucursal`
- [x] 6.4 **GREEN**: Extender `resolve_filters_from_query_params` para parsear listas y mantener compat `?sucursal=` (convertir a `sucursales_filtro=[sucursal]`)
- [x] 6.5 **RED**: Test `ventas_metrics` cablea `filters.puntos_venta` en helpers que ya aceptan `puntos_venta` → `test_ventas_metrics_punto_venta_propagation`
- [x] 6.6 **GREEN**: Modificar `reports/services/executive_dashboard/ventas_metrics.py` (líneas 27, 71, 111, 158, 174): propagar `filters.puntos_venta` en helpers y en cláusulas `filters.sucursales`
- [x] 6.7 **RED**: Test template Command Center tiene `<select multiple id="cc-sucursal">` → tags y tags `punto_venta` → `test_template_command_center_multi_select_sucursales_pv`
- [x] 6.8 **GREEN**: Modificar `reports/templates/reports/command_center.html`: reemplazar `#cc-sucursal` (select simple) por tags `sucursales` + tags `punto_venta`
- [x] 6.9 **RED**: Test JS `readFilters` multi, persistencia y querystring con `sucursales` + `punto_venta` → `test_command_center_js_read_filters_multi_sucursales_pv`
- [x] 6.10 **GREEN**: Modificar `reports/static/reports/js/command_center.js`: `readFilters` multi, persistencia, querystring y deep-links a VMM/VO con `sucursales` + `punto_venta`
- [x] 6.11 **REFACTOR**: Docs — actualizar plan §8.4.B con Command Center multi-select

---

## Fase 7: (Opcional) Cascada sucursal→PV en UI

- [x] 7.1 **N/A**: Cascada sucursal→PV no exigida por producto (31/08/2026). Test API omitido.
- [x] 7.2 **N/A**: Sin cambios en `reports/api_views.py` — cascada diferida.
- [x] 7.3 **N/A**: Test JS recarga PV omitido — producto no exigió cascada.
- [x] 7.4 **N/A**: Sin cambios en `dashboard.js` reload PV — cascada diferida.
- [x] 7.5 **N/A**: Docs §8.4.C actualizado — cascada opcional no implementada.

---

## Fase 8: Verificación final y regresión

- [x] 8.1 **TEST**: Regresión — sin selección, totales idénticos por slug (snapshot de `filters` enviados) → `test_regression_no_filters_totals_unchanged`
- [x] 8.2 **TEST**: Regresión — `pedidos-pendientes` y `remitos-no-facturados` sin cambios de payload → `test_regression_pedidos_remitos_sin_filtros_pv`
- [x] 8.3 **TEST**: Test integración — PV recorta KPIs del ejecutivo dentro de clasificadas → `test_integration_executive_pv_within_sucursales`
- [x] 8.4 **TEST**: Test integración — CC acepta `?sucursal=` y `?sucursales=` (compat) → `test_integration_cc_compat_sucursal_sucursales`
- [x] 8.5 **VERIFY**: Ejecutar suite completa de tests con `docker exec Synap_app python manage.py test reports.tests.test_filtros_pv_sucursal_ventas reports.tests.test_ventas_mensuales_licenciatarios reports.tests.test_clientes_sin_ventas_relay reports.tests.test_ventas_netas_relay reports.tests.test_executive_summary_contract reports.tests.test_executive_dashboard_contract`
- [x] 8.6 **VERIFY**: Smoke test manual — cargar cada slug de la whitelist y verificar presencia de `id="punto_venta"`; `bo-stock-facturacion` no lo muestra
- [x] 8.7 **REFACTOR**: Docs — consolidar en `docs/reports/README.md` los cuatro bloques de oleadas completadas

---

## Orden de implementación recomendado

Seguir las fases 1→2→3→4→5→6→(7 opcional)→8 en ese orden estricto. Cada fase corresponde a una unidad de trabajo (PR) de la tabla de forecast.

Las dependencias son:
- Fase 1 (O1) es independiente y puede mergearse primera.
- Fases 2 y 3 (O2.A y O2.B) pueden desarrollarse en paralelo tras O1 pero se agrupan en un solo PR para reducir overhead de review.
- Fase 4 (O3) es independiente de O2 pero comparte patrones de normalización; puede ir en paralelo conceptualmente pero conviene mergearse tras O2 para acumular aprendizajes.
- Fases 5 y 6 (O4.A y O4.B) comparten la extensión de `DashboardFilters` y `_cc_scope_sql`; se desarrollan secuencialmente dentro del mismo PR.
- Fase 7 (cascada) es opcional y no bloqueante; solo se ejecuta si producto la exige antes de O4 o en follow-up.

Cada PR debe incluir su fase de docs (REFACTOR) antes de merge.

---

## Key Learnings

1. La whitelist de slugs de ventas con PV visible es la única fuente de verdad para controlar visibilidad y gate JS.
2. El include BO se gatea con flag de contexto Python (`mostrar_filtro_punto_venta`) para evitar lógica de template frágil.
3. Los filtros de licenciatarios se aplican solo al tramo ANET post-cutover; el seed pre-cutover no tiene columnas de sucursal/PV y filtrarlo inventaría datos.
4. El anti-join de clientes sin ventas exige que los filtros se agreguen al `ON` del `LEFT JOIN`, no al `WHERE`, para preservar la semántica de "sin ventas".
5. La cascada sucursal→PV (Fase 7) es opcional y se implementa solo si producto la exige; no es bloqueante para las otras oleadas.
