# Análisis: Lista_Pedidos_OPT (VB6) vs ventana-pack/agrupar (Synap)

## Objetivo

Que la pantalla **Confirmar OPT** (`/mpr/demanda/ventana-pack/agrupar/`) muestre el equivalente a lo que en VB6 se ve y se usa en **Lista_Pedidos_OPT** cuando el usuario “selecciona” un renglón (acción que dispara `Selecciona_Renglon_Global`). En Synap la selección es **múltiple** en la primera pantalla; en VB6 es **un solo renglón** por acción.

---

## 1. Lista_Pedidos_OPT (VB6) – Estructura

### 1.1 Pantalla

- **Título:** "Lista de pedidos pendientes para vincular a OPT - Ordenes de producción de trabajo"
- **Filtros (Frame Búsqueda):** Fecha desde, Fecha hasta, Texto (Busqueda), botón Actualizar. Se usa en `Consulta_Busqueda` para cargar DataComprobante y Data_Global.
- **Grid principal visible para “Pedido produccion”:** **Grid_Global** (datasource: Data_Global).
- **GridComprobante** (“Pedido individuales”): en el diseño tiene Left/Top negativos para “Pedido produccion”, es decir queda fuera de vista; la pantalla se centra en el “global de artículos”.
- **DepositoOrigen:** DataCombo; se usa en “Parte produccion” y se sincroniza con CargaMovStock.

### 1.2 Data_Global – Origen de datos

- **RecordSource (Pedido produccion):**
  ```sql
  SELECT lista_produccion_agrupada.*, articulo.nombrearticulo, articulo.id_manual
  FROM lista_produccion_agrupada
  LEFT JOIN articulo ON (articulo.idart = lista_produccion_agrupada.id_articulo)
  WHERE lista_produccion_agrupada.cantidad_pendiente_prod <> 0
  ORDER BY articulo.nombrearticulo
  ```
- Es decir: una fila por **artículo** con demanda (pendiente > 0), con datos de lista_produccion_agrupada y nombre/cod. manual del artículo.

### 1.3 Grid_Global – Columnas

| Índice | Caption           | DataField                | Origen / Nota                          |
|--------|-------------------|--------------------------|----------------------------------------|
| 0      | Cod. Sist         | id_articulo              | lista_produccion_agrupada              |
| 1      | Cod. manual       | id_manual                | articulo                               |
| 2      | Articulo          | nombrearticulo           | articulo                               |
| 3      | Cantidad pedida   | cantidad_pedida          | lista_produccion_agrupada              |
| 4      | Cantidad stock    | (vacío)                  | Posible cálculo/oculto en práctica     |
| 5      | Cantidad total    | (vacío)                  | Idem                                   |
| 6      | Urgente           | (vacío)                  | Idem                                   |
| 7      | Urgente docenas   | (vacío)                  | Idem                                   |
| 8      | Stock minimo      | (vacío)                  | Idem                                   |
| 9      | Stock terminado   | (vacío)                  | Idem                                   |
| 10     | Pendiente fab.    | cantidad_pendiente_prod  | lista_produccion_agrupada              |
| 11     | Pendiente fab doc | (vacío)                  | Idem                                   |

- Caption del grid: **"Global de artículo para producir"**.
- ToolTip: *"Presione ENTER y selecciona solo el item indicado"*.

En VB6 las columnas con DataField vacío no se rellenan desde el RecordSource; si se muestran, sería por código adicional (en el análisis no aparece llenado explícito de esas celdas para Grid_Global).

---

## 2. Selecciona_Renglon_Global – Qué hace en VB6

### 2.1 Disparo

- **Grid_Global_DblClick** → llama a `Selecciona_Renglon_Global`.
- **Menú F12 (keySelecComp)** → mismo.

### 2.2 Flujo para TipoComprobante = "Pedido produccion"

1. **Selección única:** se toma el **id_articulo** de la fila actual de **Data_Global** (`Data_Global.Recordset.Fields!id_articulo`). No hay multi-selección; es un solo artículo por acción.

2. **Consulta por ese artículo:**
   - Se abre `rs_stock` con:
     - `lista_produccion_agrupada` + `articulo` (idart, ensamblado).
     - Filtro: `(cantidad_pedida <> 0 OR cantidad_pendiente_prod <> 0) AND id_articulo = <ese id>`.
   - En la práctica suele ser una sola fila (una lista_produccion por artículo).

3. **Por cada registro en rs_stock:**
   - Si el artículo es **ensamblado = 'Si'**: se llama a **Desarme** (explota BOM y carga CargaMovStock.CuerpoStock con los **componentes de la receta**).
   - Si no es ensamblado: se agrega **una línea** en CargaMovStock.CuerpoStock con el artículo y cantidad (cantidad_pendiente_prod u otra lógica según bulto/display).

4. **Cierre:** se cierra conexión, se muestra el mensaje *"Se agregaron los artículos del pedido al comprobante de movimiento de stock y OTP"*, se hace **Unload Me** y queda abierto **CargaMovStock** (comprobante de movimiento de stock) con las líneas cargadas.

### 2.3 ¿Qué datos se muestran en VB6 después de seleccionar? (No hay “agrupar” en VB6)

En VB6 **no existe** una pantalla intermedia “agrupar” o “confirmar”. Lo que el usuario ve **después** de hacer doble clic (o F12) es directamente **CargaMovStock** (comprobante de movimiento de stock), y **los datos que ahí se muestran** son:

- **Si el artículo elegido es armado (ensamblado = 'Si'):**  
  **Los artículos de la receta** (componentes del BOM). `Desarme` lee `en_abm_formula` (id_articulo, cantidad_articulo) y por cada componente llama a `MstockE`, que hace `CargaMovStock.CuerpoStock.Recordset.AddNew` y agrega una línea con el **componente** (IDArt, CodigoArticulo, Descripcion, Cantidad = cantidad_desarme × cantidad_articulo, etc.). Es decir: en pantalla se ven **insumos/componentes**, no el pack.

- **Si el artículo no es armado:**  
  Una sola línea: el propio artículo con su cantidad.

Por tanto, en VB6 lo que “se muestra” al confirmar la selección son **los artículos de la receta** (componentes con cantidades), no la lista de packs elegidos. No hay tabla intermedia de “packs a generar OPT”.

### 2.4 Resumen VB6

- **Una sola pantalla** de lista (Grid_Global).
- **Una fila seleccionada** (la actual del grid).
- **Sin pantalla intermedia “confirmar”:** al ejecutar la acción se abre directamente CargaMovStock.
- **Contenido de CargaMovStock:** para artículos armados = **artículos de la receta** (componentes); para no armados = una línea con el artículo.

---

## 3. Implicación para Synap “agrupar”

En VB6 lo que el usuario ve después de elegir un artículo (y que tiene receta) son **los artículos de la receta** (componentes), no el pack. En Synap, la pantalla **Confirmar OPT** (agrupar) tiene dos pestañas:

- **Packs:** los artículos seleccionados en el paso 1 (packs con cantidades editables). Esto no existe en VB6 como pantalla; allí solo está la grilla global y luego CargaMovStock.
- **Unidades:** desglose por **componentes de las recetas** (BOM) de esos packs, con cantidades agregadas. Esto **sí** equivale a lo que en VB6 se muestra en CargaMovStock para cada pack armado: **los artículos de la receta**.

Por tanto, el tab **Unidades** en agrupar es el que muestra “los mismos datos” que en VB6: **artículos de la receta** (insumos/componentes con cantidades). El tab Packs es un paso nuestro previo a generar la OPT (selección múltiple + edición de cantidades) que VB6 no tiene.

---

## 4. Synap – Flujo actual

### 4.1 Paso 1 – ventana_pack (Pedido producción trabajo)

- Equivalente a la **lista** que alimenta Grid_Global en VB6, pero con:
  - **Selección múltiple** (checkboxes por artículo).
  - Columna **Cant. a producir** (editable) por fila.
  - Tabs **Packs** y **Unidades** (desglose por componentes de recetas).
- Al pulsar **Continuar** se envían los artículos **marcados** y sus cantidades a la sesión y se redirige a **ventana_pack_agrupar**.

### 4.2 Paso 2 – ventana_pack_agrupar (Confirmar OPT)

- Se muestra **solo** la selección del paso 1 (equivalente a “las filas que en VB6 habrían sido elegidas una a una”).
- Columnas actuales: Cod. Sist, Artículo, Stock terminado, Cant. urgente, Cant. a fabricar (editable), Pedidos (tooltip con desglose).
- Acción: **Generar OPT** → se crea **una** OPT en BD (lista_produccion_agrupada / lógica MPR) con **varias** filas (varios id_articulo). No se abre CargaMovStock.

---

## 5. Comparación: qué “muestra” VB6 vs qué mostramos en agrupar

### 5.1 Contenido equivalente al “renglón seleccionado” en VB6

En VB6, lo que “se muestra” para la selección es la propia fila del **Grid_Global**, con:

- Cod. Sist (id_articulo)
- Cod. manual (id_manual)
- Articulo (nombrearticulo)
- Cantidad pedida
- (Columnas 4–9 y 11 con DataField vacío en el .frm; posiblemente no todas usadas)
- Pendiente fab. (cantidad_pendiente_prod)

En Synap, por cada **artículo seleccionado** (equivalente a ese renglón), en agrupar ya mostramos:

- Cod. Sist ✓
- Artículo (cod. manual + descripción) ✓
- Stock terminado ✓ (en VB6 sería “Stock terminado” col 9, vacío en el recordset)
- Cant. urgente ✓ (en VB6 col 6 “Urgente”, vacío en el recordset)
- Cant. a fabricar (editable) ✓ (en VB6 la “cantidad” se toma de lista_produccion en Selecciona_Renglon_Global)
- Pedidos (tooltip) ✓ (en VB6 no hay tooltip de pedidos en esta pantalla; es valor agregado nuestro)

### 5.2 Qué falta o qué alinear en agrupar respecto al VB6

1. **Cantidad pedida**
   - VB6: columna “Cantidad pedida” en Grid_Global.
   - Synap agrupar: **no** la mostramos. Podemos añadirla para paridad con la grilla VB6.

2. **Pendiente fab. (cantidad_pendiente_prod)**
   - VB6: columna “Pendiente fab.”.
   - En nuestro flujo, la “cantidad a fabricar” por fila puede ser distinta al pendiente (el usuario puede editarla). Tener **pendiente** como solo lectura ayuda a comparar con VB6 y a ver el estado de la lista.

3. **Columnas VB6 con DataField vacío**
   - “Cantidad stock”, “Cantidad total”, “Urgente”, “Urgente docenas”, “Stock mínimo”, “Stock terminado”, “Pendiente fab doc.”: en el formulario VB6 no están ligadas a campo; si en algún cliente se rellenan, sería por código no revisado aquí. En Synap ya tenemos Stock terminado y Urgente con valor real; el resto se puede considerar opcional o para una segunda iteración.

4. **DepositoOrigen**
   - En VB6 existe en Lista_Pedidos_OPT y se usa sobre todo en “Parte produccion”. En “Pedido produccion” también se usa en el flujo de Desarme (depósito origen/destino). En Synap, el depósito se elige en el flujo de **Registrar OPP** o en CargaMovStock equivalente; no es obligatorio replicar DepositoOrigen en agrupar, pero se puede documentar como diferencia.

5. **Tab Unidades en agrupar**
   - Ya incorporamos el desglose por unidades (componentes de recetas) en agrupar. En VB6 no hay una grilla “unidades” en Lista_Pedidos_OPT; el desarme se hace al abrir CargaMovStock. Nuestro tab Unidades es un **añadido** útil y no rompe la paridad con lo que “muestra” la selección en VB6.

---

## 6. Resumen para iterar

- **Objetivo:** que en **/mpr/demanda/ventana-pack/agrupar/** se vea la misma **información** que en VB6 corresponde al “renglón global” elegido, adaptado a **selección múltiple** (varias filas en lugar de una).
- **Ya alineado:** Cod. Sist, Artículo, Stock terminado, Cant. urgente, Cant. a fabricar, Pedidos (tooltip). Tab Unidades como plus.
- **Ajustes sugeridos (sin implementar aún):**
  1. Añadir columna **Cant. Pedida** en la tabla Packs de agrupar (valor solo lectura).
  2. Valorar añadir **Pendiente fab.** (cantidad_pendiente_prod) como columna solo lectura en agrupar para paridad con VB6.
  3. Dejar documentado que las columnas VB6 con DataField vacío (Cantidad stock, Cantidad total, Urgente docenas, Stock mínimo, Pendiente fab doc.) no están implementadas en VB6 desde el recordset y en Synap solo incorporamos las que tienen sentido (Stock terminado, Urgente).
  4. Seguir iterando con más requisitos (por ejemplo DepositoOrigen, o reglas de negocio de “Pedido produccion” vs “Parte produccion”) si hace falta.

---

## 7. Referencias en código VB6

- **Formulario:** `administranet_vb6/Formularios/Lista_Pedidos_OPT.frm`
- **Subrutina:** `Selecciona_Renglon_Global` (aprox. líneas 2788–3068)
- **Disparo:** `Grid_Global_DblClick` (línea 4209), menú F12 `keySelecComp` (4243)
- **Data_Global RecordSource:** líneas 3310–3314 (Pedido produccion)
- **Grid_Global:** definición columnas líneas 985–1248, Caption “Global de artículo para producir”
