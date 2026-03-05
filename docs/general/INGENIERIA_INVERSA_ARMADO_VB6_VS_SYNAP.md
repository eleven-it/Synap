# Ingeniería inversa: Armado en VB6 (CargaMovStock.frm) vs Synap MPR

**Objetivo:** Documentar el flujo completo de Armado en AdministraNET VB6 (formulario **CargaMovStock.frm**; no existe CargaIngStock.frm) y contrastar con la implementación en Synap MPR para verificar alineación al 100%.

---

## 1. Flujo VB6 – Armado en CargaMovStock.frm

### 1.1 Identificación del motivo

- **Motivo en lista:** `Motivo.AddItem "Armado", 8` → **ListIndex = 8** (noveno ítem, base 0).
- **Código numérico en BD:** En Synap `MOTIVOS_MOVIMIENTO` el código es **9** (Armado); en VB6 el motivo se guarda como texto `"Armado"` en `movimiento_stock.motivo_movimiento`.
- **Condiciones de pantalla:** Para Armado (y Desarmado) se exige **Depósito origen** y **Depósito destino**; si no, mensaje "Debe completar el deposito destino" (líneas 4782-4790). Para ListIndex 8 o 9, `DepositoDestino.Enabled = False` tras elegirlo (línea 4769).

### 1.2 Validación previa al agregar renglón

Al agregar un renglón con motivo Armado (8), se llama a **`ensamble_desarme`** (líneas 4869-4874):

1. **Resolución del artículo:**
   - Si el usuario ingresó **id_en_abm** (conjunto): se busca `articulo` con `id_en_abm = ID_Art`; si existe y `ensamblado = "Si"`, se reemplaza `ID_Art` por ese artículo (`IDArt`). Si `ensamblado = "No"` se sale sin hacer nada.
   - Si no, se usa `ID_Art` tal cual.

2. **Conjunto y fórmula:**
   - Se obtiene `articulo.id_en_abm` para ese `ID_Art`.
   - Si no hay `id_en_abm` o es 0, se sale con error "El artículo no tiene definido una formula de ensamblaje".

3. **Validación `en_abm.descuenta_en`:**
   - Se lee `en_abm.descuenta_en` para ese `id_en_abm`.
   - **Solo si `descuenta_en = "Mstock"`** se permite continuar; si no, mensaje "Error: El artículo no esta definido para ser utilizado por este proceso" y se sale.

4. **Componentes:**
   - Se abre `en_abm_formula` con `id_articulo`, `cantidad_articulo`, `tipo_unidad`, `cantidad_unidad_display`, `cantidad_dividir` para ese `id_en_abm`.
   - Si no hay registros, mensaje "El artículo no tiene definido una formula de ensamblaje" y se sale.

### 1.3 Orden de generación de renglones (Armado, ListIndex 8)

1. **Entrada (producto armado):**
   - `MstockE(ID_Art, Cantidad.Text, id_stock_en_abm, DepositoDestino.BoundText)`
   - Añade **un** renglón en `cuerpostock_mstock`: artículo = producto armado, **Entrada** = cantidad, **ES** = "Entrada", **CodDeposito** = DepositoDestino (parámetro `id_depositoE`).

2. **Salidas (componentes):**
   - Por cada fila de `en_abm_formula`:  
     `CantArt = Cantidad.Text * cantidad_articulo`  
     `MstockS(id_articulo, CantArt, CantForm, id_stock_en_abm, DepositoOrigen.BoundText, tipo_unidad, cantidad_unidad_display, cantidad_dividir)`
   - Cada llamada añade un renglón en `cuerpostock_mstock`: artículo = componente, **Salida** = CantArt, **ES** = "Salida", **CodDeposito** = DepositoOrigen.

**Orden físico en la grilla (y luego en `stock`):** primero 1 renglón Entrada (producto armado), después N renglones Salida (componentes).

### 1.4 MstockE (entrada)

- Añade un registro en **cuerpostock_mstock** (temporal) con:
  - IDArt, CodigoArticulo, Descripcion, Cantidad, **Entrada** = Cant (o según presentación), ES = "Entrada", CodDeposito = id_depositoE.
  - Si `Principal.utiliza_embalaje = "Si"` se usan multiplicador_vta/multiplicador_comp y cantidad_pres_comp desde `articulo` / `articulo_prov`.
  - Precios (PrecioCostoxU/R, PrecioVentaxR, etc.), tipo_art, id_manual, **Lote** (nro_lote, vto_lote si articulo.Lote = "Si").
- No escribe aún en `stock` ni `stock_deposito`; eso ocurre al **Aceptar**.

### 1.5 MstockS (salida)

- Añade un registro en **cuerpostock_mstock** con:
  - IDArt, CodigoArticulo, Descripcion, Cantidad, **Salida** = Cant (o según presentación/bulto/display), ES = "Salida", CodDeposito = id_depositoS.
  - Si utiliza_bulto_cerrado o utiliza_display, usa tipo_unidad, cantidad_unidad_display, cantidad_dividir.
  - Para **Armado (8)** con artículo con Lote = "Si": se muestra DataLote con lotes del artículo en **DepositoOrigen** (ordenados por fecha_vto ASC) para que el usuario elija lote en la salida.

### 1.6 Aceptar_Click – Persistencia

- Se recorre **CuerpoStock.Recordset** (cuerpostock_mstock) y por cada renglón:
  - **Armado (8):** Si Origen ≠ Destino, para cada renglón se usa el depósito correcto:
    - Si ES = "Entrada" → se abre `stock_deposito` por (id_articulo, **DepositoDestino**).
    - Si ES = "Salida" (insumos) → se abre `stock_deposito` por (id_articulo, **DepositoOrigen**).
  - **CodDeposito en tabla stock:** Se asigna con la función **IdDeposito()** (líneas 9712-9762): para Armado (8), si ES = "Entrada" → DepositoDestino; si no (insumos) → DepositoOrigen.
  - **Validación de stock en salidas:** Si `Principal.salida_sin_stock = "No"` y el renglón tiene Salida y el artículo no usa lote, se valida `rs_saldo_stock.Saldo >= Salida * cantidad_multiplicar`; si no, mensaje "No hay stock suficiente..." y rollback.
  - Se escribe en **stock** (Entrada/Salida, Saldo, CodDeposito, etc.) y se actualiza **stock_deposito** (saldo).
  - Para Armado/Desarmado con lote se llama a `Lote_ed` (id_lote, stock_lote_deposito) y se graban en el renglón stock.

- **Cabecera movimiento_stock** (líneas 4327-4395):
  - motivo_movimiento = Motivo (texto "Armado").
  - deposito_origen = DepositoOrigen.BoundText.
  - **deposito_destino:** Solo si Motivo.ListIndex = 5 (Transferencia) se usa DepositoDestino; **en todos los demás casos (incluido Armado) se guarda DepositoOrigen**. Es decir, en VB6 la cabecera de Armado tiene deposito_destino = deposito_origen (no refleja el depósito de destino del producto armado).
  - **tipo_mov:** En VB6 **solo** se asigna para ListIndex 10 (OPT) y 11 (OPP). Para Armado (8) **no** se setea tipo_mov; queda Null o valor por defecto. La identificación del movimiento como Armado es por **motivo_movimiento = "Armado"**.

### 1.7 Resumen lógico VB6

| Aspecto | VB6 (CargaMovStock) |
|--------|-----------------------|
| Origen/destino lógico | Origen = componentes, Destino = producto armado |
| Orden renglones en stock | 1 Entrada (producto armado) + N Salidas (componentes) |
| CodDeposito por renglón | Entrada → DepositoDestino; Salida → DepositoOrigen (vía IdDeposito()) |
| Cabecera movimiento_stock | deposito_origen = Origen; deposito_destino = **Origen** (no Destino) |
| tipo_mov | No se setea para Armado (solo OPT/OPP) |
| Validación previa | descuenta_en = "Mstock"; fórmula con al menos un componente |
| Validación stock componentes | En Aceptar, por renglón Salida; si salida_sin_stock = "No" exige saldo >= Salida |
| Lote | Soporta lote en salida de componentes (selección de lote en depósito origen) |
| Bulto/Display | MstockE y MstockS aplican multiplicadores y tipo_unidad según configuración |

---

## 2. Flujo Synap MPR – Armado

- **Servicio:** `ejecutar_armado(base_empresa, id_usuario, id_en_abm, cantidad_a_armar, deposito_origen, deposito_destino)` en [mpr/services.py](mpr/services.py).
- **Validaciones:** BOM existe y tiene componentes; existe artículo armado (ensamblado='Si', id_en_abm); **stock de cada componente en deposito_origen >= cantidad_articulo * cantidad_a_armar** (antes de escribir).
- **Cabecera movimiento_stock:** motivo_movimiento = "Armado", **deposito_origen** = depósito componentes, **deposito_destino** = depósito producto armado, **tipo_mov = "Armado"**.
- **Orden de renglones en stock:** primero **todas las Salidas** (componentes desde deposito_origen), luego **una Entrada** (producto armado en deposito_destino). Campo **Orden** se incrementa (1..N para salidas, N+1 para entrada).
- **stock y stock_deposito:** Por cada componente: INSERT stock (Salida, CodDeposito = deposito_origen), UPDATE/INSERT stock_deposito (resta saldo). Para el armado: INSERT stock (Entrada, CodDeposito = deposito_destino), UPDATE/INSERT stock_deposito (suma saldo).
- **Validación descuenta_en:** En `ejecutar_armado` se valida que `en_abm.descuenta_en = "Mstock"` (si viene informado); si no, se devuelve error. Si la columna no existe o viene vacía, se permite (compatibilidad).
- **Lote en componentes:** Para artículos con `articulo.Lote = 'Si'` se consume desde lotes en depósito origen (FIFO por fecha vto); se actualiza `lote_stock` y `lote.stock_total_lote` y se escriben renglones en `stock` con `id_lote` cuando la tabla lo tiene; un solo UPDATE de `stock_deposito` por componente. Si faltan tablas `lote`/`lote_stock` o el artículo no usa lote, se mantiene el comportamiento sin lote.
- **Bulto/Display:** No se aplican en armado MPR (decisión de producto: descartado para MPR; se usa siempre cantidad en unidad base).

---

## 3. Comparación y alineación

### 3.1 Alineado (misma lógica o mejor en Synap)

| Aspecto | VB6 | Synap | Nota |
|---------|-----|-------|------|
| Depósito por renglón | Entrada → Destino, Salida → Origen | Igual | Synap correcto en stock y en cabecera |
| Cabecera deposito_origen / deposito_destino | Origen correcto; destino = Origen (incorrecto en cabecera) | Origen = componentes, Destino = producto armado | Synap más coherente que VB6 |
| tipo_mov | No se setea para Armado | "Armado" | Synap permite filtrar por tipo_mov |
| Validación stock componentes | En Aceptar, renglón a renglón | Antes de escribir, en una transacción | Synap evita escribir parcialmente |
| Un movimiento, N+1 renglones | Sí | Sí | Un codigo_movimiento, varias filas stock |
| Tablas tocadas | movimiento_stock, stock, stock_deposito | Igual | Sin tablas extra en VB6 para Armado |

### 3.2 Diferencias aceptables (diseño)

| Aspecto | VB6 | Synap | Recomendación |
|---------|-----|-------|----------------|
| Orden de renglones en stock | Entrada primero, luego Salidas | Salidas primero, luego Entrada | Aceptable; saldos finales correctos; si algún reporte ordena por Orden, Synap es consistente con su numeración |
| Momento de validación stock | Al confirmar (Aceptar) | Antes de INSERT | Synap más claro y atómico |

### 3.3 Gaps (estado actual)

| Gap | VB6 | Synap | Estado |
|-----|-----|-------|--------|
| **descuenta_en = "Mstock"** | Exige que en_abm.descuenta_en = "Mstock" para permitir armado | **Implementado:** en `ejecutar_armado` se valida; si viene informado y no es "Mstock", se devuelve error. Si vacío (ej. columna inexistente), se permite. | Cerrado |
| **Lote en componentes** | Para artículos con Lote = "Si", DataLote en depósito origen; se graba id_lote y se actualiza lote_stock | **Implementado:** consumo FIFO desde lotes en depósito origen; UPDATE lote_stock y lote.stock_total_lote; INSERT stock con id_lote cuando la tabla tiene la columna; un UPDATE stock_deposito por componente. Opción de elegir lote por componente (parámetro lotes_componentes) queda para fase posterior. | Cerrado (FIFO) |
| **Bulto/Display en cantidades** | MstockE/MstockS usan multiplicador y tipo_unidad | **Descartado para MPR:** por decisión de producto no se implementan bulto/display en armado MPR; se usa siempre cantidad en unidad base. | No implementado (intencional) |

---

## 4. Conclusión

- **Lógica de negocio principal:** Sí está alineada: un movimiento Armado con depósito origen (componentes) y destino (producto armado), renglones de salida por componente y uno de entrada por producto armado, actualización de stock_deposito y validación de stock de componentes. La cabecera en Synap es además más correcta (deposito_destino real).
- **Implementado en Synap:**  
  1) **descuenta_en = "Mstock"** se valida en `ejecutar_armado`; si informado y distinto de "Mstock", se rechaza el armado.  
  2) **Lote en componentes:** consumo FIFO desde lotes en depósito origen; actualización de lote_stock y lote; renglones en stock con id_lote cuando la tabla lo soporta.  
  3) **Bulto/Display:** no se implementan en armado MPR por decisión de producto (descartado).

El proceso queda alineado con VB6 en lo crítico (descuenta_en y lote en componentes). La selección manual de lote por componente (parámetro opcional) y la UI para elegir lote quedan como mejora opcional en una fase posterior.

---

## 5. Armado solo por OPT (refactor Synap)

En Synap el armado **solo está disponible en contexto de OPT** (no existe el flujo "Armado por lista de materiales" desde el menú).

### 5.1 Reglas de negocio

- **Entrada única:** El armado se accede desde el detalle de una OPT (tarjeta "Armado desde esta OPT"), nunca desde un ítem de menú directo.
- **Habilitación:** La tarjeta "Armado desde esta OPT" está **habilitada** solo cuando:
  1. La OPT tiene **Pendiente = 0** (todo lo pedido ya fue registrado por OPP).
  2. Existe al menos una línea armable (artículo con BOM) con **cantidad restante por armar > 0**.
- **Deshabilitación:** Si Pendiente > 0 se muestra tarjeta deshabilitada con texto "Disponible cuando pendiente = 0 (todo registrado por OPP)". Si Pendiente = 0 pero ya se armó todo (cantidad ya armada ≥ cantidad pedida en todas las líneas armables), se muestra "Todo el armado de esta OPT ya fue registrado".
- **Fases del flujo OPT:** Pedida → En producción → Producida (OPP) → Pendiente 0 → **Armado** → **Cerrado**. Todas se muestran en la barra de estado del detalle de la OPT. "Armado" se considera cumplido cuando para todas las líneas armables la cantidad ya armada ≥ cantidad pedida. "Cerrado" cuando `en_proceso_produccion = 'No'`.

### 5.2 Trazabilidad de cantidad ya armada

- Al ejecutar armado desde una OPT, se pasa `id_lista_produccion` a `ejecutar_armado`; el **detalle** del movimiento se graba como `"Armado OPT {id_lista} (conjunto {id_en_abm}, {cantidad} u.)"`.
- El servicio **`get_cantidades_armadas_por_opt(base_empresa, id_lista_produccion)`** devuelve un dict `id_articulo -> cantidad_ya_armada` consultando movimientos tipo Armado cuyo detalle contiene esa OPT y sumando las entradas del artículo armado en la tabla `stock`.
- **Cantidad restante por armar** = max(0, cantidad_pedida - cantidad_ya_armada) por línea.

### 5.3 Pantalla de armado

- **URL:** `armado/?id_lista={id_lista}`. Sin `id_lista` se redirige al listado de OPT con mensaje informativo.
- **Contenido:** Tabla **Producto | Cantidad** con las líneas de la OPT que son armables; la cantidad mostrada es la **restante por armar**. No hay dropdown de conjunto (los productos vienen de la OPT). Depósitos origen (componentes) y destino (producto armado) se eligen como antes. Un solo botón "Ejecutar armado" que ejecuta el armado para cada línea con restante > 0 (mismo par de depósitos para todos).
- En el detalle de la OPT la tabla de artículos puede incluir columnas "Armado" y "Restante por armar" para las líneas armables.

### 5.4 Menú y acceso

- No existe el ítem de menú "Ejecutar armado (Lista de materiales)". El listado de conjuntos BOM (`mpr:bom_list`) sigue disponible en la sección "Lista de materiales" para consulta.
