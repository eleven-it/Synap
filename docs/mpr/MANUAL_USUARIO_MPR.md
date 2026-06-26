# Manual de usuario – Módulo MPR (Producción)

Este manual describe el uso del módulo MPR en Synap: tablero, demanda, OPT (Pedidos de producción), parte de producción (OPP), Lista de materiales, armado, reclasificación, configuración y reportes.

**Requisitos:** Usuario con acceso al módulo MPR y **empresa activa** seleccionada en sesión (base de datos AdministraNET). Sin empresa activa, el sistema redirige al dashboard.

**Referencias:** Glosario de términos en [GLOSARIO_MPR.md](GLOSARIO_MPR.md). Análisis y flujo en [ANALISIS_MPR_PROPUESTA_MVP.md](ANALISIS_MPR_PROPUESTA_MVP.md). **Pack vs componente (datos e implementación):** [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md).

---

## 1. Acceso al módulo

- Desde el menú de Synap, ingresar a **Producción (MPR)**.
- La pantalla inicial es el **Tablero** (`/mpr/`).

---

## 2. Tablero de control

**Ruta:** Producción → Tablero (`/mpr/`).

### Qué muestra

- **KPIs:** OPT en progreso, **OPT atrasadas** (OPTs con fecha objetivo vencida y pendiente > 0), Unidades pendientes, Ítems urgentes (según demanda y stock).
- **Top urgencias:** Tabla con artículo, descripción, stock terminado, demanda y estado. Las **OPTs vencidas** (fecha objetivo &lt; hoy) aparecen primero con estado **Vencida** (badge rojo) y enlace al detalle de la OPT; luego los ítems de demanda con estado Warning/Ok. Enlace “Ver todo” a la lista de OPT.

**Cuándo un ítem es urgente:** Un ítem aparece como **urgente** (estado **Warning**) cuando el **stock terminado es menor que la demanda** (pendiente de producción). Es decir, cuando hay cantidad pendiente de fabricar: la cantidad a fabricar = max(0, demanda − stock terminado) es mayor que 0. La tabla se ordena por esa cantidad a fabricar (los que más faltante tienen aparecen primero).

| Situación | Estado en tablero |
|-----------|-------------------|
| Stock terminado **≥** Demanda (pendiente) | **Ok** (no urgente) |
| Stock terminado **<** Demanda (pendiente) | **Warning** (urgente) |

Ejemplos: stock 0 con demanda 1260 → Warning; stock 540 con demanda 600 → Warning (faltan 60); stock suficiente para cubrir la demanda → Ok. En la Pedido producción trabajo (OPT), la columna **Cant. urgente** muestra stock terminado − pendiente; si es negativa, indica faltante.

- **Movimientos recientes:** Últimos movimientos de stock tipo OPT, OPP o Armado (comprobante, detalle, fecha).

**Qué se muestra en Movimientos recientes:** La lista se obtiene de la base de datos: últimos movimientos de stock **no anulados** de tipo OPT (Pedido producción), OPP (Parte producción) o Armado, ordenados por número de movimiento (más recientes primero). Por cada movimiento se muestra: **(1) Icono** según el tipo (OPT → liberación, OPP → parte, Armado → armado); **(2) Título:** “OPT liberada”, “OPP registrada”, “Armado completado” o “Movimiento stock”; **(3) Detalle:** por defecto “Comp.” seguido del número de comprobante, o el texto del campo detalle del movimiento (recortado a 50 caracteres) si existe; **(4) Fecha:** fecha del movimiento en formato dd-MM-yyyy (si no hay fecha se muestra “—”). Sirve para ver de un vistazo las últimas liberaciones OPT, partes OPP y armados realizados.

- **OPT en progreso:** Hasta 5 ítems con pendiente; enlace “Ver” al detalle de la OPT y “Liberar” al tablero/acciones.
- **OPT a cerrar:** OPTs con pendiente total 0 y aún en proceso; botón “Cerrar OPT” por cada una (POST que marca la OPT como cerrada).

### Acciones rápidas (header)

- **Armado (Lista de materiales):** Lleva al listado de conjuntos de armado (Lista de materiales).
- **Ver demanda:** Lleva a la Pedido producción trabajo (OPT) (demanda por artículo con stock y cantidad a fabricar).

---

## 3. Demanda

### 3.1 Pedido producción trabajo (OPT) / Ventana Unidades

**Ruta:** Producción → desde Tablero “Ver demanda”, o menú Demanda → Pedido producción trabajo (OPT) (`/mpr/demanda/ventana-pack/`).

**Vista Pack / Unidades:** Toggle para alternar entre demanda por **pack** y desglose por **componentes** (receta/BOM).

- **Docenas:** en las columnas «Docenas» de esta pantalla y en **Confirmar OPT**, el valor mostrado es **unidades ÷ `articulo.cantidad_promedio_bulto`**. Si el bulto es ≤ 0 o no está definido, se usa **12** como divisor (docena clásica). Al editar cantidades **en la pestaña Packs** o en **Confirmar OPT**, la sincronización unidades ↔ docenas sigue el mismo criterio por fila.
- **Pestaña Unidades (BOM):** el **Saldo** del componente es **solo** el de `stock_deposito` en el depósito configurado como **Semi elaborado** (`deposito.tipo_mpr = 'SemiElaborado'`). No se suman otros depósitos aunque tengan `suma_stock = 'Si'`. Si no hay depósito Semi elaborado asignado, el saldo se muestra en **0** y se muestra un aviso.
- **Pestaña Unidades — reserva y trazabilidad:** la política de colchón (`articulo.stock_reserva`) aplica **solo al pack terminado**; en la tabla de componentes la columna **Reserva** se muestra en **0** (no se usa maestro de receta para R). La necesidad se desglosa en **Dem. pedido** (atribuible a `max(0, P_ped − S)` del pack, explotado por BOM) y **Dem. reserva pack** (resto de la cantidad a fabricar del pack atribuible al colchón del terminado), con badge **Origen** (Pedido / Reserva pack / Ped.+res.). **Cant. a fabricar** (componente) = `max(0, Dem. pedido + Dem. reserva pack − saldo en Semi elaborado)`; **Urgente** = `max(0, Dem. pedido − saldo en Semi elaborado)`.

**Qué muestra (tabla):**

- Artículo (código y descripción).
- Saldo (stock terminado en depósitos con `suma_stock = 'Si'`).
- Reserva (indicador de stock mínimo; no es saldo).
- **Origen:** indicador Pedido / Reserva / Ped.+res. según si la demanda viene de líneas PED en detalle, de la fila sintética por reserva (`codigo_movimiento_pedido = 0`) o ambas.
- **Cant. pedido** (**P_ped**): suma en `lista_produccion_detalle` de cantidades vinculadas a comprobantes PED (código de pedido distinto de 0).
- **Dem. reserva** (**Q_res**): cantidad de la fila de detalle con código de pedido **0** (demanda por quiebre de reserva, sincronizada al pulsar **Actualizar**).
- **Cant. parcial fabricada:** unidades de pack ya armadas acumuladas en base (`lista_produccion_agrupada.cantidad_fabricada_acumulada`), incrementadas al confirmar armado (OPA) vinculado a la OPT. Si la columna no existe en la base, se muestra el valor derivado **Cant. total pedida en agrupada − Pendiente por producir** como respaldo.
- **Pedido(s):** icono con tooltip que lista pedidos reales (`comp_ped` + `cliente`) y, si aplica, una línea **Demanda reserva** con la cantidad **Q_res**. Los pedidos se ordenan por número de comprobante descendente.
- **Cant. a fabricar:** **max(0, P_ped + R − S)** con **R** = `articulo.stock_reserva` y **S** = saldo terminado (depósitos `suma_stock = 'Si'`). **Q_res** ya refleja la parte de meta por reserva persistida en detalle; no se suma dos veces a **R**.
- **Cant. urgente:** **max(0, P_ped − S)**. La reserva de artículo y **Q_res** no incrementan la urgencia respecto al saldo.
- Stock reserva / Brecha (si existe `articulo.stock_reserva`).

**Acciones:**

- **Checkbox por fila:** Marque los artículos a incluir. **Cant. a fabricar** es editable por fila en la pestaña **Packs** (esa es la cantidad que se envía al pulsar Continuar).
- **Continuar:** Visible debajo de ambas pestañas; envía la selección y las cantidades de **Packs** a la pantalla **Confirmar OPT**. La pestaña **Unidades** muestra solo el desglose por componente (puede diferir del pack).
- **Crear OPT (una fila):** Enlace “Crear OPT” que abre Nueva OPT con el artículo preseleccionado.
- **Nueva OPT (header):** Crear una orden nueva sin preselección.

### 3.1.1 Confirmar OPT (agrupar)

**Ruta:** Tras marcar artículos y pulsar **Continuar** en Pedido producción trabajo (OPT) (`/mpr/demanda/ventana-pack/agrupar/`).

Se muestra una **única tabla Unidades**: componentes de las recetas (BOM) de los packs seleccionados, con columnas Cod. Sist, Artículo, Saldo (solo Semi elaborado), Reserva (0 en componentes), Cant. pedida, **Dem. pedido**, **Dem. reserva pack**, **Origen**, **Cant. a fabricar** (editable: unidades y docenas, precargadas según la cantidad a fabricar elegida en la pantalla anterior y la explosión BOM), Urgente. **No** se solicita operario en esta pantalla (el operario se asigna en OPP y en Armado). Si la base tiene la columna `fecha_objetivo` en lista_produccion_agrupada, se muestra además el campo **Fecha objetivo** (opcional): una sola fecha para toda la orden. Esa fecha se usa para el KPI **OPT atrasadas** en el tablero (OPTs con fecha objetivo vencida y pendiente &gt; 0) y para priorizar OPTs **vencidas** en rojo en Top urgencias (informativo; uso en estadísticas queda para más adelante). El usuario puede ajustar las cantidades, indicar la fecha objetivo si aplica, y pulsar **Generar OPT** para **crear** la OPT. Tras generarla, se redirige al **Detalle de la OP**. La **ejecución** del movimiento de stock (liberar a producción) se hace automáticamente si hay un depósito con tipo «Producción» en Config. Depósitos (véase 4.4 y sección 8).

### 3.2 Pedidos a fábrica

**Ruta:** Demanda → Pedidos a fábrica (`/mpr/demanda/pedidos-fabrica/`).

Listado de pedidos de venta (PED) con estado de producción (Pendiente, Produccion, Terminado). Filtro opcional por estado de producción. La única fuente de demanda para fabricación son los pedidos en estado Pendiente. Solo lectura; sirve de contexto para la demanda que alimenta las OP.

---

## 4. Pack y componentes: cómo los identifica el sistema

En AdministraNET la tabla **`articulo` no tiene un campo único** que diga «soy pack» o «soy componente» para todos los procesos. Synap usa **criterios distintos según el flujo**. Detalle técnico: [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md).

### 4.1 Campos de `articulo` que debe conocer

| Campo | Uso en MPR |
|-------|------------|
| **ensamblado** | `'Si'` → artículo **resultado** de un armado con **lista de materiales** (pack BOM). |
| **id_en_abm** | Número del **conjunto** / receta en `en_abm`. |
| **cantidad_promedio_bulto** | Unidades por bulto para mostrar cantidades en **docenas · unidades** (no define si es pack o componente). |
| **stock_reserva** | Reserva del **terminado** en ventana demanda (no es componente). |
| **Lote** | `'Si'` → al armar se descuenta stock por **lote** (orden FIFO por vencimiento). |

Los **componentes** de una receta **no** se marcan en `articulo`: están en la tabla **`en_abm_formula`** (por cada `id_en_abm`).

### 4.2 Tres situaciones en pantalla

**A) Lista de materiales y armado con receta**

- **Pack:** artículo con `ensamblado = 'Si'` e `id_en_abm` del conjunto (se asigna en **Editar conjunto** → Artículo armado).
- **Componentes:** filas del conjunto en **Componentes** (`en_abm_formula`).

**B) Demanda, OPT y OPP**

- **Pack:** el artículo de cada línea de la OPT (`lista_produccion_agrupada`).
- **Componentes:** los que salen al **desglosar la receta** del pack (pestaña Unidades, paso OPP del asistente). Los movimientos de stock de OPT/OPP mueven **componentes**, aunque usted cargue cantidades pensando en packs.

**C) Armado surtido**

- **Pack:** solo los artículos **habilitados en MPR** (tabla Synap; comando `mpr_cargar_packs_armado_surtido` o admin Django). **No** se usa `ensamblado` para elegir el pack.
- **Componentes:** los que usted agrega en la pantalla Armado surtido (artículos con stock en el depósito origen, p. ej. 2.ª selección).

### 4.3 Qué configurar en datos

| Objetivo | Acción |
|----------|--------|
| Armar con receta fija | Lista de materiales → conjunto + componentes + artículo armado (`ensamblado`/`id_en_abm`). |
| Armar surtido | Habilitar el `IDArt` del pack terminado en config MPR (comando o admin). |
| Ver armado en detalle OPT | El pack de la línea debe tener receta (`id_en_abm`) para «Armado desde esta OPT»; **Armado surtido** se habilita si la OPT está en curso, hay al menos una **OPP** registrada y alguna cantidad fue a **2.ª selección**. |

---

## 5. OPT (Pedidos de producción)

### 5.0 Asistente de producción (wizard)

**Asignación de operarios (trazabilidad por fase):**
- En **Generar OPT** (Confirmar OPT / agrupar) **no** se muestra columna operario; la OPT se crea sin pedir operario en ese paso.
- En **OPP** el operario es obligatorio por componente con cantidad > 0.
- En **Armado** el operario es obligatorio por línea/pack con cantidad > 0.

**Ruta:** Producción → Asistente de producción (`/mpr/wizard/`).

Flujo guiado: **1. Crear orden (OPT)** → **2. Confirmar** (crear OPT y liberar a producción en un solo paso, si existe un depósito con tipo «Producción») → **3. Crear OPP** (cantidades por depósito destino; solo >0 generan movimiento) → **4. Armado** (condicional) → **5. Cierre**. Debe existir un depósito con tipo **Producción** en Config. Depósitos; al confirmar el stock se registra allí sin pedir selección.

**Pasos del asistente:**

1. **Paso 1 – Crear orden de producción (OPT):** Artículo, cantidad pedida y opcionales (depósito de producción opcional, prioridad, fecha objetivo). Al continuar no se guarda aún en base de datos.
2. **Paso 2 – Confirmar orden:** Resumen (artículo, cantidad; el depósito de entrada es el marcado como **Producción** en Config. Depósitos). Al pulsar **Confirmar y liberar a producción** se crea la OPT en base de datos y se ejecuta la liberación (movimiento OPT) hacia ese depósito. No se elige depósito en pantalla.
3. **Paso 3 – Crear OPP:** Tabla por componente × depósito destino (excepto producción). En cada celda se cargan **docenas** y **unidades sueltas**: el sistema convierte a unidades totales con **1 docena = 12 unidades** (fijo en OPP; no usa el bulto del artículo). La columna **Pendiente a distribuir** muestra el saldo en **docenas · unidades** (misma regla de 12 unidades por docena) y se actualiza al cargar cantidades. Solo cantidades totales > 0 generan movimiento (Producción → Semi Elaborado / Scrap / 2da Selección). **Cada componente con cantidad > 0 requiere operario**. La suma por componente en unidades no puede superar el **pendiente a distribuir**. **Si tras registrar una OPP la columna Pendiente a distribuir sigue siendo mayor que cero** en algún componente, el asistente **permanece en este paso** para poder registrar **otra OPP** (p. ej. otro operario); cuando ya no queda nada por distribuir, pasa al paso 4 (Armado). Al confirmar **Registrar OPP** se muestra modal de espera.
4. **Paso 4 – Armado (condicional):** Solo si el artículo tiene lista de materiales. Ejecutar armado por línea/pack (cantidad, depósitos) y **operario por línea**, u omitir y continuar. Al confirmar **Ejecutar armado** también se muestra modal de espera.
5. **Paso 5 – Cierre:** Resumen, enlaces a **Registrar OPP**, **Ver detalle de la OPT** y **Cerrar OPT** (si pendiente = 0). **Finalizar asistente** limpia el wizard y lleva al detalle o al tablero.

En cualquier paso puede **Salir del asistente**; se limpia el estado sin modificar lo ya guardado.

**Nota:** En AdministraNET, "OP" corresponde a Orden de Pago; en MPR se usa solo **OPT** (Pedido de producción / orden de producción).

---

### 5.1 Lista de OPT

**Ruta:** Producción → Lista de OPTT (`/mpr/opt/`).

**Filtros:**

- **Estado:** Todos / En proceso / Pendiente (según `en_proceso_produccion`).
- **ID artículo:** Opcional; filtra por artículo.

**Tabla:** Nº lista, Código, Artículo, Estado (En proceso / Pendiente), Cant. pedida, Cant. pendiente, Acciones (Ver, Liberar).

**Acciones:**

- **Ver:** Ir al detalle de la OP.
- **Liberar:** Lleva al tablero; desde el detalle de la OP se puede “Liberar OPT (solo en wizard; la OPT ya se crea en producción)”.

### 5.2 Nueva OPT

**Ruta:** Órdenes → Nueva OPT o “Nueva OPT” desde Pedido producción trabajo (OPT) / Tablero (`/mpr/ordenes/nueva/`).

**Pasos:**

1. **Artículo:** Seleccionar de la lista (opcionalmente preseleccionado si se llegó desde Pedido producción trabajo (OPT) con artículo).
2. **Cantidad pedida:** Número entero positivo (por defecto 1).
3. **Opcionales** (si la base lo permite): Depósito de producción, Prioridad, Fecha objetivo.
4. Pulsar **“Crear orden de producción”**.

Se crea una línea en `lista_produccion_agrupada` y se redirige al **Detalle de la OP** recién creada.

### 5.3 Detalle de una OP

**Ruta:** Desde Lista de OPT → “Ver” en una fila (`/mpr/ordenes/<id_lista>/`).

**Qué muestra:**

- Número de OP (id_lista) y totales: demanda, cantidad en esta OPT, pendiente OPP y pendiente del pedido. Las cantidades en **packs** se muestran además como **docenas · unidades** usando `articulo.cantidad_promedio_bulto` por artículo (si el bulto es ≤ 0, divisor 12). Si la OPT tiene **varios artículos con distinto bulto**, el total del encabezado queda en **packs** y debajo un **desglose por artículo** en docenas · unidades; si hay una sola línea o todas comparten el mismo bulto, el total del encabezado se muestra directamente en docenas · unidades.
- Tabla por línea: docenas · unidades y, en texto secundario, el valor en packs.
- Porcentaje completado y estado del flujo (Pedida → En producción → OPP → Pendiente 0 → Armado → Cerrado).

**Tarjetas de acción:**

- **Liberar (OPT):** Solo si la OP tiene id_lista. Lleva al formulario “Liberar a producción (OPT)”.
- **Armado (Lista de materiales):** Listado de listas de materiales. Si alguna línea de la OP es un artículo armado (tiene lista de materiales), aparece “Armado desde esta OP” con enlace al armado preseleccionando lista de materiales y cantidad.
- **Registrar OPP:** Solo si la OP tiene id_lista. Lleva al formulario “Registrar parte de producción (OPP)”.
- **Cerrar OPT:** Visible cuando el **pendiente total es 0**. Botón que envía POST para marcar la OP como cerrada (`en_proceso_produccion = 'No'`).

### 5.4 Liberar a producción (OPT)

**Ruta:** Desde Detalle de OP → “Liberar (OPT)” (`/mpr/ordenes/<id_lista>/liberar-opt/`).

**Qué hace:** Registra la **ejecución** de la OPT (equivalente al botón "Generar" en CargaMovStock con motivo "Pedido producción" en VB6): genera el movimiento de stock tipo OPT, actualiza saldos y descuenta el pendiente de la OP. Para **trazabilidad** se escribe en `lista_produccion_historico` con `id_articulo` e `id_articulo_formula` (siempre informados).

**Pasos:**

1. **Unidad de medida:** Unidad / Display / Bulto.
2. **Cantidad a liberar:** En la unidad elegida. Si se elige Display o Bulto, aparecen:
   - **Unidades por display** o **Unidades por bulto:** Factor para convertir a unidades (cantidad final = cantidad × factor).
3. **Depósito destino:** Donde se registra la entrada (ej. depósito de producción). Obligatorio.

Al confirmar se genera un movimiento de stock tipo **OPT** (Pedido producción), se actualiza stock y se descuenta el pendiente de la OP. La OP queda “En proceso”.

### 5.5 Registrar parte de producción (OPP)

**Ruta:** Desde Detalle de OP → “Registrar OPP” (`/mpr/ordenes/<id_lista>/registrar-opp/`), o paso 3 del asistente de producción.

**Formulario (matriz componente × depósito destino):**

- Por cada combinación componente y depósito (Semi Elaborado, Scrap, 2da Selección, etc., según configuración) se indican **docenas** y **unidades sueltas**. En OPP **una docena son siempre 12 unidades**; el sistema calcula el total en unidades por celda y registra el movimiento en unidades.
- Origen del stock: depósito de **Producción** (configuración MPR).
- **Operario obligatorio** por cada componente que tenga cantidad total > 0 en algún depósito.
- La suma por fila (componente) en unidades no puede superar el **pendiente a distribuir** mostrado (en **docenas · unidades**, divisor 12).
- Al pulsar **Registrar OPP** se muestra un **modal de espera específico del flujo OPP** mientras se valida y envía el POST. No cierre la ventana hasta finalizar.
- El botón **Registrar OPP** en el detalle OPT y en el wizard se muestra solo cuando hay cantidad **registrable** (> 0) en Producción; si no hay stock origen para continuar OPP, puede pasar a **Armado** con lo ya ingresado a Semi elaborado.

Al confirmar se genera un movimiento tipo **OPP** (Parte producción), se descuenta el pendiente de la OP y se actualizan saldos. La trazabilidad guarda operario por componente en histórico. Si el pendiente total llega a 0, se puede **Cerrar OPT** desde el detalle o el tablero.

### 5.6 Cerrar OPT

Disponible cuando el **pendiente total de la OPT es 0**.

- **Desde Detalle de OPT:** Bloque verde con botón “Cerrar OPT” (POST a `/mpr/ordenes/<id_lista>/cerrar/`).
- **Desde Tablero:** En “OPs a cerrar”, botón “Cerrar OPT” por cada OP listada.

Al cerrar, la OPT pasa a `en_proceso_produccion = 'No'`.

### 5.7 Guardrails de proceso

El sistema aplica **restricciones entre pasos** para mantener la coherencia del flujo:

| Acción | Restricción | Mensaje si no se cumple |
|--------|-------------|-------------------------|
| **Liberar OPT (solo en wizard; la OPT ya se crea en producción)** | La cantidad a liberar no puede superar el **pendiente** de la OP. Depósito destino obligatorio. | "La cantidad a liberar no puede superar el pendiente (X unidades)." |
| **Registrar OPP** | La OP debe estar **liberada** (en proceso). No se puede registrar OPP sin haber ejecutado antes Liberar OPT (solo en wizard; la OPT ya se crea en producción). | "Debe liberar la OP (OPT) antes de registrar la parte de producción (OPP)." |
| **Registrar OPP** | La cantidad a registrar no puede superar el **pendiente** de la OP. | "No hay cantidad a registrar para las líneas indicadas." |
| **Cerrar OPT** | El **pendiente total** de la OP debe ser **0**. | "No se puede cerrar la OP con pendiente mayor a 0. Libere OPT y registre OPP hasta completar." |

Orden recomendado: **Crear OPT** → **Liberar OPT (solo en wizard; la OPT ya se crea en producción)** → (opcionalmente Armado) → **Registrar OPP** hasta pendiente 0 → **Cerrar OPT**.

### 5.8 Operarios (ABM)

**Ruta:** Producción → Operarios (`/mpr/operarios/`).

**Listado:** Búsqueda por nombre **predictiva** (sin botón Filtrar; actualiza la URL tras una breve pausa al escribir). Switch **Incluir anulados** que, al cambiar, recarga el listado con o sin operarios anulados. Columna **Estado:** solo el switch por fila (verde = activo, rojo = anulado; anular o reactivar). Columna **Acciones:** icono de lápiz para editar. Al volver del POST se conservan búsqueda y filtro. Enlace inferior **Tablero** (icono tablero), alineado al estilo de otras pantallas MPR.

---

## 6. Lista de materiales (recetas)

### 6.1 Listado de conjuntos

**Ruta:** Producción → Lista de materiales o “Armado (Lista de materiales)” desde Tablero (`/mpr/bom/`).

Lista de conjuntos de armado (en_abm): ID, nombre, estado (activo/anulado), cantidad de componentes. Filtro “Solo activos”. Acciones: **Ver**, **Editar**.

### 6.2 Nuevo conjunto

**Ruta:** Lista de materiales → “Nuevo conjunto” (`/mpr/bom/nuevo/`).

- Ingresar **nombre** y opcionalmente **detalle**.
- Confirmar. Se crea el conjunto y se redirige a **Editar** para agregar componentes y, si aplica, **artículo armado**.

### 6.3 Detalle de un conjunto

**Ruta:** Lista de materiales → “Ver” en una fila (`/mpr/bom/<id_en_abm>/`).

Muestra cabecera (nombre, ID, detalle, estado), **artículo armado** (si está asignado) y tabla de **componentes** (código, artículo, cantidad, unidad). Acciones: **Editar**, **Ejecutar armado**, **Volver al listado**.

### 6.4 Editar conjunto

**Ruta:** Lista de materiales → “Editar” o desde Detalle (`/mpr/bom/<id_en_abm>/editar/`).

**Cabecera:**

- Nombre, Estado (Activo/Anulado), Detalle. Botón “Guardar cabecera”.

**Artículo armado:**

- Selector para asignar o desasignar el **artículo resultante** del armado (debe ser un artículo con `ensamblado = 'Si'` y `id_en_abm` = este conjunto). Sin artículo armado asignado no se puede ejecutar armado desde este conjunto.

**Componentes:**

- Tabla de componentes con opción “Anular” por fila.
- **Añadir componente:** Artículo, cantidad, unidad (opcional). Botón “Añadir”.

### 6.5 Ejecutar armado (desde Lista de materiales)

**Ruta:** Desde Detalle de conjunto → “Ejecutar armado”, o Armado con conjunto preseleccionado (`/mpr/armado/` o `/mpr/armado/<id_en_abm>/`).

**Pasos:**

1. **Conjunto (Lista de materiales):** Seleccionar el conjunto. Si se entró con id_en_abm (p. ej. desde “Armado desde esta OP”), ya viene preseleccionado.
2. **Cantidad a armar (unidades):** Número entero. Si se llegó desde el detalle de una OP con artículo armado, la cantidad puede venir preseleccionada por URL (`?cantidad=X`).
3. **Depósito origen:** Donde están los componentes (se descontará stock).
4. **Depósito destino:** Donde entrará el producto armado.

Al confirmar se genera un movimiento de stock tipo **Armado**: salidas de componentes desde origen y entrada del artículo armado en destino. La trazabilidad guarda operario por línea/pack armado. Debe haber stock suficiente de cada componente en el depósito origen.

---

## 7. Armado (pantalla general)

**Ruta:** Menú Armado o “Armado desde esta OP” desde Detalle de OP (`/mpr/armado/` o `/mpr/armado/<id_en_abm>/`).

Misma pantalla que “Ejecutar armado” de la Lista de materiales: selección de conjunto, cantidad, depósito origen y depósito destino. Si se accede con `id_en_abm` (y opcionalmente `?cantidad=X`), el conjunto y la cantidad pueden venir preseleccionados.

### 7.1 Armado surtido

**Ruta:** Producción → **Armado surtido** (`/mpr/armado-surtido/`). Especificación MVP: [SDD_ARMADO_SURTIDO_MVP.md](SDD_ARMADO_SURTIDO_MVP.md). Multi-pack (carrito): [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md).

**Propósito:** Armar **packs con composición variable** (surtidos) usando stock del depósito **2.ª selección**, sin receta BOM fija, e ingresar cada pack terminado en **Terminado**. No reemplaza el armado con lista de materiales (§6.5 / §7) ni el ingreso manual de movimientos de stock.

**Packs elegibles:** artículos con `tipo_art_fab = 'Fabricado 2da'` en AdministraNET (no usa lista de habilitados Synap `MprArticuloArmadoSurtido` salvo mantenimiento legacy).

#### Cabecera del lote

Antes de agregar armados, complete una sola vez por ejecución:

- **Depósito origen** (default 2.ª selección) y **destino** (default Terminado).
- **Operario** (obligatorio).
- **Detalle** (opcional).

Origen y destino son **compartidos** por todos los ítems del lote.

#### Disposición de pantalla (estilo POS)

La pantalla se divide en **dos columnas** (en pantallas anchas):

- **Izquierda — estación de trabajo:** cabecera del lote (se mantiene mientras arma varios packs) y sección **Armar pack** (pack, cantidad, composición).
- **Derecha — carrito del lote:** lista de packs agregados, consumo agregado en origen (colapsable) y botón **Ejecutar lote**.

Tras **Agregar al carrito**, solo se limpia la sección **Armar pack** (pack, cantidad y composición) para armar el siguiente; la cabecera **no** se reinicia.

#### Armar y agregar al carrito

1. Complete la **cabecera del lote** buscando **origen**, **destino** y **operario** (búsqueda predictiva), además del detalle opcional.
2. En **Armar pack**, busque el **pack terminado** (búsqueda predictiva por código o descripción), indique la **cantidad de packs** (enteros ≥ 1) y la **composición**: busque en stock origen, marque uno o varios componentes con el selector múltiple y pulse **Agregar seleccionados** (cantidad por pack editable en la tabla).
3. Pulse **Agregar al carrito**. El ítem aparece en la columna derecha y se limpia el formulario de armado.
4. Repita para otros packs (máximo **20** armados por lote).
5. Revise **Consumo en origen** en el carrito: suma de unidades por componente en todo el lote vs saldo disponible (estimación al agregar).

**Reglas al agregar:**

- No puede repetir el mismo pack en el lote (edite la fila existente).
- Un artículo no puede ser pack en un ítem y componente en otro del mismo lote.
- Si falta stock estimado, el sistema no agrega el ítem y muestra el motivo (validación en pantalla y, si está disponible, consulta al servidor).

Desde el carrito puede **editar** (carga el ítem en la columna izquierda) o **quitar** filas. Cada ítem permite expandir **Ver composición**.

#### Ejecutar lote

1. Con al menos un ítem en el lote, pulse **Ejecutar lote (N)**.
2. El sistema procesa los ítems **en orden de la tabla** (FIFO). Cada pack exitoso genera su propio comprobante **Armado** (MSTOCK / tipo OPA).
3. Tras finalizar, se abre un **modal** con:
   - **Grabados:** descripción del pack, cantidad grabada, saldo inicial y final del pack en destino, y comprobante MSTOCK.
   - **No grabados:** pack, cantidad y motivo (p. ej. stock insuficiente).
4. Los ítems **no grabados** permanecen en el carrito para corregir o quitar; los grabados salen del lote.
5. La pantalla **permanece en** `/mpr/armado-surtido/` (con `?id_lista=` si vino desde una OPT).

**Desde detalle OPT:** el acceso con `?id_lista=` solo se habilita si ya registró al menos una **OPP** con envío a **2.ª selección**; si no, la tarjeta en el detalle OPT aparece deshabilitada con el motivo.

**Detalles técnicos (operación):** componentes con lote usan consumo **FIFO** por vencimiento en origen; cada MSTOCK exitoso registra composición en Synap y **PrecioCosto** en renglones de stock.

**Nota:** No usar `/stock/ingreso-movimiento/` como proceso estándar de armado surtido.

---

## 8. Reclasificación

**Ruta:** Producción → Reclasificación (`/mpr/reclasificacion/`).

Para mover artículo entre depósitos con motivo **Reclasificación** (p. ej. producto a 2da selección o scrap):

1. **Artículo:** Seleccionar de la lista.
2. **Cantidad:** Entero positivo.
3. **Depósito origen** y **Depósito destino.**
4. **Detalle (opcional).**

Al confirmar se genera movimiento de stock tipo Reclasificación (salida en origen, entrada en destino).

---

## 9. Configuración: Depósitos

**Ruta:** Producción → Config. Depósitos (`/mpr/config/depositos/`).

- **Producción (OPT):** Asigne el tipo **«Producción»** a **un** depósito en la columna **Tipo** de la tabla. Ese depósito es donde se registra el stock al **confirmar** la orden en el Asistente de producción (paso 2). Sin un depósito con ese tipo, el asistente no puede liberar la OPT automáticamente.
- **Suma stock:** Por cada depósito se puede cambiar Sí / No. Solo los depósitos con “Suma stock = Sí” entran en el cálculo de **stock terminado**. Depósitos de tránsito, scrap o 2da selección suelen tener “No” según criterio de negocio.

---

## 10. Reportes MPR

**Ruta:** Producción → Reportes (`/mpr/reportes/`).

Pestañas de solo lectura:

- **Pendiente:** Órdenes/líneas con pendiente de producción (por OP, artículo, cantidades).
- **WIP:** En progreso (en_proceso_produccion = 'Si' con pendiente > 0).
- **Stock:** Stock por artículo y depósito (saldos).
- **Bajo mínimo:** Artículos con stock total (en depósitos que suman) por debajo del mínimo configurado (deposito_reposicion o articulo.stock_minimo).

---

## 11. Flujo resumido (proceso completo)

1. **Demanda:** Ver en Pedido producción trabajo (OPT) o Pedidos a fábrica qué hay que fabricar.
2. **Crear OPT:** (a) **Asistente de producción:** Paso 1 Crear orden (artículo + cantidad) → Paso 2 Confirmar (crea OPT y libera si hay depósito tipo Producción) → Paso 3 Crear OPP (cantidades por depósito) → Armado (opcional) → Cierre; o (b) Desde Pedido producción trabajo (OPT): marcar artículos, **Continuar** → Confirmar OPT (tabla Unidades) → **Generar OPT** (crea la OPT y lleva al detalle); o (c) **Nueva OPT** por artículo y cantidad.
3. **Liberar (OPT):** En el asistente va incluido en “Confirmar”. Fuera del asistente, desde el detalle de la OPT con “Liberar (OPT)” (cantidad y depósito destino).
4. **Armado (si aplica):** Ejecutar armado eligiendo conjunto, cantidad y depósitos origen/destino.
5. **Registrar OPP:** En el detalle de la OPT, “Registrar OPP” (docenas y unidades sueltas por celda; docena = 12 unidades). En el asistente, paso 3 usa la misma matriz (solo totales > 0 generan movimiento).
6. **Cerrar OPT:** Cuando el pendiente total sea 0, “Cerrar OPT” desde el detalle o desde el tablero (OPT a cerrar).

Para mantener las listas de materiales actualizadas: usar **Lista de materiales** → listado, nuevo conjunto, editar (cabecera, **artículo armado**, componentes). Luego ejecutar armado desde **Armado** o desde el detalle de una OP con “Armado desde esta OP”.

---

## 12. Mensajes y errores frecuentes

- **“No se pudo determinar la empresa activa.”** Seleccionar una empresa/base de datos antes de usar MPR.
- **“No hay artículo armado asociado a este conjunto.”** En Editar conjunto, asignar el artículo armado (`ensamblado`/`id_en_abm`) antes de ejecutar armado. Ver §4 y [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md).
- **Pack no aparece en armado surtido.** Verificar que el artículo tenga `tipo_art_fab = 'Fabricado 2da'` en AdministraNET.
- **«El pack ya está en el lote. Edite la fila existente.»** No agregue dos veces el mismo pack; use Editar en la tabla del lote.
- **«Agregue al menos un armado al lote.»** Debe agregar al menos un ítem al carrito antes de ejecutar.
- **«Máximo 20 armados por lote.»** Divida la operación en varios lotes si necesita más packs distintos.
- **Modal con ítems no grabados.** Tras ejecutar, revise el motivo; los fallidos quedan en el carrito. Corrija cantidades/composición o quite la fila y vuelva a ejecutar.
- **“Stock insuficiente de componente…”** En armado o al agregar al lote, no hay saldo suficiente del componente en el depósito origen; revisar stock, consumo agregado del lote o depósito.
- **“Stock en lotes insuficiente…”** Componente con `Lote='Si'`; revisar saldos por lote en el depósito origen.
- **“Indique cantidad a liberar (entero positivo) y depósito destino.”** Completar cantidad y depósito en Liberar OPT (solo en wizard; la OPT ya se crea en producción).
- Lista de OPT vacía con datos en la base: comprobar que la empresa activa sea la correcta y que existan filas con `cantidad_pendiente_prod > 0` en `lista_produccion_agrupada`.

---

*Documento: Manual de usuario MPR. Proyecto Synap. Actualizado según pantallas y flujos del módulo MPR.*
