# OCR factura compra — Stage 4 diseño (motor de validación interna)

## Objetivo

Evaluar **coherencia interna** de lo ya extraído (cabecera, ítems, calidades previas) y exponer resultados **solo** en `raw.document_engine_v1`, sin bloquear workflows, sin tocar posting, aprobación, duplicados ni validación fiscal de negocio.

## 1. ValidationEngine

- **Entrada:** snapshot de `document_engine_v1` ya construido (incluye `parsed.header`, `parsed.header_quality`, `parsed.line_items`, `line_items_quality`, `classification`, etc.).
- **Salida:**
  - `validations`: lista de hallazgos.
  - `validation_summary`: conteos por severidad y banderas agregadas.
- **Comportamiento:** siempre **no bloqueante**; las acciones de negocio no consultan este bloque en esta fase.

## 2. Validaciones de cabecera

| Código | Severidad | Condición |
|--------|-----------|-----------|
| `header.campos_criticos_faltantes` | warning | Lista no vacía en `header_quality.campos_criticos.lista`. |
| `header.total_sin_valor` | warning | `parsed.header.total.valor` ausente. |
| `header.proveedor_sin_valor` | info | `proveedor` vacío (solo informativo si no es error de negocio). |

## 3. Validaciones de ítems de línea

| Código | Severidad | Condición |
|--------|-----------|-----------|
| `lineas.sin_items` | info | `line_items_quality.item_count == 0`. |
| `lineas.cantidad_no_positiva` | warning | Ítem con cantidad parseable ≤ 0. |
| `lineas.precio_negativo` | warning | Precio unitario < 0. |
| `lineas.subtotal_no_calculable` | info | Cantidad o precio no numéricos (no se puede verificar cálculo). |

## 4. Cruce cabecera ↔ líneas

| Código | Severidad | Condición |
|--------|-----------|-----------|
| `cross.suma_lineas_vs_total` | warning | Total de cabecera y suma de (cant × precio unit) por ítem difieren más de umbral relativo (p. ej. 2 %). |
| `cross.suma_lineas_vs_total_grave` | error | Diferencia > 15 % (solo señal interna; no es error de negocio). |
| `cross.consistencia_legacy_fallida` | warning | Algún check en `header_quality.consistencia_legacy.checks` con `ok: false`. |

## 5. Modelo de severidad

- **info:** situación esperable o sin datos para comparar.
- **warning:** posible inconsistencia o dato incompleto.
- **error:** inconsistencia fuerte en el modelo interno (no equivale a rechazo de factura).

## 6. Modelo `validation_summary`

| Campo | Tipo | Significado |
|-------|------|-------------|
| `schema_version` | int | Versión del bloque resumen. |
| `counts` | dict | `{ "info": n, "warning": n, "error": n }`. |
| `has_errors` | bool | `counts["error"] > 0`. |
| `has_warnings` | bool | `counts["warning"] > 0`. |
| `health_score` | float | 0..1 heurístico (menos peso a info, más a error). |

## 7. Evidencia por validación

Cada registro incluye:

| Campo | Contenido |
|-------|-----------|
| `codigo` | Identificador estable. |
| `severidad` | `info` \| `warning` \| `error`. |
| `mensaje` | Texto en español, corto. |
| `evidencia` | `schema_version`, `raw_text` (fragmento útil), `referencias` (dict opcional con claves simbólicas: `campo`, `item_index`, valores numéricos de comparación). |

## 8. Versión `document_engine_v1`

- `version >= 5` cuando existan `validations` y `validation_summary`.

## 9. Implementación

- Código: `factura_compra_captura/services/document_validation_engine.py`.
- Punto de enganche: `heuristic_pdf._enriquecer_raw_document_engine_stage2` (tras Stage 3, sin mutar `parsed`).
