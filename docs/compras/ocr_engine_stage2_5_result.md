# OCR factura compra — Stage 2.5 resultado (consolidación)

## Resumen

Implementación de la **consolidación Stage 2.5**: catálogo de confianza, evidencia unificada, `document_score`, resumen de campos críticos faltantes, checks de consistencia con legacy, y **versión 3** de `document_engine_v1`. Sin cambios en posting, aprobación ni contratos públicos de API.

## Módulos añadidos o ampliados

| Archivo | Contenido |
|---------|-----------|
| `factura_compra_captura/services/confidence_catalog.py` | Constantes de confianza por tipo de extracción, bandas, pesos del `document_score`, lista de campos críticos. |
| `factura_compra_captura/services/evidence_schema.py` | `evidencia_estandar()` con `schema_version`, `page`, `bbox`, `raw_text`. |
| `factura_compra_captura/services/document_header_quality.py` | `verificar_consistencia_legacy_vs_header`, `resumen_campos_criticos_faltantes`, `calcular_document_score`, `construir_paquete_calidad_cabecera`. |
| `factura_compra_captura/services/header_parser.py` | Uso del catálogo y evidencia estándar; campo **`banda`** por campo de cabecera. |
| `factura_compra_captura/ocr/heuristic_pdf.py` | `_enriquecer_raw_document_engine_stage2` escribe `document_score`, `parsed.header_quality`, `version >= 3`. |

## Estructura JSON en `raw.document_engine_v1` (actual)

- `version` (≥ 3)
- `document_score` (float 0..1)
- `classification` (sin cambios de significado)
- `parsed.header` (campos con `valor`, `confidence`, `banda`, `source`, `evidencia`)
- `parsed.header_quality`:
  - `campos_criticos` (`lista`, `cantidad`, `total_campos`)
  - `consistencia_legacy` (`checks`, `score`, `pares_comparados`)
  - `componentes_document_score`
  - `pesos_document_score`

Campos Stage 1 (`engine_mode`, `preprocess`, `ocr_structured`) se conservan cuando aplican.

## Pruebas

- `docker exec Synap_app python manage.py test factura_compra_captura` — suite completa en verde.
- Tests OCR actualizados para `version >= 3`, `document_score`, `header_quality`, `banda` y `schema_version` en evidencias.

## Documentación de diseño

Ver **`docs/compras/ocr_engine_stage2_5_design.md`** (fuentes de verdad, reglas, limitaciones).

## Próximos pasos (no realizados)

- Ítems de línea, motor de validación de negocio, UI de revisión usando `document_score` como priorización.
