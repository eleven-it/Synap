# Informe: Trazabilidad OPT 92 y validación de tablas

**Fecha:** 2026-03-10  
**Objetivo:** Validar la trazabilidad completa de la OPT 92 en las tablas MySQL (OPT, OPPs, OPAs y Cierre) y documentar el hallazgo sobre la pantalla de cierre del wizard (Pendiente: 0 vs restante por armar).

---

## 1. Validación de tablas para trazabilidad OPT 92

A continuación se describe qué debe existir en cada tabla para una OPT 92 con flujo completo (crear OPT → liberar OPT → registrar OPP → ejecutar armado(s) → cerrar OPT) y cómo validarlo. **No se han aplicado cambios en código**; este documento sirve como checklist para ejecutar consultas en la base y detectar faltantes o inconsistencias.

### 1.1 lista_produccion_agrupada

**Uso en el flujo:** Cabecera/líneas de la OPT por artículo (pack). Se crea/actualiza al crear OPT, al liberar, al registrar OPP (decremento de `cantidad_pendiente_prod`) y al cerrar (`en_proceso_produccion = 'No'`).

**Validar para OPT 92:**

- Debe haber al menos una fila con `id_lista_produccion = 92`.
- Columnas relevantes:
  - `id_articulo`, `cantidad_pedida`, `cantidad_pendiente_prod`, `en_proceso_produccion`
  - Si la OPT fue liberada: `en_proceso_produccion = 'Si'`, `id_opt`, `id_operario_opt` (según esquema), `codigo_movimiento_opt` (código del movimiento de liberación).
- Si la OPT está “producida” (todas las OPP registradas): `SUM(cantidad_pendiente_prod)` sobre filas con `id_lista_produccion = 92` debe ser **0**.
- Si la OPT está cerrada: `en_proceso_produccion = 'No'` en todas las filas con `id_lista_produccion = 92`.

**Consultas sugeridas:**

```sql
SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, en_proceso_produccion, codigo_movimiento_opt
FROM lista_produccion_agrupada
WHERE id_lista_produccion = 92;

SELECT id_lista_produccion, SUM(cantidad_pendiente_prod) AS total_pendiente
FROM lista_produccion_agrupada
WHERE id_lista_produccion = 92
GROUP BY id_lista_produccion;
```

---

### 1.2 lista_produccion_detalle

**Uso en el flujo:** Desglose por pedido (comp_ped) asociado a la OPT. Se actualiza al crear OPT (vínculo con `id_lista_produccion`), y en OPP (`cantidad_pendiente_prod` se ajusta según esquema).

**Validar para OPT 92:**

- Debe haber filas con `id_lista_produccion = 92` (o vinculadas vía `id_lista_produccion` según el flujo de creación).
- Coherencia con `lista_produccion_agrupada`: mismos artículos/cantidades según el diseño (agrupada = resumen por artículo, detalle = por pedido).

**Consulta sugerida:**

```sql
SELECT id_lista_produccion, id_articulo, cantidad_pedida, cantidad_pendiente_prod, codigo_movimiento_pedido
FROM lista_produccion_detalle
WHERE id_lista_produccion = 92;
```

---

### 1.3 lista_produccion_historico

**Uso en el flujo:** Registro de eventos por tipo: **OPT** (liberación), **OPP** (parte de producción), **Armado** (OPA). No se escribe un evento específico “Cierre”; el cierre solo actualiza agrupada/detalle y `comp_ped`.

**Validar para OPT 92:**

- Debe haber al menos un registro con `id_lista_produccion = 92` y `tipo_evento = 'OPT'` (liberación).
- Debe haber registros con `id_lista_produccion = 92` y `tipo_evento = 'OPP'` (uno o más según OPPs registradas).
- Debe haber al menos un registro con `id_lista_produccion = 92` y `tipo_evento = 'Armado'` por cada armado ejecutado (en el código actual se inserta en `ejecutar_armado` con `id_lista_produccion`).
- No existe evento “Cierre” en esta tabla; el cierre es solo cambio de estado en agrupada/detalle y en `comp_ped`.

**Consulta sugerida:**

```sql
SELECT tipo_evento, id_articulo, id_articulo_formula, cantidad_movimiento, cantidad_armada, codigo_movimiento_mstock, id_lista_produccion, fecha, hora_evento
FROM lista_produccion_historico
WHERE id_lista_produccion = 92
ORDER BY fecha, hora_evento;
```

---

### 1.4 movimiento_stock

**Uso en el flujo:** Un movimiento por cada acción: liberación OPT, cada OPP y cada OPA (armado). El cierre no crea movimiento.

**Validar para OPT 92:**

- **OPT (liberación):** Al menos un registro con `tipo_mov = 'OPT'` y `detalle` conteniendo la referencia a la OPT 92 (por ejemplo `"OPT 92"` o similar según cómo se arma el texto en `ejecutar_liberar_opt`).
- **OPP:** Tantos registros como OPPs registradas, con `tipo_mov = 'OPP'` y `detalle` que mencione la OPT 92 (p. ej. `"OPT 92 desde"` o el patrón usado en `listar_opp_por_opt`).
- **OPA (armado):** Tantos registros como armados ejecutados para la OPT 92, con `tipo_mov = 'OPA'` (en código actual; antes podía guardarse `'Armado'` — si hay datos legacy, considerar ambos). El `detalle` debe contener `"OPT 92"` (patrón usado en `get_cantidades_armadas_por_opt`).
- **Cierre:** No debe haber ningún movimiento con `tipo_mov = 'Cierre'`; el cierre no genera fila aquí.

**Consultas sugeridas:**

```sql
SELECT codigo_movimiento, nro_comprobante, tipo_mov, motivo_movimiento, detalle, fecha, anulado
FROM movimiento_stock
WHERE (INSTR(COALESCE(detalle,''), 'OPT 92') > 0 OR INSTR(COALESCE(detalle,''), 'OPT 92)') > 0)
  AND COALESCE(anulado,'No') <> 'Si'
ORDER BY codigo_movimiento;

-- Por tipo
SELECT tipo_mov, COUNT(*) AS cantidad
FROM movimiento_stock
WHERE (INSTR(COALESCE(detalle,''), 'OPT 92') > 0 OR INSTR(COALESCE(detalle,''), 'OPT 92)') > 0)
  AND COALESCE(anulado,'No') <> 'Si'
GROUP BY tipo_mov;
```

---

### 1.5 stock

**Uso en el flujo:** Cada movimiento (OPT, OPP, OPA) genera renglones en `stock`: entradas/salidas por artículo, vinculados por `CodigoMovimiento`. Cuando la tabla incluye las columnas opcionales `codigo_mov_opt` e `id_en_abm`, Synap MPR las rellena para vincular cada renglón directamente a la OPT (código del movimiento de liberación) y al conjunto de armado (BOM); ver `docs/general/tablas/stock.md` §4.

**Validar para OPT 92:**

- Obtener los `codigo_movimiento` de `movimiento_stock` asociados a la OPT 92 (OPT, OPP, OPA) como en la consulta anterior.
- Para esos códigos, en `stock` deben existir renglones con `CodigoMovimiento` igual a cada código, con `Entrada` y `Salida` coherentes con la lógica:
  - **OPT:** entradas de productos a depósito de producción.
  - **OPP:** salidas desde producción, entradas a Semi/Scrap/etc. según distribución.
  - **OPA:** salidas de componentes desde depósito origen (Semi), entradas del artículo armado en depósito destino (Terminado).

**Consultas sugeridas:**

```sql
-- Códigos de movimiento de la OPT 92
SELECT codigo_movimiento FROM movimiento_stock
WHERE (INSTR(COALESCE(detalle,''), 'OPT 92') > 0 OR INSTR(COALESCE(detalle,''), 'OPT 92)') > 0)
  AND COALESCE(anulado,'No') <> 'Si';

-- Renglones de stock para esos códigos (usar los codigo_movimiento obtenidos)
SELECT s.CodigoMovimiento, s.IDArt, s.Entrada, s.Salida, s.id_deposito (si existe)
FROM stock s
WHERE s.CodigoMovimiento IN (<codigos de la consulta anterior>)
ORDER BY s.CodigoMovimiento, s.IDArt;
```

---

### 1.6 stock_deposito

**Uso en el flujo:** Saldos por artículo y depósito. Se actualizan en OPP (movimientos entre depósitos) y en OPA (baja de componentes en origen, alta del armado en destino).

**Validar para OPT 92:**

- No hay una columna “OPT” en `stock_deposito`; la trazabilidad es indirecta vía `stock` + `movimiento_stock`.
- Verificar que, después de OPT + OPP + OPA para la 92, los saldos de los artículos y depósitos afectados sean coherentes con las entradas/salidas en `stock` (suma de movimientos = saldo actual para cada par artículo–depósito).

**En resumen:** Revisar que los `codigo_movimiento` de la OPT 92 generen en `stock` las entradas/salidas esperadas y que la suma por (id_articulo, id_deposito) coincida con `stock_deposito`.

---

### 1.7 comp_ped

**Uso en el flujo:** Estado de pedidos de venta respecto de producción. Al liberar la OPT se puede marcar pedidos asociados como `estado_pedido_opt = 'Produccion'`; al **cerrar** la OPT se actualizan a `'Terminado'` (en `cerrar_opt` → `_actualizar_comp_ped_estado_produccion(..., 'Terminado')`).

**Validar para OPT 92:**

- Los pedidos vinculados a la OPT 92 (vía `lista_produccion_detalle.codigo_movimiento_pedido`) deben tener en `comp_ped` el `estado_pedido_opt` coherente:
  - Si la OPT está cerrada: esos pedidos deberían estar en `'Terminado'`.
  - Si la OPT está abierta pero ya liberada: podrían estar en `'Produccion'`.

**Consulta sugerida:**

```sql
SELECT cp.CodigoMovimiento, cp.estado_pedido_opt, ...
FROM comp_ped cp
WHERE cp.CodigoMovimiento IN (
  SELECT codigo_movimiento_pedido FROM lista_produccion_detalle WHERE id_lista_produccion = 92
);
```

---

## 2. Resumen de comprobaciones (checklist)

| Tabla                         | OPT (liberación) | OPP(s) | OPA(s) (armado) | Cierre        |
|------------------------------|------------------|--------|------------------|---------------|
| lista_produccion_agrupada    | Sí (en_proceso='Si', codigo_movimiento_opt, etc.) | Sí (cantidad_pendiente_prod bajando) | No escribe aquí | Sí (en_proceso='No') |
| lista_produccion_detalle     | Sí (vínculo id_lista) | Sí (ajustes según diseño) | No escribe aquí | No escribe aquí |
| lista_produccion_historico   | Sí (tipo_evento='OPT') | Sí (tipo_evento='OPP') | Sí (tipo_evento='Armado') | No (no hay evento Cierre) |
| movimiento_stock             | Sí (tipo_mov='OPT') | Sí (tipo_mov='OPP') | Sí (tipo_mov='OPA') | No (no crea movimiento) |
| stock                        | Sí (renglones por codigo_movimiento) | Sí | Sí | No |
| stock_deposito               | Indirecto vía stock | Sí (actualización saldos) | Sí (actualización saldos) | No |
| comp_ped                     | Opcional (Produccion) | No | No | Sí (Terminado) |

Si al ejecutar las consultas anteriores falta algún registro para la OPT 92 (por ejemplo ningún OPA, o ningún OPT en historico), eso indica una brecha de trazabilidad o un flujo no ejecutado.

---

## 3. Hallazgo: Paso 5 del wizard — “Pendiente: 0” vs “restante por armar”

### 3.1 Qué está pasando

En el **Paso 5 (Cierre)** del asistente de producción se muestra:

- **“Pendiente: X unidades.”**

Ese valor corresponde a **`total_pendiente`** calculado en la vista del wizard como:

```text
total_pendiente = sum(cantidad_pendiente_prod) de las líneas de la OPT
```

Es decir, es el **pendiente de producción (OPP)**:
- Cuando todas las OPP están registradas, `cantidad_pendiente_prod = 0` en todas las líneas → **total_pendiente = 0**.
- Ese “0” significa “0 unidades pendientes de registrar como OPP”, **no** “0 unidades pendientes de armar”.

Por tanto, si el usuario armó **solo 1 unidad de 1000**:
- El sistema muestra **“Pendiente: 0 unidades”** (correcto para OPP).
- Pero **no** muestra que aún quedan **999 unidades por armar** (cantidad_pedida − cantidad_ya_armada).

### 3.2 Dónde está el problema en el código

- **Vista del wizard, paso 5** (`mpr/views.py`, contexto para `paso == 5`):  
  Solo se envía `total_pendiente` (suma de `cantidad_pendiente_prod`).  
  **No** se calcula ni se envía:
  - `cantidades_armadas` (get_cantidades_armadas_por_opt),
  - `total_restante_armar` (suma de `max(0, cantidad_pedida - cantidad_ya_armada)`),
  - `hay_restante_armar` (si hay algún artículo con restante por armar > 0).

- **Plantilla del wizard paso 5** (`mpr/templates/mpr/wizard.html`):  
  Muestra solo “Pendiente: {{ total_pendiente }} unidades.”  
  No diferencia entre:
  - Pendiente de **producción (OPP)**.
  - Pendiente de **armado** (restante por armar).

- El botón **“Armar más”** está siempre visible en el paso 5 (no depende de `hay_restante_armar`), pero el mensaje “Pendiente: 0” sugiere que no queda nada por hacer, cuando en realidad sí queda armado por hacer.

### 3.3 Conclusión y recomendación (sin implementar aún)

- **Cumplimiento de trazabilidad:** Depende de que en base de datos existan los registros indicados en las secciones 1.1–1.7 para la OPT 92. Las consultas SQL anteriores permiten validar si algo no se cumple o hay diferencias.
- **UX del wizard:** Para que quede claro que se puede seguir armando mientras haya disponibilidad, se recomienda:
  1. En el paso 5 del wizard, calcular y enviar al contexto: `cantidades_armadas`, `total_restante_armar` y `hay_restante_armar` (igual que en la vista de detalle de OPT).
  2. En la plantilla, distinguir explícitamente:
     - “Pendiente producción (OPP): X unidades.”
     - “Restante por armar: Y unidades.” (y/o “Puede seguir armando mientras haya stock.”)
  3. Opcional: resaltar o habilitar de forma más evidente “Armar más” cuando `hay_restante_armar` sea verdadero.

No se han realizado cambios en el código en esta fase; solo análisis e informe.
