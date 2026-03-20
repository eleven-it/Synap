# Flujo detallado al crear la OPT (Pedido de producción trabajo)

Este documento describe paso a paso qué ocurre cuando el usuario pulsa «Generar OPT» en el asistente (ventana Confirmar OPT / ventana_pack_agrupar).

## Cuándo se escriben las tablas (no antes de confirmar)

**Ninguna actualización a lista de producción (agrupada, detalle, histórico) ocurre por el solo hecho de abrir pantallas o pulsar «Continuar».**

| Acción del usuario | Qué se escribe | Cuándo |
|--------------------|----------------|--------|
| **«Actualizar»** (en Pedido producción trabajo / ventana-pack) | `lista_produccion_detalle` (INSERT con `en_proceso_produccion = 'No'`), `lista_produccion_agrupada` (INSERT/UPDATE: `cantidad_pedida` = SUM(detalle.cantidad_pedida) y `cantidad_pendiente_prod` = SUM(detalle.cantidad_pendiente_prod) en filas con `en_proceso_produccion = 'No'`). **Trazabilidad:** asigna `lista_produccion_detalle.id_lista_produccion` a la línea de agrupada correspondiente. **Nunca** asigna `en_proceso_produccion = 'Si'`; no se toca `lista_produccion_historico`. | Solo al hacer POST del botón «Actualizar». |
| **«Generar OPT»** (en Confirmar OPT) | `lista_produccion_agrupada` (UPDATE en_proceso_produccion, `codigo_movimiento_opt` = placeholder **-id_lista_principal**, cantidad_pendiente_prod; `id_operario_opt` opcional), `lista_produccion_detalle` (UPDATE en_proceso_produccion = 'Si' **por id_lista_produccion IN (...)** cuando existe la columna), `comp_ped` (estado). Todo en **una sola transacción**: o se confirman todos los cambios o ninguno. | Solo al hacer POST con `accion=generar_opt`. |
| **Liberar OPT** (automático tras «Generar OPT» si hay depósito de producción) | Se explota la distribución (pack, qty) a **componentes** vía BOM. `movimiento_stock`, `stock` (entradas de **componentes** en depósito Producción), `stock_deposito`, `lista_produccion_agrupada` (UPDATE `en_proceso_produccion = 'Si'`, `codigo_movimiento_opt`; **no** se modifica `cantidad_pendiente_prod`), `lista_produccion_historico` (tipo_evento='OPT', una fila por componente). | Solo después de que `crear_opt_multiples_articulos` haya hecho commit. |
| **Crear OPP** (parte de producción) | La pantalla muestra y registra por **componente** y en **unidades** (no por pack). El usuario indica cuántas unidades de cada componente envía a cada depósito. Movimiento de **componentes** desde depósito de **producción** a depósitos destino (Semi Elaborado, Scrap, 2ª Selección). `stock`, `stock_deposito` (salida en origen, entrada en destino por componente). `lista_produccion_agrupada.cantidad_pendiente_prod` se **decrementa** por el equivalente pack calculado desde las unidades distribuidas (véase [MPR_OPP_COMPONENTES.md](MPR_OPP_COMPONENTES.md)). | Al pulsar «Registrar OPP» en el asistente (paso 3). |

Por tanto: **lista_produccion_historico** solo se escribe al **liberar** la OPT (o al crear OPP / armado), nunca al cargar Confirmar OPT ni al pulsar «Actualizar». Si se ven cambios en histórico o detalle «antes de confirmar», o bien hubo una confirmación previa (y los mensajes se mostraron en otra pantalla), o hay que revisar que no exista otro flujo que esté llamando a actualizar/liberar sin el clic en «Generar OPT».

## Regla de negocio

- **No se insertan filas nuevas** en `lista_produccion_agrupada` ni en `lista_produccion_detalle` al crear la OPT.
- Esas tablas se alimentan con «Actualizar» pedidos (`actualizar_pedidos_produccion`). Al crear la OPT solo se **actualizan** las filas existentes en `lista_produccion_agrupada` (en_proceso_produccion, cantidad_pendiente_prod, **codigo_movimiento_opt** negativo compartido, id_operario_opt). No se usan tablas mpr_opt ni mpr_opt_linea; el lote se agrupa por **codigo_movimiento_opt** (ver `docs/mpr/OPT_AGRUPACION_CODIGO_MOVIMIENTO.md`). El número de OPT para el usuario es **id_lista_produccion** de la línea principal.
- **Transacción:** En `crear_opt_multiples_articulos` se usa `conn.autocommit(False)` y un único `commit()` al final; si falla cualquier UPDATE (p. ej. por columnas faltantes), se hace `rollback()` y no se persiste ni agrupada ni detalle.

---

## 1. Origen de los datos (vista)

1. El usuario llega a **Confirmar OPT** con una selección en sesión (`ventana_pack_seleccion.filas`) que viene de la pantalla «Pedido producción trabajo (OPT)».
2. La vista llama a `listar_unidades_desde_seleccion(base_empresa, seleccion["filas"])`, que devuelve el desglose por **unidades** (componentes de las recetas BOM de los packs elegidos), con `id_articulo`, cantidades a fabricar, etc. **No** incluye `id_lista_produccion` (esa lista se arma por demanda/BOM, no desde agrupada).
3. El usuario edita cantidades (unidades/docenas) y pulsa **«Generar OPT»**. La asignación de operario se realiza en ejecución: OPP por componente y Armado por línea.

---

## 2. Vista (POST «Generar OPT»)

- **URL:** `POST /mpr/demanda/ventana-pack/agrupar/`, `accion=generar_opt`.
- Se lee la selección de sesión y se vuelve a llamar a `listar_unidades_desde_seleccion` para tener `filas_unidades`.
- Por cada fila con `cantidad > 0` (desde `request.POST` `cant_{id_articulo}`) se arma la lista:
  - `lineas = [(id_articulo, cantidad, id_operario_opt), ...]` donde `id_operario_opt` es opcional (compatibilidad).
- Validaciones en vista:
  - Al menos una línea con cantidad > 0.
  - Que unidades y docenas > 0 (validación en front).
- Se llama a:
  - `crear_opt_multiples_articulos(base_empresa, id_usuario, lineas)`.

---

## 3. Servicio `crear_opt_multiples_articulos`

Entrada: `base_empresa`, `id_usuario`, `lineas` donde cada elemento es `(id_articulo, cantidad, id_operario_opt)` y el operario puede ser `NULL`.

### 3.1 Normalización

- Se filtran líneas con `id_articulo` válido y `cantidad > 0`.
- Si no queda ninguna, devuelve error.

### 3.2 Resolución de filas existentes en `lista_produccion_agrupada`

- Por cada `(id_articulo, cantidad, id_operario_opt)` en `lineas`:
  - Se ejecuta:
    ```sql
    SELECT id_lista_produccion FROM lista_produccion_agrupada
    WHERE id_articulo = %s AND COALESCE(TRIM(en_proceso_produccion), 'No') = 'No'
    ORDER BY id_lista_produccion LIMIT 1
    ```
  - Si **no** hay fila para ese artículo con `en_proceso_produccion = 'No'`:
    - Se devuelve error: *"No hay fila en lista de producción (en_proceso_produccion='No') para el artículo X. Ejecute «Actualizar» pedidos primero."*
  - Si hay fila, se toma `id_lista_produccion` y se guarda en una lista interna:
    - `ids_creados = [(id_articulo, cantidad, id_lista_produccion, id_operario_opt), ...]`.

### 3.3 Actualización de `lista_produccion_agrupada`

- `id_lista_principal` = primer `id_lista_produccion` de `ids_creados`.
- Por cada `(id_articulo, cantidad, id_lista, id_operario_opt)` en `ids_creados`:
  - Se ejecuta:
    ```sql
    UPDATE lista_produccion_agrupada
    SET en_proceso_produccion = 'Si', cantidad_pendiente_prod = %s, codigo_movimiento_opt = %s, id_operario_opt = %s
    WHERE id_lista_produccion = %s
    ```
  - Con `%s` = `cantidad`, **`-id_lista_principal`** (placeholder hasta liberar), `id_operario_opt`, `id_lista`.
- Con esto, las filas de agrupada que participan en la OPT pasan a **en_proceso_produccion = 'Si'**, su pendiente queda igual a la cantidad de la OPT, y quedan agrupadas por el mismo **codigo_movimiento_opt** negativo (= **-id_lista_principal**). Requiere columnas **codigo_movimiento_opt** e **id_operario_opt** (script `sql/alter_lista_produccion_agrupada_mpr_opt.sql`).

### 3.4 Pedidos y `lista_produccion_detalle` (trazabilidad por `id_lista_produccion`)

- **Si la tabla detalle tiene la columna `id_lista_produccion`** (FK a agrupada; ver [SCHEMA_MPR_ADMINISTRANET92.md](SCHEMA_MPR_ADMINISTRANET92.md) y script `sql/alter_lista_produccion_detalle_trazabilidad.sql`):
  - Se actualiza **lista_produccion_detalle** por las líneas de agrupada que participan en la OPT:
    ```sql
    UPDATE lista_produccion_detalle SET en_proceso_produccion = 'Si'
    WHERE id_lista_produccion IN (id_lista de cada fila en ids_creados)
    ```
  - Se obtienen los `codigo_movimiento_pedido` de esas filas y se actualiza **comp_ped** con `_actualizar_comp_ped_estado_produccion(..., "Produccion")`.
- **Si la columna `id_lista_produccion` no existe en detalle** (esquema anterior), se usa el criterio por artículo y pedido:
  - `SELECT DISTINCT codigo_movimiento_pedido FROM lista_produccion_detalle WHERE id_articulo IN (...)`.
  - Se actualiza comp_ped y luego `UPDATE lista_produccion_detalle SET en_proceso_produccion = 'Si' WHERE codigo_movimiento_pedido IN (...) AND id_articulo IN (...)`.

### 3.5 Transacción y commit en base MySQL

- Toda la operación se ejecuta con `conn.autocommit(False)`. Si en cualquier paso se lanza una excepción, se ejecuta `conn.rollback()` y no se persiste ningún cambio (ni agrupada ni detalle).
- Solo al final, si todo ha ido bien, se hace `conn.commit()` de todas las actualizaciones (agrupada, detalle, comp_ped). No se crean registros en Django (Opt/OptLinea); la OPT queda representada por las filas de `lista_produccion_agrupada` con el mismo **codigo_movimiento_opt** (placeholder negativo hasta liberar).

### 3.6 Respuesta

- Devuelve `(True, id_lista_principal, None)`.
- La vista usa `id_lista_principal` para seguir el flujo (liberar OPT, redirección a wizard OPP, mensaje de éxito, etc.).

---

## 4. Resumen de tablas afectadas al crear la OPT

| Tabla / modelo        | Acción                                                                 |
|-----------------------|------------------------------------------------------------------------|
| lista_produccion_agrupada | **UPDATE** `en_proceso_produccion = 'Si'`, `cantidad_pendiente_prod = cantidad`, `codigo_movimiento_opt = -id_lista_principal`, `id_operario_opt` opcional. |
| lista_produccion_detalle  | **UPDATE** `en_proceso_produccion = 'Si'` en filas con `id_lista_produccion IN (...)` (trazabilidad); si la columna no existe, por `codigo_movimiento_pedido` e `id_articulo`. |
| comp_ped              | **UPDATE** estado del pedido a «Producción» (según `_actualizar_comp_ped_estado_produccion`). |

No se hace **INSERT** en `lista_produccion_agrupada` ni en `lista_produccion_detalle` al crear la OPT. No se usan tablas mpr_opt ni mpr_opt_linea; el lote se identifica por **codigo_movimiento_opt** compartido en `lista_produccion_agrupada`.

---

## 5. Condición previa para poder crear la OPT

- Debe existir al menos una fila en `lista_produccion_agrupada` con `en_proceso_produccion = 'No'` por cada artículo que el usuario quiera incluir en la OPT.
- Esas filas se generan al ejecutar **«Actualizar»** pedidos (`actualizar_pedidos_produccion`), que llena `lista_produccion_detalle` y `lista_produccion_agrupada` desde los pedidos PED pendientes (siempre con `en_proceso_produccion = 'No'`).

Si falta esa actualización previa, el servicio devuelve el error indicado en 3.2 y la OPT no se crea.

---

## 6. Reasignación de saldo: depósito de producción → OPP

Tras **crear y liberar** la OPT, en el **depósito de producción** quedan los **componentes** (artículos de la BOM de cada pack) con las cantidades liberadas. En el paso **Crear OPP** (paso 3 del asistente):

- La pantalla muestra una **matriz componente x depósito**: cada fila es un **componente** (artículo de la BOM de los packs de la OPT) con su **disponible en unidades** (explosión de los packs pendientes vía BOM). El usuario indica cuántas **unidades** de cada componente envía a cada depósito destino (Semi Elaborado, Scrap, 2ª Selección). Así se permite, por ejemplo, enviar una sola unidad defectuosa a Scrap y el resto a Semi Elaborado, sin forzar cantidades por pack.
- Al **registrar un OPP** (`ejecutar_opp_por_componentes`):
  - Se exige **operario por componente** cuando el componente tiene cantidad > 0 en la matriz.
  1. Se validan los saldos de **componentes** en el depósito de producción.
  2. Se generan movimientos de **componentes** desde depósito de producción hacia cada depósito destino (salida en origen, entrada en destino).
  3. Se calcula el **equivalente pack** a decrementar en `lista_produccion_agrupada.cantidad_pendiente_prod` a partir de las unidades distribuidas (con escalado proporcional cuando un componente es compartido por varios packs). Ver [MPR_OPP_COMPONENTES.md](MPR_OPP_COMPONENTES.md).

El "Disponible (unid.)" por componente se recalcula desde los packs de la OPT y su `cantidad_pendiente_prod`; al registrar OPPs se va decrementando ese pendiente por pack según el equivalente calculado.

---

## 7. Armado: componentes en Semi elaborado vienen del OPP

**OPT** y **OPP** generan movimientos de los **artículos componentes** (explosión BOM de los packs). Al liberar la OPT entran componentes en Producción; al registrar un OPP salen componentes de Producción y entran en los depósitos destino (Semi Elaborado, Scrap, 2ª Selección).

En el paso **Armado**, el «Máx. armable» se calcula con el stock de los **componentes** en el depósito **Semi elaborado** y se exige **operario por línea/pack** en la ejecución. Ese stock proviene en gran parte de los OPP que movieron componentes desde Producción a Semi Elaborado (además de compras o transferencias). Ver [MPR_ARMADO_STOCK_COMPONENTES.md](MPR_ARMADO_STOCK_COMPONENTES.md).
