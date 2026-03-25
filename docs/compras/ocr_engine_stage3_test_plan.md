# OCR factura compra — Stage 3 plan de pruebas (TDD)

## Alcance

Pruebas unitarias e integración ligera sobre `line_items_parser` y enriquecimiento de `raw.document_engine_v1`, sin tocar APIs públicas ni pipeline de posting.

## Casos

| ID | Descripción | Esperado |
|----|-------------|----------|
| T1 | Tabla simple: varias líneas OCR con patrón ítem | ≥2 ítems `source=structured`, evidencias con `page` |
| T2 | Un solo ítem en línea OCR | 1 ítem, `confidence`/`banda` presentes |
| T3 | Varios ítems alineados (misma página) | `tabular_layout_detected` coherente, `item_count` |
| T4 | `ocr_structured` vacío o sin match; `lineas_sugeridas` con datos | `fallback_used=true`, mismos valores que legacy envueltos |
| T5 | Cada ítem incluye `evidencia` con `schema_version` | Cumple esquema Stage 2.5 |
| T6 | Resumen `line_items_quality` presente | `item_count`, `avg_line_confidence`, `heuristic_line_count` |
| T7 | Integración: `analizar_archivo_factura` PDF con texto de ítems | `parsed.line_items` y `line_items_quality` en `raw` |

## Comando

```bash
docker exec Synap_app python manage.py test factura_compra_captura.tests.test_ocr_stage3
```

## Criterio de salida

Suite `factura_compra_captura` completa en verde tras implementación.
