# OCR factura compra — Stage 6 plan de pruebas

## Casos

| ID | Escenario | Criterio |
|----|------------|----------|
| T1 | Señales de workflow accesibles | `workflow_signals` presente e inalterado en forma (Stage 5) |
| T2 | Métricas de plantilla | `document_engine_metrics.template_performance` refleja match y conteos de `template_application` |
| T3 | Agregación de correcciones | `correction_analytics` con totales y `by_field` desde `analyst_feedback` |
| T4 | Resumen analítico | `analytics_snapshot` con `schema_version`, `captured_at_utc`, versión motor |
| T5 | Compatibilidad hacia atrás | Siguen existiendo claves Stage 2–5; solo se añaden claves nuevas |
| T6 | Observabilidad | `observability.log_fields` strings para logging estructurado |

## Comando

```bash
docker exec Synap_app python manage.py test factura_compra_captura.tests.test_ocr_stage6
```

## Criterio

Suite `factura_compra_captura` completa en verde.
