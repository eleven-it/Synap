# Informe de verificación — dashboard-gerencial-endpoints-legacy

**Change:** dashboard-gerencial-endpoints-legacy  
**Versión de contrato:** executive-dashboard-v1  
**Modo:** Standard (strict_tdd no activo)  
**Almacén:** hybrid (openspec + Engram)  
**Fecha verificación:** 14/07/2026

---

## Veredicto

**PASS WITH WARNINGS** — Implementación completa según tareas (16/16, incl. T13); tests ejecutados OK; `manage.py check` sin issues. Migración catálogo `0032_add_command_center_gerencial_report` aplicada (14/07/2026). Quedan huecos en pruebas HTTP (403/503) y MprSchemaError sin test runtime.

---

## Completitud de tareas

| Métrica | Valor |
|--------|-------|
| Tareas totales | 16 |
| Tareas completadas | 16 |
| Tareas incompletas | 0 |

Todas las tareas en `tasks.md` están marcadas `[x]`, incluida **T13** (delegación `query_runner` → `ventas_metrics`).

---

## Ejecución de build y tests

**Build / system check:** ✅ OK

```text
docker exec Synap_app python manage.py check
→ System check identified no issues (0 silenced).
```

**Tests solicitados:** ✅ 25 passed

```text
docker exec Synap_app python manage.py test \
  reports.tests.test_query_runner_ventas_delegation \
  reports.tests.test_executive_dashboard_contract \
  --keepdb
→ Ran 25 tests in 0.015s — OK
```

**Tests relacionados adicionales:** ✅ 8 passed

```text
docker exec Synap_app python manage.py test reports.tests.test_report_visibility --keepdb
→ Ran 8 tests in 0.002s — OK
(incluye command_center_visible_for_user)
```

**Total ejecutado:** 33 tests, 0 fallos, 0 omitidos.

**Cobertura:** ➖ No configurada en `openspec/config.yaml` para este change.

---

## Matriz de cumplimiento de escenarios (spec)

| Requisito / escenario | Test | Resultado |
|----------------------|------|-----------|
| Esc.1 — Orquestador 200, `meta.definicion`, áreas sin CRM | `test_executive_dashboard_contract > test_run_command_center_estructura` | ✅ COMPLIANT |
| Esc.2 — Ventas resumen con sucursal y montos ≥ 0 | `test_fetch_ventas_resumen_estructura` | ⚠️ PARTIAL (estructura; sin assert `cod_sucursal_filtro=3`) |
| Esc.3 — Usuario sin permiso gerencial → 403 | `test_report_visibility > command_center_visible_for_user` | ⚠️ PARTIAL (visibilidad servicio; sin APIClient 403) |
| Esc.4 — MySQL no disponible → 503 inventario | (ninguno HTTP) | ⚠️ PARTIAL (`_legacy_error_response` en vistas; sin test API) |
| Esc.5 — Esquema MPR incompleto → 200 `disponible=false` | (ninguno) | ❌ UNTESTED (implementado en `manufacturing_metrics.py`) |
| Esc.6 — `fecha_inicio` > `fecha_fin` → 400 | `test_resolve_filters_fechas_invertidas` | ✅ COMPLIANT (capa filtros; API reutiliza mismo resolver) |
| Esc.7 — P1 pedidos pendientes paginado | `test_list_pedidos_pendientes_paginado` | ✅ COMPLIANT |
| T13 — Delegación query_runner ventas | `test_query_runner_ventas_delegation` (3 tests) | ✅ COMPLIANT |

**Resumen escenarios:** 4/7 compliant en runtime; 2 partial; 1 untested.

---

## Correctitud (evidencia estática)

| Requisito | Estado | Notas |
|-----------|--------|-------|
| REQ-ED-SEC-01 — Auth + ManagerialReportsPermission | ✅ | `ExecutiveDashboardMixin.permission_classes` |
| REQ-ED-SEC-01 — 400 sin base_empresa | ✅ | `_filters_or_error` en `executive_dashboard_api_views.py` |
| REQ-ED-SEC-02 — Solo lectura | ✅ | Servicios `fetch_*` / `list_*` solo SELECT |
| REQ-ED-FILT-01 — Parámetros comunes | ✅ | `resolve_filters_from_query_params` en `base.py` |
| REQ-ED-META-01 — Metadatos obligatorios | ✅ | `build_meta`, tests contrato |
| REQ-ED-ERR-01 — Errores legacy 503/400 | ✅ | Vistas + `LegacyReadError` / `InvalidDashboardFilters` |
| REQ-ED-TYPE-01 — administranet_types | ✅ | Uso en métricas (p. ej. `round_money`, normalización) |
| REQ-ED-ORCH-01–04 — Orquestador | ✅ | `command_center.py`, URLs en `api_urls.py` |
| REQ-ED-ORCH-02 — Sin CRM | ✅ | `test_run_command_center_estructura` assert `crm` ausente |
| REQ-ED-VEN-* — Ventas P0/P1 | ✅ | `ventas_metrics.py` + vistas + tests paginación |
| REQ-ED-INV-* — Inventario P0/P1 | ✅ | `inventory_metrics.py` + tests |
| REQ-ED-COMP-* — Compras | ✅ | `purchase_metrics.py` + test estructura |
| REQ-ED-MFG-* — Manufactura | ✅ | `manufacturing_metrics.py` + captura `MprSchemaError` |
| REQ-ED-CRUZ-* — Cruzados P0/P1 | ✅ | `cross_metrics.py` + tests |
| CRM deprecado | ✅ | Sin `areas.crm` en orquestador |
| UI Command Center (T-UI*) | ✅ | `command_center.html`, `command_center.js`, slug en `views.py` |
| T13 refactor query_runner | ✅ | Delegación verificada en código y tests |

**Expansiones respecto al spec original v1:**

- Áreas adicionales **tesorería** y **ventas_cobros** (evolución post-spec).
- Spec original indicaba «Sin UI»; la entrega incluye UI Command Center (alineado a `tasks.md`).

---

## Coherencia con diseño

| Decisión | ¿Seguida? | Notas |
|----------|-----------|-------|
| Namespace `/api/reports/executive-dashboard/` | ✅ | `api_urls.py` |
| Extracción incremental (copiar SQL, no romper query_runner) | ✅ | Módulo `executive_dashboard/`; T13 delega sin duplicar |
| Orquestador modo degradado | ✅ | `_safe_legacy_area`, test aislamiento tesorería |
| Ventas crítica → 503 orquestador completo | ⚠️ | Diseño documenta 503; implementación degrada ventas como otras áreas |
| Manufactura vía `mpr.services` | ✅ | `manufacturing_metrics.py` |
| Compras desde subconsulta OC BO | ✅ | SQL con filtro fecha en test compras |
| P1 detalle paginado | ✅ | Tests pedidos, remitos, backorder, existencias |
| Migración catálogo 0032 | ✅ | `reports/migrations/0032_add_command_center_gerencial_report.py` aplicada |
| `test_executive_dashboard_api.py` | ⚠️ | Opcional en design; no creado |

---

## Issues encontrados

### CRITICAL (bloquean archive)

Ninguno.

### WARNING (convendría corregir)

1. **Escenario 5 sin test:** `MprSchemaError` → `disponible=false` no cubierto en runtime.
2. **Escenarios 3–4 sin tests HTTP:** Permisos 403 y 503 por endpoint de área no probados con `APIClient`.
3. **Desviación diseño ventas 503:** Fallo transitorio en ventas no eleva 503 al orquestador (solo degradación por área).
4. **Spec vs entrega:** Áreas tesorería/ventas_cobros no estaban en spec v1 original (documentar en archive si procede).

### SUGGESTION

1. Añadir `test_executive_dashboard_api.py` mínimo (400, 403, 503 mock).
2. Test unitario `fetch_manufactura_resumen` con `MprSchemaError` mockeado.
3. Assert explícito `meta.cod_sucursal_filtro` con `sucursal=3`.

---

## Artefactos revisados

- `openspec/changes/dashboard-gerencial-endpoints-legacy/specs/reports-executive-dashboard/spec.md`
- `openspec/changes/dashboard-gerencial-endpoints-legacy/design.md`
- `openspec/changes/dashboard-gerencial-endpoints-legacy/tasks.md`
- `openspec/changes/dashboard-gerencial-endpoints-legacy/proposal.md`
- Implementación: `reports/services/executive_dashboard/*`, `reports/executive_dashboard_api_views.py`, `reports/api_urls.py`
- Documentación: `docs/reports/EXECUTIVE_DASHBOARD_API.md`

---

## Recomendación siguiente fase

**sdd-archive** — El change cumple funcionalmente con warnings no bloqueantes. Opcional: crear migración 0032 y tests API antes del archive si producto exige paridad despliegue.
