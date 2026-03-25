# OCR factura compra — Stage 5 plan de pruebas

## Casos

| ID | Escenario | Criterio |
|----|------------|----------|
| S1 | CUIT conocido en registry → plantilla asignada | `supplier_template_match.template_id` definido |
| S2 | CUIT desconocido | `template_id` nulo o motor genérico explícito |
| S3 | Plantilla añade campo extra (p. ej. CAE) | Presente en `template_application.header_fields` |
| S4 | Plantilla añade/suplementa líneas | `template_application.line_items_supplement` no vacío cuando aplica |
| S5 | `workflow_signals` presente sin romper contratos | Claves documentadas en `document_engine_v1` |
| S6 | `analyst_feedback` con schema y lista vacía | Listo para extensiones seguras |

## Comando

```bash
docker exec Synap_app python manage.py test factura_compra_captura.tests.test_ocr_stage5
```

## Criterio

Suite `factura_compra_captura` completa en verde.
