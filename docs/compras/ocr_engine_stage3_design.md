# OCR factura compra — Stage 3 diseño (ítems de línea)

## Objetivo

Añadir extracción de **ítems de línea** y detección **tabular simple** en el motor interno, **solo** dentro de `raw.document_engine_v1`, sin alterar `lineas_sugeridas`, `OcrExtractResult`, posting, aprobación ni validaciones fiscales/duplicados.

## 1. LineItemParser

- **Entrada:** `texto_plano`, `ocr_structured` (opcional), `lineas_sugeridas` (salida legacy de `parsear_texto_factura`).
- **Salida:** lista de ítems enriquecidos (`parsed.line_items`) y métricas (`line_items_quality`).
- **Estrategia:**
  1. **Primario:** recorrer líneas de `ocr_structured.pages[].lines` y aplicar los **mismos patrones regex** que el parser heurístico (`_RE_LINEA_ITEM`, `_RE_LINEA_ITEM_UNIDADES`), con filtros equivalentes (prefijos a ignorar, exclusión de líneas de CUIT/comprobante).
  2. **Fallback:** si no hay coincidencias en líneas OCR estructuradas, **envolver** cada fila de `lineas_sugeridas` con modelo de confianza/evidencia (fuente `heuristic_fallback`), sin modificar el contenido legacy.

## 2. Detección tabular / columnas (simple)

- **Heurística A (líneas):** si hay ≥ 2 ítems extraídos desde líneas OCR con `page_num` distinto o misma página, se considera apoyo a layout tabular.
- **Heurística B (palabras):** agrupar `palabras_muestra` por `top` redondeado (cluster de fila); si existen ≥ 2 filas con ≥ 3 palabras alineadas horizontalmente (orden por `left`), `tabular_layout_detected = true`.
- No se infieren nombres de columnas AFIP; solo se reutiliza el patrón “descripción + números” ya validado en legacy.

## 3. Fallback respecto al heurístico

- `lineas_sugeridas` sigue calculándose solo con `parsear_texto_factura`.
- Stage 3 **no sustituye** esa lista; solo añade una vista enriquecida en `document_engine_v1`.
- Si OCR estructurado no aporta ítems (PDF sin TSV, OCR deshabilitado, o líneas sin match), se usa el fallback sobre `lineas_sugeridas`.

## 4. Evidencia por línea / por campo

- Misma base que Stage 2.5: `schema_version`, `page`, `bbox` (cuando aplique), `raw_text`.
- Por ítem: `campos.descripcion|cantidad|precio_unitario` con `valor`, `confidence`, `banda`, `evidencia`.
- En fallback heurístico, `page` y `bbox` suelen ser `null`; `raw_text` resume texto del ítem.

## 5. Confianza por línea

- **structured:** confianza media-alta por campo (constante en catálogo, alineada a extracción desde línea OCR).
- **heuristic_fallback:** confianza media-baja (réplica de datos ya inferidos por legacy).
- **banda:** `alta` / `media` / `baja` con los mismos umbrales que cabecera (≥0.75 / ≥0.5).

## 6. Resumen / calidad (`line_items_quality`)

| Campo | Significado |
|-------|-------------|
| `schema_version` | Versión del bloque de calidad. |
| `item_count` | Cantidad de ítems en `line_items`. |
| `avg_line_confidence` | Promedio de confianza por ítem (media de confianzas de campos numéricos y descripción). |
| `source` | `structured` \| `heuristic_fallback` \| `mixed` (reservado). |
| `fallback_used` | `true` si no hubo ítems desde OCR estructurado. |
| `tabular_layout_detected` | Indicador heurístico de tabla/columnas. |
| `heuristic_line_count` | `len(lineas_sugeridas)` para comparación. |
| `menos_items_que_heuristic` | Opcional: `true` si hay más líneas legacy que ítems estructurados. |

## 7. Versión `document_engine_v1`

- `version >= 4` cuando existan `parsed.line_items` y `line_items_quality` (este bloque se escribe siempre que se ejecute el enriquecimiento con OCR/PDF analizado, también si la lista de ítems está vacía).

## 8. Implementación de referencia

- Módulo: `factura_compra_captura.services.line_items_parser`.
- Integración: `_enriquecer_raw_document_engine_stage2(..., lineas_sugeridas, ...)` en `heuristic_pdf.py`.
