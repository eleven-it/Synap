# OCR factura compra — Stage 5 resultado

## Alcance completado

- **SupplierTemplateMatcher** (`match_supplier_template`): coincidencia por CUIT de 11 dígitos contra `SUPPLIER_TEMPLATES` en `supplier_template_registry.py`.
- **Reglas por proveedor**: estructura declarativa (`cae_regex`, `extra_item_line_regex`, `match_cuit_digits`, `priority`); plantilla demo `demo_cuit_30701855008` alineada al CUIT de tests heurísticos.
- **Ruta aditiva**: `template_application` con `header_fields` y `line_items_supplement` sin mutar `parsed.header` ni `parsed.line_items`.
- **Motor genérico por defecto**: si no hay match, `template_application.active == false` y notas explícitas.
- **Señales de flujo**: `workflow_signals` en `document_engine_v1` (`schema_version`, `supplier_template_id`, `template_matched`, `suggested_review`, `blocking_issues` fijo en `false`).
- **Feedback de analista**: `analyst_feedback` por defecto (lista vacía) + `append_analyst_correction` para registrar correcciones con normalización si el esquema no es el esperado.
- **Versión**: `document_engine_v1.version >= 6` tras enriquecimiento Stage 5.

## Archivos tocados / nuevos

| Área | Archivo |
|------|---------|
| Registry | `factura_compra_captura/services/supplier_template_registry.py` |
| Matcher | `factura_compra_captura/services/supplier_template_matcher.py` |
| Aplicación + señales + feedback | `factura_compra_captura/services/supplier_template_engine.py` |
| Integración | `factura_compra_captura/ocr/heuristic_pdf.py` (`_enriquecer_raw_document_engine_stage2`) |
| Tests | `factura_compra_captura/tests/test_ocr_stage5.py` |
| Diseño / plan | `docs/compras/ocr_engine_stage5_design.md`, `ocr_engine_stage5_test_plan.md` |

## No incluido (explícito)

- ML, auto-aprobación, decisiones bloqueantes en workflow.
- Cambios a `OcrExtractResult`, posting, aprobación, duplicados o validación fiscal.
- Mutación de contratos públicos de extracción principal más allá de campos nuevos opcionales en `document_engine_v1`.

## Comando de verificación

```bash
docker exec Synap_app python manage.py test factura_compra_captura.tests.test_ocr_stage5
docker exec Synap_app python manage.py test factura_compra_captura
```
