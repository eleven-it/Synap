# Glosario MPR (Módulo de Producción)

Términos y conceptos del módulo MPR en Synap, alineados con AdministraNET y el plan en **ANALISIS_MPR_PROPUESTA_MVP.md**.

---

## Órdenes y demanda

| Término | Descripción |
|--------|-------------|
| **OP (Orden de producción)** | Orden que agrupa demanda de producción por artículo. En AdministraNET se representa en `lista_produccion_agrupada` (por `id_lista_produccion` e `id_articulo`). Estados: pendiente de liberar, en proceso, cerrada. |
| **Lista de producción agrupada** | Tabla que agrupa la demanda por artículo: `cantidad_pedida`, `cantidad_pendiente_prod`, `en_proceso_produccion`. Es la fuente de “qué fabricar” y “cuánto falta”. |
| **Lista de producción detalle** | Desglose por pedido y artículo (`lista_produccion_detalle`): vincula demanda a pedidos de venta (comp_ped) y stockp. |
| **Pendiente de producción** | Cantidad que falta producir de una OP: `cantidad_pendiente_prod` en lista_produccion_agrupada. Se reduce al liberar OPT y al registrar OPP. |

---

## OPT (Pedido producción / Liberación)

| Término | Descripción |
|--------|-------------|
| **OPT** | **Pedido de producción** o **liberación a producción**. Movimiento de stock (motivo 11, tipo_mov 'OPT') que **confirma** la OP y registra la **entrada** de material/producto a producir en un depósito (ej. depósito de producción). Descuenta `cantidad_pendiente_prod` de la OPT. En Synap se ejecuta desde “Liberar OPT” en el detalle de la OPT. |
| **Liberar a producción** | Acción en MPR que ejecuta el OPT: genera movimiento_stock tipo OPT, actualiza stock_deposito y lista_produccion_agrupada (y opcionalmente lista_produccion_historico). |
| **Depósito destino (OPT)** | Depósito donde se registra la entrada al liberar OPT (normalmente depósito de producción o terminados). Debe tener `deposito.suma_stock` según configuración. |

---

## OPP (Parte de producción)

| Término | Descripción |
|--------|-------------|
| **OPP** | **Parte de producción**. Movimiento que registra la **salida de producto terminado**: salida desde depósito origen (ej. producción) y entrada a depósito destino (terminados, 2da selección o scrap). Tipo_mov 'OPP', motivo "Parte producción". Descuenta `cantidad_pendiente_prod` de la OPT. |
| **Registrar OPP** | Pantalla MPR para cargar cantidad producida, depósito origen y depósito destino. Clasificación opcional: Primera, 2da selección, Scrap (elegir depósito destino acorde). |
| **Cerrar OPT** | Cuando el pendiente total de la OP es 0, se puede “Cerrar OPT”: se marca `en_proceso_produccion = 'No'`. Disponible en el tablero y en el detalle de la OPT. |

---

## Armado y Lista de materiales

| Término | Descripción |
|--------|-------------|
| **Lista de materiales (receta)** | Conjunto de armado: lista de componentes y cantidades para producir un artículo armado. En AdministraNET: tabla `en_abm` (cabecera) y `en_abm_formula` (componentes por id_en_abm). |
| **Conjunto de armado** | Registro en `en_abm`: id_en_abm, nombre_en_abm, detalle, anulado. Equivale a una “receta” o lista de materiales. |
| **Artículo armado** | Artículo resultante del armado: en `articulo` tiene `ensamblado = 'Si'` e `id_en_abm` apuntando al conjunto. Se asigna en la edición de la lista de materiales en MPR. |
| **Armado** | Operación que consume componentes (salida desde depósito origen) y genera producto armado (entrada en depósito destino). Movimiento_stock tipo_mov 'Armado', motivo 9. Se ejecuta desde “Armado” en MPR con selección de lista de materiales, cantidad y depósitos. |
| **Ejecutar armado** | Pantalla MPR para elegir conjunto (lista de materiales), cantidad a armar, depósito origen (componentes) y depósito destino (producto armado). |

---

## Stock y depósitos

| Término | Descripción |
|--------|-------------|
| **Stock terminado** | Suma de saldos en depósitos con `deposito.suma_stock = 'Si'`. Usado en Pedido producción trabajo (OPT)/Unidades para “cantidad a fabricar” y “cantidad urgente”. |
| **Stock reserva** | Campo opcional en artículo (`stock_reserva`): cantidad reservada; la “brecha” es stock_reserva − stock_terminado. |
| **Depósito suma_stock** | Campo en `deposito`: 'Si' o 'No'. Solo los depósitos con suma_stock = 'Si' entran en el cálculo de stock terminado y en indicadores de Pack/Unidades. |
| **2da selección** | Productos con defectos aptos para venta a menor costo. Se suele usar un depósito específico (ej. “Depósito 2da selección”) y reclasificación desde producción. |
| **Scrap** | Desecho no vendible. Depósito dedicado o motivo de movimiento para dar de baja producto descartado. |

---

## Ventanas y pantallas MPR

| Término | Descripción |
|--------|-------------|
| **Tablero MPR** | Dashboard con KPIs (OPT en progreso, pendientes, urgentes), OPT a cerrar y movimientos recientes (OPT, OPP, Armado). |
| **Pedido producción trabajo (OPT) / Ventana Unidades** | Listado de artículos con demanda, stock terminado, **cantidad a fabricar editable**, cantidad urgente y stock reserva/brecha. Checkbox por fila para **seleccionar** artículos; botón **Crear OPT con seleccionados** crea una OPT con múltiples artículos. Origen: lista_produccion_agrupada y stock_deposito. |
| **Lista de OPT** | Listado de pedidos de producción (lista_produccion_agrupada) con filtros por estado (en proceso / pendiente) y por artículo. Ruta: `/mpr/opt/`. |
| **Nueva OPT** | Alta de OPT de un artículo (`/mpr/opt/nueva/`) o desde Pedido producción trabajo (OPT) con **múltiples artículos** (selección y cantidades editables). Opcional: depósito producción, prioridad y fecha objetivo si la tabla lo permite. |

---

## Unidades y conversión

| Término | Descripción |
|--------|-------------|
| **Unidad** | Unidad mínima de producción/venta (par, unidad, kg, etc.). En Liberar OPT y OPP las cantidades se pueden ingresar en Unidad, Display o Bulto y convertir a unidad base. |
| **Display / Bulto** | Presentaciones con multiplicador (ej. 1 display = 12 unidades). En Liberar OPT se puede elegir unidad de medida y “unidades por display” o “unidades por bulto” para calcular la cantidad en unidades. |

---

## Referencias

- **ANALISIS_MPR_PROPUESTA_MVP.md** — Análisis del proceso y propuesta del módulo MPR.
- **SCHEMA_MPR_ADMINISTRANET92.md** — Esquema de tablas lista_produccion_*, en_abm, en_abm_formula, etc.
- **docs/general/POLITICA_DOCUMENTACION.md** — Criterios de documentación del proyecto.
