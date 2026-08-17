# SPEC — Informe Ventas Mensuales Licenciatarios

**Slug:** `ventas-mensuales-licenciatarios`  
**Nombre:** Ventas Mensuales Licenciatarios  
**Plan:** [PLAN_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md](PLAN_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md)  
**Análisis plantilla:** [ANALISIS_MONTHLY_REPORTING_BEST_SOX_LICENCIATARIOS.md](ANALISIS_MONTHLY_REPORTING_BEST_SOX_LICENCIATARIOS.md)  
**Hermano:** `ventas-marcas-mensual`  
**Manual de usuario:** [MANUAL_USUARIO_REPORTES.md](MANUAL_USUARIO_REPORTES.md) (§3 Ventas Mensuales Licenciatarios).

---

## 1. Propósito

Generar y (más adelante) previsualizar el **pack Monthly Reporting** que Best Sox envía a licenciatarios (Levi’s, Puma, LW), con continuidad YTD tras el cutover BEST→AdministraNET (22/07/2026).

---

## 2. Contrato de producto

### 2.1 Entradas (MVP fase 0–2)

| Entrada | Tipo | Notas |
|---------|------|--------|
| `pack_id` | select | Ver plan §4 |
| Período facturación | fechas | Año calendario del pack (ej. 2026) |
| Seed | import Excel | Solo staff/ops; versionado |
| Filtros ANET | según pack | Marca / SuperArt / U.M. |

### 2.2 Salidas

| Salida | Descripción |
|--------|-------------|
| Excel | Plantilla `input Licensee sales` + `monthly` (+ hojas extra si pack) + hoja QA |
| Dashboard | Datos agregados pack×cliente×mes + panel pendientes match / SuperArt |
| Meta | `pack_id`, cutover, tramos seed/anet, clientes pendientes |

### 2.3 Reglas de datos (obligatorias)

1. **ene–jun:** solo seed (congelado).  
2. **01–21/07:** solo seed julio (0 si aún no cargado).  
3. **22/07+:** solo AdministraNET.  
4. **julio_total** = seed(01–21) + ANET(22–31).  
5. Royalty = Sales × tasa del pack (Levi’s 20 %, LW/Puma 13 % salvo config).  
6. **Amounts ANET (22/07+):** mismo motor que VMM — `signo × PrecioNetoxR × (SubtotalDesc/SubTotal1)` (descuento al pie de factura). El seed ene–jun / jul 1–21 **no** se recalcula (congelado tal como se envió).
7. **Match cliente seed→ANET:** el vínculo auditable (`MonthlyReportingClientMatch`) es propio de este informe (híbrido). Los mapeos confirmados de negocio (Libro1, 17/08/2026) aplican aquí — ver [MAPEO_CLIENTES_LICENCIATARIOS_SEED_ANET.md](MAPEO_CLIENTES_LICENCIATARIOS_SEED_ANET.md). Pendientes visibles en el panel hasta vincular.
8. **Artículos de venta (tramo ANET):** se excluye `articulo.tipo_art = 'Gasto'` (misma cláusula que VMM). Ver [FILTRO_TIPO_ART_GASTO.md](FILTRO_TIPO_ART_GASTO.md).

---

## 3. Formato Excel

MUST seguir tipografía, number formats, merges y fills documentados en el análisis §3 (familia Levi’s/LW primero; Puma fase 3).

Hoja `input Licensee sales` (Levi’s / LW): encabezados en inglés `Customer`, `City / Province`, `Store Type`, `Product group`; meses ene–dic desde columna E; `units`/`amounts` en fila 3; **totales en fila 2** (`=SUM(E5:E4931)` …) para que `monthly` enlace `='input Licensee sales'!E2`. City / Store Type / Product group salen del seed (y del match si el cliente es ANET). MUST NOT volcar bloques en español sobre `monthly`.

MUST NOT reutilizar el layout Matriz/Detalle de VMM como entregable a marcas.

---

## 4. Integración Synap

| Pieza | Ubicación |
|-------|-----------|
| Seed catálogo | `reports/services/ventas_mensuales_licenciatarios_seed.py` |
| Runner híbrido | `reports/services/ventas_mensuales_licenciatarios_runner.py` |
| Query wire | `reports/services/query_runner.py` slug `ventas-mensuales-licenciatarios` |
| Import seed | `reports/management/commands/import_monthly_reporting_seed.py` |
| Conciliación seed | `reports/management/commands/reconcile_monthly_reporting_seed.py` |
| Merger / export | `ventas_mensuales_licenciatarios_{merger,export}.py` |
| API match cliente | `reports/ventas_mensuales_licenciatarios_api_views.py` |
| Modelos seed | `reports/models.py` (`MonthlyReporting*`) |

UI canónica: patrones reports/MPR ([FUENTE_VERDAD_UI](../general/FUENTE_VERDAD_UI_REPORTES_MPR.md)). Diálogos: modales Synap, sin `alert` nativo.

Layout del dashboard: la barra de navegación, el banner del informe y el resumen quedan fijos; el único scroll vertical es la matriz cliente × mes (`#vml-matriz-container`). El thead y la columna Cliente permanecen sticky dentro de esa región.

Export Excel: el botón **Exportar Excel** del banner (junto a Actualizar) dispara `/api/reports/export/?type=xlsx` con `pack_id` y el rango calendario. Requiere pack seleccionado. El export vuelve a ejecutar el runner (sin caché) y toma `merge_result` desde `QueryResult.artifacts` (no desde `meta.extra`, que es solo JSON).

---

## 5. Escenarios de aceptación

- **L0:** Dado migrate/seed, cuando se abre `/reports/dashboard/ventas-mensuales-licenciatarios/`, entonces existe el informe y la query responde 200 con nota de construcción.  
- **L1:** Dado Excel jun importado, cuando se lista seed, entonces hay filas ene–jun por cliente del pack.  
- **L2:** Dado cutover, cuando se exporta YTD ago, entonces jul combina seed+ANET y ago es solo ANET.  
- **L3:** Dado pack `levis_bw`, cuando se exporta, entonces `monthly!C7` = 20 % y royalty = sales × 0,2.  
- **L4:** Dado reimport del mismo archivo, entonces no hay filas duplicadas (upsert).  
- **L5:** Dado seed importado, cuando se ejecuta conciliación dry-run vs planilla fuente, entonces totales pack×cliente×mes coinciden (ene–jun).  
- **L6:** Dado rango 01/10/2025–15/02/2026, cuando se ejecuta el informe, entonces se rechaza (mismo año calendario obligatorio).  
- **L7:** Dado un renglón ANET de una FA con dto pie 15 %, cuando se agrega `amount`, entonces es `PrecioNetoxR × 0,85` (misma expr que VMM); el seed histórico no se multiplica.
- **L8:** Dado seed con «ML FULL» (u otro de [MAPEO clientes](MAPEO_CLIENTES_LICENCIATARIOS_SEED_ANET.md) §1), cuando se aplica el match confirmado, entonces `anet_cliente_id` queda el código ANET documentado y el cliente sale del panel de pendientes.

Ver evidencia en [VERIFY_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md](VERIFY_INFORME_VENTAS_MENSUALES_LICENCIATARIOS.md).

---

## 6. Estado

| Ítem | Estado |
|------|--------|
| Decisión hermano de VMM | Hecho (07/08/2026) |
| PLAN + SPEC + VERIFY | Hecho (08/08/2026) |
| Modelos seed + importer idempotente | Hecho |
| Merger cutover 21/22 + export plantilla | Hecho |
| UI canónica + API match + modal Synap | Hecho |
| Matriz cliente × mes en dashboard | Hecho (17/08/2026) |
| Chrome fijo + scroll solo en matriz | Hecho (17/08/2026) |
| Botón Exportar Excel en banner | Hecho (17/08/2026) |
| Conciliación 6 planillas (dry-run) | Hecho |
| Mapeo clientes Libro1 → ANET (15/15) | Cerrado 17/08/2026; aplicados en Postgres (`matched`) |
| Planillas actualizadas (seed jul 1–21) | Importadas 17/08/2026 desde `Best Sox/Julio/reportesjul` (ene–jul en seed) |
