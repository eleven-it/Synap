# Análisis: «Generar OPT» (Synap) vs «Generar» en CargaMovStock (VB6) motivo 10 «Pedido Producción»

## Resumen

**No son el mismo proceso.** En VB6 hay dos acciones distintas:

| Acción | Dónde (VB6) | Qué hace |
|--------|-------------|----------|
| **Crear la OPT** | Lista_Pedidos_OPT (agrupar / alta lista) | Inserta/actualiza `lista_produccion_agrupada` (lista de artículos a producir). |
| **Ejecutar la OPT** | CargaMovStock, motivo 10 «Pedido Producción», botón «Generar» | Genera el **movimiento de stock** (MSTOCK): escribe en `stock`, `stock_deposito`, actualiza `lista_produccion_agrupada.cantidad_pendiente_prod` e inserta en `lista_produccion_historico`. |

El botón **«Generar OPT»** en Synap equivale a **crear** la OPT (como Lista_Pedidos_OPT en VB6), **no** a ejecutarla (CargaMovStock «Generar» motivo 10).

---

## 1. VB6 – CargaMovStock, motivo 10, botón «Generar» (Aceptar_Click)

### Contexto

- El usuario abre **CargaMovStock** con motivo = 10 («Pedido Producción»).
- La grilla **CuerpoStock** ya está cargada con las líneas de una **OPT ya existente** (componentes de receta; cada fila tiene `id_stock` = `id_lista_produccion` de `lista_produccion_agrupada`, cantidades, etc.).

### Qué hace «Generar» (Aceptar_Click)

1. Pide confirmación: «¿Desea generar el Movimiento de Stock?».
2. Abre transacción, incrementa **codmov** (codigo de movimiento).
3. Obtiene próximo número de comprobante **MSTOCK** desde `talonarios` (id_punto_venta, TipoComprobante = 'MSTOCK').
4. Por **cada fila** de `CuerpoStock.Recordset`:
   - Inserta en **stock** (una línea del movimiento: artículo, cantidad, entrada/salida, depósito, CodigoMovimiento, etc.).
   - Actualiza **stock_deposito** (saldo del depósito).
   - **Si Motivo.ListIndex = 10** (Pedido Producción):
     - Abre `lista_produccion_agrupada` WHERE `id_lista_produccion` = `CuerpoStock.Recordset.Fields!id_stock`.
     - Actualiza: `cantidad_pendiente_prod = cantidad_pendiente_prod - cantidad_armada_opt`.
     - Inserta en **lista_produccion_historico** (id_articulo, id_articulo_formula, cantidad_pedida, cantidad_movimiento, cantidad_armada, id_deposito, codigo_movimiento_mstock, codigo_movimiento_opt, id_usuario, Fecha).
5. Inserta en **movimiento_stock** (cabecera del movimiento) con `tipo_mov = "OPT"`.
6. Commit de la transacción.

Referencias en CargaMovStock.frm: líneas 3472 (Aceptar_Click), 4077–4106 (motivo 10: lista_produccion_agrupada y lista_produccion_historico), 4387–4388 (tipo_mov = "OPT"), 4459 (post-proceso motivo 10).

---

## 2. VB6 – Lista_Pedidos_OPT: crear/agrupar la OPT

- Lee **lista_produccion_detalle** con `en_proceso_produccion = 'No'`, agrupa por `id_articulo` (SUM cantidad_pedida).
- Para cada artículo:
  - Si ya existe fila en **lista_produccion_agrupada** para ese id_articulo: UPDATE (cantidad_pedida y cantidad_pendiente_prod += cantidad agrupada).
  - Si no existe: INSERT en **lista_produccion_agrupada** (id_articulo, cantidad_pedida, cantidad_pendiente_prod, id_usuario, en_proceso_produccion = 'No').
- UPDATE **lista_produccion_detalle** SET en_proceso_produccion = 'Si'.

Esto **crea** (o actualiza) la OPT: las filas en `lista_produccion_agrupada` que luego se pueden «ejecutar» desde CargaMovStock motivo 10.

Referencias en Lista_Pedidos_OPT.frm: líneas 3478–3511 (consulta agrupada e INSERT/UPDATE en lista_produccion_agrupada).

---

## 3. Synap – «Generar OPT» (ventana_pack_agrupar)

- El usuario eligió artículos/cantidades en «Pedido producción trabajo (OPT)» y en «Confirmar OPT» pulsa **«Generar OPT»**.
- La vista llama a **crear_opt_multiples_articulos** (mpr/services.py):
  - Por cada (id_articulo, cantidad) con cantidad > 0:
    - **INSERT** en **lista_produccion_agrupada** (id_articulo, cantidad_pedida, cantidad_pendiente_prod, id_usuario, en_proceso_produccion = 'Si').
  - Crea registros **Opt** y **OptLinea** en Django para agrupar las líneas.
- **No** escribe en `stock`, `stock_deposito`, `movimiento_stock` ni `lista_produccion_historico`.

Por tanto, **«Generar OPT» en Synap = crear la OPT** (análogo a Lista_Pedidos_OPT agrupar en VB6), **no** a ejecutar el movimiento de stock (CargaMovStock «Generar» motivo 10).

---

## 4. Equivalencia y posibles mejoras

| Proceso | VB6 | Synap |
|---------|-----|--------|
| **Crear OPT** | Lista_Pedidos_OPT (agrupar) → INSERT/UPDATE lista_produccion_agrupada | «Generar OPT» → crear_opt_multiples_articulos → INSERT lista_produccion_agrupada |
| **Ejecutar OPT** (generar MSTOCK y actualizar pendientes) | CargaMovStock motivo 10, «Generar» → stock, stock_deposito, movimiento_stock, actualizar lista_produccion_agrupada, lista_produccion_historico | ejecutar_liberar_opt (libera OPT desde detalle de OP) u otro flujo equivalente a CargaMovStock |

Para que en Synap exista el **mismo proceso** que el botón «Generar» de CargaMovStock con motivo 10, haría falta un flujo que:

1. Parta de una OPT ya creada (lista_produccion_agrupada con líneas a producir).
2. Permita elegir cantidades a «armar» por línea (o usar las pendientes).
3. Al confirmar, ejecute el equivalente a Aceptar_Click motivo 10: codmov, talonario MSTOCK, INSERT stock, actualizar stock_deposito, actualizar cantidad_pendiente_prod en lista_produccion_agrupada, INSERT lista_produccion_historico, INSERT movimiento_stock con tipo_mov = "OPT".

Ese flujo en Synap está cubierto en parte por **ejecutar_liberar_opt** (liberación desde una OP/detalle); la alineación exacta con CargaMovStock (pantalla tipo grilla de componentes y depósito) sería un desarrollo aparte si se desea paridad 1:1 con VB6.

---

## 5. Dónde se “ejecuta” la OPT en Synap (equivalente a CargaMovStock “Generar” motivo 10)

El proceso de **ejecutar** la OPT (generar MSTOCK, actualizar pendientes e histórico) en Synap está en el flujo que sigue a la **creación** de la OPT:

- **Pantalla 1:** Pedido producción trabajo (OPT) — selección de artículos y cantidades; “Continuar” → va a Confirmar OPT.
- **Pantalla 2:** Confirmar OPT (agrupar) — tabla Unidades, “Generar OPT” → **crea** la OPT (INSERT lista_produccion_agrupada) y redirige al **Detalle de la OP**.
- **Pantalla 3 (flujo posterior):** **Detalle de la OP** (`/mpr/ordenes/<id_lista>/`) — desde aquí el usuario puede hacer **“Liberar (OPT)”**, que lleva al formulario **Liberar a producción (OPT)** (`/mpr/ordenes/<id_lista>/liberar-opt/`). Al confirmar cantidad a liberar y depósito destino, se llama a **ejecutar_liberar_opt**, que es el equivalente funcional al botón «Generar» de CargaMovStock con motivo 10.

Por tanto: **sí, el “Ejecutar OPT” (proceso VB6 CargaMovStock motivo 10) en Synap se dispara desde lo que sería la pantalla 3** (detalle de la OP → Liberar OPT).

### ¿Cumple con todo el proceso de VB6?

**Sí**, en lo esencial. `ejecutar_liberar_opt` (mpr/services.py) realiza:

| Paso VB6 (Aceptar_Click motivo 10) | Synap (ejecutar_liberar_opt) |
|------------------------------------|------------------------------|
| Incrementar codmov | ✓ UPDATE codmov |
| Obtener y actualizar talonario MSTOCK (Nro comprobante) | ✓ SELECT/UPDATE talonarios WHERE TipoComprobante = 'MSTOCK' |
| INSERT movimiento_stock (tipo_mov = "OPT") | ✓ INSERT movimiento_stock con tipo_mov = 'OPT' |
| Por cada línea: INSERT stock (Entrada), actualizar stock_deposito (Saldo) | ✓ Por cada línea de la distribución: INSERT stock, UPDATE o INSERT stock_deposito |
| UPDATE lista_produccion_agrupada (cantidad_pendiente_prod -= cantidad) | ✓ UPDATE lista_produccion_agrupada SET cantidad_pendiente_prod = ... - qty |
| INSERT lista_produccion_historico | ✓ Si existe la tabla, INSERT por cada línea (id_articulo, cantidad_pedida, cantidad_movimiento, id_deposito, codigo_movimiento_mstock, codigo_movimiento_opt) |
| Marcar OP en proceso | ✓ UPDATE lista_produccion_agrupada SET en_proceso_produccion = 'Si' |

**Diferencias menores:**

- En VB6 la grilla de CargaMovStock motivo 10 puede tener una fila por **componente** (id_articulo_formula, cantidad_armada_opt); en ese caso lista_produccion_historico guarda id_articulo (artículo de la OP) e id_articulo_formula (componente). En Synap, Liberar OPT trabaja por **línea de OP** (artículo a producir); el historico se escribe por línea con `id_articulo_formula = None`. Ver más abajo (sección 7) cuándo VB6 guarda el componente y por qué Synap no lo hace.
- Contabilidad (generar_asiento_cont en VB6): en Synap no se invoca asiento contable desde ejecutar_liberar_opt; si la base lo requiere, sería un desarrollo aparte.

---

## 7. Cuándo VB6 guarda id_articulo_formula en lista_produccion_historico y por qué Synap no

### En VB6

Al generar el movimiento (Aceptar_Click, motivo 10), por **cada fila** del grid CuerpoStock se escribe un registro en lista_produccion_historico con:

- **id_articulo** = artículo de la OP (obtenido de lista_produccion_agrupada mediante id_stock de la fila).
- **id_articulo_formula** = `CuerpoStock.Recordset.Fields!IDArt` (el IDArt de **esa fila** del grid).

El contenido del grid depende de cómo se cargó desde **Lista_Pedidos_OPT** al abrir CargaMovStock con motivo 10:

1. **Artículo de la OP sin fórmula (no ensamblado):** Lista_Pedidos_OPT agrega **una fila** al grid: la de ese artículo. En esa fila, IDArt = id_articulo de la OP. Por tanto en historico: id_articulo = id_articulo_formula (mismo artículo).
2. **Artículo de la OP con fórmula (ensamblado = 'Si'):** Lista_Pedidos_OPT no agrega una fila directa; llama a **Desarme()**, que recorre **en_abm_formula** y por cada componente llama a **MstockE()**. MstockE agrega **una fila por componente**, con IDArt = componente (id_articulo de la fórmula) e id_stock = id_lista_produccion. En historico, para cada una de esas filas: id_articulo = artículo a producir (el armado), id_articulo_formula = IDArt de la fila = **componente**.

Resumen VB6: **id_articulo_formula se guarda siempre** (en código es el IDArt de la fila). Cuando la fila es de un **componente** (grid cargado por Desarme), id_articulo_formula es el componente; cuando la fila es del **artículo** (sin BOM), id_articulo_formula coincide con id_articulo.

### Comportamiento en Synap (trazabilidad)

En Synap, **Liberar OPT** escribe en lista_produccion_historico **siempre con id_articulo_formula informado** (a fines de trazabilidad). Por defecto se usa el artículo de la línea: `id_articulo_formula = id_articulo` cuando no hay desglose por componente (equivalente al caso VB6 “fila de artículo”). Si en el futuro el flujo aporta líneas por componente (p. ej. explosión BOM), se puede enviar `id_articulo_formula` distinto en la línea y se grabará tal cual.

Para trazabilidad al nivel de VB6 cuando el artículo tiene BOM (un registro por componente), habría que explotar en_abm_formula y escribir en historico **un registro por componente** (id_articulo = artículo a producir, id_articulo_formula = componente, cantidad_movimiento = cantidad del componente). Eso sería una ampliación opcional del flujo.

---

## 8. Uso real de id_articulo_formula: trazabilidad y motivo 11

### De dónde sale que se usa id_articulo_formula

No es una inferencia solo del esquema. En **CargaMovStock.frm** (motivo 10), al grabar el movimiento se asigna explícitamente:

```vb
rs_lista_produccion_historico.Fields!id_articulo = Obtener_Datos_lista_produccion_agrupada(...)
rs_lista_produccion_historico.Fields!id_articulo_formula = CuerpoStock.Recordset.Fields!IDArt
```

Es decir: en VB6 **siempre** se escribe `id_articulo_formula` con el IDArt de la fila del grid (artículo o componente según cómo se cargó el grid).

### ¿Para qué sirve? ¿Es trazabilidad?

Sí. La tabla **lista_produccion_historico** se usa como **trazabilidad** de lo liberado en cada movimiento OPT: qué artículo de la OP (id_articulo), con qué detalle de fórmula si aplica (id_articulo_formula), cantidades, depósito, código de movimiento, etc. Cuando la fila del grid es un **componente** (BOM explotada), id_articulo_formula permite saber “este movimiento liberó X del componente Y para producir el artículo Z”. En el código VB6 y en Synap no aparece ningún **lector** de esta tabla (reportes o pantallas); solo se **escribe** al generar el OPT. El uso es por tanto de **registro histórico** para auditoría o consultas futuras.

### ¿Se usa en motivo 11 (Parte producción / OPP)?

**No.** En CargaMovStock, la escritura en **lista_produccion_historico** está dentro de un único bloque condicional: **`If Motivo.ListIndex = 10 Then`** (líneas 4077–4106). Para **motivo 11** (Parte producción) el código solo actualiza stockp (cantidad_fab_pendiente_opt), asigna codigo_mov_ped_opt al movimiento de stock y genera la transferencia (salida origen / entrada destino); **no** escribe en lista_produccion_historico ni utiliza id_articulo_formula. Por tanto, en VB6 **id_articulo_formula y lista_produccion_historico son exclusivos del motivo 10 (Pedido producción / OPT)**; no forman parte del flujo del motivo 11 (Parte producción / OPP).

---

## 6. Conclusión

- **«Generar OPT» en Synap** debe (y actualmente lo hace) disparar el proceso de **crear** la OPT (lista_produccion_agrupada), equivalente a Lista_Pedidos_OPT en VB6.
- **No** debe disparar el mismo proceso que «Generar» en CargaMovStock motivo 10, porque ese proceso **ejecuta** la OPT (genera el movimiento de stock y actualiza pendientes e histórico).
- El **ejecutar OPT** (proceso de CargaMovStock “Generar” motivo 10) en Synap está en la **pantalla 3** (Detalle de la OP → Liberar OPT) y **sí cumple** con todo el proceso: codmov, MSTOCK, movimiento_stock OPT, stock, stock_deposito, actualización de lista_produccion_agrupada e inserción en lista_produccion_historico.

Documento de referencia: flujo OPT en **docs/mpr/FLUJO_VB6_PEDIDO_PRODUCCION_MPR.md** y tablas en **docs/mpr/SCHEMA_MPR_ADMINISTRANET92.md**.
