# Tabla Stock y Existencias — paridad visual con VO

**Fecha de referencia:** 30/04/2026  
**Informe:** `stock-existencias` (`reports/static/reports/js/dashboard.js`, `renderStockExistenciasTableFromState`).

## Objetivo

Rejilla con bordes, cabeceras en franjas pastel (esmeralda / violeta / cielo), celdas **sin truncar** (`break-words`, `min-w-0`, `table-fixed`), cabecera **sticky** por celda (`th` + `position: sticky`), contenedor con **scroll vertical** (`max-h-[min(72vh,48rem)]`, `[scrollbar-gutter:stable]`).

## Stock ≤ 0

Si la columna **Stock** (`r.stock`) es un número finito y **≤ 0**, toda la fila de detalle usa fondo **rojo más contrastante** (`bg-red-100`, bordes `border-red-300` / `dark:bg-red-950/55`, `dark:border-red-800`). Las columnas **Stock, Reservado y Disponible** van siempre **alineadas a la derecha** (clases Tailwind + regla CSS en columnas 7–9). La columna **Marca** no se muestra en la tabla ni entra en las dimensiones de agrupación.

**Orden por columnas:** cabeceras ordenables: **ID manual**, **Código barras**, nombre artículo, rubro, subrubro (depósito y cantidades no). ID manual y código de barras usan `localeCompare` con `numeric: true` para orden natural de dígitos. Al pulsar una cabecera ordenable se muestra el mismo modal fullscreen de espera que en la carga del informe (`#reports-legacy-query-loading-modal`), con textos «Ordenando tabla» / «Aplicando el criterio de orden…», y se oculta al terminar el redibujado (doble `requestAnimationFrame` para permitir un frame de pintado del modal antes del trabajo pesado).

**Anchos de columna:** `colgroup` con porcentajes: las tres columnas numéricas tienen cada una un **80 %** del ancho equitativo que tendrían en un reparto 9× igual; el espacio recuperado se reparte entre **Nombre artículo**, **Rubro** y **Subrubro** (mismo incremento cada una). **ID manual:** cabecera y celdas de filas `se-stock-detail-row` alineadas a la **derecha**; las filas de agrupación mantienen la primera celda a la izquierda (texto «Dimensión: valor»).

## Código de barras

- **Backend** (`query_runner._run_stock_existencias`): en SQL, `codigo_barras` usa primero **`NroCodBarraF`** y, si está vacío, **`NroCodBarra`**. Luego se serializa siempre como **cadena** en el JSON (evita que el cliente reciba `number` y muestre notación científica).
- **Frontend** (`formatStockExistenciasBarras`): refuerzo si el valor llegara numérico (`toLocaleString("fullwide")` / entero seguro).

## Archivos

- `reports/static/reports/js/dashboard.js` — tabla, estilos inyectados `synap-stock-existencias-style-v1`, clases `se-vo-stock-table` / `se-vo-stock-nested`.
- `reports/services/query_runner.py` — normalización de `codigo_barras`.
- `reports/templates/reports/dashboard_detail.html` — versión de caché `dashboard.js` (`?v=`).
