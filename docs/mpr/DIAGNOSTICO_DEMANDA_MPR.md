# Diagnóstico Demanda MPR

Comando para verificar por qué podrían no aparecer pedidos en la pantalla **Demanda** (Orden de Producción de Trabajo / ventana pack) o para revisar el estado de lista_produccion_detalle y lista_produccion_agrupada.

---

## Fila en `lista_produccion_agrupada` que no aparece en ventana-pack

La pantalla **siempre** ejecuta antes `actualizar_pedidos_produccion` y luego `listar_lista_produccion_agrupada` (solo `en_proceso_produccion` normalizado como pendiente, `cantidad_pendiente_prod > 0`, `INNER JOIN articulo`).

Compruebe en la **misma base** que usa la sesión Synap (`base_empresa`):

1. **Artículo existe:** `SELECT IDArt, tipo_art_fab FROM articulo WHERE IDArt = <id_articulo>;` — sin fila, el `INNER JOIN` excluye la agrupada aunque exista en la tabla.
2. **Recálculo desde detalle:** `actualizar_pedidos_produccion` actualiza cada `id_articulo` presente en `lista_produccion_detalle` con `en_proceso_produccion` tratado como «No» (según `COALESCE(TRIM(...))`). La agrupada queda con `cantidad_pedida` / `cantidad_pendiente_prod` = **suma** del detalle. Si el detalle suma pendiente **0**, la agrupada pasa a pendiente **0** y **desaparece** de la ventana (aunque antes hubiera 100 solo en agrupada). Revise:
   ```sql
   SELECT * FROM lista_produccion_detalle
   WHERE id_articulo = <id> AND COALESCE(TRIM(en_proceso_produccion), 'No') = 'No';
   ```
3. **OPT ya liberada:** si existe columna `codigo_movimiento_opt` y es **> 0**, la demanda se excluye de ventana-pack (no es demanda nueva).
4. **Base distinta:** la consulta manual en MySQL puede ser sobre otra base que la configurada en Synap para esa empresa.

---

## Comportamiento de la vista Demanda

La vista **Demanda** (ventana pack) **lee lista_produccion_agrupada** mediante `listar_ventana_pack` → `listar_lista_produccion_agrupada`: filas con `cantidad_pendiente_prod > 0` y `en_proceso_produccion = 'No'`, y además **excluye** filas con `codigo_movimiento_opt > 0` (OPT ya liberada: código real de `movimiento_stock`). Esas filas pertenecen a un lote OPT liberado; no deben sumarse como demanda nueva aunque queden pendientes inconsistentes tras un cierre.

Por eso puede ocurrir que el comando `diagnosticar_demanda_mpr` (sección 3) muestre **totales de detalle** para un artículo (p. ej. 127 o 130), pero en **ventana-pack no aparezca** ese artículo: si **toda** la demanda pendiente está en filas de `lista_produccion_agrupada` con `codigo_movimiento_opt > 0`, Synap las omite. El diagnóstico (sección 4) lista explícitamente esas filas como «Excluidas por codigo_movimiento_opt > 0».

- Esa tabla se alimenta con **actualizar_pedidos_produccion**, que se ejecuta **al cargar la página** (con los filtros de sesión o por defecto: mes actual) o al pulsar el botón **Actualizar**.
- El origen de Actualizar es la query de pedidos pendientes (comp_ped + stockp + articulo tipo_art_fab='Terminado', estado_pedido_opt en Pendiente/Parcial), con los **filtros de fecha y búsqueda** configurados en la pantalla.
- **pedidos_resumen** en la tabla se arma desde **lista_produccion_detalle** + `comp_ped` solo para líneas con `codigo_movimiento_pedido <> 0`. La **demanda por reserva** (fila de detalle con código **0**) se muestra aparte en el mismo tooltip y en columnas **Cant. pedido** / **Dem. reserva**.
- **Actualizar** también **sincroniza** esa demanda por reserva: `max(0, R − S)` con `R = articulo.stock_reserva` y `S` = stock terminado (depósitos `suma_stock = 'Si'`). Si no hay pedidos PED en el rango de fechas, la acción **no falla**: solo aplica la sincronización por reserva y recalcula agrupada.

Por tanto, para que un artículo aparezca en Demanda:

1. Debe existir **pendiente** en `lista_produccion_agrupada` (`cantidad_pendiente_prod > 0`, `en_proceso_produccion = 'No'`, sin OPT liberada), alimentado por **Actualizar** desde pedidos **y/o** desde la fila de demanda por reserva.
2. Los pedidos pendientes entran según rango de fechas y búsqueda; la reserva se evalúa en cada Actualizar aunque no haya PED en el rango.
3. **`listar_ventana_pack`** solo incluye artículos con **cantidad a fabricar > 0** (`max(0, P_ped + R − S)`). Si el **saldo** (stock terminado en depósitos que suman) cubre el pedido más la **reserva maestra** del artículo, la cantidad a fabricar es 0 y **no se muestra** la fila en ventana-pack (demanda satisfecha para producir), aunque el pendiente persistido en agrupada siga siendo > 0.

---

## Comando de diagnóstico

```bash
docker exec Synap_app python manage.py diagnosticar_demanda_mpr --base-empresa=administranet92
```

Opcionales (mismos criterios que los filtros de la pantalla):

- `--fecha-desde=YYYY-MM-DD` y `--fecha-hasta=YYYY-MM-DD`
- `--busqueda=texto` (filtro por NroCompBusq/NroComprobante)

El comando:

1. **Sección 1:** Ejecuta la query de **pedidos pendientes** (origen de actualizar_pedidos_produccion) y muestra cuántas filas devuelve y por artículo. Con los mismos filtros, Actualizar inserta/actualiza detalle y agrupada.
2. **Sección 2:** Indica cuántos pares (pedido, artículo) están ya en **lista_produccion_detalle**.
3. **Sección 3:** Muestra la agregación desde lista_produccion_detalle (en_proceso_produccion='No'), que Actualizar usa para escribir en agrupada.
4. **Sección 3b:** Artículos que están en pedidos pero no en la agregación de detalle (no aparecerán en Demanda hasta ejecutar Actualizar con filtros que los incluyan).
5. **Sección 4:** Estado actual de **lista_produccion_agrupada** (la pantalla Demanda aplica además exclusión de `codigo_movimiento_opt > 0`; el comando puede listar filas extra que la UI ya no agrega).
6. **Sección 5:** Nombres de columnas en detalle/agrupada por si hay diferencias de mayúsculas.

**Conclusión:** Si la sección 1 tiene filas válidas pero la 3 o 4 están vacías, hay que cargar la página (o pulsar Actualizar) con el mismo rango de fechas/búsqueda para que se llenen detalle y agrupada. Si tras eso no se ven artículos, revisar filtros y base_empresa en sesión.

---

## Artículo con `stock_reserva` y saldo bajo que no aparece en ventana-pack

La ventana **solo lista filas de `lista_produccion_agrupada`** con `cantidad_pendiente_prod > 0`, `en_proceso_produccion = 'No'` y sin OPT ya liberada (`codigo_movimiento_opt > 0` cuando aplica esa exclusión). Esa agrupada se rellena al ejecutar **Actualizar**, que además sincroniza la demanda por reserva en `lista_produccion_detalle` (código de pedido **0**).

Compruebe en MySQL para el `IDArt` en cuestión:

1. **`articulo.tipo_art_fab`**: debe ser **terminado** (fabricable en MPR). Si es materia prima, semielaborado u otro valor, **no** se genera fila de demanda por reserva (mismo criterio que los ítems de pedidos PED en `actualizar_pedidos_produccion`). Valor esperado en datos típicos: `Terminado` (Synap compara sin distinguir mayúsculas).
2. **`articulo.stock_reserva > 0`**: si es 0 o NULL, no hay quiebre de reserva que persistir.
3. **`lista_produccion_agrupada`**: tras **Actualizar**, debe existir una fila pendiente para ese `id_articulo`. Si solo había una línea antigua con `codigo_movimiento_opt > 0` y pendiente inconsistente, la ventana puede **excluirla** y no verá el artículo hasta corregir datos o tener una fila pendiente válida.
4. **FK hacia `comp_ped` en `lista_produccion_detalle.codigo_movimiento_pedido`**: si existe, MySQL **rechaza** insertar la demanda por reserva (`codigo_movimiento_pedido = 0` porque no hay comprobante PED). Comprobar en `information_schema`; la migración **«MPR — tabla lista_produccion_detalle»** (catálogo Synap) intenta **eliminar** esa FK de forma idempotente.

```sql
SELECT IDArt, tipo_art_fab, stock_reserva FROM articulo WHERE IDArt = 127;
SELECT * FROM lista_produccion_detalle WHERE id_articulo = 127 AND COALESCE(en_proceso_produccion,'No')='No';
SELECT id_lista_produccion, id_articulo, cantidad_pendiente_prod, en_proceso_produccion, codigo_movimiento_opt
FROM lista_produccion_agrupada WHERE id_articulo = 127;
SELECT CONSTRAINT_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'lista_produccion_detalle'
  AND COLUMN_NAME = 'codigo_movimiento_pedido' AND REFERENCED_TABLE_NAME IS NOT NULL;
```

---

## Packs con demanda y pestaña Unidades vacía

La pestaña **Unidades** arma el desglose BOM con `listar_ventana_pack_unidades`: solo considera packs con **Cant. a fabricar > 0** y explota `en_abm` / `en_abm_formula` vía `bulk_id_en_abm` + `bulk_bom_detalle`.

- El **tooltip de receta** en la pestaña Packs usa `articulo.id_en_abm` para todos los artículos listados (sin exigir `ensamblado = 'Si'`).
- Si en maestro el artículo tiene **receta** (`id_en_abm` y fórmulas) pero **`ensamblado` no está en «Sí»**, antes la pestaña Unidades podía quedar vacía aunque el tooltip mostrara componentes. Synap alinea la explosión de demanda con el mismo criterio que el tooltip: para demanda MPR se usa `bulk_id_en_abm(..., requiere_ensamblado_si=False)`. El flujo de **armado** de OPT (pantallas que liberan stock ensamblado) sigue usando el criterio estricto `ensamblado = 'Si'`.

**Comprobación en datos:** para un pack que vea en Packs con cantidad a fabricar > 0 y receta visible:

```sql
SELECT IDArt, CodigoArticulo, ensamblado, id_en_abm FROM articulo WHERE IDArt = ?;
```

Si `id_en_abm` está informado y hay filas activas en `en_abm_formula`, deberían listarse componentes en Unidades tras el ajuste; si `id_en_abm` es NULL, hay que asociar receta en AdministraNET.

---

## Cuándo usar el diagnóstico

- La pantalla Demanda está vacía pero hay pedidos que deberían cumplir condiciones: ejecutar el comando con los **mismos filtros de fecha** (y búsqueda) que tiene la pantalla para ver si la query de origen (sección 1) devuelve filas y si detalle/agrupada se han actualizado (secciones 2–4).
- Revisar el estado de lista_produccion_detalle/agrupada tras pulsar Actualizar o antes de crear una OPT.
- Verificar que tipo_art_fab='Terminado' y estado_pedido_opt estén correctos en los datos.

---

## Referencias

- **Actualizar** ejecuta `actualizar_pedidos_produccion` (inserta/actualiza lista_produccion_detalle y lista_produccion_agrupada). La vista Demanda lee agrupada; al cargar la página también se ejecuta actualizar_pedidos_produccion con los filtros de sesión.
- Comando **inspeccionar_pedidos_pendientes_mpr** para revisar solo pedidos con estado_pedido_opt='Pendiente' y tipo_art_fab.
