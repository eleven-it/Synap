# Pedido masivo — importación Excel

## Columnas de la hoja `Pedido`

| Col | Campo | Uso en importación |
|-----|--------|-------------------|
| **A** | Código | Clave de búsqueda en `articulo` (`id_manual`, `IDArt`, `CodigoArticuloT`, códigos de barras, `CodArtProv`). |
| **B** | Artículo (nombre) | Desambiguación cuando el código devuelve más de un candidato. |
| **C** | `id_articulo` (oculta, plantilla v4) | Si tiene valor, resuelve el artículo por `IDArt` sin ambigüedad. |
| **D+** | Cantidades (packs) | Una columna por sucursal; el encabezado identifica la sucursal (nro/calle). |

## Resolución de artículos

1. Si la plantilla es **v4** y la columna C tiene `IDArt`, se usa ese ID directamente.
2. Si no, se consulta MySQL con el **código de la columna A**.
3. Si hay varios candidatos vendibles (Terminado + ecommerce):
   - Con **nombre en columna B**: debe coincidir **exactamente** (normalizado) con `NombreArticulo`; si no hay match → error `articulo_nombre_no_coincide`.
   - Sin nombre en columna B: se usa puntaje por código (solo cuando hay un único candidato o desambiguación legacy).
4. Si persiste el empate → error `articulo_ambiguo`.

## Recomendaciones operativas

- Usar siempre la **plantilla descargada desde Synap** (v4): columna A con `id_manual` completo y columna C con `IDArt`.
- No reemplazar el código de la columna A por el **SuperArt** padre (ej. `906807` en lugar de `906807-03`): varios SKUs comparten ese valor y la fila puede asignarse al talle/color incorrecto.
- Varias filas con el mismo SuperArt en columna A pero distinto nombre (ej. T4 y T5) son válidas: el importador desambigua por nombre y detecta duplicados solo por `IDArt` resuelto, no por el código de columna A.
- Si se edita el Excel a mano, mantener alineadas las columnas A, B y C de cada fila.

## Stock en pantalla

`stock_disponible_packs` muestra **packs enteros** (unidades disponibles ÷ múltiplo de empaque, truncado hacia abajo).

## Buscadores en la matriz

| Control | Función |
|---------|---------|
| **Ubicar en la tabla** (barra superior, ícono lupa) | Filtra / salta a filas ya cargadas (client-side). |
| **Buscar artículo** (fila celeste dentro de la matriz) | Agrega artículos del catálogo (API). Si el artículo ya está en la tabla, avisa y resalta la fila existente. |
