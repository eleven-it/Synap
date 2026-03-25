# OCR factura compra — Stage 7 plan de pruebas

## Casos

| ID | Escenario | Criterio |
|----|------------|----------|
| R1 | Serializer incluye `revision_engine_context` cuando hay `document_engine_v1` | Claves `workflow_facing_summary`, `header_campos`, `line_items_ui` |
| R2 | Contexto expone resumen workflow | `workflow_facing_summary.headline` presente o `null` explícito |
| R3 | Evidencia cabecera disponible | Entradas con `confidence` / `evidencia_preview` |
| R4 | Evidencia líneas disponible | Ítems con `campos` enriquecidos para UI |
| R5 | Append de correcciones vía API | `PATCH` con `analyst_feedback_append` incrementa `metadata.analyst_feedback.corrections` |
| R6 | Compatibilidad | `GET` sin motor antiguo no rompe; campos existentes del serializer intactos |

## Comando

```bash
docker exec Synap_app python manage.py test factura_compra_captura.tests.test_revision_engine_stage7
```

## Criterio

Suite `factura_compra_captura` completa en verde.
