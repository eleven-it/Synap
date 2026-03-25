# OCR factura compra — Stage 3 resultado

## Resumen

Se añadió extracción de **ítems de línea** y métricas de calidad **solo** en `raw.document_engine_v1`, sin modificar `OcrExtractResult`, `lineas_sugeridas`, posting, aprobación ni validaciones fiscales/duplicados.

## Componentes

| Archivo | Rol |
|---------|-----|
| `factura_compra_captura/services/line_items_parser.py` | `parsear_line_items_documento`: ítems desde líneas de `ocr_structured.pages[].lines` con los mismos regex que el heurístico; fallback envolviendo `lineas_sugeridas`. |
| `factura_compra_captura/services/confidence_catalog.py` | `CONF_LINE_ITEM_STRUCTURED`, `CONF_LINE_ITEM_HEURISTIC_FALLBACK`, `LINE_ITEMS_QUALITY_SCHEMA_VERSION`. |
| `factura_compra_captura/ocr/heuristic_pdf.py` | `_enriquecer_raw_document_engine_stage2` recibe `lineas_sugeridas`, escribe `parsed.line_items`, `line_items_quality`, `version >= 4`. |

## JSON (`document_engine_v1`)

- `version` ≥ **4** con Stage 3 activo.
- `parsed.line_items`: lista de ítems con `item_index`, `source` (`structured` \| `heuristic_fallback`), `campos` (`descripcion`, `cantidad`, `precio_unitario` con `valor`, `confidence`, `banda`, `evidencia`).
- `line_items_quality`: `schema_version`, `item_count`, `avg_line_confidence`, `source`, `fallback_used`, `tabular_layout_detected`, `heuristic_line_count`, `menos_items_que_heuristic`.

## Evidencia

Misma base que cabecera (`evidencia_estandar`: `schema_version`, `page`, `bbox`, `raw_text`).

## Pruebas

- `factura_compra_captura/tests/test_ocr_stage3.py` (tabla simple, un ítem, múltiples, fallback, evidencia/banda, resumen, integración PDF).
- Plan: `docs/compras/ocr_engine_stage3_test_plan.md`.
- Diseño: `docs/compras/ocr_engine_stage3_design.md`.

```bash
docker exec Synap_app python manage.py test factura_compra_captura
```

Última ejecución: **63** tests OK.

## Limitaciones

- Detección tabular es heurística (≥2 ítems estructurados o rejilla de palabras).
- Si OCR estructurado no matchea líneas pero el heurístico sí, se usa **solo** fallback (no mezcla ítem a ítem en esta versión).

## Stage 4

No iniciado; ampliaciones futuras (p. ej. mezcla structured+heuristic, columnas nombradas) quedan fuera de este entregable.
