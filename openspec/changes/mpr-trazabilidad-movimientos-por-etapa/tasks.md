# Tareas: trazabilidad kardex por etapa (pipeline fabricados)

**Change:** `mpr-trazabilidad-movimientos-por-etapa` · **AF:** `docs/mpr/AF_TRAZABILIDAD_MOVIMIENTOS_POR_ETAPA.md` · **Design/spec:** alineados 17/09/2026

## Review Workload Forecast

| Campo | Valor |
|-------|-------|
| Líneas estimadas (autoría) | ~400–900 |
| Riesgo presupuesto 400 líneas | Alto |
| PR encadenados recomendados | Sí |
| Corte sugerido | PR1 backend+tests → PR2 UI+CSV+docs |
| Estrategia de entrega | ask-on-risk |

```text
Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High
```

### Unidades de trabajo sugeridas

| Unidad | Objetivo | PR | Comando test focal | Harness runtime | Límite rollback |
|--------|----------|-----|-------------------|-----------------|-------------------|
| 1 | Contrato backend RF-01–05, RF-10 rama SQL/dedupe | PR1 | `docker exec Synap_app python manage.py test mpr.tests.test_analisis_trazabilidad_articulo mpr.tests.test_paridad_kardex_inventario_etapa` | GET hub kardex componente pipeline (sin UI nueva) | Revertir `mpr/services.py`, `mpr/services_kardex_articulo.py`, tests PR1 |
| 2 | UI/CSV/presentación RF-06/07/09 + docs | PR2 | `docker exec Synap_app python manage.py test mpr.tests.test_kardex_articulo mpr.tests.test_reportes_trazabilidad` | Misma URL + export CSV pipeline vs pack | Revertir template, `export.py`, `reportes_presentacion.py`, `views.py`, docs |

**Antes de apply:** confirmar estrategia de cadena (`stacked-to-main` vs `feature-branch-chain`).

---

## 1. Backend (PR1)

- [x] **1.1** Implementar `get_etapas_pipeline_fabricados_mpr` en `mpr/services.py` (`anulado='No'`, `suma_stock='Si'`, orden Producción → Semi → 2.ª). **Hecho:** lista `[{id_deposito, tipo_mpr, label, orden}]` alineada a `TIPOS_MPR_PIPELINE_FABRICADOS`. **Ref:** RF-05, RF-13, ADR-02.
- [x] **1.2** En `construir_analisis_trazabilidad_articulo` (`mpr/services_kardex_articulo.py`): bifurcar `tipo_eje == "pipeline_fabricados"`; cargar etapas vía 1.1; fallback a `get_depositos_pipeline_fabricados_mpr` + advertencia si `[]`. **Ref:** ADR-02, RF-10.
- [x] **1.3** Añadir parámetro `desglosar_por_deposito: bool = False` a `_consultar_movimientos_kardex_articulo`, `_consultar_movimientos_stock_rem_fa`, `_consultar_movimientos_inventario_mstock`: con `True`, incluir `s.CodDeposito` en SELECT/GROUP BY/ORDER BY y filtrar `IN (dep_ids)`. Con `False`, SQL idéntico al actual. **Ref:** RF-01, RF-10, ADR-01.
- [x] **1.4** Propagar `cod_deposito` en normalizadores (`_normalizar_fila_kardex` y ramas REM/FA/MSTOCK); resolver `etapa`/`etapa_label` con mapa dep→`tipo_mpr`; descartar impacto fuera del mapa + advertencia. **Ref:** RF-01, RF-13, ADR-01.
- [x] **1.5** Implementar `_marcar_transferencias_internas`: mismo `codigo_movimiento`, dos depósitos pipeline → `es_transferencia_interna`, `contraparte`, `orden_impacto` 0 salida / 1 entrada, `es_primer_impacto` solo en el primero. **Ref:** RF-04, ADR-04.
- [x] **1.6** Cambiar `_deduplicar_movimientos`: clave `(codigo_movimiento, cod_deposito)`; orden `(fecha_sort, codigo_movimiento, orden_impacto, orden_etapa, cod_deposito)`; `cod_deposito=None` en ejes legacy. **Ref:** RF-04, ADR-03.
- [x] **1.7** Implementar `_calcular_saldo_corrido_por_etapa`: acumulador por `tipo_mpr`; FA (`afecta_deposito=False`) no altera vector; cada fila `saldos_por_etapa` (3 claves) + `saldo_corrido = sum(...)`. **Ref:** RF-02, RF-03, RF-13, ADR-05, ADR-12 (conteo INV = saldo etapa).
- [x] **1.8** Implementar `_calcular_saldo_inicial_por_etapa`: replay pre-período con misma explosión; fallback `stock_actual[tipo] − neto_periodo[tipo]` por etapa. Extender payload `saldo_inicial.por_etapa`, `deposito.etapas`, `stock.por_etapa`. **Ref:** RF-02, RF-03, ADR-05.
- [x] **1.9** Implementar `_fetch_stock_por_etapa_pipeline` sobre `stock_deposito` (misma regla que `_sql_agg_subquery` inventario); **MUST NOT** llamar `consultar_inventario_tabla` en request. **Ref:** RF-05, RF-11, ADR-06.
- [x] **1.10** Implementar `_conciliar_cierre_por_etapa`: solo si `Hasta >= hoy`; comparar en pares; una advertencia que reemplaza la consolidada y nombra solo etapas con dif; `kpis.conciliacion_estricta`, `conciliacion_por_etapa`. **Ref:** RF-05, ADR-07.
- [x] **1.11** Límite pipeline: multiplicar `limit` por cantidad de etapas (tope 5000); truncado/advertencia por **movimientos distintos**, no por filas. **Ref:** ADR-11.
- [x] **1.12** Mantener camino legacy: `_calcular_saldo_corrido_analisis`, `_proyectar_movimientos_kardex_compat`, `desglosar_por_deposito=False` por defecto en packs y ejes no-pipeline. **Ref:** RF-10, ADR-01, ADR-03.

---

## 2. Tests (PR1 — mayoría; contrato UI/CSV en PR2)

- [x] **2.1** **RED** Dedupe OPP: test en `mpr/tests/test_analisis_trazabilidad_articulo.py` con dos impactos mismo movimiento distinto `cod_deposito`; debe **fallar** con dedupe legacy y pasar tras 1.6. **Ref:** RF-04, ADR-03, riesgo design #1.
- [x] **2.2** Unit SQL: flag off ⇒ sin `CodDeposito` en SQL; flag on ⇒ SELECT/GROUP BY/ORDER BY + params (patrón mocks cursor). **Ref:** RF-01, RF-10, ADR-01.
- [x] **2.3** Unit orden OPP: tras dedupe+sort, salida origen antes que entrada destino; consolidado invariante en transferencia pura. **Ref:** RF-03, RF-04, ADR-04, ADR-05.
- [x] **2.4** Unit invariante `saldo_corrido == sum(saldos_por_etapa)`; FA no mueve etapas; `conteo` fila INV = saldo de su etapa. **Ref:** RF-02, RF-13, ADR-12.
- [x] **2.5** Crear `mpr/tests/test_paridad_kardex_inventario_etapa.py`: cierre 79/28/0/107 con `Hasta >= hoy`; oráculo `consultar_inventario_tabla(ambito=fabricados)` **solo en test**; mocks `stock_deposito` compartidos. **Ref:** RF-05, ADR-06.
- [x] **2.6** Integración: `Hasta < hoy` ⇒ `conciliacion_estricta=False`, sin advertencia descuadre; una etapa desviada ⇒ un solo mensaje nombrando esa etapa. **Ref:** RF-05, ADR-07.
- [x] **2.7** Actualizar `TestComponenteUsaPipelineFabricadosPorDefecto` (patch `get_etapas_pipeline_fabricados_mpr`); mantener test de fallback legacy. **Ref:** riesgo design #7, ADR-02.
- [x] **2.8** Regresión golden: `TestGoldenSampleKardex610Blanco`, `TestArticulo340StockInicialRemSobrante` en `mpr/tests/test_kardex_articulo.py` — **sin editar aserciones/golden**. **Ref:** RF-10, ADR-10.

---

## 3. UI (PR2)

- [x] **3.1** `mpr/templates/mpr/reportes/partials/kardex_articulo.html`: bajo `tipo_eje == "pipeline_fabricados"`, columna **Etapa** (badge) tras Tipo; columnas saldo Producción | Semi | 2.ª | **Consolidado**; **una sola fila** `thead` (sin colspan agrupador). **Ref:** RF-06, RF-09, ADR-08, RF-12.
- [x] **3.2** KPIs cabecera: desglose por etapa + consolidado (saldo inicial/cierre/stock badge) usando payload `por_etapa` / `kpis`. **Ref:** RF-09, ADR-08.
- [x] **3.3** `mpr/views.py`: botón expandir OPA / `subfilas_opa` solo si `es_primer_impacto`; pasar contexto de etapas a template. **Ref:** ADR-04, riesgo design #6.

---

## 4. CSV y presentación (PR2)

- [x] **4.1** `preparar_saldos_etapa_kardex` en `mpr/reportes_presentacion.py` vía `_celda_stock_deposito`; **MUST NOT** ampliar `CAMPOS_CANTIDAD` global. **Ref:** RF-07, ADR-09.
- [x] **4.2** `mpr/export.py` — `analisis_trazabilidad_a_csv`: columnas dinámicas solo pipeline (Etapa, Cód. depósito, saldos por etapa, sección `SALDOS POR ETAPA`); **no** modificar `CSV_COLUMNAS[("trazabilidad","kardex_articulo")]`. **Ref:** RF-07, RF-10, ADR-10.
- [x] **4.3** `mpr/views.py`: pasar `etapas` al export; test CSV pack byte-idéntico vs baseline (sin cambiar golden del pack). **Ref:** RF-10, ADR-10.
- [x] **4.4** Tests contrato: pipeline CSV incluye columnas/sección nuevas; presentación docenas mismo output que `_celda_stock_deposito` para mismo input. **Ref:** RF-07, ADR-09.
- [x] **4.5** Tests UI PR2 en `mpr/tests/test_kardex_articulo.py`: pipeline muestra Etapa + 4 saldos; Terminado **no** muestra columnas nuevas; conteo único botón expandir por movimiento OPA. **Ref:** RF-06, RF-10, ADR-08.

---

## 5. Documentación y verify (PR2 / post-apply)

- [x] **5.1** Cerrar preguntas abiertas 1–5 en `docs/mpr/AF_TRAZABILIDAD_MOVIMIENTOS_POR_ETAPA.md` según ADR/propose (UI columna+KPIs, dos renglones, backend corrido, Terminado oleada 2, conciliación Hasta≥hoy). **Ref:** AF § Preguntas abiertas.
- [x] **5.2** Actualizar `docs/mpr/README.md` (índice / nota contrato `saldos_por_etapa`). **Ref:** política documentación repo.
- [x] **5.3** Verify SDD: ejecutar suite completa design § Plan de pruebas; registrar en `verify-report.md` cuando corresponda fase verify. **Comando:** `docker exec Synap_app python manage.py test mpr.tests.test_analisis_trazabilidad_articulo mpr.tests.test_kardex_articulo mpr.tests.test_paridad_kardex_inventario_etapa mpr.tests.test_reportes_trazabilidad`.

---

## Orden de implementación recomendado

1. PR1: 1.1 → 1.3 → 1.4 → **2.1 RED** → 1.6 → 1.5 → 1.7 → 1.8 → 1.9 → 1.10 → 1.11 → 1.2 wiring → 2.2–2.8.
2. PR2: 4.1 → 3.1–3.3 → 4.2–4.3 → 4.4–4.5 → 5.1–5.2 → 5.3.

**Sin tocar en apply:** `stock/services/inventario_tabla.py` (solo lectura/oráculo tests, RF-11).
