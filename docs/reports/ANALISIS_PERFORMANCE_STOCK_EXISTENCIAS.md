# Análisis de rendimiento — informe Stock y existencias (`stock-existencias`)

**Fecha:** 30/04/2026  
**Alcance:** flujo actual (`reports/services/query_runner.py` → `_run_stock_existencias`, API POST dashboard, `reports/static/reports/js/dashboard.js`). Sin medición en producción en este documento; conclusiones por revisión de código y patrones típicos.

## 1. Resumen

El informe está diseñado para devolver **todo el universo de filas** que cumplan filtros (**sin `LIMIT`**), resolver **búsqueda y orden en el cliente** y **repintar la tabla completa** como HTML en cada interacción relevante. Eso es adecuado para volúmenes moderados, pero es la **principal fuente de lag perceptible** cuando hay **decenas de miles de filas o más**: el cuello de botella suele pasar de MySQL → transferencia JSON → **parseo + orden + filtrado + `innerHTML` masivo** en el navegador.

## 2. Backend (MySQL + Python)

### 2.1 Consulta principal

- **Un solo `SELECT`** con `FROM stock_deposito sd` + `INNER JOIN articulo` + `deposito` + `LEFT JOIN` marca, rubro, subrubro.
- **`LEFT JOIN` a una subconsulta agregada (`reservado`)** que lee `stockp` y `comp_ped` con filtros de PED, estados *En preparación* / *Preparado*, anulados, etc., y hace **`GROUP BY IDArt, CodDeposito`**.  
  - **Coste:** depende fuertemente del volumen de `stockp`/`comp_ped` y de índices; en bases grandes puede ser **la parte más costosa del plan** si el optimizador no puede reducir bien el conjunto antes del agregado.
- **`ORDER BY a.NombreArticulo ASC, sd.id_deposito ASC`**: obliga a ordenar el resultado completo antes de enviarlo al cliente (coste O(n log n) en filas devueltas).
- **`cursor.fetchall()`**: carga **todas** las filas en memoria del proceso Python de una vez; no hay paginación ni streaming.

### 2.2 Conexión

- Se abre **`MySQLdb.connect` dedicado** por ejecución del informe (no el pool compartido que usan otros runners en partes del código). En redes lentas o muchas peticiones concurrentes, el **handshake TCP + auth** suma latencia fija; suele ser **pequeño** frente al tiempo de la consulta en bases grandes.

### 2.3 Post-procesado Python

- Bucle **O(n)** por fila armando diccionarios (conversiones numéricas, `codigo_barras` como `str`). **Coste bajo** frente a I/O y SQL salvo *n* enorme.

### 2.4 Límites configurados

- `SET SESSION max_execution_time = 300000` (300 s) e hint `MAX_EXECUTION_TIME` en el SQL: protegen al servidor; no mejoran latencia percibida si la consulta va al límite.
- Cliente HTTP: **`EXTENDED_REPORT_FETCH_TIMEOUT_MS = 300000`** (`dashboard.js`) para este slug: evita cortes prematuros en cargas largas.

## 3. Red y serialización

- La respuesta es un **único JSON** con el array `data` completo. Con muchas filas y textos largos (`nombre`, `rubro`, `subrubro`, `codigo_barras`, etc.), el **tamaño del payload** crece linealmente: más tiempo de **serialización Django**, **compresión HTTP** (si está activa) y **descarga + `JSON.parse`** en el navegador.

## 4. Frontend (`renderStockExistenciasTableFromState`)

### 4.1 Búsqueda

- Hay **debounce de 400 ms** en el campo `#stock_existencias_busqueda` antes de volver a renderizar. Bien para evitar trabajo en cada tecla; el coste por ejecución sigue siendo **proporcional al número de filas** en memoria.

### 4.2 Orden y agrupación

- Cada clic en cabecera ordenable y cada cambio de agrupación (tags) vuelve a ejecutar **filtrado + orden + construcción de una cadena HTML muy grande** y asignación a **`innerHTML`**.  
- El navegador debe **parsear HTML**, construir el árbol DOM y aplicar estilos para **todas** las filas visibles (aunque grupos estén colapsados, el HTML del cuerpo puede seguir siendo grande según implementación).

### 4.3 Ausencia de virtualización

- No hay **ventana deslizante** (virtual scroll): todas las filas de detalle presentes en el DOM tras cada render relevante. Con **miles de filas** el coste de layout/paint y memoria DOM es una **causa típica de lag o bloqueos breves del hilo principal**.

## 5. Cómo comprobar en tu entorno (causa vs síntoma)

| Síntoma | Qué medir |
|--------|-----------|
| Espera larga con modal “Cargando…” | Tiempo hasta primera respuesta en **Network** (TTFB + descarga); en servidor, tiempo de `cursor.execute` vs `fetchall` (logs o APM). |
| UI fluida tras cargar pero al buscar/ordenar se “congela” | **Performance** del navegador: largos *tasks* al ejecutar `renderStockExistenciasTableFromState`; tamaño de `stockExistenciasDataset.rows.length`. |
| MySQL alto CPU / slow log | **`EXPLAIN ANALYZE`** (MySQL 8.0.18+) o `EXPLAIN` sobre el SQL completo; revisar uso de la subconsulta `res` y de `stock_deposito` + `articulo`. |

**Consulta útil en MySQL** (tras cargar el informe, con mismos filtros): comparar `meta.row_count` del JSON con el tiempo de la query en slow log.

## 6. Hipótesis de causa ordenadas (más probable primero)

1. **Volumen de datos sin paginación** + **repintado completo de tabla en cliente** (búsqueda, orden, agrupación).
2. **Subconsulta de reservado** + **JOIN masivo** `stock_deposito`–`articulo` y **orden global** por nombre.
3. **Payload JSON grande** (transferencia + parse).
4. Conexión nueva a MySQL y falta de índices adecuados en tablas legacy (depende de cada base).

## 7. Líneas de mejora (sin implementar aquí)

- **Servidor:** paginación o “carga progresiva” + orden/búsqueda en SQL donde aplique; materializar o cachear agregado de reservado si el negocio lo permite; revisar índices (`stock_deposito`, `stockp`, `comp_ped`, claves de `articulo` usadas en filtros).
- **Cliente:** virtualización de filas; **DocumentFragment** o actualizar solo nodos cambiantes en lugar de sustituir todo el `innerHTML`; **Web Worker** para filtrar/ordenar datasets muy grandes (más complejo).
- **Producto:** default “no incluir stock cero” ya reduce filas; reforzar filtros de depósito/rubro en bases muy grandes.

## 8. Referencias de código

- Runner: `QueryRunnerService._run_stock_existencias` — `reports/services/query_runner.py`.
- Timeout extendido y `limit`: `fetchDashboardData`, `usesExtendedQueryTimeout`, `STOCK_EXISTENCIAS_API_LIMIT` — `reports/static/reports/js/dashboard.js`.
- Render y debounce búsqueda: `renderStockExistenciasTableFromState`, `renderStockExistenciasTable` — mismo archivo.
- Especificación funcional: `docs/reports/SPEC_STOCK_EXISTENCIAS.md`.
