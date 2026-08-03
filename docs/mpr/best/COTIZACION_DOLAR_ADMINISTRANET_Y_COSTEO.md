# Cotización del dólar en AdministraNET (VB6) y uso en costeo Synap

**Fecha:** 29/07/2026  
**Fuente VB6:** `ABMCotizacion.frm`, `Carga_Cotizacion.frm`, `Funciones.bas` (`Actualiza_Cotizacion_Dolar*`, `Actualiza_Costos_Dolar_Masivo`), pedidos/facturas.  
**Diseño costeo:** [DISENO_MOTOR_COSTO_STOCK_VALORIZADO_SYNAP.md](DISENO_MOTOR_COSTO_STOCK_VALORIZADO_SYNAP.md)

---

## 1. Modelo de datos Admin

Tabla maestra **`cotizacion`** (una fila = una moneda / tipo de cotización):

| Campo | Rol |
|-------|-----|
| `id_cotizacion` | PK. Por convención **`id = 1` = dólar “defecto”** en casi todo el ERP |
| `nombre_cotizacion` | Nombre (ej. Dólar) |
| `ValorPesos` | Cotización **vigente** (cuántos pesos = 1 unidad de esa moneda) |
| `simbolo` | Símbolo display |
| `defecto` | Flag UI |
| `anulado` | Soft-delete |

**No hay historial de cotizaciones en Admin:** al guardar se **sobrescribe** `ValorPesos`. El valor viejo se pierde salvo lo que quedó congelado en comprobantes (`coti_dolar` en `stock` / `stockp` / `comp_ped`, etc.).

---

## 2. Cómo lo usa VB6 (flujo)

### 2.1 ABM y carga

1. **`ABMCotizacion`** lista monedas.  
2. **`Carga_Cotizacion`** alta/edición: escribe `nombre_cotizacion`, `ValorPesos`, `simbolo`, `anulado`.  
3. Al **modificar** la cotización con `id_cotizacion = 1`, si el sistema tiene habilitado costo en dólares (`Principal.articulo_costo_dolar = "Si"`), pregunta:

   > ¿Desea actualizar los costos de los artículos en dólares según cotización actual?

   Si sí → `Actualiza_Costos_Dolar_Masivo(ValorPesos)`.

### 2.2 Cotización en memoria / default

```vb
' Funciones.bas — Actualiza_Cotizacion_Dolar
SELECT * FROM cotizacion WHERE id_cotizacion = 1
Principal.cotizacion = ValorPesos
```

Misma regla en pedidos Synap/RE: `SELECT ValorPesos FROM cotizacion WHERE id_cotizacion=1` → `comp_ped.CotiDolar` / `stockp.coti_dolar` ([orders/09-calculations.md](../../reverse-engineering/orders/09-calculations.md)).

### 2.3 Cotización por artículo (modo configurable)

Si `Principal.cotizacion_moneda_tipo = "Articulo"`:

- Lee `articulo.id_cotizacion` → JOIN `cotizacion.ValorPesos`.  
- Si no hay match, fallback a `1` / cotización global.

Si el modo no es “Articulo”, siempre usa **id=1** (dólar defecto).

Función: `Actualiza_Cotizacion_Dolar_Articulo(id_articulo, "coti_dolar"|"id_cotizacion")`.

### 2.4 Recálculo masivo de costos en USD

`Actualiza_Costos_Dolar_Masivo(valor_cotizacion)`:

```text
PrecioCosto / PNOficial ≈ articulo.costo_dolar * valor_cotizacion
```

Solo artículos con:

```sql
selec_costo_dolar = 'Si' AND costo_dolar > 0 AND discontinuo = 'No'
```

Luego recalcula listas (`Precio1V`… según utilidades) e IVA. Es el puente **USD de lista → pesos de costo comercial**, no el motor de ficha fábrica BestSox.

### 2.5 Congelamiento en movimientos

Al grabar stock/pedidos/facturas se suele persistir:

- `coti_dolar` = valor usado en ese momento  
- `id_cotizacion` = moneda aplicada  

Así el comprobante **no cambia** si mañana sube el dólar en `cotizacion`.

### 2.6 Artículo

| Campo | Rol |
|-------|-----|
| `articulo.costo_dolar` | Costo en moneda extranjera (base del recálculo) |
| `articulo.selec_costo_dolar` | 'Si' → entra en masivo |
| `articulo.id_cotizacion` | Moneda del artículo (modo Articulo) |
| `articulo.PrecioCosto` | Resultado en pesos tras aplicar TC |

---

## 3. Limitaciones del modelo VB6 (relevantes para Synap)

| Limitación | Impacto |
|------------|---------|
| Solo valor **actual** en `cotizacion` | No se puede valorizar stock a fecha con el TC de ese día desde Admin |
| `id=1` hardcodeado | Convenio frágil pero universal en el código |
| Histórico solo en renglones de comprobante | No hay serie diaria consultable |
| Excel BestSox tenía hoja “Tipo de Cambio” aparte | Necesidad de historial **sin** romper el maestro ERP |

---

## 4. Propuesta Synap (genérica y referencial)

**No** inventar un TC paralelo “BestSox”. Anclarse al maestro Admin:

```text
cotizacion (maestro vigente, como VB6)
    id_cotizacion=1 → dólar defecto
    ValorPesos      → TC vigente

cotizacion_historial (NUEVA, genérica ERP — no prefijo best)
    id_historial, id_cotizacion, fecha, valor_pesos,
    id_usuario, observacion, created_at
    UNIQUE (id_cotizacion, fecha)
```

### Reglas

1. **Lectura “hoy” / operativa:** igual que VB6 → `cotizacion.ValorPesos` donde `id_cotizacion = 1` (o la del artículo).  
2. **Al cambiar TC en Synap (o al importar Excel):**  
   - UPDATE `cotizacion.ValorPesos` (si se decide que Synap es dueño del ABM), **y**  
   - INSERT en `cotizacion_historial` el valor anterior o el nuevo (append-only).  
3. **Costeo / valorización a fecha:**  
   `TC(fecha) = historial más reciente con fecha <= corte`; si no hay fila → fallback `ValorPesos` actual.  
4. **Parámetros de fábrica** (cotización proveedor, Polar, etc. del Excel MP):  
   no reemplazan al dólar ERP; viven como parámetros de costeo con FK opcional `id_cotizacion` cuando el parámetro *es* un TC de moneda.  
5. **Publicar costos USD→ARS** (equivalente a `Actualiza_Costos_Dolar_Masivo`): reutilizar el mismo circuito conceptual (`costo_dolar * TC`) vía servicio Synap + `precios_historial`, no una lógica BestSox.

### Qué evita

- Tabla `bsv_tipo_cambio` / TC “solo ventas BestSox”.  
- Sobrescribir `cotizacion` con series sin historial (como hace VB6 hoy).  
- Duplicar monedas fuera de `cotizacion`.

---

## 5. Prefijo de tablas del motor de costeo

Prefijo confirmado: **`mpr_costo_*`** (alineado al módulo MPR; no exclusividad BestSox/ventas).

| Antes | Actual |
|-------|--------|
| `bsv_*` / `costeo_*` | **`mpr_costo_*`** |

Ejemplos: `mpr_costo_parametro`, `mpr_costo_mp_insumo`, `mpr_costo_mp_precio`, `mpr_costo_ficha`, `mpr_costo_ficha_linea`, `mpr_costo_ficha_resultado`, `mpr_costo_sku`, `mpr_costo_valorizacion_cierre`, `mpr_costo_valorizacion_linea`.

TC histórico: **`cotizacion_historial`** (fuera del prefijo `mpr_costo_`, maestro ERP transversal).

---

## 6. Decisiones de producto (30/07/2026)

Confirmado con negocio: sugerencia BCRA + override manual + freeze en transacciones + histórico diario + pantalla de auditoría. Del checklist de buenas prácticas de mercado: **el tipo de cotización es configurable**; el resto se adopta como reglas de diseño.

**Plan de implementación (02/08/2026):** [PLAN_COTIZACION_BCRA_SYNAP.md](PLAN_COTIZACION_BCRA_SYNAP.md) — v1 aún no desarrollada en código.

### 6.1 Flujo operativo

| Paso | Comportamiento |
|------|----------------|
| Sugerir | Synap consulta fuente oficial (API BCRA) según **tipo configurado** |
| Aceptar / editar | Usuario puede aceptar la sugerencia o tipar otro valor |
| Oficial empresa | Solo el valor **aceptado** escribe `cotizacion.ValorPesos` + fila de historial |
| Transacciones | Al grabar, se **congela** TC en el comprobante (`coti_dolar` / `id_cotizacion`) como Admin hoy |
| Pasado | No se recalcula al cambiar el dólar después |
| Día | Un valor rige el día (o el último hábil carry-forward) hasta que se cambie |
| Auditoría | Pantalla de histórico por día: valor, tipo, origen, usuario, observación |

### 6.2 Tipo de cotización **configurable**

Parámetro de empresa (no hardcode): qué tipología se usa al sugerir/guardar.

Ejemplos de valores configurables:

| Código | Uso típico |
|--------|------------|
| `bcra_referencia` | Cotización BCRA de referencia (API Estadísticas Cambiarias) |
| `bcra_compra` / `bcra_venta` | Si la fuente expone compra/venta |
| `mid` | Promedio compra/venta cuando aplique |
| `manual_only` | Sin sugerencia online; solo carga manual |

El tipo queda guardado en config empresa y **también en cada fila de historial** (`tipo_cotizacion` / `origen`) para auditar con qué criterio se sugirió o cargó ese día.

Usos distintos (regalías VMM, costeo, facturación) **pueden** apuntar al mismo tipo empresa o, en fase posterior, a un override por módulo; v1 = un tipo empresa + override manual del valor.

### 6.3 Resto de prácticas adoptadas (fijas)

1. **As-of por fecha de comprobante:** al abrir/grabar con fecha D, sugerir/resolver TC de D (no “ahora” del login).  
2. **Días no hábiles:** carry-forward del último hábil con cotización BCRA/empresa.  
3. **Histórico append-only / por vigencia:** no pisar filas; cerrar tramo e insertar nuevo (o UNIQUE fecha + versión).  
4. **Origen explícito:** `bcra_sugerido` \| `manual` \| `job` + usuario que aceptó.  
5. **Job opcional:** propone (o aplica con política); no overwrite ciego de Admin sin aceptación.  
6. **Sin revaluación silenciosa** del pasado; si hubiera ajuste contable, proceso aparte.  
7. **UI:** vigente, sugerido BCRA, delta %, fecha fuente; en comprobante TC usado solo lectura tras grabar.  
8. **Multi-moneda:** historial por `(id_cotizacion, fecha)`; dólar defecto sigue siendo `id=1` como Admin.

### 6.4 Fuera de alcance v1 (salvo pedido)

- Tipos paralelo por módulo (regalías ≠ costeo) con configs distintas.  
- Dólar blue / MEP como fuente (solo si se agrega al catálogo de tipos configurables).  
- Recálculo masivo `Actualiza_Costos_Dolar_Masivo` al aceptar BCRA (sigue siendo acción explícita aparte).

---

## 7. Resumen

AdministraNET trata el dólar como **una fila viva en `cotizacion` (id=1)**, la propaga a memoria/`coti_dolar` de comprobantes, y opcionalmente recalcula `PrecioCosto` desde `costo_dolar × ValorPesos`. Synap debe **referenciar ese maestro**, agregar **`cotizacion_historial`** genérico, **sugerir BCRA según tipo configurable**, permitir override manual, congelar TC en transacciones y exponer **pantalla de auditoría** del histórico diario.
