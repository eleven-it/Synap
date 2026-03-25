# OCR factura compra — Stage 6 resultado

## Alcance completado

- **`document_engine_metrics`**: métricas derivadas (`classification`, `quality`, `validations`, `template_performance`, `line_items`) con `schema_version: 1`.
- **`correction_analytics`**: agregación desde `analyst_feedback.corrections` (`corrections_total`, `by_field`, `fields_distinct`).
- **`workflow_facing_summary`**: texto corto en español (`headline`), `review_recommended`, `metrics_digest` (no bloqueante; complementa `workflow_signals`).
- **`observability`**: `log_fields` con valores **string** para `logging` / agregadores (`fc_ocr_*`).
- **`analytics_snapshot`**: instantánea serializable con `captured_at_utc` (ISO-8601 UTC con sufijo `Z`), versión motor, métricas embebidas y `workflow_signals_digest` (sin texto OCR ni `parsed` completo).
- **`document_engine_v1.version` ≥ 7** tras el enriquecimiento.

## Archivos

| Rol | Ruta |
|-----|------|
| Lógica analítica | `factura_compra_captura/services/document_engine_analytics.py` |
| Integración | `factura_compra_captura/ocr/heuristic_pdf.py` (`_enriquecer_raw_document_engine_stage2`) |
| Tests | `factura_compra_captura/tests/test_ocr_stage6.py` |
| Diseño / plan | `docs/compras/ocr_engine_stage6_design.md`, `ocr_engine_stage6_test_plan.md` |

## Invariantes respetados

- Sin cambios en `OcrExtractResult`, posting, aprobación, duplicados ni validación fiscal.
- `parsed.header`, `parsed.line_items`, `template_application` y `workflow_signals` (forma Stage 5) **sin cambios de contrato**; solo se añaden claves nuevas en `document_engine_v1`.
- Sin decisiones bloqueantes de workflow; `workflow_signals.blocking_issues` sigue en `false`.

## Comandos de verificación

```bash
docker exec Synap_app python manage.py test factura_compra_captura.tests.test_ocr_stage6
docker exec Synap_app python manage.py test factura_compra_captura
```

## Persistencia futura

El snapshot está pensado para guardarse como JSON en columnas de auditoría o eventos de analítica; el motor OCR **no** escribe tablas de negocio por sí solo en Stage 6.
