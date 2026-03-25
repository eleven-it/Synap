# OCR factura compra — Stage 6 (5.5) diseño: observabilidad y analítica

## Objetivo

Añadir **métricas**, **analítica de correcciones**, **resúmenes orientados a workflow** y **contexto de logging estructurado** sobre `document_engine_v1`, sin ML, sin decisiones bloqueantes, sin tocar posting ni contratos de extracción pública (`OcrExtractResult`).

## 1. Modelo de métricas del motor (`document_engine_metrics`)

Diccionario **solo lectura derivado** del estado ya calculado (Stages 2–5):

| Bloque | Contenido |
|--------|-----------|
| `classification` | `tipo_documento`, `confidence` (desde `classification`). |
| `quality` | `document_score` (mismo criterio que cabecera enriquecida). |
| `validations` | `has_errors`, `has_warnings`, `counts`, `health_score` (desde `validation_summary`). |
| `template_performance` | `matched`, `template_id`, `match_confidence` (desde `supplier_template_match`); `header_fields_extracted_count`, `line_supplement_count` (desde `template_application` sin mutarla). |
| `line_items` | `parsed_count`, `item_count_quality` (desde `parsed.line_items` y `line_items_quality`). |

`schema_version: 1` en la raíz del bloque.

## 2. Métricas de proveedor / plantilla

Incluidas en `template_performance`: permiten comparar en informes **match** vs **campos extra** vs **suplemento de líneas**, sin escribir en tablas de negocio en esta etapa.

## 3. Analítica de correcciones a nivel campo (`correction_analytics`)

- **Entrada:** `analyst_feedback` (lista `corrections` con `campo`).
- **Salida:** `corrections_total`, `by_field` (conteo por nombre de campo), `fields_distinct`.
- Uso futuro: agregar eventos de UI/API que rellenen `analyst_feedback` antes del snapshot.

## 4. Resumen orientado a workflow (`workflow_facing_summary`)

- **No bloqueante:** `review_recommended` alinea con `workflow_signals.suggested_review` (misma heurística, distinta capa de presentación).
- Campos: `headline` (texto corto en español para bandejas), `template_id`, `metrics_digest` (cadena compacta para logs/agregadores).

No sustituye `workflow_signals`; coexiste como vista derivada.

## 5. Observabilidad y logs estructurados (`observability`)

- `schema_version`, `engine`, `stage_version`.
- `log_fields`: mapa **string → string** apto para `logger.info(..., extra=)` o backends que no aceptan tipos mixtos.
- Los consumidores pueden copiar `log_fields` a tracing (OpenTelemetry, etc.) en una capa posterior.

## 6. Persistencia segura de snapshots (`analytics_snapshot`)

- **Propósito:** blob JSON serializable para guardar en expediente, auditoría o cola de analítica **sin** duplicar `parsed.*` ni texto completo.
- Contenido: `schema_version`, `captured_at_utc` (ISO-8601 UTC), `document_engine_version`, referencias a métricas y resúmenes ya calculados (subconjunto estable), más `workflow_signals_digest` (solo banderas relevantes).
- **No** incluye: texto OCR, binarios, ni mutación de modelos Django en el motor heurístico.

## 7. Versión `document_engine_v1`

- `version >= 7` cuando existan los bloques Stage 6 (métricas, analítica de correcciones, snapshot, observabilidad, `workflow_facing_summary`).

## 8. Invariantes

- `parsed.header`, `parsed.line_items`, `template_application`, `workflow_signals` (forma Stage 5) **sin cambios de contrato**.
- Todo es **aditivo** bajo nuevas claves.
- Sin ML, sin auto-aprobación, sin bloqueo de workflow.
