# OCR factura compra — Stage 4 plan de pruebas

## Casos

| ID | Escenario | Criterio |
|----|------------|----------|
| V1 | Documento con cabecera completa, ítems y suma ≈ total | `health_score` alto, sin `error` o `cross.suma` warning |
| V2 | Cabecera con `campos_criticos` no vacío | Validación `header.campos_criticos_faltantes` con severidad warning |
| V3 | Ítem con cantidad 0 o negativa | `lineas.cantidad_no_positiva` |
| V4 | Suma de líneas ≠ total cabecera (> umbral) | `cross.suma_lineas_vs_total` o grave |
| V5 | Sin ítems (`item_count == 0`) | `lineas.sin_items` info |
| V6 | Solo advertencias (sin error) | `has_errors` false, `has_warnings` true |
| V7 | Cada hallazgo incluye `evidencia` con `schema_version` | Assert estructura |

## Comando

```bash
docker exec Synap_app python manage.py test factura_compra_captura.tests.test_ocr_stage4
```

## Criterio

Suite `factura_compra_captura` completa en verde.
