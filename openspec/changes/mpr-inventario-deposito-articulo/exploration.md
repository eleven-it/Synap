# Exploration: Inventario por depósito y artículo (MPR)

**Change:** `mpr-inventario-deposito-articulo`  
**Fecha:** 14/08/2026  
**Modo:** Evolution (reporte operativo MPR; no migración VB6 completa)

## Decisiones de producto (cerradas — no reabrir)

| ID | Decisión |
|----|----------|
| A | Stock como Excel `Inventarios.xlsx`: **packs** en Terminado/2da, **pares** en pipeline (Producción, Semi). Docenas con divisor BEST 12/6/4 vía `cantidad_promedio_bulto`. |
| B | 2da/Sobrante **OFF por defecto** (paridad hoja «Inventario Resumido TOTAL»). |
| C | **Stock a fecha (cortes)** incluido en **este mismo change**. |

---

## Exploration: Inventario depósito × artículo MPR

### Referencia Excel / BEST

Fuente: `Inventarios.xlsx` ← `BEST.dbo.REP_INVENTARIOS` (documentado en `docs/mpr/best/REP_INVENTARIOS_ESQUEMA.md`).

| Aspecto | Comportamiento Excel |
|---------|---------------------|
| Jerarquía | Depósito → Marca → Artículo → Talle |
| Medidas | **Suma de Stock** (UM nativa) + **Docenas** (derivada) |
| Depósitos | Producción 4000, Semi 4002, Terminado 4003, 2da 4004 |
| Docenas pipeline | Divisor **12** (100 % pares) |
| Docenas Terminado/2da | Mix **12 / 6 / 4** según PACK (`cantidad_promedio_bulto`) |
| Total cabecera | **SUM(Docenas)**, no `SUM(Stock)/12` |
| Resumido | Excluye 2da por defecto |

### Current State

#### 1. `/stock/inventario/` y `/mpr/inventario/` (`stock-inventario-tabla-mpr`)

- **Servicio:** `stock/services/inventario_tabla.py` — pivote por `tipo_mpr` (no por depósito físico).
- **Grano:** una fila por artículo + CE (Talle/Color); columnas = etapas MPR.
- **Fuente:** `stock_deposito.saldo` agregado por `deposito.tipo_mpr`, filtro `suma_stock='Si'`.
- **Presentación docenas:** `preparar_filas_inventario_presentacion` → `_celda_stock_deposito` con **`unidades_por_docena_fijo=12` siempre**, ignorando `cantidad_promedio_bulto` en la práctica:

```python
# mpr/reportes_presentacion.py — descomponer_docenas_unidades recibe fijo=12
partes = descomponer_docenas_unidades(
    abs(total), cantidad_promedio_bulto,
    unidades_por_docena_fijo=UNIDADES_POR_DOCENA_COMPONENTE,  # 12
)
```

- **Ámbitos:** Terminados (`tipo_art_fab` Terminado/Tercero) vs Fabricados (pipeline); no replica la vista Excel «todos los depósitos en columnas» ni agrupación Marca.
- **Acoplamiento:** reutilizable como fuente SQL parcial (agg por `tipo_mpr`, CE, filtros marca), pero **no** cumple reglas A ni total SUM(docenas).

#### 2. Hub MPR `demanda/stock` (`/mpr/reportes/?grupo=demanda&reporte=stock`)

- **Servicio:** `reporte_mpr_stock()` en `mpr/services.py` — filas planas artículo × depósito, `LIMIT 500`, solo `saldo != 0`.
- **Vista:** `preparar_stock_por_deposito` → partial `mpr/reportes/partials/stock.html` — columnas por **depósito físico** (orden `tipo_mpr`).
- **Misma limitación docenas:** `_celda_stock_deposito` fuerza divisor 12.
- **Sin:** Talle, Marca, filtro 2da OFF, totales SUM(docenas), export Excel, stock a fecha, paginación/búsqueda server-side.
- **Punto de inserción natural:** nuevo reporte en el hub (o evolución de `stock` con breaking UX — preferible **nuevo slug** `inventario_deposito`).

#### 3. `stock-existencias` (reports)

- **Runner:** `reports/services/stock_existencias_query.py` — universo comercial (reservado PED, BO, agrupación jerárquica).
- **Grano:** artículo × depósito comercial; **sin** talle/docenas MPR; **sin** reglas pipeline vs terminado.
- **Veredicto:** **descartado** como base (confirmado en contexto y código).

#### 4. Semántica `stock_deposito.saldo` (evidencia código)

| Etapa | Evidencia | Interpretación UM |
|-------|-----------|-------------------|
| Terminado (pack) | Armado BOM: `entrada_pack = cantidad_packs` escrito directo en `stock_deposito` (`mpr/services.py` ~L11941) | **Packs** |
| Semi / Producción (componente) | OPP/parte, tablero PCP, kardex UAT 907944-02: saldo en pares; docenas ÷12 | **Pares** |
| 2da | Misma tabla; artículos `Fabricado 2da` / surtido — **spike** para packs vs pares en muestra real | **Asumir packs** (decisión A) |

`bulto_desde_pack()` en `core/services/administranet_articulo.py` mapea PACK 1→12, 2→6, 3→4 unidades/docena (paridad BEST).

#### 5. Stock a fecha

- **Diseñado, no implementado:** `DISENO_MOTOR_COSTO_STOCK_VALORIZADO_SYNAP.md` §5.2 — hoy `stock_deposito` si corte=hoy; histórico vía `stock` con `Fecha <= corte` (criterio VB6).
- **Kardex MPR:** `construir_kardex_articulo` — `saldo_inicial=0`; no sirve para cortes globales.
- **Inventario físico:** usa `stock.FechaControl` post-snapshot (distinto contrato temporal).
- **Gap:** no existe servicio compartido `stock_a_fecha`; es prerequisito del change (decisión C).

---

### Affected Areas

| Archivo / módulo | Rol en el change |
|------------------|------------------|
| **Nuevo** `mpr/services_inventario_deposito.py` (nombre orientativo) | Consulta grano depósito×artículo, docenas por reglas A, filtros, totales, stock a fecha |
| `mpr/reportes_hub.py` | Registrar reporte `demanda/inventario_deposito` (o grupo `inventario`), partial, columnas CSV/Excel |
| `mpr/views.py` (`ReportesMPRView`) | Rama GET, export `format=xlsx`, params fecha corte / incluir_2da |
| `mpr/reportes_presentacion.py` | Nueva celda/medida con divisor **por `tipo_mpr`**, sin `unidades_por_docena_fijo=12` global; etiquetas Stock vs Docenas |
| `mpr/services.py` | Helpers reutilizables: `divisor_docena_inventario(tipo_mpr, cantidad_promedio_bulto)`, posible extracción desde `divisor_docena_pack` |
| `mpr/templates/mpr/reportes/partials/` | Partial nuevo (canon hub MPR); subtotales Marca; fila TOTAL = SUM(docenas) |
| `stock/services/inventario_tabla.py` | **Opcional fase 2:** alinear docenas si se extrae helper compartido; **no** obligatorio en MVP del reporte hub |
| `docs/mpr/INVENTARIO_DEPOSITO_ARTICULO.md` | Documentación operativa + paridad Excel |
| `docs/mpr/best/REP_INVENTARIOS_ESQUEMA.md` | Referencia cruzada divisores |
| Tests | `mpr/tests/test_inventario_deposito_report.py`, tests stock_a_fecha con fixtures `stock` |
| `ia/services/report_tools.py` | **Opcional:** enrutar NL «inventario por depósito» (fuera de MVP si presiona presupuesto) |

**No tocar en MVP:** `reports/services/stock_existencias_query.py`, kardex salvo reutilizar patrón SQL movimientos.

---

### Approaches

| # | Enfoque | Pros | Contras | Esfuerzo |
|---|---------|------|---------|----------|
| **1** | **Nuevo reporte hub MPR** (`inventario_deposito`) + servicio dedicado + stock_a_fecha + export Excel | Alineado a Excel y decisiones A–C; canon UI MPR existente; no contamina BO/stock-existencias; evolución acotada | Duplica parcialmente agg de `inventario_tabla`; requiere spike UM + validación VB6 fecha | **Medio–Alto** |
| **2** | Extender `reporte_mpr_stock` / partial `stock.html` in-place | Menos rutas nuevas | Breaking change del reporte actual (limit 500, sin talle); mezcla dos productos en un slug | Medio |
| **3** | Extender `/stock/inventario/` (pivote etapas → depósitos + docenas fix) | Reutiliza filtros marca/ambito | Grano distinto (etapas vs depósitos); permiso `stock.consultas` vs operación MPR; no encaja jerarquía Marca Excel | Medio |
| **4** | Nuevo slug en `reports/` (`mpr-inventario-deposito`) | Patrón dashboard gerencial, export maduro | Segundo entry point; permisos/report catalog; duplica hub MPR ya usado por planta | Alto |
| **5** | Solo fix `_celda_stock_deposito` global | Diff mínimo | No entrega jerarquía, totales, 2da default OFF, stock a fecha ni Excel | Bajo (insuficiente) |

---

### Recommendation

**Enfoque 1 — Nuevo reporte en hub MPR** (`grupo=demanda`, `reporte=inventario_deposito` o grupo `inventario` dedicado):

1. **Servicio de consulta** con grano `(id_deposito, id_articulo)` enriquecido con Marca, Talle (CE), Stock UM-native, Docenas calculada:
   - `tipo_mpr IN (Produccion, SemiElaborado)` → divisor 12; etiqueta secundaria «pares».
   - `tipo_mpr IN (Terminado, 2daSeleccion)` → divisor `divisor_docena_pack(cantidad_promedio_bulto)`; etiqueta «packs» o unidad según `id_unimed`/pack.
   - `docenas = stock / divisor` (float, paridad Excel); total pie = **SUM(docenas)** por scope.
2. **Filtros:** depósito(s), marca(s), búsqueda artículo, **`incluir_2da=0` default**, **`fecha_corte`** (default hoy → `stock_deposito`; pasado → reconstrucción `stock`).
3. **UI:** partial hub MPR (patrón `stock.html` + filtros de `inventario_tabla` / tags marca); fechas `dd/MM/yyyy`; modales Synap.
4. **Export:** Excel vía `format=xlsx` (patrón otros reportes MPR o `openpyxl` como inventario físico).
5. **Entrega encadenada** (presupuesto review ~800 líneas, `delivery_strategy=auto-chain`):
   - **PR-1:** consulta + docenas + UI + filtros + tests unitarios divisores/totales.
   - **PR-2:** `stock_a_fecha` + export Excel + UAT paridad muestra vs Excel.

**Refinar (no cambiar dirección):** mantener `/stock/inventario/` sin regresión; eventual helper compartido `mpr/inventario_docenas.py` consumido por tabla Stock en change posterior.

---

### Spike obligatorio (pre-propose)

| # | Pregunta | Método | Criterio de cierre |
|---|----------|--------|-------------------|
| S1 | ¿`stock_deposito.saldo` en Terminado es packs para SKUs pack y pares en Semi? | 5–10 artículos: comparar `stock_deposito` vs movimiento armado/OPP en `administranet1` | Coherencia pack-count Terminado; pares×12 docenas pipeline |
| S2 | ¿Paridad docenas vs Excel `Inventarios.xlsx` en TOTAL? | Script diagnóstico: SUM(docenas) por depósito con reglas A vs hoja hero | Delta < tolerancia acordada (p. ej. 0,01 docenas) |
| S3 | ¿Campo fecha VB6 para stock a fecha? | Revisar `Info_Stock.frm` / movimientos en Admin; prototipo SQL `SUM(stock)` hasta corte vs snapshot hoy | Misma fecha que VB6 (`stock.Fecha` vs `FechaControl` — inventario físico usa FechaControl; **confirmar cuál usa Info_Stock**) |
| S4 | Universo artículos | ¿Incluir `tipo_art_fab=Tercero` en Terminado? | **Cerrado 14/08/2026:** Tercero **incluido** |

---

### Risks

| Riesgo | Severidad | Mitigación |
|--------|-----------|------------|
| **UM mixta** pack/pares en misma columna «Stock» sin etiqueta por depósito | Alta | Columna Stock + subtítulo UM por `tipo_mpr`; no asumir pares globales |
| **`_celda_stock_deposito` /12** si se reutiliza sin refactor | Alta | Nueva función `medidas_inventario_excel(saldo, tipo_mpr, bulto)`; tests tabla-driven 12/6/4 |
| **Stock a fecha** — campo temporal equivocado (`Fecha` vs `FechaControl`) | Alta | Spike S3; tests con movimientos conocidos en contenedor |
| **Performance** reconstrucción histórica | Media | Índice `(id_articulo, CodDeposito, Fecha)` si falta; acotar depósitos MPR; paginación |
| **TOTAL ≠ SUM(stock)/12** si UI calcula mal | Media | Total solo en capa servicio; test explícito pack×3 + pipeline |
| **2da OFF default** olvidado en SQL | Baja | Filtro `tipo_mpr != 2daSeleccion` default; test regresión |
| **Regresión** `/stock/inventario/` | Baja | No modificar `consultar_inventario_tabla` en PR-1 |
| **Presupuesto review 800 líneas** | Media | PR encadenados; stock_a_fecha en PR-2 |

---

### Ready for Proposal

**Sí**, con spike S1–S3 documentado en propose (o tarea 0.1 en tasks).

El orchestrator debe pasar a **`sdd-propose`** con:

- Alcance: reporte hub MPR + stock_a_fecha + export Excel (decisiones A–C).
- Exclusiones: motor costo valorizado (`mpr_costo_*`), cambios `stock-existencias`, fix global inventario tabla (opcional posterior).
- Entrega: 2 PRs encadenados si forecast supera 400 líneas.
- Dependencia: resultado spike UM y fecha VB6.

---

### Forecast presupuesto review (orientativo)

| Slice | Líneas auth. estimadas | Riesgo 400-line budget |
|-------|------------------------|-------------------------|
| PR-1 consulta + UI + docenas | ~350–450 | Medium |
| PR-2 stock_a_fecha + Excel | ~300–500 | Medium–High |
| **Total change** | ~650–950 | **High** → chained PRs recommended |
