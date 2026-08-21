# Glosario MPR (Módulo de Producción)

Términos y conceptos del módulo MPR en Synap, alineados con AdministraNET y el plan en **ANALISIS_MPR_PROPUESTA_MVP.md**.

**Identificación pack / componente en datos:** ver [ARTICULO_PACK_COMPONENTE_MPR.md](ARTICULO_PACK_COMPONENTE_MPR.md).

**Código visible en pantallas MPR:** en tablas, selectores, reportes y mensajes al usuario se muestra **`articulo.id_manual`** (campo de contexto `codigo_manual`), normalizado con `str_codigo_manual_articulo`. No se usa `CodigoArticulo` ni `CodigoArticuloT` como sustituto cuando `id_manual` está vacío (variantes pueden compartir el mismo talón). Si no hay código manual, la UI muestra `-`.

---

## Pack y componente (datos)

| Término | Descripción |
|--------|-------------|
| **Pack** | En MPR, unidad de demanda o producto terminado que se fabrica o arma. **No** es un solo campo en `articulo`: según el flujo se identifica por `ensamblado`+`id_en_abm` (BOM), por `lista_produccion_agrupada.id_articulo` (OPT), o por `MprArticuloArmadoSurtido` (armado surtido). |
| **Componente** | Insumo que sale de un depósito al armar o al registrar OPP/OPT. En BOM está en `en_abm_formula`; en armado surtido es la composición elegida en pantalla. Cualquier `IDArt` puede ser componente sin flag en `articulo`. |
| **Pack BOM / artículo armado** | `articulo` con `ensamblado = 'Si'` e `id_en_abm` apuntando al conjunto `en_abm`. |
| **cantidad_promedio_bulto** | Unidades por bulto del artículo; divisor para docenas en OPT/armado. No indica pack vs componente. |

---

## Órdenes y demanda

| Término | Descripción |
|--------|-------------|
| **OPT (Orden de producción)** | Orden que agrupa demanda de producción por artículo. En AdministraNET se representa en `lista_produccion_agrupada` (por `id_lista_produccion` e `id_articulo`). Estados: pendiente de liberar, en proceso, cerrada. |
| **Lista de producción agrupada** | Tabla que agrupa la demanda por artículo: `cantidad_pedida`, `cantidad_pendiente_prod`, `en_proceso_produccion`, y opcionalmente `cantidad_fabricada_acumulada` (unidades de pack armadas acumuladas por línea, persistidas al registrar OPA). Es la fuente de “qué fabricar” y “cuánto falta”. |
| **Lista de producción detalle** | Desglose por pedido y artículo (`lista_produccion_detalle`): vincula demanda a pedidos de venta (`comp_ped` + `stockp`) y, con `codigo_movimiento_pedido = 0`, la **demanda por reserva** (meta `max(0, R−S)` sin fila en `comp_ped`). Opcional: columna `origen_demanda` (`RESERVA`). |
| **Pendiente de producción** | Cantidad que falta producir de una OPT: `cantidad_pendiente_prod` en lista_produccion_agrupada. Se reduce al liberar OPT y al registrar OPP. |

---

## OPT (Pedido producción / Liberación)

| Término | Descripción |
|--------|-------------|
| **OPT** | **Pedido de producción** o **liberación a producción**. Movimiento de stock (motivo 11, tipo_mov 'OPT') que **confirma** la OPT y registra la **entrada** de material/producto a producir en un depósito (ej. depósito de producción). Descuenta `cantidad_pendiente_prod` de la OPT. En Synap se ejecuta desde “Liberar OPT” en el detalle de la OPT. |
| **Liberar a producción** | Acción en MPR que ejecuta el OPT: genera movimiento_stock tipo OPT, actualiza stock_deposito y lista_produccion_agrupada (y opcionalmente lista_produccion_historico). |
| **Depósito destino (OPT)** | Depósito donde se registra la entrada al liberar OPT (normalmente depósito de producción o terminados). Debe tener `deposito.suma_stock` según configuración. |

---

## OPP (Parte de producción)

| Término | Descripción |
|--------|-------------|
| **OPP** | **Parte de producción**. Movimiento que registra la **salida de producto terminado**: salida desde depósito origen (ej. producción) y entrada a depósito destino (terminados, 2da selección o scrap). Tipo_mov 'OPP', motivo "Parte producción". Descuenta `cantidad_pendiente_prod` de la OPT. |
| **Registrar OPP** | Pantalla MPR para cargar cantidad producida, depósito origen y depósito destino. Clasificación opcional: Primera, 2da selección, Scrap (elegir depósito destino acorde). |
| **Cerrar OPT** | Cuando el pendiente total de la OPT es 0, se puede “Cerrar OPT”: se marca `en_proceso_produccion = 'No'`. Disponible en el tablero y en el detalle de la OPT. |

---

## Armado y Lista de materiales

| Término | Descripción |
|--------|-------------|
| **Lista de materiales (receta)** | Conjunto de armado: lista de componentes y cantidades para producir un artículo armado. En AdministraNET: tabla `en_abm` (cabecera) y `en_abm_formula` (componentes por id_en_abm). |
| **Conjunto de armado** | Registro en `en_abm`: id_en_abm, nombre_en_abm, detalle, anulado. Equivale a una “receta” o lista de materiales. |
| **Artículo armado** | Artículo resultante del armado: en `articulo` tiene `ensamblado = 'Si'` e `id_en_abm` apuntando al conjunto. Se asigna en la edición de la lista de materiales en MPR. |
| **Armado** | Operación que consume componentes (salida desde depósito origen) y genera producto armado (entrada en depósito destino). Movimiento_stock tipo_mov 'Armado', motivo 9. Se ejecuta desde “Armado” en MPR con selección de lista de materiales, cantidad y depósitos. |
| **Ejecutar armado** | Pantalla MPR para elegir conjunto (lista de materiales), cantidad a armar, depósito origen (componentes) y depósito destino (producto armado). |
| **Armado 1ra** | Armado de pack **primera selección** desde **Semi elaborado** hacia **Terminado** (SKU 1.ª), composición **BOM fija**. Entrada canónica: menú MPR (no desde OPT). Imputación a pedidos: rol supervisor por MSTOCK. SDD: [SDD_ARMADO_UNIFICADO_IMPUTACION.md](SDD_ARMADO_UNIFICADO_IMPUTACION.md). |
| **Armado 2da** | Armado de pack **segunda selección** (`tipo_art_fab = 'Fabricado 2da'`, SKU distinto) desde depósito **2.ª selección** con **composición libre**. Sin vínculo a pedidos (venta oportunista). Evolución de «armado surtido». Mismo SDD unificado. |
| **Armado surtido** | *Nombre legacy en código/docs.* Equivalente operativo a **Armado 2da**. Ver [SDD_ARMADO_SURTIDO_MVP.md](SDD_ARMADO_SURTIDO_MVP.md) (implementado). |
| **Lote (armado)** | Conjunto de **varios armados** (mismo modo 1ra o 2da) en carrito antes de ejecutar; un MSTOCK por pack exitoso. No mezclar 1ra y 2da en un lote. [SDD_ARMADO_SURTIDO_MULTI_LOTE.md](SDD_ARMADO_SURTIDO_MULTI_LOTE.md), [SDD_ARMADO_UNIFICADO_IMPUTACION.md](SDD_ARMADO_UNIFICADO_IMPUTACION.md). |
| **Borrador / fecha / rectificación** | Desde 2026: lote puede guardarse en estado `borrador` (sin MSTOCK), con `fecha_realizado` configurable y rectificación delta sobre lotes aprobados. Ver [ARMADO_FECHA_BORRADOR_RECTIFICACION.md](ARMADO_FECHA_BORRADOR_RECTIFICACION.md). Packs 1ra requieren `tipo_art_fab=Terminado`. |
| **Imputación armado 1ra** | Asignación **supervisor** de cada MSTOCK de Armado 1ra a demanda/pedido (`lista_produccion_detalle`). UI agrupa por lote; unidad contable = movimiento MSTOCK. FIFO sugerido. |
| **Composición (armado surtido)** | Lista de componentes y cantidades **por pack** elegida al armar; se persiste en tablas Synap (`mpr_armado_surtido_*`), no en `en_abm_formula`. |
| **Pack habilitado surtido** | Artículo terminado (`IDArt`) autorizado en **`MprArticuloArmadoSurtido`** (Synap), no por `ensamblado` en `articulo`. Alta: `mpr_cargar_packs_armado_surtido` o admin Django. |

---

## Stock y depósitos

| Término | Descripción |
|--------|-------------|
| **Stock terminado** | Suma de saldos en depósitos con `deposito.suma_stock = 'Si'`. Usado en Pedido producción trabajo (OPT)/Unidades para “cantidad a fabricar” y “cantidad urgente”. |
| **Cant. parcial fabricada (ventana demanda)** | Unidades de producto terminado (pack) ya armadas en la campaña: se lee de `cantidad_fabricada_acumulada` si la columna existe; si no, respaldo algebraico Cant. pedida − Pendiente producción. |
| **Stock reserva** | Campo en artículo (`stock_reserva`): indicador **R** de stock mínimo a garantizar; no es saldo. En ventana OPT/Packs: **P_ped** = suma en detalle con código de pedido ≠ 0; **Q_res** = fila código 0; **S** = stock terminado. **Cant. a fabricar** = max(0, **P_ped + R − S**) (un solo pool **S**; no se suma **Q_res** otra vez). **Urgente** = max(0, **P_ped − S**). |
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

## Flujo diario MPR (tablero, parte, control de calidad)

| Término | Descripción |
|--------|-------------|
| **Tablero de producción** | Demanda consolidada por **componente** (explosión BOM desde packs PED). Columnas PCP: pedido, reserva, resta total/urgente, **Fabricando**, stock pipeline (sin Terminado en componentes), Enviar. Ruta: `/mpr/tablero-produccion/`. |
| **Fabricando** | Cupo virtual: `max(0, envíos tablero − acreditado)`. Acreditado = `max(Semi+2da+Scrap, CC) + max(0, partes − CC)`. **Producción no acredita.** Un parte nuevo siempre baja Fabricando. |

| **Enviar a producción** | Registro en `mpr_envio_produccion` (ledger). No mueve stock hasta el parte. |
| **Parte de producción (E8)** | Grilla componente × operario; solo filas con Fabricando > 0. Registra `mpr_parte_linea` e ingresa stock a **Producido**. |
| **Control de calidad (clasificación / CC)** | Clasificación desde **Producido** hacia Semi / 2da / Scrap en **bloques por artículo** (sin columna máquina ni filtro Turno). Columna **Saldo producción** = saldo vivo en depósito `tipo_mpr = Produccion` (único tope por artículo). **Semi:** un ingreso por artículo/día; ledger nuevo con `id_operario` y `id_mpr_turno` nulos. **2da y Scrap:** por **(operario, turno)** del parte (máquinas colapsadas). **Artículo huérfano** (saldo Prod > 0 sin parte): solo Semi editable. Bloqueo dual del parte: 2da/scrap o Semi **histórico con operario** bloquean turno; Semi nuevo sin operario **no** bloquea. Ruta: `/mpr/tablero-produccion/clasificacion-produccion/`. Plan: [PLAN_CC_CONSOLIDADO_POR_ARTICULO.md](PLAN_CC_CONSOLIDADO_POR_ARTICULO.md). No confundir con la planilla impresa. |
| **Planilla Control de Calidad** | Hoja A4 horizontal impresa desde **Asignar artículo a máquina**: máquina, artículo, color, talle y casilleros de turnos/observaciones para completar a mano. Respeta filtros de pantalla. |
| **TALLES / COLOR (CE)** | Campos especiales de artículo (`articulo_ce` / `articulo_val_ce` / `articulo_valor_ce`). Se muestran en grilla de máquinas e inventario por etapa. |
| **Clasificado (reportes)** | Suma de `mpr_transicion_lote` con `tipo_origen = Produccion` en el período. |
| **Acreditado** | Unidades que cubren envíos sin contar como Fabricando pendiente: stock pipeline del componente, CC registrada o partes ya cargados. |
| **Componente vs pack terminado** | El tablero y CC operan sobre **componentes** (semi). El **terminado** es del pack en armado; no se muestra en tablero de producción de componentes. |
| **Línea de producción** | Agrupación de máquinas (`mpr_linea`). Cada operario tiene línea habitual y puede tener override por día en roster. |
| **Máquina** | Equipo de planta (`mpr_maquina`) con pertenencia versionada a una línea y artículos habilitados versionados. |
| **Parte móvil / declaración** | Carga del operario al fin de turno por máquina; `estado = pendiente`, `origen = movil_operario`; **no mueve stock** hasta aprobación. |
| **Gap (brecha)** | Diferencia `cantidad_aprobada − cantidad_declarada` en una línea de parte; requiere motivo si ≠ 0. |
| **Operario puro** | Usuario con `mpr.parte_operario` sin `mpr.ver`; solo accede a `/mpr/mi-parte/`. |
| **En fabricación** | Sinónimo de reporte para envíos tablero (`mpr_envio_produccion`). |
| **Producido** | Sinónimo de reporte para parte de producción acreditado (`mpr_parte_linea`). |

Ver: [TABLERO_CONSOLIDADO.md](TABLERO_CONSOLIDADO.md), [PARTE_PRODUCCION.md](PARTE_PRODUCCION.md), [TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md](TRAZABILIDAD_MAQUINA_LINEA_OPERARIO.md), [CARGA_MOVIL_OPERARIO.md](CARGA_MOVIL_OPERARIO.md), [ARTICULO_CE_TALLES_COLOR.md](ARTICULO_CE_TALLES_COLOR.md), [DOCENAS_CLASIFICACION_OPERARIO_MPR.md](DOCENAS_CLASIFICACION_OPERARIO_MPR.md), [REPORTES_MPR.md](REPORTES_MPR.md). Inventario Stock: [../stock/INVENTARIO_TABLA_MPR.md](../stock/INVENTARIO_TABLA_MPR.md).

---

## Referencias

- **ANALISIS_MPR_PROPUESTA_MVP.md** — Análisis del proceso y propuesta del módulo MPR.
- **SCHEMA_MPR_ADMINISTRANET92.md** — Esquema de tablas lista_produccion_*, en_abm, en_abm_formula, etc.
- **docs/general/POLITICA_DOCUMENTACION.md** — Criterios de documentación del proyecto.
