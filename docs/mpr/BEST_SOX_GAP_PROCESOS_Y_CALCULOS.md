# Best Sox → MPR — GAP de procesos y cálculos (no de nombres de campos)

**Fecha:** 07/07/2026  
**Principio rector:** paridad en **qué se mide y cómo se calcula**, no en tablas ni etiquetas SQL.  
**Restricción BEST:** solo lectura en Azure SQL `BEST`.  
**Complementa:** `docs/mpr/BEST_SOX_ITERACION1_VALIDACION.md`

---

## 1. Dos actores en BEST que MPR debe distinguir

En `REP_MOVIMIENTOS_TOTAL` (vista sobre `TT` / `TTL`) coexisten dos roles que **no son lo mismo**:

| Rol BEST | Campo SQL | Significado operativo | En MPR hoy | GAP |
|----------|-----------|----------------------|------------|-----|
| **Responsable de carga** | `Responsable` ← `TT.TTRESP` | Usuario del sistema que **registró** el movimiento (ej. `soledad`, `patricia`) | `id_usuario` en `mpr_parte`, `mpr_envio_produccion`, `mpr_transicion_lote`, `movimiento_stock` | **Persistido pero no expuesto** en reportes fábrica ni filtros |
| **Tejedor / operario fabricante** | `Tejedor` ← `TT.TTNOTE` | Quien **produjo** (código una letra: F, D, S, J…) | `id_operario` + `operario_nombre` en `mpr_parte_linea`; propagado a `mpr_transicion_lote` | Reporte *Por operario* cubre parte; falta en otros informes y en movimiento stock |

**Propuesta MPR (sin cambiar modelo BEST):**

- **Responsable de carga** = usuario Synap logueado al guardar envío / parte / clasificación / armado → ya es `id_usuario`; agregar **snapshot `usuario_nombre`** (como `operario_nombre`) y usarlo en reportes y auditoría.
- **Operario fabricante** = selección en grilla parte/clasificación → ya modelado; mantener separado del usuario de carga.
- En informes tipo *Produccion x Tejedor*: dimensión **operario fabricante**.
- Informes de auditoría / trazabilidad: dimensión **usuario que cargó** (equivalente Responsable).

---

## 2. Unidad de medida — pares, docenas y divisor

### 2.1 Semántica Best Sox (tablero / stock / producción)

En el dominio operativo Best Sox (planilla **PCP Produccion** = **Tablero de producción MPR**):

- **1 unidad** en saldo de depósito, parte, envío o columna **Pares** del PCP = **1 par** (no una media suelta).
- **1 docena** = **12 pares** (columnas Docenas del PCP = pares ÷ 12).

Detalle y validación numérica: **`BEST_SOX_PCP_PRODUCCION_ALINEACION.md`** §0.

**GAP UI MPR:** el toggle «Docenas / Unidades» del tablero debe etiquetarse **Pares** en contexto Best Sox; el resto «unidades sueltas» son **pares sueltos** (misma aritmética).

### 2.2 Regla de docenas en vistas BEST (`REP_*`)

BEST (todas las vistas `REP_*`):

```
docenas = cantidad / divisor
divisor = 6   si UM = 'uni' y PACK = 2
         = 4   si UM = 'uni' y PACK = 3
         = 12  en otro caso
```

MPR debe aplicar la **misma regla** en todo reporte de fábrica:

- Componentes OPP/parte: divisor 12 (`UNIDADES_POR_DOCENA_COMPONENTE`).
- Packs terminados: `cantidad_promedio_bulto` desde artículo (equivalente PACK 2→6, 3→4 en unidades).

**GAP:** validar que `cantidad_promedio_bulto` en AdministraNET reproduzca los mismos divisores que `PACK` en `MYL` de BEST para artículos Best Sox.

---

## 3. Pipeline de movimientos — equivalencia de etapas

BEST modela etapas como **centros virtuales** (tipo CC=2) + **depósitos físicos** (tipo CC=4). Los informes Excel filtran por `Origen`, `Deposito`, `Motivo`.

| Etapa operativa | Centro BEST (virtual) | Depósito físico BEST | `tipo_mpr` Synap |
|-----------------|----------------------|----------------------|------------------|
| Registro tejido | Producción (2000) | Depósito Producción (4000) | Produccion |
| Inspección / planchado | Planchado (2001) | (transferencias) | Planchado |
| Semi embalado | — | Depósito Semi-Embalado (4002) | SemiElaborado |
| 2da / sobrante | — | Depósito Sobrante y Segunda (4004) | 2daSeleccion / Scrap |
| Armado pack | Armado de Packs (2002) | Depósito Terminado (4003) | Terminado |
| Venta | Cliente Generico (3000) | Depósito Terminado | (demanda, no MPR prod.) |

**Movimiento típico de parte (BEST, 30 días):**

1. `Ingreso por Distr s/ Orden`: Producción → Depósito Producción  
2. `Egreso por Distr s/ Orden`: Planchado → Depósito Producción  
3. `Ingreso por Distr s/ Orden`: Planchado → Depósito Semi-Embalado  
4. `Alta por Armado de Pack` → Depósito Terminado  

**MPR equivalente:** parte (Produccion) → clasificación/transición (Planchado → Semi/2da/Scrap) → armado (Terminado). No hace falta replicar `TT`; sí replicar **sumas por etapa y período** que leen los Excel.

---

## 4. Catálogo de informes Excel → qué representan → cómo recrear en MPR

### 4.1 `BS-Reportes Fabrica 22.xlsx` (hub fábrica)

| Hoja Excel | Qué representa (negocio) | Filtros pivot clave | Cálculo | Recreación MPR |
|------------|-------------------------|---------------------|---------|----------------|
| **Produccion Diario** | Docenas producidas por día | `Origen = Producción` | `SUM(Docenas)` por `Fecha` | Nuevo o extender **Resumen diario**: serie `parte` en docenas por `fecha_produccion`. Filtro conceptual = movimientos desde etapa Producción. |
| **Produccion Mensual** | Igual, agregado mes | `Origen`, flags mes actual / últimos 2 meses | `SUM(Docenas)` por año-mes | Mismo origen de datos; agrupar por mes; presets de período. |
| **Produccion x Tejedor** | Producción por operario fabricante | `Origen = Producción`, `Motivo` varios, filas = código tejedor | `SUM(Docenas)` por `Tejedor` | **Por operario** (`mpr_parte_linea`); opcional desglose día/semana. |
| **Produccion x Art** | Producción por artículo / marca | `Marca`, `Articulo Origen`, `Origen` | `SUM(Docenas)` por artículo | Reporte nuevo o extensión: `SUM(parte)` por `id_articulo` + atributos marca/código. |
| **Segunda x Tejedor** | Calidad: 2da selección vs producción | `Deposito = Sobrante y Segunda`, `Motivo` varios | **Ratio:** docenas 2da ÷ docenas producción del mismo tejedor (fórmula Excel cruza con hoja Produccion x Tejedor) | Extender **Por operario**: `segunda / unidades_parte` (% 2da/Ef.); ya hay columnas semi/2da/scrap — falta **ratio explícito** y mismo denominador que BEST. |
| **Segunda Mensual** | 2da por artículo/mes | Dep. 4004 | `SUM(Docenas)` | Agregar serie mensual desde `mpr_transicion_lote` → `2daSeleccion` por operario/artículo. |
| **Sobrantes Mensual** | Sobrante por artículo | `Origen = Depósito Sobrante y Segunda` | `SUM(Docenas)` | Transiciones a Scrap / depósito sobrante; verificar mapeo `tipo_mpr`. |
| **SEMI Diario / Mensual** | Movimiento semi embalado | `Deposito = Semi-Embalado` | `SUM(Docenas)` por día/mes | `SUM(transicion)` donde `tipo_destino = SemiElaborado` (o stock semi). |
| **Armado Diario / Mensual / x ART** | Packs armados a terminado | `Deposito = Terminado`, motivos armado | `SUM(Docenas)` | Movimientos armado OPA / transición → `Terminado`; reporte por artículo pack. |
| **Total Emb total Mensual** | Embalado mensual (semi + métricas 2da/Ef.) | Motivo varios, columnas mes | Fórmulas cruzadas fila 2da/Ef. | Combinar semi mensual + ratios calidad. |
| **Inventarios *** | Stock por depósito en docenas | `Deposito`, `Marca`, excl. 2da/sobrante en algunas hojas | `SUM(Docenas)` desde `REP_INVENTARIOS` | **Demanda → Stock** (`reporte_mpr_stock`); filtros por `tipo_mpr` / depósito. |
| **PUMA Terminado / en Proceso** | Inventario filtrado marca Puma | Marca + depósito | Packs + docenas | Filtro marca en stock MPR. |
| **Ajuste Inventario** | Diferencias inventario | `Origen = Centro de Costos`, TTCODE 521/522 | `SUM(Docenas)` | Módulo ajustes stock / inventario; motivo equivalente. |
| **Ventas Diario / Mensual** | Salida terminado a cliente | Cliente Generico | `SUM(Docenas)` venta | Fuera del core MPR producción; demanda/ventas. |
| **Salidas Empleados** | Consumo interno | `Origen = Empleados` | `SUM(Docenas)` | Reporte movimientos especiales (baja prioridad). |

### 4.2 `Produccion.xlsx`

| Hoja | Representa | MPR |
|------|------------|-----|
| Produccion Diario | Igual §4.1 | Resumen diario → parte |
| Resumen Ventas Histórico | Ventas históricas por artículo | Demanda / ventas |
| Ajuste Inventario / Resumen Ajustes | Ajustes de stock | Inventario MPR |

### 4.3 `Inventarios.xlsx`

Subconjunto de inventario por etapa (Producción, Proceso/Semi, Terminado, 2da/Sobrante, TOTAL). **Un solo reporte MPR Stock** con filtros por `tipo_mpr` reproduce todas las hojas.

### 4.4 `PCP20130321.xlsx` (planificación — no es histórico)

| Hoja | Representa | Cálculo clave | MPR |
|------|------------|---------------|-----|
| **PCP Armado** | Qué falta armar para cubrir pedidos + stock seguridad | `Resta Armar = MAX(0, Pedido + MCSS − StockTerminado)`; docenas = resta/divisor | **Nuevo módulo PCP** o extensión demanda: `pendiente_armado` |
| **PCP Produccion** | Tablero de producción: qué falta producir (semi PP) y crudo | `Resta = MAX(Pedido − Stock_PP, 0)` en **pares**; docenas = pares/12 | **`/mpr/tablero-produccion/`** — ver **`BEST_SOX_PCP_PRODUCCION_ALINEACION.md`** |
| **Datos Stocks** | Stock PT vs PP (`PPoPT` = PT/PP + id) | Derivado de inventario | Stock por etapa + flag pack/componente |
| **Datos Recetas** | BOM PT → PP → crudo | `REP_RECETAS` | Explosión BOM AdministraNET (ya en demanda) |
| **Resumen Armado** | Pivot resta armar por marca/código | Agregación | Salida del motor PCP |

### 4.5 `BS Reporte F Rotacion.xlsx`

| Hoja | Representa | Cálculo | MPR |
|------|------------|---------|-----|
| Pedidos / Órdenes | Pedidos venta pendientes/parciales | `REP_ORDENES_*` | Demanda pack / pedidos |
| **Rotaciones** | Cobertura de stock en meses | `Meses Stock = StockTotal / (VentasProm2Meses)`; `Necesidad = MAX(0, Índice×Ventas − Stock)` | **Reporte nuevo Rotación** en hub Demanda |

---

## 5. Matriz GAP por dimensión de análisis

| Dimensión Excel | BEST | MPR actual | Acción |
|-----------------|------|------------|--------|
| Día / mes / semana | Campos derivados en vista | `fecha_produccion`, `creado_en` | OK; agregar agrupación semana en reportes |
| **Responsable carga** | `TTRESP` | `id_usuario` (sin nombre en reportes) | **Agregar `usuario_nombre` snapshot + dimensión reporte** |
| **Tejedor / operario** | `TTNOTE` (1 letra) | `id_operario`, `operario_nombre` | OK en parte; **diccionario letra↔operario** si migran histórico |
| Turno | No explícito en BEST | `id_mpr_turno` | MPR **más rico**; opcional filtro turno en reportes |
| Marca / código / talle | `MYL` en vista | `id_manual`, atributos artículo | OK vía artículo MySQL |
| Depósito / etapa | `Origen`, `Deposito` | `tipo_mpr` | Mapear CC 4000–4004 ↔ tipos (§3) |
| Motivo movimiento | `Motivo` (TTCODE) | `CodigoMovimiento` + texto | Tabla equivalencia motivo BEST ↔ MSTOCK |
| Lote | `LoteNo` / `BANO` | `uuid_lote`, transiciones | Trazabilidad MPR por lote (timeline) |
| Remito | `Remito` (`DDNOFR`) | `nro_comprobante` movimiento | Ya en movimiento_stock; enlazar en reportes |
| Docenas vs pares | Siempre ambos en vista (docena = 12 pares) | Modo presentación (etiqueta «unidades») | Renombrar a **pares** en tablero Best Sox |
| 2da/Eficiencia | Fórmula Excel entre hojas | Columnas semi/2da/scrap | **Agregar ratio `2da/parte` por operario** |
| PCP resta producir | Excel PCP Produccion = tablero MPR | Tablero existe; faltan resta urgente, crudo, paridad fórmula | **Alinear pendiente** con `MAX(demanda − stock_proceso)`; ver doc PCP |
| PCP resta armar | Excel PCP Armado | No existe | **Nueva capability planificación armado** |
| Rotación stock/ventas | `REP_VentasStock` | No existe | **Nuevo reporte demanda** |

---

## 6. Mapeo de informes MPR existentes → cobertura Excel

| Reporte MPR | Cubre hojas Excel | Falta para paridad |
|-------------|-------------------|-------------------|
| Resumen diario | Produccion Diario (parcial) | Serie debe ser **parte en docenas**, no solo enviado; opcional desglose por motivo/etapa |
| Por operario | Produccion x Tejedor (parcial) | Ratio 2da/Ef.; filtro por motivo; histórico por semana |
| Cadena pipeline | Vista agregada embudo | Alinear totales con sumas BEST por etapa |
| Stock | Inventarios * | Filtros marca, excl. 2da, PUMA |
| Movimientos / timeline | Auditoría TT | Incluir **usuario carga** y operario |
| Tablero de producción | **PCP Produccion** | Resta urgente, crudo, etiquetas pares/docenas, paridad `pendiente` vs Excel |
| Pendiente componentes | Vista reporte (misma lógica base) | Export/agregado; no sustituye al tablero operativo |
| Brecha pack / pedidos | PCP Armado + Rotación (parcial) | PCP armado + rotación ventas |

---

## 7. Plan de implementación sugerido (por prioridad de paridad de cálculo)

### P0 — Paridad reportes fábrica diarios (sin PCP)

1. **Responsable de carga:** persistir `usuario_nombre` en ledgers; mostrar en trazabilidad y export CSV.
2. **Produccion Diario:** en Resumen diario, destacar serie `parte` en docenas (= Excel); documentar equivalencia con filtro `Origen=Producción`.
3. **Produccion x Tejedor:** validar Por operario con mismo período; agregar columna **% del total** (ya existe) y **2da/Ef.** = `segunda / unidades`.
4. **SEMI / Armado / 2da mensual:** nuevas series en hub o pestañas en reporte pipeline desde `mpr_transicion_lote` + stock.

### P1 — Inventario y ajustes

5. Filtros inventario: por depósito, sin 2da/sobrante, por marca (PUMA).
6. Ajustes inventario: reconciliar con movimientos ajuste MPR vs TTCODE 521/522.

### P2 — Tablero / planificación (PCP)

7. **Tablero = PCP Produccion:** resta urgente, crudo, etiquetas **pares/docenas**, alinear `pendiente` si se exige paridad 1:1 con Excel (`BEST_SOX_PCP_PRODUCCION_ALINEACION.md`).
8. Servicio y pantalla **PCP Armado** (distinto del tablero de producción).

### P3 — Demanda avanzada

9. Rotación stock/ventas.
10. Pedidos pendientes/parciales estilo `REP_ORDENES_COMBINADO`.

---

## 8. Criterios de aceptación (paridad de proceso)

Para cada hoja Excel prioritaria:

1. **Misma definición de población** (filtros equivalentes, no nombres iguales).
2. **Misma fórmula de agregación** (suma docenas con divisor pack correcto).
3. **Mismas dimensiones** (día, operario, artículo, depósito/etapa).
4. **Tolerancia numérica** acordada tras operación paralela (no exige igualdad hoy: sistemas separados).
5. **Roles:** todo movimiento MPR debe poder responder «quién cargó» y «quién fabricó» cuando aplique.

---

## 9. Referencias

- Planillas: `Best Sox/*.xlsx`
- Iteración 1 numérica: `docs/mpr/BEST_SOX_ITERACION1_VALIDACION.md`
- MPR reportes: `docs/mpr/REPORTES_MPR.md`
- Pipeline etapas: `docs/mpr/PIPELINE_MPR_ETAPA1_TOPOLOGIA_ESTADOS.md`
- Parte y operario: `docs/mpr/PARTE_PRODUCCION.md`, `docs/mpr/DOCENAS_CLASIFICACION_OPERARIO_MPR.md`
