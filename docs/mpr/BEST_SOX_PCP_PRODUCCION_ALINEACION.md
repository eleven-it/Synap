# PCP Producción — alineación Best Sox vs MPR

**Planilla:** `Best Sox/PCP20130321.xlsx` → hoja **PCP Produccion**  
**Equivalente MPR:** **`/mpr/tablero-produccion/`** (Tablero de producción) — misma función operativa, distinta tecnología.  
**Fecha análisis:** 07/07/2026  
**Restricción BEST:** solo lectura SQL.

---

## 0. Convención de unidad Best Sox (crítica)

En el dominio Best Sox / BEST / planillas PCP:

| Término en Excel | Significado real | En MPR |
|------------------|------------------|--------|
| **Par** / columna **Pares** (H, L) | 1 unidad de negocio = **1 par** de medias/calzado | El entero en `stock_deposito.saldo`, `mpr_envio_produccion.cantidad`, `mpr_parte_linea.cantidad` |
| **Docena** (I, K, M) | **12 pares** (no 12 medias sueltas) | `cantidad / 12` con divisor fijo 12 en componentes |
| UM `uni` en BEST | En la práctica operativa del tablero PCP = **par** | Modo presentación «Unidades» del tablero = mostrar **pares** |

**No confundir** con una media suelta: si el saldo de depósito es `502`, son **502 pares**, no 502 piezas sueltas.

Implicación para UI MPR: en contexto Best Sox, las etiquetas «unidades» / «unidades sueltas» del toggle docenas deben leerse como **pares** / **pares sueltos** (misma aritmética: `divisor = 12`).

---

## 1. Qué representa la hoja (negocio)

Es el **Tablero de producción** de Best Sox: por cada artículo PP (componente en proceso), muestra **demanda (Pedido)**, **stock en pipeline**, **resta a producir** en **pares** y **docenas** (12 pares), más pista **urgente** y stock **crudo**.

**MPR:** misma vista en `/mpr/tablero-produccion/` — columnas Pendiente, Fabricando, etapas de stock y envío.

---

## 2. Estructura de columnas y fórmulas (verificado en Excel)

| Col | Encabezado | Origen | Cálculo |
|-----|------------|--------|---------|
| **A** | Id PP | Lista artículos activos (MML / `Listado de Articulos`) | Identificador MMID |
| **B** | PP | Descripción | `MMDESC` |
| **C** | UM | Unidad | `uni` / `par` |
| **D** | Correccion Crudo PP | Derivado receta | Código artículo **crudo** (ej. `SEKP610CR6`) |
| **E** | Pedido | **Snapshot** (valor pegado / pivot refrescado) | Cantidad pedida total del PP |
| **F** | Urgente | **Snapshot** | Subconjunto marcado urgente (≤ Pedido; en 363 filas: 87 con F=E, 276 con F&lt;E) |
| **G** | Stock | `Datos Stocks` | `SUMIF(PPoPT, "PP"&IdPP, Stock)` |
| **H** | Resta Producir — **Pares** | Calculado | `MAX(Pedido − Stock, 0)` — cantidad en **pares** |
| **I** | Resta Producir — Docenas | Calculado | `H / 12` → **12 pares = 1 docena** |
| **J** | Stock CRUDO | `Datos Stocks` | `SUMIF(PPoPT, "PP"&CrudoPP, Stock)` |
| **K** | Docenas crudo | Calculado | `J / 12` |
| **L** | Resta Urgente — Pares | Calculado | `MAX(Urgente − Stock, 0)` |
| **M** | Resta Urgente — Docenas | Calculado | `L / 12` |

**Totales cabecera:**

- `I2 = SUM(I5:I65536)` → **Total docenas a producir** (ej. snapshot: ~28.522)
- `M2 = SUM(M5:M65536)` → **Total docenas urgentes** (ej. ~12.470)

**Validación numérica (fórmulas vs valores cacheados):** en filas muestreadas (ej. `SEAT2402BLNE5`: Pedido=875, Stock=502, Resta=373) **`H = MAX(E−G, 0)` coincide**.

### 2.1 `Datos Stocks` — clave PPoPT

```
PPoPT = IF(IdDeposito = 4003, "PT", "PP") & IdArticulo
```

- **PP** = stock en cualquier depósito **excepto Terminado (4003)** → “en pipeline / proceso”.
- **PT** = solo depósito Terminado.

Para PCP Producción solo se usa prefijo **PP** (no descuenta terminado).

**Cruce BEST (solo lectura):** `SEAT2402BLNE5` stock en depósitos ≠ 4003 = **502 u.** → coincide con columna G del Excel.

### 2.2 Filtros de la hoja

| Filtro | Valor | Significado |
|--------|-------|-------------|
| **TienePedido** | (Varios) | Solo artículos con pedido &gt; 0 |
| **B2** | `SIN CRUDO` | Vista enfocada en PP sin stock crudo (361/363 filas con crudo=0 en snapshot) |

---

## 3. De dónde sale «Pedido» y «Urgente»

- **No son fórmulas** en columnas E/F (valores numéricos pegados en el snapshot del archivo).
- El libro tiene **pivot** con campos `Pedido` y `Urgente` (pivotTable1, cache externo).
- En operación diaria se **refrescan** conexiones SQL y se actualiza el snapshot (equivalente a orden de producción / MRP interno BEST).

En BEST, pedidos de venta usan `REP_ORDENES_*`; pedidos de producción internos usan tablas `OO`/`OOL` (p. ej. `OOTYPE=3`, depósito 4003). El snapshot del Excel **no coincide necesariamente** con `OOL` en vivo para un artículo dado (datos desactualizados o fuente distinta).

**Para MPR:** la fuente viva equivalente es **demanda desde PED** + `cantidad_pendiente_prod` / explosión BOM — no hace falta replicar el mecanismo pivot de Excel.

---

## 4. Equivalencia con MPR (proceso, no nombres)

### 4.1 Granularidad

| BEST PCP | MPR |
|----------|-----|
| Una fila = **artículo PP** (semielaborado / componente tejido) | Tablero / pendiente = **componente** tras explosión BOM del pack |
| Pedido directo al PP | `demanda` = pedido + reserva explotados al componente |

Si el PP en BEST es el mismo `id_articulo` que el componente en AdministraNET, las filas son comparables 1:1.

### 4.2 Fórmulas de «resta a producir» (pares y docenas)

**PCP / Tablero Best Sox (Excel):**

```
resta_pares     = MAX(pedido − stock_PP, 0)    # pares
resta_docenas   = resta_pares / 12             # 1 docena = 12 pares
resta_urgente   = MAX(urgente − stock_PP, 0)   # pares
stock_PP        = Σ saldo depósitos ≠ Terminado # cada unidad saldo = 1 par
```

**MPR tablero (`listar_tablero_por_articulo`) — cantidades internas en la misma unidad (par):**

```
demanda         = dem_ped + dem_res
urgente         = dem_ped
total           = Σ stock etapas MPR (pares en cada depósito)
pendiente       = MAX(0, demanda − total − envíos_tablero)   # pares
presentación    = docenas · pares_sueltos  (divisor 12)
```

| Columna PCP | Columna / campo MPR | Notas |
|-------------|---------------------|--------|
| Pedido (E) | `demanda` | MPR en vivo desde PED+BOM |
| Urgente (F) | `urgente` | Solo porción pedido |
| Stock (G) | `total − terminado` (stock en proceso) | 1:1 validado (ej. 502 pares) |
| Resta pares (H) | `pendiente` * | Ver nota envíos abajo |
| Resta docenas (I) | `pendiente_display` modo docenas | Misma regla `/12` |
| Resta urgente (L/M) | *GAP* | Falta columna derivada |

\* **Pendiente vs Resta pares:** cuando no hay envíos al tablero y el stock terminado no participa del `stock_PP`, `pendiente` MPR debe coincidir con columna H del PCP. La diferencia hoy es que MPR incluye **terminado** en `total` y resta **envíos** — a alinear en producto si el tablero debe ser 1:1 con la planilla.

### 4.3 Presentación pares / docenas en UI

| Modo Excel | Modo MPR tablero | Texto sugerido Best Sox |
|------------|------------------|-------------------------|
| Columna H (entero) | `presentacion=unidades` | **Pares** |
| Columna I (H÷12) | `presentacion=docenas` | **Docenas** (+ resto en pares sueltos) |
| Celdas docenas + pares sueltos | `N docenas · M unidades` | Renombrar a **«N docenas · M pares»** |

El cálculo `descomponer_docenas_unidades(..., unidades_por_docena_fijo=12)` **ya es correcto** si la cantidad base es pares; solo cambia la **etiqueta** visible.

---

## 5. GAPs concretos para paridad PCP Produccion

| # | GAP | Prioridad | Acción MPR sugerida |
|---|-----|-----------|---------------------|
| 1 | No existe reporte **PCP Producción** dedicado | Alta | Nuevo reporte en hub Demanda o Producción con columnas equivalentes |
| 2 | **Resta urgente** (col L/M) no expuesta | Alta | Columnas `resta_urgente` / `resta_urgente_docenas` |
| 3 | **Stock PP** vs `total` MPR | Media | Campo `stock_proceso` = total − terminado (o suma depósitos no Terminado) |
| 4 | **Crudo** y filtro SIN CRUDO | Media | Extensión BOM: stock crudo por `Correccion Crudo PP`; filtro “sin crudo” |
| 5 | Divisor docenas siempre 12 en PCP | OK numérico | Etiquetas «pares» en UI; packs terminados siguen usando `cantidad_promedio_bulto` |
| 6 | Pedido desde snapshot vs PED en vivo | Baja | MPR correcto en vivo; Excel es foto — no replicar snapshot |
| 7 | Filtro **TienePedido** | Baja | `WHERE resta_producir > 0 OR demanda > 0` |
| 8 | Totales I2/M2 | Baja | KPIs en cabecera del reporte |

---

## 6. Relación con otras hojas del mismo libro

| Hoja | Relación con PCP Produccion |
|------|----------------------------|
| **Datos Stocks** | Fuente de columna G/J (vía `REP_INVENTARIOS` excl. 4004 en conexión) |
| **Datos Recetas** | Fuente de columna D (crudo por PP) |
| **Listado de Articulos** | Universo de filas (MM activos) |
| **PCP Armado** | Complementario: resta **armar** terminado (pedido + seguridad − stock PT), no producir PP |
| **Stocks Crudo** | Resumen crudo; filtro SIN CRUDO en Produccion |

---

## 7. Conclusión de alineación

| Aspecto | Estado |
|---------|--------|
| Lógica `MAX(pedido − stock, 0)` | **Reproducible** en MPR con `demanda` + `stock_proceso` |
| Pista urgente | **Parcial** — `urgente` existe en tablero; falta resta urgente y reporte |
| Stock en proceso | **Validado** contra BEST (`≠ Depósito Terminado`) |
| Crudo | **GAP** — requiere BOM + stock crudo |
| Envíos tablero | **Diferencia de proceso** — MPR más fino; reporte PCP puede omitirlos |
| Docenas /12 | **Ajuste menor** — flag presentación PCP |

**Veredicto:** El **Tablero de producción MPR** es el reemplazo de **PCP Produccion**. Las cantidades deben interpretarse en **pares**; las docenas son **grupos de 12 pares**. Ajustes pendientes: etiquetas UI, columna resta urgente, crudo, y alinear fórmula `pendiente` con `MAX(demanda − stock_proceso)` si se exige paridad exacta con Excel (sin envíos / sin terminado en el stock descontado).

---

## 8. Stock crudo (columnas D, J, K)

### Qué es

**Stock crudo** no es stock del artículo PP de la fila: es el saldo en pipeline del **insumo crudo** (hilado / materia prima) que la **receta** asocia a ese PP.

| Col PCP | Nombre | Rol |
|---------|--------|-----|
| **D** | Correccion Crudo PP | Código del artículo crudo (ej. `SEKP610CR6`), desde hoja **Datos Recetas** / vista `REP_RECETAS` |
| **J** | Stock CRUDO | `SUMIF(Datos Stocks, "PP" & CrudoPP, Stock)` — pares en depósitos de proceso del **crudo** |
| **K** | Docenas crudo | `J / 12` |

Misma regla de stock que columna G, pero aplicada al **artículo crudo** de la BOM, no al PP tejido.

### Para qué sirve en planta

- **Informativo / abastecimiento:** indica si hay materia prima disponible para alimentar la producción de ese PP.
- **No entra** en `Resta producir` (H) ni en `Resta urgente` (L): esas columnas solo usan stock del **PP** (columna G).
- Filtro **SIN CRUDO** (celda B2): vista que prioriza PP **sin** stock crudo en depósito (en el snapshot analizado, 361/363 filas tenían crudo = 0).

### Equivalente MPR (futuro, no bloquea refactor urgente)

1. Desde BOM del pack/componente: resolver `id_articulo_crudo` (insumo de primer nivel o campo dedicado en receta).
2. Leer `stock_proceso` del crudo (misma regla: suma depósitos MPR ≠ Terminado).
3. Mostrar como columna opcional **Stock crudo** (pares / docenas); no sustituye la columna operativa de envío.

---

## 9. Plan de refactor tablero → columna Resta urgente (iteración)

**Decisión de producto (07/07/2026):** la columna principal del tablero debe alinearse a **Resta urgente — Pares** (PCP col **L**), no a Resta total (col H). Se mantiene el flujo **Enviar a producción**; el tope y precarga del envío pasan a esa métrica.

### 9.1 Mapeo columnas PCP ↔ tablero MPR (objetivo)

| PCP | Hoy MPR | Objetivo MPR |
|-----|---------|--------------|
| Pedido (E) | `dem_ped` (interno) | Col **Pedido** — solo **pares** |
| — (reserva pack) | `dem_res` | Col **Reserva** — solo **pares** |
| Urgente (F) | `urgente` (= `dem_ped`, solo demanda pedido) | Igual — insumo de `resta_urgente` |
| Stock (G) | `total` (incluye Terminado) | **`stock_proceso`** = `total − terminado` |
| Resta total pares (H) | `resta_total` | Subcolumna **Pares** bajo «Resta total» |
| Resta total docenas (I) | `resta_total_docenas_pcp` | Subcolumna **Docenas** (= pares ÷ 12) |
| Resta urgente pares (L) | `resta_urgente` | Subcolumna **Pares** bajo «Resta urgente» (+ Enviar) |
| Resta urgente docenas (M) | `resta_urgente_docenas_pcp` | Subcolumna **Docenas** |

### 9.2 Fórmula propuesta

```
stock_proceso   = total − terminado          # paridad PCP col G (pares)
resta_urgente   = MAX(0, dem_ped − stock_proceso)                 # col L — PCP estricto
resta_total     = MAX(0, demanda − stock_proceso)                   # col H — demanda = dem_ped + dem_res
```

- `dem_ped` = demanda solo pedido (sin reserva pack) — ya es `urgente` en `listar_tablero_por_articulo`.
- Unidad: **pares** (entero o docenas · pares sueltos con divisor 12).
- **Envíos ledger** (`mpr_envio_produccion`) **no** entran en resta (PCP no los tiene). Solo alimentan **Fabricando**.

### 9.3 Envíos ledger — decisión cerrada

| Opción | Fórmula display | Paridad Excel | Operación MPR |
|--------|-----------------|---------------|---------------|
| **A — PCP estricto** ✓ | `MAX(0, dem_ped − stock_proceso)` | 1:1 con col L/H | Resta = brecha física; envíos visibles en **Fabricando** |
| **B — Híbrido** | `MAX(0, dem_ped − stock_proceso − envíos)` | No 1:1 | Descartado (07/07/2026) |

**Decisión (07/07/2026, revisada):** opción **A — PCP estricto**. Los envíos en `mpr_envio_produccion` **no** reducen Resta urgente ni Resta total. El control operativo de lo ya enviado queda en la columna **Fabricando** (`MAX(0, envíos − stock acreditado)`).

Aplicación:

```
resta_urgente = MAX(0, dem_ped − stock_proceso)
resta_total   = MAX(0, demanda − stock_proceso)   # demanda = dem_ped + dem_res
fabricando    = MAX(0, envíos_ledger − stock_acreditado_pipeline)
a_enviar      = MAX(0, resta_urgente − envíos_ledger)   # tope columna Enviar
```

**Fabricando** complementa la vista PCP: lo enviado al tablero que aún no ingresó (o no quedó cubierto) por stock físico en pipeline. **Enviar** usa `a_enviar = resta_urgente − Σ envíos` mientras Fabricando > 0 (evita doble contar stock de proceso). Si Fabricando = 0 y el recálculo deja Resta urgente > 0, el tope **se reabre** a esa urgente (ajuste 24/07/2026).

### 9.4 Cambios previstos (cuando se implemente)

| Capa | Cambio |
|------|--------|
| `listar_tablero_por_articulo` | Campos `stock_proceso`, `resta_urgente`, `resta_total` |
| `enriquecer_filas_tablero_presentacion` | `pedido_pares`, `resta_*_pares`, `resta_*_docenas_pcp` (bloque PCP) |
| `tablero_produccion.html` | Grupo **Demanda a producir**: Pedido \| Resta total (P\|D) \| Resta urgente (P\|D); Enviar atado a urgente |
| `enviar_a_produccion_lote` | Validación/warning contra `resta_urgente` |
| Filtro | Renombrar a **«Solo urgentes»**; `resta_urgente > 0` (reemplaza `solo_pendiente` / pendiente > 0) |
| KPIs `/mpr/` | Sumar `resta_urgente`; KPI ítems urgentes coherente con filtro |
| Tests | `test_tablero_consolidado`, `test_etapa7_enviar_tablero` |
| Docs usuario | `MANUAL_USUARIO_MPR.md`, `TABLERO_CONSOLIDADO.md` |

**Sin tocar en esta iteración:** columna Stock crudo (J/K), PCP Armado.

**Diseño UX/UI:** `docs/mpr/DISENO_TABLERO_PRODUCCION_REFACTOR_PCP.md`

### 9.5 Decisiones de producto cerradas (07/07/2026)

| # | Pregunta | Decisión |
|---|----------|----------|
| 1 | ¿Columna secundaria **Resta total** (PCP col H)? | **Sí** — visible junto a Resta urgente; incluye reserva pack en la demanda |
| 2 | ¿Filtro por defecto = solo filas con brecha urgente? | **Sí** — «Solo urgentes» filtra `resta_urgente > 0` (sustituye «Solo pendientes») |
| 3 | Etiqueta columna operativa | **Pendiente:** «Resta urgente» (alineado a Excel *Resta Producir Urgente — Pares*) |

**Nota filtro (2):** filas con **envío directo sin demanda** (`dem_ped = 0`, `resta_urgente = 0`) **no aparecen** en vista «Solo urgentes». Para verlas: toggle «Ver todos» (equivalente a quitar filtro). Si en operación real son frecuentes, evaluar tercer estado «Con fabricando» en iteración posterior.

**Orden de columnas (alineado a captura PCP):**

`Artículo` · `Pedido` · `Reserva` · `Resta total` (Pares \| Docenas) · `Resta urgente` (Pares \| Docenas) · `Fabricando` · etapas stock · `Enviar`

### 9.6 Pendiente de cerrar

| # | Tema | Estado |
|---|------|--------|
| 1 | Envíos en fórmula resta: opción A vs B | **Cerrado — A (PCP estricto)** |
| 2 | Validación numérica 10 SKUs vs Excel | Antes de implementar |

---

## 10. Próximo paso sugerido

1. Validar 10 SKUs: cols H y L Excel vs `resta_total` / `resta_urgente` MPR (misma fórmula PCP).
2. Implementar refactor tablero (P2 del plan GAP).

---

## Referencias

- `docs/mpr/BEST_SOX_GAP_PROCESOS_Y_CALCULOS.md` §4.4  
- `mpr/services.py` → `listar_tablero_por_articulo`, `_calcular_pendiente_componente`  
- `docs/mpr/PIPELINE_MPR_ETAPA1_TOPOLOGIA_ESTADOS.md` → fórmula Pendiente
