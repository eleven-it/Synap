# Plan — Extensión reporte «Por operario / tejedor» + continuidad histórica BEST

**Fecha:** 08/07/2026
**Estado:** Propuesta para revisión (sin implementación de código todavía)
**Alcance:** (1) Extender el reporte **Producción › Por operario** de Synap MPR replicando lo relevante de las hojas `Produccion x Tejedor` y `Segunda x Tejedor` del Excel de fábrica; (2) preservar las **estadísticas históricas** que hoy viven en el sistema **BEST** (Azure SQL, solo lectura) cuando se haga el corte «off BEST / on Synap MPR», mostrando la **fuente** con un indicador sutil en la UI.

**Documentos que complementa / referencia:**
- `docs/mpr/BEST_SOX_GAP_PROCESOS_Y_CALCULOS.md` (catálogo Excel → MPR, mapeo etapas, roles Tejedor/Responsable)
- `docs/mpr/PROPUESTA_MIGRACION_PEDIDOS_BEST_A_MPR_CUTOVER.md` (corte de **demanda/pedidos**; este plan es su hermano para **reporting/analytics**)
- `docs/mpr/BEST_SOX_PCP_PRODUCCION_ALINEACION.md` (unidad = par; docena = 12 pares)
- `docs/mpr/REPORTES_MPR.md` (hub de reportes MPR)

> **Nota de dominio:** en Best Sox **1 unidad = 1 par**, **1 docena = 12 pares**. Todo este plan razona en pares (base) con presentación docenas/pares ya existente.

---

## 1. Contexto y estado actual

El reporte **Por operario** (`reporte_mpr_operario_parte`, `mpr/services.py`) ya entrega por operario y período: `unidades` (parte), `semi`, `segunda`, `scrap`, `pct_apto`, `pct_scrap`, ranking y KPIs. La data cruda nativa está en `mpr_parte_linea` (producción) y `mpr_transicion_lote` (clasificación 2da/semi/scrap), atribuida al **operario fabricante** (`id_operario`).

Las dos hojas BEST analizadas son **tablas dinámicas** con grano `Año/Mes × Tejedor` y valor en **docenas**:
- `Produccion x Tejedor`: docenas producidas por tejedor y mes (filtro `Origen = Producción`).
- `Segunda x Tejedor`: docenas de 2da por tejedor y mes + matriz de **ratio `Segunda / Producción`** por tejedor (KPI de calidad; `eserror` = mes sin producción).

**Gap principal frente a BEST:** falta el **KPI `% 2da`** explícito y la **dimensión temporal** (evolución mensual por tejedor). La data cruda ya existe en Synap para el período nativo; la histórica (pre-corte) vive en BEST.

---

## 2. Fase A — Quick wins sobre el reporte actual (sin datos nuevos)

Misma consulta/base; solo cálculo y presentación.

- **`% 2da`** = `segunda / producción` por operario (KPI de calidad central de BEST). Nueva columna + orden.
- **`% 1ra` (índice de calidad)** = `1 − (segunda + scrap) / producción`.
- **Costo de no-calidad** = `segunda + scrap` (pares/docenas) y su % del total de planta.
- **Delta vs promedio de planta** con semáforo (verde/ámbar/rojo) en `%2da` y productividad.
- **Pareto**: % de operarios que concentran 80% de producción y 80% de 2da.
- Manejo de `—` (N/A) cuando producción = 0 (evitar dividir por cero, como `eserror` en BEST).

**Esfuerzo:** bajo. **Riesgo:** bajo. **Datos nuevos:** no.

---

## 3. Fase B — Dimensión temporal nativa (Tejedor × Mes)

- **Heatmap Tejedor × Mes** de producción (docenas) y de `%2da`.
- **Tendencia (línea)** por operario: producción y `%2da` mes a mes.
- **Color fijo por operario** (identidad visual estable en todos los gráficos, como la leyenda color↔tejedor de BEST).
- Agrupación por `MONTH(p.fecha_produccion)` sobre las mismas tablas `mpr_*`.

**Esfuerzo:** medio. **Riesgo:** bajo. **Datos nuevos:** no (solo período nativo MPR).

---

> **Estado Fase B (08/07/2026): IMPLEMENTADA (dimensión temporal + comparación).**
> Reporte **Producción › Por operario (mensual)** (`produccion/operario_mensual`): pivote
> Año→Mes × operario con subtotales por año y Total general, **selector predictivo con tags**
> para filtrar 1 operario o comparar 2 (columna Δ), y presentación docenas/pares.
> Servicio `reporte_mpr_operario_mensual` (`mpr/services.py`), partial
> `mpr/reportes/partials/operario_mensual.html`. Pendiente opcional: heatmap/tendencia con
> Chart.js y `%2da` mensual (Fase A/B avanzada). Ver `docs/mpr/REPORTES_MPR.md`.

## 4. Fase C — Continuidad histórica BEST (solo lectura) + indicador de fuente

Objetivo: que al apagar BEST las series por tejedor/artículo/etapa **no arranquen de cero**; empalmar histórico (BEST) + nativo (MPR) en una sola línea de tiempo, marcando la fuente.

### 4.1 Estrategia (Opción 2.B — snapshot/ETL materializado)
Comando `manage.py` idempotente (dry-run + confirmar, marca `fuente`, `fecha_corte`) que lee las vistas agregadas `REP_*` de Azure SQL BEST (solo lectura, `pymssql`) y **materializa** los agregados dentro de Synap. Los reportes leen: `fecha < fecha_corte` ⇒ fuente `BEST`; `fecha ≥ fecha_corte` ⇒ fuente `MPR`. Esto **desacopla de Azure** (sobrevive al apagado de BEST).

### 4.2 Modelo de datos (3 fact tables, no una por reporte)
Todas con dimensiones + medida en pares/docenas + `fuente` + `fecha_corte`. Se crean vía el catálogo central `core/services/legacy_mysql_schema/catalog.py` (regla del repo).

- **`fact_produccion`** (flujo): `anio, mes, [fecha], id_operario/tejedor_legacy, id_articulo, marca, etapa/origen, motivo → docenas`. Cubre Produccion/Segunda/Sobrantes/Mermas/SEMI/Armado x Tejedor/Art.
- **`fact_inventario_saldo`** (nivel): `anio, mes (cierre), deposito, marca, id_articulo → docenas`. Cubre Inventarios / Stock por etapa. (Nivel fin-de-mes, no flujo.)
- **`fact_comercial`** (flujo): `anio, mes, [fecha], id_articulo, marca, tipo(venta/embarque/salida_empleado/ajuste) → docenas`. Cubre Ventas/Embarques/Salidas Empleados/Ajustes.

Cada «reporte histórico» pasa a ser una **query con filtros** sobre estas facts.

### 4.3 Mapa de identidad tejedor
`mpr_tejedor_legacy_map`: `letra_ttnote ↔ id_operario ↔ nombre ↔ color`. Imprescindible para unir a un mismo tejedor antes/después del corte. Sin match ⇒ «histórico sin asignar».

### 4.4 Alcance recomendado por prioridad
- **P0 (Fábrica/Calidad):** Produccion x Tejedor/Art/Mensual/Diario, Segunda x Tejedor/Mensual, Sobrantes, Mermas. → `fact_produccion`.
- **P1 (Etapas/WIP + Inventario nivel):** SEMI, Armado, Total Emb; Inventarios por etapa (saldo fin-de-mes). → `fact_produccion` + `fact_inventario_saldo`.
- **P2 (Comercial/Control):** Ventas, Embarques, Salidas Empleados, Ajustes, Terceros costura/tintorería. → `fact_comercial`. *Verificar antes qué ya es nativo en AdministraNET MySQL para no duplicar.*

### 4.5 Indicador de fuente en la UI (sutil)
- **Series temporales:** línea vertical de «corte»; tramo previo atenuado/con trama + leyenda «Histórico (BEST)», posterior a color pleno «Synap MPR»; tooltip con fuente.
- **Heatmap/tabla:** celdas/filas pre-corte con tinte gris + punto/badge; leyenda al pie.
- **Global:** badge neutro junto al filtro de período: «Combina histórico BEST (hasta dd/MM/yyyy) y Synap MPR (desde dd/MM/yyyy)».

### 4.6 Conciliación (criterio de aceptación)
Para ≥10 combinaciones tejedor×mes de control, `SUM(docenas)` materializado en Synap = valor del pivot Excel/`REP_*`, dentro de tolerancia acordada (idealmente 0).

---

## 5. Análisis de volumen de datos a migrar (medición en vivo, solo lectura)

> Medición real contra `REP_MOVIMIENTOS_TOTAL` (Azure SQL BEST), 08/07/2026.

### 5.1 Origen (crudo)
- Tabla base `TT`: **4.411.429** filas.
- Vista `REP_MOVIMIENTOS_TOTAL`: **~3.353.118** filas, rango **31/12/2010 → 08/07/2026** (~15,5 años).
- Filas por año (movimientos):

| Año | Filas | Año | Filas |
|----|-------|----|-------|
| 2010 | 4 | 2019 | 205.100 |
| 2011 | 92.329 | 2020 | 92.207 |
| 2012 | 118.651 | 2021 | 228.428 |
| 2013 | 148.673 | 2022 | 356.771 |
| 2014 | 162.941 | 2023 | 280.134 |
| 2015 | 198.167 | 2024 | 317.694 |
| 2016 | 169.710 | 2025 | 399.054 |
| 2017 | 176.745 | 2026 (parcial) | 226.501 |
| 2018 | 180.009 | | |

- **Costo de escaneo (riesgo clave):** un simple `GROUP BY [Año]` sobre la vista tardó **~5 min** (join sobre `TT`). Las vistas `REP_*` **no son consultables interactivamente** en caliente.

### 5.2 Salida (agregado a materializar) — medición real

- **Cardinalidad de dimensiones:** `Tejedor` = **34** · `IdArticulo` = **6.065** · `Id Deposito` = **12** · `Origen` = **12** · `Motivo` = **21** · `Marca` = **64**.
- **Filas de `fact_produccion`** con grano fino `(Año, Mes, Tejedor, IdArticulo, Deposito, Motivo)`: **669.152 filas** (15,5 años completos).
- **Movimientos con `Tejedor` asignado** (subconjunto relevante para fábrica): **~853.014** de ~3,35M. Por año: 2012 ≈ 42k, 2022 ≈ 95k, **2025 ≈ 105k**, 2026 (parcial) ≈ 62k. La atribución por tejedor es sólida desde ~2012.

| Año | Filas c/Tejedor | Año | Filas c/Tejedor |
|----|------|----|------|
| 2011 | 162 | 2019 | 46.356 |
| 2012 | 42.066 | 2020 | 14.364 |
| 2013 | 44.460 | 2021 | 53.836 |
| 2014 | 51.542 | 2022 | 94.838 |
| 2015 | 61.292 | 2023 | 66.902 |
| 2016 | 46.170 | 2024 | 76.816 |
| 2017 | 40.658 | 2025 | 105.448 |
| 2018 | 45.930 | 2026 (parcial) | 62.174 |

### 5.3 Lectura de esfuerzo/riesgo

- **Tamaño del dato materializado: BAJO.** El agregado fino de `fact_produccion` es **~670k filas** (~5× menos que el crudo), y **se reduce fuerte** con grano más grueso: si el reporte por tejedor no necesita `Motivo` ni `Deposito` (solo `Año, Mes, Tejedor, IdArticulo, etapa`), cae a **decenas de miles**. En MySQL es trivial (decenas de MB, consulta sub-segundo con índices). El mapa de tejedores es de **~34 entradas**.
- **El costo real está en el ETL de extracción, no en el resultado.** Cada full-scan de la vista tardó **2,5–5 min** (GROUP BY Año 317s, agregado 151s, cardinalidad 198s) y la conexión llegó a caerse en scans largos. ⇒ el comando debe **extraer con `GROUP BY` server-side** (devuelve ya agregado, poco transfer) y **por lotes (por año)**, con timeouts largos y reintentos, corriendo **una sola vez** (histórico) + incremental hasta el corte.
- **Matriz de riesgo:**
  - Volumen/almacenamiento: **bajo**.
  - Estabilidad de conexión Azure en consultas largas: **medio** (mitigable con batch por año + reintentos).
  - Calidad del **mapeo tejedor** (34 códigos `TTNOTE` ↔ `id_operario`) y semántica fecha/timezone SQL Server↔MySQL: **medio** (requiere validación con planta).
  - Doble conteo en la fecha de corte: **medio** (mitigable con regla dura `< corte`/`≥ corte`).

---

## 6. Seguridad e infraestructura
- `pymssql` ya disponible/usado en el repo. **Credenciales fuera del código** (`.env`), hoy hardcodeadas en `core/management/commands/analyze_best_processes.py` → **deuda a corregir**. Conexión **read-only** forzada.
- Conector Azure **solo para tenant BEST SOX** (scoping `base_empresa`).
- Tablas nuevas vía `core/services/legacy_mysql_schema/catalog.py`. Seguridad reforzada con `ENVIRONMENT=production`.

---

## 7. Orden, dependencias y criterios de aceptación
- **Orden:** A → B → C. C conviene ejecutarla junto al **corte real** (comparte conexión Azure y `fecha_corte` con el doc de cutover de pedidos).
- **Dependencias:** C depende de B (vista temporal donde empalmar) y del mapa tejedor.
- **Aceptación:** A/B sin regresiones en el reporte actual; C con conciliación numérica vs Excel/`REP_*` (§4.6) y sin doble conteo en la fecha de corte.

---

## 8. Núcleo mínimo (si hay que acotar)
Fase A completa + Fase B (heatmap/tendencia) + Fase C limitada a **P0 (`fact_produccion`)** e inventario de Terminado/Proceso/2da. P1/P2 en segunda tanda.
