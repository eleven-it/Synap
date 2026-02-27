# Flujo VB6 "Pedido producción" (motivo OPT) – Análisis extremo a extremo

Documento de análisis del proceso completo en el proyecto VB6 AdministraNET cuando se selecciona el motivo **"Pedido producción"** en CargaMovStock: desde la visibilidad del botón Busca_PEDI, apertura de Lista_Pedidos_OPT, selección de pedido/artículo y grabación del movimiento. Incluye tablas, campos y desvíos posibles.

**Referencias:** `CargaMovStock.frm`, `Lista_Pedidos_OPT.frm`. Plan de referencia: `docs/general/PLAN_PRINCIPAL_FODA_BRECHAS_SYNAP.md`.

---

## 1. Punto de entrada: CargaMovStock.frm

- **Motivo:** "Pedido producción" → `Motivo.ListIndex = 10` (CargaMovStock.frm, líneas 3198-3202: `Motivo.AddItem "Pedido producción", 10`).
- Al elegir este motivo:
  - `Label_Busca_PEDI` y `Busca_PEDI` pasan a **Visible = True** (líneas 6538-6544).
  - Caption del label: **"Lista de pedidos pendientes"**.
  - **DepositoDestino** y **LabelDestino** quedan **ocultos** (no se usa depósito destino en este motivo).
  - El usuario debe tener ya elegido **DepositoOrigen** en CargaMovStock.

---

## 2. Clic en Busca_PEDI (CargaMovStock)

**Validaciones antes de abrir Lista_Pedidos_OPT (líneas 5693-5727):**

- Se abre conexión y se consulta **comp_ped** + **cliente**:
  - `Anulado = 'No'`, `TipoComprobante IN ('PED')`, `tipo_pedido_opt = 'Fabrica'`, `Estado = 'Pendiente'`.
- Si no hay registros → mensaje *"No existen pedidos pendientes para generar OPT"* y no se abre el listado.

**Apertura de Lista_Pedidos_OPT:**

- `Lista_Pedidos_OPT.TipoComprobante = "Pedido produccion"`.
- `Lista_Pedidos_OPT.TabDatos.Tab = 2` (pestaña de vista “global” por artículo).
- `Lista_Pedidos_OPT.Inicial` → dispara `Consulta_Busqueda` en Lista_Pedidos_OPT:
  - **DataComprobante:** pedidos PED, no anulados, `estado_pedido_opt = 'Pendiente'`, `tipo_pedido_opt = 'Fabrica'`, filtro por búsqueda y rango de fechas (Fecha1, Fecha2).
  - **Data_Global:** `lista_produccion_agrupada` + articulo, `cantidad_pendiente_prod <> 0`, orden por nombre artículo.
  - **DepositoOrigen** en Lista_Pedidos_OPT se toma de **CargaMovStock.DepositoOrigen** (Lista_Pedidos_OPT.frm línea 3381).

Tablas leídas en esta fase: **comp_ped**, **cliente**, **lista_produccion_agrupada**, **articulo**.

---

## 3. Lista_Pedidos_OPT.frm – Estructura de datos

| Control / Data     | Origen (Pedido producción)                                                                 | Uso |
|--------------------|---------------------------------------------------------------------------------------------|-----|
| **DataComprobante** | comp_ped + cliente (PED, Pendiente, Fabrica, fechas, búsqueda)                            | Grilla de pedidos (GridComprobante) |
| **Data_Global**     | lista_produccion_agrupada + articulo (pendiente > 0)                                       | Grilla “global” por artículo (Grid_Global) |
| **Data_Renglon**    | Se rellena al hacer clic en un pedido: **stockp** del pedido con `articulo.ensamblado = 'Si'` | Grilla de renglones (GridRenglon) |
| **DepositoOrigen**  | Copia de CargaMovStock.DepositoOrigen en Consulta_Busqueda                                 | Depósito de producción |

Hay **dos flujos de selección** distintos.

---

## 4. Flujo A: Selección por artículo (vista agrupada – Tab 2)

- Usuario está en la pestaña que muestra **Data_Global** (artículos con pendiente).
- Acción: doble clic en **Grid_Global** o tecla de “Seleccionar comprobante” → **Selecciona_Renglon_Global** (Lista_Pedidos_OPT.frm, aprox. líneas 2788-3062).

**Lógica:**

1. Se toma el artículo de la fila actual: **Data_Global.Recordset.Fields!id_articulo**.
2. Se abre **lista_produccion_agrupada** + articulo para ese `id_articulo` (con `cantidad_pedida` o `cantidad_pendiente_prod` no nulos).  
   Campos relevantes: **id_lista_produccion**, **id_articulo**, **cantidad_pendiente_prod**, y campos de artículo (CodigoArticulo, Descripcion, PrecioCostoxU, etc.).
3. Para cada fila de ese recordset:
   - Si **articulo.ensamblado = 'Si'**: se llama **Desarme(...)** con `id_lista_produccion` como `id_stock`.  
     Desarme genera movimientos de stock y llama **MstockE**, que hace **AddNew** en CargaMovStock.CuerpoStock y asigna **id_stock** = id_lista_produccion, **cantidad_armada_opt**, **cantidad_pendiente_opt**, Entrada, etc.
   - Si **articulo.ensamblado <> 'Si'**:
     - **AddNew** en **CargaMovStock.CuerpoStock** (cuerpostock_mstock) con: CodigoArticulo, IDArt, Descripcion, Cantidad, Entrada, cantidad_pendiente_opt, ES = "Entrada", PrecioCostoxU, CodigoMovimiento (del pedido), nro_pedi, codmov_nro_pedi, CodDeposito (según Principal.deposito_salida_pedidos), etc.  
     - En el código revisado **no se asigna id_stock** en este ramal (solo se asigna en MstockE para ensamblados). Eso puede hacer que al grabar el movimiento no se actualice **lista_produccion_agrupada** para esos ítems (ver sección 7).
4. **DepositoOrigen** en CargaMovStock se deja igual o se sincroniza con Lista_Pedidos_OPT.DepositoOrigen.
5. Se llama **CargaMovStock.CalculoTotales**, mensaje de éxito, **Unload** del formulario.

Tablas/campos tocados en este flujo: **lista_produccion_agrupada**, **articulo**, **stock**, **en_abm_formula**, **CuerpoStock** (cuerpostock_mstock en memoria).

---

## 5. Flujo B: Selección por pedido y por ítem (artículo a artículo)

- Usuario hace clic en un **pedido** en **GridComprobante** (DataComprobante).
- **GridComprobante_Click** (Lista_Pedidos_OPT.frm, aprox. 3983-3894) actualiza **Data_Renglon** con:
  - **stockp** + articulo  
  - `stockp.CodigoMovimiento = DataComprobante.Recordset.Fields!CodigoMovimiento`  
  - `articulo.ensamblado = 'Si'`  
  → Solo se muestran ítems **ensamblados** del pedido.
- Usuario hace doble clic en **GridRenglon** o ENTER → **Selecciona_item** (línea 3084) → **Selecciona_item_Pedido_produccion** (línea 3108).

**Lógica:**

1. Validación: existe fila en **cuerpostock** (no cuerpostock_mstock) con mismo CodigoMovimiento e IDArt y visualiza = 'No'. Si existe → *"El artículo del pedido interno ya fue ingresado"* y sale (líneas 3122-3128).
2. **AddNew** en **CargaMovStock.CuerpoStock** (cuerpostock_mstock) con datos de **Data_Renglon** y **DataComprobante**: IDArt, CodigoArticulo, Descripcion, Cantidad, cantidad_pendiente_opt (de Data_Renglon), ES = "Salida" (fijo en este sub), PrecioCostoxU, CodigoMovimiento, nro_pedi, codmov_nro_pedi, CodDeposito, etc.
3. No se asigna **id_stock** (id_lista_produccion) en este flujo; el ítem viene de **stockp**, no de lista_produccion_agrupada.
4. Mensaje *"Agrego el artículo del pedido al renglón..."*, **CalculoTotales**, formulario permanece abierto (no Unload).

Nota: La validación usa la tabla **cuerpostock**; en CargaMovStock el detalle del movimiento es **cuerpostock_mstock**. Si en tu entorno solo se usa motivo "Pedido producción" con movimiento de stock (mstock), podría ser una inconsistencia (validar contra cuerpostock_mstock o la tabla que corresponda).

---

## 6. Tablas y campos involucrados (resumen)

| Tabla                         | Campos relevantes / uso |
|-------------------------------|--------------------------|
| **comp_ped**                  | CodigoMovimiento, id_comp_ped, TipoComprobante, Anulado, estado_pedido_opt, tipo_pedido_opt, Fecha, NroCompBusq, ImporteVenta, codigo (cliente). |
| **cliente**                  | nombre_cliente (join con comp_ped). |
| **lista_produccion_agrupada** | id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, id_usuario, en_proceso_produccion. En Grabar (CargaMovStock) se actualiza **cantidad_pendiente_prod** usando **id_stock** del renglón como id_lista_produccion. |
| **lista_produccion_detalle**   | codigo_movimiento_pedido, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion, Fecha, id_usuario. Usada en el botón “Actualización” (Actualiza_Pedidos_Produccion), no en el flujo directo de “seleccionar pedido/artículo”. |
| **stockp**                    | CodigoMovimiento, idart, cantidad, cantidad_fab_pendiente_opt, cantidad_pendiente_opt, cantidad_dividir, CodDeposito, etc. Usada para renglones cuando se elige un pedido (Data_Renglon, solo ensamblados). |
| **articulo**                  | idart, CodigoArticulo, NombreArticulo, ensamblado, PrecioCostoxU, tipo_art, Lote, id_manual, etc. |
| **cuerpostock_mstock**         | Detalle del comprobante de movimiento de stock. Campos que se rellenan desde Lista_Pedidos_OPT / CargaMovStock: CodigoMovimiento (temporal 1 hasta grabar), IDArt, Cantidad, Entrada/Salida, ES, cantidad_pendiente_opt, cantidad_armada_opt, **id_stock** (id_lista_produccion cuando viene de agrupada + Desarme), id_en_abm, nro_pedi, codmov_nro_pedi, CodDeposito, Codusuario, visualiza = 'No', etc. |
| **movimiento_stock**          | Encabezado del movimiento; **tipo_mov = "OPT"** cuando Motivo.ListIndex = 10. |
| **stock**                     | Se insertan/actualizan filas al grabar el movimiento (entradas por motivo OPT). |
| **stock_deposito**            | Actualización de saldos por depósito. |
| **lista_produccion_historico**| id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada, id_deposito, codigo_movimiento_mstock, codigo_movimiento_opt, id_usuario, Fecha. Se llenan al grabar desde CuerpoStock (id_stock, cantidad_armada_opt, etc.). |
| **deposito**                  | Depósito origen/destino; Lista_Pedidos_OPT usa el mismo DepositoOrigen que CargaMovStock. |
| **cuerpostock**               | Solo aparece en la validación de Selecciona_item_Pedido_produccion (“ya fue ingresado”); el detalle real del mov. de stock es cuerpostock_mstock. |

---

## 7. Grabación del movimiento en CargaMovStock (motivo 10)

Al confirmar el comprobante de movimiento de stock con motivo "Pedido producción" (CargaMovStock.frm, bloque aprox. 4076-4135 y 4386-4484):

1. **movimiento_stock:** se crea/actualiza con **tipo_mov = "OPT"** (línea 4388).
2. Por cada línea de **CuerpoStock** (cuerpostock_mstock):
   - **stock:** INSERT (entrada).
   - **stock_deposito:** actualización de saldo.
   - Si **Motivo.ListIndex = 10**:
     - **lista_produccion_agrupada:**  
       `WHERE id_lista_produccion = CuerpoStock.Recordset.Fields!id_stock`  
       → `cantidad_pendiente_prod -= cantidad_armada_opt` (y se evita contar dos veces el mismo id_en_abm con id_en_abm_valid).
     - **lista_produccion_historico:** INSERT con id_articulo, cantidades, id_deposito, codigo_movimiento_mstock/opt, etc.

El bloque que actualizaba **comp_ped.estado_pedido_opt** y la relación **opt_ped** está comentado en el .frm revisado (aprox. 4460-4482), por lo que en esta versión no se cambia el estado del pedido ni se escribe opt_ped al grabar.

---

## 8. Desvíos y opciones de selección (mapeo)

| Desvío / opción                         | Dónde                         | Comportamiento |
|----------------------------------------|-------------------------------|----------------|
| Sin pedidos Pendiente + Fabrica        | Busca_PEDI_Click              | No abre Lista_Pedidos_OPT; mensaje "No existen pedidos pendientes para generar OPT". |
| Lista_produccion_agrupada vacía        | Tab 2                         | Data_Global sin registros; no hay artículos para elegir en Grid_Global. |
| Artículo con ensamblado = 'Si' (Flujo A) | Selecciona_Renglon_Global     | Desarme + MstockE; se asigna **id_stock**; al grabar se descuenta lista_produccion_agrupada y se escribe lista_produccion_historico. |
| Artículo con ensamblado = 'No' (Flujo A) | Selecciona_Renglon_Global     | Solo AddNew a CuerpoStock; en el código revisado **no se asigna id_stock** → al grabar, el UPDATE a lista_produccion_agrupada por ese renglón no aplica (posible gap/bug). |
| Pedido seleccionado (Flujo B)          | GridComprobante_Click        | Data_Renglon = stockp del pedido con **ensamblado = 'Si'**; si el pedido no tiene ítems ensamblados, GridRenglon queda vacío. |
| Flujo B – artículo ya cargado          | Selecciona_item_Pedido_produccion | Validación contra **cuerpostock** (CodigoMovimiento + IDArt, visualiza = 'No'); si existe → no agrega y muestra mensaje. |
| Lote obligatorio                        | Selecciona_item_Pedido_produccion | Si articulo.Lote = 'Si' y no hay lote elegido en data_lote → mensaje "debe seleccionar uno" y no agrega. |
| Bulto cerrado / Display                | Ambos flujos                 | Cantidad/Cantidad_pendiente_opt se dividen por cantidad_dividir; se usan tipo_unidad, cantidad_unidad_display, cantidad_bulto. |
| Depósito origen                        | Lista_Pedidos_OPT / CargaMovStock | Lista_Pedidos_OPT.DepositoOrigen se rellena desde CargaMovStock; debe estar informado para Desarme y para lista_produccion_historico.id_deposito. |

---

## 9. Flujo extremo a extremo (resumen)

1. **CargaMovStock:** Usuario elige motivo "Pedido producción" (ListIndex 10) y depósito origen.
2. **Busca_PEDI:** Validación contra comp_ped (PED, Fabrica, Pendiente). Si hay datos, se abre Lista_Pedidos_OPT con Tab 2 y mismo DepositoOrigen.
3. **Lista_Pedidos_OPT:**
   - **Opción A:** Selección en Grid_Global (artículo) → Selecciona_Renglon_Global → carga ítems de lista_produccion_agrupada en CuerpoStock (ensamblados vía Desarme con id_stock; no ensamblados sin id_stock en el código visto).
   - **Opción B:** Selección de pedido en GridComprobante → Data_Renglon = stockp (solo ensamblados) → doble clic en renglón → Selecciona_item_Pedido_produccion → agrega un ítem a CuerpoStock (sin id_stock).
4. **CargaMovStock:** Usuario puede seguir agregando líneas o grabar. Al grabar: movimiento_stock (tipo_mov = OPT), stock, stock_deposito; para líneas con **id_stock** válido: actualización de lista_produccion_agrupada.cantidad_pendiente_prod e INSERT en lista_produccion_historico.
5. **Estado de pedidos:** No se actualiza comp_ped.estado_pedido_opt ni opt_ped en el bloque actual (código comentado).

---

## 10. Botón "Actualización" en Lista_Pedidos_OPT

No forma parte del flujo “seleccionar pedido y cargar en CargaMovStock”, pero alimenta las tablas que ese flujo usa:

- **Evento:** `Actualizacion_Pedidos_Click` (línea 3241) → **Actualiza_Pedidos_Produccion** (línea 3389).
- **Origen:** stockp + comp_ped (PED, Anulado='No', estado_pedido_opt='Pendiente', tipo_pedido_opt='Fabrica', filtros búsqueda y fechas).
- **Escrituras:**
  - **lista_produccion_detalle:** AddNew por (codigo_movimiento_pedido, id_articulo) si no existe; campos: cantidad_pedida, cantidad_pendiente_prod, id_articulo, codigo_movimiento_pedido, id_usuario, en_proceso_produccion = 'No', Fecha.
  - **lista_produccion_agrupada:** por id_articulo, SUM(cantidad_pedida) desde lista_produccion_detalle (en_proceso_produccion = 'No'); UPDATE si existe fila (sumar a cantidad_pedida y cantidad_pendiente_prod), AddNew si no.
  - **UPDATE lista_produccion_detalle** SET en_proceso_produccion = 'Si' WHERE en_proceso_produccion = 'No'.
  - **comp_ped:** estado_pedido_opt = "Produccion" para los codigomovimiento involucrados.
- Todo dentro de transacción (Commit/Rollback).

---

## 11. Relación con el módulo MPR en Synap

- En Synap MPR **sí** está implementada la lógica del botón "Actualización": el servicio `actualizar_pedidos_produccion` llena lista_produccion_detalle y lista_produccion_agrupada desde pedidos PED, no anulados, tipo_pedido_opt='Fabrica' (y opcionalmente estado_pedido_opt='Pendiente'), con filtros fecha y búsqueda. La pantalla Pedido producción trabajo (OPT) incluye el botón "Actualizar" que llama a la URL `ventana_pack_actualizar`.
- En Synap MPR **sí** se lee lista_produccion_agrupada y lista_produccion_detalle, y se escribe en lista_produccion_agrupada al **crear OPT** (Nueva OPT / Pedido producción trabajo (OPT)) y al cerrar OPT / OPP.
- **Flujo Pedido producción trabajo (OPT) en dos pantallas:** (1) Pantalla 1: lista por artículo con cantidad a fabricar de solo lectura; botón "Actualizar" y "Continuar" enviando la selección a `ventana_pack_agrupar`. (2) Pantalla 2 (agrupar): tabla con artículo, cantidad editable y tooltip con pedidos que conforman la cantidad; botón "Generar OPT" crea la OPT y redirige al detalle. El asistente de producción (wizard) incluye un enlace a Pedido producción trabajo (OPT).

---

## 12. Alineación codmov, talonario y nro_comprobante (Aceptar_Click VB6)

Al crear OPT (y OPP, Armado, Reclasificación) en MPR se replica la lógica de CargaMovStock Aceptar_Click:

- **codmov:** SELECT CodigoMovimiento WHERE codigo=1 FOR UPDATE, incremento, UPDATE (igual que VB6 con adLockPessimistic).
- **Talonario MSTOCK:** SELECT por id_punto_venta y TipoComprobante MSTOCK FOR UPDATE; el **nro_comprobante** se arma con el **número actual** del talonario (antes de incrementar), como en VB6 (Nro = ceros_pv & PV & "-" & Ceros_Nro_Comp & Nro).
- **Formato:** En MPR `_formato_nro_comprobante_mstock(id_pv, nro)` devuelve PV en 4 dígitos y Nro en 8 (equivalente a Ceros_Nro_pv y Ceros_Nro_Comp de Principal.frm).
- **nro_comprobante_busq:** Se persiste en movimiento_stock el valor numérico actual del talonario (NroBusq = NroComp en VB6); fallback sin esta columna si la tabla no la tiene.
- **stock:** INSERT por cada línea con CodigoMovimiento = codigo_mov (equivalente al AddNew con contador en VB6).

---

## 13. Imprimir comprobante (PDF)

En VB6, tras grabar el movimiento se pregunta *"¿Desea imprimir el comprobante de Movimiento de Stock?"* y se usa el reporte Crystal **comp_mov_stock.rpt** (parámetros: Fecha, NroMovStock, Usuario, dep_origen, dep_destino, referencia, Detalle, etc.).

En Synap MPR:

- En el **detalle de la OPT** (`opt_detail`) hay un botón **"Imprimir comprobante"**.
- Si la OPT tiene asociado un movimiento de stock (se liberó con `ejecutar_liberar_opt`), el botón abre en nueva pestaña el **PDF del comprobante** generado por el módulo Stock (`stock:movimiento_pdf`), mismo layout que el resto de movimientos (cabecera + renglones con Artículo, Entrada, Salida, Saldo).
- Si la OPT aún no tiene movimiento (solo creada desde Pedido producción trabajo (OPT), sin liberar), el botón aparece deshabilitado con el mensaje: *"Libere la OPT para generar el comprobante de movimiento de stock."*
- La relación OPT → codigo_movimiento se guarda en el modelo **Opt** (campo `codigo_movimiento`), actualizado al ejecutar la liberación.

El usuario debe tener permiso **stock.consultas** para descargar el PDF.

---

## 14. Por qué puede verse información distinta entre VB6 (Lista pedidos OPT) y Synap (Pedido producción trabajo (OPT))

Si la pantalla VB6 "Lista de pedidos pendientes para vincular a OPT" (pestaña "Pedidos globales para producir") muestra datos distintos a la Pedido producción trabajo (OPT) de Synap, las causas más probables son:

1. **Filtros de Actualización**
   - En VB6, el botón "Actualización" (y la búsqueda) usan **Fecha** (desde/hasta) y **Texto** para filtrar qué pedidos PED (Pendiente, Fabrica) entran en `lista_produccion_detalle` y `lista_produccion_agrupada`. Si en VB6 se usan por ejemplo 01/01/2025–25/02/2026, solo esos pedidos alimentan la grilla global.
   - En Synap, si el formulario de Pedido producción trabajo (OPT) **no** envía fecha ni texto al hacer "Actualizar", `actualizar_pedidos_produccion` se ejecuta sin filtros y considera **todos** los pedidos PED Pendiente + Fabrica. Así se cargan más (o menos) registros que en VB6 y los totales por artículo cambian.
   - **Solución:** En Pedido producción trabajo (OPT) (Synap) deben existir campos opcionales **Fecha desde**, **Fecha hasta** y **Texto** (búsqueda), y el botón "Actualizar" debe enviarlos en el POST a `ventana_pack_actualizar` para que el servicio use los mismos criterios que VB6.

2. **Momento de ejecutar Actualizar**
   - La tabla que ve el usuario en ambos sistemas es `lista_produccion_agrupada` (con pendiente > 0). Esa tabla se llena o actualiza **solo** cuando se ejecuta el proceso de "Actualización". Si en VB6 se acaba de ejecutar con un rango de fechas y en Synap no se ha ejecutado con el mismo rango (o se ejecutó sin filtros), los conjuntos de datos serán distintos.

3. **Stock terminado**
   - En Synap, "Stock terminado" = suma de saldos en `stock_deposito` para depósitos con `suma_stock = 'Si'` y no anulados. Si en VB6 "Stock terminado" o "Cantidad stock" se calculan con otros depósitos, otra tabla (p. ej. `stock`) o otra regla, los números no coincidirán. Hay que alinear en documentación o código qué depósitos y qué tabla usa cada sistema.

4. **Columnas mostradas**
   - VB6 muestra "Cantidad pedida", "Cantidad stock", "Stock terminado", "Pendiente fab." etc. Synap muestra "Pend. producción", "Cant. a fabricar", "Cant. urgente", "Stock reserva / Brecha". La equivalencia es: demanda desde `lista_produccion_agrupada.cantidad_pendiente_prod` (Synap: "Pend. producción"); "Cant. a fabricar" = max(0, demanda − stock terminado); "Cant. urgente" = stock terminado − demanda. Si las bases (demanda y stock terminado) difieren por los puntos anteriores, estas columnas también diferirán.

5. **Orden y agrupación**
   - En Synap, `listar_ventana_pack` agrupa por `id_articulo` sumando `cantidad_pendiente_prod` de **todas** las filas de `lista_produccion_agrupada` para ese artículo (varias OP pueden tener el mismo artículo). En VB6 la grilla global también puede ser por artículo. Si en VB6 hay una agrupación distinta (p. ej. por id_lista_produccion y no por artículo), los totales por artículo pueden no coincidir.

Para que los números sean comparables entre VB6 y Synap, conviene: (a) usar en Synap los mismos filtros de fecha y texto que en VB6 al ejecutar "Actualizar", y (b) documentar o unificar la definición de "Stock terminado" (depósitos y tabla).

---

## 15. Columnas VB6 (Grid_Global) vs Synap (Pedido producción trabajo (OPT)) y agrupamiento

**Diferencia de agrupamiento:**

- **VB6 (Lista_Pedidos_OPT, pestaña "Pedidos globales para producir"):** El origen es `Data_Global.RecordSource = SELECT lista_produccion_agrupada.*, articulo.nombrearticulo, articulo.id_manual FROM lista_produccion_agrupada ... WHERE cantidad_pendiente_prod <> 0`. Hay **una fila por cada registro de lista_produccion_agrupada** (por `id_lista_produccion` + `id_articulo`). Un mismo artículo puede aparecer en **varias filas** (varias OP/agrupaciones).
- **Synap (Pedido producción trabajo (OPT)):** Se agrupa **por artículo** (`id_articulo`): se suman `cantidad_pendiente_prod` y `cantidad_pedida` de todas las filas de lista_produccion_agrupada para ese artículo. Hay **una fila por artículo** con totales. Por tanto, en Synap se ve un resumen por artículo; en VB6 se ve el detalle por cada línea de producción (cada id_lista_produccion).

**Mapa de columnas:**

| VB6 Grid_Global (Caption / DataField) | Synap Pedido producción trabajo (OPT) (Pantalla 1) | Notas |
|---------------------------------------|----------------------------------|--------|
| Cod. Sist (id_articulo)               | Código en columna Artículo       | Synap muestra codigo_articulo (ej. id_manual o CodigoArticuloT), no id numérico. |
| Cod. manual (id_manual)               | Incluido en Artículo             | Synap usa codigo_articulo. |
| Articulo (nombrearticulo)             | Descripción en columna Artículo  | descripcion_articulo. |
| Cantidad pedida (cantidad_pedida)     | **Cant. pedida**                 | En Synap: suma de cantidad_pedida por artículo (misma agrupación que pendiente). |
| Cantidad stock (vacío en VB6)         | —                                | VB6 sin DataField; Synap no la muestra. |
| Cantidad total / Urgente / etc. (vacío)| —                               | VB6 sin datos; Synap no los muestra. |
| Stock terminado (vacío en VB6)        | **Stock terminado**              | Synap: SUM(saldo) en stock_deposito para depósitos suma_stock='Si'. |
| Pendiente fab. (cantidad_pendiente_prod) | **Pend. producción**            | Synap: suma de cantidad_pendiente_prod por artículo. |
| Pendiente fab doc (vacío)             | —                                | Synap no lo muestra. |
| —                                     | **Cant. a fabricar**             | Synap: max(0, Pend. producción − Stock terminado). |
| —                                     | **Cant. urgente**                | Synap: Stock terminado − Pend. producción. |
| —                                     | **Stock reserva / Brecha**      | Synap: articulo.stock_reserva y brecha. |

En **Pantalla 2 (Confirmar OPT)** Synap muestra Cod. Sist, Artículo, **Stock terminado**, **Cant. urgente**, **Cant. a fabricar** (editable) y la columna **Pedidos** (tooltip con desglose desde lista_produccion_detalle + comp_ped + cliente).

---

## 16. Cómo se calcula cantidad_pendiente_prod

**Origen del campo:** `cantidad_pendiente_prod` es una columna de la tabla **lista_produccion_agrupada**. Cada fila representa una línea de producción (por `id_lista_produccion` e `id_articulo`) y indica cuántas unidades de ese artículo faltan por producir en esa OP.

**Cómo se alimenta y actualiza:**

1. **Al ejecutar "Actualizar" (Actualiza_Pedidos_Produccion):** Se leen pedidos PED (no anulados, tipo_pedido_opt='Fabrica', estado_pedido_opt='Pendiente') desde **stockp** + **comp_ped**. Por cada (codigo_movimiento_pedido, id_articulo) se inserta o actualiza **lista_produccion_detalle** (cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion='No'). Luego se actualiza **lista_produccion_agrupada** por id_articulo: se suma la cantidad desde lista_produccion_detalle (filas con en_proceso_produccion='No') y se asigna a cantidad_pedida y cantidad_pendiente_prod de la fila agrupada (o se inserta una nueva). Así, cantidad_pendiente_prod pasa a reflejar la demanda pendiente de producir que viene de los pedidos.

2. **Al crear una OPT (crear_opt_multiples_articulos):** Se insertan nuevas filas en lista_produccion_agrupada con cantidad_pendiente_prod = cantidad a fabricar y en_proceso_produccion='Si'.

3. **Al liberar OPT (ejecutar_liberar_opt):** Se descuenta cantidad_pendiente_prod en las filas de lista_produccion_agrupada afectadas (según las líneas liberadas).

4. **Al registrar OPP (ejecutar_opp):** Se descuenta cantidad_pendiente_prod en la fila correspondiente de lista_produccion_agrupada.

**En Pedido producción trabajo (OPT) (Synap):** La columna "Pend. producción" muestra la **suma** de `cantidad_pendiente_prod` de **todas** las filas de lista_produccion_agrupada para ese artículo (varias OP pueden tener el mismo artículo). Es decir: total de unidades pendientes de producir para ese artículo en todas las líneas de producción activas.

---

*Documento generado a partir del análisis de CargaMovStock.frm y Lista_Pedidos_OPT.frm (VB6 AdministraNET). Actualizar al migrar o cambiar el flujo en Synap MPR.*
