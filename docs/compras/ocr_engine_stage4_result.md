# OCR factura compra — Stage 4 resultado

## Resumen

Se incorporó un **motor de validación interna** que evalúa coherencia entre cabecera enriquecida, ítems de línea y consistencia legacy, exponiendo resultados en `raw.document_engine_v1.validations` y `validation_summary`. **No bloquea** workflows, no altera posting, aprobación, duplicados ni validación fiscal, y no modifica `OcrExtractResult`, `campos_cabecera`, `lineas_sugeridas` ni los bloques `parsed.header` / `parsed.line_items`.

## Módulo

| Archivo | Rol |
|---------|-----|
| `factura_compra_captura/services/document_validation_engine.py` | `ejecutar_validaciones_documento(document_engine_v1)` → `validations`, `validation_summary`. Constantes de umbral `UMBRAL_SUMA_WARNING` (2 %), `UMBRAL_SUMA_ERROR` (15 %). |

## Integración

- `heuristic_pdf._enriquecer_raw_document_engine_stage2`: tras armar `parsed` y `line_items_quality`, ejecuta validaciones y asigna `validations`, `validation_summary`, `version >= 5`.

## JSON

- **`validations`:** lista de `{ codigo, severidad, mensaje, evidencia }` con `evidencia.schema_version`, `raw_text`, `referencias`.
- **`validation_summary`:** `schema_version`, `counts` (info/warning/error), `has_errors`, `has_warnings`, `health_score` (0..1 heurístico).

## Documentación

- Diseño: `docs/compras/ocr_engine_stage4_design.md`
- Plan de pruebas: `docs/compras/ocr_engine_stage4_test_plan.md`

## Pruebas

```bash
docker exec Synap_app python manage.py test factura_compra_captura
```

Última ejecución: **73** tests OK (`test_ocr_stage4.py` + integración PDF).

## Alcance explícitamente no incluido

- Plantillas de proveedor, ML, bloqueo de workflow por validaciones internas (fases posteriores).
