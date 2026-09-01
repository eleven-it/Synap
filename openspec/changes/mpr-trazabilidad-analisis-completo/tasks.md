# Tasks: Trazabilidad artículo — análisis completo

**Change:** `mpr-trazabilidad-analisis-completo` | **TDD:** estricto | **Entrega:** 3 PRs encadenados

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 800–1200 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR1 collector → PR2 UI → PR3 export+timeline+docs |
| Delivery strategy | ask-on-risk |
| Chain strategy | feature-branch-chain |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Servicio análisis + collector + tests | PR1 | `docker exec Synap_app python manage.py test mpr.tests.test_analisis_trazabilidad_articulo` | Pack 610 jul–sep/2026 vía shell servicio | Revertir `services_kardex_articulo.py`, `services.py`, tests nuevos |
| 2 | UI bloques kardex + KPI strip | PR2 | `docker exec Synap_app python manage.py test mpr.tests.test_kardex_articulo` | GET hub `kardex_articulo?id_articulo=1398` manual | Revertir templates + rama `views.py` kardex |
| 3 | CSV + timeline wrapper + docs | PR3 | `docker exec Synap_app python manage.py test mpr.tests.test_reportes_trazabilidad` | Export CSV + deep-link `#timeline` manual | Revertir `reportes_hub.py`, timeline partial, docs |

### Criterios aceptación (plan §6) → fase

| # | Criterio | Fase verificación |
|---|----------|-------------------|
| CA-1 | Pack 610: ≥4 OPA 42/68/30/120, saldo corrido coherente | PR1 tests + PR2 manual |
| CA-2 | REM/FA/inventario etiquetados en período | PR1 tests + PR2 UI |
| CA-3 | Pedido = paridad tablero Pack | PR1 tests demanda/brecha |
| CA-4 | PED Urgente con Terminado negativo visible | PR1 fórmulas + PR2 STOCK/BRECHA |
| CA-5 | BOM 3 componentes + link kardex componente | PR2 BOM partial |
| CA-6 | Tests unitarios collector + fórmulas | PR1 |
| CA-7 | Docs REPORTES_MPR + TRAZABILIDAD_ARTICULO | PR3 |
| CA-8 | UI español, dd/MM/yyyy, sin alert/confirm | PR2 + PR3 |

---

## Phase 1: PR1 — Servicio y collector (sin UI grande)

- [x] 1.1 RED: crear `mpr/tests/test_analisis_trazabilidad_articulo.py` con fixtures mock — clasificación REM/FA/INV, FA excluido saldo, dedupe OPP, saldo inicial, fórmulas brecha (REQ-ANAL-08/09/10, CA-1/2/3/4/6)
- [x] 1.2 GREEN: `listar_demanda_ped_por_articulo` en `mpr/services.py` — wrapper `_listar_demanda_ped_vivo_fifo` por `id_articulo` (REQ-ANAL-04)
- [x] 1.3 GREEN: `_consultar_movimientos_stock_rem_fa` en `mpr/services_kardex_articulo.py` — query `stock` `Comprobante IN ('REM','FA')` (REQ-ANAL-08)
- [x] 1.4 GREEN: `_consultar_movimientos_inventario_mstock` — motivo faltante/sobrante/inventario + `TipoComp` (REQ-ANAL-10)
- [x] 1.5 GREEN: `_consultar_eventos_mpr_articulo` — extraer ledgers timeline existente (REQ-ANAL-08)
- [x] 1.6 GREEN: `_clasificar_movimiento_analisis` + `_afecta_deposito_terminado` — extiende kardex → `opa|opp|rem|fa|inventario|mpr_*` (REQ-ANAL-08/10)
- [x] 1.7 GREEN: `_deduplicar_movimientos` — clave `codigo_movimiento`; preferir MSTOCK sobre `mpr_parte` (REQ-ANAL-08)
- [x] 1.8 GREEN: `_calcular_saldo_inicial_terminado` — stock real al inicio `desde`; flag `calculado_ok` (REQ-ANAL-09)
- [x] 1.9 GREEN: `_unificar_y_saldo_corrido` — merge cronológico + `_calcular_saldo_corrido_movimientos`; FA sin efecto excluido del acumulado (REQ-ANAL-09/10)
- [x] 1.10 GREEN: bloques `demanda_ped`, `stock`, `brechas`, `a_producir` — fórmulas tablero pack vía `_ventana_pack_stock_maps` (REQ-ANAL-05/06/11)
- [x] 1.11 GREEN: `construir_analisis_trazabilidad_articulo` — orquesta identidad, BOM, bloques y movimientos; payload según design (REQ-ANAL-01)
- [x] 1.12 GREEN: `construir_kardex_articulo` — wrapper delgado delegando análisis; proyección compat backward (REQ-ANAL-01)
- [x] 1.13 REFACTOR: RED→GREEN tests `mpr/tests/test_kardex_articulo.py` — wrapper no rompe contrato existente
- [x] 1.14 Verificar CA-3/4/6: suite PR1 verde; anotar IDs fixture pack 610 para PR2 manual

---

## Phase 2: PR2 — UI bloques kardex

- [x] 2.1 RED: test integración vista `kardex_articulo` — payload incluye claves `demanda_ped`, `stock`, `brechas`, `movimientos`, `kpis` (REQ-ANAL-01/13)
- [x] 2.2 GREEN: `mpr/views.py` rama `kardex_articulo` — llama `construir_analisis_trazabilidad_articulo`; pasa bloques en `meta` + `filas=movimientos`
- [x] 2.3 GREEN: crear `_bloque_demanda_ped.html` — tabla PED, totales P_ped, fechas dd/MM/yyyy (REQ-ANAL-04)
- [x] 2.4 GREEN: crear `_bloque_stock_brecha.html` — Terminado negativo alerta, texto explicativo brecha (REQ-ANAL-05/06, CA-4)
- [x] 2.5 GREEN: crear `_bloque_a_producir.html` — TOT Urgente, capacidad Semi, alerta Semi=0 (REQ-ANAL-11)
- [x] 2.6 GREEN: modificar `_kpi_strip.html` — Pedido, Terminado (rojo si <0), PED Urgente, TOT Urgente (REQ-ANAL-06)
- [x] 2.7 GREEN: modificar `kardex_articulo.html` — cabecera pack/componente, orden bloques design, badges movimientos, columna «Afecta depósito», subfilas OPA expandibles, ancla `#timeline` (REQ-ANAL-03/07/08/13, CA-8)
- [x] 2.8 GREEN: BOM links → `kardex_articulo` del componente (no timeline) (REQ-ANAL-07, CA-5)
- [x] 2.9 Manual CA-1/2/5: pack 610 jul–sep/2026 — ≥4 OPA, REM/FA/INV visibles, 3 componentes BOM

---

## Phase 3: PR3 — Export, timeline thin wrapper y docs

- [x] 3.1 RED: test timeline delegación — `timeline` usa mismo servicio; no consultas paralelas (REQ-TRAZ-06, REQ-TRAZ-02)
- [x] 3.2 RED: test deep-link — params `id_articulo`, `desde`, `hasta` preservados en enlace kardex `#timeline` (REQ-TRAZ-06)
- [x] 3.3 GREEN: `mpr/views.py` rama `timeline` — payload unificado; `eventos=meta.eventos_mpr` (REQ-TRAZ-01/02)
- [x] 3.4 GREEN: `trazabilidad_timeline.html` — banner + botón GET kardex con params; scroll JS a `#timeline` (REQ-TRAZ-03/06, CA-8)
- [x] 3.5 GREEN: `mpr/reportes_hub.py` — label «Análisis trazabilidad»; columnas CSV multi-sección UTF-8 BOM español (REQ-ANAL-12, CA-7 parcial)
- [x] 3.6 GREEN: export CSV vía hub — consume `construir_analisis_trazabilidad_articulo` sin recomputar (REQ-ANAL-01/12)
- [x] 3.7 REFACTOR: `mpr/tests/test_reportes_trazabilidad.py` — REQ-TRAZ-04/05 preservados tras delegación
- [x] 3.8 Docs: actualizar `docs/mpr/REPORTES_MPR.md` — informe unificado kardex (CA-7)
- [x] 3.9 Docs: crear `docs/mpr/TRAZABILIDAD_ARTICULO.md` — reglas FA/saldo, bloques, export (CA-7)
- [x] 3.10 Manual CA-7/8: export CSV bloques + timeline deep-link; confirmar sin `alert`/`confirm`

---

## Phase 4: Verificación final (post-PR3)

- [x] 4.1 Ejecutar suite completa: `docker exec Synap_app python manage.py test mpr.tests.test_analisis_trazabilidad_articulo mpr.tests.test_kardex_articulo mpr.tests.test_reportes_trazabilidad` (CA-6)
- [x] 4.2 Checklist CA-1…CA-8 contra plan §6; registrar evidencia manual pack 610 en verify-report
